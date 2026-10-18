# -*- coding: utf-8 -*-
"""
Planner — 基于 OSAI Contract 的规划器
======================================
将 goal（自然语言目标）分解为步骤列表。
经唯一 Gateway 调用获准的类型化请求；未配置时明确不可用。

每步包含：action、tool、params、expected_output、risk_level。

复用：
  - 唯一 SYSTEM AI Gateway（不重写 AI 调用）
  - ai_task_engine 持久化规划结果到 ai_task 表（复用）

设计原则：
  - AI 输出必须经过 JSON 解析和结构验证，不直接信任
  - 规划失败返回空计划与明确原因，不伪造执行动作
  - 规划结果可持久化、可人工修正
  - 不引入 OSAI 运行时依赖，通过 Contract 接口对齐

与 OSAI Contract 对齐点（C-01 Agent Runtime Contract）：
  - Plan 结构：steps[].{action, tool, params, expected_output, risk_level}
  - 规划模式仅代表预算；模型选择归唯一 Gateway
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class PlanMode(str, Enum):
    """规划模式。"""
    ROUTINE = "routine"       # 常规规划预算
    DEEP = "deep"             # 深度规划预算
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
    context_budget: Optional[Dict[str, Any]] = None
    is_fallback: bool = False           # 是否为降级规划
    fallback_reason: str = ""
    outcome_contract_sha256: Optional[str] = None
    # Populated only from independently read canonical committed output receipts.
    outcome_receipt_bindings: Dict[str, Dict[str, Any]] = field(default_factory=dict)

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
        gateway_request_factory: Optional[Callable] = None,
    ):
        """
        Args:
            ai_chat_func: AI 调用函数 callback(system, user, model) -> (content, provider)
                          None 则使用唯一 Gateway 的类型化请求工厂
            persist_func: 规划结果持久化回调 callback(plan) -> None
            default_mode: 默认规划模式
        """
        self._ai_chat_func = ai_chat_func
        self._persist_func = persist_func
        self._default_mode = default_mode
        self._gateway_request_factory = gateway_request_factory
        self._gateway_context = {}

    def _get_ai_chat(self) -> Callable:
        """获取 AI 调用函数。"""
        if self._ai_chat_func:
            return self._ai_chat_func
        def gateway_chat(system, user, **kwargs):
            from lumenis.system.ai_gateway import core
            if self._gateway_request_factory is None:
                # A generic context cannot mint source-use or external-send
                # authority. An unconfigured planner remains explicitly absent.
                raise RuntimeError("PLANNER_AUTHORIZED_REQUEST_REQUIRED")
            request = self._gateway_request_factory(system, user, dict(self._gateway_context))
            from lumenis.system.ai_gateway.owned_service import OwnedServiceRequest
            if type(request) is not OwnedServiceRequest:
                raise RuntimeError("PLANNER_TYPED_REQUEST_REQUIRED")
            from lumenis.system.ai_gateway.owned_service import measure_owned_request, owned_service_status
            measured = measure_owned_request(request)
            omitted = []
            reduced = dict(self._gateway_context)
            # Preserve goal, identity/scope and tool contracts in full. Remove
            # only complete low-priority derived sections, with explicit receipt.
            for key in ("derived_memory", "reviewed_learning_context"):
                if measured.get("ok") is not True or measured.get("fits") is True:
                    break
                if key not in reduced:
                    continue
                value = reduced.pop(key)
                import hashlib
                omitted.append({"section": key, "sha256": hashlib.sha256(json.dumps(
                    value, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                    "reason": "selected_model_context_budget"})
                reduced["context_omissions"] = list(omitted)
                user = self._build_user_prompt(self._gateway_goal, reduced, self._gateway_max_steps)
                request = self._gateway_request_factory(system, user, dict(self._gateway_context))
                if type(request) is not OwnedServiceRequest:
                    raise RuntimeError("PLANNER_TYPED_REQUEST_REQUIRED")
                measured = measure_owned_request(request)
            if measured.get("ok") is not True:
                raise RuntimeError(measured.get("code", "PLANNER_TOKEN_COUNT_UNAVAILABLE"))
            self._last_context_budget = {**measured, "omitted_sections": omitted}
            if measured.get("fits") is not True:
                raise RuntimeError("PLANNER_REQUIRED_CONTEXT_EXCEEDS_MODEL_BUDGET")
            status = owned_service_status(request.domain_id)
            if status.get("binding_sha256") != measured.get("binding_sha256"):
                raise RuntimeError("PLANNER_MEASURED_BINDING_CHANGED")
            # Gateway and runtime revalidate binding, source and exact tokenizer
            # budget again before generation; this receipt is never an authority.
            result = core.run_owned_request(request, expected_binding_sha256=measured["binding_sha256"])
            if not isinstance(result, dict) or result.get("ok") is not True:
                raise RuntimeError((result or {}).get("code", "PLANNER_GATEWAY_UNAVAILABLE"))
            content = result.get("analysis")
            if isinstance(content, dict):
                content = json.dumps(content, ensure_ascii=False, allow_nan=False)
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError("PLANNER_GATEWAY_RESULT_INVALID")
            return content, result.get("provider", "owned")
        return gateway_chat

    def _select_model(self, mode: PlanMode) -> str:
        # The unique Gateway owns actual user/provider/model selection. These
        # planning budgets do not choose or silently fall back to any provider.
        return "gateway-selected" if mode is not PlanMode.RULE_BASED else "none"

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
        mode = mode or self._default_mode
        model = self._select_model(mode)
        plan = Plan(goal=goal, mode=mode.value, model=model)

        if mode == PlanMode.RULE_BASED:
            return self._rule_based_plan(goal, plan)

        try:
            self._gateway_context = dict(context or {})
            self._gateway_goal, self._gateway_max_steps = goal, max_steps
            self._last_context_budget = None
            user_prompt = self._build_user_prompt(goal, context, max_steps)
            chat_func = self._get_ai_chat()

            content, provider = chat_func(
                _PLANNER_SYSTEM_PROMPT,
                user_prompt,
                model=model,
                temperature=0.1,
                max_tokens=2000,
            )

            plan.context_budget = self._last_context_budget
            plan.raw_response = content or ""
            plan.token_usage = self._extract_token_usage()

            if not content:
                return self._fallback_plan(goal, plan, "AI returned empty response")

            steps = self._parse_plan_response(content, max_steps)
            if not steps:
                return self._fallback_plan(goal, plan, "Failed to parse AI response as JSON")

            plan.steps = steps
            plan.is_fallback = False

        except Exception as e:
            return self._fallback_plan(goal, plan, f"AI planning failed: {str(e)[:200]}")

        # 持久化
        if self._persist_func:
            try:
                self._persist_func(plan)
            except Exception:
                pass

        return plan

    def _build_user_prompt(
        self,
        goal: str,
        context: Optional[Dict[str, Any]],
        max_steps: int,
    ) -> str:
        """构建用户提示词。"""
        parts = [f"目标：{goal}", f"最大步骤数：{max_steps}"]
        if context:
            raw = json.dumps(context, ensure_ascii=False, allow_nan=False)
            # Explicit bounded payload, never an invalid half-JSON or silent loss.
            if len(raw.encode("utf-8")) > 8 * 1024 * 1024:
                raise ValueError("PLANNER_CONTEXT_TOO_LARGE")
            parts.append(f"上下文：{raw}")
        parts.append("请输出规划 JSON。")
        return "\n".join(parts)

    def _parse_plan_response(self, content: str, max_steps: int) -> List[PlanStep]:
        """解析 AI 返回的规划 JSON。"""
        # 提取 JSON（AI 可能在 JSON 前后加文字）
        json_str = self._extract_json(content)
        if not json_str:
            return []

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return []

        raw_steps = data.get("steps", [])
        if not isinstance(raw_steps, list):
            return []

        steps = []
        for i, raw in enumerate(raw_steps[:max_steps]):
            if not isinstance(raw, dict):
                continue
            step = PlanStep(
                index=i,
                action=str(raw.get("action", "")).strip(),
                tool=str(raw.get("tool", "")).strip(),
                params=raw.get("params", {}) if isinstance(raw.get("params"), dict) else {},
                expected_output=str(raw.get("expected_output", "")).strip(),
                risk_level=str(raw.get("risk_level", "low")).lower(),
            )
            if step.risk_level not in ("low", "medium", "high", "critical"):
                step.risk_level = "low"
            if step.action:  # 至少要有 action
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

        # 尝试提取第一个 {...} 块
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            candidate = match.group(0)
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

        # 尝试提取 ```json ... ``` 块
        match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if match:
            candidate = match.group(1).strip()
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

        return None

    def _fallback_plan(self, goal: str, plan: Plan, reason: str) -> Plan:
        """降级规划：单步直接执行。"""
        plan.is_fallback = True
        plan.fallback_reason = reason
        plan.context_budget = getattr(self, "_last_context_budget", None)
        # A missing/invalid model response is not a generic executable action.
        plan.steps = []
        return plan

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
        return plan

    @staticmethod
    def _extract_token_usage() -> Dict[str, int]:
        # No usage claim without the exact Gateway receipt. Never read a stale
        # thread-local receipt from a retired provider module.
        return {}

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
