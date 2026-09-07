# -*- coding: utf-8 -*-
"""
Replanner — 重规划器（ZBC MISSING 项补齐）
===========================================
触发条件：
  - 步骤失败超过 max_retries
  - 观察到环境变化（DB 不可用、AI 熔断、工具不可用）
  - 预算超阈值（max_steps / max_time / max_cost）

调整策略：
  - 换工具：当前工具不可用时换备用工具
  - 换参数：参数不当时调整参数
  - 拆步骤：复杂步骤拆为多个简单步骤
  - 简化目标：目标过大时缩小范围

核心原则：不是同参数 retry，而是基于 observation 重新规划。

复用：
  - planner.Planner 重新生成计划
  - observation.Observation 作为重规划输入
  - ai_task_engine 持久化重规划记录

与 OSAI Contract 对齐点（C-01 Agent Runtime Contract）：
  - replan_count 计数，max_replans 上限
  - 重规划触发：step_failure / environment_change / budget_exceeded
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .planner import Plan, PlanStep, Planner, PlanMode


class ReplanTrigger(str, Enum):
    """重规划触发原因。"""
    STEP_FAILURE = "step_failure"                 # 步骤失败超 max_retries
    ENVIRONMENT_CHANGE = "environment_change"     # 观察到环境变化
    BUDGET_EXCEEDED = "budget_exceeded"           # 预算超阈值
    LOW_CONFIDENCE = "low_confidence"             # 低置信度结果
    HUMAN_FEEDBACK = "human_feedback"             # 人工反馈
    GOAL_MISMATCH = "goal_mismatch"               # 执行结果与目标不符


class ReplanStrategy(str, Enum):
    """重规划策略。"""
    SWITCH_TOOL = "switch_tool"           # 换工具
    ADJUST_PARAMS = "adjust_params"       # 换参数
    SPLIT_STEP = "split_step"             # 拆步骤
    SIMPLIFY_GOAL = "simplify_goal"       # 简化目标
    FULL_REPLAN = "full_replan"           # 完全重新规划
    SKIP_STEP = "skip_step"               # 跳过当前步骤


@dataclass
class ReplanDecision:
    """重规划决策。"""
    decision_id: str = field(default_factory=lambda: f"replan_{uuid.uuid4().hex[:12]}")
    trigger: str = ""
    strategy: str = ""
    reason: str = ""
    original_step_index: int = -1
    original_step_action: str = ""
    new_steps: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    observation_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Replanner:
    """基于 Observation 的重规划器。

    用法：
        replanner = Replanner(planner=planner)
        decision = replanner.should_replan(
            observation=obs,
            failed_step=step,
            retry_count=3,
            max_retries=3,
        )
        if decision:
            new_plan = replanner.replan(goal, current_plan, decision, observation)
    """

    def __init__(
        self,
        planner: Optional[Planner] = None,
        max_replans: int = 2,
        ai_chat_func: Optional[Callable] = None,
    ):
        """
        Args:
            planner: 规划器实例（None 则新建）
            max_replans: 最大重规划次数
            ai_chat_func: AI 调用函数（用于深度重规划）
        """
        self._planner = planner or Planner(ai_chat_func=ai_chat_func)
        self._max_replans = max_replans
        self._replan_count = 0
        self._history: List[ReplanDecision] = []

    @property
    def replan_count(self) -> int:
        return self._replan_count

    @property
    def history(self) -> List[ReplanDecision]:
        return list(self._history)

    def can_replan(self) -> bool:
        """是否还可以重规划。"""
        return self._replan_count < self._max_replans

    def should_replan(
        self,
        observation: Optional[Any] = None,
        failed_step: Optional[PlanStep] = None,
        retry_count: int = 0,
        max_retries: int = 3,
        budget_exceeded: bool = False,
        low_confidence: bool = False,
    ) -> Optional[ReplanDecision]:
        """判断是否需要重规划。

        Args:
            observation: 当前观察结果
            failed_step: 失败的步骤
            retry_count: 当前重试次数
            max_retries: 最大重试次数
            budget_exceeded: 是否预算超限
            low_confidence: 是否低置信度

        Returns:
            ReplanDecision 或 None（不需要重规划）
        """
        # 检查重规划次数上限
        if not self.can_replan():
            return None

        # 触发1：步骤失败超 max_retries
        if failed_step is not None and retry_count >= max_retries:
            strategy = self._select_strategy_for_failure(failed_step, observation)
            return ReplanDecision(
                trigger=ReplanTrigger.STEP_FAILURE.value,
                strategy=strategy.value,
                reason=f"step '{failed_step.action}' failed {retry_count} times (max={max_retries})",
                original_step_index=failed_step.index,
                original_step_action=failed_step.action,
                observation_summary=self._summarize_observation(observation),
            )

        # 触发2：环境变化
        if observation is not None and getattr(observation, "environment_changed", False):
            changed = getattr(observation, "changed_fields", [])
            if "db_status" in changed or "ai_status" in changed or "ai_circuit_state" in changed:
                return ReplanDecision(
                    trigger=ReplanTrigger.ENVIRONMENT_CHANGE.value,
                    strategy=ReplanStrategy.ADJUST_PARAMS.value,
                    reason=f"environment changed: {', '.join(changed)}",
                    observation_summary=self._summarize_observation(observation),
                )

        # 触发3：预算超限
        if budget_exceeded:
            return ReplanDecision(
                trigger=ReplanTrigger.BUDGET_EXCEEDED.value,
                strategy=ReplanStrategy.SIMPLIFY_GOAL.value,
                reason="budget exceeded, simplifying goal",
                observation_summary=self._summarize_observation(observation),
            )

        # 触发4：低置信度
        if low_confidence:
            return ReplanDecision(
                trigger=ReplanTrigger.LOW_CONFIDENCE.value,
                strategy=ReplanStrategy.SPLIT_STEP.value,
                reason="low confidence result, splitting step for verification",
                observation_summary=self._summarize_observation(observation),
            )

        return None

    def replan(
        self,
        goal: str,
        current_plan: Plan,
        decision: ReplanDecision,
        observation: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Plan:
        """执行重规划，返回新计划。

        Args:
            goal: 原始目标
            current_plan: 当前计划
            decision: 重规划决策
            observation: 当前观察结果
            context: 附加上下文

        Returns:
            新的 Plan
        """
        self._replan_count += 1
        self._history.append(decision)

        strategy = ReplanStrategy(decision.strategy)

        if strategy == ReplanStrategy.FULL_REPLAN:
            return self._full_replan(goal, observation, context)
        elif strategy == ReplanStrategy.SWITCH_TOOL:
            return self._switch_tool_replan(current_plan, decision, observation)
        elif strategy == ReplanStrategy.ADJUST_PARAMS:
            return self._adjust_params_replan(current_plan, decision, observation)
        elif strategy == ReplanStrategy.SPLIT_STEP:
            return self._split_step_replan(current_plan, decision)
        elif strategy == ReplanStrategy.SIMPLIFY_GOAL:
            return self._simplify_goal_replan(goal, current_plan, decision)
        elif strategy == ReplanStrategy.SKIP_STEP:
            return self._skip_step_replan(current_plan, decision)
        else:
            return self._full_replan(goal, observation, context)

    def _select_strategy_for_failure(
        self,
        failed_step: PlanStep,
        observation: Optional[Any],
    ) -> ReplanStrategy:
        """根据失败原因选择重规划策略。"""
        error = (failed_step.error or "").lower()

        # 工具不可用 → 换工具
        if any(kw in error for kw in ("not found", "unavailable", "no handler", "disabled")):
            return ReplanStrategy.SWITCH_TOOL

        # 参数错误 → 调整参数
        if any(kw in error for kw in ("invalid param", "bad request", "missing", "type error")):
            return ReplanStrategy.ADJUST_PARAMS

        # 超时/资源不足 → 拆步骤
        if any(kw in error for kw in ("timeout", "memory", "too large", "rate limit")):
            return ReplanStrategy.SPLIT_STEP

        # AI 熔断 → 换工具（降级到规则）
        if observation is not None:
            if getattr(observation, "ai_circuit_state", "") == "OPEN":
                return ReplanStrategy.SWITCH_TOOL

        # 默认完全重新规划
        return ReplanStrategy.FULL_REPLAN

    def _full_replan(
        self,
        goal: str,
        observation: Optional[Any],
        context: Optional[Dict[str, Any]],
    ) -> Plan:
        """完全重新规划。"""
        replan_context = dict(context or {})
        if observation:
            replan_context["previous_observation"] = {
                "db_status": getattr(observation, "db_status", "unknown"),
                "ai_status": getattr(observation, "ai_status", "unknown"),
                "environment_changed": getattr(observation, "environment_changed", False),
            }
        replan_context["replan_count"] = self._replan_count
        replan_context["replan_reason"] = "full_replan_after_failure"

        return self._planner.plan(
            goal,
            mode=PlanMode.DEEP,
            context=replan_context,
        )

    def _switch_tool_replan(
        self,
        current_plan: Plan,
        decision: ReplanDecision,
        observation: Optional[Any],
    ) -> Plan:
        """换工具重规划：将失败步骤的工具替换为备用工具。"""
        new_plan = Plan(
            goal=current_plan.goal,
            mode=current_plan.mode,
            model=current_plan.model,
            is_fallback=True,
            fallback_reason=f"switch_tool: {decision.reason}",
        )

        # 备用工具映射
        fallback_tools = {
            "ai_analysis": "rule_based_analysis",
            "db_query": "cache_query",
            "web_search": "local_search",
            "direct_execution": "rule_engine",
        }

        for step in current_plan.steps:
            new_step = PlanStep(
                index=step.index,
                action=step.action,
                tool=fallback_tools.get(step.tool, step.tool),
                params=dict(step.params),
                expected_output=step.expected_output,
                risk_level=step.risk_level,
            )
            if step.index == decision.original_step_index:
                new_step.params["_replan_note"] = f"switched from {step.tool} to {new_step.tool}"
                new_step.risk_level = "medium"
            new_plan.steps.append(new_step)

        decision.new_steps = [s.to_dict() for s in new_plan.steps]
        return new_plan

    def _adjust_params_replan(
        self,
        current_plan: Plan,
        decision: ReplanDecision,
        observation: Optional[Any],
    ) -> Plan:
        """调整参数重规划。"""
        new_plan = Plan(
            goal=current_plan.goal,
            mode=current_plan.mode,
            model=current_plan.model,
            is_fallback=True,
            fallback_reason=f"adjust_params: {decision.reason}",
        )

        for step in current_plan.steps:
            new_step = PlanStep(
                index=step.index,
                action=step.action,
                tool=step.tool,
                params=dict(step.params),
                expected_output=step.expected_output,
                risk_level=step.risk_level,
            )
            if step.index == decision.original_step_index:
                # 保守调整：减少批量、增加超时、降低精度
                new_step.params["_retry_adjusted"] = True
                new_step.params["batch_size"] = min(
                    int(new_step.params.get("batch_size", 100)), 10
                )
                new_step.params["timeout"] = int(new_step.params.get("timeout", 60)) * 2
                new_step.params["_replan_note"] = "params adjusted after failure"
            new_plan.steps.append(new_step)

        decision.new_steps = [s.to_dict() for s in new_plan.steps]
        return new_plan

    def _split_step_replan(
        self,
        current_plan: Plan,
        decision: ReplanDecision,
    ) -> Plan:
        """拆步骤重规划：将失败步骤拆为多个小步骤。"""
        new_plan = Plan(
            goal=current_plan.goal,
            mode=current_plan.mode,
            model=current_plan.model,
            is_fallback=True,
            fallback_reason=f"split_step: {decision.reason}",
        )

        new_index = 0
        for step in current_plan.steps:
            if step.index == decision.original_step_index:
                # 拆为：准备 → 执行 → 验证
                sub_steps = [
                    PlanStep(
                        index=new_index,
                        action=f"[准备] {step.action}",
                        tool=step.tool,
                        params={"phase": "prepare", **step.params},
                        expected_output=f"准备完成：{step.expected_output}",
                        risk_level="low",
                    ),
                    PlanStep(
                        index=new_index + 1,
                        action=f"[执行] {step.action}",
                        tool=step.tool,
                        params={"phase": "execute", **step.params},
                        expected_output=step.expected_output,
                        risk_level=step.risk_level,
                    ),
                    PlanStep(
                        index=new_index + 2,
                        action=f"[验证] {step.action}",
                        tool="verification",
                        params={"phase": "verify", "original_action": step.action},
                        expected_output=f"验证结果：{step.expected_output}",
                        risk_level="low",
                    ),
                ]
                new_plan.steps.extend(sub_steps)
                new_index += 3
            else:
                step.index = new_index
                new_plan.steps.append(step)
                new_index += 1

        decision.new_steps = [s.to_dict() for s in new_plan.steps]
        return new_plan

    def _simplify_goal_replan(
        self,
        goal: str,
        current_plan: Plan,
        decision: ReplanDecision,
    ) -> Plan:
        """简化目标重规划：只保留关键步骤。"""
        new_plan = Plan(
            goal=f"{goal}（简化版）",
            mode=PlanMode.RULE_BASED.value,
            model="rule_based",
            is_fallback=True,
            fallback_reason=f"simplify_goal: {decision.reason}",
        )

        # 只保留低风险步骤
        critical_steps = [
            s for s in current_plan.steps
            if s.risk_level in ("low", "medium")
        ]
        if not critical_steps and current_plan.steps:
            critical_steps = [current_plan.steps[0]]

        for i, step in enumerate(critical_steps[:5]):
            new_plan.steps.append(PlanStep(
                index=i,
                action=step.action,
                tool=step.tool,
                params=dict(step.params),
                expected_output=step.expected_output,
                risk_level="low",
            ))

        decision.new_steps = [s.to_dict() for s in new_plan.steps]
        return new_plan

    def _skip_step_replan(
        self,
        current_plan: Plan,
        decision: ReplanDecision,
    ) -> Plan:
        """跳过失败步骤，继续后续步骤。"""
        new_plan = Plan(
            goal=current_plan.goal,
            mode=current_plan.mode,
            model=current_plan.model,
            is_fallback=True,
            fallback_reason=f"skip_step: {decision.reason}",
        )

        new_index = 0
        for step in current_plan.steps:
            if step.index == decision.original_step_index:
                continue  # 跳过
            step.index = new_index
            step.status = "pending"
            new_plan.steps.append(step)
            new_index += 1

        decision.new_steps = [s.to_dict() for s in new_plan.steps]
        return new_plan

    @staticmethod
    def _summarize_observation(observation: Optional[Any]) -> Dict[str, Any]:
        """提取观察结果摘要。"""
        if observation is None:
            return {}
        return {
            "db_status": getattr(observation, "db_status", "unknown"),
            "ai_status": getattr(observation, "ai_status", "unknown"),
            "ai_circuit_state": getattr(observation, "ai_circuit_state", "unknown"),
            "collection_status": getattr(observation, "collection_status", "unknown"),
            "environment_changed": getattr(observation, "environment_changed", False),
            "previous_step_error": getattr(observation, "previous_step_error", None),
        }

    def reset(self) -> None:
        """重置重规划计数（测试用）。"""
        self._replan_count = 0
        self._history.clear()
