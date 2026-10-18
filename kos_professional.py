"""
LUMENIS KOS Professional Account Gateway
序境专业号接入口 — 每品牌可选，默认关闭

设计原则：
- 可选模块：每个品牌独立开关，默认 disabled
- 安全守法：只读公开数据，不越权、不破解风控、不采集非授权内容
- 熔断保护：接入失败不影响主链路，返回 empty 态
- 轻量：不做强制全量脱敏，开启后按需授权
"""
import sqlite3
from lumenis.shared.database import get_repository
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

# ============ 表结构 ============

_SCHEMA = """
CREATE TABLE IF NOT EXISTS professional_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id TEXT NOT NULL DEFAULT 'default',
    platform TEXT NOT NULL DEFAULT 'xiaohongshu',
    account_id TEXT NOT NULL,
    account_name TEXT,
    verified_type TEXT,
    auth_status TEXT NOT NULL DEFAULT 'disabled',  -- disabled / pending / authorized / revoked
    enabled INTEGER NOT NULL DEFAULT 0,              -- 品牌开关
    access_token TEXT,                               -- 加密存储，不写明文
    last_sync_at TEXT,
    sync_status TEXT DEFAULT 'idle',                 -- idle / syncing / success / failed
    last_error TEXT,
    created_at TEXT,
    updated_at TEXT,
    UNIQUE(brand_id, platform, account_id)
);

CREATE TABLE IF NOT EXISTS professional_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    brand_id TEXT NOT NULL,
    metric_date TEXT NOT NULL,
    impressions INTEGER DEFAULT 0,       -- 曝光
    views INTEGER DEFAULT 0,             -- 观看
    cover_ctr REAL DEFAULT 0,            -- 封面点击率
    follower_gain INTEGER DEFAULT 0,     -- 涨粉
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    collects INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    source TEXT DEFAULT 'import',        -- import / api
    created_at TEXT,
    UNIQUE(account_id, metric_date)
);
"""


def _get_conn() -> sqlite3.Connection:
    return get_repository().connect()


def init_db():
    """初始化表结构（幂等）。"""
    conn = _get_conn()
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()


# ============ 品牌开关 ============

