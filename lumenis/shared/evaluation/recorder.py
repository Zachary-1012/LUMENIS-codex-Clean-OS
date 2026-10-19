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

from lumenis.shared.database import DatabaseRepository, main_db_path

# Public compatibility snapshot only; repository operations resolve the
# canonical path at call time in _get_connection().
DEFAULT_DB_PATH = main_db_path()


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
    conn = DatabaseRepository(path).connect(timeout=10)
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
    evaluation_id: Optional[str] = None,
    connection: Optional[sqlite3.Connection] = None,
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
        evaluation_id=evaluation_id or str(uuid.uuid4()),
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

    if connection is not None and db_path is not None:
        raise ValueError("external connection cannot be combined with db_path")
    owned_connection = connection is None
    conn = _get_connection(db_path) if owned_connection else connection
    if not owned_connection and not conn.in_transaction:
        raise ValueError("external evaluation connection requires an active transaction")
    try:
        if source == "synthetic_interpretability" and not _is_synthetic_interpretability_record(conn, record.to_dict()):
            raise ValueError("synthetic diagnostic source requires exact signed owner evidence")
        existing = None
        if evaluation_id:
            existing = conn.execute(
                "SELECT * FROM evaluation_records WHERE evaluation_id=?", (evaluation_id,)
            ).fetchone()
        if existing:
            current = dict(existing)
            proposed = record.to_dict()
            # Caller-supplied stable IDs support retry after a report was saved.
            # Never replace an existing evaluation with conflicting evidence.
            fields = ("dimension", "metric_name", "metric_value", "threshold", "status",
                      "source", "evidence_ref", "metadata")
            if any(current.get(field) != proposed[field] for field in fields):
                raise ValueError("evaluation_id already belongs to different evidence")
            record.evaluated_at = current["evaluated_at"]
        else:
            conn.execute(
                """INSERT INTO evaluation_records
                   (evaluation_id, dimension, metric_name, metric_value, threshold,
                    status, evaluated_at, source, evidence_ref, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (record.evaluation_id, record.dimension, record.metric_name,
                 record.metric_value, record.threshold, record.status,
                 record.evaluated_at, record.source, record.evidence_ref, record.metadata),
            )
        if owned_connection:
            conn.commit()
    finally:
        if owned_connection:
            conn.close()

    return record


def project_current_assurance(conn, record: Dict[str, Any]) -> Dict[str, Any]:
    """Project retired report inference in every reader without rewriting history."""
    if (record.get('source') != 'daily_reports:source_brief_job'
            or record.get('metric_name') != 'multimodal_analysis_integrity'):
        return record
    reason = 'REPORT_INFERENCE_NOT_REVERIFIED'
    try:
        metadata = json.loads(record.get('metadata') or '{}')
        if not isinstance(metadata, dict):
            raise ValueError('invalid metadata')
        row = conn.execute(
            'SELECT source_snapshot FROM daily_reports WHERE report_id=? AND artifact_hash=?',
            (metadata.get('report_id'), metadata.get('artifact_hash')),
        ).fetchone()
        snapshot = json.loads(row[0]) if row else {}
        media = snapshot.get('multimodal') if isinstance(snapshot, dict) else None
        if (isinstance(media, dict) and snapshot.get('job_id') == metadata.get('job_id')
                and snapshot.get('scope') == metadata.get('scope')
                and snapshot.get('actor_id') == metadata.get('actor_id')):
            if media.get('provider') not in {'ollama', 'zhipu', 'doubao', 'jev'}:
                return record
            reason = 'HISTORICAL_NOT_REVERIFIED'
    except (ValueError, TypeError):
        pass
    except sqlite3.OperationalError as exc:
        if 'no such table: daily_reports' not in str(exc):
            raise
    return {**record, 'metric_value': None,
            'status': 'unknown' if record.get('status') == 'pass' else record.get('status', 'unknown'),
            'historical_record_status': record.get('status'),
            'historical_metric_value': record.get('metric_value'),
            'inference_status': reason, 'current_inference_verified': False}


def get_evaluation_record(evaluation_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Read one persisted evaluation by its stable owner-assigned identity."""
    if not isinstance(evaluation_id, str) or not evaluation_id.strip():
        raise ValueError("evaluation_id is required")
    conn = _get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM evaluation_records WHERE evaluation_id=?",
            (evaluation_id,),
        ).fetchone()
        result = project_current_assurance(conn, dict(row)) if row else None
    finally:
        conn.close()
    return result


