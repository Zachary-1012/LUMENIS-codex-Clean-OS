"""
account/security.py — 安全工具

密码哈希(PBKDF2)、验证码哈希、登录限流、安全问答。
从 v4_upgrade/auth/security.py 主线化提升，保持兼容。
"""
import hashlib
import hmac
import secrets
import time
import os

# 认证配置（与 v4_upgrade/config.py 保持一致）
AUTH_CONFIG = {
    "token_expire_hours": 24 * 7,
    "max_login_attempts": 5,
    "lockout_minutes": 15,
    "bcrypt_rounds": 12,
    "session_cookie_name": "cth_poms_v4_session",
    "master_access_key": os.environ.get("V4_ACCESS_KEY", "张志宏"),
}

# 角色权限（与 v4_upgrade/config.py 保持一致）
ROLE_PERMISSIONS = {
    "owner": {
        "browse_all": True, "update_data": True, "add_topic": True,
        "add_event": True, "add_note": True, "receive_reports": True,
        "trigger_collect": True, "export_reports": True,
        "view_audit": True, "view_task_status": True,
        "manage_accounts": True, "manage_security": True,
        "system_config": True, "manage_modules": True,
        "delete_raw_data": True, "lock_config": True,
        "developer_access": True,
    },
    "admin": {
        "browse_all": True, "update_data": True, "add_topic": True,
        "add_event": True, "add_note": True, "receive_reports": True,
        "trigger_collect": True, "export_reports": True,
        "view_audit": True, "view_task_status": True,
        "manage_accounts": False, "manage_security": False,
        "system_config": False, "manage_modules": False,
        "delete_raw_data": False, "lock_config": False,
        "developer_access": False,
    },
    "user": {
        "browse_all": False, "update_data": False, "add_topic": False,
        "add_event": False, "add_note": False, "receive_reports": True,
        "trigger_collect": False, "export_reports": True,
        "view_audit": False, "view_task_status": False,
        "manage_accounts": False, "manage_security": False,
        "system_config": False, "manage_modules": False,
        "delete_raw_data": False, "lock_config": False,
        "developer_access": False,
    },
}

# 名额硬约束
QUOTA_LIMITS = {
    "owner": 1,
    "admin": 3,
    "member": 5,   # v4_users 中 role='user' 即 member
}


def hash_password(password: str, salt: str = None) -> str:
    """PBKDF2 密码哈希，返回 pbkdf2$<iterations>$<salt>$<hash_hex>"""
    if salt is None:
        salt = secrets.token_hex(16)
    iterations = AUTH_CONFIG["bcrypt_rounds"] * 10000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2${iterations}${salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """验证密码"""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2":
            return False
        _, iterations, salt, hash_hex = parts
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def generate_token(user_id: int = None) -> str:
    """生成会话 Token"""
    return secrets.token_urlsafe(32)


def hash_security_answer(answer: str) -> str:
    return hash_password(answer.strip())


def verify_security_answer(answer: str, stored_hash: str) -> bool:
    return verify_password(answer.strip(), stored_hash)


def hash_verification_code(code: str, salt: str = None):
    """验证码哈希，返回 (hash, salt)"""
    if salt is None:
        salt = secrets.token_hex(16)
    iterations = 50000  # 验证码较短，用较高迭代
    dk = hashlib.pbkdf2_hmac("sha256", code.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2${iterations}${salt}${dk.hex()}", salt


def verify_verification_code(code: str, stored_hash: str) -> bool:
    """验证验证码"""
    return verify_password(code, stored_hash)


def generate_numeric_code(length: int = 6) -> str:
    """
    生成 N 位随机数字验证码。
    使用 secrets.randbelow 密码学安全随机，禁止可预测。
    首位可以为0（验证码不要求首位非零）。
    """
    if not (6 <= length <= 8):
        length = 6
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def check_login_attempts(username: str, ip: str) -> dict:
    """检查登录尝试限流"""
    from .models import get_db
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT failed_attempts, locked_until FROM v4_users WHERE username=?",
            (username,)
        )
        user = cur.fetchone()
        if user and user["locked_until"]:
            lock_time = user["locked_until"]
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            if lock_time > now:
                return {"allowed": False, "remaining": 0, "locked_until": lock_time}
            else:
                conn.execute(
                    "UPDATE v4_users SET failed_attempts=0, locked_until=NULL WHERE username=?",
                    (username,)
                )
                conn.commit()
        if user:
            remaining = AUTH_CONFIG["max_login_attempts"] - user["failed_attempts"]
            return {"allowed": remaining > 0, "remaining": max(0, remaining), "locked_until": None}
        return {"allowed": True, "remaining": AUTH_CONFIG["max_login_attempts"], "locked_until": None}
    finally:
        conn.close()


def record_login_attempt(username: str, ip: str, success: bool):
    """记录登录尝试"""
    from .models import get_db
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO v4_login_attempts (username, ip, success) VALUES (?,?,?)",
            (username, ip, 1 if success else 0)
        )
        if success:
            conn.execute(
                "UPDATE v4_users SET failed_attempts=0, locked_until=NULL, "
                "last_login_at=datetime('now','localtime'), last_login_ip=? WHERE username=?",
                (ip, username)
            )
        else:
            cur = conn.execute("SELECT failed_attempts FROM v4_users WHERE username=?", (username,))
            row = cur.fetchone()
            if row:
                new_count = row["failed_attempts"] + 1
                if new_count >= AUTH_CONFIG["max_login_attempts"]:
                    lock_until = time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(time.time() + AUTH_CONFIG["lockout_minutes"] * 60)
                    )
                    conn.execute(
                        "UPDATE v4_users SET failed_attempts=?, locked_until=? WHERE username=?",
                        (new_count, lock_until, username)
                    )
                else:
                    conn.execute(
                        "UPDATE v4_users SET failed_attempts=? WHERE username=?",
                        (new_count, username)
                    )
        conn.commit()
    finally:
        conn.close()


def verify_security_questions(answers: dict) -> bool:
    """验证安全问答"""
    from .models import get_db
    conn = get_db()
    try:
        cur = conn.execute("SELECT question, answer_hash FROM v4_security_questions WHERE is_active=1")
        questions = cur.fetchall()
        if not questions:
            return False
        for q in questions:
            user_answer = answers.get(q["question"], "")
            if not verify_security_answer(user_answer, q["answer_hash"]):
                return False
        return True
    finally:
        conn.close()