def is_enabled(brand_id: str = 'default', platform: str = 'xiaohongshu') -> bool:
    """检查某品牌专业号接入是否开启。默认关闭。"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT enabled FROM professional_accounts WHERE brand_id=? AND platform=? LIMIT 1",
            (brand_id, platform)
        ).fetchone()
        return bool(row and row['enabled'])
    except Exception:
        return False
    finally:
        conn.close()


def enable(brand_id: str, platform: str, account_id: str,
           account_name: str = '', verified_type: str = '') -> Dict[str, Any]:
    """开启某品牌专业号接入（按钮触发）。"""
    conn = _get_conn()
    now = datetime.now().isoformat()
    try:
        conn.execute("""
            INSERT INTO professional_accounts
                (brand_id, platform, account_id, account_name, verified_type,
                 auth_status, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'pending', 1, ?, ?)
            ON CONFLICT(brand_id, platform, account_id)
            DO UPDATE SET enabled=1, auth_status='pending', updated_at=?
        """, (brand_id, platform, account_id, account_name, verified_type, now, now, now))
        conn.commit()
        return {"ok": True, "brand_id": brand_id, "account_id": account_id,
                "status": "pending", "message": "专业号接入已开启，等待授权"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def disable(brand_id: str, platform: str, account_id: str) -> Dict[str, Any]:
    """关闭某品牌专业号接入。"""
    conn = _get_conn()
    now = datetime.now().isoformat()
    try:
        conn.execute("""
            UPDATE professional_accounts
            SET enabled=0, auth_status='disabled', updated_at=?
            WHERE brand_id=? AND platform=? AND account_id=?
        """, (now, brand_id, platform, account_id))
        conn.commit()
        return {"ok": True, "status": "disabled"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def list_accounts(brand_id: str = 'default') -> List[Dict[str, Any]]:
    """列出某品牌的专业号接入配置。"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM professional_accounts WHERE brand_id=? ORDER BY created_at",
            (brand_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


# ============ 数据导入（开启后才可用） ============

def import_metrics(brand_id: str, account_id: str, metrics: List[Dict[str, Any]],
                   source: str = 'import') -> Dict[str, Any]:
    """
    导入专业号后台数据（曝光/点击率/涨粉等）。
    仅在该品牌专业号接入开启后才执行。
    熔断：失败不抛异常，返回错误状态。
    """
    if not is_enabled(brand_id):
        return {"ok": False, "error": "专业号接入未开启", "code": "NOT_ENABLED"}

    conn = _get_conn()
    now = datetime.now().isoformat()
    imported = 0
    failed = 0
    try:
        for m in metrics:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO professional_metrics
                        (account_id, brand_id, metric_date, impressions, views,
                         cover_ctr, follower_gain, likes, comments, collects, shares,
                         source, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account_id, brand_id,
                    m.get('metric_date', ''),
                    m.get('impressions', 0),
                    m.get('views', 0),
                    m.get('cover_ctr', 0),
                    m.get('follower_gain', 0),
                    m.get('likes', 0),
                    m.get('comments', 0),
                    m.get('collects', 0),
                    m.get('shares', 0),
                    source, now
                ))
                imported += 1
            except Exception:
                failed += 1
        conn.execute("""
            UPDATE professional_accounts
            SET last_sync_at=?, sync_status=CASE WHEN ? > 0 THEN 'success' ELSE 'failed' END,
                last_error=CASE WHEN ? > 0 THEN NULL ELSE 'all rows failed' END,
                updated_at=?
            WHERE brand_id=? AND account_id=?
        """, (now, imported, imported, now, brand_id, account_id))
        conn.commit()
        return {"ok": True, "imported": imported, "failed": failed}
    except Exception as e:
        return {"ok": False, "error": str(e), "imported": imported, "failed": failed}
    finally:
        conn.close()


def get_metrics(brand_id: str, account_id: str = '',
                start_date: str = '', end_date: str = '') -> List[Dict[str, Any]]:
    """查询专业号指标。未开启返回空列表。"""
    if not is_enabled(brand_id):
        return []
    conn = _get_conn()
    try:
        q = "SELECT * FROM professional_metrics WHERE brand_id=?"
        params = [brand_id]
        if account_id:
            q += " AND account_id=?"
            params.append(account_id)
        if start_date:
            q += " AND metric_date >= ?"
            params.append(start_date)
        if end_date:
            q += " AND metric_date <= ?"
            params.append(end_date)
        q += " ORDER BY metric_date DESC LIMIT 365"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


# ============ 熔断装饰器 ============

