# -*- coding: utf-8 -*-
"""P2 基础框架 — Memory 安全治理（只建模型+枚举，不做完整 Memory 引擎）。
六级状态：RAW → OBSERVATION → CANDIDATE → VALIDATED → GENERALIZABLE → ADMITTED
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class MemoryState(str, Enum):
    RAW = "RAW"
    OBSERVATION = "OBSERVATION"
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    GENERALIZABLE = "GENERALIZABLE"
    ADMITTED = "ADMITTED"
    CONFLICT = "CONFLICT"
    REVOKED = "REVOKED"


class MemoryReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVOKED = "revoked"
    EXPIRED = "expired"
    CONFLICT = "conflict"


_MEMORY_TRANSITIONS = {
    MemoryState.RAW: {MemoryState.OBSERVATION, MemoryState.REVOKED},
    MemoryState.OBSERVATION: {MemoryState.CANDIDATE, MemoryState.REVOKED},
    MemoryState.CANDIDATE: {MemoryState.VALIDATED, MemoryState.REVOKED, MemoryState.CONFLICT},
    MemoryState.VALIDATED: {MemoryState.GENERALIZABLE, MemoryState.REVOKED, MemoryState.CONFLICT},
    MemoryState.GENERALIZABLE: {MemoryState.ADMITTED, MemoryState.REVOKED, MemoryState.CONFLICT},
    MemoryState.ADMITTED: {MemoryState.REVOKED, MemoryState.CONFLICT},
    MemoryState.CONFLICT: {MemoryState.CANDIDATE, MemoryState.REVOKED},
    MemoryState.REVOKED: set(),
}


@dataclass
class MemoryRecord:
    memory_id: str
    content: str
    state: MemoryState = MemoryState.RAW
    source: str = ""
    version: str = "1.0.0"
    scope: str = "global"
    domain: str = ""
    confidence: float = 0.0
    review_status: MemoryReviewStatus = MemoryReviewStatus.UNREVIEWED
    reviewer: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    conflict_with: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        d["state"] = self.state.value
        d["review_status"] = self.review_status.value
        return d

    def is_active(self):
        if self.review_status in (MemoryReviewStatus.REVOKED, MemoryReviewStatus.EXPIRED, MemoryReviewStatus.REJECTED):
            return False
        if self.expires_at:
            try:
                exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > exp: return False
            except Exception: pass
        return True

    def can_transition_to(self, target):
        return target in _MEMORY_TRANSITIONS.get(self.state, set())


class MemoryGovernor:
    def __init__(self):
        self._records: Dict[str, MemoryRecord] = {}

    def register(self, record):
        if record.memory_id in self._records:
            return {"success": False, "error": "memory_id already exists"}
        self._records[record.memory_id] = record
        return {"success": True, "memory_id": record.memory_id, "state": record.state.value}

    def transition(self, memory_id, target, reviewer=None):
        rec = self._records.get(memory_id)
        if not rec: return {"success": False, "error": "memory not found"}
        if not rec.can_transition_to(target):
            return {"success": False, "error": f"invalid transition {rec.state.value} -> {target.value}"}
        rec.state = target
        rec.updated_at = datetime.now(timezone.utc).isoformat()
        if reviewer: rec.reviewer = reviewer
        if target == MemoryState.ADMITTED: rec.review_status = MemoryReviewStatus.APPROVED
        return {"success": True, "memory_id": memory_id, "new_state": target.value}

    def revoke(self, memory_id, reason=""):
        rec = self._records.get(memory_id)
        if not rec: return {"success": False, "error": "memory not found"}
        rec.review_status = MemoryReviewStatus.REVOKED
        rec.state = MemoryState.REVOKED
        rec.updated_at = datetime.now(timezone.utc).isoformat()
        rec.metadata["revoke_reason"] = reason
        return {"success": True, "memory_id": memory_id, "status": "revoked"}

    def mark_conflict(self, memory_id, conflict_with):
        rec = self._records.get(memory_id)
        if not rec: return {"success": False, "error": "memory not found"}
        rec.state = MemoryState.CONFLICT
        rec.review_status = MemoryReviewStatus.CONFLICT
        rec.conflict_with = conflict_with
        rec.updated_at = datetime.now(timezone.utc).isoformat()
        return {"success": True, "memory_id": memory_id, "status": "conflict", "conflict_with": conflict_with}

    def get_active(self, scope=None, domain=None):
        results = []
        for rec in self._records.values():
            if not rec.is_active(): continue
            if scope and rec.scope != scope: continue
            if domain and rec.domain != domain: continue
            results.append(rec)
        return results

    def stats(self):
        by_state = {s.value: 0 for s in MemoryState}
        by_review = {r.value: 0 for r in MemoryReviewStatus}
        active = 0
        for rec in self._records.values():
            by_state[rec.state.value] += 1
            by_review[rec.review_status.value] += 1
            if rec.is_active(): active += 1
        return {"total": len(self._records), "active": active, "by_state": by_state, "by_review": by_review}


_governor = None
def get_memory_governor():
    global _governor
    if _governor is None: _governor = MemoryGovernor()
    return _governor
