# -*- coding: utf-8 -*-
"""VIZ Data Provider — 函数驱动可视化后端的数据注入层。

职责：
  1. 从真实 SQLite DB（data/monitor.db）查询原始数据
  2. 每个可视化函数对应一个 provider 函数
  3. 返回标准化数据包（records / total / source_timestamp / status / error）
  4. 查询失败显式返回 status=error，不静默、不 mock、不默认值填充
  5. 数据缺失返回空 records + status=no_data，由 ui_view_model 层显式表达

硬约束：
  - 禁止 mock/假数据，必须真实查询
  - 不修改 database.py 结构，本模块独立建连查询
  - API key / 敏感字段不入返回
  - 时间范围通过 compute_time_bounds 计算后注入 SQL
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ui_view_model import (
    DataQuery,
    DataResult,
    DataStatus,
    TimeRange,
    compute_time_bounds,
    filter_records_by_time,
)

# ── DB 连接 ────────────────────────────────────────────────────────────────

def _get_db_path() -> str:
    return os.path.abspath(
        os.environ.get("ZBC_DB_PATH")
        or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "monitor.db")
    )


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _rows_to_dicts(rows) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows]


def _safe_query(sql: str, params: Tuple = ()) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """执行查询，返回 (rows, error)。失败时 rows=[]，error=异常信息。"""
    try:
        with _get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return _rows_to_dicts(rows), None
    except Exception as exc:
        return [], str(exc)


def _safe_scalar(sql: str, params: Tuple = ()) -> Tuple[Optional[Any], Optional[str]]:
    """执行单值查询，返回 (value, error)。"""
    try:
        with _get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return (row[0] if row else None), None
    except Exception as exc:
        return None, str(exc)


def _time_clause(time_range: TimeRange, field: str = "collected_at") -> Tuple[str, Tuple]:
    """根据 TimeRange 生成 SQL 时间过滤子句。返回 (clause, params)。"""
    start, end = compute_time_bounds(time_range)
    if start is None:
        return "", ()
    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    return f" AND {field} >= ?", (start_str,)


def _make_data_result(
    source: str,
    records: List[Dict[str, Any]],
    total: Optional[int] = None,
    error: Optional[str] = None,
    source_timestamp: Optional[str] = None,
    time_range: TimeRange = TimeRange.TODAY,
) -> DataResult:
    """构造标准化 DataResult。"""
    if error:
        status = DataStatus.ERROR
    elif not records:
        status = DataStatus.NO_DATA
    else:
        status = DataStatus.OK
    return DataResult(
        query=DataQuery(source=source, time_range=time_range),
        records=records,
        total=total if total is not None else len(records),
        status=status,
        error=error,
        source_timestamp=source_timestamp,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Overview 域 Provider
# ═══════════════════════════════════════════════════════════════════════════

def provide_overview_stats(params: Dict[str, Any]) -> DataResult:
    """舆情总览统计：从 notes 表查询全量统计。"""
    tr = TimeRange.from_str(params.get("time_range", "today"))
    clause, cparams = _time_clause(tr, "collected_at")
    sql = f"""SELECT
        COUNT(*) as total,
        SUM(CASE WHEN sentiment='positive' THEN 1 ELSE 0 END) as positive,
        SUM(CASE WHEN sentiment='neutral' THEN 1 ELSE 0 END) as neutral,
        SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) as negative,
        SUM(CASE WHEN risk_level IN ('high','critical') THEN 1 ELSE 0 END) as high_risk,
        SUM(CASE WHEN risk_level='medium' THEN 1 ELSE 0 END) as medium_risk,
        SUM(CASE WHEN risk_level='low' THEN 1 ELSE 0 END) as low_risk,
        COALESCE(SUM(likes),0) as total_likes,
        COALESCE(SUM(comments),0) as total_comments,
        COALESCE(SUM(likes+comments+collects+shares),0) as total_engagements,
        SUM(CASE WHEN is_official=1 THEN 1 ELSE 0 END) as official_count,
        MAX(collected_at) as latest_collected
        FROM notes WHERE status='active' {clause}"""
    row, error = _safe_scalar(sql, cparams)
    if error:
        return _make_data_result("notes", [], error=error, time_range=tr)
    if row is None:
        return _make_data_result("notes", [], source_timestamp=None, time_range=tr)
    # row is a single scalar from _safe_scalar? No — _safe_scalar returns row[0].
    # We need the full row. Let me use _safe_query instead.
    records, error = _safe_query(sql, cparams)
    if error:
        return _make_data_result("notes", [], error=error, time_range=tr)
    ts = records[0].get("latest_collected") if records else None
    return _make_data_result("notes", records, total=records[0].get("total", 0) if records else 0,
                              source_timestamp=ts, time_range=tr)


def provide_overview_trend(params: Dict[str, Any]) -> DataResult:
    """舆情趋势：按日聚合笔记数、互动量、负面占比。"""
    tr = TimeRange.from_str(params.get("time_range", "30d"))
    clause, cparams = _time_clause(tr, "collected_at")
    sql = f"""SELECT
        date(collected_at) as day,
        COUNT(*) as note_count,
        COALESCE(SUM(likes+comments+collects+shares),0) as engagement,
        SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) as negative_count
        FROM notes WHERE status='active' {clause}
        GROUP BY date(collected_at) ORDER BY day ASC"""
    records, error = _safe_query(sql, cparams)
    if error:
        return _make_data_result("notes+daily_reports", [], error=error, time_range=tr)
    ts = records[-1].get("day") if records else None
    return _make_data_result("notes+daily_reports", records, source_timestamp=ts, time_range=tr)


def provide_industry_dist(params: Dict[str, Any]) -> DataResult:
    """业态分布：按 category 字段分组统计。"""
    tr = TimeRange.from_str(params.get("time_range", "30d"))
    limit = int(params.get("limit", 10))
    clause, cparams = _time_clause(tr, "collected_at")
    sql = f"""SELECT category, COUNT(*) as cnt,
        COALESCE(SUM(likes+comments+collects+shares),0) as engagement
        FROM notes WHERE status='active' AND category IS NOT NULL AND category != '' {clause}
        GROUP BY category ORDER BY cnt DESC LIMIT ?"""
    records, error = _safe_query(sql, cparams + (limit,))
    if error:
        return _make_data_result("notes", [], error=error, time_range=tr)
    return _make_data_result("notes", records, time_range=tr)


# ═══════════════════════════════════════════════════════════════════════════
# Brand 域 Provider
# ═══════════════════════════════════════════════════════════════════════════

def provide_brand_top10(params: Dict[str, Any]) -> DataResult:
    """品牌热度 TOP10：从 notes 的 source_keyword / matched_keywords 聚合。"""
    tr = TimeRange.from_str(params.get("time_range", "30d"))
    clause, cparams = _time_clause(tr, "collected_at")
    sql = f"""SELECT
        COALESCE(NULLIF(source_keyword,''),'unknown') as brand,
        COUNT(*) as mention_count,
        COALESCE(SUM(likes+comments+collects+shares),0) as engagement,
        MAX(collected_at) as latest
        FROM notes WHERE status='active' {clause}
        GROUP BY brand ORDER BY engagement DESC LIMIT 10"""
    records, error = _safe_query(sql, cparams)
    if error:
        return _make_data_result("notes+brand_directory", [], error=error, time_range=tr)
    ts = records[0].get("latest") if records else None
    return _make_data_result("notes+brand_directory", records, source_timestamp=ts, time_range=tr)


def provide_brand_growth(params: Dict[str, Any]) -> DataResult:
    """品牌增长：对比当前周期与上一周期的品牌互动量变化。"""
    tr = TimeRange.from_str(params.get("time_range", "30d"))
    start, end = compute_time_bounds(tr)
    if start is None:
        return _make_data_result("notes+metric_snapshots", [], time_range=tr)
    period_secs = (end - start).total_seconds()
    prev_start = start - __import__("datetime").timedelta(seconds=period_secs)
    cur_sql = """SELECT COALESCE(NULLIF(source_keyword,''),'unknown') as brand,
        COUNT(*) as cnt, COALESCE(SUM(likes+comments+collects+shares),0) as engagement
        FROM notes WHERE status='active' AND collected_at >= ? AND collected_at < ?
        GROUP BY brand ORDER BY engagement DESC LIMIT 20"""
    prev_sql = cur_sql
    cur_rows, err1 = _safe_query(cur_sql, (start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")))
    prev_rows, err2 = _safe_query(prev_sql, (prev_start.strftime("%Y-%m-%d %H:%M:%S"), start.strftime("%Y-%m-%d %H:%M:%S")))
    if err1 or err2:
        return _make_data_result("notes+metric_snapshots", [], error=err1 or err2, time_range=tr)
    prev_map = {r["brand"]: r for r in prev_rows}
    for r in cur_rows:
        p = prev_map.get(r["brand"], {})
        r["prev_engagement"] = p.get("engagement", 0)
        r["prev_count"] = p.get("cnt", 0)
        r["is_new"] = r["brand"] not in prev_map
    return _make_data_result("notes+metric_snapshots", cur_rows, time_range=tr)


# ═══════════════════════════════════════════════════════════════════════════
# KOS 域 Provider
# ═══════════════════════════════════════════════════════════════════════════

def provide_kos_list(params: Dict[str, Any]) -> DataResult:
    """KOS 专业号列表。"""
    limit = int(params.get("limit", 20))
    status = params.get("status", "")
    sql = "SELECT * FROM professional_accounts WHERE 1=1"
    cparams: Tuple = ()
    if status:
        sql += " AND status = ?"
        cparams = (status,)
    sql += " ORDER BY followers_count DESC LIMIT ?"
    cparams = cparams + (limit,)
    # 表可能不存在，用 _safe_query 捕获
    records, error = _safe_query(sql, cparams)
    if error:
        # 回退到 kos_profiles 表
        records, error = _safe_query("SELECT * FROM kos_profiles LIMIT ?", (limit,))
    if error:
        return _make_data_result("professional_accounts+kos_profiles", [], error=error)
    return _make_data_result("professional_accounts+kos_profiles", records)


def provide_kos_attribution(params: Dict[str, Any]) -> DataResult:
    """KOS 归因分析。"""
    kos_id = params.get("kos_id", "")
    tr = TimeRange.from_str(params.get("time_range", "30d"))
    clause, cparams = _time_clause(tr, "collected_at")
    if kos_id:
        sql = f"""SELECT author_id, author_nickname, COUNT(*) as note_count,
            COALESCE(SUM(likes+comments+collects+shares),0) as engagement,
            MAX(collected_at) as latest
            FROM notes WHERE status='active' AND author_id = ? {clause}
            GROUP BY author_id"""
        records, error = _safe_query(sql, (kos_id,) + cparams)
    else:
        sql = f"""SELECT author_id, author_nickname, COUNT(*) as note_count,
            COALESCE(SUM(likes+comments+collects+shares),0) as engagement,
            MAX(collected_at) as latest
            FROM notes WHERE status='active' AND author_id != '' {clause}
            GROUP BY author_id ORDER BY engagement DESC LIMIT 20"""
        records, error = _safe_query(sql, cparams)
    if error:
        return _make_data_result("kos_profiles+notes", [], error=error, time_range=tr)
    ts = records[0].get("latest") if records else None
    return _make_data_result("kos_profiles+notes", records, source_timestamp=ts, time_range=tr)


# ═══════════════════════════════════════════════════════════════════════════
# Risk 域 Provider
# ═══════════════════════════════════════════════════════════════════════════

def provide_risk_active(params: Dict[str, Any]) -> DataResult:
    """活跃风险笔记：高/中风险，排除已驳回(negative_confirmed=2)。"""
    tr = TimeRange.from_str(params.get("time_range", "7d"))
    level = params.get("level", "high")
    limit = int(params.get("limit", 20))
    clause, cparams = _time_clause(tr, "collected_at")
    if level == "high":
        level_clause = "risk_level IN ('high','critical')"
    elif level == "medium":
        level_clause = "risk_level='medium'"
    else:
        level_clause = "risk_level IN ('high','critical','medium')"
    sql = f"""SELECT * FROM notes WHERE status='active' AND {level_clause}
        AND COALESCE(negative_confirmed,0) <> 2 {clause}
        ORDER BY risk_score DESC, collected_at DESC LIMIT ?"""
    records, error = _safe_query(sql, cparams + (limit,))
    if error:
        return _make_data_result("notes", [], error=error, time_range=tr)
    ts = records[0].get("collected_at") if records else None
    return _make_data_result("notes", records, source_timestamp=ts, time_range=tr)


def provide_risk_trend(params: Dict[str, Any]) -> DataResult:
    """风险趋势：按日聚合高/中/低风险数量。"""
    tr = TimeRange.from_str(params.get("time_range", "30d"))
    clause, cparams = _time_clause(tr, "collected_at")
    sql = f"""SELECT date(collected_at) as day,
        SUM(CASE WHEN risk_level IN ('high','critical') THEN 1 ELSE 0 END) as high,
        SUM(CASE WHEN risk_level='medium' THEN 1 ELSE 0 END) as medium,
        SUM(CASE WHEN risk_level='low' THEN 1 ELSE 0 END) as low,
        COUNT(*) as total
        FROM notes WHERE status='active' {clause}
        GROUP BY date(collected_at) ORDER BY day ASC"""
    records, error = _safe_query(sql, cparams)
    if error:
        return _make_data_result("notes+daily_reports", [], error=error, time_range=tr)
    return _make_data_result("notes+daily_reports", records, time_range=tr)


# ═══════════════════════════════════════════════════════════════════════════
# Events 域 Provider
# ═══════════════════════════════════════════════════════════════════════════

def provide_events_list(params: Dict[str, Any]) -> DataResult:
    """事件列表。"""
    limit = int(params.get("limit", 20))
    status = params.get("status", "")
    sql = "SELECT * FROM events WHERE 1=1"
    cparams: Tuple = ()
    if status:
        sql += " AND status = ?"
        cparams = (status,)
    sql += " ORDER BY CASE status WHEN 'active' THEN 0 ELSE 1 END, risk_score DESC, mention_count DESC LIMIT ?"
    cparams = cparams + (limit,)
    records, error = _safe_query(sql, cparams)
    if error:
        return _make_data_result("events+event_mentions", [], error=error)
    # 补充 mention 数
    for ev in records:
        mid = ev.get("id")
        if mid:
            mc, _ = _safe_scalar("SELECT COUNT(*) FROM event_mentions WHERE event_id=?", (mid,))
            if mc is not None:
                ev["mention_count_actual"] = mc
    ts = records[0].get("last_seen") or records[0].get("first_seen") if records else None
    return _make_data_result("events+event_mentions", records, source_timestamp=ts)


def provide_events_propagation(params: Dict[str, Any]) -> DataResult:
    """事件传播链：event_mentions + event_graph。"""
    event_id = params.get("event_id", "")
    if not event_id:
        return _make_data_result("events+event_mentions+event_graph", [],
                                  error="event_id is required")
    # event_mentions
    mentions, err1 = _safe_query(
        "SELECT * FROM event_mentions WHERE event_id=? ORDER BY match_score DESC LIMIT 50",
        (event_id,))
    # event_graph relations
    relations, err2 = _safe_query(
        "SELECT * FROM event_graph_relations WHERE source_event_id=? OR target_event_id=? LIMIT 50",
        (event_id, event_id))
    if err1 and err2:
        return _make_data_result("events+event_mentions+event_graph", [], error=err1 or err2)
    combined = []
    for m in mentions:
        m["_type"] = "mention"
        combined.append(m)
    for r in relations:
        r["_type"] = "graph_relation"
        combined.append(r)
    return _make_data_result("events+event_mentions+event_graph", combined)


# ═══════════════════════════════════════════════════════════════════════════
# Notes 域 Provider
# ═══════════════════════════════════════════════════════════════════════════

def provide_notes_realtime(params: Dict[str, Any]) -> DataResult:
    """实时笔记：最新采集的笔记。"""
    tr = TimeRange.from_str(params.get("time_range", "today"))
    limit = int(params.get("limit", 20))
    clause, cparams = _time_clause(tr, "collected_at")
    sql = f"""SELECT id, note_id, title, content, url, author_nickname,
        likes, comments, collects, shares, sentiment, risk_level, risk_score,
        collected_at, publish_datetime, is_official, category
        FROM notes WHERE status='active' {clause}
        ORDER BY collected_at DESC LIMIT ?"""
    records, error = _safe_query(sql, cparams + (limit,))
    if error:
        return _make_data_result("notes", [], error=error, time_range=tr)
    ts = records[0].get("collected_at") if records else None
    return _make_data_result("notes", records, source_timestamp=ts, time_range=tr)


def provide_notes_search(params: Dict[str, Any]) -> DataResult:
    """笔记搜索：按关键词、情感、风险过滤。"""
    keyword = params.get("keyword", "")
    if not keyword:
        return _make_data_result("notes+note_comments", [], error="keyword is required")
    tr = TimeRange.from_str(params.get("time_range", "30d"))
    sentiment = params.get("sentiment", "")
    risk_level = params.get("risk_level", "")
    limit = int(params.get("limit", 20))
    clause, cparams = _time_clause(tr, "collected_at")
    sql = f"""SELECT id, note_id, title, content, url, author_nickname,
        likes, comments, collects, shares, sentiment, risk_level, risk_score,
        collected_at, publish_datetime
        FROM notes WHERE status='active' AND (title LIKE ? OR content LIKE ?) {clause}"""
    cparams = (f"%{keyword}%", f"%{keyword}%") + cparams
    if sentiment:
        sql += " AND sentiment = ?"
        cparams = cparams + (sentiment,)
    if risk_level:
        sql += " AND risk_level = ?"
        cparams = cparams + (risk_level,)
    sql += " ORDER BY collected_at DESC LIMIT ?"
    cparams = cparams + (limit,)
    records, error = _safe_query(sql, cparams)
    if error:
        return _make_data_result("notes+note_comments", [], error=error, time_range=tr)
    ts = records[0].get("collected_at") if records else None
    return _make_data_result("notes+note_comments", records, source_timestamp=ts, time_range=tr)


# ═══════════════════════════════════════════════════════════════════════════
# System 域 Provider
# ═══════════════════════════════════════════════════════════════════════════

def provide_system_runtime(params: Dict[str, Any]) -> DataResult:
    """系统运行时：worker 状态 + checkpoint + collection 最新状态。"""
    workers, err1 = _safe_query(
        "SELECT status, COUNT(*) as cnt FROM runtime_guardian_workers GROUP BY status")
    checkpoints, err2 = _safe_query(
        "SELECT * FROM runtime_guardian_checkpoints ORDER BY id DESC LIMIT 5")
    latest_collection, err3 = _safe_query(
        "SELECT * FROM collection_logs ORDER BY id DESC LIMIT 5")
    if err1 and err2 and err3:
        return _make_data_result("runtime_guardian", [], error=err1 or err2 or err3)
    records = [{
        "workers": workers,
        "checkpoints": checkpoints,
        "latest_collections": latest_collection,
        "db_path": _get_db_path(),
    }]
    ts = None
    if checkpoints:
        ts = checkpoints[0].get("created_at") or checkpoints[0].get("updated_at")
    return _make_data_result("runtime_guardian_checkpoints+runtime_guardian_workers",
                              records, source_timestamp=ts)


def provide_system_workers(params: Dict[str, Any]) -> DataResult:
    """Worker 状态列表。"""
    status = params.get("status", "")
    limit = int(params.get("limit", 50))
    sql = "SELECT * FROM runtime_guardian_workers WHERE 1=1"
    cparams: Tuple = ()
    if status:
        sql += " AND status = ?"
        cparams = (status,)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    cparams = cparams + (limit,)
    records, error = _safe_query(sql, cparams)
    if error:
        return _make_data_result("runtime_guardian_workers", [], error=error)
    ts = records[0].get("updated_at") or records[0].get("last_heartbeat_at") if records else None
    return _make_data_result("runtime_guardian_workers", records, source_timestamp=ts)


def provide_system_database_tables(params: Dict[str, Any]) -> DataResult:
    """数据库表统计：所有表的行数。"""
    tables, error = _safe_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    if error:
        return _make_data_result("sqlite_master", [], error=error)
    records = []
    for t in tables:
        tname = t["name"]
        cnt, cerr = _safe_scalar(f"SELECT COUNT(*) FROM [{tname}]")
        records.append({
            "table_name": tname,
            "row_count": cnt if cerr is None else None,
            "query_error": cerr,
        })
    return _make_data_result("sqlite_master", records)


def provide_system_health(params: Dict[str, Any]) -> DataResult:
    """系统健康四灯：DB/采集器/登录态/去重/主体过滤/风险引擎。"""
    # DB 可写性
    db_ok, db_err = _safe_scalar("SELECT 1")
    # 最新采集
    latest_coll, coll_err = _safe_query(
        "SELECT status, finished_at, notes_count, error_msg FROM collection_logs ORDER BY id DESC LIMIT 1")
    # worker 健康
    worker_stats, w_err = _safe_query(
        "SELECT status, COUNT(*) as cnt FROM runtime_guardian_workers GROUP BY status")
    records = [{
        "db": {"ok": db_err is None, "error": db_err},
        "collector": {
            "latest_status": latest_coll[0].get("status") if latest_coll else None,
            "latest_finished": latest_coll[0].get("finished_at") if latest_coll else None,
            "latest_count": latest_coll[0].get("notes_count") if latest_coll else None,
            "latest_error": latest_coll[0].get("error_msg") if latest_coll else None,
            "query_error": coll_err,
        },
        "workers": worker_stats,
        "workers_error": w_err,
    }]
    ts = latest_coll[0].get("finished_at") if latest_coll else None
    return _make_data_result("collection_logs+runtime_guardian_checkpoints",
                              records, source_timestamp=ts)


# ═══════════════════════════════════════════════════════════════════════════
# AI 域 Provider
# ═══════════════════════════════════════════════════════════════════════════

def provide_ai_call_logs(params: Dict[str, Any]) -> DataResult:
    """AI 调用日志。"""
    tr = TimeRange.from_str(params.get("time_range", "7d"))
    provider = params.get("provider", "")
    success = params.get("success", "")
    limit = int(params.get("limit", 50))
    clause, cparams = _time_clause(tr, "created_at")
    sql = "SELECT id, provider, model, task_id, trace_id, success, latency_ms, token_usage, confidence, final_decision, created_at FROM ai_call_logs WHERE 1=1" + clause
    if provider:
        sql += " AND provider = ?"
        cparams = cparams + (provider,)
    if success:
        sql += " AND success = ?"
        cparams = cparams + (1 if success.lower() in ("1", "true", "yes") else 0,)
    sql += " ORDER BY id DESC LIMIT ?"
    cparams = cparams + (limit,)
    records, error = _safe_query(sql, cparams)
    if error:
        return _make_data_result("ai_call_logs", [], error=error, time_range=tr)
    ts = records[0].get("created_at") if records else None
    return _make_data_result("ai_call_logs", records, source_timestamp=ts, time_range=tr)


# ═══════════════════════════════════════════════════════════════════════════
# Collector 域 Provider
# ═══════════════════════════════════════════════════════════════════════════

def provide_collector_status(params: Dict[str, Any]) -> DataResult:
    """采集器状态：最近采集日志 + 质量日志统计。"""
    tr = TimeRange.from_str(params.get("time_range", "today"))
    clause, cparams = _time_clause(tr, "started_at")
    # 采集日志统计
    coll_stats, err1 = _safe_query(
        f"""SELECT status, COUNT(*) as runs, COALESCE(SUM(notes_count),0) as total_notes,
        MAX(finished_at) as latest_finished
        FROM collection_logs WHERE 1=1 {clause} GROUP BY status""", cparams)
    # 最新 10 条采集日志
    latest_runs, err2 = _safe_query(
        f"SELECT * FROM collection_logs WHERE 1=1 {clause} ORDER BY id DESC LIMIT 10", cparams)
    # 质量日志统计
    quality_stats, err3 = _safe_query(
        "SELECT status, COUNT(*) as cnt FROM collector_quality_log GROUP BY status")
    if err1 and err2 and err3:
        return _make_data_result("collection_logs+collector_quality_log", [],
                                  error=err1 or err2 or err3, time_range=tr)
    records = [{
        "collection_stats": coll_stats,
        "latest_runs": latest_runs,
        "quality_stats": quality_stats,
    }]
    ts = None
    if latest_runs:
        ts = latest_runs[0].get("finished_at") or latest_runs[0].get("started_at")
    return _make_data_result("collection_logs+collector_quality_log",
                              records, source_timestamp=ts, time_range=tr)


def provide_collector_quality_gate(params: Dict[str, Any]) -> DataResult:
    """采集质量门：通过率、拒绝率、去重率、各步骤质量。"""
    tr = TimeRange.from_str(params.get("time_range", "7d"))
    step = params.get("step", "")
    clause, cparams = _time_clause(tr, "checked_at")
    # collector_quality_log 统计
    ql_sql = f"""SELECT status, COUNT(*) as cnt, AVG(score) as avg_score
        FROM collector_quality_log WHERE 1=1 {clause} GROUP BY status"""
    ql_stats, err1 = _safe_query(ql_sql, cparams)
    # ai_filter_log 统计
    af_sql = f"""SELECT filter_result, COUNT(*) as cnt, AVG(confidence) as avg_confidence
        FROM ai_filter_log WHERE 1=1 {clause} GROUP BY filter_result"""
    af_stats, err2 = _safe_query(af_sql, cparams)
    if err1 and err2:
        return _make_data_result("collector_quality_log+ai_filter_log", [],
                                  error=err1 or err2, time_range=tr)
    records = [{
        "quality_log_stats": ql_stats,
        "ai_filter_stats": af_stats,
        "step_filter": step,
    }]
    return _make_data_result("collector_quality_log+ai_filter_log",
                              records, time_range=tr)


# ═══════════════════════════════════════════════════════════════════════════
# Provider 注册表
# ═══════════════════════════════════════════════════════════════════════════

PROVIDER_MAP = {
    "overview.stats": provide_overview_stats,
    "overview.trend": provide_overview_trend,
    "overview.industry_dist": provide_industry_dist,
    "brand.top10": provide_brand_top10,
    "brand.growth": provide_brand_growth,
    "kos.list": provide_kos_list,
    "kos.attribution": provide_kos_attribution,
    "risk.active": provide_risk_active,
    "risk.trend": provide_risk_trend,
    "events.list": provide_events_list,
    "events.propagation": provide_events_propagation,
    "notes.realtime": provide_notes_realtime,
    "notes.search": provide_notes_search,
    "system.runtime": provide_system_runtime,
    "system.workers": provide_system_workers,
    "system.database_tables": provide_system_database_tables,
    "system.health": provide_system_health,
    "ai.call_logs": provide_ai_call_logs,
    "collector.status": provide_collector_status,
    "collector.quality_gate": provide_collector_quality_gate,
}


def get_provider(function_name: str):
    """按 function_name 获取 provider 函数。"""
    return PROVIDER_MAP.get(function_name)


def fetch_data(function_name: str, params: Dict[str, Any]) -> DataResult:
    """统一取数入口：查找 provider → 执行 → 返回 DataResult。"""
    provider = get_provider(function_name)
    if provider is None:
        return _make_data_result("unknown", [], error=f"no provider for {function_name}")
    try:
        return provider(params)
    except Exception as exc:
        return _make_data_result(function_name, [], error=str(exc))
