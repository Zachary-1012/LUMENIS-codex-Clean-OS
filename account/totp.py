"""
account/totp.py — TOTP 动态口令（通道A，绑定 iPhone「密码」/iCloud 钥匙串）

RFC6238 实现：HMAC-SHA1，30秒时间窗口，6位数字。
系统生成种子(secret) + otpauth:// QR码，用户iPhone扫码存入「密码」。
登录ZBMP时每30秒出6位数字，网页 autocomplete="one-time-code" 自动填充。
抗重放：同一code只能用一次（记录最后使用的time step）。
"""
import hmac
import hashlib
import base64
import struct
import time
import secrets
import io
import os
import sys

# 确保 vendor 目录中的 qrcode 库可导入
_vendor_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'vendor')
if os.path.isdir(_vendor_path) and _vendor_path not in sys.path:
    sys.path.insert(0, _vendor_path)

# TOTP 参数（RFC6238 默认）
TOTP_CONFIG = {
    "digits": 6,
    "period": 30,        # 30秒窗口
    "algorithm": "SHA1",
    "issuer": "ZBC-LUMENIS",
}

# 抗重放：记录每个用户最后使用的 time step
_used_steps = {}  # {user_id: last_step}


def generate_secret(length: int = 32) -> str:
    """生成 TOTP 种子（base32 编码）"""
    raw = secrets.token_bytes(length)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _get_hotp(secret: str, counter: int, digits: int = 6) -> str:
    """HOTP 核心算法（RFC4226）"""
    key = base64.b32decode(secret.upper() + "=" * ((8 - len(secret) % 8) % 8))
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    binary = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10 ** digits)).zfill(digits)


