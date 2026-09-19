# -*- coding: utf-8 -*-
"""
lumenis.shared.evaluation.recorder — LUMENIS Shared Evaluation 记录与持久化层

核心原则（不可违反）：
1. 不允许只统计接口是否返回 200 —— 必须评价真实质量（数据/AI/Collector/Report/Runtime）
2. unknown 状态绝对不默认 pass —— 无数据/无法评估时标记 unknown，汇总时单独计数且拉低整体评级
3. 每条评估记录必须可追溯：source + evidence_ref + evaluated_at
4. 向后兼容：CREATE TABLE IF NOT EXISTS，不破坏现有数据库

五维度：data / ai / collector / report / runtime
状态：pass / warn / fail / unknown
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---- 常量 ----
VALID_DIMENSIONS = ("data", "ai", "collector", "report", "runtime")
VALID_STATUSES = ("pass", "warn", "fail", "unknown")

from lumenis.shared.database import main_db_path


# ============================================================
# EvaluationRecord 数据类
# ============================================================
@dataclass
class EvaluationRecord:
    """单条评估记录 —— 五维度统一数据结构。

    字段说明：
    - evaluation_id: 唯一标识（UUID4）
    - dimension: 维度 data/ai/collector/report/runtime
    - metric_name: 指标名（如 completeness, success_rate）
    - metric_value: 指标值（数值，0.0-1.0 或原始值）
    - threshold: 阈值描述（JSON 字符串，含 pass/warn/fail 边界）
    - status: pass/warn/fail/unknown（unknown 绝不默认 pass）
    - evaluated_at: 评估时间 ISO8601
    - source: 数据来源（表名/文件/模块名）
    - evidence_ref: 证据引用（SQL/文件路径/trace_id）
    - metadata: 扩展元数据 JSON
    """
    evaluation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dimension: str = ""
    metric_name: str = ""
    metric_value: Optional[float] = None
    threshold: str = ""
    status: str = "unknown"
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    source: str = ""
    evidence_ref: str = ""
    metadata: str = "{}"

    def __post_init__(self):
        if self.dimension and self.dimension not in VALID_DIMENSIONS:
            raise ValueError(f"Invalid dimension: {self.dimension}. Must be one of {VALID_DIMENSIONS}")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {self.status}. Must be one of {VALID_STATUSES}")
        # metadata 确保是 JSON 字符串
        if isinstance(self.metadata, dict):
            self.metadata = json.dumps(self.metadata, ensure_ascii=False)
        if isinstance(self.threshold, dict):
            self.threshold = json.dumps(self.threshold, ensure_ascii=False)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# 阈值判断
# ============================================================
def judge_status(
    value: Optional[float],
    pass_threshold: float,
    warn_threshold: float,
    higher_is_better: bool = True,
) -> str:
    """根据阈值判断状态。

    核心规则：
    - value 为 None → unknown（绝不默认 pass）
    - higher_is_better=True:  value >= pass_threshold → pass; >= warn_threshold → warn; else fail
    - higher_is_better=False: value <= pass_threshold → pass; <= warn_threshold → warn; else fail

    Args:
        value: 指标值，None 表示无法评估
        pass_threshold: pass 边界
        warn_threshold: warn 边界（介于 pass 和 fail 之间）
        higher_is_better: True=越高越好（如成功率），False=越低越好（如延迟、重复率）

    Returns:
        "pass" | "warn" | "fail" | "unknown"
    """
    if value is None:
        return "unknown"
    if higher_is_better:
        if value >= pass_threshold:
            return "pass"
        elif value >= warn_threshold:
            return "warn"
        else:
            return "fail"
    else:
        if value <= pass_threshold:
            return "pass"
        elif value <= warn_threshold:
            return "warn"
        else:
            return "fail"


def threshold_to_str(pass_threshold: float, warn_threshold: float, higher_is_better: bool = True) -> str:
    """将阈值配置序列化为字符串，存入 record.threshold。"""
    return json.dumps({
        "pass": pass_threshold,
        "warn": warn_threshold,
        "higher_is_better": higher_is_better,
    }, ensure_ascii=False)


# ============================================================
# 数据库层
# ============================================================
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS evaluation_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_id   TEXT    NOT NULL UNIQUE,
    dimension       TEXT    NOT NULL,
    metric_name     TEXT    NOT NULL,
    metric_value    REAL,
    threshold       TEXT    DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'unknown',
    evaluated_at    TEXT    NOT NULL,
    source          TEXT    DEFAULT '',
    evidence_ref    TEXT    DEFAULT '',
    metadata        TEXT    DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_eval_records_dimension ON evaluation_records(dimension);
CREATE INDEX IF NOT EXISTS idx_eval_records_status    ON evaluation_records(status);
CREATE INDEX IF NOT EXISTS idx_eval_records_evaluated ON evaluation_records(evaluated_at);
"""


