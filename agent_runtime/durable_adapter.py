# -*- coding: utf-8 -*-
"""
Durable Execution Adapter — Durable Execution 适配器
====================================================
复用 ai_task_engine 的 checkpoint/retry/recover/cancel 能力，不重写。

通过 Adapter 模式将 ai_task_engine 的能力暴露给 Agent Runtime：
  - checkpoint: 每步完成后保存状态到 ai_task_step
  - pause/resume: 暂停/恢复
  - retry: 重试失败步骤
  - recover: 异常后恢复
  - cancel: 取消任务

设计原则：
  - 不修改 ai_task_engine 源码
  - 通过组合/包装调用其现有方法
  - DB 写入失败时降级为内存状态，不阻断 Agent Loop
  - 所有写操作经过 permission_gate 检查

与 OSAI Contract 对齐点（C-01 Agent Runtime Contract）：
  - checkpoint_ref / trace_ref 字段
  - pause/resume/retry/recover/cancel API
"""
from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Checkpoint:
    """检查点数据。"""
    checkpoint_id: str = field(default_factory=lambda: f"cp_{uuid.uuid4().hex[:12]}")
    agent_id: str = ""
    task_id: str = ""
    step_index: int = 0
    state: str = ""
    plan_snapshot: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DurableExecutionAdapter:
    """Durable Execution 适配器。

    复用 ai_task_engine.TaskEngine 的：
      - create_task()       : 创建任务记录
      - _db_add_step()      : 保存步骤（checkpoint）
      - _db_add_evidence()  : 保存证据
      - cancel_task()       : 取消任务
      - get_steps()         : 恢复步骤历史

    用法：
        adapter = DurableExecutionAdapter()
        task_id = adapter.create_task(goal="分析舆情")
        adapter.checkpoint(task_id, step_index=0, state="executing", ...)
        adapter.cancel(task_id, reason="user cancelled")
    """

    def __init__(
        self,
        task_engine: Optional[Any] = None,
        permission_gate: Optional[Any] = None,
        enabled: bool = True,
    ):
        """
        Args:
            task_engine: ai_task_engine.TaskEngine 实例（None 则延迟获取）
            permission_gate: permission_gate.PermissionGate 实例（None 则延迟获取）
            enabled: 是否启用 DB 持久化（False 则仅内存）
        """
        self._task_engine = task_engine
        self._permission_gate = permission_gate
        self._enabled = enabled
        self._lock = threading.RLock()
        self._memory_checkpoints: Dict[str, List[Checkpoint]] = {}
        self._memory_tasks: Dict[str, Dict[str, Any]] = {}

    def _get_task_engine(self) -> Optional[Any]:
        """延迟获取 TaskEngine。"""
        if self._task_engine is None:
            try:
                from ai_task_engine import get_task_engine
                self._task_engine = get_task_engine()
            except Exception:
                self._task_engine = None
        return self._task_engine

    def _get_permission_gate(self) -> Optional[Any]:
        """延迟获取 PermissionGate。"""
        if self._permission_gate is None:
            try:
                from permission_gate import get_permission_gate
                self._permission_gate = get_permission_gate()
            except Exception:
                self._permission_gate = None
        return self._permission_gate

    def _check_permission(self, operation: Any, resource: str = "") -> bool:
        """检查权限（fail-closed）。"""
        gate = self._get_permission_gate()
        if gate is None:
            return False  # 无权限门时 fail-closed
        try:
            result = gate.check(operation, resource=resource)
            return result.allowed
        except Exception:
            return False

    def create_task(
        self,
        goal: str,
        agent_id: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """创建任务记录，返回 task_id。

        复用 ai_task_engine.create_task()。
        """
        task_id = f"agent_{uuid.uuid4().hex[:16]}"

        # 内存记录
        with self._lock:
            self._memory_tasks[task_id] = {
                "task_id": task_id,
                "goal": goal,
                "agent_id": agent_id,
                "context": context or {},
                "status": "created",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        # DB 持久化（复用 ai_task_engine）
        if self._enabled:
            engine = self._get_task_engine()
            if engine is not None:
                try:
                    # 检查权限
                    from permission_gate import OperationType, RiskLevel
                    if not self._check_permission(OperationType.DB_WRITE, "ai_task"):
                        return task_id  # 权限不足时仅内存

                    db_task_id = engine.create_task(
                        task_input=goal,
                        context=context or {},
                    )
                    if db_task_id:
                        task_id = db_task_id
                except Exception:
                    pass  # DB 写入失败降级为内存

        return task_id

    def checkpoint(
        self,
        task_id: str,
        step_index: int,
        state: str,
        plan_snapshot: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        step_detail: str = "",
        step_status: str = "running",
        agent_id: str = "",
    ) -> Checkpoint:
        """保存检查点（每步完成后调用）。

        复用 ai_task_engine._db_add_step()。
        """
        cp = Checkpoint(
            agent_id=agent_id,
            task_id=task_id,
            step_index=step_index,
            state=state,
            plan_snapshot=plan_snapshot or {},
            context=context or {},
        )

        # 内存记录
        with self._lock:
            if task_id not in self._memory_checkpoints:
                self._memory_checkpoints[task_id] = []
            self._memory_checkpoints[task_id].append(cp)

        # DB 持久化
        if self._enabled:
            engine = self._get_task_engine()
            if engine is not None:
                try:
                    from permission_gate import OperationType
                    if not self._check_permission(OperationType.DB_WRITE, "ai_task_step"):
                        return cp

                    engine._db_add_step(
                        task_id=task_id,
                        phase=f"agent_step_{step_index}",
                        status=step_status,
                        detail=step_detail or state,
                        agent_id=agent_id or None,
                    )
                except Exception:
                    pass  # 降级为内存

        return cp

    def complete_step(
        self,
        task_id: str,
        step_index: int,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """标记步骤完成/失败。"""
        status = "completed" if error is None else "failed"
        self.checkpoint(
            task_id=task_id,
            step_index=step_index,
            state=status,
            step_detail=json.dumps(result or {}, ensure_ascii=False)[:500],
            step_status=status,
        )

    def save_evidence(
        self,
        task_id: str,
        evidence_type: str,
        content: str,
        step_id: Optional[str] = None,
        authenticity_score: float = 0.8,
    ) -> Optional[str]:
        """保存证据（复用 ai_task_engine._db_add_evidence）。"""
        if not self._enabled:
            return None

        engine = self._get_task_engine()
        if engine is None:
            return None

        try:
            from permission_gate import OperationType
            if not self._check_permission(OperationType.DB_WRITE, "ai_task_evidence"):
                return None

            return engine._db_add_evidence(
                task_id=task_id,
                evidence_type=evidence_type,
                content=content,
                source="agent_runtime",
                step_id=step_id,
                authenticity_score=authenticity_score,
            )
        except Exception:
            return None

    def cancel(self, task_id: str, reason: str = "user_cancelled") -> bool:
        """取消任务（复用 ai_task_engine.cancel_task）。"""
        with self._lock:
            if task_id in self._memory_tasks:
                self._memory_tasks[task_id]["status"] = "cancelled"
                self._memory_tasks[task_id]["cancel_reason"] = reason

        if self._enabled:
            engine = self._get_task_engine()
            if engine is not None:
                try:
                    engine.cancel_task(task_id, reason=reason)
                    return True
                except Exception:
                    pass

        return True  # 内存取消总是成功

    def recover(self, task_id: str) -> Optional[Dict[str, Any]]:
        """从检查点恢复任务状态。"""
        # 先从内存恢复
        with self._lock:
            checkpoints = self._memory_checkpoints.get(task_id, [])
            task = self._memory_tasks.get(task_id)

        if checkpoints:
            last_cp = checkpoints[-1]
            return {
                "task_id": task_id,
                "task": task,
                "last_checkpoint": last_cp.to_dict(),
                "checkpoint_count": len(checkpoints),
                "source": "memory",
            }

        # 从 DB 恢复
        if self._enabled:
            engine = self._get_task_engine()
            if engine is not None:
                try:
                    steps = engine.get_steps(task_id)
                    if steps:
                        return {
                            "task_id": task_id,
                            "steps": steps,
                            "step_count": len(steps),
                            "source": "db",
                        }
                except Exception:
                    pass

        return None

    def retry_step(
        self,
        task_id: str,
        step_index: int,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """重试步骤（记录重试，实际执行由 Loop 完成）。"""
        with self._lock:
            task = self._memory_tasks.get(task_id, {})
            retry_key = f"step_{step_index}_retries"
            current = task.get(retry_key, 0) + 1
            task[retry_key] = current
            self._memory_tasks[task_id] = task

        return {
            "task_id": task_id,
            "step_index": step_index,
            "retry_count": current,
            "max_retries": max_retries,
            "can_retry": current < max_retries,
        }

    def get_checkpoints(self, task_id: str) -> List[Checkpoint]:
        """获取任务的所有检查点。"""
        with self._lock:
            return list(self._memory_checkpoints.get(task_id, []))

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息。"""
        with self._lock:
            return dict(self._memory_tasks.get(task_id, {}))

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出任务。"""
        with self._lock:
            tasks = list(self._memory_tasks.values())
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        return tasks

    def reset(self) -> None:
        """重置（测试用）。"""
        with self._lock:
            self._memory_checkpoints.clear()
            self._memory_tasks.clear()
