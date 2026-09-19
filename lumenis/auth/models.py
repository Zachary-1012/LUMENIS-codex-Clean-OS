"""
认证数据库模型
在现有 monitor.db 中新增 V4 认证相关表，不影响现有表。
"""
import sqlite3
import os
from lumenis.shared.database import get_repository

V4_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS v4_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',  -- owner/admin/user
    display_name TEXT,
    email TEXT,
    status TEXT DEFAULT 'active',  -- active/disabled
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

CREATE INDEX IF NOT EXISTS idx_v4_sessions_token ON v4_sessions(token);
CREATE INDEX IF NOT EXISTS idx_v4_audit_user ON v4_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_v4_audit_time ON v4_audit_logs(created_at);
"""


def get_db():
    """获取数据库连接"""
    conn = get_repository().connect()
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_auth_db():
    """初始化认证相关表，幂等操作"""
    conn = get_db()
    try:
        conn.executescript(V4_TABLES_SQL)
        conn.commit()
        # 确保主账号存在（默认 Zachary/Zachary01，首次启动时创建）
        _ensure_owner_account(conn)
        _ensure_default_security_questions(conn)
    finally:
        conn.close()


def _ensure_owner_account(conn):
    """确保主账号存在，不存在则创建"""
    from .security import hash_password
    cur = conn.execute("SELECT COUNT(*) as cnt FROM v4_users WHERE role='owner'")
    if cur.fetchone()["cnt"] == 0:
        pwd_hash = hash_password("Zachary01")
        conn.execute(
            "INSERT INTO v4_users (username, password_hash, role, display_name, status) VALUES (?,?,?,?,?)",
            ("Zachary", pwd_hash, "owner", "超级主账号", "active")
        )
        conn.commit()


def _ensure_default_security_questions(conn):
    """确保默认安全问答存在"""
    from .security import hash_password
    cur = conn.execute("SELECT COUNT(*) as cnt FROM v4_security_questions WHERE is_active=1")
    if cur.fetchone()["cnt"] == 0:
        defaults = [
            ("手机号", hash_password("18504635216")),
            ("生日", hash_password("1012")),
        ]
        for q, a_hash in defaults:
            conn.execute(
                "INSERT INTO v4_security_questions (question, answer_hash, is_active) VALUES (?,?,1)",
                (q, a_hash)
            )
        conn.commit()
