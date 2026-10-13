# -*- coding: utf-8 -*-
"""Product Core API blueprints for the current application.

``lumenis_bp`` retains the ``/lumenis``-prefixed foundation and Skill Hub
routes. ``domain_api_bp`` defines the root-level product ``/api`` routes,
including current CTH/BMP and Shared workflow bindings. ``app.py`` registers
both blueprints; omitting them removes current product routes. Each route
composes its existing domain, Shared and SYSTEM owners rather than creating a
second owner in this module.
"""
import json
import time as _time
import uuid as _uuid
from flask import Blueprint, request, jsonify

lumenis_bp = Blueprint("lumenis", __name__, url_prefix="/lumenis")

# Domain API blueprint (root-level, no /lumenis prefix — for xujing-viz.js /api/* calls)
domain_api_bp = Blueprint("domain_api", __name__)

_SHARED_WORKSPACE_SCOPE_HEADER = "X-Lumenis-Workspace-Scope"
_SHARED_WORKSPACE_SCOPE_KEYS = frozenset({"scope_kind", "version"})
_SHARED_WORKSPACE_LEGACY_HEADERS = frozenset({
    "X-Domain-Id", "X-Product-Id", "X-Lumenis-Context-Mode",
    "X-Subject-ID", "X-Brand-Focus-ID", "X-Actor-ID", "X-Principal-Ref",
    "X-Project-ID", "X-Workspace-ID",
})
_SHARED_WORKSPACE_LEGACY_QUERY = frozenset({
    "domain_id", "domainid", "domain", "product_id", "productid", "product",
    "subject_id", "subjectid", "subject", "brand_focus_id", "brandfocusid",
    "brand_focus", "global_scope", "globalscope", "context_mode", "contextmode",
    "scope", "scope_kind", "scopekind", "version", "scope_version",
    "actor_id", "actorid", "principal_ref", "principalref",
    "project_id", "projectid", "workspace_id", "workspaceid",
})


def _reject_shared_workspace_legacy_selectors():
    if (any(name in request.headers for name in _SHARED_WORKSPACE_LEGACY_HEADERS)
            or any(key.lower() in _SHARED_WORKSPACE_LEGACY_QUERY for key in request.args)):
        raise ValueError("SHARED_WORKSPACE_SCOPE_MIXED")


def _parse_shared_workspace_scope_header():
    """Parse only the exact, actor-free Shared discriminator on a registered owner route."""
    if _SHARED_WORKSPACE_SCOPE_HEADER not in request.headers:
        return None
    values = request.headers.getlist(_SHARED_WORKSPACE_SCOPE_HEADER)
    if len(values) != 1 or not isinstance(values[0], str) or len(values[0].encode("utf-8")) > 256:
        raise ValueError("SHARED_WORKSPACE_SCOPE_INVALID")

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("SHARED_WORKSPACE_SCOPE_INVALID")
            result[key] = value
        return result

    try:
        scope = json.loads(
            values[0], object_pairs_hook=unique_pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("SHARED_WORKSPACE_SCOPE_INVALID")),
        )
        from lumenis.system.security.permission import validate_shared_workspace_scope
        scope = validate_shared_workspace_scope(scope)
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("SHARED_WORKSPACE_SCOPE_INVALID") from exc
    _reject_shared_workspace_legacy_selectors()
    return scope


def _shared_workspace_scope_body(scope):
    if not isinstance(scope, dict) or not (_SHARED_WORKSPACE_SCOPE_KEYS & set(scope)):
        return None
    _reject_shared_workspace_legacy_selectors()
    from lumenis.system.security.permission import validate_shared_workspace_scope
    return validate_shared_workspace_scope(scope)


def _internal_pitch_body():
    """Bounded JSON only; client identity and server file paths are forbidden."""
    import math
    if not request.is_json or (request.content_length or 0) > 1024 * 1024:
        raise ValueError("INTERNAL_PITCH_REQUEST_INVALID")
    raw = request.get_data(cache=True)
    if len(raw) > 1024 * 1024:
        raise ValueError("INTERNAL_PITCH_REQUEST_INVALID")

    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("INTERNAL_PITCH_REQUEST_INVALID")
            result[key] = value
        return result

    def floating(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("INTERNAL_PITCH_REQUEST_INVALID")
        return result

    try:
        data = json.loads(raw, object_pairs_hook=pairs, parse_float=floating,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("INTERNAL_PITCH_REQUEST_INVALID")))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("INTERNAL_PITCH_REQUEST_INVALID") from exc
    if not isinstance(data, dict):
        raise ValueError("INTERNAL_PITCH_REQUEST_INVALID")
    return data


def _internal_pitch_scope(data=None):
    header_scope = _parse_shared_workspace_scope_header()
    if data is not None:
        scope = data.get("scope")
        shared_scope = _shared_workspace_scope_body(scope)
        if shared_scope is not None:
            if request.args or (header_scope is not None and header_scope != shared_scope):
                raise ValueError("INTERNAL_PITCH_EXACT_SCOPE_REQUIRED")
            return shared_scope
        if header_scope is not None:
            raise ValueError("INTERNAL_PITCH_EXACT_SCOPE_REQUIRED")
    else:
        if header_scope is not None:
            if request.args:
                raise ValueError("INTERNAL_PITCH_EXACT_SCOPE_REQUIRED")
            return header_scope
        if set(request.args) != {"domain_id", "subject_id", "brand_focus_id", "global_scope"} or any(
                len(request.args.getlist(key)) != 1 for key in request.args):
            raise ValueError("INTERNAL_PITCH_REQUEST_INVALID")
        if request.args["global_scope"] not in {"true", "false"}:
            raise ValueError("INTERNAL_PITCH_EXACT_SCOPE_REQUIRED")
        scope = {"domain_id": request.args["domain_id"], "subject_id": request.args["subject_id"] or None,
                 "brand_focus_id": request.args["brand_focus_id"] or None,
                 "global_scope": request.args["global_scope"] == "true"}
    if (not isinstance(scope, dict) or set(scope) != {"domain_id", "subject_id", "brand_focus_id", "global_scope"}
            or type(scope["global_scope"]) is not bool):
        raise ValueError("INTERNAL_PITCH_EXACT_SCOPE_REQUIRED")
    return scope