def _get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or main_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """初始化 evaluation_records 表（幂等，不破坏现有数据）。"""
    conn = _get_connection(db_path)
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


# ============================================================
# record_evaluation —— 核心写入 API
# ============================================================
def record_evaluation(
    dimension: str,
    metric_name: str,
    metric_value: Optional[float],
    pass_threshold: float,
    warn_threshold: float,
    higher_is_better: bool = True,
    source: str = "",
    evidence_ref: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None,
    evaluated_at: Optional[str] = None,
) -> EvaluationRecord:
    """记录一条评估结果，自动判断状态并持久化。

    这是统一 Evaluation 系统的核心写入入口。任何维度的任何指标都通过此函数记录。

    关键保证：
    - metric_value=None → status=unknown（绝不默认 pass）
    - 自动按阈值判断 pass/warn/fail
    - 持久化到 evaluation_records 表

    Args:
        dimension: 维度 data/ai/collector/report/runtime
        metric_name: 指标名
        metric_value: 指标值（None 表示无法评估 → unknown）
        pass_threshold: pass 边界
        warn_threshold: warn 边界
        higher_is_better: 越高越好 or 越低越好
        source: 数据来源
        evidence_ref: 证据引用
        metadata: 扩展元数据
        db_path: 数据库路径（默认项目 monitor.db）
        evaluated_at: 评估时间（默认当前）

    Returns:
        EvaluationRecord（已持久化）
    """
    status = judge_status(metric_value, pass_threshold, warn_threshold, higher_is_better)
    record = EvaluationRecord(
        dimension=dimension,
        metric_name=metric_name,
        metric_value=metric_value,
        threshold=threshold_to_str(pass_threshold, warn_threshold, higher_is_better),
        status=status,
        source=source,
        evidence_ref=evidence_ref,
        metadata=metadata or {},
    )
    if evaluated_at:
        record.evaluated_at = evaluated_at

    conn = _get_connection(db_path)
    try:
        conn.execute(
            """INSERT OR REPLACE INTO evaluation_records
               (evaluation_id, dimension, metric_name, metric_value, threshold,
                status, evaluated_at, source, evidence_ref, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record.evaluation_id, record.dimension, record.metric_name,
             record.metric_value, record.threshold, record.status,
             record.evaluated_at, record.source, record.evidence_ref, record.metadata),
        )
        conn.commit()
    finally:
        conn.close()

    return record


def record_evaluation_raw(record: EvaluationRecord, db_path: Optional[str] = None) -> EvaluationRecord:
    """直接写入一个已构造的 EvaluationRecord（用于自定义状态场景）。"""
    conn = _get_connection(db_path)
    try:
        conn.execute(
            """INSERT OR REPLACE INTO evaluation_records
               (evaluation_id, dimension, metric_name, metric_value, threshold,
                status, evaluated_at, source, evidence_ref, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record.evaluation_id, record.dimension, record.metric_name,
             record.metric_value, record.threshold, record.status,
             record.evaluated_at, record.source, record.evidence_ref, record.metadata),
        )
        conn.commit()
    finally:
        conn.close()
    return record


