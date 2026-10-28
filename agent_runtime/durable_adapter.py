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
from contextlib import nullcontext
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

_CHECKPOINT_FORMAT = "lumenis.agent_runtime.checkpoint"
_CHECKPOINT_VERSION = 1
_CHECKPOINT_CONTEXT_KEYS = frozenset({"actor_id", "domain_id", "scope", "agent_runtime"})
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
            if key in {"APPROVAL_REQUIRED", "requiring_approval"} and type(item) is int and item >= 0:
                cleaned[key] = item  # Registry policy count, never an approval/token.
                continue
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


_PLAN_RECEIPT_FIELDS = (
    "provider", "status", "code", "operation", "attempt_id", "domain_id", "scope",
    "request_id", "request_digest", "run_id", "model_id", "model_revision", "recipe",
    "runtime_sha256", "executor_sha256", "source_use_policy_version", "source_use_policy_sha256",
    "source_binding_sha256", "input_revision_sha256", "source_evidence_refs",
    "prompt_tokens", "completion_tokens", "total_tokens",
)
_PLAN_RECEIPT_KEYS = frozenset(_PLAN_RECEIPT_FIELDS)
_LEGACY_PLAN_RECEIPT_FIELDS = (
    "provider", "status", "operation", "request_id", "request_digest", "run_id",
    "model_id", "model_revision", "recipe", "source_use_policy_sha256",
    "source_binding_sha256", "input_revision_sha256", "source_evidence_refs",
    "prompt_tokens", "completion_tokens", "total_tokens",
)
_LEGACY_PLAN_RECEIPT_KEYS = frozenset(_LEGACY_PLAN_RECEIPT_FIELDS)
_PLAN_TOKEN_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens")


def _validated_plan_inference_receipt(
    value: Any, *, require_attempt_id: bool = False,
) -> dict[str, Any] | None:
    """Accept only the bounded receipt emitted by the existing Agent Gateway."""
    if type(value) is not dict:
        return None
    keys = set(value)
    allowed_keys = (_PLAN_RECEIPT_KEYS,) if require_attempt_id else (
        _PLAN_RECEIPT_KEYS, _LEGACY_PLAN_RECEIPT_KEYS,
    )
    if all(keys != candidate for candidate in allowed_keys):
        return None
    current_receipt = keys == _PLAN_RECEIPT_KEYS
    if (value.get("provider") != "owned" or value.get("status") != "COMPLETED"
            or value.get("operation") != "agent_plan"
            or current_receipt and value.get("code") != "OWNED_INFERENCE_COMPLETED"):
        return None
    if "attempt_id" in value and (type(value["attempt_id"]) is not str
                                  or not re.fullmatch(r"attempt_[0-9a-f]{32}", value["attempt_id"])):
        return None
    for key in ("request_id", "run_id", "model_id", "model_revision", "recipe"):
        item = value.get(key)
        if type(item) is not str or not item.strip() or len(item) > 512:
            return None
    for key in ("request_digest", "source_use_policy_sha256", "source_binding_sha256",
                "input_revision_sha256"):
        item = value.get(key)
        if type(item) is not str or not re.fullmatch(r"[0-9a-f]{64}", item):
            return None
    if current_receipt:
        for key in ("runtime_sha256", "executor_sha256"):
            item = value.get(key)
            if type(item) is not str or not re.fullmatch(r"[0-9a-f]{64}", item):
                return None
        for key in ("domain_id", "scope", "source_use_policy_version"):
            item = value.get(key)
            if type(item) is not str or not item.strip() or len(item) > 1024:
                return None
    refs = value.get("source_evidence_refs")
    if (type(refs) is not list or not refs or len(refs) > 128
            or any(type(item) is not str or not item.strip() or len(item) > 512 for item in refs)):
        return None
    tokens = [value.get(key) for key in _PLAN_TOKEN_FIELDS]
    if (any(type(item) is not int or item < 0 for item in tokens)
            or value["completion_tokens"] < 1
            or value["total_tokens"] != value["prompt_tokens"] + value["completion_tokens"]):
        return None
    fields = _PLAN_RECEIPT_FIELDS if "attempt_id" in value else _LEGACY_PLAN_RECEIPT_FIELDS
    return {key: value[key] for key in fields}


