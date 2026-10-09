# -*- coding: utf-8 -*-
"""调度决策审计存储（旁路新表，向后兼容，绝不修改/删除 collection_logs 等任何旧表与数据）。

对齐《采集调度与风控最终执行指令》第十三条：调度必须可回答“为什么系统这一次没有采集”，
而不是只能看到“0 条”。因此把每次决策依据（含被拒绝原因、next_run_at、cooldown_until、
风险态、是否需要验证、触发来源）落库为 schedule_decisions。
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import re
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

    @contextmanager
    def platform_attempt_lock(self, platform: str):
        """Keep one baseline worker per platform across processes and restarts.

        This OS lock contains no business data or credentials. The OS releases
        it when the holder exits, including when its task wrapper has died;
        another worker cannot treat a still-running orphan as an expired lease.
        """
        if not isinstance(platform, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", platform):
            raise ValueError("invalid platform lock identity")
        directory = Path(self.db_path).resolve().parent / "runtime" / "collector-schedule"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (platform + ".lock")
        with path.open("a+b") as handle:
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (BlockingIOError, PermissionError):
                yield False
                return
            try:
                yield True
            finally:
                handle.seek(0)
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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

    @staticmethod
    def _baseline_history(rows):
        from .prelaunch_baseline import BaselineRunHistory

        def parse(value):
            try:
                parsed = datetime.fromisoformat(value) if value else None
                return parsed.replace(tzinfo=__import__("datetime").timezone.utc) if parsed and parsed.tzinfo is None else parsed
            except (TypeError, ValueError):
                return None

        last_attempt = parse(rows[0]["started_at"]) if rows else None
        running = bool(rows and rows[0]["result_status"] == "RUNNING")
        failures = 0
        last_failure = None
        last_success = None
        for row in rows:
            status = row["result_status"]
            if status == "FAILED":
                failures += 1
                if last_failure is None:
                    last_failure = parse(row["finished_at"]) or parse(row["started_at"])
            elif status == "SUCCESS":
                last_success = parse(row["finished_at"]) or parse(row["started_at"])
                break
            elif status == "RUNNING":
                continue
        return BaselineRunHistory(last_attempt_at=last_attempt,
                                  last_failure_at=last_failure,
                                  last_success_at=last_success,
                                  consecutive_failures=failures,
                                  attempt_in_progress=running)

    def _baseline_rows(self, conn, plan_id):
        return [dict(row) for row in conn.execute(
            """SELECT id, started_at, finished_at, result_status
                 FROM schedule_decisions
                WHERE platform='prelaunch_public_baseline' AND task_id=?
                ORDER BY id DESC""", (plan_id,)
        ).fetchall()]

    def claim_public_baseline_attempt(self, plan, *, now: datetime,
                                      lease_seconds: int = 3600):
        """Atomically claim one due attempt in the existing SYSTEM audit store."""
        from .prelaunch_baseline import BaselineConfigError, evaluate_baseline_due

        if not getattr(plan, "_signed_config_digest", ""):
            raise BaselineConfigError("HMAC_UNAVAILABLE")
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be positive")
        self.ensure_schema()
        c = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            rows = self._baseline_rows(c, plan.plan_id)
            history = self._baseline_history(rows)
            if history.attempt_in_progress:
                started = history.last_attempt_at
                if started is None or (now - started).total_seconds() < lease_seconds:
                    decision = evaluate_baseline_due(plan, history, now=now)
                    c.commit()
                    return None, decision
                c.execute(
                    """UPDATE schedule_decisions
                          SET result_status='FAILED', finished_at=?,
                              error_code='WORKER_LEASE_EXPIRED',
                              scheduler_decision='WORKER_LEASE_EXPIRED'
                        WHERE id=? AND result_status='RUNNING'""",
                    (now.isoformat(timespec="seconds"), rows[0]["id"]),
                )
                rows = self._baseline_rows(c, plan.plan_id)
                history = self._baseline_history(rows)
            decision = evaluate_baseline_due(plan, history, now=now)
            if not decision.due:
                c.commit()
                return None, decision
            stamp = now.isoformat(timespec="seconds")
            cur = c.execute(
                """INSERT INTO schedule_decisions
                   (platform, task_id, started_at, result_status, trigger_source,
                    allow, scheduler_decision, created_at)
                   VALUES ('prelaunch_public_baseline', ?, ?, 'RUNNING',
                           'prelaunch_baseline', 1, 'BASELINE_ATTEMPT_CLAIMED', ?)""",
                (plan.plan_id, stamp, stamp),
            )
            attempt_id = int(cur.lastrowid)
            c.commit()
            return attempt_id, decision
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    def finish_public_baseline_attempt(self, plan, attempt_id: int, *,
                                       success: bool, now: datetime,
                                       error_code: Optional[str] = None) -> bool:
        """Persist one honest terminal outcome; a claimed attempt is completed once."""
        from .prelaunch_baseline import BaselineConfigError
        if not getattr(plan, "_signed_config_digest", ""):
            raise BaselineConfigError("HMAC_UNAVAILABLE")
        if not isinstance(success, bool):
            raise ValueError("success must be an explicit boolean")
        if not success and not error_code:
            raise ValueError("failed attempts require an error_code")
        c = self._conn()
        try:
            cur = c.execute(
                """UPDATE schedule_decisions
                      SET finished_at=?, result_status=?, error_code=?,
                          scheduler_decision=?
                    WHERE id=? AND platform='prelaunch_public_baseline'
                      AND task_id=? AND result_status='RUNNING'""",
                (now.isoformat(timespec="seconds"),
                 "SUCCESS" if success else "FAILED", None if success else error_code,
                 "BASELINE_SUCCESS" if success else "BASELINE_FAILED",
                 int(attempt_id), plan.plan_id),
            )
            c.commit()
            return cur.rowcount == 1
        finally:
            c.close()

    def public_baseline_history(self, plan):
        """Read durable due state after process restart; never resets/reseeds it."""
        self.ensure_schema()
        c = self._conn()
        try:
            return self._baseline_history(self._baseline_rows(c, plan.plan_id))
        finally:
            c.close()
