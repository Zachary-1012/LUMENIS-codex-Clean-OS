"""
account/api.py — 账户体系 API 蓝图

统一到 /api/system/account/* 命名空间。
包含：资料/密码/设备/成员/审批/审计/恢复/密钥/验证码/TOTP/产品保护/导航/技能
"""
import json
from flask import Blueprint, request, jsonify, g

from .service import (
    get_current_user, require_auth, require_owner, require_admin_or_owner,
    create_member, list_members, update_member, remove_member,
    get_quota_counts, change_password, update_profile,
    list_sessions, revoke_session, ensure_account_initialized,
)
from .verification import (
    request_verification_code, verify_code, resend_code,
    list_pending_codes, VERIFICATION_CONFIG,
)
from .workspace_keys import (
    list_workspace_keys, create_workspace_key, revoke_workspace_key,
    get_rotation_required_count,
)
from .authorization import (
    get_member_authorizations, set_member_authorizations,
    check_dual_domain_permission,
)
from .audit import log_audit, query_audit_logs, get_audit_stats
from .totp import (
    get_totp_status, setup_totp, confirm_totp, verify_user_totp, reset_totp,
    TOTP_CONFIG,
)
from .product_protection import (
    get_protection_config, set_protection_config, check_protection_required,
)
from .nav_config import (
    get_nav_config, save_nav_config, reset_nav_config, get_all_nav_configs, DEFAULT_NAV,
)
from .skills import (
    list_skills, set_skill_status, configure_skill, add_custom_skill, get_enabled_skills,
    get_skill_info, execute_skill_api, get_skill_executions, get_skills_status_light,
    register_validated_skill,
)
from skill_package_runtime import preview_skill_source
from mcp_discovery import call_mcp_stdio, discover_mcp_stdio
from github_connector import GitHubConnector, GitHubConnectorError

account_bp = Blueprint("account", __name__, url_prefix="/api/system/account")


# ──────────────────────────────────────────────
# 账户资料
# ──────────────────────────────────────────────

@account_bp.route("/profile", methods=["GET"])
@require_auth
def api_get_profile():
    """当前用户资料"""
    user = g.current_user
    return jsonify({
        "ok": True,
        "profile": {
            "id": user["id"], "username": user["username"], "role": user["role"],
            "display_name": user.get("display_name"), "email": user.get("email"),
            "phone": user.get("phone"), "avatar": user.get("avatar"),
            "must_change_password": user.get("must_change_password", False),
        }
    })


@account_bp.route("/profile", methods=["PUT"])
@require_auth
def api_update_profile():
    """更新资料（头像/显示名/邮箱/手机）"""
    data = request.get_json(silent=True) or {}
    result = update_profile(
        g.current_user["id"],
        display_name=data.get("display_name"),
        email=data.get("email"),
        phone=data.get("phone"),
        avatar=data.get("avatar"),
    )
    if result["success"]:
        log_audit("profile_update", "account", str(g.current_user["id"]), "更新个人资料")
    return jsonify(result), 200 if result["success"] else 400


@account_bp.route("/change-password", methods=["POST"])
@require_auth
def api_change_password():
    """改密（验证旧密码）"""
    data = request.get_json(silent=True) or {}
    result = change_password(
        g.current_user["id"],
        data.get("old_password", ""),
        data.get("new_password", ""),
    )
    if result["success"]:
        log_audit("password_change", "security", str(g.current_user["id"]), "修改密码")
    return jsonify(result), 200 if result["success"] else 400


# ──────────────────────────────────────────────
# 受信任设备与会话
# ──────────────────────────────────────────────

@account_bp.route("/devices", methods=["GET"])
@require_auth
def api_list_devices():
    """受信任设备与会话列表"""
    user = g.current_user
    # owner/admin 看全部，普通用户看自己
    if user["role"] in ("owner", "admin"):
        sessions = list_sessions()
    else:
        sessions = list_sessions(user_id=user["id"])
    return jsonify({"ok": True, "devices": sessions, "current_session_id": user.get("session_id")})


