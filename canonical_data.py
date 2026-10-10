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
  CollectedNote (lumenis/adapters/base.py)
    → persist_social_note() / persist_web_mention() (lumenis/adapters/persist.py)
    → notes / web_mentions 表（现有主存储）
    → note_to_canonical() / web_mention_to_canonical() (本模块)
    → canonical_data 表（统一 Canonical 视图，旁路新增）

调用链证据（函数名+文件+行号）：
  - canonical_data.persist_canonical()        → canonical_data.py:180
  - canonical_data.note_to_canonical()         → canonical_data.py:230
  - canonical_data.web_mention_to_canonical()  → canonical_data.py:280
  - canonical_data.collected_note_to_canonical()→ canonical_data.py:320
  - canonical_data.sync_all_to_canonical()      → canonical_data.py:370
  - persist.persist_social_note()               → lumenis/adapters/persist.py:103
  - persist.persist_web_mention()               → lumenis/adapters/persist.py:134
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from lumenis.shared.database import DatabaseRepository
from lumenis.shared.database.scope import normalize_product_domain
from canonical_metrics import engagement_count, engagement_stats
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
RISK_UNKNOWN = "unknown"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_CRITICAL = "critical"

SOURCE_TYPE_NOTE = "note"
SOURCE_TYPE_WEB_MENTION = "web_mention"
SOURCE_TYPE_COLLECTED = "collected_note"

PRODUCT_CTH = "CTH"  # 广州太古汇客户交付版
PRODUCT_ZBMP = "ZBMP"  # Z-Brand Monitoring Platform 母平台


def _canonical_record_identity(product_id: Any, domain_id: Any = "") -> tuple[str, str]:
    """Require explicit known identity, using the existing compatibility owner."""
    if not isinstance(product_id, str) or not product_id or product_id != product_id.strip():
        raise ValueError("Canonical product_id must be a non-empty exact string")
    if not isinstance(domain_id, str) or domain_id != domain_id.strip():
        raise ValueError("Canonical domain_id must be an exact string")
    return normalize_product_domain(product_id, domain_id)


def _inbound_canonical_identity(row: Dict[str, Any], product_id: Any) -> tuple[str, str]:
    """An inbound declaration cannot override or contradict the caller's identity."""
    product, domain = _canonical_record_identity(product_id, row.get("domain_id", ""))
    if "product_id" in row:
        declared_product, declared_domain = _canonical_record_identity(
            row["product_id"], row.get("domain_id", ""),
        )
        if (declared_product, declared_domain) != (product, domain):
            raise ValueError("Canonical inbound product_id conflicts with caller identity")
    return product, domain

CANONICAL_TABLE = "canonical_data"
SCHEMA_VERSION = "1.0.0"

# ============================================================
# 缺失值标记（P0 红线：禁止 0/"未知" 静默填充）
# ============================================================
MISSING = None  # Python 层缺失值统一用 None；JSON 序列化为 null；DB 存储为 NULL


def is_missing(value):
    """判断值是否为缺失（None 或空字符串标记）。真实 0 返回 False。"""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() in ("", "missing", "null", "None"):
        return True
    return False


def display_missing(value, placeholder="--"):
    """前端展示辅助：缺失值显示占位符，真实值原样返回。"""
    if is_missing(value):
        return placeholder
    return value



# ============================================================
# 时间归一化（P0 红线：publish_datetime vs captured_at 严格分离）
# ============================================================
import re as _re_time
from datetime import datetime as _dt, timedelta as _td

_RELATIVE_PATTERNS = [
    (_re_time.compile(r'刚刚'), 'just_now'),
    (_re_time.compile(r'(\d+)\s*分钟前'), 'minutes_ago'),
    (_re_time.compile(r'(\d+)\s*小时前'), 'hours_ago'),
    (_re_time.compile(r'昨天\s*(\d{1,2})?:?(\d{1,2})?'), 'yesterday'),
    (_re_time.compile(r'(\d+)\s*天前'), 'days_ago'),
    (_re_time.compile(r'(\d+)\s*周前'), 'weeks_ago'),
    (_re_time.compile(r'(\d+)\s*个月前'), 'months_ago'),
]

_ABSOLUTE_FORMATS = [
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d",
    "%Y年%m月%d日 %H:%M", "%Y年%m月%d日",
    "%m-%d %H:%M", "%m/%d %H:%M",
]


