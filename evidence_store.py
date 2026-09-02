# -*- coding: utf-8 -*-
"""Zachary OS AI · Evidence Store（统一证据存储层）

Contract：OSAI 研究侧 → ZBC 生产侧。
对齐 EVIDENCE-PATTERNS.md：每个"完成/DONE"都有可回放证据，禁止"写完=完成"。

表：app_evidence_records（43字段，16原有指标证据 + 27新增通用证据）

核心能力：
  1. record_evidence(**kwargs) — 通用 Evidence 写入
  2. record_collection_evidence(...) — 采集任务 Evidence 便捷方法
  3. record_health_evidence(...) — 健康检查 Evidence 便捷方法
  4. query_evidence(filters, limit, offset) — 结构化查询
  5. get_stats() — 按 result/level/account 统计

设计原则：
  - 失败必留证据链（异常时 result=FAIL，actual 记录异常详情）
  - 事实 vs 声明分离（AI 产出单独标 model/confidence，不与系统事实混存）
  - 采集异常禁止以 0 条充当结果（必须落真实状态证据）
  - 只读查询，不修改业务数据
"""
from __future__ import annotations
import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# 数据库路径（与 database.py 一致，支持 ZBC_DB_PATH 覆盖）
import os
DB_PATH = os.environ.get("ZBC_DB_PATH", str(Path(__file__).parent / "data" / "monitor.db"))

# Evidence 级别常量（L0-L10，对齐 EVIDENCE-PATTERNS.md）
LEVELS = ["L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10"]

# Evidence 结果常量
RESULTS = ["PASS", "FAIL", "ENV", "GAP", "REGRESSION"]

