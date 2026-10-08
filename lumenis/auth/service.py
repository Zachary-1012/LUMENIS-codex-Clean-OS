"""
认证服务：登录、登出、会话管理、权限校验
"""
import time
import sqlite3
from functools import wraps
from flask import request, jsonify, g, has_request_context
from .models import get_db, init_auth_db
from .security import (
    verify_password, generate_token, check_login_attempts,
    record_login_attempt, verify_security_questions, normalize_login_ip
)
from ..config import AUTH_CONFIG, ROLE_PERMISSIONS

# 模块级标记，确保只初始化一次
_initialized = False


def ensure_initialized():
    global _initialized
    if not _initialized:
        init_auth_db()
        _initialized = True


def login(username: str, password: str, ip: str = None, user_agent: str = None) -> dict:
    """
    用户登录
    返回: {"success": bool, "token": str, "user": dict, "error": str}
    """
    ensure_initialized()
    if not ip and has_request_context():
        ip = request.remote_addr
    ip = normalize_login_ip(ip)

    # 检查登录限流
    check = check_login_attempts(username, ip)
    if not check["allowed"]:
        return {"success": False, "error": f"账号已锁定，请{check['locked_until']}后再试", "remaining": 0}

    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM v4_users WHERE username=? AND status='active'", (username,))
        user = cur.fetchone()
        if not user or not verify_password(password, user["password_hash"]):
            record_login_attempt(username, ip, False)
            remaining = check["remaining"] - 1
            return {
                "success": False,
                "error": f"用户名或密码错误，剩余尝试次数：{max(0, remaining)}",
                "remaining": max(0, remaining)
            }

        # 登录成功
        record_login_attempt(username, ip, True)
        token = generate_token(user["id"])
        expires_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + AUTH_CONFIG["token_expire_hours"] * 3600))

        conn.execute(
            "INSERT INTO v4_sessions (user_id, token, ip, user_agent, expires_at) VALUES (?,?,?,?,?)",
            (user["id"], token, ip, user_agent, expires_at)
        )
        conn.commit()

        return {
            "success": True,
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "display_name": user["display_name"],
                "must_change_password": bool(user["must_change_password"]),
            },
            "expires_at": expires_at,
        }
    finally:
        conn.close()


def login_by_key(access_key: str, ip: str = None, user_agent: str = None) -> dict:
    """
    密钥登录（替代短信验证码的第二登录方式）。
    密钥校验通过即以超级主账号(owner)身份颁发会话；同样走登录限流，防止暴力尝试。
    """
    import hmac
    ensure_initialized()
    if not ip and has_request_context():
        ip = request.remote_addr
    ip = normalize_login_ip(ip)
    master = AUTH_CONFIG.get("master_access_key", "")

    conn = get_db()
    try:
        # Serialize the per-IP check, comparison, attempt record and session
        # insert so concurrent bad keys cannot all pass the final slot.
        conn.execute("BEGIN IMMEDIATE")
        check = check_login_attempts("__access_key__", ip, conn=conn)
        if not check["allowed"]:
            conn.rollback()
            return {"success": False, "error": f"尝试过多已锁定，请{check['locked_until']}后再试", "remaining": 0}

        if not master or not access_key or not hmac.compare_digest(
            str(access_key).strip().encode("utf-8"), str(master).strip().encode("utf-8")
        ):
            record_login_attempt("__access_key__", ip, False, conn=conn)
            conn.commit()
            remaining = check["remaining"] - 1
            return {"success": False, "error": f"密钥错误，剩余尝试次数：{max(0, remaining)}",
                    "remaining": max(0, remaining)}

        cur = conn.execute("SELECT * FROM v4_users WHERE role='owner' AND status='active' ORDER BY id LIMIT 1")
        user = cur.fetchone()
        if not user:
            conn.rollback()
            return {"success": False, "error": "主账号未初始化，请先用账号密码登录一次"}
        record_login_attempt("__access_key__", ip, True, conn=conn)
        token = generate_token(user["id"])
        expires_at = time.strftime("%Y-%m-%d %H:%M:%S",
                                   time.localtime(time.time() + AUTH_CONFIG["token_expire_hours"] * 3600))
        conn.execute(
            "INSERT INTO v4_sessions (user_id, token, ip, user_agent, expires_at) VALUES (?,?,?,?,?)",
            (user["id"], token, ip, user_agent, expires_at)
        )
        conn.commit()
        return {
            "success": True, "token": token, "login_type": "access_key",
            "user": {
                "id": user["id"], "username": user["username"], "role": user["role"],
                "display_name": user["display_name"], "must_change_password": bool(user["must_change_password"]),
            },
            "expires_at": expires_at,
        }
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def logout(token: str):
    """登出，销毁会话"""
    conn = get_db()
    try:
        conn.execute("DELETE FROM v4_sessions WHERE token=?", (token,))
        conn.commit()
    finally:
        conn.close()


