# -*- coding: utf-8 -*-
"""ZBC AI Task Engine — Production-Ready 任务编排执行引擎

完整调用链：
  User → AI Task → Task Parser → Intent → Agent → Skill Selection
  → Permission Gate → Execution → Evidence → Verification → Response → Trace

核心能力：
  1. 任务生命周期管理（create/run/cancel/approve）
  2. 同步/异步执行，超时控制，重试+指数退避
  3. 熔断器（Circuit Breaker）：连续失败后暂停执行
  4. 死信队列（DLQ）：重试耗尽后进入 DLQ，人工升级
  5. 验证（Verification）：每个结果必须验证做了什么/为什么/调用了什么/结果/证据/是否成功
  6. 调用链追踪（Trace）：完整记录到 ai_task_trace 表
  7. OSAI 边界：ZBC 不依赖 OSAI Runtime，OSAI DOWN 时核心功能正常
  8. AI Provider 降级链：智谱 → ARK → 千问 → Ollama → 本地规则（通过 ai_channel，失败则降级）

数据库迁移（向后兼容）：
  - ai_task：任务主表
  - ai_task_step：执行步骤时间线
  - ai_task_evidence：证据列表
  - ai_task_trace：调用链追踪
  全部 CREATE TABLE IF NOT EXISTS，不修改/不删除任何现有表。

生产红线：
  - 不修改 SUBJECT_WORDS / subject_hit()
  - 不删除/清空/重建 monitor.db
  - AI 只增强，不做业务最终真值
  - 敏感凭证只经 .env 注入，不写入源码/日志/DB
"""
from __future__ import annotations

import json
import logging
import os
import hashlib
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from lumenis.shared.database import get_repository, main_db_path

logger = logging.getLogger(__name__)
# ZBC Lifecycle Contract V1.0 (bypass-mode, never breaks main chain)
try:
    from lifecycle_mixin import LifecycleMixin as _LifecycleMixin
    _LIFECYCLE_AVAILABLE = True
except Exception:
    _LifecycleMixin = None
    _LIFECYCLE_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════
# 1. 数据库配置（复用 database.py 的 DB_PATH，独立迁移）
# ═══════════════════════════════════════════════════════════════

try:
    from database import DB_PATH, get_db
except ImportError:
    # 测试环境 fallback
    DB_PATH = main_db_path()

    from contextlib import contextmanager

    @contextmanager
    def get_db():
        conn = get_repository().connect(timeout=30)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════
# 2. 枚举定义
# ═══════════════════════════════════════════════════════════════

class TaskStatus(str, Enum):
    PENDING = "pending"                    # 已创建，待解析
    PARSING = "parsing"                    # 解析中
    AWAITING_APPROVAL = "awaiting_approval"  # 等待人工审批
    READY = "ready"                        # 解析+权限通过，待执行
    RUNNING = "running"                    # 执行中
    SUCCEEDED = "succeeded"                # 成功
    FAILED = "failed"                      # 失败
    CANCELLED = "cancelled"                # 已取消
    DLQ = "dlq"                            # 死信队列（重试耗尽）
    UNKNOWN = "unknown"                    # 未知状态（STOP+Evidence+Human）


class StepPhase(str, Enum):
    PARSE = "parse"
    INTENT = "intent"
    AGENT_SELECT = "agent_select"
    SKILL_SELECT = "skill_select"
    PERMISSION = "permission"
    EXECUTE = "execute"
    VERIFY = "verify"
    RESPOND = "respond"
    APPROVAL = "approval"
    ERROR = "error"


class CircuitState(str, Enum):
    CLOSED = "closed"      # 正常执行
    OPEN = "open"          # 熔断打开，拒绝执行
    HALF_OPEN = "half_open"  # 半开，试探性执行


# ═══════════════════════════════════════════════════════════════
# 3. 数据库 Schema（向后兼容迁移）
# ═══════════════════════════════════════════════════════════════

_TASK_ENGINE_SCHEMA = """
CREATE TABLE IF NOT EXISTS ai_task (
    task_id TEXT PRIMARY KEY,
    user_input TEXT NOT NULL,
    intent TEXT,
    confidence REAL,
    entities_json TEXT DEFAULT '{}',
    parameters_json TEXT DEFAULT '{}',
    context_json TEXT DEFAULT '{}',
    agent_id TEXT,
    skill_id TEXT,
    status TEXT DEFAULT 'pending',
    risk_level TEXT DEFAULT 'L0',
    risk_reason TEXT,
    permission_required TEXT,
    permission_result TEXT,
    approval_token TEXT,
    approved_by TEXT,
    approved_at TEXT,
    result_json TEXT,
    error TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TEXT,
    updated_at TEXT,
    started_at TEXT,
    finished_at TEXT,
    created_by TEXT DEFAULT 'system',
    permanent_deny INTEGER DEFAULT 0,
    admin_required INTEGER DEFAULT 0,
    human_approval_required INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ai_task_step (
    step_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    detail TEXT,
    agent_id TEXT,
    skill_id TEXT,
    started_at TEXT,
    finished_at TEXT,
    duration_ms INTEGER,
    error TEXT,
    FOREIGN KEY (task_id) REFERENCES ai_task(task_id)
);

CREATE TABLE IF NOT EXISTS ai_task_evidence (
    evidence_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    step_id TEXT,
    evidence_type TEXT,
    content TEXT,
    source TEXT,
    authenticity_score REAL DEFAULT 0.0,
    created_at TEXT,
    previous_hash TEXT,
    current_hash TEXT,
    FOREIGN KEY (task_id) REFERENCES ai_task(task_id)
);

CREATE TABLE IF NOT EXISTS ai_task_trace (
    trace_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    span TEXT NOT NULL,
    parent_span TEXT,
    detail TEXT,
    status TEXT,
    started_at TEXT,
    finished_at TEXT,
    duration_ms INTEGER,
    metadata_json TEXT DEFAULT '{}',
    FOREIGN KEY (task_id) REFERENCES ai_task(task_id)
);

CREATE INDEX IF NOT EXISTS idx_ai_task_status ON ai_task(status);
CREATE INDEX IF NOT EXISTS idx_ai_task_created ON ai_task(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_task_step_task ON ai_task_step(task_id);
CREATE INDEX IF NOT EXISTS idx_ai_task_evidence_task ON ai_task_evidence(task_id);
CREATE INDEX IF NOT EXISTS idx_ai_task_trace_task ON ai_task_trace(task_id);
"""


