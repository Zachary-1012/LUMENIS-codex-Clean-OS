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
import sqlite3
from canonical_metrics import engagement_stats as _canon_es, engagement_of as _canon_eo
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
            cfg_aw = data.get("_attribution_weights", data.get("attribution_weights", {}))
            if cfg_aw:
                for k in _DEFAULT_ATTRIBUTION_WEIGHTS:
                    if k in cfg_aw:
                        result["attribution_weights"][k] = cfg_aw[k]
                result["config_status"] = "configured"
            else:
                logger.warning(
                    "KOS归因配置缺失: attribution_weights，使用默认值 %s，可能导致口径漂移",
                    _DEFAULT_ATTRIBUTION_WEIGHTS)
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
                    "KOS归因配置缺失: platform_weights，所有平台回退等权，可能导致口径漂移")
                result["platform_weights"] = {
                    "xiaohongshu": {"likes": 1.0, "comments": 1.0, "collects": 1.0, "shares": 1.0}}
        else:
            logger.warning(
                "KOS归因配置缺失: 配置文件 %s 不存在，使用默认值，可能导致口径漂移", CONFIG_PATH)
            result["platform_weights"] = {
                "xiaohongshu": {"likes": 1.0, "comments": 1.0, "collects": 1.0, "shares": 1.0}}
    except Exception as e:
        logger.warning(
            "KOS归因配置损坏: 读取 %s 失败(%s)，使用默认值，可能导致口径漂移", CONFIG_PATH, e)
        result["platform_weights"] = {
            "xiaohongshu": {"likes": 1.0, "comments": 1.0, "collects": 1.0, "shares": 1.0}}

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
        plat, cfg["platform_weights"].get("xiaohongshu",
        {"likes": 1.0, "comments": 1.0, "collects": 1.0, "shares": 1.0}))
    return (float(note.get("likes") or 0) * pw["likes"]
            + float(note.get("comments") or 0) * pw["comments"]
            + float(note.get("collects") or 0) * pw["collects"]
            + float(note.get("shares") or 0) * pw["shares"])


def _conn():
    return DatabaseRepository(str(DB_PATH)).connect()


def calculate_attribution(author_id: str, brand_name: str = "广州太古汇") -> dict:
    """计算单个KOS的多触点归因贡献。

    返回各维度贡献分（0-100），基于真实数据计算。
    G1: demand_threshold/time_weight_coeff/interactions 均从配置读取。
    """
    cfg = load_attribution_config()
    aw = cfg["attribution_weights"]
    conn = _conn()
    try:
        # 该KOS的笔记（G1: 增加 source_platform 用于平台权重计算）
        notes = conn.execute(
            "SELECT note_id, title, likes, comments, collects, shares, sentiment, risk_level, content_quality_score, publish_datetime, source_platform FROM notes WHERE author_id=? ORDER BY publish_datetime DESC",
            (author_id,)
        ).fetchall()

        if not notes:
            return {"ok": False, "error": "KOS has no notes", "author_id": author_id}

        note_count = len(notes)
        # [Canonical WRAP-09] 等权四字段互动统一走 engagement_stats；per_field 供 reach_score 复用
        _es = _canon_es([dict(n) for n in notes])
        total_likes, total_comments = _es["per_field"]["likes"], _es["per_field"]["comments"]
        total_collects, total_shares = _es["per_field"]["collects"], _es["per_field"]["shares"]
        # G1: 总互动量按平台权重计算（不再用等权 sum）
        total_interactions = sum(_platform_weighted_interactions(dict(n)) for n in notes)

        # 内容贡献：笔记数 + 平均质量
        avg_quality = sum(n["content_quality_score"] or 0 for n in notes) / note_count
        content_score = min(100, (note_count / 10.0) * 40 + avg_quality * 60)

        # 互动贡献：总互动量归一化（G1: 阈值从配置读取）
        interaction_score = min(100, (total_interactions / float(aw["interaction_threshold"])) * 100)

        # 传播贡献：收藏+分享占比（G1: 阈值从配置读取）
        reach_score = min(100, ((total_collects + total_shares) / float(aw["reach_threshold"])) * 100) if (total_collects + total_shares) > 0 else 0

        # 事件贡献：该KOS笔记标题命中events关键词的数量（简化匹配）
        event_rows = conn.execute("SELECT keywords FROM events WHERE keywords IS NOT NULL AND keywords != ''").fetchall()
        event_keywords = set()
        for er in event_rows:
            for kw in (er["keywords"] or "").split(","):
                kw = kw.strip()
                if len(kw) >= 2:
                    event_keywords.add(kw.lower())
        event_count = 0
        for n in notes:
            title = (n["title"] or "").lower()
            if any(kw in title for kw in event_keywords):
                event_count += 1
        event_score = min(100, event_count * 20)

        # 品牌贡献：品牌相关笔记占比（通过 subject_hit 逻辑，简化为标题含品牌词）
        brand_keywords = [brand_name, "太古汇", "中免", "CDF", "海南"]
        brand_notes = sum(1 for n in notes if any(kw.lower() in (n["title"] or "").lower() for kw in brand_keywords))
        brand_score = min(100, (brand_notes / note_count) * 100)

        # 用户需求贡献：评论数（高评论=用户需求活跃）
        # G1: demand_threshold 从配置读取，不再硬编码 500
        demand_score = min(100, (total_comments / float(aw["demand_threshold"])) * 100)

        # 商业贡献：收藏数（高收藏=购买意向）
        # G1: commercial_threshold 从配置读取
        commercial_score = min(100, (total_collects / float(aw["commercial_threshold"])) * 100)

        # 风险贡献：负面/风险笔记占比（反向，越低越好）
        risk_notes = sum(1 for n in notes if (n["risk_level"] or "") in ("high", "medium") or (n["sentiment"] or "") == "negative")
        risk_score = min(100, (risk_notes / note_count) * 100)

        # 综合归因分（加权）
        total_score = (
            content_score * 0.20 +
            interaction_score * 0.25 +
            reach_score * 0.15 +
            event_score * 0.10 +
            brand_score * 0.10 +
            demand_score * 0.10 +
            commercial_score * 0.05 +
            (100 - risk_score) * 0.05
        )

        return {
            "ok": True,
            "author_id": author_id,
            "brand_name": brand_name,
            "note_count": note_count,
            "total_interactions": round(total_interactions, 1),
            "config_status": cfg["config_status"],
            "attribution": {
                "content": round(content_score, 1),
                "interaction": round(interaction_score, 1),
                "reach": round(reach_score, 1),
                "event": round(event_score, 1),
                "brand": round(brand_score, 1),
                "demand": round(demand_score, 1),
                "commercial": round(commercial_score, 1),
                "risk": round(risk_score, 1),
            },
            "total_attribution_score": round(total_score, 1),
            "breakdown": {
                "content_pct": round(content_score / total_score * 100, 1) if total_score > 0 else 0,
                "interaction_pct": round(interaction_score / total_score * 100, 1) if total_score > 0 else 0,
                "reach_pct": round(reach_score / total_score * 100, 1) if total_score > 0 else 0,
                "event_pct": round(event_score / total_score * 100, 1) if total_score > 0 else 0,
                "brand_pct": round(brand_score / total_score * 100, 1) if total_score > 0 else 0,
                "demand_pct": round(demand_score / total_score * 100, 1) if total_score > 0 else 0,
                "commercial_pct": round(commercial_score / total_score * 100, 1) if total_score > 0 else 0,
            }
        }
    finally:
        conn.close()