def get_current_user(*, read_only: bool = False) -> dict:
    """从请求中获取当前登录用户"""
    if not read_only:
        ensure_initialized()
    token = None
    # 从Header获取
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    # 从Cookie获取
    if not token:
        token = request.cookies.get(AUTH_CONFIG["session_cookie_name"])

    if not token:
        return None

    if read_only:
        from lumenis.shared.database import get_repository
        conn = get_repository().connect(read_only=True, wal=False, timeout=0.25, busy_timeout_ms=250)
    else:
        conn = get_db()
    try:
        cur = conn.execute("""
            SELECT u.*, s.expires_at FROM v4_sessions s
            JOIN v4_users u ON u.id = s.user_id
            WHERE s.token=? AND u.status='active'
        """, (token,))
        row = cur.fetchone()
        if not row:
            return None
        # 检查过期
        if row["expires_at"] < time.strftime("%Y-%m-%d %H:%M:%S"):
            if not read_only:
                conn.execute("DELETE FROM v4_sessions WHERE token=?", (token,))
                conn.commit()
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
            "display_name": row["display_name"],
            "token": token,
        }
    finally:
        conn.close()


def require_auth(f):
    """登录校验装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "未登录或登录已过期"}), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def require_permission(permission: str):
    """权限校验装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "未登录"}), 401
            role_perms = ROLE_PERMISSIONS.get(user["role"], {})
            if not role_perms.get(permission, False):
                return jsonify({"error": "权限不足"}), 403
            g.current_user = user
            return f(*args, **kwargs)
        return decorated
    return decorator


def require_owner(f):
    """主账号专属装饰器"""
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


def require_security_verification(f):
    """
    安全问答校验装饰器
    请求体需包含 security_answers: {"手机号": "xxx", "生日": "xxx"}
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        data = request.get_json(silent=True) or {}
        answers = data.get("security_answers", {})
        if not verify_security_questions(answers):
            return jsonify({"error": "安全验证失败，请回答正确的安全问题"}), 403
        return f(*args, **kwargs)
    return decorated


def create_user(username: str, password: str, role: str = "user",
                display_name: str = None, email: str = None, created_by: int = None) -> dict:
    """创建用户（主账号操作）"""
    from .security import hash_password
    ensure_initialized()
    conn = get_db()
    try:
        # 检查用户名重复
        cur = conn.execute("SELECT COUNT(*) as cnt FROM v4_users WHERE username=?", (username,))
        if cur.fetchone()["cnt"] > 0:
            return {"success": False, "error": "用户名已存在"}
        # 管理员数量限制
        if role == "admin":
            cur = conn.execute("SELECT COUNT(*) as cnt FROM v4_users WHERE role='admin'")
            if cur.fetchone()["cnt"] >= 3:
                return {"success": False, "error": "管理员账号最多3个"}
        if role not in ROLE_PERMISSIONS:
            return {"success": False, "error": "无效的角色"}

        pwd_hash = hash_password(password)
        conn.execute(
            """INSERT INTO v4_users (username, password_hash, role, display_name, email, must_change_password)
               VALUES (?,?,?,?,?,1)""",
            (username, pwd_hash, role, display_name or username, email)
        )
        conn.commit()
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return {"success": True, "user_id": user_id, "must_change_password": True}
    finally:
        conn.close()


def list_users() -> list:
    """列出所有用户（主账号）"""
    conn = get_db()
    try:
        cur = conn.execute("""
            SELECT id, username, role, display_name, email, status,
                   last_login_at, created_at, failed_attempts, locked_until
            FROM v4_users ORDER BY CASE role WHEN 'owner' THEN 1 WHEN 'admin' THEN 2 ELSE 3 END, id
        """)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def update_user_status(user_id: int, status: str) -> bool:
    """启用/禁用用户"""
    conn = get_db()
    try:
        conn.execute("UPDATE v4_users SET status=? WHERE id=? AND role!='owner'", (status, user_id))
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def change_password(user_id: int, old_password: str, new_password: str) -> dict:
    """修改密码"""
    from .security import hash_password
    conn = get_db()
    try:
        cur = conn.execute("SELECT password_hash FROM v4_users WHERE id=?", (user_id,))
        user = cur.fetchone()
        if not user or not verify_password(old_password, user["password_hash"]):
            return {"success": False, "error": "原密码错误"}
        if len(new_password) < 6:
            return {"success": False, "error": "新密码至少6位"}
        conn.execute(
            "UPDATE v4_users SET password_hash=?, must_change_password=0 WHERE id=?",
            (hash_password(new_password), user_id)
        )
        conn.commit()
        return {"success": True}
    finally:
        conn.close()


def reset_user_password(user_id: int, new_password: str) -> dict:
    """主账号重置子账号密码"""
    from .security import hash_password
    conn = get_db()
    try:
        conn.execute(
            "UPDATE v4_users SET password_hash=?, must_change_password=1 WHERE id=? AND role!='owner'",
            (hash_password(new_password), user_id)
        )
        conn.commit()
        return {"success": True, "must_change_password": True}
    finally:
        conn.close()
