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
    db_path = os.environ.get('TAIKOO_DB_PATH',
                             os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'monitor.db'))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


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
