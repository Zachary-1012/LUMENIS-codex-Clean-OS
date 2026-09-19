# -*- coding: utf-8 -*-

"""LUMENIS Shared Evidence Store（统一证据存储层）



归属：LUMENIS Shared Capability / Evidence；跨仓学习输出仅通过 versioned Contract / Artifact。

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
import re

import sqlite3

import hashlib

from datetime import datetime

from pathlib import Path

from typing import Any, Optional



# 数据库路径（与 database.py 一致，支持 ZBC_DB_PATH 覆盖）

import os

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = os.environ.get("ZBC_DB_PATH", str(PROJECT_ROOT / "data" / "monitor.db"))



EVIDENCE_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS app_evidence_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL DEFAULT 'xhs_app',
    capture_mode TEXT NOT NULL DEFAULT 'screenshot',
    captured_at TEXT,
    topic TEXT,
    metric_name TEXT NOT NULL,
    metric_value TEXT NOT NULL,
    evidence_hash TEXT,
    evidence_path TEXT,
    parse_confidence REAL DEFAULT 1.0,
    verified_by TEXT,
    verified_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_app_evidence_topic ON app_evidence_records(topic);
CREATE INDEX IF NOT EXISTS idx_app_evidence_status ON app_evidence_records(status);
CREATE INDEX IF NOT EXISTS idx_app_evidence_hash ON app_evidence_records(evidence_hash);
"""


