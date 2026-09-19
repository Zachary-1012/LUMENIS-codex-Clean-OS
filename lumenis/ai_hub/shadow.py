# -*- coding: utf-8 -*-
"""AI Shadow（影子映射）队列。

原则：AI 产生的任何“建议动作”一律先进影子队列（pending），不直接写入客户业务库；
由有权限的人逐条 accept / reject，留痕可审计。采纳后的真正执行交给对应业务模块，
本模块只负责建议、依据与决策状态，确保 AI 与客户版数据隔离、可回滚、可解释。
"""
from __future__ import annotations
import os, json, sqlite3, threading, uuid
from datetime import datetime
from lumenis.shared.database import get_repository

_lock = threading.Lock()
VALID_STATUS = ("pending", "accepted", "rejected", "dismissed")


def _conn():
    c = get_repository().connect(timeout=15)
    c.row_factory = sqlite3.Row
    return c


def ensure_table():
    with _lock, _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS v4_ai_shadow(
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                module TEXT,
                kind TEXT,
                title TEXT,
                rationale TEXT,
                payload TEXT,
                status TEXT DEFAULT 'pending',
                decided_by TEXT,
                decided_at TEXT,
                note TEXT
            )"""
        )


def add_suggestion(module: str, title: str, payload, rationale=None, kind: str = "suggestion") -> dict:
    """把一条 AI 建议放入影子队列（绝不直接改业务数据）。"""
    ensure_table()
    sid = uuid.uuid4().hex[:12]
    row = {
        "id": sid,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "module": module or "",
        "kind": kind or "suggestion",
        "title": (title or "")[:200],
        "rationale": json.dumps(rationale or {}, ensure_ascii=False),
        "payload": json.dumps(payload if payload is not None else {}, ensure_ascii=False),
        "status": "pending",
    }
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO v4_ai_shadow(id,created_at,module,kind,title,rationale,payload,status)"
            " VALUES(:id,:created_at,:module,:kind,:title,:rationale,:payload,:status)", row)
    return {"ok": True, "id": sid}


def _row_to_dict(r: sqlite3.Row) -> dict:
    d = dict(r)
    for k in ("rationale", "payload"):
        try:
            d[k] = json.loads(d.get(k) or "{}")
        except Exception:
            d[k] = {}
    return d


def list_suggestions(status: str = "pending", limit: int = 100):
    ensure_table()
    q = "SELECT * FROM v4_ai_shadow"
    args = ()
    if status in VALID_STATUS:
        q += " WHERE status=?"
        args = (status,)
    elif status == "all":
        pass
    else:
        q += " WHERE status='pending'"
    q += " ORDER BY rowid DESC LIMIT ?"
    args = (*args, int(limit))
    with _lock, _conn() as c:
        rows = c.execute(q, args).fetchall()
    return [_row_to_dict(r) for r in rows]


def decide(sid: str, decision: str, user: str = "", note: str = "") -> dict:
    """人工决策：accepted / rejected / dismissed。"""
    if decision not in VALID_STATUS or decision == "pending":
        return {"ok": False, "error": "非法决策状态"}
    ensure_table()
    with _lock, _conn() as c:
        cur = c.execute(
            "UPDATE v4_ai_shadow SET status=?, decided_by=?, decided_at=?, note=? WHERE id=?",
            (decision, user or "", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), note or "", sid))
        if cur.rowcount == 0:
            return {"ok": False, "error": "建议不存在"}
    return {"ok": True, "id": sid, "status": decision}


def stats():
    ensure_table()
    with _lock, _conn() as c:
        rows = c.execute("SELECT status, COUNT(*) n FROM v4_ai_shadow GROUP BY status").fetchall()
    out = {s: 0 for s in VALID_STATUS}
    for r in rows:
        out[r["status"]] = r["n"]
    out["total"] = sum(v for k, v in out.items() if k != "total")
    return out
