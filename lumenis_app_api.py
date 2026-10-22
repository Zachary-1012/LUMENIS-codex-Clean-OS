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
    domain_keys = {"domain_id", "subject_id", "brand_focus_id", "global_scope"}
    shared_keys = {"scope_kind", "version"}
    if data is not None:
        # A POST has one scope location. Do not silently ignore a competing query.
        if request.args:
            raise ValueError("INTERNAL_PITCH_REQUEST_INVALID")
        scope = data.get("scope")
    else:
        if any(len(request.args.getlist(key)) != 1 for key in request.args):
            raise ValueError("INTERNAL_PITCH_REQUEST_INVALID")
        if set(request.args) == shared_keys:
            if request.args["scope_kind"] != "shared_workspace" or request.args["version"] != "1":
                raise ValueError("INTERNAL_PITCH_EXACT_SCOPE_REQUIRED")
            scope = {"scope_kind": "shared_workspace", "version": 1}
        elif set(request.args) == domain_keys:
            if request.args["global_scope"] not in {"true", "false"}:
                raise ValueError("INTERNAL_PITCH_EXACT_SCOPE_REQUIRED")
            scope = {"domain_id": request.args["domain_id"], "subject_id": request.args["subject_id"] or None,
                     "brand_focus_id": request.args["brand_focus_id"] or None,
                     "global_scope": request.args["global_scope"] == "true"}
        else:
            raise ValueError("INTERNAL_PITCH_REQUEST_INVALID")
    if isinstance(scope, dict) and set(scope) == shared_keys:
        if scope["scope_kind"] == "shared_workspace" and type(scope["version"]) is int and scope["version"] == 1:
            return scope
        raise ValueError("INTERNAL_PITCH_EXACT_SCOPE_REQUIRED")
    if (not isinstance(scope, dict) or set(scope) != domain_keys
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
    from lumenis.shared.reporting.saved_work import authorize_saved_work
    from lumenis.system.security.permission import resolve_local_workspace_principal
    prefix = "/api/experience/creation/internal-pitches"
    routes = {
        "domain_api.api_internal_pitch_prepare": (prefix, "POST", re.escape(prefix)),
        "domain_api.api_internal_pitch_read": (
            prefix + "/<task_id>", "GET", re.escape(prefix) + r"/task-pitch-[0-9a-f]{24}"),
        "domain_api.api_internal_pitch_action": (
            prefix + "/<task_id>/<action>", "POST",
            re.escape(prefix) + r"/task-pitch-[0-9a-f]{24}/(?:run|cancel)"),
        "domain_api.api_internal_pitch_export": (
            prefix + "/<task_id>/export", "GET",
            re.escape(prefix) + r"/task-pitch-[0-9a-f]{24}/export"),
    }
    expected = routes.get(request.endpoint)
    if (expected is None or request.url_rule is None
            or request.url_rule.rule != expected[0] or request.method != expected[1]
            or re.fullmatch(expected[2], request.path) is None):
        return False
    action = "read" if request.method == "GET" else "write"
    actor = resolve_local_workspace_principal(module="reports", action=action)
    if actor is None:
        return False
    try:
        data = _internal_pitch_body() if request.method == "POST" else None
        authorize_saved_work(actor, _internal_pitch_scope(data), action=action)
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
        elif isinstance(exc, PermissionError) or "PERMISSION" in code or "DENIED" in code:
            status = 403
        elif isinstance(exc, LookupError):
            status = 404
        elif any(term in code for term in ("CONFLICT", "CANCELLED", "NOT_RUNNABLE", "STILL_ACTIVE")):
            status = 409
        elif isinstance(exc, RuntimeError) or any(term in code for term in ("INTEGRITY", "MISSING", "OWNER_FAILED", "UNAVAILABLE")):
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
        required = case_fields if "case_id" in data else source_fields
        optional = {"options", "planning_constraints"}
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
                             "save-request", "save", "restore", "review"}:
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


def _skill_api_actor():
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import resolve_local_workspace_principal
    actor = get_current_user(read_only=True)
    if isinstance(actor, dict) and type(actor.get("id")) is int:
        return actor
    actor = resolve_local_workspace_principal(module="skills", action="read")
    if actor is None:
        raise PermissionError("AUTHENTICATED_ACTOR_REQUIRED")
    return actor


