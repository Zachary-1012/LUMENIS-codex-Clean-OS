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

DB_PATH = os.environ.get("ZBC_DB_PATH", str(Path(__file__).parent / "data" / "monitor.db"))


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
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
