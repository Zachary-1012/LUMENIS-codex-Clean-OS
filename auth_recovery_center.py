"""
Auth Recovery Center
认证恢复中心：检测登录/Cookie异常 → 创建恢复任务 → 用户人工恢复 → 健康探活后解除熔断。
不破解验证码、不绕过平台安全机制。
"""
from __future__ import annotations

import json
import time
import sqlite3
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

from database import DB_PATH


class RecoveryStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class AuthIssueType(str, Enum):
    COOKIE_EXPIRED = "cookie_expired"
    LOGIN_EXPIRED = "login_expired"
    CAPTCHA = "captcha"
    QR_REQUIRED = "qr_required"
    SESSION_INVALID = "session_invalid"
    IP_RISK = "ip_risk"
    UNKNOWN = "unknown"


@dataclass
class RecoveryTask:
    id: int = 0
    platform: str = "xhs"
    issue_type: str = AuthIssueType.UNKNOWN.value
    status: str = RecoveryStatus.PENDING.value
    title: str = ""
    description: str = ""
    qr_code_url: str = ""
    recovery_url: str = ""
    created_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    expires_at: str = ""
    created_by: str = "system"
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuthRecoveryCenter:
    """认证恢复中心；数据库路径统一由 ZBC database 层管理。"""

    _instance: Optional['AuthRecoveryCenter'] = None
    TASK_TTL_SECONDS = 3600

    def __new__(cls) -> 'AuthRecoveryCenter':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._ensure_table()

    def _ensure_table(self) -> None:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS auth_recovery_tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        platform TEXT NOT NULL,
                        issue_type TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        title TEXT,
                        description TEXT,
                        qr_code_url TEXT,
                        recovery_url TEXT,
                        created_at TEXT,
                        updated_at TEXT,
                        completed_at TEXT,
                        expires_at TEXT,
                        created_by TEXT DEFAULT 'system',
                        error_message TEXT,
                        metadata TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_recovery_status ON auth_recovery_tasks(status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_recovery_platform ON auth_recovery_tasks(platform)")
        except Exception as e:
            print(f"[AuthRecoveryCenter] 创建表失败: {e}")

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def create_task(self, platform: str, issue_type: str, title: str,
                    description: str = "", recovery_url: str = "",
                    qr_code_url: str = "", metadata: Optional[Dict] = None) -> RecoveryTask:
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        expires = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + self.TASK_TTL_SECONDS))
        task = RecoveryTask(platform=platform, issue_type=issue_type, title=title,
                            description=description, qr_code_url=qr_code_url,
                            recovery_url=recovery_url, created_at=now, updated_at=now,
                            expires_at=expires, metadata=metadata or {})
        try:
            with self._get_conn() as conn:
                cur = conn.execute("""
                    INSERT INTO auth_recovery_tasks
                    (platform, issue_type, status, title, description, qr_code_url, recovery_url,
                     created_at, updated_at, expires_at, created_by, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (task.platform, task.issue_type, task.status, task.title, task.description,
                      task.qr_code_url, task.recovery_url, task.created_at, task.updated_at,
                      task.expires_at, task.created_by, json.dumps(task.metadata, ensure_ascii=False)))
                task.id = cur.lastrowid
        except Exception as e:
            print(f"[AuthRecoveryCenter] 创建任务失败: {e}")
        return task

    def get_pending_tasks(self, platform: Optional[str] = None) -> List[RecoveryTask]:
        self._expire_old_tasks()
        try:
            with self._get_conn() as conn:
                if platform:
                    rows = conn.execute("SELECT * FROM auth_recovery_tasks WHERE status = ? AND platform = ? ORDER BY created_at DESC",
                                        (RecoveryStatus.PENDING.value, platform)).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM auth_recovery_tasks WHERE status = ? ORDER BY created_at DESC",
                                        (RecoveryStatus.PENDING.value,)).fetchall()
                return [self._row_to_task(row) for row in rows]
        except Exception as e:
            print(f"[AuthRecoveryCenter] 获取待处理任务失败: {e}")
            return []

    def mark_in_progress(self, task_id: int) -> bool:
        return self._update_status(task_id, RecoveryStatus.IN_PROGRESS.value)

    def mark_completed(self, task_id: int, error_message: str = "") -> bool:
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            with self._get_conn() as conn:
                cur = conn.execute("""UPDATE auth_recovery_tasks
                    SET status = ?, completed_at = ?, updated_at = ?, error_message = ? WHERE id = ?""",
                    (RecoveryStatus.COMPLETED.value, now, now, error_message, task_id))
                return cur.rowcount > 0
        except Exception as e:
            print(f"[AuthRecoveryCenter] 标记完成失败: {e}")
            return False

    def mark_failed(self, task_id: int, error_message: str = "") -> bool:
        return self._update_status(task_id, RecoveryStatus.FAILED.value, error_message)

    def _update_status(self, task_id: int, status: str, error_message: str = "") -> bool:
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            with self._get_conn() as conn:
                cur = conn.execute("UPDATE auth_recovery_tasks SET status = ?, updated_at = ?, error_message = ? WHERE id = ?",
                                   (status, now, error_message, task_id))
                return cur.rowcount > 0
        except Exception as e:
            print(f"[AuthRecoveryCenter] 更新状态失败: {e}")
            return False

    def _expire_old_tasks(self) -> None:
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            with self._get_conn() as conn:
                conn.execute("UPDATE auth_recovery_tasks SET status = ?, updated_at = ? WHERE status = ? AND expires_at < ?",
                             (RecoveryStatus.EXPIRED.value, now, RecoveryStatus.PENDING.value, now))
        except Exception:
            pass

    def _row_to_task(self, row: sqlite3.Row) -> RecoveryTask:
        try:
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
        except Exception:
            metadata = {}
        return RecoveryTask(
            id=row['id'], platform=row['platform'], issue_type=row['issue_type'], status=row['status'],
            title=row['title'] or '', description=row['description'] or '', qr_code_url=row['qr_code_url'] or '',
            recovery_url=row['recovery_url'] or '', created_at=row['created_at'] or '', updated_at=row['updated_at'] or '',
            completed_at=row['completed_at'] or '', expires_at=row['expires_at'] or '', created_by=row['created_by'] or '',
            error_message=row['error_message'] or '', metadata=metadata)

    def detect_and_create_task(self, platform: str, issue_type: str, title: str,
                                description: str = "", recovery_url: str = "") -> Optional[RecoveryTask]:
        for task in self.get_pending_tasks(platform=platform):
            if task.issue_type == issue_type:
                return task
        return self.create_task(platform=platform, issue_type=issue_type, title=title,
                                description=description, recovery_url=recovery_url)

    def get_recovery_summary(self) -> Dict[str, Any]:
        pending = self.get_pending_tasks()
        return {'pending_count': len(pending), 'pending_tasks': [t.to_dict() for t in pending],
                'has_issue': bool(pending), 'ttl_seconds': self.TASK_TTL_SECONDS}


recovery_center = AuthRecoveryCenter()
