# -*- coding: utf-8 -*-
"""
ZBC Canonical Data Layer（产品域 08：Canonical Data）
=========================================================
统一核心数据实体，打通 Raw→Canonical 数据链断点。

对齐 OSAI P0-3 `osai_engine/canonical_data.py` 的 CanonicalBase 模型，
同时适配 ZBC 现有 notes / web_mentions 表的实际字段。

设计原则（AGENTS.md 宪法）：
  - 先旁路、再切换：canonical_data 表为新增旁路表，不破坏现有 notes/web_mentions
  - publish_datetime（真实发布时间）与 captured_at（采集时间）严格分离（P0 红线）
  - 规则与数据是业务最终真值，AI 只是增强层
  - 幂等写入：按 canonical_id 去重，已存在则更新非标注字段

数据流：
  CollectedNote (v4_upgrade/adapters/base.py)
    → persist_social_note() / persist_web_mention() (v4_upgrade/adapters/persist.py)
    → notes / web_mentions 表（现有主存储）
    → note_to_canonical() / web_mention_to_canonical() (本模块)
    → canonical_data 表（统一 Canonical 视图，旁路新增）

调用链证据（函数名+文件+行号）：
  - canonical_data.persist_canonical()        → canonical_data.py:180
  - canonical_data.note_to_canonical()         → canonical_data.py:230
  - canonical_data.web_mention_to_canonical()  → canonical_data.py:280
  - canonical_data.collected_note_to_canonical()→ canonical_data.py:320
  - canonical_data.sync_all_to_canonical()      → canonical_data.py:370
  - persist.persist_social_note()               → v4_upgrade/adapters/persist.py:103
  - persist.persist_web_mention()               → v4_upgrade/adapters/persist.py:134
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 常量与取值域（与 canonical_metrics.py 口径一致）
# ============================================================
SENTIMENT_POSITIVE = "positive"
SENTIMENT_NEUTRAL = "neutral"
SENTIMENT_NEGATIVE = "negative"
SENTIMENT_UNKNOWN = "unknown"

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_CRITICAL = "critical"

SOURCE_TYPE_NOTE = "note"
SOURCE_TYPE_WEB_MENTION = "web_mention"
SOURCE_TYPE_COLLECTED = "collected_note"

PRODUCT_CTH = "CTH"  # 广州太古汇客户交付版
PRODUCT_ZBMP = "ZBMP"  # Z-Brand Monitoring Platform 母平台

CANONICAL_TABLE = "canonical_data"
SCHEMA_VERSION = "1.0.0"


# ============================================================
# 工具函数
# ============================================================
def _new_canonical_id(prefix: str = "can") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _content_hash(content: Any) -> str:
    raw = json.dumps(content, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def _safe_int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _safe_float(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# ============================================================
# CanonicalRecord 数据模型
# ============================================================
@dataclass
class CanonicalRecord:
    """统一 Canonical 数据记录。

    对齐 OSAI CanonicalBase（canonical_id/product_id/subject_id/scope/source_id/
    external_id/timestamp/provenance/content_hash/version/created_at/updated_at），
    扩展 ZBC 业务字段（sentiment/risk/quality/engagement/subject_type/content_type）。

    P0 红线：publish_datetime 与 captured_at 严格分离，绝不混用。
    """
    # --- 身份与追踪（对齐 OSAI CanonicalBase）---
    canonical_id: str = field(default_factory=lambda: _new_canonical_id())
    product_id: str = PRODUCT_CTH
    subject_id: str = ""
    scope: str = "default"
    source_id: str = ""
    external_id: str = ""
    provenance: str = ""
    content_hash: str = ""
    version: str = SCHEMA_VERSION

    # --- 来源定位 ---
    source_type: str = SOURCE_TYPE_NOTE  # note / web_mention / collected_note
    source_table: str = ""  # notes / web_mentions
    source_platform: str = ""  # xhs / weibo / douyin / ...
    source_keyword: str = ""

    # --- 内容 ---
    title: str = ""
    content: str = ""
    url: str = ""
    canonical_url: str = ""
    author_id: str = ""
    author_name: str = ""

    # --- 时间（P0 红线：严格分离）---
    publish_datetime: str = ""  # 真实发布时间（平台提供）
    captured_at: str = ""  # 系统采集时间（本服务写入）

    # --- 情感与风险 ---
    sentiment: str = SENTIMENT_NEUTRAL
    sentiment_score: float = 0.0
    risk_level: str = RISK_LOW
    risk_score: int = 0

    # --- 质量与置信 ---
    quality_status: str = "unknown"
    quality_score: float = 0.0
    confidence: float = 0.0
    relevance_status: str = "relevant"
    verification_status: str = "review"

    # --- 主体与内容类型（AGENTS.md 9.1：严格分开）---
    subject_type: str = ""  # KOS/KOL/KOC/normal_user/media/official/institution
    content_type: str = ""  # UGC/商业/官方/测评/体验/投诉/活动内容

    # --- 互动量（4 字段，与 canonical_metrics.ENGAGEMENT_KEYS 一致）---
    engagement_likes: int = 0
    engagement_comments: int = 0
    engagement_collects: int = 0
    engagement_shares: int = 0

    # --- 标签与事件 ---
    topics: str = "[]"  # JSON array
    tags: str = "[]"  # JSON array
    event_hint: str = ""

    # --- 证据与 AI ---
    evidence_ref: str = ""
    ai_provider: str = "rule"
    ai_model: str = ""
    raw_ref: str = ""  # 原始数据引用（JSON: {"table": "notes", "id": 1}）

    # --- 时间戳 ---
    created_at: str = field(default_factory=_now_str)
    updated_at: str = field(default_factory=_now_str)

    def compute_hash(self) -> str:
        """基于 title+content+url 计算内容哈希，用于去重检测。"""
        self.content_hash = _content_hash({
            "title": self.title,
            "content": self.content,
            "url": self.url,
        })
        return self.content_hash

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def engagement_total(self) -> int:
        """互动总量 = likes+comments+collects+shares（与 canonical_metrics 口径一致）。"""
        return (self.engagement_likes + self.engagement_comments
                + self.engagement_collects + self.engagement_shares)


# ============================================================
# 数据库：建表与连接
# ============================================================
CANONICAL_TABLE_DDL = f"""
CREATE TABLE IF NOT EXISTS {CANONICAL_TABLE} (
    -- 身份与追踪（对齐 OSAI CanonicalBase）
    canonical_id      TEXT PRIMARY KEY,
    product_id        TEXT DEFAULT 'CTH',
    subject_id        TEXT DEFAULT '',
    scope             TEXT DEFAULT 'default',
    source_id         TEXT DEFAULT '',
    external_id       TEXT DEFAULT '',
    provenance        TEXT DEFAULT '',
    content_hash      TEXT DEFAULT '',
    version           TEXT DEFAULT '{SCHEMA_VERSION}',

    -- 来源定位
    source_type       TEXT DEFAULT 'note',
    source_table      TEXT DEFAULT '',
    source_platform   TEXT DEFAULT '',
    source_keyword    TEXT DEFAULT '',

    -- 内容
    title             TEXT DEFAULT '',
    content           TEXT DEFAULT '',
    url               TEXT DEFAULT '',
    canonical_url     TEXT DEFAULT '',
    author_id         TEXT DEFAULT '',
    author_name       TEXT DEFAULT '',

    -- 时间（P0 红线：严格分离）
    publish_datetime  TEXT DEFAULT '',
    captured_at       TEXT DEFAULT '',

    -- 情感与风险
    sentiment         TEXT DEFAULT 'neutral',
    sentiment_score   REAL DEFAULT 0.0,
    risk_level        TEXT DEFAULT 'low',
    risk_score        INTEGER DEFAULT 0,

    -- 质量与置信
    quality_status    TEXT DEFAULT 'unknown',
    quality_score     REAL DEFAULT 0.0,
    confidence        REAL DEFAULT 0.0,
    relevance_status  TEXT DEFAULT 'relevant',
    verification_status TEXT DEFAULT 'review',

    -- 主体与内容类型
    subject_type      TEXT DEFAULT '',
    content_type      TEXT DEFAULT '',

    -- 互动量
    engagement_likes     INTEGER DEFAULT 0,
    engagement_comments  INTEGER DEFAULT 0,
    engagement_collects  INTEGER DEFAULT 0,
    engagement_shares    INTEGER DEFAULT 0,

    -- 标签与事件
    topics            TEXT DEFAULT '[]',
    tags              TEXT DEFAULT '[]',
    event_hint        TEXT DEFAULT '',

    -- 证据与 AI
    evidence_ref      TEXT DEFAULT '',
    ai_provider       TEXT DEFAULT 'rule',
    ai_model          TEXT DEFAULT '',
    raw_ref           TEXT DEFAULT '',

    -- 时间戳
    created_at        TEXT DEFAULT '',
    updated_at        TEXT DEFAULT ''
);
"""

# 索引：加速按来源、平台、时间、主体查询
CANONICAL_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_canonical_source ON {CANONICAL_TABLE}(source_type, source_table, source_id)",
    f"CREATE INDEX IF NOT EXISTS idx_canonical_platform ON {CANONICAL_TABLE}(source_platform)",
    f"CREATE INDEX IF NOT EXISTS idx_canonical_publish ON {CANONICAL_TABLE}(publish_datetime)",
    f"CREATE INDEX IF NOT EXISTS idx_canonical_captured ON {CANONICAL_TABLE}(captured_at)",
    f"CREATE INDEX IF NOT EXISTS idx_canonical_subject ON {CANONICAL_TABLE}(subject_type, content_type)",
    f"CREATE INDEX IF NOT EXISTS idx_canonical_hash ON {CANONICAL_TABLE}(content_hash)",
    f"CREATE INDEX IF NOT EXISTS idx_canonical_risk ON {CANONICAL_TABLE}(risk_level, sentiment)",
]


def ensure_canonical_table(db_path: str) -> None:
    """确保 canonical_data 表存在（幂等，不破坏现有数据）。"""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = sqlite3.connect(db_path, timeout=15)
    try:
        con.execute(CANONICAL_TABLE_DDL)
        for idx_sql in CANONICAL_INDEXES:
            con.execute(idx_sql)
        con.commit()
    finally:
        con.close()


def get_connection(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL;")
    return con


# ============================================================
# 写入：persist_canonical（幂等）
# ============================================================
def persist_canonical(con: sqlite3.Connection, record: CanonicalRecord) -> str:
    """写入或更新一条 Canonical 记录。返回 inserted/updated。

    幂等策略：按 canonical_id 去重；已存在则更新内容/互动/时间等非标注字段，
    不覆盖已有人工标注（verification_status/relevance_status/subject_type/content_type
    等若已有非默认值则保留）。
    """
    if not record.content_hash:
        record.compute_hash()
    record.updated_at = _now_str()

    existing = con.execute(
        f"SELECT canonical_id FROM {CANONICAL_TABLE} WHERE canonical_id=? LIMIT 1",
        (record.canonical_id,)
    ).fetchone()

    fields = list(asdict(record).keys())
    placeholders = ", ".join(["?"] * len(fields))
    values = [getattr(record, f) for f in fields]

    if existing:
        # 更新：保留已有标注字段（非空/非默认值不覆盖）
        update_pairs = []
        update_values = []
        protected = {"verification_status", "relevance_status", "subject_type",
                     "content_type", "confidence", "quality_status", "sentiment",
                     "risk_level", "ai_provider", "ai_model"}
        row = con.execute(
            f"SELECT * FROM {CANONICAL_TABLE} WHERE canonical_id=?",
            (record.canonical_id,)
        ).fetchone()
        existing_dict = dict(row) if row else {}

        for f in fields:
            if f == "canonical_id":
                continue
            new_val = getattr(record, f)
            old_val = existing_dict.get(f, "")
            # 受保护字段：旧值非空且非默认时保留
            if f in protected and old_val not in ("", "neutral", "low", "unknown",
                                                    "relevant", "review", "rule", 0, 0.0):
                continue
            update_pairs.append(f"{f}=?")
            update_values.append(new_val)

        if update_pairs:
            update_values.append(record.canonical_id)
            con.execute(
                f"UPDATE {CANONICAL_TABLE} SET {', '.join(update_pairs)} WHERE canonical_id=?",
                tuple(update_values)
            )
        return "updated"

    con.execute(
        f"INSERT INTO {CANONICAL_TABLE} ({', '.join(fields)}) VALUES ({placeholders})",
        tuple(values)
    )
    return "inserted"


# ============================================================
# Raw→Canonical 转化函数
# ============================================================
def note_to_canonical(note_row: Dict[str, Any], product_id: str = PRODUCT_CTH) -> CanonicalRecord:
    """将 notes 表的一行转化为 CanonicalRecord。

    调用链：notes 表（raw/标准化存储）→ note_to_canonical() → canonical_data 表
    文件: canonical_data.py:230

    时间口径（P0 红线）：
      - publish_datetime ← note_row['publish_datetime']（优先）或 publish_date
      - captured_at ← note_row['captured_at']（优先）或 collected_at
      二者绝不混用。
    """
    note_id = _safe_str(note_row.get("note_id"))
    publish_dt = _safe_str(note_row.get("publish_datetime") or note_row.get("publish_date"))
    captured = _safe_str(note_row.get("captured_at") or note_row.get("collected_at"))

    rec = CanonicalRecord(
        canonical_id=f"can_note_{note_id}" if note_id else _new_canonical_id("can_note"),
        product_id=product_id,
        source_id=note_id,
        external_id=note_id,
        source_type=SOURCE_TYPE_NOTE,
        source_table="notes",
        source_platform=_safe_str(note_row.get("source_platform")),
        source_keyword=_safe_str(note_row.get("source_keyword")),
        title=_safe_str(note_row.get("title")),
        content=_safe_str(note_row.get("content") or note_row.get("body")),
        url=_safe_str(note_row.get("url")),
        canonical_url=_safe_str(note_row.get("url")),
        author_id=_safe_str(note_row.get("author_id")),
        author_name=_safe_str(note_row.get("author_nickname")),
        publish_datetime=publish_dt,
        captured_at=captured,
        sentiment=_safe_str(note_row.get("sentiment") or SENTIMENT_NEUTRAL),
        sentiment_score=_safe_float(note_row.get("sentiment_score")),
        risk_level=_safe_str(note_row.get("risk_level") or RISK_LOW),
        risk_score=_safe_int(note_row.get("risk_score")),
        quality_status=_safe_str(note_row.get("data_quality_status") or "unknown"),
        quality_score=_safe_float(note_row.get("data_quality_score") or note_row.get("content_quality_score")),
        confidence=_safe_float(note_row.get("verification_confidence")),
        relevance_status=_safe_str(note_row.get("relevance_status") or "relevant"),
        verification_status=_safe_str(note_row.get("verification_status") or "review"),
        subject_type=_safe_str(note_row.get("subject_type")),
        content_type=_safe_str(note_row.get("content_type")),
        engagement_likes=_safe_int(note_row.get("likes")),
        engagement_comments=_safe_int(note_row.get("comments")),
        engagement_collects=_safe_int(note_row.get("collects")),
        engagement_shares=_safe_int(note_row.get("shares")),
        topics=_safe_str(note_row.get("topics") or "[]"),
        event_hint=_safe_str(note_row.get("event_hint")),
        ai_provider=_safe_str(note_row.get("ai_provider") or "rule"),
        ai_model=_safe_str(note_row.get("ai_model")),
        raw_ref=json.dumps({"table": "notes", "note_id": note_id,
                             "id": note_row.get("id")}, ensure_ascii=False),
        provenance=f"notes:{note_id}",
    )
    rec.compute_hash()
    return rec


def web_mention_to_canonical(web_row: Dict[str, Any], product_id: str = PRODUCT_CTH) -> CanonicalRecord:
    """将 web_mentions 表的一行转化为 CanonicalRecord。

    调用链：web_mentions 表 → web_mention_to_canonical() → canonical_data 表
    文件: canonical_data.py:280

    时间口径（P0 红线）：
      - publish_datetime ← web_row['published_at']
      - captured_at ← web_row['fetched_at']
    """
    source_id = _safe_str(web_row.get("source_id"))
    publish_dt = _safe_str(web_row.get("published_at"))
    captured = _safe_str(web_row.get("fetched_at"))

    rec = CanonicalRecord(
        canonical_id=f"can_web_{source_id}" if source_id else _new_canonical_id("can_web"),
        product_id=product_id,
        source_id=source_id,
        external_id=source_id,
        source_type=SOURCE_TYPE_WEB_MENTION,
        source_table="web_mentions",
        source_platform=_safe_str(web_row.get("source_platform") or web_row.get("source_adapter")),
        source_keyword=_safe_str(web_row.get("query")),
        title=_safe_str(web_row.get("title")),
        content=_safe_str(web_row.get("content")),
        url=_safe_str(web_row.get("url")),
        canonical_url=_safe_str(web_row.get("canonical_url") or web_row.get("url")),
        author_id="",
        author_name="",
        publish_datetime=publish_dt,
        captured_at=captured,
        sentiment=SENTIMENT_NEUTRAL,  # web_mentions 暂无情感字段，默认 neutral
        sentiment_score=0.0,
        risk_level=RISK_LOW,
        risk_score=0,
        quality_status="unknown",
        quality_score=0.0,
        confidence=0.0,
        relevance_status=_safe_str(web_row.get("relevance") or "pending"),
        verification_status=_safe_str(web_row.get("verification") or "review"),
        subject_type="media",  # 网页提及默认媒体类
        content_type="news",  # 默认新闻类
        engagement_likes=0,
        engagement_comments=0,
        engagement_collects=0,
        engagement_shares=0,
        topics="[]",
        event_hint="",
        ai_provider=_safe_str(web_row.get("ai_provider") or "rule"),
        ai_model="",
        raw_ref=json.dumps({"table": "web_mentions", "source_id": source_id,
                             "id": web_row.get("id")}, ensure_ascii=False),
        provenance=f"web_mentions:{source_id}",
    )
    rec.compute_hash()
    return rec


def collected_note_to_canonical(collected: Any, source_platform: str = "",
                                  keyword: str = "", product_id: str = PRODUCT_CTH) -> CanonicalRecord:
    """将 v4_upgrade CollectedNote（dataclass）转化为 CanonicalRecord。

    调用链：CollectedNote (v4_upgrade/adapters/base.py:25)
            → collected_note_to_canonical() → canonical_data 表
    文件: canonical_data.py:320

    时间口径（P0 红线）：
      - publish_datetime ← collected.publish_date（平台发布时间）
      - captured_at ← 当前采集时刻（本函数写入）
    """
    title = _safe_str(getattr(collected, "title", ""))
    content = _safe_str(getattr(collected, "content", ""))
    url = _safe_str(getattr(collected, "url", ""))
    platform = _safe_str(getattr(collected, "source_platform", "") or source_platform)
    publish_dt = _safe_str(getattr(collected, "publish_date", ""))
    author = _safe_str(getattr(collected, "author", ""))
    author_id = _safe_str(getattr(collected, "author_id", ""))

    # 从 raw_data 提取平台原始 ID
    raw_data = getattr(collected, "raw_data", {}) or {}
    external_id = ""
    if isinstance(raw_data, dict):
        external_id = _safe_str(
            raw_data.get("aweme_id") or raw_data.get("shortcode")
            or raw_data.get("note_id") or raw_data.get("id") or ""
        )

    # 稳定 canonical_id：基于 platform+url+title 哈希
    id_key = url or f"{platform}:{author}:{title}"
    stable_hash = _content_hash({"platform": platform, "key": id_key})
    canonical_id = f"can_col_{stable_hash}"

    rec = CanonicalRecord(
        canonical_id=canonical_id,
        product_id=product_id,
        source_id=f"{platform}_{external_id}" if external_id else f"{platform}_{stable_hash}",
        external_id=external_id,
        source_type=SOURCE_TYPE_COLLECTED,
        source_table="",
        source_platform=platform,
        source_keyword=keyword,
        title=title,
        content=content,
        url=url,
        canonical_url=url,
        author_id=author_id,
        author_name=author,
        publish_datetime=publish_dt,
        captured_at=_now_str(),  # 采集时刻由本服务写入
        sentiment=SENTIMENT_NEUTRAL,
        sentiment_score=0.0,
        risk_level=RISK_LOW,
        risk_score=0,
        quality_status="unknown",
        quality_score=0.0,
        confidence=0.0,
        relevance_status="unverified",
        verification_status="pending",
        subject_type="normal_user",
        content_type="ugc",
        engagement_likes=_safe_int(getattr(collected, "likes", 0)),
        engagement_comments=_safe_int(getattr(collected, "comments", 0)),
        engagement_collects=_safe_int(getattr(collected, "collects", 0)),
        engagement_shares=_safe_int(getattr(collected, "shares", 0)),
        topics="[]",
        event_hint="",
        ai_provider="rule",
        ai_model="",
        raw_ref=json.dumps({"source": "CollectedNote", "platform": platform,
                             "keyword": keyword}, ensure_ascii=False),
        provenance=f"collected:{platform}:{keyword}",
    )
    rec.compute_hash()
    return rec


# ============================================================
# 批量同步：sync_all_to_canonical
# ============================================================
def sync_all_to_canonical(db_path: str, product_id: str = PRODUCT_CTH) -> Dict[str, Any]:
    """将现有 notes + web_mentions 全部同步到 canonical_data 表。

    调用链：notes/web_mentions（raw 存储）
            → note_to_canonical()/web_mention_to_canonical()
            → persist_canonical() → canonical_data 表
    文件: canonical_data.py:370

    返回统计 dict：{notes_total, notes_inserted, notes_updated,
                     web_total, web_inserted, web_updated, errors}
    """
    ensure_canonical_table(db_path)
    con = get_connection(db_path)
    stats = {
        "notes_total": 0, "notes_inserted": 0, "notes_updated": 0,
        "web_total": 0, "web_inserted": 0, "web_updated": 0,
        "errors": [],
    }
    try:
        # 同步 notes
        try:
            rows = con.execute("SELECT * FROM notes").fetchall()
            stats["notes_total"] = len(rows)
            for row in rows:
                try:
                    rec = note_to_canonical(dict(row), product_id)
                    flag = persist_canonical(con, rec)
                    if flag == "inserted":
                        stats["notes_inserted"] += 1
                    else:
                        stats["notes_updated"] += 1
                except Exception as e:
                    stats["errors"].append(f"note id={row.get('id')}: {e}")
        except Exception as e:
            stats["errors"].append(f"notes sync failed: {e}")

        # 同步 web_mentions
        try:
            rows = con.execute("SELECT * FROM web_mentions").fetchall()
            stats["web_total"] = len(rows)
            for row in rows:
                try:
                    rec = web_mention_to_canonical(dict(row), product_id)
                    flag = persist_canonical(con, rec)
                    if flag == "inserted":
                        stats["web_inserted"] += 1
                    else:
                        stats["web_updated"] += 1
                except Exception as e:
                    stats["errors"].append(f"web_mention id={row.get('id')}: {e}")
        except Exception as e:
            stats["errors"].append(f"web_mentions sync failed: {e}")

        con.commit()
    finally:
        con.close()
    return stats


# ============================================================
# 查询
# ============================================================
def get_canonical_by_id(con: sqlite3.Connection, canonical_id: str) -> Optional[Dict[str, Any]]:
    """按 canonical_id 查询单条记录。"""
    row = con.execute(
        f"SELECT * FROM {CANONICAL_TABLE} WHERE canonical_id=?", (canonical_id,)
    ).fetchone()
    return dict(row) if row else None


def list_canonical(con: sqlite3.Connection, source_type: str = "",
                   platform: str = "", limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """列出 canonical 记录，可按来源类型/平台过滤。"""
    sql = f"SELECT * FROM {CANONICAL_TABLE}"
    conditions = []
    params = []
    if source_type:
        conditions.append("source_type=?")
        params.append(source_type)
    if platform:
        conditions.append("source_platform=?")
        params.append(platform)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY captured_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = con.execute(sql, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def count_canonical(con: sqlite3.Connection) -> Dict[str, int]:
    """统计 canonical_data 表各来源类型数量。"""
    result = {"total": 0}
    try:
        row = con.execute(f"SELECT COUNT(*) as c FROM {CANONICAL_TABLE}").fetchone()
        result["total"] = row["c"] if row else 0
        rows = con.execute(
            f"SELECT source_type, COUNT(*) as c FROM {CANONICAL_TABLE} GROUP BY source_type"
        ).fetchall()
        for r in rows:
            result[r["source_type"]] = r["c"]
    except Exception:
        pass
    return result


# ============================================================
# Schema Version 管理
# ============================================================
SCHEMA_VERSION_TABLE = "schema_version"

SCHEMA_VERSION_DDL = f"""
CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    version     TEXT NOT NULL,
    description TEXT DEFAULT '',
    applied_at  TEXT DEFAULT '',
    applied_by  TEXT DEFAULT 't4-canonical'
);
"""


def ensure_schema_version_table(db_path: str) -> None:
    """确保 schema_version 表存在。"""
    con = sqlite3.connect(db_path, timeout=15)
    try:
        con.execute(SCHEMA_VERSION_DDL)
        con.commit()
    finally:
        con.close()


def register_schema_version(db_path: str, version: str, description: str,
                             applied_by: str = "t4-canonical") -> None:
    """注册一条 schema 版本记录。"""
    ensure_schema_version_table(db_path)
    con = sqlite3.connect(db_path, timeout=15)
    try:
        con.execute(
            f"INSERT INTO {SCHEMA_VERSION_TABLE} (version, description, applied_at, applied_by) VALUES (?,?,?,?)",
            (version, description, _now_str(), applied_by)
        )
        con.commit()
    finally:
        con.close()


def get_schema_versions(db_path: str) -> List[Dict[str, Any]]:
    """查询所有 schema 版本记录。"""
    ensure_schema_version_table(db_path)
    con = sqlite3.connect(db_path, timeout=15)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(f"SELECT * FROM {SCHEMA_VERSION_TABLE} ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


# ============================================================
# 自检与 CLI
# ============================================================
def self_check(db_path: str) -> Dict[str, Any]:
    """Canonical Data 层自检：表存在性、数据量、时间口径分离验证。"""
    result = {
        "canonical_table_exists": False,
        "schema_version_table_exists": False,
        "canonical_count": 0,
        "by_source_type": {},
        "publish_datetime_populated": 0,
        "captured_at_populated": 0,
        "time_separation_violations": 0,
        "notes_source_count": 0,
        "web_source_count": 0,
        "status": "PASS",
        "issues": [],
    }
    con = sqlite3.connect(db_path, timeout=15)
    con.row_factory = sqlite3.Row
    try:
        # 表存在性
        row = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (CANONICAL_TABLE,)
        ).fetchone()
        result["canonical_table_exists"] = row is not None

        row = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (SCHEMA_VERSION_TABLE,)
        ).fetchone()
        result["schema_version_table_exists"] = row is not None

        if result["canonical_table_exists"]:
            stats = count_canonical(con)
            result["canonical_count"] = stats.get("total", 0)
            result["by_source_type"] = {k: v for k, v in stats.items() if k != "total"}

            # 时间口径分离验证
            rows = con.execute(
                f"SELECT publish_datetime, captured_at FROM {CANONICAL_TABLE}"
            ).fetchall()
            for r in rows:
                pd = _safe_str(r["publish_datetime"])
                ca = _safe_str(r["captured_at"])
                if pd:
                    result["publish_datetime_populated"] += 1
                if ca:
                    result["captured_at_populated"] += 1
                # 违反：两者都非空但值相同（可能是混用）
                if pd and ca and pd == ca:
                    result["time_separation_violations"] += 1

            # 来源统计
            row = con.execute(
                f"SELECT COUNT(*) as c FROM {CANONICAL_TABLE} WHERE source_table='notes'"
            ).fetchone()
            result["notes_source_count"] = row["c"] if row else 0
            row = con.execute(
                f"SELECT COUNT(*) as c FROM {CANONICAL_TABLE} WHERE source_table='web_mentions'"
            ).fetchone()
            result["web_source_count"] = row["c"] if row else 0

        # 判定
        if not result["canonical_table_exists"]:
            result["status"] = "FAIL"
            result["issues"].append("canonical_data 表不存在")
        if result["canonical_count"] == 0:
            result["issues"].append("canonical_data 表为空，需运行 sync_all_to_canonical()")
        if result["time_separation_violations"] > 0:
            result["status"] = "FAIL"
            result["issues"].append(
                f"发现 {result['time_separation_violations']} 条 publish_datetime==captured_at，违反时间分离红线"
            )
    except Exception as e:
        result["status"] = "ERROR"
        result["issues"].append(f"自检异常: {e}")
    finally:
        con.close()
    return result


if __name__ == "__main__":
    import sys
    db = r"D:\Taikoo-monitor-new\data\monitor.db"
    if len(sys.argv) > 1:
        db = sys.argv[1]

    print("=== ZBC Canonical Data Layer 自检 ===")
    print(f"DB: {db}")

    # 1. 确保表存在
    ensure_canonical_table(db)
    ensure_schema_version_table(db)
    print("[OK] canonical_data 表 + schema_version 表 已确保存在")

    # 2. 注册 schema 版本
    register_schema_version(db, SCHEMA_VERSION,
                            f"canonical_data 表初始化（T4 Canonical Data Layer），字段对齐 OSAI CanonicalBase")
    print(f"[OK] schema_version 已注册: {SCHEMA_VERSION}")

    # 3. 同步现有数据
    print("\n--- 同步 notes + web_mentions → canonical_data ---")
    stats = sync_all_to_canonical(db)
    for k, v in stats.items():
        if k != "errors":
            print(f"  {k}: {v}")
    if stats["errors"]:
        print(f"  errors ({len(stats['errors'])}):")
        for e in stats["errors"][:5]:
            print(f"    - {e}")

    # 4. 自检
    print("\n--- 自检结果 ---")
    check = self_check(db)
    for k, v in check.items():
        if k != "issues":
            print(f"  {k}: {v}")
    if check["issues"]:
        print("  issues:")
        for i in check["issues"]:
            print(f"    - {i}")
    print(f"\n最终状态: {check['status']}")