def calculate_multi_touch_attribution(note_ids: list, brand_name: str = "广州太古汇") -> dict:
    """多触点归因：一组笔记涉及的所有KOS的贡献分解。

    不把最终结果简单全部归因给最后一个KOS，按时间衰减+互动权重分配。
    G1: time_weight 系数从配置读取；interactions 按平台权重计算。
    """
    if not note_ids:
        return {"ok": False, "error": "no note_ids"}

    cfg = load_attribution_config()
    aw = cfg["attribution_weights"]
    conn = _conn()
    try:
        placeholders = ",".join("?" * len(note_ids))
        # G1: 增加 source_platform 用于平台权重计算
        notes = conn.execute(
            f"SELECT note_id, author_id, author_nickname, likes, comments, collects, shares, publish_datetime, source_platform FROM notes WHERE note_id IN ({placeholders}) ORDER BY publish_datetime ASC",
            note_ids
        ).fetchall()

        if not notes:
            return {"ok": False, "error": "notes not found"}

        # G1: 总互动量按平台权重计算（不再用等权 canonical sum）
        total_interactions = sum(_platform_weighted_interactions(dict(n)) for n in notes)
        if total_interactions == 0:
            total_interactions = 1

        # 聚合到KOS
        kos_contrib = {}
        for i, n in enumerate(notes):
            aid = n["author_id"]
            if aid not in kos_contrib:
                kos_contrib[aid] = {"author_nickname": n["author_nickname"], "notes": 0, "interactions": 0, "weighted_score": 0}
            # G1: 单条互动按平台权重计算（不再用 canonical 等权）
            interactions = _platform_weighted_interactions(dict(n))
            # G1: 时间衰减系数从配置读取（time_weight_coeff + time_weight_range）
            # 原公式: 0.5 + (i / (len-1)) * 1.0 → coeff + (i / (len-1)) * range
            time_weight = float(aw["time_weight_coeff"]) + (i / max(1, len(notes) - 1)) * float(aw["time_weight_range"])
            kos_contrib[aid]["notes"] += 1
            kos_contrib[aid]["interactions"] += interactions
            kos_contrib[aid]["weighted_score"] += interactions * time_weight

        total_weighted = sum(v["weighted_score"] for v in kos_contrib.values()) or 1

        result = []
        for aid, v in sorted(kos_contrib.items(), key=lambda x: x[1]["weighted_score"], reverse=True):
            result.append({
                "author_id": aid,
                "author_nickname": v["author_nickname"],
                "note_count": v["notes"],
                "interactions": round(v["interactions"], 1),
                "attribution_pct": round(v["weighted_score"] / total_weighted * 100, 1),
            })

        return {
            "ok": True,
            "brand_name": brand_name,
            "total_notes": len(notes),
            "total_kos": len(kos_contrib),
            "config_status": cfg["config_status"],
            "attribution": result,
            "method": "time_decay_multi_touch (not last-touch, platform-weighted)",
        }
    finally:
        conn.close()
