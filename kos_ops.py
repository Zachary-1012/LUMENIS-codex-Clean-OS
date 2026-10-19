"""KOS 运营模块（KOS MASTER EXECUTION CONTRACT v1 · 二十四节运营闭环）

留资管理 / 合作状态 / 邮件邀约（HCG 门控）/ 运营动作闭环

红线：
- 留资录入、合作草稿：本地运营编辑，不触发 HCG
- 留资导出 lead_export / 合作确认 cooperation_confirm / 邮件发送 email_send：必须走 HCG 状态机
- 状态机 AI_GENERATED -> PENDING_HUMAN_REVIEW -> HUMAN_APPROVED -> EXECUTING -> SUCCESS/FAILED
"""
from __future__ import annotations
import json, os, smtplib, sqlite3
from datetime import datetime
from pathlib import Path
from email.message import EmailMessage

import kos_execution as kx
import kos_engine as ke

from lumenis.shared.database import get_repository, main_db_path

DB_PATH = main_db_path()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _conn() -> sqlite3.Connection:
    # Shared Database resolves ZBC_DB_PATH at call time.
    conn = get_repository().connect(timeout=10)
    # 运营动作台账（KOS 运营闭环）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kos_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id TEXT NOT NULL,
            action TEXT NOT NULL,
            note TEXT DEFAULT '',
            actor TEXT DEFAULT 'AI',
            created_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kos_ops_author ON kos_operations(author_id)")
    return conn


