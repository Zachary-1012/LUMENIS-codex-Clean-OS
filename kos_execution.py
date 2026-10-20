# -*- coding: utf-8 -*-
"""HUMAN_CONTROL_GATE_v1 执行状态机（全局规则，KOS 强制）。

状态机：AI_GENERATED -> PENDING_HUMAN_REVIEW -> HUMAN_APPROVED -> EXECUTING -> SUCCESS / FAILED
禁止 AI 从"生成/推荐"直接跳到"已执行"。
所有 gated 执行必须留审计（actor / approval timestamp / payload / result / evidence）。

表：kos_executions（migration_8_to_9 创建；本模块幂等自建兜底）。
"""
from __future__ import annotations
import json, os, sqlite3, uuid
from datetime import datetime
from pathlib import Path

from lumenis.shared.database import get_repository, main_db_path

DB_PATH = main_db_path()

# 敏感动作类型（HCG 强制人工确认）
GATED_ACTIONS = {
    "reply_send",          # 评论回复（含承诺/商务/敏感表述）
    "outreach_send",       # 博主触达/私信
    "email_send",          # 邮件邀约
    "lead_export",         # 留资数据导出/处理
    "cooperation_confirm", # 商务合作确认
    "contract_confirm",    # 合同/报价/预算/权益确认
    "paid_media",          # 投流创建/投放/充值/预算变更
    "publish",             # 内容发布
    "reward_issue",        # 奖励发放
}

# 合法状态机转移（HCG 锁定，无捷径）
ALLOWED_TRANSITIONS = {
    "AI_GENERATED": {"PENDING_HUMAN_REVIEW"},
    "PENDING_HUMAN_REVIEW": {"HUMAN_APPROVED", "REJECTED"},
    "HUMAN_APPROVED": {"EXECUTING"},
    "EXECUTING": {"SUCCESS", "FAILED"},
}
TERMINAL = {"SUCCESS", "FAILED", "REJECTED"}
START = "AI_GENERATED"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _conn() -> sqlite3.Connection:
    conn = get_repository().connect(timeout=10)
    # 幂等自建（表缺失时兜底，migration 会正式创建）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kos_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT UNIQUE,
            action_type TEXT NOT NULL,
            target_author_id TEXT DEFAULT '',
            target_brand TEXT DEFAULT '',
            payload TEXT DEFAULT '{}',
            status TEXT DEFAULT 'AI_GENERATED',
            actor TEXT DEFAULT '',
            created_at TEXT,
            approved_at TEXT,
            executed_at TEXT,
            result TEXT DEFAULT '',
            evidence_ref TEXT DEFAULT '',
            failure_reason TEXT DEFAULT '',
            version TEXT DEFAULT 'v1'
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kos_exec_status ON kos_executions(status)")
    return conn