def _internal_pitch_actor(action):
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import resolve_local_workspace_principal
    actor = resolve_local_workspace_principal(module="reports", action=action)
    if actor is None:
        actor = get_current_user(read_only=True)
    if actor is None:
        raise PermissionError("AUTH_REQUIRED")
    return actor


def _internal_pitch_local_access_allowed():
    """The explicitly open workspace still checks exact live Registry scope."""
    import re
    from lumenis.shared.reporting.saved_work import authorize
    from lumenis.system.security.permission import resolve_local_workspace_principal
    prefix = "/api/experience/creation/internal-pitches"
    routes = {
        "domain_api.api_internal_pitch_prepare": (prefix, "POST"),
        "domain_api.api_internal_pitch_read": (prefix + "/<task_id>", "GET"),
        "domain_api.api_internal_pitch_action": (prefix + "/<task_id>/<action>", "POST"),
        "domain_api.api_internal_pitch_export": (prefix + "/<task_id>/export", "GET"),
    }
    expected = routes.get(request.endpoint)
    if (expected is None or request.url_rule is None
            or request.url_rule.rule != expected[0] or request.method != expected[1]):
        return False
    path = request.path
    if request.endpoint == "domain_api.api_internal_pitch_prepare":
        path_valid = path == prefix
    elif request.endpoint == "domain_api.api_internal_pitch_read":
        path_valid = re.fullmatch(re.escape(prefix) + r"/task-pitch-[0-9a-f]{24}", path) is not None
    elif request.endpoint == "domain_api.api_internal_pitch_action":
        path_valid = (re.fullmatch(re.escape(prefix) + r"/task-pitch-[0-9a-f]{24}/(?:run|cancel)", path)
                      is not None)
    else:
        path_valid = re.fullmatch(re.escape(prefix) + r"/task-pitch-[0-9a-f]{24}/export", path) is not None
    if not path_valid:
        return False
    action = "read" if request.method == "GET" else "write"
    actor = resolve_local_workspace_principal(module="reports", action=action)
    if actor is None:
        return False
    try:
        data = _internal_pitch_body() if request.method == "POST" else None
        scope = _internal_pitch_scope(data)
        if scope.get("scope_kind") == "shared_workspace":
            from lumenis.shared.content_creation.internal_pitch import _context
            _context(actor, scope, action)
        else:
            authorize(actor, scope, action=action)
        return True
    except (ValueError, PermissionError):
        return False


def _internal_pitch_response(call):
    from flask import current_app
    try:
        result = call()
        if not isinstance(result, dict):
            return result
        response = jsonify({"ok": True, "contract": "lumenis.internal-pitch.v1", "result": result})
        response.headers["Cache-Control"] = "no-store"
        return response, 202 if result["state"] == "pending" else 200
    except (ValueError, PermissionError, LookupError, RuntimeError) as exc:
        import re
        code = str(exc)
        if re.fullmatch(r"[A-Z_0-9]{1,100}", code) is None:
            current_app.logger.exception("internal pitch owner failed")
            code = "INTERNAL_PITCH_OWNER_FAILED"
        if code == "AUTH_REQUIRED":
            status = 401
        elif "UNAVAILABLE" in code:
            status = 503
        elif isinstance(exc, PermissionError) or "PERMISSION" in code or "DENIED" in code:
            status = 403
        elif isinstance(exc, LookupError):
            status = 404
        elif any(term in code for term in ("CONFLICT", "CANCELLED", "NOT_RUNNABLE", "STILL_ACTIVE")):
            status = 409
        elif isinstance(exc, RuntimeError) or any(term in code for term in ("INTEGRITY", "MISSING", "OWNER_FAILED")):
            status = 503
        else:
            status = 400
        response = jsonify({"ok": False, "code": code})
        response.headers["Cache-Control"] = "no-store"
        return response, status
    except Exception:
        current_app.logger.exception("internal pitch owner unavailable")
        return jsonify({"ok": False, "code": "INTERNAL_PITCH_OWNER_UNAVAILABLE"}), 503


@domain_api_bp.post("/api/experience/creation/internal-pitches")
def api_internal_pitch_prepare():
    def execute():
        from lumenis.shared.content_creation.internal_pitch import prepare_internal_pitch
        data = _internal_pitch_body()
        allowed = {"scope", "manuscript", "shot_plan", "request_id", "citations", "work_id",
                   "previous_artifact_id", "expected_draft_digest", "profile", "input_manifest", "upstream_ref"}
        required = {"scope", "manuscript", "request_id"}
        if "profile" not in data:
            required.add("shot_plan")
        if not required.issubset(data) or set(data) - allowed:
            raise ValueError("INTERNAL_PITCH_REQUEST_INVALID")
        scope = _internal_pitch_scope(data)
        return prepare_internal_pitch(actor=_internal_pitch_actor("write"), scope=scope,
                                      **{key: value for key, value in data.items() if key != "scope"})
    return _internal_pitch_response(execute)


@domain_api_bp.get("/api/experience/creation/internal-pitches/<task_id>")
def api_internal_pitch_read(task_id):
    def execute():
        from lumenis.shared.content_creation.internal_pitch import read_internal_pitch
        return read_internal_pitch(task_id, actor=_internal_pitch_actor("read"), scope=_internal_pitch_scope())
    return _internal_pitch_response(execute)


