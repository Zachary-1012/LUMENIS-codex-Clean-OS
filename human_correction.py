# -*- coding: utf-8 -*-
"""
人工修正可追溯（P0 红线：不得直接覆盖原始字段）
====================================================
人工修正必须记录：修正前原始值、修正后新值、修正人、修正时间、修正原因。
使用独立 human_corrections 表，不覆盖原始字段。

关联：canonical_id / source_id / raw_id
"""
from __future__ import annotations

import json
import os
import sqlite3
from lumenis.shared.database import DatabaseRepository
import time
from typing import Any, Dict, List, Optional

CORRECTION_TABLE = "human_corrections"

CORRECTION_DDL = f"""
CREATE TABLE IF NOT EXISTS {CORRECTION_TABLE} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    correction_id TEXT UNIQUE,
    canonical_id TEXT DEFAULT '',
    source_id TEXT DEFAULT '',
    source_table TEXT DEFAULT '',
    field_name TEXT NOT NULL,      -- 被修正的字段名
    original_value TEXT DEFAULT '', -- 修正前原始值（JSON 序列化）
    corrected_value TEXT DEFAULT '',-- 修正后新值（JSON 序列化）
    corrected_by TEXT DEFAULT '',   -- 修正人
    correction_reason TEXT DEFAULT '',  -- 修正原因
    correction_time TEXT DEFAULT '',    -- 修正时间
    status TEXT DEFAULT 'active',   -- active/reverted
    reverted_by TEXT DEFAULT '',
    reverted_at TEXT DEFAULT '',
    revert_reason TEXT DEFAULT ''
);
"""

CORRECTION_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_correction_canonical ON {CORRECTION_TABLE}(canonical_id)",
    f"CREATE INDEX IF NOT EXISTS idx_correction_source ON {CORRECTION_TABLE}(source_id, source_table)",
    f"CREATE INDEX IF NOT EXISTS idx_correction_field ON {CORRECTION_TABLE}(field_name)",
]


def ensure_correction_table(db_path: str) -> None:
    """确保人工修正表存在（幂等）。"""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    con = DatabaseRepository(db_path).connect(timeout=15)
    try:
        con.execute(CORRECTION_DDL)
        for idx in CORRECTION_INDEXES:
            con.execute(idx)
        con.commit()
    finally:
        con.close()


def _now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _new_correction_id() -> str:
    import uuid
    return f"cor_{uuid.uuid4().hex[:16]}"


def record_correction(db_path: str, *, field_name: str,
                      original_value: Any, corrected_value: Any,
                      corrected_by: str, correction_reason: str = "",
                      canonical_id: str = "", source_id: str = "",
                      source_table: str = "") -> Dict[str, Any]:
    """记录一条人工修正。不覆盖原始字段，仅追加修正记录。

    P0 红线：
    - 必须记录修正前原始值和修正后新值
    - 必须记录修正人、修正时间、修正原因
    - 不得直接覆盖原始字段
    """
    if not field_name:
        raise ValueError("field_name 不能为空")
    if not corrected_by:
        raise ValueError("corrected_by 不能为空（必须记录修正人）")

    ensure_correction_table(db_path)
    cid = _new_correction_id()
    now = _now_str()

    con = DatabaseRepository(db_path).connect(timeout=15)
    try:
        con.execute(
            f"INSERT INTO {CORRECTION_TABLE} "
            f"(correction_id, canonical_id, source_id, source_table, "
            f"field_name, original_value, corrected_value, "
            f"corrected_by, correction_reason, correction_time, status) "
            f"VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (cid, canonical_id, source_id, source_table,
             field_name,
             json.dumps(original_value, ensure_ascii=False, default=str),
             json.dumps(corrected_value, ensure_ascii=False, default=str),
             corrected_by, correction_reason, now, "active"),
        )
        con.commit()
    finally:
        con.close()

    return {
        "correction_id": cid,
        "field_name": field_name,
        "original_value": original_value,
        "corrected_value": corrected_value,
        "corrected_by": corrected_by,
        "correction_reason": correction_reason,
        "correction_time": now,
        "canonical_id": canonical_id,
        "source_id": source_id,
        "source_table": source_table,
        "status": "active",
    }


def get_corrections(db_path: str, *, canonical_id: str = "",
                    source_id: str = "", field_name: str = "",
                    active_only: bool = True,
                    limit: int = 100) -> List[Dict[str, Any]]:
    """查询人工修正记录。"""
    ensure_correction_table(db_path)
    con = DatabaseRepository(db_path).connect(timeout=15)
    con.row_factory = sqlite3.Row
    try:
        sql = f"SELECT * FROM {CORRECTION_TABLE}"
        conds = []
        params = []
        if canonical_id:
            conds.append("canonical_id=?")
            params.append(canonical_id)
        if source_id:
            conds.append("source_id=?")
            params.append(source_id)
        if field_name:
            conds.append("field_name=?")
            params.append(field_name)
        if active_only:
            conds.append("status='active'")
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = con.execute(sql, tuple(params)).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            # 反序列化值
            for key in ("original_value", "corrected_value"):
                try:
                    d[key] = json.loads(d[key]) if d[key] else None
                except (json.JSONDecodeError, TypeError):
                    pass
            result.append(d)
        return result
    finally:
        con.close()


def revert_correction(db_path: str, correction_id: str,
                      reverted_by: str, revert_reason: str = "") -> Dict[str, Any]:
    """撤销一条人工修正（标记为 reverted，不删除记录）。"""
    ensure_correction_table(db_path)
    now = _now_str()
    con = DatabaseRepository(db_path).connect(timeout=15)
    try:
        con.execute(
            f"UPDATE {CORRECTION_TABLE} SET status='reverted', "
            f"reverted_by=?, reverted_at=?, revert_reason=? "
            f"WHERE correction_id=?",
            (reverted_by, now, revert_reason, correction_id),
        )
        con.commit()
        return {"correction_id": correction_id, "status": "reverted",
                "reverted_by": reverted_by, "reverted_at": now}
    finally:
        con.close()


def apply_corrections_to_record(db_path: str, record: Dict[str, Any],
                                canonical_id: str = "") -> Dict[str, Any]:
    """将 active 的人工修正应用到记录副本（不修改原始记录，返回修正后的视图）。

    P0 红线：原始字段不被覆盖；此函数返回新 dict，原始 record 不变。
    """
    if not canonical_id and "canonical_id" in record:
        canonical_id = record["canonical_id"]
    corrections = get_corrections(db_path, canonical_id=canonical_id, active_only=True)
    if not corrections:
        return dict(record)
    corrected = dict(record)
    for c in corrections:
        field = c["field_name"]
        corrected[field] = c["corrected_value"]
        corrected[f"_correction_{field}"] = {
            "original": c["original_value"],
            "corrected_by": c["corrected_by"],
            "reason": c["correction_reason"],
            "time": c["correction_time"],
        }
    return corrected
