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
  8. AI Provider 路由：复用 SYSTEM AI Gateway，失败时保留明确降级状态

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
import math
import re
import secrets
import sqlite3
import threading
import time
import uuid
from contextlib import nullcontext
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from lumenis.shared.database import get_repository, main_db_path

logger = logging.getLogger(__name__)
_AI_CALL_TIMEOUT_SECONDS = 15.0
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


_MANAGED_REPORT_TASK_PREFIX = "rbrief_"
_MANAGED_REPORT_TASK_CREATOR = "shared.reporting.source_brief"
_MANAGED_REPORT_TASK_ID_RE = re.compile(
    r"^rbrief_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_TRAINING_RECEIPT_TASK_PREFIX = "trainrelay_"
_TRAINING_RECEIPT_TASK_CREATOR = "owned_training_phase_receipts:v1"
_TRAINING_RECEIPT_TASK_ID_RE = re.compile(
    r"^trainrelay_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_TRAINING_RECEIPT_OWNER = "owned_training_phase_receipts:v1"
_TRAINING_RECEIPT_USER_INPUT = "Owned training phase receipt state"
_TRAINING_RECEIPT_FINGERPRINT_FIELDS = (
    "request_sha256", "model_identity_sha256", "manifest_sha256", "train_sha256",
    "heldout_sha256", "recipe_sha256", "scope_sha256",
)
_TRAINING_RECEIPT_CONTEXT_FIELDS = frozenset({
    "managed_owner", "binding", "fingerprints", "run_digest", "task_digest",
    "next_sequence", "last_receipt_sha256",
})
_TRAINING_RECEIPT_V2_CONTEXT_FIELDS = _TRAINING_RECEIPT_CONTEXT_FIELDS | {"admission"}
_TRAINING_ADMISSION_FIELDS = frozenset({
    "schema_version", "approval_reference", "public_key_pin", "last_phase",
    "pending_step_id", "terminal",
})
_TRAINING_APPROVAL_REFERENCE_FIELDS = frozenset({
    "schema_version", "operation", "resource", "approval_token_sha256",
    "issuance_audit_id", "granted_by", "granted_at", "expires_at",
})
_TRAINING_PHASES = frozenset({
    "initial", "before_output_dir", "before_train", "step_begin", "substep_end",
    "pre_optimizer_step", "before_adapter_save", "before_tokenizer_save",
    "after_saved_artifact_check",
})
_TRAINING_PHASE_TRANSITIONS = {
    None: frozenset({"initial"}),
    "initial": frozenset({"before_output_dir"}),
    "before_output_dir": frozenset({"before_train"}),
    "before_train": frozenset({"step_begin"}),
    "step_begin": frozenset({"substep_end", "pre_optimizer_step"}),
    "substep_end": frozenset({"substep_end", "pre_optimizer_step"}),
    "pre_optimizer_step": frozenset({"step_begin", "before_adapter_save"}),
    "before_adapter_save": frozenset({"before_tokenizer_save"}),
    "before_tokenizer_save": frozenset({"after_saved_artifact_check"}),
    "after_saved_artifact_check": frozenset(),
}
_TRAINING_TERMINAL_PHASE = "after_saved_artifact_check"
_REPORT_AUDIT_REF_RE = re.compile(r"^aud_[0-9a-f]{16}$")
_REPORT_IMAGE_REF_RE = re.compile(r"^ART-[0-9a-f]{16}$")
_REPORT_CONTEXT_KEYS = frozenset({
    "actor_ref", "scope", "job_id", "limit", "image_source_ref",
    "business_question", "permission_audit_ref",
})
_REPORT_CONTEXT_OPTIONAL_KEYS = frozenset({"operation_audit_ref", "source_ids", "revision", "research", "request_id", "reference"})
_REPORT_SCOPE_KEYS = frozenset({
    "product_id", "global_scope", "entity_label", "subject_id",
    "brand_focus_id",
})


def _is_managed_report_task_id(task_id: Any) -> bool:
    return type(task_id) is str and task_id.startswith(_MANAGED_REPORT_TASK_PREFIX)


def _guard_generic_task_access(task_id: Any) -> None:
    if type(task_id) is str and task_id.startswith("task-pitch-"):
        raise PermissionError("internal pitch tasks require their managed owner methods")
    if _is_managed_report_task_id(task_id):
        raise PermissionError(
            "managed report tasks are accessible only through report-task methods"
        )
    if _is_training_receipt_task_id(task_id):
        raise PermissionError(
            "training receipt tasks are accessible only through training-receipt methods"
        )


def _is_training_receipt_task_id(task_id: Any) -> bool:
    return type(task_id) is str and task_id.startswith(_TRAINING_RECEIPT_TASK_PREFIX)


def _require_training_receipt_task_id(task_id: Any) -> str:
    if not _is_training_receipt_task_id(task_id):
        raise PermissionError("task is not a managed training receipt task")
    if _TRAINING_RECEIPT_TASK_ID_RE.fullmatch(task_id) is None:
        raise ValueError("managed training receipt task id is malformed")
    try:
        parsed = uuid.UUID(task_id.removeprefix(_TRAINING_RECEIPT_TASK_PREFIX))
    except (AttributeError, TypeError, ValueError):
        raise ValueError("managed training receipt task id is malformed") from None
    if parsed.version != 4 or str(parsed) != task_id.removeprefix(_TRAINING_RECEIPT_TASK_PREFIX):
        raise ValueError("managed training receipt task id is not a canonical UUID4")
    return task_id


def _require_managed_report_task_id(task_id: Any) -> str:
    if not _is_managed_report_task_id(task_id):
        raise PermissionError("task is not a managed report task")
    if _MANAGED_REPORT_TASK_ID_RE.fullmatch(task_id) is None:
        raise ValueError("managed report task id is malformed")
    return task_id


def _strict_json_object_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def _strict_json_loads(raw: Any, *, field_name: str) -> Any:
    if type(raw) is not str:
        raise ValueError(f"{field_name} must be JSON text")
    try:
        return json.loads(
            raw,
            object_pairs_hook=_strict_json_object_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"invalid JSON constant: {value}")
            ),
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"{field_name} contains malformed JSON") from exc


def _serialize_strict_json(value: Any, *, field_name: str) -> str:
    try:
        encoded = json.dumps(
            value, ensure_ascii=False, allow_nan=False, sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} is not valid JSON data") from exc
    _strict_json_loads(encoded, field_name=field_name)
    return encoded


def _validate_training_receipt_fingerprints(value: Any) -> Dict[str, str]:
    if type(value) is not dict or set(value) != set(_TRAINING_RECEIPT_FINGERPRINT_FIELDS):
        raise ValueError("training receipt fingerprints have missing or unsupported fields")
    result = {}
    for name in _TRAINING_RECEIPT_FINGERPRINT_FIELDS:
        digest = value.get(name)
        if type(digest) is not str or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError(f"training receipt {name} must be a lowercase SHA-256 digest")
        result[name] = digest
    return result


def _validate_training_receipt_binding(value: Any) -> Dict[str, Any]:
    if type(value) is not dict or set(value) != {"resource", "identity", "scope_descriptors"}:
        raise ValueError("training receipt binding has missing or unsupported fields")
    resource = value.get("resource")
    if type(resource) is not str or re.fullmatch(r"owned_training:v1:[0-9a-f]{64}", resource) is None:
        raise ValueError("training receipt resource is invalid")

    identity = value.get("identity")
    identity_keys = {"actor_id", "caller", "principal_kind", "principal_ref"}
    if type(identity) is not dict or set(identity) != identity_keys:
        raise ValueError("training receipt identity has missing or unsupported fields")
    actor_id = identity.get("actor_id")
    caller = identity.get("caller")
    principal_kind = identity.get("principal_kind")
    principal_ref = identity.get("principal_ref")
    if actor_id is not None:
        if (type(actor_id) is not int or actor_id <= 0
                or caller != f"actor:{actor_id}"
                or principal_kind is not None or principal_ref is not None):
            raise ValueError("training receipt account identity is incoherent")
    elif not (
        caller == "workspace:local"
        and principal_kind == "local_workspace"
        and principal_ref == "workspace:local"
    ):
        raise ValueError("training receipt workspace identity is incoherent")
    normalized_identity = {
        "actor_id": actor_id, "caller": caller,
        "principal_kind": principal_kind, "principal_ref": principal_ref,
    }

    descriptors = value.get("scope_descriptors")
    if type(descriptors) is not dict or not descriptors:
        raise ValueError("training receipt scope descriptors must be a non-empty object")
    normalized_descriptors = {}
    descriptor_keys = {"domain_id", "product_id", "global_scope", "subject_id", "brand_focus_id"}
    for scope, descriptor in descriptors.items():
        if (type(scope) is not str or not scope or scope != scope.strip()
                or len(scope) > 256 or any(ord(char) < 32 for char in scope)
                or type(descriptor) is not dict or set(descriptor) != descriptor_keys):
            raise ValueError("training receipt scope descriptor is invalid")
        domain_id = descriptor.get("domain_id")
        product_id = descriptor.get("product_id")
        global_scope = descriptor.get("global_scope")
        subject_id = descriptor.get("subject_id")
        brand_focus_id = descriptor.get("brand_focus_id")
        if (type(global_scope) is not bool
                or domain_id not in {"cth", "bmp"}
                or product_id != ("CTH" if domain_id == "cth" else "ZBMP")):
            raise ValueError("training receipt scope descriptor domain is invalid")
        if global_scope:
            valid_scope = scope == "GLOBAL / ALL" and subject_id is None and brand_focus_id is None
        elif domain_id == "cth":
            valid_scope = (
                type(subject_id) is str and bool(subject_id) and subject_id == subject_id.strip()
                and len(subject_id) <= 256 and not any(ord(char) < 32 for char in subject_id)
                and scope == subject_id and brand_focus_id is None
            )
        else:
            valid_scope = (
                type(brand_focus_id) is str and bool(brand_focus_id)
                and brand_focus_id == brand_focus_id.strip() and len(brand_focus_id) <= 256
                and not any(ord(char) < 32 for char in brand_focus_id)
                and scope == brand_focus_id and subject_id is None
            )
        if not valid_scope:
            raise ValueError("training receipt scope descriptor does not match its scope")
        normalized_descriptors[scope] = {
            "domain_id": domain_id, "product_id": product_id,
            "global_scope": global_scope, "subject_id": subject_id,
            "brand_focus_id": brand_focus_id,
        }
    return {
        "resource": resource, "identity": normalized_identity,
        "scope_descriptors": normalized_descriptors,
    }


def _validate_training_approval_reference(value: Any) -> Dict[str, Any]:
    if type(value) is not dict or set(value) != _TRAINING_APPROVAL_REFERENCE_FIELDS:
        raise ValueError("training approval reference has missing or unsupported fields")
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("training approval reference schema is invalid")
    if value.get("operation") != "model_train":
        raise ValueError("training approval reference operation is invalid")
    resource = value.get("resource")
    if type(resource) is not str or re.fullmatch(r"owned_training:v1:[0-9a-f]{64}", resource) is None:
        raise ValueError("training approval reference resource is invalid")
    token_digest = value.get("approval_token_sha256")
    if type(token_digest) is not str or re.fullmatch(r"[0-9a-f]{64}", token_digest) is None:
        raise ValueError("training approval reference token digest is invalid")
    if type(value.get("issuance_audit_id")) is not str or _REPORT_AUDIT_REF_RE.fullmatch(value["issuance_audit_id"]) is None:
        raise ValueError("training approval reference issuance audit is invalid")
    granted_by = value.get("granted_by")
    if (type(granted_by) is not str or not granted_by.strip()
            or len(granted_by) > 256 or any(ord(character) < 32 for character in granted_by)):
        raise ValueError("training approval reference grant owner is invalid")

    parsed_times = []
    for field_name in ("granted_at", "expires_at"):
        raw = value.get(field_name)
        if type(raw) is not str or len(raw) > 64:
            raise ValueError("training approval reference time is invalid")
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            raise ValueError("training approval reference time is invalid") from None
        if parsed.timestamp() <= 0:
            raise ValueError("training approval reference timestamp must be positive")
        parsed_times.append(parsed.timestamp())
    if parsed_times[1] <= parsed_times[0]:
        raise ValueError("training approval reference expiry must follow issuance")
    return {name: value[name] for name in (
        "schema_version", "operation", "resource", "approval_token_sha256",
        "issuance_audit_id", "granted_by", "granted_at", "expires_at",
    )}


def _validate_training_public_key_pin(value: Any) -> Dict[str, Any]:
    from lumenis.system.security.training_receipts import _validate_pinned_public_key

    if type(value) is not dict:
        raise ValueError("training receipt public key pin is invalid")
    key_id, _public_key = _validate_pinned_public_key(value)
    if key_id != value.get("key_id"):
        raise ValueError("training receipt public key pin is invalid")
    return {
        "schema_version": value["schema_version"],
        "key_id": value["key_id"],
        "algorithm": value["algorithm"],
        "public_key": value["public_key"],
    }


def _validate_training_admission(value: Any) -> Dict[str, Any]:
    if type(value) is not dict or set(value) != _TRAINING_ADMISSION_FIELDS:
        raise ValueError("sealed training admission has missing or unsupported fields")
    if type(value.get("schema_version")) is not int or value["schema_version"] != 2:
        raise ValueError("sealed training admission schema is invalid")
    approval_reference = _validate_training_approval_reference(value.get("approval_reference"))
    public_key_pin = _validate_training_public_key_pin(value.get("public_key_pin"))
    last_phase = value.get("last_phase")
    if last_phase is not None and (type(last_phase) is not str or last_phase not in _TRAINING_PHASES):
        raise ValueError("sealed training admission phase is invalid")
    pending_step_id = value.get("pending_step_id")
    if pending_step_id is not None and (
        type(pending_step_id) is not str
        or re.fullmatch(r"trainphase_[0-9a-f]{64}", pending_step_id) is None
    ):
        raise ValueError("sealed training admission pending step is invalid")
    terminal = value.get("terminal")
    if type(terminal) is not bool:
        raise ValueError("sealed training admission terminal flag is invalid")
    if terminal != (last_phase == _TRAINING_TERMINAL_PHASE) or (terminal and pending_step_id is not None):
        raise ValueError("sealed training admission terminal state is incoherent")
    return {
        "schema_version": 2,
        "approval_reference": approval_reference,
        "public_key_pin": public_key_pin,
        "last_phase": last_phase,
        "pending_step_id": pending_step_id,
        "terminal": terminal,
    }


def _training_phase_now(now: Optional[int]) -> int:
    if now is None:
        return int(time.time())
    if type(now) is not int or now <= 0:
        raise ValueError("training phase clock must be a positive integer")
    return now


def _training_approval_expiry_seconds(reference: Dict[str, Any]) -> int:
    parsed = datetime.fromisoformat(reference["expires_at"].replace("Z", "+00:00"))
    return int(parsed.timestamp())


def _training_phase_step_id(task_id: str, nonce: str) -> str:
    return "trainphase_" + hashlib.sha256((task_id + nonce).encode("utf-8")).hexdigest()


def _training_phase_transition_allowed(last_phase: Optional[str], phase: str) -> bool:
    return phase in _TRAINING_PHASE_TRANSITIONS.get(last_phase, frozenset())


def _training_challenge_matches_context(challenge: Dict[str, Any], context: Dict[str, Any]) -> bool:
    expected = {
        "run_digest": context["run_digest"],
        "task_digest": context["task_digest"],
        **context["fingerprints"],
        "sequence": context["next_sequence"],
    }
    return all(challenge.get(name) == value for name, value in expected.items())


def _training_receipt_task_digest(task_id: str) -> str:
    return hashlib.sha256(task_id.encode("utf-8")).hexdigest()


def _training_receipt_public_state(task_id: str, context: Dict[str, Any], status: str) -> Dict[str, Any]:
    public = {
        "task_id": task_id,
        "run_digest": context["run_digest"],
        "task_digest": context["task_digest"],
        "next_sequence": context["next_sequence"],
        "fingerprints": dict(context["fingerprints"]),
        "status": status,
    }
    admission = context.get("admission")
    if admission is not None:
        public.update({
            "admission_version": 2,
            "pinned_public_key": dict(admission["public_key_pin"]),
            "last_phase": admission["last_phase"],
            "terminal": admission["terminal"],
        })
    return public


def _validate_training_receipt_context(
    raw: Any, *, task_id: str, expected_binding: Dict[str, Any],
) -> Dict[str, Any]:
    context = _strict_json_loads(raw, field_name="training receipt task context")
    if (type(context) is not dict
            or (set(context) != _TRAINING_RECEIPT_CONTEXT_FIELDS
                and set(context) != _TRAINING_RECEIPT_V2_CONTEXT_FIELDS)):
        raise ValueError("training receipt task context has missing or unsupported fields")
    if context.get("managed_owner") != _TRAINING_RECEIPT_OWNER:
        raise PermissionError("task is not owned by the training receipt state owner")
    binding = _validate_training_receipt_binding(context.get("binding"))
    if binding != expected_binding:
        raise PermissionError("training receipt task binding does not match the expected binding")
    fingerprints = _validate_training_receipt_fingerprints(context.get("fingerprints"))
    if (type(context.get("task_digest")) is not str
            or context["task_digest"] != _training_receipt_task_digest(task_id)):
        raise ValueError("training receipt task digest does not match its task ID")
    if type(context.get("run_digest")) is not str or re.fullmatch(r"[0-9a-f]{64}", context["run_digest"]) is None:
        raise ValueError("training receipt run digest is invalid")
    sequence = context.get("next_sequence")
    if type(sequence) is not int or not 1 <= sequence <= 1_000_000_000:
        raise ValueError("training receipt next sequence is invalid")
    last_receipt = context.get("last_receipt_sha256")
    if last_receipt is not None and (
        type(last_receipt) is not str or re.fullmatch(r"[0-9a-f]{64}", last_receipt) is None
    ):
        raise ValueError("training receipt last receipt hash is invalid")
    normalized = {
        "managed_owner": _TRAINING_RECEIPT_OWNER,
        "binding": binding,
        "fingerprints": fingerprints,
        "run_digest": context["run_digest"],
        "task_digest": context["task_digest"],
        "next_sequence": sequence,
        "last_receipt_sha256": last_receipt,
    }
    if "admission" in context:
        normalized["admission"] = _validate_training_admission(context["admission"])
    return normalized


def _valid_report_text(value: Any, max_length: int) -> bool:
    return (
        type(value) is str
        and len(value) <= max_length
        and not any(ord(character) == 0 for character in value)
    )


def _valid_report_scope_id(value: Any) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value) <= 256
        and not any(ord(character) < 32 for character in value)
    )


