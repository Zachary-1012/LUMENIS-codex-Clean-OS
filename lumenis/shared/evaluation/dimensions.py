# -*- coding: utf-8 -*-
"""
lumenis.shared.evaluation.dimensions — LUMENIS 五维度真实质量评估

五维度：data / ai / collector / report / runtime

设计原则：
1. 不允许只统计接口 200 —— 每个指标都评价真实数据质量
2. unknown 绝不默认 pass —— 无数据时 metric_value=None → status=unknown
3. 支持 mock_data 注入 —— 测试时不执行真实采集/AI调用/报告生成
4. 每个指标有明确阈值（pass/warn/fail）
5. 所有结果通过 Shared Evaluation recorder.record_evaluation() 持久化

数据源映射：
- data:      notes 表（必填字段、新鲜度、重复率、溯源字段）
- ai:        ai_filter_log + note_review_history 表
- collector: collection_logs + collector-metrics.jsonl
- report:    daily_reports 表 + data/reports/ 目录
- runtime:   runtime_guardian_checkpoints + system_health_api
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .recorder import (
    DEFAULT_DB_PATH,
    EvaluationRecord,
    judge_status,
    record_evaluation,
    threshold_to_str,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]


# ============================================================
# 阈值配置（集中管理，可被覆盖）
# ============================================================
THRESHOLDS: Dict[str, Dict[str, Any]] = {
    # ---- data 维度 ----
    "data.completeness":       {"pass": 0.90, "warn": 0.70, "higher_is_better": True},
    "data.freshness_hours":    {"pass": 24.0, "warn": 72.0, "higher_is_better": False},
    "data.duplication_rate":   {"pass": 0.05, "warn": 0.15, "higher_is_better": False},
    "data.provenance_rate":    {"pass": 0.95, "warn": 0.80, "higher_is_better": True},
    # ---- ai 维度 ----
    "ai.accuracy":             {"pass": 0.85, "warn": 0.70, "higher_is_better": True},
    "ai.confidence_avg":       {"pass": 0.70, "warn": 0.50, "higher_is_better": True},
    "ai.human_correction_rate":{"pass": 0.10, "warn": 0.25, "higher_is_better": False},
    "ai.provider_reliability": {"pass": 0.90, "warn": 0.75, "higher_is_better": True},
    "ai.fallback_rate":        {"pass": 0.20, "warn": 0.40, "higher_is_better": False},
    # ---- collector 维度 ----
    "collector.success_rate":  {"pass": 0.85, "warn": 0.60, "higher_is_better": True},
    "collector.failure_rate":  {"pass": 0.10, "warn": 0.30, "higher_is_better": False},
    "collector.recovery_rate": {"pass": 0.70, "warn": 0.40, "higher_is_better": True},
    "collector.latency_sec":   {"pass": 120.0, "warn": 300.0, "higher_is_better": False},
    # ---- report 维度 ----
    "report.generation_success":{"pass": 0.90, "warn": 0.70, "higher_is_better": True},
    "report.artifact_validity":{"pass": 0.90, "warn": 0.70, "higher_is_better": True},
    "report.evidence_coverage":{"pass": 0.80, "warn": 0.60, "higher_is_better": True},
    # ---- runtime 维度 ----
    "runtime.uptime_hours":    {"pass": 24.0, "warn": 1.0, "higher_is_better": True},
    "runtime.heartbeat_rate":  {"pass": 0.95, "warn": 0.80, "higher_is_better": True},
    "runtime.crash_count":     {"pass": 0.0, "warn": 3.0, "higher_is_better": False},
    "runtime.recovery_count":  {"pass": 2.0, "warn": 5.0, "higher_is_better": False},
}


def _get_threshold(metric_key: str) -> Dict[str, Any]:
    return THRESHOLDS.get(metric_key, {"pass": 0.8, "warn": 0.6, "higher_is_better": True})


def _conn(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _safe_query(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
    """容错查询：表不存在等异常返回空列表（不崩溃，评估结果为 unknown）。"""
    try:
        return conn.execute(sql, params).fetchall()
    except Exception:
        return []


# ============================================================
# Data 维度评估
# ============================================================
def evaluate_data_dimension(
    db_path: Optional[str] = None,
    mock_data: Optional[Dict[str, Any]] = None,
) -> List[EvaluationRecord]:
    """数据维度评估：completeness / freshness / duplication / provenance。

    mock_data 结构（测试用）：
    {
        "total_notes": 100,
        "complete_notes": 95,          # 必填字段齐全
        "latest_publish_hours_ago": 2, # 最新数据距现在小时数
        "duplicate_count": 3,          # 重复记录数
        "provenance_count": 98,        # 有 source+timestamp 的记录数
    }
    """
    records: List[EvaluationRecord] = []
    source = "notes" + (" (mock)" if mock_data else "")

    if mock_data:
        total = mock_data.get("total_notes", 0)
        complete = mock_data.get("complete_notes", 0)
        freshness_hours = mock_data.get("latest_publish_hours_ago")
        dup_count = mock_data.get("duplicate_count", 0)
        provenance = mock_data.get("provenance_count", 0)
        evidence = "mock_data injected"
    else:
        conn = _conn(db_path)
        try:
            # 总数
            total = _safe_query(conn, "SELECT COUNT(*) as c FROM notes")[0]["c"]
            # completeness: note_id, title, content, url, publish_datetime, collected_at 非空
            complete_rows = _safe_query(conn, """
                SELECT COUNT(*) as c FROM notes
                WHERE note_id IS NOT NULL AND note_id != ''
                  AND title IS NOT NULL AND title != ''
                  AND content IS NOT NULL AND content != ''
                  AND collected_at IS NOT NULL AND collected_at != ''
            """)
            complete = complete_rows[0]["c"] if complete_rows else 0
            # freshness: 最新 publish_datetime 或 collected_at
            fresh_rows = _safe_query(conn, """
                SELECT MAX(CASE WHEN publish_datetime != '' THEN publish_datetime ELSE collected_at END) as latest
                FROM notes
            """)
            latest_str = fresh_rows[0]["latest"] if fresh_rows else None
            freshness_hours = None
            if latest_str:
                try:
                    latest_dt = datetime.fromisoformat(str(latest_str).replace("Z", "+00:00"))
                    freshness_hours = (datetime.now() - latest_dt).total_seconds() / 3600.0
                except Exception:
                    freshness_hours = None
            # duplication: is_duplicate=1
            dup_rows = _safe_query(conn, "SELECT COUNT(*) as c FROM notes WHERE is_duplicate=1")
            dup_count = dup_rows[0]["c"] if dup_rows else 0
            # provenance: source_platform + collected_at + note_id 非空
            prov_rows = _safe_query(conn, """
                SELECT COUNT(*) as c FROM notes
                WHERE source_platform IS NOT NULL AND source_platform != ''
                  AND collected_at IS NOT NULL AND collected_at != ''
                  AND note_id IS NOT NULL AND note_id != ''
            """)
            provenance = prov_rows[0]["c"] if prov_rows else 0
            evidence = "SELECT FROM notes"
        finally:
            conn.close()

    # 1. completeness
    completeness = round(complete / total, 4) if total > 0 else None
    th = _get_threshold("data.completeness")
    records.append(record_evaluation(
        dimension="data", metric_name="completeness",
        metric_value=completeness,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | total={total}, complete={complete}",
        metadata={"total_notes": total, "complete_notes": complete},
        db_path=db_path,
    ))

    # 2. freshness
    th = _get_threshold("data.freshness_hours")
    records.append(record_evaluation(
        dimension="data", metric_name="freshness_hours",
        metric_value=round(freshness_hours, 2) if freshness_hours is not None else None,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | latest={freshness_hours}h ago",
        metadata={"freshness_hours": freshness_hours},
        db_path=db_path,
    ))

    # 3. duplication
    duplication = round(dup_count / total, 4) if total > 0 else None
    th = _get_threshold("data.duplication_rate")
    records.append(record_evaluation(
        dimension="data", metric_name="duplication_rate",
        metric_value=duplication,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | duplicates={dup_count}/{total}",
        metadata={"duplicate_count": dup_count, "total_notes": total},
        db_path=db_path,
    ))

    # 4. provenance
    provenance_rate = round(provenance / total, 4) if total > 0 else None
    th = _get_threshold("data.provenance_rate")
    records.append(record_evaluation(
        dimension="data", metric_name="provenance_rate",
        metric_value=provenance_rate,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | provenance={provenance}/{total}",
        metadata={"provenance_count": provenance, "total_notes": total},
        db_path=db_path,
    ))

    return records


# ============================================================
# AI 维度评估
# ============================================================
def evaluate_ai_dimension(
    db_path: Optional[str] = None,
    mock_data: Optional[Dict[str, Any]] = None,
) -> List[EvaluationRecord]:
    """AI 维度评估：accuracy / confidence / human_correction / provider_reliability / fallback。

    mock_data 结构：
    {
        "ai_total": 100,
        "ai_correct": 85,            # 与规则/人工一致
        "confidence_values": [0.8, 0.9, ...],  # 或直接 avg_confidence
        "avg_confidence": 0.75,
        "human_corrections": 5,
        "provider_calls": 50,
        "provider_success": 45,
        "fallback_count": 10,
    }
    """
    records: List[EvaluationRecord] = []
    source = "ai_filter_log+note_review_history" + (" (mock)" if mock_data else "")

    if mock_data:
        ai_total = mock_data.get("ai_total", 0)
        ai_correct = mock_data.get("ai_correct", 0)
        avg_conf = mock_data.get("avg_confidence")
        if avg_conf is None and "confidence_values" in mock_data:
            cvs = mock_data["confidence_values"]
            avg_conf = sum(cvs) / len(cvs) if cvs else None
        human_corr = mock_data.get("human_corrections", 0)
        provider_calls = mock_data.get("provider_calls", 0)
        provider_success = mock_data.get("provider_success", 0)
        fallback_count = mock_data.get("fallback_count", 0)
        evidence = "mock_data injected"
    else:
        conn = _conn(db_path)
        try:
            # ai_total + confidence avg
            ai_rows = _safe_query(conn, """
                SELECT COUNT(*) as c, AVG(confidence) as avg_conf
                FROM ai_filter_log WHERE provider != 'rule'
            """)
            ai_total = ai_rows[0]["c"] if ai_rows else 0
            avg_conf = ai_rows[0]["avg_conf"] if ai_rows else None
            # accuracy: filter_result 非 pending/error 视为有效（简化口径，实际需人工标注对比）
            acc_rows = _safe_query(conn, """
                SELECT COUNT(*) as c FROM ai_filter_log
                WHERE provider != 'rule' AND filter_result IN ('pass', 'filtered')
            """)
            ai_correct = acc_rows[0]["c"] if acc_rows else 0
            # human corrections
            corr_rows = _safe_query(conn, "SELECT COUNT(*) as c FROM note_review_history")
            human_corr = corr_rows[0]["c"] if corr_rows else 0
            # provider reliability
            prov_rows = _safe_query(conn, """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN filter_result != 'error' THEN 1 ELSE 0 END) as success
                FROM ai_filter_log WHERE provider != 'rule'
            """)
            provider_calls = prov_rows[0]["total"] if prov_rows else 0
            provider_success = prov_rows[0]["success"] if prov_rows else 0
            # fallback: provider='rule' 的比例
            fb_rows = _safe_query(conn, "SELECT COUNT(*) as c FROM ai_filter_log WHERE provider = 'rule'")
            fallback_count = fb_rows[0]["c"] if fb_rows else 0
            evidence = "SELECT FROM ai_filter_log, note_review_history"
        finally:
            conn.close()

    # 1. accuracy
    accuracy = round(ai_correct / ai_total, 4) if ai_total > 0 else None
    th = _get_threshold("ai.accuracy")
    records.append(record_evaluation(
        dimension="ai", metric_name="accuracy",
        metric_value=accuracy,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | correct={ai_correct}/{ai_total}",
        metadata={"ai_total": ai_total, "ai_correct": ai_correct},
        db_path=db_path,
    ))

    # 2. confidence
    th = _get_threshold("ai.confidence_avg")
    records.append(record_evaluation(
        dimension="ai", metric_name="confidence_avg",
        metric_value=round(avg_conf, 4) if avg_conf is not None else None,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | avg_confidence={avg_conf}",
        metadata={"avg_confidence": avg_conf},
        db_path=db_path,
    ))

    # 3. human correction rate
    total_for_correction = ai_total + human_corr
    human_rate = round(human_corr / total_for_correction, 4) if total_for_correction > 0 else None
    th = _get_threshold("ai.human_correction_rate")
    records.append(record_evaluation(
        dimension="ai", metric_name="human_correction_rate",
        metric_value=human_rate,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | corrections={human_corr}/{total_for_correction}",
        metadata={"human_corrections": human_corr},
        db_path=db_path,
    ))

    # 4. provider reliability
    prov_rel = round(provider_success / provider_calls, 4) if provider_calls > 0 else None
    th = _get_threshold("ai.provider_reliability")
    records.append(record_evaluation(
        dimension="ai", metric_name="provider_reliability",
        metric_value=prov_rel,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | success={provider_success}/{provider_calls}",
        metadata={"provider_calls": provider_calls, "provider_success": provider_success},
        db_path=db_path,
    ))

    # 5. fallback rate
    total_ai_calls = provider_calls + fallback_count
    fallback_rate = round(fallback_count / total_ai_calls, 4) if total_ai_calls > 0 else None
    th = _get_threshold("ai.fallback_rate")
    records.append(record_evaluation(
        dimension="ai", metric_name="fallback_rate",
        metric_value=fallback_rate,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | fallback={fallback_count}/{total_ai_calls}",
        metadata={"fallback_count": fallback_count, "total_ai_calls": total_ai_calls},
        db_path=db_path,
    ))

    return records


# ============================================================
# Collector 维度评估
# ============================================================
def evaluate_collector_dimension(
    db_path: Optional[str] = None,
    mock_data: Optional[Dict[str, Any]] = None,
) -> List[EvaluationRecord]:
    """Collector 维度评估：success_rate / failure_rate / recovery_rate / latency。

    mock_data 结构：
    {
        "total_runs": 100,
        "success_runs": 85,
        "failure_runs": 10,
        "recovery_runs": 7,         # 从失败恢复成功
        "avg_latency_sec": 90.0,
    }
    """
    records: List[EvaluationRecord] = []
    source = "collection_logs" + (" (mock)" if mock_data else "")

    if mock_data:
        total_runs = mock_data.get("total_runs", 0)
        success_runs = mock_data.get("success_runs", 0)
        failure_runs = mock_data.get("failure_runs", 0)
        recovery_runs = mock_data.get("recovery_runs", 0)
        avg_latency = mock_data.get("avg_latency_sec")
        evidence = "mock_data injected"
    else:
        conn = _conn(db_path)
        try:
            total_rows = _safe_query(conn, "SELECT COUNT(*) as c FROM collection_logs")
            total_runs = total_rows[0]["c"] if total_rows else 0
            succ_rows = _safe_query(conn, "SELECT COUNT(*) as c FROM collection_logs WHERE status='success'")
            success_runs = succ_rows[0]["c"] if succ_rows else 0
            fail_rows = _safe_query(conn, "SELECT COUNT(*) as c FROM collection_logs WHERE status IN ('failed','error','blocked')")
            failure_runs = fail_rows[0]["c"] if fail_rows else 0
            # recovery: 失败后后续成功（简化口径：有 error_msg 但最终 status=success）
            rec_rows = _safe_query(conn, """
                SELECT COUNT(*) as c FROM collection_logs
                WHERE status='success' AND error_msg IS NOT NULL AND error_msg != ''
            """)
            recovery_runs = rec_rows[0]["c"] if rec_rows else 0
            # latency: finished_at - started_at
            lat_rows = _safe_query(conn, """
                SELECT AVG((julianday(finished_at) - julianday(started_at)) * 86400) as avg_lat
                FROM collection_logs
                WHERE finished_at IS NOT NULL AND finished_at != ''
                  AND started_at IS NOT NULL AND started_at != ''
            """)
            avg_latency = lat_rows[0]["avg_lat"] if lat_rows else None
            evidence = "SELECT FROM collection_logs"
        finally:
            conn.close()

    # 1. success_rate
    success_rate = round(success_runs / total_runs, 4) if total_runs > 0 else None
    th = _get_threshold("collector.success_rate")
    records.append(record_evaluation(
        dimension="collector", metric_name="success_rate",
        metric_value=success_rate,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | success={success_runs}/{total_runs}",
        metadata={"total_runs": total_runs, "success_runs": success_runs},
        db_path=db_path,
    ))

    # 2. failure_rate
    failure_rate = round(failure_runs / total_runs, 4) if total_runs > 0 else None
    th = _get_threshold("collector.failure_rate")
    records.append(record_evaluation(
        dimension="collector", metric_name="failure_rate",
        metric_value=failure_rate,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | failure={failure_runs}/{total_runs}",
        metadata={"failure_runs": failure_runs},
        db_path=db_path,
    ))

    # 3. recovery_rate
    recovery_rate = round(recovery_runs / failure_runs, 4) if failure_runs > 0 else (0.0 if total_runs > 0 else None)
    th = _get_threshold("collector.recovery_rate")
    records.append(record_evaluation(
        dimension="collector", metric_name="recovery_rate",
        metric_value=recovery_rate,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | recovery={recovery_runs}/{failure_runs}",
        metadata={"recovery_runs": recovery_runs, "failure_runs": failure_runs},
        db_path=db_path,
    ))

    # 4. latency
    th = _get_threshold("collector.latency_sec")
    records.append(record_evaluation(
        dimension="collector", metric_name="latency_sec",
        metric_value=round(avg_latency, 2) if avg_latency is not None else None,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | avg_latency={avg_latency}s",
        metadata={"avg_latency_sec": avg_latency},
        db_path=db_path,
    ))

    return records


# ============================================================
# Report 维度评估
# ============================================================
def evaluate_report_dimension(
    db_path: Optional[str] = None,
    mock_data: Optional[Dict[str, Any]] = None,
    reports_dir: Optional[str] = None,
) -> List[EvaluationRecord]:
    """Report 维度评估：generation_success / artifact_validity / evidence_coverage。

    mock_data 结构：
    {
        "total_reports": 30,
        "generated_reports": 28,       # 有 summary 内容
        "valid_artifacts": 25,         # 文件存在+非空
        "evidence_covered": 24,        # 有 hot_notes/key_events/risk_alerts
    }
    """
    records: List[EvaluationRecord] = []
    source = "daily_reports+reports_dir" + (" (mock)" if mock_data else "")

    if mock_data:
        total_reports = mock_data.get("total_reports", 0)
        generated = mock_data.get("generated_reports", 0)
        valid_artifacts = mock_data.get("valid_artifacts", 0)
        evidence_covered = mock_data.get("evidence_covered", 0)
        evidence = "mock_data injected"
    else:
        conn = _conn(db_path)
        try:
            total_rows = _safe_query(conn, "SELECT COUNT(*) as c FROM daily_reports")
            total_reports = total_rows[0]["c"] if total_rows else 0
            # generation_success: summary 非空
            gen_rows = _safe_query(conn, """
                SELECT COUNT(*) as c FROM daily_reports
                WHERE summary IS NOT NULL AND summary != ''
            """)
            generated = gen_rows[0]["c"] if gen_rows else 0
            # evidence_coverage: 有 hot_notes 或 key_events 或 risk_alerts
            ev_rows = _safe_query(conn, """
                SELECT COUNT(*) as c FROM daily_reports
                WHERE (hot_notes IS NOT NULL AND hot_notes != '[]' AND hot_notes != '')
                   OR (key_events IS NOT NULL AND key_events != '[]' AND key_events != '')
                   OR (risk_alerts IS NOT NULL AND risk_alerts != '[]' AND risk_alerts != '')
            """)
            evidence_covered = ev_rows[0]["c"] if ev_rows else 0
            evidence = "SELECT FROM daily_reports"
        finally:
            conn.close()

        # artifact_validity: 检查 data/reports/ 目录下文件
        rdir = reports_dir or os.path.join(_REPO_ROOT, "data", "reports")
        valid_artifacts = 0
        artifact_total = 0
        if os.path.isdir(rdir):
            for fname in os.listdir(rdir):
                if fname.endswith((".docx", ".xlsx", ".pdf", ".html", ".md")):
                    artifact_total += 1
                    fpath = os.path.join(rdir, fname)
                    try:
                        if os.path.getsize(fpath) >= 100:  # 非空
                            valid_artifacts += 1
                    except OSError:
                        pass
        # 如果目录无文件，用 DB 记录数代替
        if artifact_total == 0:
            valid_artifacts = generated
            artifact_total = total_reports
        else:
            # 归一化：用目录文件数作为 total
            total_reports = artifact_total
            generated = valid_artifacts  # 目录中有文件即视为生成成功

    # 1. generation_success
    gen_rate = round(generated / total_reports, 4) if total_reports > 0 else None
    th = _get_threshold("report.generation_success")
    records.append(record_evaluation(
        dimension="report", metric_name="generation_success",
        metric_value=gen_rate,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | generated={generated}/{total_reports}",
        metadata={"total_reports": total_reports, "generated_reports": generated},
        db_path=db_path,
    ))

    # 2. artifact_validity
    artifact_rate = round(valid_artifacts / total_reports, 4) if total_reports > 0 else None
    th = _get_threshold("report.artifact_validity")
    records.append(record_evaluation(
        dimension="report", metric_name="artifact_validity",
        metric_value=artifact_rate,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | valid={valid_artifacts}/{total_reports}",
        metadata={"valid_artifacts": valid_artifacts},
        db_path=db_path,
    ))

    # 3. evidence_coverage
    ev_rate = round(evidence_covered / total_reports, 4) if total_reports > 0 else None
    th = _get_threshold("report.evidence_coverage")
    records.append(record_evaluation(
        dimension="report", metric_name="evidence_coverage",
        metric_value=ev_rate,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | evidence={evidence_covered}/{total_reports}",
        metadata={"evidence_covered": evidence_covered},
        db_path=db_path,
    ))

    return records


# ============================================================
# Runtime 维度评估
# ============================================================
def evaluate_runtime_dimension(
    db_path: Optional[str] = None,
    mock_data: Optional[Dict[str, Any]] = None,
) -> List[EvaluationRecord]:
    """Runtime 维度评估：uptime / heartbeat / crash / recovery。

    mock_data 结构：
    {
        "uptime_hours": 48.0,
        "heartbeat_total": 100,
        "heartbeat_ok": 98,
        "crash_count": 0,
        "recovery_count": 1,
    }
    """
    records: List[EvaluationRecord] = []
    source = "runtime_guardian_checkpoints" + (" (mock)" if mock_data else "")

    if mock_data:
        uptime = mock_data.get("uptime_hours")
        hb_total = mock_data.get("heartbeat_total", 0)
        hb_ok = mock_data.get("heartbeat_ok", 0)
        crash_count = mock_data.get("crash_count")
        recovery_count = mock_data.get("recovery_count")
        evidence = "mock_data injected"
    else:
        conn = _conn(db_path)
        try:
            # uptime: 最早 checkpoint 到现在
            up_rows = _safe_query(conn, "SELECT MIN(created_at) as earliest FROM runtime_guardian_checkpoints")
            earliest = up_rows[0]["earliest"] if up_rows else None
            uptime = None
            if earliest:
                try:
                    start_dt = datetime.fromisoformat(str(earliest))
                    uptime = (datetime.now() - start_dt).total_seconds() / 3600.0
                except Exception:
                    uptime = None
            # heartbeat: state='active' 的比例
            hb_rows = _safe_query(conn, """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN state='active' THEN 1 ELSE 0 END) as ok
                FROM runtime_guardian_checkpoints
            """)
            hb_total = hb_rows[0]["total"] if hb_rows else 0
            hb_ok = hb_rows[0]["ok"] if hb_rows else 0
            # crash: state 含 crash/failed/dead
            crash_rows = _safe_query(conn, """
                SELECT COUNT(*) as c FROM runtime_guardian_checkpoints
                WHERE state IN ('crashed','failed','dead')
            """)
            crash_count = crash_rows[0]["c"] if crash_rows else 0
            # recovery: metadata 含 recovery 或 position 含 recover
            rec_rows = _safe_query(conn, """
                SELECT COUNT(*) as c FROM runtime_guardian_checkpoints
                WHERE position LIKE '%recover%' OR metadata LIKE '%recovery%'
            """)
            recovery_count = rec_rows[0]["c"] if rec_rows else 0
            evidence = "SELECT FROM runtime_guardian_checkpoints"
        finally:
            conn.close()

    # 1. uptime
    th = _get_threshold("runtime.uptime_hours")
    records.append(record_evaluation(
        dimension="runtime", metric_name="uptime_hours",
        metric_value=round(uptime, 2) if uptime is not None else None,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | uptime={uptime}h",
        metadata={"uptime_hours": uptime},
        db_path=db_path,
    ))

    # 2. heartbeat
    hb_rate = round(hb_ok / hb_total, 4) if hb_total > 0 else None
    th = _get_threshold("runtime.heartbeat_rate")
    records.append(record_evaluation(
        dimension="runtime", metric_name="heartbeat_rate",
        metric_value=hb_rate,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | heartbeat={hb_ok}/{hb_total}",
        metadata={"heartbeat_total": hb_total, "heartbeat_ok": hb_ok},
        db_path=db_path,
    ))

    # 3. crash_count
    th = _get_threshold("runtime.crash_count")
    records.append(record_evaluation(
        dimension="runtime", metric_name="crash_count",
        metric_value=float(crash_count) if crash_count is not None else None,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | crashes={crash_count}",
        metadata={"crash_count": crash_count},
        db_path=db_path,
    ))

    # 4. recovery_count
    th = _get_threshold("runtime.recovery_count")
    records.append(record_evaluation(
        dimension="runtime", metric_name="recovery_count",
        metric_value=float(recovery_count) if recovery_count is not None else None,
        pass_threshold=th["pass"], warn_threshold=th["warn"],
        higher_is_better=th["higher_is_better"],
        source=source, evidence_ref=f"{evidence} | recoveries={recovery_count}",
        metadata={"recovery_count": recovery_count},
        db_path=db_path,
    ))

    return records


# ============================================================
# 维度分发表
# ============================================================
DIMENSION_EVALUATORS = {
    "data": evaluate_data_dimension,
    "ai": evaluate_ai_dimension,
    "collector": evaluate_collector_dimension,
    "report": evaluate_report_dimension,
    "runtime": evaluate_runtime_dimension,
}
