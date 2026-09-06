# -*- coding: utf-8 -*-
"""
采集结果统一入库服务（Persistence Service）
=================================================
把各适配器返回的标准化 CollectedNote 落到现有 monitor.db，不新建重复表：

  · 社媒类（抖音 / Instagram / 小红书 / 知乎 / 大众点评 / 什么值得买 / 微博 / B站）
    → notes 表，以 source_platform 区分平台，note_id / url 去重，已存在则更新互动量；
  · 网页新闻类（搜狗 / Google / Bing / 百度 / 搜狗微信 / 豆包搜索）
    → web_mentions 表，canonical_url 去重；
  · 每次采集运行（含六态、抓取/采纳/去重计数、错误）→ web_runs 表，
    作为“全局采集健康状态中心”的数据底座。

严格区分发布时间与采集时间：publish_date/published_at 只取平台发布时间，
captured_at/fetched_at 由本服务写入当前采集时刻，二者不混用。
"""
import os
import json
import time
import sqlite3
import hashlib
import datetime
from typing import List, Dict
from .base import CollectedNote, AdapterResult
from ..config import DB_PATH

import logging
logger = logging.getLogger(__name__)

# T4 Canonical Data 旁路接入（不影响主流程，失败仅记录日志）
try:
    from canonical_data import (
        collected_note_to_canonical, persist_canonical, ensure_canonical_table,
    )
    _CANONICAL_AVAILABLE = True
except Exception as _e:
    logger.warning(f"[T4] canonical_data 旁路不可用: {_e}")
    _CANONICAL_AVAILABLE = False


def _canonical_bypass(con, n, keyword, source_platform=""):
    """T4 旁路：将 CollectedNote 同步写入 canonical_data 表。

    调用链：CollectedNote -> collected_note_to_canonical() -> persist_canonical() -> canonical_data
    文件: canonical_data.py:320 (collected_note_to_canonical), :180 (persist_canonical)

    严格旁路：任何异常不影响主流程，仅记录日志。
    publish_datetime（平台发布时间）与 captured_at（采集时间）在 canonical_data 内部分离。
    """
    if not _CANONICAL_AVAILABLE:
        return
    try:
        ensure_canonical_table(DB_PATH)
        rec = collected_note_to_canonical(n, source_platform=source_platform, keyword=keyword)
        persist_canonical(con, rec)
    except Exception as e:
        logger.warning(f"[T4] canonical 旁路写入失败（不影响主流程）: {e}")

# 平台分流：社媒 → notes；其余搜索/网页 → web_mentions
SOCIAL_PLATFORMS = {
    "douyin", "instagram", "xiaohongshu", "rednote", "zhihu",
    "dianping", "smzdm", "weibo", "bilibili",
}
WEB_PLATFORMS = {
    "sogou_search", "google", "bing_search", "baidu_search",
    "sogou_wechat", "doubao_search",
}

# 六态（与系统采集状态机一致，失败绝不写成“0条成功”）
STATE_SUCCESS = "SUCCESS"
STATE_EMPTY = "EMPTY"
STATE_AUTH_REQUIRED = "AUTH_REQUIRED"
STATE_CAPTCHA = "CAPTCHA"
STATE_BLOCKED = "BLOCKED"
STATE_NETWORK_ERROR = "NETWORK_ERROR"
STATE_FAIL = "FAIL"

_AUTH_HINTS = ["登录", "login", "cookie", "登录态", "auth", "未登录", "扫码"]
_CAPTCHA_HINTS = ["验证码", "人机", "滑块", "captcha", "验证"]
_BLOCK_HINTS = ["300012", "风控", "频繁", "风险", "安全限制", "knitsail", "熔断", "unusual", "反爬"]
_NET_HINTS = ["网络", "timeout", "timed out", "连接", "network", "proxy", "代理", "无法访问"]


def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn() -> sqlite3.Connection:
    """连接主库（调用方负责关闭）。"""
    path = DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL;")
    return con


def _md5(text: str) -> str:
    return hashlib.md5((text or "").encode("utf-8", "ignore")).hexdigest()


def classify_state(result: AdapterResult) -> str:
    """依据 success / notes / error 文本判定六态（失败细分，绝不与 EMPTY 混淆）。"""
    if result.success:
        return STATE_SUCCESS if result.notes else STATE_EMPTY
    err = (result.error or "").lower()
    if any(h in err for h in _AUTH_HINTS):
        return STATE_AUTH_REQUIRED
    if any(h in err for h in _CAPTCHA_HINTS):
        return STATE_CAPTCHA
    if any(h in err for h in _BLOCK_HINTS):
        return STATE_BLOCKED
    if any(h in err for h in _NET_HINTS):
        return STATE_NETWORK_ERROR
    return STATE_FAIL


def _social_note_id(platform: str, n: CollectedNote) -> str:
    """社媒笔记稳定主键：优先平台内部 id，其次 URL 哈希。"""
    rid = ""
    if isinstance(n.raw_data, dict):
        rid = str(n.raw_data.get("aweme_id") or n.raw_data.get("shortcode")
                  or n.raw_data.get("note_id") or n.raw_data.get("id") or "")
    if rid:
        return f"{platform}_{rid}"
    key = n.url or f"{n.author}:{n.title}"
    return f"{platform}_{_md5(key)[:16]}"


