# -*- coding: utf-8 -*-
"""LUMENIS — canonical Skill Execution Chain (适配接入，不重写 skill_registry)。
执行链：Task → Permission → Agent → Skill → Tool → Action Firewall
       → Effect Fence / Idempotency → Execute → Evidence → Evaluation → Trace
"""
from __future__ import annotations
import json, uuid
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
    CANCELLED = "cancelled"; FAILED = "failed"; BLOCKED = "blocked"; REJECTED = "rejected"

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
    product: str = "SYSTEM"; domain: str = "system"; version: str = "1.0.0"
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

    request_context = ctx.request_context if isinstance(ctx.request_context, dict) else {}
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
        shared_scope = request_context.get("shared_workspace_scope")
        shared_content_import = (
            type(upload) is ContentSourceImport
            and upload.domain_id is None and upload.subject_id is None
            and upload.brand_focus_id is None and upload.global_scope is False
            and upload.scope_kind == "shared_workspace"
            and type(upload.scope_version) is int and upload.scope_version == 1
            and type(shared_scope) is dict
            and set(shared_scope) == {"scope_kind", "version"}
            and shared_scope == {"scope_kind": "shared_workspace", "version": 1}
            and str(ctx.product or "").strip().upper() == "SHARED"
            and ctx.domain is None
        )
        legacy_content_import = (
            type(upload) is ContentSourceImport
            and domain_aliases.get(str(ctx.domain or "").strip().lower()) == upload.domain_id
            and product_aliases.get(str(ctx.product or "").strip().lower()) == upload.domain_id
        )
        context_matches = (
            type(upload) is ContentSourceImport
            and ctx.skill_id == "shared.content_project"
            and ctx.action_type is ActionType.WRITE
            and identity_matches
            and (legacy_content_import or shared_content_import)
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

    target = str(ctx.input_payload.get("target") or f"skill:{ctx.skill_id}")
    if (ctx.workspace_principal is not None and isinstance(request_context, dict)
            and set(request_context) == {'agent_task_id'}):
        try:
            from agent_runtime.task_binding import authorized_context, _current_binding, _digest
            from ai_task_engine import get_task_engine
            task_id = request_context['agent_task_id']
            task = get_task_engine().get_task(task_id)
            context = authorized_context(task, ctx.workspace_principal)
            _current_binding(task_id, ctx.skill_id)
            expected = 'agentstep_' + _digest({'task': task_id, 'skill': ctx.skill_id, 'inputs': ctx.input_payload})[:32]
            if (ctx.skill_id not in _BACKGROUND_INPUTS or ctx.action_type is not ActionType.READ
                    or ctx.user_id is not None or ctx.execution_id != expected
                    or set(ctx.input_payload) - _BACKGROUND_INPUTS[ctx.skill_id]
                    or ctx.domain != context['domain_id'] or ctx.product != context['product']
                    or task['status'] == 'cancelled'):
                raise PermissionError('LOCAL_AGENT_SKILL_BINDING_INVALID')
            return {'allowed': True, 'reason': 'Scoped server local Agent read', 'code': 'PERMISSION_GRANTED',
                    'resource': 'skill:' + ctx.skill_id, 'caller': 'workspace:local',
                    'operation_type': 'read', 'requires_approval': False}
        except Exception:
            return {'allowed': False, 'reason': 'Local Agent task binding unavailable', 'code': 'LOCAL_AGENT_SCOPE_DENIED'}
    if ctx.workspace_principal is not None:
        shared_scope = request_context.get("shared_workspace_scope") if isinstance(request_context, dict) else None
        if not (
            ctx.skill_id == "shared.content_project"
            and ctx.action_type is ActionType.EXPORT
            and str(ctx.product or "").strip().upper() == "SHARED"
            and ctx.domain is None
            and type(shared_scope) is dict
            and set(shared_scope) == {"scope_kind", "version"}
            and shared_scope == {"scope_kind": "shared_workspace", "version": 1}
        ):
            return {"allowed": False, "reason": "local principal requires an exact Content import or project export",
                    "code": "LOCAL_PRINCIPAL_ACTION_UNSUPPORTED"}

    shared_scope = request_context.get("shared_workspace_scope") if isinstance(request_context, dict) else None
    if (
        ctx.skill_id == "shared.content_project"
        and ctx.action_type is ActionType.EXPORT
        and str(ctx.product or "").strip().upper() == "SHARED"
        and ctx.domain is None
        and type(shared_scope) is dict
        and set(shared_scope) == {"scope_kind", "version"}
        and shared_scope == {"scope_kind": "shared_workspace", "version": 1}
    ):
        from lumenis.system.security import check_shared_workspace_effect

        actor = ctx.workspace_principal if ctx.workspace_principal is not None else {"id": ctx.user_id}
        result = check_shared_workspace_effect(
            actor, shared_scope, _canonical_operation(ctx.action_type), target,
            module="content", action="write",
        )
        payload = result.to_dict()
        payload["code"] = "PERMISSION_GRANTED" if result.allowed else (
            "APPROVAL_REQUIRED" if result.requires_approval else "PERMISSION_DENIED"
        )
        return payload

    from lumenis.system.security import get_permission_gate
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
    "diagnostics",
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
        except Exception:  # noqa: BLE001
            return {"success": False, "error": "SKILL_HANDLER_FAILED",
                    "code": "SKILL_HANDLER_FAILED", "source": "custom_handler"}
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
        except Exception:  # noqa: BLE001
            return {"success": False, "error": "SKILL_MCP_RUNTIME_FAILED",
                    "code": "SKILL_MCP_RUNTIME_FAILED", "source": "registered_mcp"}
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

def _trace_json(value, limit=8 * 1024 * 1024):
    """Keep complete sanitized JSON in the existing trace owner, never a digest.

    Oversize is explicit failure, not successful persistence of missing content.
    Credentials remain excluded by the shared checkpoint sanitizer.
    """
    from agent_runtime.durable_adapter import _sanitize_checkpoint_value
    safe, _sensitive = _sanitize_checkpoint_value(value)
    text = json.dumps(safe, ensure_ascii=False, default=str, allow_nan=False)
    if len(text.encode("utf-8")) > limit:
        raise ValueError("SKILL_TRACE_PAYLOAD_TOO_LARGE: maximum 8 MiB; use existing Artifact reference")
    return text


def _agent_scope_binding(ctx, *, connection=None):
    """Bind an account Skill invocation to its current server-owned Agent task."""
    request = ctx.request_context if isinstance(ctx.request_context, dict) else {}
    if 'agent_task_id' not in request:
        if str(ctx.execution_id).startswith('skillscope_agentstep_'):
            raise PermissionError('AGENT_SKILL_TASK_BINDING_REQUIRED')
        return None
    from ai_task_engine import get_task_engine
    from agent_runtime.task_binding import authorized_context, _current_binding, _digest
    task_id = request['agent_task_id']
    task = get_task_engine().get_task(task_id)
    if not isinstance(task, dict):
        raise PermissionError('AGENT_TASK_UNAVAILABLE')
    context = authorized_context(task, {'id': ctx.user_id}, connection=connection)
    _current_binding(task_id, ctx.skill_id)
    expected = 'skillscope_agentstep_' + _digest({'task': task_id, 'skill': ctx.skill_id, 'inputs': ctx.input_payload})[:32]
    if (type(ctx.user_id) is not int or context['actor_id'] != ctx.user_id
            or ctx.workspace_principal is not None or ctx.action_type is not ActionType.READ
            or ctx.skill_id not in _BACKGROUND_INPUTS or set(ctx.input_payload) - _BACKGROUND_INPUTS[ctx.skill_id]
            or ctx.execution_id != expected or task['status'] == 'cancelled'
            or ctx.domain != context['domain_id'] or ctx.product != context['product']
            or ctx.task != task['user_input'] or request.get('skill_scope') != context['scope']):
        raise PermissionError('AGENT_SKILL_BINDING_INVALID')
    return {'task_id': task_id, 'binding_sha256': _digest({
        'task_id': task_id, 'created_by': task['created_by'],
        'context': task['context'], 'user_input': task['user_input']})}


def _direct_scope_admission(ctx, *, connection=None):
    """Admit an explicit selector through Permission; input_payload is never scope."""
    context = ctx.request_context if isinstance(ctx.request_context, dict) else {}
    agent_binding = _agent_scope_binding(ctx, connection=connection) if ctx.workspace_principal is None else None
    if "skill_scope" not in context:
        return None
    scope = context["skill_scope"]
    if (type(scope) is not dict or not scope
            or set(scope) - {"subject_id", "brand_focus_id", "global_scope"}
            or type(ctx.user_id) is not int or ctx.user_id <= 0
            or ctx.workspace_principal is not None
            or ctx.domain not in ("cth", "zbmp")
            or ctx.product != {"cth": "CTH", "zbmp": "ZBMP"}.get(ctx.domain)):
        raise PermissionError("SKILL_SCOPE_SELECTOR_INVALID")
    from lumenis.system.security.permission import check_actor_scope_permission
    decision = check_actor_scope_permission(
        {"id": ctx.user_id}, domain_id=ctx.domain, module=ctx.skill_id,
        action="write" if ctx.action_type in (ActionType.WRITE, ActionType.COMMIT, ActionType.PUSH) else "read",
        subject_id=scope.get("subject_id"), brand_focus_id=scope.get("brand_focus_id"),
        global_scope=scope.get("global_scope", False), connection=connection,
    )
    if not decision.allowed or decision.verification_state != "verified":
        raise PermissionError("SKILL_SCOPE_PERMISSION_DENIED")
    return {"domain_id": decision.domain_id, "subject_id": decision.subject_id,
            "brand_focus_id": decision.brand_focus_id, "global_scope": decision.global_scope,
            "scope_audit_id": decision.scope_audit_id, "scope_basis": "explicit_selection",
            **({"agent_task": agent_binding} if agent_binding is not None else {})}


def _execution_scope_digest(row):
    """Bind the saved result, principal and every material trace field, not a preview."""
    import hashlib
    fields = {key: row.get(key) for key in (
        "execution_id", "skill_id", "user_id", "domain", "product", "task", "action_type",
        "input_json", "output_json", "status", "error", "evaluation_json",
        "permission_json", "firewall_json", "effect_fence_json", "created_at")}
    evidence = json.loads(row.get("evidence_json") or "{}")
    evidence.pop("scope_receipt", None)
    fields["evidence"] = evidence
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _execution_request_scope_digest(row):
    import hashlib
    fields = {key: row.get(key) for key in (
        "execution_id", "skill_id", "user_id", "domain", "product", "task", "action_type",
        "input_json", "permission_json", "created_at")}
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _queued_execution_scope(row):
    """Recover an explicit selector from signed submission, then recheck live admission."""
    if not row['execution_id'].startswith('skilljob_scoped_'):
        return None
    from account.models import get_db
    from lumenis.shared.evidence import store
    proof = json.loads(row.get('evidence_json') or '{}').get('scope_receipt') or {}
    con = get_db()
    try:
        receipt = con.execute('SELECT * FROM app_evidence_records WHERE id=?',
                              (proof.get('evidence_id'),)).fetchone()
    finally:
        con.close()
    if not receipt or not store.verify_evidence_record_integrity(receipt):
        raise PermissionError('BACKGROUND_SCOPE_RECEIPT_INVALID')
    material = json.loads(receipt['inputs_json'])['scope_receipt']
    if (material.get('contract') != 'skill-execution-request-scope-v1'
            or material.get('execution_id') != row['execution_id']
            or material.get('actor_id') != row['user_id']
            or material.get('trace_sha256') != _execution_request_scope_digest(row)
            or material.get('domain_id') != row['domain']
            or receipt['source'] != 'skill_execution_scope'):
        raise PermissionError('BACKGROUND_SCOPE_BINDING_CHANGED')
    scope = {key: material[key] for key in ('subject_id', 'brand_focus_id', 'global_scope')}
    context = SkillExecutionContext(skill_id=row['skill_id'], user_id=row['user_id'],
        domain=row['domain'], product=row['product'], action_type=ActionType(row['action_type']),
        request_context={'skill_scope': scope})
    _direct_scope_admission(context)
    return scope


def _record_execution_scope_receipt(ctx, conn):
    context = ctx.request_context if isinstance(ctx.request_context, dict) else {}
    pending = ctx.status is ExecutionStatus.PENDING and ctx.execution_id.startswith('skilljob_scoped_')
    if "skill_scope" not in context or (ctx.status is not ExecutionStatus.COMPLETED and not pending):
        return
    # Revalidate at finalization too: a handler cannot mint a receipt after
    # the selected source scope has been withdrawn while it was running.
    admission = _direct_scope_admission(ctx, connection=conn)
    if not getattr(ctx, "_scope_admission", None):
        raise PermissionError("SKILL_SCOPE_ADMISSION_MISSING")
    for key in ("domain_id", "subject_id", "brand_focus_id", "global_scope", "agent_task"):
        if admission.get(key) != ctx._scope_admission.get(key):
            raise PermissionError("SKILL_SCOPE_CHANGED_DURING_EXECUTION")
    row = dict(conn.execute("SELECT * FROM skill_executions WHERE execution_id=?",
                           (ctx.execution_id,)).fetchone())
    expected = {"user_id": ctx.user_id, "skill_id": ctx.skill_id, "domain": ctx.domain,
                "product": ctx.product, "task": ctx.task, "action_type": ctx.action_type.value,
                "input_json": _trace_json(ctx.input_payload)}
    if any(row[key] != value for key, value in expected.items()):
        raise PermissionError("SKILL_SCOPE_TRACE_IDENTITY_MISMATCH")
    from lumenis.shared.evidence import store
    store.ensure_evidence_schema(conn)
    material = {"contract": "skill-execution-request-scope-v1" if pending else "skill-execution-scope-v1",
                "actor_id": ctx.user_id, "execution_id": ctx.execution_id,
                "trace_sha256": _execution_request_scope_digest(row) if pending else _execution_scope_digest(row),
                **admission}
    evidence_id = store.record_evidence(
        source="skill_execution_scope", feature_id=ctx.execution_id,
        product=ctx.product, domain_id=admission["domain_id"],
        subject_id=admission["subject_id"], brand_focus_id=admission["brand_focus_id"],
        global_scope=admission["global_scope"], inputs={"scope_receipt": material},
        outputs={"execution_status": row["status"], "result_validation": "not_established_by_scope_receipt"},
        account="actor:" + str(ctx.user_id), status="pending", result="PASS",
        test_name="execution-scope-binding", provider=__name__, connection=conn)
    receipt = conn.execute("SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)).fetchone()
    if not receipt or not store.verify_evidence_record_integrity(receipt):
        raise ValueError("SKILL_SCOPE_RECEIPT_READBACK_FAILED")
    evidence = json.loads(row.get("evidence_json") or "{}")
    evidence["scope_receipt"] = {"version": 1, "evidence_id": evidence_id}
    conn.execute("UPDATE skill_executions SET evidence_json=? WHERE execution_id=?",
                 (_trace_json(evidence), ctx.execution_id))
    ctx.evidence = evidence


def verified_execution_scope(row, actor):
    """Return current, signed scope for status projection, never result/source admission.

    Legacy/no-proof rows remain unknown. The caller still needs the original
    result owner's fresh source-use checks before reading protected output.
    """
    try:
        from account.models import get_db
        from lumenis.shared.evidence import store
        from lumenis.system.security.permission import check_actor_scope_permission
        if (not isinstance(row, dict) or not isinstance(actor, dict)
                or type(actor.get("id")) is not int or row.get("user_id") != actor["id"]):
            return None
        proof = json.loads(row.get("evidence_json") or "{}").get("scope_receipt")
        if (type(proof) is not dict or set(proof) != {"version", "evidence_id"}
                or proof["version"] != 1 or type(proof["evidence_id"]) is not int):
            return None
        con = get_db()
        try:
            live = con.execute("SELECT * FROM skill_executions WHERE execution_id=?",
                               (row.get("execution_id"),)).fetchone()
            receipt = con.execute("SELECT * FROM app_evidence_records WHERE id=?",
                                  (proof["evidence_id"],)).fetchone()
        finally:
            con.close()
        if (not live or dict(live) != row or not receipt
                or not store.verify_evidence_record_integrity(receipt)):
            return None
        record = dict(receipt)
        material = json.loads(record["inputs_json"])["scope_receipt"]
        if (material.get("contract") != "skill-execution-scope-v1"
                or material.get("scope_basis") != "explicit_selection"
                or record.get("source") != "skill_execution_scope"
                or material.get("actor_id") != actor["id"]
                or material.get("execution_id") != row.get("execution_id")
                or material.get("trace_sha256") != _execution_scope_digest(row)
                or material.get("domain_id") != row.get("domain")
                or record.get("domain_id") != row.get("domain")
                or record.get("product_id") != row.get("product")
                or row.get("status") != "completed"):
            return None
        scope = {key: material[key] for key in (
            "domain_id", "subject_id", "brand_focus_id", "global_scope")}
        agent_binding = material.get('agent_task')
        if agent_binding is not None or row['execution_id'].startswith('skillscope_agentstep_'):
            if not isinstance(agent_binding, dict) or set(agent_binding) != {'task_id', 'binding_sha256'}:
                return None
            ctx = SkillExecutionContext(execution_id=row['execution_id'], skill_id=row['skill_id'],
                user_id=row['user_id'], domain=row['domain'], product=row['product'], task=row['task'],
                input_payload=json.loads(row['input_json']), action_type=ActionType(row['action_type']),
                request_context={'agent_task_id': agent_binding['task_id'],
                    'skill_scope': {key: scope[key] for key in ('subject_id', 'brand_focus_id', 'global_scope')}})
            if _agent_scope_binding(ctx) != agent_binding:
                return None
        decision = check_actor_scope_permission(actor, module=row["skill_id"], action="read", **scope)
        if not decision.allowed or decision.verification_state != "verified":
            return None
        return {**scope, "evidence_id": proof["evidence_id"], "digest": material["trace_sha256"]}
    except Exception:
        return None


def write_trace(ctx, duration_ms=0, *, connection=None):
    try:
        if connection is None:
            ensure_skill_executions_table()
            if (ctx.status in (ExecutionStatus.PENDING, ExecutionStatus.COMPLETED) and isinstance(ctx.request_context, dict)
                    and "skill_scope" in ctx.request_context):
                from lumenis.shared.evidence import store
                store.init_evidence_store()
            from account.models import get_db
            conn = get_db()
        else:
            conn = connection
        try:
            conn.execute("SAVEPOINT skill_scope_trace")
            cursor = conn.execute("""INSERT INTO skill_executions
                (execution_id, skill_id, user_id, domain, product, task, action_type,
                 input_json, output_json, status, error, evidence_json, evaluation_json,
                 permission_json, firewall_json, effect_fence_json, duration_ms)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(execution_id) DO UPDATE SET
                output_json=excluded.output_json,status=excluded.status,error=excluded.error,
                evidence_json=excluded.evidence_json,evaluation_json=excluded.evaluation_json,
                permission_json=excluded.permission_json,firewall_json=excluded.firewall_json,
                effect_fence_json=excluded.effect_fence_json,duration_ms=excluded.duration_ms
                WHERE skill_executions.status NOT IN ('cancelled', 'completed')""", (
                ctx.execution_id, ctx.skill_id, ctx.user_id, ctx.domain, ctx.product,
                ctx.task, ctx.action_type.value,
                _trace_json(ctx.input_payload),
                _trace_json(ctx.execute_result) if ctx.execute_result else None,
                ctx.status.value, ctx.error,
                _trace_json(ctx.evidence) if ctx.evidence else None,
                _trace_json(ctx.evaluation) if ctx.evaluation else None,
                _trace_json(ctx.permission_result) if ctx.permission_result else None,
                _trace_json(ctx.firewall_result) if ctx.firewall_result else None,
                _trace_json(ctx.effect_fence_result) if ctx.effect_fence_result else None,
                duration_ms))
            if cursor.rowcount == 1:
                _record_execution_scope_receipt(ctx, conn)
            conn.execute("RELEASE SAVEPOINT skill_scope_trace")
            if connection is None:
                conn.commit()
            return cursor.rowcount == 1
        except Exception:
            conn.execute("ROLLBACK TO SAVEPOINT skill_scope_trace")
            conn.execute("RELEASE SAVEPOINT skill_scope_trace")
            raise
        finally:
            if connection is None:
                conn.close()
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).error("Skill trace finalization failed; details suppressed")
        return False


def _reserve_package_execution(ctx, skill_info):
    """Serialize registered package admission with metadata changes; no new schema."""
    config = skill_info.config if skill_info is not None else None
    if not isinstance(config, dict) or config.get("source_type") not in {"github", "local", "zip", "skill_md"}:
        return None
    from lumenis.shared.database import get_repository
    fields = ("runtime", "source", "source_type", "entrypoint", "install_path", "active_version", "version",
              "tools_json", "permissions_granted_json", "input_schema_json", "output_schema_json",
              "compatibility_json", "install_state", "lifecycle_state", "health_state")
    try:
        with get_repository().transaction(timeout=10) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM skills_registry WHERE skill_id=?", (ctx.skill_id,)).fetchone()
            if row is None or not set(fields) <= set(row.keys()):
                return "SKILL_RUNTIME_METADATA_UNAVAILABLE"
            if row["status"] != "enabled" or row["install_state"] != "installed" or row["health_state"] != "healthy":
                return "SKILL_RUNTIME_NOT_READY"
            from .lifecycle import _hash as registry_hash
            if not isinstance(config.get("registry_sha256"), str):
                return "SKILL_RUNTIME_METADATA_SNAPSHOT_REQUIRED"
            if config["registry_sha256"] != registry_hash(dict(row)):
                return "SKILL_RUNTIME_METADATA_CHANGED"
            current_config = json.loads(row["config_json"]) if row["config_json"] else {}
            if not isinstance(current_config, dict):
                return "SKILL_RUNTIME_METADATA_INVALID"
            for name in fields:
                if row[name] is not None:
                    current_config[name] = row[name]
            current_config["registry_sha256"] = registry_hash(dict(row))
            if current_config != config or row["version"] != skill_info.version:
                return "SKILL_RUNTIME_METADATA_CHANGED"
            previous = connection.execute("SELECT 1 FROM skill_executions WHERE execution_id=?", (ctx.execution_id,)).fetchone()
            if previous is not None:
                return "SKILL_EXECUTION_ID_COLLISION"
            ctx.status = ExecutionStatus.RUNNING
            if not write_trace(ctx, connection=connection):
                raise RuntimeError("Skill execution reservation could not be persisted")
        return "reserved"
    except Exception:
        return "SKILL_EXECUTION_RESERVATION_UNAVAILABLE"

def query_executions(skill_id=None, limit=50, status=None, offset=0, *, strict=False, execution_id=None):
    try:
        from account.models import get_db
        conn = get_db()
        try:
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='skill_executions'").fetchone() is None:
                return []  # A fresh workspace has no Skill executions yet.
            sql = "SELECT * FROM skill_executions"; conds = []; params = []
            if execution_id: conds.append("execution_id=?"); params.append(execution_id)
            if skill_id: conds.append("skill_id=?"); params.append(skill_id)
            if status: conds.append("status=?"); params.append(status)
            if conds: sql += " WHERE " + " AND ".join(conds)
            sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"; params.extend([limit, offset])
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally: conn.close()
    except Exception:
        if strict:
            raise
        return []

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
        metadata = {
            "skill_id": ctx.skill_id,
            "action_type": ctx.action_type.value,
            "status": ctx.status.value,
            "permission": ctx.permission_result,
            "firewall": ctx.firewall_result,
            "effect_fence": ctx.effect_fence_result,
            "evaluation": ctx.evaluation,
        }
        shared_context = ctx.request_context if isinstance(ctx.request_context, dict) else {}
        shared_scope = shared_context.get("shared_workspace_scope")
        if shared_scope is not None:
            if (
                ctx.skill_id != "shared.content_project"
                or str(ctx.product or "").strip().upper() != "SHARED"
                or ctx.domain is not None
                or set(shared_context) != {"shared_workspace_scope"}
            ):
                raise ValueError("SHARED_SKILL_EVIDENCE_CONTEXT_INVALID")
            from lumenis.system.security.permission import LocalWorkspacePrincipal

            actor = (
                ctx.workspace_principal if type(ctx.workspace_principal) is LocalWorkspacePrincipal
                else {"id": ctx.user_id}
            )
            ev, is_new = store.add_shared_skill_execution_evidence(
                actor=actor, shared_workspace_scope=shared_scope,
                source_url=f"skill://{ctx.skill_id}/{ctx.execution_id}",
                raw_content=raw_content, source_id=ctx.execution_id,
                task_id=ctx.execution_id, trace_id=ctx.execution_id,
                collection_metadata=metadata,
            )
            persisted = store.get_evidence(ev.evidence_id)
            if (
                persisted is None or persisted.content_hash != ev.content_hash
                or persisted.domain_id != "content" or persisted.product_id != "SHARED"
                or persisted.subject_scope != ev.subject_scope
            ):
                raise ValueError("SHARED_SKILL_EVIDENCE_READBACK_FAILED")
        else:
            ev, is_new = store.add_evidence(
                source_type="skill_execution",
                source_url=f"skill://{ctx.skill_id}/{ctx.execution_id}",
                source_id=ctx.execution_id,
                raw_content=raw_content,
                subject_scope="GLOBAL / ALL",
                task_id=ctx.execution_id,
                trace_id=ctx.execution_id,
                collection_metadata=metadata,
                provider="lumenis.shared.agents.skills.execution",
                domain_id=ctx.domain or None,
                product_id=ctx.product or None,
            )
        return {"ok": True, "evidence_id": ev.evidence_id, "is_new": is_new}
    except Exception:  # noqa: BLE001
        return {"ok": False, "error": "SKILL_EVIDENCE_BRIDGE_FAILED",
                "code": "SKILL_EVIDENCE_BRIDGE_FAILED",
                "note": "evidence bridge failed, main chain unaffected"}


def run_execution_chain(skill_id, task="", input_payload=None, action_type=ActionType.ANALYZE,
                        user_id=None, user_role="user", product="SYSTEM", domain="system",
                        permission_role=None,
                        skill_info=None, handler=None, content_source_import=None,
                        request_context=None, workspace_principal=None, execution_id=None):
    import time
    start = time.time()
    ctx = SkillExecutionContext(skill_id=skill_id, task=task, input_payload=input_payload or {},
                                 action_type=action_type, user_id=user_id, product=product, domain=domain,
                                 permission_role=permission_role,
                                 content_source_import=content_source_import,
                                 request_context=request_context,
                                 workspace_principal=workspace_principal)
    if execution_id is not None:
        ctx.execution_id = execution_id
    elif isinstance(request_context, dict) and "skill_scope" in request_context:
        # Preserve the fact that this row requires a scope proof even if its
        # evidence_json is damaged or removed later. Legacy IDs stay unknown.
        ctx.execution_id = "skillscope_" + ctx.execution_id
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
    try:
        ctx._scope_admission = _direct_scope_admission(ctx)
    except PermissionError as exc:
        ctx.status = ExecutionStatus.REJECTED
        ctx.error = str(exc)
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
    reservation = None if source_import else _reserve_package_execution(ctx, skill_info)
    if reservation not in (None, "reserved"):
        ctx.status = ExecutionStatus.REJECTED
        ctx.error = reservation
        return ctx
    if (getattr(ctx, '_scope_admission', None) or {}).get('agent_task'):
        try:
            current = _direct_scope_admission(ctx)
            if any(current.get(key) != ctx._scope_admission.get(key) for key in
                   ('domain_id', 'subject_id', 'brand_focus_id', 'global_scope', 'agent_task')):
                raise PermissionError('AGENT_SKILL_CHANGED_BEFORE_EXECUTION')
        except PermissionError as exc:
            ctx.status = ExecutionStatus.REJECTED
            ctx.error = str(exc)
            write_trace(ctx, int((time.time() - start) * 1000))
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
    trace_saved = write_trace(ctx, int((time.time() - start) * 1000))
    if not trace_saved and (reservation == "reserved" or ctx.status is ExecutionStatus.COMPLETED):
        ctx.status = ExecutionStatus.FAILED
        ctx.error = "SKILL_EXECUTION_TRACE_FINALIZATION_FAILED"
        ctx.evaluation = {
            **(ctx.evaluation or {}), "success": False, "auto_admitted": False,
            "validation_required": True, "validation_status": "failed_no_trace",
            "reason": "execution output could not be durably recorded",
        }
    return ctx

def get_skills_light_status(product=None):
    results = []
    try:
        from account.skills import list_skills
        for s in list_skills(product=product, status="enabled"):
            results.append({"skill_id": s["skill_id"], "name": s.get("name", s["skill_id"]),
                "description": s.get("description", ""), "product": s.get("product", "SYSTEM"),
                "domain": s.get("domain", "system"), "status": "enabled", "state": "enabled",
                "version": s.get("version", "1.0"), "source": "db"})
    except Exception: pass
    try:
        from .registry import get_skill_registry
        existing = {r["skill_id"] for r in results}
        for meta in get_skill_registry().list_all():
            if meta.skill_id in existing: continue
            results.append({"skill_id": meta.skill_id, "name": meta.skill_id.replace("zbc.", "").replace("_", " ").title(),
                "description": meta.description, "product": getattr(meta, "product", "SYSTEM"),
                "domain": getattr(meta, "domain", "system"), "status": "registered", "state": "registered",
                "version": meta.version, "risk_level": meta.risk_level.value, "source": "builtin_registry"})
    except Exception: pass
    return results


# This is a handler binding to the existing TaskQueue, not a second scheduler.
# Only bounded, local, non-business-reading handlers are safe for this lane.
_BACKGROUND_INPUTS = {
    'zbc.skill_registry_snapshot': set(),
    'zbc.agent_boundary_audit': set(),
    'shared.social_card': {'title', 'subtitle', 'accent', 'width', 'height'},
    'shared.video_shotcraft': {'brief'},
    'shared.huashu': {'brief', 'domain', 'product', 'platform', 'asset_type', 'audience', 'goal'},
}


def _background_binding(info):
    return _stable_hash({k: info.get(k) for k in (
        'skill_id', 'version', 'registry_sha256', 'status', 'product', 'domain',
        'source', 'runtime', 'entrypoint', 'config', 'active_version')})


def enqueue_registered_skill(*, skill_id, task, input_payload, action_type,
                             user_id, product, domain, skill_info, scope=None):
    if (skill_id not in _BACKGROUND_INPUTS or action_type not in (ActionType.READ, ActionType.ANALYZE)
            or skill_info.get('status') != 'enabled'
            or not isinstance(input_payload, dict)
            or set(input_payload) - _BACKGROUND_INPUTS[skill_id]
            or len(json.dumps(input_payload, ensure_ascii=False)) > 16000
            or len(task) > 4000):
        return {'success': False, 'code': 'BACKGROUND_HANDLER_NOT_ALLOWED'}
    ctx = SkillExecutionContext(execution_id=('skilljob_scoped_' if scope is not None else 'skilljob_') + uuid.uuid4().hex,
        skill_id=skill_id, task=task, input_payload=input_payload, action_type=action_type,
        user_id=user_id, product=product, domain=domain,
        request_context={'skill_scope': scope} if scope is not None else None)
    try:
        ctx._scope_admission = _direct_scope_admission(ctx)
    except PermissionError as exc:
        return {'success': False, 'code': str(exc)}
    # Durable server-created binding also recovers submit->enqueue interruptions.
    ctx.permission_result = {'background_binding': _background_binding(skill_info)}
    if not write_trace(ctx):
        return {'success': False, 'code': 'SKILL_EXECUTION_TRACE_FINALIZATION_FAILED'}
    return {'success': True, 'accepted': True, 'execution_id': ctx.execution_id,
            'status': 'pending', 'skill_id': skill_id}


def cancel_registered_skill(execution_id):
    from account.models import get_db
    conn = get_db()
    try:
        conn.execute("UPDATE skill_executions SET status='cancelled', error='USER_CANCELLED' "
                     "WHERE execution_id=? AND status IN ('pending','running')", (execution_id,))
        conn.commit()
    finally:
        conn.close()
    return query_executions(execution_id=execution_id, limit=1, strict=True)[0]


def run_registered_skill_job(execution_id):
    """Recover/consume exactly one submitted Skill using the existing leased worker.

    The durable Skill terminal receipt wins over a missing queue ack. No effectful
    or model-backed handlers are admitted, and no session credential is persisted.
    """
    from account.skills import execute_skill_api, get_skill_info
    from lumenis.system.collector.guard.task_queue import TaskQueue
    from lumenis.system.collector.guard.queue_worker import QueueWorker
    rows = query_executions(execution_id=execution_id, limit=1, strict=True)
    if not rows or not execution_id.startswith('skilljob_'):
        raise LookupError('registered background execution not found')
    row = rows[0]
    try:
        scope = _queued_execution_scope(row) if row['status'] in ('pending', 'running') else None
    except Exception:
        from account.models import get_db
        con = get_db()
        try:
            con.execute("UPDATE skill_executions SET status='rejected',error='BACKGROUND_SCOPE_BINDING_CHANGED' "
                        "WHERE execution_id=? AND status IN ('pending','running')", (execution_id,))
            con.commit()
        finally:
            con.close()
        return query_executions(execution_id=execution_id, limit=1, strict=True)[0]
    binding = json.loads(row.get('permission_json') or '{}').get('background_binding')
    if not binding and row['status'] in ('pending', 'running'):
        raise ValueError('background binding missing')
    queue = TaskQueue()
    try:
        queue_id = queue.enqueue_once('registered_skill', {
            'execution_id': execution_id, 'actor_id': row['user_id'],
            'product': row['product'], 'binding': binding,
        }, execution_id)
        operational = queue.get(queue_id)
        if row['status'] not in ('pending', 'running') and operational['status'] == 'running':
            # The business receipt is already terminal; reconcile the ack gap
            # with the current server-issued lease, without executing a handler.
            queue.ack(queue_id, run_id=operational['run_id'],
                      worker_id=operational['worker_id'], lease_owner=operational['lease_owner'])
            return row
        queue.reap_stale(60, task_id=queue_id)

        class SelectedQueue:
            def dequeue(self, **kwargs):
                return queue.dequeue(task_id=queue_id, **kwargs)
            def __getattr__(self, name):
                return getattr(queue, name)

        def processor(job):
            # Fence lease reclamation around this bounded local-only computation
            # and its existing trace transaction. Never hold it across a provider.
            with queue.attempt_guard(job['id'], run_id=job['run_id'],
                    worker_id=job['worker_id'], lease_owner=job['lease_owner']) as current:
                if not current:
                    return False
                live = query_executions(execution_id=execution_id, limit=1, strict=True)[0]
                if live['status'] not in ('pending', 'running'):
                    return True
                try:
                    current_scope = _queued_execution_scope(live)
                except Exception:
                    from account.models import get_db
                    con = get_db()
                    try:
                        con.execute("UPDATE skill_executions SET status='rejected',error='BACKGROUND_SCOPE_BINDING_CHANGED' "
                                    "WHERE execution_id=? AND status IN ('pending','running')", (execution_id,))
                        con.commit()
                    finally:
                        con.close()
                    return True
                if current_scope != scope:
                    raise PermissionError('BACKGROUND_SCOPE_BINDING_CHANGED')
                info = get_skill_info(live['skill_id'])
                expected = job['payload']
                if (live['user_id'] != expected['actor_id'] or live['product'] != expected['product']
                        or not info or _background_binding(info) != expected['binding']
                        or live['skill_id'] not in _BACKGROUND_INPUTS):
                    from account.models import get_db
                    con = get_db()
                    try:
                        con.execute("UPDATE skill_executions SET status='rejected',error='BACKGROUND_BINDING_CHANGED' "
                                    "WHERE execution_id=? AND status IN ('pending','running')", (execution_id,))
                        con.commit()
                    finally:
                        con.close()
                    return True
                from account.models import get_db
                con = get_db()
                try:
                    changed = con.execute("UPDATE skill_executions SET status='running' "
                        "WHERE execution_id=? AND status IN ('pending','running')", (execution_id,)).rowcount
                    con.commit()
                finally:
                    con.close()
                if not changed:
                    return True
                result = execute_skill_api(live['skill_id'], task=live['task'],
                    input_payload=json.loads(live['input_json'] or '{}'),
                    action_type=live['action_type'], user_id=live['user_id'],
                    product=live['product'], _execution_id=execution_id, scope=current_scope)
                persisted = query_executions(execution_id=execution_id, limit=1, strict=True)[0]
                if persisted['status'] in ('pending', 'running') and not result.get('success'):
                    # Account/registry rejection can occur before the chain starts.
                    from account.models import get_db
                    con = get_db()
                    try:
                        con.execute("UPDATE skill_executions SET status='rejected',error=? "
                                    "WHERE execution_id=? AND status IN ('pending','running')",
                                    (result.get('code', 'SKILL_EXECUTION_REJECTED'), execution_id))
                        con.commit()
                    finally:
                        con.close()
                return query_executions(execution_id=execution_id, limit=1, strict=True)[0]['status'] not in ('pending','running')
        QueueWorker(SelectedQueue(), processor).process_once()
    finally:
        queue.close()
    return query_executions(execution_id=execution_id, limit=1, strict=True)[0]


def start_registered_skill_job(execution_id):
    """Wake the existing leased worker for a selected durable request."""
    import threading
    def work():
        try:
            run_registered_skill_job(execution_id)
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).error(
                'Registered Skill worker interrupted; durable request can resume; details suppressed')
    thread = threading.Thread(target=work, name='registered-skill-worker', daemon=True)
    thread.start()
    return thread