def _validated_context_budget(value, receipt, model):
    if type(value) is not dict:
        return None
    def sha(item):
        return type(item) is str and re.fullmatch(r'[0-9a-f]{64}', item) is not None
    required = value.get('required_context_sha256')
    if required is not None and not sha(required):
        return None
    memory_sha256 = value.get('human_correction_memory_sha256')
    if memory_sha256 is not None and not sha(memory_sha256):
        return None
    no_model_fields = {'required_context_sha256', 'measurement', 'model_execution'}
    if set(value) in (no_model_fields, no_model_fields | {'human_correction_memory_sha256'}):
        return dict(value) if (model == 'none' and receipt is None
            and value['measurement'] == 'NOT_REQUESTED_NO_MODEL' and value['model_execution'] == 'NOT_RUN') else None
    fields = {'ok', 'fits', 'prompt_tokens', 'context_window_tokens', 'output_token_limit',
              'output_tokens_reserved', 'request_sha256', 'runtime_sha256', 'tokenizer_identity',
              'formatter_sha256', 'count_method', 'generation_performed', 'binding_sha256'}
    if not fields.issubset(value) or set(value) - fields - {
            'omitted_sections', 'required_context_sha256', 'human_correction_memory_sha256'}:
        return None
    if (value['ok'] is not True or type(value['fits']) is not bool or value['generation_performed'] is not False
            or value['count_method'] != 'loaded_runtime_tokenizer'
            or any(not sha(value[key]) for key in ('request_sha256', 'runtime_sha256', 'tokenizer_identity',
                                                  'formatter_sha256', 'binding_sha256'))
            or value['tokenizer_identity'] != value['runtime_sha256']):
        return None
    from lumenis.system.ai_gateway.owned_service import _MAX_TOKEN_LIMIT
    counts = ('prompt_tokens', 'context_window_tokens', 'output_token_limit', 'output_tokens_reserved')
    if any(type(value[key]) is not int or not (0 if key == 'prompt_tokens' else 1) <= value[key] <= _MAX_TOKEN_LIMIT
           for key in counts):
        return None
    if (not value['output_tokens_reserved'] <= value['output_token_limit'] <= value['context_window_tokens']
            or value['fits'] != (value['prompt_tokens'] + value['output_tokens_reserved'] <= value['context_window_tokens'])
            or receipt is None or value['request_sha256'] != receipt['request_digest']
            or value['prompt_tokens'] != receipt['prompt_tokens']
            or receipt['completion_tokens'] > value['output_tokens_reserved']):
        return None
    omissions = value.get('omitted_sections', [])
    if type(omissions) is not list or len(omissions) > 2:
        return None
    for omission in omissions:
        if (type(omission) is not dict or set(omission) != {'section', 'sha256', 'reason'}
                or omission['section'] not in {'derived_memory', 'reviewed_learning_context'}
                or not sha(omission['sha256']) or omission['reason'] != 'selected_model_context_budget'):
            return None
    return {**value, 'omitted_sections': [dict(item) for item in omissions]}