def _skill_bound_task(task_id, actor):
    from ai_task_engine import get_task_engine
    from agent_runtime.task_binding import authorized_context
    if not isinstance(task_id, str) or not task_id:
        raise PermissionError("SKILL_TASK_BINDING_REQUIRED")
    task = get_task_engine().get_task(task_id)
    if not isinstance(task, dict):
        raise PermissionError("SKILL_TASK_ACCESS_DENIED")
    return task, authorized_context(task, actor)


def _skill_api_response(payload, status=200):
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response, status


def _skill_record(row):
    """Compatibility projection of the existing durable execution owner."""
    return {
        "invocation_id": row["execution_id"], "execution_id": row["execution_id"],
        "skill_id": row["skill_id"], "task": row["task"],
        "workspace": row["product"], "timestamp": row["created_at"],
        "status": str(row["status"]).upper(),
        "result": json.loads(row.get("output_json") or "null"),
        "evidence": json.loads(row.get("evidence_json") or "null"),
        "evaluation": json.loads(row.get("evaluation_json") or "null"),
    }


def _skill_visible_records(actor):
    from ai_api import _task_row_read_allowed
    from lumenis.shared.agents.skills.execution import query_executions, verified_execution_scope
    limit = max(1, min(200, int(request.args.get("limit", "50"))))
    task_id = request.args.get("task_id")
    bound = _skill_bound_task(task_id, actor) if task_id else None
    account_actor = isinstance(actor, dict) and type(actor.get("id")) is int
    if not account_actor and bound is None:
        raise PermissionError("SKILL_TASK_BINDING_REQUIRED")
    records, snapshots, offset = [], [], 0
    while len(records) < limit:
        rows = query_executions(skill_id=request.args.get("skill_id") or None,
                                limit=100, offset=offset, strict=True)
        for row in rows:
            if bound is not None:
                from agent_runtime.task_binding import _digest, _current_binding
                task, context = bound
                inputs = json.loads(row.get("input_json") or "{}")
                identifier = ("skillscope_" if account_actor else "") + "agentstep_" + _digest({
                    "task": task_id, "skill": row["skill_id"], "inputs": inputs})[:32]
                if (row["execution_id"] != identifier or row["task"] != task["user_input"]
                        or row["product"] != context["product"] or row["user_id"] != context["actor_id"]):
                    continue
                try:
                    _current_binding(task_id, row["skill_id"])
                except (PermissionError, ValueError, KeyError):
                    continue
            if account_actor:
                if not _task_row_read_allowed(row, kind="SKILL_EXECUTION"):
                    continue
                # Legacy domain records without signed scope are not ownership
                # proof. SYSTEM retains its existing actor/module read contract.
                if row["product"] != "SYSTEM" and not verified_execution_scope(row, actor):
                    continue
            from lumenis.shared.agents.skills.execution import read_source_free_execution
            if read_source_free_execution(row, actor) is None:
                continue
            records.append(_skill_record(row))
            snapshots.append(row)
            if len(records) == limit:
                break
        offset += len(rows)
        if len(rows) < 100:
            break
    # A later row can race an earlier row's revocation. Reopen every selected
    # producer at the final response boundary, not just the listing scope.
    for row in snapshots:
        if read_source_free_execution(row, _skill_api_actor()) is None:
            raise PermissionError("SKILL_RESULT_ACCESS_CHANGED")
    return records


