# -*- coding: utf-8 -*-
"""LUMENIS — canonical Skill Execution Chain (适配接入，不重写 skill_registry)。
执行链：Task → Permission → Agent → Skill → Tool → Action Firewall
       → Effect Fence / Idempotency → Execute → Evidence → Evaluation → Trace
"""
from __future__ import annotations
import json, traceback, uuid
from dataclasses import dataclass, field, asdict, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class SkillState(str, Enum):
    REGISTERED = "registered"; ENABLED = "enabled"; RUNNING = "running"
    COMPLETED = "completed"; FAILED = "failed"; DISABLED = "disabled"

class ActionType(str, Enum):
    READ = "READ"; ANALYZE = "ANALYZE"; SUGGEST = "SUGGEST"
    EXPORT = "EXPORT"; WRITE = "WRITE"; COMMIT = "COMMIT"; PUSH = "PUSH"

class ExecutionStatus(str, Enum):
    PENDING = "pending"; RUNNING = "running"; COMPLETED = "completed"
    FAILED = "failed"; BLOCKED = "blocked"; REJECTED = "rejected"

_VALID_TRANSITIONS = {
    SkillState.REGISTERED: {SkillState.ENABLED, SkillState.DISABLED},
    SkillState.ENABLED: {SkillState.RUNNING, SkillState.DISABLED},
    SkillState.RUNNING: {SkillState.COMPLETED, SkillState.FAILED, SkillState.DISABLED},
    SkillState.COMPLETED: {SkillState.ENABLED, SkillState.DISABLED},
    SkillState.FAILED: {SkillState.ENABLED, SkillState.DISABLED},
    SkillState.DISABLED: {SkillState.ENABLED},
}


@dataclass
class SkillExecutionContext:
    execution_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    skill_id: str = ""
    user_id: Optional[int] = None
    permission_role: Optional[str] = None
    domain: str = "SYSTEM"
    product: str = "SYSTEM"
    task: str = ""
    input_payload: Dict[str, Any] = field(default_factory=dict)
    # Server-derived upload identity. It is never read from input_payload and
    # is intentionally omitted from serialized execution context.
    content_source_import: Any = field(default=None, repr=False)
    # Opaque server-created domain/focus context carried to the existing handler.
    request_context: Any = field(default=None, repr=False)
    # Sealed server principal for account-free local Content operations.
    workspace_principal: Any = field(default=None, repr=False)
    action_type: ActionType = ActionType.ANALYZE
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    permission_result: Optional[Dict[str, Any]] = None
    firewall_result: Optional[Dict[str, Any]] = None
    effect_fence_result: Optional[Dict[str, Any]] = None
    execute_result: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    evaluation: Optional[Dict[str, Any]] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    error: Optional[str] = None
    def to_dict(self):
        # Exclude opaque server objects before asdict traverses/deep-copies them.
        public_context = replace(
            self, content_source_import=None, request_context=None, workspace_principal=None,
        )
        d = asdict(public_context)
        d["action_type"] = self.action_type.value
        d["status"] = self.status.value
        d.pop("content_source_import", None)
        d.pop("request_context", None)
        d.pop("workspace_principal", None)
        return d

@dataclass
class SkillRuntimeInfo:
    skill_id: str; name: str = ""; description: str = ""
    product: str = "SYSTEM"; domain: str = "global"; version: str = "1.0.0"
    state: SkillState = SkillState.REGISTERED
    enabled: bool = False
    config: Dict[str, Any] = field(default_factory=dict)
    cross_domain_allowed: List[str] = field(default_factory=list)
    source: str = "builtin"
    def to_dict(self):
        d = asdict(self); d["state"] = self.state.value; return d

# ZBC Lifecycle Contract V1.0 (bypass-mode)
try:
    from lifecycle_mixin import LifecycleMixin as _LifecycleMixin
    _LIFECYCLE_AVAILABLE = True
