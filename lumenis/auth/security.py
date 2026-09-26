"""
安全工具：密码哈希、Token生成、安全问答验证、登录限流
不依赖第三方库，全部用标准库实现。
"""
import hashlib
import hmac
import secrets
import time
import sqlite3
from ..config import AUTH_CONFIG
from .models import get_db


def hash_password(password: str, salt: str = None) -> str:
    """
    PBKDF2 密码哈希
    返回格式: pbkdf2$<iterations>$<salt_hex>$<hash_hex>
    """
    if salt is None:
        salt = secrets.token_hex(16)
    iterations = AUTH_CONFIG["bcrypt_rounds"] * 10000  # 等效强度
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


def generate_token(user_id: int) -> str:
    """生成会话Token"""
    return secrets.token_urlsafe(32)


def hash_security_answer(answer: str) -> str:
    """安全问答答案哈希（复用密码哈希）"""
    return hash_password(answer.strip())


def verify_security_answer(answer: str, stored_hash: str) -> bool:
    """验证安全问答答案"""
    return verify_password(answer.strip(), stored_hash)


def check_login_attempts(username: str, ip: str) -> dict:
    """
    检查登录尝试，返回是否允许登录
    返回: {"allowed": bool, "remaining": int, "locked_until": str}
    """
    conn = get_db()
    try:
        # 检查账号锁定
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
                # 锁定已过期，重置
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
    """记录登录尝试，失败时累加，成功时重置"""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO v4_login_attempts (username, ip, success) VALUES (?,?,?)",
            (username, ip, 1 if success else 0)
        )
        if success:
            conn.execute(
                "UPDATE v4_users SET failed_attempts=0, locked_until=NULL, last_login_at=datetime('now','localtime'), last_login_ip=? WHERE username=?",
                (ip, username)
            )
        else:
            cur = conn.execute("SELECT failed_attempts FROM v4_users WHERE username=?", (username,))
            row = cur.fetchone()
            if row:
                new_count = row["failed_attempts"] + 1
                if new_count >= AUTH_CONFIG["max_login_attempts"]:
                    lock_until = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + AUTH_CONFIG["lockout_minutes"] * 60))
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
    """
    验证安全问答，全部正确才通过
    answers: operator-supplied values keyed by configured question
    """
    conn = get_db()
    try:
        cur = conn.execute("SELECT question, answer_hash FROM v4_security_questions WHERE is_active=1")
        questions = cur.fetchall()
        if not questions:
            return False  # 没有配置安全问答，不允许操作
        for q in questions:
            user_answer = answers.get(q["question"], "")
            if not verify_security_answer(user_answer, q["answer_hash"]):
                return False
        return True
    finally:
        conn.close()
