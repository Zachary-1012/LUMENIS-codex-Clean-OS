# -*- coding: utf-8 -*-
"""ZBC Phase 13 - Agent Boundary & Permission Control.

Agent boundary specification: Agents cannot become production super-privilege.
Default permission is READ + AUDIT. High-risk operations require human approval.

Components:
  - AgentIdentity: agent id, role, permission scope, tool allow/deny lists
  - ActionFirewall: intercept high-risk operations (delete_/grant_/drop_/rm_/sudo)
  - ApprovalManager: human approval management
  - IdempotencyGuard: operation idempotency
  - AgentBoundary: facade combining all layers
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class AgentRole(str, Enum):
    READER = "READER"
    AUDITOR = "AUDITOR"
    ANALYST = "ANALYST"
    DEVELOPER = "DEVELOPER"
    OPERATOR = "OPERATOR"
    SUPER_ADMIN = "SUPER_ADMIN"


class Permission(str, Enum):
    READ = "READ"
    AUDIT = "AUDIT"
    ANALYZE = "ANALYZE"
    RESEARCH = "RESEARCH"
    PLAN = "PLAN"
    PATCH_PREVIEW = "PATCH_PREVIEW"
    TEST = "TEST"
    VERIFY = "VERIFY"
    WRITE = "WRITE"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"
    COMMIT = "COMMIT"
    PUSH = "PUSH"


class ActionDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


ROLE_DEFAULT_PERMISSIONS: Dict[AgentRole, Set[Permission]] = {
    AgentRole.READER: {Permission.READ},
    AgentRole.AUDITOR: {Permission.READ, Permission.AUDIT},
    AgentRole.ANALYST: {
        Permission.READ, Permission.AUDIT, Permission.ANALYZE,
        Permission.RESEARCH, Permission.PLAN,
    },
    AgentRole.DEVELOPER: {
        Permission.READ, Permission.AUDIT, Permission.ANALYZE,
        Permission.RESEARCH, Permission.PLAN, Permission.PATCH_PREVIEW,
        Permission.TEST, Permission.VERIFY,
    },
    AgentRole.OPERATOR: {
        Permission.READ, Permission.AUDIT, Permission.VERIFY,
        Permission.TEST,
    },
    AgentRole.SUPER_ADMIN: set(),
}

AGENT_PERMISSION_DENYLIST: Set[Permission] = {
    Permission.COMMIT,
    Permission.PUSH,
    Permission.DELETE,
}

HIGH_RISK_ACTION_PREFIXES: Tuple[str, ...] = (
    "delete_", "drop_", "grant_", "revoke_", "truncate_",
    "rm_", "sudo_", "format_", "mkfs_", "chmod_777",
    "escalate_", "bypass_", "override_", "disable_security",
    "modify_subject", "write_production",
)

HIGH_RISK_PATTERNS = [
    (re.compile(r"\brm\s+-rf\b", re.IGNORECASE), "destructive_remove"),
    (re.compile(r"\bsudo\b", re.IGNORECASE), "privilege_escalation"),
    (re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE), "sql_drop_table"),
    (re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE), "sql_delete"),
    (re.compile(r"\bTRUNCATE\b", re.IGNORECASE), "sql_truncate"),
    (re.compile(r"\bGRANT\s+(ALL|SUPER)\b", re.IGNORECASE), "sql_grant_privilege"),
    (re.compile(r":\(\)\s*\{", re.IGNORECASE), "fork_bomb"),
    (re.compile(r">\s*/dev/sd[a-z]", re.IGNORECASE), "disk_overwrite"),
    (re.compile(r"\bchmod\s+777\b", re.IGNORECASE), "world_writable"),
    (re.compile(r"\b(subject_hit|SUBJECT_WORDS|SUBJECT_EXCLUDE_WORDS)\s*=", re.IGNORECASE),
     "modify_subject_authority"),
]

DEFAULT_TOOL_ALLOWLIST: Set[str] = {
    "search_notes", "get_events", "get_notes", "query_database",
    "get_daily_report", "get_stats", "get_brand_info",
    "analyze_sentiment", "analyze_trend", "generate_report",
    "summarize_content", "classify_content",
    "audit_skill", "audit_agent", "verify_data", "check_health",
    "skill_registry_snapshot", "get_skill_metadata",
    "agent_boundary_audit", "get_agent_identity",
}

DEFAULT_TOOL_DENYLIST: Set[str] = {
    "delete_note", "delete_event", "drop_table", "truncate_table",
    "execute_shell", "run_command", "exec_code", "eval_code",
    "modify_subject_words", "write_production_db", "grant_permission",
    "revoke_permission", "escalate_privilege", "disable_audit",
    "commit_code", "push_code", "merge_branch",
}


@dataclass
class AgentIdentity:
    agent_id: str
    role: AgentRole
    permission_scope: Set[Permission] = field(default_factory=set)
    allowed_tools: Set[str] = field(default_factory=set)
    denied_tools: Set[str] = field(default_factory=set)
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_human: bool = False

    def __post_init__(self) -> None:
        if not self.is_human and self.role == AgentRole.SUPER_ADMIN:
            raise ValueError(
                f"Agent '{self.agent_id}': cannot have SUPER_ADMIN role. "
                f"Super admin is human-only."
            )
        defaults = ROLE_DEFAULT_PERMISSIONS.get(self.role, set())
        self.permission_scope = set(self.permission_scope) | defaults
        if not self.is_human:
            self.permission_scope -= AGENT_PERMISSION_DENYLIST
        self.denied_tools = set(self.denied_tools) | DEFAULT_TOOL_DENYLIST
        if not self.allowed_tools:
            self.allowed_tools = set(DEFAULT_TOOL_ALLOWLIST)
        else:
            self.allowed_tools = set(self.allowed_tools) - self.denied_tools

    def has_permission(self, perm: Permission) -> bool:
        return perm in self.permission_scope

    def can_use_tool(self, tool_name: str) -> bool:
        if tool_name in self.denied_tools:
            return False
        if self.allowed_tools and tool_name not in self.allowed_tools:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["role"] = self.role.value
        d["permission_scope"] = sorted(p.value for p in self.permission_scope)
        d["allowed_tools"] = sorted(self.allowed_tools)
        d["denied_tools"] = sorted(self.denied_tools)
        return d


class ActionFirewall:
    def __init__(
        self,
        *,
        extra_deny_patterns: Optional[List[re.Pattern]] = None,
        extra_allow_tools: Optional[Set[str]] = None,
    ) -> None:
        self._extra_patterns = extra_deny_patterns or []
        self._extra_allow = extra_allow_tools or set()
        self._decision_log: List[Dict[str, Any]] = []

    def check(
        self,
        identity: AgentIdentity,
        action: str,
        *,
        tool_name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        description: str = "",
    ) -> Dict[str, Any]:
        ts = datetime.now(timezone.utc).isoformat()
        action_lower = (action or "").lower()
        desc_text = f"{action} {description} {params or ''}"

        for prefix in HIGH_RISK_ACTION_PREFIXES:
            if action_lower.startswith(prefix) or (tool_name and tool_name.lower().startswith(prefix)):
                return self._decide(
                    ActionDecision.REQUIRE_APPROVAL, identity, action,
                    f"high-risk action prefix '{prefix}' requires human approval",
                    f"prefix:{prefix}", ts,
                )

        for pat, label in HIGH_RISK_PATTERNS:
            if pat.search(desc_text):
                return self._decide(
                    ActionDecision.DENY, identity, action,
                    f"matched high-risk pattern: {label}",
                    f"pattern:{label}", ts,
                )
        for pat in self._extra_patterns:
            if pat.search(desc_text):
                return self._decide(
                    ActionDecision.DENY, identity, action,
                    f"matched extra deny pattern: {pat.pattern}",
                    "extra_pattern", ts,
                )

        if tool_name and tool_name in identity.denied_tools:
            return self._decide(
                ActionDecision.DENY, identity, action,
                f"tool '{tool_name}' is in denied_tools",
                "tool_denylist", ts,
            )

        effective_allow = identity.allowed_tools | self._extra_allow
        if tool_name and effective_allow and tool_name not in effective_allow:
            return self._decide(
                ActionDecision.DENY, identity, action,
                f"tool '{tool_name}' not in allowlist",
                "tool_allowlist", ts,
            )

        if action_lower.startswith(("write_", "create_", "update_", "modify_", "exec_")):
            if not identity.has_permission(Permission.WRITE) and not identity.has_permission(Permission.EXECUTE):
                return self._decide(
                    ActionDecision.DENY, identity, action,
                    f"write/execute action requires WRITE or EXECUTE permission "
                    f"(agent has: {sorted(p.value for p in identity.permission_scope)})",
                    "permission_insufficient", ts,
                )

        return self._decide(
            ActionDecision.ALLOW, identity, action,
            "OK", None, ts,
        )

    def _decide(
        self, decision: ActionDecision, identity: AgentIdentity,
        action: str, reason: str, matched_rule: Optional[str], ts: str,
    ) -> Dict[str, Any]:
        result = {
            "decision": decision.value,
            "reason": reason,
            "action": action,
            "agent_id": identity.agent_id,
            "matched_rule": matched_rule,
            "timestamp": ts,
        }
        self._decision_log.append(result)
        return result

    @property
    def decision_log(self) -> List[Dict[str, Any]]:
        return list(self._decision_log)


@dataclass
class ApprovalRequest:
    request_id: str
    agent_id: str
    action: str
    tool_name: Optional[str]
    reason: str
    params_hash: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    expires_at: str = field(
        default_factory=lambda: (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    )


class ApprovalManager:
    def __init__(self, *, ttl_minutes: int = 30) -> None:
        self._requests: Dict[str, ApprovalRequest] = {}
        self._ttl = ttl_minutes

    def request(
        self,
        identity: AgentIdentity,
        action: str,
        *,
        tool_name: Optional[str] = None,
        reason: str = "",
        params: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        params_str = str(sorted((params or {}).items()))
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:16]
        request_id = hashlib.sha256(
            f"{identity.agent_id}:{action}:{tool_name}:{params_hash}:{time.time()}".encode()
        ).hexdigest()[:16]
        req = ApprovalRequest(
            request_id=request_id,
            agent_id=identity.agent_id,
            action=action,
            tool_name=tool_name,
            reason=reason,
            params_hash=params_hash,
        )
        self._requests[request_id] = req
        return req

    def approve(self, request_id: str, *, approver: str) -> Dict[str, Any]:
        req = self._requests.get(request_id)
        if req is None:
            return {"ok": False, "error": "request not found"}
        if self._is_expired(req):
            req.status = ApprovalStatus.EXPIRED
            return {"ok": False, "error": "request expired"}
        req.status = ApprovalStatus.APPROVED
        req.decided_at = datetime.now(timezone.utc).isoformat()
        req.decided_by = approver
        return {"ok": True, "request_id": request_id, "status": "APPROVED"}

    def reject(self, request_id: str, *, approver: str, reason: str = "") -> Dict[str, Any]:
        req = self._requests.get(request_id)
        if req is None:
            return {"ok": False, "error": "request not found"}
        req.status = ApprovalStatus.REJECTED
        req.decided_at = datetime.now(timezone.utc).isoformat()
        req.decided_by = approver
        return {"ok": True, "request_id": request_id, "status": "REJECTED", "reason": reason}

    def is_approved(self, request_id: str) -> bool:
        req = self._requests.get(request_id)
        if req is None:
            return False
        if self._is_expired(req):
            req.status = ApprovalStatus.EXPIRED
            return False
        return req.status == ApprovalStatus.APPROVED

    def get(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._requests.get(request_id)

    def list_pending(self) -> List[ApprovalRequest]:
        return [
            r for r in self._requests.values()
            if r.status == ApprovalStatus.PENDING and not self._is_expired(r)
        ]

    def _is_expired(self, req: ApprovalRequest) -> bool:
        try:
            exp = datetime.fromisoformat(req.expires_at)
            return datetime.now(timezone.utc) > exp
        except Exception:
            return True


class IdempotencyGuard:
    def __init__(self, *, window_seconds: int = 300) -> None:
        self._seen: Dict[str, float] = {}
        self._window = window_seconds

    def _key(self, agent_id: str, action: str, params: Optional[Dict[str, Any]]) -> str:
        params_str = str(sorted((params or {}).items()))
        return hashlib.sha256(f"{agent_id}:{action}:{params_str}".encode()).hexdigest()[:16]

    def check(self, agent_id: str, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        key = self._key(agent_id, action, params)
        now = time.time()
        last = self._seen.get(key)
        if last is not None and (now - last) < self._window:
            return {"duplicate": True, "key": key, "last_seen": last}
        self._seen[key] = now
        return {"duplicate": False, "key": key, "last_seen": last}

    def cleanup(self) -> int:
        now = time.time()
        expired = [k for k, t in self._seen.items() if (now - t) >= self._window]
        for k in expired:
            del self._seen[k]
        return len(expired)


class AgentBoundary:
    def __init__(self) -> None:
        self.firewall = ActionFirewall()
        self.approvals = ApprovalManager()
        self.idempotency = IdempotencyGuard()
        self._identities: Dict[str, AgentIdentity] = {}

    def create_agent(
        self,
        agent_id: str,
        role: AgentRole = AgentRole.AUDITOR,
        *,
        extra_permissions: Optional[Set[Permission]] = None,
        extra_allowed_tools: Optional[Set[str]] = None,
        description: str = "",
    ) -> AgentIdentity:
        if role == AgentRole.SUPER_ADMIN:
            raise ValueError(
                f"Cannot create agent '{agent_id}' with SUPER_ADMIN role. "
                f"Super admin is human-only."
            )
        identity = AgentIdentity(
            agent_id=agent_id,
            role=role,
            permission_scope=extra_permissions or set(),
            allowed_tools=set(DEFAULT_TOOL_ALLOWLIST) | (extra_allowed_tools or set()),
            description=description,
            is_human=False,
        )
        self._identities[agent_id] = identity
        return identity

    def create_human(
        self,
        agent_id: str,
        role: AgentRole = AgentRole.SUPER_ADMIN,
        *,
        description: str = "human operator",
    ) -> AgentIdentity:
        identity = AgentIdentity(
            agent_id=agent_id, role=role, description=description, is_human=True,
        )
        self._identities[agent_id] = identity
        return identity

    def get_identity(self, agent_id: str) -> Optional[AgentIdentity]:
        return self._identities.get(agent_id)

    def check_action(
        self,
        identity: AgentIdentity,
        action: str,
        *,
        tool_name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        description: str = "",
    ) -> Dict[str, Any]:
        idem = self.idempotency.check(identity.agent_id, action, params)
        if idem["duplicate"]:
            return {
                "decision": ActionDecision.DENY.value,
                "reason": f"duplicate operation within {self.idempotency._window}s window",
                "action": action,
                "agent_id": identity.agent_id,
                "matched_rule": "idempotency",
                "idempotency_key": idem["key"],
            }
        fw = self.firewall.check(
            identity, action, tool_name=tool_name, params=params, description=description,
        )
        fw["idempotency_key"] = idem["key"]
        return fw

    def request_approval(
        self,
        identity: AgentIdentity,
        action: str,
        *,
        tool_name: Optional[str] = None,
        reason: str = "",
        params: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        return self.approvals.request(
            identity, action, tool_name=tool_name, reason=reason, params=params,
        )

    def execute_with_approval(
        self,
        identity: AgentIdentity,
        action: str,
        executor: Callable[[], Any],
        *,
        tool_name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        approval_request_id: Optional[str] = None,
        description: str = "",
    ) -> Dict[str, Any]:
        check = self.check_action(
            identity, action, tool_name=tool_name, params=params, description=description,
        )
        if check["decision"] == ActionDecision.DENY.value:
            return {"executed": False, "reason": check["reason"], "check": check}
        if check["decision"] == ActionDecision.REQUIRE_APPROVAL.value:
            if not approval_request_id or not self.approvals.is_approved(approval_request_id):
                return {
                    "executed": False,
                    "reason": "requires human approval (none provided or not approved)",
                    "check": check,
                }
        try:
            result = executor()
            return {"executed": True, "result": result, "check": check}
        except Exception as e:
            return {"executed": False, "reason": f"executor error: {type(e).__name__}: {e}",
                    "check": check}

    def stats(self) -> Dict[str, Any]:
        return {
            "agents_registered": len(
                [i for i in self._identities.values() if not i.is_human]
            ),
            "humans_registered": len(
                [i for i in self._identities.values() if i.is_human]
            ),
            "pending_approvals": len(self.approvals.list_pending()),
            "firewall_decisions_logged": len(self.firewall.decision_log),
        }


_global_boundary: Optional[AgentBoundary] = None


def get_agent_boundary() -> AgentBoundary:
    global _global_boundary
    if _global_boundary is None:
        _global_boundary = AgentBoundary()
    return _global_boundary


if __name__ == "__main__":
    import json
    boundary = get_agent_boundary()
    print("=== AgentBoundary self-check ===")
    agent = boundary.create_agent("test-agent", AgentRole.AUDITOR)
    print(f"Agent: {agent.agent_id}, perms={sorted(p.value for p in agent.permission_scope)}")
    r = boundary.check_action(agent, "search_notes", tool_name="search_notes")
    print(f"search_notes: {r['decision']}")
    r = boundary.check_action(agent, "delete_x", tool_name="delete_note")
    print(f"delete_x: {r['decision']} - {r['reason'][:50]}")
    print(json.dumps(boundary.stats(), ensure_ascii=False, indent=2))
    print("self-check done")