@account_bp.route("/devices/<int:session_id>/revoke", methods=["POST"])
@require_auth
def api_revoke_device(session_id):
    """远程登出"""
    user = g.current_user
    # 普通用户只能吊销自己的会话
    if user["role"] not in ("owner", "admin"):
        sessions = list_sessions(user_id=user["id"])
        own_ids = {s["id"] for s in sessions}
        if session_id not in own_ids:
            return jsonify({"error": "只能吊销自己的会话"}), 403
    result = revoke_session(session_id)
    if result["success"]:
        log_audit("session_revoke", "security", str(session_id), f"用户{user['username']}远程登出会话{session_id}")
    return jsonify(result), 200 if result["success"] else 400


# ──────────────────────────────────────────────
# 成员管理（名额硬约束 1+3+5）
# ──────────────────────────────────────────────

@account_bp.route("/members", methods=["GET"])
@require_admin_or_owner
def api_list_members():
    """成员列表（含名额计数）"""
    members = list_members()
    quota = get_quota_counts()
    return jsonify({"ok": True, "members": members, "quota": quota})


@account_bp.route("/members", methods=["POST"])
@require_owner
def api_create_member():
    """新建/邀请成员（名额硬约束）"""
    data = request.get_json(silent=True) or {}
    result = create_member(
        username=data.get("username", ""),
        password=data.get("password", ""),
        role=data.get("role", "user"),
        display_name=data.get("display_name"),
        email=data.get("email"),
        created_by=g.current_user["id"],
    )
    if result["success"]:
        log_audit("member_create", "account", str(result.get("user_id")),
                  f"创建成员 {data.get('username')} 角色={data.get('role')}")
        return jsonify(result), 201
    if result.get("code") == "QUOTA_EXCEEDED":
        return jsonify(result), 403
    return jsonify(result), 400


@account_bp.route("/members/<int:user_id>", methods=["PUT"])
@require_admin_or_owner
def api_update_member(user_id):
    """更新成员（角色/授权/状态）"""
    data = request.get_json(silent=True) or {}
    # admin 不能改其他 admin 或 owner
    if g.current_user["role"] == "admin":
        from .models import get_db
        conn = get_db()
        try:
            cur = conn.execute("SELECT role FROM v4_users WHERE id=?", (user_id,))
            target = cur.fetchone()
            if target and target["role"] in ("owner", "admin"):
                return jsonify({"error": "管理员不能修改主账号或其他管理员"}), 403
        finally:
            conn.close()
    result = update_member(
        user_id,
        role=data.get("role"),
        status=data.get("status"),
        display_name=data.get("display_name"),
        email=data.get("email"),
        phone=data.get("phone"),
    )
    if result["success"]:
        log_audit("member_update", "account", str(user_id), f"更新成员 {user_id}")
    return jsonify(result), 200 if result["success"] else 400


@account_bp.route("/members/<int:user_id>", methods=["DELETE"])
@require_owner
def api_remove_member(user_id):
    """移除成员（释放名额）"""
    result = remove_member(user_id)
    if result["success"]:
        log_audit("member_remove", "account", str(user_id),
                  f"移除成员 {result.get('removed_username')}")
    return jsonify(result), 200 if result["success"] else 400


@account_bp.route("/members/<int:user_id>/authorizations", methods=["GET"])
@require_admin_or_owner
def api_get_member_auths(user_id):
    """获取成员双域授权矩阵"""
    auths = get_member_authorizations(user_id)
    return jsonify({"ok": True, "user_id": user_id, "authorizations": auths})


@account_bp.route("/members/<int:user_id>/authorizations", methods=["PUT"])
@require_owner
def api_set_member_auths(user_id):
    """设置成员双域授权矩阵"""
    data = request.get_json(silent=True) or {}
    auths = data.get("authorizations", [])
    result = set_member_authorizations(user_id, auths, granted_by=g.current_user["id"])
    return jsonify(result), 200 if result["success"] else 400


# ──────────────────────────────────────────────
# 登录审批
# ──────────────────────────────────────────────

