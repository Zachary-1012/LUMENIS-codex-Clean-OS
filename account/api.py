"""
account/api.py — 账户体系 API 蓝图

统一到 /api/system/account/* 命名空间。
包含：资料/密码/设备/成员/审批/审计/恢复/密钥/验证码/产品保护/导航/技能
"""
import json
import threading as _threading
import time as _time
import uuid as _uuid
import sqlite3 as _sqlite3
from urllib.parse import urlsplit as _urlsplit
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
from .product_protection import (
    get_protection_config, set_protection_config, check_protection_required,
)
from .nav_config import (
    get_nav_config, save_nav_config, reset_nav_config, get_all_nav_configs, DEFAULT_NAV,
)
from .skills import (
    list_skills, set_skill_status, configure_skill, add_custom_skill, get_enabled_skills,
    get_skill_info, execute_skill_api, get_skill_executions, get_skills_status_light,
    register_validated_skill, activate_installed_mcp_skill,
)
from lumenis.shared.agents.skills.package_runtime import preview_skill_source
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
# 产品保护配置（ZBMP=密码 / CTH=密码 / SYSTEM=二次确认）
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


@account_bp.route("/skills/source/activate", methods=["POST"])
@require_owner
def api_activate_installed_skill():
    """Activate a built, locally installed MCP Skill after its self-test.

    The endpoint never downloads or executes an arbitrary path.  The runtime
    adapter accepts only packages under the canonical Skill package root and
    records the result in the existing registry; enabling remains separate.
    """
    data = request.get_json(silent=True) or {}
    skill_id = str(data.get("skill_id") or "").strip()
    install_path = str(data.get("install_path") or "").strip()
    result = activate_installed_mcp_skill(
        skill_id,
        install_path,
        revision=str(data.get("revision") or "").strip(),
        digest=str(data.get("digest") or "").strip(),
    )
    return jsonify(result), 200 if result.get("success") else 400


# Short-lived server-issued candidates, bound to actor and registry snapshot.
# Multi-worker misses fail closed; clients repeat preparation on that worker.
_MCP_REVIEW_LOCK = _threading.RLock()
_MCP_REVIEW_CANDIDATES = {}


def _mcp_same_origin():
    """Match the product's browser-origin policy; native bearer clients may omit Origin."""
    if not request.is_json:
        return False
    if request.headers.get("Sec-Fetch-Site", "").lower() in {"cross-site", "cross-origin"}:
        return False
    candidate = request.headers.get("Origin", request.headers.get("Referer"))
    if candidate is None:
        return True
    try:
        parsed = _urlsplit(candidate)
        return (
            parsed.scheme in {"http", "https"}
            and not parsed.username
            and not parsed.password
            and parsed.scheme.lower() == request.scheme.lower()
            and parsed.netloc.lower() == request.host.lower()
        )
    except (ValueError, TypeError):
        return False


def _mcp_review_scope(data):
    """Recheck the authenticated actor's current exact skills scope before process startup."""
    from lumenis.system.security import permission

    scope = {
        "domain_id": data.get("domain_id", "cth"),
        "subject_id": data.get("subject_id"),
        "brand_focus_id": data.get("brand_focus_id"),
        "global_scope": data.get("global_scope", True),
    }
    decision = permission.check_actor_scope_permission(
        {"id": g.current_user["id"]},
        action="write",
        module="skills",
        gate=permission.get_permission_gate(),
        **scope,
    )
    if (
        type(decision) is not permission.ActorScopePermissionResult
        or decision.allowed is not True
        or decision.verification_state != "verified"
    ):
        raise PermissionError("MCP_SKILL_SCOPE_DENIED")
    return scope


