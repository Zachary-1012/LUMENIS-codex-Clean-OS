# -*- coding: utf-8 -*-
"""LUMENIS Shared Evidence API（证据查询和受控回放 REST 接口）

把 Shared Evidence Store 能力暴露给产品客户端/API consumer。
证据查询保持只读；失败写入重放使用两步 owner 确认：
POST /api/evidence/replay-failed/approval，再 POST /api/evidence/replay-failed。
两次请求都必须提交完全相同的 {action: "evidence.replay_failed", confirm: true, limit}，
且 limit 为 1..200。审批不向客户端返回令牌，只绑定服务端会话 user_id、操作和 limit，
5 分钟有效且一次使用。
"""
from __future__ import annotations
from . import store as evidence_store
import logging
import threading


logger = logging.getLogger(__name__)
_EVIDENCE_REPLAY_ACTION = "evidence.replay_failed"
_EVIDENCE_REPLAY_RESOURCE = "evidence.replay_failed"
_EVIDENCE_REPLAY_LOCK = threading.Lock()

def _scope_error(code, message, status):
    from flask import jsonify
    return jsonify({"ok": False, "code": code, "error": message}), status


def resolve_evidence_request_scope(action="read"):
    """Require a server-issued actor, exact CTH/BMP scope, and Permission.

    GLOBAL_ALL needs X-Domain-Id on Evidence data routes because the store
    has separate exact CTH and BMP global markers; this differs from the
    selection-only /api/settings/context response, whose global context has
    no domain. It returns only explicitly global-marked Evidence rows.
    """
    from flask import request
    from lumenis.auth.service import get_current_user
    from subject_registry import (
        SubjectValidationError,
        get_subject_by_id,
        normalize_domain,
    )
    from lumenis.system.security import permission

    try:
        actor = get_current_user()
    except Exception:
        return None, _scope_error(
            "AUTH_UNAVAILABLE", "账号会话暂不可用", 503
        )
    if actor is None:
        actor = permission.resolve_local_workspace_principal(module="evidence", action=action)
    if type(actor) is not permission.LocalWorkspacePrincipal and (not isinstance(actor, dict) or type(actor.get("id")) is not int):
        return None, _scope_error("AUTH_REQUIRED", "需要有效账号会话", 401)

    mode = request.headers.get("X-Lumenis-Context-Mode", "")
    raw_domain = request.headers.get("X-Domain-Id", "")
    raw_subject = request.headers.get("X-Subject-ID", "")
    if mode not in {"FOCUS", "GLOBAL_ALL"} or not raw_domain:
        return None, _scope_error(
            "EVIDENCE_SCOPE_REQUIRED",
            "Evidence 查询需要上下文模式及 CTH/BMP 域；GLOBAL_ALL 还需明确域",
            400,
        )
    try:
        normalized_domain = normalize_domain(raw_domain)
    except SubjectValidationError:
        return None, _scope_error("INVALID_EVIDENCE_SCOPE", "业务域无效", 400)
    if normalized_domain not in {"CTH", "BMP"}:
        return None, _scope_error("INVALID_EVIDENCE_SCOPE", "仅支持 CTH 或 BMP Evidence", 400)

    subject_id = None
    brand_focus_id = None
    global_scope = mode == "GLOBAL_ALL"
    if global_scope:
        if raw_subject or request.headers.get("X-Brand-Focus-ID"):
            return None, _scope_error(
                "INVALID_EVIDENCE_SCOPE", "GLOBAL_ALL 不能携带聚焦主体", 400
            )
    else:
        if not raw_subject or raw_subject != raw_subject.strip():
            return None, _scope_error(
                "INVALID_EVIDENCE_SCOPE", "FOCUS 需要有效 X-Subject-ID", 400
            )
        try:
            subject = get_subject_by_id(normalized_domain, raw_subject)
        except Exception:
            return None, _scope_error(
                "SUBJECT_REGISTRY_UNAVAILABLE", "主体注册表暂不可用", 503
            )
        if not isinstance(subject, dict):
            return None, _scope_error("SUBJECT_NOT_FOUND", "主体未在有效注册表中", 404)
        expected_type = "company" if normalized_domain == "CTH" else "brand"
        if subject.get("subject_type") != expected_type:
            return None, _scope_error(
                "INVALID_EVIDENCE_SCOPE", "主体类型与业务域不匹配", 400
            )
        if normalized_domain == "CTH":
            subject_id = raw_subject
        else:
            brand_focus_id = subject.get("brand_focus_id")
            if not isinstance(brand_focus_id, str) or not brand_focus_id:
                return None, _scope_error(
                    "INVALID_EVIDENCE_SCOPE", "主体未绑定有效 BrandFocus", 400
                )

    try:
        checker = (permission.check_local_workspace_scope_permission if type(actor) is permission.LocalWorkspacePrincipal
                   else permission.check_actor_scope_permission)
        decision = checker(
            actor,
            domain_id=normalized_domain,
            action=action,
            module="evidence",
            subject_id=subject_id,
            brand_focus_id=brand_focus_id,
            global_scope=global_scope,
        )
    except Exception:
        return None, _scope_error(
            "AUTHORIZATION_UNAVAILABLE", "Evidence 范围授权暂不可用", 503
        )
    if decision.verification_state != "verified":
        return None, _scope_error(
            "AUTHORIZATION_UNAVAILABLE", "Evidence 范围授权暂不可用", 503
        )
    if not decision.allowed:
        return None, _scope_error(
            "EVIDENCE_SCOPE_DENIED", "没有读取该 Evidence 范围的权限", 403
        )

    return {
        "actor": actor,
        "product": "CTH" if normalized_domain == "CTH" else "ZBMP",
        "domain_id": "cth" if normalized_domain == "CTH" else "zbmp",
        "subject_id": subject_id,
        "brand_focus_id": brand_focus_id,
        "global_scope": global_scope,
        "response": {
            "mode": mode,
            "domain_id": normalized_domain,
            "subject_id": subject_id,
            "brand_focus_id": brand_focus_id,
            "global_scope": global_scope,
            "evidence_scope": (
                "EXPLICIT_GLOBAL_MARKED_EVIDENCE_ONLY"
                if global_scope
                else "EXACT_SUBJECT_OR_BRAND_FOCUS_EVIDENCE"
            ),
        },
    }, None