def registered_background_handler(skill_id):
    if skill_id not in _BACKGROUND_INPUTS:
        raise ValueError('BACKGROUND_HANDLER_NOT_ALLOWED')
    # Explicit local dispatch prevents installed OSAI/MCP adapters from changing
    # the execution effects of a queued deterministic request.
    def run(ctx):
        if ctx.skill_id != skill_id:
            raise PermissionError('REGISTERED_HANDLER_BINDING_MISMATCH')
        return _execute_builtin_local(ctx, None)
    return run


_SOURCE_FREE_HANDLER_VERSION = 'registered-local-input-only-v1'


def validate_source_free_input(skill_id, payload):
    """Typed bounded input for the existing five local handlers; no Source refs."""
    if (skill_id not in _BACKGROUND_INPUTS or not isinstance(payload, dict)
            or set(payload) - _BACKGROUND_INPUTS[skill_id]):
        raise PermissionError('SOURCE_READER_UNBOUND')
    for key, value in payload.items():
        if key in {'width', 'height'}:
            if type(value) is not int or not 1 <= value <= 4096:
                raise PermissionError('SOURCE_FREE_INPUT_INVALID')
        elif not isinstance(value, str) or len(value) > 32768:
            raise PermissionError('SOURCE_FREE_INPUT_INVALID')
    if len(json.dumps(payload, ensure_ascii=False).encode()) > 65536:
        raise PermissionError('SOURCE_FREE_INPUT_INVALID')