except Exception:
    _LifecycleMixin = None
    _LIFECYCLE_AVAILABLE = False


def _canonical_operation(action_type):
    from lumenis.system.security import OperationType
    mapping = {
        ActionType.READ: OperationType.SKILL_EXECUTE,
        ActionType.ANALYZE: OperationType.SKILL_EXECUTE,
        ActionType.SUGGEST: OperationType.SKILL_EXECUTE,
        ActionType.EXPORT: OperationType.DATA_EXPORT,
        ActionType.WRITE: OperationType.DB_WRITE,
        ActionType.COMMIT: OperationType.CONFIG_MODIFY,
        ActionType.PUSH: OperationType.RUNTIME_OPERATION,
    }
    return mapping[action_type]


def check_permission(ctx, user_role="user", skill_info=None):
    """Skill context checks + canonical SYSTEM Permission decision.

    Skill enablement and product affinity are execution-context facts. Final
    operation authorization is owned only by lumenis.system.security.
    """
    if skill_info and not skill_info.enabled:
        return {"allowed": False, "reason": f"skill '{ctx.skill_id}' is disabled", "code": "SKILL_DISABLED"}
    if skill_info and skill_info.product != "SHARED":
        caller = ctx.product.upper(); sk = skill_info.product.upper()
        if caller != sk and caller != "SYSTEM":
            if caller not in [a.upper() for a in skill_info.cross_domain_allowed]:
                return {"allowed": False, "reason": f"cross-domain denied: caller={caller}, skill={sk}",
                        "code": "CROSS_DOMAIN_DENIED"}

    # Preserve the existing least-privilege role boundary, but do not let it
    # become a second permission authority.
    if user_role not in ("owner", "admin") and ctx.action_type in (
        ActionType.WRITE, ActionType.COMMIT, ActionType.PUSH,
    ):
        low_write_roles = {
            "cth": "cth_operator",
            "bmp": "zbmp_operator",
            "zbmp": "zbmp_operator",
            "system": "system_writer",
        }
        if (
            ctx.action_type is not ActionType.WRITE
            or ctx.permission_role != low_write_roles.get(str(ctx.domain or "").lower())
        ):
            return {"allowed": False, "reason": f"role '{user_role}' cannot execute {ctx.action_type.value}",
                    "code": "INSUFFICIENT_ROLE"}

    if ctx.content_source_import is not None:
        from lumenis.system.security import (
            ContentSourceImport, LocalWorkspacePrincipal, check_content_source_import_permission,
        )

        upload = ctx.content_source_import
        local_import = ctx.workspace_principal is not None
        identity_matches = (
            type(ctx.workspace_principal) is LocalWorkspacePrincipal
            and ctx.user_id is None and type(upload) is ContentSourceImport
            and upload.actor_id is None
            and upload.principal_kind == "local_workspace"
            and upload.principal_ref == "workspace:local"
        ) if local_import else (
            type(ctx.user_id) is int and ctx.user_id > 0
            and type(upload) is ContentSourceImport
            and upload.actor_id == ctx.user_id
        )
        domain_aliases = {"cth": "cth", "bmp": "bmp", "zbmp": "bmp"}
        product_aliases = {"cth": "cth", "bmp": "bmp", "zbmp": "bmp"}
        context_matches = (
            type(upload) is ContentSourceImport
            and ctx.skill_id == "shared.content_project"
            and ctx.action_type is ActionType.WRITE
            and identity_matches
            and domain_aliases.get(str(ctx.domain or "").strip().lower()) == upload.domain_id
            and product_aliases.get(str(ctx.product or "").strip().lower()) == upload.domain_id
            and skill_info is not None
            and skill_info.skill_id == "shared.content_project"
            and skill_info.enabled is True
            and str(skill_info.product or "").upper() == "SHARED"
        )
        if not context_matches:
            return {
                "allowed": False,
                "reason": "content source import execution context does not match its server descriptor",
                "code": "CONTENT_SOURCE_CONTEXT_MISMATCH",
            }
        if local_import:
            decision = check_content_source_import_permission(
                None, upload, principal=ctx.workspace_principal,
            )
        else:
            decision = check_content_source_import_permission({"id": ctx.user_id}, upload)
        payload = decision.to_dict()
        payload["code"] = "PERMISSION_GRANTED" if decision.allowed else (
            "APPROVAL_REQUIRED" if decision.requires_approval else "PERMISSION_DENIED"
        )
        return payload

    if ctx.workspace_principal is not None:
        return {"allowed": False, "reason": "local principal requires an exact Content import",
                "code": "LOCAL_PRINCIPAL_ACTION_UNSUPPORTED"}

    from lumenis.system.security import get_permission_gate
    target = str(ctx.input_payload.get("target") or f"skill:{ctx.skill_id}")
    result = get_permission_gate().check(
        operation_type=_canonical_operation(ctx.action_type),
        resource=target,
        caller=f"skill_executor:{ctx.skill_id}",
        operation_id=ctx.execution_id,
        domain_id=ctx.domain,
        role=ctx.permission_role,
    )
    payload = result.to_dict()
    payload["code"] = "PERMISSION_GRANTED" if result.allowed else (
        "APPROVAL_REQUIRED" if result.requires_approval else "PERMISSION_DENIED"
    )
    return payload


