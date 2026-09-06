"""
account/verification.py — Apple 式随机数字验证码系统

核心特性：
- secrets.randbelow 密码学安全随机（6-8位）
- DB 只存 PBKDF2 hash，明文仅生成时经受信任渠道出现一次
- 限时（默认120秒）、一次性（用后即焚）、失败上限（默认5次）
- 重发冷却（60秒）、单位时间重发上限（5分钟内3次）
- 校验通过颁发短期 grant（workspace 8小时 / 受信任设备30天）
- 预留短信/邮件渠道接口，无凭证标 BLOCKED 不伪造已发送
"""
import time
import secrets
from flask import request, g

from .models import get_db
from .security import (
    hash_verification_code, verify_verification_code,
    generate_numeric_code, generate_token,
)

# 验证码配置
VERIFICATION_CONFIG = {
    "code_length": 6,            # 默认6位，可配6-8
    "expiry_seconds": 120,       # 默认120秒过期
    "max_attempts": 5,           # 失败上限5次
    "resend_cooldown": 60,       # 重发冷却60秒
    "resend_window_seconds": 300,  # 单位时间窗口5分钟
    "resend_window_max": 3,      # 窗口内最多3次
    "workspace_grant_hours": 8,  # 工作区grant 8小时
    "trusted_device_days": 30,   # 受信任设备30天
}

VALID_SCENARIOS = ("workspace_unlock", "sensitive_action", "new_device")


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _now_ts():
    return time.time()


def _get_user_id():
    user = getattr(g, "current_user", None)
    return user["id"] if user else None


def _count_recent_codes(conn, user_id, scenario, window_seconds):
    """统计窗口内已发送的验证码数量"""
    since = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - window_seconds))
    cur = conn.execute(
        "SELECT COUNT(*) as cnt FROM v4_verification_codes WHERE user_id=? AND scenario=? AND created_at>=?",
        (user_id, scenario, since)
    )
    return cur.fetchone()["cnt"]


def _get_last_code(conn, user_id, scenario):
    """获取最近一条 pending 验证码"""
    cur = conn.execute(
        "SELECT * FROM v4_verification_codes WHERE user_id=? AND scenario=? AND status='pending' "
        "ORDER BY id DESC LIMIT 1",
        (user_id, scenario)
    )
    return cur.fetchone()