@account_bp.route("/skills/source/mcp/discover", methods=["POST"])
@require_owner
def api_discover_mcp_source():
    """Discover only the registered entrypoint; request argv is never executed."""
    from mcp_skill_runtime import discover_registered_mcp

    if not _mcp_same_origin():
        return jsonify({"ok": False, "error": "MCP_SAME_ORIGIN_JSON_REQUIRED"}), 403
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "MCP request must be a JSON object"}), 400
    skill_id = data.get("skill_id")
    if (
        not isinstance(skill_id, str)
        or not skill_id
        or any(k in data for k in ("command", "args", "source"))
    ):
        return (
            jsonify(
                {
                    "ok": False,
                    "state": "REGISTERED_SKILL_REQUIRED",
                    "error": "Use skill_id for an installed registered MCP Skill; arbitrary argv discovery is disabled.",
                }
            ),
            400,
        )
    if data.get("confirm_process") is not True:
        return (
            jsonify({"ok": False, "state": "BLOCKED", "error": "confirm_process must be true"}),
            400,
        )
    info = get_skill_info(skill_id)
    if not info or info.get("runtime") != "mcp":
        return jsonify({"ok": False, "state": "REGISTERED_SKILL_REQUIRED"}), 404
    try:
        _mcp_review_scope(data)
    except PermissionError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    result = discover_registered_mcp(info)
    return jsonify(result), 200 if result.get("ok") else 400


