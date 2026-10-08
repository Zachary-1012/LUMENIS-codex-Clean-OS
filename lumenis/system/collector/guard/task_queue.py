# -*- coding: utf-8 -*-
"""极简 SQLite 任务队列（能力提取自 neotask：SQLite 后端 + 优先级 + 零依赖）。

neotask（neopen/neotask, 2026-03）是 Celery 的轻量零依赖替代——SQLite/Redis 后端、
优先级、延时、重试。ZBC 采集已有同步调度 + DLQ 死信重放，此处补齐基线 §10 的
「Scheduler/Queue/Worker」中的 Queue 层：把批量任务（关键词采集、事件分析、报告生成）
入队，Worker 按优先级/时间消费，失败自动退避重试（对齐 baldur/neotask 范式）。

能力：
  - enqueue(task_type, payload, priority, delay)  -> id
  - dequeue()                                      -> 取到期最高优先级任务并标记 running（worker 用）
  - ack/fail/heartbeat/checkpoint require the server-issued run_id receipt
    returned by dequeue, so a reclaimed task cannot be mutated by an old worker.
  - stats()                                        -> 各状态计数（监控/Observatory 用）
零第三方依赖（纯 sqlite3），数据落盘可恢复（数据零丢失）。
"""
import json
import os
import threading
import time
import uuid

from lumenis.shared.database import DatabaseRepository
from lumenis.shared.database.registry import get_data_dir

# 默认队列文件（可注入）
DEFAULT_PATH = os.path.join(get_data_dir(), "task_queue.db")

_LOCK = threading.Lock()


