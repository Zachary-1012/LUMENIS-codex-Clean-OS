# -*- coding: utf-8 -*-
"""P2 基础框架 — Agent Action Firewall（校验函数+测试，不接入所有 Agent）。

校验链：Identity → Intent → Tool → Parameter → Target → Scope → Risk → Permission → Action
策略：READ/ANALYZE/SUGGEST 允许，EXPORT 条件允许，WRITE 受限，
     COMMIT/PUSH 默认拒绝，DEPLOY 人工审批，生产 DB 直写硬拒绝。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class AgentAction(str, Enum):
    READ = "READ"
    ANALYZE = "ANALYZE"
    SUGGEST = "SUGGEST"
    EXPORT = "EXPORT"
    WRITE = "WRITE"
    COMMIT = "COMMIT"
    PUSH = "PUSH"
    DEPLOY = "DEPLOY"


class RiskLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


_DEFAULT_POLICY: Dict[AgentAction, str] = {
    AgentAction.READ: "ALLOW",
    AgentAction.ANALYZE: "ALLOW",
    AgentAction.SUGGEST: "ALLOW",
    AgentAction.EXPORT: "CONDITIONAL",
    AgentAction.WRITE: "RESTRICTED",
    AgentAction.COMMIT: "DENY",
    AgentAction.PUSH: "DENY",
    AgentAction.DEPLOY: "APPROVAL_REQUIRED",
}

_HIGH_RISK_TARGETS = [
    "production_db", "prod_db", "master_db",
    "git_remote", "origin",
    "system_config", "critical_config",
    "credentials", "secrets", "keys",
]

_PROD_DB_PATTERNS = ["production_db", "prod_db", "master_db", "生产库", "主库"]

_SENSITIVE_PARAMS = {"password", "token", "api_key", "secret", "cookie",
                      "session", "private_key", "credential"}


@dataclass
class ActionRequest:
    identity: str = ""
    intent: str = ""
    tool: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    target: str = ""
    scope: str = "global"
    action: AgentAction = AgentAction.READ
    user_role: str = "user"


@dataclass
class FirewallResult:
    allowed: bool
    action: str
    decision: str
    reason: str
    risk_level: str
    checks: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed, "action": self.action, "decision": self.decision,
            "reason": self.reason, "risk_level": self.risk_level,
            "checks": self.checks, "requires_approval": self.requires_approval,
        }


def _check_identity(req):
    if not req.identity or not req.identity.strip():
        return False, "identity is required"
    return True, "OK"

def _check_intent(req):
    if not req.intent or not req.intent.strip():
        return False, "intent is required"
    if len(req.intent) > 2000:
        return False, "intent too long"
    return True, "OK"

def _check_tool(req):
    if not req.tool or not req.tool.strip():
        return False, "tool is required"
    return True, "OK"

def _check_parameters(req):
    if not isinstance(req.parameters, dict):
        return False, "parameters must be a dict"
    for key in req.parameters:
        if key.lower() in _SENSITIVE_PARAMS:
            return False, f"parameter '{key}' contains sensitive data"
    return True, "OK"

def _check_target(req):
    target_lower = req.target.lower()
    risk = RiskLevel.LOW
    is_prod_db = any(p in target_lower for p in _PROD_DB_PATTERNS)
    if is_prod_db and req.action in (AgentAction.WRITE, AgentAction.COMMIT, AgentAction.PUSH, AgentAction.DEPLOY):
        return False, "production DB direct write is hard-denied; must go through Effect Fence + manual validation", RiskLevel.CRITICAL
    for hr in _HIGH_RISK_TARGETS:
        if hr in target_lower:
            risk = RiskLevel.HIGH
            break
    if req.action in (AgentAction.COMMIT, AgentAction.PUSH):
        risk = RiskLevel.CRITICAL
    elif req.action == AgentAction.DEPLOY:
        risk = RiskLevel.HIGH
    elif req.action == AgentAction.WRITE and risk == RiskLevel.LOW:
        risk = RiskLevel.MEDIUM
    return True, "OK", risk

def _check_scope(req):
    valid_scopes = {"global", "zbmp", "cth", "system", "user"}
    if req.scope.lower() not in valid_scopes:
        return False, f"invalid scope: {req.scope}"
    return True, "OK"

def _check_permission(req):
    if req.user_role in ("owner", "admin"):
        return True, "OK"
    if req.action in (AgentAction.READ, AgentAction.ANALYZE, AgentAction.SUGGEST):
        return True, "OK"
    return False, f"role '{req.user_role}' cannot execute {req.action.value}"


def validate_action(req, extra_policy=None):
    checks = {}
    ok, msg = _check_identity(req); checks["identity"] = {"passed": ok, "detail": msg}
    if not ok: return FirewallResult(False, req.action.value, "DENY", msg, "HIGH", checks)
    ok, msg = _check_intent(req); checks["intent"] = {"passed": ok, "detail": msg}
    if not ok: return FirewallResult(False, req.action.value, "DENY", msg, "HIGH", checks)
    ok, msg = _check_tool(req); checks["tool"] = {"passed": ok, "detail": msg}
    if not ok: return FirewallResult(False, req.action.value, "DENY", msg, "HIGH", checks)
    ok, msg = _check_parameters(req); checks["parameters"] = {"passed": ok, "detail": msg}
    if not ok: return FirewallResult(False, req.action.value, "DENY", msg, "CRITICAL", checks)
    ok, msg, risk = _check_target(req); checks["target"] = {"passed": ok, "detail": msg, "risk": risk.value}
    if not ok: return FirewallResult(False, req.action.value, "DENY", msg, risk.value, checks)
    ok, msg = _check_scope(req); checks["scope"] = {"passed": ok, "detail": msg}
    if not ok: return FirewallResult(False, req.action.value, "DENY", msg, risk.value, checks)
    ok, msg = _check_permission(req); checks["permission"] = {"passed": ok, "detail": msg}
    if not ok: return FirewallResult(False, req.action.value, "DENY", msg, risk.value, checks)

    policy = dict(_DEFAULT_POLICY)
    if extra_policy: policy.update(extra_policy)
    decision = policy.get(req.action, "DENY")
    checks["action_policy"] = {"decision": decision}

    if decision == "ALLOW":
        return FirewallResult(True, req.action.value, "ALLOW", "action permitted", risk.value, checks)
    elif decision == "CONDITIONAL":
        has_sensitive = any(k.lower() in _SENSITIVE_PARAMS for k in req.parameters)
        if has_sensitive:
            return FirewallResult(False, req.action.value, "DENY", "export contains sensitive data", "HIGH", checks, requires_approval=True)
        return FirewallResult(True, req.action.value, "CONDITIONAL_PASS", "export without sensitive data", risk.value, checks)
    elif decision == "RESTRICTED":
        return FirewallResult(True, req.action.value, "RESTRICTED", "write allowed only through Effect Fence", risk.value, checks, requires_approval=(risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)))
    elif decision == "APPROVAL_REQUIRED":
        return FirewallResult(False, req.action.value, "APPROVAL_REQUIRED", f"action {req.action.value} requires manual human approval", risk.value, checks, requires_approval=True)
    else:
        return FirewallResult(False, req.action.value, "DENY", f"action {req.action.value} is denied by default", risk.value, checks)


if __name__ == "__main__":
    print("=== Action Firewall self-check ===")
    r1 = validate_action(ActionRequest(identity="a1", intent="read", tool="db", parameters={}, target="local", action=AgentAction.READ, user_role="user"))
    print(f"READ: allowed={r1.allowed}")
    r2 = validate_action(ActionRequest(identity="a1", intent="push", tool="git", parameters={}, target="origin", action=AgentAction.PUSH, user_role="user"))
    print(f"PUSH: allowed={r2.allowed}")
    r3 = validate_action(ActionRequest(identity="owner", intent="deploy", tool="d", parameters={}, target="staging", action=AgentAction.DEPLOY, user_role="owner"))
    print(f"DEPLOY: allowed={r3.allowed}, requires_approval={r3.requires_approval}")
    r4 = validate_action(ActionRequest(identity="owner", intent="write", tool="db", parameters={}, target="production_db", action=AgentAction.WRITE, user_role="owner"))
    print(f"PROD_DB_WRITE: allowed={r4.allowed}")
    print("done")
