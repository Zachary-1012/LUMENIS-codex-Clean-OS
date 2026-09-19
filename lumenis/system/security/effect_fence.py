# -*- coding: utf-8 -*-
"""LUMENIS SYSTEM canonical Effect Fence and side-effect idempotency.

The fence is the last deterministic boundary before a handler may create an
external or persistent side effect. It never promotes Agent/AI output directly
into Production Truth.
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .action_firewall import AgentAction


_PRODUCTION_TARGETS = (
    "production_db", "prod_db", "master_db", "生产库", "主库",
    "production_truth", "canonical_data", "zbc_canonical_data",
)
_MUTATING = {
    AgentAction.WRITE, AgentAction.COMMIT, AgentAction.PUSH, AgentAction.DEPLOY,
}


@dataclass
class FenceDecision:
    allowed: bool
    action: str
    fenced: bool
    reason: str
    target: str = ""
    effect_mode: str = "read_only"
    requires_staging: bool = False
    requires_manual_validation: bool = False
    auto_admit: bool = False
    idempotency_key: Optional[str] = None
    idempotent_hit: bool = False
    reservation_status: str = "none"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EffectFence:
    """Single owner for side-effect admission and idempotency reservations."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reservations: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _digest(action: AgentAction, target: str, payload: Dict[str, Any]) -> str:
        body = json.dumps(
            {"action": action.value, "target": target, "payload": payload},
            ensure_ascii=False, sort_keys=True, default=str,
        )
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_staging(payload: Dict[str, Any]) -> bool:
        mode = str(
            payload.get("effect_mode")
            or payload.get("stage")
            or payload.get("environment")
            or ""
        ).strip().lower()
        return bool(payload.get("staging") is True or mode in {"staging", "preview", "dry_run", "dry-run"})

    def check(
        self,
        *,
        action: AgentAction,
        target: str = "",
        payload: Optional[Dict[str, Any]] = None,
        operation_id: Optional[str] = None,
    ) -> FenceDecision:
        payload = dict(payload or {})
        target_text = str(target or "")
        lower_target = target_text.lower()

        if action not in _MUTATING:
            return FenceDecision(
                allowed=True,
                action=action.value,
                fenced=True,
                reason="non-mutating action passed Effect Fence",
                target=target_text,
                effect_mode="read_only",
                reservation_status="not_required",
            )

        if any(marker in lower_target for marker in _PRODUCTION_TARGETS):
            return FenceDecision(
                allowed=False,
                action=action.value,
                fenced=True,
                reason="direct mutation of Production Truth is hard-denied",
                target=target_text,
                effect_mode="blocked",
                requires_staging=True,
                requires_manual_validation=True,
                reservation_status="rejected",
            )

        if not self._is_staging(payload):
            return FenceDecision(
                allowed=False,
                action=action.value,
                fenced=True,
                reason="mutating action requires explicit staging/dry-run effect mode before execution",
                target=target_text,
                effect_mode="blocked",
                requires_staging=True,
                requires_manual_validation=True,
                reservation_status="rejected",
            )

        digest = self._digest(action, target_text, payload)
        key = str(operation_id or digest)
        with self._lock:
            existing = self._reservations.get(key)
            if existing is not None:
                if existing["digest"] != digest:
                    return FenceDecision(
                        allowed=False,
                        action=action.value,
                        fenced=True,
                        reason="idempotency key collision with different side-effect payload",
                        target=target_text,
                        effect_mode="staging",
                        requires_staging=True,
                        requires_manual_validation=True,
                        idempotency_key=key,
                        idempotent_hit=True,
                        reservation_status="conflict",
                    )
                return FenceDecision(
                    allowed=False,
                    action=action.value,
                    fenced=True,
                    reason="duplicate side-effect request blocked by idempotency reservation",
                    target=target_text,
                    effect_mode="staging",
                    requires_staging=True,
                    requires_manual_validation=True,
                    idempotency_key=key,
                    idempotent_hit=True,
                    reservation_status=existing.get("status", "reserved"),
                )

            self._reservations[key] = {
                "digest": digest,
                "status": "reserved",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        return FenceDecision(
            allowed=True,
            action=action.value,
            fenced=True,
            reason="staging side effect reserved; Production Truth admission remains manual",
            target=target_text,
            effect_mode="staging",
            requires_staging=True,
            requires_manual_validation=True,
            auto_admit=False,
            idempotency_key=key,
            reservation_status="reserved",
        )

    def complete(self, idempotency_key: Optional[str], *, success: bool) -> None:
        if not idempotency_key:
            return
        with self._lock:
            item = self._reservations.get(idempotency_key)
            if item is None:
                return
            item["status"] = "completed" if success else "failed"
            item["finished_at"] = datetime.now(timezone.utc).isoformat()

    def clear_for_testing(self) -> None:
        with self._lock:
            self._reservations.clear()


_default_fence = EffectFence()


def get_effect_fence() -> EffectFence:
    return _default_fence


__all__ = ["FenceDecision", "EffectFence", "get_effect_fence"]