def init_evidence_store(db_path: str = None) -> None:
    """Create the canonical Evidence table/indexes and apply additive chain fields."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path, timeout=10)
    try:
        conn.executescript(EVIDENCE_TABLE_SCHEMA)
        conn.commit()
    finally:
        conn.close()
    migrate_evidence_chain_fields(path)


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

    """生成 Evidence 内容哈希（16字符截断，兼容现有记录），用于去重和溯源。"""

    content = json.dumps(fields, sort_keys=True, ensure_ascii=False, default=str)

    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]





def compute_full_content_hash(raw_content: str) -> str:

    """计算原始内容完整 SHA256 哈希（64字符）。



    Phase 8 新增：与 evidence_chain.compute_content_hash 对齐，

    用于 content_hash 字段和证据完整性校验。不影响现有 evidence_hash（16字符截断）。

    """

    if raw_content is None:

        raw_content = ""

    return hashlib.sha256(str(raw_content).encode("utf-8")).hexdigest()





# Phase 8 新增字段（向后兼容，全部可空/有默认值，通过 ADD COLUMN 迁移）

EVIDENCE_CHAIN_NEW_COLUMNS = [

    ("content_hash", "TEXT", "''"),           # 完整 SHA256（64字符），原始内容哈希

    ("subject_scope", "TEXT", "'CTH'"),       # 主体范围（广州太古汇=CTH）

    ("collection_metadata", "TEXT", "'{}'"),  # 采集元数据 JSON

    ("provider", "TEXT", "'rule'"),           # 采集提供者/适配器

    ("authenticity_score", "REAL", "1.0"),    # 真实性评分 0-1

    ("publish_datetime", "TEXT", "NULL"),     # 内容真实发布时间（可空）


    ("domain_id", "TEXT", "NULL"),            # 业务域ID（ZBMP/CTH/SYSTEM）

    ("product_id", "TEXT", "NULL"),           # 产品ID（双域隔离）

]





def migrate_evidence_chain_fields(db_path: str = None) -> dict:

    """Phase 8 迁移：为 app_evidence_records 表添加证据链新字段。



    使用 ADD COLUMN（SQLite 非破坏性操作），新字段全部可空/有默认值，

    不修改、不删除、不覆盖现有任何数据。



    Returns:

        {"added": [...], "skipped": [...], "total_existing_columns": int}

    """

    path = db_path or DB_PATH

    conn = sqlite3.connect(path, timeout=10)

    try:

        existing = {row[1] for row in conn.execute("PRAGMA table_info(app_evidence_records)").fetchall()}

        added, skipped = [], []

        for col_name, col_type, default in EVIDENCE_CHAIN_NEW_COLUMNS:

            if col_name in existing:

                skipped.append(col_name)

                continue

            default_clause = f" DEFAULT {default}" if default != "NULL" else ""

            conn.execute(f"ALTER TABLE app_evidence_records ADD COLUMN {col_name} {col_type}{default_clause}")

            added.append(col_name)

        conn.commit()

        return {

            "added": added,

            "skipped": skipped,

            "total_existing_columns": len(existing) + len(added),

            "note": "ADD COLUMN 非破坏性迁移，现有数据未被修改",

        }

    finally:

        conn.close()





def _get_conn() -> sqlite3.Connection:

    conn = sqlite3.connect(DB_PATH, timeout=10)

    conn.row_factory = sqlite3.Row

    return conn





def _safe_identifier(name: str) -> str:
    """校验SQL标识符（表名/列名）仅含安全字符，防止标识符注入。"""
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name or ''):
        raise ValueError(f"非法SQL标识符: {name!r}")
    return name


def _get_table_columns(conn: sqlite3.Connection, table: str = "app_evidence_records") -> set:

    """获取表实际存在的列名集合（向后兼容：只插入存在的列，新字段未迁移时自动跳过）。"""

    try:

        rows = conn.execute(f"PRAGMA table_info({_safe_identifier(table)})").fetchall()

        return {row[1] for row in rows}

    except Exception:

        return set()





def _record_write_failure(fields: dict, error: Exception) -> None:

    """Evidence 写入失败时：写 audit_logs + DLQ（不中断业务，失败不可见=违反）。

    P1 复杂度治理：evidence_write_failed 必须记录+标记降级+进入健康摘要+可补写重放。
    """

    import uuid as _uuid

    now = _now()

    dlq_id = f"evfail-{_uuid.uuid4().hex[:12]}"

    detail_json = _json_dumps({

        "error_type": type(error).__name__,

        "error_message": str(error)[:500],

        "asset_id": fields.get("asset_id", ""),

        "feature_id": fields.get("feature_id", ""),

        "source": fields.get("source", ""),

        "level": fields.get("level", ""),

        "result": fields.get("result", ""),

        "fields_keys": list(fields.keys()),

        "timestamp": now,

    })

    # 1) 写入 v4_audit_logs（审计中心可查）

    try:

        audit_conn = sqlite3.connect(DB_PATH, timeout=5)

        audit_conn.execute(

            "INSERT INTO v4_audit_logs (user_id, username, action, resource, resource_id, detail, ip, created_at) "

            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",

            (0, "system", "evidence_write_failed", "app_evidence_records",

             fields.get("asset_id", "") or dlq_id, detail_json, "127.0.0.1", now),

        )

        audit_conn.commit()

        audit_conn.close()

    except Exception:

        pass  # audit 写入失败不阻塞

    # 2) 写入 runtime_guardian_dlq（可补写重放）

    try:

        dlq_conn = sqlite3.connect(DB_PATH, timeout=5)

        dlq_conn.execute(

            "INSERT INTO runtime_guardian_dlq "

            "(dlq_id, worker_id, run_id, task_type, payload, error, error_type, "

            " attempts, max_attempts, status, created_at, updated_at, domain_id, product_id) "

            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",

            (dlq_id, "evidence_store", "record_evidence", "evidence_write",

             _json_dumps(fields), str(error)[:500], type(error).__name__,

             0, 3, "PENDING", now, now,

             fields.get("subject_scope", "SYSTEM"), fields.get("product", "ZBC")),

        )

        dlq_conn.commit()

        dlq_conn.close()

    except Exception:

        pass  # DLQ 写入失败不阻塞





def replay_failed_evidence(limit: int = 50) -> dict:

    """重放最近失败的 evidence 写入（从 runtime_guardian_dlq 读取并重试）。

    Returns:
        {"replayed": N, "succeeded": N, "failed": N, "remaining": N}
    """

    now = _now()

    conn = sqlite3.connect(DB_PATH, timeout=10)

    conn.row_factory = sqlite3.Row

    try:

        rows = conn.execute(

            "SELECT id, dlq_id, payload, attempts, max_attempts FROM runtime_guardian_dlq "

            "WHERE task_type='evidence_write' AND status IN ('PENDING','FAILED') "

            "ORDER BY id ASC LIMIT ?",

            (limit,),

        ).fetchall()

    except Exception as e:

        return {"replayed": 0, "succeeded": 0, "failed": 0, "remaining": 0, "error": str(e)}

    finally:

        conn.close()



    succeeded = 0

    failed = 0

    for row in rows:

        try:

            fields = json.loads(row["payload"])

        except Exception:

            continue

        attempts = row["attempts"] + 1

        try:

            # 重试写入

            retry_conn = sqlite3.connect(DB_PATH, timeout=10)

            existing_cols = _get_table_columns(retry_conn)

            if existing_cols:

                fields = {k: v for k, v in fields.items() if k in existing_cols}

            cols = ", ".join(fields.keys())

            placeholders = ", ".join(["?"] * len(fields))

            values = list(fields.values())

            retry_conn.execute(

                f"INSERT INTO app_evidence_records ({cols}) VALUES ({placeholders})",

                values,

            )

            retry_conn.commit()

            retry_conn.close()

            succeeded += 1

            # 标记 DLQ 为 RESOLVED

            _update_dlq_status(row["id"], "RESOLVED", attempts, now)

        except Exception as e:

            failed += 1

            new_status = "FAILED" if attempts >= row["max_attempts"] else "PENDING"

            _update_dlq_status(row["id"], new_status, attempts, now, error=str(e)[:300])



    # 统计剩余

    try:

        count_conn = sqlite3.connect(DB_PATH, timeout=5)

        remaining = count_conn.execute(

            "SELECT COUNT(*) FROM runtime_guardian_dlq "

            "WHERE task_type='evidence_write' AND status IN ('PENDING','FAILED')"

        ).fetchone()[0]

        count_conn.close()

    except Exception:

        remaining = -1



    return {

        "replayed": len(rows),

        "succeeded": succeeded,

        "failed": failed,

        "remaining": remaining,

    }





def _update_dlq_status(row_id: int, status: str, attempts: int, now: str, error: str = "") -> None:

    try:

        conn = sqlite3.connect(DB_PATH, timeout=5)

        if error:

            conn.execute(

                "UPDATE runtime_guardian_dlq SET status=?, attempts=?, updated_at=?, last_attempt_at=?, error=? WHERE id=?",

                (status, attempts, now, now, error, row_id),

            )

        else:

            conn.execute(

                "UPDATE runtime_guardian_dlq SET status=?, attempts=?, updated_at=?, last_attempt_at=?, resolved_at=? WHERE id=?",

                (status, attempts, now, now, now, row_id),

            )

        conn.commit()

        conn.close()

    except Exception:

        pass





def get_evidence_write_failure_count(hours: int = 24) -> int:

    """获取最近 N 小时 evidence 写入失败计数（用于健康摘要）。"""

    try:

        conn = sqlite3.connect(DB_PATH, timeout=5)

        count = conn.execute(

            "SELECT COUNT(*) FROM v4_audit_logs "

            "WHERE action='evidence_write_failed' "

            "AND created_at >= datetime('now', ?, 'localtime')",

            (f"-{hours} hours",),

        ).fetchone()[0]

        conn.close()

        return count

    except Exception:

        return 0





def record_evidence(

    *,

    source: str = "lumenis",

    project: str = "LUMENIS",

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

    # Phase 8 证据链新字段（全部可选，向后兼容）

    raw_content: str = "",

    subject_scope: str = "CTH",

    collection_metadata: Any = None,

    provider: str = "rule",

    authenticity_score: float = 1.0,

    publish_datetime: str = "",

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

        # 注意：started_at/created_at 等时间戳是元数据，不参与证据内容哈希——
    # 相同业务内容必须得到相同哈希（幂等去重），跨秒写入也不能变。
    "account": account,

    }

    ev_hash = _evidence_hash(hash_fields)



    # Phase 8: 完整内容哈希（如果提供了 raw_content）

    full_content_hash = compute_full_content_hash(raw_content) if raw_content else ""



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

        # Phase 8 证据链新字段

        "content_hash": full_content_hash,

        "subject_scope": subject_scope,

        "collection_metadata": _json_dumps(collection_metadata) if collection_metadata else "{}",

        "provider": provider,

        "authenticity_score": authenticity_score,

        "publish_datetime": publish_datetime or None,

    }

    # 过滤掉 None 值（空字符串保留，因为是有意义的默认值）

    fields = {k: v for k, v in fields.items() if v is not None}



    try:

        conn = _get_conn()

        # 向后兼容：只插入表中实际存在的列（新字段未迁移时自动跳过，不报错）

        existing_cols = _get_table_columns(conn)

        if existing_cols:

            fields = {k: v for k, v in fields.items() if k in existing_cols}



        cols = ", ".join(fields.keys())

        placeholders = ", ".join(["?"] * len(fields))

        values = list(fields.values())



        cursor = conn.execute(

            f"INSERT INTO app_evidence_records ({cols}) VALUES ({placeholders})",

            values,

        )

        conn.commit()

        return cursor.lastrowid

    except Exception as e:

        # P1 非静默健康：写入失败必须记录+降级+可重放，不中断业务

        try:

            conn.rollback()

        except Exception:

            pass

        _record_write_failure(fields, e)

        return -1  # 失败标记：调用方可检测

    finally:

        try:

            conn.close()

        except Exception:

            pass





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

    feature_id: str = "XHS_COLLECT",

    provider: str = "rule",

    source: str = "collector",

    collected_at: str = "",

    collection_metadata=None,

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

    # Reuse the existing Evidence metadata contract. Keep only provenance and
    # operational state; raw provider records, credentials and response bodies
    # never enter this record.
    safe_metadata = {
        "provider": str(provider or "rule")[:100],
        "source": str(source or "collector")[:180],
        "collected_at": str(collected_at or "")[:40],
    }
    if isinstance(collection_metadata, dict):
        allowed_metadata = {
            "healthcheck_scope", "session_state", "endpoint_configured",
            "error_type", "source_platform",
        }
        for key in allowed_metadata:
            value = collection_metadata.get(key)
            if isinstance(value, (str, int, float, bool)):
                safe_metadata[key] = value

    try:
        from lumenis.system.collector.adapters.safe_collection import sanitize

        safe_metadata = sanitize(safe_metadata)
    except Exception:
        # The provenance allowlist above remains safe if the optional sanitizer
        # cannot be imported during application bootstrap.
        pass



    return record_evidence(

        source="collector",

        project="LUMENIS",

        product="CTH",

        feature_id=feature_id or "XHS_COLLECT",

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
        provider=provider or "rule",
        collection_metadata=safe_metadata,

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

        project="LUMENIS",

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

    "init_evidence_store",
    "record_evidence",

    "record_collection_evidence",

    "record_health_evidence",

    "query_evidence",

    "get_stats",

    "compute_full_content_hash",

    "migrate_evidence_chain_fields",

    "EVIDENCE_CHAIN_NEW_COLUMNS",

    "LEVELS",

    "RESULTS",

    "ENVS",

]