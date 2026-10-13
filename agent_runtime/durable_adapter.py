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
import re
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_CHECKPOINT_FORMAT = "lumenis.agent_runtime.checkpoint"
_CHECKPOINT_VERSION = 1
_CHECKPOINT_CONTEXT_KEYS = frozenset({"actor_id", "domain_id", "scope"})
_CREDENTIAL_VALUE = re.compile(
    r"(?i)\b(?:bearer\s+[\w./~+-]{8,}|(?:sk|pk)-[\w-]{8,}|"
    r"gh[pousr]_[A-Za-z0-9]{10,}|github_pat_[\w]{10,}|"
    r"xox[baprs]-[\w-]{10,}|AIza[\w-]{20,}|"
    r"eyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,})"
)


def _sanitize_checkpoint_value(value: Any, token_usage: bool = False):
    """Redact recognizable credentials and omit secret fields from checkpoint data."""
    if isinstance(value, dict):
        cleaned, sensitive = {}, False
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            metric = token_usage and isinstance(item, (int, float)) and not isinstance(item, bool)
            if normalized == "rawresponse":
                continue
            if any(word in normalized for word in (
                    "apikey", "secret", "password", "credential", "authorization", "cookie",
                    "session", "approval", "accesstoken", "refreshtoken")) or (
                    "token" in normalized and normalized != "tokenusage" and not metric):
                sensitive = True
                continue
            safe_item, item_sensitive = _sanitize_checkpoint_value(item, token_usage or normalized == "tokenusage")
            sensitive = sensitive or item_sensitive
            cleaned[key] = safe_item
        return cleaned, sensitive
    if isinstance(value, (list, tuple)):
        items = [_sanitize_checkpoint_value(item, token_usage) for item in value]
        return [item[0] for item in items], any(item[1] for item in items)
    if isinstance(value, str) and _CREDENTIAL_VALUE.search(value):
        return _CREDENTIAL_VALUE.sub("[REDACTED]", value), True
    return value, False


def _sanitize_plan_snapshot(value: Any):
    """Preserve typed inference usage without admitting credentials as metrics.

    This exception applies only to the plan's Gateway receipt. Retained numbers
    describe usage; they establish no execution, permission or model admission.
    """
    if not isinstance(value, dict) or "inference_receipt" not in value:
        return _sanitize_checkpoint_value(value)
    remainder = {key: item for key, item in value.items() if key != "inference_receipt"}
    safe_plan, sensitive = _sanitize_checkpoint_value(remainder)
    receipt = value["inference_receipt"]
    if not isinstance(receipt, dict):
        safe_plan["inference_receipt"] = {}
        return safe_plan, True
    metric_keys = frozenset({"prompt_tokens", "completion_tokens", "total_tokens",
                             "context_window_tokens", "output_token_limit"})
    metrics = {key: item for key, item in receipt.items() if key in metric_keys}
    metadata = {key: item for key, item in receipt.items() if key not in metric_keys}
    safe_receipt, receipt_sensitive = _sanitize_checkpoint_value(metadata)
    valid = all(type(item) is int and item >= (1 if key in {
        "context_window_tokens", "output_token_limit"} else 0)
                for key, item in metrics.items())
    counts = {"prompt_tokens", "completion_tokens", "total_tokens"}
    if counts.intersection(metrics):
        valid = valid and counts.issubset(metrics)
        if counts.issubset(metrics):
            valid = valid and metrics["total_tokens"] == (
                metrics["prompt_tokens"] + metrics["completion_tokens"])
    if {"output_token_limit", "context_window_tokens"}.issubset(metrics):
        valid = valid and metrics["output_token_limit"] <= metrics["context_window_tokens"]
    if {"total_tokens", "context_window_tokens"}.issubset(metrics):
        valid = valid and metrics["total_tokens"] <= metrics["context_window_tokens"]
    if {"completion_tokens", "output_token_limit"}.issubset(metrics):
        valid = valid and metrics["completion_tokens"] <= metrics["output_token_limit"]
    if valid:
        safe_receipt.update(metrics)
    safe_plan["inference_receipt"] = safe_receipt
    return safe_plan, sensitive or receipt_sensitive or not valid


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
        safe_goal, _ = _sanitize_checkpoint_value(goal)
        safe_context, _ = _sanitize_checkpoint_value(context or {})
        safe_context = ({key: value for key, value in safe_context.items()
                         if key in _CHECKPOINT_CONTEXT_KEYS}
                        if isinstance(safe_context, dict) else {})
        if self._enabled:
            engine = self._require_task_engine()
            self._require_write_permission("ai_task")
            try:
                created = engine.create_task(
                    user_input=safe_goal,
                    context=safe_context,
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
                    "goal": safe_goal,
                    "agent_id": agent_id,
                    "context": safe_context,
                    "status": persisted.get("status", "pending"),
                    "created_at": persisted.get("created_at"),
                }
            return task_id

        task_id = f"agent_{uuid.uuid4().hex[:16]}"
        with self._lock:
            self._memory_tasks[task_id] = {
                "task_id": task_id,
                "goal": safe_goal,
                "agent_id": agent_id,
                "context": safe_context,
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
        safe_plan, plan_sensitive = _sanitize_plan_snapshot(plan_snapshot or {})
        context = {key: value for key, value in (context or {}).items()
                   if key in _CHECKPOINT_CONTEXT_KEYS}
        safe_context, context_sensitive = _sanitize_checkpoint_value(context)
        safe_metadata, metadata_sensitive = _sanitize_checkpoint_value(metadata or {})
        safe_detail, detail_sensitive = _sanitize_checkpoint_value(step_detail or state)
        if not isinstance(safe_plan, dict):
            safe_plan = {}
        if not isinstance(safe_context, dict):
            safe_context = {}
        if not isinstance(safe_metadata, dict):
            safe_metadata = {}
        steps = safe_plan.get("steps")
        canonical = bool(safe_plan.get("plan_id")) and isinstance(steps, list)
        sensitive = plan_sensitive or context_sensitive or metadata_sensitive or detail_sensitive
        resumable = canonical and not sensitive and safe_metadata.get("resumable") is not False
        safe_metadata["resumable"] = resumable
        if not resumable:
            safe_metadata["non_resumable_reason"] = ("sensitive checkpoint material omitted"
                                                       if sensitive else "canonical plan snapshot unavailable")
        else:
            safe_metadata.pop("non_resumable_reason", None)

        cp = Checkpoint(
            agent_id=agent_id,
            task_id=task_id,
            step_index=step_index,
            state=state,
            plan_snapshot=safe_plan,
            context=safe_context,
            metadata=safe_metadata,
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
                    "step_detail": safe_detail,
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
        plan_snapshot: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        agent_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """标记步骤完成/失败。"""
        status = "completed" if error is None else "failed"
        checkpoint_metadata = dict(metadata or {})
        checkpoint_metadata.update({"result": result, "error": error})
        self.checkpoint(
            task_id=task_id,
            step_index=step_index,
            state=status,
            plan_snapshot=plan_snapshot,
            context=context,
            agent_id=agent_id,
            step_detail=status,
            step_status=status,
            metadata=checkpoint_metadata,
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
