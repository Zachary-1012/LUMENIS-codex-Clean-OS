"""
Auth Recovery Center（V3.0 P0 新增）
归属：Z-Brand Core / P0 采集健康中心 / Auth Recovery Center
目标：所有平台Cookie失效、登录异常，都在系统内部弹窗提示，并提供二维码恢复入口。
能力：
  1. 认证状态检测（Cookie失效/登录过期/验证码/扫码需求）
  2. 系统内弹窗提示（前端轮询获取恢复任务）
  3. 二维码恢复入口（生成恢复任务，用户扫码后状态回写）
  4. 状态回写（恢复后自动更新runtime-state，解除熔断）
  5. 自动恢复任务调度（检测到异常时自动创建恢复任务）

约束：
  - 不破解验证码、不绕过平台安全机制
  - 恢复必须由用户人工完成扫码/验证
  - 恢复后必须做健康探活，确认完全健康才解除熔断
"""
from __future__ import annotations

import json
import logging
import os
import time
import sqlite3
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

from repository_registry import resolve_path
from db_paths import main_db_path


logger = logging.getLogger(__name__)

class RecoveryStatus(str, Enum):
    PENDING = "pending"          # 待处理（已创建恢复任务，等待用户操作）
    IN_PROGRESS = "in_progress"  # 进行中（用户已开始扫码/验证）
    COMPLETED = "completed"      # 已完成（用户验证成功，健康探活通过）
    FAILED = "failed"            # 失败（验证失败或超时）
    EXPIRED = "expired"          # 已过期（超过有效期未处理）


class AuthIssueType(str, Enum):
    COOKIE_EXPIRED = "cookie_expired"      # Cookie失效
    LOGIN_EXPIRED = "login_expired"        # 登录过期
    CAPTCHA = "captcha"                    # 验证码
    QR_REQUIRED = "qr_required"            # 需要扫码
    SESSION_INVALID = "session_invalid"    # 会话无效
    IP_RISK = "ip_risk"                    # IP风控
    UNKNOWN = "unknown"                     # 未知


@dataclass
class RecoveryTask:
    """恢复任务"""
    id: int = 0
    platform: str = "xhs"
    issue_type: str = AuthIssueType.UNKNOWN.value
    status: str = RecoveryStatus.PENDING.value
    title: str = ""
    description: str = ""
    qr_code_url: str = ""          # 二维码图片URL（如有）
    recovery_url: str = ""          # 恢复操作URL（引导用户到指定页面）
    created_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    expires_at: str = ""
    created_by: str = "system"      # system / manual
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


