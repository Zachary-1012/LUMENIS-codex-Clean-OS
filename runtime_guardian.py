# -*- coding: utf-8 -*-
"""
ZBC Runtime Guardian — 统一运行时生命周期守护
=================================================
工单：ZBC-PHASE2-RUNTIME-GUARDIAN-001
对齐：AGENTS.md §3 AI运行时 / §13 修改安全协议 / §17 最终原则

将分散的稳定性模块（system_guardian / stability_monitor / system_watchdog /
auto_recovery / resident_health / runtime_preflight / monitor_pipeline /
tunnel_guardian / collector_guard）统一收敛到 Runtime Guardian，建立完整生命周期：

    Worker → Lease → Heartbeat → Checkpoint → Reaper → Retry → DLQ → Resume

核心硬红线（不因任何模型/配置选择而改变）：
  1. 禁止无限自动重启：RetryLimit(默认3) + Cooldown(指数退避) + CircuitBreaker(5次失败熔断300s) + DLQ
  2. 系统生命线不绑定任何单一组件；任一组件不可用时自动降级，主链路不中断
  3. 所有状态持久化到 SQLite（data/monitor.db），新建表用 CREATE TABLE IF NOT EXISTS，向后兼容
  4. 不修改 collector 主链路、SUBJECT_WORDS / subject_hit()、不写 Secret 到源码

现有模块适配策略：不删除，改为薄包装或标记 Legacy，内部委托给 RuntimeGuardian，保持 import 兼容。
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 允许通过环境变量覆盖 DB 路径（测试隔离 / Staging），未设置时默认生产库
DB_PATH = os.path.abspath(
    os.environ.get("ZBC_RUNTIME_GUARDIAN_DB")
    or os.environ.get("ZBC_DB_PATH")
    or os.path.join(_BASE_DIR, "data", "monitor.db")
)

# 默认策略常量
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 2.0       # 秒
DEFAULT_BACKOFF_MAX = 60.0       # 秒
DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 5   # 连续失败次数
DEFAULT_CIRCUIT_BREAKER_RESET_TIMEOUT = 300  # 秒（熔断后冷却）
DEFAULT_LEASE_TTL = 60            # 秒
DEFAULT_HEARTBEAT_INTERVAL = 10   # 秒
DEFAULT_HEARTBEAT_MISSED_THRESHOLD = 3   # 连续错过次数
DEFAULT_REAPER_INTERVAL = 30      # 秒

_module_lock = threading.RLock()
_instances: Dict[str, "RuntimeGuardian"] = {}


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _now_ts() -> float:
    return time.time()


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------
class CircuitState(Enum):
    """熔断器状态：CLOSED(正常) → OPEN(熔断) → HALF_OPEN(半开试探)"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class WorkerStatus(Enum):
    """Worker 运行状态"""
    RUNNING = "running"
    IDLE = "idle"
    FAILED = "failed"
    RECOVERING = "recovering"
    DEAD = "dead"
    STOPPED = "stopped"


class DLQStatus(Enum):
    """死信队列条目状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    DEAD = "dead"
    ARCHIVED = "archived"


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------
@dataclass
class WorkerLease:
    """租约：确保同一 worker 同一时刻只有一个持有者在执行"""
    lease_owner: str
    acquired_at: float
    expires_at: float
    renewed_at: float = 0.0

    def is_expired(self, now: Optional[float] = None) -> bool:
        return (now or _now_ts()) >= self.expires_at

    def remaining_seconds(self, now: Optional[float] = None) -> float:
        return max(0.0, self.expires_at - (now or _now_ts()))


@dataclass
class Heartbeat:
    """心跳：worker 存活信号"""
    last_heartbeat_at: float = 0.0
    heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL
    missed_threshold: int = DEFAULT_HEARTBEAT_MISSED_THRESHOLD
    missed_count: int = 0

    def beat(self) -> None:
        self.last_heartbeat_at = _now_ts()
        self.missed_count = 0

    def is_timed_out(self, now: Optional[float] = None) -> bool:
        if self.last_heartbeat_at == 0:
            return False
        elapsed = (now or _now_ts()) - self.last_heartbeat_at
        return elapsed > self.heartbeat_interval * self.missed_threshold


@dataclass
class Checkpoint:
    """检查点：可恢复的执行位置"""
    checkpoint_id: str
    run_id: str
    position: str = ""
    state: str = "active"
    created_at: float = field(default_factory=_now_ts)
    updated_at: float = field(default_factory=_now_ts)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryPolicy:
    """重试策略：限制重试次数 + 指数退避 + 熔断器阈值"""
    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_base: float = DEFAULT_BACKOFF_BASE
    backoff_max: float = DEFAULT_BACKOFF_MAX
    circuit_breaker_threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD

    def backoff_seconds(self, attempt: int) -> float:
        """第 attempt 次重试前的等待秒数（指数退避，封顶）"""
        if attempt <= 0:
            return 0.0
        return min(self.backoff_base ** attempt, self.backoff_max)

    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_retries


# ---------------------------------------------------------------------------
# CircuitBreaker 熔断器
# ---------------------------------------------------------------------------
class CircuitBreaker:
    """
    熔断器：CLOSED → OPEN → HALF_OPEN 状态转换。

    - CLOSED：正常放行，连续失败达 threshold 后 → OPEN
    - OPEN：直接拒绝请求，reset_timeout 秒后 → HALF_OPEN
    - HALF_OPEN：放行一次试探请求，成功 → CLOSED，失败 → OPEN
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
        reset_timeout: float = DEFAULT_CIRCUIT_BREAKER_RESET_TIMEOUT,
        now_func = None,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._now = now_func or _now_ts
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at: float = 0.0
        self._last_failure_at: float = 0.0
        self._last_success_at: float = 0.0
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._maybe_half_open()
            return self._state

    def _maybe_half_open(self) -> None:
        """OPEN 状态超过 reset_timeout 后自动转 HALF_OPEN"""
        if self._state == CircuitState.OPEN:
            if self._now() - self._opened_at >= self.reset_timeout:
                self._state = CircuitState.HALF_OPEN

    def allow_request(self) -> bool:
        """是否允许请求通过"""
        with self._lock:
            self._maybe_half_open()
            if self._state == CircuitState.OPEN:
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            self._success_count += 1
            self._last_success_at = self._now()
            self._failure_count = 0
            if self._state in (CircuitState.OPEN, CircuitState.HALF_OPEN):
                self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_at = self._now()
            if self._state == CircuitState.HALF_OPEN:
                # 半开试探失败 → 重新熔断
                self._state = CircuitState.OPEN
                self._opened_at = self._now()
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = self._now()

    def reset(self) -> None:
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._opened_at = 0.0

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            self._maybe_half_open()
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "failure_threshold": self.failure_threshold,
                "reset_timeout": self.reset_timeout,
                "opened_at": self._opened_at,
                "last_failure_at": self._last_failure_at,
                "last_success_at": self._last_success_at,
            }

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """受熔断器保护的执行：熔断时直接抛 RuntimeError，不调用 func"""
        if not self.allow_request():
            raise RuntimeError(
                f"CircuitBreaker '{self.name}' is OPEN (failures={self._failure_count}, "
                f"threshold={self.failure_threshold})"
            )
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise


