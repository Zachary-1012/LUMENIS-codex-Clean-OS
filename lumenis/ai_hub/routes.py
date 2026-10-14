# -*- coding: utf-8 -*-
"""AI Hub 路由：状态 / 对话 / 任意模块分析 / 学习记录 / 影子队列。"""
from flask import Blueprint, request, jsonify
from ..auth import require_auth, get_current_user, log_audit
from . import service, shadow

ai_bp = Blueprint("v4_ai", __name__)


@ai_bp.route("/ai/status", methods=["GET"])
@require_auth
def ai_status():
    return jsonify({"success": True, "ai": service.status()})


@ai_bp.route("/ai/chat", methods=["POST"])
@require_auth
def ai_chat():
    data = request.get_json() or {}
    q = data.get("message") or data.get("question") or ""
    # Ordinary chat must not depend on selecting a business report scope.
    # A reports:read scope alone is not a SourceUse grant for sending business
    # records to a model. Until a typed Gateway operation supplies and validates
    # that SourceUse contract, the service receives no business retrieval scope.
    result = service.chat(q, history=data.get("history"), scope=data.get("scope", "all"),
                          source_scope=None)
    success = result.pop("ok", False)
    status = result.get("status")
    http_status = 200 if success else (400 if status == "INVALID_INPUT" else 503 if status == "UNAVAILABLE" else 502)
    return jsonify({"success": success, **result}), http_status


@ai_bp.route("/ai/analyze", methods=["POST"])
@require_auth
def ai_analyze():
    data = request.get_json() or {}
    result = service.analyze_module(data.get("module", ""), data.get("text", ""), data.get("meta"))
    success = result.pop("ok", False)
    status = result.get("status")
    http_status = 200 if success else (400 if status == "INVALID_INPUT" else 503 if status == "UNAVAILABLE" else 502)
    return jsonify({"success": success, **result}), http_status


@ai_bp.route("/ai/learn", methods=["GET"])
@require_auth
def ai_learn():
    return jsonify({"success": True, **service.learning_stats(limit=int(request.args.get("limit", 50)))})


@ai_bp.route("/ai/shadow", methods=["GET", "POST"])
@require_auth
def ai_shadow():
    if request.method == "POST":
        data = request.get_json() or {}
        r = shadow.add_suggestion(
            data.get("module", ""), data.get("title", ""), data.get("payload"),
            rationale=data.get("rationale"), kind=data.get("kind", "suggestion"))
        if r.get("ok"):
            log_audit("ai_shadow_add", "ai", r.get("id"), f"AI建议入影子队列: {data.get('title','')[:40]}")
        return jsonify(r)
    status = request.args.get("status", "pending")
    return jsonify({"success": True, "stats": shadow.stats(),
                    "items": shadow.list_suggestions(status, int(request.args.get("limit", 100)))})


@ai_bp.route("/ai/shadow/<sid>/decide", methods=["POST"])
@require_auth
def ai_shadow_decide(sid):
    user = get_current_user() or {}
    role = user.get("role", "user")
    if role not in ("owner", "admin"):
        return jsonify({"success": False, "error": "仅主账号/管理员可审核 AI 建议"}), 403
    data = request.get_json() or {}
    r = shadow.decide(sid, data.get("decision", ""), user.get("username", ""), data.get("note", ""))
    if r.get("ok"):
        log_audit("ai_shadow_decide", "ai", sid, f"AI建议决策={data.get('decision')}")
    return jsonify(r)


@ai_bp.route("/ai/shadow/stats", methods=["GET"])
@require_auth
def ai_shadow_stats():
    return jsonify({"success": True, "stats": shadow.stats()})