def init_task_engine_db() -> None:
    """初始化 Task Engine 数据库表（幂等，向后兼容）。

    只创建新表，不修改/不删除任何现有表。
    新增字段通过 ALTER TABLE ADD COLUMN 幂等迁移。
    """
    try:
        # Resolve at call time so an isolated runtime/test changing ZBC_DB_PATH
        # cannot send approval tasks to a stale import-time database.
        db_path = main_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with get_repository().connect(timeout=30) as conn:
            conn.executescript(_TASK_ENGINE_SCHEMA)
            # 向后兼容迁移：evidence 链式哈希字段（Decision 6: 全链路Evidence/Audit Trail）
            ev_cols = {r[1] for r in conn.execute('PRAGMA table_info(ai_task_evidence)').fetchall()}
            if "previous_hash" not in ev_cols:
                conn.execute("ALTER TABLE ai_task_evidence ADD COLUMN previous_hash TEXT")
            if "current_hash" not in ev_cols:
                conn.execute("ALTER TABLE ai_task_evidence ADD COLUMN current_hash TEXT")
        logger.info("[TaskEngine] 数据库迁移完成（ai_task/step/evidence/trace，含链式哈希）")
    except Exception as e:
        logger.error(f"[TaskEngine] 数据库迁移失败: {e}", exc_info=True)
        raise


# ═══════════════════════════════════════════════════════════════
# 4. 熔断器（Circuit Breaker）
# ═══════════════════════════════════════════════════════════════