@domain_api_bp.post("/api/experience/creation/internal-pitches/<task_id>/<action>")
def api_internal_pitch_action(task_id, action):
    def execute():
        from lumenis.shared.content_creation.internal_pitch import run_internal_pitch, cancel_internal_pitch
        if action not in {"run", "cancel"}:
            raise LookupError("INTERNAL_PITCH_ACTION_NOT_FOUND")
        data = _internal_pitch_body()
        if set(data) != {"scope"}:
            raise ValueError("INTERNAL_PITCH_REQUEST_INVALID")
        return {"run": run_internal_pitch, "cancel": cancel_internal_pitch}[action](
            task_id, actor=_internal_pitch_actor("write"), scope=_internal_pitch_scope(data))
    return _internal_pitch_response(execute)


@domain_api_bp.get("/api/experience/creation/internal-pitches/<task_id>/export")
def api_internal_pitch_export(task_id):
    def execute():
        import io
        from flask import send_file
        from lumenis.shared.content_creation.internal_pitch import download_internal_pitch
        result = download_internal_pitch(task_id, actor=_internal_pitch_actor("read"), scope=_internal_pitch_scope())
        response = send_file(io.BytesIO(result["content"]), mimetype=result["media_type"],
                             as_attachment=True, download_name=result["filename"], max_age=0)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Artifact-ID"] = result["action_receipt"]["output"]["artifact_id"]
        response.headers["X-Artifact-SHA256"] = result["sha256"]
        return response
    return _internal_pitch_response(execute)


def _business_work_body():
    try:
        return _internal_pitch_body()
    except ValueError as exc:
        raise ValueError("BUSINESS_WORK_REQUEST_INVALID") from exc


def _business_work_binding(operation):
    """Compose existing domain and creation readers with the current server actor."""
    from api_dual_domain import BusinessDecisionWorkflow, authorize_business_work_request
    from experience_runtime import _source_brief_context
    from lumenis.shared.content_creation.internal_pitch import read_internal_pitch
    from lumenis.shared.reporting.source_brief_job import _scope_material

    actor_ref, _audit, material, actor = _source_brief_context(
        "read" if operation == "read" else "write", include_actor=True,
    )
    scope = _scope_material(**material)
    if scope["global"]:
        raise PermissionError("BUSINESS_WORK_FOCUS_REQUIRED")
    service = BusinessDecisionWorkflow(internal_action_reader=read_internal_pitch, action_actor=actor)
    authorize = lambda selected: authorize_business_work_request(
        selected, actor_ref=actor_ref, scope=scope,
    )
    return service, actor_ref, scope, authorize


def _business_work_local_access_allowed():
    """Open entry uses the same sealed loopback principal and exact live scope."""
    from lumenis.system.security.permission import resolve_local_workspace_principal
    expected = {
        "domain_api.api_business_work_prepare": "POST",
        "domain_api.api_business_work_read": "GET",
        "domain_api.api_business_work_advance": "POST",
    }
    if expected.get(request.endpoint) != request.method:
        return False
    action = "read" if request.method == "GET" else "write"
    if resolve_local_workspace_principal(module="reports", action=action) is None:
        return False
    try:
        _business_work_binding("read" if action == "read" else "prepare")
        return True
    except (ValueError, LookupError, PermissionError, RuntimeError):
        return False


def _business_work_response(call):
    from flask import current_app
    try:
        result = call()
        response = jsonify({"ok": True, "result": result, "publish_status": "not_performed"})
        response.headers["Cache-Control"] = "no-store"
        return response
    except (ValueError, LookupError, PermissionError, RuntimeError) as exc:
        import re
        code = str(exc)
        if re.fullmatch(r"[A-Z_0-9]{1,100}", code) is None:
            code = "BUSINESS_WORK_UNAVAILABLE"
        status = 401 if code == "AUTH_REQUIRED" else 403 if (
            isinstance(exc, PermissionError) or code == "CONTENT_SCOPE_DENIED"
        ) else (
            404 if isinstance(exc, LookupError) else 409 if code in {
                "BUSINESS_WORK_REVISION_CONFLICT", "BUSINESS_WORK_SUBMISSION_CONFLICT",
            } else 503 if isinstance(exc, RuntimeError) else 400
        )
        response = jsonify({"ok": False, "code": code, "publish_status": "not_performed"})
        response.headers["Cache-Control"] = "no-store"
        return response, status
    except Exception:
        current_app.logger.exception("business work owner unavailable")
        return jsonify({"ok": False, "code": "BUSINESS_WORK_UNAVAILABLE"}), 503


@domain_api_bp.post("/api/experience/business-works")
def api_business_work_prepare():
    def execute():
        data = _business_work_body()
        common = {"submission_id", "kind"}
        source_fields = common | {"source_job_id", "question"}
        case_fields = common | {"case_id"}
        optional = {"options", "planning_constraints"}
        required = case_fields if "case_id" in data else source_fields
        if not required.issubset(data) or set(data) - required - optional:
            raise ValueError("BUSINESS_WORK_REQUEST_INVALID")
        service, actor_ref, scope, authorize = _business_work_binding("prepare")
        if "case_id" in data:
            return service.prepare_from_case(actor_ref=actor_ref, scope=scope, authorize=authorize, **data)
        return service.prepare(actor_ref=actor_ref, scope=scope, authorize=authorize, **data)
    return _business_work_response(execute)


@domain_api_bp.get("/api/experience/business-works/<work_id>")
def api_business_work_read(work_id):
    def execute():
        if (set(request.args) - {"revision"}
                or any(len(request.args.getlist(key)) != 1 for key in request.args)
                or ("revision" in request.args and not request.args["revision"])):
            raise ValueError("BUSINESS_WORK_REQUEST_INVALID")
        service, actor_ref, scope, authorize = _business_work_binding("read")
        revision = request.args.get("revision")
        return service.reopen(work_id, actor_ref=actor_ref, scope=scope, authorize=authorize,
                              revision=revision)
    return _business_work_response(execute)


