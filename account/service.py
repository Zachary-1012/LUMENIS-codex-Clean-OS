"""
account/service.py — 核心业务逻辑

用户/成员管理、名额硬约束(1+3+5)、会话管理、资料/密码修改。
AI 不参与授权判定，完全由规则+DB状态决定。
"""
import time
from functools import wraps
from flask import request, jsonify, g

from .models import get_db
from .security import (
    verify_password, generate_token, check_login_attempts,
    record_login_attempt, AUTH_CONFIG, QUOTA_LIMITS, hash_password,
)

_initialized = False


def ensure_account_initialized():
    global _initialized
    if not _initialized:
        from .models import init_account_db
        init_account_db()
        _initialized = True


# ──────────────────────────────────────────────
# 认证与会话
# ──────────────────────────────────────────────

def get_current_user() -> dict:
    """从请求 Header/Cookie 获取当前登录用户"""
    ensure_account_initialized()
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get(AUTH_CONFIG["session_cookie_name"])
    if not token:
        return None

    conn = get_db()
    try:
        cur = conn.execute("""
            SELECT u.*, s.expires_at, s.id as session_id, s.ip as session_ip, s.user_agent as session_ua
            FROM v4_sessions s
            JOIN v4_users u ON u.id = s.user_id
            WHERE s.token=? AND u.status='active'
        """, (token,))
        row = cur.fetchone()
        if not row:
            return None
        if row["expires_at"] < time.strftime("%Y-%m-%d %H:%M:%S"):
            conn.execute("DELETE FROM v4_sessions WHERE token=?", (token,))
            conn.commit()
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
            "display_name": row["display_name"],
            "email": row["email"],
            "avatar": row["avatar"] if "avatar" in row.keys() else None,
            "phone": row["phone"] if "phone" in row.keys() else None,
            "must_change_password": bool(row["must_change_password"]),
            "token": token,
            "session_id": row["session_id"],
        }
    finally:
        conn.close()


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "未登录或登录已过期"}), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def require_owner(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "未登录"}), 401
        if user["role"] != "owner":
            return jsonify({"error": "仅主账号可操作"}), 403
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def require_admin_or_owner(f):
    """管理员或主账号可操作（成员管理等）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "未登录"}), 401
        if user["role"] not in ("owner", "admin"):
            return jsonify({"error": "权限不足，仅管理员或主账号可操作"}), 403
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────
# 名额硬约束
# ──────────────────────────────────────────────

def get_quota_counts() -> dict:
    """
    返回名额使用计数。
    停用(disabled)仍占名额，只有删除才释放。
    """
    conn = get_db()
    try:
        cur = conn.execute("SELECT role, COUNT(*) as cnt FROM v4_users GROUP BY role")
        counts = {row["role"]: row["cnt"] for row in cur.fetchall()}
        admin_used = counts.get("admin", 0)
        member_used = counts.get("user", 0)  # role='user' 即 member
        owner_used = counts.get("owner", 0)
        return {
            "owner": {"used": owner_used, "limit": QUOTA_LIMITS["owner"]},
            "admin": {"used": admin_used, "limit": QUOTA_LIMITS["admin"]},
            "member": {"used": member_used, "limit": QUOTA_LIMITS["member"]},
        }
    finally:
        conn.close()


def _check_quota(role: str) -> dict:
    """检查名额是否已满。role: admin/member"""
    quota = get_quota_counts()
    key = "member" if role == "user" else role
    if quota[key]["used"] >= quota[key]["limit"]:
        return {
            "allowed": False,
            "error": f"名额已满，{key}上限{quota[key]['limit']}（当前{quota[key]['used']}），请先移除成员释放名额",
        }
    return {"allowed": True}


# ──────────────────────────────────────────────
# 成员管理
# ──────────────────────────────────────────────

def create_member(username: str, password: str, role: str = "user",
                  display_name: str = None, email: str = None,
                  created_by: int = None) -> dict:
    """
    创建成员（admin 或 member/user）。
    强制名额硬约束：admin<=3, member<=5（含停用）。
    """
    ensure_account_initialized()
    role = role.lower().strip()
    if role not in ("admin", "user"):
        return {"success": False, "error": "角色必须是 admin 或 member"}
    # 内部统一用 user 表示 member
    db_role = "user" if role == "member" else role

    # 名额检查
    quota_check = _check_quota(db_role)
    if not quota_check["allowed"]:
        return {"success": False, "error": quota_check["error"], "code": "QUOTA_EXCEEDED"}

    conn = get_db()
    try:
        cur = conn.execute("SELECT COUNT(*) as cnt FROM v4_users WHERE username=?", (username,))
        if cur.fetchone()["cnt"] > 0:
            return {"success": False, "error": "用户名已存在"}

        pwd_hash = hash_password(password)
        conn.execute(
            """INSERT INTO v4_users (username, password_hash, role, display_name, email, must_change_password)
               VALUES (?,?,?,?,?,1)""",
            (username, pwd_hash, db_role, display_name or username, email)
        )
        conn.commit()
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return {"success": True, "user_id": user_id, "must_change_password": True,
                "role": db_role, "quota": get_quota_counts()}
    finally:
        conn.close()


def list_members() -> list:
    """列出所有成员（含名额计数信息）"""
    conn = get_db()
    try:
        cur = conn.execute("""
            SELECT id, username, role, display_name, email, phone, avatar, status,
                   last_login_at, last_login_ip, created_at, failed_attempts, locked_until,
                   must_change_password
            FROM v4_users
            ORDER BY CASE role WHEN 'owner' THEN 1 WHEN 'admin' THEN 2 ELSE 3 END, id
        """)
        members = [dict(row) for row in cur.fetchall()]
        # 补充授权矩阵
        for m in members:
            m["authorizations"] = _get_auths_for_user(conn, m["id"])
        return members
    finally:
        conn.close()


def _get_auths_for_user(conn, user_id):
    cur = conn.execute(
        "SELECT product_id, module, action, data_scope, time_range FROM v4_member_authorizations WHERE user_id=?",
        (user_id,)
    )
    return [dict(r) for r in cur.fetchall()]


def update_member(user_id: int, role: str = None, status: str = None,
                  display_name: str = None, email: str = None,
                  phone: str = None) -> dict:
    """更新成员信息（角色/状态/资料）。不能改 owner。"""
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM v4_users WHERE id=?", (user_id,))
        user = cur.fetchone()
        if not user:
            return {"success": False, "error": "用户不存在"}
        if user["role"] == "owner":
            return {"success": False, "error": "不能修改主账号"}

        updates = []
        params = []
        if role and role != user["role"]:
            if role not in ("admin", "user"):
                return {"success": False, "error": "无效角色"}
            # 角色变更也要检查目标名额
            quota_check = _check_quota(role)
            if not quota_check["allowed"]:
                return {"success": False, "error": quota_check["error"], "code": "QUOTA_EXCEEDED"}
            updates.append("role=?")
            params.append(role)
        if status:
            if status not in ("active", "disabled"):
                return {"success": False, "error": "状态必须是 active 或 disabled"}
            updates.append("status=?")
            params.append(status)
        if display_name is not None:
            updates.append("display_name=?")
            params.append(display_name)
        if email is not None:
            updates.append("email=?")
            params.append(email)
        if phone is not None:
            updates.append("phone=?")
            params.append(phone)

        if not updates:
            return {"success": True, "message": "无变更"}

        updates.append("updated_at=datetime('now','localtime')")
        params.append(user_id)
        conn.execute(f"UPDATE v4_users SET {', '.join(updates)} WHERE id=?", params)
        conn.commit()
        return {"success": True, "quota": get_quota_counts()}
    finally:
        conn.close()


def remove_member(user_id: int) -> dict:
    """
    移除成员（删除记录，释放名额）。不能删 owner。
    同时清理其授权矩阵和会话。
    """
    conn = get_db()
    try:
        cur = conn.execute("SELECT role, username FROM v4_users WHERE id=?", (user_id,))
        user = cur.fetchone()
        if not user:
            return {"success": False, "error": "用户不存在"}
        if user["role"] == "owner":
            return {"success": False, "error": "不能删除主账号"}

        conn.execute("DELETE FROM v4_member_authorizations WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM v4_sessions WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM v4_users WHERE id=?", (user_id,))
        conn.commit()
        return {"success": True, "removed_username": user["username"],
                "quota": get_quota_counts()}
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 资料与密码
# ──────────────────────────────────────────────

def update_profile(user_id: int, display_name: str = None, email: str = None,
                   phone: str = None, avatar: str = None) -> dict:
    """更新当前用户资料"""
    conn = get_db()
    try:
        updates = []
        params = []
        if display_name is not None:
            updates.append("display_name=?")
            params.append(display_name)
        if email is not None:
            updates.append("email=?")
            params.append(email)
        if phone is not None:
            updates.append("phone=?")
            params.append(phone)
        if avatar is not None:
            updates.append("avatar=?")
            params.append(avatar)
        if not updates:
            return {"success": True, "message": "无变更"}
        updates.append("updated_at=datetime('now','localtime')")
        params.append(user_id)
        conn.execute(f"UPDATE v4_users SET {', '.join(updates)} WHERE id=?", params)
        conn.commit()
        return {"success": True}
    finally:
        conn.close()


def change_password(user_id: int, old_password: str, new_password: str) -> dict:
    """修改密码（验证旧密码）"""
    conn = get_db()
    try:
        cur = conn.execute("SELECT password_hash FROM v4_users WHERE id=?", (user_id,))
        user = cur.fetchone()
        if not user or not verify_password(old_password, user["password_hash"]):
            return {"success": False, "error": "原密码错误"}
        if len(new_password) < 6:
            return {"success": False, "error": "新密码至少6位"}
        conn.execute(
            "UPDATE v4_users SET password_hash=?, must_change_password=0, updated_at=datetime('now','localtime') WHERE id=?",
            (hash_password(new_password), user_id)
        )
        conn.commit()
        return {"success": True}
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 受信任设备与会话
# ──────────────────────────────────────────────

def list_sessions(user_id: int = None) -> list:
    """列出会话（受信任设备）。不传 user_id 则列全部。"""
    conn = get_db()
    try:
        if user_id:
            cur = conn.execute("""
                SELECT s.id, s.user_id, s.ip, s.user_agent, s.expires_at, s.created_at,
                       u.username, u.display_name
                FROM v4_sessions s JOIN v4_users u ON u.id = s.user_id
                WHERE s.user_id=? ORDER BY s.created_at DESC
            """, (user_id,))
        else:
            cur = conn.execute("""
                SELECT s.id, s.user_id, s.ip, s.user_agent, s.expires_at, s.created_at,
                       u.username, u.display_name
                FROM v4_sessions s JOIN v4_users u ON u.id = s.user_id
                ORDER BY s.created_at DESC LIMIT 100
            """)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        sessions = []
        for row in cur.fetchall():
            d = dict(row)
            d["is_active"] = d["expires_at"] >= now
            sessions.append(d)
        return sessions
    finally:
        conn.close()


def revoke_session(session_id: int, current_user_id: int = None) -> dict:
    """远程登出（吊销会话）。不能吊销自己当前会话以外的限制由调用方控制。"""
    conn = get_db()
    try:
        if current_user_id:
            cur = conn.execute("SELECT user_id FROM v4_sessions WHERE id=?", (session_id,))
            row = cur.fetchone()
            if not row:
                return {"success": False, "error": "会话不存在"}
        conn.execute("DELETE FROM v4_sessions WHERE id=?", (session_id,))
        conn.commit()
        return {"success": True, "revoked": session_id}
    finally:
        conn.close()
