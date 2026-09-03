# -*- coding: utf-8 -*-
"""极简 SQLite 任务队列（能力提取自 neotask：SQLite 后端 + 优先级 + 零依赖）。

neotask（neopen/neotask, 2026-03）是 Celery 的轻量零依赖替代——SQLite/Redis 后端、
优先级、延时、重试。ZBC 采集已有同步调度 + DLQ 死信重放，此处补齐基线 §10 的
「Scheduler/Queue/Worker」中的 Queue 层：把批量任务（关键词采集、事件分析、报告生成）
入队，Worker 按优先级/时间消费，失败自动退避重试（对齐 baldur/neotask 范式）。

能力：
  - enqueue(task_type, payload, priority, delay)  -> id
  - dequeue()                                      -> 取到期最高优先级任务并标记 running（worker 用）
  - ack(id) / fail(id, error)                      -> 完成确认 / 失败退避重试（attempts 上限转 failed）
  - stats()                                        -> 各状态计数（监控/Observatory 用）
零第三方依赖（纯 sqlite3），数据落盘可恢复（数据零丢失）。
"""
import json
import os
import sqlite3
import threading
import time

# 默认队列文件（可注入）
DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "data", "task_queue.db")

_LOCK = threading.Lock()


class TaskQueue:
    def __init__(self, path=None, max_attempts=3):
        self.path = path or DEFAULT_PATH
        self.max_attempts = max_attempts
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
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
                    locked_at REAL DEFAULT 0
                )""")
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

    def dequeue(self):
        """取到期最高优先级任务并标记 running（原子，防多 worker 重复取）。
        无到期任务返回 None。"""
        with _LOCK, self._conn:
            row = self._conn.execute(
                "SELECT * FROM tasks WHERE status='pending' AND scheduled_at <= ? "
                "ORDER BY priority ASC, scheduled_at ASC, id ASC LIMIT 1",
                (time.time(),)).fetchone()
            if row is None:
                return None
            self._conn.execute(
                "UPDATE tasks SET status='running', locked_at=? WHERE id=?",
                (time.time(), row["id"]))
            d = dict(row)
            try:
                d["payload"] = json.loads(d["payload"])
            except (json.JSONDecodeError, TypeError):
                pass
            return d

    def ack(self, task_id):
        """确认完成 -> done。"""
        with _LOCK, self._conn:
            self._conn.execute("UPDATE tasks SET status='done' WHERE id=?", (task_id,))

    def fail(self, task_id, error=""):
        """失败 -> attempts+1；未达上限回 pending 并指数退避重排（下次更晚），否则 failed。"""
        with _LOCK, self._conn:
            row = self._conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                return
            attempts = row["attempts"] + 1
            if attempts >= self.max_attempts:
                self._conn.execute(
                    "UPDATE tasks SET status='failed', attempts=?, last_error=? WHERE id=?",
                    (attempts, (error or "")[:500], task_id))
                return
            # 指数退避：2^attempts 秒（首次失败 2s，二次 4s...）
            backoff = 2 ** attempts
            self._conn.execute(
                "UPDATE tasks SET status='pending', attempts=?, last_error=?, "
                "scheduled_at=?, locked_at=0 WHERE id=?",
                (attempts, (error or "")[:500], time.time() + backoff, task_id))

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
                "SELECT id, task_type, priority, attempts, status, last_error "
                "FROM tasks WHERE status=? ORDER BY id DESC LIMIT ?",
                (status, limit)).fetchall()
            return [dict(r) for r in rows]