def normalize_relative_time(raw_value, reference_time=None):
    """将相对时间归一化为绝对时间戳。失败返回 None，不得猜测。"""
    if raw_value is None:
        return None
    if isinstance(raw_value, str) and raw_value.strip() in ("", "missing", "null", "None"):
        return None
    if isinstance(raw_value, _dt):
        return raw_value.strftime("%Y-%m-%d %H:%M:%S")
    s = str(raw_value).strip()
    ref = reference_time or _dt.now()
    for fmt in _ABSOLUTE_FORMATS:
        try:
            parsed = _dt.strptime(s, fmt)
            if fmt in ("%m-%d %H:%M", "%m/%d %H:%M"):
                parsed = parsed.replace(year=ref.year)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    for pattern, kind in _RELATIVE_PATTERNS:
        m = pattern.search(s)
        if not m:
            continue
        try:
            if kind == 'just_now':
                return ref.strftime("%Y-%m-%d %H:%M:%S")
            elif kind == 'minutes_ago':
                return (ref - _td(minutes=int(m.group(1)))).strftime("%Y-%m-%d %H:%M:%S")
            elif kind == 'hours_ago':
                return (ref - _td(hours=int(m.group(1)))).strftime("%Y-%m-%d %H:%M:%S")
            elif kind == 'yesterday':
                yesterday = ref - _td(days=1)
                hour = int(m.group(1)) if m.group(1) else 0
                minute = int(m.group(2)) if m.group(2) else 0
                return yesterday.replace(hour=hour, minute=minute, second=0).strftime("%Y-%m-%d %H:%M:%S")
            elif kind == 'days_ago':
                return (ref - _td(days=int(m.group(1)))).strftime("%Y-%m-%d %H:%M:%S")
            elif kind == 'weeks_ago':
                return (ref - _td(weeks=int(m.group(1)))).strftime("%Y-%m-%d %H:%M:%S")
            elif kind == 'months_ago':
                return (ref - _td(days=int(m.group(1)) * 30)).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            continue
    return None


def verify_time_separation(record):
    """验证 publish_datetime 与 captured_at 严格分离。"""
    pd = getattr(record, 'publish_datetime', '')
    ca = getattr(record, 'captured_at', '')
    result = {'valid': True, 'publish_datetime': pd, 'captured_at': ca, 'issue': None}
    if pd and ca and pd == ca:
        result['valid'] = False
        result['issue'] = 'publish_datetime 与 captured_at 相同，可能混用'
    return result



def _safe_int_or_none(v):
    """安全转 int，缺失值保留 None（不转为 0）。P0 红线。"""
    if v is None:
        return None
    if isinstance(v, str) and v.strip() in ("", "missing", "null", "None"):
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _safe_float_or_none(v):
    """安全转 float，缺失值保留 None（不转为 0.0）。P0 红线。"""
    if v is None:
        return None
    if isinstance(v, str) and v.strip() in ("", "missing", "null", "None"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None



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
    domain_id: str = ""  # 双域核心：cth/zbmp/system，__post_init__ 从 product_id 映射
    subject_id: str = ""
    brand_focus_id: str = ""
    scope_status: str = "UNASSIGNED"
    scope_evidence_ref: str = ""
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
    sentiment: str = SENTIMENT_UNKNOWN
    sentiment_score: Optional[float] = None
    risk_level: str = RISK_UNKNOWN
    risk_score: Optional[int] = None

    # --- 质量与置信 ---
    quality_status: str = "unknown"
    quality_score: Optional[float] = None
    confidence: Optional[float] = None
    relevance_status: str = "unknown"
    verification_status: str = "review"
    localization_score: Optional[float] = None  # IC-039: 跨文化本地化评分 0-1，None=未评估

    # --- 主体与内容类型（AGENTS.md 9.1：严格分开）---
    subject_type: str = ""  # KOS/KOL/KOC/normal_user/media/official/institution
    content_type: str = ""  # UGC/商业/官方/测评/体验/投诉/活动内容

    # --- 互动量（P0 红线：缺失为 None，不得静默填 0）---
    engagement_likes: Optional[int] = None
    engagement_comments: Optional[int] = None
    engagement_collects: Optional[int] = None
    engagement_shares: Optional[int] = None

    # --- 标签与事件 ---
    topics: str = "[]"  # JSON array
    tags: str = "[]"  # JSON array
    event_hint: str = ""

    # --- 评论/详情采集状态（P0 红线：失败不静默丢弃）---
    comments_status: str = "pending"  # pending/success/failed/partial/timeout
    detail_status: str = "pending"    # pending/success/failed/partial/timeout
    comments_error: str = ""
    detail_error: str = ""

    # --- 证据与 AI（P0 红线：AI 结果与原始数据分离存储）---
    evidence_ref: str = ""
    ai_provider: str = "rule"
    ai_model: str = ""
    ai_analysis: str = ""  # AI 分析结果（独立字段，不覆盖原始 content/sentiment/risk）
    raw_ref: str = ""  # 原始数据引用（JSON: {"table": "notes", "id": 1}）

    # --- 时间戳 ---
    created_at: str = field(default_factory=_now_str)
    updated_at: str = field(default_factory=_now_str)

    def __post_init__(self):
        """Preserve declared CTH defaults and normalize only supported identities."""
        self.product_id, self.domain_id = _canonical_record_identity(
            self.product_id, self.domain_id,
        )

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

    def engagement_observation(self) -> Dict[str, Any]:
        """Measured components, complete total and coverage from the sole metric owner."""
        return engagement_stats([{
            "likes": self.engagement_likes, "comments": self.engagement_comments,
            "collects": self.engagement_collects, "shares": self.engagement_shares,
        }])

    def engagement_total(self) -> Optional[int]:
        """Complete four-component total; partial/unknown remains None.

        engagement_observation exposes any measured subtotal with its coverage.
        """
        return self.engagement_observation()["sum"]


# ============================================================
# 数据库：建表与连接
# ============================================================
CANONICAL_TABLE_DDL = f"""
CREATE TABLE IF NOT EXISTS {CANONICAL_TABLE} (
    -- 身份与追踪（对齐 OSAI CanonicalBase）
    canonical_id      TEXT PRIMARY KEY,
    product_id        TEXT DEFAULT 'CTH',
    domain_id         TEXT DEFAULT 'cth',
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
    sentiment         TEXT DEFAULT 'unknown',
    sentiment_score   REAL,
    risk_level        TEXT DEFAULT 'unknown',
    risk_score        INTEGER,

    -- 质量与置信
    quality_status    TEXT DEFAULT 'unknown',
    quality_score     REAL,
    confidence        REAL,
    relevance_status  TEXT DEFAULT 'unknown',
    verification_status TEXT DEFAULT 'review',
    localization_score REAL,  -- IC-039: 跨文化本地化评分 0-1，NULL=未评估

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

    -- 评论/详情采集状态
    comments_status   TEXT DEFAULT 'pending',
    detail_status     TEXT DEFAULT 'pending',
    comments_error    TEXT DEFAULT '',
    detail_error      TEXT DEFAULT '',

    -- 证据与 AI（AI 结果与原始数据分离）
    evidence_ref      TEXT DEFAULT '',
    ai_provider       TEXT DEFAULT 'rule',
    ai_model          TEXT DEFAULT '',
    ai_analysis       TEXT DEFAULT '',
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



def ensure_canonical_scope_columns(conn: sqlite3.Connection) -> None:
    """Add v14 scope storage through the caller's canonical connection."""
    table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (CANONICAL_TABLE,),
    ).fetchone()
    if table_exists is None:
        raise sqlite3.OperationalError(
            "canonical_data must exist before v14 scope storage is applied"
        )

    columns = {
        row[1] for row in conn.execute(f"PRAGMA table_info({CANONICAL_TABLE})")
    }
    # subject_id and evidence_ref belong to the existing Canonical Data contract.
    # Preserve them; scope_evidence_ref is a separate explicit v14 scope reference.
    additions = {
        "subject_id": "TEXT",
        "brand_focus_id": "TEXT",
        "scope_status": "TEXT NOT NULL DEFAULT 'UNASSIGNED'",
        "scope_evidence_ref": "TEXT",
    }
    for column, definition in additions.items():
        if column not in columns:
            conn.execute(
                f"ALTER TABLE {CANONICAL_TABLE} ADD COLUMN {column} {definition}"
            )
    conn.execute(
        "UPDATE canonical_data SET scope_status='UNASSIGNED' "
        "WHERE scope_status IS NULL OR TRIM(scope_status)=''"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_canonical_scope_subject "
        "ON canonical_data(subject_id, scope_status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_canonical_scope_brand "
        "ON canonical_data(brand_focus_id, scope_status)"
    )

