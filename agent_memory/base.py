# -*- coding: utf-8 -*-
"""分层 Memory 基础接口与数据结构。

与 OSAI memory_lifecycle.py 的 MemoryStore 六层模型通过 Contract 对齐：
  - 统一 store/retrieve/query/forget 接口
  - 记录携带 layer / key / value / timestamp / ttl / metadata
  - 不 import OSAI 代码，仅数据结构对齐
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


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
        if self.ttl_seconds <= 0:
            return False
        now = now or time.time()
        try:
            created = datetime.fromisoformat(self.timestamp).timestamp()
        except Exception:
            return False
        return (now - created) > self.ttl_seconds

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
            actor = {"id": actor_id} if actor_id is not None else resolve_local_workspace_principal(module="skills", action="read")
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
        results = self._query(filters or {}, limit)
        now = time.time()
        return [r for r in results if not r.is_expired(now)][:limit]

    def forget(self, key: str) -> bool:
        if not self.enabled:
            return False
        return self._forget(key)

    def correct(self, key, value, *, expected_revision):
        if not self.enabled or self._task_binding is None:
            raise PermissionError("MEMORY_TASK_BINDING_REQUIRED")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("MEMORY_REVISION_REQUIRED")
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

    def _query(self, filters: Dict[str, Any], limit: int) -> List[MemoryRecord]:
        results = []
        records = self._derived_rows() if self._task_binding is not None else self._in_memory.values()
        for rec in records:
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