# 环境常量
ENVS = ["local", "staging", "prod"]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _json_dumps(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return str(obj)


def _evidence_hash(fields: dict) -> str:
    """生成 Evidence 内容哈希，用于去重和溯源。"""
    content = json.dumps(fields, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def record_evidence(
    *,
    source: str = "zbc",
    project: str = "ZBC",
    product: str = "CTH",
    feature_id: str = "",
    asset_id: str = "",
    commit_sha: str = "",
    version: str = "",
    env: str = "prod",
    level: str = "L4",
    test_name: str = "",
    result: str = "PASS",
    started_at: str = "",
    finished_at: str = "",
    inputs: Any = None,
    outputs: Any = None,
    expected: str = "",
    actual: str = "",
    log_path: str = "",
    screenshot_path: str = "",
    trace_path: str = "",
    api_request: str = "",
    api_response: str = "",
    db_before: str = "",
    db_after: str = "",
    root_cause: str = "",
    resolution: str = "",
    account: str = "",
    duration_ms: int = 0,
    notes: str = "",
    metric_name: str = "",
    metric_value: str = "",
    topic: str = "",
    status: str = "verified",
) -> int:
    """写入一条通用 Evidence 记录。

    Returns:
      新记录的 id
    """
    now = _now()
    if not started_at:
        started_at = now
    if not finished_at:
        finished_at = now

    # 兼容现有字段
    if not metric_name:
        metric_name = test_name or feature_id or "evidence"
    if not metric_value:
        metric_value = result

    # 生成哈希
    hash_fields = {
        "source": source, "project": project, "product": product,
        "feature_id": feature_id, "level": level, "result": result,
        "account": account, "started_at": started_at,
    }
    ev_hash = _evidence_hash(hash_fields)

    # 动态构造 INSERT（只插入非空/有意义的字段，避免列值不匹配）
    fields = {
        "source": source, "project": project, "product": product,
        "feature_id": feature_id, "asset_id": asset_id, "commit_sha": commit_sha,
        "version": version, "env": env, "level": level, "test_name": test_name,
        "result": result, "started_at": started_at, "finished_at": finished_at,
        "inputs_json": _json_dumps(inputs), "outputs_json": _json_dumps(outputs),
        "expected": expected, "actual": actual,
        "log_path": log_path, "screenshot_path": screenshot_path, "trace_path": trace_path,
        "api_request": api_request, "api_response": api_response,
        "db_before": db_before, "db_after": db_after,
        "root_cause": root_cause, "resolution": resolution,
        "account": account, "duration_ms": duration_ms,
        "metric_name": metric_name, "metric_value": metric_value,
        "topic": topic, "status": status, "notes": notes,
        "evidence_hash": ev_hash, "capture_mode": "automated", "captured_at": now,
        "created_at": now, "updated_at": now,
    }
    # 过滤掉 None 值（空字符串保留，因为是有意义的默认值）
    fields = {k: v for k, v in fields.items() if v is not None}
    cols = ", ".join(fields.keys())
    placeholders = ", ".join(["?"] * len(fields))
    values = list(fields.values())

    conn = _get_conn()
    try:
        cursor = conn.execute(
            f"INSERT INTO app_evidence_records ({cols}) VALUES ({placeholders})",
            values,
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def record_collection_evidence(
    *,
    account: str,
    platform: str = "xhs",
    notes_collected: int = 0,
    notes_filtered: int = 0,
    notes_inserted: int = 0,
    notes_updated: int = 0,
    duration_ms: int = 0,
    result: str = "PASS",
    error_type: str = "",
    error_message: str = "",
    session_state: str = "",
    keywords: list = None,
    started_at: str = "",
    version: str = "",
) -> int:
    """采集任务 Evidence 便捷方法。

    强制规则：
      - 采集异常时 result=FAIL，actual 记录异常类型和消息
      - 禁止以 0 条充当结果（即使 notes_collected=0，也要记录真实状态）
    """
    actual_parts = [
        f"collected={notes_collected}",
        f"filtered={notes_filtered}",
        f"inserted={notes_inserted}",
        f"updated={notes_updated}",
    ]
    if error_type:
        actual_parts.append(f"error_type={error_type}")
    if error_message:
        actual_parts.append(f"error={error_message[:200]}")
    if session_state:
        actual_parts.append(f"session={session_state}")

    return record_evidence(
        source="collector",
        project="ZBC",
        product="CTH",
        feature_id="XHS_COLLECT",
        level="L8",
        test_name=f"collection_{account}",
        result=result,
        started_at=started_at,
        inputs={"account": account, "platform": platform, "keywords": keywords or []},
        outputs={
            "notes_collected": notes_collected,
            "notes_filtered": notes_filtered,
            "notes_inserted": notes_inserted,
            "notes_updated": notes_updated,
        },
        actual="; ".join(actual_parts),
        account=account,
        duration_ms=duration_ms,
        version=version,
        notes=f"平台={platform}; 会话={session_state or 'unknown'}" if session_state else f"平台={platform}",
    )


def record_health_evidence(
    *,
    account: str,
    level: str = "L3",
    port: int = 0,
    port_alive: bool = False,
    cdp_ws_ok: bool = False,
    login_state: str = "",
    cookie_count: int = 0,
    result: str = "PASS",
    detail: str = "",
    started_at: str = "",
    version: str = "",
) -> int:
    """健康检查 Evidence 便捷方法。

    三层健康检查：L1端口存活 → L2 CDP控制面 → L3登录态有效
    """
    actual_parts = [
        f"port={port}",
        f"port_alive={port_alive}",
        f"cdp_ws_ok={cdp_ws_ok}",
        f"login_state={login_state or 'unknown'}",
        f"cookies={cookie_count}",
    ]
    if detail:
        actual_parts.append(f"detail={detail[:200]}")

    return record_evidence(
        source="health_monitor",
        project="ZBC",
        product="CTH",
        feature_id="RESIDENT_HEALTH",
        level=level,
        test_name=f"health_check_{account}",
        result=result,
        started_at=started_at,
        inputs={"account": account, "port": port},
        outputs={
            "port_alive": port_alive,
            "cdp_ws_ok": cdp_ws_ok,
            "login_state": login_state,
            "cookie_count": cookie_count,
        },
        actual="; ".join(actual_parts),
        account=account,
        version=version,
        notes=detail[:500] if detail else "",
    )


def query_evidence(
    *,
    source: str = "",
    project: str = "",
    product: str = "",
    feature_id: str = "",
    level: str = "",
    result: str = "",
    account: str = "",
    env: str = "",
    limit: int = 50,
    offset: int = 0,
    order_by: str = "created_at DESC",
) -> list[dict]:
    """结构化查询 Evidence 记录。"""
    conditions = []
    params = []
    if source:
        conditions.append("source = ?")
        params.append(source)
    if project:
        conditions.append("project = ?")
        params.append(project)
    if product:
        conditions.append("product = ?")
        params.append(product)
    if feature_id:
        conditions.append("feature_id = ?")
        params.append(feature_id)
    if level:
        conditions.append("level = ?")
        params.append(level)
    if result:
        conditions.append("result = ?")
        params.append(result)
    if account:
        conditions.append("account = ?")
        params.append(account)
    if env:
        conditions.append("env = ?")
        params.append(env)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"SELECT * FROM app_evidence_records{where} ORDER BY {order_by} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    conn = _get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_stats() -> dict:
    """Evidence 统计：按 result/level/account/source 分组。"""
    conn = _get_conn()
    try:
        stats = {"total": 0, "by_result": {}, "by_level": {}, "by_account": {}, "by_source": {}, "recent": []}

        stats["total"] = conn.execute("SELECT COUNT(*) FROM app_evidence_records").fetchone()[0]

        for row in conn.execute("SELECT result, COUNT(*) as cnt FROM app_evidence_records GROUP BY result"):
            stats["by_result"][row["result"]] = row["cnt"]

        for row in conn.execute("SELECT level, COUNT(*) as cnt FROM app_evidence_records GROUP BY level ORDER BY level"):
            stats["by_level"][row["level"]] = row["cnt"]

        for row in conn.execute("SELECT account, COUNT(*) as cnt FROM app_evidence_records WHERE account != '' GROUP BY account ORDER BY cnt DESC"):
            stats["by_account"][row["account"]] = row["cnt"]

        for row in conn.execute("SELECT source, COUNT(*) as cnt FROM app_evidence_records GROUP BY source ORDER BY cnt DESC"):
            stats["by_source"][row["source"]] = row["cnt"]

        recent = conn.execute(
            "SELECT id, source, feature_id, level, result, account, actual, created_at "
            "FROM app_evidence_records ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
        stats["recent"] = [dict(row) for row in recent]

        return stats
    finally:
        conn.close()


# 便捷导出
__all__ = [
    "record_evidence",
    "record_collection_evidence",
    "record_health_evidence",
    "query_evidence",
    "get_stats",
    "LEVELS",
    "RESULTS",
    "ENVS",
]
