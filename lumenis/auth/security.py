"""
安全工具：密码哈希、Token生成、安全问答验证、登录限流
不依赖第三方库，全部用标准库实现。
"""
import hashlib
import hmac
import secrets
import time
import sqlite3
from datetime import datetime, timedelta
from ..config import AUTH_CONFIG
from .models import get_db


_ACCESS_KEY_ATTEMPT_USERNAME = "__access_key__"
_ATTEMPT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _local_timestamp() -> str:
    """Use one local-time representation for attempt and cooldown boundaries."""
    return time.strftime(_ATTEMPT_TIME_FORMAT, time.localtime())


def normalize_login_ip(ip: str = None) -> str:
    """Normalize missing client addresses into one non-bypassable bucket."""
    return str(ip or "").strip() or "unknown"


def _parse_attempt_timestamp(value: str) -> datetime:
    return datetime.strptime(value, _ATTEMPT_TIME_FORMAT)


def _is_ip_bucket(username) -> bool:
    """Synthetic per-IP buckets (access key, workspace key) are named __name__."""
    return isinstance(username, str) and len(username) > 4 and username.startswith("__") and username.endswith("__")


def _check_access_key_attempts(conn, ip: str, bucket: str = None) -> dict:
    """Check the access-key/IP bucket using the existing attempt audit rows."""
    max_attempts = int(AUTH_CONFIG["max_login_attempts"])
    if max_attempts <= 0:
        return {"allowed": False, "remaining": 0, "locked_until": None}

    cooldown = timedelta(minutes=int(AUTH_CONFIG["lockout_minutes"]))
    bucket = bucket or _ACCESS_KEY_ATTEMPT_USERNAME
    last_success = conn.execute(
        """
        SELECT id
        FROM v4_login_attempts
        WHERE username=? AND success=1
          AND (ip=? OR (?='unknown' AND (ip IS NULL OR TRIM(ip)='')))
        ORDER BY id DESC LIMIT 1
        """,
        (bucket, ip, ip),
    ).fetchone()
    after_success_id = last_success["id"] if last_success else 0
    failures = conn.execute(
        """
        SELECT id, created_at
        FROM v4_login_attempts
        WHERE username=? AND success=0 AND id>?
          AND (ip=? OR (?='unknown' AND (ip IS NULL OR TRIM(ip)='')))
        ORDER BY id DESC LIMIT ?
        """,
        (bucket, after_success_id, ip, ip, max_attempts),
    ).fetchall()

    if not failures:
        return {"allowed": True, "remaining": max_attempts, "locked_until": None}

    now = _parse_attempt_timestamp(_local_timestamp())
    newest_failure = _parse_attempt_timestamp(failures[0]["created_at"])
    if now - newest_failure >= cooldown:
        return {"allowed": True, "remaining": max_attempts, "locked_until": None}

    # A cooldown-sized gap begins a new failure window. Rows before that gap
    # remain immutable audit history and do not affect the current bucket.
    current_window = [failures[0]]
    newer_time = newest_failure
    for failure in failures[1:]:
        failure_time = _parse_attempt_timestamp(failure["created_at"])
        if newer_time - failure_time >= cooldown:
            break
        current_window.append(failure)
        newer_time = failure_time

    if len(current_window) >= max_attempts:
        locked_until = newest_failure + cooldown
        if now < locked_until:
            return {
                "allowed": False,
                "remaining": 0,
                "locked_until": locked_until.strftime(_ATTEMPT_TIME_FORMAT),
            }
        return {"allowed": True, "remaining": max_attempts, "locked_until": None}

    remaining = max_attempts - len(current_window)
    return {"allowed": True, "remaining": remaining, "locked_until": None}


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


def check_login_attempts(username: str, ip: str, conn=None) -> dict:
    """
    检查登录尝试，返回是否允许登录
    返回: {"allowed": bool, "remaining": int, "locked_until": str}
    """
    owns_connection = conn is None
    if owns_connection:
        conn = get_db()
    try:
        if _is_ip_bucket(username):
            return _check_access_key_attempts(conn, normalize_login_ip(ip), username)

        # 检查账号锁定
        cur = conn.execute(
            "SELECT failed_attempts, locked_until FROM v4_users WHERE username=?",
            (username,)
        )
        user = cur.fetchone()
        if user and user["locked_until"]:
            lock_time = user["locked_until"]
            now = _local_timestamp()
            if lock_time > now:
                return {"allowed": False, "remaining": 0, "locked_until": lock_time}
            else:
                # 锁定已过期，重置
                conn.execute(
                    "UPDATE v4_users SET failed_attempts=0, locked_until=NULL WHERE username=?",
                    (username,)
                )
                if owns_connection:
                    conn.commit()
                # Refresh the row: the fetched sqlite3.Row still contains the
                # pre-reset failed_attempts value.
                cur = conn.execute(
                    "SELECT failed_attempts, locked_until FROM v4_users WHERE username=?",
                    (username,)
                )
                user = cur.fetchone()

        if user:
            remaining = AUTH_CONFIG["max_login_attempts"] - user["failed_attempts"]
            return {"allowed": remaining > 0, "remaining": max(0, remaining), "locked_until": None}
        return {"allowed": True, "remaining": AUTH_CONFIG["max_login_attempts"], "locked_until": None}
    finally:
        if owns_connection:
            conn.close()


def record_login_attempt(username: str, ip: str, success: bool, conn=None):
    """记录登录尝试，失败时累加，成功时重置"""
    owns_connection = conn is None
    if owns_connection:
        conn = get_db()
    try:
        conn.execute(
            "INSERT INTO v4_login_attempts (username, ip, success, created_at) VALUES (?,?,?,?)",
            (username, normalize_login_ip(ip), 1 if success else 0, _local_timestamp())
        )
        # Access-key attempts have their own username/IP bucket in the shared
        # attempt log; they must not mutate the owner's password lockout state.
        if _is_ip_bucket(username):
            pass
        elif success:
            conn.execute(
                "UPDATE v4_users SET failed_attempts=0, locked_until=NULL, last_login_at=datetime('now','localtime'), last_login_ip=? WHERE username=?",
                (normalize_login_ip(ip), username)
            )
        else:
            cur = conn.execute("SELECT failed_attempts FROM v4_users WHERE username=?", (username,))
            row = cur.fetchone()
            if row:
                new_count = row["failed_attempts"] + 1
                if new_count >= AUTH_CONFIG["max_login_attempts"]:
                    lock_until = (
                        datetime.strptime(_local_timestamp(), _ATTEMPT_TIME_FORMAT)
                        + timedelta(minutes=int(AUTH_CONFIG["lockout_minutes"]))
                    ).strftime(_ATTEMPT_TIME_FORMAT)
                    conn.execute(
                        "UPDATE v4_users SET failed_attempts=?, locked_until=? WHERE username=?",
                        (new_count, lock_until, username)
                    )
                else:
                    conn.execute(
                        "UPDATE v4_users SET failed_attempts=? WHERE username=?",
                        (new_count, username)
                    )
        if owns_connection:
            conn.commit()
    finally:
        if owns_connection:
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