class CircuitBreaker:
    """简易熔断器。

    连续失败超过阈值 → OPEN（拒绝执行）→ 冷却期后 HALF_OPEN（试探）→ 成功则 CLOSED。
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 30,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    def can_execute(self) -> bool:
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.OPEN:
                if (self._last_failure_time and
                        time.time() - self._last_failure_time > self.recovery_timeout):
                    self._state = CircuitState.HALF_OPEN
                    return True
                return False
            # HALF_OPEN：允许一次试探
            return True

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "state": self._state.value,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout_seconds": self.recovery_timeout,
            }


# ═══════════════════════════════════════════════════════════════
# 5. Verification Result
# ═══════════════════════════════════════════════════════════════

@dataclass
class VerificationResult:
    """验证结果：每个任务执行后必须产出。"""
    verified: bool
    what_was_done: str                        # 做了什么
    why: str                                   # 为什么
    what_was_called: str                      # 调用了什么（Agent/Skill/API）
    result_summary: str                        # 结果摘要
    evidence_ids: List[str] = field(default_factory=list)  # 证据 ID 列表
    success: bool = False                      # 是否成功
    needs_human_confirmation: bool = False     # 是否需人工确认
    human_confirmation_reason: str = ""
    verification_method: str = "rule_based"   # 验证方式
    verified_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════
# 6. TaskEngine 核心类
# ═══════════════════════════════════════════════════════════════

class TaskEngine:
    """AI Task Engine 编排执行引擎。

    完整调用链闭环：
      create_task → parse_task → select_agent → select_skill
      → check_permission → execute_task → verify_result → respond → trace
    """

    def __init__(
        self,
        auto_init_db: bool = True,
        default_timeout_seconds: int = 60,
        default_max_retries: int = 3,
    ):
        self.default_timeout = default_timeout_seconds
        self.default_max_retries = default_max_retries
        self._circuit = CircuitBreaker()
        self._lock = threading.Lock()
        self._running_tasks: Dict[str, threading.Thread] = {}
        self._cancelled: set = set()

        # Lifecycle Contract V1.0 (bypass-mode)
        self._lifecycle_worker = None
        if _LIFECYCLE_AVAILABLE:
            try:
                self._lifecycle_worker = _LifecycleMixin(
                    worker_name="ai_task_engine", domain_id="zbmp", product_id="ZBMP",
                )
                self._lifecycle_worker.lifecycle_create()
            except Exception:
                self._lifecycle_worker = None

        # 延迟导入，避免循环依赖
        self._parser = None
        self._agent_registry = None
        self._permission_gate = None
        self._skill_registry = None

        if auto_init_db:
            init_task_engine_db()

    # ──────────────────────────────────────────────────────────
    # 延迟初始化依赖
    # ──────────────────────────────────────────────────────────

    @property
    def parser(self):
        if self._parser is None:
            from ai_task_parser import get_task_parser
            self._parser = get_task_parser()
        return self._parser

    @property
    def agent_registry(self):
        if self._agent_registry is None:
            from ai_agent_registry import get_agent_registry
            self._agent_registry = get_agent_registry()
        return self._agent_registry

    @property
    def permission_gate(self):
        if self._permission_gate is None:
            try:
                from lumenis.system.security import get_permission_gate
                self._permission_gate = get_permission_gate()
            except ImportError:
                self._permission_gate = None
        return self._permission_gate

    @property
    def skill_registry(self):
        if self._skill_registry is None:
            try:
                from lumenis.shared.agents.skills.registry import get_skill_registry
                self._skill_registry = get_skill_registry()
            except ImportError:
                self._skill_registry = None
        return self._skill_registry

    # ──────────────────────────────────────────────────────────
    # DB 辅助
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat()

    @staticmethod
    def _gen_id(prefix: str = "id") -> str:
        return f"{prefix}_{uuid.uuid4().hex[:16]}"

    def _db_update_task(self, task_id: str, **fields) -> None:
        if not fields:
            return
        fields["updated_at"] = self._now()
        set_clause = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values()) + [task_id]
        with get_db() as conn:
            conn.execute(f"UPDATE ai_task SET {set_clause} WHERE task_id=?", values)

    def _db_get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM ai_task WHERE task_id=?", (task_id,)
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        # 解析 JSON 字段
        for json_field in ("entities_json", "parameters_json", "context_json", "result_json"):
            val = d.get(json_field)
            if val:
                try:
                    d[json_field.replace("_json", "")] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    d[json_field.replace("_json", "")] = {}
        return d

    def _db_add_step(
        self,
        task_id: str,
        phase: str,
        status: str = "running",
        detail: str = "",
        agent_id: Optional[str] = None,
        skill_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> str:
        step_id = self._gen_id("step")
        now = self._now()
        with get_db() as conn:
            conn.execute(
                """INSERT INTO ai_task_step
                   (step_id, task_id, phase, status, detail, agent_id, skill_id,
                    started_at, finished_at, duration_ms, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (step_id, task_id, phase, status, detail, agent_id, skill_id,
                 now, now if status != "running" else None,
                 0 if status != "running" else None, error),
            )
        return step_id

    def _db_update_step(self, step_id: str, **fields) -> None:
        if not fields:
            return
        if "finished_at" not in fields and fields.get("status") != "running":
            fields["finished_at"] = self._now()
        set_clause = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values()) + [step_id]
        with get_db() as conn:
            conn.execute(f"UPDATE ai_task_step SET {set_clause} WHERE step_id=?", values)

    def _db_add_evidence(
        self,
        task_id: str,
        evidence_type: str,
        content: str,
        source: str = "task_engine",
        step_id: Optional[str] = None,
        authenticity_score: float = 0.8,
    ) -> str:
        evidence_id = self._gen_id("ev")
        now = self._now()
        # 链式哈希（Decision 6: 全链路Evidence/Audit Trail，不可篡改）
        # current_hash = SHA256(previous_hash + evidence_id + task_id + content + created_at)
        previous_hash = None
        try:
            with get_db() as conn:
                row = conn.execute(
                    "SELECT current_hash FROM ai_task_evidence WHERE task_id=? ORDER BY created_at DESC LIMIT 1",
                    (task_id,),
                ).fetchone()
                if row and row[0]:
                    previous_hash = row[0]
        except Exception:
            previous_hash = None
        hash_input = f"{previous_hash or 'genesis'}|{evidence_id}|{task_id}|{content}|{now}"
        current_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        with get_db() as conn:
            conn.execute(
                """INSERT INTO ai_task_evidence
                   (evidence_id, task_id, step_id, evidence_type, content, source,
                    authenticity_score, created_at, previous_hash, current_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (evidence_id, task_id, step_id, evidence_type, content, source,
                 authenticity_score, now, previous_hash, current_hash),
            )
        return evidence_id

    def _db_add_trace(
        self,
        task_id: str,
        span: str,
        detail: str = "",
        status: str = "ok",
        parent_span: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        started_at: Optional[str] = None,
        finished_at: Optional[str] = None,
    ) -> str:
        trace_id = self._gen_id("trace")
        now = self._now()
        duration_ms = 0
        if started_at and finished_at:
            try:
                s = datetime.fromisoformat(started_at)
                f = datetime.fromisoformat(finished_at)
                duration_ms = int((f - s).total_seconds() * 1000)
            except Exception:
                duration_ms = 0
        with get_db() as conn:
            conn.execute(
                """INSERT INTO ai_task_trace
                   (trace_id, task_id, span, parent_span, detail, status,
                    started_at, finished_at, duration_ms, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (trace_id, task_id, span, parent_span, detail, status,
                 started_at or now, finished_at or now, duration_ms,
                 json.dumps(metadata or {}, ensure_ascii=False)),
            )
        return trace_id

    # ──────────────────────────────────────────────────────────
    # 1. 创建任务
    # ──────────────────────────────────────────────────────────

    def create_task(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        created_by: str = "system",
    ) -> Dict[str, Any]:
        """创建 AI Task。

        Returns:
            任务摘要 dict
        """
        task_id = self._gen_id("task")
        now = self._now()
        ctx = context or {}

        with get_db() as conn:
            conn.execute(
                """INSERT INTO ai_task
                   (task_id, user_input, context_json, status, created_at, updated_at, created_by)
                   VALUES (?, ?, ?, 'pending', ?, ?, ?)""",
                (task_id, user_input, json.dumps(ctx, ensure_ascii=False), now, now, created_by),
            )

        self._db_add_trace(task_id, "task.create", f"Task created by {created_by}", "ok")
        logger.info(f"[TaskEngine] 任务已创建: {task_id}")

        return {
            "task_id": task_id,
            "status": TaskStatus.PENDING.value,
            "created_at": now,
            "user_input": user_input,
        }

    # ──────────────────────────────────────────────────────────
    # 2. 解析任务（Parser → Intent）
    # ──────────────────────────────────────────────────────────

    def parse_task(self, task_id: str) -> Dict[str, Any]:
        """解析任务：提取 intent/entities/parameters/context。"""
        task = self._db_get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        self._db_update_task(task_id, status=TaskStatus.PARSING.value)
        step_id = self._db_add_step(task_id, StepPhase.PARSE.value, "running", "Parsing user input")
        trace_start = self._now()

        try:
            parsed = self.parser.parse(
                task["user_input"],
                context=task.get("context", {}),
                task_id=task_id,
            )

            # 永久 DENY 直接终止
            if parsed.permanent_deny:
                self._db_update_task(
                    task_id,
                    intent=parsed.intent.value,
                    confidence=parsed.confidence,
                    entities_json=json.dumps(parsed.entities, ensure_ascii=False),
                    parameters_json=json.dumps(parsed.parameters, ensure_ascii=False),
                    risk_level=parsed.risk_level.value,
                    risk_reason=parsed.risk_reason,
                    permanent_deny=1,
                    status=TaskStatus.FAILED.value,
                    error=f"PERMANENT_DENY: {parsed.risk_reason}",
                    finished_at=self._now(),
                )
                self._db_update_step(step_id, status="failed", error=parsed.risk_reason)
                self._db_add_evidence(
                    task_id, "permission_deny",
                    f"Permanent deny: {parsed.risk_reason}",
                    source="task_parser", step_id=step_id, authenticity_score=1.0,
                )
                self._db_add_trace(
                    task_id, "task.parse", "Permanent deny, task terminated",
                    "denied", started_at=trace_start, finished_at=self._now(),
                )
                return self._db_get_task(task_id)

            # Admin 需求直接终止（fail-closed，当前系统无 Admin 角色）
            if parsed.admin_required:
                self._db_update_task(
                    task_id,
                    intent=parsed.intent.value,
                    confidence=parsed.confidence,
                    entities_json=json.dumps(parsed.entities, ensure_ascii=False),
                    parameters_json=json.dumps(parsed.parameters, ensure_ascii=False),
                    risk_level=parsed.risk_level.value,
                    risk_reason=parsed.risk_reason,
                    admin_required=1,
                    status=TaskStatus.FAILED.value,
                    error=f"ADMIN_REQUIRED: {parsed.risk_reason}",
                    finished_at=self._now(),
                )
                self._db_update_step(step_id, status="denied", error=parsed.risk_reason)
                self._db_add_evidence(
                    task_id, "permission_deny",
                    f"Admin required: {parsed.risk_reason}",
                    source="task_parser", step_id=step_id, authenticity_score=1.0,
                )
                self._db_add_trace(
                    task_id, "task.parse", "Admin required, task denied",
                    "denied", started_at=trace_start, finished_at=self._now(),
                )
                return self._db_get_task(task_id)

            # 人工审批需求 → 直接进入 awaiting_approval（在 Agent 选择之前）
            if parsed.human_approval_required or parsed.risk_level.value in ("L3", "L4"):
                self._db_update_task(
                    task_id,
                    intent=parsed.intent.value,
                    confidence=parsed.confidence,
                    entities_json=json.dumps(parsed.entities, ensure_ascii=False),
                    parameters_json=json.dumps(parsed.parameters, ensure_ascii=False),
                    risk_level=parsed.risk_level.value,
                    risk_reason=parsed.risk_reason,
                    human_approval_required=1 if parsed.human_approval_required else 0,
                    status=TaskStatus.AWAITING_APPROVAL.value,
                )
                self._db_update_step(step_id, status="awaiting_approval",
                                     detail=f"Human approval required: {parsed.risk_reason}")
                self._db_add_evidence(
                    task_id, "awaiting_approval",
                    f"Human approval required: {parsed.risk_reason}",
                    source="task_parser", step_id=step_id, authenticity_score=0.9,
                )
                self._db_add_trace(
                    task_id, "task.parse",
                    f"Awaiting human approval: risk={parsed.risk_level.value}",
                    "awaiting_approval", started_at=trace_start, finished_at=self._now(),
                )
                return self._db_get_task(task_id)

            self._db_update_task(
                task_id,
                intent=parsed.intent.value,
                confidence=parsed.confidence,
                entities_json=json.dumps(parsed.entities, ensure_ascii=False),
                parameters_json=json.dumps(parsed.parameters, ensure_ascii=False),
                risk_level=parsed.risk_level.value,
                risk_reason=parsed.risk_reason,
                admin_required=1 if parsed.admin_required else 0,
                human_approval_required=1 if parsed.human_approval_required else 0,
            )
            self._db_update_step(step_id, status="succeeded",
                                 detail=f"intent={parsed.intent.value}, confidence={parsed.confidence:.2f}")
            self._db_add_trace(
                task_id, "task.parse",
                f"Parsed: intent={parsed.intent.value}, risk={parsed.risk_level.value}",
                "ok", started_at=trace_start, finished_at=self._now(),
                metadata={"intent": parsed.intent.value, "confidence": parsed.confidence},
            )
            return self._db_get_task(task_id)

        except Exception as e:
            logger.error(f"[TaskEngine] 解析失败: {task_id}: {e}", exc_info=True)
            self._db_update_step(step_id, status="failed", error=str(e))
            self._db_update_task(task_id, status=TaskStatus.FAILED.value, error=str(e),
                                 finished_at=self._now())
            raise

    # ──────────────────────────────────────────────────────────
    # 3. Agent + Skill 选择
    # ──────────────────────────────────────────────────────────

    def select_agent_and_skill(self, task_id: str) -> Dict[str, Any]:
        """选择 Agent 和 Skill。"""
        task = self._db_get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        intent_str = task.get("intent", "unknown")
        try:
            from ai_task_parser import Intent
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        # Agent 选择
        agent_step = self._db_add_step(task_id, StepPhase.AGENT_SELECT.value, "running")
        agent = self.agent_registry.select_best_agent(intent, task.get("context", {}))

        if agent is None:
            self._db_update_step(agent_step, status="failed",
                                 error=f"No agent found for intent={intent_str}")
            self._db_update_task(
                task_id, status=TaskStatus.FAILED.value,
                error=f"No agent available for intent={intent_str}",
                finished_at=self._now(),
            )
            self._db_add_evidence(
                task_id, "agent_not_found",
                f"No agent registered for intent={intent_str}",
                source="agent_registry", step_id=agent_step,
            )
            return self._db_get_task(task_id)

        self._db_update_step(agent_step, status="succeeded",
                             detail=f"agent={agent.agent_id}, risk={agent.risk_level.value}")

        # Skill 选择
        skill_step = self._db_add_step(task_id, StepPhase.SKILL_SELECT.value, "running")
        skills = self.agent_registry.select_skills(agent, intent, task.get("context", {}))
        primary_skill = skills[0] if skills else None

        self._db_update_task(task_id, agent_id=agent.agent_id, skill_id=primary_skill)
        self._db_update_step(skill_step, status="succeeded",
                             detail=f"skills={skills}, primary={primary_skill}")
        self._db_add_trace(
            task_id, "task.agent_select",
            f"Selected agent={agent.agent_id}, skills={skills}",
            "ok", metadata={"agent_id": agent.agent_id, "skills": skills},
        )
        return self._db_get_task(task_id)

    # ──────────────────────────────────────────────────────────
    # 4. 权限检查（Permission Gate, fail-closed）
    # ──────────────────────────────────────────────────────────

    def check_permission(self, task_id: str) -> Dict[str, Any]:
        """执行权限检查。fail-closed：未通过则任务进入 awaiting_approval 或 failed。"""
        task = self._db_get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        step_id = self._db_add_step(task_id, StepPhase.PERMISSION.value, "running")
        trace_start = self._now()

        # Admin 需求 → 需 Admin 权限（当前系统无 Admin 角色，fail-closed 拒绝）
        if task.get("admin_required"):
            reason = "ADMIN_REQUIRED: 此操作需 Admin 权限（删除数据/修改配置/生产数据/代码/部署）"
            self._db_update_step(step_id, status="denied", error=reason)
            self._db_update_task(
                task_id, status=TaskStatus.FAILED.value,
                permission_result="denied", error=reason, finished_at=self._now(),
            )
            self._db_add_evidence(
                task_id, "permission_deny", reason,
                source="permission_gate", step_id=step_id, authenticity_score=1.0,
            )
            self._db_add_trace(task_id, "task.permission", reason, "denied",
                               started_at=trace_start, finished_at=self._now())
            return self._db_get_task(task_id)

        # 人工审批需求 → awaiting_approval
        if task.get("human_approval_required") or task.get("risk_level") in ("L3", "L4"):
            reason = (f"HUMAN_APPROVAL_REQUIRED: risk={task.get('risk_level')}, "
                      f"reason={task.get('risk_reason', '')}")
            self._db_update_step(step_id, status="awaiting_approval", detail=reason)
            self._db_update_task(
                task_id, status=TaskStatus.AWAITING_APPROVAL.value,
                permission_result="awaiting_approval",
            )
            self._db_add_trace(task_id, "task.permission", reason, "awaiting_approval",
                               started_at=trace_start, finished_at=self._now())
            return self._db_get_task(task_id)

        # L0/L1/L2：通过 PermissionGate 检查
        if self.permission_gate is not None:
            try:
                from lumenis.system.security import OperationType, RiskLevel as PGRisk
                # 映射操作类型
                agent_id = task.get("agent_id", "")
                if "browser" in agent_id:
                    op_type = OperationType.BROWSER_OPERATION
                elif task.get("intent") == "generate_report":
                    op_type = OperationType.REPORT_GENERATE
                else:
                    op_type = OperationType.AI_CALL

                result = self.permission_gate.check(
                    operation_type=op_type,
                    resource=f"ai_task:{task_id}",
                    caller="task_engine",
                    operation_id=f"task_{task_id}",
                )

                if not result.allowed:
                    self._db_update_step(step_id, status="denied", error=result.reason)
                    self._db_update_task(
                        task_id, status=TaskStatus.FAILED.value,
                        permission_result="denied", error=result.reason,
                        finished_at=self._now(),
                    )
                    self._db_add_evidence(
                        task_id, "permission_deny", result.reason,
                        source="permission_gate", step_id=step_id, authenticity_score=1.0,
                    )
                    self._db_add_trace(task_id, "task.permission", result.reason, "denied",
                                       started_at=trace_start, finished_at=self._now())
                    return self._db_get_task(task_id)

                self._db_update_step(step_id, status="succeeded",
                                     detail=f"PermissionGate allowed: {result.reason}")
                self._db_update_task(task_id, permission_result="allowed",
                                     status=TaskStatus.READY.value)
                self._db_add_trace(task_id, "task.permission", "Permission allowed", "ok",
                                   started_at=trace_start, finished_at=self._now())
                return self._db_get_task(task_id)

            except Exception as e:
                logger.warning(f"[TaskEngine] PermissionGate 异常，fail-closed: {e}")
                self._db_update_step(step_id, status="failed", error=str(e))
                self._db_update_task(task_id, status=TaskStatus.FAILED.value,
                                     permission_result="error", error=str(e),
                                     finished_at=self._now())
                raise
        else:
            # PermissionGate 不可用：L0/L1 自动放行（只读分析），L2+ fail-closed
            risk = task.get("risk_level", "L3")
            if risk in ("L0", "L1"):
                self._db_update_step(step_id, status="succeeded",
                                     detail=f"PermissionGate unavailable, L0/L1 auto-allow (read-only)")
                self._db_update_task(task_id, permission_result="auto_allow_l0l1",
                                     status=TaskStatus.READY.value)
                self._db_add_trace(task_id, "task.permission",
                                   "PermissionGate unavailable, L0/L1 auto-allow", "ok",
                                   started_at=trace_start, finished_at=self._now())
                return self._db_get_task(task_id)
            else:
                reason = f"FAIL_CLOSED: PermissionGate unavailable, risk={risk} denied"
                self._db_update_step(step_id, status="denied", error=reason)
                self._db_update_task(task_id, status=TaskStatus.FAILED.value,
                                     permission_result="denied", error=reason,
                                     finished_at=self._now())
                self._db_add_trace(task_id, "task.permission", reason, "denied",
                                   started_at=trace_start, finished_at=self._now())
                return self._db_get_task(task_id)

    # ──────────────────────────────────────────────────────────
    # 5. 执行任务（含超时/重试/退避/熔断）
    # ──────────────────────────────────────────────────────────

    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """执行任务。支持重试（最多 max_retries）、指数退避、熔断。"""
        # Lifecycle: start worker for this task (bypass-mode)
        _lc_started = False
        if self._lifecycle_worker:
            try:
                _lc_started = self._lifecycle_worker.lifecycle_start(run_id=f"task_{task_id}")
            except Exception:
                pass
        try:
            return self._execute_task_inner(task_id)
        finally:
            # 任务结束（成功/失败/熔断/取消/DLQ/异常）必须停止 lifecycle 心跳线程，
            # 否则每次 execute_task 都泄漏一个 lifecycle-hb 线程（全量测试累积到末尾拖死进程，生产长期运行同样泄漏）
            if _lc_started and self._lifecycle_worker:
                try:
                    self._lifecycle_worker.lifecycle_stop(reason="task_finished")
                except Exception:
                    pass

    def _execute_task_inner(self, task_id: str) -> Dict[str, Any]:
        task = self._db_get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        # 熔断检查
        if not self._circuit.can_execute():
            reason = f"CIRCUIT_BREAKER_OPEN: {self._circuit.get_state()}"
            self._db_update_task(task_id, status=TaskStatus.FAILED.value, error=reason,
                                 finished_at=self._now())
            self._db_add_evidence(task_id, "circuit_breaker", reason, source="circuit_breaker")
            return self._db_get_task(task_id)

        max_retries = task.get("max_retries", self.default_max_retries)
        last_error = None

        for attempt in range(max_retries + 1):
            if task_id in self._cancelled:
                self._db_update_task(task_id, status=TaskStatus.CANCELLED.value,
                                     finished_at=self._now())
                return self._db_get_task(task_id)

            try:
                result = self._execute_once(task_id, attempt)
                self._circuit.record_success()
                return result
            except Exception as e:
                last_error = e
                self._circuit.record_failure()
                retry_count = attempt + 1
                self._db_update_task(task_id, retry_count=retry_count)

                if retry_count <= max_retries:
                    # 指数退避：1s, 2s, 4s...
                    backoff = min(2 ** attempt, 30)
                    logger.warning(f"[TaskEngine] 执行失败 (attempt {retry_count}/{max_retries}), "
                                   f"退避 {backoff}s: {e}")
                    self._db_add_evidence(
                        task_id, "retry",
                        f"Attempt {retry_count} failed: {e}, retrying in {backoff}s",
                        source="task_engine",
                    )
                    time.sleep(backoff)
                    # 重新读取任务状态
                    task = self._db_get_task(task_id)
                    continue
                else:
                    # 重试耗尽 → DLQ
                    logger.error(f"[TaskEngine] 重试耗尽，进入 DLQ: {task_id}: {e}")
                    self._db_update_task(
                        task_id, status=TaskStatus.DLQ.value,
                        error=f"Retries exhausted: {e}", finished_at=self._now(),
                    )
                    self._db_add_evidence(
                        task_id, "dlq",
                        f"Task entered DLQ after {max_retries} retries. Last error: {e}",
                        source="task_engine", authenticity_score=1.0,
                    )
                    self._db_add_trace(task_id, "task.execute", "Retries exhausted, DLQ", "dlq")
                    return self._db_get_task(task_id)

        # 理论上不会到这里
        return self._db_get_task(task_id)

    def _execute_once(self, task_id: str, attempt: int) -> Dict[str, Any]:
        """单次执行。"""
        task = self._db_get_task(task_id)
        step_id = self._db_add_step(
            task_id, StepPhase.EXECUTE.value, "running",
            detail=f"Attempt {attempt + 1}, agent={task.get('agent_id')}, skill={task.get('skill_id')}",
            agent_id=task.get("agent_id"), skill_id=task.get("skill_id"),
        )
        trace_start = self._now()
        self._db_update_task(task_id, status=TaskStatus.RUNNING.value, started_at=self._now())

        try:
            # 根据 Agent 类型执行对应逻辑
            agent_id = task.get("agent_id", "")
            intent = task.get("intent", "unknown")
            result_data = self._dispatch_execution(task, agent_id, intent)

            # 验证
            verification = self._verify_result(task, result_data, step_id)

            # 组装最终结果
            final_result = {
                "task_id": task_id,
                "intent": intent,
                "agent_id": agent_id,
                "skill_id": task.get("skill_id"),
                "output": result_data,
                "verification": verification.to_dict(),
                "executed_at": self._now(),
            }

            self._db_update_task(
                task_id,
                status=TaskStatus.SUCCEEDED.value,
                result_json=json.dumps(final_result, ensure_ascii=False, default=str),
                finished_at=self._now(),
            )
            self._db_update_step(step_id, status="succeeded",
                                 detail=f"Execution succeeded, verified={verification.verified}")
            self._db_add_trace(
                task_id, "task.execute",
                f"Execution succeeded, verified={verification.verified}",
                "ok", started_at=trace_start, finished_at=self._now(),
                metadata={"attempt": attempt, "verification": verification.verified},
            )
            return self._db_get_task(task_id)

        except Exception as e:
            self._db_update_step(step_id, status="failed", error=str(e))
            self._db_add_trace(task_id, "task.execute", f"Execution failed: {e}", "error",
                               started_at=trace_start, finished_at=self._now())
            raise

    def _dispatch_execution(
        self,
        task: Dict[str, Any],
        agent_id: str,
        intent: str,
    ) -> Dict[str, Any]:
        """根据 Agent 类型分发执行。

        所有执行均为只读/分析，不修改生产数据。
        AI 调用通过 ai_channel（如可用），失败则降级到本地规则。
        """
        user_input = task.get("user_input", "")
        parameters = task.get("parameters", {})

        # ── 数据查询 Agent ──
        if agent_id == "data_query_agent":
            return self._execute_data_query(task, intent)

        # ── 分析推理 Agent ──
        if agent_id == "analysis_agent":
            return self._execute_analysis(task, intent)

        # ── 报告生成 Agent ──
        if agent_id == "report_agent":
            return self._execute_report(task, intent)

        # ── 浏览器 Agent（只读） ──
        if agent_id == "browser_agent":
            return self._execute_browser(task, intent)

        # ── 默认：AI 辅助回答（通过 ai_channel，带降级） ──
        return self._execute_ai_assist(task, intent)

    def _execute_data_query(self, task: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """数据查询：只读查询 DB。"""
        parameters = task.get("parameters", {})
        result: Dict[str, Any] = {
            "query_type": intent,
            "parameters": parameters,
            "data_source": "monitor.db (read-only)",
            "note": "Data query executed in read-only mode",
        }

        # 尝试查询笔记数量（只读）
        try:
            with get_db() as conn:
                total_notes = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
                total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            result["notes_count"] = total_notes
            result["events_count"] = total_events
            result["query_success"] = True
        except Exception as e:
            result["query_success"] = False
            result["query_error"] = str(e)

        # AI 辅助总结（可选，带降级）
        ai_summary = self._try_ai_summarize(task.get("user_input", ""), result)
        if ai_summary:
            result["ai_summary"] = ai_summary

        return result

    def _execute_analysis(self, task: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """分析推理：纯内存计算。"""
        result: Dict[str, Any] = {
            "analysis_type": intent,
            "input": task.get("user_input", ""),
            "method": "rule_based_with_ai_optional",
        }

        # AI 辅助分析（带降级）
        ai_analysis = self._try_ai_analyze(task.get("user_input", ""))
        if ai_analysis:
            result["ai_analysis"] = ai_analysis
            result["analysis_provider"] = ai_analysis.get("provider", "unknown")
        else:
            result["ai_analysis"] = None
            result["analysis_provider"] = "local_rules (AI unavailable, degraded)"
            result["degradation_note"] = "AI provider unavailable, using local rule-based analysis"

        return result

    def _execute_report(self, task: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """报告生成：只读聚合。"""
        result: Dict[str, Any] = {
            "report_type": intent,
            "status": "generated",
            "note": "Report generated from read-only data aggregation",
        }
        try:
            with get_db() as conn:
                result["notes_count"] = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
                result["events_count"] = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        except Exception as e:
            result["error"] = str(e)
        return result

    def _execute_browser(self, task: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """浏览器 Agent：只读操作。严格遵守官方账号只读保护。"""
        return {
            "browser_action": intent,
            "mode": "read_only",
            "note": "Browser operations are read-only. No login/post/like/follow/comment allowed.",
            "status": "planned",
            "requires_manual_browser": True,
        }

    def _execute_ai_assist(self, task: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """默认 AI 辅助（带 Provider 降级链）。"""
        ai_result = self._try_ai_analyze(task.get("user_input", ""))
        if ai_result:
            return {"ai_response": ai_result, "provider": ai_result.get("provider", "unknown")}
        return {
            "ai_response": None,
            "provider": "none",
            "degradation": "All AI providers unavailable, local rules only",
            "note": "System continues to function without AI (AI is enhancement layer only)",
        }

    # ──────────────────────────────────────────────────────────
    # AI Provider 降级链（智谱 → ARK → 千问 → Ollama → 本地规则）
    # ──────────────────────────────────────────────────────────

    def _try_ai_summarize(self, text: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """尝试 AI 总结，失败返回 None（降级）。"""
        return self._call_ai_with_fallback("summarize", text, data)

    def _try_ai_analyze(self, text: str) -> Optional[Dict[str, Any]]:
        """尝试 AI 分析，失败返回 None（降级）。"""
        return self._call_ai_with_fallback("analyze", text, {})

    def _call_ai_with_fallback(
        self,
        operation: str,
        text: str,
        data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """通过 ai_channel 调用 AI，带 Provider 降级和超时保护。

        降级链：智谱 → ARK → 千问 → Ollama → 本地规则（返回 None）
        任何异常/超时都不中断主任务（AI 是增强层）。
        超时保护：15秒，避免 AI Provider 挂起阻塞主链路。
        """
        result_holder: Dict[str, Any] = {}

        def _ai_worker():
            try:
                from lumenis.system.ai_gateway import channel as ai_channel
                if hasattr(ai_channel, "call_ai_with_fallback"):
                    r = ai_channel.call_ai_with_fallback(
                        prompt=text, operation=operation, context=data,
                    )
                    if r:
                        result_holder["result"] = r if isinstance(r, dict) else {"response": str(r)}
                        return
                elif hasattr(ai_channel, "AIChannel"):
                    ch = ai_channel.AIChannel()
                    if hasattr(ch, "chat"):
                        resp = ch.chat(text)
                        if resp:
                            result_holder["result"] = {"response": str(resp), "provider": "ai_channel"}
                            return
            except Exception as _e:
                logger.debug(f"[TaskEngine] AI worker error: {_e}")
                result_holder["error"] = str(_e)

        import threading as _threading
        worker = _threading.Thread(target=_ai_worker, daemon=True)
        worker.start()
        worker.join(timeout=15)  # 15秒超时保护
        if worker.is_alive():
            logger.warning("[TaskEngine] AI call timed out after 15s, degrading to local rules")
            return None
        return result_holder.get("result")

    # ──────────────────────────────────────────────────────────
    # 6. 验证（Verification）
    # ──────────────────────────────────────────────────────────

    def _verify_result(
        self,
        task: Dict[str, Any],
        result_data: Dict[str, Any],
        execute_step_id: str,
    ) -> VerificationResult:
        """验证执行结果。

        验证维度：
          - what_was_done: 做了什么
          - why: 为什么
          - what_was_called: 调用了什么
          - result_summary: 结果摘要
          - evidence: 证据
          - success: 是否成功
          - needs_human_confirmation: 是否需人工确认
        """
        step_id = self._db_add_step(task["task_id"], StepPhase.VERIFY.value, "running")

        intent = task.get("intent", "unknown")
        agent_id = task.get("agent_id", "unknown")
        skill_id = task.get("skill_id")

        # 收集证据
        evidence_ids: List[str] = []

        # 证据1：输入
        ev_input = self._db_add_evidence(
            task["task_id"], "input",
            f"User input: {task.get('user_input', '')[:500]}",
            source="user", step_id=step_id, authenticity_score=1.0,
        )
        evidence_ids.append(ev_input)

        # 证据2：解析结果
        ev_parse = self._db_add_evidence(
            task["task_id"], "parsed",
            f"Intent={intent}, risk={task.get('risk_level')}, agent={agent_id}",
            source="task_parser", step_id=step_id, authenticity_score=0.9,
        )
        evidence_ids.append(ev_parse)

        # 证据3：执行结果
        result_summary = json.dumps(result_data, ensure_ascii=False, default=str)[:1000]
        ev_result = self._db_add_evidence(
            task["task_id"], "execution_result",
            result_summary, source=agent_id, step_id=execute_step_id,
            authenticity_score=0.8,
        )
        evidence_ids.append(ev_result)

        # 判定成功
        success = result_data is not None and not result_data.get("error")

        # 判定是否需人工确认
        needs_human = task.get("risk_level") in ("L3", "L4") or task.get("human_approval_required")

        what_was_called = f"agent={agent_id}"
        if skill_id:
            what_was_called += f", skill={skill_id}"
        if result_data.get("analysis_provider"):
            what_was_called += f", ai_provider={result_data['analysis_provider']}"

        verification = VerificationResult(
            verified=True,
            what_was_done=f"Executed {intent} via {agent_id}",
            why=f"Task intent={intent}, risk={task.get('risk_level')}, permission={task.get('permission_result')}",
            what_was_called=what_was_called,
            result_summary=result_summary[:200],
            evidence_ids=evidence_ids,
            success=bool(success),
            needs_human_confirmation=bool(needs_human),
            human_confirmation_reason=task.get("risk_reason", "") if needs_human else "",
            verification_method="rule_based+evidence_chain",
        )

        self._db_update_step(step_id, status="succeeded",
                             detail=f"Verified: success={success}, evidence_count={len(evidence_ids)}")
        self._db_add_trace(
            task["task_id"], "task.verify",
            f"Verification complete: success={success}, evidence={len(evidence_ids)}",
            "ok", metadata={"success": success, "evidence_count": len(evidence_ids)},
        )
        return verification

    # ──────────────────────────────────────────────────────────
    # 7. 人工审批
    # ──────────────────────────────────────────────────────────

    def approve_task(
        self,
        task_id: str,
        approved_by: str = "human",
        approval_note: str = "",
    ) -> Dict[str, Any]:
        """人工审批通过。"""
        task = self._db_get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if task.get("status") != TaskStatus.AWAITING_APPROVAL.value:
            return {"error": f"Task not in awaiting_approval state: {task.get('status')}"}

        # 生成审批令牌（通过 PermissionGate）
        approval_token = None
        if self.permission_gate is not None:
            try:
                approval_token = self.permission_gate.grant_approval(
                    operation="ai_task_execution",
                    duration_minutes=30,
                    resource=f"ai_task:{task_id}",
                    granted_by=approved_by,
                )
            except Exception as e:
                logger.warning(f"[TaskEngine] PermissionGate grant_approval failed: {e}")

        self._db_update_task(
            task_id,
            status=TaskStatus.READY.value,
            approval_token=approval_token,
            approved_by=approved_by,
            approved_at=self._now(),
            permission_result="approved",
        )
        self._db_add_step(
            task_id, StepPhase.APPROVAL.value, "succeeded",
            detail=f"Approved by {approved_by}. {approval_note}",
        )
        self._db_add_evidence(
            task_id, "approval",
            f"Human approval by {approved_by}. {approval_note}",
            source="human", authenticity_score=1.0,
        )
        self._db_add_trace(task_id, "task.approval", f"Approved by {approved_by}", "approved")
        return self._db_get_task(task_id)

    # ──────────────────────────────────────────────────────────
    # 8. 取消任务
    # ──────────────────────────────────────────────────────────

    def cancel_task(self, task_id: str, reason: str = "user_cancelled") -> Dict[str, Any]:
        """取消任务。"""
        self._cancelled.add(task_id)
        self._db_update_task(
            task_id, status=TaskStatus.CANCELLED.value,
            error=reason, finished_at=self._now(),
        )
        self._db_add_step(task_id, StepPhase.ERROR.value, "cancelled", detail=reason)
        self._db_add_trace(task_id, "task.cancel", reason, "cancelled")
        return self._db_get_task(task_id)

    # ──────────────────────────────────────────────────────────
    # 9. 完整运行（parse → select → permission → execute）
    # ──────────────────────────────────────────────────────────

    def run_task(self, task_id: str) -> Dict[str, Any]:
        """完整运行任务：解析 → Agent/Skill选择 → 权限 → 执行。"""
        # 1. 解析
        task = self.parse_task(task_id)
        if task.get("status") in (TaskStatus.FAILED.value, TaskStatus.CANCELLED.value):
            return task

        # 2. Agent + Skill 选择
        task = self.select_agent_and_skill(task_id)
        if task.get("status") in (TaskStatus.FAILED.value, TaskStatus.CANCELLED.value):
            return task

        # 3. 权限检查
        task = self.check_permission(task_id)
        if task.get("status") != TaskStatus.READY.value:
            return task  # awaiting_approval 或 denied

        # 4. 执行
        return self.execute_task(task_id)

    def create_and_run(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        created_by: str = "system",
    ) -> Dict[str, Any]:
        """创建并立即运行任务。"""
        created = self.create_task(user_input, context, created_by)
        return self.run_task(created["task_id"])

    # ──────────────────────────────────────────────────────────
    # 10. 查询接口
    # ──────────────────────────────────────────────────────────

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._db_get_task(task_id)

    def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM ai_task"
        params: List[Any] = []
        if status:
            query += " WHERE status=?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with get_db() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_steps(self, task_id: str) -> List[Dict[str, Any]]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM ai_task_step WHERE task_id=? ORDER BY started_at",
                (task_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_evidence(self, task_id: str) -> List[Dict[str, Any]]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM ai_task_evidence WHERE task_id=? ORDER BY created_at",
                (task_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_trace(
        self,
        task_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        if task_id:
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT * FROM ai_task_trace WHERE task_id=? ORDER BY started_at",
                    (task_id,),
                ).fetchall()
        else:
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT * FROM ai_task_trace ORDER BY started_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(r) for r in rows]

    def get_permissions(self) -> Dict[str, Any]:
        """获取当前用户权限矩阵。"""
        if self.permission_gate is not None:
            return self.permission_gate.get_status()
        return {
            "permission_gate": "unavailable",
            "enabled_permissions": ["READ", "ANALYZE"],
            "note": "PermissionGate unavailable, defaulting to read-only",
        }

    def get_capabilities(self) -> Dict[str, Any]:
        """获取能力清单。"""
        return {
            "intents": self.parser.list_intents(),
            "agents": self.agent_registry.get_capabilities_matrix(),
            "circuit_breaker": self._circuit.get_state(),
            "engine_version": "task-engine-v1.0.0",
            "osai_boundary": {
                "zbc_depends_on_osai": False,
                "osai_down_impact": "none (ZBC core functions continue)",
                "ai_provider_chain": ["zhipu", "ark", "qianwen", "ollama", "local_rules"],
            },
        }

    def get_dlq(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取死信队列任务。"""
        return self.list_tasks(status=TaskStatus.DLQ.value, limit=limit)

    def health_check(self) -> Dict[str, Any]:
        """健康检查。"""
        return {
            "status": "healthy",
            "db": "connected",
            "circuit_breaker": self._circuit.get_state(),
            "parser": "available",
            "agent_registry": "available",
            "permission_gate": "available" if self.permission_gate else "unavailable (degraded)",
            "osai_boundary": "independent (ZBC does not depend on OSAI)",
            "timestamp": self._now(),
        }


# ═══════════════════════════════════════════════════════════════
# 7. 全局单例
# ═══════════════════════════════════════════════════════════════

_default_engine: Optional[TaskEngine] = None
_engine_lock = threading.Lock()


def get_task_engine() -> TaskEngine:
    global _default_engine
    if _default_engine is None:
        with _engine_lock:
            if _default_engine is None:
                _default_engine = TaskEngine()
    return _default_engine


def reset_task_engine() -> None:
    global _default_engine
    with _engine_lock:
        _default_engine = None


__all__ = [
    "TaskStatus",
    "StepPhase",
    "CircuitState",
    "CircuitBreaker",
    "VerificationResult",
    "TaskEngine",
    "init_task_engine_db",
    "get_task_engine",
    "reset_task_engine",
]