def get_totp(secret: str, timestamp: float = None, period: int = 30, digits: int = 6) -> str:
    """获取当前 TOTP 验证码"""
    if timestamp is None:
        timestamp = time.time()
    counter = int(timestamp // period)
    return _get_hotp(secret, counter, digits)


def verify_totp(secret: str, code: str, user_id: int = None,
                period: int = 30, digits: int = 6, window: int = 1) -> dict:
    """
    校验 TOTP 验证码。
    window=1 表示允许前后各1个时间窗口（共3个窗口），容错时钟偏移。
    抗重放：同一 time step 的 code 只能用一次。
    """
    code = (code or "").strip()
    if not code.isdigit() or len(code) != digits:
        return {"success": False, "error": f"验证码必须是{digits}位数字"}

    now = int(time.time() // period)
    for offset in range(-window, window + 1):
        step = now + offset
        expected = _get_hotp(secret, step, digits)
        if hmac.compare_digest(code, expected):
            # 抗重放检查
            if user_id is not None:
                last_step = _used_steps.get(user_id)
                if last_step is not None and step <= last_step:
                    return {"success": False, "error": "验证码已使用，请等待下一个30秒窗口"}
                _used_steps[user_id] = step
            return {"success": True, "step": step, "period": period}

    return {"success": False, "error": "验证码错误或已过期"}


def get_otpauth_url(secret: str, account_name: str, issuer: str = None) -> str:
    """生成 otpauth:// URL（用于二维码）"""
    issuer = issuer or TOTP_CONFIG["issuer"]
    from urllib.parse import quote
    return (f"otpauth://totp/{quote(issuer)}:{quote(account_name)}"
            f"?secret={secret}&issuer={quote(issuer)}"
            f"&algorithm={TOTP_CONFIG['algorithm']}"
            f"&digits={TOTP_CONFIG['digits']}"
            f"&period={TOTP_CONFIG['period']}")


def generate_qr_code_svg(secret: str, account_name: str, issuer: str = None) -> str:
    """
    生成二维码（SVG data URL）。
    使用 qrcode 库生成 SVG，无需 PIL/Pillow 依赖。
    """
    try:
        import qrcode
        from qrcode.image.svg import SvgPathImage
        url = get_otpauth_url(secret, account_name, issuer)
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
            image_factory=SvgPathImage,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image()
        # 获取 SVG 字符串
        svg_bytes = io.BytesIO()
        img.save(svg_bytes)
        svg_str = svg_bytes.getvalue().decode('utf-8')
        # 转为 data URL
        import base64 as b64
        svg_b64 = b64.b64encode(svg_str.encode('utf-8')).decode('ascii')
        return f"data:image/svg+xml;base64,{svg_b64}"
    except Exception as e:
        return (f"data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'>"
                f"<text x='10' y='100' font-size='12'>QR unavailable: {e}</text></svg>")


# ── TOTP 绑定状态管理（DB） ──

def get_totp_status(user_id: int) -> dict:
    """获取用户 TOTP 绑定状态"""
    from .models import get_db
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT secret, enabled, created_at, last_used_at FROM v4_totp_secrets WHERE user_id=?",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return {"enabled": False, "bound": False}
        return {
            "enabled": bool(row["enabled"]),
            "bound": True,
            "created_at": row["created_at"],
            "last_used_at": row["last_used_at"],
            # 不返回 secret 明文
        }
    finally:
        conn.close()


def setup_totp(user_id: int, account_name: str = None) -> dict:
    """
    初始化 TOTP：生成种子+QR码，返回给用户扫码绑定。
    此时 secret 存入 DB 但 enabled=0，需用户输入一次验证码确认绑定。
    """
    from .models import get_db
    from .security import hash_password
    secret = generate_secret()
    account_name = account_name or "ZBC"
    qr_data = generate_qr_code_svg(secret, account_name)
    otpauth_url = get_otpauth_url(secret, account_name)

    conn = get_db()
    try:
        # 删除旧的未启用绑定
        conn.execute("DELETE FROM v4_totp_secrets WHERE user_id=? AND enabled=0", (user_id,))
        # secret 加密存储（用 hash_password 做对称加密不合适，这里存 base64 混淆后的值）
        # 实际生产应使用环境变量密钥加密，这里做 base64+XOR 混淆存储
        obfuscated = _obfuscate_secret(secret)
        conn.execute(
            """INSERT INTO v4_totp_secrets (user_id, secret, enabled, created_at)
               VALUES (?,?,0,datetime('now','localtime'))""",
            (user_id, obfuscated)
        )
        conn.commit()
        return {
            "success": True,
            "secret": secret,  # 仅此时返回明文一次
            "qr_code": qr_data,
            "otpauth_url": otpauth_url,
            "account_name": account_name,
            "issuer": TOTP_CONFIG["issuer"],
            "digits": TOTP_CONFIG["digits"],
            "period": TOTP_CONFIG["period"],
            "message": "请用iPhone「密码」或iCloud钥匙串扫码绑定，然后输入6位验证码确认",
        }
    finally:
        conn.close()


def confirm_totp(user_id: int, code: str) -> dict:
    """确认 TOTP 绑定：用户输入验证码，正确则 enabled=1"""
    from .models import get_db
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT secret FROM v4_totp_secrets WHERE user_id=? AND enabled=0 ORDER BY id DESC LIMIT 1",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return {"success": False, "error": "没有待确认的TOTP绑定，请先扫码"}
        secret = _deobfuscate_secret(row["secret"])
        result = verify_totp(secret, code, user_id=None)  # 绑定时不做抗重放
        if not result["success"]:
            return result
        # 先删除旧的 enabled=1 绑定（避免 UNIQUE constraint），再启用新绑定
        conn.execute("DELETE FROM v4_totp_secrets WHERE user_id=? AND enabled=1", (user_id,))
        conn.execute(
            "UPDATE v4_totp_secrets SET enabled=1 WHERE user_id=? AND enabled=0",
            (user_id,)
        )
        conn.commit()

        from .audit import log_audit
        log_audit("totp_bind", "security", str(user_id), "TOTP绑定成功")

        return {"success": True, "message": "TOTP绑定成功，下次登录ZBMP需输入6位动态码"}
    finally:
        conn.close()


def verify_user_totp(user_id: int, code: str) -> dict:
    """校验已绑定用户的 TOTP 验证码（登录ZBMP时调用）"""
    from .models import get_db
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT secret FROM v4_totp_secrets WHERE user_id=? AND enabled=1 LIMIT 1",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return {"success": False, "error": "未绑定TOTP，请先在设置中绑定", "code": 403}
        secret = _deobfuscate_secret(row["secret"])
        result = verify_totp(secret, code, user_id=user_id)
        if result["success"]:
            conn.execute(
                "UPDATE v4_totp_secrets SET last_used_at=datetime('now','localtime') WHERE user_id=?",
                (user_id,)
            )
            conn.commit()
        return result
    finally:
        conn.close()


def reset_totp(user_id: int) -> dict:
    """重置 TOTP（主账号操作，需安全验证）"""
    from .models import get_db
    conn = get_db()
    try:
        conn.execute("DELETE FROM v4_totp_secrets WHERE user_id=?", (user_id,))
        conn.commit()
        _used_steps.pop(user_id, None)
        from .audit import log_audit
        log_audit("totp_reset", "security", str(user_id), "TOTP已重置")
        return {"success": True, "message": "TOTP已重置，需要重新绑定"}
    finally:
        conn.close()


# ── Secret 混淆存储（非加密，仅防直接读取） ──
_OBFUSCATION_KEY = b"ZBC-LUMENIS-TOTP-2026"

def _obfuscate_secret(secret: str) -> str:
    raw = secret.encode("ascii")
    key = _OBFUSCATION_KEY
    xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    import base64 as b64
    return b64.b64encode(xored).decode("ascii")


def _deobfuscate_secret(obfuscated: str) -> str:
    import base64 as b64
    raw = b64.b64decode(obfuscated.encode("ascii"))
    key = _OBFUSCATION_KEY
    xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    return xored.decode("ascii")