def _sanitize_plan_snapshot(value: Any):
    """Sanitize a plan and bind persisted token metrics to an exact Gateway receipt."""
    if type(value) is not dict:
        return _sanitize_checkpoint_value(value)
    raw = dict(value)
    receipt_raw = raw.pop("inference_receipt", None)
    usage_raw = raw.pop("token_usage", None)
    budget_raw = raw.pop('context_budget', None)
    cleaned, sensitive = _sanitize_checkpoint_value(raw)
    if type(cleaned) is not dict:
        return {}, True

    receipt_claimed = receipt_raw not in (None, {})
    usage_claimed = usage_raw not in (None, {})
    receipt = _validated_plan_inference_receipt(receipt_raw)
    if receipt is not None:
        expected_usage = {key: receipt[key] for key in _PLAN_TOKEN_FIELDS}
        if usage_claimed and usage_raw != expected_usage:
            sensitive = True
        cleaned["inference_receipt"] = receipt
        cleaned["token_usage"] = expected_usage
    else:
        if receipt_claimed or usage_claimed:
            sensitive = True
        if receipt_claimed:
            cleaned.pop("inference_receipt", None)
        cleaned["token_usage"] = {}
    if budget_raw is not None:
        budget = _validated_context_budget(budget_raw, receipt, raw.get('model'))
        if budget is None:
            sensitive = True
        else:
            cleaned['context_budget'] = budget
    return cleaned, sensitive


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
        operational_admission=None,
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
        self._operational_admission = operational_admission
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

    def _require_write_permission(self, resource: str, *, connection=None) -> None:
        if self._operational_admission is not None:
            from lumenis.system.security.permission import (
                check_task_operational_write, _TASK_OPERATIONAL_FIELDS)
            decision = check_task_operational_write(self._operational_admission,
                resource=resource, fields=_TASK_OPERATIONAL_FIELDS.get(resource, ()), connection=connection)
            if not decision.allowed:
                raise PermissionError(decision.reason)
            return
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
        _terminal: Optional[Dict[str, Any]] = None,
    ) -> Checkpoint:
        """保存检查点（每步完成后调用）。

        复用 ai_task_engine._db_add_step()。
        """
        if self._operational_admission is not None and task_id != self._operational_admission.task_id:
            raise PermissionError("TASK_OPERATIONAL_TASK_MISMATCH")
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
                if _terminal is not None or state == "executing" or self._operational_admission is not None:
                    self._require_write_permission("ai_task")
                    outcome = _terminal or {"status": "running", "result": None, "error": None}
                    return self._commit_terminal_checkpoint(engine, cp, detail, outcome)
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

    def finalize_task(self, task_id: str, state: str, *, result=None, error=None, **checkpoint_args) -> Checkpoint:
        """Commit a whole-task outcome with its checkpoint, never a single step.

        Both records use the existing TaskEngine tables in one SQLite transaction.
        No tool is rerun by this operation; a repeated identical finalization is a no-op.
        """
        if state not in {"completed", "failed", "cancelled"}:
            raise ValueError("Invalid terminal agent state")
        safe_result, _ = _sanitize_checkpoint_value(result)
        safe_error, _ = _sanitize_checkpoint_value(error)
        terminal = {"status": "succeeded" if state == "completed" else state,
                    "result": safe_result if state == "completed" else None,
                    "error": safe_error}
        if self._enabled:
            self._require_write_permission("ai_task")
        cp = self.checkpoint(task_id=task_id, state=state, _terminal=terminal, **checkpoint_args)
        if not self._enabled:
            with self._lock:
                self._memory_tasks[task_id].update(terminal)
        return cp

    def _commit_terminal_checkpoint(self, engine, cp, detail, terminal):
        from lumenis.shared.database import get_repository

        encoded = json.dumps(terminal["result"], ensure_ascii=False, sort_keys=True, allow_nan=False)
        guard = self._operational_admission.guard() if self._operational_admission is not None else nullcontext()
        with guard, get_repository().transaction() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT status,result_json,error,created_by FROM ai_task WHERE task_id=?",
                               (cp.task_id,)).fetchone()
            if row is None or row["created_by"] != "agent_runtime":
                raise ValueError("Agent finalization requires its existing TaskEngine task")
            if row["status"] == terminal["status"] == "cancelled":
                terminal = {**terminal, "error": row["error"]}
            if (row["status"] in {"succeeded", "failed", "cancelled"}
                    and not (row["status"] == "failed" and terminal["status"] == "running")):
                # Cancellation always wins over a late worker outcome.
                if (row["status"] != terminal["status"] or
                        json.loads(row["result_json"] or "null") != terminal["result"] or
                        row["error"] != terminal["error"]):
                    raise RuntimeError("Task already has a different terminal outcome")
                rows = conn.execute("SELECT * FROM ai_task_step WHERE task_id=? ORDER BY rowid DESC",
                                    (cp.task_id,)).fetchall()
                for existing in rows:
                    previous = self._checkpoint_from_step(dict(existing))
                    if previous is not None and previous.state == cp.state:
                        return previous
                # A separately cancelled task can still acquire its final checkpoint.
            now = engine._now()
            conn.execute("""INSERT INTO ai_task_step
                (step_id,task_id,phase,status,detail,agent_id,started_at,finished_at,duration_ms)
                VALUES (?,?,?,?,?,?,?,?,0)""",
                (engine._gen_id("step"), cp.task_id, f"agent_step_{cp.step_index}",
                 cp.state, detail, cp.agent_id or None, now, now))
            conn.execute("""UPDATE ai_task SET status=?,result_json=?,error=?,finished_at=?,updated_at=?
                            WHERE task_id=?""",
                         (terminal["status"], encoded, terminal["error"],
                          None if terminal["status"] == "running" else now, now, cp.task_id))
            # Recheck write policy at the commit boundary; exceptions roll back both records.
            self._require_write_permission("ai_task", connection=conn)
            self._require_write_permission("ai_task_step", connection=conn)
        with self._lock:
            self._memory_checkpoints.setdefault(cp.task_id, []).append(cp)
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
        if self._operational_admission is not None:
            if task_id != self._operational_admission.task_id:
                raise PermissionError("TASK_OPERATIONAL_TASK_MISMATCH")
            from lumenis.shared.database import get_repository
            import hashlib
            evidence_id, now = engine._gen_id("ev"), engine._now()
            with self._operational_admission.guard(), get_repository().transaction() as conn:
                conn.execute("BEGIN IMMEDIATE")
                self._require_write_permission("ai_task_evidence", connection=conn)
                previous = conn.execute("SELECT current_hash FROM ai_task_evidence WHERE task_id=? ORDER BY rowid DESC LIMIT 1", (task_id,)).fetchone()
                previous_hash = previous[0] if previous else None
                current_hash = hashlib.sha256(f"{previous_hash or 'genesis'}|{evidence_id}|{task_id}|{content}|{now}".encode()).hexdigest()
                conn.execute("""INSERT INTO ai_task_evidence(evidence_id,task_id,step_id,evidence_type,
                    content,source,authenticity_score,created_at,previous_hash,current_hash)
                    VALUES(?,?,?,?,?,'agent_runtime',?,?,?,?)""",
                    (evidence_id,task_id,step_id,evidence_type,content,authenticity_score,now,previous_hash,current_hash))
                self._require_write_permission("ai_task_evidence", connection=conn)
            return evidence_id
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

    @staticmethod
    def _model_request_identity(request):
        from lumenis.system.ai_gateway.owned_service import OwnedServiceRequest, owned_service_request_digest
        if type(request) is not OwnedServiceRequest or request.operation != 'agent_plan':
            raise ValueError('AGENT_MODEL_TYPED_REQUEST_REQUIRED')
        return {'schema': 'agent-owned-model-attempt/v1', 'task_id': request.job_id,
                'request_id': request.request_id, 'request_digest': owned_service_request_digest(request),
                'source_binding_sha256': request.source_binding_sha256,
                'input_revision_sha256': request.input_revision_sha256,
                'source_use_policy_sha256': request.source_use_policy_sha256}

    def _model_request_row(self, connection, request):
        identity = self._model_request_identity(request)
        rows = connection.execute("SELECT * FROM ai_task_step WHERE task_id=? AND phase='agent_model_request' ORDER BY rowid",
                                  (request.job_id,)).fetchall()
        if not rows:
            return None, None
        if len(rows) != 1:
            raise RuntimeError('AGENT_MODEL_ATTEMPT_CONFLICT')
        row = dict(rows[0])
        try:
            content = json.loads(row['detail'])
        except (ValueError, TypeError) as exc:
            raise RuntimeError('AGENT_MODEL_RECEIPT_INVALID') from exc
        if type(content) is not dict or any(content.get(key) != value for key, value in identity.items()):
            raise RuntimeError('AGENT_MODEL_INPUT_CHANGED_NO_REPLAY')
        return row, content

    def read_model_response(self, request):
        """Read an immutable completed response; an uncertain attempt never runs again."""
        if not self._enabled or self._operational_admission is None:
            raise PermissionError('AGENT_MODEL_DURABLE_ADMISSION_REQUIRED')
        from lumenis.shared.database import get_repository
        with get_repository().connection(read_only=True, wal=False) as con:
            self._require_write_permission('ai_task_step', connection=con)
            row, content = self._model_request_row(con, request)
            if row is None:
                return None
            if row['status'] != 'completed' or content.get('state') != 'COMPLETED':
                raise RuntimeError('AGENT_MODEL_RESULT_UNKNOWN_NO_REPLAY')
            result, budget = self._checked_model_response(
                request, content.get('result'), content.get('context_budget'),
                allow_legacy_attempt_receipt=True,
            )
            evaluation_call_ref, evaluation_link_state = self._checked_evaluation_link(
                content.get('evaluation_call_ref'),
                content.get('evaluation_link_state', 'NOT_RECORDED'),
            )
            self._require_write_permission('ai_task_step', connection=con)
            return {'result': result, 'context_budget': budget,
                    'evaluation_call_ref': evaluation_call_ref,
                    'evaluation_link_state': evaluation_link_state}

    def reserve_model_request(self, request):
        """Reserve in the existing Task step table before the model invocation."""
        if not self._enabled or self._operational_admission is None or request.job_id != self._operational_admission.task_id:
            raise PermissionError('AGENT_MODEL_DURABLE_ADMISSION_REQUIRED')
        from lumenis.shared.database import get_repository
        engine = self._require_task_engine()
        identity = self._model_request_identity(request)
        with self._operational_admission.guard(), get_repository().transaction() as con:
            con.execute('BEGIN IMMEDIATE')
            self._require_write_permission('ai_task_step', connection=con)
            row, _ = self._model_request_row(con, request)
            if row is not None:
                raise RuntimeError('AGENT_MODEL_RESULT_UNKNOWN_NO_REPLAY')
            task = con.execute('SELECT agent_id,status FROM ai_task WHERE task_id=?', (request.job_id,)).fetchone()
            if not task or task['status'] == 'cancelled':
                raise PermissionError('USER_CANCELLED')
            identifier, now = engine._gen_id('step'), engine._now()
            content = {**identity, 'state': 'RESERVED', 'recovery': 'UNKNOWN_NO_AUTOMATIC_MODEL_REPLAY',
                       'queue_attempt': {'run_id': self._operational_admission.run_id,
                                         'worker_id': self._operational_admission.worker_id,
                                         'lease_owner': self._operational_admission.lease_owner}}
            con.execute('''INSERT INTO ai_task_step
                (step_id,task_id,phase,status,detail,agent_id,started_at) VALUES(?,?,'agent_model_request','running',?,?,?)''',
                (identifier, request.job_id, json.dumps(content, ensure_ascii=False, sort_keys=True,
                 allow_nan=False), task['agent_id'], now))
            self._require_write_permission('ai_task_step', connection=con)
        return identifier

    @staticmethod
    def _checked_model_response(request, result, budget, *, allow_legacy_attempt_receipt=False):
        """Keep a request-matching receipt and bounded, credential-free plan data."""
        receipt = _validated_plan_inference_receipt(
            {key: result[key] for key in _PLAN_RECEIPT_FIELDS if key in result},
            require_attempt_id=not allow_legacy_attempt_receipt,
        ) if type(result) is dict else None
        if (receipt is None or result.get('ok') is not True or result.get('real_input_bound') is not True
                or receipt['request_id'] != request.request_id
                or receipt['request_digest'] != DurableExecutionAdapter._model_request_identity(request)['request_digest']
                or any(receipt[key] != getattr(request, key) for key in
                       ('source_binding_sha256', 'input_revision_sha256', 'source_use_policy_sha256'))
                or 'domain_id' in receipt and receipt['domain_id'] != request.domain_id
                or 'scope' in receipt and receipt['scope'] != request.scope
                or 'source_use_policy_version' in receipt
                   and receipt['source_use_policy_version'] != request.source_use_policy_version
                or receipt['source_evidence_refs'] != list(request.source_evidence_refs)):
            raise RuntimeError('AGENT_MODEL_RECEIPT_INVALID')
        checked_budget = _validated_context_budget(budget, receipt, receipt['model_id'])
        analysis, sensitive = _sanitize_checkpoint_value(result.get('analysis'))
        if (checked_budget is None or sensitive or type(analysis) not in (str, dict)
                or not analysis or len(json.dumps(analysis, ensure_ascii=False).encode()) > 4 * 1024 * 1024):
            raise RuntimeError('AGENT_MODEL_RESULT_NOT_PERSISTABLE')
        return {'ok': True, 'real_input_bound': True, **receipt, 'analysis': analysis}, checked_budget

    @staticmethod
    def _checked_evaluation_link(evaluation_call_ref, evaluation_link_state):
        allowed_states = {'VERIFIED', 'NOT_LINKED', 'NOT_RECORDED', 'UNAVAILABLE'}
        if evaluation_link_state not in allowed_states:
            raise RuntimeError('AGENT_MODEL_EVALUATION_LINK_INVALID')
        if evaluation_link_state == 'VERIFIED':
            if (type(evaluation_call_ref) is not str
                    or re.fullmatch(r'ai-call:v1:[1-9][0-9]{0,15}:[0-9a-f]{64}', evaluation_call_ref) is None):
                raise RuntimeError('AGENT_MODEL_EVALUATION_LINK_INVALID')
        elif evaluation_call_ref is not None:
            raise RuntimeError('AGENT_MODEL_EVALUATION_LINK_INVALID')
        return evaluation_call_ref, evaluation_link_state

    def record_model_response(self, request, reservation, result, budget, *,
                              evaluation_call_ref=None, evaluation_link_state='NOT_RECORDED'):
        """Commit the verified result before tool formation; no prompt/secret retention."""
        if self._operational_admission is None or request.job_id != self._operational_admission.task_id:
            raise PermissionError('AGENT_MODEL_DURABLE_ADMISSION_REQUIRED')
        # A failed/unavailable response cannot authorize a retry. Preserve only
        # the reservation in that case, including after an unknown process exit.
        if type(result) is not dict or result.get('ok') is not True or result.get('status') != 'COMPLETED':
            return
        retained, checked_budget = self._checked_model_response(request, result, budget)
        evaluation_call_ref, evaluation_link_state = self._checked_evaluation_link(
            evaluation_call_ref, evaluation_link_state,
        )
        from lumenis.shared.database import get_repository
        engine = self._require_task_engine()
        with self._operational_admission.guard(), get_repository().transaction() as con:
            con.execute('BEGIN IMMEDIATE')
            self._require_write_permission('ai_task_step', connection=con)
            row, content = self._model_request_row(con, request)
            if row is None or row['step_id'] != reservation or row['status'] != 'running' or content.get('state') != 'RESERVED':
                raise RuntimeError('AGENT_MODEL_ATTEMPT_CONFLICT')
            task = con.execute('SELECT status FROM ai_task WHERE task_id=?', (request.job_id,)).fetchone()
            if not task or task['status'] == 'cancelled':
                raise PermissionError('USER_CANCELLED')
            completed = {**content, 'state': 'COMPLETED', 'recovery': 'IMMUTABLE_RESULT_NO_MODEL_REPLAY',
                         'result': retained, 'context_budget': checked_budget,
                         'evaluation_call_ref': evaluation_call_ref,
                         'evaluation_link_state': evaluation_link_state}
            con.execute("UPDATE ai_task_step SET status='completed',detail=?,finished_at=?,duration_ms=0 WHERE step_id=? AND status='running'",
                        (json.dumps(completed, ensure_ascii=False, sort_keys=True, allow_nan=False), engine._now(), reservation))
            self._require_write_permission('ai_task_step', connection=con)

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