# ---------------------------------------------------------------------------
# 数据库层
# ---------------------------------------------------------------------------
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runtime_guardian_workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id TEXT UNIQUE NOT NULL,
    worker_name TEXT DEFAULT '',
    domain_id TEXT DEFAULT 'system',
    product_id TEXT DEFAULT 'SYSTEM',
    status TEXT DEFAULT 'idle',
    lease_owner TEXT DEFAULT '',
    run_id TEXT DEFAULT '',
    checkpoint_id TEXT DEFAULT '',
    last_success_at TEXT DEFAULT '',
    last_heartbeat_at TEXT DEFAULT '',
    last_checkpoint_at TEXT DEFAULT '',
    failure_count INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    recovery_reason TEXT DEFAULT '',
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS runtime_guardian_checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checkpoint_id TEXT UNIQUE NOT NULL,
    run_id TEXT DEFAULT '',
    worker_id TEXT DEFAULT '',
    position TEXT DEFAULT '',
    state TEXT DEFAULT 'active',
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS runtime_guardian_dlq (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dlq_id TEXT UNIQUE NOT NULL,
    worker_id TEXT DEFAULT '',
    run_id TEXT DEFAULT '',
    domain_id TEXT DEFAULT 'system',
    product_id TEXT DEFAULT 'SYSTEM',
    task_type TEXT DEFAULT '',
    payload TEXT DEFAULT '{}',
    error TEXT DEFAULT '',
    error_type TEXT DEFAULT '',
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime')),
    last_attempt_at TEXT DEFAULT '',
    resolved_at TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_rg_workers_status ON runtime_guardian_workers(status);
CREATE INDEX IF NOT EXISTS idx_rg_workers_lease ON runtime_guardian_workers(lease_owner);
CREATE INDEX IF NOT EXISTS idx_rg_checkpoints_run ON runtime_guardian_checkpoints(run_id);
CREATE INDEX IF NOT EXISTS idx_rg_dlq_status ON runtime_guardian_dlq(status);
CREATE INDEX IF NOT EXISTS idx_rg_dlq_worker ON runtime_guardian_dlq(worker_id);
"""


def _get_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    """获取数据库连接（每次新建，线程安全）"""
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """初始化数据库表（向后兼容：CREATE TABLE IF NOT EXISTS）"""
    with _get_db(db_path) as conn:
        conn.executescript(_SCHEMA_SQL)
        # 双域核心迁移：添加 domain_id / product_id 列（幂等）
        for tbl in ('runtime_guardian_workers', 'runtime_guardian_dlq'):
            try:
                cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()]
                if 'domain_id' not in cols:
                    conn.execute(f"ALTER TABLE {tbl} ADD COLUMN domain_id TEXT DEFAULT 'system'")
                if 'product_id' not in cols:
                    conn.execute(f"ALTER TABLE {tbl} ADD COLUMN product_id TEXT DEFAULT 'SYSTEM'")
            except Exception as _mig_err:
                print(f"[runtime_guardian] {tbl} domain migration skipped: {_mig_err}")


# ---------------------------------------------------------------------------
# DLQ 死信队列
# ---------------------------------------------------------------------------
class DLQ:
    """
    死信队列：存储超过重试上限的失败任务，持久化到 SQLite。

    入队条件：重试次数达 max_retries 后仍失败 → 入 DLQ（不再自动重启）。
    出队/重放：由 ResumeManager 或人工触发，成功后标记 done。
    """

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or DB_PATH
        init_db(self._db_path)

    def _conn(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        conn = sqlite3.connect(self._db_path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def enqueue(
        self,
        *,
        worker_id: str = "",
        run_id: str = "",
        domain_id: str = "system",
        product_id: str = "SYSTEM",
        task_type: str = "",
        payload: Optional[Dict[str, Any]] = None,
        error: str = "",
        error_type: str = "",
        max_attempts: int = DEFAULT_MAX_RETRIES,
    ) -> str:
        """入队一条死信，返回 dlq_id。双域核心：必须携带 domain_id/product_id。"""
        dlq_id = uuid.uuid4().hex[:16]
        now = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO runtime_guardian_dlq
                   (dlq_id, worker_id, run_id, domain_id, product_id, task_type, payload, error, error_type,
                    attempts, max_attempts, status, created_at, updated_at, last_attempt_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    dlq_id, worker_id, run_id, domain_id, product_id, task_type,
                    json.dumps(payload or {}, ensure_ascii=False),
                    error, error_type, 0, max_attempts,
                    DLQStatus.PENDING.value, now, now, now,
                ),
            )
        return dlq_id

    def list_pending(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM runtime_guardian_dlq WHERE status = ? ORDER BY created_at ASC LIMIT ?",
                (DLQStatus.PENDING.value, limit),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get(self, dlq_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM runtime_guardian_dlq WHERE dlq_id = ?", (dlq_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def mark_processing(self, dlq_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE runtime_guardian_dlq SET status = ?, updated_at = ? WHERE dlq_id = ? AND status = ?",
                (DLQStatus.PROCESSING.value, _now_iso(), dlq_id, DLQStatus.PENDING.value),
            )
            return cur.rowcount > 0

    def ack(self, dlq_id: str) -> bool:
        """重放成功：标记 done"""
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE runtime_guardian_dlq SET status = ?, resolved_at = ?, updated_at = ? WHERE dlq_id = ?",
                (DLQStatus.DONE.value, _now_iso(), _now_iso(), dlq_id),
            )
            return cur.rowcount > 0

    def fail_retry(self, dlq_id: str, error: str = "", error_type: str = "") -> bool:
        """重放失败：attempts+1，超 max_attempts 标记 dead（不再自动重放）"""
        item = self.get(dlq_id)
        if not item:
            return False
        attempts = item["attempts"] + 1
        max_attempts = item["max_attempts"]
        new_status = DLQStatus.DEAD.value if attempts >= max_attempts else DLQStatus.PENDING.value
        with self._conn() as conn:
            conn.execute(
                """UPDATE runtime_guardian_dlq
                   SET attempts = ?, status = ?, error = ?, error_type = ?,
                       last_attempt_at = ?, updated_at = ?
                   WHERE dlq_id = ?""",
                (attempts, new_status, error, error_type, _now_iso(), _now_iso(), dlq_id),
            )
        return True

    def stats(self) -> Dict[str, int]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM runtime_guardian_dlq GROUP BY status"
            ).fetchall()
        result = {"total": 0}
        for r in rows:
            result[r["status"]] = r["cnt"]
            result["total"] += r["cnt"]
        return result

    def replay(
        self,
        handler: Callable[[Dict[str, Any]], None],
        *,
        max_items: int = 50,
    ) -> Tuple[int, int]:
        """
        重放 pending 任务：对每条调用 handler(payload_dict)。
        成功 → ack，失败 → fail_retry。返回 (ok_count, fail_count)。
        """
        pending = self.list_pending(limit=max_items)
        ok = fail = 0
        for item in pending:
            dlq_id = item["dlq_id"]
            if not self.mark_processing(dlq_id):
                continue
            try:
                handler(item.get("payload") or {})
                self.ack(dlq_id)
                ok += 1
            except Exception as e:
                self.fail_retry(dlq_id, error=str(e), error_type=type(e).__name__)
                fail += 1
        return ok, fail

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        for key in ("payload",):
            if key in d and d[key]:
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d


# ---------------------------------------------------------------------------
# ResumeManager 从 checkpoint 恢复
# ---------------------------------------------------------------------------
class ResumeManager:
    """从检查点恢复执行状态"""

    def __init__(self, guardian: "RuntimeGuardian"):
        self._guardian = guardian

    def save_checkpoint(
        self,
        *,
        run_id: str,
        worker_id: str = "",
        position: str = "",
        state: str = "active",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """保存检查点，返回 checkpoint_id"""
        checkpoint_id = uuid.uuid4().hex[:16]
        now = _now_iso()
        with _get_db(self._guardian._db_path) as conn:
            conn.execute(
                """INSERT INTO runtime_guardian_checkpoints
                   (checkpoint_id, run_id, worker_id, position, state, metadata, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    checkpoint_id, run_id, worker_id, position, state,
                    json.dumps(metadata or {}, ensure_ascii=False), now, now,
                ),
            )
        # 更新 worker 的 last_checkpoint_at / checkpoint_id
        self._guardian._update_worker_fields(
            worker_id,
            last_checkpoint_at=now,
            checkpoint_id=checkpoint_id,
        )
        return checkpoint_id

    def get_latest_checkpoint(self, run_id: str) -> Optional[Dict[str, Any]]:
        with _get_db(self._guardian._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM runtime_guardian_checkpoints WHERE run_id = ? ORDER BY id DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["metadata"] = json.loads(d.get("metadata") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["metadata"] = {}
        return d

    def list_checkpoints(self, run_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with _get_db(self._guardian._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM runtime_guardian_checkpoints WHERE run_id = ? ORDER BY id DESC LIMIT ?",
                (run_id, limit),
            ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["metadata"] = json.loads(d.get("metadata") or "{}")
            except (json.JSONDecodeError, TypeError):
                d["metadata"] = {}
            result.append(d)
        return result

    def resume_from_checkpoint(
        self,
        run_id: str,
        resume_fn: Callable[[Dict[str, Any]], Any],
    ) -> Tuple[bool, Any]:
        """
        从最新检查点恢复：找到 checkpoint → 调用 resume_fn(checkpoint_dict)。
        返回 (是否找到检查点, resume_fn 返回值)。
        """
        cp = self.get_latest_checkpoint(run_id)
        if not cp:
            return False, None
        try:
            result = resume_fn(cp)
            return True, result
        except Exception:
            raise


# ---------------------------------------------------------------------------
# Reaper 回收过期租约和僵死 worker
# ---------------------------------------------------------------------------
class Reaper:
    """回收过期租约和僵死 worker（心跳超时的 worker 标记为 dead 并释放租约）"""

    def __init__(self, guardian: "RuntimeGuardian"):
        self._guardian = guardian

    def reap_expired_leases(self) -> List[str]:
        """回收所有过期租约，返回被回收的 worker_id 列表"""
        now = _now_ts()
        reaped = []
        with _get_db(self._guardian._db_path) as conn:
            rows = conn.execute(
                "SELECT worker_id, lease_owner, metadata FROM runtime_guardian_workers WHERE lease_owner != ''"
            ).fetchall()
            for row in rows:
                meta = {}
                try:
                    meta = json.loads(row["metadata"] or "{}")
                except (json.JSONDecodeError, TypeError):
                    pass
                lease_expires = meta.get("lease_expires_at", 0)
                if lease_expires and now >= lease_expires:
                    conn.execute(
                        "UPDATE runtime_guardian_workers SET lease_owner = '', status = ?, updated_at = ? WHERE worker_id = ?",
                        (WorkerStatus.DEAD.value, _now_iso(), row["worker_id"]),
                    )
                    reaped.append(row["worker_id"])
        return reaped

    def reap_zombie_workers(self, heartbeat_timeout: float = 60.0) -> List[str]:
        """
        回收心跳超时的僵死 worker：last_heartbeat_at 超过 heartbeat_timeout 秒 → 标记 dead。
        返回被回收的 worker_id 列表。
        """
        now = _now_iso()
        cutoff_ts = _now_ts() - heartbeat_timeout
        cutoff_str = datetime.fromtimestamp(cutoff_ts).strftime("%Y-%m-%d %H:%M:%S")
        reaped = []
        with _get_db(self._guardian._db_path) as conn:
            rows = conn.execute(
                """SELECT worker_id FROM runtime_guardian_workers
                   WHERE status IN (?, ?) AND last_heartbeat_at != '' AND last_heartbeat_at < ?""",
                (WorkerStatus.RUNNING.value, WorkerStatus.RECOVERING.value, cutoff_str),
            ).fetchall()
            for row in rows:
                conn.execute(
                    "UPDATE runtime_guardian_workers SET status = ?, lease_owner = '', recovery_reason = ?, updated_at = ? WHERE worker_id = ?",
                    (WorkerStatus.DEAD.value, "heartbeat_timeout", now, row["worker_id"]),
                )
                reaped.append(row["worker_id"])
        return reaped

    def run_cycle(self, heartbeat_timeout: float = 60.0) -> Dict[str, List[str]]:
        """执行一次完整回收周期"""
        leases = self.reap_expired_leases()
        zombies = self.reap_zombie_workers(heartbeat_timeout)
        return {"reaped_leases": leases, "reaped_zombies": zombies}


# ---------------------------------------------------------------------------
# RuntimeGuardian 统一生命周期管理
# ---------------------------------------------------------------------------
class RuntimeGuardian:
    """
    统一运行时生命周期守护者。

    生命周期：Worker → Lease → Heartbeat → Checkpoint → Reaper → Retry → DLQ → Resume

    用法：
        guardian = RuntimeGuardian.get_instance("collector")
        worker_id = guardian.register_worker("xhs_collector")
        lease = guardian.acquire_lease(worker_id, owner="node-1")
        guardian.heartbeat(worker_id)
        guardian.save_checkpoint(run_id="run_001", worker_id=worker_id, position="page=3")
        guardian.execute_with_retry(worker_id, task_fn)  # 失败自动重试+熔断+DLQ
    """

    def __init__(self, name: str = "default", db_path: Optional[str] = None):
        self.name = name
        self._db_path = db_path or DB_PATH
        self._lock = threading.RLock()
        self._workers: Dict[str, Dict[str, Any]] = {}
        self._heartbeats: Dict[str, Heartbeat] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._retry_policy = RetryPolicy()
        self._dlq = DLQ(db_path=self._db_path)
        self._resume = ResumeManager(self)
        self._reaper = Reaper(self)
        self._reaper_thread: Optional[threading.Thread] = None
        self._reaper_running = False
        init_db(self._db_path)

    # ------------------------------------------------------------------
    # 单例
    # ------------------------------------------------------------------
    @classmethod
    def get_instance(cls, name: str = "default") -> "RuntimeGuardian":
        with _module_lock:
            if name not in _instances:
                _instances[name] = cls(name=name)
            return _instances[name]

    # ------------------------------------------------------------------
    # Worker 注册与管理
    # ------------------------------------------------------------------
    def register_worker(self, worker_name: str, metadata: Optional[Dict[str, Any]] = None,
                        domain_id: str = "system", product_id: str = "SYSTEM") -> str:
        """注册一个 worker，返回 worker_id。双域核心：必须携带 domain_id/product_id。"""
        worker_id = uuid.uuid4().hex[:16]
        now = _now_iso()
        meta = dict(metadata or {})
        meta.setdefault("domain_id", domain_id)
        meta.setdefault("product_id", product_id)
        with _get_db(self._db_path) as conn:
            conn.execute(
                """INSERT INTO runtime_guardian_workers
                   (worker_id, worker_name, domain_id, product_id, status, metadata, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    worker_id, worker_name, domain_id, product_id, WorkerStatus.IDLE.value,
                    json.dumps(meta, ensure_ascii=False), now, now,
                ),
            )
        with self._lock:
            self._workers[worker_id] = {
                "worker_id": worker_id,
                "worker_name": worker_name,
                "domain_id": domain_id,
                "product_id": product_id,
                "status": WorkerStatus.IDLE.value,
            }
            self._heartbeats[worker_id] = Heartbeat()
        return worker_id

    def get_worker(self, worker_id: str) -> Optional[Dict[str, Any]]:
        with _get_db(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM runtime_guardian_workers WHERE worker_id = ?", (worker_id,)
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["metadata"] = json.loads(d.get("metadata") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["metadata"] = {}
        return d

    def list_workers(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with _get_db(self._db_path) as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM runtime_guardian_workers WHERE status = ? ORDER BY created_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM runtime_guardian_workers ORDER BY created_at DESC"
                ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["metadata"] = json.loads(d.get("metadata") or "{}")
            except (json.JSONDecodeError, TypeError):
                d["metadata"] = {}
            result.append(d)
        return result

    def update_worker_status(self, worker_id: str, status: WorkerStatus, reason: str = "") -> bool:
        with _get_db(self._db_path) as conn:
            cur = conn.execute(
                "UPDATE runtime_guardian_workers SET status = ?, recovery_reason = ?, updated_at = ? WHERE worker_id = ?",
                (status.value, reason, _now_iso(), worker_id),
            )
            return cur.rowcount > 0

    def _update_worker_fields(self, worker_id: str, **fields) -> bool:
        """更新 worker 的追踪字段（内部使用）"""
        if not fields:
            return False
        allowed = {
            "last_success_at", "last_heartbeat_at", "last_checkpoint_at",
            "failure_count", "retry_count", "lease_owner", "run_id",
            "checkpoint_id", "recovery_reason", "status", "metadata",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [_now_iso(), worker_id]
        with _get_db(self._db_path) as conn:
            cur = conn.execute(
                f"UPDATE runtime_guardian_workers SET {set_clause}, updated_at = ? WHERE worker_id = ?",
                values,
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Lease 租约
    # ------------------------------------------------------------------
    def acquire_lease(
        self,
        worker_id: str,
        owner: str,
        ttl_seconds: float = DEFAULT_LEASE_TTL,
    ) -> Optional[WorkerLease]:
        """
        获取租约。如果 worker 已有未过期租约且 owner 不同 → 返回 None（抢占失败）。
        如果已有未过期租约且 owner 相同 → 续期。
        如果租约已过期 → 重新获取。
        """
        now = _now_ts()
        worker = self.get_worker(worker_id)
        if not worker:
            return None

        existing_owner = worker.get("lease_owner", "")
        meta = worker.get("metadata", {})
        existing_expires = meta.get("lease_expires_at", 0)

        if existing_owner and existing_owner != owner and now < existing_expires:
            # 租约被其他 owner 持有且未过期
            return None

        expires_at = now + ttl_seconds
        lease = WorkerLease(
            lease_owner=owner,
            acquired_at=now,
            expires_at=expires_at,
            renewed_at=now,
        )
        meta["lease_expires_at"] = expires_at
        meta["lease_acquired_at"] = now
        with _get_db(self._db_path) as conn:
            conn.execute(
                "UPDATE runtime_guardian_workers SET lease_owner = ?, metadata = ?, status = ?, updated_at = ? WHERE worker_id = ?",
                (owner, json.dumps(meta, ensure_ascii=False), WorkerStatus.RUNNING.value, _now_iso(), worker_id),
            )
        return lease

    def renew_lease(self, worker_id: str, owner: str, ttl_seconds: float = DEFAULT_LEASE_TTL) -> Optional[WorkerLease]:
        """续期租约（必须是当前 owner）"""
        worker = self.get_worker(worker_id)
        if not worker or worker.get("lease_owner") != owner:
            return None
        now = _now_ts()
        expires_at = now + ttl_seconds
        meta = worker.get("metadata", {})
        meta["lease_expires_at"] = expires_at
        meta["lease_renewed_at"] = now
        with _get_db(self._db_path) as conn:
            conn.execute(
                "UPDATE runtime_guardian_workers SET metadata = ?, updated_at = ? WHERE worker_id = ?",
                (json.dumps(meta, ensure_ascii=False), _now_iso(), worker_id),
            )
        return WorkerLease(
            lease_owner=owner,
            acquired_at=meta.get("lease_acquired_at", now),
            expires_at=expires_at,
            renewed_at=now,
        )

    def release_lease(self, worker_id: str, owner: str) -> bool:
        """释放租约（必须是当前 owner）"""
        worker = self.get_worker(worker_id)
        if not worker or worker.get("lease_owner") != owner:
            return False
        meta = worker.get("metadata", {})
        meta.pop("lease_expires_at", None)
        meta.pop("lease_acquired_at", None)
        with _get_db(self._db_path) as conn:
            conn.execute(
                "UPDATE runtime_guardian_workers SET lease_owner = '', metadata = ?, status = ?, updated_at = ? WHERE worker_id = ?",
                (json.dumps(meta, ensure_ascii=False), WorkerStatus.IDLE.value, _now_iso(), worker_id),
            )
        return True

    def get_lease(self, worker_id: str) -> Optional[WorkerLease]:
        worker = self.get_worker(worker_id)
        if not worker or not worker.get("lease_owner"):
            return None
        meta = worker.get("metadata", {})
        return WorkerLease(
            lease_owner=worker["lease_owner"],
            acquired_at=meta.get("lease_acquired_at", 0),
            expires_at=meta.get("lease_expires_at", 0),
            renewed_at=meta.get("lease_renewed_at", 0),
        )

    # ------------------------------------------------------------------
    # Heartbeat 心跳
    # ------------------------------------------------------------------
    def heartbeat(self, worker_id: str, domain_id: Optional[str] = None) -> bool:
        """发送心跳，更新 last_heartbeat_at。双域核心：心跳携带 domain_id。"""
        now = _now_iso()
        with self._lock:
            if worker_id not in self._heartbeats:
                self._heartbeats[worker_id] = Heartbeat()
            self._heartbeats[worker_id].beat()
        fields = {"last_heartbeat_at": now}
        if domain_id:
            fields["domain_id"] = domain_id
            # 同步更新 metadata 中的 domain_id
            worker = self.get_worker(worker_id)
            if worker:
                meta = worker.get("metadata", {}) or {}
                meta["domain_id"] = domain_id
                fields["metadata"] = json.dumps(meta, ensure_ascii=False)
        return self._update_worker_fields(worker_id, **fields)

    def is_worker_alive(self, worker_id: str) -> bool:
        """检查 worker 是否存活（心跳未超时）。从未发送心跳的 worker 视为不存活。"""
        with self._lock:
            hb = self._heartbeats.get(worker_id)
            if hb:
                if hb.last_heartbeat_at == 0:
                    return False
                return not hb.is_timed_out()
        # 内存中没有心跳记录，查 DB
        worker = self.get_worker(worker_id)
        if not worker or not worker.get("last_heartbeat_at"):
            return False
        try:
            hb_time = datetime.strptime(worker["last_heartbeat_at"], "%Y-%m-%d %H:%M:%S")
            return (_now_ts() - hb_time.timestamp()) < DEFAULT_HEARTBEAT_INTERVAL * DEFAULT_HEARTBEAT_MISSED_THRESHOLD
        except (ValueError, TypeError):
            return False

    def get_heartbeat(self, worker_id: str) -> Optional[Heartbeat]:
        with self._lock:
            return self._heartbeats.get(worker_id)

    # ------------------------------------------------------------------
    # Checkpoint 检查点（委托给 ResumeManager）
    # ------------------------------------------------------------------
    @property
    def checkpoints(self) -> ResumeManager:
        return self._resume

    def save_checkpoint(self, **kwargs) -> str:
        return self._resume.save_checkpoint(**kwargs)

    def get_latest_checkpoint(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self._resume.get_latest_checkpoint(run_id)

    # ------------------------------------------------------------------
    # Retry + CircuitBreaker + DLQ 统一执行
    # ------------------------------------------------------------------
    def get_circuit_breaker(self, worker_id: str) -> CircuitBreaker:
        with self._lock:
            if worker_id not in self._circuit_breakers:
                self._circuit_breakers[worker_id] = CircuitBreaker(
                    name=f"guardian:{self.name}:{worker_id}",
                    failure_threshold=self._retry_policy.circuit_breaker_threshold,
                )
            return self._circuit_breakers[worker_id]

    def execute_with_retry(
        self,
        worker_id: str,
        func: Callable,
        *args,
        task_type: str = "",
        payload: Optional[Dict[str, Any]] = None,
        run_id: str = "",
        **kwargs,
    ) -> Any:
        """
        受完整保护的执行：重试 + 指数退避 + 熔断器 + DLQ。

        流程：
          1. 检查熔断器，OPEN 则直接拒绝
          2. 执行 func，成功 → 记录 success，返回结果
          3. 失败 → 记录 failure，检查重试策略
          4. 可重试 → 指数退避后重试
          5. 超过 max_retries → 入 DLQ，抛出最后异常

        禁止无限重启：第 max_retries+1 次失败后进入 DLQ，不再自动重试。
        """
        cb = self.get_circuit_breaker(worker_id)
        policy = self._retry_policy
        last_error: Optional[Exception] = None
        run_id = run_id or uuid.uuid4().hex[:12]

        for attempt in range(policy.max_retries + 1):
            # 熔断器检查
            if not cb.allow_request():
                # 熔断中：直接入 DLQ，不再重试
                dlq_id = self._dlq.enqueue(
                    worker_id=worker_id,
                    run_id=run_id,
                    task_type=task_type,
                    payload=payload,
                    error=f"CircuitBreaker OPEN after {cb._failure_count} failures",
                    error_type="CircuitBreakerOpen",
                    max_attempts=policy.max_retries,
                )
                self._update_worker_fields(
                    worker_id,
                    failure_count=self._get_worker_failure_count(worker_id) + 1,
                    recovery_reason=f"circuit_breaker_open dlq={dlq_id}",
                )
                raise RuntimeError(
                    f"CircuitBreaker OPEN for worker {worker_id}; task moved to DLQ {dlq_id}"
                )

            try:
                result = func(*args, **kwargs)
                cb.record_success()
                self._update_worker_fields(
                    worker_id,
                    last_success_at=_now_iso(),
                    run_id=run_id,
                )
                return result
            except Exception as e:
                last_error = e
                cb.record_failure()
                self._update_worker_fields(
                    worker_id,
                    failure_count=self._get_worker_failure_count(worker_id) + 1,
                    retry_count=attempt + 1,
                )

                if attempt >= policy.max_retries:
                    # 超过重试上限 → 入 DLQ
                    dlq_id = self._dlq.enqueue(
                        worker_id=worker_id,
                        run_id=run_id,
                        task_type=task_type,
                        payload=payload,
                        error=str(e),
                        error_type=type(e).__name__,
                        max_attempts=policy.max_retries,
                    )
                    self._update_worker_fields(
                        worker_id,
                        status=WorkerStatus.FAILED.value,
                        recovery_reason=f"max_retries_exceeded dlq={dlq_id}",
                    )
                    raise RuntimeError(
                        f"Task failed after {attempt + 1} attempts; moved to DLQ {dlq_id}. "
                        f"Last error: {type(e).__name__}: {e}"
                    ) from e

                # 指数退避后重试
                wait = policy.backoff_seconds(attempt + 1)
                time.sleep(wait)

        # 理论上不会到这里
        raise last_error or RuntimeError("execute_with_retry: unknown failure")

    def _get_worker_failure_count(self, worker_id: str) -> int:
        worker = self.get_worker(worker_id)
        return worker.get("failure_count", 0) if worker else 0

    # ------------------------------------------------------------------
    # DLQ 访问
    # ------------------------------------------------------------------
    @property
    def dlq(self) -> DLQ:
        return self._dlq

    # ------------------------------------------------------------------
    # Reaper 后台回收
    # ------------------------------------------------------------------
    def start_reaper(self, interval: float = DEFAULT_REAPER_INTERVAL) -> None:
        """启动后台回收线程（幂等）"""
        with self._lock:
            if self._reaper_running:
                return
            self._reaper_running = True
            self._reaper_thread = threading.Thread(
                target=self._reaper_loop, args=(interval,), daemon=True, name=f"rg-reaper-{self.name}"
            )
            self._reaper_thread.start()

    def stop_reaper(self) -> None:
        with self._lock:
            self._reaper_running = False

    def _reaper_loop(self, interval: float) -> None:
        while self._reaper_running:
            try:
                self._reaper.run_cycle()
            except Exception:
                pass
            time.sleep(interval)

    def reap_now(self, heartbeat_timeout: float = 60.0) -> Dict[str, List[str]]:
        """立即执行一次回收"""
        return self._reaper.run_cycle(heartbeat_timeout)

    # ------------------------------------------------------------------
    # 双域核心：按域查询任务/Worker
    # ------------------------------------------------------------------
    def get_tasks_by_domain(self, domain_id: str) -> Dict[str, Any]:
        """按域查询任务列表（workers + DLQ entries），实现任务队列按域隔离。

        返回 {domain_id, workers, dlq_entries, total_active, total_failed}。
        CTH 大规模采集不拖垮 ZBMP：调用方按域分别查询和调度。
        """
        with _get_db(self._db_path) as conn:
            workers = []
            try:
                rows = conn.execute(
                    "SELECT * FROM runtime_guardian_workers WHERE domain_id = ? ORDER BY created_at DESC",
                    (domain_id,),
                ).fetchall()
                for row in rows:
                    d = dict(row)
                    try:
                        d["metadata"] = json.loads(d.get("metadata") or "{}")
                    except (json.JSONDecodeError, TypeError):
                        d["metadata"] = {}
                    workers.append(d)
            except Exception as _e:
                workers = []

            dlq_entries = []
            try:
                rows = conn.execute(
                    "SELECT * FROM runtime_guardian_dlq WHERE domain_id = ? ORDER BY created_at DESC LIMIT 100",
                    (domain_id,),
                ).fetchall()
                for row in rows:
                    d = dict(row)
                    try:
                        d["payload"] = json.loads(d.get("payload") or "{}")
                    except (json.JSONDecodeError, TypeError):
                        d["payload"] = {}
                    dlq_entries.append(d)
            except Exception as _e:
                dlq_entries = []

        running = sum(1 for w in workers if w.get("status") == WorkerStatus.RUNNING.value)
        failed = sum(1 for w in workers if w.get("status") in (
            WorkerStatus.FAILED.value, WorkerStatus.DEAD.value))
        return {
            "domain_id": domain_id,
            "workers": workers,
            "dlq_entries": dlq_entries,
            "total_workers": len(workers),
            "running": running,
            "failed": failed,
            "dlq_count": len(dlq_entries),
        }

    def list_workers_by_domain(self, domain_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """按域列出 workers（Guardian 按域隔离 worker 列表）。"""
        result = self.get_tasks_by_domain(domain_id)
        workers = result.get("workers", [])
        if status:
            workers = [w for w in workers if w.get("status") == status]
        return workers

    # ------------------------------------------------------------------
    # 健康检查与状态
    # ------------------------------------------------------------------
    def health_check(self) -> Dict[str, Any]:
        """统一健康检查（替代 system_guardian.health_check）"""
        workers = self.list_workers()
        running = sum(1 for w in workers if w["status"] == WorkerStatus.RUNNING.value)
        failed = sum(1 for w in workers if w["status"] == WorkerStatus.FAILED.value)
        dead = sum(1 for w in workers if w["status"] == WorkerStatus.DEAD.value)
        dlq_stats = self._dlq.stats()
        cb_stats = {wid: cb.stats() for wid, cb in self._circuit_breakers.items()}

        overall = "healthy"
        if failed > 0 or dead > 0:
            overall = "degraded"
        if any(cb["state"] == CircuitState.OPEN.value for cb in cb_stats.values()):
            overall = "degraded"

        return {
            "timestamp": _now_iso(),
            "guardian_name": self.name,
            "overall": overall,
            "workers": {
                "total": len(workers),
                "running": running,
                "idle": sum(1 for w in workers if w["status"] == WorkerStatus.IDLE.value),
                "failed": failed,
                "dead": dead,
            },
            "dlq": dlq_stats,
            "circuit_breakers": cb_stats,
            "reaper_running": self._reaper_running,
        }

    def get_retry_policy(self) -> RetryPolicy:
        return self._retry_policy

    def set_retry_policy(self, policy: RetryPolicy) -> None:
        with self._lock:
            self._retry_policy = policy

    # ------------------------------------------------------------------
    # 上下文管理器：自动获取/释放租约 + 心跳
    # ------------------------------------------------------------------
    @contextmanager
    def supervised_worker(
        self,
        worker_name: str,
        owner: str = "",
        lease_ttl: float = DEFAULT_LEASE_TTL,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        上下文管理器：自动注册 worker → 获取租约 → 进入 with 块 → 退出时释放租约。

        用法：
            with guardian.supervised_worker("xhs_collector", owner="node-1") as (worker_id, lease):
                guardian.heartbeat(worker_id)
                result = guardian.execute_with_retry(worker_id, collect_fn)
        """
        worker_id = self.register_worker(worker_name, metadata=metadata)
        owner = owner or f"pid-{os.getpid()}"
        lease = self.acquire_lease(worker_id, owner, ttl_seconds=lease_ttl)
        self.heartbeat(worker_id)
        try:
            yield worker_id, lease
        finally:
            if lease:
                self.release_lease(worker_id, owner)
            self.update_worker_status(worker_id, WorkerStatus.STOPPED, reason="context_exit")


# ---------------------------------------------------------------------------
# 便捷函数（供 Legacy 模块委托调用）
# ---------------------------------------------------------------------------
def get_guardian(name: str = "default") -> RuntimeGuardian:
    """获取 RuntimeGuardian 单例"""
    return RuntimeGuardian.get_instance(name)


def legacy_health_check() -> Dict[str, Any]:
    """供 system_guardian 等 Legacy 模块委托的健康检查"""
    return get_guardian("legacy").health_check()


def legacy_global_exception_handler(func: Callable) -> Callable:
    """供 system_guardian 委托的全局异常捕获装饰器（保留原行为，增加 Guardian 记录）"""
    import functools
    import traceback

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 记录到 Guardian（不阻断原行为）
            try:
                g = get_guardian("legacy")
                wid = g.register_worker(f"legacy_{func.__name__}")
                g._update_worker_fields(
                    wid,
                    failure_count=1,
                    recovery_reason=f"{type(e).__name__}: {e}",
                )
            except Exception:
                pass
            raise
    return wrapper


# 模块加载时初始化 DB（不阻断）
try:
    init_db()
except Exception:
    pass