def create_execution(action_type: str, target_author_id: str = "", target_brand: str = "",
                     payload: dict | None = None, actor: str = "AI", version: str = "v1") -> dict:
    """创建 gated action，初始状态 AI_GENERATED（不执行）。返回 execution 记录。"""
    if action_type not in GATED_ACTIONS:
        raise ValueError(f"action_type 不在 HCG 门控动作内: {action_type}")
    eid = "KX-" + datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
    conn = _conn()
    try:
        conn.execute(
            """INSERT INTO kos_executions
               (execution_id, action_type, target_author_id, target_brand, payload, status, actor,
                created_at, approved_at, executed_at, result, evidence_ref, failure_reason, version)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (eid, action_type, target_author_id, target_brand,
             json.dumps(payload or {}, ensure_ascii=False), START, actor,
             _now(), None, None, "", "", "", version),
        )
        conn.commit()
        return get_execution(eid)
    finally:
        conn.close()


def transition(execution_id: str, to_status: str, actor: str = "", payload: dict | None = None,
               result: str = "", evidence_ref: str = "", failure_reason: str = "") -> dict:
    """状态机转移（校验合法路径）。actor 必填（HUMAN_APPROVED/EXECUTING/SUCCESS 必须记录人工操作者）。"""
    _all_targets = set()
    for _v in ALLOWED_TRANSITIONS.values():
        _all_targets.update(_v)
    if to_status not in _all_targets:
        raise ValueError(f"非法目标状态: {to_status}")
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM kos_executions WHERE execution_id = ?", (execution_id,)).fetchone()
        if not row:
            raise KeyError(f"execution 不存在: {execution_id}")
        cur = dict(row)
        allowed = ALLOWED_TRANSITIONS.get(cur["status"], set())
        if to_status not in allowed:
            raise ValueError(f"非法状态转移: {cur['status']} -> {to_status}")
        # 人工确认动作必须记录 actor
        if to_status in ("HUMAN_APPROVED", "EXECUTING") and not actor:
            raise ValueError("人工确认/执行必须提供 actor（操作者）")
        updates = {"status": to_status}
        if to_status == "PENDING_HUMAN_REVIEW":
            pass
        if to_status == "HUMAN_APPROVED":
            updates["approved_at"] = _now()
        if to_status == "EXECUTING":
            updates["executed_at"] = _now()
        if to_status in ("SUCCESS", "FAILED"):
            updates["executed_at"] = updates.get("executed_at") or _now()
        if to_status in ("SUCCESS", "FAILED") and result:
            updates["result"] = result
        if evidence_ref:
            updates["evidence_ref"] = evidence_ref
        if failure_reason:
            updates["failure_reason"] = failure_reason
        if payload is not None:
            updates["payload"] = json.dumps(payload, ensure_ascii=False)
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(f"UPDATE kos_executions SET {set_clause} WHERE execution_id = ?",
                     list(updates.values()) + [execution_id])
        conn.commit()
        return get_execution(execution_id)
    finally:
        conn.close()


def get_execution(execution_id: str) -> dict | None:
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM kos_executions WHERE execution_id = ?", (execution_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_executions(status: str = "", action_type: str = "", target_author_id: str = "",
                    limit: int = 50) -> list:
    conn = _conn()
    try:
        conds, params = [], []
        if status:
            conds.append("status = ?"); params.append(status)
        if action_type:
            conds.append("action_type = ?"); params.append(action_type)
        if target_author_id:
            conds.append("target_author_id = ?"); params.append(target_author_id)
        where = (" WHERE " + " AND ".join(conds)) if conds else ""
        rows = conn.execute(
            f"SELECT * FROM kos_executions{where} ORDER BY id DESC LIMIT ?", params + [int(limit)]).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# Deployment code may register an existing channel adapter. HTTP input cannot
# select/import a callable or manufacture a provider receipt.
_SCOPED_EXECUTION_ADAPTERS = {}


def _scoped_context(actor, scope, action="read", connection=None):
    from kos_ops import _scoped_operation_identity
    return _scoped_operation_identity(actor, scope, action, connection)


def _scoped_write_check(actor, scope, resource, request_id):
    from lumenis.shared.reporting.saved_work import _check_effect
    from lumenis.system.security.permission import OperationType
    from kos_ops import ScopedOperationApprovalRequired
    from lumenis.system.security.permission import get_permission_gate
    if get_permission_gate().get_valid_approval_token("db_write", resource, exact=True) is None:
        raise ScopedOperationApprovalRequired(resource, request_id)
    try:
        _check_effect(actor, scope, OperationType.DB_WRITE, resource)
    except ValueError as exc:
        if str(exc) != "WORK_EFFECT_PERMISSION_DENIED":
            raise
        raise ScopedOperationApprovalRequired(resource, request_id) from exc


def _scoped_record(row, context):
    if row is None:
        raise LookupError("KOS_EXECUTION_NOT_FOUND")
    record = dict(row)
    try:
        payload = json.loads(record["payload"])
    except (TypeError, ValueError) as exc:
        raise ValueError("KOS_EXECUTION_BINDING_INVALID") from exc
    if not isinstance(payload, dict) or payload.get("schema") != "lumenis.kos-scoped-execution/v1" or payload.get("context") != context:
        raise PermissionError("KOS_EXECUTION_SCOPE_OR_ACTOR_MISMATCH")
    from lumenis.shared.reporting.saved_work import _digest
    if payload.get("request_sha256") != _digest(payload.get("request")):
        raise ValueError("KOS_EXECUTION_REQUEST_CHANGED")
    return record, payload


def list_scoped_executions(*, actor, scope, status="", action_type="", target_author_id="", limit=50):
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("KOS_EXECUTION_LIMIT_INVALID")
    context = _scoped_context(actor, scope)
    caller = context.get("principal_ref") or "actor:" + str(context["actor_id"])
    with get_repository().connection(read_only=True, wal=False) as con:
        if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='kos_executions'").fetchone() is None:
            return []
        records = []
        cursor = con.execute(
            "SELECT * FROM kos_executions WHERE version = ? AND actor = ? AND target_brand = ? ORDER BY id DESC",
            ("scoped-v1", caller, context["brand_focus_id"]),
        )
        for row in cursor:
            try:
                record, _payload = _scoped_record(row, context)
            except PermissionError as exc:
                # The indexed owner fields placed this row inside the requested
                # actor/scope, so contradictory signed context is corruption,
                # not another actor's row to silently skip.
                raise ValueError("KOS_EXECUTION_BINDING_INVALID") from exc
            if ((status and record["status"] != status)
                    or (action_type and record["action_type"] != action_type)
                    or (target_author_id and record["target_author_id"] != target_author_id)):
                continue
            records.append(record)
            if len(records) == limit:
                break
        _scoped_context(actor, scope, connection=con)
    return records


def _check_scoped_source_binding(*, actor, scope, request, connection, expected_version=None):
    """Revalidate an operation-backed request under the execution write lock.

    The v1 request's source digest already commits to its version. An explicit
    route-read version adds a consistency check without changing existing v1
    request/approval identities. This never updates or approves the source.
    """
    import kos_ops
    from lumenis.shared.reporting.saved_work import _json
    payload = request["payload"]
    binding_fields = {"private_plan", "source_record_id", "source_sha256"}
    if not binding_fields.intersection(payload):
        if expected_version is not None:
            raise ValueError("KOS_PLAN_BINDING_INVALID")
        return
    if set(payload) != binding_fields or (expected_version is not None and
            (type(expected_version) is not int or expected_version <= 0)):
        raise ValueError("KOS_PLAN_BINDING_INVALID")
    source = kos_ops.resolve_scoped_operation_record(actor=actor, scope=scope,
        record_id=payload["source_record_id"], author_id=request["target_author_id"],
        connection=connection)
    if source["sha256"] != payload["source_sha256"]:
        raise ValueError("KOS_PLAN_SOURCE_HASH_MISMATCH")
    if expected_version is not None and source["version"] != expected_version:
        raise ValueError("KOS_PLAN_SOURCE_VERSION_MISMATCH")
    mapping = {"paid_plan": "paid_media", "reward_plan": "reward_issue",
               "cooperation": "cooperation_confirm"}
    if mapping.get(source["operation"]) != request["action_type"]:
        raise ValueError("KOS_PLAN_ACTION_MISMATCH")
    if _json(source["payload"]) != _json(payload["private_plan"]):
        raise ValueError("KOS_EXECUTION_PAYLOAD_CONFLICT")


def create_scoped_execution(*, actor, scope, action_type, target_author_id, payload, request_id,
                            expected_source_version=None):
    import re
    import hashlib
    from lumenis.shared.reporting.saved_work import _digest, _json, _safe_payload
    if (action_type not in GATED_ACTIONS or not isinstance(target_author_id, str) or not target_author_id.strip()
            or not isinstance(payload, dict) or not isinstance(request_id, str)
            or re.fullmatch(r"[A-Za-z0-9_-]{8,128}", request_id) is None):
        raise ValueError("KOS_EXECUTION_INPUT_INVALID")
    _safe_payload(payload)
    context = _scoped_context(actor, scope, "write")
    request = {"action_type": action_type, "target_author_id": target_author_id, "payload": json.loads(_json(payload))}
    request_hash = _digest(request)
    resource = "kos-execution-create:v1:" + _digest({"context": context, "request_id": request_id, "request": request})
    _scoped_write_check(actor, scope, resource, request_id)
    execution_id = "KX-S-" + hashlib.sha256(_json({"context": context, "request_id": request_id})).hexdigest()[:32]
    stored = {"schema": "lumenis.kos-scoped-execution/v1", "context": context, "request": request,
              "request_id": request_id, "request_sha256": request_hash, "events": [], "provider_receipt": None}
    caller = context.get("principal_ref") or "actor:" + str(context["actor_id"])
    conn = _conn()
    try:
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        _check_scoped_source_binding(actor=actor, scope=scope, request=request,
            connection=conn, expected_version=expected_source_version)
        old = conn.execute("SELECT * FROM kos_executions WHERE execution_id=?", (execution_id,)).fetchone()
        if old:
            record, existing = _scoped_record(old, context)
            if existing["request_sha256"] != request_hash:
                raise ValueError("KOS_EXECUTION_REQUEST_CONFLICT")
            _scoped_context(actor, scope, "read", connection=conn)
            conn.rollback()
            return {"ok": True, "execution": record, "replayed": True, "external_effect": "not_performed"}
        conn.execute("""INSERT INTO kos_executions(execution_id, action_type, target_author_id, target_brand,
            payload, status, actor, created_at, version) VALUES(?,?,?,?,?,?,?,?,?)""",
            (execution_id, action_type, target_author_id, scope["brand_focus_id"], _json(stored).decode(),
             START, caller, _now(), "scoped-v1"))
        _scoped_context(actor, scope, "write", connection=conn)
        _scoped_write_check(actor, scope, resource, request_id)
        conn.commit()
        row = conn.execute("SELECT * FROM kos_executions WHERE execution_id=?", (execution_id,)).fetchone()
        return {"ok": True, "execution": dict(row), "replayed": False, "external_effect": "not_performed"}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def transition_scoped_execution(execution_id, to_status, *, actor, scope):
    """Only real approved local review transitions; external outcomes are adapter-owned."""
    from lumenis.shared.reporting.saved_work import _digest, _json
    if to_status not in {"PENDING_HUMAN_REVIEW", "HUMAN_APPROVED", "REJECTED"}:
        raise ValueError("KOS_EXTERNAL_OUTCOME_REQUIRES_PROVIDER_RECEIPT")
    context = _scoped_context(actor, scope, "write")
    conn = _conn()
    try:
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        record, payload = _scoped_record(conn.execute("SELECT * FROM kos_executions WHERE execution_id=?", (execution_id,)).fetchone(), context)
        if to_status not in ALLOWED_TRANSITIONS.get(record["status"], set()):
            raise ValueError("KOS_EXECUTION_TRANSITION_INVALID")
        resource = "kos-execution-transition:v1:" + _digest({"context": context, "id": execution_id,
            "from": record["status"], "to": to_status, "request_sha256": payload["request_sha256"]})
        _scoped_write_check(actor, scope, resource, payload["request_id"])
        payload["events"].append({"from": record["status"], "to": to_status, "at": _now(), "resource": resource})
        conn.execute("UPDATE kos_executions SET status=?, payload=?, approved_at=? WHERE execution_id=? AND status=?",
            (to_status, _json(payload).decode(), _now() if to_status == "HUMAN_APPROVED" else record["approved_at"], execution_id, record["status"]))
        _scoped_context(actor, scope, "write", connection=conn)
        _scoped_write_check(actor, scope, resource, payload["request_id"])
        conn.commit()
        return {"ok": True, "execution": dict(conn.execute("SELECT * FROM kos_executions WHERE execution_id=?", (execution_id,)).fetchone()), "external_effect": "not_performed"}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_scoped_execution(execution_id, *, actor, scope):
    """Use only a server-registered authorized channel and independently checked receipt.

    No registered adapter means no network call and no EXECUTING/SUCCESS claim.
    An in-progress retry queries the adapter by stable execution ID; it never
    blindly repeats an external effect after an interrupted persistence step.
    """
    from lumenis.shared.reporting.saved_work import _json, _digest
    context = _scoped_context(actor, scope, "write")
    with get_repository().connection(read_only=True, wal=False) as con:
        record, payload = _scoped_record(con.execute("SELECT * FROM kos_executions WHERE execution_id=?", (execution_id,)).fetchone(), context)
    if record["status"] not in {"HUMAN_APPROVED", "EXECUTING", "SUCCESS"}:
        raise PermissionError("KOS_HUMAN_APPROVAL_REQUIRED")
    adapter = _SCOPED_EXECUTION_ADAPTERS.get(record["action_type"])
    if adapter is None:
        return {"ok": False, "code": "KOS_CHANNEL_NOT_CONFIGURED", "execution": record, "external_effect": "not_performed"}
    if not all(callable(getattr(adapter, name, None)) for name in ("authorize", "execute", "lookup_receipt", "verify_receipt")):
        raise ValueError("KOS_CHANNEL_ADAPTER_INVALID")
    # The channel's existing permission owner must authorize the exact recipient,
    # payload and effect before it can run. A client boolean is never consulted.
    if adapter.authorize(actor=actor, scope=scope, execution_id=execution_id, request=payload["request"]) is not True:
        raise PermissionError("KOS_CHANNEL_EFFECT_DENIED")
    dispatch_resource = "kos-execution-dispatch:v1:" + _digest({"context": context, "id": execution_id,
        "request_sha256": payload["request_sha256"]})
    _scoped_write_check(actor, scope, dispatch_resource, payload["request_id"])
    if record["status"] == "SUCCESS":
        if adapter.verify_receipt(payload["provider_receipt"], execution_id=execution_id, request=payload["request"]) is not True:
            raise ValueError("KOS_PROVIDER_RECEIPT_INVALID")
        return {"ok": True, "execution": record, "replayed": True}
    if record["status"] == "HUMAN_APPROVED":
        with get_repository().transaction() as con:
            _scoped_context(actor, scope, "write", connection=con)
            changed = con.execute("UPDATE kos_executions SET status='EXECUTING',executed_at=? WHERE execution_id=? AND status='HUMAN_APPROVED'", (_now(), execution_id)).rowcount
        try:
            _scoped_context(actor, scope, "write")
            adapter_allowed = adapter.authorize(actor=actor, scope=scope, execution_id=execution_id, request=payload["request"])
            if adapter_allowed is not True:
                raise PermissionError("KOS_CHANNEL_EFFECT_DENIED")
            # Recheck after channel admission and immediately before the effect.
            _scoped_write_check(actor, scope, dispatch_resource, payload["request_id"])
        except Exception:
            if changed == 1:
                # This invocation owns the CAS and has NOT entered execute.
                # Compensate only this known-no-effect reservation; never retry
                # an attempted effect whose outcome could be unknown.
                with get_repository().transaction() as con:
                    con.execute("UPDATE kos_executions SET status='HUMAN_APPROVED',executed_at=NULL WHERE execution_id=? AND status='EXECUTING' AND payload=?",
                                (execution_id, _json(payload).decode()))
            raise
        receipt = (adapter.execute(execution_id=execution_id, request=payload["request"]) if changed == 1
                   else adapter.lookup_receipt(execution_id=execution_id))
    else:
        receipt = adapter.lookup_receipt(execution_id=execution_id)
    if receipt is None:
        return {"ok": False, "code": "KOS_RECEIPT_PENDING", "execution_id": execution_id}
    if adapter.verify_receipt(receipt, execution_id=execution_id, request=payload["request"]) is not True:
        raise ValueError("KOS_PROVIDER_RECEIPT_INVALID")
    if not isinstance(receipt, dict) or receipt.get("status") not in {"SUCCESS", "FAILED"} or not receipt.get("reference"):
        raise ValueError("KOS_PROVIDER_RECEIPT_INVALID")
    payload["provider_receipt"] = receipt
    with get_repository().transaction() as con:
        _scoped_context(actor, scope, "write", connection=con)
        con.execute("UPDATE kos_executions SET status=?,payload=?,result=?,evidence_ref=? WHERE execution_id=? AND status='EXECUTING'",
            (receipt["status"], _json(payload).decode(), "verified provider receipt", receipt["reference"], execution_id))
    return {"ok": receipt["status"] == "SUCCESS", "execution_id": execution_id, "receipt": receipt}
