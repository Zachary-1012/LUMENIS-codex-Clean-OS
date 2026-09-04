# -*- coding: utf-8 -*-
"""Z-Brand-Core KOS 归因模块（多触点贡献分解）

原则：
1. 不把最终结果简单全部归因给最后一个KOS。
2. 支持多触点：内容贡献/互动贡献/传播贡献/事件贡献/品牌贡献/用户需求贡献/商业贡献/风险贡献。
3. 数据来自真实数据库，不造虚假归因。
"""
from __future__ import annotations
import sqlite3
from canonical_metrics import engagement_stats as _canon_es, engagement_of as _canon_eo
from typing import Optional
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "monitor.db"


def _conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def calculate_attribution(author_id: str, brand_name: str = "广州太古汇") -> dict:
    """计算单个KOS的多触点归因贡献。

    返回各维度贡献分（0-100），基于真实数据计算。
    """
    conn = _conn()
    try:
        # 该KOS的笔记
        notes = conn.execute(
            "SELECT note_id, title, likes, comments, collects, shares, sentiment, risk_level, content_quality_score, publish_datetime FROM notes WHERE author_id=? ORDER BY publish_datetime DESC",
            (author_id,)
        ).fetchall()

        if not notes:
            return {"ok": False, "error": "KOS has no notes", "author_id": author_id}

        note_count = len(notes)
        # [Canonical WRAP-09] 等权四字段互动统一走 engagement_stats；per_field 供 reach_score 复用
        _es = _canon_es([dict(n) for n in notes])
        total_likes, total_comments = _es["per_field"]["likes"], _es["per_field"]["comments"]
        total_collects, total_shares = _es["per_field"]["collects"], _es["per_field"]["shares"]
        total_interactions = _es["sum"]

        # 内容贡献：笔记数 + 平均质量
        avg_quality = sum(n["content_quality_score"] or 0 for n in notes) / note_count
        content_score = min(100, (note_count / 10.0) * 40 + avg_quality * 60)

        # 互动贡献：总互动量归一化
        interaction_score = min(100, (total_interactions / 5000.0) * 100)

        # 传播贡献：收藏+分享占比
        reach_score = min(100, ((total_collects + total_shares) / 2000.0) * 100) if (total_collects + total_shares) > 0 else 0

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
        demand_score = min(100, (total_comments / 500.0) * 100)

        # 商业贡献：收藏数（高收藏=购买意向）
        commercial_score = min(100, (total_collects / 1000.0) * 100)

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
            "total_interactions": total_interactions,
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
    """
    if not note_ids:
        return {"ok": False, "error": "no note_ids"}

    conn = _conn()
    try:
        placeholders = ",".join("?" * len(note_ids))
        notes = conn.execute(
            f"SELECT note_id, author_id, author_nickname, likes, comments, collects, shares, publish_datetime FROM notes WHERE note_id IN ({placeholders}) ORDER BY publish_datetime ASC",
            note_ids
        ).fetchall()

        if not notes:
            return {"ok": False, "error": "notes not found"}

        # 按时间衰减权重（越早的笔记权重越低，最近的越高，但不全归最后一个）
        total_interactions = _canon_es([dict(n) for n in notes])["sum"]  # [Canonical WRAP-09] 等权四字段
        if total_interactions == 0:
            total_interactions = 1

        # 聚合到KOS
        kos_contrib = {}
        for i, n in enumerate(notes):
            aid = n["author_id"]
            if aid not in kos_contrib:
                kos_contrib[aid] = {"author_nickname": n["author_nickname"], "notes": 0, "interactions": 0, "weighted_score": 0}
            interactions = _canon_eo(dict(n))  # [Canonical WRAP-09] 单条等权四字段
            # 时间衰减：位置越靠后权重越高（线性 0.5-1.5），但不全归最后一个
            time_weight = 0.5 + (i / max(1, len(notes) - 1)) * 1.0
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
                "interactions": v["interactions"],
                "attribution_pct": round(v["weighted_score"] / total_weighted * 100, 1),
            })

        return {
            "ok": True,
            "brand_name": brand_name,
            "total_notes": len(notes),
            "total_kos": len(kos_contrib),
            "attribution": result,
            "method": "time_decay_multi_touch (not last-touch)",
        }
    finally:
        conn.close()