@lumenis_bp.route("/api/skills/invoke", methods=["POST"])
def skill_invoke():
    """Compatibility transport; execute through the canonical Skill owner.

    A Basic perimeter credential, workspace label or supplied user role is never
    an actor. Domain executions require explicit, live scope; local work reuses
    the existing sealed Agent task binding. No independent JSONL truth is written.
    """
    try:
        actor = _skill_api_actor()
        data = request.get_json(silent=True)
        if (not isinstance(data, dict) or (request.content_length or 0) > 1024 * 1024
                or not isinstance(data.get("skill_id"), str) or not data["skill_id"].strip()
                or not isinstance(data.get("input", {}), dict)
                or not isinstance(data.get("task", ""), str)
                or not isinstance(data.get("action_type", "ANALYZE"), str)):
            return _skill_api_response({"ok": False, "code": "SKILL_REQUEST_INVALID"}, 400)
        if data.get("task_id"):
            from agent_runtime.task_binding import _invoke_local_tool
            task, context = _skill_bound_task(data["task_id"], actor)
            if (data.get("action_type", "READ") != "READ"
                    or ("scope" in data and data["scope"] != context["scope"])
                    or ("task" in data and data["task"] != task["user_input"])
                    or ("product" in data and data["product"] != context["product"])):
                raise PermissionError("SKILL_TASK_BINDING_MISMATCH")
            outcome = _invoke_local_tool(data["task_id"], data["skill_id"], _source_free=True, **data.get("input", {}))
            if outcome.get("success") is True:
                from lumenis.shared.agents.skills.execution import query_executions, read_source_free_execution
                rows = query_executions(execution_id=outcome.get("skill_execution_id"), limit=1, strict=True)
                if not rows or read_source_free_execution(rows[0], actor) is None:
                    return _skill_api_response({"ok": False, "code": "SOURCE_READER_UNBOUND",
                                               "result": None}, 409)
        else:
            from account.skills import execute_skill_api, get_skill_info
            if not isinstance(actor, dict) or type(actor.get("id")) is not int:
                raise PermissionError("SKILL_TASK_BINDING_REQUIRED")
            product = data.get("product", data.get("workspace"))
            if product not in {"CTH", "BMP", "ZBMP", "SYSTEM"}:
                return _skill_api_response({"ok": False, "code": "PRODUCT_CONTEXT_REQUIRED"}, 400)
            info = get_skill_info(data["skill_id"])
            registered_product = str(info.get("product") or "").upper()
            if product == "SYSTEM" and registered_product not in {"SYSTEM", "SHARED"}:
                raise PermissionError("SKILL_PRODUCT_BINDING_DENIED")
            if product != "SYSTEM" and not isinstance(data.get("scope"), dict):
                return _skill_api_response({"ok": False, "code": "SKILL_EXACT_SCOPE_REQUIRED"}, 400)
            outcome = execute_skill_api(data["skill_id"], task=data.get("task", ""),
                input_payload=data.get("input", {}), action_type=data.get("action_type", "ANALYZE"),
                user_id=actor["id"], product=product, scope=data.get("scope"), _local_only=True)
        success = outcome.get("success") is True
        return _skill_api_response({**outcome, "ok": success,
            "invocation_id": outcome.get("execution_id", outcome.get("skill_execution_id")),
            "status": "COMPLETED" if success else str(outcome.get("status") or "BLOCKED").upper()},
            200 if success else 404 if outcome.get("code") == "NOT_FOUND" else 403)
    except PermissionError:
        return _skill_api_response({"ok": False, "code": "SKILL_ACCESS_DENIED"}, 403)
    except (ValueError, TypeError, KeyError):
        return _skill_api_response({"ok": False, "code": "SKILL_REQUEST_INVALID"}, 400)
    except Exception:
        return _skill_api_response({"ok": False, "code": "SKILL_EXECUTION_UNAVAILABLE"}, 503)


@lumenis_bp.route("/api/skills/invocations")
def skill_invocations_history():
    """Reopen the same actor's executions with fresh owner/scope checks."""
    try:
        records = _skill_visible_records(_skill_api_actor())
        return _skill_api_response({"ok": True, "count": len(records), "records": records,
            "persistence": "skill_executions", "legacy_history_state": "UNBOUND_NOT_ADMITTED",
            "source_reader_state": "BOUND_LOCAL_PRODUCERS_ONLY",
            "recovery": "Re-run the original request through the authorized Skill owner; legacy files are retained."})
    except PermissionError:
        return _skill_api_response({"ok": False, "code": "SKILL_ACCESS_DENIED", "records": []}, 403)
    except (ValueError, TypeError):
        return _skill_api_response({"ok": False, "code": "SKILL_REQUEST_INVALID", "records": []}, 400)
    except Exception:
        return _skill_api_response({"ok": False, "code": "SKILL_HISTORY_UNAVAILABLE", "records": []}, 503)


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

