# -*- coding: utf-8 -*-
"""
ZBC 历史数据适配性融合迁移脚本 v2（可重跑 / 幂等 / 只增不删）

管线：Raw → Normalize(字段映射当前72表schema) → subject_rules红线重判
     → 质量门禁 → Canonical(content_hash/provenance/rule_version)
     → Domain打product_id → 幂等upsert(note_id/platform_id/content_hash)

硬约束（audit/HISTORICAL_MIGRATION_PLAN_V1.0.md §8）：
1. publish_date/publish_datetime 100%回填；复用 v4_upgrade/data_cleanup/fix_publish_date.py
2. topic_campaign taikoo_15th 任务完整保留：paused状态/起止日期/240min间隔/7 topic/120笔记/325快照时间线
3. 本地审计优先：不复用已存在模块，产出reusable/adapt/missing清单

铁律：
- 旧53表只做字段映射，绝不照搬schema覆盖当前主线
- subject_hit重判，不沿用旧is_taikoo_verified标签
- publish_datetime(平台发布) ≠ captured_at(采集时刻)
- content_hash+platform_id精准去重，缺失显式null不填0
- 域归属：太古汇相关=CTH，品牌传播=ZBMP，拿不准=unknown
- 只增不删、幂等可重跑、不碰源与备份

用法：
  python scripts/migrate_historical_data.py --dry-run          # 只对账不写入
  python scripts/migrate_historical_data.py --trial --limit 30 # 小批试迁每表30条
  python scripts/migrate_historical_data.py                     # 全量迁移
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 路径配置
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

OLD_DB = os.path.join(BASE_DIR, "data", "_old_staging_ref.db")
NEW_DB = os.path.join(BASE_DIR, "data", "monitor.db")
AUDIT_DIR = os.path.join(BASE_DIR, "audit")
os.makedirs(AUDIT_DIR, exist_ok=True)

RULE_VERSION = "hist-v1.0"
PROVENANCE_TAG = "historical_import:staging_db_20260901"

# ============================================================
# 导入当前项目模块
# ============================================================
from subject_rules import subject_hit, subject_reason, SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS  # noqa: E402
from database import get_db, DB_PATH  # noqa: E402

# 硬约束#1：复用 fix_publish_date.py 的 parse_relative_date，不重写
try:
    from v4_upgrade.data_cleanup.fix_publish_date import (
        parse_relative_date as _canonical_parse_relative_date,
        fix_publish_dates as _canonical_fix_publish_dates,
        backfill_captured_from_collected as _canonical_backfill_captured,
    )
    _FIX_PUBLISH_AVAILABLE = True
except ImportError:
    _FIX_PUBLISH_AVAILABLE = False
    # fallback：内联最小实现（仅当模块不可用时）
    def _canonical_parse_relative_date(raw, captured_at=None, collected_at=None):
        if not raw:
            return raw
        raw = str(raw).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}", raw):
            return raw[:10]
        return raw

# ============================================================
# 工具函数
# ============================================================

def _md5_short(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]


def _safe_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val)


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        if val is None or val == "":
            return default
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def _normalize_publish_time(raw: str, captured_at: str = "", collected_at: str = "") -> str:
    """
    双时间铁律：发布时间归一化。
    硬约束#1：复用 fix_publish_date.parse_relative_date，不重写。
    处理 GDELT格式(20260826T003000Z)、相对时间、残缺日期。
    """
    if not raw or not isinstance(raw, str):
        return ""
    t = raw.strip()

    # GDELT格式：20260826T003000Z
    m = re.match(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$", t)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}:{m.group(6)}"

    # ISO带T
    if re.match(r"^\d{4}-\d{2}-\d{2}T", t):
        return t.replace("T", " ").replace("Z", "")

    # 已经是绝对时间
    if re.match(r"^\d{4}-\d{2}-\d{2}", t):
        return t

    # 复用 canonical parse_relative_date（返回YYYY-MM-DD）
    parsed = _canonical_parse_relative_date(t, captured_at or None, collected_at or None)
    if parsed and re.match(r"^\d{4}-\d{2}-\d{2}", parsed):
        return parsed[:10]

    # "MM-DD地域" 格式（评论时间如 08-12广东）
    m = re.match(r"^(\d{1,2})-(\d{1,2})", t)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        ref = datetime.now()
        if captured_at:
            try:
                ref = datetime.strptime(captured_at[:10], "%Y-%m-%d")
            except ValueError:
                pass
        year = ref.year
        if month > ref.month or (month == ref.month and day > ref.day):
            year -= 1
        try:
            return f"{year}-{month:02d}-{day:02d}"
        except ValueError:
            pass

    return t  # 无法解析，保留原值（不伪造）


def _classify_domain(title: str, content: str, source_platform: str,
                      source_keyword: str = "", matched_keywords: str = "") -> Tuple[str, str]:
    """双域归属：CTH=太古汇主体命中，ZBMP=web品牌传播，unknown=拿不准。"""
    is_cth = subject_hit(title=title, body=content, content=content,
                          source_keyword=source_keyword, matched_keywords=matched_keywords)
    if is_cth:
        return "CTH", "subject_hit:太古汇主体词命中"
    if source_platform and source_platform not in ("xhs", "xiaohongshu", ""):
        if "web" in source_platform.lower() or source_platform in (
            "gdelt", "sogou_search", "baidu", "weibo", "bilibili", "zhihu"
        ):
            return "ZBMP", "web_platform:品牌传播域"
    return "unknown", "domain_unclear:非CTH主体且非明确ZBMP来源"


def _quality_gate(note: Dict[str, Any]) -> Tuple[str, float, str]:
    """质量门禁：ok/warn/error + 分数 + 原因。"""
    score = 100.0
    reasons = []
    title = _safe_str(note.get("title", "")).strip()
    url = _safe_str(note.get("url", "")).strip()
    pub = _safe_str(note.get("publish_datetime", "") or note.get("publish_date", "")).strip()
    content = _safe_str(note.get("content", "")).strip()
    if not title:
        score -= 30; reasons.append("缺标题")
    if not url:
        score -= 20; reasons.append("缺URL")
    if not pub:
        score -= 25; reasons.append("缺发布时间")
    if not content or len(content) < 10:
        score -= 15; reasons.append("正文过短/缺失")
    score = max(0.0, score)
    status = "ok" if score >= 80 else ("warn" if score >= 50 else "error")
    return status, score, ";".join(reasons) if reasons else "all_core_fields_present"


# ============================================================
# 旧库读取
# ============================================================

class OldDBReader:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, timeout=30)
        self.conn.row_factory = sqlite3.Row

    def read_table(self, table: str, limit: int = 0, offset: int = 0) -> List[Dict]:
        sql = f"SELECT * FROM [{table}]"
        params = []
        if limit > 0:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def count(self, table: str) -> int:
        try:
            return self.conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    def close(self):
        self.conn.close()


# ============================================================
# 迁移结果
# ============================================================

class MigrationResult:
    def __init__(self, table: str):
        self.table = table
        self.source_count = 0
        self.inserted = 0
        self.updated = 0
        self.failed = 0
        self.failures: List[str] = []
        self.cth_count = 0
        self.zbmp_count = 0
        self.unknown_count = 0

    def to_dict(self) -> Dict:
        return {
            "table": self.table, "source_count": self.source_count,
            "inserted": self.inserted, "updated": self.updated,
            "failed": self.failed, "failures": self.failures[:10],
            "cth_count": self.cth_count, "zbmp_count": self.zbmp_count,
            "unknown_count": self.unknown_count,
        }


# ============================================================
# notes 迁移（核心管线）
# ============================================================

def migrate_notes(reader: OldDBReader, limit: int = 0, dry_run: bool = False) -> MigrationResult:
    result = MigrationResult("notes")
    result.source_count = reader.count("notes")
    rows = reader.read_table("notes", limit=limit)
    print(f"  [notes] 读取 {len(rows)} 条 / 源总数 {result.source_count}")

    with get_db() as conn:
        for idx, row in enumerate(rows):
            try:
                note_id = _safe_str(row.get("note_id", "")).strip()
                if not note_id:
                    result.failed += 1; result.failures.append(f"row{idx}: empty note_id"); continue

                title = _safe_str(row.get("title", ""))
                content = _safe_str(row.get("content", ""))
                body = _safe_str(row.get("body", "")) or content
                source_platform = _safe_str(row.get("source_platform", "xhs")) or "xhs"
                source_keyword = _safe_str(row.get("source_keyword", ""))
                matched_keywords = _safe_str(row.get("matched_keywords", ""))
                url = _safe_str(row.get("url", ""))

                # subject_rules红线重判
                is_subject = subject_hit(title=title, body=body, content=content,
                                          source_keyword=source_keyword, matched_keywords=matched_keywords)
                subject_reason_str = subject_reason({"title": title, "body": body, "content": content,
                    "source_keyword": source_keyword, "matched_keywords": matched_keywords})

                # 双时间铁律
                old_pub_dt = _safe_str(row.get("publish_datetime", ""))
                old_pub_date = _safe_str(row.get("publish_date", ""))
                old_captured = _safe_str(row.get("captured_at", ""))
                old_collected = _safe_str(row.get("collected_at", ""))

                publish_datetime = _normalize_publish_time(
                    old_pub_dt or old_pub_date, captured_at=old_captured, collected_at=old_collected)
                publish_date = publish_datetime[:10] if publish_datetime else (old_pub_date[:10] if old_pub_date else "")
                captured_at = _normalize_publish_time(old_captured or old_collected)

                # 质量门禁
                q_status, q_score, q_reason = _quality_gate({
                    "title": title, "url": url, "publish_datetime": publish_datetime, "content": content})

                # Canonical
                content_hash = _md5_short(f"{title}|{body}|{note_id}")
                provenance = PROVENANCE_TAG
                rule_version = RULE_VERSION

                # Domain
                product_id, domain_reason = _classify_domain(
                    title, body, source_platform, source_keyword, matched_keywords)
                if product_id == "CTH": result.cth_count += 1
                elif product_id == "ZBMP": result.zbmp_count += 1
                else: result.unknown_count += 1

                vals = {
                    "note_id": note_id, "source_platform": source_platform, "title": title,
                    "content": content, "url": url, "cover": _safe_str(row.get("cover", "")),
                    "author_id": _safe_str(row.get("author_id", "")),
                    "author_nickname": _safe_str(row.get("author_nickname", "")),
                    "author_avatar": _safe_str(row.get("author_avatar", "")),
                    "likes": _safe_int(row.get("likes")), "comments": _safe_int(row.get("comments")),
                    "collects": _safe_int(row.get("collects")), "shares": _safe_int(row.get("shares")),
                    "note_type": _safe_str(row.get("note_type", "normal")) or "normal",
                    "xsec_token": _safe_str(row.get("xsec_token", "")),
                    "publish_date": publish_date, "publish_datetime": publish_datetime,
                    "collected_at": old_collected, "captured_at": captured_at,
                    "detail_fetched_at": _safe_str(row.get("detail_fetched_at", "")),
                    "comments_fetched_at": _safe_str(row.get("comments_fetched_at", "")),
                    "comments_collected": _safe_int(row.get("comments_collected")),
                    "sentiment": _safe_str(row.get("sentiment", "neutral")) or "neutral",
                    "sentiment_score": _safe_float(row.get("sentiment_score")),
                    "risk_level": _safe_str(row.get("risk_level", "low")) or "low",
                    "risk_score": _safe_int(row.get("risk_score")),
                    "summary": _safe_str(row.get("summary", "")),
                    "topics": _safe_str(row.get("topics", "[]")) or "[]",
                    "ai_provider": _safe_str(row.get("ai_provider", "rule")) or "rule",
                    "ai_analyzed_at": _safe_str(row.get("ai_analyzed_at", "")),
                    "is_official": _safe_int(row.get("is_official")),
                    "category": _safe_str(row.get("category", "other")) or "other",
                    "status": _safe_str(row.get("status", "active")) or "active",
                    "last_seen_at": _safe_str(row.get("last_seen_at", "")) or captured_at,
                    "is_taikoo_verified": 1 if is_subject else 0,
                    "verify_reason": subject_reason_str,
                    "relevance_status": _safe_str(row.get("relevance_status", "relevant")) or "relevant",
                    "verification_status": _safe_str(row.get("verification_status", "review")) or "review",
                    "verification_confidence": _safe_float(row.get("verification_confidence")),
                    "fact_basis": _safe_str(row.get("fact_basis", "text")) or "text",
                    "ai_reason": _safe_str(row.get("ai_reason", "")),
                    "event_hint": _safe_str(row.get("event_hint", "")),
                    "translations": _safe_str(row.get("translations", "{}")) or "{}",
                    "relevance_score": _safe_float(row.get("relevance_score"), 1.0),
                    "content_quality": _safe_float(row.get("content_quality"), 0.5),
                    "duplicate_of": _safe_str(row.get("duplicate_of", "")),
                    "ai_model": _safe_str(row.get("ai_model", "")),
                    "last_reviewed_at": _safe_str(row.get("last_reviewed_at", "")),
                    "ai_filter_status": _safe_str(row.get("ai_filter_status", "pending")) or "pending",
                    "ai_filter_reason": _safe_str(row.get("ai_filter_reason", "")),
                    "ai_filtered_at": _safe_str(row.get("ai_filtered_at", "")),
                    "content_quality_score": _safe_float(row.get("content_quality_score"), 0.5),
                    "is_duplicate": _safe_int(row.get("is_duplicate")),
                    "noise_type": _safe_str(row.get("noise_type", "")),
                    "ai_insight": _safe_str(row.get("ai_insight", "")),
                    "data_quality_status": q_status, "data_quality_score": q_score,
                    "collector_version": _safe_str(row.get("collector_version", "")) or "historical_import",
                    "body": body, "source_keyword": source_keyword, "matched_keywords": matched_keywords,
                    "negative_confirmed": _safe_int(row.get("negative_confirmed")),
                    "content_hash": content_hash, "provenance": provenance,
                    "rule_version": rule_version, "product_id": product_id,
                }

                if dry_run:
                    existing = conn.execute("SELECT id FROM notes WHERE note_id=?", (note_id,)).fetchone()
                    if existing: result.updated += 1
                    else: result.inserted += 1
                    continue

                existing = conn.execute("SELECT id FROM notes WHERE note_id=?", (note_id,)).fetchone()
                if existing:
                    # UPDATE：空值才覆盖，核心字段强制更新
                    set_clauses = []
                    update_params = []
                    for k, v in vals.items():
                        if k == "note_id":
                            continue
                        if k in ("likes", "comments", "collects", "shares", "risk_score",
                                 "sentiment_score", "comments_collected", "is_taikoo_verified",
                                 "data_quality_score"):
                            set_clauses.append(f"{k}=?")
                        else:
                            set_clauses.append(f"{k}=COALESCE(NULLIF(?, ''), {k})")
                        update_params.append(v)
                    update_params.append(note_id)
                    conn.execute(f"UPDATE notes SET {', '.join(set_clauses)} WHERE note_id=?", update_params)
                    # 强制写入新增字段（确保非空）
                    conn.execute(
                        "UPDATE notes SET content_hash=?, provenance=?, rule_version=?, product_id=?, "
                        "is_taikoo_verified=?, verify_reason=?, data_quality_status=?, data_quality_score=? "
                        "WHERE note_id=?",
                        (content_hash, provenance, rule_version, product_id,
                         1 if is_subject else 0, subject_reason_str, q_status, q_score, note_id))
                    result.updated += 1
                else:
                    cols = list(vals.keys())
                    placeholders = ", ".join(["?"] * len(cols))
                    conn.execute(f"INSERT INTO notes ({', '.join(cols)}) VALUES ({placeholders})",
                                 [vals[c] for c in cols])
                    result.inserted += 1

                # metric_snapshots（旁路，不阻断）
                try:
                    conn.execute(
                        "INSERT INTO metric_snapshots(entity_type,entity_key,likes,comments,collects,shares,"
                        "browse_count,discussion_count,note_count,source,collector_version,snapshot_at) "
                        "VALUES('note',?,?,?,?,?,NULL,NULL,NULL,?,?,?)",
                        (note_id, vals["likes"], vals["comments"], vals["collects"], vals["shares"],
                         "historical_import", "hist-v1.0",
                         captured_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                except Exception:
                    pass

            except Exception as e:
                result.failed += 1
                result.failures.append(f"row{idx}: {str(e)[:120]}")
                if result.failed <= 3:
                    print(f"    [WARN] notes row{idx} failed: {e}")

    return result


# ============================================================
# 通用简单表迁移（schema兼容，排除id列）
# ============================================================

def migrate_simple_table(reader: OldDBReader, table: str, unique_key: str,
                          limit: int = 0, dry_run: bool = False) -> MigrationResult:
    """
    通用表迁移：schema完全兼容的表直接upsert。
    两种模式：
    - unique_key != 'id'（业务唯一键）：排除id列，按业务键upsert
    - unique_key == 'id'（append-only审计/日志表）：包含id列，INSERT OR IGNORE（幂等、保留旧id）
    """
    result = MigrationResult(table)
    result.source_count = reader.count(table)
    rows = reader.read_table(table, limit=limit)
    if not rows:
        return result
    print(f"  [{table}] 读取 {len(rows)} 条 / 源总数 {result.source_count}")

    is_id_key = (unique_key == "id")

    with get_db() as conn:
        new_cols = {r[1] for r in conn.execute(f"PRAGMA table_info([{table}])").fetchall()}

    for idx, row in enumerate(rows):
        try:
            if is_id_key:
                # id主键表：包含id，用INSERT OR IGNORE
                filtered = {k: v for k, v in row.items() if k in new_cols}
                if "id" not in filtered or filtered["id"] is None:
                    result.failed += 1; continue
            else:
                # 业务键表：排除id
                filtered = {k: v for k, v in row.items() if k in new_cols and k != "id"}
                if not filtered or unique_key not in filtered:
                    result.failed += 1
                    result.failures.append(f"row{idx}: missing key")
                    continue

            key_val = _safe_str(filtered[unique_key])
            if not key_val and not is_id_key:
                result.failed += 1; continue

            with get_db() as conn:
                if dry_run:
                    if is_id_key:
                        existing = conn.execute(
                            f"SELECT 1 FROM [{table}] WHERE id=?", (filtered["id"],)).fetchone()
                    else:
                        existing = conn.execute(
                            f"SELECT 1 FROM [{table}] WHERE [{unique_key}]=?", (key_val,)).fetchone()
                    if existing: result.updated += 1
                    else: result.inserted += 1
                    continue

                cols = list(filtered.keys())
                if is_id_key:
                    # INSERT OR IGNORE：id冲突则跳过（幂等）
                    placeholders = ", ".join(["?"] * len(cols))
                    try:
                        conn.execute(
                            f"INSERT OR IGNORE INTO [{table}] ({', '.join(cols)}) VALUES ({placeholders})",
                            [filtered[c] for c in cols])
                        if conn.total_changes > 0:
                            result.inserted += 1
                        else:
                            result.updated += 1  # 被IGNORE=已存在
                    except Exception:
                        result.failed += 1
                else:
                    existing = conn.execute(
                        f"SELECT 1 FROM [{table}] WHERE [{unique_key}]=?", (key_val,)).fetchone()
                    if existing:
                        set_clause = ", ".join([f"{c}=?" for c in cols if c != unique_key])
                        params = [filtered[c] for c in cols if c != unique_key] + [key_val]
                        conn.execute(f"UPDATE [{table}] SET {set_clause} WHERE [{unique_key}]=?", params)
                        result.updated += 1
                    else:
                        placeholders = ", ".join(["?"] * len(cols))
                        conn.execute(f"INSERT INTO [{table}] ({', '.join(cols)}) VALUES ({placeholders})",
                                     [filtered[c] for c in cols])
                        result.inserted += 1
        except Exception as e:
            result.failed += 1
            result.failures.append(f"row{idx}: {str(e)[:120]}")

    return result


# ============================================================
# topic_campaign_notes 迁移（24→16列适配）
# ============================================================

def migrate_topic_campaign_notes(reader: OldDBReader, limit: int = 0,
                                   dry_run: bool = False) -> MigrationResult:
    result = MigrationResult("topic_campaign_notes")
    result.source_count = reader.count("topic_campaign_notes")
    rows = reader.read_table("topic_campaign_notes", limit=limit)
    print(f"  [topic_campaign_notes] 读取 {len(rows)} 条 / 源总数 {result.source_count}")

    NEW_COLS = {"campaign_key", "topic", "note_id", "title", "content", "author",
                 "publish_datetime", "likes", "comments", "collects", "shares",
                 "note_url", "first_seen_at", "last_seen_at", "raw_json"}

    with get_db() as conn:
        for idx, row in enumerate(rows):
            try:
                filtered = {k: v for k, v in row.items() if k in NEW_COLS}
                note_id = _safe_str(filtered.get("note_id", ""))
                campaign_key = _safe_str(filtered.get("campaign_key", ""))
                if not note_id or not campaign_key:
                    result.failed += 1; continue

                # publish_datetime归一化
                pub = _safe_str(filtered.get("publish_datetime", ""))
                filtered["publish_datetime"] = _normalize_publish_time(
                    pub, captured_at=_safe_str(row.get("first_seen_at", "")))

                if dry_run:
                    result.inserted += 1; continue

                existing = conn.execute(
                    "SELECT id FROM topic_campaign_notes WHERE campaign_key=? AND note_id=?",
                    (campaign_key, note_id)).fetchone()
                cols = list(filtered.keys())
                if existing:
                    set_clause = ", ".join([f"{c}=?" for c in cols if c not in ("campaign_key", "note_id")])
                    params = [filtered[c] for c in cols if c not in ("campaign_key", "note_id")]
                    params.extend([campaign_key, note_id])
                    conn.execute(f"UPDATE topic_campaign_notes SET {set_clause} WHERE campaign_key=? AND note_id=?", params)
                    result.updated += 1
                else:
                    placeholders = ", ".join(["?"] * len(cols))
                    conn.execute(f"INSERT INTO topic_campaign_notes ({', '.join(cols)}) VALUES ({placeholders})",
                                 [filtered[c] for c in cols])
                    result.inserted += 1
            except Exception as e:
                result.failed += 1
                result.failures.append(f"row{idx}: {str(e)[:120]}")
    return result


# ============================================================
# topic_campaigns 迁移（硬约束#2：保留paused状态/起止日期/间隔）
# ============================================================

def migrate_topic_campaigns(reader: OldDBReader, dry_run: bool = False) -> MigrationResult:
    """
    硬约束#2：topic_campaign taikoo_15th 必须完整保留：
    - status=paused（不被新库active覆盖）
    - start_date=2026-08-28, end_date=2026-10-07
    - interval_minutes=240
    - created_at/updated_at 保留旧库时间戳
    """
    result = MigrationResult("topic_campaigns")
    result.source_count = reader.count("topic_campaigns")
    rows = reader.read_table("topic_campaigns")
    print(f"  [topic_campaigns] 读取 {len(rows)} 条 / 源总数 {result.source_count}")

    NEW_COLS = {"campaign_key", "name", "start_date", "end_date", "status",
                 "interval_minutes", "created_at", "updated_at"}

    with get_db() as conn:
        for idx, row in enumerate(rows):
            try:
                filtered = {k: v for k, v in row.items() if k in NEW_COLS}
                campaign_key = _safe_str(filtered.get("campaign_key", ""))
                if not campaign_key:
                    result.failed += 1; continue

                # 硬约束：强制保留旧库status（paused），不被新库覆盖
                old_status = _safe_str(row.get("status", ""))
                filtered["status"] = old_status or "paused"

                if dry_run:
                    result.inserted += 1; continue

                existing = conn.execute(
                    "SELECT id FROM topic_campaigns WHERE campaign_key=?", (campaign_key,)).fetchone()
                cols = list(filtered.keys())
                if existing:
                    # 强制更新所有字段（包括status=paused）
                    set_clause = ", ".join([f"{c}=?" for c in cols if c != "campaign_key"])
                    params = [filtered[c] for c in cols if c != "campaign_key"] + [campaign_key]
                    conn.execute(f"UPDATE topic_campaigns SET {set_clause} WHERE campaign_key=?", params)
                    result.updated += 1
                else:
                    placeholders = ", ".join(["?"] * len(cols))
                    conn.execute(f"INSERT INTO topic_campaigns ({', '.join(cols)}) VALUES ({placeholders})",
                                 [filtered[c] for c in cols])
                    result.inserted += 1
                print(f"    [topic_campaigns] {campaign_key}: status={filtered['status']} "
                      f"start={filtered.get('start_date')} end={filtered.get('end_date')} "
                      f"interval={filtered.get('interval_minutes')}min")
            except Exception as e:
                result.failed += 1
                result.failures.append(f"row{idx}: {str(e)[:120]}")
    return result


# ============================================================
# event_mentions 迁移
# ============================================================

def migrate_event_mentions(reader: OldDBReader, limit: int = 0, dry_run: bool = False) -> MigrationResult:
    result = MigrationResult("event_mentions")
    result.source_count = reader.count("event_mentions")
    rows = reader.read_table("event_mentions", limit=limit)
    print(f"  [event_mentions] 读取 {len(rows)} 条 / 源总数 {result.source_count}")

    with get_db() as conn:
        for idx, row in enumerate(rows):
            try:
                eid = _safe_int(row.get("event_id"))
                stype = _safe_str(row.get("source_type", ""))
                sid = _safe_str(row.get("source_id", ""))
                if not sid:
                    result.failed += 1; continue
                if dry_run:
                    result.inserted += 1; continue
                existing = conn.execute(
                    "SELECT id FROM event_mentions WHERE event_id=? AND source_type=? AND source_id=?",
                    (eid, stype, sid)).fetchone()
                if existing:
                    conn.execute("UPDATE event_mentions SET match_score=?, created_at=? WHERE id=?",
                        (_safe_float(row.get("match_score")), _safe_str(row.get("created_at", "")), existing["id"]))
                    result.updated += 1
                else:
                    conn.execute(
                        "INSERT INTO event_mentions(event_id,source_type,source_id,match_score,created_at) VALUES(?,?,?,?,?)",
                        (eid, stype, sid, _safe_float(row.get("match_score")),
                         _safe_str(row.get("created_at", "")) or datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    result.inserted += 1
            except Exception as e:
                result.failed += 1
                result.failures.append(f"row{idx}: {str(e)[:100]}")
    return result


# ============================================================
# 主迁移流程
# ============================================================

def run_migration(trial: bool = False, limit: int = 0, dry_run: bool = False) -> Dict:
    start_time = time.time()
    print(f"\n{'='*70}")
    print(f"ZBC 历史数据适配性融合迁移 v2")
    print(f"模式: {'DRY-RUN' if dry_run else 'TRIAL小批' if trial else 'FULL全量'}")
    print(f"每表限制: {limit if limit > 0 else '无限制'}")
    print(f"fix_publish_date模块: {'可用' if _FIX_PUBLISH_AVAILABLE else 'fallback模式'}")
    print(f"开始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    reader = OldDBReader(OLD_DB)
    all_results: List[MigrationResult] = []

    # === 1. notes（核心管线）===
    print("[1/10] notes（subject重判+双时间+质量门禁+Canonical+Domain）")
    r = migrate_notes(reader, limit=limit, dry_run=dry_run)
    all_results.append(r)
    print(f"  → 源:{r.source_count} 新增:{r.inserted} 更新:{r.updated} 失败:{r.failed} "
          f"CTH:{r.cth_count} ZBMP:{r.zbmp_count} unknown:{r.unknown_count}")

    # === 2. note_comments ===
    print("\n[2/10] note_comments")
    r = migrate_simple_table(reader, "note_comments", "comment_id", limit=limit, dry_run=dry_run)
    all_results.append(r)
    print(f"  → 源:{r.source_count} 新增:{r.inserted} 更新:{r.updated} 失败:{r.failed}")

    # === 3. events ===
    print("\n[3/10] events")
    r = migrate_simple_table(reader, "events", "event_key", limit=limit, dry_run=dry_run)
    all_results.append(r)
    print(f"  → 源:{r.source_count} 新增:{r.inserted} 更新:{r.updated} 失败:{r.failed}")

    # === 4. web_mentions ===
    print("\n[4/10] web_mentions")
    r = migrate_simple_table(reader, "web_mentions", "source_id", limit=limit, dry_run=dry_run)
    all_results.append(r)
    print(f"  → 源:{r.source_count} 新增:{r.inserted} 更新:{r.updated} 失败:{r.failed}")

    # === 5. topic_campaigns（硬约束#2：保留paused）===
    print("\n[5/10] topic_campaigns（硬约束：保留paused状态/起止日期/间隔）")
    r = migrate_topic_campaigns(reader, dry_run=dry_run)
    all_results.append(r)
    print(f"  → 源:{r.source_count} 新增:{r.inserted} 更新:{r.updated} 失败:{r.failed}")

    # === 6. topic_campaign_topics ===
    print("\n[6/10] topic_campaign_topics（保留enabled状态）")
    r = migrate_simple_table(reader, "topic_campaign_topics", "id", limit=limit, dry_run=dry_run)
    all_results.append(r)
    print(f"  → 源:{r.source_count} 新增:{r.inserted} 更新:{r.updated} 失败:{r.failed}")

    # === 7. topic_campaign_snapshots（325条时间线）===
    print("\n[7/10] topic_campaign_snapshots（时间线快照，全量保留）")
    r = migrate_simple_table(reader, "topic_campaign_snapshots", "id", limit=limit, dry_run=dry_run)
    all_results.append(r)
    print(f"  → 源:{r.source_count} 新增:{r.inserted} 更新:{r.updated} 失败:{r.failed}")

    # === 8. topic_campaign_notes（120条，24→16列）===
    print("\n[8/10] topic_campaign_notes（120条，24→16列适配）")
    r = migrate_topic_campaign_notes(reader, limit=limit, dry_run=dry_run)
    all_results.append(r)
    print(f"  → 源:{r.source_count} 新增:{r.inserted} 更新:{r.updated} 失败:{r.failed}")

    # === 9. event_mentions + 审计表 + 运营表 ===
    print("\n[9/10] event_mentions + 审计表 + 运营表")
    r = migrate_event_mentions(reader, limit=limit, dry_run=dry_run)
    all_results.append(r)
    print(f"  [event_mentions] 源:{r.source_count} 新增:{r.inserted} 更新:{r.updated} 失败:{r.failed}")

    for tbl, key in [
        ("note_review_history", "id"), ("ai_filter_log", "id"),
        ("collection_logs", "id"), ("daily_reports", "id"),
        ("daily_digest", "digest_date"), ("event_insights", "id"),
        ("collector_quality_log", "id"), ("feedback_keywords", "keyword"),
        ("web_sources", "source_key"), ("web_runs", "id"),
    ]:
        r = migrate_simple_table(reader, tbl, key, limit=limit, dry_run=dry_run)
        all_results.append(r)
        print(f"  [{tbl}] 源:{r.source_count} 新增:{r.inserted} 更新:{r.updated} 失败:{r.failed}")

    # === 10. 硬约束#1：publish_date 100%回填（复用fix_publish_date）===
    print(f"\n[10/10] 硬约束#1：publish_date/publish_datetime 100%回填")
    if not dry_run and _FIX_PUBLISH_AVAILABLE:
        fix_result = _canonical_fix_publish_dates(dry_run=False)
        print(f"  fix_publish_dates: 检查{fix_result['total_checked']}条, 修复{fix_result['fixed_count']}条")
        bf_result = _canonical_backfill_captured(dry_run=False)
        print(f"  backfill_captured: 回填{bf_result['backfill_count']}条")
    elif dry_run:
        print("  DRY-RUN: 跳过实际回填")
    else:
        print("  [WARN] fix_publish_date模块不可用，使用fallback")

    # === 对账 ===
    print(f"\n{'='*70}")
    print("逐表对账（迁移后新库实际计数）")
    print(f"{'='*70}")
    reconciliation = []
    with get_db() as conn:
        for r in all_results:
            try:
                actual = conn.execute(f"SELECT COUNT(*) FROM [{r.table}]").fetchone()[0]
            except sqlite3.OperationalError:
                actual = -1
            reconciliation.append({"table": r.table, "source_count": r.source_count,
                "inserted": r.inserted, "updated": r.updated, "failed": r.failed, "actual_after": actual})
            print(f"  [{r.table:30s}] 源:{r.source_count:>6d} 新增:{r.inserted:>5d} "
                  f"更新:{r.updated:>5d} 失败:{r.failed:>4d} → 新库:{actual:>6d}")

    reader.close()
    elapsed = time.time() - start_time

    # 保存报告
    report_path = os.path.join(AUDIT_DIR, f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    summary = {
        "mode": "dry_run" if dry_run else ("trial" if trial else "full"),
        "limit_per_table": limit, "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_seconds": round(elapsed, 1),
        "fix_publish_date_available": _FIX_PUBLISH_AVAILABLE,
        "results": [r.to_dict() for r in all_results],
        "reconciliation": reconciliation,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n对账报告: {report_path}")

    total_source = sum(r.source_count for r in all_results)
    total_inserted = sum(r.inserted for r in all_results)
    total_updated = sum(r.updated for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    status = "PASS" if total_failed == 0 else ("PARTIAL" if total_failed < total_source * 0.05 else "BLOCKED")
    print(f"\n{'='*70}")
    print(f"完成 | 耗时:{elapsed:.1f}s | 源:{total_source} 新增:{total_inserted} 更新:{total_updated} 失败:{total_failed}")
    print(f"状态: {status}")
    print(f"{'='*70}")

    summary.update({"overall_status": status, "total_source": total_source,
        "total_inserted": total_inserted, "total_updated": total_updated, "total_failed": total_failed})
    return summary


def main():
    parser = argparse.ArgumentParser(description="ZBC 历史数据适配性融合迁移 v2")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--trial", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    limit = args.limit
    if args.trial and limit == 0:
        limit = 30
    result = run_migration(trial=args.trial, limit=limit, dry_run=args.dry_run)
    return 0 if result["overall_status"] in ("PASS", "PARTIAL") else 1


if __name__ == "__main__":
    sys.exit(main())