@account_bp.route("/approvals", methods=["GET"])
@require_admin_or_owner
def api_list_approvals():
    """待审批登录列表"""
    from .models import get_db
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT * FROM v4_login_approvals WHERE status='pending' ORDER BY requested_at DESC LIMIT 50"
        )
        approvals = [dict(r) for r in cur.fetchall()]
        return jsonify({"ok": True, "approvals": approvals})
    finally:
        conn.close()


@account_bp.route("/approvals/<int:approval_id>/approve", methods=["POST"])
@require_admin_or_owner
def api_approve_login(approval_id):
    """批准登录"""
    from .models import get_db
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM v4_login_approvals WHERE id=? AND status='pending'", (approval_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "审批不存在或已处理"}), 404
        conn.execute(
            "UPDATE v4_login_approvals SET status='approved', decided_at=datetime('now','localtime'), decided_by=? WHERE id=?",
            (g.current_user["id"], approval_id)
        )
        conn.commit()
        log_audit("login_approve", "security", str(approval_id), f"批准登录 {row['username']}")
        return jsonify({"ok": True, "approval_id": approval_id, "status": "approved"})
    finally:
        conn.close()


@account_bp.route("/approvals/<int:approval_id>/reject", methods=["POST"])
@require_admin_or_owner
def api_reject_login(approval_id):
    """拒绝登录"""
    from .models import get_db
    data = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM v4_login_approvals WHERE id=? AND status='pending'", (approval_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "审批不存在或已处理"}), 404
        conn.execute(
            "UPDATE v4_login_approvals SET status='rejected', decided_at=datetime('now','localtime'), decided_by=?, reason=? WHERE id=?",
            (g.current_user["id"], data.get("reason", ""), approval_id)
        )
        conn.commit()
        log_audit("login_reject", "security", str(approval_id), f"拒绝登录 {row['username']}")
        return jsonify({"ok": True, "approval_id": approval_id, "status": "rejected"})
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 审计日志
# ──────────────────────────────────────────────

@account_bp.route("/audit", methods=["GET"])
@require_admin_or_owner
def api_audit_logs():
    """审计日志（分页）"""
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 50))
    result = query_audit_logs(
        page=page, page_size=page_size,
        username=request.args.get("username"),
        action=request.args.get("action"),
        start_date=request.args.get("start_date"),
        end_date=request.args.get("end_date"),
    )
    return jsonify({"ok": True, **result})


@account_bp.route("/audit/stats", methods=["GET"])
@require_admin_or_owner
def api_audit_stats():
    """审计统计"""
    return jsonify({"ok": True, **get_audit_stats()})


# ──────────────────────────────────────────────
# 账号恢复（复用 auth_recovery_center）
# ──────────────────────────────────────────────

@account_bp.route("/recovery", methods=["GET"])
@require_auth
def api_recovery_options():
    """恢复选项（复用 auth_recovery_center）"""
    from .models import get_db
    conn = get_db()
    try:
        cur = conn.execute("SELECT id, question, is_active FROM v4_security_questions")
        questions = [dict(r) for r in cur.fetchall()]
        return jsonify({
            "ok": True,
            "recovery_methods": ["security_questions", "recovery_code"],
            "security_questions": questions,
            "note": "复用现有 auth_recovery_center 安全问答+恢复码机制",
        })
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 工作区与程序化访问密钥
# ──────────────────────────────────────────────

@account_bp.route("/workspace-keys", methods=["GET"])
@require_admin_or_owner
def api_list_workspace_keys():
    """程序化访问密钥列表"""
    workspace = request.args.get("workspace")
    keys = list_workspace_keys(workspace)
    rotation = get_rotation_required_count()
    return jsonify({"ok": True, "keys": keys, "rotation_summary": rotation})


@account_bp.route("/workspace-keys", methods=["POST"])
@require_owner
def api_create_workspace_key():
    """创建程序化密钥（强制过期+绑定设备/IP）"""
    data = request.get_json(silent=True) or {}
    result = create_workspace_key(
        workspace=data.get("workspace", "ZBMP"),
        label=data.get("label", ""),
        created_by=g.current_user["id"],
        expires_days=int(data.get("expires_days", 30)),
        bound_device=data.get("bound_device"),
        bound_ip=data.get("bound_ip"),
        key_type=data.get("key_type", "programmatic"),
    )
    return jsonify(result), 201 if result["success"] else 400