def _check_sensitive_data(payload):
    sensitive = {"password", "token", "api_key", "secret", "cookie", "session", "private_key", "credential", "phone", "id_card"}
    text = json.dumps(payload, ensure_ascii=False).lower()
    return any(k in text for k in sensitive)


def action_firewall(ctx, extra_policy=None):
    """Consume canonical Permission and run the canonical SYSTEM Action Firewall."""
    from lumenis.system.security import (
        ActionRequest, AgentAction, PermissionResult, validate_action,
    )
    target = str(
        (ctx.permission_result or {}).get("resource")
        if ctx.content_source_import is not None
        else (ctx.input_payload.get("target") or f"skill:{ctx.skill_id}")
    )
    req = ActionRequest(
        identity=f"skill_executor:{ctx.execution_id}",
        intent=ctx.task or f"execute skill {ctx.skill_id}",
        tool=f"skill:{ctx.skill_id}",
        parameters=ctx.input_payload,
        target=target,
        scope=ctx.domain,
        action=AgentAction(ctx.action_type.value),
    )
    permission = None
    if ctx.permission_result:
        fields = {
            "allowed", "reason", "requires_approval", "approval_token", "audit_id",
            "operation_type", "resource", "risk_level", "permission_required",
            "caller", "operation_id", "idempotent_hit", "domain_id", "timestamp",
        }
        permission = PermissionResult(**{
            k: v for k, v in ctx.permission_result.items() if k in fields
        })
    result = validate_action(req, permission_result=permission, extra_policy=extra_policy)
    return result.to_dict()


def effect_fence(ctx):
    """Run the canonical Effect Fence; mutating handlers cannot bypass it."""
    from lumenis.system.security import AgentAction, get_effect_fence
    target = str(
        (ctx.permission_result or {}).get("resource")
        if ctx.content_source_import is not None
        else (ctx.input_payload.get("target") or f"skill:{ctx.skill_id}")
    )
    payload = (
        {"staging": True, "content_source_resource": target}
        if ctx.content_source_import is not None
        else ctx.input_payload
    )
    decision = get_effect_fence().check(
        action=AgentAction(ctx.action_type.value),
        target=target,
        payload=payload,
        operation_id=ctx.execution_id,
    )
    return decision.to_dict()


