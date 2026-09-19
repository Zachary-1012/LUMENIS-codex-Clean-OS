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
        self._in_memory[record.key] = record
        return True

    def _retrieve(self, key: str) -> Optional[MemoryRecord]:
        return self._in_memory.get(key)

    def _query(self, filters: Dict[str, Any], limit: int) -> List[MemoryRecord]:
        results = []
        for rec in self._in_memory.values():
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
                elif fk in rec.metadata:
                    if rec.metadata[fk] != fv:
                        match = False
                        break
            if match:
                results.append(rec)
        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[:limit]

    def _forget(self, key: str) -> bool:
        return self._in_memory.pop(key, None) is not None


def get_db_connection(db_path: str):
    """获取 SQLite 连接（只读模式优先，写入时用普通连接）。"""
    import sqlite3
    from lumenis.shared.database import DatabaseRepository
    conn = DatabaseRepository(db_path).connect()
    conn.row_factory = sqlite3.Row
    return conn