def ensure_canonical_table(
    db_path: Optional[str] = None,
    *,
    connection: Optional[sqlite3.Connection] = None,
) -> None:
    """确保 canonical_data 表存在（幂等，不破坏现有数据）。

    A supplied connection is used as-is; its caller owns commit, rollback, and
    close. Pass either ``db_path`` or ``connection``, never both.
    """
    if connection is not None:
        if db_path is not None:
            raise ValueError("pass either db_path or connection, not both")
        con = connection
        owns_connection = False
    else:
        if db_path is None:
            raise ValueError("db_path is required when connection is not provided")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        con = DatabaseRepository(db_path).connect(timeout=15)
        owns_connection = True
    try:
        con.execute(CANONICAL_TABLE_DDL)
        for idx_sql in CANONICAL_INDEXES:
            con.execute(idx_sql)
        # 双域核心迁移：添加 domain_id 列（幂等，已存在则跳过）
        try:
            cols = [r[1] for r in con.execute("PRAGMA table_info(canonical_data)").fetchall()]
            if "domain_id" not in cols:
                con.execute("ALTER TABLE canonical_data ADD COLUMN domain_id TEXT DEFAULT 'cth'")
                # 回填：按 product_id 映射 domain_id
                con.execute("UPDATE canonical_data SET domain_id='cth' WHERE product_id='CTH' AND (domain_id IS NULL OR domain_id='')")
                con.execute("UPDATE canonical_data SET domain_id='zbmp' WHERE product_id='ZBMP' AND (domain_id IS NULL OR domain_id='')")
        except Exception as _mig_err:
            if not owns_connection:
                raise
            print(f"[canonical_data] domain_id migration skipped: {_mig_err}")
        ensure_canonical_scope_columns(con)
        if owns_connection:
            con.commit()
    finally:
        if owns_connection:
            con.close()