_NON_SUCCESS_RESULT_STATES = frozenset({
    "blocked", "rejected", "denied", "unavailable", "input_required",
    "error", "failed", "failure", "partial", "not_collected",
    "not_available", "pending", "offline", "not_ready", "no_handler",
    "timeout", "cancelled", "canceled",
})
_RESULT_STATE_FIELDS = ("status", "state", "data_state")
_RESULT_METADATA_FIELDS = frozenset({
    "status", "state", "data_state", "ok", "success", "isError", "allowed",
    "error", "errors", "code", "message", "source", "provider", "model",
    "connected", "skill_id", "tool", "tool_name", "tool_definition", "server_info",
    "protocol_version", "transport", "security", "trace", "warnings", "duration_ms",
    "implementation_state", "external_fetch", "provider_call", "production_truth_write",
    "query", "task", "version", "timestamp", "created_at", "updated_at", "type",
})
_RESULT_VALUE_FIELDS = frozenset({
    "result", "output", "osai", "structuredContent", "content", "data", "value",
    "answer", "response", "text", "artifact", "records", "items", "resources",
    "research_assets", "notes", "stats",
})


def _normalized_result_state(value: Any) -> str:
    if isinstance(value, Enum):
        value = value.value
    if not isinstance(value, str):
        return ""
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _has_result_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list, tuple, set)):
        return bool(value)
    return True