@account_bp.route("/workspace-keys/<int:key_id>", methods=["DELETE"])
@require_owner
def api_revoke_workspace_key(key_id):
    """吊销密钥"""
    result = revoke_workspace_key(key_id)
    return jsonify(result), 200 if result["success"] else 400


# ──────────────────────────────────────────────
# 随机数字验证码（兜底通道）
# ──────────────────────────────────────────────

@account_bp.route("/verification/request", methods=["POST"])
@require_auth
def api_request_verification():
    """请求验证码（场景：workspace_unlock/sensitive_action/new_device）"""
    data = request.get_json(silent=True) or {}
    result = request_verification_code(
        scenario=data.get("scenario", "sensitive_action"),
        user_id=g.current_user["id"],
        code_length=data.get("code_length"),
        delivery_channel=data.get("delivery_channel", "in_app"),
    )
    status = result.pop("code", 200)
    return jsonify(result), status if result.get("success") else (status if status != 200 else 400)


@account_bp.route("/verification/verify", methods=["POST"])
@require_auth
def api_verify_code():
    """校验验证码（返回短期grant）"""
    data = request.get_json(silent=True) or {}
    result = verify_code(
        code_id=int(data.get("code_id", 0)),
        code_plain=data.get("code", ""),
        user_id=g.current_user["id"],
    )
    status = result.pop("code", 200)
    return jsonify(result), status if result.get("success") else (status if status != 200 else 400)


@account_bp.route("/verification/resend", methods=["POST"])
@require_auth
def api_resend_code():
    """重发验证码（受冷却限制）"""
    data = request.get_json(silent=True) or {}
    result = resend_code(
        scenario=data.get("scenario", "sensitive_action"),
        user_id=g.current_user["id"],
    )
    status = result.pop("code", 200)
    return jsonify(result), status if result.get("success") else (status if status != 200 else 400)


@account_bp.route("/verification/pending", methods=["GET"])
@require_auth
def api_pending_codes():
    """待批准验证码（受信任设备端查看）"""
    codes = list_pending_codes(user_id=g.current_user["id"])
    return jsonify({"ok": True, "pending": codes})


# ──────────────────────────────────────────────
# TOTP（ZBMP 访问保护主通道）
# ──────────────────────────────────────────────

@account_bp.route("/totp/status", methods=["GET"])
@require_auth
def api_totp_status():
    """TOTP 绑定状态"""
    status = get_totp_status(g.current_user["id"])
    return jsonify({"ok": True, **status, "config": TOTP_CONFIG})


@account_bp.route("/totp/setup", methods=["POST"])
@require_auth
def api_totp_setup():
    """初始化 TOTP（生成种子+QR码）"""
    data = request.get_json(silent=True) or {}
    result = setup_totp(g.current_user["id"], account_name=data.get("account_name"))
    return jsonify(result), 200 if result["success"] else 400


@account_bp.route("/totp/confirm", methods=["POST"])
@require_auth
def api_totp_confirm():
    """确认 TOTP 绑定"""
    data = request.get_json(silent=True) or {}
    result = confirm_totp(g.current_user["id"], data.get("code", ""))
    return jsonify(result), 200 if result["success"] else 400


