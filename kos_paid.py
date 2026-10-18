"""KOS P2 投流与奖励执行闭环（KOS MASTER EXECUTION CONTRACT v1）

投流计划（paid_media）与奖励发放（reward_issue）均为 HCG 门控动作：
AI_GENERATED -> PENDING_HUMAN_REVIEW -> HUMAN_APPROVED -> EXECUTING -> SUCCESS/FAILED

- 投流：评分建议已有（ad_candidate_score）；本模块落地执行计划 + 效果反馈（ROI 真实记录）
- 奖励：计算已有（reward_calculate）；本模块落地发放台账（reward_issue 门控）
"""
from __future__ import annotations
import json, os, sqlite3
from datetime import datetime
from pathlib import Path

import kos_execution as kx

from lumenis.shared.database import get_repository, main_db_path

DB_PATH = main_db_path()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _conn() -> sqlite3.Connection:
    # Shared Database resolves ZBC_DB_PATH at call time.
    conn = get_repository().connect(timeout=10)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kos_paid_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT UNIQUE,
            author_id TEXT DEFAULT '',
            note_id TEXT DEFAULT '',
            budget REAL DEFAULT 0,
            channel TEXT DEFAULT 'xhs',
            status TEXT DEFAULT 'DRAFT',
            expected_reach INTEGER DEFAULT 0,
            spend REAL DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            conversions INTEGER DEFAULT 0,
            roi REAL DEFAULT 0,
            created_at TEXT,
            executed_at TEXT,
            evidence_ref TEXT DEFAULT ''
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kos_paid_author ON kos_paid_plans(author_id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kos_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reward_id TEXT UNIQUE,
            author_id TEXT NOT NULL,
            points REAL DEFAULT 0,
            amount REAL DEFAULT 0,
            reason TEXT DEFAULT '',
            status TEXT DEFAULT 'AI_GENERATED',
            actor TEXT DEFAULT 'AI',
            created_at TEXT,
            issued_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kos_reward_author ON kos_rewards(author_id)")
    return conn


# ---------------------------------------------------------------------------
# 投流执行闭环（paid_media HCG 门控）
# ---------------------------------------------------------------------------
def create_paid_plan(author_id: str = "", note_id: str = "", budget: float = 0,
                     channel: str = "xhs", expected_reach: int = 0, actor: str = "AI") -> dict:
    """创建投流计划（HCG paid_media 门控：仅登记 execution，不实际投放）。"""
    if budget <= 0:
        return {"ok": False, "error": "预算必须 > 0"}
    exec_ = kx.create_execution(
        action_type="paid_media",
        target_author_id=author_id,
        payload={"note_id": note_id, "budget": budget, "channel": channel,
                 "expected_reach": expected_reach},
        actor=actor)
    return {"ok": True, "plan_id": exec_["execution_id"],
            "hcg": {"status": exec_["status"], "execution_id": exec_["execution_id"],
                    "note": "投流计划未执行；需人工审批后落地，投流结果以真实投放数据为准"}}


def execute_paid_plan(execution_id: str, actor: str) -> dict:
    """人工审批后执行投流计划（记录计划台账，不伪造 ROI）。"""
    e = kx.get_execution(execution_id)
    if not e:
        return {"ok": False, "error": "execution 不存在"}
    payload = json.loads(e.get("payload") or "{}")
    try:
        kx.transition(execution_id, "PENDING_HUMAN_REVIEW", actor=actor)
        kx.transition(execution_id, "HUMAN_APPROVED", actor=actor)
        kx.transition(execution_id, "EXECUTING", actor=actor)
        plan_id = "PAID-" + datetime.now().strftime("%Y%m%d%H%M%S") + "-" + execution_id[-6:]
        conn = _conn()
        try:
            conn.execute(
                """INSERT INTO kos_paid_plans
                   (plan_id, author_id, note_id, budget, channel, status, expected_reach, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (plan_id, e.get("target_author_id") or "", payload.get("note_id", ""),
                 payload.get("budget", 0), payload.get("channel", "xhs"),
                 "RUNNING", payload.get("expected_reach", 0), _now()))
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, "plan_id": plan_id,
                **kx.transition(execution_id, "SUCCESS", actor=actor,
                                result=f"paid plan {plan_id} started",
                                evidence_ref=f"exec={execution_id}")}
    except Exception as exc:
        try:
            kx.transition(execution_id, "FAILED", actor=actor, failure_reason=str(exc))
        except Exception:
            pass
        return {"ok": False, "error": str(exc)}


def record_paid_result(plan_id: str, spend: float = 0, impressions: int = 0,
                       clicks: int = 0, conversions: int = 0, actor: str = "AI") -> dict:
    """记录投流效果反馈（真实投放数据），计算 ROI，不伪造。"""
    conn = _conn()
    try:
        r = conn.execute("SELECT * FROM kos_paid_plans WHERE plan_id = ?", (plan_id,)).fetchone()
        if not r:
            return {"ok": False, "error": f"投流计划不存在: {plan_id}"}
        spend = float(spend or 0)
        impressions = int(impressions or 0)
        clicks = int(clicks or 0)
        conversions = int(conversions or 0)
        # ROI = (转化价值 - 花费) / 花费；价值按当前可测算口径（无转化价值默认按点击估算）
        roi = round((conversions * 50 - spend) / spend, 2) if spend > 0 else 0
        conn.execute(
            """UPDATE kos_paid_plans SET spend=?, impressions=?, clicks=?, conversions=?, roi=?, status='COMPLETED', executed_at=?
               WHERE plan_id=?""",
            (spend, impressions, clicks, conversions, roi, _now(), plan_id))
        conn.commit()
        return {"ok": True, "plan_id": plan_id, "spend": spend, "impressions": impressions,
                "clicks": clicks, "conversions": conversions, "roi": roi,
                "note": "ROI 为可测算口径（转化价值按默认 50/转化估算，需按实际营销价值校准）"}
    finally:
        conn.close()


def paid_plans(author_id: str = "", limit: int = 50) -> list:
    conn = _conn()
    try:
        if author_id:
            rows = conn.execute("SELECT * FROM kos_paid_plans WHERE author_id=? ORDER BY id DESC LIMIT ?",
                                (author_id, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM kos_paid_plans ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 奖励发放闭环（reward_issue HCG 门控）
# ---------------------------------------------------------------------------
def issue_reward(author_id: str, points: float = 0, amount: float = 0,
                 reason: str = "", actor: str = "AI") -> dict:
    """创建奖励发放（HCG reward_issue 门控：仅登记 execution，不实际发放）。"""
    if points <= 0 and amount <= 0:
        return {"ok": False, "error": "积分或金额必须 > 0"}
    exec_ = kx.create_execution(
        action_type="reward_issue",
        target_author_id=author_id,
        payload={"points": points, "amount": amount, "reason": reason},
        actor=actor)
    return {"ok": True, "hcg": {"status": exec_["status"], "execution_id": exec_["execution_id"],
                                "note": "奖励未发放；需人工审批后执行"}}


def execute_reward(execution_id: str, actor: str) -> dict:
    """人工审批后发放奖励（记录台账）。"""
    e = kx.get_execution(execution_id)
    if not e:
        return {"ok": False, "error": "execution 不存在"}
    payload = json.loads(e.get("payload") or "{}")
    try:
        kx.transition(execution_id, "PENDING_HUMAN_REVIEW", actor=actor)
        kx.transition(execution_id, "HUMAN_APPROVED", actor=actor)
        kx.transition(execution_id, "EXECUTING", actor=actor)
        reward_id = "RWD-" + datetime.now().strftime("%Y%m%d%H%M%S") + "-" + execution_id[-6:]
        conn = _conn()
        try:
            conn.execute(
                """INSERT INTO kos_rewards
                   (reward_id, author_id, points, amount, reason, status, actor, created_at, issued_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (reward_id, e.get("target_author_id") or "", payload.get("points", 0),
                 payload.get("amount", 0), payload.get("reason", ""),
                 "ISSUED", actor, _now(), _now()))
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, "reward_id": reward_id,
                **kx.transition(execution_id, "SUCCESS", actor=actor,
                                result=f"reward {reward_id} issued",
                                evidence_ref=f"exec={execution_id}")}
    except Exception as exc:
        try:
            kx.transition(execution_id, "FAILED", actor=actor, failure_reason=str(exc))
        except Exception:
            pass
        return {"ok": False, "error": str(exc)}


def reward_ledger(author_id: str = "", limit: int = 50) -> list:
    conn = _conn()
    try:
        if author_id:
            rows = conn.execute("SELECT * FROM kos_rewards WHERE author_id=? ORDER BY id DESC LIMIT ?",
                                (author_id, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM kos_rewards ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def resolve_scoped_paid_plan(*, actor, scope, plan_id, author_id="", connection=None):
    """Resolve current scoped plan versions; historical unscoped rows grant nothing.

    Results remain user-supplied observations. A resolved plan is neither a
    platform delivery receipt nor proof that paid amplification occurred.
    """
    import re
    from contextlib import nullcontext
    import kos_ops
    context = kos_ops._scoped_operation_identity(actor, scope, "read", connection=connection)
    if not isinstance(plan_id, str) or not plan_id or plan_id != plan_id.strip():
        raise ValueError("KOS_PRIVATE_PLAN_REQUIRED")
    if author_id and (not isinstance(author_id, str) or author_id != author_id.strip()):
        raise ValueError("AUTHOR_ID_REQUIRED")
    if re.fullmatch(r"kos-plan:v1:[0-9a-f]{64}", plan_id):
        records = kos_ops.read_scoped_operations(actor=actor, scope=scope, operation="paid_plan",
            complete_history=True, connection=connection)["items"]
        matches = [item for item in records if item["plan_id"] == plan_id]
        if len(matches) != 1:
            raise PermissionError("KOS_PLAN_NOT_FOUND_IN_SCOPE")
        source = matches[0]
        if any(item["author_id"] == source["author_id"] and item["version"] > source["version"] for item in records):
            raise ValueError("KOS_PLAN_VERSION_SUPERSEDED")
        binding = {"schema": "lumenis.kos-plan-binding/v1", "plan_id": plan_id,
                   "author_id": source["author_id"], "source_record_id": source["record_id"],
                   "source_sha256": source["sha256"], "source_version": source["version"]}
    elif re.fullmatch(r"KX-S-[0-9a-f]{32}", plan_id):
        manager = nullcontext(connection) if connection is not None else get_repository().connection(read_only=True, wal=False)
        with manager as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='kos_executions'").fetchone()
            row = con.execute("SELECT * FROM kos_executions WHERE execution_id=?", (plan_id,)).fetchone() if exists else None
            if row is None:
                raise PermissionError("KOS_PLAN_NOT_FOUND_IN_SCOPE")
            record, stored = kx._scoped_record(row, context)
            request = stored["request"]
            if (record["action_type"] != "paid_media" or request.get("action_type") != "paid_media"
                    or record["target_author_id"] != request.get("target_author_id")
                    or record["target_brand"] != scope["brand_focus_id"]):
                raise ValueError("KOS_PLAN_ACTION_OR_TARGET_MISMATCH")
            if record["status"] not in {"AI_GENERATED", "PENDING_HUMAN_REVIEW", "HUMAN_APPROVED", "EXECUTING", "SUCCESS"}:
                raise ValueError("KOS_PLAN_STATE_INVALID")
            binding = {"schema": "lumenis.kos-plan-binding/v1", "plan_id": plan_id,
                       "author_id": request["target_author_id"], "source_execution_id": plan_id,
                       "source_sha256": stored["request_sha256"]}
            kos_ops._scoped_operation_identity(actor, scope, "read", connection=con)
    elif plan_id.startswith(("PAID-", "KX-")):
        raise ValueError("KOS_LEGACY_PLAN_REQUIRES_SCOPED_RECREATION")
    else:
        raise ValueError("KOS_PLAN_REFERENCE_INVALID")
    if author_id and binding["author_id"] != author_id:
        raise ValueError("KOS_PLAN_AUTHOR_MISMATCH")
    if not isinstance(binding["author_id"], str) or not binding["author_id"].strip():
        raise ValueError("KOS_PLAN_AUTHOR_INVALID")
    return binding
