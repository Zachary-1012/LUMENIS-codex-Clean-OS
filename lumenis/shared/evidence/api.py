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

    @bp.route("/api/evidence/stats", methods=["GET"])
    def evidence_stats():
        """证据统计：总数 + 按 result/level/account/source 分组 + 最近 10 条。"""
        try:
            return jsonify({"ok": True, "stats": evidence_store.get_stats()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @bp.route("/api/evidence/list", methods=["GET"])
    def evidence_list():
        """证据列表（支持 source/feature_id/level/result/account/env 筛选 + 分页）。"""
        try:
            rows = evidence_store.query_evidence(
                source=request.args.get("source", ""),
                feature_id=request.args.get("feature_id", ""),
                level=request.args.get("level", ""),
                result=request.args.get("result", ""),
                account=request.args.get("account", ""),
                env=request.args.get("env", ""),
                limit=min(int(request.args.get("limit", "50")), 200),
                offset=int(request.args.get("offset", "0")),
            )
            return jsonify({"ok": True, "count": len(rows), "records": rows})
        except ValueError as e:
            return jsonify({"ok": False, "error": f"参数错误: {e}"}), 400
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @bp.route("/api/evidence/<int:record_id>", methods=["GET"])
    def evidence_detail(record_id):
        """单条证据详情。"""
        try:
            rows = evidence_store.query_evidence(limit=1000)
            record = next((r for r in rows if r["id"] == record_id), None)
            if not record:
                return jsonify({"ok": False, "error": "证据不存在"}), 404
            return jsonify({"ok": True, "record": record})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @bp.route("/api/evidence/timeline", methods=["GET"])
    def evidence_timeline():
        """时间线视图：按 feature_id 分组的最近证据（健康/采集分开）。"""
        try:
            account = request.args.get("account", "")
            limit = min(int(request.args.get("limit", "30")), 100)
            health = evidence_store.query_evidence(
                feature_id="RESIDENT_HEALTH", account=account, limit=limit)
            collection = evidence_store.query_evidence(
                feature_id="XHS_COLLECT", account=account, limit=limit)
            return jsonify({
                "ok": True,
                "health": health,
                "collection": collection,
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

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
