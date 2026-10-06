"""
工作区访问密钥（ZBMP 等受限工作区）—— Z-Brand Core

设计原则：
- 复用现有 v4 用户/会话体系（v4_users / v4_sessions），只新增"工作区级 API Key"授权层，不新造账号体系。
- This module preserves the historical workspace-key compatibility contract; it does not define the current LUMENIS default context or product entry.
- 明文密钥仅在签发时返回一次；数据库只存 PBKDF2 hash（复用 security.hash_password）。
- 全部 CREATE TABLE IF NOT EXISTS，向后兼容、不删不改任何既有表；删除本文件与对应路由即可完整回滚。
- AI 不参与授权判定；授权完全由本模块的规则与数据库状态决定。
"""
import time
import secrets

from .models import get_db
from .security import hash_password, verify_password, generate_token

WS_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS v4_workspace_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace TEXT NOT NULL,              -- 工作区标识，如 ZBMP
    label TEXT,                           -- 密钥备注（用途/设备）
    key_prefix TEXT NOT NULL,             -- 明文前 10 位，仅用于列表辨识
    key_hash TEXT NOT NULL,               -- PBKDF2 hash，不存明文
    created_by INTEGER,                   -- 签发人 user_id
    status TEXT NOT NULL DEFAULT 'active', -- active / revoked
    expires_at TEXT,                      -- 可空，空=不过期
    last_used_at TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS v4_workspace_grants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    workspace TEXT NOT NULL,
    key_id INTEGER,
    session_token TEXT,                   -- 绑定 v4_sessions.token；空=非会话直连
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_ws_keys_ws ON v4_workspace_keys(workspace, status);
CREATE INDEX IF NOT EXISTS idx_ws_grants_tok ON v4_workspace_grants(session_token, workspace);
"""

_inited = False


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def ensure_workspace_tables(conn=None):
    """幂等建表。可传入已有连接复用事务。"""
    global _inited
    own = conn is None
    conn = conn or get_db()
    try:
        conn.executescript(WS_TABLES_SQL)
        conn.commit()
        _inited = True
    finally:
        if own:
            conn.close()


def issue_workspace_key(workspace, label="", created_by=None, expires_days=None, plain=None):
    """签发工作区密钥。明文只在返回值里出现一次。"""
    workspace = (workspace or "").strip().upper()
    if not workspace:
        return {"success": False, "error": "缺少工作区标识"}
    conn = get_db()
    try:
        ensure_workspace_tables(conn)
        key = plain or ("zbmp_" + secrets.token_urlsafe(24))
        prefix = key[:10]
        expires_at = None
        if expires_days:
            expires_at = time.strftime("%Y-%m-%d %H:%M:%S",
                                       time.localtime(time.time() + expires_days * 86400))
        cur = conn.execute(
            "INSERT INTO v4_workspace_keys(workspace,label,key_prefix,key_hash,created_by,expires_at) "
            "VALUES(?,?,?,?,?,?)",
            (workspace, label, prefix, hash_password(key), created_by, expires_at),
        )
        conn.commit()
        return {"success": True, "id": cur.lastrowid, "workspace": workspace,
                "key": key, "key_prefix": prefix, "expires_at": expires_at}
    finally:
        conn.close()


def verify_workspace_key(workspace, key):
    """校验明文密钥是否为该工作区的有效(active/未过期)密钥；命中回写 last_used_at，返回记录 dict，否则 None。"""
    workspace = (workspace or "").strip().upper()
    if not workspace or not key:
        return None
    conn = get_db()
    try:
        ensure_workspace_tables(conn)
        rows = conn.execute(
            "SELECT * FROM v4_workspace_keys WHERE workspace=? AND status='active'",
            (workspace,),
        ).fetchall()
        now = _now()
        for r in rows:
            if r["expires_at"] and r["expires_at"] < now:
                continue
            if verify_password(key.strip(), r["key_hash"]):
                conn.execute("UPDATE v4_workspace_keys SET last_used_at=datetime('now','localtime') WHERE id=?",
                             (r["id"],))
                conn.commit()
                return dict(r)
        return None
    finally:
        conn.close()


def list_workspace_keys(workspace=None):
    """列出密钥（绝不含 hash/明文），供管理页展示。"""
    conn = get_db()
    try:
        ensure_workspace_tables(conn)
        sql = ("SELECT id,workspace,label,key_prefix,status,created_by,expires_at,last_used_at,created_at "
               "FROM v4_workspace_keys")
        params = ()
        if workspace:
            sql += " WHERE workspace=?"
            params = ((workspace or "").strip().upper(),)
        sql += " ORDER BY id DESC"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def revoke_workspace_key(key_id):
    """吊销密钥（不删除记录，保留审计），同时失效其相关 grant。"""
    conn = get_db()
    try:
        ensure_workspace_tables(conn)
        conn.execute("UPDATE v4_workspace_keys SET status='revoked' WHERE id=?", (key_id,))
        conn.execute("UPDATE v4_workspace_grants SET expires_at=datetime('now','localtime') WHERE key_id=?",
                     (key_id,))
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def grant_session(user_id, workspace, key_id, session_token, grant_hours=12):
    """给指定会话写入工作区授权（unlock 成功后调用）。"""
    workspace = (workspace or "").strip().upper()
    expires_at = time.strftime("%Y-%m-%d %H:%M:%S",
                               time.localtime(time.time() + grant_hours * 3600))
    conn = get_db()
    try:
        ensure_workspace_tables(conn)
        conn.execute(
            "INSERT INTO v4_workspace_grants(user_id,workspace,key_id,session_token,expires_at) "
            "VALUES(?,?,?,?,?)",
            (user_id, workspace, key_id, session_token, expires_at),
        )
        conn.commit()
        return {"success": True, "expires_at": expires_at}
    finally:
        conn.close()


def session_can_access(session_token, workspace):
    """该会话当前是否对某工作区有有效授权。"""
    workspace = (workspace or "").strip().upper()
    if not session_token:
        return False
    conn = get_db()
    try:
        ensure_workspace_tables(conn)
        row = conn.execute(
            "SELECT 1 FROM v4_workspace_grants WHERE session_token=? AND workspace=? AND expires_at>=? LIMIT 1",
            (session_token, workspace, _now()),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def open_owner_session(ip="", user_agent=""):
    """无现有会话、但密钥有效时：以 owner 身份建立一个 v4 会话（本地单机工作区门票即登录态）。"""
    from ..config import AUTH_CONFIG
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM v4_users WHERE role='owner' AND status='active' ORDER BY id LIMIT 1").fetchone()
        if not row:
            return None
        token = generate_token(row["id"])
        expires_at = time.strftime("%Y-%m-%d %H:%M:%S",
                                   time.localtime(time.time() + AUTH_CONFIG["token_expire_hours"] * 3600))
        conn.execute(
            "INSERT INTO v4_sessions(user_id,token,ip,user_agent,expires_at) VALUES(?,?,?,?,?)",
            (row["id"], token, ip, user_agent, expires_at),
        )
        conn.execute("UPDATE v4_users SET last_login_at=datetime('now','localtime'),last_login_ip=? WHERE id=?",
                     (ip, row["id"]))
        conn.commit()
        return {"token": token, "user_id": row["id"], "username": row["username"],
                "role": row["role"], "display_name": row["display_name"], "expires_at": expires_at}
    finally:
        conn.close()