def _product_result_is_success(value: Any) -> bool:
    """Accept real output and explicit no-record states, never error-shaped output."""
    if not _has_result_content(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip()
        state = _normalized_result_state(text.split(":", 1)[0])
        return state not in _NON_SUCCESS_RESULT_STATES
    if isinstance(value, (list, tuple, set)):
        return all(_product_result_is_success(item) for item in value)
    if not isinstance(value, dict):
        return True

    for flag in ("ok", "success", "allowed"):
        flag_value = value.get(flag)
        if flag_value is False or (
            isinstance(flag_value, (int, float)) and not isinstance(flag_value, bool)
            and flag_value == 0
        ) or (
            isinstance(flag_value, str)
            and flag_value.strip().lower() in {"false", "no", "0"}
        ):
            return False
    if value.get("isError") is True or value.get("error") or value.get("errors"):
        return False

    states = {
        _normalized_result_state(value.get(field))
        for field in _RESULT_STATE_FIELDS
        if value.get(field) is not None
    }
    if states & _NON_SUCCESS_RESULT_STATES:
        return False

    # A declared no-record outcome is a valid completed read, even when its
    # records list is empty. A status/transport/message-only object is not a
    # business result, even when it claims success.
    explicit_no_records = bool(states & {"no_record", "no_records"})
    business_fields = [
        (key, item) for key, item in value.items()
        if str(key) not in _RESULT_METADATA_FIELDS
    ]
    populated = [
        (key, item) for key, item in business_fields if _has_result_content(item)
    ]
    if not populated:
        return explicit_no_records
    for key, item in populated:
        if key in _RESULT_VALUE_FIELDS or isinstance(item, (dict, list, tuple, set)):
            if not _product_result_is_success(item):
                return False
    return True


def _product_result_error(value: Any) -> str:
    if isinstance(value, dict):
        errors = value.get("errors")
        if isinstance(errors, (list, tuple)):
            messages = [str(item).strip() for item in errors if str(item).strip()]
            if messages:
                return "; ".join(messages)[:240]
        for key in ("error", "code", "message", "status", "state", "data_state"):
            message = value.get(key)
            if isinstance(message, str) and message.strip():
                return message.strip()[:240]
    return "Skill adapter returned a non-success result"


def execute_skill(ctx, handler=None, skill_info=None):
    if handler is not None:
        try:
            result = handler(ctx)
            success = _product_result_is_success(result)
            return {
                "success": success,
                "result": result,
                "source": "custom_handler",
                "error": None if success else _product_result_error(result),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()[-500:], "source": "custom_handler"}
    # Registered MCP Skills use the same execution chain as built-ins.  The
    # adapter is deliberately read-only and fail-closed; the Skill metadata is
    # passed through the existing registry rather than creating a new one.
    if skill_info and str((skill_info.config or {}).get("runtime") or "").lower() == "mcp":
        try:
            from mcp_skill_runtime import invoke_registered_mcp
            mcp_result = invoke_registered_mcp(
                {"skill_id": skill_info.skill_id, **(skill_info.config or {})},
                ctx.input_payload,
            )
            success = (
                isinstance(mcp_result, dict)
                and mcp_result.get("ok") is True
                and "result" in mcp_result
                and _product_result_is_success(mcp_result)
            )
            return {
                "success": success,
                "result": mcp_result,
                "source": "registered_mcp",
                "error": None if success else _product_result_error(mcp_result),
            }
        except Exception as e:
            return {"success": False, "error": str(e),
                    "traceback": traceback.format_exc()[-500:],
                    "source": "registered_mcp"}
    try:
        from lumenis_skill_adapter import get_skill_adapter
        adapter = get_skill_adapter()
        if adapter.available:
            osai_result = adapter.invoke_skill(
                task=ctx.task or json.dumps(ctx.input_payload, ensure_ascii=False),
                skill_id=ctx.skill_id,
                user_permissions=["READ", "AUDIT", "ANALYZE", "RESEARCH", "PLAN", "PATCH_PREVIEW", "TEST", "VERIFY"],
                timeout=60.0)
            if osai_result.get("connected"):
                result = osai_result.get("osai")
                success = _product_result_is_success(osai_result)
                return {
                    "success": success,
                    "result": result,
                    "source": "osai_adapter",
                    "error": None if success else _product_result_error(result),
                }
            # OSAI 不可用，回退到内置本地
    except Exception:
        pass
    try:
        from .registry import get_skill_registry
        reg = get_skill_registry()
        meta = reg.get(ctx.skill_id)
        if meta:
            local = _execute_builtin_local(ctx, meta)
            if local is not None:
                success = _product_result_is_success(local)
                return {
                    "success": success,
                    "result": local,
                    "source": "builtin_local",
                    "error": None if success else _product_result_error(local),
                }
    except Exception:
        pass
    return {"success": False, "error": "no executable handler available", "source": "none", "code": "NO_HANDLER"}


def _execute_builtin_local(ctx, meta):
    sid = ctx.skill_id
    if sid.startswith("shared."):
        try:
            from lumenis_shared_skills import run_shared_skill
            return run_shared_skill(sid, task=ctx.task, input_payload=ctx.input_payload)
        except Exception:
            # Keep the execution chain's existing fail-closed behavior.  The
            # caller receives NO_HANDLER/failed evidence instead of a fake
            # successful tool result.
            return None
    if sid == "zbc.subject_authority_read":
        try:
            from .registry import get_skill_registry
            return {"subject_words_count": 0, "registry_total": get_skill_registry().stats().get("total", 0)}
        except Exception: return None
    elif sid == "zbc.skill_registry_snapshot":
        try:
            from .registry import get_skill_registry
            return get_skill_registry().stats()
        except Exception: return None
    elif sid == "zbc.agent_boundary_audit":
        return {"identity": {"agent_id": ctx.execution_id, "role": "skill_executor"},
                "permission_scope": ["READ", "ANALYZE"]}
    return None


def _stable_hash(obj):
    import hashlib
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:16]

def _summarize(obj, max_len=200):
    if obj is None: return ""
    text = json.dumps(obj, ensure_ascii=False, default=str)
    return text[:max_len] + ("..." if len(text) > max_len else "")

def build_evidence(ctx):
    return {"execution_id": ctx.execution_id, "skill_id": ctx.skill_id, "timestamp": ctx.timestamp,
            "input_hash": _stable_hash(ctx.input_payload),
            "output_summary": _summarize(ctx.execute_result),
            "permission": ctx.permission_result, "firewall": ctx.firewall_result,
            "effect_fence": ctx.effect_fence_result,
            "source": ctx.execute_result.get("source") if ctx.execute_result else None}

