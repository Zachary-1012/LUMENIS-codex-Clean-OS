"""
account/models.py — 数据库模型与建表

保留全部 v4_ 表名，新增 v4_verification_codes / v4_member_authorizations / v4_login_approvals。
对 v4_users 做幂等 ALTER TABLE 新增 avatar/phone 字段（不破坏现有数据）。
全部 CREATE TABLE IF NOT EXISTS / ALTER TABLE 安全操作。

数据库路径统一通过 db_paths.main_db_path() 在连接时解析，避免模块 reload / 环境变量切换后
继续使用 import-time 固化路径，保证测试/生产 DB identity 与全仓 canonical contract 一致。
"""
import os
import sqlite3

from lumenis.shared.database import get_repository, main_db_path

# ── 基础 v4 表（与 lumenis/auth/models.py 保持一致，幂等重建） ──
BASE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS v4_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    display_name TEXT,
    email TEXT,
    status TEXT DEFAULT 'active',
    failed_attempts INTEGER DEFAULT 0,
    locked_until TEXT,
    last_login_at TEXT,
    last_login_ip TEXT,
    must_change_password INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS v4_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    ip TEXT,
    user_agent TEXT,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES v4_users(id)
);

CREATE TABLE IF NOT EXISTS v4_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    action TEXT NOT NULL,
    resource TEXT,
    resource_id TEXT,
    detail TEXT,
    ip TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS v4_security_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer_hash TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS v4_login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    ip TEXT,
    success INTEGER,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS v4_workspace_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace TEXT NOT NULL,
    label TEXT,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    created_by INTEGER,
    status TEXT NOT NULL DEFAULT 'active',
    expires_at TEXT,
    last_used_at TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS v4_workspace_grants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    workspace TEXT NOT NULL,
    key_id INTEGER,
    session_token TEXT,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
"""

# ── 新增表：随机数字验证码 ──
VERIFICATION_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS v4_verification_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    scenario TEXT NOT NULL,              -- workspace_unlock / sensitive_action / new_device
    code_hash TEXT NOT NULL,             -- PBKDF2 hash，不存明文
    code_salt TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    failed_attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 5,
    status TEXT DEFAULT 'pending',       -- pending / verified / expired / revoked
    delivery_channel TEXT DEFAULT 'in_app',  -- in_app / sms / email
    delivery_status TEXT DEFAULT 'delivered', -- delivered / blocked / failed
    ip TEXT,
    user_agent TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    verified_at TEXT,
    FOREIGN KEY (user_id) REFERENCES v4_users(id)
);
CREATE INDEX IF NOT EXISTS idx_vc_user_scenario ON v4_verification_codes(user_id, scenario, status);
CREATE INDEX IF NOT EXISTS idx_vc_expires ON v4_verification_codes(expires_at);
"""

# ── 新增表：成员双域授权矩阵 ──
AUTHORIZATION_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS v4_member_authorizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id TEXT NOT NULL,            -- ZBMP / CTH / SHARED / SYSTEM
    module TEXT NOT NULL DEFAULT '*',    -- 模块标识，*=全部
    action TEXT NOT NULL DEFAULT 'read', -- read / write
    data_scope TEXT,                     -- 数据范围描述（可选）
    time_range TEXT,                     -- 时段限制（可选）
    granted_by INTEGER,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(user_id, product_id, module, action)
);
CREATE INDEX IF NOT EXISTS idx_ma_user ON v4_member_authorizations(user_id);
"""

# ── 新增表：登录审批 ──
APPROVAL_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS v4_login_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    ip TEXT,
    user_agent TEXT,
    device_info TEXT,
    status TEXT DEFAULT 'pending',       -- pending / approved / rejected
    requested_at TEXT DEFAULT (datetime('now','localtime')),
    decided_at TEXT,
    decided_by INTEGER,
    reason TEXT,
    FOREIGN KEY (user_id) REFERENCES v4_users(id)
);
CREATE INDEX IF NOT EXISTS idx_la_status ON v4_login_approvals(status);
"""

