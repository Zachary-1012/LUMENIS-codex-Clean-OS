# -*- coding: utf-8 -*-
"""
Agent Loop — Goal-driven Agent Runtime 主循环
==============================================
输入：goal（自然语言目标）+ context
循环：Plan → Execute → Observe → (Replan if needed) → 直到完成/失败/取消

预算控制：
  - max_steps    : 默认 20
  - max_time     : 默认 300s
  - max_cost     : 默认 $2.0
  - max_retries  : 默认 3
  - max_replans  : 默认 2
  - timeout      : 单步超时
  - cancellation : 支持外部取消

每步检查：
  - SYSTEM Permission Gate（fail-closed）
  - SYSTEM Action Firewall
  - SYSTEM Effect Fence / Idempotency

COMMIT/PUSH/Production Write 默认 DENY；所有副作用必须走唯一 SYSTEM 安全链。
Circuit breaker：复用 runtime_guardian / ai_channel 的熔断器。

设计原则：
  - 状态机驱动，每步转换可审计
  - 预算硬限制，超限即终止（fail-closed）
  - 所有工具执行经过安全检查链
  - AI 输出不直接成为 Production Truth
  - 默认不启用（Feature Flag），不影响现有功能

与 OSAI Contract 对齐点（C-01 Agent Runtime Contract）：
  - Agent.run(task, context) -> AgentResult
  - config: max_steps/max_time/max_cost/max_retries/max_replans/timeout
  - status: completed/failed/cancelled/timeout
  - metrics: steps/duration_ms/cost/replans/retries
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .state_machine import AgentState, AgentStateMachine, StateTransitionError
from .observation import ObservationLayer, Observation
from .planner import Plan, PlanStep, Planner, PlanMode
from .replanner import Replanner, ReplanDecision
from lumenis.shared.evaluation.trajectory import TrajectoryEvaluator, TrajectoryMetrics, TrajectoryEvaluation
from .durable_adapter import DurableExecutionAdapter


@dataclass
class AgentConfig:
    """Agent 运行配置（预算控制）。"""
    max_steps: int = 20
    max_time_seconds: float = 300.0
    max_cost: float = 2.0
    max_retries: int = 3
    max_replans: int = 2
    step_timeout_seconds: float = 60.0
    circuit_breaker_threshold: int = 5
    enable_durable_execution: bool = True
    enable_evaluation: bool = True
    plan_mode: str = "routine"  # routine / deep / rule_based

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentResult:
    """Agent 执行结果。"""
    agent_id: str
    task_id: str
    status: str                        # completed/failed/cancelled/timeout/budget_exceeded
    goal: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    plan: Optional[Dict[str, Any]] = None
    evaluation: Optional[Dict[str, Any]] = None
    transitions: List[Dict[str, Any]] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AgentLoop:
    """Goal-driven Agent Loop 主循环。

    用法：
        config = AgentConfig(max_steps=10, max_time_seconds=120)
        loop = AgentLoop(config=config)
        result = loop.run("分析今日广州太古汇舆情趋势", context={})
        print(result.status, result.metrics)
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        planner: Optional[Planner] = None,
        replanner: Optional[Replanner] = None,
        observation_layer: Optional[ObservationLayer] = None,
        evaluator: Optional[TrajectoryEvaluator] = None,
        durable_adapter: Optional[DurableExecutionAdapter] = None,
        tool_executor: Optional[Callable] = None,
        ai_chat_func: Optional[Callable] = None,
        permission_gate: Optional[Any] = None,
    ):
        """
        Args:
            config: Agent 配置（预算控制）
            planner: 规划器（None 则新建）
            replanner: 重规划器（None 则新建）
            observation_layer: 观察层（None 则新建，auto_register_default=False 避免测试时连 DB）
            evaluator: 轨迹评估器（None 则新建）
            durable_adapter: Durable Execution 适配器（None 则新建）
            tool_executor: 工具执行函数 callback(step: PlanStep, context) -> Dict
                           None 则使用默认执行器（仅记录，不真实执行）
            ai_chat_func: AI 调用函数（用于 planner）
            permission_gate: 权限门实例（None 则延迟获取）
        """
        self.config = config or AgentConfig()
        self._ai_chat_func = ai_chat_func
        self._planner = planner or Planner(ai_chat_func=ai_chat_func)
        self._replanner = replanner or Replanner(
            planner=self._planner, max_replans=self.config.max_replans)
        self._observation_layer = observation_layer or ObservationLayer(
            auto_register_default=False)
        self._evaluator = evaluator or TrajectoryEvaluator()
        self._durable = durable_adapter or DurableExecutionAdapter(
            enabled=self.config.enable_durable_execution)
        self._tool_executor = tool_executor or self._default_tool_executor
        self._permission_gate = permission_gate

        # 运行时状态
        self._cancelled = False
        self._cancel_lock = threading.Lock()
        self._start_time: float = 0.0
        self._current_cost: float = 0.0
        self._steps_started: int = 0
        self._active_context: Dict[str, Any] = {}
        self._consecutive_failures: int = 0
        self._current_plan: Optional[Plan] = None

    # ──────────────────────────────────────────────────────────
    # 公共 API
    # ──────────────────────────────────────────────────────────

    def run(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
    ) -> AgentResult:
        """执行 Agent Loop。

        Args:
            goal: 自然语言目标
            context: 附加上下文
            agent_id: Agent ID（None 则自动生成）

        Returns:
            AgentResult 执行结果
        """
        agent_id = agent_id or f"agent_{uuid.uuid4().hex[:12]}"
        context = context or {}

        # 初始化
        self._cancelled = False
        self._start_time = time.time()
        self._current_cost = 0.0
        self._steps_started = 0
        self._active_context = context
        self._consecutive_failures = 0
        self._replanner.reset()

        sm = AgentStateMachine(agent_id=agent_id, goal=goal)
        self._observation_layer.agent_id = agent_id

        result = AgentResult(
            agent_id=agent_id,
            task_id="",
            status="running",
            goal=goal,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        # 创建 Durable Task
        task_id = self._durable.create_task(goal, agent_id=agent_id, context=context)
        result.task_id = task_id

        try:
            # 1. PLANNING
            sm.transition_to(AgentState.PLANNING, reason="start planning")
            plan = self._planner.plan(
                goal,
                mode=PlanMode(self.config.plan_mode),
                context=context,
            )
            result.plan = plan.to_dict()
            self._current_plan = plan
            self._current_cost += self._estimate_plan_cost(plan)

            if not plan.steps:
                sm.fail("planner returned empty plan")
                result.status = "failed"
                result.error = "Planner returned empty plan"
                return self._finalize(result, sm)

            # 2. 执行循环
            sm.transition_to(AgentState.EXECUTING, reason="plan ready",
                             metadata={"total_steps": plan.total_steps})

            step_index = 0
            while step_index < len(plan.steps):
                # 检查取消
                if self._is_cancelled():
                    sm.cancel(reason="external cancellation")
                    result.status = "cancelled"
                    return self._finalize(result, sm)

                # 检查预算
                budget_status = self._check_budget(step_index)
                if budget_status != "ok":
                    if budget_status == "max_steps":
                        sm.fail("max_steps exceeded", reason="budget_exceeded")
                    elif budget_status == "max_time":
                        sm.fail("max_time exceeded", reason="timeout")
                    elif budget_status == "max_cost":
                        sm.fail("max_cost exceeded", reason="budget_exceeded")
                    result.status = budget_status
                    result.error = f"Budget exceeded: {budget_status}"
                    return self._finalize(result, sm)

                # 检查熔断
                if self._consecutive_failures >= self.config.circuit_breaker_threshold:
                    sm.fail("circuit breaker opened", reason="too many consecutive failures")
                    result.status = "failed"
                    result.error = f"Circuit breaker: {self._consecutive_failures} consecutive failures"
                    return self._finalize(result, sm)

                step = plan.steps[step_index]
                step.status = "running"

                # 3. 安全检查（每步）
                security = self._check_security(step, context)
                if not security["allowed"]:
                    step.status = "failed"
                    step.error = security["reason"]
                    self._consecutive_failures += 1

                    # 检查是否需要重规划
                    obs = self._observation_layer.observe(
                        step=step_index,
                        previous_error=step.error,
                    )
                    decision = self._replanner.should_replan(
                        observation=obs,
                        failed_step=step,
                        retry_count=self._consecutive_failures,
                        max_retries=self.config.max_retries,
                    )
                    if decision:
                        plan = self._do_replan(sm, goal, plan, decision, obs, context)
                        step_index = 0
                        continue
                    else:
                        step_index += 1
                        continue

                # 4. EXECUTE
                self._safe_transition(sm, AgentState.EXECUTING,
                                      reason=f"executing step {step_index}",
                                      metadata={"step": step_index})
                exec_result = self._execute_step(
                    step, context, task_id, step_index, security=security)

                # 5. OBSERVE
                sm.transition_to(AgentState.OBSERVING, reason=f"step {step_index} done")
                obs = self._observation_layer.observe(
                    step=step_index,
                    previous_result=exec_result,
                    previous_error=exec_result.get("error"),
                    previous_duration_ms=exec_result.get("duration_ms", 0),
                )

                if exec_result.get("success"):
                    step.status = "completed"
                    step.result = exec_result
                    step.duration_ms = exec_result.get("duration_ms", 0)
                    self._consecutive_failures = 0
                    self._current_cost += exec_result.get("estimated_cost", 0.0)
                    step_index += 1
                else:
                    step.status = "failed"
                    step.error = exec_result.get("error", "unknown error")
                    self._consecutive_failures += 1

                    # 6. REPLAN 检查
                    decision = self._replanner.should_replan(
                        observation=obs,
                        failed_step=step,
                        retry_count=self._consecutive_failures,
                        max_retries=self.config.max_retries,
                        budget_exceeded=self._check_budget(step_index) != "ok",
                    )
                    if decision:
                        plan = self._do_replan(sm, goal, plan, decision, obs, context)
                        step_index = 0
                        continue
                    else:
                        step_index += 1

            # 循环结束 → 完成
            sm.complete(reason="all steps executed")
            result.status = "completed"
            result.result = {
                "completed_steps": sum(1 for s in plan.steps if s.status == "completed"),
                "total_steps": len(plan.steps),
                "final_step_results": [
                    {"index": s.index, "action": s.action, "status": s.status}
                    for s in plan.steps
                ],
            }

        except StateTransitionError as e:
            sm.fail(str(e), reason="state_machine_error")
            result.status = "failed"
            result.error = f"State machine error: {e}"
        except Exception as e:
            sm.fail(str(e), reason="unexpected_error")
            result.status = "failed"
            result.error = f"Unexpected error: {str(e)[:500]}"

        return self._finalize(result, sm)

    def cancel(self) -> None:
        """外部取消 Agent 执行。"""
        with self._cancel_lock:
            self._cancelled = True

    # ──────────────────────────────────────────────────────────
    # 内部方法
    # ──────────────────────────────────────────────────────────

    def _safe_transition(
        self,
        sm: AgentStateMachine,
        target: AgentState,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """安全转换：仅当当前状态与目标不同时才转换，避免 same-state 非法转换。"""
        if sm.state != target:
            sm.transition_to(target, reason=reason, metadata=metadata)

    def _is_cancelled(self) -> bool:
        with self._cancel_lock:
            return self._cancelled

    def _check_budget(self, current_step: int) -> str:
        """检查预算，返回 'ok' 或超限类型。"""
        if current_step >= self.config.max_steps:
            return "max_steps"
        elapsed = time.time() - self._start_time
        if elapsed >= self.config.max_time_seconds:
            return "max_time"
        if self._current_cost >= self.config.max_cost:
            return "max_cost"
        return "ok"

    def _checkpoint_metadata(
        self,
        steps_started: Optional[int] = None,
        estimated_cost: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Capture cumulative run usage and its limits without resetting budget."""
        elapsed = max(0.0, time.time() - self._start_time) if self._start_time else 0.0
        limits = ("max_steps", "max_time_seconds", "max_cost", "max_retries",
                  "max_replans", "step_timeout_seconds")
        return {
            "elapsed_seconds": round(elapsed, 3),
            "estimated_cost": round(self._current_cost if estimated_cost is None
                                     else estimated_cost, 6),
            "steps_started": self._steps_started if steps_started is None else steps_started,
            "replans": self._replanner.replan_count,
            "limits": {name: getattr(self.config, name) for name in limits},
        }

    def _checkpoint_plan_snapshot(
        self,
        step_index: Optional[int] = None,
        status: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Copy the current plan and overlay the just-finished step before run() mutates it."""
        if self._current_plan is None:
            return {}
        snapshot = self._current_plan.to_dict()
        if step_index is not None and isinstance(snapshot.get("steps"), list):
            item = next((item for item in snapshot["steps"]
                         if isinstance(item, dict) and item.get("index") == step_index), None)
            if item is not None:
                item.update(status=status or item.get("status"), result=result, error=error)
                if isinstance(result, dict) and isinstance(result.get("duration_ms"), (int, float)):
                    item["duration_ms"] = result["duration_ms"]
        return snapshot

    @staticmethod
    def _security_action(step: PlanStep):
        """Derive a deterministic SYSTEM action classification for one Agent step."""
        from lumenis.system.security import AgentAction

        explicit = str((step.params or {}).get("action_type") or "").strip().upper()
        if explicit in AgentAction.__members__:
            return AgentAction[explicit]

        text = f"{step.tool} {step.action}".lower()
        if "deploy" in text:
            return AgentAction.DEPLOY
        if "push" in text or "publish" in text:
            return AgentAction.PUSH
        if "commit" in text:
            return AgentAction.COMMIT
        if "export" in text:
            return AgentAction.EXPORT
        if str(step.risk_level).lower() in {"high", "critical"}:
            return AgentAction.WRITE
        return AgentAction.ANALYZE

    @staticmethod
    def _security_operation(action):
        from lumenis.system.security import AgentAction, OperationType

        return {
            AgentAction.READ: OperationType.SKILL_EXECUTE,
            AgentAction.ANALYZE: OperationType.SKILL_EXECUTE,
            AgentAction.SUGGEST: OperationType.SKILL_EXECUTE,
            AgentAction.EXPORT: OperationType.DATA_EXPORT,
            AgentAction.WRITE: OperationType.DB_WRITE,
            AgentAction.COMMIT: OperationType.CONFIG_MODIFY,
            AgentAction.PUSH: OperationType.RUNTIME_OPERATION,
            AgentAction.DEPLOY: OperationType.RUNTIME_OPERATION,
        }[action]

    def _check_security(self, step: PlanStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """SYSTEM Permission → Action Firewall → Effect Fence; every error fails closed."""
        from lumenis.system.security import (
            ActionRequest,
            RiskLevel,
            get_effect_fence,
            is_testing_bypass_enabled,
            validate_action,
        )

        action = self._security_action(step)
        operation = self._security_operation(action)
        risk_name = str(step.risk_level or "low").upper()
        risk = RiskLevel[risk_name] if risk_name in RiskLevel.__members__ else RiskLevel.LOW
        target = str((step.params or {}).get("target") or f"skill:{step.tool or 'agent_step'}")
        scope = str(
            context.get("domain")
            or context.get("product")
            or "system"
        ).strip().lower()
        operation_id = str(step.step_id)

        # 1. Canonical Permission. A missing/broken permission owner is never auto-allowed.
        try:
            gate = self._get_permission_gate()
            if gate is None:
                raise RuntimeError("canonical SYSTEM Permission unavailable")
            perm_result = gate.check(
                operation,
                resource=target,
                risk_level=risk,
                caller=f"agent_runtime:{self._observation_layer.agent_id}",
                operation_id=operation_id,
                domain_id=str(context.get("domain_id") or "") or None,
                role=str(context.get("role") or "") or None,
            )
            if not perm_result.allowed:
                return {
                    "allowed": False,
                    "reason": f"permission denied: {perm_result.reason}",
                    "layer": "permission",
                    "permission": perm_result.to_dict(),
                }
        except Exception as exc:
            if is_testing_bypass_enabled():
                return {
                    "allowed": True,
                    "reason": f"explicit testing bypass: {exc}",
                    "layer": "testing_bypass",
                    "fence_idempotency_key": None,
                }
            return {
                "allowed": False,
                "reason": f"permission error: {exc}",
                "layer": "permission",
            }

        # 2. Canonical Action Firewall. Permission is an input, never re-invented here.
        try:
            fw_result = validate_action(
                ActionRequest(
                    identity=f"agent_runtime:{self._observation_layer.agent_id}",
                    intent=step.action or "execute planned step",
                    tool=step.tool or "agent_step",
                    parameters=dict(step.params or {}),
                    target=target,
                    scope=scope,
                    action=action,
                ),
                permission_result=perm_result,
            )
        except Exception as exc:
            return {
                "allowed": False,
                "reason": f"action firewall error: {exc}",
                "layer": "action_firewall",
            }

        if not fw_result.allowed:
            return {
                "allowed": False,
                "reason": fw_result.reason,
                "layer": "action_firewall",
                "permission": perm_result.to_dict(),
                "firewall": fw_result.to_dict(),
            }

        # 3. Canonical Effect Fence / side-effect idempotency.
        try:
            fence_result = get_effect_fence().check(
                action=action,
                target=target,
                payload=dict(step.params or {}),
                operation_id=operation_id,
            )
        except Exception as exc:
            return {
                "allowed": False,
                "reason": f"effect fence error: {exc}",
                "layer": "effect_fence",
                "permission": perm_result.to_dict(),
                "firewall": fw_result.to_dict(),
            }

        if not fence_result.allowed:
            return {
                "allowed": False,
                "reason": fence_result.reason,
                "layer": "effect_fence",
                "permission": perm_result.to_dict(),
                "firewall": fw_result.to_dict(),
                "effect_fence": fence_result.to_dict(),
            }

        return {
            "allowed": True,
            "reason": "SYSTEM security chain passed",
            "layer": "effect_fence",
            "permission": perm_result.to_dict(),
            "firewall": fw_result.to_dict(),
            "effect_fence": fence_result.to_dict(),
            "fence_idempotency_key": fence_result.idempotency_key,
        }

    def _get_permission_gate(self) -> Optional[Any]:
        """延迟获取唯一 SYSTEM Permission owner。"""
        if self._permission_gate is None:
            try:
                from lumenis.system.security import get_permission_gate
                self._permission_gate = get_permission_gate()
            except Exception:
                self._permission_gate = None
        return self._permission_gate

    def _execute_step(
        self,
        step: PlanStep,
        context: Dict[str, Any],
        task_id: str,
        step_index: int,
        security: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行单个步骤。"""
        start = time.time()
        try:
            # Checkpoint
            self._durable.checkpoint(
                task_id=task_id,
                step_index=step_index,
                state="executing",
                plan_snapshot=self._checkpoint_plan_snapshot(),
                context=self._active_context,
                step_detail=step.action,
                step_status="running",
                agent_id=self._observation_layer.agent_id,
                metadata=self._checkpoint_metadata(self._steps_started + 1),
            )
            self._steps_started += 1

            # 执行工具
            result = self._tool_executor(step, context)

            # Close the Effect Fence reservation with the real execution outcome.
            fence_key = (security or {}).get("fence_idempotency_key")
            if fence_key:
                from lumenis.system.security import get_effect_fence
                get_effect_fence().complete(
                    fence_key, success=bool(result.get("success")))

            duration_ms = round((time.time() - start) * 1000, 2)
            result["duration_ms"] = duration_ms
            step_success = bool(result.get("success"))
            step_error = result.get("error")
            if not step_success and not step_error:
                step_error = "step execution failed"
            next_cost = self._current_cost
            if step_success:
                next_cost += result.get("estimated_cost", 0.0)

            # 完成 Checkpoint
            self._durable.complete_step(
                task_id=task_id,
                step_index=step_index,
                result=result,
                error=step_error,
                plan_snapshot=self._checkpoint_plan_snapshot(
                    step_index=step_index,
                    status="completed" if step_success else "failed",
                    result=result,
                    error=step_error,
                ),
                context=self._active_context,
                agent_id=self._observation_layer.agent_id,
                metadata=self._checkpoint_metadata(estimated_cost=next_cost),
            )

            return result

        except Exception as e:
            fence_key = (security or {}).get("fence_idempotency_key")
            if fence_key:
                try:
                    from lumenis.system.security import get_effect_fence
                    get_effect_fence().complete(fence_key, success=False)
                except Exception:
                    pass
            duration_ms = round((time.time() - start) * 1000, 2)
            return {
                "success": False,
                "error": str(e)[:500],
                "duration_ms": duration_ms,
            }

    def _do_replan(
        self,
        sm: AgentStateMachine,
        goal: str,
        current_plan: Plan,
        decision: ReplanDecision,
        observation: Observation,
        context: Dict[str, Any],
    ) -> Plan:
        """执行重规划。"""
        sm.transition_to(AgentState.REPLANNING, reason=decision.reason,
                         metadata={"replan_count": self._replanner.replan_count + 1})
        new_plan = self._replanner.replan(goal, current_plan, decision, observation, context)
        self._current_plan = new_plan
        sm.transition_to(AgentState.EXECUTING, reason="replanned, resuming execution")
        return new_plan

    def _estimate_plan_cost(self, plan: Plan) -> float:
        """估算规划成本（token → 美元）。"""
        tokens = plan.token_usage.get("total_tokens", 0)
        # 粗略估算：glm-4.5-air 约 $0.001/1K tokens，glm-5.3 约 $0.01/1K tokens
        rate = 0.01 if plan.model == "glm-5.3" else 0.001
        return round(tokens / 1000 * rate, 6)

    def _finalize(self, result: AgentResult, sm: AgentStateMachine) -> AgentResult:
        """收尾：评估、指标、持久化。"""
        result.finished_at = datetime.now(timezone.utc).isoformat()
        result.duration_ms = round((time.time() - self._start_time) * 1000, 2)
        result.transitions = sm.transition_history()

        # 刷新 plan 快照（反映步骤执行状态）
        if self._current_plan is not None:
            result.plan = self._current_plan.to_dict()

        # 计算指标
        plan_data = result.plan or {}
        steps = plan_data.get("steps", [])
        completed = sum(1 for s in steps if s.get("status") == "completed")
        failed = sum(1 for s in steps if s.get("status") == "failed")

        result.metrics = {
            "steps": len(steps),
            "completed_steps": completed,
            "failed_steps": failed,
            "duration_ms": result.duration_ms,
            "cost": round(self._current_cost, 6),
            "replans": self._replanner.replan_count,
            "retries": self._consecutive_failures,
            "final_state": sm.state.value,
        }

        # 轨迹评估
        if self.config.enable_evaluation:
            try:
                metrics = TrajectoryMetrics(
                    total_steps=len(steps),
                    completed_steps=completed,
                    failed_steps=failed,
                    replan_count=self._replanner.replan_count,
                    retry_count=self._consecutive_failures,
                    total_duration_ms=result.duration_ms,
                    estimated_cost=self._current_cost,
                    budget_cost=self.config.max_cost,
                    expected_steps=len(steps),
                    goal_achieved=result.status == "completed",
                    final_error=result.error,
                )
                eval_result = self._evaluator.evaluate(
                    metrics, agent_id=result.agent_id, task_id=result.task_id)
                result.evaluation = eval_result.to_dict()

                # 保存评估证据
                self._durable.save_evidence(
                    task_id=result.task_id,
                    evidence_type="trajectory_evaluation",
                    content=json.dumps(result.evaluation, ensure_ascii=False, default=str)[:2000],
                    authenticity_score=eval_result.overall_score,
                )
            except Exception:
                pass

        # Durable 完成
        if result.status in ("completed", "failed", "cancelled"):
            self._durable.checkpoint(
                task_id=result.task_id,
                step_index=len(steps),
                state=result.status,
                plan_snapshot=self._checkpoint_plan_snapshot(),
                context=self._active_context,
                step_detail=f"agent {result.status}",
                step_status=result.status,
                agent_id=result.agent_id,
                metadata=self._checkpoint_metadata(),
            )

        return result

    @staticmethod
    def _default_tool_executor(step: PlanStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """默认工具执行器（仅记录，不真实执行）。

        生产环境应注入经过 SYSTEM 权限校验的 tool_executor；默认执行器只记录任务，不调用工具。
        """
        return {
            "success": True,
            "output": f"[default_executor] executed: {step.action}",
            "tool": step.tool,
            "params": step.params,
            "estimated_cost": 0.0,
        }