def evaluate_execution(ctx):
    exec_res = ctx.execute_result or {}
    success = exec_res.get("success", False)
    return {"evaluated": True, "success": success, "quality_score": 0.8 if success else 0.0,
            "auto_admitted": False,
            "validation_required": ctx.action_type in (
                ActionType.EXPORT, ActionType.WRITE, ActionType.COMMIT, ActionType.PUSH,
            ),
            "validation_status": "pending_manual_validation" if success else "failed_no_validation",
            "reason": "execution completed; requires manual validation" if success else "execution failed"}


def ensure_skill_executions_table():
    try:
        from account.models import get_db
        conn = get_db()
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS skill_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT UNIQUE NOT NULL, skill_id TEXT NOT NULL, user_id INTEGER,
                domain TEXT DEFAULT 'SYSTEM', product TEXT DEFAULT 'SYSTEM', task TEXT,
                action_type TEXT DEFAULT 'ANALYZE', input_json TEXT, output_json TEXT,
                status TEXT DEFAULT 'pending', error TEXT, evidence_json TEXT, evaluation_json TEXT,
                permission_json TEXT, firewall_json TEXT, effect_fence_json TEXT,
                duration_ms INTEGER DEFAULT 0, created_at TEXT DEFAULT (datetime('now','localtime')))""")
            conn.commit()
        finally: conn.close()
    except Exception: pass

def write_trace(ctx, duration_ms=0):
    try:
        ensure_skill_executions_table()
        from account.models import get_db
        conn = get_db()
        try:
            conn.execute("""INSERT OR REPLACE INTO skill_executions
                (execution_id, skill_id, user_id, domain, product, task, action_type,
                 input_json, output_json, status, error, evidence_json, evaluation_json,
                 permission_json, firewall_json, effect_fence_json, duration_ms)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                ctx.execution_id, ctx.skill_id, ctx.user_id, ctx.domain, ctx.product,
                ctx.task, ctx.action_type.value,
                json.dumps(ctx.input_payload, ensure_ascii=False, default=str)[:4000],
                json.dumps(ctx.execute_result, ensure_ascii=False, default=str)[:4000] if ctx.execute_result else None,
                ctx.status.value, ctx.error,
                json.dumps(ctx.evidence, ensure_ascii=False, default=str)[:4000] if ctx.evidence else None,
                json.dumps(ctx.evaluation, ensure_ascii=False, default=str)[:4000] if ctx.evaluation else None,
                json.dumps(ctx.permission_result, ensure_ascii=False, default=str)[:2000] if ctx.permission_result else None,
                json.dumps(ctx.firewall_result, ensure_ascii=False, default=str)[:2000] if ctx.firewall_result else None,
                json.dumps(ctx.effect_fence_result, ensure_ascii=False, default=str)[:2000] if ctx.effect_fence_result else None,
                duration_ms))
            conn.commit(); return True
        finally: conn.close()
    except Exception: return False

def query_executions(skill_id=None, limit=50, status=None):
    try:
        from account.models import get_db
        conn = get_db()
        try:
            sql = "SELECT * FROM skill_executions"; conds = []; params = []
            if skill_id: conds.append("skill_id=?"); params.append(skill_id)
            if status: conds.append("status=?"); params.append(status)
            if conds: sql += " WHERE " + " AND ".join(conds)
            sql += " ORDER BY created_at DESC LIMIT ?"; params.append(limit)
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally: conn.close()
    except Exception: return []

def transition_state(current, target):
    allowed = _VALID_TRANSITIONS.get(current, set())
    if target in allowed: return True, f"{current.value} -> {target.value}"
    return False, f"invalid transition: {current.value} -> {target.value}"