def _record_source_free_execution(ctx, *, registry_binding):
    """Receipt for the existing bounded local handlers, never arbitrary adapters.

    Called only by the account owner after registered_background_handler ran.
    This is producer proof in the existing Evidence store, not a scope grant.
    """
    from account.models import get_db
    from lumenis.shared.evidence import store
    if ctx.status is not ExecutionStatus.COMPLETED:
        return
    if (ctx.skill_id not in _BACKGROUND_INPUTS or set(ctx.input_payload) - _BACKGROUND_INPUTS[ctx.skill_id]
            or ctx.action_type not in (ActionType.READ, ActionType.ANALYZE)):
        raise PermissionError('SOURCE_READER_UNBOUND')
    validate_source_free_input(ctx.skill_id, ctx.input_payload)
    from account.skills import get_skill_info
    info = get_skill_info(ctx.skill_id)
    if (str(info.get('runtime') or 'builtin').lower() != 'builtin'
            or str(info.get('source') or 'builtin').lower() != 'builtin'
            or _background_binding(info) != registry_binding):
        raise PermissionError('SOURCE_READER_UNBOUND')
    store.init_evidence_store()
    con = get_db()
    try:
        store.ensure_evidence_schema(con)
        row = dict(con.execute('SELECT * FROM skill_executions WHERE execution_id=?',
                               (ctx.execution_id,)).fetchone())
        material = {'contract': 'bounded-local-skill-result-v1', 'execution_id': ctx.execution_id,
            'actor_id': ctx.user_id, 'registry_binding': registry_binding,
            'trace_sha256': _execution_scope_digest(row),
            'agent_task_id': (ctx.request_context or {}).get('agent_task_id'),
            'producer': 'registered_background_handler', 'handler_version': _SOURCE_FREE_HANDLER_VERSION, 'source_use': 'user-input-only'}
        identifier = store.record_evidence(source='skill_execution_local_producer',
            feature_id=ctx.execution_id, product=ctx.product, inputs=material,
            outputs={'result_validation': 'bounded-local-producer'},
            provider=__name__, version='bounded-local-skill-result-v1', connection=con)
        receipt = con.execute('SELECT * FROM app_evidence_records WHERE id=?', (identifier,)).fetchone()
        if not receipt or not store.verify_evidence_record_integrity(receipt):
            raise PermissionError('SKILL_PRODUCER_RECEIPT_FAILED')
        con.commit()
    finally:
        con.close()


