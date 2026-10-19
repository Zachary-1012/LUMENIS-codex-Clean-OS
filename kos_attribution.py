# -*- coding: utf-8 -*-
"""LUMENIS BMP KOS attribution compatibility module

原则：
1. 不把最终结果简单全部归因给最后一个KOS。
2. 支持多触点：内容贡献/互动贡献/传播贡献/事件贡献/品牌贡献/用户需求贡献/商业贡献/风险贡献。
3. 数据来自真实数据库，不造虚假归因。

G1 修复（2026-09-06）：
- demand_score 阈值从 config/kos_platform_rules.json 的 attribution_weights.demand_threshold 读取，不再硬编码 /500
- time_weight 系数从 attribution_weights.time_weight_coeff 读取，不再硬编码 0.5
- interactions 按平台权重计算（各平台 likes/comments/shares/collects 权重不同），从 platform_weights 读取
- 配置缺失时显式 WARNING 日志 + 回退默认值（默认值与配置一致，不静默）
"""
from __future__ import annotations
import json
import logging
import math
import sqlite3
from canonical_metrics import engagement_count
from typing import Optional
from pathlib import Path
from lumenis.shared.database import main_db_path
from lumenis.shared.database.repository import DatabaseRepository

logger = logging.getLogger(__name__)

DB_PATH = Path(main_db_path())
CONFIG_PATH = Path(__file__).parent / "config" / "kos_platform_rules.json"

# G1: 归因模块默认值（必须与 config/kos_platform_rules.json 的 attribution_weights 一致）
# 配置缺失时显式 WARNING 后回退到此默认，不静默。
_DEFAULT_ATTRIBUTION_WEIGHTS = {
    "demand_threshold": 500,
    "time_weight_coeff": 0.5,
    "time_weight_range": 1.0,
    "interaction_threshold": 5000,
    "reach_threshold": 2000,
    "commercial_threshold": 1000,
}

# 平台名归一化：xhs / xiaohongshu-cdp → xiaohongshu
_PLATFORM_ALIASES = {
    "xhs": "xiaohongshu",
    "xiaohongshu-cdp": "xiaohongshu",
    "rednote": "xiaohongshu",
}

_attr_config_cache = None
_attr_config_status = "unloaded"


def _normalize_platform(platform):
    """归一化平台名，未知平台回退 xiaohongshu。"""
    if not platform:
        return "xiaohongshu"
    p = str(platform).strip().lower()
    return _PLATFORM_ALIASES.get(p, p)


def load_attribution_config():
    """G1: 从 config/kos_platform_rules.json 加载归因权重配置。

    返回 dict，包含 attribution_weights 和 platform_weights（从各平台 engagement_weights 提取）。
    配置缺失/损坏时显式 WARNING 并回退内置默认值（默认值与配置一致）。
    """
    global _attr_config_cache, _attr_config_status
    if _attr_config_cache is not None:
        return _attr_config_cache

    result = {
        "attribution_weights": dict(_DEFAULT_ATTRIBUTION_WEIGHTS),
        "platform_weights": {},
        "config_status": "fallback_default",
    }

    try:
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            # attribution_weights：顶层配置（以下划线开头，避免被 kos_metrics 当作平台遍历）
            cfg_aw = data.get(
                "_attribution_weights", data.get("attribution_weights", {})
            )
            if cfg_aw:
                for k in _DEFAULT_ATTRIBUTION_WEIGHTS:
                    if k in cfg_aw:
                        result["attribution_weights"][k] = cfg_aw[k]
                result["config_status"] = "configured"
            else:
                logger.warning(
                    "KOS归因配置缺失: attribution_weights，使用默认值 %s，可能导致口径漂移",
                    _DEFAULT_ATTRIBUTION_WEIGHTS,
                )
            # platform_weights：从各平台 engagement_weights 提取
            for plat_key in ("xiaohongshu", "douyin", "weibo", "bilibili", "zhihu"):
                plat_cfg = data.get(plat_key, {})
                ew = plat_cfg.get("engagement_weights", {})
                if ew:
                    result["platform_weights"][plat_key] = {
                        "likes": float(ew.get("likes", 1.0)),
                        "comments": float(ew.get("comments", 1.0)),
                        "collects": float(ew.get("collects", 1.0)),
                        "shares": float(ew.get("shares", 1.0)),
                    }
            if not result["platform_weights"]:
                logger.warning(
                    "KOS归因配置缺失: platform_weights，所有平台回退等权，可能导致口径漂移"
                )
                result["platform_weights"] = {
                    "xiaohongshu": {
                        "likes": 1.0,
                        "comments": 1.0,
                        "collects": 1.0,
                        "shares": 1.0,
                    }
                }
        else:
            logger.warning(
                "KOS归因配置缺失: 配置文件 %s 不存在，使用默认值，可能导致口径漂移",
                CONFIG_PATH,
            )
            result["platform_weights"] = {
                "xiaohongshu": {
                    "likes": 1.0,
                    "comments": 1.0,
                    "collects": 1.0,
                    "shares": 1.0,
                }
            }
    except Exception as e:
        logger.warning(
            "KOS归因配置损坏: 读取 %s 失败(%s)，使用默认值，可能导致口径漂移",
            CONFIG_PATH,
            e,
        )
        result["platform_weights"] = {
            "xiaohongshu": {
                "likes": 1.0,
                "comments": 1.0,
                "collects": 1.0,
                "shares": 1.0,
            }
        }

    _attr_config_cache = result
    _attr_config_status = result["config_status"]
    return result