@domain_api_bp.post("/api/experience/business-works/<work_id>/<operation>")
def api_business_work_advance(work_id, operation):
    def execute():
        if operation not in {"choose", "adopt", "cancel", "interrupt", "resume", "action", "outcome", "outcome_unknown",
                             "save-request", "save"}:
            raise LookupError("BUSINESS_WORK_OPERATION_NOT_FOUND")
        data = _business_work_body()
        if operation in {"save-request", "save"}:
            required = {"request_id", "expected_revision", "citations"}
            optional = {"previous_artifact_id", "expected_draft_digest"}
            if (not required.issubset(data) or set(data) - required - optional
                    or (("previous_artifact_id" in data) != ("expected_draft_digest" in data))
                    or not isinstance(data["expected_revision"], str)
                    or not isinstance(data["request_id"], str)
                    or not isinstance(data["citations"], list)):
                raise ValueError("BUSINESS_WORK_REQUEST_INVALID")
            service, actor_ref, scope, authorize = _business_work_binding("save")
            save = service.save_result_request if operation == "save-request" else service.save_result
            return save(work_id, actor_ref=actor_ref, scope=scope, authorize=authorize, **data)
        if set(data) != {"submission_id", "payload", "expected_revision"}:
            raise ValueError("BUSINESS_WORK_REQUEST_INVALID")
        service, actor_ref, scope, authorize = _business_work_binding(operation)
        return service.advance(work_id, actor_ref=actor_ref, scope=scope, operation=operation,
                               authorize=authorize, **data)
    return _business_work_response(execute)


def _context_error(code, message, status):
    return jsonify({"ok": False, "code": code, "error": message}), status


def _context_selection_from_scope(domain_id, subject_id):
    """Resolve and authorize one registered Subject or BrandFocus selection."""
    from subject_context import ContextSelection
    from subject_registry import (
        SubjectRegistryUnavailableError,
        SubjectValidationError,
        get_subject_by_id,
        normalize_domain,
    )
    from lumenis.system.security.permission import (
        check_actor_scope_permission, local_workspace_read_allowed,
    )
    from lumenis.auth.service import get_current_user

    local_read = local_workspace_read_allowed("subject_registry")
    actor = None if local_read else get_current_user()
    if not local_read and (not isinstance(actor, dict) or type(actor.get("id")) is not int):
        return None, _context_error("AUTH_REQUIRED", "需要有效账号会话", 401)
    try:
        normalized_domain = normalize_domain(domain_id)
        if normalized_domain not in {"CTH", "BMP"}:
            raise SubjectValidationError("domain_id 仅支持 CTH 或 BMP")
        if not isinstance(subject_id, str) or not subject_id or subject_id != subject_id.strip():
            raise SubjectValidationError("subject_id 无效")
        subject = get_subject_by_id(normalized_domain, subject_id)
    except SubjectValidationError as exc:
        return None, _context_error("INVALID_CONTEXT", str(exc), 400)
    except SubjectRegistryUnavailableError:
        return None, _context_error(
            "SUBJECT_REGISTRY_UNAVAILABLE", "主体注册表暂不可用", 503
        )
    except Exception:
        return None, _context_error(
            "SUBJECT_REGISTRY_UNAVAILABLE", "主体注册表暂不可用", 503
        )

    if subject is None:
        return None, _context_error("SUBJECT_NOT_FOUND", "主体未在有效注册表中", 404)

    is_cth = normalized_domain == "CTH"
    expected_type = "company" if is_cth else "brand"
    brand_focus_id = subject.get("brand_focus_id")
    if subject.get("subject_type") != expected_type or (
        not is_cth and (not isinstance(brand_focus_id, str) or not brand_focus_id)
    ):
        return None, _context_error("INVALID_CONTEXT_SCOPE", "主体类型与业务域不匹配", 400)

    try:
        decision = None if local_read else check_actor_scope_permission(
            actor,
            domain_id=normalized_domain,
            action="read",
            module="subject_registry",
            subject_id=subject_id if is_cth else None,
            brand_focus_id=None if is_cth else brand_focus_id,
        )
    except Exception:
        return None, _context_error(
            "AUTHORIZATION_UNAVAILABLE", "主体范围授权暂不可用", 503
        )
    if not local_read and decision.verification_state != "verified":
        return None, _context_error(
            "AUTHORIZATION_UNAVAILABLE", "主体范围授权暂不可用", 503
        )
    if not local_read and not decision.allowed:
        return None, _context_error(
            "SUBJECT_SCOPE_DENIED", "没有读取该主体范围的权限", 403
        )

    return ContextSelection.focus(
        domain_id=normalized_domain,
        subject_id=subject_id,
        brand_focus_id=None if is_cth else brand_focus_id,
    ), None


def _context_envelope(selection):
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import local_workspace_read_allowed
    from subject_registry import DOMAINS, get_subject_by_id

    local_read = local_workspace_read_allowed("subject_registry")
    actor = None if local_read else get_current_user()
    domains = []
    try:
        if local_read:
            domains = list(DOMAINS)
        elif isinstance(actor, dict) and type(actor.get("id")) is int:
            from account.authorization import check_dual_domain_permission
            domains = [domain for domain in DOMAINS if check_dual_domain_permission(
                actor["id"], "ZBMP" if domain == "BMP" else "CTH",
                module="subject_registry", action="read",
            )]
        context = selection.to_dict()
        if selection.mode == "FOCUS":
            subject = get_subject_by_id(selection.domain_id, selection.subject_id)
            if subject is None:
                return _context_error("SUBJECT_NOT_FOUND", "主体未在有效注册表中", 404)
            context["display_name"] = {
                locale: subject[key] for locale, key in (("zh-CN", "name_zh"), ("en", "name_en"))
                if subject.get(key)
            }
    except Exception:
        return _context_error("CONTEXT_UNAVAILABLE", "工作范围暂不可用，请重试", 503)
    return jsonify({
        "ok": True,
        "contract": "lumenis.context.v1",
        "selection_only": True,
        "context": context,
        "authorized_domains": [
            {"id": domain, "name": DOMAINS[domain]["name"], "product": DOMAINS[domain]["product"]}
            for domain in domains
        ],
        "access_mode": "local_read_only" if local_read else "actor" if actor else "selection_only",
    })