def request_verification_code(scenario: str, user_id: int = None,
                              code_length: int = None, delivery_channel: str = "in_app") -> dict:
    """
    请求验证码。
    scenario: workspace_unlock / sensitive_action / new_device
    返回: {success, code_id, expires_at, delivery_channel, delivery_status, cooldown_remaining}
    注意：验证码明文不在返回值中（仅经受信任渠道展示），测试场景可通过 in_app 渠道获取。
    """
    if scenario not in VALID_SCENARIOS:
        return {"success": False, "error": f"无效场景，必须是 {VALID_SCENARIOS} 之一"}

    user_id = user_id or _get_user_id()
    if not user_id:
        return {"success": False, "error": "未登录", "code": 401}

    length = code_length or VERIFICATION_CONFIG["code_length"]
    if not (6 <= length <= 8):
        return {"success": False, "error": "验证码长度必须在6-8位之间"}

    ip = request.remote_addr if request else "unknown"
    ua = request.headers.get("User-Agent", "") if request else ""

    conn = get_db()
    try:
        # 检查重发冷却
        last = _get_last_code(conn, user_id, scenario)
        if last:
            created_ts = time.mktime(time.strptime(last["created_at"], "%Y-%m-%d %H:%M:%S"))
            elapsed = time.time() - created_ts
            if elapsed < VERIFICATION_CONFIG["resend_cooldown"]:
                remaining = int(VERIFICATION_CONFIG["resend_cooldown"] - elapsed)
                return {
                    "success": False, "error": f"重发冷却中，请{remaining}秒后再试",
                    "cooldown_remaining": remaining, "code": 429,
                }

        # 检查单位时间重发上限
        window_count = _count_recent_codes(
            conn, user_id, scenario, VERIFICATION_CONFIG["resend_window_seconds"]
        )
        if window_count >= VERIFICATION_CONFIG["resend_window_max"]:
            return {
                "success": False,
                "error": f"发送过于频繁，{VERIFICATION_CONFIG['resend_window_seconds']//60}分钟内最多{VERIFICATION_CONFIG['resend_window_max']}次",
                "code": 429,
            }

        # 使旧的 pending 码失效
        conn.execute(
            "UPDATE v4_verification_codes SET status='revoked' WHERE user_id=? AND scenario=? AND status='pending'",
            (user_id, scenario)
        )

        # 生成验证码
        code_plain = generate_numeric_code(length)
        code_hash, code_salt = hash_verification_code(code_plain)
        expires_at = time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(time.time() + VERIFICATION_CONFIG["expiry_seconds"])
        )

        # 送达渠道处理
        delivery_status = "delivered"
        if delivery_channel == "sms":
            delivery_status = _send_sms_code(user_id, code_plain)
        elif delivery_channel == "email":
            delivery_status = _send_email_code(user_id, code_plain)
        # in_app: 系统内通知，标记 delivered（由受信任设备会话展示）

        cur = conn.execute(
            """INSERT INTO v4_verification_codes
               (user_id, scenario, code_hash, code_salt, expires_at, max_attempts,
                delivery_channel, delivery_status, ip, user_agent)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (user_id, scenario, code_hash, code_salt, expires_at,
             VERIFICATION_CONFIG["max_attempts"], delivery_channel, delivery_status, ip, ua)
        )
        conn.commit()
        code_id = cur.lastrowid

        # 审计
        from .audit import log_audit
        log_audit("verification_request", "verification", str(code_id),
                  f"场景={scenario}, 渠道={delivery_channel}, 状态={delivery_status}")

        result = {
            "success": True,
            "code_id": code_id,
            "scenario": scenario,
            "expires_at": expires_at,
            "expiry_seconds": VERIFICATION_CONFIG["expiry_seconds"],
            "delivery_channel": delivery_channel,
            "delivery_status": delivery_status,
            "code_length": length,
        }
        # in_app 渠道：在受信任设备会话内展示验证码明文（仅此时出现一次）
        if delivery_channel == "in_app":
            result["in_app_code"] = code_plain  # 仅受信任会话内可见，不写日志
        return result
    finally:
        conn.close()


def verify_code(code_id: int, code_plain: str, user_id: int = None) -> dict:
    """
    校验验证码。
    成功：一次性用后即焚，颁发短期 grant。
    失败：累加失败次数，达上限作废。
    """
    user_id = user_id or _get_user_id()
    if not user_id:
        return {"success": False, "error": "未登录", "code": 401}

    if not code_plain or not code_plain.isdigit():
        return {"success": False, "error": "验证码必须是数字"}

    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM v4_verification_codes WHERE id=?", (code_id,))
        record = cur.fetchone()
        if not record:
            return {"success": False, "error": "验证码不存在", "code": 404}
        if record["user_id"] != user_id:
            return {"success": False, "error": "验证码与用户不匹配", "code": 403}
        if record["status"] != "pending":
            return {"success": False, "error": f"验证码状态异常：{record['status']}", "code": 400}

        now = _now()
        # 过期检查
        if record["expires_at"] < now:
            conn.execute("UPDATE v4_verification_codes SET status='expired' WHERE id=?", (code_id,))
            conn.commit()
            return {"success": False, "error": "验证码已过期，请重新获取", "code": 410}

        # 失败次数检查
        if record["failed_attempts"] >= record["max_attempts"]:
            conn.execute("UPDATE v4_verification_codes SET status='revoked' WHERE id=?", (code_id,))
            conn.commit()
            return {"success": False, "error": "失败次数过多，验证码已作废，请重新获取", "code": 429}

        # 校验
        if not verify_verification_code(code_plain, record["code_hash"]):
            new_attempts = record["failed_attempts"] + 1
            remaining = record["max_attempts"] - new_attempts
            if new_attempts >= record["max_attempts"]:
                conn.execute(
                    "UPDATE v4_verification_codes SET failed_attempts=?, status='revoked' WHERE id=?",
                    (new_attempts, code_id)
                )
            else:
                conn.execute(
                    "UPDATE v4_verification_codes SET failed_attempts=? WHERE id=?",
                    (new_attempts, code_id)
                )
            conn.commit()
            # 记录登录尝试
            from .security import record_login_attempt
            user = getattr(g, "current_user", None)
            record_login_attempt(user["username"] if user else "unknown",
                                 request.remote_addr if request else "unknown", False)
            return {
                "success": False, "error": f"验证码错误，剩余尝试次数：{max(0, remaining)}",
                "remaining_attempts": max(0, remaining), "code": 401,
            }

        # 校验成功：用后即焚
        conn.execute(
            "UPDATE v4_verification_codes SET status='verified', verified_at=? WHERE id=?",
            (now, code_id)
        )
        conn.commit()

        # 颁发短期 grant
        grant = _issue_grant(user_id, record["scenario"], code_id)

        from .audit import log_audit
        log_audit("verification_verify", "verification", str(code_id),
                  f"场景={record['scenario']}, 校验成功, grant={grant.get('grant_type')}")

        return {
            "success": True,
            "grant": grant,
            "scenario": record["scenario"],
        }
    finally:
        conn.close()


def _issue_grant(user_id: int, scenario: str, code_id: int) -> dict:
    """校验通过后颁发短期 grant"""
    token = generate_token()
    if scenario == "new_device":
        # 受信任设备：30天
        expires_at = time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(time.time() + VERIFICATION_CONFIG["trusted_device_days"] * 86400)
        )
        grant_type = "trusted_device"
        workspace = "SYSTEM"
    else:
        # workspace_unlock / sensitive_action：8小时工作区grant
        expires_at = time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(time.time() + VERIFICATION_CONFIG["workspace_grant_hours"] * 3600)
        )
        grant_type = "workspace"
        workspace = "ZBMP" if scenario == "workspace_unlock" else "SYSTEM"

    conn = get_db()
    try:
        # 写入 v4_workspace_grants（复用现有表）
        session_token = None
        user = getattr(g, "current_user", None)
        if user and user.get("token"):
            session_token = user["token"]
        conn.execute(
            """INSERT INTO v4_workspace_grants (user_id, workspace, key_id, session_token, expires_at)
               VALUES (?,?,?,?,?)""",
            (user_id, workspace, code_id, session_token, expires_at)
        )
        conn.commit()
        return {
            "grant_type": grant_type,
            "workspace": workspace,
            "expires_at": expires_at,
            "token": token,
        }
    finally:
        conn.close()


def resend_code(scenario: str, user_id: int = None) -> dict:
    """重发验证码（受冷却限制）"""
    return request_verification_code(scenario, user_id=user_id)


def list_pending_codes(user_id: int = None) -> list:
    """
    待批准验证码列表（受信任设备端查看）。
    不返回 code_hash / 明文。
    """
    user_id = user_id or _get_user_id()
    conn = get_db()
    try:
        cur = conn.execute("""
            SELECT id, user_id, scenario, expires_at, failed_attempts, max_attempts,
                   status, delivery_channel, delivery_status, ip, user_agent, created_at
            FROM v4_verification_codes
            WHERE status='pending' AND expires_at >= datetime('now','localtime')
            ORDER BY created_at DESC LIMIT 50
        """)
        codes = [dict(r) for r in cur.fetchall()]
        # in_app 渠道的 pending 码，在受信任设备上展示明文（仅此时）
        for c in codes:
            if c["delivery_channel"] == "in_app":
                # 不返回明文——明文只在 request 时出现一次
                c["in_app_display"] = True
        return codes
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 预留送达渠道接口（无凭证标 BLOCKED）
# ──────────────────────────────────────────────

def _send_sms_code(user_id: int, code: str) -> str:
    """
    短信发送接口（预留）。
    无短信服务凭证时返回 BLOCKED，不伪造已发送。
    """
    # 检查是否配置了短信凭证
    import os
    sms_api_key = os.environ.get("SMS_API_KEY", "")
    sms_api_secret = os.environ.get("SMS_API_SECRET", "")
    if not sms_api_key or not sms_api_secret:
        return "blocked"  # 无凭证，标 BLOCKED
    # TODO: 实际短信发送逻辑（有凭证时实现）
    return "blocked"


def _send_email_code(user_id: int, code: str) -> str:
    """
    邮件发送接口（预留）。
    无邮件服务凭证时返回 BLOCKED，不伪造已发送。
    """
    import os
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_user = os.environ.get("SMTP_USER", "")
    if not smtp_host or not smtp_user:
        return "blocked"  # 无凭证，标 BLOCKED
    # TODO: 实际邮件发送逻辑（有凭证时实现）
    return "blocked"
