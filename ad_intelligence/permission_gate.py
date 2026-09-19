# -*- coding: utf-8 -*-
"""Ad Intelligence permission adapter.

Ad Intelligence keeps a domain-facing READ/ANALYZE/PREVIEW/EXECUTE interface,
but it does not own permission state or human approvals. Final authorization is
always delegated to the canonical SYSTEM Permission owner.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
import logging
import os
from typing import Any, Callable, Optional

from lumenis.system.security import (
    OperationType,
    PermissionGate,
    get_permission_gate as get_system_permission_gate,
)

logger = logging.getLogger(__name__)


class AdPermissionLevel(str, Enum):
    READ = "read"
    ANALYZE = "analyze"
    PREVIEW = "preview"
    EXECUTE = "execute"


class AdPermissionGate:
    """Domain adapter over SYSTEM Permission.

    The enabled-level set is only a feature-exposure switch. It never
    authorizes an action by itself. EXECUTE additionally requires the canonical
    AD_EXECUTE decision and canonical human approval token.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        *,
        system_gate: Optional[PermissionGate] = None,
    ):
        self._enabled_levels = {AdPermissionLevel.READ, AdPermissionLevel.ANALYZE}
        self._operation_log = []
        self._system_gate = system_gate or get_system_permission_gate()
        self._approval_token: Optional[str] = None
        self._load_config(config_path)

    def _load_config(self, config_path: Optional[str]):
        env_level = os.environ.get("AD_PERMISSION_LEVEL")
        if not env_level:
            return
        level_map = {
            "read": {AdPermissionLevel.READ},
            "analyze": {AdPermissionLevel.READ, AdPermissionLevel.ANALYZE},
            "preview": {
                AdPermissionLevel.READ, AdPermissionLevel.ANALYZE,
                AdPermissionLevel.PREVIEW,
            },
            "execute": set(AdPermissionLevel),
        }
        if env_level.lower() in level_map:
            self._enabled_levels = level_map[env_level.lower()]

    @staticmethod
    def _operation_type(level: AdPermissionLevel) -> OperationType:
        return {
            AdPermissionLevel.READ: OperationType.AI_CALL,
            AdPermissionLevel.ANALYZE: OperationType.AI_CALL,
            AdPermissionLevel.PREVIEW: OperationType.AD_PREVIEW,
            AdPermissionLevel.EXECUTE: OperationType.AD_EXECUTE,
        }[level]

    def has_permission(self, level: AdPermissionLevel) -> bool:
        return level in self._enabled_levels

    def enable_level(self, level: AdPermissionLevel) -> None:
        self._enabled_levels.add(level)

    def disable_level(self, level: AdPermissionLevel) -> None:
        self._enabled_levels.discard(level)

    def require(
        self,
        level: AdPermissionLevel,
        operation: str = "",
        *,
        resource: Optional[str] = None,
        operation_id: Optional[str] = None,
    ) -> bool:
        if not self.has_permission(level):
            logger.warning("[AdPermissionGate] feature level disabled: %s - %s", level.value, operation)
            return False

        result = self._system_gate.check(
            self._operation_type(level),
            resource=resource or f"ad:{operation or level.value}",
            caller="ad_intelligence",
            operation_id=operation_id,
            domain_id="zbmp",
        )
        if not result.allowed:
            logger.warning("[AdPermissionGate] SYSTEM Permission denied: %s", result.reason)
        return bool(result.allowed)

    def grant_human_approval(self, duration_minutes: int = 30) -> str:
        token = self._system_gate.grant_approval(
            OperationType.AD_EXECUTE.value,
            duration_minutes=duration_minutes,
            granted_by="human:ad_intelligence",
        )
        self._approval_token = token
        return token

    def revoke_human_approval(self) -> None:
        if self._approval_token:
            self._system_gate.revoke_approval(self._approval_token)
        self._approval_token = None

    def _check_approval_expiry(self) -> None:
        if self._approval_token and not self._system_gate.is_approved(OperationType.AD_EXECUTE.value):
            self._approval_token = None

    def log_operation(
        self,
        level: AdPermissionLevel,
        operation: str,
        details: dict,
        success: bool,
    ):
        self._check_approval_expiry()
        self._operation_log.append({
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "operation": operation,
            "details": details,
            "success": success,
            "permission_owner": "lumenis.system.security.permission",
        })
        logger.info("[AdPermissionGate] operation audit: %s success=%s", operation, success)

    def execute_with_gate(
        self,
        level: AdPermissionLevel,
        operation: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> tuple[bool, Any]:
        if not self.require(level, operation):
            return False, f"权限不足: 需要 {level.value} 级别"
        try:
            result = func(*args, **kwargs)
            self.log_operation(level, operation, {"args": str(args), "kwargs": str(kwargs)}, True)
            return True, result
        except Exception as exc:
            self.log_operation(level, operation, {"error": str(exc)}, False)
            return False, str(exc)

    def get_status(self) -> dict:
        self._check_approval_expiry()
        return {
            "enabled_levels": sorted(level.value for level in self._enabled_levels),
            "human_approved": self._system_gate.is_approved(OperationType.AD_EXECUTE.value),
            "operation_count": len(self._operation_log),
            "permission_owner": "lumenis.system.security.permission",
        }


_default_gate: Optional[AdPermissionGate] = None


def get_permission_gate() -> AdPermissionGate:
    global _default_gate
    if _default_gate is None:
        _default_gate = AdPermissionGate()
    return _default_gate