@domain_api_bp.route("/api/settings/context", methods=["GET", "PUT", "DELETE"])
def api_settings_context():
    """Expose selection-only context; data routes reauthorize every use."""
    from subject_context import ContextSelection

    if request.method == "DELETE":
        # Clearing focus only returns the static GLOBAL selection. It reads no
        # business data and performs no persistent or external effect.
        return _context_envelope(ContextSelection.global_all())

    if request.method == "PUT":
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or set(payload) != {
            "mode", "domain_id", "subject_id"
        } or payload.get("mode") != "FOCUS":
            return _context_error("INVALID_CONTEXT", "需要合法的 FOCUS 主体选择", 400)
        selection, error = _context_selection_from_scope(
            payload.get("domain_id"), payload.get("subject_id")
        )
        return error if error is not None else _context_envelope(selection)

    mode = request.headers.get("X-Lumenis-Context-Mode", "GLOBAL_ALL")
    domain_id = request.headers.get("X-Domain-Id")
    subject_id = request.headers.get("X-Subject-ID")
    if mode == "GLOBAL_ALL":
        if domain_id or subject_id:
            return _context_error(
                "INVALID_CONTEXT", "GLOBAL_ALL 不能携带聚焦主体", 400
            )
        return _context_envelope(ContextSelection.global_all())
    if mode != "FOCUS" or not domain_id or not subject_id:
        return _context_error("INVALID_CONTEXT", "聚焦上下文不完整", 400)
    selection, error = _context_selection_from_scope(domain_id, subject_id)
    return error if error is not None else _context_envelope(selection)



# Shared Skill JSON API (App transport)
# ========== Skill Hub API（Cross-Core Adapter，ZBC 不维护独立 Skill Truth） ==========

from lumenis_skill_adapter import get_skill_adapter

# Skill 调用记录（内存级 runtime cache，不写数据库，保留最近 100 条）
# 注意：这不是永久历史，仅作 runtime trace。UI 无持久化证据时显示 NO_DATA。
_skill_invocations = []


@lumenis_bp.route("/api/skills/status")
def skill_status():
    """Skill Registry 状态 —— 从 OSAI Canonical Registry 真实读取。

    ZBC 不再维护独立 _LUMENIS_SKILLS 硬编码 Truth。
    OSAI 不可用时返回 UNAVAILABLE，不造假数据。
    """
    adapter = get_skill_adapter()
    snap = adapter.get_registry_snapshot()

    if not snap["connected"]:
        return jsonify({
            "total": 0,
            "running": 0,
            "sync_status": "UNAVAILABLE",
            "skills": [],
            "canonical_source": "OSAI Canonical Registry",
            "connection_status": "UNAVAILABLE",
            "error": snap.get("error"),
            "last_sync": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        })

    # 只返回 IMPLEMENTED + PARTIAL 的 Skill 给前端（PLANNED 不显示为可用）
    visible_skills = [s for s in snap["skills"]
                      if s["status"] in ("IMPLEMENTED", "PARTIAL")]

    return jsonify({
        "total": snap.get("implemented_count", 0),
        "running": 0,
        "sync_status": "CONNECTED",
        "skills": visible_skills,
        "canonical_source": "OSAI Canonical Registry",
        "connection_status": "CONNECTED",
        "implemented_count": snap.get("implemented_count", 0),
        "partial_count": snap.get("partial_count", 0),
        "planned_count": snap.get("planned_count", 0),
        "registry_total": snap.get("total", 0),
        "last_sync": _time.strftime("%Y-%m-%dT%H:%M:%S"),
    })