def record_execution_evidence(ctx):
    """连接点a: Skill execution -> Shared Evidence 桥接。
    执行链完成后将执行证据写入 lumenis.shared.evidence.EvidenceStore (zbc_evidence表)，
    走 Contract/Artifact 边界。失败不阻断主链路（旁路记录）。
    """
    try:
        from lumenis.shared.evidence import EvidenceStore
        store = EvidenceStore()
        exec_res = ctx.execute_result or {}
        raw_content = json.dumps({
            "execution_id": ctx.execution_id,
            "skill_id": ctx.skill_id,
            "task": ctx.task,
            "action_type": ctx.action_type.value,
            "input_payload": ctx.input_payload,
            "execute_result": exec_res,
            "status": ctx.status.value,
            "error": ctx.error,
        }, ensure_ascii=False, default=str)
        ev, is_new = store.add_evidence(
            source_type="skill_execution",
            source_url=f"skill://{ctx.skill_id}/{ctx.execution_id}",
            source_id=ctx.execution_id,
            raw_content=raw_content,
            subject_scope=ctx.domain or "SYSTEM",
            task_id=ctx.execution_id,
            trace_id=ctx.execution_id,
            collection_metadata={
                "skill_id": ctx.skill_id,
                "action_type": ctx.action_type.value,
                "status": ctx.status.value,
                "permission": ctx.permission_result,
                "firewall": ctx.firewall_result,
                "effect_fence": ctx.effect_fence_result,
                "evaluation": ctx.evaluation,
            },
            provider="lumenis.shared.agents.skills.execution",
            domain_id=ctx.domain or "system",
            product_id=ctx.product or "SYSTEM",
        )
        return {"ok": True, "evidence_id": ev.evidence_id, "is_new": is_new}
    except Exception as e:
        return {"ok": False, "error": str(e), "note": "evidence bridge failed, main chain unaffected"}


