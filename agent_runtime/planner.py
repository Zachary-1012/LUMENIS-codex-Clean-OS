# -*- coding: utf-8 -*-
"""
Planner — 基于 OSAI Contract 的规划器
======================================
将 goal（自然语言目标）分解为步骤列表。
调用智谱 GLM：glm-5.3 做深度规划，glm-4.5-air 做常规规划。

每步包含：action、tool、params、expected_output、risk_level。

复用：
  - intelligence._chat() 调用智谱 GLM（不重写 AI 调用）
  - ai_task_engine 持久化规划结果到 ai_task 表（复用）

设计原则：
  - AI 输出必须经过 JSON 解析和结构验证，不直接信任
  - 规划失败时降级为单步计划（直接执行 goal）
  - 规划结果可持久化、可人工修正
  - 不引入 OSAI 运行时依赖，通过 Contract 接口对齐

与 OSAI Contract 对齐点（C-01 Agent Runtime Contract）：
  - Plan 结构：steps[].{action, tool, params, expected_output, risk_level}
  - 规划模型选择：deep=glm-5.3, routine=glm-4.5-air
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
    ROUTINE = "routine"       # 常规规划，glm-4.5-air
    DEEP = "deep"             # 深度规划，glm-5.3
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
    ):
        """
        Args:
            ai_chat_func: AI 调用函数 callback(system, user, model) -> (content, provider)
                          None 则使用 intelligence._chat
            persist_func: 规划结果持久化回调 callback(plan) -> None
            default_mode: 默认规划模式
        """
        self._ai_chat_func = ai_chat_func
        self._persist_func = persist_func
        self._default_mode = default_mode

    def _get_ai_chat(self) -> Callable:
        """获取 AI 调用函数。"""
        if self._ai_chat_func:
            return self._ai_chat_func
        # 复用 ZBC 现有 AI 调用（智谱 GLM）
        from intelligence import _chat as zbc_chat
        return zbc_chat

    def _select_model(self, mode: PlanMode) -> str:
        """根据规划模式选择模型。"""
        if mode == PlanMode.DEEP:
            return "glm-5.3"
        return "glm-4.5-air"

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
            user_prompt = self._build_user_prompt(goal, context, max_steps)
            chat_func = self._get_ai_chat()

            content, provider = chat_func(
                _PLANNER_SYSTEM_PROMPT,
                user_prompt,
                model=model,
                temperature=0.1,
                max_tokens=2000,
            )

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
            parts.append(f"上下文：{json.dumps(context, ensure_ascii=False, default=str)[:500]}")
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
        plan.steps = [
            PlanStep(
                index=0,
                action=f"执行目标：{goal}",
                tool="direct_execution",
                params={"goal": goal},
                expected_output="目标执行结果",
                risk_level="medium",
            )
        ]
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
        """从 intelligence 模块提取 token 使用量。"""
        try:
            from intelligence import _get_call_meta
            meta = _get_call_meta()
            return {
                "prompt_tokens": meta.get("prompt_tokens", 0),
                "completion_tokens": meta.get("completion_tokens", 0),
                "total_tokens": meta.get("total_tokens", 0),
            }
        except Exception:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

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