def _skill_evidence_projection(row, scope):
    """Read a known producer through its original SourceUse owner."""
    from account.models import get_db
    from lumenis.shared.evidence.store import verify_evidence_record_integrity
    from lumenis.shared.reporting.saved_work import authorize, _verified_evidence
    from lumenis.shared.agents.skills.execution import query_executions, read_source_free_execution
    if not verify_evidence_record_integrity(row):
        return None
    try:
        if row.get("source") == "skill_execution_scope":
            material = json.loads(row["inputs_json"])["scope_receipt"]
            executions = query_executions(execution_id=material["execution_id"], limit=1, strict=True)
            if not executions or read_source_free_execution(executions[0], scope["actor"]) is None:
                return None
            return {"execution_id": executions[0]["execution_id"],
                    "evidence": _skill_record(executions[0])["evidence"]}
        con = get_db()
        try:
            context = authorize(scope["actor"], {key: scope[key] for key in (
                "domain_id", "subject_id", "brand_focus_id", "global_scope")}, action="read", connection=con)
            return _verified_evidence(con, row["id"], context, scope["actor"])
        finally:
            con.close()
    except (PermissionError, ValueError, KeyError, TypeError, LookupError):
        return None


@lumenis_bp.route("/api/intelligence/evidence")
def api_intelligence_evidence():
    """Exact-scope discovery followed by the original producer's SourceUse read."""
    from lumenis.shared.evidence.api import resolve_evidence_request_scope
    from lumenis.shared.evidence.store import query_scoped_evidence
    try:
        scope, error = resolve_evidence_request_scope()
        if error is not None:
            return error
        if set(request.args) - {"limit", "offset"}:
            raise ValueError("unknown query")
        limit = int(request.args.get("limit", "50"))
        offset = int(request.args.get("offset", "0"))
        if not 1 <= limit <= 200 or offset < 0:
            raise ValueError("invalid pagination")
        visible, snapshots, skipped = [], [], 0
        after_time = after_id = None
        while len(visible) < limit:
            candidates = query_scoped_evidence(product=scope["product"], domain_id=scope["domain_id"],
                subject_id=scope["subject_id"], brand_focus_id=scope["brand_focus_id"],
                global_scope=scope["global_scope"], limit=100,
                after_created_at=after_time, after_id=after_id)
            for row in candidates:
                projection = _skill_evidence_projection(row, scope)
                if projection is None:
                    continue
                if skipped < offset:
                    skipped += 1
                    continue
                visible.append(projection)
                snapshots.append(row)
                if len(visible) == limit:
                    break
            if len(candidates) < 100:
                break
            after_time, after_id = candidates[-1].get("created_at"), candidates[-1]["id"]
        current_scope, error = resolve_evidence_request_scope()
        if error is not None:
            return error
        if current_scope != scope:
            raise PermissionError("EVIDENCE_SCOPE_CHANGED")
        for row, projection in zip(snapshots, visible):
            if _skill_evidence_projection(row, current_scope) != projection:
                raise PermissionError("SOURCE_USE_CHANGED_DURING_READ")
        return _skill_api_response({"ok": True, "count": len(visible), "chains": visible,
            "scope": scope["response"], "source": "shared_evidence", "persistence": "app_evidence_records",
            "legacy_history_state": "UNBOUND_NOT_ADMITTED", "source_reader_state": "KNOWN_PRODUCERS_ONLY",
            "unbound_producer_code": "SOURCE_READER_UNBOUND",
            "recovery": "Re-run the original request through the authorized Skill owner; legacy files are retained."})
    except PermissionError:
        return _skill_api_response({"ok": False, "code": "SKILL_ACCESS_DENIED", "chains": []}, 403)
    except (ValueError, TypeError):
        return _skill_api_response({"ok": False, "code": "SKILL_REQUEST_INVALID", "chains": []}, 400)
    except Exception:
        return _skill_api_response({"ok": False, "code": "SKILL_EVIDENCE_UNAVAILABLE", "chains": []}, 503)



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