@account_bp.route("/skills/<skill_id>/mcp/contract/prepare", methods=["POST"])
@require_owner
def api_prepare_mcp_contract(skill_id):
    from lumenis.shared.agents.skills.lifecycle import prepare_skill_metadata_change
    from lumenis.system.security import permission

    if not _mcp_same_origin():
        return jsonify({"ok": False, "error": "MCP_SAME_ORIGIN_JSON_REQUIRED"}), 403
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "MCP request must be a JSON object"}), 400
    if any(key in data for key in ("discovery", "tools", "tool_contracts", "command", "args")):
        return jsonify({"ok": False, "error": "Contract discovery must be server-generated"}), 400
    try:
        actor = g.current_user["id"]
        scope = _mcp_review_scope(data)
        candidate = prepare_skill_metadata_change(
            skill_id,
            "review_mcp_contract",
            operation_id=str(_uuid.uuid4()),
            confirm_process=data.get("confirm_process") is True,
        )
        resource = permission.skill_metadata_approval_resource(
            candidate, actor_id=actor, principal=None, **scope
        )
        with _MCP_REVIEW_LOCK:
            now = _time.monotonic()
            for key, item in list(_MCP_REVIEW_CANDIDATES.items()):
                if item[0] <= now:
                    del _MCP_REVIEW_CANDIDATES[key]
            if len(_MCP_REVIEW_CANDIDATES) >= 128:
                return jsonify({"ok": False, "error": "Too many pending contract reviews"}), 429
            _MCP_REVIEW_CANDIDATES[candidate.candidate_sha256] = (
                now + 300,
                actor,
                candidate,
                scope,
            )
        return jsonify(
            {
                "ok": True,
                "candidate": candidate.to_dict(),
                "approval_resource": resource,
                "expires_in_seconds": 300,
                "next": "Review schemas, then POST confirm=true and candidate_sha256 to mcp/contract/approve",
            }
        )
    except (ValueError, PermissionError, LookupError, RuntimeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@account_bp.route("/skills/<skill_id>/mcp/contract/approve", methods=["POST"])
@require_owner
def api_approve_mcp_contract(skill_id):
    from lumenis.shared.agents.skills.lifecycle import apply_skill_metadata_change
    from lumenis.system.security import permission

    if not _mcp_same_origin():
        return jsonify({"ok": False, "error": "MCP_SAME_ORIGIN_JSON_REQUIRED"}), 403
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "MCP request must be a JSON object"}), 400
    fingerprint = data.get("candidate_sha256")
    if data.get("confirm") is not True or not isinstance(fingerprint, str):
        return (
            jsonify({"ok": False, "error": "Exact candidate_sha256 and confirm=true are required"}),
            400,
        )
    with _MCP_REVIEW_LOCK:
        entry = _MCP_REVIEW_CANDIDATES.get(fingerprint)
        if (
            not entry
            or entry[0] <= _time.monotonic()
            or entry[1] != g.current_user["id"]
            or entry[2].skill_id != skill_id
        ):
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "Contract review expired or does not match actor/Skill; prepare again",
                    }
                ),
                409,
            )
        _expires, actor, candidate, scope = entry
        gate = permission.get_permission_gate()
        spec = gate.get_operation_spec(permission.OperationType.CONFIG_MODIFY)
        if (
            permission.is_testing_bypass_enabled()
            or not gate.has_permission(permission.PermissionLevel.COMMIT)
            or spec.permission is not permission.PermissionLevel.COMMIT
            or spec.risk not in {permission.RiskLevel.HIGH, permission.RiskLevel.CRITICAL}
            or spec.auto_allow is not False
        ):
            return (
                jsonify(
                    {"ok": False, "error": "Canonical COMMIT/manual approval policy is required"}
                ),
                403,
            )
        token = None
        try:
            resource = permission.skill_metadata_approval_resource(
                candidate, actor_id=actor, principal=None, **scope
            )
            token = gate.grant_approval(
                permission.OperationType.CONFIG_MODIFY.value,
                duration_minutes=5,
                resource=resource,
                granted_by=f"mcp_contract_owner:{actor}",
            )
            result = apply_skill_metadata_change(
                candidate, gate=gate, actor_id=actor, principal=None, **scope
            )
            del _MCP_REVIEW_CANDIDATES[fingerprint]
            return jsonify(
                {
                    "ok": True,
                    "result": result,
                    "next": "Skill remains disabled. Re-run the existing local activation/self-check for the same package, then enable and execute. A changed runtime requires a fresh contract review.",
                }
            )
        except _sqlite3.DatabaseError:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "MCP contract approval storage is not ready; initialize the canonical database first",
                    }
                ),
                503,
            )
        except (ValueError, PermissionError, LookupError, RuntimeError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 403
        finally:
            if token:
                gate.revoke_approval(token)


@account_bp.route("/skills/source/mcp/call", methods=["POST"])
@require_owner
def api_call_mcp_tool():
    """Compatibility endpoint delegates to the canonical registered execution chain."""
    if not _mcp_same_origin():
        return jsonify({"ok": False, "error": "MCP_SAME_ORIGIN_JSON_REQUIRED"}), 403
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "MCP request must be a JSON object"}), 400
    skill_id = data.get("skill_id")
    if (
        not isinstance(skill_id, str)
        or not skill_id
        or any(
            k in data
            for k in (
                "command",
                "args",
                "source",
                "permissions_granted",
                "allowed_tools",
                "tool_contracts",
            )
        )
    ):
        return (
            jsonify(
                {
                    "ok": False,
                    "state": "REGISTERED_SKILL_REQUIRED",
                    "error": "Use a registered skill_id: prepare/approve its mcp/contract, enable it, then call /skills/<skill_id>/execute. Client-provided argv and grants are not accepted.",
                }
            ),
            400,
        )
    info = get_skill_info(skill_id)
    if not info or info.get("runtime") != "mcp":
        return jsonify({"ok": False, "state": "REGISTERED_SKILL_REQUIRED"}), 404
    payload = {
        key: data[key]
        for key in ("tool_name", "arguments", "human_approved", "timeout")
        if key in data
    }
    result = execute_skill_api(
        skill_id=skill_id,
        input_payload=payload,
        user_id=g.current_user["id"],
        product=data.get("product"),
    )
    return jsonify(result), 200 if result.get("success") else 400


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


def _builtin_skill_status_actor():
    from lumenis.auth.service import get_current_user as current_user
    from lumenis.system.security.permission import resolve_local_workspace_principal
    actor = current_user(read_only=True)
    if isinstance(actor, dict):
        if actor.get('role') != 'owner':
            raise PermissionError('SKILL_STATUS_OWNER_REQUIRED')
        return actor
    actor = resolve_local_workspace_principal(module='skills', action='write')
    if actor is None:
        raise PermissionError('SKILL_STATUS_IDENTITY_REQUIRED')
    return actor