# ── 新增表：产品保护配置 ──
PROTECTION_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS v4_product_protection (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT UNIQUE NOT NULL,     -- ZBMP / CTH / SYSTEM
    enabled INTEGER DEFAULT 1,
    method TEXT DEFAULT 'none',          -- password / reauth / none
    config_json TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
"""

# ── 新增表：用户导航自定义 ──
NAV_CONFIG_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS user_nav_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    domain TEXT NOT NULL,                -- ZBMP / CTH / SYSTEM
    nav_items TEXT NOT NULL,             -- JSON: [{id,label,icon,visible,order}]
    updated_at TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(user_id, domain)
);
"""

# ── 新增表：技能/Agent 注册表 ──
SKILLS_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS skills_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    product TEXT DEFAULT 'SYSTEM',       -- ZBMP / CTH / SYSTEM
    domain TEXT DEFAULT 'global',
    status TEXT DEFAULT 'disabled',      -- enabled / disabled
    config_json TEXT,
    version TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
"""

ACCOUNT_TABLES_SQL = (BASE_TABLES_SQL + VERIFICATION_TABLES_SQL +
                      AUTHORIZATION_TABLES_SQL + APPROVAL_TABLES_SQL +
                      PROTECTION_TABLES_SQL +
                      NAV_CONFIG_TABLES_SQL + SKILLS_TABLES_SQL)

# 需要对 v4_users 新增的字段（幂等 ALTER）
_USER_NEW_COLUMNS = [
    ("must_change_password", "INTEGER DEFAULT 0"),
    ("avatar", "TEXT"),
    ("phone", "TEXT"),
]
# 需要对 v4_workspace_keys 新增的字段
_WS_KEY_NEW_COLUMNS = [
    ("bound_device", "TEXT"),
    ("bound_ip", "TEXT"),
    ("key_type", "TEXT DEFAULT 'programmatic'"),
]

# Universal Skill Runtime metadata extends the existing skills_registry.  It
# is deliberately a column migration rather than a second plugin database.
# Runtime/package contents and secrets are not stored in this table.
_SKILL_RUNTIME_COLUMNS = [
    ("source", "TEXT"),
    ("source_type", "TEXT DEFAULT 'builtin'"),
    ("revision", "TEXT"),
    ("digest", "TEXT"),
    ("runtime", "TEXT DEFAULT 'builtin'"),
    ("entrypoint", "TEXT"),
    ("capabilities_json", "TEXT DEFAULT '[]'"),
    ("tools_json", "TEXT DEFAULT '[]'"),
    ("input_schema_json", "TEXT DEFAULT '{}'"),
    ("output_schema_json", "TEXT DEFAULT '{}'"),
    ("permissions_requested_json", "TEXT DEFAULT '[]'"),
    ("permissions_granted_json", "TEXT DEFAULT '[]'"),
    ("secrets_required_json", "TEXT DEFAULT '[]'"),
    ("dependencies_json", "TEXT DEFAULT '[]'"),
    ("compatibility_json", "TEXT DEFAULT '{}'"),
    ("trust_level", "TEXT DEFAULT 'unverified'"),
    ("health_state", "TEXT DEFAULT 'unknown'"),
    ("install_state", "TEXT DEFAULT 'not_installed'"),
    ("lifecycle_state", "TEXT DEFAULT 'registered'"),
    ("install_path", "TEXT"),
    ("active_version", "TEXT"),
    ("previous_version", "TEXT"),
    ("last_error", "TEXT"),
    ("last_health_at", "TEXT"),
]


def get_db():
    """获取数据库连接；路径在调用时通过全仓 canonical resolver 解析。"""
    conn = get_repository().connect()
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _column_exists(conn, table, column):
    """检查列是否存在"""
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = {row["name"] for row in cur.fetchall()}
    return column in cols


def ensure_auth_user_columns(conn):
    """Apply the canonical additive user columns before account bootstrap."""
    for col, col_type in _USER_NEW_COLUMNS:
        if not _column_exists(conn, "v4_users", col):
            conn.execute(f"ALTER TABLE v4_users ADD COLUMN {col} {col_type}")


def _ensure_owner_account(conn):
    """Provision an initial owner only from explicit operator injection.

    Existing accounts are never rotated or overwritten by initialization.
    Unconfigured pre-beta deployments do not acquire a predictable login.
    """
    from .security import hash_password
    cur = conn.execute("SELECT COUNT(*) as cnt FROM v4_users WHERE role='owner'")
    if cur.fetchone()["cnt"] == 0:
        username = os.environ.get("LUMENIS_BOOTSTRAP_OWNER_USERNAME", "").strip()
        password = os.environ.get("LUMENIS_BOOTSTRAP_OWNER_PASSWORD", "")
        if not username and not password:
            return
        if not username or len(password) < 16:
            raise ValueError("Initial owner requires an explicit username and password of at least 16 characters")
        pwd_hash = hash_password(password)
        conn.execute(
            "INSERT INTO v4_users (username, password_hash, role, display_name, status, must_change_password) "
            "VALUES (?,?,?,?,?,1)",
            (username, pwd_hash, "owner", "超级主账号", "active")
        )
        conn.commit()


def _ensure_default_security_questions(conn):
    """Compatibility hook: recovery answers must be set by an authorized owner.

    Never seed personal or publicly known answers. Existing configured recovery
    records are deliberately preserved for a separately authorized rotation.
    """


def init_account_db():
    """初始化账户体系全部表，幂等操作。并入主数据库启动链。"""
    conn = get_db()
    try:
        conn.executescript(ACCOUNT_TABLES_SQL)
        # TOTP was removed by product decision. Existing v4_totp_secrets rows and
        # stored 'totp' protection methods are retained untouched (AGENTS.md §9:
        # no silent destructive migration); nothing reads them any more and
        # product_protection maps a stored 'totp' method to password on read.
        conn.commit()
        # 幂等新增列
        ensure_auth_user_columns(conn)
        for col, col_type in _WS_KEY_NEW_COLUMNS:
            if not _column_exists(conn, "v4_workspace_keys", col):
                conn.execute(f"ALTER TABLE v4_workspace_keys ADD COLUMN {col} {col_type}")
        for col, col_type in _SKILL_RUNTIME_COLUMNS:
            if not _column_exists(conn, "skills_registry", col):
                conn.execute(f"ALTER TABLE skills_registry ADD COLUMN {col} {col_type}")
        conn.commit()
        # 索引
        conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_v4_sessions_token ON v4_sessions(token);
            CREATE INDEX IF NOT EXISTS idx_v4_audit_user ON v4_audit_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_v4_audit_time ON v4_audit_logs(created_at);
            CREATE INDEX IF NOT EXISTS idx_ws_keys_ws ON v4_workspace_keys(workspace, status);
            CREATE INDEX IF NOT EXISTS idx_ws_grants_tok ON v4_workspace_grants(session_token, workspace);
        """)
        conn.commit()
        _ensure_owner_account(conn)
        _ensure_default_security_questions(conn)
    finally:
        conn.close()
