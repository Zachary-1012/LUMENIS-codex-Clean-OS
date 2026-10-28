# -*- coding: utf-8 -*-
"""分层 Memory 基础接口与数据结构。

与 OSAI memory_lifecycle.py 的 MemoryStore 六层模型通过 Contract 对齐：
  - 统一 store/retrieve/query/forget 接口
  - 记录携带 layer / key / value / timestamp / ttl / metadata
  - 不 import OSAI 代码，仅数据结构对齐
"""
from __future__ import annotations

import json
import math
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


_MEMORY_QUERY_TIME: ContextVar[Optional[float]] = ContextVar(
    "lumenis_memory_query_time", default=None,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_hash(obj: Any) -> str:
    import hashlib
    return hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


@dataclass
class MemoryRecord:
    """统一记忆记录结构（六层共用）。"""
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    layer: str = ""                       # working/task/episodic/semantic/skill/learning
    key: str = ""                         # 记忆键
    value: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_now_iso)
    ttl_seconds: float = 0.0              # 0 = 不过期
    source: str = "agent_runtime"         # 来源标识
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = _stable_hash(self.value)

    def is_expired(self, now: Optional[float] = None) -> bool:
        try:
            ttl_seconds = float(self.ttl_seconds)
        except (TypeError, ValueError, OverflowError):
            return True
        if ttl_seconds == 0:
            return False
        if ttl_seconds < 0 or not math.isfinite(ttl_seconds):
            return True
        try:
            created_at = datetime.fromisoformat(self.timestamp)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            created = created_at.timestamp()
        except (TypeError, ValueError, OverflowError, OSError):
            # A time-limited correction with an unreadable creation time cannot
            # be proven active. Fail closed so malformed stored timestamps do
            # not silently turn a temporary memory into permanent prompt input.
            return True
        current = time.time() if now is None else now
        try:
            current_time = float(current)
            if not math.isfinite(current_time):
                return True
            return (current_time - created) > ttl_seconds
        except (TypeError, ValueError, OverflowError):
            return True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseMemoryLayer:
    """记忆层抽象基类。

    子类必须实现：
      - _store(record) -> bool
      - _retrieve(key) -> Optional[MemoryRecord]
      - _query(filters, limit) -> List[MemoryRecord]
      - _forget(key) -> bool
    公共层负责 TTL 检查、Feature Flag 守卫、统一日志。
    """

    LAYER_NAME: str = "base"

    def __init__(self, db_path: Optional[str] = None, enabled: bool = False):
        self.db_path = db_path
        self.enabled = enabled
        self._in_memory: Dict[str, MemoryRecord] = {}
        self._task_binding = None

    def bind_task(self, task_id: str, actor_id: int):
        """Bind derived memory to an existing server task, never caller-supplied scope."""
        if not self.db_path or (actor_id is not None and type(actor_id) is not int):
            raise ValueError("MEMORY_TASK_BINDING_REQUIRED")
        self._task_binding = (str(task_id), actor_id)
        self._binding_context()
        self._in_memory.clear()
        return self

    def _binding_context(self, connection=None, *, write=False):
        if self._task_binding is None:
            raise PermissionError("MEMORY_TASK_BINDING_REQUIRED")
        task_id, actor_id = self._task_binding
        conn = connection or get_db_connection(self.db_path)
        try:
            row = conn.execute("SELECT * FROM ai_task WHERE task_id=?", (task_id,)).fetchone()
            if row is None:
                raise PermissionError("MEMORY_TASK_NOT_FOUND")
            task = dict(row)
            task["context"] = json.loads(task.get("context_json") or "{}")
            from agent_runtime.task_binding import authorized_context
            from lumenis.system.security.permission import resolve_local_workspace_principal
            shared_task = task["context"].get("domain_id") == "shared"
            actor = {"id": actor_id} if actor_id is not None else resolve_local_workspace_principal(
                module="content" if shared_task else "skills", action="read")
            if actor is None:
                raise PermissionError("MEMORY_ACTOR_REQUIRED")
            context = authorized_context(task, actor, connection=conn)
            # Derived memory, task snapshots and archived outputs are all views
            # of this original task. Reuse its canonical child-result read gate;
            # the parent Agent grant alone cannot revive withdrawn Skill data.
            from agent_runtime.task_binding import authorize_task_result_read
            task["result"] = json.loads(task.get("result_json") or "null")
            if authorize_task_result_read(task, actor) is not True:
                raise PermissionError("MEMORY_TASK_RESULT_SCOPE_DENIED")
            if write:
                if context['domain_id'] == 'shared':
                    from lumenis.system.security.permission import authorize_shared_workspace
                    authorize_shared_workspace(context['actor'], context['scope'], module='content', action='write', connection=conn)
                else:
                    from lumenis.system.security.permission import check_actor_scope_permission, check_local_workspace_scope_permission
                    checker = check_actor_scope_permission if actor_id is not None else check_local_workspace_scope_permission
                    decision = checker(context["actor"], domain_id=context["domain_id"],
                        action="write", module="agent_runtime" if actor_id is not None else "skills", connection=conn, **context["scope"])
                    if not decision.allowed:
                        raise PermissionError("MEMORY_WRITE_SCOPE_DENIED")
            return {"actor_id": actor_id, "domain_id": context["domain_id"],
                    "scope": context["scope"], "task_id": task_id}
        finally:
            if connection is None:
                conn.close()

    def _derived_rows(self):
        binding = self._binding_context()
        conn = get_db_connection(self.db_path)
        try:
            rows = conn.execute(
                "SELECT content_json FROM agent_learning_records WHERE learning_type=? AND related_task_id=? AND lifecycle_stage='raw'",
                ("derived_memory_" + self.LAYER_NAME, binding["task_id"])).fetchall()
            records = []
            for row in rows:
                try:
                    data = json.loads(row[0])
                    if (data.get("schema_version") != 1 or data.get("binding") != binding
                            or data.get("state") != "active"):
                        continue
                    record = MemoryRecord(**data["record"])
                    record.metadata = {**record.metadata, "memory_revision": data["revision"]}
                    records.append(record)
                except (ValueError, TypeError, KeyError):
                    continue
            self._binding_context(conn)
            return records
        finally:
            conn.close()

    def _write_derived(self, record, *, forgotten=False, expected_revision=None):
        binding = self._binding_context(write=True)
        identity = "derived:" + _stable_hash([self.LAYER_NAME, binding, record.key])
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._binding_context(conn, write=True)
            old = conn.execute("SELECT content_json FROM agent_learning_records WHERE record_id=?", (identity,)).fetchone()
            prior = json.loads(old[0]) if old else {}
            if old and (prior.get("schema_version") != 1 or prior.get("binding") != binding):
                raise PermissionError("MEMORY_BINDING_CHANGED")
            if (old and prior.get("state") == "forgotten" and not forgotten
                    and expected_revision is None):
                # FIX-060 E04-FORGET: a delayed writer may finish after a user forgets this key.
                # Keep the tombstone authoritative; a fresh implicit store is
                # not proof that the old derived work was intentionally restored.
                # An explicit correction can restore it only by matching the
                # current tombstone revision checked immediately below.
                raise PermissionError("MEMORY_FORGET_TOMBSTONE")
            if expected_revision is not None and prior.get("revision", 0) != expected_revision:
                raise RuntimeError("MEMORY_REVISION_CONFLICT")
            revision = int(prior.get("revision", 0)) + 1
            record.metadata = {**record.metadata, "truth_kind": "derived_memory"}
            data = {"schema_version": 1, "revision": revision, "binding": binding,
                    "state": "forgotten" if forgotten else "active", "record": record.to_dict()}
            raw = json.dumps(data, ensure_ascii=False, allow_nan=False)
            if len(raw.encode("utf-8")) > 8 * 1024 * 1024:
                raise ValueError("MEMORY_CONTENT_TOO_LARGE")
            stage = "archived" if forgotten else "raw"
            if old:
                changed = conn.execute("UPDATE agent_learning_records SET content_json=?,lifecycle_stage=? WHERE record_id=? AND content_json=?",
                    (raw, stage, identity, old[0])).rowcount
                if changed != 1:
                    raise RuntimeError("MEMORY_REVISION_CONFLICT")
            else:
                conn.execute("INSERT INTO agent_learning_records(record_id,learning_type,source,content_json,confidence,lifecycle_stage,related_task_id,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (identity, "derived_memory_" + self.LAYER_NAME, "agent_runtime_derived", raw, 0.0, stage, binding["task_id"], record.timestamp))
            self._binding_context(conn, write=True)
            conn.commit()
            self._in_memory.clear()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── 公共接口（Feature Flag + TTL 守卫） ──────────────────────

    def store(self, key: str, value: Dict[str, Any],
              metadata: Optional[Dict[str, Any]] = None,
              ttl_seconds: float = 0.0,
              source: str = "agent_runtime") -> Optional[MemoryRecord]:
        if not self.enabled:
            return None
        record = MemoryRecord(
            layer=self.LAYER_NAME, key=key, value=value,
            metadata=metadata or {}, ttl_seconds=ttl_seconds, source=source,
        )
        ok = self._store(record)
        return record if ok else None

    def retrieve(self, key: str) -> Optional[MemoryRecord]:
        if not self.enabled:
            return None
        rec = self._retrieve(key)
        if rec and rec.is_expired():
            if self._task_binding is None:
                self._forget(key)
            return None
        return rec

    def query(self, filters: Optional[Dict[str, Any]] = None,
              limit: int = 50) -> List[MemoryRecord]:
        if not self.enabled:
            return []
        now = time.time()
        # Apply TTL before limiting so newer short-lived records cannot hide
        # older still-valid records from API/Agent callers. Pass one clock
        # reading through both layers so an expiry-boundary query is stable.
        # Keep the long-standing subclass hook signature. Scope-aware owners
        # can wrap `_query(filters, limit)` and call `super()`; the base hook
        # reads this context-local clock without requiring those owners to
        # change their method signature.
        query_time_token = _MEMORY_QUERY_TIME.set(now)
        try:
            results = self._query(filters or {}, limit)
        finally:
            _MEMORY_QUERY_TIME.reset(query_time_token)
        return [r for r in results if not r.is_expired(now)][:limit]

    def forget(self, key: str) -> bool:
        if not self.enabled:
            return False
        return self._forget(key)

    def correct(self, key, value, *, expected_revision):
        if not self.enabled or self._task_binding is None:
            raise PermissionError("MEMORY_TASK_BINDING_REQUIRED")
        if type(key) is not str or not key.strip() or len(key) > 256 or type(value) is not dict:
            raise ValueError("MEMORY_CORRECTION_INVALID")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("MEMORY_REVISION_REQUIRED")
        # A correction is an explicit user-authored context input. Never let a
        # secret-shaped value or sensitive field become eligible for Gateway
        # consumption; redaction here would silently change the user's text.
        from agent_runtime.durable_adapter import _sanitize_checkpoint_value
        _safe_value, sensitive = _sanitize_checkpoint_value(value)
        if sensitive:
            raise ValueError("MEMORY_SENSITIVE_CONTENT_REJECTED")
        record = MemoryRecord(layer=self.LAYER_NAME, key=key, value=value,
                              metadata={"type": "user_correction"})
        self._write_derived(record, expected_revision=expected_revision)
        return self.retrieve(key)

    def forget_revision(self, key, *, expected_revision):
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValueError("MEMORY_REVISION_REQUIRED")
        record = self.retrieve(key)
        if record is None:
            return False
        return self._write_derived(record, forgotten=True, expected_revision=expected_revision)

    def forget_expired(self) -> int:
        """清理过期记忆，返回清理数量。"""
        if not self.enabled:
            return 0
        now = time.time()
        expired = [k for k, r in self._in_memory.items() if r.is_expired(now)]
        for k in expired:
            self._in_memory.pop(k, None)
        return len(expired)

    def stats(self) -> Dict[str, Any]:
        return {
            "layer": self.LAYER_NAME,
            "enabled": self.enabled,
            "in_memory_count": len(self._in_memory),
        }

    # ── 子类实现 ─────────────────────────────────────────────────

    def _store(self, record: MemoryRecord) -> bool:
        if self._task_binding is not None:
            return self._write_derived(record)
        self._in_memory[record.key] = record
        return True

    def _retrieve(self, key: str) -> Optional[MemoryRecord]:
        if self._task_binding is not None:
            return next((r for r in self._derived_rows() if r.key == key), None)
        return self._in_memory.get(key)

    def _query(self, filters: Dict[str, Any], limit: int,
               *, valid_at: Optional[float] = None) -> List[MemoryRecord]:
        results = []
        records = self._derived_rows() if self._task_binding is not None else self._in_memory.values()
        query_time = _MEMORY_QUERY_TIME.get() if valid_at is None else valid_at
        now = time.time() if query_time is None else query_time
        for rec in records:
            if rec.is_expired(now):
                continue
            match = True
            for fk, fv in filters.items():
                if fk == "keyword":
                    text = json.dumps(rec.value, ensure_ascii=False).lower()
                    if str(fv).lower() not in text:
                        match = False
                        break
                elif fk == "source":
                    if rec.source != fv:
                        match = False
                        break
                else:
                    if fk not in rec.metadata or rec.metadata[fk] != fv:
                        match = False
                        break
            if match:
                results.append(rec)
        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[:limit]

    def _forget(self, key: str) -> bool:
        if self._task_binding is not None:
            record = self._retrieve(key)
            return self._write_derived(record, forgotten=True) if record else False
        return self._in_memory.pop(key, None) is not None


def get_db_connection(db_path: str):
    """获取 SQLite 连接（只读模式优先，写入时用普通连接）。"""
    import sqlite3
    from lumenis.shared.database import DatabaseRepository
    conn = DatabaseRepository(db_path).connect()
    conn.row_factory = sqlite3.Row
    return conn


def read_task_user_correction_context(db_path, task_id, actor_id, *,
                                      maximum_records=100, maximum_bytes=262144):
    """Read only explicit, active human corrections for this exact task.

    The returned payload is a derivative of the existing Memory owner. It is
    not Source/Evidence, Canonical fact, permission, training consent, or a
    cross-task preference store. Over-capacity context is represented honestly
    and is never partially included.
    """
    if (type(task_id) is not str or not task_id
            or actor_id is not None and type(actor_id) is not int
            or type(maximum_records) is not int or not 1 <= maximum_records <= 500
            or type(maximum_bytes) is not int or not 1024 <= maximum_bytes <= 2 * 1024 * 1024):
        raise ValueError("MEMORY_CONTEXT_PARAMETERS_INVALID")
    from .episodic import EpisodicMemory
    from .semantic import SemanticMemory
    from .task import TaskMemory

    records = []
    binding = None
    query_time = time.time()
    for layer, memory_type in (("episodic", EpisodicMemory),
                               ("semantic", SemanticMemory),
                               ("task", TaskMemory)):
        memory = memory_type(db_path=db_path, enabled=True).bind_task(task_id, actor_id)
        current_binding = memory._binding_context()
        if binding is None:
            binding = current_binding
        elif current_binding != binding:
            raise PermissionError("MEMORY_CONTEXT_BINDING_CHANGED")
        for record in active_user_correction_records(memory._derived_rows(), now=query_time):
            if (type(record.key) is not str or not record.key.strip()
                    or type(record.value) is not dict
                    or type(record.metadata.get("memory_revision")) is not int
                    or record.metadata["memory_revision"] < 1
                    or type(record.timestamp) is not str):
                return _memory_context_envelope(binding, [], state="INVALID_RECORD_BLOCKED",
                    record_count=len(records) + 1)
            from agent_runtime.durable_adapter import _sanitize_checkpoint_value
            _safe, sensitive = _sanitize_checkpoint_value(record.value)
            if sensitive:
                return _memory_context_envelope(binding, [], state="SENSITIVE_CONTENT_BLOCKED",
                    record_count=len(records) + 1)
            records.append({
                "layer": layer,
                "key": record.key,
                "revision": record.metadata.get("memory_revision"),
                "timestamp": record.timestamp,
                "value": record.value,
                "truth_kind": "user_authored_unverified_correction",
            })

    records = order_user_correction_context(records)
    return _memory_context_envelope(binding, records, maximum_records=maximum_records,
                                    maximum_bytes=maximum_bytes)


def active_user_correction_records(records, *, now=None):
    """Return only active, non-expired human corrections for prompt context.

    ``BaseMemoryLayer.query`` already filters TTL before applying its limit, but
    the task-bound Gateway context reader walks the layer's raw derived rows so
    it can validate the complete correction set and snapshot it atomically.
    Apply the same expiry rule here; otherwise an explicitly short-lived
    correction could remain in a resumed Agent task after its TTL elapsed.
    """
    if type(records) is not list:
        raise ValueError("MEMORY_CONTEXT_RECORDS_INVALID")
    query_time = time.time() if now is None else now
    if type(query_time) not in (int, float):
        raise ValueError("MEMORY_CONTEXT_TIME_INVALID")
    return [record for record in records
            if record.metadata.get("type") == "user_correction"
            and not record.is_expired(query_time)]


def order_user_correction_context(records):
    """Order current user corrections newest first using absolute timestamps."""
    if type(records) is not list:
        raise ValueError("MEMORY_CONTEXT_RECORDS_INVALID")

    def key(record):
        try:
            created_at = datetime.fromisoformat(record["timestamp"])
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            return (created_at.timestamp(), record["layer"], record["key"])
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError("MEMORY_CONTEXT_TIMESTAMP_INVALID") from exc

    return sorted(records, key=key, reverse=True)


def _memory_context_envelope(binding, records, *, state=None, record_count=None,
                             maximum_records=100,
                             maximum_bytes=262144):
    import hashlib
    encoded = json.dumps(records, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode()
    capacity_exceeded = len(records) > maximum_records or len(encoded) > maximum_bytes
    result_state = state or ("CAPACITY_EXCEEDED" if capacity_exceeded else
                             "AVAILABLE" if records else "EMPTY")
    result_count = len(records) if record_count is None else record_count
    raw_snapshot = {"binding": binding, "state": result_state,
                    "record_count": result_count, "records": records}
    snapshot_sha256 = hashlib.sha256(json.dumps(raw_snapshot, ensure_ascii=False,
        sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    if state is not None:
        return {"schema": "task-user-corrections/v1", "state": state,
                "record_count": result_count, "records": [],
                "snapshot_sha256": snapshot_sha256,
                "source_policy": "same_task_explicit_user_corrections_only"}
    if capacity_exceeded:
        return {"schema": "task-user-corrections/v1", "state": result_state,
                "record_count": result_count, "records": [],
                "snapshot_sha256": snapshot_sha256,
                "omission": "complete_human_context_exceeds_bound_no_partial_inclusion",
                "source_policy": "same_task_explicit_user_corrections_only"}
    return {"schema": "task-user-corrections/v1",
            "state": result_state, "record_count": result_count, "records": records,
            "snapshot_sha256": snapshot_sha256,
            "source_policy": "same_task_explicit_user_corrections_only"}