def run_execution_chain(skill_id, task="", input_payload=None, action_type=ActionType.ANALYZE,
                        user_id=None, user_role="user", product="SYSTEM", domain="global",
                        permission_role=None,
                        skill_info=None, handler=None, content_source_import=None,
                        request_context=None, workspace_principal=None):
    import time
    start = time.time()
    ctx = SkillExecutionContext(skill_id=skill_id, task=task, input_payload=input_payload or {},
                                 action_type=action_type, user_id=user_id, product=product, domain=domain,
                                 permission_role=permission_role,
                                 content_source_import=content_source_import,
                                 request_context=request_context,
                                 workspace_principal=workspace_principal)
    source_import = content_source_import is not None
    if source_import and not callable(handler):
        ctx.status = ExecutionStatus.REJECTED
        ctx.error = "content source import requires its server-owned execution handler"
        return ctx
    ctx.permission_result = check_permission(ctx, user_role=user_role, skill_info=skill_info)
    if not ctx.permission_result["allowed"]:
        ctx.status = ExecutionStatus.REJECTED; ctx.error = ctx.permission_result["reason"]
        if not source_import:
            write_trace(ctx, int((time.time() - start) * 1000))
        return ctx
    ctx.firewall_result = action_firewall(ctx)
    if not ctx.firewall_result["allowed"]:
        ctx.status = ExecutionStatus.REJECTED; ctx.error = ctx.firewall_result.get("reason", "action denied")
        if not source_import:
            write_trace(ctx, int((time.time() - start) * 1000))
        return ctx
    ctx.effect_fence_result = effect_fence(ctx)
    if not ctx.effect_fence_result.get("allowed", False):
        ctx.status = ExecutionStatus.BLOCKED
        ctx.error = ctx.effect_fence_result.get("reason", "effect fence blocked")
        if not source_import:
            write_trace(ctx, int((time.time() - start) * 1000))
        return ctx
    if source_import:
        # Close the gap between the initial authorization/fence checks and the
        # handler boundary. The descriptor is frozen and must remain the exact
        # object supplied by the trusted caller; its approval/account scope is
        # freshly checked without an operation_id or cached receipt.
        if (ctx.content_source_import is not content_source_import
                or ctx.workspace_principal is not workspace_principal):
            ctx.status = ExecutionStatus.REJECTED
            ctx.error = "content source import descriptor changed before handler execution"
            try:
                from lumenis.system.security import get_effect_fence
                get_effect_fence().complete(
                    ctx.effect_fence_result.get("idempotency_key"), success=False,
                )
            except Exception:
                pass
            return ctx
        ctx.permission_result = check_permission(
            ctx, user_role=user_role, skill_info=skill_info,
        )
        if not ctx.permission_result["allowed"]:
            ctx.status = ExecutionStatus.REJECTED
            ctx.error = ctx.permission_result["reason"]
            try:
                from lumenis.system.security import get_effect_fence
                get_effect_fence().complete(
                    ctx.effect_fence_result.get("idempotency_key"), success=False,
                )
            except Exception:
                pass
            return ctx
        ctx.firewall_result = action_firewall(ctx)
        if not ctx.firewall_result["allowed"]:
            ctx.status = ExecutionStatus.REJECTED
            ctx.error = ctx.firewall_result.get("reason", "action denied")
            try:
                from lumenis.system.security import get_effect_fence
                get_effect_fence().complete(
                    ctx.effect_fence_result.get("idempotency_key"), success=False,
                )
            except Exception:
                pass
            return ctx
    ctx.status = ExecutionStatus.RUNNING
    ctx.execute_result = execute_skill(ctx, handler=handler, skill_info=skill_info)
    try:
        from lumenis.system.security import get_effect_fence
        get_effect_fence().complete(
            ctx.effect_fence_result.get("idempotency_key"),
            success=bool(ctx.execute_result.get("success")),
        )
    except Exception:
        pass
    ctx.evidence = build_evidence(ctx)
    ctx.evaluation = evaluate_execution(ctx)
    if ctx.execute_result.get("success"):
        ctx.status = ExecutionStatus.COMPLETED
    else:
        ctx.status = ExecutionStatus.FAILED; ctx.error = ctx.execute_result.get("error", "execution failed")
    if source_import and ctx.status is not ExecutionStatus.COMPLETED:
        return ctx
    ctx.evidence_record = record_execution_evidence(ctx)
    evidence_required = ctx.action_type in (
        ActionType.EXPORT, ActionType.WRITE, ActionType.COMMIT, ActionType.PUSH,
    )
    if (ctx.status is ExecutionStatus.COMPLETED and evidence_required
            and (not isinstance(ctx.evidence_record, dict)
                 or ctx.evidence_record.get("ok") is not True)):
        ctx.status = ExecutionStatus.FAILED
        ctx.error = "EVIDENCE_RECORD_FAILED"
        ctx.evaluation = {
            **(ctx.evaluation or {}),
            "success": False,
            "quality_score": 0.0,
            "auto_admitted": False,
            "validation_required": True,
            "validation_status": "failed_no_evidence",
            "reason": "effect completed but required Evidence could not be recorded",
        }
    write_trace(ctx, int((time.time() - start) * 1000))
    return ctx

def get_skills_light_status(product=None):
    results = []
    try:
        from account.skills import list_skills
        for s in list_skills(product=product, status="enabled"):
            results.append({"skill_id": s["skill_id"], "name": s.get("name", s["skill_id"]),
                "description": s.get("description", ""), "product": s.get("product", "SYSTEM"),
                "domain": s.get("domain", "global"), "status": "enabled", "state": "enabled",
                "version": s.get("version", "1.0"), "source": "db"})
    except Exception: pass
    try:
        from .registry import get_skill_registry
        existing = {r["skill_id"] for r in results}
        for meta in get_skill_registry().list_all():
            if meta.skill_id in existing: continue
            results.append({"skill_id": meta.skill_id, "name": meta.skill_id.replace("zbc.", "").replace("_", " ").title(),
                "description": meta.description, "product": getattr(meta, "product", "SYSTEM"),
                "domain": getattr(meta, "domain", "global"), "status": "registered", "state": "registered",
                "version": meta.version, "risk_level": meta.risk_level.value, "source": "builtin_registry"})
    except Exception: pass
    return results