@account_bp.route("/totp/verify", methods=["POST"])
def api_totp_verify():
    """校验 TOTP（ZBMP登录用，不需要先登录）。成功后颁发短期session。"""
    import time as _time
    from .security import generate_token, AUTH_CONFIG
    from .models import get_db
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "缺少 user_id"}), 400
    result = verify_user_totp(int(user_id), data.get("code", ""))
    status = result.pop("code", 200)
    if result["success"]:
        # 颁发短期 session（8小时，ZBMP工作区grant）
        conn = get_db()
        try:
            cur = conn.execute("SELECT username, role, display_name FROM v4_users WHERE id=? AND status='active'", (int(user_id),))
            user = cur.fetchone()
            if user:
                token = generate_token()
                expires_at = _time.strftime("%Y-%m-%d %H:%M:%S",
                    _time.localtime(_time.time() + 8 * 3600))
                ip = request.remote_addr if request else "unknown"
                ua = request.headers.get("User-Agent", "") if request else ""
                conn.execute(
                    "INSERT INTO v4_sessions (user_id, token, ip, user_agent, expires_at) VALUES (?,?,?,?,?)",
                    (int(user_id), token, ip, ua, expires_at)
                )
                conn.commit()
                result["token"] = token
                result["expires_at"] = expires_at
                result["user"] = {"id": int(user_id), "username": user["username"],
                                  "role": user["role"], "display_name": user["display_name"]}
                result["grant_type"] = "workspace"
                result["workspace"] = "ZBMP"
        finally:
            conn.close()
        log_audit("totp_verify", "security", str(user_id), "TOTP验证成功，颁发ZBMP工作区session")
    return jsonify(result), status if result.get("success") else (status if status != 200 else 400)


@account_bp.route("/totp/reset", methods=["POST"])
@require_owner
def api_totp_reset():
    """重置 TOTP"""
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id", g.current_user["id"]))
    result = reset_totp(user_id)
    return jsonify(result), 200 if result["success"] else 400


# ──────────────────────────────────────────────
# 产品保护配置（ZBMP=TOTP / CTH=密码 / SYSTEM=二次确认）
# ──────────────────────────────────────────────

@account_bp.route("/protection", methods=["GET"])
@require_auth
def api_get_protection():
    """获取产品保护配置"""
    product = request.args.get("product")
    config = get_protection_config(product)
    return jsonify({"ok": True, "protection": config})


@account_bp.route("/protection", methods=["PUT"])
@require_owner
def api_set_protection():
    """设置产品保护配置"""
    data = request.get_json(silent=True) or {}
    result = set_protection_config(
        product_id=data.get("product", ""),
        enabled=data.get("enabled"),
        method=data.get("method"),
        config_json=data.get("config_json"),
    )
    return jsonify(result), 200 if result["success"] else 400


# ──────────────────────────────────────────────
# 导航/工作台自定义
# ──────────────────────────────────────────────

@account_bp.route("/nav", methods=["GET"])
@require_auth
def api_get_nav():
    """获取导航配置"""
    domain = request.args.get("domain", "SYSTEM")
    nav = get_nav_config(g.current_user["id"], domain)
    return jsonify({"ok": True, "domain": domain, "nav_items": nav, "default": DEFAULT_NAV.get(domain.upper(), [])})


@account_bp.route("/nav", methods=["PUT"])
@require_auth
def api_save_nav():
    """保存导航配置"""
    data = request.get_json(silent=True) or {}
    result = save_nav_config(
        g.current_user["id"],
        data.get("domain", "SYSTEM"),
        data.get("nav_items", []),
    )
    return jsonify(result), 200 if result["success"] else 400


@account_bp.route("/nav/reset", methods=["POST"])
@require_auth
def api_reset_nav():
    """一键恢复默认导航"""
    data = request.get_json(silent=True) or {}
    result = reset_nav_config(g.current_user["id"], data.get("domain", "SYSTEM"))
    return jsonify(result)


# ──────────────────────────────────────────────
# 技能/Skills 管理
# ──────────────────────────────────────────────

@account_bp.route("/skills", methods=["GET"])
@require_auth
def api_list_skills():
    """技能列表"""
    product = request.args.get("product")
    status = request.args.get("status")
    skills = list_skills(product=product, status=status)
    return jsonify({"ok": True, "skills": skills})


@account_bp.route("/skills/source/preview", methods=["POST"])
@require_owner
def api_preview_skill_source():
    """只读探测 Skill 来源；不下载、不安装、不执行、不授予权限。"""
    data = request.get_json(silent=True) or {}
    source = data.get("source", "")
    result = preview_skill_source(
        source,
        resolve_remote=bool(data.get("resolve_remote", False)),
        fetch_remote_manifest=bool(data.get("fetch_remote_manifest", False)),
    )
    return jsonify(result), 200 if result.get("ok") else 400


