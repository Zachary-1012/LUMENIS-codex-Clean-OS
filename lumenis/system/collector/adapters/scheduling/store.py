# -*- coding: utf-8 -*-
"""调度决策审计存储（旁路新表，向后兼容，绝不修改/删除 collection_logs 等任何旧表与数据）。

对齐《采集调度与风控最终执行指令》第十三条：调度必须可回答“为什么系统这一次没有采集”，
而不是只能看到“0 条”。因此把每次决策依据（含被拒绝原因、next_run_at、cooldown_until、
风险态、是否需要验证、触发来源）落库为 schedule_decisions。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from lumenis.shared.database import DatabaseRepository

_FMT = "%Y-%m-%d %H:%M:%S"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schedule_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    account_id TEXT,
    task_id TEXT,
    started_at TEXT,
    finished_at TEXT,
    duration_sec REAL,
    result_status TEXT,
    items_found INTEGER DEFAULT 0,
    items_saved INTEGER DEFAULT 0,
    error_code TEXT,
    error_message TEXT,
    risk_status TEXT,
    risk_score REAL,
    cooldown_until TEXT,
    next_run_at TEXT,
    session_status TEXT,
    verification_required INTEGER DEFAULT 0,
    trigger_source TEXT,
    allow INTEGER DEFAULT 0,
    scheduler_decision TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_schedule_decisions_platform ON schedule_decisions(platform, created_at);
"""


class ScheduleDecisionStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._repository = DatabaseRepository(db_path)

    def _conn(self) -> sqlite3.Connection:
        return self._repository.connect(timeout=15)

    def ensure_schema(self) -> None:
        """幂等建表；只新增 schedule_decisions，不触碰任何既有表。"""
        c = self._conn()
        try:
            c.executescript(_SCHEMA)
            c.commit()
        finally:
            c.close()

    def record(self, *, platform: str, allow: bool, scheduler_decision: str,
               result_status: Optional[str] = None, account_id: Optional[str] = None,
               task_id: Optional[str] = None, started_at: Optional[str] = None,
               finished_at: Optional[str] = None, duration_sec: Optional[float] = None,
               items_found: int = 0, items_saved: int = 0, error_code: Optional[str] = None,
               error_message: Optional[str] = None, risk_status: Optional[str] = None,
               risk_score: Optional[float] = None, cooldown_until: Optional[str] = None,
               next_run_at: Optional[str] = None, session_status: Optional[str] = None,
               verification_required: bool = False, trigger_source: str = "scheduler") -> int:
        c = self._conn()
        try:
            cur = c.execute(
                """INSERT INTO schedule_decisions
                   (platform,account_id,task_id,started_at,finished_at,duration_sec,result_status,
                    items_found,items_saved,error_code,error_message,risk_status,risk_score,
                    cooldown_until,next_run_at,session_status,verification_required,trigger_source,
                    allow,scheduler_decision,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (platform, account_id, task_id, started_at, finished_at, duration_sec, result_status,
                 items_found, items_saved, error_code, error_message, risk_status, risk_score,
                 cooldown_until, next_run_at, session_status, 1 if verification_required else 0,
                 trigger_source, 1 if allow else 0, scheduler_decision,
                 datetime.now().strftime(_FMT)))
            c.commit()
            return int(cur.lastrowid)
        finally:
            c.close()

    def recent(self, platform: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        c = self._conn()
        try:
            if platform:
                rows = c.execute(
                    "SELECT * FROM schedule_decisions WHERE platform=? ORDER BY id DESC LIMIT ?",
                    (platform, limit)).fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM schedule_decisions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            c.close()

    def last_decision(self, platform: str) -> Optional[Dict[str, Any]]:
        rows = self.recent(platform, 1)
        return rows[0] if rows else None