def _existing_id(con: sqlite3.Connection, table: str, col: str, val: str):
    row = con.execute(f"SELECT id FROM {table} WHERE {col}=? LIMIT 1", (val,)).fetchone()
    return row[0] if row else None


def persist_social_note(con, n: CollectedNote, keyword: str) -> str:
    """写入/更新一条社媒笔记到 notes。返回 inserted/updated/duplicate。"""
    platform = n.source_platform or "unknown"
    note_id = _social_note_id(platform, n)
    now = now_str()
    existing = _existing_id(con, "notes", "note_id", note_id)
    if existing:
        # 已存在：仅刷新互动量与最后出现时间，不覆盖已有人工标注/AI 结论
        con.execute(
            """UPDATE notes SET likes=?, comments=?, collects=?, shares=?,
               last_seen_at=?, captured_at=COALESCE(NULLIF(captured_at,''), ?)
               WHERE note_id=?""",
            (n.likes, n.comments, n.collects, n.shares, now, now, note_id),
        )
        # T4 旁路：同步更新 canonical_data（不影响主流程）
        _canonical_bypass(con, n, keyword, source_platform=platform)
        return "updated"
    con.execute(
        """INSERT INTO notes
           (note_id, title, content, body, url, cover, author_id, author_nickname,
            likes, comments, collects, shares, publish_date, publish_datetime,
            source_platform, source_keyword, captured_at, collected_at,
            collector_version, status, verification_status, ai_filter_status,
            is_taikoo_verified, relevance_status, data_quality_status)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (note_id, n.title, n.content, n.content, n.url, n.cover, n.author_id,
         n.author, n.likes, n.comments, n.collects, n.shares,
         n.publish_date, n.publish_date, platform, keyword, now, now,
         "v4-adapter", "active", "pending", "pending", 0, "unverified", "unknown"),
    )
    # T4 旁路：同步写入 canonical_data（不影响主流程）
    _canonical_bypass(con, n, keyword, source_platform=platform)
    return "inserted"


def persist_web_mention(con, n: CollectedNote, keyword: str, adapter: str) -> str:
    """写入/更新一条网页提及到 web_mentions。返回 inserted/updated。"""
    canonical = n.url or f"{adapter}:{n.title}"
    source_id = f"{adapter}_{_md5(canonical)[:16]}"
    domain = ""
    try:
        domain = urllib_domain(canonical)
    except Exception:
        domain = ""
    existing = _existing_id(con, "web_mentions", "source_id", source_id)
    if existing:
        con.execute(
            "UPDATE web_mentions SET fetched_at=? WHERE source_id=?", (now_str(), source_id))
        return "updated"
    con.execute(
        """INSERT INTO web_mentions
           (source_id, source_platform, source_type, title, content, url, domain,
            published_at, fetched_at, source_adapter, query, canonical_url,
            relevance, verification, ai_provider)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (source_id, adapter, "web", n.title, n.content, n.url, domain,
         n.publish_date, now_str(), adapter, keyword, canonical,
         "pending", "review", "rule"),
    )
    # T4 旁路：同步写入 canonical_data（不影响主流程）
    _canonical_bypass(con, n, keyword, source_platform=adapter)
    return "inserted"


def urllib_domain(url: str) -> str:
    import urllib.parse
    host = urllib.parse.urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def persist_result(platform: str, adapter_display: str, result: AdapterResult,
                   keyword: str, con=None) -> Dict:
    """把单平台结果入库，并写一条 web_runs 运行记录。返回统计 dict。"""
    own = con is None
    con = con or get_conn()
    state = classify_state(result)
    inserted = updated = 0
    is_social = platform in SOCIAL_PLATFORMS
    try:
        if result.success:
            for n in result.notes:
                if is_social:
                    flag = persist_social_note(con, n, keyword)
                else:
                    flag = persist_web_mention(con, n, keyword, platform)
                if flag == "inserted":
                    inserted += 1
                elif flag == "updated":
                    updated += 1
        started = now_str()
        con.execute(
            """INSERT INTO web_runs
               (adapter, query, started_at, finished_at, fetched, accepted, rejected, error)
               VALUES (?,?,?,?,?,?,?,?)""",
            (platform, keyword, started, now_str(), len(result.notes),
             inserted, updated, "" if result.success else (result.error or state)),
        )
        # 同步刷新 web_sources 来源状态（健康灯用）
        con.execute(
            """INSERT INTO web_sources (source_key, source_name, adapter, enabled,
                 last_run_at, last_success_at, last_error, item_count)
               VALUES (?,?,?,1,?,?,?,?)
               ON CONFLICT(source_key) DO UPDATE SET
                 last_run_at=excluded.last_run_at,
                 last_success_at=excluded.last_success_at,
                 last_error=excluded.last_error, item_count=excluded.item_count""",
            (platform, adapter_display, platform, now_str(),
             now_str() if result.success else "",
             "" if result.success else (result.error or state), inserted),
        )
        if own:
            con.commit()
    finally:
        if own:
            con.close()
    return {
        "platform": platform, "display": adapter_display, "state": state,
        "success": result.success, "fetched": len(result.notes),
        "inserted": inserted, "updated": updated,
        "error": result.error, "duration": round(result.duration_seconds, 2),
    }