def _validate_managed_report_context(context: Any) -> Dict[str, Any]:
    """Validate and snapshot the server-derived Source Brief task context.

    This is a storage contract only. Callers must authorize the real request
    through SYSTEM Permission before creating or running a managed report task.
    """
    if type(context) is not dict:
        raise ValueError("managed report context must be an object")
    keys = set(context)
    if (
        not _REPORT_CONTEXT_KEYS.issubset(keys)
        or not keys.issubset(_REPORT_CONTEXT_KEYS | _REPORT_CONTEXT_OPTIONAL_KEYS)
    ):
        raise ValueError("managed report context has missing or unsupported fields")

    actor_ref = context.get("actor_ref")
    valid_actor = (
        actor_ref == "workspace:local"
        or (
            type(actor_ref) is str
            and re.fullmatch(r"actor:[1-9][0-9]{0,18}", actor_ref) is not None
        )
    )
    if not valid_actor:
        raise ValueError("managed report actor_ref is invalid")

    scope = context.get("scope")
    shared = scope == {"scope_kind": "shared_workspace", "version": 1} and type(scope.get("version")) is int
    if not shared:
        if type(scope) is not dict or set(scope) != _REPORT_SCOPE_KEYS:
            raise ValueError("managed report scope has missing or unsupported fields")
        product_id = scope.get("product_id")
        global_scope = scope.get("global_scope")
        entity_label = scope.get("entity_label")
        subject_id = scope.get("subject_id")
        brand_focus_id = scope.get("brand_focus_id")
        if (
            product_id not in {"CTH", "ZBMP"}
            or type(global_scope) is not bool
            or not _valid_report_text(entity_label, 256)
            or not entity_label.strip()
        ):
            raise ValueError("managed report scope is invalid")
        if global_scope:
            if subject_id is not None or brand_focus_id is not None:
                raise ValueError("global managed report scope must not carry a focus id")
        elif product_id == "CTH":
            if not _valid_report_scope_id(subject_id) or brand_focus_id is not None:
                raise ValueError("CTH managed report scope requires only subject_id")
        elif not _valid_report_scope_id(brand_focus_id) or subject_id is not None:
            raise ValueError("BMP managed report scope requires only brand_focus_id")

    job_id = context.get("job_id")
    if type(job_id) is not str or re.fullmatch(r"brief-[0-9a-f]{32}", job_id) is None:
        raise ValueError("managed report job_id is invalid")

    revision = context.get("revision")
    if revision is not None:
        if type(revision) is not dict or set(revision) != {"parent_job_id", "review_id"}:
            raise ValueError("managed report revision reference is invalid")
        parent_job_id, review_id = revision["parent_job_id"], revision["review_id"]
        if (type(parent_job_id) is not str
                or re.fullmatch(r"brief-[0-9a-f]{32}", parent_job_id) is None
                or parent_job_id == job_id or type(review_id) is not str
                or re.fullmatch(r"ART-[0-9a-f]{16}" if shared else r"[0-9a-f]{64}", review_id) is None):
            raise ValueError("managed report revision reference is invalid")

    limit = context.get("limit")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("managed report limit must be an integer from 1 to 100")

    image_source_ref = context.get("image_source_ref")
    if image_source_ref is not None and (
        type(image_source_ref) is not str
        or _REPORT_IMAGE_REF_RE.fullmatch(image_source_ref) is None
    ):
        raise ValueError("managed report image_source_ref is invalid")

    question = context.get("business_question")
    if question is not None and (
        not _valid_report_text(question, 1500)
        or not 4 <= len(question.strip()) <= 1500
    ):
        raise ValueError("managed report business_question is invalid")
    from canonical_data import validate_source_ids
    validate_source_ids(context.get("source_ids"), limit=min(limit, 8) if question is not None else limit)

    request_id = context.get("request_id")
    if request_id is not None and (type(request_id) is not str or re.fullmatch(r"[A-Za-z0-9_-]{8,128}", request_id) is None):
        raise ValueError("SOURCE_BRIEF_REQUEST_ID_INVALID")
    reference = context.get("reference")
    if reference is not None:
        if (type(reference) is not dict or set(reference) != {"artifact_id", "sha256", "work_id", "version"}
                or type(reference.get("version")) is not int or reference["version"] < 1
                or re.fullmatch(r"ART-[0-9a-f]{16}", str(reference.get("artifact_id"))) is None
                or re.fullmatch(r"[0-9a-f]{64}", str(reference.get("sha256"))) is None
                or re.fullmatch(r"WORK-[0-9a-f]{24}", str(reference.get("work_id"))) is None):
            raise ValueError("RESEARCH_REFERENCE_INVALID")
    research = context.get("research")
    if research is not None:
        if type(research) is not dict or set(research) - {"dimension", "regions", "languages", "decision_brief"}:
            raise ValueError("RESEARCH_METADATA_INVALID")
        from agent_research.source_bound import analyze_source_records
        analyze_source_records("Validate research metadata", [], **research)

    permission_audit_ref = context.get("permission_audit_ref")
    if (
        type(permission_audit_ref) is not str
        or _REPORT_AUDIT_REF_RE.fullmatch(permission_audit_ref) is None
    ):
        raise ValueError("managed report permission_audit_ref is invalid")
    if "operation_audit_ref" in context:
        operation_audit_ref = context["operation_audit_ref"]
        if (
            type(operation_audit_ref) is not str
            or _REPORT_AUDIT_REF_RE.fullmatch(operation_audit_ref) is None
        ):
            raise ValueError("managed report operation_audit_ref is invalid")

    # JSON round-trip gives the stored task a detached, immutable-by-caller snapshot.
    return _strict_json_loads(
        _serialize_strict_json(context, field_name="managed report context"),
        field_name="managed report context",
    )


def _validate_managed_report_parameters(value: Any) -> Dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("managed report parameters must be an object")
    if not value:
        return value
    if set(value) != {"worker_pid", "worker_started_at"}:
        raise ValueError("managed report worker identity is malformed")
    worker_pid = value.get("worker_pid")
    worker_started_at = value.get("worker_started_at")
    if (
        type(worker_pid) is not int or worker_pid <= 0
        or type(worker_started_at) not in (int, float)
        or not math.isfinite(worker_started_at) or worker_started_at <= 0
    ):
        raise ValueError("managed report worker identity is malformed")
    return value