def read_source_free_execution(row, actor):
    """Reopen only producer-proven local outputs under current original owners."""
    from account.models import get_db
    from account.skills import get_skill_info
    from account.authorization import check_dual_domain_permission
    from lumenis.shared.evidence import store
    from lumenis.system.security.permission import _is_server_local_workspace_principal
    try:
        if row['skill_id'] not in _BACKGROUND_INPUTS or row['status'] != 'completed':
            return None
        inputs = json.loads(row.get('input_json') or '{}')
        if not isinstance(inputs, dict) or set(inputs) - _BACKGROUND_INPUTS[row['skill_id']]:
            return None
        validate_source_free_input(row['skill_id'], inputs)
        con = get_db()
        try:
            live = con.execute('SELECT * FROM skill_executions WHERE execution_id=?', (row['execution_id'],)).fetchone()
            proofs = con.execute("SELECT * FROM app_evidence_records WHERE source='skill_execution_local_producer' AND feature_id=? ORDER BY id DESC", (row['execution_id'],)).fetchall()
            user = con.execute('SELECT status FROM v4_users WHERE id=?', (row['user_id'],)).fetchone() if row['user_id'] else None
        finally:
            con.close()
        if not live or dict(live) != row:
            return None
        proof = next((dict(item) for item in proofs if store.verify_evidence_record_integrity(item)), None)
        if proof is None or proof['provider'] != __name__ or proof['version'] != 'bounded-local-skill-result-v1':
            return None
        material = json.loads(proof['inputs_json'])
        info = get_skill_info(row['skill_id'])
        if (material.get('contract') != 'bounded-local-skill-result-v1'
                or material.get('execution_id') != row['execution_id'] or material.get('actor_id') != row['user_id']
                or material.get('trace_sha256') != _execution_scope_digest(row)
                or material.get('producer') != 'registered_background_handler'
                or material.get('source_use') != 'user-input-only'
                or material.get('handler_version') != _SOURCE_FREE_HANDLER_VERSION
                or str(info.get('runtime') or 'builtin').lower() != 'builtin'
                or str(info.get('source') or 'builtin').lower() != 'builtin'
                or not info or info.get('status') != 'enabled'
                or material.get('registry_binding') != _background_binding(info)):
            return None
        if row['user_id'] is not None:
            if (not isinstance(actor, dict) or type(actor.get('id')) is not int
                    or actor['id'] != row['user_id'] or not user or user['status'] != 'active'
                    or not check_dual_domain_permission(actor['id'], row['product'], module=row['skill_id'], action='read')):
                return None
            if row['product'] != 'SYSTEM' and not verified_execution_scope(row, actor):
                return None
        else:
            if not _is_server_local_workspace_principal(actor):
                return None
            from ai_task_engine import get_task_engine
            from agent_runtime.task_binding import authorized_context, _current_binding, _digest
            task_id = material.get('agent_task_id')
            task = get_task_engine().get_task(task_id)
            context = authorized_context(task, actor)
            _current_binding(task_id, row['skill_id'])
            expected = 'agentstep_' + _digest({'task':task_id,'skill':row['skill_id'],'inputs':inputs})[:32]
            if (context['actor_id'] is not None or row['execution_id'] != expected
                    or row['task'] != task['user_input'] or row['product'] != context['product']):
                return None
        return row
    except Exception:
        return None