def reload_attribution_config():
    """重新加载归因配置（测试/热更新用）。"""
    global _attr_config_cache, _attr_config_status
    _attr_config_cache = None
    _attr_config_status = "unloaded"
    return load_attribution_config()


def _platform_weighted_interactions(note, platform=""):
    """G1: 按平台权重计算单条笔记的加权互动量。

    权重从 config/kos_platform_rules.json 的 platform_weights 读取。
    未知平台回退 xiaohongshu 权重；配置缺失时回退等权（已在 load_attribution_config 中 WARNING）。
    """
    cfg = load_attribution_config()
    plat = _normalize_platform(platform or note.get("source_platform", ""))
    pw = cfg["platform_weights"].get(
        plat,
        cfg["platform_weights"].get(
            "xiaohongshu",
            {"likes": 1.0, "comments": 1.0, "collects": 1.0, "shares": 1.0},
        ),
    )
    values = {
        key: engagement_count(note.get(key))
        for key in ("likes", "comments", "collects", "shares")
    }
    if any(value is None for value in values.values()):
        return None
    return sum(float(values[key]) * pw[key] for key in values)


def _conn():
    return DatabaseRepository(str(DB_PATH)).connect()


def calculate_attribution(
    author_id: str, brand_name: str, *, scope=None, actor=None
) -> dict:
    """Read explicitly source-linked events, not conversion or causal credit.

    The event owner verifies every mention's Canonical scope and signed event
    receipt. A shared source is an association; time order alone adds no link.
    """
    from reprocess import _normalize_scope
    from lumenis.shared.reporting.saved_work import authorize
    import database
    import kos_engine

    exact = _normalize_scope(scope, allow_global=False)
    if exact["domain_id"] != "zbmp":
        raise ValueError("BMP_SCOPE_REQUIRED")
    if not isinstance(author_id, str) or not author_id.strip() or len(author_id) > 512:
        raise ValueError("AUTHOR_ID_REQUIRED")
    if not isinstance(brand_name, str) or not brand_name.strip():
        raise ValueError("BRAND_SCOPE_REQUIRED")
    context = authorize(actor, scope, action="read")
    binding = {
        "contract": "lumenis.scope-read-binding.v1",
        "domain_id": "BMP",
        "product_id": "ZBMP",
        "canonical_scope": "FOCUS",
        "brand_focus_id": exact["brand_focus_id"],
        "read_allowed": True,
        "scope_verified": True,
    }
    material = kos_engine.read_scoped_profiles(binding)
    profiles = [row for row in material["profiles"] if row["author_id"] == author_id]
    source_ids = {
        observation["source_id"]
        for row in profiles
        for observation in row["observations"]
        if observation.get("source_id")
    }
    event_result = database.get_scoped_events(
        limit=500, scope=scope, include_sources=True
    )
    associations = []
    for event in event_result["events"]:
        matched = []
        for source in event.get("sources", []):
            identifier = (
                source.get("note_id")
                if source.get("source_table") == "notes"
                else source.get("source_id")
            )
            if identifier in source_ids and source.get("author_id") == author_id:
                matched.append(
                    {
                        "source_id": identifier,
                        "scope_evidence_ref": source.get("scope_evidence_ref"),
                        "source_platform": source.get("source_platform"),
                        "published_at": source.get("publish_datetime"),
                    }
                )
        if matched:
            associations.append(
                {
                    "event_id": event["id"],
                    "event_title": event.get("event_title") or event.get("title"),
                    "event_date": event.get("event_date"),
                    "event_scope_evidence_ref": event["scope_evidence_ref"],
                    "linked_sources": matched,
                    "link_basis": "EXPLICIT_VERIFIED_EVENT_MENTION",
                    "causal_effect": None,
                    "conversion_credit": None,
                }
            )
    if authorize(actor, scope, action="read") != context:
        raise PermissionError("SCOPE_PERMISSION_CHANGED")
    return {
        "ok": True,
        "status": "AVAILABLE" if profiles else "NO_AUTHORIZED_AUTHOR_SOURCES",
        "author_id": author_id,
        "brand_name": brand_name,
        "brand_focus_id": exact["brand_focus_id"],
        "profiles": profiles,
        "event_associations": associations,
        "observed_source_count": len(source_ids),
        "coverage": (
            "PARTIAL"
            if material["truncated"] or event_result["truncated"]
            else "OBSERVED_SCOPE_ONLY"
        ),
        "source_rejected_count": material["rejected_count"],
        "event_rejected_count": event_result["rejected_count"],
        "method": "verified-source-event-association:v1",
        "association_state": (
            "SOURCE_LINKED" if associations else "NO_VERIFIED_SOURCE_LINK"
        ),
        "model_attribution": "NOT_RUN",
        "verified_conversion": "NOT_ESTABLISHED",
        "causal_effect": "NOT_ESTABLISHED",
        "population_coverage": "UNKNOWN",
    }