def register_evidence_api(app):
    """在 Flask app 上注册 Evidence 查询蓝图。"""
    from flask import Blueprint, jsonify, request

    bp = Blueprint("evidence_api", __name__)

    def _owner_for_replay():
        from lumenis.auth.service import get_current_user

        user = get_current_user()
        if not user:
            return None, (jsonify({"ok": False, "error": "未登录或登录已过期"}), 401)
        if not isinstance(user, dict) or user.get("role") != "owner":
            return None, (jsonify({"ok": False, "error": "仅主账号可操作 Evidence 重放"}), 403)
        # get_current_user() reads this ID from the authenticated v4 session;
        # never accept the actor identity from the request body.
        user_id = user.get("id")
        if type(user_id) is not int or user_id < 1:
            return None, (jsonify({"ok": False, "error": "无法确认操作人身份"}), 403)
        return user, None

    def _confirmed_replay_limit():
        payload = request.get_json(silent=True)
        expected_keys = {"action", "confirm", "limit"}
        if not isinstance(payload, dict) or set(payload) != expected_keys:
            return None, (jsonify({"ok": False, "error": "请求字段必须严格为 action、confirm、limit"}), 400)
        if payload.get("action") != _EVIDENCE_REPLAY_ACTION:
            return None, (jsonify({"ok": False, "error": "Evidence 重放 action 不匹配"}), 400)
        if payload.get("confirm") is not True:
            return None, (jsonify({"ok": False, "error": "必须明确 confirm=true"}), 400)
        limit = payload.get("limit")
        if type(limit) is not int or not 1 <= limit <= 200:
            return None, (jsonify({"ok": False, "error": "limit 必须是 1 到 200 的整数"}), 400)
        return limit, None

    def _replay_resource(user_id: int, limit: int) -> str:
        return f"{_EVIDENCE_REPLAY_RESOURCE}:user:{user_id}:limit:{limit}"

    def _permission_gate_contract(gate, operation_type, permission_level, risk_level):
        spec = gate.get_operation_spec(operation_type)
        return (
            gate.has_permission(permission_level)
            and spec is not None
            and spec.permission == permission_level
            and spec.risk == risk_level
            and not spec.auto_allow
        )

    def _read_error(code, message, status):
        return jsonify({"ok": False, "code": code, "error": message}), status

    def _authorized_read_scope():
        return resolve_evidence_request_scope()

    def _query_scope(scope, *, limit, offset, after_created_at=None, after_id=None):
        return evidence_store.query_scoped_evidence(
            product=scope["product"],
            domain_id=scope["domain_id"],
            subject_id=scope["subject_id"],
            brand_focus_id=scope["brand_focus_id"],
            global_scope=scope["global_scope"],
            limit=limit,
            offset=offset,
            after_created_at=after_created_at,
            after_id=after_id,
        )

    def _filtered_page(scope, filters, *, limit, offset):
        """Apply legacy equality filters after exact scope filtering, then page."""
        rows = []
        filtered_offset = 0
        after_created_at = None
        after_id = None
        while len(rows) < limit:
            page = _query_scope(
                scope, limit=200, offset=0,
                after_created_at=after_created_at, after_id=after_id,
            )
            if not page:
                break
            after_created_at = page[-1].get("created_at")
            after_id = page[-1].get("id")
            for record in page:
                if any(record.get(key) != value for key, value in filters.items()):
                    continue
                if filtered_offset < offset:
                    filtered_offset += 1
                    continue
                rows.append(record)
                if len(rows) == limit:
                    break
            if len(page) < 200:
                break
        return rows

    def _scoped_pages(scope):
        after_created_at = None
        after_id = None
        while True:
            page = _query_scope(
                scope, limit=200, offset=0,
                after_created_at=after_created_at, after_id=after_id,
            )
            if not page:
                return
            yield from page
            after_created_at = page[-1].get("created_at")
            after_id = page[-1].get("id")
            if len(page) < 200:
                return

    def _query_integer(name, default, maximum=None):
        raw = request.args.get(name)
        try:
            value = default if raw is None else int(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{name} 必须是整数")
        if name == "limit" and maximum is not None:
            value = min(value, maximum)
        if value < (1 if name == "limit" else 0):
            raise ValueError(f"{name} 超出允许范围")
        return value

    def _reject_unknown_query_args(allowed):
        unknown = set(request.args.keys()) - set(allowed)
        if unknown:
            return _read_error(
                "UNSUPPORTED_EVIDENCE_FILTER",
                "Evidence 查询包含不支持的参数: " + ", ".join(sorted(unknown)),
                400,
            )
        return None

    @bp.route("/api/evidence/stats", methods=["GET"])
    def evidence_stats():
        """Aggregate only records carrying the actor-authorized exact scope."""
        scope, error = _authorized_read_scope()
        if error:
            return error
        query_error = _reject_unknown_query_args(set())
        if query_error:
            return query_error
        try:
            stats = {
                "total": 0,
                "by_result": {},
                "by_level": {},
                "by_account": {},
                "by_source": {},
                "null_counts": {},
                "recent": [],
            }
            for row in _scoped_pages(scope):
                stats["total"] += 1
                for field, group in (
                    ("result", "by_result"),
                    ("level", "by_level"),
                    ("source", "by_source"),
                ):
                    value = row.get(field)
                    # Keep SQL NULL visible in JSON without inventing a string
                    # group key that could collide with a real source value.
                    if value is None:
                        stats["null_counts"][field] = (
                            stats["null_counts"].get(field, 0) + 1
                        )
                    else:
                        stats[group][value] = stats[group].get(value, 0) + 1
                account = row.get("account")
                if account:
                    stats["by_account"][account] = stats["by_account"].get(account, 0) + 1
                if len(stats["recent"]) < 10:
                    stats["recent"].append({
                        field: row.get(field)
                        for field in (
                            "id", "source", "feature_id", "level", "result",
                            "account", "actual", "created_at",
                        )
                    })
            return jsonify({"ok": True, "stats": stats, "scope": scope["response"]})
        except Exception:
            logger.exception("Scoped Evidence stats query failed")
            return _read_error("EVIDENCE_READ_UNAVAILABLE", "Evidence 查询暂不可用", 503)

    @bp.route("/api/evidence/list", methods=["GET"])
    def evidence_list():
        """List exact-scope Evidence with the existing equality filters/page."""
        scope, error = _authorized_read_scope()
        if error:
            return error
        filter_keys = {"source", "feature_id", "level", "result", "account", "env"}
        query_error = _reject_unknown_query_args(filter_keys | {"limit", "offset"})
        if query_error:
            return query_error
        try:
            limit = _query_integer("limit", 50, maximum=200)
            offset = _query_integer("offset", 0)
            filters = {key: value for key in filter_keys if (value := request.args.get(key, ""))}
            rows = _filtered_page(scope, filters, limit=limit, offset=offset)
            return jsonify({
                "ok": True, "count": len(rows), "records": rows,
                "scope": scope["response"],
            })
        except ValueError as exc:
            return _read_error("INVALID_EVIDENCE_QUERY", str(exc), 400)
        except Exception:
            logger.exception("Scoped Evidence list query failed")
            return _read_error("EVIDENCE_READ_UNAVAILABLE", "Evidence 查询暂不可用", 503)

    @bp.route("/api/evidence/<int:record_id>", methods=["GET"])
    def evidence_detail(record_id):
        """Return 404 for records outside the actor's exact Evidence scope."""
        scope, error = _authorized_read_scope()
        if error:
            return error
        query_error = _reject_unknown_query_args(set())
        if query_error:
            return query_error
        try:
            record = next(iter(_filtered_page(
                scope, {"id": record_id}, limit=1, offset=0
            )), None)
            if not record:
                return _read_error("EVIDENCE_NOT_FOUND", "证据不存在", 404)
            return jsonify({"ok": True, "record": record, "scope": scope["response"]})
        except Exception:
            logger.exception("Scoped Evidence detail query failed")
            return _read_error("EVIDENCE_READ_UNAVAILABLE", "Evidence 查询暂不可用", 503)

    @bp.route("/api/evidence/timeline", methods=["GET"])
    def evidence_timeline():
        """Return the health/collection timeline inside the exact authorized scope."""
        scope, error = _authorized_read_scope()
        if error:
            return error
        query_error = _reject_unknown_query_args({"account", "limit"})
        if query_error:
            return query_error
        try:
            limit = _query_integer("limit", 30, maximum=100)
            account = request.args.get("account", "")
            filters = {"account": account} if account else {}
            health = _filtered_page(
                scope, {**filters, "feature_id": "RESIDENT_HEALTH"},
                limit=limit, offset=0,
            )
            collection = _filtered_page(
                scope, {**filters, "feature_id": "XHS_COLLECT"},
                limit=limit, offset=0,
            )
            return jsonify({
                "ok": True,
                "health": health,
                "collection": collection,
                "scope": scope["response"],
            })
        except ValueError as exc:
            return _read_error("INVALID_EVIDENCE_QUERY", str(exc), 400)
        except Exception:
            logger.exception("Scoped Evidence timeline query failed")
            return _read_error("EVIDENCE_READ_UNAVAILABLE", "Evidence 查询暂不可用", 503)

    @bp.route("/api/evidence/replay-failed/approval", methods=["POST"])
    def evidence_replay_failed_approval():
        """为当前 owner 明确确认的单次、限额 Evidence 重放建立短时审批。"""
        try:
            from lumenis.system.security import (
                OperationType,
                PermissionLevel,
                RiskLevel,
                get_permission_gate,
            )

            user, auth_error = _owner_for_replay()
            if auth_error:
                return auth_error
            limit, payload_error = _confirmed_replay_limit()
            if payload_error:
                return payload_error

            gate = get_permission_gate()
            if not _permission_gate_contract(
                gate,
                OperationType.RUNTIME_OPERATION,
                PermissionLevel.COMMIT,
                RiskLevel.HIGH,
            ):
                return jsonify({"ok": False, "error": "SYSTEM 未启用所需 COMMIT / HIGH 审批策略"}), 403

            resource = _replay_resource(user["id"], limit)
            # Keep approval creation and replay consumption mutually exclusive
            # within this process. The gate itself is process-local and remains
            # fail-closed if a request reaches a worker without this approval.
            with _EVIDENCE_REPLAY_LOCK:
                prior = gate.get_valid_approval_token(
                    OperationType.RUNTIME_OPERATION.value, resource, exact=True
                )
                if prior:
                    gate.revoke_approval(prior)
                gate.grant_approval(
                    OperationType.RUNTIME_OPERATION.value,
                    duration_minutes=5,
                    resource=resource,
                    granted_by=f"evidence_replay_owner:{user['id']}",
                )
            return jsonify({
                "ok": True,
                "action": _EVIDENCE_REPLAY_ACTION,
                "limit": limit,
                "expires_in_seconds": 300,
            })
        except Exception:
            logger.exception("Evidence replay approval failed")
            return jsonify({"ok": False, "error": "无法建立 Evidence 重放审批"}), 403

    @bp.route("/api/evidence/replay-failed", methods=["POST"])
    def evidence_replay_failed():
        """执行与当前 owner、action 和 limit 完全绑定的一次性重放。"""
        try:
            from lumenis.system.security import (
                OperationType,
                PermissionLevel,
                RiskLevel,
                get_permission_gate,
            )

            user, auth_error = _owner_for_replay()
            if auth_error:
                return auth_error
            limit, payload_error = _confirmed_replay_limit()
            if payload_error:
                return payload_error

            gate = get_permission_gate()
            if not _permission_gate_contract(
                gate,
                OperationType.RUNTIME_OPERATION,
                PermissionLevel.COMMIT,
                RiskLevel.HIGH,
            ):
                return jsonify({"ok": False, "error": "SYSTEM 未启用所需 COMMIT / HIGH 审批策略"}), 403

            resource = _replay_resource(user["id"], limit)
            with _EVIDENCE_REPLAY_LOCK:
                permission = gate.check(
                    operation_type=OperationType.RUNTIME_OPERATION,
                    resource=resource,
                    risk_level=RiskLevel.HIGH,
                    caller=f"evidence_replay:{user['id']}",
                    domain_id="system",
                    # Trusted server-side mapping only, after real owner auth.
                    role="system_operator",
                    exact_approval_required=True,
                )
                if (
                    not permission.allowed
                    or not permission.requires_approval
                    or not permission.approval_token
                ):
                    return jsonify({"ok": False, "error": "缺少匹配本次 owner/limit 的有效审批"}), 403

                try:
                    result = evidence_store.replay_failed_evidence(limit=limit)
                finally:
                    # Consume even on exceptions so a partial write cannot be
                    # repeated under the same explicit owner confirmation.
                    gate.revoke_approval(permission.approval_token)
                if result.get("error"):
                    return jsonify({**result, "ok": False}), 503
                if isinstance(result.get("failed"), int) and result["failed"] > 0:
                    return jsonify({**result, "ok": False}), 207
                return jsonify({**result, "ok": True})
        except Exception as e:
            logger.exception("Evidence replay execution failed")
            return jsonify({"ok": False, "error": str(e)}), 500

    app.register_blueprint(bp)
    return bp
