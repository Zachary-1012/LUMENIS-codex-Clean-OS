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
from contextlib import contextmanager
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

    def enqueue_once(self, task_type, payload, request_key):
        """Atomically recover one server-bound request without a second task store."""
        if not isinstance(task_type, str) or not task_type or type(payload) is not dict:
            raise ValueError("TASK_QUEUE_REQUEST_INVALID")
        if not isinstance(request_key, str) or not request_key:
            raise ValueError("TASK_QUEUE_REQUEST_KEY_INVALID")
        if "request_key" in payload and payload["request_key"] != request_key:
            raise ValueError("TASK_QUEUE_REQUEST_KEY_MISMATCH")
        now = time.time()
        with _LOCK, self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                "SELECT id,payload FROM tasks WHERE task_type=? AND json_extract(payload, '$.request_key')=? "
                "ORDER BY id LIMIT 1", (task_type, request_key)).fetchone()
            if row is not None:
                existing_payload = json.loads(row["payload"])
                for field in ("request_id", "request_digest", "binding", "parent_version_sha256"):
                    if field in payload and existing_payload.get(field) != payload[field]:
                        raise ValueError("TASK_QUEUE_REQUEST_ID_CONFLICT")
                return row['id']
            material = {**payload, 'request_key': request_key}
            return self._conn.execute(
                "INSERT INTO tasks(task_type,payload,priority,status,created_at,scheduled_at) "
                "VALUES(?,?,5,'pending',?,?)",
                (task_type, json.dumps(material, ensure_ascii=False, sort_keys=True, allow_nan=False), now, now)).lastrowid

    def dequeue(self, worker_id="", lease_owner="", *, task_id=None):
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
            target = " AND id=?" if task_id is not None else ""
            params = (time.time(), task_id) if task_id is not None else (time.time(),)
            row = self._conn.execute(
                "SELECT * FROM tasks WHERE status='pending' AND scheduled_at <= ? " + target +
                " ORDER BY priority ASC, scheduled_at ASC, id ASC LIMIT 1", params).fetchone()
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

    def fail(self, task_id, error="", *, run_id=None, worker_id=None, lease_owner=None, retryable=True):
        """Fail only the active attempt; return False for a stale receipt."""
        return self._fail_attempt(
            task_id, error, run_id=run_id, worker_id=worker_id,
            lease_owner=lease_owner, retryable=retryable)

    def _fail_attempt(self, task_id, error, *, run_id, worker_id, lease_owner,
                      stale_before=None, retryable=True):
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
            if retryable is False or attempts >= self.max_attempts:
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

    def reap_stale(self, timeout_seconds, reason="heartbeat timeout", *, task_id=None):
        """Recover stale running leases through bounded retry, never leave them running."""
        cutoff = time.time() - max(0, float(timeout_seconds))
        with _LOCK, self._conn:
            rows = self._conn.execute(
                "SELECT id, run_id, worker_id, lease_owner FROM tasks "
                "WHERE status='running' AND last_heartbeat_at < ? AND COALESCE(run_id, '') <> ''"
                + (" AND id=?" if task_id is not None else ""),
                (cutoff, task_id) if task_id is not None else (cutoff,)).fetchall()
        recovered = []
        for row in rows:
            if self._fail_attempt(
                row["id"], reason, run_id=row["run_id"], worker_id=row["worker_id"],
                lease_owner=row["lease_owner"], stale_before=cutoff):
                recovered.append(row["id"])
        return recovered

    def defer(self, task_id, *, run_id=None, worker_id=None, lease_owner=None, delay_seconds=0):
        """Yield a valid continuation/local-throttle boundary without failure."""
        if type(delay_seconds) not in (int, float) or not 0 <= delay_seconds <= 3600:
            raise ValueError("invalid queue deferral delay")
        if not self._has_attempt_receipt(run_id, worker_id, lease_owner):
            return False
        with _LOCK, self._conn:
            cur = self._conn.execute(
                "UPDATE tasks SET status='pending', scheduled_at=?, locked_at=0, lease_owner='' "
                "WHERE id=? AND status='running' AND run_id=? AND worker_id=? AND lease_owner=?",
                (time.time() + delay_seconds, task_id, run_id, worker_id, lease_owner))
            return cur.rowcount == 1

    def resume_expired(self, task_id, deadline_at):
        """Server-authorized new window for the same expired task and operation IDs."""
        if type(deadline_at) not in (int, float) or not time.time() < deadline_at <= time.time() + 3600:
            raise ValueError("invalid resumed task deadline")
        with _LOCK, self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                "SELECT payload FROM tasks WHERE id=? AND status='failed' AND last_error='TASK_DEADLINE_EXCEEDED'",
                (task_id,)).fetchone()
            if row is None:
                return False
            payload = json.loads(row["payload"])
            if payload.get("cancel_requested") is True:
                return False
            payload["deadline_at"] = deadline_at
            self._conn.execute(
                "UPDATE tasks SET payload=?,status='pending',scheduled_at=?,attempts=0,locked_at=0,"
                "lease_owner='',last_error='',recovery_reason='EXPLICIT_DEADLINE_CONTINUATION' WHERE id=?",
                (json.dumps(payload, ensure_ascii=False), time.time(), task_id))
            return True

    @contextmanager
    def attempt_guard(self, task_id, *, run_id=None, worker_id=None, lease_owner=None):
        """Fence a short business commit against concurrent lease reclamation.

        Enter only at the existing business transaction, never around network
        acquisition. Keep the queue write reservation until that transaction
        commits or rolls back, so a stale attempt cannot publish business truth.
        """
        if not self._has_attempt_receipt(run_id, worker_id, lease_owner):
            yield False
            return
        with _LOCK:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                row = self._conn.execute(
                    "SELECT id,payload FROM tasks WHERE id=? AND status='running' AND run_id=? "
                    "AND worker_id=? AND lease_owner=?",
                    (task_id, run_id, worker_id, lease_owner)).fetchone()
                payload = json.loads(row["payload"]) if row is not None else {}
                deadline = payload.get("deadline_at")
                valid_deadline = deadline is None or (type(deadline) in (int, float) and time.time() < deadline)
                yield row is not None and valid_deadline and payload.get("cancel_requested") is not True
            finally:
                # This context is a reservation only: no operational writes
                # after the inner business DB has committed. Releasing the
                # reservation must not turn committed Evidence into false zero
                # or cause its already-referenced files to be cleaned up.
                try:
                    self._conn.rollback()
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception("Queue reservation release failed; business outcome unchanged")


    def get(self, task_id):
        """Read durable operational state, including its existing JSON payload."""
        with _LOCK, self._conn:
            row = self._conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["payload"] = json.loads(result["payload"])
            return result

    def save_progress(self, task_id, progress, *, run_id=None, worker_id=None, lease_owner=None):
        """Checkpoint operational result references in the existing payload column.

        This is not business/Evidence storage. The same attempt fence guards
        this update as ack/fail; immutable request fields remain untouched.
        """
        if not self._has_attempt_receipt(run_id, worker_id, lease_owner):
            return False
        with _LOCK, self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                "SELECT payload FROM tasks WHERE id=? AND status='running' AND run_id=? "
                "AND worker_id=? AND lease_owner=?",
                (task_id, run_id, worker_id, lease_owner)).fetchone()
            if row is None:
                return False
            payload = json.loads(row["payload"])
            payload["progress"] = progress
            self._conn.execute(
                "UPDATE tasks SET payload=?, last_checkpoint_at=? WHERE id=?",
                (json.dumps(payload, ensure_ascii=False), time.time(), task_id))
            return True

    def request_cancel(self, task_id, *, task_type, request_key, reason="user_cancelled"):
        """Request cancellation for one owner-bound generic operation.

        The business route must authorize the actor/scope before calling this
        method. The queue additionally binds the mutation to the exact task
        type and immutable request key. Running work stays leased in
        ``cancel_requested`` until its worker confirms cancellation; pending
        work becomes terminal immediately. A completed result always wins.
        """
        if (type(task_id) is not int or task_id <= 0
                or not isinstance(task_type, str) or not task_type
                or not isinstance(request_key, str) or not request_key):
            return None
        reason = str(reason or "user_cancelled")[:500]
        with _LOCK, self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                "SELECT * FROM tasks WHERE id=? AND task_type=? "
                "AND json_extract(payload,'$.request_key')=?",
                (task_id, task_type, request_key),
            ).fetchone()
            if row is None:
                return None
            payload = json.loads(row["payload"])
            status = row["status"]
            if status == "pending":
                payload["cancel_requested"] = True
                self._conn.execute(
                    "UPDATE tasks SET payload=?,status='cancelled',last_error=?,"
                    "recovery_reason='USER_CANCELLED',lease_owner='' "
                    "WHERE id=? AND status='pending'",
                    (json.dumps(payload, ensure_ascii=False, sort_keys=True), reason, task_id),
                )
            elif status == "running":
                payload["cancel_requested"] = True
                self._conn.execute(
                    "UPDATE tasks SET payload=?,status='cancel_requested',last_error=? "
                    "WHERE id=? AND status='running' AND run_id=? AND worker_id=? AND lease_owner=?",
                    (json.dumps(payload, ensure_ascii=False, sort_keys=True), reason,
                     task_id, row["run_id"], row["worker_id"], row["lease_owner"]),
                )
            # Repeated cancellation is idempotent. Terminal success/failure
            # remains authoritative and is never overwritten.
            current = self._conn.execute(
                "SELECT * FROM tasks WHERE id=?", (task_id,)
            ).fetchone()
            self._conn.commit()
            result = dict(current)
            result["payload"] = json.loads(result["payload"])
            return result

    def finish_cancelled(self, task_id, *, task_type, request_key, reason="user_cancelled",
                         run_id=None, worker_id=None, lease_owner=None):
        """Confirm cancellation from the current leased worker only."""
        if (not self._has_attempt_receipt(run_id, worker_id, lease_owner)
                or not isinstance(task_type, str) or not task_type
                or not isinstance(request_key, str) or not request_key):
            return False
        reason = str(reason or "user_cancelled")[:500]
        with _LOCK, self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                "SELECT payload FROM tasks WHERE id=? AND task_type=? "
                "AND status='cancel_requested' AND run_id=? AND worker_id=? AND lease_owner=? "
                "AND json_extract(payload,'$.request_key')=?",
                (task_id, task_type, run_id, worker_id, lease_owner, request_key),
            ).fetchone()
            if row is None:
                return False
            payload = json.loads(row["payload"])
            if payload.get("cancel_requested") is not True:
                return False
            cursor = self._conn.execute(
                "UPDATE tasks SET status='cancelled',last_error=?,recovery_reason='USER_CANCELLED',"
                "lease_owner='' WHERE id=? AND task_type=? AND status='cancel_requested' "
                "AND run_id=? AND worker_id=? AND lease_owner=? "
                "AND json_extract(payload,'$.request_key')=?",
                (reason, task_id, task_type, run_id, worker_id, lease_owner, request_key),
            )
            return cursor.rowcount == 1

    def commit_result(self, task_id, result_ref=None, commit_effect=None, *, task_type, request_key,
                      run_id=None, worker_id=None, lease_owner=None):
        """Commit the existing business result under the active queue lease.

        ``commit_effect`` performs the final owner-side Artifact registration
        and readback, and returns its small result-reference DTO. The compact
        two-argument form ``commit_result(task_id, commit_effect, ...)`` is
        preferred when the Artifact reference is known only after registration;
        callers may provide a precomputed ``result_ref`` as the second argument
        when it is already fixed. The queue write reservation serializes the
        owner commit with cancellation, then stores the result reference and
        marks the durable operation done in the same queue transaction. If the
        process exits after the Artifact owner commits but before this queue
        transaction commits, the caller must reconcile by the immutable task
        id and return the already-registered Artifact on explicit recovery.
        """
        if callable(result_ref) and commit_effect is None:
            commit_effect, result_ref = result_ref, None
        if (not self._has_attempt_receipt(run_id, worker_id, lease_owner)
                or not isinstance(task_type, str) or not task_type
                or not isinstance(request_key, str) or not request_key
                or result_ref is not None and type(result_ref) is not dict
                or not callable(commit_effect)):
            return False

        def encode_result(value):
            if type(value) is not dict:
                raise ValueError("TASK_RESULT_REFERENCE_INVALID")
            try:
                encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     allow_nan=False, separators=(",", ":"))
            except (TypeError, ValueError) as exc:
                raise ValueError("TASK_RESULT_REFERENCE_INVALID") from exc
            if len(encoded.encode("utf-8")) > 16 * 1024:
                raise ValueError("TASK_RESULT_REFERENCE_TOO_LARGE")
            return encoded

        encoded_result = encode_result(result_ref) if result_ref is not None else None

        with _LOCK, self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                "SELECT payload FROM tasks WHERE id=? AND task_type=? AND status='running' "
                "AND run_id=? AND worker_id=? AND lease_owner=? "
                "AND json_extract(payload,'$.request_key')=?",
                (task_id, task_type, run_id, worker_id, lease_owner, request_key),
            ).fetchone()
            if row is None:
                return False
            payload = json.loads(row["payload"])
            if payload.get("cancel_requested") is True:
                return False
            deadline = payload.get("deadline_at")
            if deadline is not None and (type(deadline) not in (int, float) or time.time() >= deadline):
                return False

            effect_result = commit_effect()
            if effect_result is False:
                return False

            if encoded_result is None:
                encoded_result = encode_result(effect_result)

            payload["result"] = json.loads(encoded_result)
            cursor = self._conn.execute(
                "UPDATE tasks SET payload=?,status='done',last_success_at=?,lease_owner='',"
                "last_error='',recovery_reason='' WHERE id=? AND task_type=? AND status='running' "
                "AND run_id=? AND worker_id=? AND lease_owner=? "
                "AND json_extract(payload,'$.request_key')=?",
                (json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False),
                 time.time(), task_id, task_type, run_id, worker_id, lease_owner, request_key),
            )
            return cursor.rowcount == 1

    def record_result_metadata(self, task_id, metadata, *, task_type, request_key):
        """Monotonically add owner-authored metadata to an existing task result.

        This is a post-completion operational annotation (for example, whether
        the result's Evidence side-write was recorded). It is deliberately
        fenced to the exact completed task and immutable request identity and
        cannot change task state or the committed result reference.
        """
        if (type(task_id) is not int or task_id <= 0
                or type(metadata) is not dict
                or any(type(key) is not str or not key for key in metadata)
                or not isinstance(task_type, str) or not task_type
                or not isinstance(request_key, str) or not request_key):
            return False
        try:
            encoded_metadata = json.dumps(
                metadata, ensure_ascii=False, sort_keys=True, allow_nan=False,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("TASK_RESULT_METADATA_INVALID") from exc
        if len(encoded_metadata.encode("utf-8")) > 16 * 1024:
            raise ValueError("TASK_RESULT_METADATA_TOO_LARGE")

        with _LOCK, self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                "SELECT payload FROM tasks WHERE id=? AND task_type=? AND status='done' "
                "AND json_extract(payload,'$.request_key')=?",
                (task_id, task_type, request_key),
            ).fetchone()
            if row is None:
                return False
            payload = json.loads(row["payload"])
            result = payload.get("result")
            if type(result) is not dict:
                return False
            current = result.get("metadata", {})
            if type(current) is not dict:
                return False
            for key, value in metadata.items():
                if key in current and current[key] != value:
                    return False
            additions = {key: value for key, value in metadata.items() if key not in current}
            if not additions:
                return True
            current.update(additions)
            result["metadata"] = current
            payload["result"] = result
            encoded_payload = json.dumps(
                payload, ensure_ascii=False, sort_keys=True, allow_nan=False,
            )
            cursor = self._conn.execute(
                "UPDATE tasks SET payload=? WHERE id=? AND task_type=? AND status='done' "
                "AND json_extract(payload,'$.request_key')=?",
                (encoded_payload, task_id, task_type, request_key),
            )
            return cursor.rowcount == 1

    def mark_interrupted_if_dead(self, task_id, *, task_type, request_key,
                                  stale_after_seconds, worker_alive_check):
        """Mark a lost operation interrupted only after lease expiry and a death check.

        Heartbeat age alone is not proof of worker death. The owner supplies a
        check for the exact persisted worker/run identity (for example the
        process and worker thread) and this method revalidates the lease under
        the queue transaction before changing its state.
        """
        if (type(task_id) is not int or task_id <= 0
                or not isinstance(task_type, str) or not task_type
                or not isinstance(request_key, str) or not request_key
                or type(stale_after_seconds) not in (int, float)
                or stale_after_seconds <= 0 or stale_after_seconds > 86400
                or not callable(worker_alive_check)):
            return False
        cutoff = time.time() - float(stale_after_seconds)
        with _LOCK, self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                "SELECT status,payload,run_id,worker_id,lease_owner,last_heartbeat_at FROM tasks "
                "WHERE id=? AND task_type=? AND status IN ('running','cancel_requested') "
                "AND json_extract(payload,'$.request_key')=?",
                (task_id, task_type, request_key),
            ).fetchone()
            if row is None or float(row["last_heartbeat_at"] or 0) >= cutoff:
                return False
            if worker_alive_check(row["worker_id"], row["lease_owner"], row["run_id"]):
                return False
            payload = json.loads(row["payload"])
            cancelled = row["status"] == "cancel_requested" or payload.get("cancel_requested") is True
            state = "cancelled" if cancelled else "interrupted"
            reason = "CANCELLED_AFTER_CONFIRMED_WORKER_EXIT" if cancelled else "WORKER_EXIT_CONFIRMED"
            cursor = self._conn.execute(
                "UPDATE tasks SET status=?,last_error=?,recovery_reason=?,lease_owner='' "
                "WHERE id=? AND task_type=? AND status=? AND run_id=? AND worker_id=? AND lease_owner=? "
                "AND last_heartbeat_at < ? AND json_extract(payload,'$.request_key')=?",
                (state, reason, reason, task_id, task_type, row["status"], row["run_id"],
                 row["worker_id"], row["lease_owner"], cutoff, request_key),
            )
            return cursor.rowcount == 1

    def resume_interrupted(self, task_id, *, task_type, request_key):
        """Explicitly make one confirmed interrupted task claimable again."""
        if (type(task_id) is not int or task_id <= 0
                or not isinstance(task_type, str) or not task_type
                or not isinstance(request_key, str) or not request_key):
            return False
        with _LOCK, self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                "SELECT payload FROM tasks WHERE id=? AND task_type=? AND status='interrupted' "
                "AND json_extract(payload,'$.request_key')=?",
                (task_id, task_type, request_key),
            ).fetchone()
            if row is None:
                return False
            payload = json.loads(row["payload"])
            if payload.get("cancel_requested") is True:
                return False
            payload["resume_count"] = int(payload.get("resume_count", 0)) + 1
            cursor = self._conn.execute(
                "UPDATE tasks SET payload=?,status='pending',scheduled_at=?,locked_at=0,"
                "run_id='',worker_id='',lease_owner='',last_error='',"
                "recovery_reason='EXPLICIT_USER_RESUME' WHERE id=? AND task_type=? "
                "AND status='interrupted' AND json_extract(payload,'$.request_key')=?",
                (json.dumps(payload, ensure_ascii=False, sort_keys=True), time.time(),
                 task_id, task_type, request_key),
            )
            return cursor.rowcount == 1

    def close(self):
        """关闭数据库连接（测试/清理用）。"""
        try:
            self._conn.close()
        except Exception:
            pass

    def yield_pending(self, task_id, *, run_id=None, worker_id=None, lease_owner=None, delay=0):
        """Release one page/chunk without consuming the transport retry budget."""
        if not self._has_attempt_receipt(run_id, worker_id, lease_owner):
            return False
        with _LOCK, self._conn:
            current = self._conn.execute('SELECT payload FROM tasks WHERE id=? AND status=\'running\' '
                'AND run_id=? AND worker_id=? AND lease_owner=?',
                (task_id, run_id, worker_id, lease_owner)).fetchone()
            if current is None or json.loads(current['payload']).get('cancel_requested') is True:
                return False
            self._conn.execute('UPDATE tasks SET status=\'pending\',scheduled_at=?,locked_at=0,lease_owner=\'\' '
                'WHERE id=? AND run_id=? AND worker_id=? AND lease_owner=?',
                (time.time() + max(0, float(delay)), task_id, run_id, worker_id, lease_owner))
            return True

    def set_manual_request_cancelled(self, task_id, request_key, *, cancelled):
        """Operational transition after the Collector revalidates its exact owner.

        Cancellation invalidates the attempt before a subsequent business commit.
        A commit already published is recovered from its signed Source receipt.
        """
        if type(cancelled) is not bool or not isinstance(request_key, str) or not request_key:
            return False
        with _LOCK, self._conn:
            self._conn.execute('BEGIN IMMEDIATE')
            row = self._conn.execute("SELECT * FROM tasks WHERE id=? AND task_type=? AND json_extract(payload,'$.request_key')=?",
                (task_id, 'collector_manual_request', request_key)).fetchone()
            if row is None or row['status'] == 'done':
                return False
            payload = json.loads(row['payload'])
            if (cancelled is False and payload.get('cancel_requested') is not True
                    and row['status'] != 'failed'):
                return False
            payload['cancel_requested'] = cancelled
            scheduled_at = max(time.time(), float(row['scheduled_at'] or 0))
            attempts = row['attempts'] if cancelled else 0
            self._conn.execute('UPDATE tasks SET payload=?,status=\'pending\',scheduled_at=?,run_id=\'\','
                'worker_id=\'\',lease_owner=\'\',locked_at=0,last_error=?,attempts=? WHERE id=?',
                (json.dumps(payload, ensure_ascii=False), scheduled_at,
                 'CANCELLED' if cancelled else '', attempts, task_id))
            return True

    def stats(self):
        """各状态计数 + 汇总（Observatory/监控消费）。"""
        with _LOCK, self._conn:
            rows = self._conn.execute(
                "SELECT status, COUNT(*) AS n FROM tasks GROUP BY status").fetchall()
            d = {r["status"]: r["n"] for r in rows}
            d["total"] = sum(d.values())
            return d

    def list_manual_requests(self, identity, scope, *, before=None, limit=20):
        if (set(identity) not in ({'actor_id'}, {'principal_ref'})
                or type(limit) is not int or not 1 <= limit <= 100
                or before is not None and (type(before) is not int or before <= 0)):
            raise ValueError('COLLECTION_HISTORY_REQUEST_INVALID')
        fields = {f'identity.{key}': value for key, value in identity.items()}
        fields.update({f'scope.{key}': scope.get(key) for key in
                       ('domain_id', 'global_scope', 'subject_id', 'brand_focus_id')})
        clauses = ['task_type=?']
        parameters = ['collector_manual_request']
        for key, value in fields.items():
            clauses.append('json_extract(payload, ?) IS ?')
            parameters.extend(['$.binding.' + key, value])
        if before is not None:
            clauses.append('id<?')
            parameters.append(before)
        with _LOCK:
            rows = self._conn.execute('SELECT * FROM tasks WHERE ' + ' AND '.join(clauses)
                + ' ORDER BY id DESC LIMIT ?', [*parameters, limit + 1]).fetchall()
        result = []
        for row in rows[:limit]:
            item = dict(row)
            item['payload'] = json.loads(item['payload'])
            result.append(item)
        return result, result[-1]['id'] if len(rows) > limit else None

    def list_by_status(self, status, limit=50):
        """按状态列出任务（运维/调试）。"""
        with _LOCK, self._conn:
            rows = self._conn.execute(
                "SELECT id, task_type, priority, attempts, status, last_error, run_id, worker_id, lease_owner, started_at, last_heartbeat_at, last_success_at, last_checkpoint_at, checkpoint_id, recovery_reason "
                "FROM tasks WHERE status=? ORDER BY id DESC LIMIT ?",
                (status, limit)).fetchall()
            return [dict(r) for r in rows]

    def list_by_type(self, task_type, *, before_id=None, limit=20,
                     actor_ref=None, scope_sha256=None):
        """List one task type in reverse creation order with optional binding filters.

        Actor/scope predicates run in SQL before pagination so tasks belonging
        to other bindings cannot crowd a caller's page. Returned payloads are
        decoded using the existing task row contract.
        """
        if (not isinstance(task_type, str) or not task_type
                or type(limit) is not int or not 1 <= limit <= 50
                or before_id is not None and (type(before_id) is not int or before_id <= 0)
                or actor_ref is not None and (not isinstance(actor_ref, str) or not actor_ref)
                or scope_sha256 is not None and (not isinstance(scope_sha256, str) or not scope_sha256)):
            raise ValueError("TASK_QUEUE_LIST_REQUEST_INVALID")
        clauses = ["task_type=?"]
        parameters = [task_type]
        if before_id is not None:
            clauses.append("id<?")
            parameters.append(before_id)
        if actor_ref is not None:
            clauses.append("json_extract(payload,'$.binding.actor_ref')=?")
            parameters.append(actor_ref)
        if scope_sha256 is not None:
            clauses.append("json_extract(payload,'$.binding.scope_sha256')=?")
            parameters.append(scope_sha256)
        with _LOCK, self._conn:
            rows = self._conn.execute(
                "SELECT * FROM tasks WHERE " + " AND ".join(clauses)
                + " ORDER BY id DESC LIMIT ?",
                (*parameters, limit + 1),
            ).fetchall()
        result = []
        for row in rows[:limit]:
            item = dict(row)
            item["payload"] = json.loads(item["payload"])
            result.append(item)
        next_before_id = result[-1]["id"] if len(rows) > limit else None
        return result, next_before_id