def get_connection(db_path: str) -> sqlite3.Connection:
    con = DatabaseRepository(db_path).connect(timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL;")
    return con


# ============================================================
# 写入：persist_canonical（幂等）
# ============================================================
def _validate_canonical_scope(
    con: sqlite3.Connection, record: CanonicalRecord,
) -> Optional[Dict[str, Any]]:
    """Reject mixed scope identities and require signed Evidence for VERIFIED."""
    def exact_text(value: Any, field_name: str) -> str:
        if value is None and field_name in {"subject_id", "brand_focus_id", "scope_evidence_ref"}:
            return ""
        if not isinstance(value, str) or value != value.strip():
            raise ValueError(f"Canonical {field_name} must be an exact trimmed string")
        return value

    product = exact_text(record.product_id, "product_id")
    domain = exact_text(record.domain_id, "domain_id")
    status = exact_text(record.scope_status, "scope_status")
    subject = exact_text(record.subject_id, "subject_id")
    brand = exact_text(record.brand_focus_id, "brand_focus_id")
    evidence_ref = exact_text(record.scope_evidence_ref, "scope_evidence_ref")
    normalized_product, expected_domain = _canonical_record_identity(product, domain)
    if (product, domain) != (normalized_product, expected_domain):
        raise ValueError("Canonical product_id and domain_id must use normalized storage identity")
    for metric in ("engagement_likes", "engagement_comments", "engagement_collects", "engagement_shares"):
        value = getattr(record, metric)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(f"Canonical {metric} must be an exact nonnegative integer or None")

    if not status or status != status.upper():
        raise ValueError("Canonical scope_status must be a non-empty uppercase value")
    if subject and brand:
        raise ValueError("Canonical scope cannot mix Subject and BrandFocus")
    if domain != expected_domain:
        raise ValueError("Canonical product_id and domain_id conflict")
    if subject and product != PRODUCT_CTH:
        raise ValueError("only CTH Canonical records may carry subject_id")
    if brand and product != PRODUCT_ZBMP:
        raise ValueError("only BMP Canonical records may carry brand_focus_id")
    if status != "VERIFIED":
        return None

    focus = subject if product == PRODUCT_CTH else brand if product == PRODUCT_ZBMP else ""
    if not focus or not evidence_ref or not record.source_id:
        raise ValueError("VERIFIED Canonical scope requires one exact focus and Evidence")
    try:
        from lumenis.shared.evidence.store import classify_evidence_integrity
    except (ImportError, AttributeError) as exc:
        raise RuntimeError("signed Evidence verification is unavailable") from exc

    cursor = con.execute("SELECT * FROM app_evidence_records WHERE id=?", (evidence_ref,))
    row = cursor.fetchone()
    if row is None:
        raise ValueError("Canonical scope Evidence is missing")
    evidence = dict(zip((column[0] for column in cursor.description), row))
    assurance = classify_evidence_integrity(evidence)
    if (
        assurance.get("verified") is not True
        or assurance.get("assurance") != "writer-authenticated"
        or str(evidence.get("result") or "").upper() != "PASS"
        or str(evidence.get("status") or "").lower() != "verified"
        or evidence.get("product_id") != product
        or evidence.get("domain_id") != domain
    ):
        raise ValueError("Canonical scope Evidence is not signed and verified for this domain")
    try:
        inputs = json.loads(evidence.get("inputs_json") or "")
    except (TypeError, ValueError) as exc:
        raise ValueError("Canonical scope Evidence inputs are invalid") from exc
    expected_scope = {"domain_id": domain, "product_id": product, "global": False}
    expected_scope["subject_id" if product == PRODUCT_CTH else "brand_focus_id"] = focus
    if (
        not isinstance(inputs, dict)
        or inputs.get("_lumenis_scope") != expected_scope
        or not isinstance(inputs.get("source_ids"), list)
        or record.source_id not in inputs["source_ids"]
    ):
        raise ValueError("Canonical scope Evidence does not cover the exact source and focus")
    return {
        "id": evidence.get("id"),
        "source_id": record.source_id,
        "stored_scope": {
            "product_id": product,
            "domain_id": domain,
            "subject_id": subject,
            "brand_focus_id": brand,
            "scope_status": status,
        },
        "integrity": {
            "integrity_version": assurance.get("version"),
            "verified": True,
            "lineage_verified": True,
            "algorithm": assurance.get("algorithm"),
            "digest": evidence.get("integrity_digest"),
            "assurance": assurance.get("assurance"),
        },
    }


def _reject_verified_scope_rewrite(existing: dict, record: CanonicalRecord) -> None:
    if str(existing.get("scope_status") or "").upper() != "VERIFIED":
        return
    prior = tuple(str(existing.get(key) or "") for key in (
        "product_id", "domain_id", "subject_id", "brand_focus_id",
    ))
    current = tuple(str(getattr(record, key) or "") for key in (
        "product_id", "domain_id", "subject_id", "brand_focus_id",
    ))
    if record.scope_status != "VERIFIED" or current != prior:
        raise ValueError("verified Canonical scope cannot be downgraded or rebound")


def _has_scope_correction(con: sqlite3.Connection, source_id: str, *,
                          source_platform: str, product_id: str, domain_id: str) -> bool:
    """Check the existing signed Evidence owner for an unassignment tombstone."""
    from lumenis.shared.evidence.store import classify_evidence_integrity

    cursor = con.execute(
        "SELECT * FROM app_evidence_records WHERE feature_id='SCOPE_CORRECTION' "
        "AND product_id=? AND domain_id=?", (product_id, domain_id),
    )
    names = [column[0] for column in cursor.description]
    for row in cursor.fetchall():
        evidence = dict(zip(names, row))
        try:
            inputs = json.loads(evidence.get("inputs_json") or "")
            correction = inputs.get("scope_correction") if isinstance(inputs, dict) else None
            source_ids = inputs.get("source_ids") if isinstance(inputs, dict) else None
        except (TypeError, ValueError):
            raise ValueError("scope correction Evidence inputs are invalid") from None
        if not isinstance(correction, dict) or correction.get("target_scope_status") != "UNASSIGNED":
            continue
        if correction.get("platform") != source_platform:
            continue
        if not isinstance(source_ids, list) or any(type(item) is not str for item in source_ids):
            raise ValueError("scope correction Evidence source identities are invalid")
        if not classify_evidence_integrity(evidence).get("verified"):
            raise ValueError("scope correction Evidence signature is invalid")
        if source_id in source_ids:
            return True
    return False


def persist_canonical(con: sqlite3.Connection, record: CanonicalRecord) -> str:
    """写入或更新一条 Canonical 记录。返回 inserted/updated。

    幂等策略：按 canonical_id 去重；已存在则更新内容/互动/时间等非标注字段，
    不覆盖已有人工标注（verification_status/relevance_status/subject_type/content_type
    等若已有非默认值则保留）。
    """
    _validate_canonical_scope(con, record)
    if record.scope_status == "VERIFIED" and record.source_id and _has_scope_correction(
        con, record.source_id, source_platform=record.source_platform,
        product_id=record.product_id, domain_id=record.domain_id,
    ):
        raise ValueError("an explicitly corrected source scope cannot be restored")
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
        _reject_verified_scope_rewrite(existing_dict, record)

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


def persist_scope_correction(
    con: sqlite3.Connection,
    *,
    source_id: str,
    product_id: str,
    domain_id: str,
    expected_subject_id: Optional[str],
    expected_brand_focus_id: Optional[str],
    expected_scope_evidence_ref: int,
    correction_evidence_id: int,
) -> None:
    """Clear one exact VERIFIED Canonical scope under signed correction Evidence.

    This is deliberately separate from ordinary Canonical upsert: the normal
    no-rebind fence remains unchanged. The caller owns the transaction and
    must update the matching Raw row in the same transaction.
    """
    from lumenis.shared.evidence.store import classify_evidence_integrity

    if (type(correction_evidence_id) is not int or correction_evidence_id < 1
            or type(expected_scope_evidence_ref) is not int
            or expected_scope_evidence_ref < 1 or not source_id):
        raise ValueError("exact correction Evidence and source identity are required")
    cursor = con.execute(
        "SELECT * FROM app_evidence_records WHERE id=? LIMIT 1",
        (correction_evidence_id,),
    )
    evidence_row = cursor.fetchone()
    if evidence_row is None:
        raise ValueError("scope correction Evidence is missing")
    evidence = dict(zip((item[0] for item in cursor.description), evidence_row))
    if (
        not classify_evidence_integrity(evidence).get("verified")
        or evidence.get("feature_id") != "SCOPE_CORRECTION"
        or str(evidence.get("result") or "").upper() != "PASS"
        or str(evidence.get("status") or "").lower() != "verified"
        or evidence.get("product_id") != product_id
        or evidence.get("domain_id") != domain_id
    ):
        raise ValueError("scope correction Evidence is not signed for this product/domain")
    try:
        inputs = json.loads(evidence.get("inputs_json") or "")
        correction = inputs.get("scope_correction") if isinstance(inputs, dict) else None
        source_ids = inputs.get("source_ids") if isinstance(inputs, dict) else None
    except (TypeError, ValueError):
        raise ValueError("scope correction Evidence inputs are invalid") from None
    old_scope = {"domain_id": domain_id, "product_id": product_id, "global": False}
    old_scope["subject_id" if domain_id == "cth" else "brand_focus_id"] = (
        expected_subject_id if domain_id == "cth" else expected_brand_focus_id
    )
    if (
        not isinstance(correction, dict)
        or correction.get("expected_scope_evidence_ref") != expected_scope_evidence_ref
        or correction.get("target_scope_status") != "UNASSIGNED"
        or correction.get("target_subject_id") is not None
        or correction.get("target_brand_focus_id") is not None
        or not isinstance(source_ids, list)
        or source_id not in source_ids
        or inputs.get("_lumenis_scope") != old_scope
    ):
        raise ValueError("scope correction Evidence does not bind the expected old scope and source")

    row = con.execute(
        f"SELECT product_id, domain_id, subject_id, brand_focus_id, scope_status, "
        f"scope_evidence_ref FROM {CANONICAL_TABLE} WHERE external_id=? LIMIT 1",
        (source_id,),
    ).fetchone()
    expected = (
        product_id, domain_id, expected_subject_id or "",
        expected_brand_focus_id or "", "VERIFIED", str(expected_scope_evidence_ref),
    )
    if row is None or tuple(row) != expected:
        raise ValueError("Canonical source scope changed since the correction was reviewed")
    updated = con.execute(
        f"UPDATE {CANONICAL_TABLE} SET subject_id='', brand_focus_id='', "
        "scope_status='UNASSIGNED', scope_evidence_ref='' "
        "WHERE external_id=? AND product_id=? AND domain_id=? AND subject_id=? "
        "AND brand_focus_id=? AND scope_status='VERIFIED' AND scope_evidence_ref=?",
        (source_id, product_id, domain_id, expected_subject_id or "",
         expected_brand_focus_id or "", str(expected_scope_evidence_ref)),
    )
    if updated.rowcount != 1:
        raise ValueError("Canonical scope correction lost its expected-old compare-and-set")


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
    product_id, domain_id = _inbound_canonical_identity(note_row, product_id)
    note_id = _safe_str(note_row.get("note_id"))
    publish_dt = _safe_str(note_row.get("publish_datetime") or note_row.get("publish_date"))
    captured = _safe_str(note_row.get("captured_at") or note_row.get("collected_at"))

    rec = CanonicalRecord(
        canonical_id=f"can_note_{note_id}" if note_id else _new_canonical_id("can_note"),
        product_id=product_id,
        domain_id=domain_id,
        subject_id=_safe_str(note_row.get("subject_id")),
        brand_focus_id=_safe_str(note_row.get("brand_focus_id")),
        scope_status=_safe_str(note_row.get("scope_status") or "UNASSIGNED").upper(),
        scope_evidence_ref=_safe_str(note_row.get("scope_evidence_ref")),
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
        sentiment=_safe_str(note_row.get("sentiment") or SENTIMENT_UNKNOWN),
        sentiment_score=_safe_float_or_none(note_row.get("sentiment_score")),
        risk_level=_safe_str(note_row.get("risk_level") or RISK_UNKNOWN),
        risk_score=_safe_int_or_none(note_row.get("risk_score")),
        quality_status=_safe_str(note_row.get("data_quality_status") or "unknown"),
        quality_score=_safe_float_or_none(note_row.get("data_quality_score") or note_row.get("content_quality_score")),
        confidence=_safe_float_or_none(note_row.get("verification_confidence")),
        relevance_status=_safe_str(note_row.get("relevance_status") or "unknown"),
        verification_status=_safe_str(note_row.get("verification_status") or "review"),
        subject_type=_safe_str(note_row.get("subject_type")),
        content_type=_safe_str(note_row.get("content_type")),
        engagement_likes=engagement_count(note_row.get("likes")),
        engagement_comments=engagement_count(note_row.get("comments")),
        engagement_collects=engagement_count(note_row.get("collects")),
        engagement_shares=engagement_count(note_row.get("shares")),
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
    product_id, domain_id = _inbound_canonical_identity(web_row, product_id)
    source_id = _safe_str(web_row.get("source_id"))
    publish_dt = _safe_str(web_row.get("published_at"))
    captured = _safe_str(web_row.get("fetched_at"))

    rec = CanonicalRecord(
        canonical_id=f"can_web_{source_id}" if source_id else _new_canonical_id("can_web"),
        product_id=product_id,
        domain_id=domain_id,
        subject_id=_safe_str(web_row.get("subject_id")),
        brand_focus_id=_safe_str(web_row.get("brand_focus_id")),
        scope_status=_safe_str(web_row.get("scope_status") or "UNASSIGNED").upper(),
        scope_evidence_ref=_safe_str(web_row.get("scope_evidence_ref")),
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
        sentiment=SENTIMENT_UNKNOWN,
        sentiment_score=None,
        risk_level=RISK_UNKNOWN,
        risk_score=None,
        quality_status="unknown",
        quality_score=None,
        confidence=None,
        relevance_status=_safe_str(web_row.get("relevance") or "pending"),
        verification_status=_safe_str(web_row.get("verification") or "review"),
        subject_type="media",  # 网页提及默认媒体类
        content_type="news",  # 默认新闻类
        engagement_likes=None,  # web_mentions 无互动字段，显式标记缺失
        engagement_comments=None,
        engagement_collects=None,
        engagement_shares=None,
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
    """将 lumenis CollectedNote（dataclass）转化为 CanonicalRecord。

    调用链：CollectedNote (lumenis/adapters/base.py:25)
            → collected_note_to_canonical() → canonical_data 表
    文件: canonical_data.py:320

    时间口径（P0 红线）：
      - publish_datetime ← collected.publish_date（平台发布时间）
      - captured_at ← 当前采集时刻（本函数写入）
    """
    identity = {
        key: getattr(collected, key)
        for key in ("product_id", "domain_id") if hasattr(collected, key)
    }
    product_id, domain_id = _inbound_canonical_identity(identity, product_id)
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
        domain_id=domain_id,
        subject_id=_safe_str(getattr(collected, "subject_id", "")),
        brand_focus_id=_safe_str(getattr(collected, "brand_focus_id", "")),
        scope_status=_safe_str(getattr(collected, "scope_status", "UNASSIGNED") or "UNASSIGNED").upper(),
        scope_evidence_ref=_safe_str(getattr(collected, "scope_evidence_ref", "")),
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
        sentiment=_safe_str(getattr(collected, "sentiment", "") or SENTIMENT_UNKNOWN),
        sentiment_score=_safe_float_or_none(getattr(collected, "sentiment_score", None)),
        risk_level=_safe_str(getattr(collected, "risk_level", "") or RISK_UNKNOWN),
        risk_score=_safe_int_or_none(getattr(collected, "risk_score", None)),
        quality_status="unknown",
        quality_score=_safe_float_or_none(getattr(collected, "quality_score", None)),
        confidence=_safe_float_or_none(getattr(collected, "confidence", None)),
        relevance_status="unverified",
        verification_status="pending",
        subject_type="normal_user",
        content_type="ugc",
        engagement_likes=engagement_count(getattr(collected, "likes", None)),
        engagement_comments=engagement_count(getattr(collected, "comments", None)),
        engagement_collects=engagement_count(getattr(collected, "collects", None)),
        engagement_shares=engagement_count(getattr(collected, "shares", None)),
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
    product_id, _ = _canonical_record_identity(product_id)
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


def validate_source_ids(source_ids: list[str] | None, *, limit: int = 100) -> list[str] | None:
    """Validate an exact, bounded Canonical source selection without reading storage."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer between 1 and 100")
    if source_ids is None:
        return None
    if type(source_ids) is not list or not 1 <= len(source_ids) <= 100:
        raise ValueError("source_ids must be a list containing 1 to 100 IDs")
    if len(source_ids) > limit:
        raise ValueError("source_ids cannot exceed limit")

    selected: list[str] = []
    for source_id in source_ids:
        if (type(source_id) is not str or not source_id
                or source_id != source_id.strip() or len(source_id) > 512
                or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in source_id)):
            raise ValueError("source_ids must contain exact nonblank strings up to 512 characters without control characters")
        selected.append(source_id)
    if len(set(selected)) != len(selected):
        raise ValueError("source_ids must be unique")
    return selected


# Shared source identity projection. Conflicting/duplicate parents stay visible.
CANONICAL_SOURCE_LEVEL_PREDICATE = """(
            source_type <> 'document_row'
            OR NOT EXISTS (
                SELECT 1 FROM canonical_data AS parent
                WHERE parent.source_id=canonical_data.source_id
                  AND parent.product_id=canonical_data.product_id
                  AND parent.source_type='document'
                  AND parent.scope_evidence_ref=canonical_data.scope_evidence_ref
                  AND parent.domain_id=canonical_data.domain_id
                  AND COALESCE(parent.subject_id,'')=COALESCE(canonical_data.subject_id,'')
                  AND COALESCE(parent.brand_focus_id,'')=COALESCE(canonical_data.brand_focus_id,'')
                  AND 1=(
                      SELECT COUNT(*) FROM canonical_data AS parent_count
                      WHERE parent_count.source_id=canonical_data.source_id
                        AND parent_count.product_id=canonical_data.product_id
                        AND parent_count.source_type='document'
                  )
            )
        )"""


def list_scoped_canonical(
    con: sqlite3.Connection, *, product_id: str, subject_id: Optional[str] = None,
    brand_focus_id: Optional[str] = None, limit: int = 30,
    source_ids: list[str] | None = None, source_level: bool = False,
) -> Dict[str, Any]:
    """Read Canonical rows only when their exact signed scope still verifies."""
    if not isinstance(con, sqlite3.Connection):
        raise TypeError("con must be a SQLite connection")
    if type(product_id) is not str:
        raise TypeError("product_id must be a string")
    products = {"CTH": (PRODUCT_CTH, "cth"), "cth": (PRODUCT_CTH, "cth"),
                "ZBMP": (PRODUCT_ZBMP, "zbmp"), "zbmp": (PRODUCT_ZBMP, "zbmp"),
                "BMP": (PRODUCT_ZBMP, "zbmp"), "bmp": (PRODUCT_ZBMP, "zbmp")}
    if product_id not in products:
        raise ValueError("product_id must be CTH/cth or ZBMP/zbmp")
    if type(limit) is not int:
        raise TypeError("limit must be an integer")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if type(source_level) is not bool:
        raise TypeError("source_level must be an explicit boolean")
    source_ids = validate_source_ids(source_ids, limit=limit)

    def validate_focus(value: Optional[str], name: str) -> Optional[str]:
        if value is None:
            return None
        if type(value) is not str:
            raise TypeError(f"{name} must be a string or None")
        if not value or value != value.strip():
            raise ValueError(f"{name} must be a non-empty exact string")
        return value

    subject_id = validate_focus(subject_id, "subject_id")
    brand_focus_id = validate_focus(brand_focus_id, "brand_focus_id")
    if subject_id is not None and brand_focus_id is not None:
        raise ValueError("subject_id and brand_focus_id cannot be mixed")
    product, domain = products[product_id]
    if product == PRODUCT_CTH and brand_focus_id is not None:
        raise ValueError("CTH reads accept subject_id only")
    if product == PRODUCT_ZBMP and subject_id is not None:
        raise ValueError("ZBMP reads accept brand_focus_id only")

    where = ["product_id=?", "domain_id=?"]
    params: List[Any] = [product, domain]
    focus = subject_id if product == PRODUCT_CTH else brand_focus_id
    focus_column = "subject_id" if product == PRODUCT_CTH else "brand_focus_id"
    other_column = "brand_focus_id" if product == PRODUCT_CTH else "subject_id"
    if focus is not None:
        where.extend([f"{focus_column}=?", f"({other_column} IS NULL OR {other_column}='')"])
        params.append(focus)
    if source_ids is not None:
        where.append("source_id IN (" + ",".join("?" for _ in source_ids) + ")")
        params.extend(source_ids)
    if source_level:
        # A selected document row is a Canonical projection of its parent
        # source, not another source-level sample. Hide that projection only
        # when its unique parent has the same signed Evidence and exact scope.
        # Duplicated parents or mismatched Evidence/scope remain visible so the
        # Source Brief owner can fail closed instead of masking the conflict.
        where.append(CANONICAL_SOURCE_LEVEL_PREDICATE)
    predicate = " AND ".join(where)
    candidate_count = con.execute(
        f"SELECT COUNT(*) FROM {CANONICAL_TABLE} WHERE {predicate}", tuple(params),
    ).fetchone()[0]
    cursor = con.execute(
        f"SELECT * FROM {CANONICAL_TABLE} WHERE {predicate} "
        "ORDER BY captured_at DESC, canonical_id ASC LIMIT ?",
        tuple(params + [limit]),
    )
    columns = [column[0] for column in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    records: List[Dict[str, Any]] = []
    rejected_count = 0
    for row in rows:
        record = CanonicalRecord()
        for field_name in (
            "canonical_id", "product_id", "domain_id", "subject_id",
            "brand_focus_id", "scope_status", "scope_evidence_ref", "source_id",
        ):
            setattr(record, field_name, row.get(field_name))
        try:
            proof = _validate_canonical_scope(con, record)
        except ValueError:
            rejected_count += 1
            continue
        if proof is None:
            rejected_count += 1
            continue
        row["scope_evidence"] = proof
        records.append(row)

    scanned_count = len(rows)
    return {
        "records": records,
        "candidate_count": candidate_count,
        "scanned_count": scanned_count,
        "rejected_count": rejected_count,
        "returned_count": len(records),
        "limit": limit,
        "truncated": candidate_count > scanned_count,
    }


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
# FUNC-CONTENT-02: 情感分析单一真相源（P0 红线：禁止双口径）
# ============================================================
def unified_sentiment_analysis(title, content="", topics=None, return_reasons=False):
    """统一情感分析入口（单一真相源）。

    P0 红线：ai_analyzer.py 与 topic_campaign.py 不得各自实现情感分析口径。
    所有情感分析必须通过本函数，底层委托 ai_analyzer.analyze_sentiment（主规则引擎）。
    canonical_data.sentiment 字段为存储层单一真相源。
    """
    try:
        from ai_analyzer import analyze_sentiment as _aa_sentiment
        return _aa_sentiment(title, content, topics, return_reasons)
    except Exception:
        t = (title or "").lower()
        c = (content or "").lower()
        text = t + " " + c
        neg = any(w in text for w in ("垃圾", "投诉", "失望", "避雷", "维权", "退款", "差", "坑"))
        pos = any(w in text for w in ("好", "赞", "喜欢", "推荐", "满意", "棒", "优秀"))
        if neg and not pos:
            return {"sentiment": "negative", "score": -0.5, "reasons": ["fallback"]} if return_reasons else "negative"
        if pos and not neg:
            return {"sentiment": "positive", "score": 0.5, "reasons": ["fallback"]} if return_reasons else "positive"
        return {"sentiment": "neutral", "score": 0.0, "reasons": ["fallback"]} if return_reasons else "neutral"


# ============================================================
# 去重精准（P0 红线：content_hash + platform_id 组合键）
# ============================================================
def dedup_key(content_hash, platform_id):
    """生成去重键：content_hash + platform_id 组合。"""
    if not content_hash or not platform_id:
        return None
    return f"{platform_id}:{content_hash}"


def find_duplicates(con, content_hash, platform_id, canonical_id=None):
    """查找与给定 content_hash + platform_id 重复的记录。"""
    if not content_hash or not platform_id:
        return []
    sql = f"SELECT canonical_id FROM {CANONICAL_TABLE} WHERE content_hash=? AND source_platform=?"
    params = [content_hash, platform_id]
    if canonical_id:
        sql += " AND canonical_id != ?"
        params.append(canonical_id)
    rows = con.execute(sql, tuple(params)).fetchall()
    return [r[0] for r in rows]


def is_duplicate(con, content_hash, platform_id, canonical_id=None):
    """判断是否存在重复记录（content_hash + platform_id 组合）。"""
    return len(find_duplicates(con, content_hash, platform_id, canonical_id)) > 0


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
    con = DatabaseRepository(db_path).connect(timeout=15)
    try:
        con.execute(SCHEMA_VERSION_DDL)
        con.commit()
    finally:
        con.close()


def register_schema_version(db_path: str, version: str, description: str,
                             applied_by: str = "t4-canonical") -> None:
    """注册一条 schema 版本记录。"""
    ensure_schema_version_table(db_path)
    con = DatabaseRepository(db_path).connect(timeout=15)
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
    con = DatabaseRepository(db_path).connect(timeout=15)
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
    con = DatabaseRepository(db_path).connect(timeout=15)
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
    from core.repository_registry import get_db_path
    db = get_db_path()
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