@lumenis_bp.route("/api/skills/invoke", methods=["POST"])
def skill_invoke():
    """Skill 调用 —— ZBC → Cross-Core Adapter → OSAI SkillInvoker。

    完整链：Workspace → Task → Skill Selector → Manifest → Permission →
    Context → Engine → Provider → Execution → Evidence → Evaluation → Trace → Result

    当前层级：ZBC 记录调用请求（ACCEPTED），实际执行由 OSAI 完成。
    任何一层不存在返回 PARTIALLY_CONNECTED，不伪造 COMPLETED。
    """
    data = request.get_json(silent=True) or {}
    skill_id = data.get("skill_id", "")
    task = data.get("task", "manual invoke")
    workspace = data.get("workspace", "unknown")

    # 从 OSAI Canonical Registry 获取 Skill 定义（唯一 Truth）
    adapter = get_skill_adapter()
    skill_info = adapter.get_skill(skill_id)

    if not skill_info.get("found"):
        return jsonify({
            "status": "FAILED",
            "error": "Unknown skill: %s" % skill_id,
            "registry_status": skill_info.get("status", "UNKNOWN"),
        }), 404

    skill = skill_info["skill"]

    # 检查 Skill 是否真实可执行
    if skill["status"] != "IMPLEMENTED":
        return jsonify({
            "status": "BLOCKED",
            "error": "Skill not implemented: %s (status=%s)" % (skill_id, skill["status"]),
            "skill_status": skill["status"],
        }), 400

    import os as _os
    invocation_id = "INV-" + _uuid.uuid4().hex[:10]
    fallback_trace = "TRACE-" + _uuid.uuid4().hex[:10]
    skill_version = skill.get("version", "0.0.0")

    # 真实执行：ZBC → Cross-Core Adapter → OSAI SkillInvoker
    # Permission(fail-close) → Context → Engine → Provider → Evidence(落盘) → Evaluation
    exec_res = adapter.invoke_skill(
        task=task, skill_id=skill_id, workspace=workspace,
        skill_version=skill_version,
    )

    base = {
        "invocation_id": invocation_id,
        "skill_id": skill_id,
        "skill_name": skill.get("name", ""),
        "skill_version": skill_version,
        "task": task,
        "workspace": workspace,
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        "permissions_required": skill.get("permissions", []),
        "execution_core": "OSAI Intelligence Core",
        "canonical_source": "OSAI Canonical Registry",
    }

    if not exec_res.get("connected"):
        # OSAI 不可用/超时：诚实兜底为已受理，绝不伪造 COMPLETED
        record = dict(base, **{
            "trace_id": fallback_trace,
            "status": "ACCEPTED",
            "execution_status": "PARTIALLY_CONNECTED",
            "evidence_status": "NO_EVIDENCE",
            "evaluation_status": "NO_DATA",
            "error": exec_res.get("error"),
            "note": "OSAI runtime unavailable; invocation accepted only, not executed.",
        })
    else:
        osai = exec_res["osai"] or {}
        ost = osai.get("status", "UNKNOWN")
        trace_id = osai.get("trace_id", fallback_trace)
        ev_id = osai.get("evidence_id")
        eval_id = osai.get("evaluation_id")
        perm = osai.get("permission_check")
        result = osai.get("result") or {}
        if ost == "SUCCESS":
            record = dict(base, **{
                "trace_id": trace_id, "status": "COMPLETED",
                "execution_status": "CONNECTED",
                "evidence_status": "EVIDENCE_CREATED" if ev_id else "NO_EVIDENCE",
                "evaluation_status": "EVALUATION_CREATED" if eval_id else "NO_DATA",
                "evidence_id": ev_id, "evaluation_id": eval_id,
                "engine_id": osai.get("engine_id"), "model_id": osai.get("model_id"),
                "result": result, "permission_check": perm,
            })
        elif ost == "BLOCKED":
            record = dict(base, **{
                "trace_id": trace_id, "status": "BLOCKED",
                "execution_status": "CONNECTED",
                "evidence_status": "NO_EVIDENCE",
                "evaluation_status": "NO_DATA",
                "permission_check": perm,
                "error": osai.get("error", "PERMISSION_DENIED"),
            })
        else:  # FAILED / UNKNOWN —— 链路连通但执行失败，错误同样进 EvidenceChain
            record = dict(base, **{
                "trace_id": trace_id, "status": "FAILED",
                "execution_status": "CONNECTED",
                "evidence_status": "EVIDENCE_CREATED" if ev_id else "NO_EVIDENCE",
                "evaluation_status": "NO_DATA",
                "evidence_id": ev_id, "evaluation_id": eval_id,
                "engine_id": osai.get("engine_id"), "model_id": osai.get("model_id"),
                "permission_check": perm, "error": osai.get("error"),
            })

    # 持久化到独立 JSONL（不写生产 monitor.db，不改 DB schema）
    try:
        ddir = _os.environ.get("LUMENIS_RUNTIME_DIR") or _os.path.join(
            _os.path.dirname(_os.path.abspath(__file__)), "data", "lumenis")
        _os.makedirs(ddir, exist_ok=True)
        with open(_os.path.join(ddir, "skill_invocations.jsonl"),
                  "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception as persist_err:
        record["persist_warning"] = str(persist_err)

    _skill_invocations.append(record)
    if len(_skill_invocations) > 100:
        _skill_invocations.pop(0)

    return jsonify(record)


@lumenis_bp.route("/api/skills/invocations")
def skill_invocations_history():
    """Skill 调用历史 —— 读取持久化 JSONL（重启不丢），非内存假历史。"""
    import os as _os
    limit = request.args.get("limit", default=50, type=int)
    skill_id = request.args.get("skill_id", default="")
    ddir = _os.environ.get("LUMENIS_RUNTIME_DIR") or _os.path.join(
        _os.path.dirname(_os.path.abspath(__file__)), "data", "lumenis")
    fpath = _os.path.join(ddir, "skill_invocations.jsonl")
    rows = []
    try:
        if _os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if skill_id and rec.get("skill_id") != skill_id:
                        continue
                    rows.append(rec)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "records": []}), 500
    rows = rows[-limit:]
    rows.reverse()
    return jsonify({
        "ok": True, "count": len(rows), "records": rows,
        "persistence": "file_based:data/lumenis/skill_invocations.jsonl",
    })


@lumenis_bp.route("/api/skills/sync", methods=["POST"])
def skill_sync():
    """GitHub Skill Manifest 同步 —— 真实检查 GitHub → Manifest → Registry。

    不固定返回 SYNCED。实际检测：
    1. OSAI Canonical Registry 是否可用
    2. Manifest 文件是否存在
    3. 已实现 Skill 与 Manifest 是否有冲突
    发现 conflict 返回 CONFLICT。
    """
    adapter = get_skill_adapter()
    sync_result = adapter.check_sync_status()

    return jsonify({
        "status": sync_result["sync_status"],
        "synced_count": sync_result["synced_count"],
        "conflicts": sync_result["conflict_count"],
        "conflict_detail": {
            "missing_manifest": sync_result.get("missing_manifest", []),
            "unimplemented_manifest": sync_result.get("unimplemented_manifest", []),
        },
        "manifest_files": sync_result.get("manifest_files", 0),
        "implemented_count": sync_result.get("implemented_count", 0),
        "last_sync": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        "canonical_source": "OSAI Canonical Registry / skills/manifests/",
        "error": sync_result.get("error"),
        "message": (
            "Sync verified. No conflicts."
            if sync_result["sync_status"] == "SYNCED"
            else "Conflicts detected. Manual review required."
            if sync_result["sync_status"] == "CONFLICT"
            else "OSAI unavailable. Cannot verify sync."
        ),
    })