def _current_report_worker_identity() -> Dict[str, Any]:
    try:
        import psutil

        identity = {
            "worker_pid": os.getpid(),
            "worker_started_at": psutil.Process().create_time(),
        }
    except Exception as exc:
        raise RuntimeError("cannot verify managed report worker identity") from exc
    return _validate_managed_report_parameters(identity)


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
    verification_scope: str = "EXECUTION_RETURN"
    outcome_status: str = "NOT_VERIFIED"
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
        self._agent_zero_lock_guard = threading.Lock()
        self._agent_zero_task_locks: Dict[str, Any] = {}

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

    def _claim_agent_zero_attempt(self, task_id: str, attempt: Dict[str, Any]) -> bool:
        """Persist the one-shot GUI dispatch claim before any external request."""
        from agent_runtime.agent_zero_gui_executor import AGENT_ZERO_TASK_RECORD

        if (attempt.get("task_id") != task_id or attempt.get("state") != "dispatching"
                or not isinstance(attempt.get("attempt_id"), str)):
            return False
        with self._agent_zero_task_lock(task_id):
            if task_id in self._cancelled:
                return False
            with get_repository().transaction(timeout=30) as conn:
                row = conn.execute(
                    "SELECT parameters_json, permission_result, status FROM ai_task WHERE task_id=?",
                    (task_id,),
                ).fetchone()
                if row is None or row["permission_result"] != "allowed":
                    return False
                if row["status"] not in {TaskStatus.RUNNING.value, TaskStatus.READY.value}:
                    return False
                raw = row["parameters_json"] or "{}"
                params = _strict_json_loads(raw, field_name="Agent Zero task parameters")
                if type(params) is not dict or AGENT_ZERO_TASK_RECORD in params:
                    return False
                params[AGENT_ZERO_TASK_RECORD] = dict(attempt)
                encoded = _serialize_strict_json(params, field_name="Agent Zero task parameters")
                cursor = conn.execute(
                    "UPDATE ai_task SET parameters_json=?, updated_at=? "
                    "WHERE task_id=? AND parameters_json=? AND permission_result='allowed' AND status IN ('running','ready')",
                    (encoded, self._now(), task_id, raw),
                )
                return cursor.rowcount == 1

    def _transition_agent_zero_attempt(
        self, task_id: str, attempt_id: str, replacement: Dict[str, Any],
    ) -> bool:
        """CAS an existing dispatch record without creating a second attempt."""
        from agent_runtime.agent_zero_gui_executor import AGENT_ZERO_TASK_RECORD

        if (replacement.get("task_id") != task_id
                or replacement.get("attempt_id") != attempt_id
                or replacement.get("state") not in {
                    "dispatching", "submitted", "outcome_unknown", "completed", "failed", "cancelled",
                }):
            return False
        allowed = {
            "dispatching": {"submitted", "outcome_unknown", "completed", "failed", "cancelled"},
            "submitted": {"submitted", "outcome_unknown", "completed", "failed", "cancelled"},
            "outcome_unknown": {"outcome_unknown", "cancelled"},
        }
        with self._agent_zero_task_lock(task_id), get_repository().transaction(timeout=30) as conn:
            row = conn.execute(
                "SELECT parameters_json FROM ai_task WHERE task_id=?", (task_id,),
            ).fetchone()
            if row is None:
                return False
            raw = row["parameters_json"] or "{}"
            params = _strict_json_loads(raw, field_name="Agent Zero task parameters")
            if type(params) is not dict:
                return False
            current = params.get(AGENT_ZERO_TASK_RECORD)
            if (type(current) is not dict or current.get("attempt_id") != attempt_id
                    or replacement["state"] not in allowed.get(current.get("state"), set())):
                return False
            params[AGENT_ZERO_TASK_RECORD] = dict(replacement)
            encoded = _serialize_strict_json(params, field_name="Agent Zero task parameters")
            cursor = conn.execute(
                "UPDATE ai_task SET parameters_json=?, updated_at=? WHERE task_id=? AND parameters_json=?",
                (encoded, self._now(), task_id, raw),
            )
            return cursor.rowcount == 1

    def _agent_zero_task_lock(self, task_id: str) -> Any:
        with self._agent_zero_lock_guard:
            lock = self._agent_zero_task_locks.get(task_id)
            if lock is None:
                # Reentrant because cancellation owns the lock while recording
                # the worker receipt through the same CAS callback.
                lock = threading.RLock()
                self._agent_zero_task_locks[task_id] = lock
            return lock

    def _agent_zero_permission(self, task_id: str, action: str) -> Dict[str, Any]:
        """Obtain a fresh exact Permission receipt before an Agent Zero effect."""
        try:
            gate = self.permission_gate
            if gate is None:
                return {}
            from lumenis.system.security import OperationType

            operation_id = f"agent_zero_{action}_{task_id}"
            result = gate.check(
                operation_type=OperationType.BROWSER_OPERATION,
                resource=f"ai_task:{task_id}",
                caller="task_engine",
                operation_id=operation_id,
            )
            return {
                "allowed": result.allowed is True,
                "operation_type": result.operation_type,
                "resource": result.resource,
                "operation_id": result.operation_id,
                "requires_approval": result.requires_approval is True,
                "audit_id": result.audit_id,
            }
        except Exception:
            logger.warning("Agent Zero Permission recheck unavailable; request denied")
            return {}

    def _agent_zero_cancelled(self, task_id: str) -> bool:
        if task_id in self._cancelled:
            return True
        current = self._db_get_task(task_id)
        return current is None or current.get("status") not in {
            TaskStatus.RUNNING.value, TaskStatus.READY.value,
        }

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
        *,
        request_idempotency_key: Optional[str] = None,
        request_payload_sha256: Optional[str] = None,
        return_created: bool = False,
    ) -> Any:
        """创建 AI Task。

        Returns:
            任务摘要 dict
        """
        if created_by == "shared_internal_pitch":
            raise PermissionError("internal pitch tasks require their managed owner methods")
        if (created_by == _TRAINING_RECEIPT_TASK_CREATOR
                or (type(context) is dict
                    and context.get("managed_owner") == _TRAINING_RECEIPT_OWNER)):
            raise PermissionError(
                "training receipt tasks are created only through training-receipt methods"
            )
        ctx = context or {}
        if (request_idempotency_key is None) != (request_payload_sha256 is None):
            raise ValueError("TASK_REQUEST_IDEMPOTENCY_BINDING_INVALID")

        if request_idempotency_key is not None:
            if (not isinstance(request_idempotency_key, str)
                    or re.fullmatch(r"[0-9a-f]{64}", request_idempotency_key) is None
                    or not isinstance(request_payload_sha256, str)
                    or re.fullmatch(r"[0-9a-f]{64}", request_payload_sha256) is None
                    or not isinstance(ctx, dict)):
                raise ValueError("TASK_REQUEST_IDEMPOTENCY_BINDING_INVALID")
            request_binding = ctx.get("agent_task_request")
            if (not isinstance(request_binding, dict)
                    or request_binding.get("idempotency_sha256") != request_idempotency_key
                    or request_binding.get("payload_sha256") != request_payload_sha256
                    or not isinstance(request_binding.get("request_id"), str)
                    or re.fullmatch(r"[0-9a-f]{32}", request_binding["request_id"]) is None
                    or request_binding.get("actor_ref") not in {"workspace:local"}
                        and (not isinstance(request_binding.get("actor_ref"), str)
                             or re.fullmatch(r"actor:[1-9][0-9]{0,18}", request_binding["actor_ref"]) is None)
                    or not isinstance(request_binding.get("actor_sha256"), str)
                    or re.fullmatch(r"[0-9a-f]{64}", request_binding["actor_sha256"]) is None
                    or not isinstance(request_binding.get("scope_sha256"), str)
                    or re.fullmatch(r"[0-9a-f]{64}", request_binding["scope_sha256"]) is None):
                raise ValueError("TASK_REQUEST_IDEMPOTENCY_BINDING_INVALID")

            def request_digest(value):
                raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                                 allow_nan=False, separators=(",", ":"))
                return hashlib.sha256(raw.encode()).hexdigest()

            actor_ref = request_binding["actor_ref"]
            runtime_contract = ctx.get("agent_runtime")
            if actor_ref == "workspace:local":
                workspace_binding = (runtime_contract.get("workspace_binding")
                                     if isinstance(runtime_contract, dict) else None)
                actor_identity_valid = (
                    ctx.get("actor_id") is None
                    and isinstance(runtime_contract, dict)
                    and runtime_contract.get("principal_kind") == "local_workspace"
                    and runtime_contract.get("principal_ref") == actor_ref
                    and isinstance(workspace_binding, str)
                )
                actor_material = {"actor_ref": actor_ref, "workspace_binding": workspace_binding}
            else:
                actor_id = ctx.get("actor_id")
                actor_identity_valid = type(actor_id) is int and actor_ref == f"actor:{actor_id}"
                actor_material = {"actor_ref": actor_ref}
            scope_material = {"domain_id": ctx.get("domain_id"), "scope": ctx.get("scope")}
            expected_actor_sha256 = request_digest(actor_material)
            expected_scope_sha256 = request_digest(scope_material)
            expected_idempotency_sha256 = request_digest({
                "actor_sha256": expected_actor_sha256,
                "scope_sha256": expected_scope_sha256,
                "request_id": request_binding["request_id"],
            })
            if (not actor_identity_valid
                    or request_binding["actor_sha256"] != expected_actor_sha256
                    or request_binding["scope_sha256"] != expected_scope_sha256
                    or request_binding["idempotency_sha256"] != expected_idempotency_sha256):
                raise ValueError("TASK_REQUEST_IDEMPOTENCY_BINDING_INVALID")

            # The existing ai_task primary key is the atomic idempotency guard;
            # context_json carries the server-authored actor/scope/payload proof.
            # No separate task store or schema migration is needed.
            task_id = "task_" + request_idempotency_key[:32]
            now = self._now()
            created = False
            with get_db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                existing = conn.execute(
                    "SELECT user_input,context_json,created_by FROM ai_task WHERE task_id=?",
                    (task_id,),
                ).fetchone()
                if existing is not None:
                    existing_context = _strict_json_loads(
                        existing[1], field_name="agent task request context")
                    existing_binding = (existing_context.get("agent_task_request")
                                       if isinstance(existing_context, dict) else None)
                    if (existing[0] != user_input or existing[2] != created_by
                            or not isinstance(existing_binding, dict)
                            or any(existing_binding.get(key) != request_binding.get(key)
                                   for key in ("request_id", "actor_ref", "actor_sha256", "scope_sha256", "payload_sha256",
                                               "idempotency_sha256"))):
                        raise ValueError("AGENT_TASK_REQUEST_ID_CONFLICT")
                else:
                    conn.execute(
                        """INSERT INTO ai_task
                           (task_id, user_input, context_json, status, created_at, updated_at, created_by)
                           VALUES (?, ?, ?, 'pending', ?, ?, ?)""",
                        (task_id, user_input, json.dumps(ctx, ensure_ascii=False, sort_keys=True, allow_nan=False), now, now, created_by),
                    )
                    created = True
            if created:
                self._db_add_trace(task_id, "task.create", "Idempotent Agent task created", "ok")
                logger.info(f"[TaskEngine] 任务已创建: {task_id}")
            task = self._db_get_task(task_id)
            return (task, created) if return_created else task

        task_id = self._gen_id("task")
        now = self._now()
        with get_db() as conn:
            conn.execute(
                """INSERT INTO ai_task
                   (task_id, user_input, context_json, status, created_at, updated_at, created_by)
                   VALUES (?, ?, ?, 'pending', ?, ?, ?)""",
                (task_id, user_input, json.dumps(ctx, ensure_ascii=False), now, now, created_by),
            )

        self._db_add_trace(task_id, "task.create", f"Task created by {created_by}", "ok")
        logger.info(f"[TaskEngine] 任务已创建: {task_id}")

        task = {
            "task_id": task_id,
            "status": TaskStatus.PENDING.value,
            "created_at": now,
            "user_input": user_input,
        }
        return (task, True) if return_created else task

    def create_mathematical_task(self, user_input, context, *, created_by):
        """One authenticated mathematical operation survives a lost creation ACK."""
        request_id = context.get("openai_math_request_id")
        if not isinstance(request_id, str) or re.fullmatch(r"[0-9a-f]{32}", request_id) is None:
            raise ValueError("MATHEMATICAL_REQUEST_ID_REQUIRED")
        identity = hashlib.sha256(json.dumps({"actor": created_by, "request": request_id},
                                            sort_keys=True).encode()).hexdigest()
        task_id = "task_" + identity[:16]
        raw_context = json.dumps(context, ensure_ascii=False, sort_keys=True)
        now = self._now()
        with get_db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT user_input,context_json,created_by FROM ai_task WHERE task_id=?",
                                    (task_id,)).fetchone()
            if existing is not None:
                if (existing[0] != user_input or json.loads(existing[1]) != context
                        or existing[2] != created_by):
                    raise ValueError("MATHEMATICAL_REQUEST_CONTENT_CHANGED")
            else:
                conn.execute("INSERT INTO ai_task (task_id,user_input,context_json,status,created_at,updated_at,created_by) "
                             "VALUES (?,?,?,'pending',?,?,?)",
                             (task_id, user_input, raw_context, now, now, created_by))
        if existing is None:
            self._db_add_trace(task_id, "task.create", "Authenticated mathematical operation", "ok")
        return self._db_get_task(task_id)

    def create_pitch_task(self, context: Dict[str, Any], *, before_commit=None) -> Dict[str, Any]:
        """Persist internal-making intent in the existing task table, not a grant."""
        from lumenis.shared.reporting.saved_work import _digest, _json
        if (type(context) is not dict or set(context) != {"schema", "owner_context", "request_id", "input_hash", "input"}
                or context["schema"] != "lumenis.internal-pitch-task/v1"
                or type(context["owner_context"]) is not dict
                or type(context["request_id"]) is not str
                or re.fullmatch(r"[A-Za-z0-9_-]{8,128}", context["request_id"]) is None
                or type(context["input"]) is not dict or context["input_hash"] != _digest(context["input"])):
            raise ValueError("INTERNAL_PITCH_TASK_INPUT_INVALID")
        frozen = _json(context).decode()
        task_id = "task-pitch-" + _digest({"context": context["owner_context"], "request_id": context["request_id"]})[:24]
        now = self._now()
        with get_repository().connection() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute("""INSERT OR IGNORE INTO ai_task
                (task_id,user_input,intent,parameters_json,context_json,status,risk_level,created_at,updated_at,created_by)
                VALUES (?,?,'create_internal_pitch','{}',?,'pending','L0',?,?,'shared_internal_pitch')""",
                (task_id, context["input"].get("title", "Internal draft"), frozen, now, now))
            current = self.get_pitch_task(task_id, owner_context=context["owner_context"], connection=con)
            if current["context_json"] != frozen:
                raise ValueError("INTERNAL_PITCH_REQUEST_REUSE_CONFLICT")
            if before_commit is not None:
                before_commit()
            con.commit()
        return current

    def get_pitch_task(self, task_id: str, *, owner_context: Dict[str, Any], connection=None) -> Dict[str, Any]:
        """Read exact owner/context; the caller still performs fresh Permission."""
        if type(task_id) is not str or re.fullmatch(r"task-pitch-[0-9a-f]{24}", task_id) is None:
            raise ValueError("INTERNAL_PITCH_TASK_ID_INVALID")
        if connection is None:
            with get_repository().connection(read_only=True, wal=False) as con:
                return self.get_pitch_task(task_id, owner_context=owner_context, connection=con)
        row = connection.execute("SELECT * FROM ai_task WHERE task_id=? AND created_by='shared_internal_pitch'", (task_id,)).fetchone()
        if row is None:
            raise LookupError("INTERNAL_PITCH_TASK_NOT_FOUND")
        value = dict(row)
        value["context"] = _strict_json_loads(value["context_json"], field_name="pitch context")
        context = value["context"]
        from lumenis.shared.reporting.saved_work import _digest, _json
        if (type(context) is not dict or set(context) != {"schema", "owner_context", "request_id", "input_hash", "input"}
                or context.get("schema") != "lumenis.internal-pitch-task/v1"
                or context.get("owner_context") != owner_context):
            raise PermissionError("INTERNAL_PITCH_TASK_SCOPE_DENIED")
        if (context["input_hash"] != _digest(context["input"])
                or "task-pitch-" + _digest({"context": owner_context, "request_id": context["request_id"]})[:24] != task_id
                or _json(context).decode() != value["context_json"]
                or value["intent"] != "create_internal_pitch"
                or value["status"] not in {"pending", "running", "cancel_requested", "cancelled", "failed", "interrupted", "succeeded"}):
            raise ValueError("INTERNAL_PITCH_TASK_INTEGRITY_INVALID")
        value["parameters"] = _strict_json_loads(value["parameters_json"], field_name="pitch worker")
        value["result"] = _strict_json_loads(value["result_json"], field_name="pitch result") if value["result_json"] else None
        return value

    def claim_pitch_task(self, task_id: str, *, owner_context: Dict[str, Any], before_commit=None) -> Dict[str, Any]:
        import psutil
        worker = {"pid": os.getpid(), "started_at": psutil.Process().create_time(), "nonce": uuid.uuid4().hex}
        parameters = _serialize_strict_json(worker, field_name="pitch worker")
        with get_repository().connection() as con:
            con.execute("BEGIN IMMEDIATE")
            current = self.get_pitch_task(task_id, owner_context=owner_context, connection=con)
            if current["status"] not in {"pending", "failed", "interrupted"}:
                raise ValueError("INTERNAL_PITCH_TASK_NOT_RUNNABLE")
            con.execute("""UPDATE ai_task SET status='running',parameters_json=?,started_at=?,
                finished_at=NULL,result_json=NULL,error=NULL,updated_at=? WHERE task_id=?""",
                (parameters, self._now(), self._now(), task_id))
            result = self.get_pitch_task(task_id, owner_context=owner_context, connection=con)
            if before_commit is not None:
                before_commit()
            con.commit()
        return result

    def require_pitch_worker(self, task_id: str, *, owner_context: Dict[str, Any], worker: Dict[str, Any], connection=None) -> None:
        import psutil
        current = self.get_pitch_task(task_id, owner_context=owner_context, connection=connection)
        if current["status"] in {"cancel_requested", "cancelled"}:
            raise ValueError("INTERNAL_PITCH_CANCELLED")
        if (current["status"] != "running" or current["parameters"] != worker
                or worker.get("pid") != os.getpid() or worker.get("started_at") != psutil.Process().create_time()):
            raise ValueError("INTERNAL_PITCH_WORKER_CONFLICT")

    def cancel_pitch_task(self, task_id: str, *, owner_context: Dict[str, Any], before_commit=None) -> Dict[str, Any]:
        """Request cancellation; a committed result is always retained."""
        with get_repository().connection() as con:
            con.execute("BEGIN IMMEDIATE")
            task = self.get_pitch_task(task_id, owner_context=owner_context, connection=con)
            state = task["status"]
            if state in {"pending", "failed", "interrupted"}:
                con.execute("UPDATE ai_task SET status='cancelled',finished_at=?,updated_at=? WHERE task_id=?", (self._now(), self._now(), task_id))
            elif state == "running":
                con.execute("UPDATE ai_task SET status='cancel_requested',updated_at=? WHERE task_id=?", (self._now(), task_id))
            if before_commit is not None:
                before_commit()
            con.commit()
        return self.get_pitch_task(task_id, owner_context=owner_context)

    def reconcile_pitch_worker(self, task_id: str, *, owner_context: Dict[str, Any], before_commit=None) -> Dict[str, Any]:
        """Recover only after the exact recorded OS worker is proven gone."""
        import psutil
        with get_repository().connection() as con:
            con.execute("BEGIN IMMEDIATE")
            task = self.get_pitch_task(task_id, owner_context=owner_context, connection=con)
            if task["status"] in {"running", "cancel_requested"}:
                worker = task["parameters"]
                if (set(worker) != {"pid", "started_at", "nonce"} or type(worker["pid"]) is not int
                        or worker["pid"] <= 0 or type(worker["started_at"]) not in {int, float}):
                    raise RuntimeError("INTERNAL_PITCH_WORKER_UNVERIFIED")
                try:
                    process = psutil.Process(worker["pid"])
                    if process.is_running() and process.create_time() == worker["started_at"]:
                        raise RuntimeError("INTERNAL_PITCH_WORKER_STILL_ACTIVE")
                except psutil.NoSuchProcess:
                    pass
                state = "cancelled" if task["status"] == "cancel_requested" else "interrupted"
                con.execute("UPDATE ai_task SET status=?,updated_at=? WHERE task_id=? AND parameters_json=?",
                            (state, self._now(), task_id, task["parameters_json"]))
            if before_commit is not None:
                before_commit()
            con.commit()
        return self.get_pitch_task(task_id, owner_context=owner_context)

    def commit_pitch_task(self, task_id: str, *, owner_context: Dict[str, Any], worker: Dict[str, Any], connection, artifact: Dict[str, Any], document: Dict[str, Any]) -> None:
        """Commit making result on the Artifact owner's same transaction."""
        if not isinstance(connection, sqlite3.Connection) or not connection.in_transaction:
            raise ValueError("INTERNAL_PITCH_COMMIT_TRANSACTION_REQUIRED")
        self.require_pitch_worker(task_id, owner_context=owner_context, worker=worker, connection=connection)
        row = connection.execute("SELECT sha256,size_bytes,source_execution_id FROM lumenis_shared_artifacts WHERE artifact_id=?", (artifact["artifact_id"],)).fetchone()
        if (row is None or tuple(row) != (artifact["sha256"], artifact["size_bytes"], document["work_id"])
                or document["context"] != owner_context or document["task_id"] != task_id):
            raise ValueError("INTERNAL_PITCH_COMMIT_BINDING_INVALID")
        result = {"artifact_id": artifact["artifact_id"], "sha256": artifact["sha256"], "size_bytes": artifact["size_bytes"],
                  "work_id": document["work_id"], "version": document["version"],
                  "parent_artifact_id": document["parent_artifact_id"], "parent_sha256": document["parent_sha256"],
                  "action_kind": "INTERNAL_TEXT_REVISION" if document["version"] > 1 else "INTERNAL_TEXT_CREATION",
                  "execution_state": "ARTIFACT_COMMITTED", "business_outcome": "NOT_OBSERVED", "external_effect": "NOT_PERFORMED"}
        connection.execute("UPDATE ai_task SET status='succeeded',result_json=?,finished_at=?,updated_at=? WHERE task_id=?",
                           (_serialize_strict_json(result, field_name="pitch result"), self._now(), self._now(), task_id))

    def fail_pitch_task(self, task_id: str, *, owner_context: Dict[str, Any], worker: Dict[str, Any], error: str) -> None:
        if type(error) is not str or re.fullmatch(r"[A-Z_0-9]{1,100}", error) is None:
            raise ValueError("INTERNAL_PITCH_ERROR_INVALID")
        with get_repository().connection() as con:
            con.execute("BEGIN IMMEDIATE")
            task = self.get_pitch_task(task_id, owner_context=owner_context, connection=con)
            if task["status"] in {"running", "cancel_requested"} and task["parameters"] == worker:
                state = "cancelled" if task["status"] == "cancel_requested" else "failed"
                con.execute("UPDATE ai_task SET status=?,error=?,finished_at=?,updated_at=? WHERE task_id=?",
                            (state, error, self._now(), self._now(), task_id))
            con.commit()

    def create_report_task(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Persist one server-authorized Source Brief task in the existing table.

        Authorization belongs to the existing Reporting route and SYSTEM
        Permission owner. This method validates the storage shape only; it does
        not grant authority to create, claim, resume, or publish a report.
        """
        report_context = _validate_managed_report_context(context)
        task_id = f"{_MANAGED_REPORT_TASK_PREFIX}{uuid.uuid4()}"
        if report_context.get("request_id"):
            binding = _serialize_strict_json({key: report_context[key] for key in ("actor_ref", "scope", "request_id")},
                                             field_name="report request binding")
            task_id = _MANAGED_REPORT_TASK_PREFIX + str(uuid.uuid5(uuid.NAMESPACE_URL, binding))
            try:
                existing = self.get_report_task(task_id)
            except KeyError:
                existing = None
            if existing is not None:
                excluded = {"permission_audit_ref", "operation_audit_ref"}
                if ({k:v for k,v in existing["context"].items() if k not in excluded}
                        != {k:v for k,v in report_context.items() if k not in excluded}):
                    raise RuntimeError("SOURCE_BRIEF_REQUEST_ID_CONFLICT")
                return existing
        now = self._now()
        with get_db() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO ai_task
                   (task_id, user_input, intent, parameters_json, context_json,
                    status, risk_level, created_at, updated_at, created_by)
                   VALUES (?, ?, 'generate_report', '{}', ?, 'pending', 'L0', ?, ?, ?)""",
                (
                    task_id,
                    report_context["business_question"] or "Source Brief",
                    _serialize_strict_json(
                        report_context, field_name="managed report context"
                    ),
                    now,
                    now,
                    _MANAGED_REPORT_TASK_CREATOR,
                ),
            )
        stored = self.get_report_task(task_id)
        excluded = {"permission_audit_ref", "operation_audit_ref"}
        if ({k:v for k,v in stored["context"].items() if k not in excluded}
                != {k:v for k,v in report_context.items() if k not in excluded}):
            raise RuntimeError("SOURCE_BRIEF_REQUEST_ID_CONFLICT")
        return stored

    def get_report_task(self, task_id: str) -> Dict[str, Any]:
        """Return one managed report task, failing closed on malformed JSON."""
        _require_managed_report_task_id(task_id)
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM ai_task WHERE task_id=? AND created_by=?",
                (task_id, _MANAGED_REPORT_TASK_CREATOR),
            ).fetchone()
        if row is None:
            raise KeyError(f"Managed report task not found: {task_id}")

        return self._decode_report_task(row)

    @staticmethod
    def _decode_report_task(row):
        task = dict(row)
        if task.get("created_by") != _MANAGED_REPORT_TASK_CREATOR:
            raise PermissionError("task is not owned by Source Brief reporting")
        context = _strict_json_loads(
            task.get("context_json"), field_name="managed report context"
        )
        task["context"] = _validate_managed_report_context(context)
        parameters = _strict_json_loads(
            task.get("parameters_json"), field_name="managed report parameters"
        )
        task["parameters"] = _validate_managed_report_parameters(parameters)
        if task.get("result_json") is not None:
            task["result"] = _strict_json_loads(
                task["result_json"], field_name="managed report result"
            )
        return task

    @staticmethod
    def report_revision(task):
        """Opaque compare-and-swap token covering state, worker and all inputs."""
        return hashlib.sha256(_serialize_strict_json({key: task.get(key) for key in
            ("task_id", "context_json", "status", "parameters_json", "result_json", "error", "updated_at")},
            field_name="report revision").encode()).hexdigest()

    def mutate_report_task(self, task_id, *, actor_ref, scope, expected_revision,
                           operation, changes=None):
        task = self.get_report_task(task_id)
        if task["context"]["actor_ref"] != actor_ref or task["context"]["scope"] != scope:
            raise PermissionError("SOURCE_BRIEF_TASK_SCOPE_DENIED")
        if expected_revision != self.report_revision(task):
            raise RuntimeError("SOURCE_BRIEF_TASK_REVISION_CONFLICT")
        state = task["status"]
        if operation == "cancel":
            if state not in {"pending", "running", "interrupted", "failed"}:
                raise ValueError("SOURCE_BRIEF_TASK_NOT_CANCELLABLE")
            next_state, context = "cancelled", task["context"]
        elif operation == "restore":
            if state != "cancelled":
                raise ValueError("SOURCE_BRIEF_TASK_NOT_CANCELLED")
            next_state, context = "pending", task["context"]
        elif operation == "edit":
            if state not in {"pending", "interrupted", "failed", "cancelled"}:
                raise ValueError("SOURCE_BRIEF_TASK_NOT_EDITABLE")
            if (not isinstance(changes, dict) or not changes
                    or set(changes) - {"business_question", "source_ids", "limit", "research", "reference"}
                    or task["context"].get("revision") is not None):
                raise ValueError("SOURCE_BRIEF_TASK_EDIT_INVALID")
            context = _validate_managed_report_context({**task["context"], **changes})
            next_state = state
        else:
            raise ValueError("SOURCE_BRIEF_TASK_OPERATION_INVALID")
        with get_db() as conn:
            cursor = conn.execute("""UPDATE ai_task SET context_json=?, user_input=?, status=?,
                updated_at=?, error=NULL WHERE task_id=? AND created_by=? AND status=?
                AND context_json=? AND parameters_json=? AND updated_at=?
                AND NOT EXISTS(SELECT 1 FROM daily_reports WHERE report_id=?)""",
                (_serialize_strict_json(context, field_name="managed report context"),
                 context["business_question"] or "Source Brief", next_state, self._now(), task_id,
                 _MANAGED_REPORT_TASK_CREATOR, state, task["context_json"], task["parameters_json"],
                 task["updated_at"], task["context"]["job_id"]))
            if cursor.rowcount != 1:
                raise RuntimeError("SOURCE_BRIEF_TASK_REVISION_CONFLICT")
        return self.get_report_task(task_id)

    def list_report_tasks(self, *, actor_ref, scope, limit=30, cursor=None,
                          dimension=None, state=None):
        """Filter exact actor/scope and dimension before stable keyset pagination."""
        import base64
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("SOURCE_BRIEF_LIST_LIMIT_INVALID")
        if state is not None and state not in {"pending", "running", "interrupted", "failed", "cancelled", "succeeded"}:
            raise ValueError("SOURCE_BRIEF_TASK_STATE_INVALID")
        if dimension is not None:
            from agent_research.taxonomy import normalize_dimension
            normalize_dimension(dimension)
        selectors = {"actor": actor_ref, "scope": scope, "dimension": dimension, "state": state}
        identity = hashlib.sha256(_serialize_strict_json(selectors, field_name="selector").encode()).hexdigest()
        boundary = None
        if cursor is not None:
            try:
                decoded = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
                if set(decoded) != {"identity", "boundary"} or decoded["identity"] != identity:
                    raise ValueError()
                boundary = _require_managed_report_task_id(decoded["boundary"])
            except Exception as exc:
                raise ValueError("SOURCE_BRIEF_TASK_CURSOR_INVALID") from exc
        conditions = ["created_by=?", "json_valid(context_json)", "json_extract(context_json,'$.actor_ref')=?"]
        params = [_MANAGED_REPORT_TASK_CREATOR, actor_ref]
        for key in ("product_id", "global_scope", "entity_label", "subject_id", "brand_focus_id", "scope_kind", "version"):
            conditions.append("json_extract(context_json,'$.scope." + key + "') IS ?")
            params.append(scope.get(key))
        scope_conditions, scope_params = list(conditions), list(params)
        if dimension is not None:
            conditions.append("COALESCE(json_extract(context_json,'$.research.dimension'),'growth_opportunity')=?")
            params.append(dimension)
        if state is not None:
            conditions.append("status=?")
            params.append(state)
        with get_db() as conn:
            conn.execute('BEGIN')
            from agent_research.taxonomy import RESEARCH_DIMENSIONS
            states = ('pending','running','interrupted','failed','cancelled','succeeded')
            grouped = conn.execute("SELECT COALESCE(json_extract(context_json,'$.research.dimension'),'growth_opportunity'),status,COUNT(*) FROM ai_task WHERE " +
                " AND ".join(scope_conditions) + " GROUP BY 1,2", scope_params).fetchall()
            dimension_summary = [{**label, 'task_count':0, 'states':{state:0 for state in states}}
                                 for label in RESEARCH_DIMENSIONS]
            by_dimension = {item['key']:item for item in dimension_summary}
            for key, task_state, count in grouped:
                if key not in by_dimension or task_state not in states:
                    raise RuntimeError('SOURCE_BRIEF_TASK_SUMMARY_UNKNOWN_CLASSIFICATION')
                by_dimension[key]['states'][task_state] = count
                by_dimension[key]['task_count'] += count
            for item in dimension_summary:
                item['open'] = sum(item['states'][state] for state in ('pending','running','interrupted','failed'))
                item['completed'] = item['states']['succeeded']
            summary_total = sum(item['task_count'] for item in dimension_summary)
            total = conn.execute("SELECT COUNT(*) FROM ai_task WHERE " + " AND ".join(conditions), params).fetchone()[0]
            if boundary:
                conditions.append("task_id<?")
                params.append(boundary)
            rows = conn.execute("SELECT * FROM ai_task WHERE " + " AND ".join(conditions) +
                                " ORDER BY task_id DESC LIMIT ?", [*params, limit + 1]).fetchall()
            tasks = [self._decode_report_task(row) for row in rows[:limit]]
        more = len(rows) > limit
        token = base64.urlsafe_b64encode(json.dumps({"identity": identity,
            "boundary": tasks[-1]["task_id"]}).encode()).decode() if more else None
        return {"items": tasks, "total": total, "has_more": more, "next_cursor": token,
                "summary": {"dimensions": dimension_summary, "total": summary_total,
                            "basis": "persisted_task_state_same_sqlite_snapshot",
                            "business_outcome": "NOT_ESTABLISHED", "scope": scope}}

    def claim_report_task(self, task_id: str) -> bool:
        """Atomically claim an eligible managed report task for this process."""
        task_id = _require_managed_report_task_id(task_id)
        task = self.get_report_task(task_id)
        if task.get("status") not in {"pending", "interrupted", "failed"}:
            return False

        worker_identity = _current_report_worker_identity()

        expected_status = task["status"]
        now = self._now()
        worker_parameters = _serialize_strict_json(
            {
                "worker_pid": worker_identity["worker_pid"],
                "worker_started_at": worker_identity["worker_started_at"],
            },
            field_name="managed report worker identity",
        )
        with get_db() as conn:
            cursor = conn.execute(
                """UPDATE ai_task
                   SET status='running', started_at=?, finished_at=NULL,
                       result_json=NULL, error=NULL, parameters_json=?, updated_at=?
                   WHERE task_id=? AND created_by=? AND status=? AND context_json=? AND updated_at=?""",
                (
                    now,
                    worker_parameters,
                    now,
                    task_id,
                    _MANAGED_REPORT_TASK_CREATOR,
                    expected_status, task["context_json"], task["updated_at"],
                ),
            )
        return cursor.rowcount == 1

    def finish_report_task(
        self,
        task_id: str,
        *,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Finish only a currently running managed report task (CAS)."""
        task_id = _require_managed_report_task_id(task_id)
        task = self.get_report_task(task_id)
        if task.get("status") != "running":
            return False
        if task["parameters"] != _current_report_worker_identity():
            return False
        if (result is None) == (error is None):
            raise ValueError("provide exactly one of result or error")

        now = self._now()
        if error is not None:
            if (
                not _valid_report_text(error, 2000)
                or not error.strip()
            ):
                raise ValueError("managed report error must be a non-empty string")
            sql = """UPDATE ai_task
                     SET status='failed', result_json=NULL, error=?,
                         finished_at=?, updated_at=?
                     WHERE task_id=? AND created_by=? AND status='running'
                       AND parameters_json=?"""
            params = (
                error, now, now, task_id, _MANAGED_REPORT_TASK_CREATOR,
                task["parameters_json"],
            )
        else:
            if type(result) is not dict:
                raise ValueError("managed report result must be an object")
            result_json = _serialize_strict_json(
                result, field_name="managed report result"
            )
            sql = """UPDATE ai_task
                     SET status='succeeded', result_json=?, error=NULL,
                         finished_at=?, updated_at=?
                     WHERE task_id=? AND created_by=? AND status='running'
                       AND parameters_json=?"""
            params = (
                result_json, now, now, task_id, _MANAGED_REPORT_TASK_CREATOR,
                task["parameters_json"],
            )
        with get_db() as conn:
            cursor = conn.execute(sql, params)
        return cursor.rowcount == 1

    def mark_interrupted_report_task(
        self, task_id: str, expected_parameters_json: str,
    ) -> bool:
        """Mark a dead worker's task interrupted; caller must verify process death."""
        task_id = _require_managed_report_task_id(task_id)
        expected_parameters = _validate_managed_report_parameters(
            _strict_json_loads(
                expected_parameters_json,
                field_name="expected managed report worker identity",
            )
        )
        if not expected_parameters:
            raise ValueError("expected managed report worker identity is missing")
        task = self.get_report_task(task_id)
        if task.get("status") != "running":
            return False
        now = self._now()
        with get_db() as conn:
            cursor = conn.execute(
                """UPDATE ai_task
                   SET status='interrupted', error='worker_interrupted',
                       finished_at=?, updated_at=?
                   WHERE task_id=? AND created_by=? AND status='running'
                     AND parameters_json=?""",
                (
                    now,
                    now,
                    task_id,
                    _MANAGED_REPORT_TASK_CREATOR,
                    expected_parameters_json,
                ),
            )
        return cursor.rowcount == 1

    @staticmethod
    def _training_receipt_row_state(row: Any, expected_binding: Dict[str, Any]):
        if row is None:
            raise KeyError("Managed training receipt task not found")
        task = dict(row)
        task_id = _require_training_receipt_task_id(task.get("task_id"))
        if (task.get("created_by") != _TRAINING_RECEIPT_TASK_CREATOR
                or task.get("user_input") != _TRAINING_RECEIPT_USER_INPUT):
            raise PermissionError("task is not owned by the training receipt state owner")
        context = _validate_training_receipt_context(
            task.get("context_json"), task_id=task_id, expected_binding=expected_binding,
        )
        status = task.get("status")
        admission = context.get("admission")
        if status not in {"ready", "running", "unknown", "failed", "completed"}:
            raise ValueError("training receipt task status is invalid")
        if (admission is None and status == "completed") or (
            admission is not None and (status == "completed") != admission["terminal"]
        ):
            raise ValueError("training receipt task status does not match its admission state")
        return task, context

    @staticmethod
    def _training_checkpoint_material(value):
        """Strict bounded derivative metadata; never deserialize authority."""
        raw = _serialize_strict_json(value, field_name="training checkpoint state")
        if len(raw.encode("utf-8")) > 1024 * 1024:
            raise ValueError("CHECKPOINT_REQUEST_INVALID")
        return _strict_json_loads(raw, field_name="training checkpoint state"), raw

    def _training_checkpoint_task(self, task_id, *, expected_binding,
                                  expected_approval_reference, pinned_public_key, connection):
        self._require_training_receipt_connection(connection)
        task_id = _require_training_receipt_task_id(task_id)
        row = connection.execute("SELECT * FROM ai_task WHERE task_id=? AND created_by=?",
                                 (task_id, _TRAINING_RECEIPT_TASK_CREATOR)).fetchone()
        return self._require_training_receipt_v2_task(row, task_id=task_id,
            expected_binding=expected_binding, expected_approval_reference=expected_approval_reference,
            expected_public_key=pinned_public_key)

    def training_execution_read(self, task_id, *, expected_binding,
                                expected_approval_reference, pinned_public_key, connection):
        """Read the versioned execution subrecord under the original sealed Task."""
        _, context, _ = self._training_checkpoint_task(task_id, expected_binding=expected_binding,
            expected_approval_reference=expected_approval_reference,
            pinned_public_key=pinned_public_key, connection=connection)
        step_id = "trainexec_" + context["task_digest"]
        row = connection.execute("SELECT * FROM ai_task_step WHERE task_id=? AND step_id=?",
                                 (task_id, step_id)).fetchone()
        if row is None:
            return None
        detail = _strict_json_loads(row["detail"], field_name="training execution subrecord")
        fields = {"schema_version", "owner", "task_digest", "fingerprints", "policy_sha256",
                  "byte_limit", "attempt_id", "worker_epoch", "run_digest", "worker_binding",
                  "next_sequence", "last_phase", "pending_challenge", "handoff", "state"}
        if (type(detail) is not dict or set(detail) != fields or detail["schema_version"] != 3
                or type(detail["schema_version"]) is not int
                or detail["owner"] != "owned_training_execution:v1"
                or detail["task_digest"] != context["task_digest"]
                or detail["fingerprints"] != context["fingerprints"]
                or row["phase"] != "owned_training_execution"
                or row["status"] != detail["state"]):
            raise ValueError("CHECKPOINT_SCOPE_MISMATCH")
        self._training_checkpoint_material(detail)
        from lumenis.system.security import training_receipts as receipts
        for field in ("task_digest", "policy_sha256", "run_digest"):
            receipts._checkpoint_hash(detail[field])
        receipts._checkpoint_uuid(detail["attempt_id"])
        for field in ("worker_epoch", "next_sequence"):
            receipts._checkpoint_integer(detail[field], 1)
        if (type(detail["byte_limit"]) is not int or not 1 <= detail["byte_limit"] <= 1024**4
                or type(detail["worker_binding"]) is not dict
                or set(detail["worker_binding"]) != {"pid", "created_at", "lock_sha256"}
                or type(detail["worker_binding"]["pid"]) is not int or detail["worker_binding"]["pid"] <= 0
                or type(detail["worker_binding"]["created_at"]) not in {int, float}
                or not math.isfinite(detail["worker_binding"]["created_at"])
                or detail["worker_binding"]["created_at"] <= 0
                or type(detail["state"]) is not str
                or detail["state"] not in {"RUNNABLE", "LOAD_ADMITTED", "LOADED", "COMPLETED", "FAILED", "INTERRUPTED"}
                or (detail["last_phase"] is not None and detail["last_phase"] not in _TRAINING_PHASES)):
            raise ValueError("CHECKPOINT_REQUEST_INVALID")
        receipts._checkpoint_hash(detail["worker_binding"]["lock_sha256"])
        return detail

    def _training_execution_write(self, task_id, *, previous, current, connection):
        """CAS on the existing step table; caller owns commit/Permission lease."""
        self._require_training_receipt_connection(connection)
        _, raw = self._training_checkpoint_material(current)
        step_id = "trainexec_" + current["task_digest"]
        if previous is None:
            connection.execute("""INSERT INTO ai_task_step
                (step_id,task_id,phase,status,detail,started_at) VALUES (?,?,?,?,?,?)""",
                (step_id, task_id, "owned_training_execution", current["state"], raw, self._now()))
        else:
            _, before = self._training_checkpoint_material(previous)
            cursor = connection.execute("""UPDATE ai_task_step SET detail=?,status=?
                WHERE step_id=? AND task_id=? AND detail=?""", (raw, current["state"], step_id, task_id, before))
            if cursor.rowcount != 1:
                raise RuntimeError("CHECKPOINT_OPERATION_CONFLICT")

    def training_execution_initialize(self, task_id, *, worker_binding, policy_sha256, byte_limit,
                                      expected_binding, expected_approval_reference,
                                      pinned_public_key, connection):
        import copy
        worker, _ = self._training_checkpoint_material(worker_binding)
        if (type(worker) is not dict or set(worker) != {"pid", "created_at", "lock_sha256"}
                or type(worker["pid"]) is not int or worker["pid"] <= 0
                or type(worker["created_at"]) not in {int, float}
                or not math.isfinite(worker["created_at"]) or worker["created_at"] <= 0
                or type(worker["lock_sha256"]) is not str or re.fullmatch(r"[0-9a-f]{64}", worker["lock_sha256"]) is None
                or type(policy_sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", policy_sha256) is None
                or type(byte_limit) is not int or not 1 <= byte_limit <= 1024**4):
            raise ValueError("CHECKPOINT_REQUEST_INVALID")
        task, context, _ = self._training_checkpoint_task(task_id, expected_binding=expected_binding,
            expected_approval_reference=expected_approval_reference, pinned_public_key=pinned_public_key,
            connection=connection)
        args = dict(expected_binding=expected_binding, expected_approval_reference=expected_approval_reference,
                    pinned_public_key=pinned_public_key, connection=connection)
        prior = self.training_execution_read(task_id, **args)
        if prior is not None:
            if (prior["worker_binding"] != worker or prior["policy_sha256"] != policy_sha256
                    or prior["byte_limit"] != byte_limit):
                raise PermissionError("CHECKPOINT_WORKER_FENCE_LOST")
            return copy.deepcopy(prior)
        if task["status"] not in {"ready", "running"} or context["admission"]["terminal"]:
            raise PermissionError("CHECKPOINT_RUN_MISMATCH")
        value = {"schema_version": 3, "owner": "owned_training_execution:v1",
            "task_digest": context["task_digest"], "fingerprints": context["fingerprints"],
            "policy_sha256": policy_sha256, "byte_limit": byte_limit, "attempt_id": str(uuid.uuid4()),
            "worker_epoch": 1, "run_digest": context["run_digest"], "worker_binding": worker,
            "next_sequence": context["next_sequence"], "last_phase": context["admission"]["last_phase"],
            "pending_challenge": None, "handoff": None, "state": "RUNNABLE"}
        self._training_execution_write(task_id, previous=None, current=value, connection=connection)
        return copy.deepcopy(value)

    def training_operation_read(self, task_id, *, operation_id, **args):
        import copy
        from lumenis.system.security.training_receipts import _checkpoint_uuid
        _checkpoint_uuid(operation_id)
        execution = self.training_execution_read(task_id, **args)
        if execution is None:
            raise PermissionError("CHECKPOINT_CONTRACT_NOT_BOUND")
        step_id = "trainop_" + hashlib.sha256((task_id + operation_id).encode()).hexdigest()
        row = args["connection"].execute("SELECT * FROM ai_task_step WHERE task_id=? AND step_id=?",
                                       (task_id, step_id)).fetchone()
        if row is None:
            return None
        detail = _strict_json_loads(row["detail"], field_name="training checkpoint operation")
        fields = {"schema_version", "operation_id", "kind", "input", "input_sha256", "state", "result"}
        if (type(detail) is not dict or set(detail) != fields
                or type(detail["schema_version"]) is not int or detail["schema_version"] != 1
                or detail["operation_id"] != operation_id or detail["kind"] not in {"save", "load"}
                or row["status"] != detail["state"] or row["phase"] != "training_" + detail["kind"]):
            raise ValueError("CHECKPOINT_OPERATION_CONFLICT")
        _, encoded = self._training_checkpoint_material(detail["input"])
        if hashlib.sha256(encoded.encode()).hexdigest() != detail["input_sha256"]:
            raise ValueError("CHECKPOINT_HASH_MISMATCH")
        self._training_checkpoint_material(detail)
        return copy.deepcopy(detail)

    def training_operation_prepare(self, task_id, *, operation_id, kind, normalized_input, result, **args):
        if type(kind) is not str or kind not in {"save", "load"}:
            raise ValueError("CHECKPOINT_REQUEST_INVALID")
        prior = self.training_operation_read(task_id, operation_id=operation_id, **args)
        value, raw = self._training_checkpoint_material(normalized_input)
        input_hash = hashlib.sha256(raw.encode()).hexdigest()
        if prior is not None:
            if prior["kind"] != kind or prior["input_sha256"] != input_hash or prior["input"] != value:
                raise PermissionError("CHECKPOINT_OPERATION_CONFLICT")
            return prior
        detail = {"schema_version": 1, "operation_id": operation_id, "kind": kind, "input": value,
            "input_sha256": input_hash, "state": "RESERVED" if kind == "save" else "LOAD_ADMITTED",
            "result": result}
        _, encoded = self._training_checkpoint_material(detail)
        step_id = "trainop_" + hashlib.sha256((task_id + operation_id).encode()).hexdigest()
        args["connection"].execute("""INSERT INTO ai_task_step
            (step_id,task_id,phase,status,detail,started_at) VALUES (?,?,?,?,?,?)""",
            (step_id, task_id, "training_" + kind, detail["state"], encoded, self._now()))
        return self.training_operation_read(task_id, operation_id=operation_id, **args)

    def training_checkpoint_latest_receipt(self, task_id, **args):
        import copy
        from lumenis.system.security import training_receipts as receipts
        self.training_execution_read(task_id, **args)
        rows = args["connection"].execute("""SELECT detail FROM ai_task_step
            WHERE task_id=? AND phase='training_save' AND status='COMMITTED'""", (task_id,)).fetchall()
        if len(rows) > 4096:
            raise ValueError("CHECKPOINT_REQUEST_INVALID")
        records = []
        for row in rows:
            operation = _strict_json_loads(row["detail"], field_name="committed training checkpoint")
            record = operation["result"]
            receipts.verify_training_checkpoint_receipt(record["receipt"],
                expected_payload={k: v for k, v in record.items() if k != "receipt"}, pinned_public_key=args["pinned_public_key"])
            if record["task_digest"] != _training_receipt_task_digest(task_id):
                raise ValueError("CHECKPOINT_SCOPE_MISMATCH")
            records.append(record)
        records.sort(key=lambda value: value["artifact_version"])
        parent, refs = None, set()
        for version, record in enumerate(records, 1):
            if (record["artifact_version"] != version or record["parent_ref"] != parent
                    or record["artifact_ref"] in refs):
                raise ValueError("CHECKPOINT_OPERATION_CONFLICT")
            refs.add(record["artifact_ref"])
            parent = record["artifact_ref"]
        return copy.deepcopy(records[-1]) if records else None

    def training_checkpoint_receipt_for_artifact(self, task_id, *, artifact_ref, **args):
        import copy
        from lumenis.system.security import training_receipts as receipts
        receipts._checkpoint_ref(artifact_ref)
        self.training_checkpoint_latest_receipt(task_id, **args)
        rows = args["connection"].execute("""SELECT detail FROM ai_task_step
            WHERE task_id=? AND phase='training_save' AND status='COMMITTED'""", (task_id,)).fetchall()
        matches = []
        for row in rows:
            operation = _strict_json_loads(row["detail"], field_name="committed training checkpoint")
            if operation["result"]["artifact_ref"] == artifact_ref:
                matches.append(operation["result"])
        if len(matches) > 1:
            raise ValueError("CHECKPOINT_OPERATION_CONFLICT")
        return copy.deepcopy(matches[0]) if matches else None

    def training_operation_transition(self, task_id, *, operation_id, before_state, state, result, **args):
        record = self.training_operation_read(task_id, operation_id=operation_id, **args)
        if record is None or record["state"] != before_state:
            raise PermissionError("CHECKPOINT_OPERATION_CONFLICT")
        transitions = {"RESERVED": {"WRITING", "FAILED", "INTERRUPTED"},
            "WRITING": {"COMMITTED", "FAILED", "INTERRUPTED"},
            "LOAD_ADMITTED": {"LOAD_ADMITTED", "LOADING", "FAILED", "INTERRUPTED"},
            "LOADING": {"LOADED", "FAILED", "INTERRUPTED"}, "LOADED": {"RUNNABLE", "FAILED"}}
        if type(state) is not str or state not in transitions.get(before_state, set()):
            raise PermissionError("CHECKPOINT_OPERATION_CONFLICT")
        _, previous = self._training_checkpoint_material(record)
        current = {**record, "state": state, "result": result}
        _, encoded = self._training_checkpoint_material(current)
        step_id = "trainop_" + hashlib.sha256((task_id + operation_id).encode()).hexdigest()
        cursor = args["connection"].execute("""UPDATE ai_task_step SET status=?,detail=?,finished_at=?
            WHERE step_id=? AND task_id=? AND detail=?""", (state, encoded,
            self._now() if state in {"COMMITTED", "RUNNABLE", "FAILED", "INTERRUPTED"} else None,
            step_id, task_id, previous))
        if cursor.rowcount != 1:
            raise RuntimeError("CHECKPOINT_OPERATION_CONFLICT")
        return current

    def training_require_current_checkpoint_admission(self, task_id, *, admission, operation,
                                                      expected_fingerprints, worker_binding, **args):
        """Verify current persisted start bytes; Permission/runtime remain callers."""
        from lumenis.system.security import training_receipts as receipts
        if type(admission) is not receipts.VerifiedTrainingCheckpointAdmission or operation not in {"save", "load"}:
            raise PermissionError("CHECKPOINT_REQUEST_INVALID")
        execution = self.training_execution_read(task_id, **args)
        envelope = admission.envelope
        payload = envelope["payload"]
        record = self.training_operation_read(task_id, operation_id=payload["operation_id"], **args)
        if (execution is None or record is None or record["kind"] != operation
                or record["state"] != ("RESERVED" if operation == "save" else "LOAD_ADMITTED")
                or type(record["result"]) is not dict or record["result"].get("admission") != envelope
                or execution["worker_binding"] != worker_binding
                or execution["fingerprints"] != expected_fingerprints
                or payload["fingerprints"] != expected_fingerprints
                or payload["task_digest"] != execution["task_digest"]
                or payload["run_digest"] != execution["run_digest"]
                or payload["attempt_id"] != execution["attempt_id"]
                or payload["worker_epoch"] != execution["worker_epoch"]
                or payload["policy_sha256"] != execution["policy_sha256"]
                or payload["operation"] != operation):
            raise PermissionError("CHECKPOINT_WORKER_FENCE_LOST")
        receipts.verify_training_checkpoint_admission(envelope, expected_payload=record["result"]["admission"]["payload"],
            pinned_public_key=args["pinned_public_key"])
        return record

    def training_execution_register_resume(self, task_id, *, previous_worker_binding,
                                          worker_binding, worker_stop_receipt_ref, **args):
        import copy
        value = self.training_execution_read(task_id, **args)
        if (value is None or value["worker_binding"] != previous_worker_binding
                or value["pending_challenge"] is not None
                or type(worker_stop_receipt_ref) is not str or not worker_stop_receipt_ref
                or worker_binding == previous_worker_binding):
            raise PermissionError("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
        # Runtime has already stopped/reaped the exact old process tree while
        # retaining its OS lock; this method stores no caller Boolean claim.
        worker, _ = self._training_checkpoint_material(worker_binding)
        if (type(worker) is not dict or set(worker) != {"pid", "created_at", "lock_sha256"}
                or type(worker["pid"]) is not int or worker["pid"] <= 0
                or type(worker["created_at"]) not in {int, float} or not math.isfinite(worker["created_at"])
                or worker["created_at"] <= 0 or type(worker["lock_sha256"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", worker["lock_sha256"]) is None):
            raise ValueError("CHECKPOINT_REQUEST_INVALID")
        _, original, _ = self._training_checkpoint_task(task_id,
            expected_binding=args["expected_binding"], expected_approval_reference=args["expected_approval_reference"],
            pinned_public_key=args["pinned_public_key"], connection=args["connection"])
        current = {**value, "worker_binding": worker, "worker_epoch": value["worker_epoch"] + 1,
            "attempt_id": str(uuid.uuid4()), "run_digest": hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
            "next_sequence": max(value["next_sequence"], original["next_sequence"]),
            "last_phase": None, "pending_challenge": None, "handoff": None, "state": "LOAD_ADMITTED"}
        self._training_execution_write(task_id, previous=value, current=current, connection=args["connection"])
        return copy.deepcopy(current)

    def training_execution_commit_loaded(self, task_id, *, phase_handoff, **args):
        from lumenis.system.security import training_receipts as receipts
        value = self.training_execution_read(task_id, **args)
        payload = phase_handoff.get("payload") if type(phase_handoff) is dict else None
        if value is None or value["state"] != "LOAD_ADMITTED" or type(payload) is not dict:
            raise PermissionError("CHECKPOINT_LOAD_FAILED")
        receipts.verify_training_recovery_handoff(phase_handoff, expected_payload=payload,
                                                  pinned_public_key=args["pinned_public_key"])
        expected = {"task_id": task_id, "task_digest": value["task_digest"], "run_digest": value["run_digest"],
            "attempt_id": value["attempt_id"], "worker_epoch": value["worker_epoch"],
            "fingerprints": value["fingerprints"], "next_sequence": value["next_sequence"],
            "worker_binding_sha256": hashlib.sha256(receipts._canonical_json_bytes(value["worker_binding"])).hexdigest()}
        if any(type(payload.get(k)) is not type(v) or payload[k] != v for k, v in expected.items()):
            raise PermissionError("CHECKPOINT_SCOPE_MISMATCH")
        record = self.training_operation_read(task_id, operation_id=payload["load_operation_id"], **args)
        if record is None or record["state"] != "LOADED" or record["result"].get("phase_handoff") != phase_handoff:
            raise PermissionError("CHECKPOINT_NOT_COMMITTED")
        current = {**value, "state": "LOADED", "handoff": phase_handoff}
        self._training_execution_write(task_id, previous=value, current=current, connection=args["connection"])
        return current

    def training_prepare_recovery_phase_challenge(self, task_id, *, phase, **args):
        from lumenis.system.security import training_receipts as receipts
        current_time = int(time.time())
        value = self.training_execution_read(task_id, **args)
        if value is None or value["state"] not in {"LOADED", "RUNNABLE"}:
            raise PermissionError("CHECKPOINT_NOT_COMMITTED")
        previous = dict(value)
        if value["pending_challenge"] is not None:
            # Lost response is reconciled explicitly; never renew a physical
            # resumed phase by silently reissuing its start.
            raise PermissionError("CHECKPOINT_COMMIT_UNKNOWN")
        if value["last_phase"] is None:
            if phase != "before_train" or value["handoff"] is None:
                raise PermissionError("CHECKPOINT_REQUEST_INVALID")
            receipts.verify_training_recovery_handoff(value["handoff"],
                expected_payload=value["handoff"]["payload"], pinned_public_key=args["pinned_public_key"])
            value = {**value, "handoff": None}
        elif not _training_phase_transition_allowed(value["last_phase"], phase):
            raise PermissionError("CHECKPOINT_RUN_MISMATCH")
        challenge = receipts.validate_training_phase_challenge({"schema_version": 1,
            "task_digest": value["task_digest"], "run_digest": value["run_digest"],
            **value["fingerprints"], "nonce": hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
            "phase": phase, "sequence": value["next_sequence"], "issued_at": current_time,
            "expires_at": min(current_time + 60, _training_approval_expiry_seconds(args["expected_approval_reference"]))})
        value = {**value, "pending_challenge": challenge}
        self._training_execution_write(task_id, previous=previous, current=value, connection=args["connection"])
        return challenge

    def training_commit_recovery_phase_receipt(self, task_id, *, challenge, receipt, **args):
        from lumenis.system.security import training_receipts as receipts
        value = self.training_execution_read(task_id, **args)
        if value is None or value["pending_challenge"] != challenge:
            raise PermissionError("CHECKPOINT_OPERATION_CONFLICT")
        receipts.verify_training_phase_decision(receipt, expected_challenge=challenge,
                                                pinned_public_key=args["pinned_public_key"])
        for name, expected in {**value["fingerprints"], "run_digest": value["run_digest"],
                               "task_digest": value["task_digest"], "sequence": value["next_sequence"]}.items():
            if type(challenge.get(name)) is not type(expected) or challenge[name] != expected:
                raise PermissionError("CHECKPOINT_SCOPE_MISMATCH")
        _, detail = self._training_checkpoint_material({"challenge": challenge, "receipt": receipt})
        args["connection"].execute("""INSERT INTO ai_task_step
            (step_id,task_id,phase,status,detail,started_at,finished_at) VALUES (?,?,?,?,?,?,?)""",
            (_training_phase_step_id(task_id, challenge["nonce"]), task_id, challenge["phase"], "allow",
             detail, self._now(), self._now()))
        state = "COMPLETED" if challenge["phase"] == _TRAINING_TERMINAL_PHASE else "RUNNABLE"
        current = {**value, "next_sequence": value["next_sequence"] + 1, "last_phase": challenge["phase"],
                   "pending_challenge": None, "state": state}
        self._training_execution_write(task_id, previous=value, current=current, connection=args["connection"])
        return current

    def training_recovery_phase_history(self, task_id, *, nonce, **args):
        """Read signed derivative history for this loaded attempt, never a permit."""
        import copy
        from lumenis.system.security import training_receipts as receipts
        if type(nonce) is not str or re.fullmatch(r"[0-9a-f]{64}", nonce) is None:
            raise ValueError("CHECKPOINT_REQUEST_INVALID")
        execution = self.training_execution_read(task_id, **args)
        if execution is None:
            raise PermissionError("CHECKPOINT_NOT_COMMITTED")
        row = args["connection"].execute(
            "SELECT * FROM ai_task_step WHERE task_id=? AND step_id=?",
            (task_id, _training_phase_step_id(task_id, nonce))).fetchone()
        if row is None:
            return None
        detail = _strict_json_loads(row["detail"], field_name="recovery phase history")
        if type(detail) is not dict or set(detail) != {"challenge", "receipt"}:
            raise ValueError("CHECKPOINT_SCOPE_MISMATCH")
        challenge = receipts.validate_training_phase_challenge(
            detail["challenge"], now=detail["challenge"]["issued_at"])
        expected = {"task_digest": execution["task_digest"], "run_digest": execution["run_digest"],
                    **execution["fingerprints"], "nonce": nonce}
        if (any(type(challenge.get(k)) is not type(v) or challenge[k] != v for k, v in expected.items())
                or row["phase"] != challenge["phase"] or row["status"] != "allow"
                or challenge["sequence"] >= execution["next_sequence"]):
            raise ValueError("CHECKPOINT_SCOPE_MISMATCH")
        receipts.verify_training_phase_decision(detail["receipt"], expected_challenge=challenge,
            pinned_public_key=args["pinned_public_key"], now=detail["receipt"]["issued_at"])
        return copy.deepcopy(detail)

    @staticmethod
    def _require_training_receipt_connection(connection: Any) -> None:
        if type(connection) is not sqlite3.Connection or not connection.in_transaction:
            raise RuntimeError("training phase consumption requires an active SQLite transaction")
        rows = connection.execute("PRAGMA database_list").fetchall()
        main_path = next((row[2] for row in rows if row[1] == "main"), None)
        if not isinstance(main_path, str) or not main_path:
            raise RuntimeError("training phase connection is not a file-backed canonical database")
        expected_path = os.path.abspath(main_db_path())
        if os.path.normcase(os.path.realpath(main_path)) != os.path.normcase(os.path.realpath(expected_path)):
            raise RuntimeError("training phase connection is not the canonical TaskEngine database")

    def create_training_receipt_task(
        self, *, binding: Dict[str, Any], fingerprints: Dict[str, str],
        connection: Optional[sqlite3.Connection] = None,
        approval_reference: Optional[Dict[str, Any]] = None,
        pinned_public_key: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist private phase-receipt state in the existing TaskEngine table.

        The caller supplies server-derived Permission identity and scope
        material. This method stores no approval token and does not authorize
        or claim that training has started or succeeded.
        """
        normalized_binding = _validate_training_receipt_binding(binding)
        normalized_fingerprints = _validate_training_receipt_fingerprints(fingerprints)
        sealed = approval_reference is not None or pinned_public_key is not None
        if (approval_reference is None) != (pinned_public_key is None):
            raise ValueError("sealed training admission requires both approval reference and public key pin")
        normalized_reference = (
            _validate_training_approval_reference(approval_reference) if sealed else None
        )
        normalized_key = _validate_training_public_key_pin(pinned_public_key) if sealed else None
        if sealed and connection is None:
            raise RuntimeError("sealed training task creation requires the caller transaction")
        if connection is not None:
            self._require_training_receipt_connection(connection)
        task_id = f"{_TRAINING_RECEIPT_TASK_PREFIX}{uuid.uuid4()}"
        _require_training_receipt_task_id(task_id)
        context = {
            "managed_owner": _TRAINING_RECEIPT_OWNER,
            "binding": normalized_binding,
            "fingerprints": normalized_fingerprints,
            "run_digest": hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
            "task_digest": _training_receipt_task_digest(task_id),
            "next_sequence": 1,
            "last_receipt_sha256": None,
        }
        if sealed:
            context["admission"] = {
                "schema_version": 2,
                "approval_reference": normalized_reference,
                "public_key_pin": normalized_key,
                "last_phase": None,
                "pending_step_id": None,
                "terminal": False,
            }
        now = self._now()
        context_manager = (get_repository().transaction(timeout=30)
                           if connection is None else nullcontext(connection))
        with context_manager as conn:
            if sealed:
                rows = conn.execute(
                    "SELECT * FROM ai_task WHERE created_by=? ORDER BY task_id",
                    (_TRAINING_RECEIPT_TASK_CREATOR,),
                ).fetchall()
                matches = []
                for candidate_row in rows:
                    candidate = dict(candidate_row)
                    raw_context = _strict_json_loads(
                        candidate.get("context_json"), field_name="training receipt task context",
                    )
                    if type(raw_context) is not dict or raw_context.get("managed_owner") != _TRAINING_RECEIPT_OWNER:
                        raise ValueError("managed training task context is invalid")
                    candidate_binding = _validate_training_receipt_binding(raw_context.get("binding"))
                    candidate_task, candidate_context = self._training_receipt_row_state(
                        candidate_row, candidate_binding,
                    )
                    existing_admission = candidate_context.get("admission")
                    if (existing_admission is not None
                            and existing_admission["approval_reference"]["approval_token_sha256"]
                            == normalized_reference["approval_token_sha256"]):
                        matches.append((candidate_task, candidate_context))
                if len(matches) > 1:
                    raise RuntimeError("one training approval grant matches multiple managed tasks")
                if matches:
                    existing_task, existing_context = matches[0]
                    existing_admission = existing_context["admission"]
                    if (
                        existing_context["binding"] != normalized_binding
                        or existing_context["fingerprints"] != normalized_fingerprints
                        or existing_admission["approval_reference"] != normalized_reference
                        or existing_admission["public_key_pin"] != normalized_key
                    ):
                        raise PermissionError("training approval grant is already bound to different task material")
                    return _training_receipt_public_state(
                        existing_task["task_id"], existing_context, existing_task["status"],
                    )
            conn.execute(
                """INSERT INTO ai_task
                   (task_id, user_input, context_json, status, risk_level,
                    created_at, updated_at, created_by)
                   VALUES (?, ?, ?, 'ready', 'L0', ?, ?, ?)""",
                (
                    task_id, _TRAINING_RECEIPT_USER_INPUT,
                    _serialize_strict_json(context, field_name="training receipt context"),
                    now, now, _TRAINING_RECEIPT_TASK_CREATOR,
                ),
            )
        return _training_receipt_public_state(task_id, context, "ready")

    def get_training_receipt_task(
        self, task_id: str, *, expected_binding: Dict[str, Any],
        connection: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        """Read one managed phase task without exposing its private binding."""
        task_id = _require_training_receipt_task_id(task_id)
        binding = _validate_training_receipt_binding(expected_binding)
        if connection is not None:
            self._require_training_receipt_connection(connection)
        context_manager = (get_repository().connection(timeout=30)
                           if connection is None else nullcontext(connection))
        with context_manager as conn:
            row = conn.execute(
                "SELECT * FROM ai_task WHERE task_id=? AND created_by=?",
                (task_id, _TRAINING_RECEIPT_TASK_CREATOR),
            ).fetchone()
        task, context = self._training_receipt_row_state(row, binding)
        return _training_receipt_public_state(task_id, context, task["status"])

    @staticmethod
    def _require_training_receipt_v2_task(
        row: Any, *, task_id: str, expected_binding: Dict[str, Any],
        expected_approval_reference: Dict[str, Any],
        expected_public_key: Optional[Dict[str, Any]] = None,
    ):
        task, context = TaskEngine._training_receipt_row_state(row, expected_binding)
        admission = context.get("admission")
        if admission is None:
            raise PermissionError("training receipt task does not have sealed v2 admission")
        normalized_reference = _validate_training_approval_reference(expected_approval_reference)
        if admission["approval_reference"] != normalized_reference:
            raise PermissionError("training receipt approval reference does not match the sealed task")
        if expected_public_key is not None:
            normalized_key = _validate_training_public_key_pin(expected_public_key)
            if admission["public_key_pin"] != normalized_key:
                raise PermissionError("training receipt public key pin does not match the sealed task")
        return task, context, admission

    def require_training_receipt_admission(
        self, task_id: str, expected_binding: Dict[str, Any],
        expected_approval_reference: Dict[str, Any],
        expected_public_key: Optional[Dict[str, Any]] = None,
        connection: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        """Read sealed v2 state only after the caller supplies its current exact grant reference."""
        task_id = _require_training_receipt_task_id(task_id)
        binding = _validate_training_receipt_binding(expected_binding)
        if connection is None:
            raise RuntimeError("sealed training admission requires the caller transaction")
        self._require_training_receipt_connection(connection)
        row = connection.execute(
            "SELECT * FROM ai_task WHERE task_id=? AND created_by=?",
            (task_id, _TRAINING_RECEIPT_TASK_CREATOR),
        ).fetchone()
        task, context, _admission = self._require_training_receipt_v2_task(
            row, task_id=task_id, expected_binding=binding,
            expected_approval_reference=expected_approval_reference,
            expected_public_key=expected_public_key,
        )
        return _training_receipt_public_state(task_id, context, task["status"])

    def get_training_receipt_history_material(
        self, task_id: str, *, expected_identity: Dict[str, Any],
        connection: sqlite3.Connection,
    ) -> Dict[str, Any]:
        """Return validated private material for an already sealed task owner.

        This is a read-only server composition helper. It neither authenticates
        the caller nor restores Permission authority from the persisted grant.
        """
        from copy import deepcopy

        task_id = _require_training_receipt_task_id(task_id)
        self._require_training_receipt_connection(connection)
        row = connection.execute(
            "SELECT * FROM ai_task WHERE task_id=? AND created_by=?",
            (task_id, _TRAINING_RECEIPT_TASK_CREATOR),
        ).fetchone()
        if row is None:
            raise KeyError("Managed training receipt task not found")
        task_row = dict(row)
        if (task_row.get("created_by") != _TRAINING_RECEIPT_TASK_CREATOR
                or task_row.get("user_input") != _TRAINING_RECEIPT_USER_INPUT):
            raise PermissionError("task is not owned by the training receipt state owner")

        stored_raw = _strict_json_loads(
            task_row.get("context_json"), field_name="training receipt task context",
        )
        if (type(stored_raw) is not dict
                or set(stored_raw) != _TRAINING_RECEIPT_V2_CONTEXT_FIELDS
                or stored_raw.get("managed_owner") != _TRAINING_RECEIPT_OWNER):
            raise ValueError("training history requires a sealed v2 task context")
        stored_binding = _validate_training_receipt_binding(stored_raw.get("binding"))
        binding = _validate_training_receipt_binding({
            "resource": stored_binding["resource"],
            "identity": expected_identity,
            "scope_descriptors": stored_binding["scope_descriptors"],
        })
        if binding["identity"] != stored_binding["identity"]:
            raise PermissionError("training receipt task identity does not match the expected identity")

        raw_admission = stored_raw.get("admission")
        if type(raw_admission) is not dict:
            raise ValueError("training history requires sealed v2 admission")
        reference = _validate_training_approval_reference(raw_admission.get("approval_reference"))
        task, context, admission = self._require_training_receipt_v2_task(
            task_row, task_id=task_id, expected_binding=binding,
            expected_approval_reference=reference,
        )
        approval_reference = _validate_training_approval_reference(
            admission["approval_reference"],
        )
        pinned_public_key = _validate_training_public_key_pin(admission["public_key_pin"])
        return {
            "binding": deepcopy(context["binding"]),
            "fingerprints": deepcopy(context["fingerprints"]),
            "approval_reference": deepcopy(approval_reference),
            "pinned_public_key": deepcopy(pinned_public_key),
        }

    def prepare_training_phase_challenge(
        self, task_id: str, expected_binding: Dict[str, Any],
        expected_approval_reference: Dict[str, Any],
        pinned_public_key: Dict[str, Any], phase: str,
        connection: sqlite3.Connection, now: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Persist or read the one server-generated live challenge for the next phase."""
        task_id = _require_training_receipt_task_id(task_id)
        binding = _validate_training_receipt_binding(expected_binding)
        reference = _validate_training_approval_reference(expected_approval_reference)
        key_pin = _validate_training_public_key_pin(pinned_public_key)
        self._require_training_receipt_connection(connection)
        from lumenis.system.security.training_receipts import validate_training_phase_challenge

        current_time = _training_phase_now(now)
        if type(phase) is not str or phase not in _TRAINING_PHASES:
            raise ValueError("training phase is not registered")
        if _training_approval_expiry_seconds(reference) <= current_time:
            raise PermissionError("training approval reference has expired")
        row = connection.execute(
            "SELECT * FROM ai_task WHERE task_id=? AND created_by=?",
            (task_id, _TRAINING_RECEIPT_TASK_CREATOR),
        ).fetchone()
        task, context, admission = self._require_training_receipt_v2_task(
            row, task_id=task_id, expected_binding=binding,
            expected_approval_reference=reference, expected_public_key=key_pin,
        )
        if task["status"] not in {"ready", "running"} or admission["terminal"]:
            raise PermissionError("training phase task is not available for challenge preparation")
        if context["next_sequence"] >= 1_000_000_000:
            raise RuntimeError("training phase sequence space is exhausted; a new task is required")
        if not _training_phase_transition_allowed(admission["last_phase"], phase):
            raise PermissionError("training phase transition is not allowed")

        expired_pending = None
        if admission["pending_step_id"] is not None:
            pending_row = connection.execute(
                "SELECT * FROM ai_task_step WHERE step_id=? AND task_id=?",
                (admission["pending_step_id"], task_id),
            ).fetchone()
            if pending_row is None or pending_row["status"] != "pending":
                raise ValueError("training admission pending step is missing or inconsistent")
            pending_detail = _strict_json_loads(
                pending_row["detail"], field_name="training phase pending step detail",
            )
            if type(pending_detail) is not dict or set(pending_detail) != {"challenge"}:
                raise ValueError("training phase pending step detail is invalid")
            stored_challenge = pending_detail["challenge"]
            if type(stored_challenge) is not dict:
                raise ValueError("training phase pending challenge is invalid")
            try:
                historical_pending = validate_training_phase_challenge(
                    stored_challenge, now=stored_challenge.get("issued_at"),
                )
            except (TypeError, ValueError):
                raise ValueError("training phase pending challenge is invalid") from None
            if (not _training_challenge_matches_context(historical_pending, context)
                    or historical_pending["phase"] != pending_row["phase"]
                    or historical_pending["phase"] != phase
                    or _training_phase_step_id(task_id, historical_pending["nonce"])
                    != admission["pending_step_id"]):
                raise ValueError("training phase pending challenge does not match current task state")
            if historical_pending["expires_at"] > current_time:
                try:
                    return validate_training_phase_challenge(stored_challenge, now=current_time)
                except (TypeError, ValueError):
                    raise ValueError("training phase pending challenge is invalid") from None
            expired_pending = (pending_row, pending_detail)

        expires_at = min(
            current_time + 60,
            _training_approval_expiry_seconds(reference),
        )
        if expires_at <= current_time:
            raise PermissionError("training approval reference has expired")
        challenge = {
            "schema_version": 1,
            "run_digest": context["run_digest"],
            "task_digest": context["task_digest"],
            **context["fingerprints"],
            "nonce": secrets.token_hex(32),
            "phase": phase,
            "sequence": context["next_sequence"],
            "issued_at": current_time,
            "expires_at": expires_at,
        }
        challenge = validate_training_phase_challenge(challenge, now=current_time)
        step_id = _training_phase_step_id(task_id, challenge["nonce"])
        step_detail = _serialize_strict_json(
            {"challenge": challenge}, field_name="training phase pending step detail",
        )
        next_context = dict(context)
        next_admission = dict(admission)
        next_admission["pending_step_id"] = step_id
        next_context["admission"] = next_admission
        serialized_context = _serialize_strict_json(
            next_context, field_name="training receipt context",
        )
        savepoint = "sealed_training_phase_prepare"
        connection.execute(f"SAVEPOINT {savepoint}")
        try:
            if expired_pending is not None:
                old_row, old_detail = expired_pending
                expired_cursor = connection.execute(
                    """UPDATE ai_task_step SET status='expired', finished_at=?
                       WHERE step_id=? AND task_id=? AND status='pending' AND detail=?""",
                    (self._now(), old_row["step_id"], task_id,
                     _serialize_strict_json(old_detail, field_name="training phase pending step detail")),
                )
                if expired_cursor.rowcount != 1:
                    raise RuntimeError("training phase pending step changed during expiry")
            connection.execute(
                """INSERT INTO ai_task_step
                   (step_id, task_id, phase, status, detail, started_at,
                    finished_at, duration_ms, error)
                   VALUES (?, ?, ?, 'pending', ?, ?, NULL, NULL, NULL)""",
                (step_id, task_id, phase, step_detail, self._now()),
            )
            updated = connection.execute(
                """UPDATE ai_task SET context_json=?, updated_at=?
                   WHERE task_id=? AND created_by=? AND status=? AND context_json=?""",
                (serialized_context, self._now(), task_id, _TRAINING_RECEIPT_TASK_CREATOR,
                 task["status"], task["context_json"]),
            )
            if updated.rowcount != 1:
                raise RuntimeError("training receipt task changed during challenge preparation")
            connection.execute(f"RELEASE SAVEPOINT {savepoint}")
        except Exception:
            connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise
        return dict(challenge)

    def require_pending_training_phase_challenge(
        self, task_id: str, expected_binding: Dict[str, Any],
        expected_approval_reference: Dict[str, Any],
        pinned_public_key: Dict[str, Any], challenge: Dict[str, Any],
        connection: sqlite3.Connection, now: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Require byte-for-byte equality with the live server-persisted challenge."""
        task_id = _require_training_receipt_task_id(task_id)
        binding = _validate_training_receipt_binding(expected_binding)
        reference = _validate_training_approval_reference(expected_approval_reference)
        key_pin = _validate_training_public_key_pin(pinned_public_key)
        self._require_training_receipt_connection(connection)
        from lumenis.system.security.training_receipts import validate_training_phase_challenge

        current_time = _training_phase_now(now)
        row = connection.execute(
            "SELECT * FROM ai_task WHERE task_id=? AND created_by=?",
            (task_id, _TRAINING_RECEIPT_TASK_CREATOR),
        ).fetchone()
        task, context, admission = self._require_training_receipt_v2_task(
            row, task_id=task_id, expected_binding=binding,
            expected_approval_reference=reference, expected_public_key=key_pin,
        )
        if task["status"] not in {"ready", "running"} or admission["terminal"]:
            raise PermissionError("training phase task is not available for a pending challenge")
        if admission["pending_step_id"] is None:
            raise PermissionError("training phase task has no pending server challenge")
        validated = validate_training_phase_challenge(challenge, now=current_time)
        if (not _training_challenge_matches_context(validated, context)
                or not _training_phase_transition_allowed(admission["last_phase"], validated["phase"])
                or _training_phase_step_id(task_id, validated["nonce"]) != admission["pending_step_id"]):
            raise PermissionError("training phase challenge does not match the current pending task")
        step = connection.execute(
            "SELECT * FROM ai_task_step WHERE step_id=? AND task_id=?",
            (admission["pending_step_id"], task_id),
        ).fetchone()
        if step is None or step["status"] != "pending" or step["phase"] != validated["phase"]:
            raise PermissionError("training phase challenge is not pending")
        detail = _strict_json_loads(step["detail"], field_name="training phase pending step detail")
        if type(detail) is not dict or set(detail) != {"challenge"} or detail["challenge"] != validated:
            raise PermissionError("training phase challenge differs from the server-persisted challenge")
        return validated

    def consume_training_phase_challenge(
        self, task_id: str, *, expected_binding: Dict[str, Any], challenge: Dict[str, Any],
        receipt_sha256: str, decision: str, connection: sqlite3.Connection,
        receipt: Optional[Dict[str, Any]] = None,
        expected_approval_reference: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Consume one legacy nonce or one sealed, fully signed v2 phase receipt."""
        task_id = _require_training_receipt_task_id(task_id)
        binding = _validate_training_receipt_binding(expected_binding)
        if type(receipt_sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", receipt_sha256) is None:
            raise ValueError("training phase receipt hash must be a lowercase SHA-256 digest")
        if type(decision) is not str or decision not in {"allow", "deny"}:
            raise ValueError("training phase decision must be allow or deny")
        self._require_training_receipt_connection(connection)

        from lumenis.system.security.training_receipts import (
            _canonical_json_bytes,
            validate_training_phase_challenge,
            verify_training_phase_decision,
        )

        row = connection.execute(
            "SELECT * FROM ai_task WHERE task_id=? AND created_by=?",
            (task_id, _TRAINING_RECEIPT_TASK_CREATOR),
        ).fetchone()
        task, context = self._training_receipt_row_state(row, binding)
        admission = context.get("admission")
        if admission is not None:
            try:
                historical_now = challenge.get("issued_at") if type(challenge) is dict else None
                validated = validate_training_phase_challenge(challenge, now=historical_now)
            except (TypeError, ValueError):
                raise ValueError("sealed training phase challenge is invalid") from None
            if receipt is None or expected_approval_reference is None:
                raise PermissionError("sealed training receipt and current approval reference are required")
            reference = _validate_training_approval_reference(expected_approval_reference)
            if reference != admission["approval_reference"]:
                raise PermissionError("training receipt approval reference does not match the sealed task")
            if decision != "allow":
                raise PermissionError("sealed training phase receipts must verify an allow decision")
            try:
                canonical_receipt = _canonical_json_bytes(receipt)
            except (TypeError, ValueError):
                raise ValueError("training phase signed receipt is not canonical JSON") from None
            actual_receipt_sha256 = hashlib.sha256(canonical_receipt).hexdigest()
            if actual_receipt_sha256 != receipt_sha256:
                raise ValueError("training phase receipt hash does not match the complete signed receipt")

            step_id = _training_phase_step_id(task_id, validated["nonce"])
            existing_step = connection.execute(
                "SELECT * FROM ai_task_step WHERE step_id=? AND task_id=?",
                (step_id, task_id),
            ).fetchone()
            if existing_step is not None and existing_step["status"] == "allow":
                stored_detail = _strict_json_loads(
                    existing_step["detail"], field_name="training phase receipt step detail",
                )
                if type(stored_detail) is not dict or set(stored_detail) != {
                    "challenge", "receipt_sha256", "decision", "receipt",
                }:
                    raise ValueError("stored sealed training receipt detail is invalid")
                stored_challenge = stored_detail["challenge"]
                stored_receipt = stored_detail["receipt"]
                if (stored_detail["decision"] != "allow"
                        or stored_detail["receipt_sha256"] != receipt_sha256
                        or stored_receipt != receipt
                        or stored_challenge != validated
                        or existing_step["phase"] != validated["phase"]
                        or hashlib.sha256(_canonical_json_bytes(stored_receipt)).hexdigest()
                        != stored_detail["receipt_sha256"]):
                    raise PermissionError("training phase nonce was already consumed with different receipt bytes")
                issued_at = stored_receipt.get("issued_at") if type(stored_receipt) is dict else None
                try:
                    historical_challenge = validate_training_phase_challenge(
                        stored_challenge, now=stored_challenge.get("issued_at"),
                    )
                    verify_training_phase_decision(
                        stored_receipt,
                        expected_challenge=historical_challenge,
                        pinned_public_key=admission["public_key_pin"],
                        now=issued_at,
                    )
                except (TypeError, ValueError):
                    raise ValueError("stored sealed training phase receipt failed historical verification") from None
                if (historical_challenge["task_digest"] != context["task_digest"]
                        or any(historical_challenge.get(name) != value
                               for name, value in context["fingerprints"].items())):
                    raise ValueError("stored sealed training receipt no longer matches task material")
                return _training_receipt_public_state(task_id, context, task["status"])

            if task["status"] not in {"ready", "running"}:
                raise PermissionError("training phase task is not available for challenge consumption")
            current_time = int(time.time())
            pending_challenge = self.require_pending_training_phase_challenge(
                task_id, binding, reference, admission["public_key_pin"], validated,
                connection, now=current_time,
            )
            verify_training_phase_decision(
                receipt,
                expected_challenge=pending_challenge,
                pinned_public_key=admission["public_key_pin"],
                now=current_time,
            )
            next_context = dict(context)
            next_context["next_sequence"] += 1
            next_context["last_receipt_sha256"] = receipt_sha256
            next_admission = dict(admission)
            next_admission["last_phase"] = pending_challenge["phase"]
            next_admission["pending_step_id"] = None
            next_admission["terminal"] = pending_challenge["phase"] == _TRAINING_TERMINAL_PHASE
            next_context["admission"] = next_admission
            serialized_context = _serialize_strict_json(
                next_context, field_name="training receipt context",
            )
            detail = _serialize_strict_json(
                {
                    "challenge": pending_challenge,
                    "receipt_sha256": receipt_sha256,
                    "decision": "allow",
                    "receipt": receipt,
                },
                field_name="training phase receipt step detail",
            )
            next_status = "completed" if next_admission["terminal"] else "running"
            now_text = self._now()
            savepoint = "sealed_training_phase_consume"
            connection.execute(f"SAVEPOINT {savepoint}")
            try:
                updated_step = connection.execute(
                    """UPDATE ai_task_step SET status='allow', detail=?, finished_at=?, duration_ms=0
                       WHERE step_id=? AND task_id=? AND status='pending' AND phase=?""",
                    (detail, now_text, step_id, task_id, pending_challenge["phase"]),
                )
                if updated_step.rowcount != 1:
                    raise RuntimeError("training phase pending receipt changed during consumption")
                updated_task = connection.execute(
                    """UPDATE ai_task SET context_json=?, status=?, updated_at=?,
                           finished_at=CASE WHEN ?='completed' THEN ? ELSE NULL END
                       WHERE task_id=? AND created_by=? AND status=? AND context_json=?""",
                    (serialized_context, next_status, now_text, next_status, now_text,
                     task_id, _TRAINING_RECEIPT_TASK_CREATOR, task["status"], task["context_json"]),
                )
                if updated_task.rowcount != 1:
                    raise RuntimeError("training phase task changed during receipt consumption")
                connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            except Exception:
                connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                connection.execute(f"RELEASE SAVEPOINT {savepoint}")
                raise
            return _training_receipt_public_state(task_id, next_context, next_status)

        if receipt is not None or expected_approval_reference is not None:
            raise ValueError("legacy training receipt tasks cannot be promoted to sealed admission")
        validated = validate_training_phase_challenge(challenge)
        if task["status"] not in {"ready", "running"}:
            raise PermissionError("training phase task is not available for challenge consumption")
        expected_challenge_fields = {
            "run_digest": context["run_digest"],
            "task_digest": context["task_digest"],
            **context["fingerprints"],
            "sequence": context["next_sequence"],
        }
        if any(validated.get(name) != value for name, value in expected_challenge_fields.items()):
            raise PermissionError("training phase challenge does not match the current task state")
        # The persisted next_sequence must remain within the same bound that
        # the SYSTEM Security challenge validator accepts on every later read.
        if context["next_sequence"] >= 1_000_000_000:
            raise RuntimeError("training phase sequence space is exhausted; a new task is required")

        now = self._now()
        step_id = "trainphase_" + hashlib.sha256(
            (task_id + validated["nonce"]).encode("utf-8")
        ).hexdigest()
        detail = _serialize_strict_json(
            {
                "challenge": validated,
                "receipt_sha256": receipt_sha256,
                "decision": decision,
            },
            field_name="training phase receipt step detail",
        )
        next_context = dict(context)
        next_context["next_sequence"] += 1
        next_context["last_receipt_sha256"] = receipt_sha256
        serialized_context = _serialize_strict_json(
            next_context, field_name="training receipt context",
        )
        next_status = "running" if decision == "allow" else "failed"
        savepoint = "training_phase_receipt_consume"
        connection.execute(f"SAVEPOINT {savepoint}")
        try:
            connection.execute(
                """INSERT INTO ai_task_step
                   (step_id, task_id, phase, status, detail, started_at,
                    finished_at, duration_ms, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL)""",
                (step_id, task_id, validated["phase"], decision, detail, now, now),
            )
            cursor = connection.execute(
                """UPDATE ai_task SET context_json=?, status=?, updated_at=?,
                       finished_at=CASE WHEN ?='failed' THEN ? ELSE NULL END
                   WHERE task_id=? AND created_by=? AND status=? AND context_json=?""",
                (
                    serialized_context, next_status, now, next_status, now,
                    task_id, _TRAINING_RECEIPT_TASK_CREATOR, task["status"],
                    task["context_json"],
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("training phase task changed during nonce consumption")
            connection.execute(f"RELEASE SAVEPOINT {savepoint}")
        except Exception:
            connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise
        return _training_receipt_public_state(task_id, next_context, next_status)

    def get_training_phase_receipt(
        self, task_id: str, expected_binding: Dict[str, Any],
        expected_approval_reference: Dict[str, Any], nonce: str,
        connection: sqlite3.Connection,
    ) -> Optional[Dict[str, Any]]:
        """Read back one committed signed receipt without renewing its authority."""
        task_id = _require_training_receipt_task_id(task_id)
        binding = _validate_training_receipt_binding(expected_binding)
        reference = _validate_training_approval_reference(expected_approval_reference)
        if type(nonce) is not str or re.fullmatch(r"[0-9a-f]{64}", nonce) is None:
            raise ValueError("training phase receipt nonce is invalid")
        self._require_training_receipt_connection(connection)
        from lumenis.system.security.training_receipts import (
            _canonical_json_bytes,
            validate_training_phase_challenge,
            verify_training_phase_decision,
        )

        row = connection.execute(
            "SELECT * FROM ai_task WHERE task_id=? AND created_by=?",
            (task_id, _TRAINING_RECEIPT_TASK_CREATOR),
        ).fetchone()
        task, context, admission = self._require_training_receipt_v2_task(
            row, task_id=task_id, expected_binding=binding,
            expected_approval_reference=reference,
        )
        step_id = _training_phase_step_id(task_id, nonce)
        step = connection.execute(
            "SELECT * FROM ai_task_step WHERE step_id=? AND task_id=?",
            (step_id, task_id),
        ).fetchone()
        if step is None:
            raise KeyError("Training phase nonce was not found")
        detail = _strict_json_loads(step["detail"], field_name="training phase receipt step detail")
        if step["status"] == "pending":
            if type(detail) is not dict or set(detail) != {"challenge"}:
                raise ValueError("pending training phase detail is invalid")
            challenge_value = detail["challenge"]
            try:
                issued_at = challenge_value.get("issued_at") if type(challenge_value) is dict else None
                historical_challenge = validate_training_phase_challenge(
                    challenge_value, now=issued_at,
                )
            except (TypeError, ValueError):
                raise ValueError("pending training phase challenge is invalid") from None
            if (admission["pending_step_id"] != step_id
                    or _training_phase_step_id(task_id, historical_challenge["nonce"]) != step_id
                    or historical_challenge["task_digest"] != context["task_digest"]
                    or any(historical_challenge.get(name) != value
                           for name, value in context["fingerprints"].items())
                    or historical_challenge["phase"] != step["phase"]):
                raise ValueError("pending training phase challenge does not match task state")
            return None
        if step["status"] != "allow" or type(detail) is not dict or set(detail) != {
            "challenge", "receipt_sha256", "decision", "receipt",
        }:
            raise PermissionError("training phase nonce has no committed signed allow receipt")
        challenge_value = detail["challenge"]
        receipt = detail["receipt"]
        issued_at = receipt.get("issued_at") if type(receipt) is dict else None
        try:
            challenge_issued_at = challenge_value.get("issued_at") if type(challenge_value) is dict else None
            challenge_copy = validate_training_phase_challenge(
                challenge_value, now=challenge_issued_at,
            )
            if detail["decision"] != "allow":
                raise ValueError("stored decision is not allow")
            receipt_digest = hashlib.sha256(_canonical_json_bytes(receipt)).hexdigest()
            if (type(detail["receipt_sha256"]) is not str
                    or re.fullmatch(r"[0-9a-f]{64}", detail["receipt_sha256"]) is None
                    or receipt_digest != detail["receipt_sha256"]
                    or step["phase"] != challenge_copy["phase"]
                    or challenge_copy["task_digest"] != context["task_digest"]
                    or any(challenge_copy.get(name) != value
                           for name, value in context["fingerprints"].items())):
                raise ValueError("stored signed receipt material does not match")
            verify_training_phase_decision(
                receipt,
                expected_challenge=challenge_copy,
                pinned_public_key=admission["public_key_pin"],
                now=issued_at,
            )
        except (TypeError, ValueError):
            raise ValueError("stored training phase receipt failed historical verification") from None
        return {
            "receipt": dict(receipt),
            "challenge": dict(challenge_copy),
            "state": _training_receipt_public_state(task_id, context, task["status"]),
            "pinned_public_key": dict(admission["public_key_pin"]),
        }

    def interrupt_training_receipt_task(
        self, task_id: str, *, expected_binding: Dict[str, Any],
        connection: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        """Mark an active managed phase task unknown for explicit recovery."""
        task_id = _require_training_receipt_task_id(task_id)
        binding = _validate_training_receipt_binding(expected_binding)
        if connection is not None:
            self._require_training_receipt_connection(connection)
        now = self._now()
        context_manager = (get_repository().transaction(timeout=30)
                           if connection is None else nullcontext(connection))
        with context_manager as conn:
            row = conn.execute(
                "SELECT * FROM ai_task WHERE task_id=? AND created_by=?",
                (task_id, _TRAINING_RECEIPT_TASK_CREATOR),
            ).fetchone()
            task, context = self._training_receipt_row_state(row, binding)
            if task["status"] not in {"ready", "running"}:
                raise PermissionError("only an active training receipt task can be interrupted")
            admission = context.get("admission")
            if admission is not None:
                next_context = dict(context)
                next_admission = dict(admission)
                pending_step_id = admission["pending_step_id"]
                pending_step = None
                if pending_step_id is not None:
                    pending_step = conn.execute(
                        "SELECT * FROM ai_task_step WHERE step_id=? AND task_id=?",
                        (pending_step_id, task_id),
                    ).fetchone()
                    if pending_step is None or pending_step["status"] != "pending":
                        raise ValueError("training admission pending step is missing or inconsistent")
                    pending_detail = _strict_json_loads(
                        pending_step["detail"], field_name="training phase pending step detail",
                    )
                    if type(pending_detail) is not dict or set(pending_detail) != {"challenge"}:
                        raise ValueError("training phase pending step detail is invalid")
                    challenge_value = pending_detail["challenge"]
                    try:
                        from lumenis.system.security.training_receipts import validate_training_phase_challenge

                        historical_challenge = validate_training_phase_challenge(
                            challenge_value,
                            now=challenge_value.get("issued_at") if type(challenge_value) is dict else None,
                        )
                    except (TypeError, ValueError):
                        raise ValueError("training phase pending challenge is invalid") from None
                    if (not _training_challenge_matches_context(historical_challenge, context)
                            or historical_challenge["phase"] != pending_step["phase"]
                            or _training_phase_step_id(task_id, historical_challenge["nonce"])
                            != pending_step_id):
                        raise ValueError("training phase pending challenge does not match task state")
                next_admission["pending_step_id"] = None
                next_context["admission"] = next_admission
                serialized_context = _serialize_strict_json(
                    next_context, field_name="training receipt context",
                )
                savepoint = "sealed_training_phase_interrupt"
                conn.execute(f"SAVEPOINT {savepoint}")
                try:
                    if pending_step is not None:
                        interrupted_step = conn.execute(
                            """UPDATE ai_task_step SET status='interrupted', finished_at=?
                               WHERE step_id=? AND task_id=? AND status='pending'""",
                            (now, pending_step_id, task_id),
                        )
                        if interrupted_step.rowcount != 1:
                            raise RuntimeError("training phase pending step changed during interruption")
                    cursor = conn.execute(
                        """UPDATE ai_task SET context_json=?, status='unknown', updated_at=?
                           WHERE task_id=? AND created_by=? AND status=? AND context_json=?""",
                        (serialized_context, now, task_id, _TRAINING_RECEIPT_TASK_CREATOR,
                         task["status"], task["context_json"]),
                    )
                    if cursor.rowcount != 1:
                        raise RuntimeError("training receipt task changed during interruption")
                    conn.execute(f"RELEASE SAVEPOINT {savepoint}")
                except Exception:
                    conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                    conn.execute(f"RELEASE SAVEPOINT {savepoint}")
                    raise
                return _training_receipt_public_state(task_id, next_context, "unknown")
            cursor = conn.execute(
                """UPDATE ai_task SET status='unknown', updated_at=?
                   WHERE task_id=? AND created_by=? AND status=? AND context_json=?""",
                (now, task_id, _TRAINING_RECEIPT_TASK_CREATOR,
                 task["status"], task["context_json"]),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("training receipt task changed during interruption")
        return _training_receipt_public_state(task_id, context, "unknown")

    def resume_training_receipt_task(
        self, task_id: str, *, expected_binding: Dict[str, Any],
        connection: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        """Start a new challenge epoch only after explicit interruption recovery."""
        task_id = _require_training_receipt_task_id(task_id)
        binding = _validate_training_receipt_binding(expected_binding)
        if connection is not None:
            self._require_training_receipt_connection(connection)
        now = self._now()
        context_manager = (get_repository().transaction(timeout=30)
                           if connection is None else nullcontext(connection))
        with context_manager as conn:
            row = conn.execute(
                "SELECT * FROM ai_task WHERE task_id=? AND created_by=?",
                (task_id, _TRAINING_RECEIPT_TASK_CREATOR),
            ).fetchone()
            task, context = self._training_receipt_row_state(row, binding)
            if task["status"] != "unknown":
                raise PermissionError("only an unknown training receipt task can be resumed")
            admission = context.get("admission")
            if admission is not None and admission["pending_step_id"] is not None:
                raise ValueError("unknown sealed training task still has a pending challenge")
            next_context = dict(context)
            next_context["run_digest"] = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
            serialized_context = _serialize_strict_json(
                next_context, field_name="training receipt context",
            )
            cursor = conn.execute(
                """UPDATE ai_task SET context_json=?, status='ready', error=NULL,
                       finished_at=NULL, updated_at=?
                   WHERE task_id=? AND created_by=? AND status='unknown' AND context_json=?""",
                (serialized_context, now, task_id, _TRAINING_RECEIPT_TASK_CREATOR,
                 task["context_json"]),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("training receipt task changed during recovery")
        return _training_receipt_public_state(task_id, next_context, "ready")

    # ──────────────────────────────────────────────────────────
    # 2. 解析任务（Parser → Intent）
    # ──────────────────────────────────────────────────────────

    def parse_task(self, task_id: str) -> Dict[str, Any]:
        """解析任务：提取 intent/entities/parameters/context。"""
        _guard_generic_task_access(task_id)
        task = self._db_get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        self._db_update_task(task_id, status=TaskStatus.PARSING.value)
        step_id = self._db_add_step(task_id, StepPhase.PARSE.value, "running", "Parsing user input")
        trace_start = self._now()

        try:
            context = task.get("context") or {}
            parse_input = task["user_input"]
            if context.get("analysis_operation") in {"source_statistics", "openai_math"}:
                # An explicit read-only operation is not a free-form command.
                # Revalidate its authenticated Owner input before routing it;
                # the word "publication" must not turn date counts into publishing.
                self._read_analysis_source(task)
                parse_input = "统计来源样本"
            parsed = self.parser.parse(
                parse_input,
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
        _guard_generic_task_access(task_id)
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
        context = task.get("context") or {}
        agent = (self.agent_registry.get("analysis_agent")
                 if context.get("analysis_operation") in {"source_statistics", "openai_math"}
                 else self.agent_registry.select_best_agent(intent, context))

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
        skills = ([] if context.get("analysis_operation") in {"source_statistics", "openai_math"}
                  else self.agent_registry.select_skills(agent, intent, context))
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
        _guard_generic_task_access(task_id)
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
                elif (task.get("intent") == "generate_report" or agent_id == "analysis_agent"
                      or (task.get("context") or {}).get("source_brief_job_id")):
                    op_type = OperationType.REPORT_GENERATE
                else:
                    op_type = OperationType.AI_CALL

                permission_context = {}
                if (task.get("context") or {}).get("source_brief_job_id"):
                    # Reopen through the scoped Owner before using its domain.
                    # Body-supplied domain fields and cached operation decisions
                    # must not substitute for live source/actor authorization.
                    report = self._read_analysis_source(task)
                    permission_context["domain_id"] = report["source_brief"]["scope"]["domain_id"]
                result = self.permission_gate.check(
                    operation_type=op_type,
                    resource=f"ai_task:{task_id}",
                    caller="task_engine",
                    operation_id=None if permission_context else f"task_{task_id}",
                    **permission_context,
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
        _guard_generic_task_access(task_id)
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
        _guard_generic_task_access(task_id)
        task = self._db_get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        from agent_runtime.agent_zero_gui_executor import is_agent_zero_gui_task
        if is_agent_zero_gui_task(task):
            from agent_runtime.agent_zero_gui_executor import AGENT_ZERO_TASK_RECORD
            record = (task.get("parameters") or {}).get(AGENT_ZERO_TASK_RECORD)
            if (task.get("status") in {
                    TaskStatus.SUCCEEDED.value, TaskStatus.CANCELLED.value, TaskStatus.UNKNOWN.value,
            } or (record and task.get("status") == TaskStatus.FAILED.value)):
                return task

        # 熔断检查
        if not self._circuit.can_execute():
            reason = f"CIRCUIT_BREAKER_OPEN: {self._circuit.get_state()}"
            self._db_update_task(task_id, status=TaskStatus.FAILED.value, error=reason,
                                 finished_at=self._now())
            self._db_add_evidence(task_id, "circuit_breaker", reason, source="circuit_breaker")
            return self._db_get_task(task_id)

        from agent_runtime.agent_zero_gui_executor import is_agent_zero_gui_task
        # External GUI tasks have durable attempt identity and may not be replayed
        # by the generic retry loop after an ambiguous worker result.
        max_retries = 0 if is_agent_zero_gui_task(task) else task.get("max_retries", self.default_max_retries)
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
        _guard_generic_task_access(task_id)
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

            from agent_runtime.agent_zero_gui_executor import is_agent_zero_gui_task
            if is_agent_zero_gui_task(task) and isinstance(result_data, dict):
                current_task = self._db_get_task(task_id) or task
                if current_task.get("status") in {TaskStatus.UNKNOWN.value, TaskStatus.CANCELLED.value}:
                    self._db_update_step(
                        step_id,
                        status="unknown" if current_task.get("status") == TaskStatus.UNKNOWN.value else "cancelled",
                        error=current_task.get("error"),
                        detail="Agent Zero task state changed while the external attempt was in flight.",
                    )
                    return current_task
                if result_data.get("task_outcome") != "COMPLETED":
                    task_outcome = result_data.get("task_outcome")
                    if task_outcome == "OUTCOME_UNKNOWN":
                        status = TaskStatus.UNKNOWN.value
                        step_status = "unknown"
                    elif task_outcome == "CANCELLED":
                        status = TaskStatus.CANCELLED.value
                        step_status = "cancelled"
                    else:
                        status = TaskStatus.FAILED.value
                        step_status = "failed"
                    failure_code = result_data.get("failure_code") or "AGENT_ZERO_EXECUTION_UNAVAILABLE"
                    final_result = {
                        "task_id": task_id,
                        "intent": intent,
                        "agent_id": agent_id,
                        "skill_id": task.get("skill_id"),
                        "output": result_data,
                        "verification": None,
                        "execution_status": task_outcome or "UNAVAILABLE",
                        "failure_code": failure_code,
                        "executed_at": self._now(),
                    }
                    self._db_update_task(
                        task_id, status=status, error=failure_code,
                        result_json=json.dumps(final_result, ensure_ascii=False, default=str),
                        finished_at=self._now(),
                    )
                    self._db_update_step(
                        step_id, status=step_status, error=failure_code,
                        detail="Agent Zero did not produce a verified completed result.",
                    )
                    self._db_add_evidence(
                        task_id, "agent_zero_execution_state", failure_code,
                        source="agent_zero_gui_executor", step_id=step_id, authenticity_score=1.0,
                    )
                    self._db_add_trace(
                        task_id, "task.execute", failure_code, step_status,
                        started_at=trace_start, finished_at=self._now(),
                        metadata={
                            "attempt_id": result_data.get("attempt_id"),
                            "external_submission": result_data.get("external_submission") is True,
                            "task_outcome": task_outcome,
                        },
                    )
                    return self._db_get_task(task_id)

            ai_failure_code = self._owned_ai_failure_code(agent_id, result_data)
            if ai_failure_code:
                result_data["task_outcome"] = "UNAVAILABLE"
                result_data["task_error"] = ai_failure_code
                final_result = {
                    "task_id": task_id, "intent": intent, "agent_id": agent_id,
                    "skill_id": task.get("skill_id"), "output": result_data,
                    "verification": None, "execution_status": "FAILED",
                    "failure_code": ai_failure_code, "executed_at": self._now(),
                }
                self._db_update_task(
                    task_id, status=TaskStatus.FAILED.value, error=ai_failure_code,
                    result_json=json.dumps(final_result, ensure_ascii=False, default=str),
                    finished_at=self._now(),
                )
                self._db_update_step(
                    step_id, status="failed", error=ai_failure_code,
                    detail="Owned AI result unavailable; task was not marked successful.",
                )
                self._db_add_evidence(
                    task_id, "owned_ai_unavailable", ai_failure_code,
                    source="owned_gateway", step_id=step_id, authenticity_score=1.0,
                )
                self._db_add_trace(
                    task_id, "task.execute", ai_failure_code, "error",
                    started_at=trace_start, finished_at=self._now(),
                    metadata={"attempt": attempt, "provider": "owned", "task_outcome": "UNAVAILABLE"},
                )
                return self._db_get_task(task_id)

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
                "task_outcome": verification.outcome_status,
            }

            completed = verification.verified and verification.success
            failed = bool(result_data.get("error"))
            outcome_state = (TaskStatus.SUCCEEDED if completed else
                             TaskStatus.FAILED if failed else TaskStatus.UNKNOWN)

            serialized = json.dumps(final_result, ensure_ascii=False, default=str)
            with get_db() as conn:
                if completed and (task.get("context") or {}).get("analysis_operation") == "openai_math":
                    from lumenis.shared.evaluation.openai_math_papers.product_outcome import verify_product_outcome
                    if not verify_product_outcome(self, task, result_data, connection=conn):
                        raise PermissionError("MATHEMATICAL_OUTCOME_CHANGED_BEFORE_TASK_COMMIT")
                changed = conn.execute(
                    "UPDATE ai_task SET status=?, result_json=?, error=?, finished_at=?, updated_at=? "
                    "WHERE task_id=? AND status=?",
                    (outcome_state.value, serialized,
                     str(result_data.get("error")) if failed else None if completed else "USER_OUTCOME_NOT_VERIFIED",
                     self._now(), self._now(), task_id, TaskStatus.RUNNING.value),
                ).rowcount
            if changed != 1:
                self._db_update_step(step_id, status="cancelled", detail="Task state changed before result commit.")
                return self._db_get_task(task_id)
            committed = self._db_get_task(task_id)
            if not committed or committed.get("result") != final_result:
                raise RuntimeError("TASK_RESULT_COMMITTED_READBACK_MISMATCH")
            self._db_update_step(step_id, status="succeeded" if completed else "failed" if failed else "unknown",
                                 detail=f"Execution returned; outcome={verification.outcome_status}")
            self._db_add_trace(
                task_id, "task.execute",
                f"Execution returned; outcome={verification.outcome_status}",
                "ok" if completed else "error" if failed else "unknown",
                started_at=trace_start, finished_at=self._now(),
                metadata={"attempt": attempt, "verification": verification.verified},
            )
            return self._db_get_task(task_id)

        except Exception as e:
            self._db_update_step(step_id, status="failed", error=str(e))
            self._db_add_trace(task_id, "task.execute", f"Execution failed: {e}", "error",
                               started_at=trace_start, finished_at=self._now())
            raise

    @staticmethod
    def _owned_ai_failure_code(agent_id: str, result_data: Any) -> Optional[str]:
        """Fail AI-dependent tasks when the owned Gateway produced no answer.

        Data queries may still succeed when their database result is real and
        their optional AI summary is unavailable.
        """
        if not isinstance(result_data, dict):
            return None
        if agent_id == "analysis_agent" and result_data.get("ai_required") is True and (
            result_data.get("ai_analysis_status") != "completed"
            or result_data.get("ai_analysis") is None
        ):
            return (result_data.get("ai_analysis_error") or "OWNED_RUNTIME_NOT_BOUND")
        if "ai_response" in result_data and (
            result_data.get("ai_status") != "completed"
            or result_data.get("ai_response") is None
        ):
            return (result_data.get("ai_error") or "OWNED_RUNTIME_NOT_BOUND")
        return None

    def _dispatch_execution(
        self,
        task: Dict[str, Any],
        agent_id: str,
        intent: str,
    ) -> Dict[str, Any]:
        """根据 Agent 类型分发执行。

        所有执行均为只读/分析，不修改生产数据。
        AI 调用通过唯一 SYSTEM AI Gateway；失败时保留显式状态。
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

        # ── 默认：AI 辅助回答（通过 SYSTEM AI Gateway） ──
        return self._execute_ai_assist(task, intent)

    def _execute_data_query(self, task: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """Query only an admitted, version-bound Source Owner sample."""
        context = task.get("context") or {}
        if (context.get("source_brief_job_id") and
                context.get("analysis_operation") in {"source_statistics", "openai_math"}):
            return self._execute_analysis(task, intent)
        return {"status": "unavailable", "error": "SCOPED_SOURCE_OWNER_REQUIRED",
                "query_type": intent, "ai_required": False,
                "business_outcome": "NOT_OBSERVED",
                "next_action": {"method": "POST",
                                "path": "/api/experience/reports/source-brief/start",
                                "context": "current authorized GLOBAL or selected focus",
                                "description": "Generate or select a scoped source result before querying it."}}

    def _execute_analysis(self, task: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """Compute useful statistics over an admitted SourceBrief; AI is opt-in."""
        operation = (task.get("context") or {}).get("analysis_operation")
        if operation == "openai_math":
            from lumenis.shared.evaluation.openai_math_papers.product_outcome import execute_product_task
            try:
                return execute_product_task(self, task)
            except (ValueError, PermissionError, LookupError, RuntimeError, ArithmeticError) as exc:
                code = str(exc)
                return {"analysis_operation": operation, "ai_required": False,
                        "base_analysis_status": "unavailable",
                        "error": code if re.fullmatch(r"[A-Z_0-9]{1,120}", code)
                        else "MATHEMATICAL_COMPUTATION_UNAVAILABLE",
                        "business_outcome": "NOT_OBSERVED"}
        result = {"analysis_type": intent, "method": "source_brief_statistics/v1",
                  "analysis_operation": operation,
                  "ai_required": False, "ai_analysis": None,
                  "ai_analysis_status": "not_requested", "analysis_provider": "unavailable",
                  "business_outcome": "NOT_OBSERVED"}
        try:
            report = self._read_analysis_source(task)
            statistics = self._source_statistics(report["source_brief"])
            result.update(base_analysis=statistics, base_analysis_status="completed",
                          source_brief_job_id=report["job_id"],
                          artifact_outcome=report["artifact_outcome"])
        except (ValueError, PermissionError, LookupError, RuntimeError) as exc:
            code = str(exc)
            result.update(base_analysis_status="unavailable",
                          error=code if re.fullmatch(r"[A-Z_0-9]{1,120}", code) else "ANALYSIS_SOURCE_UNAVAILABLE")
            return result
        if (task.get("context") or {}).get("ai_enhancement") is True:
            # Only reuse the Reporting Owner's already admitted derivative.
            # A statistics request cannot silently grant AI source use or start
            # another inference call under REPORT_GENERATE permission.
            enhancement = report.get("business_analysis") or {}
            admitted = enhancement.get("state") == "draft"
            result.update(ai_analysis=enhancement if admitted else None,
                          ai_analysis_status="admitted_source_brief_derivative" if admitted else "unavailable",
                          ai_analysis_error=None if admitted else "AI_ENHANCEMENT_NOT_ADMITTED_FOR_SOURCE_VERSION")
        return result

    @staticmethod
    def _analysis_actor(task: dict[str, Any]):
        from lumenis.auth.service import get_current_user
        from lumenis.system.security.permission import resolve_local_workspace_principal
        actor = resolve_local_workspace_principal(module="reports", action="read")
        if actor is None:
            actor = get_current_user()
        if actor is None:
            raise PermissionError("ANALYSIS_AUTH_REQUIRED")
        ref = getattr(actor, "principal_ref", None)
        if ref is None and isinstance(actor, dict) and type(actor.get("id")) is int:
            ref = f"actor:{actor['id']}"
        if ref is None or task.get("created_by") != ref:
            raise PermissionError("ANALYSIS_TASK_ACTOR_MISMATCH")
        return actor, ref

    def _read_analysis_source(self, task: dict[str, Any]) -> dict[str, Any]:
        from experience_runtime import _source_brief_context
        from lumenis.shared.reporting.source_brief_job import (
            _scope_material,
            get_source_brief_job,
        )
        context = task.get("context") or {}
        job_id, expected = context.get("source_brief_job_id"), context.get("source_brief_artifact_hash")
        if not isinstance(job_id, str) or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("ANALYSIS_SOURCE_BRIEF_REQUIRED")
        actor, ref = self._analysis_actor(task)
        current_ref, _, material = _source_brief_context("read")
        if current_ref != ref:
            raise PermissionError("ANALYSIS_TASK_ACTOR_MISMATCH")
        report = get_source_brief_job(job_id, actor_id=ref, actor=actor,
                                     expected_scope=_scope_material(**material))
        if report["artifact_outcome"]["artifact_hash"] != expected:
            raise RuntimeError("ANALYSIS_SOURCE_VERSION_CHANGED")
        if not report["source_brief"]["records"]:
            raise ValueError("ANALYSIS_NO_VERIFIED_SOURCE")
        return report

    @staticmethod
    def _source_statistics(brief: dict[str, Any]) -> dict[str, Any]:
        from collections import Counter
        records = brief["records"]
        by_source = {record["source_id"]: record for record in records}
        dates, unknown_dates = Counter(), 0
        for record in by_source.values():
            value = record.get("publish_datetime")
            try:
                day = datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
            except (ValueError, TypeError, AttributeError):
                unknown_dates += 1
            else:
                dates[day] += 1
        n = len(by_source)
        return {"input_count": len(records), "unique_source_count": n,
                "duplicate_projection_count": len(records) - n,
                "platform_counts": dict(sorted(Counter(record.get("source_platform") or "UNKNOWN"
                                                         for record in by_source.values()).items())),
                "source_type_counts": dict(sorted(Counter(record.get("source_type") or "UNKNOWN"
                                                            for record in by_source.values()).items())),
                "publication_day_counts": dict(sorted(dates.items())),
                "publication_time_known_count": n - unknown_dates,
                "publication_time_unknown_count": unknown_dates,
                "publication_time_known_ratio": (n - unknown_dates) / n if n else None,
                "denominator": "unique verified sources in this SourceBrief sample",
                "sample": brief["sample"], "scope": brief["scope"],
                "coverage": "UNKNOWN", "causal_claim": "NOT_ESTABLISHED",
                "interpretation": "Sample counts and native publication dates only; not market demand, sentiment or platform-wide coverage."}

    def _execute_report(self, task: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """Reports use the same admitted Owner path, never a global DB count."""
        return self._execute_data_query(task, intent)

    def _execute_browser(self, task: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """Reject withdrawn desktop execution and unbound internal browser work."""
        from agent_runtime.agent_zero_gui_executor import is_agent_zero_gui_task
        if is_agent_zero_gui_task(task):
            code = "GENERAL_OS_EXECUTION_WITHDRAWN"
            return {"status": "unavailable", "error": code, "failure_code": code,
                    "task_outcome": "UNAVAILABLE", "execution_status": "UNAVAILABLE",
                    "external_submission": False}
        return {
            "status": "unavailable",
            "browser_action": intent,
            "error": "INTERNAL_BROWSER_TASK_BINDING_NOT_BOUND",
            "failure_code": "INTERNAL_BROWSER_TASK_BINDING_NOT_BOUND",
            "external_submission": False,
        }

    def _execute_ai_assist(self, task: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """默认 AI 辅助（记录 Gateway 的 provider 和状态）。"""
        ai_result = self._try_ai_analyze(task.get("user_input", ""))
        if ai_result and ai_result.get("status") == "completed":
            return {
                "ai_response": ai_result,
                "provider": ai_result.get("provider", "unknown"),
                "ai_status": ai_result["status"],
            }
        result = {
            "ai_response": None,
            "provider": (ai_result or {}).get("provider", "unknown"),
            "ai_status": (ai_result or {}).get("status", "unavailable"),
            "degradation": "AI Gateway did not return a completed model response.",
            "note": "Task continued without an AI response.",
        }
        if (ai_result or {}).get("error"):
            result["ai_error"] = ai_result["error"]
        return result

    # ──────────────────────────────────────────────────────────
    # Canonical AI Gateway bridge
    # ──────────────────────────────────────────────────────────

    def _try_ai_summarize(self, text: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """尝试 AI 总结，并返回含 provider/status 的结构化结果。"""
        return self._call_ai_with_fallback("summarize", text, data)

    def _try_ai_analyze(self, text: str) -> Dict[str, Any]:
        """尝试 AI 分析，并返回含 provider/status 的结构化结果。"""
        return self._call_ai_with_fallback("analyze", text, {})

    def _call_ai_with_fallback(
        self,
        operation: str,
        text: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Call the owned SYSTEM Gateway only; never select a legacy provider."""
        result_holder: Dict[str, Any] = {}

        def _ai_worker() -> None:
            try:
                from lumenis.system.ai_gateway import core as ai_gateway
                user_parts = [f"Operation: {operation}", f"Input:\n{text or ''}"]
                if data:
                    user_parts.append(
                        "Context JSON:\n" + json.dumps(data, ensure_ascii=False, default=str)
                    )
                gateway_result = ai_gateway.run_owned_analysis(
                    text=(
                        "You are the LUMENIS task assistant. Complete the requested operation "
                        "using only the supplied input and context. State uncertainty clearly.\n\n"
                        + "\n\n".join(user_parts)
                    ),
                    analysis_type=f"task_engine_{operation}",
                )
                if not isinstance(gateway_result, dict):
                    gateway_result = {
                        "ok": False, "status": "ERROR",
                        "code": "OWNED_GATEWAY_RESULT_INVALID", "provider": "owned",
                    }
                gateway_status = str(gateway_result.get("status") or "ERROR").upper()
                analysis = gateway_result.get("analysis")
                response = analysis.strip() if isinstance(analysis, str) else ""
                if isinstance(analysis, dict):
                    for key in ("response", "text", "answer", "summary", "reply"):
                        value = analysis.get(key)
                        if isinstance(value, str) and value.strip():
                            response = value.strip()
                            break
                completed = (
                    gateway_result.get("ok") is True and gateway_status == "COMPLETED"
                    and gateway_result.get("provider") == "owned" and bool(response)
                )
                status = "completed" if completed else (
                    gateway_status.lower() if gateway_status != "COMPLETED" else "error"
                )
                result_holder["result"] = {
                    "status": status,
                    "provider": "owned",
                    "response": response if completed else None,
                    "model": gateway_result.get("model"),
                    **({} if completed else {
                        "error": gateway_result.get("code") or "OWNED_ANALYSIS_NOT_COMPLETED",
                    }),
                }
            except Exception as exc:
                # Store only the exception type: provider exceptions can include
                # URLs or credential material and must not enter task evidence.
                result_holder["result"] = {
                    "status": "error",
                    "provider": "unknown",
                    "response": None,
                    "model": None,
                    "error": type(exc).__name__,
                }

        worker = threading.Thread(target=_ai_worker, daemon=True)
        worker.start()
        worker.join(timeout=_AI_CALL_TIMEOUT_SECONDS)
        if worker.is_alive():
            logger.warning("[TaskEngine] canonical AI Gateway call timed out")
            return {
                "status": "timeout",
                "provider": "unknown",
                "response": None,
                "model": None,
                "error": "Gateway timeout",
            }
        return result_holder.get("result", {
            "status": "error",
            "provider": "unknown",
            "response": None,
            "model": None,
            "error": "Gateway returned no result",
        })

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
            source="user", step_id=step_id, authenticity_score=None,
        )
        evidence_ids.append(ev_input)

        # 证据2：解析结果
        ev_parse = self._db_add_evidence(
            task["task_id"], "parsed",
            f"Intent={intent}, risk={task.get('risk_level')}, agent={agent_id}",
            source="task_parser", step_id=step_id, authenticity_score=None,
        )
        evidence_ids.append(ev_parse)

        # 证据3：执行结果
        result_summary = json.dumps(result_data, ensure_ascii=False, default=str)[:1000]
        ev_result = self._db_add_evidence(
            task["task_id"], "execution_result",
            result_summary, source=agent_id, step_id=execute_step_id,
            authenticity_score=None,
        )
        evidence_ids.append(ev_result)

        # Execution returning is not verification of a useful committed outcome.
        success, verification_scope = self._verify_owner_outcome(task, result_data)

        # 判定是否需人工确认
        needs_human = task.get("risk_level") in ("L3", "L4") or task.get("human_approval_required")

        what_was_called = f"agent={agent_id}"
        if skill_id:
            what_was_called += f", skill={skill_id}"
        if result_data.get("analysis_provider"):
            what_was_called += f", ai_provider={result_data['analysis_provider']}"

        verification = VerificationResult(
            verified=bool(success),
            what_was_done=f"Executed {intent} via {agent_id}",
            why=f"Task intent={intent}, risk={task.get('risk_level')}, permission={task.get('permission_result')}",
            what_was_called=what_was_called,
            result_summary=result_summary[:200],
            evidence_ids=evidence_ids,
            success=bool(success),
            needs_human_confirmation=bool(needs_human),
            human_confirmation_reason=task.get("risk_reason", "") if needs_human else "",
            verification_method="independent_owner_readback" if success else "execution_return_only",
            verification_scope=verification_scope,
            outcome_status="VERIFIED" if success else "FAILED" if result_data.get("error") else "NOT_VERIFIED",
        )

        self._db_update_step(step_id, status="succeeded" if success else "failed" if result_data.get("error") else "unknown",
                             detail=f"Verified: success={success}, evidence_count={len(evidence_ids)}")
        self._db_add_trace(
            task["task_id"], "task.verify",
            f"Verification complete: success={success}, evidence={len(evidence_ids)}",
            "ok" if success else "unknown", metadata={"success": success, "evidence_count": len(evidence_ids)},
        )
        return verification

    def _verify_owner_outcome(self, task: dict[str, Any], result: dict[str, Any]):
        """Consume current canonical Owner readers, never a caller's verified flag."""
        if isinstance(result, dict) and result.get("executor") == "agent_zero_gui":
            from agent_runtime.agent_zero_gui_executor import is_agent_zero_gui_task
            if is_agent_zero_gui_task(task):
                return False, "GENERAL_OS_EXECUTION_WITHDRAWN"
        if not isinstance(result, dict) or result.get("error"):
            return False, "EXECUTION_RETURN"
        if (task.get("agent_id") == "analysis_agent" or
                (task.get("context") or {}).get("analysis_operation") in {"source_statistics", "openai_math"}):
            try:
                if (task.get("context") or {}).get("analysis_operation") == "openai_math":
                    from lumenis.shared.evaluation.openai_math_papers.product_outcome import verify_product_outcome
                    return verify_product_outcome(self, task, result), "VERSIONED_MATHEMATICAL_SCENARIO"
                report = self._read_analysis_source(task)
                valid = ((task.get("context") or {}).get("analysis_operation") == "source_statistics"
                         and result.get("analysis_operation") == "source_statistics"
                         and result.get("base_analysis_status") == "completed"
                         and result.get("source_brief_job_id") == report["job_id"]
                         and result.get("artifact_outcome") == report["artifact_outcome"]
                         and result.get("base_analysis") == self._source_statistics(report["source_brief"]))
                return valid, "SOURCE_BRIEF_SAMPLE_ANALYSIS"
            except (ValueError, PermissionError, LookupError, RuntimeError):
                return False, "SOURCE_BRIEF_SAMPLE_ANALYSIS"
        return False, "EXECUTION_RETURN"

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
        _guard_generic_task_access(task_id)
        task = self._db_get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if task.get("status") != TaskStatus.AWAITING_APPROVAL.value:
            return {"error": f"Task not in awaiting_approval state: {task.get('status')}"}

        if self.permission_gate is None:
            raise PermissionError("TASK_APPROVAL_ISSUER_UNAVAILABLE")
        try:
            approval_token = self.permission_gate.grant_approval(
                operation="ai_task_execution", duration_minutes=30,
                resource=f"ai_task:{task_id}", granted_by=approved_by)
        except Exception as exc:
            raise PermissionError("TASK_APPROVAL_ISSUANCE_FAILED") from exc
        if not isinstance(approval_token, str) or not approval_token.strip():
            raise PermissionError("TASK_APPROVAL_ISSUANCE_FAILED")

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

    def _cancel_agent_zero_task(self, task_id: str, reason: str) -> Dict[str, Any]:
        from agent_runtime.agent_zero_gui_executor import AGENT_ZERO_TASK_RECORD

        with self._agent_zero_task_lock(task_id):
            task = self._db_get_task(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            record = (task.get("parameters") or {}).get(AGENT_ZERO_TASK_RECORD)
            if task.get("status") in {
                    TaskStatus.SUCCEEDED.value, TaskStatus.CANCELLED.value,
                    TaskStatus.FAILED.value, TaskStatus.DLQ.value, TaskStatus.UNKNOWN.value,
            }:
                return task
            self._cancelled.add(task_id)
            if isinstance(record, dict):
                # A historical attempt record may have crossed the boundary.
                # Preserve it and the uncertainty; never contact a withdrawn worker.
                error = "GENERAL_OS_EXECUTION_WITHDRAWN"
                self._db_update_task(
                    task_id, status=TaskStatus.UNKNOWN.value, error=error,
                    finished_at=self._now(),
                )
                self._db_add_step(
                    task_id, StepPhase.ERROR.value, "unknown",
                    detail="External attempt outcome is unknown; worker was not contacted.", error=error,
                )
                self._db_add_trace(task_id, "task.cancel", error, "unknown",
                                   metadata={"external_contact": "NOT_ATTEMPTED"})
                return self._db_get_task(task_id)
            self._db_update_task(
                task_id, status=TaskStatus.CANCELLED.value,
                error=reason, finished_at=self._now(),
            )
            self._db_add_step(task_id, StepPhase.ERROR.value, "cancelled", detail=reason)
            self._db_add_trace(task_id, "task.cancel", reason, "cancelled")
            return self._db_get_task(task_id)

    def cancel_task(self, task_id: str, reason: str = "user_cancelled") -> Dict[str, Any]:
        """取消任务。"""
        _guard_generic_task_access(task_id)
        from agent_runtime.agent_zero_gui_executor import is_agent_zero_gui_task
        task = self._db_get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        if is_agent_zero_gui_task(task):
            return self._cancel_agent_zero_task(task_id, reason)

        terminal = {TaskStatus.SUCCEEDED.value, TaskStatus.CANCELLED.value,
                    TaskStatus.UNKNOWN.value, TaskStatus.FAILED.value, TaskStatus.DLQ.value}
        if task.get("status") in terminal:
            return task
        with get_db() as conn:
            changed = conn.execute(
                "UPDATE ai_task SET status=?, error=?, finished_at=?, updated_at=? "
                "WHERE task_id=? AND status=?",
                (TaskStatus.CANCELLED.value, reason, self._now(), self._now(), task_id, task["status"]),
            ).rowcount
        if changed != 1:
            return self._db_get_task(task_id)
        self._cancelled.add(task_id)
        self._db_add_step(task_id, StepPhase.ERROR.value, "cancelled", detail=reason)
        self._db_add_trace(task_id, "task.cancel", reason, "cancelled")
        return self._db_get_task(task_id)

    # ──────────────────────────────────────────────────────────
    # 9. 完整运行（parse → select → permission → execute）
    # ──────────────────────────────────────────────────────────

    def run_task(self, task_id: str) -> Dict[str, Any]:
        """完整运行任务：解析 → Agent/Skill选择 → 权限 → 执行。"""
        _guard_generic_task_access(task_id)
        from agent_runtime.agent_zero_gui_executor import (
            AGENT_ZERO_TASK_RECORD,
            is_agent_zero_gui_task,
        )
        current = self._db_get_task(task_id)
        if (current and current.get("status") == TaskStatus.UNKNOWN.value
                and current.get("finished_at") and current.get("result")):
            # Execution already returned, but its user outcome is unresolved.
            # Reading/running it again must not repeat possible external effects.
            return current
        if current and current.get("status") in {TaskStatus.SUCCEEDED.value, TaskStatus.CANCELLED.value, TaskStatus.RUNNING.value}:
            if current.get("agent_id") == "analysis_agent" and current.get("status") == TaskStatus.SUCCEEDED.value:
                stored = current.get("result") or {}
                valid, _ = self._verify_owner_outcome(current, stored.get("output") or {})
                if not valid:
                    return {**current, "status": TaskStatus.UNKNOWN.value,
                            "error": "ANALYSIS_OWNER_READBACK_NOT_VERIFIED"}
            return current
        if current and is_agent_zero_gui_task(current):
            record = (current.get("parameters") or {}).get(AGENT_ZERO_TASK_RECORD)
            if (isinstance(record, dict) or current.get("status") in {
                    TaskStatus.SUCCEEDED.value, TaskStatus.CANCELLED.value, TaskStatus.UNKNOWN.value,
            }):
                # A new API call may inspect this task, but never resubmits its
                # external GUI effect. Ambiguous attempts stay UNKNOWN.
                return current
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
        _guard_generic_task_access(task_id)
        return self._db_get_task(task_id)

    def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = (
            "SELECT * FROM ai_task WHERE substr(task_id, 1, 7) <> ? "
            "AND substr(task_id, 1, ?) <> ? "
            "AND task_id NOT LIKE 'task-pitch-%'"
        )
        params: List[Any] = [
            _MANAGED_REPORT_TASK_PREFIX, len(_TRAINING_RECEIPT_TASK_PREFIX),
            _TRAINING_RECEIPT_TASK_PREFIX,
        ]
        if status:
            query += " AND status=?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with get_db() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_steps(self, task_id: str) -> List[Dict[str, Any]]:
        _guard_generic_task_access(task_id)
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM ai_task_step WHERE task_id=? ORDER BY started_at",
                (task_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_evidence(self, task_id: str) -> List[Dict[str, Any]]:
        _guard_generic_task_access(task_id)
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
        _guard_generic_task_access(task_id)
        if task_id:
            with get_db() as conn:
                rows = conn.execute(
                    """SELECT * FROM ai_task_trace
                       WHERE task_id=? AND substr(task_id, 1, 7) <> ?
                         AND substr(task_id, 1, ?) <> ?
                       ORDER BY started_at""",
                    (task_id, _MANAGED_REPORT_TASK_PREFIX,
                     len(_TRAINING_RECEIPT_TASK_PREFIX), _TRAINING_RECEIPT_TASK_PREFIX),
                ).fetchall()
        else:
            with get_db() as conn:
                rows = conn.execute(
                    """SELECT * FROM ai_task_trace
                       WHERE substr(task_id, 1, 7) <> ?
                         AND substr(task_id, 1, ?) <> ?
                       ORDER BY started_at DESC LIMIT ?""",
                    (_MANAGED_REPORT_TASK_PREFIX, len(_TRAINING_RECEIPT_TASK_PREFIX),
                     _TRAINING_RECEIPT_TASK_PREFIX, limit),
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
                "osai_down_impact": (
                    "AI-dependent tasks are unavailable until the LUMENIS-owned "
                    "Gateway runtime is bound; non-AI Core workflows continue"
                ),
                "ai_provider_chain": ["owned_gateway"],
                "ai_runtime_status": "OWNED_RUNTIME_NOT_BOUND",
                "fallback_allowed": False,
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
            "osai_boundary": (
                "LUMENIS-owned AI uses the SYSTEM Gateway; AI tasks remain unavailable "
                "until the owned runtime is bound; non-AI Core workflows continue"
            ),
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