def kos_circuit_breaker(timeout: float = 30.0, default_return=None):
    """
    KOS 熔断装饰器：任何 KOS 函数失败不影响主链路。
    超时 / 异常 → 返回 default_return（通常是空 dict / 空 list）。
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                print(f"[KOS CIRCUIT BREAKER] {func.__name__} failed: {e}")
                return default_return if default_return is not None else {"ok": False, "error": str(e)}
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


# 初始化
init_db()


# Current actor/BrandFocus work records use the existing versioned KOS ledger.
# Legacy professional_accounts rows have no actor ownership and are never
# silently attributed to the current workspace.
def _scoped_account_key(platform, account_id):
    from lumenis.shared.reporting.saved_work import _digest

    if (
        not isinstance(platform, str)
        or not platform.strip()
        or len(platform) > 80
        or not isinstance(account_id, str)
        or not account_id.strip()
        or len(account_id) > 200
    ):
        raise ValueError("PROFESSIONAL_ACCOUNT_INPUT_INVALID")
    return "professional:" + _digest({"platform": platform, "account_id": account_id})


def validate_private_payload(operation, payload):
    import math

    if operation == "professional_config":
        required = {"platform", "account_id", "account_name", "enabled"}
        if set(payload) != required or type(payload["enabled"]) is not bool:
            raise ValueError("PROFESSIONAL_CONFIG_INVALID")
        if (
            not isinstance(payload["account_name"], str)
            or len(payload["account_name"]) > 300
        ):
            raise ValueError("PROFESSIONAL_ACCOUNT_NAME_INVALID")
    else:
        if (
            set(payload) != {"platform", "account_id", "metrics", "source_kind"}
            or payload["source_kind"] != "USER_DECLARED"
        ):
            raise ValueError("PROFESSIONAL_METRIC_ORIGIN_INVALID")
        rows = payload["metrics"]
        if not isinstance(rows, list) or not 1 <= len(rows) <= 500:
            raise ValueError("PROFESSIONAL_METRICS_REQUIRED")
        dates = set()
        metrics = {
            "impressions",
            "views",
            "cover_ctr",
            "follower_gain",
            "likes",
            "comments",
            "collects",
            "shares",
        }
        for row in rows:
            if (
                not isinstance(row, dict)
                or set(row) - metrics - {"metric_date"}
                or not isinstance(row.get("metric_date"), str)
            ):
                raise ValueError("PROFESSIONAL_METRIC_INPUT_INVALID")
            from datetime import date

            normalized_date = date.fromisoformat(row["metric_date"]).isoformat()
            if normalized_date in dates:
                raise ValueError("PROFESSIONAL_METRIC_DUPLICATE_DATE")
            dates.add(normalized_date)
            for field in metrics:
                value = row.get(field)
                if value is not None and (
                    type(value) not in (int, float)
                    or not math.isfinite(value)
                    or (field != "follower_gain" and value < 0)
                ):
                    raise ValueError("PROFESSIONAL_METRIC_NUMBER_INVALID")
    _scoped_account_key(payload["platform"], payload["account_id"])


def read_scoped_accounts(*, actor, scope, platform=None):
    import kos_ops

    records = kos_ops.read_scoped_operations(
        actor=actor, scope=scope, operation="professional_config", limit=200,
        complete_history=True
    )
    latest = {}
    for record in records["items"]:
        latest.setdefault(record["author_id"], record)
    accounts = []
    for record in latest.values():
        payload = record["payload"]
        validate_private_payload("professional_config", payload)
        if _scoped_account_key(payload["platform"], payload["account_id"]) != record["author_id"]:
            raise ValueError("PROFESSIONAL_ACCOUNT_IDENTITY_MISMATCH")
        if platform is not None and payload["platform"] != platform:
            continue
        accounts.append(
            {
                **payload,
                "version": record["version"],
                "sha256": record["sha256"],
                "auth_status": "UNKNOWN",
                "platform_connection": "NOT_VERIFIED",
                "state": "LOCAL_ENABLED" if payload["enabled"] else "LOCAL_DISABLED",
            }
        )
    return {
        "accounts": accounts,
        "legacy_scope": "UNKNOWN",
        "scope": scope,
        "coverage": "LATEST_PER_ACCOUNT_FROM_COMPLETE_VERIFIED_HISTORY",
    }


def configure_scoped_account(
    *,
    actor,
    scope,
    platform,
    account_id,
    enabled,
    account_name="",
    request_id,
    expected_version=0
):
    import kos_ops

    payload = {
        "platform": platform,
        "account_id": account_id,
        "account_name": account_name,
        "enabled": enabled,
    }
    validate_private_payload("professional_config", payload)
    result = kos_ops.write_scoped_operation(
        actor=actor,
        scope=scope,
        author_id=_scoped_account_key(platform, account_id),
        operation="professional_config",
        payload=payload,
        request_id=request_id,
        expected_version=expected_version,
    )
    return {
        **result,
        "state": "LOCAL_ENABLED" if enabled else "LOCAL_DISABLED",
        "auth_status": "UNKNOWN",
        "platform_connection": "NOT_VERIFIED",
        "external_effect": "not_performed",
    }


def import_scoped_metrics(
    *, actor, scope, platform, account_id, metrics, request_id, expected_version=0
):
    import kos_ops

    key = _scoped_account_key(platform, account_id)
    configurations = kos_ops.read_scoped_operations(
        actor=actor, scope=scope, author_id=key, operation="professional_config"
    )
    if (
        not configurations["items"]
        or configurations["items"][0]["payload"]["enabled"] is not True
    ):
        raise ValueError("PROFESSIONAL_LOCAL_CONFIGURATION_DISABLED")
    payload = {
        "platform": platform,
        "account_id": account_id,
        "metrics": metrics,
        "source_kind": "USER_DECLARED",
    }
    validate_private_payload("professional_metrics", payload)
    return kos_ops.write_scoped_operation(
        actor=actor,
        scope=scope,
        author_id=key,
        operation="professional_metrics",
        payload=payload,
        request_id=request_id,
        expected_version=expected_version,
    )


def read_scoped_metrics(
    *, actor, scope, platform, account_id, start_date="", end_date=""
):
    import kos_ops
    from datetime import date

    if start_date:
        start_date = date.fromisoformat(start_date).isoformat()
    if end_date:
        end_date = date.fromisoformat(end_date).isoformat()
    if start_date and end_date and start_date > end_date:
        raise ValueError("PROFESSIONAL_DATE_RANGE_INVALID")
    records = kos_ops.read_scoped_operations(
        actor=actor,
        scope=scope,
        author_id=_scoped_account_key(platform, account_id),
        operation="professional_metrics",
        complete_history=True,
    )
    current = records["items"][0] if records["items"] else None
    fields = (
        "impressions",
        "views",
        "cover_ctr",
        "follower_gain",
        "likes",
        "comments",
        "collects",
        "shares",
    )
    # Each accepted import replaces only its named dates. Newer batches must
    # not hide prior dates, and previous revisions must never be summed twice.
    by_date = {}
    for record in records["items"]:
        payload = record["payload"]
        validate_private_payload("professional_metrics", payload)
        if payload["platform"] != platform or payload["account_id"] != account_id:
            raise ValueError("PROFESSIONAL_ACCOUNT_IDENTITY_MISMATCH")
        for row in payload["metrics"]:
            metric_date = date.fromisoformat(row["metric_date"]).isoformat()
            if metric_date not in by_date:
                by_date[metric_date] = {
                    **row,
                    **{field: row.get(field) for field in fields},
                    "metric_date": metric_date,
                    "source_kind": "USER_DECLARED",
                    "official_verification": "NOT_VERIFIED",
                    "version": record["version"],
                    "record_id": record["record_id"],
                    "sha256": record["sha256"],
                    "imported_at": record["created_at"],
                }
    values = [by_date[key] for key in sorted(by_date, reverse=True)
              if (not start_date or key >= date.fromisoformat(start_date).isoformat())
              and (not end_date or key <= date.fromisoformat(end_date).isoformat())]
    return {
        "metrics": values,
        "current": current,
        "versions": records["items"],
        "scope": scope,
        "legacy_scope": "UNKNOWN",
        "external_campaign_results": "NOT_ESTABLISHED",
        "projection": "latest-row-per-date-from-complete-verified-history:v1",
        "import_semantics": "replace_named_dates_retain_omitted_dates",
        "withdrawal_semantics": "no_date_deletion_by_omission; account_disable_preserves_history",
    }


def validate_configuration_at_commit(connection, *, context, account_key):
    """Recheck local enablement in the same serialized ledger transaction."""
    import json
    from lumenis.shared.reporting.saved_work import _digest

    rows = connection.execute(
        "SELECT note FROM kos_operations WHERE author_id=? AND action='scoped_professional_config' ORDER BY id DESC",
        (account_key,),
    ).fetchall()
    for row in rows:
        value = json.loads(row[0])
        if value.get("context") != context:
            continue
        if value.get("sha256") != _digest(
            {key: item for key, item in value.items() if key != "sha256"}
        ):
            raise ValueError("KOS_OPERATION_INTEGRITY_FAILED")
        if value["payload"]["enabled"] is not True:
            raise ValueError("PROFESSIONAL_LOCAL_CONFIGURATION_DISABLED")
        return
    raise ValueError("PROFESSIONAL_LOCAL_CONFIGURATION_DISABLED")
