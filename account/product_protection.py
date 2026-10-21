"""
account/product_protection.py — 产品级访问保护配置

按 product(ZBMP/CTH/SYSTEM) 分别存储和读取保护配置：
- ZBMP = 账号+密码登录（默认开；TOTP 已按产品决定删除）
- CTH = 账号+密码登录（默认开）
- SYSTEM = 敏感操作二次确认（默认开）

两套独立机制，分区、分表单、分API、分逻辑，绝不混。
"""
from .models import get_db

# 默认保护配置
DEFAULT_PROTECTION = {
    "ZBMP": {
        "enabled": True,
        "method": "password",        # 账号+密码（TOTP 已删除）
        "description": "进入ZBMP需输入账号密码",
    },
    "CTH": {
        "enabled": True,
        "method": "password",        # 账号+密码
        "description": "进入CTH需输入账号密码",
    },
    "SYSTEM": {
        "enabled": True,
        "method": "reauth",          # 敏感操作二次确认
        "description": "成员管理/密钥/审计导出等敏感操作需二次验证",
    },
}

VALID_PRODUCTS = ("ZBMP", "CTH", "SYSTEM")
VALID_METHODS = ("password", "reauth", "none")


def get_protection_config(product_id: str = None) -> dict:
    """
    获取产品保护配置。
    不传 product_id 返回全部三个产品的配置。
    """
    conn = get_db()
    try:
        if product_id:
            product_id = product_id.upper()
            cur = conn.execute(
                "SELECT product_id, enabled, method, config_json, updated_at "
                "FROM v4_product_protection WHERE product_id=?",
                (product_id,)
            )
            row = cur.fetchone()
            if row:
                return _row_to_config(row)
            return DEFAULT_PROTECTION.get(product_id, {"enabled": False, "method": "none"})

        # 返回全部
        result = {}
        cur = conn.execute(
            "SELECT product_id, enabled, method, config_json, updated_at FROM v4_product_protection"
        )
        db_configs = {row["product_id"]: _row_to_config(row) for row in cur.fetchall()}
        for p in VALID_PRODUCTS:
            result[p] = db_configs.get(p, DEFAULT_PROTECTION.get(p, {"enabled": False, "method": "none"}))
        return result
    finally:
        conn.close()


def set_protection_config(product_id: str, enabled: bool = None,
                          method: str = None, config_json: str = None) -> dict:
    """设置产品保护配置"""
    product_id = (product_id or "").upper()
    if product_id not in VALID_PRODUCTS:
        return {"success": False, "error": f"无效产品：{product_id}，必须是 {VALID_PRODUCTS}"}
    if method and method not in VALID_METHODS:
        return {"success": False, "error": f"无效方式：{method}，必须是 {VALID_METHODS}"}

    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT id FROM v4_product_protection WHERE product_id=?", (product_id,)
        )
        existing = cur.fetchone()
        if existing:
            updates = []
            params = []
            if enabled is not None:
                updates.append("enabled=?")
                params.append(1 if enabled else 0)
            if method:
                updates.append("method=?")
                params.append(method)
            if config_json is not None:
                updates.append("config_json=?")
                params.append(config_json)
            updates.append("updated_at=datetime('now','localtime')")
            params.append(product_id)
            conn.execute(
                f"UPDATE v4_product_protection SET {', '.join(updates)} WHERE product_id=?",
                params
            )
        else:
            default = DEFAULT_PROTECTION.get(product_id, {})
            conn.execute(
                """INSERT INTO v4_product_protection (product_id, enabled, method, config_json)
                   VALUES (?,?,?,?)""",
                (product_id,
                 1 if enabled is not None else (1 if default.get("enabled") else 0),
                 method or default.get("method", "none"),
                 config_json)
            )
        conn.commit()

        from .audit import log_audit
        log_audit("protection_config_update", "security", product_id,
                  f"产品={product_id}, enabled={enabled}, method={method}")

        return {"success": True, "config": get_protection_config(product_id)}
    finally:
        conn.close()


def check_protection_required(product_id: str) -> dict:
    """检查某产品是否需要访问保护，返回保护方式"""
    config = get_protection_config(product_id)
    if not config.get("enabled"):
        return {"required": False, "method": "none"}
    return {"required": True, "method": config.get("method", "none")}


def _row_to_config(row) -> dict:
    method = row["method"]
    if method == "totp":  # legacy rows: TOTP was removed, fall back to password
        method = "password"
    return {
        "product_id": row["product_id"],
        "enabled": bool(row["enabled"]),
        "method": method,
        "config_json": row["config_json"],
        "updated_at": row["updated_at"],
        "description": DEFAULT_PROTECTION.get(row["product_id"], {}).get("description", ""),
    }