@lumenis_bp.route("/api/intelligence/evidence")
def api_intelligence_evidence():
    """Intelligence Evidence — 读取 OSAI 持久化 Evidence Chain。

    Cross-Core: 通过 subprocess 调用 OSAI evidence reader，
    不直接访问 OSAI 内部模块。
    """
    import subprocess
    import json
    import os

    osai_root = os.environ.get("OSAI_ROOT") or get_skill_adapter()._osai_root or ""
    reader_script = os.path.join(osai_root, "scripts", "list_evidence.py") if osai_root else ""

    # Fallback: direct file read if script not available
    evidence_dir = os.path.join(osai_root, "evidence", "chains")
    chains = []
    try:
        if os.path.exists(evidence_dir):
            for fname in sorted(os.listdir(evidence_dir), reverse=True)[:50]:
                if fname.endswith(".json"):
                    fpath = os.path.join(evidence_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as fh:
                            chains.append(json.load(fh))
                    except Exception:
                        pass
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "count": 0, "chains": []}), 500

    return jsonify({
        "ok": True,
        "count": len(chains),
        "chains": chains,
        "source": "osai_evidence_chains",
        "persistence": "file_based"
    })




def _get_domain_context():
    """Resolve an explicit domain selection without inventing a CTH default.

    The shared request resolver owns header/session/domain_id precedence. The
    old ``zbc_domain`` cookie and ``domain`` query key remain accepted as
    compatibility selectors only when they agree with that resolved identity.
    Selection does not grant access; each data path still performs its owner
    Permission check.
    """
    from domain_isolation import DomainContext, get_domain_context, set_domain_context
    from subject_context import (
        get_request_brand, resolve_request_identity, set_thread_context,
    )

    domain, product = resolve_request_identity()
    legacy_values = []
    cookie_domain = request.cookies.get("zbc_domain")
    if cookie_domain is not None:
        legacy_values.append(cookie_domain)
    if "domain" in request.args:
        values = request.args.getlist("domain")
        if len(values) != 1:
            raise ValueError("INVALID_DOMAIN_IDENTITY")
        legacy_values.append(values[0])

    legacy_identity = None
    for value in legacy_values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("INVALID_DOMAIN_IDENTITY")
        from domain_isolation import resolve_domain_identity
        candidate = resolve_domain_identity(value)
        if legacy_identity is not None and legacy_identity != candidate:
            raise ValueError("DOMAIN_IDENTITY_CONFLICT")
        legacy_identity = candidate

    if domain and legacy_identity and (domain, product) != legacy_identity:
        raise ValueError("DOMAIN_IDENTITY_CONFLICT")
    if not domain and legacy_identity:
        domain, product = legacy_identity

    bound = get_domain_context()
    if bound and bound.domain_id:
        if domain and (bound.domain_id, bound.product_id) != (domain, product):
            raise ValueError("DOMAIN_CONTEXT_CONFLICT")
        if not domain:
            domain, product = bound.domain_id, bound.product_id

    if domain and (not bound or not bound.domain_id):
        # Compatibility selectors bind only a validated domain. Focus is kept
        # only when it was explicitly supplied in request metadata.
        subject_id = request.headers.get("X-Subject-ID", "")
        brand_key = get_request_brand() or ""
        context = DomainContext(domain_id=domain, product_id=product,
                                subject_id=subject_id, brand_key=brand_key)
        set_domain_context(context)
        set_thread_context(context.to_subject_context())
    return domain or None


def _domain_api_selection_only(domain=None):
    return {
        "ok": True,
        "domain": domain,
        "mode": "GLOBAL_ALL" if domain is None else "DOMAIN_SELECTED",
        "data_state": "DOMAIN_UNSELECTED" if domain is None else "SCOPE_NOT_READ",
        "selection_only": True,
    }


def _domain_api_canonical(domain, module):
    """Use the existing scoped Canonical and Permission owners for API reads."""
    import api_dual_domain
    from domain_isolation import get_domain_context

    if domain == "system":
        raise ValueError("BUSINESS_DOMAIN_REQUIRED")
    if domain == "cth":
        connection = api_dual_domain._get_conn()
        try:
            result = api_dual_domain.read_cth_scoped_canonical(
                connection, module=module, limit=100,
            )
        finally:
            connection.close()
        return result["scope"], result["canonical"]

    if domain != "zbmp":
        raise ValueError("BUSINESS_DOMAIN_REQUIRED")

    # Reuse the existing experience scope owner. It performs fresh Permission
    # checks for GLOBAL_ALL and exact registered BrandFocus requests.
    from experience_runtime import _bmp01_read_scope
    binding, error = _bmp01_read_scope()
    if error is not None:
        response, status = error
        raise _DomainApiScopeError(response.get_json().get("code", "SCOPE_UNAVAILABLE"), status)
    current = get_domain_context()
    if current and (current.subject_id or current.brand_key):
        if (binding.get("canonical_scope") != "FOCUS"
                or binding.get("subject_id") != current.subject_id):
            raise _DomainApiScopeError("FOCUS_SCOPE_HEADER_REQUIRED", 400)

    from lumenis.shared.database import get_repository
    import canonical_data
    connection = get_repository().connect()
    try:
        result = canonical_data.list_scoped_canonical(
            connection, product_id="ZBMP",
            brand_focus_id=binding.get("brand_focus_id"), limit=100,
        )
    finally:
        connection.close()
    scope = {
        "mode": binding["canonical_scope"],
        "domain_id": binding["domain_id"],
        "product_id": binding["product_id"],
        "subject_id": binding.get("subject_id"),
        "brand_focus_id": binding.get("brand_focus_id"),
        "global": binding["canonical_scope"] == "GLOBAL_ALL",
    }
    return scope, result


class _DomainApiScopeError(RuntimeError):
    def __init__(self, code, status):
        super().__init__(code)
        self.code = code
        self.status = status



# ---------- Domain Data APIs (real data binding for xujing-viz.js) ----------