class TaskQueue:
    def __init__(self, path=None, max_attempts=3):
        self.path = path or DEFAULT_PATH
        self.max_attempts = max_attempts
        self._repository = DatabaseRepository(self.path)
        self._conn = self._repository.connect(check_same_thread=False)
        self._init()

    def _init(self):
        with _LOCK, self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,
                    status TEXT DEFAULT 'pending',
                    created_at REAL,
                    scheduled_at REAL,
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT DEFAULT '',
                    locked_at REAL DEFAULT 0,
                    run_id TEXT DEFAULT '',
                    worker_id TEXT DEFAULT '',
                    lease_owner TEXT DEFAULT '',
                    started_at REAL DEFAULT 0,
                    last_heartbeat_at REAL DEFAULT 0,
                    last_success_at REAL DEFAULT 0,
                    last_checkpoint_at REAL DEFAULT 0,
                    checkpoint_id TEXT DEFAULT '',
                    recovery_reason TEXT DEFAULT ''
                )""")
            columns = {row[1] for row in self._conn.execute("PRAGMA table_info(tasks)")}
            for name, definition in (("run_id", "TEXT DEFAULT ''"), ("worker_id", "TEXT DEFAULT ''"),
                ("lease_owner", "TEXT DEFAULT ''"), ("started_at", "REAL DEFAULT 0"),
                ("last_heartbeat_at", "REAL DEFAULT 0"), ("last_success_at", "REAL DEFAULT 0"),
                ("last_checkpoint_at", "REAL DEFAULT 0"), ("checkpoint_id", "TEXT DEFAULT ''"),
                ("recovery_reason", "TEXT DEFAULT ''")):
                if name not in columns:
                    self._conn.execute("ALTER TABLE tasks ADD COLUMN %s %s" % (name, definition))
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_consume "
                "ON tasks(status, scheduled_at, priority)")

    def enqueue(self, task_type, payload, priority=5, delay=0):
        """入队。delay>0 为延时任务（scheduled_at = now + delay）。"""
        now = time.time()
        with _LOCK, self._conn:
            cur = self._conn.execute(
                "INSERT INTO tasks(task_type, payload, priority, status, created_at, scheduled_at) "
                "VALUES(?,?,?, 'pending', ?, ?)",
                (task_type, json.dumps(payload, ensure_ascii=False), int(priority),
                 now, now + float(delay)))
            return cur.lastrowid

    def dequeue(self, worker_id="", lease_owner=""):
        """Claim the next due task and issue a fresh server-owned run_id receipt.

        A new receipt is generated for every claim, including retries. Callers
        must return that receipt with every lease mutation. No due task returns
        None; otherwise the returned dict reflects the claimed row.
        """
        worker_id = str(worker_id or "")
        lease_owner = str(lease_owner or worker_id)
        with _LOCK, self._conn:
            # Serialize the read/claim pair across processes, not only threads.
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                "SELECT * FROM tasks WHERE status='pending' AND scheduled_at <= ? "
                "ORDER BY priority ASC, scheduled_at ASC, id ASC LIMIT 1",
                (time.time(),)).fetchone()
            if row is None:
                return None
            now = time.time()
            task_id = row["id"]
            run_id = uuid.uuid4().hex
            claimed = self._conn.execute(
                "UPDATE tasks SET status='running', locked_at=?, worker_id=?, lease_owner=?, run_id=?, "
                "started_at=?, last_heartbeat_at=? WHERE id=? AND status='pending'",
                (now, worker_id, lease_owner, run_id, now, now, task_id))
            if claimed.rowcount != 1:
                return None
            # 重新查询以返回 UPDATE 后的最新数据（避免返回旧的 status/pending）
            updated = self._conn.execute(
                "SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            d = dict(updated)
            try:
                d["payload"] = json.loads(d["payload"])
            except (json.JSONDecodeError, TypeError):
                pass
            return d

    @staticmethod
    def _has_attempt_receipt(run_id, worker_id, lease_owner):
        return bool(run_id) and worker_id is not None and lease_owner is not None

    def ack(self, task_id, *, run_id=None, worker_id=None, lease_owner=None):
        """Acknowledge only the currently running attempt identified by dequeue."""
        if not self._has_attempt_receipt(run_id, worker_id, lease_owner):
            return False
        with _LOCK, self._conn:
            cur = self._conn.execute(
                "UPDATE tasks SET status='done', last_success_at=?, lease_owner='' "
                "WHERE id=? AND status='running' AND run_id=? AND worker_id=? AND lease_owner=?",
                (time.time(), task_id, run_id, worker_id, lease_owner))
            return cur.rowcount == 1

    def heartbeat(self, task_id, worker_id, *, run_id=None, lease_owner=None):
        """Renew only the active attempt; old or incomplete receipts fail closed."""
        if not self._has_attempt_receipt(run_id, worker_id, lease_owner):
            return False
        with _LOCK, self._conn:
            cur = self._conn.execute(
                "UPDATE tasks SET last_heartbeat_at=? "
                "WHERE id=? AND status='running' AND run_id=? AND worker_id=? AND lease_owner=?",
                (time.time(), task_id, run_id, worker_id, lease_owner))
            return cur.rowcount == 1

    def checkpoint(self, task_id, worker_id, checkpoint_id, *, run_id=None, lease_owner=None):
        """Persist a checkpoint only for the active attempt receipt."""
        if not self._has_attempt_receipt(run_id, worker_id, lease_owner):
            return False
        with _LOCK, self._conn:
            now = time.time()
            cur = self._conn.execute(
                "UPDATE tasks SET checkpoint_id=?, last_checkpoint_at=? "
                "WHERE id=? AND status='running' AND run_id=? AND worker_id=? AND lease_owner=?",
                (str(checkpoint_id), now, task_id, run_id, worker_id, lease_owner))
            return cur.rowcount == 1

    def fail(self, task_id, error="", *, run_id=None, worker_id=None, lease_owner=None):
        """Fail only the active attempt; return False for a stale receipt."""
        return self._fail_attempt(
            task_id, error, run_id=run_id, worker_id=worker_id,
            lease_owner=lease_owner)

    def _fail_attempt(self, task_id, error, *, run_id, worker_id, lease_owner,
                      stale_before=None):
        if not self._has_attempt_receipt(run_id, worker_id, lease_owner):
            return False
        where = (
            "id=? AND status='running' AND run_id=? AND worker_id=? AND lease_owner=?"
        )
        identity = [task_id, run_id, worker_id, lease_owner]
        if stale_before is not None:
            where += " AND last_heartbeat_at < ?"
            identity.append(float(stale_before))
        error_text = str(error or "")[:500]
        with _LOCK, self._conn:
            # Hold the SQLite write reservation across validation and transition.
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                "SELECT attempts FROM tasks WHERE " + where, identity).fetchone()
            if row is None:
                return False
            attempts = int(row["attempts"] or 0) + 1
            if attempts >= self.max_attempts:
                cur = self._conn.execute(
                    "UPDATE tasks SET status='failed', attempts=?, last_error=?, "
                    "lease_owner='', recovery_reason=? WHERE " + where,
                    (attempts, error_text, error_text, *identity))
                return cur.rowcount == 1
            # 指数退避：2^attempts 秒（首次失败 2s，二次 4s...）
            backoff = 2 ** attempts
            cur = self._conn.execute(
                "UPDATE tasks SET status='pending', attempts=?, last_error=?, "
                "scheduled_at=?, locked_at=0, lease_owner='', recovery_reason=? WHERE " + where,
                (attempts, error_text, time.time() + backoff, error_text, *identity))
            return cur.rowcount == 1

    def reap_stale(self, timeout_seconds, reason="heartbeat timeout"):
        """Recover stale running leases through bounded retry, never leave them running."""
        cutoff = time.time() - max(0, float(timeout_seconds))
        with _LOCK, self._conn:
            rows = self._conn.execute(
                "SELECT id, run_id, worker_id, lease_owner FROM tasks "
                "WHERE status='running' AND last_heartbeat_at < ? AND COALESCE(run_id, '') <> ''",
                (cutoff,)).fetchall()
        recovered = []
        for row in rows:
            if self._fail_attempt(
                row["id"], reason, run_id=row["run_id"], worker_id=row["worker_id"],
                lease_owner=row["lease_owner"], stale_before=cutoff):
                recovered.append(row["id"])
        return recovered

    def close(self):
        """关闭数据库连接（测试/清理用）。"""
        try:
            self._conn.close()
        except Exception:
            pass

    def stats(self):
        """各状态计数 + 汇总（Observatory/监控消费）。"""
        with _LOCK, self._conn:
            rows = self._conn.execute(
                "SELECT status, COUNT(*) AS n FROM tasks GROUP BY status").fetchall()
            d = {r["status"]: r["n"] for r in rows}
            d["total"] = sum(d.values())
            return d

    def list_by_status(self, status, limit=50):
        """按状态列出任务（运维/调试）。"""
        with _LOCK, self._conn:
            rows = self._conn.execute(
                "SELECT id, task_type, priority, attempts, status, last_error, run_id, worker_id, lease_owner, started_at, last_heartbeat_at, last_success_at, last_checkpoint_at, checkpoint_id, recovery_reason "
                "FROM tasks WHERE status=? ORDER BY id DESC LIMIT ?",
                (status, limit)).fetchall()
            return [dict(r) for r in rows]