def calculate_multi_touch_attribution(
    note_ids: list, brand_name: str, *, scope=None
) -> dict:
    """Calculate attribution only from notes verified in the exact selected BrandFocus."""
    from reprocess import _canonical_source_ids, _normalize_scope

    try:
        exact = _normalize_scope(scope, allow_global=False)
    except ValueError as exc:
        return {"ok": False, "status": "blocked", "code": str(exc)}
    if exact["domain_id"] != "zbmp":
        return {"ok": False, "status": "invalid_request", "code": "BMP_SCOPE_REQUIRED"}
    if not isinstance(brand_name, str) or not brand_name.strip():
        return {
            "ok": False,
            "status": "invalid_request",
            "code": "BRAND_SCOPE_REQUIRED",
        }
    if not isinstance(note_ids, list) or not note_ids or len(note_ids) > 100:
        return {"ok": False, "status": "invalid_request", "code": "NOTE_IDS_REQUIRED"}
    normalized_ids = []
    for note_id in note_ids:
        if not isinstance(note_id, str) or not note_id or note_id != note_id.strip():
            return {
                "ok": False,
                "status": "invalid_request",
                "code": "NOTE_IDS_INVALID",
            }
        if note_id not in normalized_ids:
            normalized_ids.append(note_id)

    cfg = load_attribution_config()
    aw = cfg["attribution_weights"]
    conn = _conn()
    try:
        admitted_ids = _canonical_source_ids(
            exact,
            source_ids=normalized_ids,
            limit=len(normalized_ids),
            connection=conn,
        )
        if set(admitted_ids) != set(normalized_ids):
            return {
                "ok": False,
                "status": "denied",
                "code": "CANONICAL_NOTE_SCOPE_MISMATCH",
            }

        placeholders = ",".join("?" for _ in normalized_ids)
        notes = conn.execute(
            "SELECT note_id, author_id, author_nickname, likes, comments, collects, shares, "
            "publish_datetime, source_platform FROM notes WHERE note_id IN ("
            + placeholders
            + ") "
            "AND scope_status='VERIFIED' AND brand_focus_id=? "
            "AND COALESCE(subject_id,'')='' AND NULLIF(TRIM(scope_evidence_ref),'') IS NOT NULL "
            "ORDER BY publish_datetime ASC",
            tuple(normalized_ids) + (exact["brand_focus_id"],),
        ).fetchall()
        if len(notes) != len(normalized_ids):
            return {
                "ok": False,
                "status": "denied",
                "code": "CANONICAL_NOTE_SCOPE_CHANGED",
            }

        missing_authors = sum(
            not isinstance(note["author_id"], str) or not note["author_id"].strip()
            for note in notes
        )
        if missing_authors:
            return {
                "ok": False,
                "status": "incomplete",
                "code": "AUTHOR_ID_UNAVAILABLE",
                "total_notes": len(notes),
                "identified_author_notes": len(notes) - missing_authors,
                "unattributed_note_count": missing_authors,
                "attribution": [],
            }

        interactions_by_note = [
            _platform_weighted_interactions(dict(note)) for note in notes
        ]
        incomplete_engagement = sum(value is None for value in interactions_by_note)
        if incomplete_engagement:
            return {
                "ok": False,
                "status": "incomplete",
                "code": "ENGAGEMENT_DATA_INCOMPLETE",
                "total_notes": len(notes),
                "engagement_complete_note_count": len(notes) - incomplete_engagement,
                "engagement_incomplete_note_count": incomplete_engagement,
                "attribution": [],
            }
        kos_contrib = {}
        for index, note in enumerate(notes):
            platform = str(note["source_platform"] or "").strip()
            author = (
                platform or "UNKNOWN:" + note["note_id"],
                note["author_id"].strip(),
            )
            if author not in kos_contrib:
                kos_contrib[author] = {
                    "author_nickname": note["author_nickname"],
                    "source_platform": platform or None,
                    "source_ids": [],
                    "notes": 0,
                    "interactions": 0,
                    "weighted_score": 0,
                }
            interactions = interactions_by_note[index]
            time_weight = float(aw["time_weight_coeff"]) + (
                index / max(1, len(notes) - 1)
            ) * float(aw["time_weight_range"])
            kos_contrib[author]["source_ids"].append(note["note_id"])
            kos_contrib[author]["notes"] += 1
            kos_contrib[author]["interactions"] += interactions
            kos_contrib[author]["weighted_score"] += interactions * time_weight

        total_weighted = math.fsum(
            item["weighted_score"] for item in kos_contrib.values()
        )
        if not math.isfinite(total_weighted) or total_weighted <= 0:
            return {
                "ok": False,
                "status": "unavailable",
                "code": (
                    "ZERO_ENGAGEMENT_DENOMINATOR"
                    if total_weighted == 0
                    else "ENGAGEMENT_DENOMINATOR_UNAVAILABLE"
                ),
                "total_notes": len(notes),
                "total_kos": len(kos_contrib),
                "total_weighted_interactions": (
                    total_weighted if math.isfinite(total_weighted) else None
                ),
                "attribution": [],
            }
        result = [
            {
                "author_id": author[1],
                "source_platform": values["source_platform"],
                "source_ids": values["source_ids"],
                "author_nickname": values["author_nickname"],
                "note_count": values["notes"],
                "interactions": round(values["interactions"], 1),
                "attribution_pct": round(
                    values["weighted_score"] / total_weighted * 100, 1
                ),
            }
            for author, values in sorted(
                kos_contrib.items(),
                key=lambda item: item[1]["weighted_score"],
                reverse=True,
            )
        ]
        return {
            "ok": True,
            "status": "COMPLETED",
            "brand_name": brand_name,
            "brand_focus_id": exact["brand_focus_id"],
            "total_notes": len(notes),
            "total_kos": len(kos_contrib),
            "total_weighted_interactions": total_weighted,
            "config_status": cfg["config_status"],
            "attribution": result,
            "method": "ordered-position-weighted-source-share:v1",
            "interpretation": "DESCRIPTIVE_WEIGHTED_INTERACTION_SHARE_NOT_CONVERSION",
            "model_attribution": "LEGACY_POSITION_WEIGHTED_SHARE_NOT_MARKOV_SHAPLEY",
            "verified_conversion": "NOT_ESTABLISHED",
            "causal_effect": "NOT_ESTABLISHED",
        }
    finally:
        conn.close()