@domain_api_bp.route("/api/domain/overview")
def api_domain_overview():
    """Compatibility overview backed by the current scoped Canonical owner."""
    try:
        domain = _get_domain_context()
        if domain is None:
            return jsonify(_domain_api_selection_only())
        scope, canonical = _domain_api_canonical(domain, "content")
        records = canonical.get("records", [])
        stats = {
            "returned_records": len(records),
            "candidate_count": canonical.get("candidate_count"),
            "truncated": canonical.get("truncated"),
        }
        for field, output in (("sentiment", "sentiment_distribution"),
                              ("risk_level", "risk_distribution"),
                              ("source_platform", "platform_distribution")):
            counts = {}
            for row in records:
                value = row.get(field)
                if isinstance(value, str) and value.strip():
                    counts[value] = counts.get(value, 0) + 1
            stats[output] = counts
        result = {
            "ok": True,
            "domain": domain,
            "domain_name": "CTH / LUMENIS Commerce Operations" if domain == "cth" else "BMP / LUMENIS Brand & Market" if domain == "zbmp" else "SYSTEM",
            "stats": stats,
            "scope": scope,
            "canonical_records": records,
            "data_state": "READY" if records else "NOT_COLLECTED",
            "overview": {
                "trend": [],  # populated by /api/metric-trend for specific entities
                "time_range": "all",
            },
            "data_source": "permission-checked canonical_data.list_scoped_canonical",
        }
        return jsonify(result)
    except _DomainApiScopeError as e:
        return jsonify({"ok": False, "code": e.code}), e.status
    except ValueError as e:
        return jsonify({"ok": False, "code": str(e)}), 400
    except Exception as e:
        if hasattr(e, "code") and hasattr(e, "status"):
            return jsonify({"ok": False, "code": e.code}), e.status
        return jsonify({"ok": False, "code": "DOMAIN_OVERVIEW_UNAVAILABLE", "error": str(e)}), 503


@domain_api_bp.route("/api/domain/brands")
def api_domain_brands():
    """Compatibility brand projection from the authorized Canonical slice."""
    try:
        domain = _get_domain_context()
        if domain is None:
            return jsonify({**_domain_api_selection_only(), "brands": [], "total": None})
        scope, canonical = _domain_api_canonical(domain, "content")
        counts = {}
        for row in canonical.get("records", []):
            name = row.get("brand_focus_id") if domain == "zbmp" else row.get("brand_key")
            if isinstance(name, str) and name.strip():
                counts[name] = counts.get(name, 0) + 1
        brands = [{"name": name, "count": count} for name, count in sorted(counts.items())]
        return jsonify({
            "ok": True, "domain": domain, "scope": scope,
            "data_state": "READY" if brands else "NOT_COLLECTED", "brands": brands,
            "total": len(brands),
            "canonical_returned": canonical.get("returned_count", 0),
            "truncated": canonical.get("truncated"),
            "data_source": "permission-checked canonical_data.list_scoped_canonical",
        })
    except _DomainApiScopeError as e:
        return jsonify({"ok": False, "code": e.code}), e.status
    except ValueError as e:
        return jsonify({"ok": False, "code": str(e)}), 400
    except Exception as e:
        if hasattr(e, "code") and hasattr(e, "status"):
            return jsonify({"ok": False, "code": e.code}), e.status
        return jsonify({"ok": False, "code": "DOMAIN_BRANDS_UNAVAILABLE", "error": str(e)}), 503


@domain_api_bp.route("/api/domain/risk")
def api_domain_risk():
    """Compatibility risk view from the authorized Canonical slice."""
    try:
        domain = _get_domain_context()
        if domain is None:
            return jsonify({**_domain_api_selection_only(), "risk_notes": [], "risk_stats": {}})
        scope, canonical = _domain_api_canonical(domain, "reports")
        records = canonical.get("records", [])
        risk_notes = [row for row in records
                      if isinstance(row.get("risk_level"), str)
                      and row["risk_level"].strip().lower() in {"critical", "high", "medium", "低", "中", "高", "严重"}]
        risk_stats = {}
        for row in records:
            level = row.get("risk_level")
            if isinstance(level, str) and level.strip():
                key = level.strip().lower()
                risk_stats[key] = risk_stats.get(key, 0) + 1
        return jsonify({
            "ok": True, "domain": domain, "scope": scope,
            "data_state": "READY" if records else "NOT_COLLECTED",
            "risk_notes": risk_notes,
            "risk_stats": risk_stats,
            "canonical_returned": canonical.get("returned_count", 0),
            "truncated": canonical.get("truncated"),
            "data_source": "permission-checked canonical_data.list_scoped_canonical",
        })
    except _DomainApiScopeError as e:
        return jsonify({"ok": False, "code": e.code}), e.status
    except ValueError as e:
        return jsonify({"ok": False, "code": str(e)}), 400
    except Exception as e:
        if hasattr(e, "code") and hasattr(e, "status"):
            return jsonify({"ok": False, "code": e.code}), e.status
        return jsonify({"ok": False, "code": "DOMAIN_RISK_UNAVAILABLE", "error": str(e)}), 503


@domain_api_bp.route("/api/domain/context")
def api_domain_context():
    """Return current domain context + isolation boundaries."""
    try:
        domain = _get_domain_context()
        from domain_isolation import DOMAINS, get_domain
        if domain is None:
            return jsonify({
                "ok": True,
                "current_domain": None,
                "domain_info": None,
                "selection": "GLOBAL / ALL",
                "available_domains": {k: v.name for k, v in DOMAINS.items()},
                "header_required": "X-Domain-Id or explicit context selection",
            })
        d = get_domain(domain)
        return jsonify({
            "ok": True,
            "current_domain": domain,
            "domain_info": d.to_dict(),
            "available_domains": {k: v.name for k, v in DOMAINS.items()},
            "header_required": "X-Domain-Id or cookie zbc_domain",
        })
    except ValueError as e:
        return jsonify({"ok": False, "current_domain": None, "code": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "current_domain": domain, "error": str(e)}), 500
