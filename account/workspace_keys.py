"""
account/workspace_keys.py — 工作区与程序化访问密钥管理

静态密钥平滑迁移：
- v4_workspace_keys 不删表
- 降级为"受信任设备/程序化访问"可选项
- 新创建的 key 必须有 expires_at（不允许 expires_days=0 永不过期）
- 可绑定设备/IP
- 存量无过期密钥列出（requires_rotation=true），引导轮换
- 不强制吊销存量密钥（避免影响在线会话）
"""
import time
import secrets

from .models import get_db
from .security import hash_password, verify_password


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def list_workspace_keys(workspace: str = None) -> list:
    """
    列出密钥（绝不含 hash/明文）。
    对无过期密钥标记 requires_rotation=true。
    """
    conn = get_db()
    try:
        sql = ("SELECT id, workspace, label, key_prefix, status, created_by, "
               "expires_at, last_used_at, created_at, bound_device, bound_ip, key_type "
               "FROM v4_workspace_keys")
        params = ()
        if workspace:
            sql += " WHERE workspace=?"
            params = ((workspace or "").strip().upper(),)
        sql += " ORDER BY id DESC"
        keys = [dict(r) for r in conn.execute(sql, params).fetchall()]
        now = _now()
        for k in keys:
            # 无过期或已过期 → 需要轮换
            k["requires_rotation"] = (
                k["expires_at"] is None
                or k["expires_at"] == ""
                or k["expires_at"] < now
            )
            k["is_expired"] = bool(k["expires_at"] and k["expires_at"] < now)
        return keys
    finally:
        conn.close()


def create_workspace_key(workspace: str, label: str = "", created_by: int = None,
                         expires_days: int = 30, bound_device: str = None,
                         bound_ip: str = None, key_type: str = "programmatic") -> dict:
    """
    创建程序化访问密钥。
    强制过期：expires_days 必须 > 0，不允许永不过期。
    明文只在返回值里出现一次。
    """
    workspace = (workspace or "").strip().upper()
    if not workspace:
        return {"success": False, "error": "缺少工作区标识"}
    if not label:
        return {"success": False, "error": "label 不能为空"}
    if not expires_days or expires_days <= 0:
        return {"success": False, "error": "必须设置过期时间（expires_days > 0），不允许永不过期"}
    if key_type not in ("programmatic", "trusted_device"):
        return {"success": False, "error": "key_type 必须是 programmatic 或 trusted_device"}

    conn = get_db()
    try:
        key = "zbmp_" + secrets.token_urlsafe(24)[:32]
        prefix = key[:12] + "..."
        expires_at = time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(time.time() + expires_days * 86400)
        )
        cur = conn.execute(
            """INSERT INTO v4_workspace_keys
               (workspace, label, key_prefix, key_hash, created_by, status, expires_at,
                bound_device, bound_ip, key_type)
               VALUES (?,?,?,?,?,'active',?,?,?,?)""",
            (workspace, label, prefix, hash_password(key), created_by, expires_at,
             bound_device, bound_ip, key_type)
        )
        conn.commit()
        key_id = cur.lastrowid

        from .audit import log_audit
        log_audit("workspace_key_create", "workspace_key", str(key_id),
                  f"工作区={workspace}, 类型={key_type}, 过期={expires_days}天")

        return {
            "success": True, "id": key_id, "workspace": workspace,
            "key_plain": key,  # 只在生成时返回一次
            "key_prefix": prefix, "label": label,
            "expires_at": expires_at, "expires_days": expires_days,
            "bound_device": bound_device, "bound_ip": bound_ip,
            "key_type": key_type,
            "message": "请立即保存此密钥，之后无法再次查看",
        }
    finally:
        conn.close()


def revoke_workspace_key(key_id: int) -> dict:
    """吊销密钥（不删除记录，保留审计），同时失效其相关 grant。"""
    conn = get_db()
    try:
        cur = conn.execute("SELECT workspace, label FROM v4_workspace_keys WHERE id=?", (key_id,))
        row = cur.fetchone()
        if not row:
            return {"success": False, "error": "密钥不存在"}
        conn.execute("UPDATE v4_workspace_keys SET status='revoked' WHERE id=?", (key_id,))
        conn.execute(
            "UPDATE v4_workspace_grants SET expires_at=datetime('now','localtime') WHERE key_id=?",
            (key_id,)
        )
        conn.commit()

        from .audit import log_audit
        log_audit("workspace_key_revoke", "workspace_key", str(key_id),
                  f"工作区={row['workspace']}, label={row['label']}")

        return {"success": True, "key_id": key_id, "status": "revoked"}
    finally:
        conn.close()


def get_rotation_required_count() -> dict:
    """统计需要轮换的存量无过期密钥数量"""
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT COUNT(*) as cnt FROM v4_workspace_keys WHERE status='active' AND (expires_at IS NULL OR expires_at='')"
        )
        no_expiry = cur.fetchone()["cnt"]
        cur = conn.execute(
            "SELECT COUNT(*) as cnt FROM v4_workspace_keys WHERE status='active' AND expires_at < datetime('now','localtime')"
        )
        expired = cur.fetchone()["cnt"]
        cur = conn.execute("SELECT COUNT(*) as cnt FROM v4_workspace_keys WHERE status='active'")
        total_active = cur.fetchone()["cnt"]
        return {
            "total_active": total_active,
            "no_expiry": no_expiry,
            "expired": expired,
            "requires_rotation": no_expiry + expired,
        }
    finally:
        conn.close()


def verify_workspace_key(workspace: str, key: str, ip: str = None) -> dict:
    """
    校验程序化密钥。
    检查绑定IP、过期状态。命中回写 last_used_at。
    """
    workspace = (workspace or "").strip().upper()
    if not workspace or not key:
        return {"success": False, "error": "缺少参数"}
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM v4_workspace_keys WHERE workspace=? AND status='active'",
            (workspace,)
        ).fetchall()
        now = _now()
        for r in rows:
            if r["expires_at"] and r["expires_at"] < now:
                continue
            # 绑定IP校验
            if r["bound_ip"] and ip and r["bound_ip"] != ip:
                continue
            if verify_password(key.strip(), r["key_hash"]):
                conn.execute(
                    "UPDATE v4_workspace_keys SET last_used_at=datetime('now','localtime') WHERE id=?",
                    (r["id"],)
                )
                conn.commit()
                return {"success": True, "key_id": r["id"], "workspace": workspace,
                        "key_type": r["key_type"] if "key_type" in r.keys() else "programmatic"}
        return {"success": False, "error": "密钥无效或已过期"}
    finally:
        conn.close()
