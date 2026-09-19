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
