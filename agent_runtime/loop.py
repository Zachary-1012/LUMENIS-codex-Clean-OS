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
  - timeout      : 单步超时配置；当前同步执行器不提供硬中断
  - cancellation : 支持外部取消

每步检查：
  - SYSTEM Permission Gate（fail-closed）
  - SYSTEM Action Firewall
  - SYSTEM Effect Fence / Idempotency

COMMIT/PUSH/Production Write 默认 DENY；所有副作用必须走唯一 SYSTEM 安全链。
Circuit breaker：复用 runtime_guardian / ai_channel 的熔断器。

设计原则：
  - 状态机驱动，每步转换可审计
  - 每步前检查累计预算，超限不开始下一步（fail-closed）
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
import math
import threading
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .state_machine import AgentState, AgentStateMachine, StateTransitionError
from .observation import ObservationLayer, Observation
from .planner import Plan, PlanStep, Planner, PlanMode
from .replanner import Replanner, ReplanDecision
from lumenis.shared.evaluation import trajectory as _trajectory
from .durable_adapter import DurableExecutionAdapter, _sanitize_checkpoint_value
from agent_capability.formation import FormationError

# Retain the existing public class bindings without restricting star imports.
TrajectoryEvaluation = _trajectory.TrajectoryEvaluation
TrajectoryEvaluator = _trajectory.TrajectoryEvaluator
TrajectoryMetrics = _trajectory.TrajectoryMetrics


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
        tool_binding: Optional[Any] = None,
        *,
        owned_request_factory: Callable | None = None,
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
                           未绑定则返回真实 unavailable，不执行或模拟成功
            ai_chat_func: AI 调用函数（用于 planner）
            permission_gate: 权限门实例（None 则延迟获取）
            owned_request_factory: Server-owned typed Gateway request assembly.
                                   Never supplied by task context or model output.
        """
        self.config = config or AgentConfig()
        if owned_request_factory is not None and (planner is not None or ai_chat_func is not None):
            raise ValueError("owned_request_factory requires the default owned planner")
        self._ai_chat_func = ai_chat_func
        self._planner = planner or Planner(
            ai_chat_func=ai_chat_func, owned_request_factory=owned_request_factory,
            is_cancelled=self._is_cancelled,
        )
        self._replanner = replanner or Replanner(
            planner=self._planner, max_replans=self.config.max_replans)
        self._observation_layer = observation_layer or ObservationLayer(
            auto_register_default=False)
        self._evaluator = evaluator or TrajectoryEvaluator()
        self._durable = durable_adapter or DurableExecutionAdapter(
            enabled=self.config.enable_durable_execution)
        self._tool_executor = tool_executor or self._default_tool_executor
        self._tool_executor_bound = (
            tool_executor is not None and tool_executor is not self._default_tool_executor
            and self._tool_executor is tool_executor
        )
        self._permission_gate = permission_gate
        # Server-owned resolver/direct binding, not a model-supplied callback.
        self._tool_binding = tool_binding
        if tool_binding is not None:
            self._tool_executor_bound = True

        # 运行时状态
        self._cancelled = False
        self._cancel_lock = threading.Lock()
        self._start_time: float = 0.0
        self._current_cost: float = 0.0
        self._steps_started: int = 0
        self._active_context: Dict[str, Any] = {}
        self._active_limits: Dict[str, Any] = {}
        self._resuming = False
        self._consecutive_failures: int = 0
        self._current_plan: Optional[Plan] = None

    # ──────────────────────────────────────────────────────────
    # 公共 API
    # ──────────────────────────────────────────────────────────

    def resume(self, task_id: str, *, context: Dict[str, Any]) -> AgentResult:
        """Resume a durable plan after fresh authorization.

        Cumulative elapsed, cost, step, and replan budgets are restored. The
        current synchronous tool executor has no hard per-step cancellation;
        its saved timeout remains policy metadata and is not enforced here.
        """
        if not isinstance(task_id, str) or not task_id.strip():
            raise RuntimeError("A persisted TaskEngine task ID is required")
        recovered = self._durable.recover(task_id)
        if not isinstance(recovered, dict) or recovered.get("source") != "db":
            raise RuntimeError("TaskEngine-backed checkpoint is unavailable")
        task, checkpoint = recovered.get("task"), recovered.get("last_checkpoint")
        if not isinstance(task, dict) or not isinstance(checkpoint, dict):
            raise RuntimeError("Persisted agent checkpoint is missing")
        if task.get("status") == "cancelled" or checkpoint.get("state") == "cancelled":
            raise RuntimeError("Cancelled agent tasks cannot be resumed")
        if task.get("status") not in {"pending", "ready", "running", "failed", "succeeded", "completed"}:
            raise RuntimeError("Persisted TaskEngine task state is not resumable")
        if (task.get("created_by") != "agent_runtime" or task.get("agent_id") != checkpoint.get("agent_id")
                or checkpoint.get("task_id") != task_id or task.get("task_id") != task_id):
            raise RuntimeError("Persisted agent task identity does not match its checkpoint")
        metadata = checkpoint.get("metadata")
        if not isinstance(metadata, dict) or metadata.get("resumable") is not True:
            raise RuntimeError("Persisted agent checkpoint is not resumable")
        plan = self._restore_checkpoint_plan(checkpoint.get("plan_snapshot"))
        if plan.goal != task.get("goal"):
            raise RuntimeError("Persisted plan goal does not match its TaskEngine task")
        checkpoint_state = checkpoint.get("state")
        checkpoint_index = checkpoint.get("step_index")
        if (checkpoint_state not in {"executing", "completed", "failed"}
                or type(checkpoint_index) is not int or checkpoint_index < 0
                or checkpoint_index > len(plan.steps)):
            raise RuntimeError("Persisted agent checkpoint state or index is malformed")
        saved_context = checkpoint.get("context")
        if not isinstance(saved_context, dict) or saved_context != task.get("context"):
            raise RuntimeError("Persisted agent context binding is malformed")
        metrics = self._restore_checkpoint_metrics(metadata)

        actor = context.get("actor") if isinstance(context, dict) else None
        actor_id = context.get("actor_id") if isinstance(context, dict) else None
        domain_id = context.get("domain_id") if isinstance(context, dict) else None
        scope = context.get("scope") if isinstance(context, dict) else None
        if (type(actor_id) is not int or actor_id < 1 or not isinstance(actor, dict)
                or type(actor.get("id")) is not int or actor.get("id") != actor_id
                or actor_id != saved_context.get("actor_id")
                or domain_id != saved_context.get("domain_id")
                or not self._valid_typed_scope(domain_id, scope)
                or scope != saved_context.get("scope")):
            return self._resume_result(task, plan, "blocked", "Fresh actor, domain, and scope do not match the persisted binding")
        fresh_context, sensitive = _sanitize_checkpoint_value(context)
        if sensitive or not isinstance(fresh_context, dict):
            return self._resume_result(task, plan, "blocked", "Fresh resume context contains credential or approval material")
        module = fresh_context.get("module")
        if not isinstance(module, str) or not module.strip():
            return self._resume_result(task, plan, "blocked", "Fresh resume context must identify the authorized module")
        fresh_context.setdefault("domain", domain_id)
        self._observation_layer.agent_id = task["agent_id"]

        if self._task_is_completed(task, checkpoint, plan):
            security = self._check_security(
                PlanStep(index=0, action="read completed agent result", tool="agent_runtime.resume"),
                fresh_context, fresh_authorization=True,
            )
            if not security.get("allowed"):
                return self._resume_result(task, plan, "blocked", security.get("reason", "Fresh read permission denied"))
            return self._read_completed_result(task, plan)

        next_index = next((i for i, step in enumerate(plan.steps)
                           if step.status not in {"completed", "skipped"}), len(plan.steps))
        if next_index == len(plan.steps):
            security = self._check_security(
                PlanStep(index=0, action="read completed agent result", tool="agent_runtime.resume"),
                fresh_context, fresh_authorization=True,
            )
            if not security.get("allowed"):
                return self._resume_result(task, plan, "blocked", security.get("reason", "Fresh read permission denied"))
            return self._read_completed_result(task, plan)
        if checkpoint_state == "executing":
            if (checkpoint_index == len(plan.steps)
                    or plan.steps[checkpoint_index].status != "running"):
                raise RuntimeError("Persisted executing checkpoint does not match its plan step")
            next_index = checkpoint_index
        if checkpoint_state == "completed":
            if checkpoint_index == len(plan.steps):
                if any(step.status not in {"completed", "skipped"} for step in plan.steps):
                    raise RuntimeError("Completed agent checkpoint has incomplete plan steps")
            elif plan.steps[checkpoint_index].status != "completed":
                raise RuntimeError("Completed checkpoint does not match its plan step")
        if checkpoint_state == "failed":
            if checkpoint_index == len(plan.steps):
                if not any(step.status == "failed" for step in plan.steps):
                    raise RuntimeError("Failed agent checkpoint has no failed plan step")
            elif plan.steps[checkpoint_index].status != "failed":
                raise RuntimeError("Failed checkpoint does not match its plan step")
        step = plan.steps[next_index]
        try:
            pending_action = self._security_action(step)
        except FormationError as exc:
            return self._resume_result(task, plan, "reconciliation_required", str(exc))
        if (step.status in {"running", "failed"}
                and pending_action.value in {"WRITE", "EXPORT", "COMMIT", "PUSH", "DEPLOY"}):
            return self._resume_result(
                task, plan, "reconciliation_required",
                f"Step {step.step_id} may have produced a consequential effect; reconcile it before resuming",
            )
        if not self._tool_executor_bound:
            if self._tool_binding is not None:
                self._tool_executor_bound = True
        if not self._tool_executor_bound:
            return self._resume_result(
                task, plan, "blocked", "TOOL_EXECUTOR_NOT_BOUND: resume requires an injected tool executor",
            )
        # Saved pending calls must retain their original trusted formation.
        # A current registry certificate or approval cannot manufacture it.
        try:
            if self._tool_binding is None:
                raise FormationError("TOOL_FORMATION_NOT_BOUND")
            for pending in plan.steps[next_index:]:
                if pending.status not in {"completed", "skipped"}:
                    if not isinstance(pending.formation, dict):
                        raise FormationError("TOOL_FORMATION_MISSING")
                    self._tool_binding.form_step(pending, fresh_context, expected=pending.formation)
        except FormationError as exc:
            return self._resume_result(task, plan, "reconciliation_required", str(exc))

        current_limits = self._current_budget_limits()
        saved_limits = metrics["limits"]
        effective_limits = {key: min(current_limits[key], saved_limits[key]) for key in current_limits}
        return self.run(
            task.get("goal", ""), context=fresh_context, agent_id=task["agent_id"],
            _resume_state={
                "task_id": task_id, "plan": plan, "next_index": next_index,
                "elapsed_seconds": metrics["elapsed_seconds"],
                "estimated_cost": metrics["estimated_cost"],
                "steps_started": metrics["steps_started"], "replans": metrics["replans"],
                "limits": effective_limits,
            },
        )

    @staticmethod
    def _valid_typed_scope(domain_id: Any, scope: Any) -> bool:
        if (not isinstance(domain_id, str) or not isinstance(scope, dict)
                or set(scope) != {"global_scope", "subject_id", "brand_focus_id"}
                or type(scope.get("global_scope")) is not bool):
            return False
        subject, brand = scope.get("subject_id"), scope.get("brand_focus_id")
        if scope["global_scope"]:
            return subject is None and brand is None
        domain = domain_id.strip().lower()
        if domain == "cth":
            return isinstance(subject, str) and bool(subject.strip()) and brand is None
        if domain in {"bmp", "zbmp"}:
            return subject is None and isinstance(brand, str) and bool(brand.strip())
        return False

    def _read_completed_result(self, task, plan):
        # Called only after the existing fresh read authorization. Reopen and
        # verify through the Artifact/Evidence owner; never repeat the effect.
        outcome = self._evaluator.verify_outcome(
            task["task_id"], plan.outcome_contract_sha256,
            expected_output_receipts=plan.outcome_receipt_bindings,
            require_bound_receipts=True,
        )
        if self._evaluator.has_outcome_contract and outcome["state"] != "VERIFIED":
            result = self._resume_result(task, plan, "blocked", outcome["reason"])
        else:
            result = self._resume_result(task, plan, "already_completed", "Task is already completed", include_result=True)
        result.evaluation = {"outcome_verification": outcome}
        return result

    @staticmethod
    def _restore_checkpoint_plan(snapshot: Any) -> Plan:
        if not isinstance(snapshot, dict) or not snapshot.get("plan_id") or not isinstance(snapshot.get("steps"), list):
            raise RuntimeError("Persisted agent plan snapshot is malformed")
        try:
            fields = set(Plan.__dataclass_fields__)
            if set(snapshot) - fields:
                raise ValueError("unknown plan fields")
            data = {key: value for key, value in snapshot.items() if key != "steps"}
            data["steps"] = []
            for index, item in enumerate(snapshot["steps"]):
                if (not isinstance(item, dict) or set(item) - set(PlanStep.__dataclass_fields__)
                        or not item.get("step_id") or type(item.get("index")) is not int
                        or item["index"] != index
                        or item.get("status") not in {"pending", "running", "completed", "failed", "skipped"}):
                    raise ValueError("invalid plan step identity or state")
                data["steps"].append(PlanStep(**item))
            if (not isinstance(data.get("goal"), str) or not isinstance(data.get("plan_id"), str)
                    or not data["plan_id"] or not data["steps"]
                    or len({step.step_id for step in data["steps"]}) != len(data["steps"])
                    or any(not isinstance(step.step_id, str) or not step.step_id.strip()
                           or not isinstance(step.action, str) or not isinstance(step.tool, str)
                           or not isinstance(step.params, dict)
                           for step in data["steps"])):
                raise ValueError("empty plan or duplicate step identity")
            usage = data.get("token_usage", {})
            if (not isinstance(usage, dict) or any(
                    type(value) not in (int, float) or not math.isfinite(value) or value < 0
                    for value in usage.values())):
                raise ValueError("invalid plan token metrics")
            return Plan(**data)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Persisted agent plan snapshot is malformed") from exc

    @staticmethod
    def _restore_checkpoint_metrics(metadata: Dict[str, Any]) -> Dict[str, Any]:
        limits = metadata.get("limits")
        values = ("max_steps", "max_time_seconds", "max_cost", "max_retries",
                  "max_replans", "step_timeout_seconds")
        numeric = ("elapsed_seconds", "estimated_cost")
        if (not isinstance(limits, dict) or any(key not in limits for key in values)
                or any(type(metadata.get(key)) not in (int, float) or not math.isfinite(metadata[key])
                       or metadata[key] < 0 for key in numeric)
                or any(type(metadata.get(key)) is not int or metadata[key] < 0 for key in ("steps_started", "replans"))):
            raise RuntimeError("Persisted agent budget checkpoint is malformed")
        if any(type(limits[key]) not in (int, float) or not math.isfinite(limits[key])
               or limits[key] < 0 for key in values):
            raise RuntimeError("Persisted agent budget limits are malformed")
        return {key: metadata[key] for key in numeric + ("steps_started", "replans")} | {
            "limits": {key: limits[key] for key in values}
        }

    def _task_is_completed(self, task: Dict[str, Any], checkpoint: Dict[str, Any], plan: Plan) -> bool:
        completed = ((checkpoint.get("state") == "completed"
                      and checkpoint.get("step_index") == len(plan.steps))
                     or task.get("status") in {"succeeded", "completed"})
        if completed and any(step.status not in {"completed", "skipped"} for step in plan.steps):
            raise RuntimeError("Completed agent task has incomplete plan steps")
        return completed

    def _resume_result(
        self, task: Dict[str, Any], plan: Plan, status: str, error: str,
        include_result: bool = False,
    ) -> AgentResult:
        result = AgentResult(
            agent_id=task.get("agent_id", ""), task_id=task.get("task_id", ""),
            status=status, goal=task.get("goal", "") if include_result else "",
            error=None if include_result else error,
            plan=plan.to_dict() if include_result else None,
            started_at=datetime.now(timezone.utc).isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
        if include_result:
            result.result = self._completed_result(plan)
        return result

    @staticmethod
    def _completed_result(plan: Plan) -> Dict[str, Any]:
        """Return executed tool results, including results reopened from a checkpoint."""
        return {
            "completed_steps": sum(step.status == "completed" for step in plan.steps),
            "total_steps": len(plan.steps),
            "final_step_results": [
                {"index": step.index, "step_id": step.step_id, "action": step.action,
                 "tool": step.tool, "status": step.status, "result": step.result}
                for step in plan.steps
            ],
        }

    def run(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        _resume_state: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """执行 Agent Loop。

        Args:
            goal: 自然语言目标
            context: 附加上下文
            agent_id: Agent ID（None 则自动生成）

        Returns:
            AgentResult 执行结果
        """
        resuming = _resume_state is not None
        agent_id = agent_id or f"agent_{uuid.uuid4().hex[:12]}"
        context = context or {}

        # 初始化
        self._cancelled = False
        self._resuming = resuming
        self._active_limits = (_resume_state["limits"] if resuming else self._current_budget_limits())
        self._start_time = (time.time() - _resume_state["elapsed_seconds"]
                            if resuming else time.time())
        self._current_cost = _resume_state["estimated_cost"] if resuming else 0.0
        self._steps_started = _resume_state["steps_started"] if resuming else 0
        self._active_context = context
        self._consecutive_failures = 0
        self._replanner.reset()
        self._replanner._max_replans = self._active_limits["max_replans"]
        if resuming:
            self._replanner._replan_count = _resume_state["replans"]

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
        task_id = (_resume_state["task_id"] if resuming
                   else self._durable.create_task(goal, agent_id=agent_id, context=context))
        result.task_id = task_id

        try:
            sm.transition_to(AgentState.PLANNING, reason="resume checkpoint" if resuming else "start planning")
            plan = (_resume_state["plan"] if resuming else self._planner.plan(
                goal, mode=PlanMode(self.config.plan_mode), context=context,
            ))
            result.plan = plan.to_dict()
            self._current_plan = plan
            if self._is_cancelled():
                sm.cancel(reason="cancelled during planning")
                result.status = "cancelled"
                return self._finalize(result, sm)
            if not resuming:
                self._current_cost += self._estimate_plan_cost(plan)
                plan.outcome_contract_sha256 = self._evaluator.form_outcome_contract(task_id)
                if self._tool_binding is not None:
                    for pending in plan.steps:
                        if pending.status not in {"completed", "skipped"}:
                            # Planning output can select a candidate but cannot
                            # mint or carry forward its own authorization.
                            pending.formation = None
                            pending.formation = self._tool_binding.form_step(pending, context).binding
                elif self._tool_executor_bound:
                    result.status = "blocked"
                    result.error = "TOOL_FORMATION_NOT_BOUND"
                    sm.fail(result.error)
                    return self._finalize(result, sm)

            if not plan.steps:
                sm.fail("planner returned empty plan")
                result.status = "failed"
                result.error = "Planner returned empty plan"
                return self._finalize(result, sm)

            # 2. 执行循环
            sm.transition_to(AgentState.EXECUTING, reason="plan ready",
                             metadata={"total_steps": plan.total_steps})

            step_index = _resume_state["next_index"] if resuming else 0
            while step_index < len(plan.steps):
                if plan.steps[step_index].status in {"completed", "skipped"}:
                    step_index += 1
                    continue
                # 检查取消
                if self._is_cancelled():
                    sm.cancel(reason="external cancellation")
                    result.status = "cancelled"
                    return self._finalize(result, sm)

                # 检查预算
                budget_status = self._check_budget(self._steps_started)
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
                try:
                    security, exec_result = self._admit_and_execute_step(
                        step, context, task_id, step_index, fresh_authorization=resuming)
                except FormationError as exc:
                    result.status = "reconciliation_required"
                    result.error = str(exc)
                    result.metrics["formation_changed_fields"] = list(exc.changed_fields)
                    sm.fail(result.error)
                    return self._finalize(result, sm)
                if not security["allowed"]:
                    step.status = "failed"
                    step.error = security["reason"]
                    self._consecutive_failures += 1
                    if resuming:
                        sm.fail(step.error, reason="fresh_authorization_denied")
                        result.status = "blocked"
                        result.error = step.error
                        return self._finalize(result, sm)

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
                if exec_result.get("reconciliation_required"):
                    result.status = "reconciliation_required"
                    result.error = exec_result.get("error")
                    sm.fail(result.error)
                    return self._finalize(result, sm)
                if self._is_cancelled() or exec_result.get("cancelled"):
                    sm.cancel(reason="cancelled before tool dispatch")
                    result.status = "cancelled"
                    return self._finalize(result, sm)

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
                    if self._security_action(step).value in {"WRITE", "EXPORT", "COMMIT", "PUSH", "DEPLOY"}:
                        result.status = "reconciliation_required"
                        result.error = "Consequential tool outcome requires owner reconciliation before retry"
                        sm.fail(result.error)
                        return self._finalize(result, sm)
                    self._consecutive_failures += 1
                    if resuming:
                        sm.fail(step.error, reason="resumed_step_failed")
                        result.status = "failed"
                        result.error = step.error
                        return self._finalize(result, sm)

                    # 6. REPLAN 检查
                    decision = self._replanner.should_replan(
                        observation=obs,
                        failed_step=step,
                        retry_count=self._consecutive_failures,
                        max_retries=self.config.max_retries,
                        budget_exceeded=self._check_budget(self._steps_started) != "ok",
                    )
                    if decision:
                        plan = self._do_replan(sm, goal, plan, decision, obs, context)
                        step_index = 0
                        continue
                    else:
                        step_index += 1

            if not plan.steps or any(step.status != "completed" for step in plan.steps):
                sm.fail("required agent steps remain incomplete", reason="incomplete_plan")
                result.status = "failed"
                result.error = "Required plan steps did not complete"
            else:
                sm.complete(reason="all steps executed")
                result.status = "completed"
                result.result = self._completed_result(plan)

        except StateTransitionError as e:
            sm.fail(str(e), reason="state_machine_error")
            result.status = "failed"
            result.error = f"State machine error: {e}"
        except FormationError as e:
            sm.fail(str(e))
            result.status = "reconciliation_required"
            result.error = str(e)
            result.metrics["formation_changed_fields"] = list(e.changed_fields)
            return self._finalize(result, sm)
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
        limits = self._active_limits or self._current_budget_limits()
        if current_step >= limits["max_steps"]:
            return "max_steps"
        elapsed = time.time() - self._start_time
        if elapsed >= limits["max_time_seconds"]:
            return "max_time"
        if self._current_cost >= limits["max_cost"]:
            return "max_cost"
        return "ok"

    def _current_budget_limits(self) -> Dict[str, Any]:
        names = ("max_steps", "max_time_seconds", "max_cost", "max_retries",
                 "max_replans", "step_timeout_seconds")
        return {name: getattr(self.config, name) for name in names}

    def _checkpoint_metadata(
        self,
        steps_started: Optional[int] = None,
        estimated_cost: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Capture cumulative run usage and its limits without resetting budget."""
        elapsed = max(0.0, time.time() - self._start_time) if self._start_time else 0.0
        return {
            "elapsed_seconds": round(elapsed, 3),
            "estimated_cost": round(self._current_cost if estimated_cost is None
                                     else estimated_cost, 6),
            "steps_started": self._steps_started if steps_started is None else steps_started,
            "replans": self._replanner.replan_count,
            "limits": dict(self._active_limits or self._current_budget_limits()),
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

        # Effects are distinct canonical obligations, not a numeric privilege
        # ladder. READ/ANALYZE/SUGGEST labels cannot erase the handler's effect.
        formed_effect = (step.formation or {}).get("effect")
        if step.formation is not None and (type(formed_effect) is not str
                                           or formed_effect not in AgentAction.__members__):
            raise FormationError("TOOL_FORMATION_EFFECT_INVALID")
        explicit = str((step.params or {}).get("action_type") or "").strip().upper()
        if explicit in AgentAction.__members__:
            requested = AgentAction[explicit]
        else:
            text = f"{step.tool} {step.action}".lower()
            if "deploy" in text:
                requested = AgentAction.DEPLOY
            elif "push" in text or "publish" in text:
                requested = AgentAction.PUSH
            elif "commit" in text:
                requested = AgentAction.COMMIT
            elif "export" in text:
                requested = AgentAction.EXPORT
            elif formed_effect in AgentAction.__members__:
                requested = AgentAction[formed_effect]
            elif str(step.risk_level).lower() in {"high", "critical"}:
                requested = AgentAction.WRITE
            else:
                requested = AgentAction[formed_effect] if formed_effect in {"READ", "ANALYZE"} else AgentAction.ANALYZE
        if formed_effect in AgentAction.__members__:
            formed = AgentAction[formed_effect]
            if requested != formed and requested.value not in {"READ", "ANALYZE", "SUGGEST"}:
                raise FormationError("TOOL_EFFECT_DECLARATION_CONFLICT")
            return formed
        return requested

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

    def _check_security(
        self, step: PlanStep, context: Dict[str, Any], *, fresh_authorization: bool = False,
    ) -> Dict[str, Any]:
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
            if fresh_authorization:
                from lumenis.system.security import check_actor_scope_permission

                binding = context.get("scope")
                actor_scope = check_actor_scope_permission(
                    context.get("actor"),
                    domain_id=str(context.get("domain_id") or ""),
                    action=("write" if action.value in {"WRITE", "COMMIT", "PUSH", "DEPLOY"}
                            else "read"),
                    module=str(context.get("module") or ""),
                    subject_id=binding.get("subject_id") if isinstance(binding, dict) else None,
                    brand_focus_id=binding.get("brand_focus_id") if isinstance(binding, dict) else None,
                    global_scope=binding.get("global_scope", False) if isinstance(binding, dict) else False,
                    gate=gate,
                )
                if not actor_scope.allowed:
                    return {
                        "allowed": False,
                        "reason": f"actor scope denied: {actor_scope.reason}",
                        "layer": "actor_scope",
                    }
            gate_args = {
                "resource": target,
                "risk_level": risk,
                "caller": f"agent_runtime:{self._observation_layer.agent_id}",
                "domain_id": str(context.get("domain_id") or "") or None,
            }
            if not fresh_authorization:
                gate_args.update(
                    operation_id=operation_id,
                    role=str(context.get("role") or "") or None,
                )
            perm_result = gate.check(operation, **gate_args)
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

    def _admit_and_execute_step(self, step, context, task_id, step_index, *, fresh_authorization=False):
        if self._tool_binding is None:
            if self._tool_executor_bound:
                raise FormationError("TOOL_FORMATION_NOT_BOUND")
            security = (self._check_security(step, context, fresh_authorization=True)
                        if fresh_authorization else self._check_security(step, context))
            return security, (self._execute_step(step, context, task_id, step_index, security=security)
                              if security.get("allowed") else None)
        if not isinstance(step.formation, dict):
            raise FormationError("TOOL_FORMATION_MISSING")
        selected = self._tool_binding.form_step(step, context, expected=step.formation)
        with selected.guard(step, context):
            security = (self._check_security(step, context, fresh_authorization=True)
                        if fresh_authorization else self._check_security(step, context))
            if not security.get("allowed"):
                return security, None
            selected.assert_current(step, context)
            if self._is_cancelled():
                return security, {"success": False, "cancelled": True}
            return security, self._execute_step(step, context, task_id, step_index,
                                                security=security, selected_call=selected)

    def _execute_step(
        self,
        step: PlanStep,
        context: Dict[str, Any],
        task_id: str,
        step_index: int,
        security: Optional[Dict[str, Any]] = None,
        selected_call: Optional[Any] = None,
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
            result = (selected_call.invoke(step, context) if selected_call is not None
                      else self._tool_executor(step, context))
            if not isinstance(result, dict) or type(result.get("success")) is not bool:
                raise RuntimeError("TOOL_RESULT_CONTRACT_INVALID")

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
                "reconciliation_required": isinstance(e, FormationError),
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
        # A proposal cannot mutate the accepted plan before its requirements are checked.
        new_plan = self._replanner.replan(
            goal, deepcopy(current_plan), decision, observation, context)
        self._validate_replan(current_plan, new_plan, decision)
        new_plan.outcome_contract_sha256 = current_plan.outcome_contract_sha256
        new_plan.outcome_receipt_bindings = deepcopy(current_plan.outcome_receipt_bindings)
        self._current_plan = new_plan
        sm.transition_to(AgentState.EXECUTING, reason="replanned, resuming execution")
        return new_plan

    @staticmethod
    def _validate_replan(current_plan: Plan, candidate: Plan, decision: ReplanDecision) -> None:
        """Retain every required outcome and completed result across automatic replans."""
        if not isinstance(candidate, Plan) or not candidate.steps:
            raise ValueError("REPLAN_EMPTY_PLAN")
        if candidate.goal != current_plan.goal:
            raise ValueError("REPLAN_GOAL_CHANGED")
        if (candidate.outcome_contract_sha256 is not None
                and candidate.outcome_contract_sha256 != current_plan.outcome_contract_sha256):
            raise FormationError("REPLAN_OUTCOME_CONTRACT_CHANGED")
        if (candidate.outcome_receipt_bindings
                and candidate.outcome_receipt_bindings != current_plan.outcome_receipt_bindings):
            raise FormationError("REPLAN_OUTCOME_RECEIPT_CHANGED")
        if decision.strategy == "split_step" and any(
            step.index == decision.original_step_index and step.risk_level in {"high", "critical"}
            for step in current_plan.steps
        ):
            # The generic executor cannot prove that prepare/execute are distinct
            # safe phases. Repeating a write after an uncertain outcome needs
            # the owning tool's recovery/idempotency contract.
            raise ValueError("REPLAN_SIDE_EFFECT_SPLIT_REQUIRES_TOOL_CONTRACT")
        by_id = {step.step_id: step for step in candidate.steps}
        if len(by_id) != len(candidate.steps):
            raise ValueError("REPLAN_DUPLICATE_STEP_ID")
        risk = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        original_ids = {step.step_id for step in current_plan.steps}
        for previous in current_plan.steps:
            replacement = by_id.get(previous.step_id)
            if replacement is None:
                raise ValueError("REPLAN_REQUIRED_STEP_LOST")
            split_execution = (decision.strategy == "split_step"
                               and previous.index == decision.original_step_index
                               and replacement.action == f"[执行] {previous.action}")
            if (replacement.expected_output != previous.expected_output
                    or (replacement.action != previous.action and not split_execution)):
                raise ValueError("REPLAN_REQUIRED_OUTCOME_CHANGED")
            if (replacement.risk_level not in risk or previous.risk_level not in risk
                    or risk[replacement.risk_level] < risk[previous.risk_level]):
                raise ValueError("REPLAN_RISK_DOWNGRADE")
            if previous.status == "completed":
                old, new = previous.to_dict(), replacement.to_dict()
                old.pop("index")
                new.pop("index")
                if old != new:
                    raise ValueError("REPLAN_COMPLETED_STEP_CHANGED")
            elif replacement.status == "completed":
                raise ValueError("REPLAN_UNEXECUTED_STEP_COMPLETED")
            elif previous.formation is not None and replacement.to_dict() != previous.to_dict():
                # Changed formed arguments/tool/effect need an explicit owner
                # decision, not a model-created successor call or fresh budget.
                if (replacement.tool != previous.tool or replacement.params != previous.params
                        or replacement.formation != previous.formation):
                    raise FormationError("REPLAN_FORMED_CALL_CHANGED")
        if any(step.status == "completed" and step.step_id not in original_ids
               for step in candidate.steps):
            raise ValueError("REPLAN_UNEXECUTED_STEP_COMPLETED")

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

        integrity_failure = result.metrics.get("formation_changed_fields")
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
        if integrity_failure is not None:
            result.metrics["formation_changed_fields"] = integrity_failure
        if self._resuming:
            result.metrics["step_timeout_enforcement"] = "not_enforced_by_synchronous_executor"
            result.metrics["effective_budget_limits"] = dict(self._active_limits)

        # 轨迹评估
        if self.config.enable_evaluation or self._evaluator.has_outcome_contract:
            try:
                metrics = TrajectoryMetrics(
                    total_steps=len(steps),
                    completed_steps=completed,
                    failed_steps=failed,
                    replan_count=self._replanner.replan_count,
                    retry_count=self._consecutive_failures,
                    total_duration_ms=result.duration_ms,
                    estimated_cost=self._current_cost,
                    budget_cost=(self._active_limits or self._current_budget_limits())["max_cost"],
                    expected_steps=len(steps),
                    goal_achieved=result.status == "completed",
                    final_error=result.error,
                )
                eval_result = self._evaluator.evaluate(
                    metrics, agent_id=result.agent_id, task_id=result.task_id,
                    expected_contract_sha256=(self._current_plan.outcome_contract_sha256
                                              if self._current_plan else None),
                    expected_output_receipts=(self._current_plan.outcome_receipt_bindings
                                              if self._current_plan else None))
                result.evaluation = eval_result.to_dict()
                outcome = eval_result.outcome_verification
                result.metrics["outcome_state"] = outcome.get("state", "NOT_VERIFIED")
                if (outcome.get("state") == "VERIFIED" and self._current_plan
                        and result.status == "completed"):
                    self._current_plan.outcome_receipt_bindings = deepcopy(
                        outcome.get("committed_output_bindings", {}))
                    result.plan = self._current_plan.to_dict()
                if (self._evaluator.has_outcome_contract and result.status == "completed"
                        and outcome.get("state") != "VERIFIED"):
                    result.status = "blocked"
                    result.error = outcome.get("reason", "OUTCOME_NOT_VERIFIED")
                    result.result = None

                # 保存评估证据
                self._durable.save_evidence(
                    task_id=result.task_id,
                    evidence_type="trajectory_evaluation",
                    content=json.dumps(result.evaluation, ensure_ascii=False, default=str)[:2000],
                    authenticity_score=eval_result.overall_score,
                )
            except Exception:
                result.evaluation = {"outcome_verification": {"state": "BLOCKED",
                    "reason": "OUTCOME_OWNER_UNAVAILABLE", "verified_goal_achieved": False,
                    "user_verified": False}}
                if self._evaluator.has_outcome_contract and result.status == "completed":
                    result.status = "blocked"
                    result.error = "OUTCOME_OWNER_UNAVAILABLE"
                    result.result = None

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

        if self._resuming and result.status != "completed":
            result.goal = ""
            result.plan = None
            result.result = None
        return result

    @staticmethod
    def _default_tool_executor(step: PlanStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Missing execution binding is unavailable, never a completed user job."""
        return {
            "success": False,
            "error": "TOOL_EXECUTOR_NOT_BOUND: no tool was executed",
            "tool": step.tool,
            "estimated_cost": 0.0,
        }
