# -*- coding: utf-8 -*-
"""版本中心路由：页面 + 状态/历史/保存/检查更新/推送/拉取/回滚/自动配置。"""
import os
from flask import Blueprint, request, jsonify, redirect
from ..auth import require_auth, require_owner, get_current_user, log_audit
from .git_manager import gm

version_bp = Blueprint(
    "v4_version", __name__,
    url_prefix="/version-center",
)


@version_bp.route("/")
def version_center_page():
    """版本中心页面（未登录跳 V4 登录页，避免白屏）。"""
    user = get_current_user()
    if not user:
        return redirect("/v4/settings/login")
    return jsonify({"ok": True, "ui_reset": True, "page": "version_center", "user": user.get("username") if user else None})


@version_bp.route("/api/status", methods=["GET"])
@require_auth
def api_status():
    return jsonify({"success": True, "status": gm().status()})


@version_bp.route("/api/history", methods=["GET"])
@require_auth
def api_history():
    limit = request.args.get("limit", 20, type=int)
    return jsonify(gm().history(limit))


@version_bp.route("/api/save", methods=["POST"])
@require_owner
def api_save():
    """立即保存版本：源码变化→安全闸→commit→（可选）push。"""
    body = request.get_json() or {}
    user = get_current_user() or {}
    r = gm().save_version(
        message=body.get("message", ""),
        bump=body.get("bump") or None,
        do_push=bool(body.get("do_push", True)),
        author=user.get("username", "owner"),
    )
    log_audit("version_save", "version", r.get("sha", ""),
              f"保存版本 {r.get('version', '')} push={r.get('pushed')}")
    code = 200 if r.get("ok") else 400
    return jsonify(r), code


@version_bp.route("/api/push", methods=["POST"])
@require_owner
def api_push():
    r = gm().push()
    log_audit("version_push", "version", "", "手动推送 GitHub" if r["ok"] else f"推送失败:{r.get('err')}")
    return jsonify({"success": r["ok"], **r}), (200 if r["ok"] else 400)


@version_bp.route("/api/check", methods=["POST"])
@require_auth
def api_check():
    r = gm().check_update()
    return jsonify(r), (200 if r.get("ok") else 400)


@version_bp.route("/api/pull", methods=["POST"])
@require_owner
def api_pull():
    r = gm().pull()
    log_audit("version_pull", "version", "", "拉取远程更新" if r["ok"] else f"拉取失败:{r.get('err')}")
    return jsonify({"success": r["ok"], **r}), (200 if r["ok"] else 400)


@version_bp.route("/api/rollback", methods=["POST"])
@require_owner
def api_rollback():
    """回滚版本：默认 revert（保留历史）；hard 需 confirm=true 二次确认。"""
    body = request.get_json() or {}
    sha = body.get("sha", "")
    mode = body.get("mode", "revert")
    r = gm().rollback(sha, mode=mode, confirm_hard=bool(body.get("confirm", False)))
    log_audit("version_rollback", "version", sha, f"回滚 mode={mode} ok={r['ok']}")
    return jsonify({"success": r["ok"], **r}), (200 if r["ok"] else 400)


@version_bp.route("/api/config", methods=["GET", "POST"])
def api_config():
    user = get_current_user()
    if not user or user.get("role") != "owner":
        return jsonify({"success": False, "error": "仅主账号可配置自动版本"}), 403
    if request.method == "POST":
        cfg = gm().save_config(request.get_json() or {})
        log_audit("version_config", "version", "", f"自动版本配置: {cfg}")
        return jsonify({"success": True, "config": cfg})
    return jsonify({"success": True, "config": gm().load_config()})