@account_bp.route("/skills/source/register", methods=["POST"])
@require_owner
def api_register_skill_source():
    """登记已验证的 Skill 元数据；不安装、不执行、不授予权限。"""
    data = request.get_json(silent=True) or {}
    source = data.get("source", "")
    preview = preview_skill_source(
        source,
        resolve_remote=bool(data.get("resolve_remote", False)),
        fetch_remote_manifest=bool(data.get("fetch_remote_manifest", False)),
    )
    result = register_validated_skill(preview)
    return jsonify(result), 201 if result.get("success") else 400


@account_bp.route("/skills/source/mcp/discover", methods=["POST"])
@require_owner
def api_discover_mcp_source():
    """只读发现 MCP 能力；不调用工具、不注册、不授予权限。"""
    data = request.get_json(silent=True) or {}
    source = str(data.get("source") or "")
    from skill_package_runtime import detect_source
    detected = detect_source(source)
    if detected.source_type != "mcp_stdio":
        return jsonify({"ok": False, "state": "BLOCKED", "error": "source must be an mcp+stdio source"}), 400
    command = data.get("command")
    args = data.get("args", [])
    if not isinstance(command, list) or not isinstance(args, list):
        return jsonify({"ok": False, "state": "BLOCKED", "error": "command and args must be argv lists"}), 400
    result = discover_mcp_stdio(
        command,
        args,
        allow_process=bool(data.get("confirm_process", False)),
        timeout=float(data.get("timeout", 10.0)),
    )
    return jsonify(result), 200 if result.get("ok") else 400


@account_bp.route("/skills/source/mcp/call", methods=["POST"])
@require_owner
def api_call_mcp_tool():
    """Call one reviewed read-only MCP tool; never persist its result."""
    data = request.get_json(silent=True) or {}
    source = str(data.get("source") or "")
    from skill_package_runtime import detect_source
    detected = detect_source(source)
    if detected.source_type != "mcp_stdio":
        return jsonify({
            "ok": False, "state": "BLOCKED",
            "error": "source must be an mcp+stdio source",
        }), 400
    command = data.get("command")
    args = data.get("args", [])
    if not isinstance(command, list) or not isinstance(args, list):
        return jsonify({
            "ok": False, "state": "BLOCKED",
            "error": "command and args must be argv lists",
        }), 400
    tool_name = data.get("tool_name")
    permissions = data.get("permissions_granted", [])
    allowed_tools = data.get("allowed_tools", [])
    arguments = data.get("arguments", {})
    if not isinstance(tool_name, str) or not isinstance(permissions, list):
        return jsonify({
            "ok": False, "state": "BLOCKED",
            "error": "tool_name and permissions_granted are required",
        }), 400
    if not isinstance(allowed_tools, list) or not isinstance(arguments, dict):
        return jsonify({
            "ok": False, "state": "BLOCKED",
            "error": "allowed_tools must be a list and arguments must be an object",
        }), 400
    try:
        timeout = float(data.get("timeout", 10.0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "state": "BLOCKED", "error": "timeout is invalid"}), 400
    result = call_mcp_stdio(
        command,
        args,
        tool_name=tool_name,
        arguments=arguments,
        allow_process=data.get("confirm_process") is True,
        allow_tool_call=data.get("confirm_tool_call") is True,
        human_approved=data.get("human_approved") is True,
        permissions_granted=permissions,
        allowed_tools=allowed_tools,
        timeout=timeout,
    )
    return jsonify(result), 200 if result.get("ok") else 400


@account_bp.route("/connectors/github/status", methods=["GET"])
@require_owner
def api_github_connector_status():
    """Return GitHub connector state without exposing credential material."""
    return jsonify({"ok": True, "connector": GitHubConnector().status()})