def authorize_builtin_skill_status_root_request():
    """Delegate only the original explicit builtin status confirmation routes."""
    entries = {'account.api_enable_skill': '/api/system/account/skills/<skill_id>/enable',
               'account.api_disable_skill': '/api/system/account/skills/<skill_id>/disable'}
    try:
        if (request.method != 'POST' or request.endpoint not in entries or request.url_rule is None
                or request.url_rule.rule != entries[request.endpoint]):
            return False
        body = request.get_json(silent=True)
        if type(body) is not dict or body.get('mode') not in {'prepare', 'confirm'}:
            return False
        from .skills import _builtin_status_row, _builtin_status_identity
        from lumenis.shared.database import get_repository
        with get_repository().connection(read_only=True, wal=False) as connection:
            _builtin_status_identity(_builtin_skill_status_actor(), connection)
            _builtin_status_row(connection, (request.view_args or {}).get('skill_id'))
        return True
    except (PermissionError, ValueError, LookupError, RuntimeError):
        return False


def _builtin_skill_status_response(skill_id, status):
    from .skills import prepare_builtin_skill_status, confirm_builtin_skill_status
    try:
        data = request.get_json(silent=True)
        if request.args or type(data) is not dict or (request.content_length or 0) > 8192:
            raise ValueError('SKILL_STATUS_REQUEST_INVALID')
        actor = _builtin_skill_status_actor()
        if data.get('mode') == 'prepare' and set(data) == {'mode', 'operation_id'}:
            result = prepare_builtin_skill_status(skill_id, status, actor=actor, operation_id=data['operation_id'])
        elif data.get('mode') == 'confirm' and set(data) == {
                'mode', 'operation_id', 'expected_binding', 'confirm', 'confirmed_resource'}:
            from experience_runtime import _content_source_same_origin
            result = confirm_builtin_skill_status(skill_id, status, actor=actor,
                operation_id=data['operation_id'], expected_binding=data['expected_binding'],
                confirm=data['confirm'], confirmed_resource=data['confirmed_resource'],
                same_origin=_content_source_same_origin())
        else:
            raise ValueError('SKILL_STATUS_REQUEST_INVALID')
        return jsonify({'ok': True, 'success': True, 'result': result})
    except PermissionError as exc:
        return jsonify({'ok': False, 'code': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'ok': False, 'code': str(exc)}), 400
    except LookupError:
        return jsonify({'ok': False, 'code': 'SKILL_NOT_REGISTERED'}), 404
    except RuntimeError as exc:
        return jsonify({'ok': False, 'code': str(exc)}), 409
    except Exception:
        return jsonify({'ok': False, 'code': 'SKILL_STATUS_UNAVAILABLE'}), 503


@require_owner
def _legacy_skill_status(skill_id, status):
    result = set_skill_status(skill_id, status)
    return jsonify(result), 200 if result['success'] else 400


@account_bp.route("/skills/<skill_id>/enable", methods=["POST"])
def api_enable_skill(skill_id):
    """Enable the selected skill; explicit builtin mode also supports local work."""
    data = request.get_json(silent=True)
    if isinstance(data, dict) and 'mode' in data:
        return _builtin_skill_status_response(skill_id, 'enabled')
    return _legacy_skill_status(skill_id, 'enabled')


@account_bp.route("/skills/<skill_id>/disable", methods=["POST"])
def api_disable_skill(skill_id):
    """禁用技能"""
    data = request.get_json(silent=True)
    if isinstance(data, dict) and 'mode' in data:
        return _builtin_skill_status_response(skill_id, 'disabled')
    return _legacy_skill_status(skill_id, 'disabled')


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
        # Product is a requested lens only; execute_skill_api rechecks it
        # against the authenticated user's server-side authorization matrix.
        product=data.get("product"), scope=data.get("scope"),
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