# ============================================================
# get_evaluation_summary —— 汇总 API
# ============================================================
def get_evaluation_summary(
    dimension: Optional[str] = None,
    since: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """获取评估汇总。

    汇总逻辑（unknown 绝不默认 pass）：
    - 按维度统计 pass/warn/fail/unknown 计数
    - pass_rate = pass / total（unknown 计入 total 分母，拉低 pass_rate）
    - overall_status:
      * 有任何 fail → "fail"
      * 有任何 unknown 且无 fail → "warn"（unknown 是风险信号）
      * 有 warn 且无 fail/unknown → "warn"
      * 全部 pass → "pass"
    - 按指标列出最新一条记录

    Args:
        dimension: 可选，只汇总某维度
        since: 可选，只汇总此时间之后的记录（ISO8601 字符串）
        db_path: 数据库路径

    Returns:
        汇总 dict
    """
    conn = _get_connection(db_path)
    try:
        query = "SELECT * FROM evaluation_records WHERE 1=1"
        params: List[Any] = []
        if dimension:
            query += " AND dimension = ?"
            params.append(dimension)
        if since:
            query += " AND evaluated_at >= ?"
            params.append(since)
        query += " ORDER BY evaluated_at DESC"
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    records = [dict(r) for r in rows]

    # 按维度统计
    by_dimension: Dict[str, Dict[str, int]] = {}
    for rec in records:
        dim = rec["dimension"]
        if dim not in by_dimension:
            by_dimension[dim] = {"pass": 0, "warn": 0, "fail": 0, "unknown": 0, "total": 0}
        by_dimension[dim][rec["status"]] = by_dimension[dim].get(rec["status"], 0) + 1
        by_dimension[dim]["total"] += 1

    # 计算每个维度的 pass_rate 和 overall_status
    dimension_summary = {}
    for dim, counts in by_dimension.items():
        total = counts["total"]
        pass_rate = round(counts["pass"] / total, 4) if total > 0 else 0.0
        # overall_status 判定（unknown 不默认 pass）
        if counts["fail"] > 0:
            overall = "fail"
        elif counts["unknown"] > 0:
            overall = "warn"  # unknown 是风险信号
        elif counts["warn"] > 0:
            overall = "warn"
        else:
            overall = "pass"
        dimension_summary[dim] = {
            **counts,
            "pass_rate": pass_rate,
            "overall_status": overall,
        }

    # 全局汇总
    total_records = len(records)
    total_pass = sum(c["pass"] for c in by_dimension.values())
    total_warn = sum(c["warn"] for c in by_dimension.values())
    total_fail = sum(c["fail"] for c in by_dimension.values())
    total_unknown = sum(c["unknown"] for c in by_dimension.values())
    global_pass_rate = round(total_pass / total_records, 4) if total_records > 0 else 0.0

    if total_fail > 0:
        global_status = "fail"
    elif total_unknown > 0:
        global_status = "warn"
    elif total_warn > 0:
        global_status = "warn"
    else:
        global_status = "pass" if total_records > 0 else "unknown"

    # 每个指标的最新记录
    latest_by_metric: Dict[str, Dict[str, Any]] = {}
    for rec in records:
        key = f"{rec['dimension']}.{rec['metric_name']}"
        if key not in latest_by_metric:
            latest_by_metric[key] = rec

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_records": total_records,
        "global_status": global_status,
        "global_pass_rate": global_pass_rate,
        "counts": {
            "pass": total_pass,
            "warn": total_warn,
            "fail": total_fail,
            "unknown": total_unknown,
        },
        "by_dimension": dimension_summary,
        "latest_by_metric": latest_by_metric,
        "filter": {"dimension": dimension, "since": since},
    }


def get_evaluation_records(
    dimension: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """查询评估记录列表。"""
    conn = _get_connection(db_path)
    try:
        query = "SELECT * FROM evaluation_records WHERE 1=1"
        params: List[Any] = []
        if dimension:
            query += " AND dimension = ?"
            params.append(dimension)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY evaluated_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


# 模块加载时自动初始化表（幂等）
try:
    init_db()
except Exception as _e:
    print(f"[SharedEvaluation] init_db warning: {_e}", flush=True)