@account_bp.route("/connectors/github/authorization-url", methods=["POST"])
@require_owner
def api_github_authorization_url():
    """Build an OAuth request; callback state must be persisted and verified by the host."""
    data = request.get_json(silent=True) or {}
    try:
        url = GitHubConnector().authorization_url(data.get("state", ""))
    except GitHubConnectorError as exc:
        return jsonify({"ok": False, "code": exc.code, "error": str(exc)}), 400
    return jsonify({
        "ok": True,
        "authorization_url": url,
        "state_handling": "host_must_persist_and_verify_before_callback_exchange",
        "write_enabled": False,
    })


@account_bp.route("/skills/<skill_id>/enable", methods=["POST"])
@require_owner
def api_enable_skill(skill_id):
    """启用技能"""
    result = set_skill_status(skill_id, "enabled")
    return jsonify(result), 200 if result["success"] else 400


@account_bp.route("/skills/<skill_id>/disable", methods=["POST"])
@require_owner
def api_disable_skill(skill_id):
    """禁用技能"""
    result = set_skill_status(skill_id, "disabled")
    return jsonify(result), 200 if result["success"] else 400


@account_bp.route("/skills/<skill_id>/config", methods=["PUT"])
@require_owner
def api_configure_skill(skill_id):
    """配置技能"""
    data = request.get_json(silent=True) or {}
    result = configure_skill(skill_id, data.get("config", {}))
    return jsonify(result), 200 if result["success"] else 400


@account_bp.route("/skills", methods=["POST"])
@require_owner
def api_add_skill():
    """添加自定义技能"""
    data = request.get_json(silent=True) or {}
    result = add_custom_skill(
        skill_id=data.get("skill_id", ""),
        name=data.get("name", ""),
        description=data.get("description", ""),
        product=data.get("product", "SYSTEM"),
        domain=data.get("domain", "global"),
    )
    return jsonify(result), 201 if result["success"] else 400


@account_bp.route("/skills/<skill_id>/execute", methods=["POST"])
@require_auth
def api_execute_skill(skill_id):
    """执行 Skill（走完整执行链：Permission→Firewall→Effect Fence→Execute→Evidence→Evaluation→Trace）"""
    data = request.get_json(silent=True) or {}
    user = g.current_user
    result = execute_skill_api(
        skill_id=skill_id,
        task=data.get("task", ""),
        input_payload=data.get("input", {}),
        action_type=data.get("action_type", "ANALYZE"),
        user_id=user.get("id"),
        user_role=user.get("role", "user"),
        product=data.get("product", "SYSTEM"),
    )
    status_code = 200 if result.get("success") else (404 if result.get("code") == "NOT_FOUND" else 400)
    return jsonify(result), status_code


@account_bp.route("/skills/<skill_id>/executions", methods=["GET"])
@require_auth
def api_skill_executions(skill_id):
    """Skill 执行历史"""
    limit = int(request.args.get("limit", 50))
    status = request.args.get("status")
    execs = get_skill_executions(skill_id=skill_id, limit=limit, status=status)
    return jsonify({"ok": True, "skill_id": skill_id, "executions": execs, "total": len(execs)})


@account_bp.route("/skills/status", methods=["GET"])
@require_auth
def api_skills_status():
    """轻量状态（主界面小卡片用，函数驱动真实数据）"""
    product = request.args.get("product")
    status = get_skills_status_light(product=product)
    return jsonify({"ok": True, **status})


@account_bp.route("/skills/<skill_id>", methods=["GET"])
@require_auth
def api_get_skill_detail(skill_id):
    """单个 Skill 详情（含配置+最近执行）"""
    info = get_skill_info(skill_id)
    if not info:
        return jsonify({"ok": False, "error": "skill not found"}), 404
    return jsonify({"ok": True, "skill": info})


# ──────────────────────────────────────────────
# 名额计数（公开端点，前端展示用）
# ──────────────────────────────────────────────

@account_bp.route("/quota", methods=["GET"])
@require_auth
def api_quota():
    """名额计数"""
    return jsonify({"ok": True, "quota": get_quota_counts()})