def _smtp_settings() -> dict:
    """SMTP 配置：环境变量优先，叠加 data/email_smtp.json（与 app.py 一致）。"""
    st = {
        "host": os.getenv("SMTP_HOST", "").strip(),
        "port": int(os.getenv("SMTP_PORT", "465") or 465),
        "user": os.getenv("SMTP_USER", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from": os.getenv("SMTP_FROM", "").strip(),
        "ssl": os.getenv("SMTP_SSL", "1").lower() not in ("0", "false", "no"),
    }
    cfg_path = Path(__file__).parent / "data" / "email_smtp.json"
    if cfg_path.exists():
        try:
            st.update(json.loads(cfg_path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return st


# ---------------------------------------------------------------------------
# 1. 留资管理（本地运营编辑；导出走 HCG lead_export）
# ---------------------------------------------------------------------------
def save_lead(author_id: str, contact_name: str = "", phone: str = "", wechat: str = "",
              email: str = "", mcn: str = "", company: str = "", region: str = "",
              actor: str = "AI") -> dict:
    """保存/更新 KOS 留资（写入 kos_profiles 资产字段，幂等补齐列）。"""
    conn = _conn()
    try:
        ke._ensure_asset_columns(conn)
        cur = conn.execute("SELECT author_id FROM kos_profiles WHERE author_id = ?", (author_id,)).fetchone()
        if not cur:
            return {"ok": False, "error": f"KOS 不存在: {author_id}"}
        conn.execute(
            """UPDATE kos_profiles SET contact_name=?, phone=?, wechat=?, email=?, mcn=?, company=?, updated_at=?
               WHERE author_id=?""",
            (contact_name, phone, wechat, email, mcn, company, _now(), author_id))
        # 运营动作留痕
        conn.execute("INSERT INTO kos_operations (author_id, action, note, actor, created_at) VALUES (?,?,?,?,?)",
                     (author_id, "lead_update", f"contact={contact_name} email={email}", actor, _now()))
        conn.commit()
        return {"ok": True, "author_id": author_id}
    finally:
        conn.close()


def get_lead(author_id: str) -> dict:
    conn = _conn()
    try:
        r = conn.execute(
            "SELECT author_id, contact_name, phone, wechat, email, mcn, company, ownership_type, identity_label "
            "FROM kos_profiles WHERE author_id = ?", (author_id,)).fetchone()
        return dict(r) if r else {"ok": False, "error": "not found"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 2. 合作状态（草稿记录；cooperation_confirm 确认走 HCG）
# ---------------------------------------------------------------------------
def update_cooperation(author_id: str, cooperation_status: str = "NONE", quote: float = 0.0,
                       budget: float = 0.0, note: str = "", actor: str = "AI") -> dict:
    """更新合作状态草稿。cooperation_status: NONE/LEAD/DISCUSSING/NEGOTIATING/CONFIRMED/COMPLETED/REJECTED。"""
    valid = {"NONE", "LEAD", "DISCUSSING", "NEGOTIATING", "CONFIRMED", "COMPLETED", "REJECTED"}
    if cooperation_status not in valid:
        return {"ok": False, "error": f"非法合作状态: {cooperation_status}, 可选: {sorted(valid)}"}
    conn = _conn()
    try:
        ke._ensure_asset_columns(conn)
        cur = conn.execute("SELECT author_id FROM kos_profiles WHERE author_id = ?", (author_id,)).fetchone()
        if not cur:
            return {"ok": False, "error": f"KOS 不存在: {author_id}"}
        conn.execute(
            "UPDATE kos_profiles SET cooperation_status=?, quote=?, budget=?, updated_at=? WHERE author_id=?",
            (cooperation_status, float(quote or 0), float(budget or 0), _now(), author_id))
        conn.execute("INSERT INTO kos_operations (author_id, action, note, actor, created_at) VALUES (?,?,?,?,?)",
                     (author_id, "cooperation_draft", f"status={cooperation_status} quote={quote} budget={budget} {note}", actor, _now()))
        conn.commit()
        return {"ok": True, "author_id": author_id, "cooperation_status": cooperation_status}
    finally:
        conn.close()


def confirm_cooperation(author_id: str, confirmed_by: str, quote: float = 0.0, budget: float = 0.0) -> dict:
    """商务合作确认（HCG cooperation_confirm 门控）：仅登记 execution，由人工确认后落地。"""
    conn = _conn()
    try:
        r = conn.execute("SELECT author_id FROM kos_profiles WHERE author_id = ?", (author_id,)).fetchone()
        if not r:
            return {"ok": False, "error": f"KOS 不存在: {author_id}"}
        exec_ = kx.create_execution(
            action_type="cooperation_confirm",
            target_author_id=author_id,
            payload={"quote": quote, "budget": budget},
            actor="AI")
        return {"ok": True, "hcg": {"status": exec_["status"], "execution_id": exec_["execution_id"],
                                    "note": "合作确认需人工审批后才生效"}}
    finally:
        conn.close()


def execute_cooperation(execution_id: str, actor: str) -> dict:
    """人工确认后落地合作确认（HCG 状态机 EXECUTING -> SUCCESS）。"""
    e = kx.get_execution(execution_id)
    if not e:
        return {"ok": False, "error": "execution 不存在"}
    payload = json.loads(e.get("payload") or "{}")
    try:
        kx.transition(execution_id, "PENDING_HUMAN_REVIEW", actor=actor)
        e2 = kx.transition(execution_id, "EXECUTING", actor=actor)
        conn = _conn()
        try:
            conn.execute(
                "UPDATE kos_profiles SET cooperation_status='CONFIRMED', quote=?, budget=?, updated_at=? WHERE author_id=?",
                (payload.get("quote", 0), payload.get("budget", 0), _now(), e["target_author_id"]))
            conn.execute("INSERT INTO kos_operations (author_id, action, note, actor, created_at) VALUES (?,?,?,?,?)",
                         (e["target_author_id"], "cooperation_confirmed", f"by={actor}", actor, _now()))
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, **kx.transition(execution_id, "SUCCESS", actor=actor,
                                            result="cooperation confirmed", evidence_ref=f"exec={execution_id}")}
    except Exception as exc:
        try:
            kx.transition(execution_id, "FAILED", actor=actor, failure_reason=str(exc))
        except Exception:
            pass
        return {"ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# 3. 邮件邀约（HCG email_send 门控：生成 -> 人工确认 -> 发送）
# ---------------------------------------------------------------------------
def create_invitation_email(author_id: str, subject: str = "", body: str = "", actor: str = "AI") -> dict:
    """创建邮件邀约 execution（AI_GENERATED，不发送）。"""
    conn = _conn()
    try:
        r = conn.execute("SELECT contact_name, email FROM kos_profiles WHERE author_id = ?", (author_id,)).fetchone()
        if not r:
            return {"ok": False, "error": f"KOS 不存在: {author_id}"}
        email = (r["email"] or "").strip()
        if not email:
            return {"ok": False, "error": "KOS 未登记邮箱（email 字段为空）"}
        exec_ = kx.create_execution(
            action_type="email_send",
            target_author_id=author_id,
            payload={"to_email": email, "subject": subject, "body": body},
            actor=actor)
        return {"ok": True, "to_email": email, "hcg": {"status": exec_["status"],
                                                       "execution_id": exec_["execution_id"],
                                                       "note": "邮件未发送；需人工审批后执行"}}
    finally:
        conn.close()


def send_invitation_email(execution_id: str, actor: str) -> dict:
    """人工确认后发送邮件（HCG：EXECUTING -> SUCCESS/FAILED）。"""
    e = kx.get_execution(execution_id)
    if not e:
        return {"ok": False, "error": "execution 不存在"}
    if e.get("status") not in ("PENDING_HUMAN_REVIEW", "HUMAN_APPROVED", "EXECUTING"):
        return {"ok": False, "error": f"状态不允许发送: {e.get('status')}"}
    try:
        e = kx.transition(execution_id, "PENDING_HUMAN_REVIEW", actor=actor)
        e = kx.transition(execution_id, "HUMAN_APPROVED", actor=actor)
        e = kx.transition(execution_id, "EXECUTING", actor=actor)
        payload = json.loads(e.get("payload") or "{}")
        st = _smtp_settings()
        if not (st.get("host") and st.get("user") and st.get("password")):
            raise RuntimeError("SMTP 未配置（SMTP_HOST/USER/PASSWORD）")
        msg = EmailMessage()
        msg["Subject"] = payload.get("subject") or "KOS 合作邀约"
        msg["From"] = st.get("from") or st["user"]
        msg["To"] = payload.get("to_email", "")
        msg.set_content(payload.get("body") or "")
        if st.get("ssl"):
            with smtplib.SMTP_SSL(st["host"], int(st.get("port", 465)), timeout=20) as server:
                server.login(st["user"], st["password"]); server.send_message(msg)
        else:
            with smtplib.SMTP(st["host"], int(st.get("port", 587)), timeout=20) as server:
                server.starttls(); server.login(st["user"], st["password"]); server.send_message(msg)
        conn = _conn()
        try:
            conn.execute("INSERT INTO kos_operations (author_id, action, note, actor, created_at) VALUES (?,?,?,?,?)",
                         (e["target_author_id"], "email_sent", f"to={payload.get('to_email')}", actor, _now()))
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, **kx.transition(execution_id, "SUCCESS", actor=actor,
                                            result="email sent", evidence_ref=f"exec={execution_id}")}
    except Exception as exc:
        try:
            kx.transition(execution_id, "FAILED", actor=actor, failure_reason=str(exc))
        except Exception:
            pass
        return {"ok": False, "error": str(exc), "stage": "send_failed"}


# ---------------------------------------------------------------------------
# 4. 运营动作闭环（记录 + 生命周期推进）
# ---------------------------------------------------------------------------
_LIFECYCLE_STAGES = ["discovered", "observed", "growing", "stable", "burst", "cooperating", "core", "dormant"]


def record_operation(author_id: str, action: str, note: str = "", actor: str = "AI") -> dict:
    """记录运营动作并推进生命周期（发现->观察->成长->稳定->爆发->合作->核心->沉寂）。"""
    conn = _conn()
    try:
        ke._ensure_asset_columns(conn)
        cur = conn.execute("SELECT lifecycle_stage FROM kos_profiles WHERE author_id = ?", (author_id,)).fetchone()
        if not cur:
            return {"ok": False, "error": f"KOS 不存在: {author_id}"}
        conn.execute("INSERT INTO kos_operations (author_id, action, note, actor, created_at) VALUES (?,?,?,?,?)",
                     (author_id, action, note, actor, _now()))
        # 生命周期推进映射
        advance = {
            "outreach": "observed", "lead_captured": "growing", "cooperation": "cooperating",
            "content_published": "stable", "viral": "burst", "core_partner": "core", "inactive": "dormant",
        }
        target = advance.get(action)
        if target and cur["lifecycle_stage"] != target:
            # 按顺序只允许向前推进（核心/沉寂为终态，不倒退）
            stages = _LIFECYCLE_STAGES
            if cur["lifecycle_stage"] in stages and target in stages:
                if stages.index(target) > stages.index(cur["lifecycle_stage"]):
                    conn.execute("UPDATE kos_profiles SET lifecycle_stage=?, updated_at=? WHERE author_id=?",
                                 (target, _now(), author_id))
        conn.commit()
        new_stage = conn.execute("SELECT lifecycle_stage FROM kos_profiles WHERE author_id = ?", (author_id,)).fetchone()["lifecycle_stage"]
        return {"ok": True, "author_id": author_id, "action": action, "lifecycle_stage": new_stage}
    finally:
        conn.close()


def operation_log(author_id: str = "", limit: int = 50) -> list:
    conn = _conn()
    try:
        if author_id:
            rows = conn.execute(
                "SELECT author_id, action, note, actor, created_at FROM kos_operations WHERE author_id=? ORDER BY id DESC LIMIT ?",
                (author_id, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT author_id, action, note, actor, created_at FROM kos_operations ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _smtp_configured() -> bool:
    st = _smtp_settings()
    return bool(st.get("host") and st.get("user") and st.get("password"))


def _scoped_operation_identity(actor, scope, action, connection=None):
    from lumenis.shared.reporting.saved_work import authorize
    if scope.get("domain_id") not in {"bmp", "zbmp"} or not scope.get("brand_focus_id") or scope.get("global_scope") is not False:
        raise ValueError("KOS_EXACT_BRAND_SCOPE_REQUIRED")
    return authorize(actor, scope, action=action, connection=connection)


def resolve_author_aliases(body, *, required=True, execution=False):
    """Legacy KOS_ID is an author identifier, never scope or identity authority."""
    keys = ("author_id", "kos_id", "target_author_id") if execution else ("author_id", "kos_id")
    values = []
    for key in keys:
        if key not in body:
            continue
        value = body[key]
        if not required and isinstance(value, str) and not value.strip():
            continue
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 200:
            raise ValueError("AUTHOR_ID_REQUIRED")
        values.append(value.strip())
    if len(set(values)) > 1:
        raise ValueError("KOS_AUTHOR_ID_CONFLICT")
    if not values and required:
        raise ValueError("AUTHOR_ID_REQUIRED")
    return values[0] if values else ""


def normalize_execution_payload(body, action_type):
    """Adapt legacy cooperation amounts before hashing the exact approval."""
    import math
    payload = body.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("KOS_EXECUTION_PAYLOAD_INVALID")
    payload = dict(payload)
    for key in ("quote", "budget"):
        if action_type == "cooperation_confirm":
            for value in [mapping[key] for mapping in (body, payload) if key in mapping]:
                if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                    raise ValueError("KOS_OPERATION_NUMBER_INVALID")
        if key in body:
            if action_type != "cooperation_confirm":
                raise ValueError("KOS_EXECUTION_FIELDS_INVALID")
            if key in payload and payload[key] != body[key]:
                raise ValueError("KOS_EXECUTION_PAYLOAD_CONFLICT")
            payload[key] = body[key]
    return payload


def _operation_projection(value, record_id):
    result = {**value, "record_id": record_id}
    if value["operation"] == "paid_plan":
        # Derived from the existing immutable version, not a second plan store.
        result["plan_id"] = "kos-plan:v1:" + value["sha256"]
    return result


# Complete projections must fail explicitly rather than silently losing history.
_SCOPED_HISTORY_MAX_ROWS = 10000
_SCOPED_HISTORY_MAX_BYTES = 16 * 1024 * 1024


class ScopedOperationHistoryLimitError(RuntimeError):
    """The full verified projection exceeds the existing owner's read budget."""


def read_scoped_operations(*, actor, scope, author_id="", operation=None, limit=100,
                           complete_history=False, connection=None):
    """Read only actor-owned structured operations; never infer legacy row scope."""
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("KOS_OPERATION_LIMIT_INVALID")
    if type(complete_history) is not bool:
        raise ValueError("KOS_OPERATION_HISTORY_MODE_INVALID")
    from contextlib import nullcontext
    context = _scoped_operation_identity(actor, scope, "read", connection=connection)
    manager = nullcontext(connection) if connection is not None else get_repository().connection(read_only=True, wal=False)
    with manager as con:
        exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='kos_operations'").fetchone()
        if exists is None:
            return {"items": [], "coverage": "NOT_COLLECTED", "legacy_scope": "UNKNOWN"}
        predicate = "action LIKE 'scoped_%'"
        params = []
        if author_id:
            predicate += " AND author_id=?"
            params.append(author_id)
        if operation is not None:
            predicate += " AND action=?"
            params.append("scoped_" + str(operation))
        query = "SELECT * FROM kos_operations WHERE " + predicate + " ORDER BY id DESC"
        if complete_history:
            query += " LIMIT ?"
            params.append(_SCOPED_HISTORY_MAX_ROWS + 1)
        rows = con.execute(query, params)
        items = []
        chains = {}
        scanned_bytes = 0
        for index, row in enumerate(rows):
            if complete_history:
                scanned_bytes += len(str(row["note"]).encode("utf-8"))
                if index >= _SCOPED_HISTORY_MAX_ROWS or scanned_bytes > _SCOPED_HISTORY_MAX_BYTES:
                    raise ScopedOperationHistoryLimitError("KOS_OPERATION_HISTORY_RESOURCE_LIMIT")
            try:
                value = json.loads(row["note"])
            except (TypeError, ValueError):
                continue
            if (not isinstance(value, dict) or value.get("schema") != "lumenis.kos-private-operation/v1"
                    or value.get("context") != context or value.get("author_id") != row["author_id"]
                    or row["action"] != "scoped_" + str(value.get("operation"))):
                continue
            if operation is not None and value.get("operation") != operation:
                continue
            from lumenis.shared.reporting.saved_work import _digest
            if value.get("sha256") != _digest({key: item for key, item in value.items() if key != "sha256"}):
                raise ValueError("KOS_OPERATION_INTEGRITY_FAILED")
            key = (value["author_id"], value["operation"])
            newer = chains.get(key)
            if newer is not None and (newer["parent_sha256"] != value["sha256"] or newer["version"] != value["version"] + 1):
                raise ValueError("KOS_OPERATION_PARENT_CHAIN_INVALID")
            chains[key] = value
            if complete_history or len(items) < limit:
                items.append(_operation_projection(value, row["id"]))
        if any(value["version"] != 1 or value["parent_sha256"] is not None for value in chains.values()):
            raise ValueError("KOS_OPERATION_PARENT_CHAIN_INVALID")
        _scoped_operation_identity(actor, scope, "read", connection=con)
    return {"items": items, "coverage": "scoped_actor_records", "legacy_scope": "UNKNOWN"}


def resolve_scoped_operation_record(*, actor, scope, record_id, author_id="", connection=None):
    """Resolve an explicit immutable draft without a default 100-row truncation."""
    if type(record_id) is not int or record_id <= 0:
        raise ValueError("KOS_OPERATION_RECORD_ID_INVALID")
    records = read_scoped_operations(actor=actor, scope=scope, complete_history=True,
                                     connection=connection)["items"]
    matches = [item for item in records if item["record_id"] == record_id]
    if len(matches) != 1:
        raise PermissionError("KOS_PLAN_NOT_FOUND_IN_SCOPE")
    source = matches[0]
    if author_id and source["author_id"] != author_id:
        raise ValueError("KOS_PLAN_AUTHOR_MISMATCH")
    if any(item["author_id"] == source["author_id"] and item["operation"] == source["operation"]
           and item["version"] > source["version"] for item in records):
        raise ValueError("KOS_PLAN_VERSION_SUPERSEDED")
    return source


def _bind_paid_result(*, actor, scope, author_id, payload, connection=None):
    from kos_paid import resolve_scoped_paid_plan
    return resolve_scoped_paid_plan(actor=actor, scope=scope, plan_id=payload.get("plan_id"),
                                   author_id=author_id, connection=connection)


class ScopedOperationApprovalRequired(PermissionError):
    def __init__(self, resource, request_id):
        super().__init__("KOS_OPERATION_APPROVAL_REQUIRED")
        self.resource = resource
        self.request_id = request_id


def _validate_scoped_operation(author_id, operation, payload, request_id, expected_version):
    import math
    import re
    from lumenis.shared.reporting.saved_work import _safe_payload
    fields = {
        "lead": {"contact_name", "phone", "wechat", "email", "mcn", "company", "region"},
        "cooperation": {"cooperation_status", "quote", "budget", "note"},
        "manual_metrics": {"wecom_add", "sales_amount", "boosting_budget", "inquiry", "clicks", "impressions", "revenue"},
        "paid_plan": {"note_id", "budget", "channel", "expected_reach"},
        "reward_plan": {"points", "amount", "reason"},
        "ownership_claim": {"ownership_class", "note"},
        "operation_note": {"action", "note"},
        "paid_result": {"plan_id", "spend", "impressions", "clicks", "conversions", "note"},
        "professional_config": {"platform", "account_id", "account_name", "enabled"},
        "professional_metrics": {"platform", "account_id", "metrics", "source_kind"},
    }
    if (not isinstance(author_id, str) or not author_id.strip() or len(author_id) > 200
            or operation not in fields or not isinstance(payload, dict) or not payload
            or set(payload) - fields[operation] or not isinstance(request_id, str)
            or re.fullmatch(r"[A-Za-z0-9_-]{8,128}", request_id) is None
            or type(expected_version) is not int or expected_version < 0):
        raise ValueError("KOS_OPERATION_INPUT_INVALID")
    if operation in {"professional_config", "professional_metrics"}:
        from kos_professional import validate_private_payload
        validate_private_payload(operation, payload)
        _safe_payload(payload)
        return
    numeric = {"quote", "budget", "wecom_add", "sales_amount", "boosting_budget", "inquiry", "clicks", "impressions", "revenue", "expected_reach", "points", "amount", "spend", "conversions"}
    for key, value in payload.items():
        if key in numeric:
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError("KOS_OPERATION_NUMBER_INVALID")
        elif not isinstance(value, str) or len(value) > 4000:
            raise ValueError("KOS_OPERATION_TEXT_INVALID")
    if operation == "cooperation" and payload.get("cooperation_status", "NONE") not in {"NONE", "LEAD", "DISCUSSING", "NEGOTIATING", "REJECTED"}:
        raise ValueError("KOS_COOPERATION_CONFIRMATION_REQUIRED")
    if operation == "ownership_claim":
        from kos_engine import OWNERSHIP_CLASSES
        if payload.get("ownership_class") not in OWNERSHIP_CLASSES:
            raise ValueError("KOS_OWNERSHIP_CLASS_INVALID")
    if operation == "paid_result" and not payload.get("plan_id"):
        raise ValueError("KOS_PRIVATE_PLAN_REQUIRED")
    _safe_payload(payload)


def scoped_operation_resource(*, actor, scope, author_id, operation, payload, request_id, expected_version=0):
    from lumenis.shared.reporting.saved_work import _digest
    _validate_scoped_operation(author_id, operation, payload, request_id, expected_version)
    context = _scoped_operation_identity(actor, scope, "write")
    request = {"context": context, "author_id": author_id, "operation": operation,
        "payload": payload, "request_id": request_id, "expected_version": expected_version}
    if operation == "paid_result":
        request["plan_binding"] = _bind_paid_result(actor=actor, scope=scope, author_id=author_id, payload=payload)
    return "kos-private:v1:" + _digest(request)

def write_scoped_operation(*, actor, scope, author_id, operation, payload, request_id, expected_version=0):
    """Append an exact private draft version to the existing operations ledger."""
    import re
    from lumenis.shared.reporting.saved_work import _digest, _json, _safe_payload, _check_effect
    from lumenis.system.security.permission import OperationType
    if (not isinstance(author_id, str) or not author_id.strip() or len(author_id) > 200
            or operation not in {"lead", "cooperation", "manual_metrics", "paid_plan", "reward_plan", "ownership_claim", "operation_note", "paid_result", "professional_config", "professional_metrics"}
            or not isinstance(payload, dict) or not isinstance(request_id, str)
            or re.fullmatch(r"[A-Za-z0-9_-]{8,128}", request_id) is None
            or type(expected_version) is not int or expected_version < 0):
        raise ValueError("KOS_OPERATION_INPUT_INVALID")
    _validate_scoped_operation(author_id, operation, payload, request_id, expected_version)
    payload = json.loads(_json(payload))
    _safe_payload(payload)
    context = _scoped_operation_identity(actor, scope, "write")
    binding = (_bind_paid_result(actor=actor, scope=scope, author_id=author_id, payload=payload)
               if operation == "paid_result" else None)
    resource_request = {"context": context, "author_id": author_id, "operation": operation,
        "payload": payload, "request_id": request_id, "expected_version": expected_version}
    if binding is not None:
        resource_request["plan_binding"] = binding
    resource = "kos-private:v1:" + _digest(resource_request)
    from lumenis.system.security.permission import get_permission_gate
    if get_permission_gate().get_valid_approval_token("db_write", resource, exact=True) is None:
        raise ScopedOperationApprovalRequired(resource, request_id)
    try:
        _check_effect(actor, scope, OperationType.DB_WRITE, resource)
    except ValueError as exc:
        if str(exc) != "WORK_EFFECT_PERMISSION_DENIED":
            raise
        raise ScopedOperationApprovalRequired(resource, request_id) from exc
    conn = _conn()
    try:
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        if operation == "paid_result" and binding != _bind_paid_result(
                actor=actor, scope=scope, author_id=author_id, payload=payload, connection=conn):
            raise ValueError("KOS_PLAN_BINDING_CHANGED")
        # Read matching immutable versions in this write transaction so concurrent
        # editors cannot both consume one expected version.
        rows = conn.execute("SELECT note,id FROM kos_operations WHERE author_id=? AND action=? ORDER BY id DESC",
                            (author_id, "scoped_" + operation)).fetchall()
        previous = None
        for row in rows:
            try:
                value = json.loads(row[0])
            except (TypeError, ValueError):
                continue
            if not isinstance(value, dict) or value.get("context") != context:
                continue
            if value.get("sha256") != _digest({key: item for key, item in value.items() if key != "sha256"}):
                raise ValueError("KOS_OPERATION_INTEGRITY_FAILED")
            if value.get("request_id") == request_id:
                if value.get("resource") != resource:
                    raise ValueError("KOS_OPERATION_REQUEST_CONFLICT")
                _scoped_operation_identity(actor, scope, "read", connection=conn)
                conn.rollback()
                return {"ok": True, "operation": _operation_projection(value, row["id"]), "replayed": True, "external_effect": "not_performed"}
            if previous is None:
                previous = value
        if operation == "professional_metrics":
            from kos_professional import validate_configuration_at_commit
            validate_configuration_at_commit(conn, context=context, account_key=author_id)
        actual = previous["version"] if previous else 0
        if actual != expected_version:
            raise ValueError("KOS_OPERATION_VERSION_CONFLICT")
        value = {"schema": "lumenis.kos-private-operation/v1", "context": context, "author_id": author_id,
            "operation": operation, "payload": payload, "request_id": request_id, "resource": resource,
            "version": actual + 1, "parent_sha256": previous["sha256"] if previous else None,
            "created_at": _now(), "state": "PRIVATE_DRAFT", "authorship": "user-supplied",
            "external_effect": "not_performed", "factual_verification": "NOT_ESTABLISHED"}
        if binding is not None:
            value["plan_binding"] = binding
        value["sha256"] = _digest(value)
        caller = context.get("principal_ref") or "actor:" + str(context["actor_id"])
        inserted = conn.execute("INSERT INTO kos_operations(author_id,action,note,actor,created_at) VALUES(?,?,?,?,?)",
                     (author_id, "scoped_" + operation, _json(value).decode(), caller, _now()))
        _scoped_operation_identity(actor, scope, "write", connection=conn)
        if get_permission_gate().get_valid_approval_token("db_write", resource, exact=True) is None:
            raise ScopedOperationApprovalRequired(resource, request_id)
        _check_effect(actor, scope, OperationType.DB_WRITE, resource, connection=conn)
        conn.commit()
        return {"ok": True, "operation": _operation_projection(value, inserted.lastrowid), "replayed": False, "external_effect": "not_performed"}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