class AuthRecoveryCenter:
    """认证恢复中心

    单例模式，全局唯一实例。
    负责：检测认证异常 → 创建恢复任务 → 前端弹窗提示 → 用户扫码恢复 → 状态回写 → 健康探活 → 解除熔断
    """

    _instance: Optional['AuthRecoveryCenter'] = None
    DB_PATH = resolve_path('data/monitor.db')
    TASK_TTL_SECONDS = 3600  # 恢复任务有效期1小时

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

    # ── 数据库 ────────────────────────────────────────────────

    def _ensure_table(self) -> None:
        """确保恢复任务表存在"""
        try:
            conn = sqlite3.connect(main_db_path())
            cur = conn.cursor()
            cur.execute("""
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
            cur.execute("CREATE INDEX IF NOT EXISTS idx_recovery_status ON auth_recovery_tasks(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_recovery_platform ON auth_recovery_tasks(platform)")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[AuthRecoveryCenter] 创建表失败: {e}")

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(main_db_path())
        conn.row_factory = sqlite3.Row
        return conn

    # ── 恢复任务管理 ──────────────────────────────────────────

    def create_task(self, platform: str, issue_type: str, title: str,
                    description: str = "", recovery_url: str = "",
                    qr_code_url: str = "", metadata: Optional[Dict] = None) -> RecoveryTask:
        """创建恢复任务

        当检测到认证异常时调用，系统自动创建恢复任务，前端弹窗提示用户。
        """
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        expires = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + self.TASK_TTL_SECONDS))

        task = RecoveryTask(
            platform=platform,
            issue_type=issue_type,
            status=RecoveryStatus.PENDING.value,
            title=title,
            description=description,
            qr_code_url=qr_code_url,
            recovery_url=recovery_url,
            created_at=now,
            updated_at=now,
            expires_at=expires,
            created_by='system',
            metadata=metadata or {},
        )

        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO auth_recovery_tasks
                (platform, issue_type, status, title, description, qr_code_url, recovery_url,
                 created_at, updated_at, expires_at, created_by, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.platform, task.issue_type, task.status, task.title,
                task.description, task.qr_code_url, task.recovery_url,
                task.created_at, task.updated_at, task.expires_at,
                task.created_by, json.dumps(task.metadata, ensure_ascii=False),
            ))
            task.id = cur.lastrowid
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[AuthRecoveryCenter] 创建任务失败: {e}")

        return task

    def get_pending_tasks(self, platform: Optional[str] = None) -> List[RecoveryTask]:
        """获取待处理的恢复任务（前端轮询用，用于弹窗提示）"""
        self._expire_old_tasks()
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            if platform:
                cur.execute("""
                    SELECT * FROM auth_recovery_tasks
                    WHERE status = ? AND platform = ?
                    ORDER BY created_at DESC
                """, (RecoveryStatus.PENDING.value, platform))
            else:
                cur.execute("""
                    SELECT * FROM auth_recovery_tasks
                    WHERE status = ?
                    ORDER BY created_at DESC
                """, (RecoveryStatus.PENDING.value,))
            tasks = [self._row_to_task(row) for row in cur.fetchall()]
            conn.close()
            return tasks
        except Exception as e:
            print(f"[AuthRecoveryCenter] 获取待处理任务失败: {e}")
            return []

    def mark_in_progress(self, task_id: int) -> bool:
        """标记任务为进行中（用户开始扫码/验证）"""
        return self._update_status(task_id, RecoveryStatus.IN_PROGRESS.value)

    def mark_completed(self, task_id: int, error_message: str = "") -> bool:
        """标记任务为已完成（用户验证成功）

        注意：标记完成后，还需要做健康探活，确认完全健康才解除熔断。
        这里只标记任务完成，健康探活由调用方（topic_recover）执行。
        """
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("""
                UPDATE auth_recovery_tasks
                SET status = ?, completed_at = ?, updated_at = ?, error_message = ?
                WHERE id = ?
            """, (RecoveryStatus.COMPLETED.value, now, now, error_message, task_id))
            conn.commit()
            success = cur.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            print(f"[AuthRecoveryCenter] 标记完成失败: {e}")
            return False

    def mark_failed(self, task_id: int, error_message: str = "") -> bool:
        """标记任务为失败"""
        return self._update_status(task_id, RecoveryStatus.FAILED.value, error_message)

    def _update_status(self, task_id: int, status: str, error_message: str = "") -> bool:
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("""
                UPDATE auth_recovery_tasks
                SET status = ?, updated_at = ?, error_message = ?
                WHERE id = ?
            """, (status, now, error_message, task_id))
            conn.commit()
            success = cur.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            print(f"[AuthRecoveryCenter] 更新状态失败: {e}")
            return False

    def _expire_old_tasks(self) -> None:
        """过期旧任务"""
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("""
                UPDATE auth_recovery_tasks
                SET status = ?, updated_at = ?
                WHERE status = ? AND expires_at < ?
            """, (RecoveryStatus.EXPIRED.value, now, RecoveryStatus.PENDING.value, now))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _row_to_task(self, row: sqlite3.Row) -> RecoveryTask:
        metadata = {}
        try:
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
        except Exception:
            pass
        return RecoveryTask(
            id=row['id'],
            platform=row['platform'],
            issue_type=row['issue_type'],
            status=row['status'],
            title=row['title'] or '',
            description=row['description'] or '',
            qr_code_url=row['qr_code_url'] or '',
            recovery_url=row['recovery_url'] or '',
            created_at=row['created_at'] or '',
            updated_at=row['updated_at'] or '',
            completed_at=row['completed_at'] or '',
            expires_at=row['expires_at'] or '',
            created_by=row['created_by'] or '',
            error_message=row['error_message'] or '',
            metadata=metadata,
        )

    # ── 认证异常检测与自动恢复 ────────────────────────────────

    def detect_and_create_task(self, platform: str, issue_type: str,
                                title: str, description: str = "",
                                recovery_url: str = "") -> Optional[RecoveryTask]:
        """检测认证异常并自动创建恢复任务

        当采集链路检测到Cookie失效/登录过期/验证码/扫码需求时调用。
        如果已有相同platform+issue_type的pending任务，不重复创建。
        """
        # 检查是否已有相同的待处理任务
        pending = self.get_pending_tasks(platform=platform)
        for t in pending:
            if t.issue_type == issue_type:
                return t  # 已有相同任务，不重复创建

        # 创建新任务
        return self.create_task(
            platform=platform,
            issue_type=issue_type,
            title=title,
            description=description,
            recovery_url=recovery_url,
        )

    def get_recovery_summary(self) -> Dict[str, Any]:
        """获取恢复中心摘要（API用）"""
        pending = self.get_pending_tasks()
        return {
            'pending_count': len(pending),
            'pending_tasks': [t.to_dict() for t in pending],
            'has_issue': len(pending) > 0,
            'ttl_seconds': self.TASK_TTL_SECONDS,
        }


# 全局单例
recovery_center = AuthRecoveryCenter()
