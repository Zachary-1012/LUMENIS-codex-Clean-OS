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
  - 启用持久化时，以 TaskEngine 数据库为准；写入失败必须显式返回错误
  - 仅在显式禁用持久化时使用内存状态
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

_CHECKPOINT_FORMAT = "lumenis.agent_runtime.checkpoint"
_CHECKPOINT_VERSION = 1


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
                from lumenis.system.security import get_permission_gate
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
            result = gate.check(
                operation_type=operation,
                resource=resource,
                caller="agent_runtime.durable_adapter",
            )
            return result.allowed
        except Exception:
            return False

    def _require_task_engine(self) -> Any:
        engine = self._get_task_engine()
        if engine is None:
            raise RuntimeError("Durable TaskEngine is unavailable")
        return engine

    def _require_write_permission(self, resource: str) -> None:
        try:
            from lumenis.system.security import OperationType
        except Exception as exc:
            raise PermissionError("Durable write permission is unavailable") from exc
        if not self._check_permission(OperationType.DB_WRITE, resource):
            raise PermissionError(f"Durable write denied for {resource}")

    @staticmethod
    def _task_from_db(task: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if task is None:
            return None
        result = dict(task)
        try:
            context = json.loads(result.get("context_json") or "{}")
        except (json.JSONDecodeError, TypeError) as exc:
            raise RuntimeError("Persisted TaskEngine context is malformed") from exc
        if not isinstance(context, dict):
            raise RuntimeError("Persisted TaskEngine context must be an object")
        result["context"] = context
        result["goal"] = result.get("user_input", result.get("goal", ""))
        result["agent_id"] = result.get("agent_id") or ""
        result["source"] = "db"
        return result

    @staticmethod
    def _checkpoint_from_step(step: Dict[str, Any]) -> Optional[Checkpoint]:
        phase = str(step.get("phase") or "")
        if not phase.startswith("agent_step_"):
            return None
        try:
            envelope = json.loads(step.get("detail") or "")
        except (json.JSONDecodeError, TypeError) as exc:
            raise RuntimeError("Persisted agent checkpoint is malformed") from exc
        if (not isinstance(envelope, dict) or envelope.get("format") != _CHECKPOINT_FORMAT
                or envelope.get("version") != _CHECKPOINT_VERSION):
            raise RuntimeError("Persisted agent checkpoint version is unsupported")
        payload = envelope.get("checkpoint")
        if not isinstance(payload, dict):
            raise RuntimeError("Persisted agent checkpoint payload is missing")
        try:
            checkpoint = Checkpoint(**payload)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Persisted agent checkpoint payload is invalid") from exc
        if (checkpoint.task_id != step.get("task_id")
                or type(checkpoint.step_index) is not int or checkpoint.step_index < 0
                or str(checkpoint.step_index) != phase.removeprefix("agent_step_")
                or not isinstance(checkpoint.plan_snapshot, dict)
                or not isinstance(checkpoint.context, dict)
                or not isinstance(checkpoint.metadata, dict)):
            raise RuntimeError("Persisted agent checkpoint identity does not match its step")
        return checkpoint

    @classmethod
    def _db_checkpoints(cls, steps: List[Dict[str, Any]]) -> List[Checkpoint]:
        checkpoints = []
        for step in steps:
            checkpoint = cls._checkpoint_from_step(step)
            if checkpoint is not None:
                checkpoints.append(checkpoint)
        return checkpoints

    def create_task(
        self,
        goal: str,
        agent_id: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """创建任务记录，返回 task_id。

        复用 ai_task_engine.create_task()。
        """
        if self._enabled:
            engine = self._require_task_engine()
            self._require_write_permission("ai_task")
            try:
                created = engine.create_task(
                    user_input=goal,
                    context=context or {},
                    created_by="agent_runtime",
                )
                task_id = created.get("task_id") if isinstance(created, dict) else None
                if not isinstance(task_id, str) or not task_id:
                    raise RuntimeError("TaskEngine returned no task ID")
                engine._db_update_task(task_id, agent_id=agent_id)
                persisted = engine.get_task(task_id) if task_id else None
            except Exception as exc:
                raise RuntimeError("TaskEngine could not persist agent task") from exc
            if not task_id or persisted is None:
                raise RuntimeError("TaskEngine did not confirm the persisted agent task")
            with self._lock:
                self._memory_tasks[task_id] = {
                    "task_id": task_id,
                    "goal": goal,
                    "agent_id": agent_id,
                    "context": context or {},
                    "status": persisted.get("status", "pending"),
                    "created_at": persisted.get("created_at"),
                }
            return task_id

        task_id = f"agent_{uuid.uuid4().hex[:16]}"
        with self._lock:
            self._memory_tasks[task_id] = {
                "task_id": task_id,
                "goal": goal,
                "agent_id": agent_id,
                "context": context or {},
                "status": "created",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source": "memory",
            }
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
        metadata: Optional[Dict[str, Any]] = None,
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
            metadata=metadata or {},
        )

        if self._enabled:
            engine = self._require_task_engine()
            self._require_write_permission("ai_task_step")
            try:
                if engine.get_task(task_id) is None:
                    raise ValueError("TaskEngine task does not exist")
                detail = json.dumps({
                    "format": _CHECKPOINT_FORMAT,
                    "version": _CHECKPOINT_VERSION,
                    "checkpoint": cp.to_dict(),
                    "step_detail": step_detail or state,
                    "step_status": step_status,
                }, ensure_ascii=False, separators=(",", ":"))
                step_id = engine._db_add_step(
                    task_id=task_id,
                    phase=f"agent_step_{step_index}",
                    status=step_status,
                    detail=detail,
                    agent_id=agent_id or None,
                )
                if not step_id:
                    raise RuntimeError("TaskEngine returned no checkpoint step ID")
            except Exception as exc:
                raise RuntimeError("TaskEngine could not persist agent checkpoint") from exc

        with self._lock:
            self._memory_checkpoints.setdefault(task_id, []).append(cp)

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
            step_detail=json.dumps({"result": result, "error": error}, ensure_ascii=False),
            step_status=status,
            metadata={"result": result, "error": error},
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

        engine = self._require_task_engine()
        self._require_write_permission("ai_task_evidence")
        try:
            evidence_id = engine._db_add_evidence(
                task_id=task_id,
                evidence_type=evidence_type,
                content=content,
                source="agent_runtime",
                step_id=step_id,
                authenticity_score=authenticity_score,
            )
        except Exception as exc:
            raise RuntimeError("TaskEngine could not persist agent evidence") from exc
        if not evidence_id:
            raise RuntimeError("TaskEngine returned no persisted evidence ID")
        return evidence_id

    def cancel(self, task_id: str, reason: str = "user_cancelled") -> bool:
        """取消任务（复用 ai_task_engine.cancel_task）。"""
        if self._enabled:
            engine = self._require_task_engine()
            self._require_write_permission("ai_task")
            try:
                cancelled = engine.cancel_task(task_id, reason=reason)
                persisted = engine.get_task(task_id)
            except Exception as exc:
                raise RuntimeError("TaskEngine could not persist task cancellation") from exc
            if (not isinstance(cancelled, dict) or cancelled.get("status") != "cancelled"
                    or not isinstance(persisted, dict) or persisted.get("status") != "cancelled"):
                raise RuntimeError("TaskEngine did not confirm persisted task cancellation")
            with self._lock:
                if task_id in self._memory_tasks:
                    self._memory_tasks[task_id].update(status="cancelled", cancel_reason=reason)
            return True

        with self._lock:
            if task_id in self._memory_tasks:
                self._memory_tasks[task_id]["status"] = "cancelled"
                self._memory_tasks[task_id]["cancel_reason"] = reason
        return True  # 仅内存模式不代表 TaskEngine 持久化取消

    def recover(self, task_id: str) -> Optional[Dict[str, Any]]:
        """从检查点恢复任务状态。"""
        if self._enabled:
            engine = self._require_task_engine()
            try:
                task = self._task_from_db(engine.get_task(task_id))
                if task is None:
                    return None
                steps = engine.get_steps(task_id)
                checkpoints = self._db_checkpoints(steps)
            except Exception as exc:
                if isinstance(exc, RuntimeError):
                    raise
                raise RuntimeError("TaskEngine could not recover persisted task") from exc
            return {
                "task_id": task_id,
                "task": task,
                "steps": steps,
                "step_count": len(steps),
                "checkpoints": [item.to_dict() for item in checkpoints],
                "checkpoint_count": len(checkpoints),
                "last_checkpoint": checkpoints[-1].to_dict() if checkpoints else None,
                "source": "db",
            }

        with self._lock:
            checkpoints = self._memory_checkpoints.get(task_id, [])
            task = self._memory_tasks.get(task_id)
        if not checkpoints:
            return None
        return {
            "task_id": task_id,
            "task": task,
            "last_checkpoint": checkpoints[-1].to_dict(),
            "checkpoint_count": len(checkpoints),
            "source": "memory",
        }

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
        if self._enabled:
            engine = self._require_task_engine()
            try:
                return self._db_checkpoints(engine.get_steps(task_id))
            except Exception as exc:
                if isinstance(exc, RuntimeError):
                    raise
                raise RuntimeError("TaskEngine could not read persisted checkpoints") from exc
        with self._lock:
            return list(self._memory_checkpoints.get(task_id, []))

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息。"""
        if self._enabled:
            engine = self._require_task_engine()
            try:
                return self._task_from_db(engine.get_task(task_id))
            except Exception as exc:
                if isinstance(exc, RuntimeError):
                    raise
                raise RuntimeError("TaskEngine could not read persisted task") from exc
        with self._lock:
            task = self._memory_tasks.get(task_id)
            return dict(task) if task is not None else {}

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出任务。"""
        if self._enabled:
            engine = self._require_task_engine()
            try:
                tasks = engine.list_tasks(status=status)
                return [self._task_from_db(task) for task in tasks
                        if task.get("created_by") == "agent_runtime"]
            except Exception as exc:
                if isinstance(exc, RuntimeError):
                    raise
                raise RuntimeError("TaskEngine could not list persisted tasks") from exc
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
