# -*- coding: utf-8 -*-
"""
Planner — 基于 OSAI Contract 的规划器
======================================
将 goal（自然语言目标）分解为步骤列表。
AI 规划只消费现有 SYSTEM AI Gateway 的受信任 typed Owned 请求。

每步包含：action、tool、params、expected_output、risk_level。

复用：
  - SYSTEM AI Gateway 校验模型、SourceUse、Permission 和版本
  - ai_task_engine 持久化规划结果到 ai_task 表（复用）

设计原则：
  - AI 输出必须经过 JSON 解析和结构验证，不直接信任
  - 规划失败返回无可执行步骤，不隐式执行原始目标
  - 规划结果可持久化、可人工修正
  - 不引入 OSAI 运行时依赖，通过 Contract 接口对齐

与 OSAI Contract 对齐点（C-01 Agent Runtime Contract）：
  - Plan 结构：steps[].{action, tool, params, expected_output, risk_level}
  - routine/deep 是规划要求，模型身份来自真实 Gateway 回执
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class PlanMode(str, Enum):
    """规划模式。"""
    ROUTINE = "routine"       # 常规规划
    DEEP = "deep"             # 深度规划
    RULE_BASED = "rule_based"  # 规则降级，不调用 AI


class RiskLevel(str, Enum):
    """步骤风险等级。"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PlanStep:
    """规划中的单个步骤。"""
    step_id: str = field(default_factory=lambda: f"step_{uuid.uuid4().hex[:8]}")
    index: int = 0
    action: str = ""                    # 动作描述
    tool: str = ""                      # 工具/skill 名称
    params: Dict[str, Any] = field(default_factory=dict)
    expected_output: str = ""           # 预期输出描述
    risk_level: str = "low"             # low/medium/high/critical
    status: str = "pending"             # pending/running/completed/failed/skipped
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    # Set by the trusted runtime after planning; never accepted from model JSON.
    formation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Plan:
    """完整规划结果。"""
    plan_id: str = field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}")
    goal: str = ""
    mode: str = "routine"
    model: str = ""
    steps: List[PlanStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    token_usage: Dict[str, int] = field(default_factory=dict)
    raw_response: str = ""
    is_fallback: bool = False           # 是否为降级规划
    fallback_reason: str = ""
    outcome_contract_sha256: Optional[str] = None
    # Populated only from independently read canonical committed output receipts.
    outcome_receipt_bindings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Actual Gateway provenance, separate from model-generated steps/authority.
    inference_receipt: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["steps"] = [s.to_dict() for s in self.steps]
        return d

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def max_risk(self) -> str:
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        if not self.steps:
            return "low"
        return max(self.steps, key=lambda s: order.get(s.risk_level, 0)).risk_level


# 规划系统提示词
_PLANNER_SYSTEM_PROMPT = """你是一个专业的任务规划器。将用户的目标分解为可执行的步骤列表。

要求：
1. 每个步骤必须包含：action（动作描述）、tool（工具名称）、params（参数字典）、expected_output（预期输出）、risk_level（low/medium/high/critical）
2. 步骤按执行顺序排列
3. 优先使用低风险工具
4. 涉及写操作（WRITE/COMMIT/PUSH）的步骤 risk_level 必须为 high 或 critical
5. 最多输出 15 个步骤
6. 只输出 JSON，不要输出其他文字

输出格式：
{
  "steps": [
    {
      "action": "步骤描述",
      "tool": "工具名称",
      "params": {"key": "value"},
      "expected_output": "预期结果描述",
      "risk_level": "low"
    }
  ]
}"""


class Planner:
    """Goal-driven 规划器。

    用法：
        planner = Planner()
        plan = planner.plan("分析今日广州太古汇舆情趋势", mode="deep")
        for step in plan.steps:
            print(step.action, step.tool)
    """

    def __init__(
        self,
        ai_chat_func: Optional[Callable] = None,
        persist_func: Optional[Callable] = None,
        default_mode: PlanMode = PlanMode.ROUTINE,
        *,
        owned_request_factory: Callable | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ):
        """
        Args:
            ai_chat_func: AI 调用函数 callback(system, user, model) -> (content, provider)
                          显式注入的兼容调用，不选择旧 Provider
            persist_func: 规划结果持久化回调 callback(plan) -> None
            default_mode: 默认规划模式
            owned_request_factory: 服务端绑定的请求工厂；调用方提供真实 actor、
                                   SourceUse、Evidence、scope 和输入版本
        """
        self._ai_chat_func = ai_chat_func
        self._persist_func = persist_func
        self._default_mode = default_mode
        self._owned_request_factory = owned_request_factory
        self._is_cancelled = is_cancelled

    def plan(
        self,
        goal: str,
        mode: Optional[PlanMode] = None,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 15,
    ) -> Plan:
        """将目标分解为步骤列表。

        Args:
            goal: 自然语言目标
            mode: 规划模式（routine/deep），None 则使用默认
            context: 附加上下文
            max_steps: 最大步骤数

        Returns:
            Plan 规划结果
        """
        mode = PlanMode(mode or self._default_mode)
        plan = Plan(goal=goal, mode=mode.value)
        if (type(goal) is not str or not goal.strip()
                or type(max_steps) is not int or not 1 <= max_steps <= 15
                or (context is not None and type(context) is not dict)):
            return self._fallback_plan(goal, plan, "PLANNING_INPUT_INVALID")

        if mode == PlanMode.RULE_BASED:
            return self._rule_based_plan(goal, plan)

        try:
            user_prompt = self._build_user_prompt(goal, context, max_steps)
            user_prompt += f"\n规划模式：{mode.value}"
            system_prompt = _PLANNER_SYSTEM_PROMPT.replace("最多输出 15 个步骤", f"最多输出 {max_steps} 个步骤")
            if self._owned_request_factory is not None:
                content = self._run_owned_plan(plan, system_prompt, user_prompt, max_steps)
                if content is None:
                    return self._fallback_plan(goal, plan, plan.fallback_reason)
            elif self._ai_chat_func is not None:
                content, _provider = self._ai_chat_func(
                    system_prompt, user_prompt, model=None, temperature=0.1, max_tokens=2000,
                )
            else:
                return self._fallback_plan(goal, plan, "OWNED_PLANNING_REQUEST_NOT_BOUND")

            plan.raw_response = content or ""

            if not content:
                return self._fallback_plan(goal, plan, "AI returned empty response")

            steps = self._parse_plan_response(content, max_steps)
            if not steps:
                return self._fallback_plan(goal, plan, "Failed to parse AI response as JSON")

            plan.steps = steps
            plan.is_fallback = False

        except Exception as e:
            # Exception messages can contain credentials or private payloads.
            return self._fallback_plan(goal, plan, f"AI planning failed: {type(e).__name__}")

        # 持久化
        return self._persist_plan(plan)

    def _run_owned_plan(self, plan: Plan, system_prompt: str, user_prompt: str,
                        max_steps: int) -> str | None:
        from lumenis.system.ai_gateway import core
        from lumenis.system.ai_gateway.owned_service import OwnedServiceRequest

        schema = self._response_schema(max_steps)
        schema_json = json.dumps(schema, ensure_ascii=False, sort_keys=True, allow_nan=False)
        request = self._owned_request_factory(
            system_prompt=system_prompt, user_payload=user_prompt,
            response_schema_json=schema_json, max_output_tokens=2000,
        )
        # No context field may mint SourceUse/Permission or replace the full task.
        if (type(request) is not OwnedServiceRequest or request.operation != "agent_plan"
                or request.system_prompt != system_prompt or request.user_payload != user_prompt
                or request.response_schema_json != schema_json or request.max_output_tokens != 2000):
            plan.fallback_reason = "OWNED_PLANNING_REQUEST_MISMATCH"
            return None
        result = core.run_owned_analysis(request=request, is_cancelled=self._is_cancelled)
        plan.inference_receipt = {key: value for key, value in result.items()
                                  if key not in {"analysis", "text", "runtime"}}
        if result.get("ok") is not True or result.get("status") != "COMPLETED":
            plan.fallback_reason = result.get("code") or "OWNED_PLANNING_UNAVAILABLE"
            return None
        plan.model = result["model_id"]
        plan.token_usage = {key: result[key] for key in (
            "prompt_tokens", "completion_tokens", "total_tokens") if key in result}
        analysis = result.get("analysis")
        return (json.dumps(analysis, ensure_ascii=False, allow_nan=False)
                if type(analysis) is dict else result.get("text"))

    @staticmethod
    def _response_schema(max_steps: int) -> dict[str, Any]:
        return {
            "type": "object", "required": ["steps"], "additionalProperties": False,
            "properties": {"steps": {
                "type": "array", "minItems": 1, "maxItems": max_steps,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["action", "tool", "params", "expected_output", "risk_level"],
                    "properties": {
                        "action": {"type": "string", "minLength": 1},
                        "tool": {"type": "string", "minLength": 1},
                        "params": {"type": "object"},
                        "expected_output": {"type": "string", "minLength": 1},
                        "risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    },
                },
            }},
        }

    def _persist_plan(self, plan: Plan) -> Plan:
        if self._persist_func:
            try:
                self._persist_func(plan)
            except Exception:
                plan.steps = []
                plan.is_fallback = True
                plan.fallback_reason = "PLANNING_PERSISTENCE_FAILED"
        return plan

    def _build_user_prompt(
        self,
        goal: str,
        context: Optional[Dict[str, Any]],
        max_steps: int,
    ) -> str:
        """构建用户提示词。"""
        parts = [f"目标：{goal}", f"最大步骤数：{max_steps}"]
        if context is not None:
            parts.append(f"上下文：{json.dumps(context, ensure_ascii=False, allow_nan=False)}")
        parts.append("请输出规划 JSON。")
        return "\n".join(parts)

    def _parse_plan_response(self, content: str, max_steps: int) -> List[PlanStep]:
        """解析 AI 返回的规划 JSON。"""
        # 提取 JSON（AI 可能在 JSON 前后加文字）
        json_str = self._extract_json(content)
        if not json_str:
            return []

        from lumenis.system.ai_gateway.owned_service import (
            OwnedServiceBlocked,
            _strict_json,
        )
        try:
            data = _strict_json(json_str)
            # JSON's numeric syntax can overflow (e.g. 1e999) without invoking
            # parse_constant. Reject it anywhere, including arbitrary params.
            json.dumps(data, ensure_ascii=False, allow_nan=False)
        except (OwnedServiceBlocked, ValueError, TypeError):
            return []
        if type(data) is not dict or set(data) != {"steps"}:
            return []
        raw_steps = data["steps"]
        if type(raw_steps) is not list or not 1 <= len(raw_steps) <= max_steps:
            return []

        steps = []
        for i, raw in enumerate(raw_steps):
            if (type(raw) is not dict
                    or set(raw) != {"action", "tool", "params", "expected_output", "risk_level"}
                    or any(type(raw[key]) is not str or not raw[key].strip()
                           for key in ("action", "tool", "expected_output"))
                    or type(raw["params"]) is not dict
                    or type(raw["risk_level"]) is not str
                    or raw["risk_level"] not in {"low", "medium", "high", "critical"}):
                return []
            step = PlanStep(
                index=i,
                action=raw["action"], tool=raw["tool"], params=raw["params"],
                expected_output=raw["expected_output"], risk_level=raw["risk_level"],
            )
            steps.append(step)

        return steps

    @staticmethod
    def _extract_json(text: str) -> Optional[str]:
        """从文本中提取 JSON 字符串。"""
        # 尝试直接解析
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # Balanced top-level objects avoid greedy prose braces and never pick
        # a valid nested fragment out of a malformed enclosing object.
        candidates = []
        start, depth, quoted, escaped = None, 0, False, False
        for index, character in enumerate(text):
            if depth and quoted:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    quoted = False
                continue
            if depth and character == '"':
                quoted = True
            elif character == "{":
                if depth == 0:
                    start = index
                depth += 1
            elif character == "}" and depth:
                depth -= 1
                if depth == 0:
                    candidate = text[start:index + 1]
                    try:
                        json.loads(candidate)
                        candidates.append(candidate)
                    except json.JSONDecodeError:
                        pass
        return candidates[0] if len(candidates) == 1 and depth == 0 else None

    def _fallback_plan(self, goal: str, plan: Plan, reason: str) -> Plan:
        """规划不可用；完整目标保留，执行器不收到合成步骤。"""
        plan.is_fallback = True
        plan.fallback_reason = reason
        plan.steps = []
        return self._persist_plan(plan)

    def _rule_based_plan(self, goal: str, plan: Plan) -> Plan:
        """规则规划（不调用 AI）。"""
        plan.is_fallback = True
        plan.fallback_reason = "rule_based mode"
        plan.steps = [
            PlanStep(
                index=0,
                action=f"规则执行：{goal}",
                tool="rule_engine",
                params={"goal": goal},
                expected_output="规则引擎执行结果",
                risk_level="low",
            )
        ]
        return self._persist_plan(plan)

    def validate_plan(self, plan: Plan) -> List[str]:
        """验证规划结果的完整性和安全性。

        Returns:
            问题列表（空列表表示验证通过）
        """
        issues = []
        if not plan.goal:
            issues.append("plan.goal is empty")
        if not plan.steps:
            issues.append("plan has no steps")
        for i, step in enumerate(plan.steps):
            if not step.action:
                issues.append(f"step[{i}].action is empty")
            if step.risk_level in ("high", "critical") and not step.tool:
                issues.append(f"step[{i}] high risk but no tool specified")
        return issues
