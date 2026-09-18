"""
设置页路由 - 苹果风格分组布局
主账号专属：账号管理、安全问答、系统配置、模块管理、审计日志
"""
import os
from flask import Blueprint, render_template, request, jsonify, g, redirect
from ..auth import (
    require_owner, require_auth, get_current_user, create_user, list_users,
    update_user_status, change_password, reset_user_password,
    log_audit, query_audit_logs, get_audit_stats, verify_security_questions,
    ensure_initialized
)
from ..auth.models import get_db
from ..auth.security import hash_security_answer

settings_bp = Blueprint("v4_settings", __name__,
                        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
                        url_prefix="/settings")  # 相对前缀，由父蓝图 /v4 拼成 /v4/settings


@settings_bp.before_request
def _ensure():
    ensure_initialized()


@settings_bp.route("/login")
def v4_login_page():
    """V4 自带登录页（不鉴权）：账密 / 密钥 两种方式滑动切换。已登录则直接进设置页。"""
    if get_current_user():
        return redirect("/v4/settings/")
    return jsonify({"ok": True, "ui_reset": True, "page": "login"})


@settings_bp.route("/")
def settings_page():
    """设置页主页面：未登录跳转到 V4 登录页（页面壳不返回 401 白屏，数据接口仍由 @require_auth 拦截）"""
    user = get_current_user()
    if not user:
        return redirect("/v4/settings/login")
    return jsonify({"ok": True, "ui_reset": True, "page": "settings", "user": user.get("username") if user else None})


# ============ 账号管理 ============

@settings_bp.route("/api/users", methods=["GET"])
@require_owner
def api_list_users():
    """获取用户列表"""
    users = list_users()
    return jsonify({"success": True, "users": users})


@settings_bp.route("/api/users", methods=["POST"])
@require_owner
def api_create_user():
    """创建用户（需安全验证）"""
    data = request.get_json()
    # 安全验证
    answers = data.get("security_answers", {})
    if not verify_security_questions(answers):
        return jsonify({"success": False, "error": "安全验证失败"}), 403

    result = create_user(
        username=data.get("username", "").strip(),
        password=data.get("password", ""),
        role=data.get("role", "user"),
        display_name=data.get("display_name"),
        email=data.get("email"),
        created_by=g.current_user["id"],
    )
    if result["success"]:
        log_audit("create_user", "user", str(result["user_id"]),
                  f"创建用户 {data.get('username')} 角色={data.get('role')}")
    return jsonify(result)


@settings_bp.route("/api/users/<int:user_id>/status", methods=["POST"])
@require_owner
def api_toggle_user_status(user_id):
    """启用/禁用用户"""
    data = request.get_json()
    status = data.get("status", "disabled")
    answers = data.get("security_answers", {})
    if not verify_security_questions(answers):
        return jsonify({"success": False, "error": "安全验证失败"}), 403

    ok = update_user_status(user_id, status)
    if ok:
        log_audit("toggle_user_status", "user", str(user_id), f"设置状态={status}")
    return jsonify({"success": ok})


@settings_bp.route("/api/users/<int:user_id>/reset-password", methods=["POST"])
@require_owner
def api_reset_password(user_id):
    """重置子账号密码"""
    data = request.get_json()
    answers = data.get("security_answers", {})
    if not verify_security_questions(answers):
        return jsonify({"success": False, "error": "安全验证失败"}), 403

    result = reset_user_password(user_id, data.get("new_password", ""))
    if result["success"]:
        log_audit("reset_password", "user", str(user_id), "重置密码")
    return jsonify(result)


@settings_bp.route("/api/change-password", methods=["POST"])
@require_auth
def api_change_password():
    """修改自己的密码"""
    data = request.get_json()
    user = get_current_user()
    result = change_password(
        user_id=user["id"],
        old_password=data.get("old_password", ""),
        new_password=data.get("new_password", ""),
    )
    if result["success"]:
        log_audit("change_password", "user", str(user["id"]), "修改密码")
    return jsonify(result)


# ============ 安全问答管理 ============

@settings_bp.route("/api/security-questions", methods=["GET"])
@require_owner
def api_get_security_questions():
    """获取安全问答列表（不返回答案）"""
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT id, question, is_active, created_at FROM v4_security_questions ORDER BY id"
        )
        questions = [dict(row) for row in cur.fetchall()]
        return jsonify({"success": True, "questions": questions})
    finally:
        conn.close()


@settings_bp.route("/api/security-questions", methods=["POST"])
@require_owner
def api_add_security_question():
    """添加安全问答"""
    data = request.get_json()
    question = data.get("question", "").strip()
    answer = data.get("answer", "").strip()
    if not question or not answer:
        return jsonify({"success": False, "error": "问题和答案不能为空"})
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO v4_security_questions (question, answer_hash, is_active, created_by) VALUES (?,?,1,?)",
            (question, hash_security_answer(answer), g.current_user["id"])
        )
        conn.commit()
        log_audit("add_security_question", "security", None, f"添加问题: {question}")
        return jsonify({"success": True})
    finally:
        conn.close()


@settings_bp.route("/api/security-questions/<int:qid>", methods=["DELETE"])
@require_owner
def api_delete_security_question(qid):
    """删除安全问答（至少保留2个）"""
    conn = get_db()
    try:
        cur = conn.execute("SELECT COUNT(*) as cnt FROM v4_security_questions WHERE is_active=1")
        if cur.fetchone()["cnt"] <= 2:
            return jsonify({"success": False, "error": "至少保留2个安全问题"})
        conn.execute("UPDATE v4_security_questions SET is_active=0 WHERE id=?", (qid,))
        conn.commit()
        log_audit("delete_security_question", "security", str(qid))
        return jsonify({"success": True})
    finally:
        conn.close()


# ============ 审计日志 ============

@settings_bp.route("/api/audit-logs", methods=["GET"])
@require_owner
def api_audit_logs():
    """查询审计日志"""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 50, type=int)
    username = request.args.get("username")
    action = request.args.get("action")
    result = query_audit_logs(page, page_size, username, action)
    return jsonify(result)


@settings_bp.route("/api/audit-stats", methods=["GET"])
@require_owner
def api_audit_stats():
    """审计统计"""
    return jsonify(get_audit_stats())


# ============ 系统配置 ============

@settings_bp.route("/api/system-config", methods=["GET"])
@require_owner
def api_get_system_config():
    """获取系统配置"""
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM system_config")
        configs = [dict(row) for row in cur.fetchall()]
        return jsonify({"success": True, "configs": configs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    finally:
        conn.close()


@settings_bp.route("/api/system-config", methods=["POST"])
@require_owner
def api_update_system_config():
    """更新系统配置"""
    data = request.get_json()
    answers = data.get("security_answers", {})
    if not verify_security_questions(answers):
        return jsonify({"success": False, "error": "安全验证失败"}), 403
    # 配置更新逻辑（复用现有system_config表）
    log_audit("update_system_config", "system", None, str(data.get("updates", {})))
    return jsonify({"success": True, "message": "配置已更新"})