def get_artifact_evaluations(
    *, job_id: str, artifact_hash: str, scope: Dict[str, Any], actor_id: str,
    evidence_refs: set[str], db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Read evaluations bound to an already authorized, verified report artifact.

    The report owner must enforce access before calling. Exact artifact, scope,
    actor (when recorded), and evidence checks precede any user projection.
    Legacy engineering reviews can omit actor but cannot omit artifact scope.
    """
    if not job_id or not artifact_hash or not scope or not actor_id or not evidence_refs:
        raise ValueError("Exact report artifact binding is required")
    conn = DatabaseRepository(db_path or main_db_path()).connect(read_only=True, wal=False)
    try:
        rows = conn.execute(
            """SELECT * FROM evaluation_records WHERE dimension='report'
               AND json_extract(CASE WHEN json_valid(metadata) THEN metadata ELSE '{}' END,
                                '$.job_id')=?
               AND json_extract(CASE WHEN json_valid(metadata) THEN metadata ELSE '{}' END,
                                '$.artifact_hash')=?
               ORDER BY evaluated_at DESC, id DESC""",
            (job_id, artifact_hash),
        ).fetchall()
        records = [project_current_assurance(conn, dict(row)) for row in rows]
    finally:
        conn.close()
    matched = []
    for record in records:
        metadata = json.loads(record["metadata"])
        if metadata.get("scope") != scope or record["evidence_ref"] not in evidence_refs:
            continue
        if "actor_id" in metadata:
            if metadata["actor_id"] != actor_id:
                continue
        elif record["source"] != "engineering_runtime_review":
            continue
        matched.append(record)
    return matched


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
        records = [project_current_assurance(conn, dict(row)) for row in rows
                   if not _is_synthetic_interpretability_record(conn, dict(row))]
    finally:
        conn.close()

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
        if limit <= 0:
            return []
        # Filter current projected status, not a retired persisted PASS. Fetch
        # bounded chunks so pagination fills correctly without a full-table list.
        query += " ORDER BY evaluated_at DESC, id DESC"
        cursor = conn.execute(query, params)
        records = []
        while len(records) < limit:
            rows = cursor.fetchmany(min(limit, 256))
            if not rows:
                break
            for row in rows:
                record = project_current_assurance(conn, dict(row))
                if status is None or record['status'] == status:
                    records.append(record)
                    if len(records) == limit:
                        break
    finally:
        conn.close()
    return records


# 模块加载时自动初始化表（幂等）
try:
    init_db()
except Exception as _e:
    print(f"[SharedEvaluation] init_db warning: {_e}", flush=True)


def _is_synthetic_interpretability_record(conn, record):
    """Only exact signed synthetic-owner records are separate from business ratings.

    A self-reported source label cannot remove an unrelated business failure.
    Invalid/tampered rows stay in normal summaries rather than disappearing.
    """
    if record.get("source") != "synthetic_interpretability":
        return False
    import re
    reference = record.get("evidence_ref")
    if type(reference) is not str or re.fullmatch(r"app_evidence_records:[1-9][0-9]*", reference) is None:
        return False
    try:
        from lumenis.shared.evidence import store
        from lumenis.shared.evaluation.ai import project_synthetic_interpretability_metrics
        row = conn.execute("SELECT * FROM app_evidence_records WHERE id=?", (int(reference.split(":")[1]),)).fetchone()
        if row is None:
            return False
        row = dict(row)
        if (row.get("source") != "owned_ai_gateway"
                or row.get("feature_id") != "SYNTHETIC_INTERPRETABILITY_PACKET"
                or row.get("version") != "synthetic-interpretability:v1"
                or row.get("status") != "derived" or row.get("result") != "RECORDED"
                or not store.verify_evidence_record_integrity(row)):
            return False
        outputs = json.loads(row["outputs_json"])
        if outputs.get("runtime_verification") != "CAPTURE_ONLY_NOT_REEXECUTED":
            return False
        projected = project_synthetic_interpretability_metrics(outputs["packet"],
            evidence_ref=reference, packet_sha256=outputs["packet_sha256"])
        for item in projected:
            if (record.get("metric_name") == item["metric_name"]
                    and record.get("dimension") == item["dimension"]
                    and record.get("metric_value") == item["metric_value"]
                    and json.loads(record.get("metadata", "{}")) == item["metadata"]
                    and json.loads(record.get("threshold", "{}")) == json.loads(threshold_to_str(
                        item["pass_threshold"], item["warn_threshold"], False))
                    and record.get("status") == judge_status(item["metric_value"],
                        item["pass_threshold"], item["warn_threshold"], False)):
                return True
    except (KeyError, TypeError, ValueError, sqlite3.Error):
        return False
    return False
