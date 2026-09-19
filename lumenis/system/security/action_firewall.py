# -*- coding: utf-8 -*-
"""LUMENIS SYSTEM canonical Action Firewall.

This module owns deterministic action-level validation. Permission is decided
only by :mod:`lumenis.system.security.permission`; the firewall consumes the
permission result and never creates a second role/approval authority.

Production write chain:
Task -> Permission -> Action Firewall -> Effect Fence / Idempotency
     -> Execute -> Evidence -> Evaluation -> Trace
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from .permission import PermissionResult


class AgentAction(str, Enum):
    READ = "READ"
    ANALYZE = "ANALYZE"
    SUGGEST = "SUGGEST"
    EXPORT = "EXPORT"
    WRITE = "WRITE"
    COMMIT = "COMMIT"
    PUSH = "PUSH"
    DEPLOY = "DEPLOY"


class FirewallRisk(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


_ACTION_POLICY: Dict[AgentAction, str] = {
    AgentAction.READ: "ALLOW",
    AgentAction.ANALYZE: "ALLOW",
    AgentAction.SUGGEST: "ALLOW",
    AgentAction.EXPORT: "CONDITIONAL",
    AgentAction.WRITE: "RESTRICTED",
    AgentAction.COMMIT: "DENY",
    AgentAction.PUSH: "DENY",
    AgentAction.DEPLOY: "APPROVAL_REQUIRED",
}

_HIGH_RISK_TARGETS = (
    "production_db", "prod_db", "master_db", "production_truth",
    "canonical_data", "git_remote", "origin", "system_config",
    "critical_config", "credentials", "secrets", "keys",
)
_PROD_TARGET_PATTERNS = (
    "production_db", "prod_db", "master_db", "生产库", "主库",
    "production_truth", "canonical_data",
)
_SENSITIVE_PARAMS = {
    "password", "token", "api_key", "secret", "cookie", "session",
    "private_key", "credential",
}
_VALID_SCOPES = {"global", "bmp", "zbmp", "cth", "system", "user", "shared"}


@dataclass
class ActionRequest:
    identity: str = ""
    intent: str = ""
    tool: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    target: str = ""
    scope: str = "global"
    action: AgentAction = AgentAction.READ


@dataclass
class FirewallResult:
    allowed: bool
    action: str
    decision: str
    reason: str
    risk_level: str
    checks: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    requires_effect_fence: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "decision": self.decision,
            "reason": self.reason,
            "risk_level": self.risk_level,
            "checks": self.checks,
            "requires_approval": self.requires_approval,
            "requires_effect_fence": self.requires_effect_fence,
        }


def _deny(req: ActionRequest, decision: str, reason: str, risk: FirewallRisk,
          checks: Dict[str, Any], *, approval: bool = False,
          fence: bool = False) -> FirewallResult:
    return FirewallResult(
        False, req.action.value, decision, reason, risk.value, checks,
        requires_approval=approval, requires_effect_fence=fence,
    )


def _structural_checks(req: ActionRequest) -> tuple[bool, str, FirewallRisk, Dict[str, Any]]:
    checks: Dict[str, Any] = {}

    ok = bool(req.identity and req.identity.strip())
    checks["identity"] = {"passed": ok}
    if not ok:
        return False, "identity is required", FirewallRisk.HIGH, checks

    ok = bool(req.intent and req.intent.strip()) and len(req.intent) <= 2000
    checks["intent"] = {"passed": ok}
    if not ok:
        return False, "intent is required and must be <= 2000 chars", FirewallRisk.HIGH, checks

    ok = bool(req.tool and req.tool.strip())
    checks["tool"] = {"passed": ok}
    if not ok:
        return False, "tool is required", FirewallRisk.HIGH, checks

    if not isinstance(req.parameters, dict):
        checks["parameters"] = {"passed": False}
        return False, "parameters must be a dict", FirewallRisk.HIGH, checks
    sensitive = sorted(k for k in req.parameters if str(k).lower() in _SENSITIVE_PARAMS)
    ok = not sensitive
    checks["parameters"] = {"passed": ok, "sensitive_keys": sensitive}
    if not ok:
        return False, "sensitive parameters are not allowed through the action boundary", FirewallRisk.CRITICAL, checks

    scope = str(req.scope or "global").lower()
    ok = scope in _VALID_SCOPES
    checks["scope"] = {"passed": ok, "scope": scope}
    if not ok:
        return False, f"invalid scope: {req.scope}", FirewallRisk.HIGH, checks

    target = str(req.target or "").lower()
    mutating = req.action in {
        AgentAction.WRITE, AgentAction.COMMIT, AgentAction.PUSH, AgentAction.DEPLOY,
    }
    if mutating and any(p in target for p in _PROD_TARGET_PATTERNS):
        checks["target"] = {"passed": False, "target": req.target, "production_truth": True}
        return (
            False,
            "direct mutation of Production Truth is hard-denied; route through Effect Fence and governed admission",
            FirewallRisk.CRITICAL,
            checks,
        )

    risk = FirewallRisk.LOW
    if any(p in target for p in _HIGH_RISK_TARGETS):
        risk = FirewallRisk.HIGH
    if req.action in {AgentAction.COMMIT, AgentAction.PUSH}:
        risk = FirewallRisk.CRITICAL
    elif req.action == AgentAction.DEPLOY:
        risk = FirewallRisk.HIGH
    elif req.action == AgentAction.WRITE and risk == FirewallRisk.LOW:
        risk = FirewallRisk.MEDIUM
    checks["target"] = {"passed": True, "target": req.target, "risk": risk.value}
    return True, "OK", risk, checks


def validate_action(
    req: ActionRequest,
    *,
    permission_result: Optional[PermissionResult] = None,
    extra_policy: Optional[Dict[AgentAction, str]] = None,
) -> FirewallResult:
    """Validate one action without owning permission state.

    If a PermissionResult is supplied it must be allowed. Callers in the
    production execution chain MUST supply it. Standalone structural audits may
    omit it; the result then records permission as unverified rather than
    silently inventing permission.
    """
    ok, reason, risk, checks = _structural_checks(req)
    if not ok:
        return _deny(req, "DENY", reason, risk, checks)

    if permission_result is None:
        checks["permission"] = {"verified": False}
    else:
        checks["permission"] = {
            "verified": True,
            "allowed": bool(permission_result.allowed),
            "audit_id": permission_result.audit_id,
            "operation_id": permission_result.operation_id,
        }
        if not permission_result.allowed:
            return _deny(
                req, "DENY", "canonical Permission denied the action",
                risk, checks, approval=bool(permission_result.requires_approval),
            )

    policy = dict(_ACTION_POLICY)
    if extra_policy:
        policy.update(extra_policy)
    decision = policy.get(req.action, "DENY")
    checks["action_policy"] = {"decision": decision}

    if decision == "ALLOW":
        return FirewallResult(True, req.action.value, "ALLOW", "action permitted",
                              risk.value, checks)
    if decision == "CONDITIONAL":
        return FirewallResult(
            True, req.action.value, "CONDITIONAL_PASS",
            "export passed deterministic sensitive-data checks",
            risk.value, checks,
        )
    if decision == "RESTRICTED":
        return FirewallResult(
            True, req.action.value, "RESTRICTED",
            "mutation may proceed only through canonical Effect Fence",
            risk.value, checks, requires_effect_fence=True,
        )
    if decision == "APPROVAL_REQUIRED":
        approved = bool(permission_result and permission_result.allowed and permission_result.approval_token)
        if approved:
            return FirewallResult(
                True, req.action.value, "APPROVED",
                "canonical Permission carries a valid human approval",
                risk.value, checks, requires_approval=True, requires_effect_fence=True,
            )
        return _deny(
            req, "APPROVAL_REQUIRED",
            f"action {req.action.value} requires canonical human approval",
            risk, checks, approval=True, fence=True,
        )

    return _deny(
        req, "DENY", f"action {req.action.value} is denied by default",
        risk, checks,
    )


__all__ = [
    "AgentAction", "FirewallRisk", "ActionRequest", "FirewallResult",
    "validate_action",
]
