# -*- coding: utf-8 -*-
"""Z-Brand-Core KOS Engine（KOS 传播主体引擎）

复用现有 notes/note_comments/events/evidence 表，不重建内容库。
核心能力：作者聚合、S/A/B/C 分层、生命周期、潜力/风险识别、
评论分析、博主触达文案、投流候选评分、奖励积分、动态 HTML 报告。

Contract：KOS 是传播主体层，不与 UGC（内容类型）混淆。
AI 只负责语义分类/洞察，不替代核心主体过滤。
"""
from __future__ import annotations
import sqlite3, os, math, json, io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DB_PATH = os.environ.get("ZBC_DB_PATH", str(Path(__file__).parent / "data" / "monitor.db"))

# KOS 分层阈值（第一版可配置，根据真实数据校准）
TIER_THRESHOLDS = {
    "S": {"pct": 5, "label": "核心标杆", "actions": ["优先合作", "活动邀请", "投流候选", "案例沉淀", "重点维护"]},
    "A": {"pct": 20, "label": "重点培养", "actions": ["活动邀请", "内容任务", "定向运营", "内容放大"]},
    "B": {"pct": 50, "label": "稳定传播", "actions": ["常规任务", "内容激励", "持续观察"]},
    "C": {"pct": 100, "label": "待验证", "actions": ["观察", "激活", "测试", "淘汰候选"]},
}

# 生命周期阶段
LIFECYCLE_STAGES = ["discovered", "growing", "stable", "mature", "declining", "dormant", "reactivated"]

# 评论分类
COMMENT_CATEGORIES = [
    "普通互动", "产品咨询", "活动咨询", "购买意向", "使用体验",
    "质疑", "负面", "投诉", "高价值用户", "舆情风险", "NO_REPLY"
]


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def refresh_profiles() -> dict:
    """从 notes 重新聚合作者数据，刷新 kos_profiles 表。"""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT author_id, MAX(author_nickname) as author_nickname, MAX(author_avatar) as author_avatar,
            COUNT(*) as note_count, COALESCE(SUM(likes),0) as total_likes,
            COALESCE(SUM(comments),0) as total_comments, COALESCE(SUM(collects),0) as total_collects,
            COALESCE(SUM(shares),0) as total_shares, COALESCE(AVG(content_quality_score),0) as content_quality_avg,
            MAX(subject_type) as subject_type,
            SUM(CASE WHEN sentiment='positive' THEN 1 ELSE 0 END) as positive_count,
            SUM(CASE WHEN sentiment='neutral' THEN 1 ELSE 0 END) as neutral_count,
            SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) as negative_count,
            SUM(CASE WHEN risk_level IN ('high','medium') THEN 1 ELSE 0 END) as risk_count,
            MIN(publish_datetime) as first_publish_at, MAX(publish_datetime) as last_publish_at
        FROM notes WHERE author_id IS NOT NULL AND author_id != '' GROUP BY author_id
    """)
    authors = cur.fetchall()
    profiles = []
    for a in authors:
        d = dict(a)
        nc = d['note_count'] or 0
        tl = d['total_likes'] or 0
        tc = d['total_comments'] or 0
        tcol = d['total_collects'] or 0
        ts = d['total_shares'] or 0
        eng = tl + tc * 2 + tcol * 1.5 + ts * 2
        avg_eng = eng / nc if nc > 0 else 0
        st = d.get('subject_type') or ''
        brand_rel = {'kos': 30, 'official': 20, 'media': 15, 'institution': 10, 'normal_user': 5}.get(st, 3)
        brand_rel += min(nc * 2, 20)
        cq = d.get('content_quality_avg') or 0
        risk_pen = min((d.get('risk_count') or 0) * 5 + (d.get('negative_count') or 0) * 2, 15)
        eng_score = min(math.log10(eng + 1) * 15, 40) if eng > 0 else 0
        vol_score = min(math.log10(nc + 1) * 12, 20) if nc > 0 else 0
        q_score = min(cq * 10, 10) if cq > 0 else 0
        score = max(0, min(100, round(eng_score + vol_score + brand_rel * 0.2 + q_score - risk_pen * 0.5, 2)))
        active_days = 0
        fp, lp = d.get('first_publish_at'), d.get('last_publish_at')
        if fp and lp:
            try:
                f = datetime.fromisoformat(fp.replace('Z', '+00:00')) if 'T' in fp else datetime.strptime(fp[:10], '%Y-%m-%d')
                l = datetime.fromisoformat(lp.replace('Z', '+00:00')) if 'T' in lp else datetime.strptime(lp[:10], '%Y-%m-%d')
                active_days = (l - f).days
            except Exception:
                pass
        if nc == 1: lifecycle = 'discovered'
        elif active_days < 7 and nc >= 2: lifecycle = 'growing'
        elif active_days >= 30 and avg_eng > 100: lifecycle = 'stable'
        elif active_days >= 90 and nc >= 5: lifecycle = 'mature'
        else: lifecycle = 'active'
        is_potential = 1 if (nc <= 3 and avg_eng > 500) else 0
        is_risk = 1 if ((d.get('negative_count') or 0) + (d.get('risk_count') or 0)) / max(nc, 1) > 0.3 else 0
        profiles.append({**d, 'total_engagement': eng, 'avg_engagement': avg_eng,
            'brand_relevance_score': brand_rel, 'kos_score': score, 'lifecycle_stage': lifecycle,
            'active_days': active_days, 'is_potential': is_potential, 'is_risk': is_risk})
    profiles.sort(key=lambda x: x['kos_score'], reverse=True)
    n = len(profiles)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for i, p in enumerate(profiles):
        pct = (i + 1) / n * 100
        tier = 'S' if pct <= 5 else 'A' if pct <= 20 else 'B' if pct <= 50 else 'C'
        cur.execute("""INSERT OR REPLACE INTO kos_profiles
            (author_id, author_nickname, author_avatar, note_count, total_likes, total_comments,
             total_collects, total_shares, total_engagement, avg_likes, avg_comments, avg_engagement,
             subject_type, brand_relevance_score, content_quality_avg, positive_count, neutral_count,
             negative_count, risk_count, first_publish_at, last_publish_at, active_days, growth_trend,
             kos_tier, kos_score, lifecycle_stage, is_potential, is_risk, is_top, content_tags,
             top_topics, ai_insight, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (p['author_id'], p.get('author_nickname') or '', p.get('author_avatar') or '', p['note_count'],
             p['total_likes'], p['total_comments'], p['total_collects'], p['total_shares'], p['total_engagement'],
             round(p['total_likes'] / max(p['note_count'], 1), 1), round(p['total_comments'] / max(p['note_count'], 1), 1),
             round(p['avg_engagement'], 1), p.get('subject_type') or '', p['brand_relevance_score'],
             round(p.get('content_quality_avg') or 0, 2), p.get('positive_count') or 0, p.get('neutral_count') or 0,
             p.get('negative_count') or 0, p.get('risk_count') or 0, p.get('first_publish_at'),
             p.get('last_publish_at'), p['active_days'], 'stable', tier, p['kos_score'], p['lifecycle_stage'],
             p['is_potential'], p['is_risk'], 1 if tier == 'S' else 0, '', '', '', now_str, now_str))
    conn.commit()
    stats = get_stats()
    conn.close()
    return stats


def get_stats() -> dict:
    """KOS 总体统计。"""
    conn = _get_conn()
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM kos_profiles").fetchone()[0]
    tiers = {r['kos_tier']: r['cnt'] for r in cur.execute("SELECT kos_tier, COUNT(*) as cnt FROM kos_profiles GROUP BY kos_tier")}
    lifecycle = {r['lifecycle_stage']: r['cnt'] for r in cur.execute("SELECT lifecycle_stage, COUNT(*) as cnt FROM kos_profiles GROUP BY lifecycle_stage")}
    potential = cur.execute("SELECT COUNT(*) FROM kos_profiles WHERE is_potential=1").fetchone()[0]
    risk = cur.execute("SELECT COUNT(*) FROM kos_profiles WHERE is_risk=1").fetchone()[0]
    top = cur.execute("SELECT COUNT(*) FROM kos_profiles WHERE is_top=1").fetchone()[0]
    conn.close()
    return {"total": total, "by_tier": tiers, "by_lifecycle": lifecycle,
            "potential": potential, "risk": risk, "top": top}


def list_profiles(*, tier: str = "", lifecycle: str = "", potential_only: bool = False,
                  risk_only: bool = False, search: str = "", limit: int = 50, offset: int = 0,
                  sort_by: str = "kos_score") -> dict:
    """KOS 列表查询（支持筛选/搜索/分页/排序）。"""
    conds, params = [], []
    if tier: conds.append("kos_tier = ?"); params.append(tier)
    if lifecycle: conds.append("lifecycle_stage = ?"); params.append(lifecycle)
    if potential_only: conds.append("is_potential = 1")
    if risk_only: conds.append("is_risk = 1")
    if search: conds.append("(author_nickname LIKE ? OR subject_type LIKE ?)"); params.extend([f"%{search}%"] * 2)
    where = " WHERE " + " AND ".join(conds) if conds else ""
    sort_col = sort_by if sort_by in ["kos_score", "total_engagement", "note_count", "total_likes", "avg_engagement"] else "kos_score"
    conn = _get_conn()
    total = conn.execute(f"SELECT COUNT(*) FROM kos_profiles{where}", params).fetchone()[0]
    rows = conn.execute(f"SELECT * FROM kos_profiles{where} ORDER BY {sort_col} DESC LIMIT ? OFFSET ?",
                         params + [limit, offset]).fetchall()
    conn.close()
    return {"total": total, "returned": len(rows), "limit": limit, "offset": offset,
            "profiles": [dict(r) for r in rows]}


def get_profile(author_id: str) -> Optional[dict]:
    """单个 KOS 详情（含其笔记列表）。"""
    if not author_id: return None
    conn = _get_conn()
    p = conn.execute("SELECT * FROM kos_profiles WHERE author_id = ?", (author_id,)).fetchone()
    if not p:
        conn.close()
        return None
    notes = conn.execute("""SELECT note_id, title, content, likes, comments, collects, shares,
        publish_datetime, sentiment, risk_level, url FROM notes WHERE author_id = ? ORDER BY publish_datetime DESC LIMIT 20""",
        (author_id,)).fetchall()
    conn.close()
    d = dict(p)
    d["notes"] = [dict(n) for n in notes]
    return d


def analyze_comments(author_id: str = "", note_id: str = "", limit: int = 50) -> dict:
    """评论分析（复用 note_comments 表，AI 分类+回复建议+NO_REPLY 规则）。"""
    conn = _get_conn()
    conds, params = [], []
    if note_id: conds.append("note_id = ?"); params.append(note_id)
    if author_id:
        note_ids = [r[0] for r in conn.execute("SELECT note_id FROM notes WHERE author_id = ?", (author_id,)).fetchall()]
        if note_ids:
            placeholders = ",".join("?" * len(note_ids))
            conds.append(f"note_id IN ({placeholders})")
            params.extend(note_ids)
        else:
            conn.close()
            return {"total": 0, "comments": []}
    where = " WHERE " + " AND ".join(conds) if conds else ""
    total = conn.execute(f"SELECT COUNT(*) FROM note_comments{where}", params).fetchone()[0]
    rows = conn.execute(f"SELECT * FROM note_comments{where} ORDER BY publish_time DESC LIMIT ?", params + [limit]).fetchall()
    conn.close()
    comments = []
    for r in rows:
        d = dict(r)
        content = d.get("content") or ""
        # 规则分类（第一版基于关键词，后续可接 AI）
        category = "普通互动"
        should_reply = True
        risk_level = "low"
        if any(kw in content for kw in ["怎么买", "多少钱", "价格", "链接", "购买", "哪里买"]):
            category = "购买意向"
        elif any(kw in content for kw in ["活动", "时间", "地点", "怎么参加", "报名"]):
            category = "活动咨询"
        elif any(kw in content for kw in ["不好", "垃圾", "投诉", "骗", "假", "差评", "失望"]):
            category = "负面"
            risk_level = "high"
            should_reply = False  # 高风险不自动回复
        elif any(kw in content for kw in ["法律", "起诉", "报警", "安全", "事故"]):
            category = "投诉"
            risk_level = "high"
            should_reply = False
        elif any(kw in content for kw in ["请问", "咨询", "推荐", "哪个好"]):
            category = "产品咨询"
        elif any(kw in content for kw in ["体验", "用了", "感觉", "测评"]):
            category = "使用体验"
        d["category"] = category
        d["should_reply"] = should_reply
        d["risk_level"] = risk_level
        d["reply_suggestion"] = "" if not should_reply else "建议回复（待 AI 生成）"
        comments.append(d)
    cat_stats = {}
    for c in comments:
        cat_stats[c["category"]] = cat_stats.get(c["category"], 0) + 1
    return {"total": total, "returned": len(comments), "by_category": cat_stats, "comments": comments}


def generate_outreach(author_id: str, brand_name: str = "广州太古汇", campaign_name: str = "") -> dict:
    """生成博主触达邀约文案（DRAFT 状态，不伪造已发送）。"""
    profile = get_profile(author_id)
    if not profile:
        return {"ok": False, "error": "KOS 不存在"}
    name = profile.get("author_nickname") or "博主"
    tier = profile.get("kos_tier") or "C"
    notes = profile.get("notes", [])
    top_topic = notes[0].get("title", "品牌相关内容") if notes else "优质内容"
    content_direction = "探店体验 / 活动报道 / 品牌故事" if tier in ["S", "A"] else "单品测评 / 场景种草"
    benefits = "专属活动邀请 + 品牌合作权益 + 内容流量支持" if tier == "S" else "活动体验机会 + 内容激励"
    template = f"""您好，{name}：

我们是{brand_name}品牌团队。基于您此前发布的「{top_topic[:30]}」内容以及与{brand_name}的匹配度，希望邀请您参与我们的内容合作。

合作方向：
{content_direction}

合作权益：
{benefits}

如您感兴趣，欢迎回复与我们沟通具体合作方式。期待与您合作。

{brand_name}品牌团队"""
    return {"ok": True, "status": "DRAFT", "author_id": author_id, "author_name": name,
            "tier": tier, "brand_name": brand_name, "campaign_name": campaign_name,
            "content": template, "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


def ad_candidate_score(note_id: str = "", author_id: str = "") -> dict:
    """投流候选评分（自然表现 × 品牌相关度 × 互动质量 × 风险，不生成虚假 ROI）。"""
    conn = _get_conn()
    if note_id:
        row = conn.execute("SELECT * FROM notes WHERE note_id = ?", (note_id,)).fetchone()
        candidates = [dict(row)] if row else []
    elif author_id:
        rows = conn.execute("SELECT * FROM notes WHERE author_id = ? ORDER BY likes DESC LIMIT 10", (author_id,)).fetchall()
        candidates = [dict(r) for r in rows]
    else:
        rows = conn.execute("SELECT * FROM notes WHERE sentiment != 'negative' AND risk_level NOT IN ('high','medium') ORDER BY likes DESC LIMIT 20").fetchall()
        candidates = [dict(r) for r in rows]
    conn.close()
    results = []
    for n in candidates:
        likes = n.get("likes") or 0
        comments = n.get("comments") or 0
        collects = n.get("collects") or 0
        shares = n.get("shares") or 0
        eng = likes + comments * 2 + collects * 1.5 + shares * 2
        quality = n.get("content_quality_score") or 0
        risk = 1 if n.get("risk_level") in ["high", "medium"] else 0
        neg = 1 if n.get("sentiment") == "negative" else 0
        # 投流评分：自然表现 40% + 互动质量 30% + 内容质量 20% - 风险 10%
        nat_score = min(math.log10(eng + 1) * 12, 40) if eng > 0 else 0
        interact_quality = min((comments + collects) / max(likes, 1) * 30, 30) if likes > 0 else 0
        q_score = min(quality * 20, 20) if quality > 0 else 0
        risk_pen = (risk + neg) * 10
        ad_score = max(0, min(100, round(nat_score + interact_quality + q_score - risk_pen, 1)))
        if ad_score >= 70: recommendation = "推荐投流"
        elif ad_score >= 40: recommendation = "建议观察"
        else: recommendation = "不建议投流"
        results.append({"note_id": n.get("note_id"), "title": (n.get("title") or "")[:50],
                        "author": n.get("author_nickname"), "engagement": eng,
                        "ad_score": ad_score, "recommendation": recommendation})
    results.sort(key=lambda x: x["ad_score"], reverse=True)
    return {"total": len(results), "candidates": results}


def reward_calculate(author_id: str, period: str = "month") -> dict:
    """奖励积分计算（基础+质量+传播+事件+商业贡献-风险，不擅自承诺具体金额）。"""
    profile = get_profile(author_id)
    if not profile:
        return {"ok": False, "error": "KOS 不存在"}
    base = profile.get("note_count", 0) * 10  # 基础发布
    quality = (profile.get("content_quality_avg") or 0) * 50  # 质量积分
    reach = min(math.log10(profile.get("total_engagement", 0) + 1) * 30, 100)  # 传播积分
    event = 0  # 事件贡献（待关联 events 表）
    risk_pen = (profile.get("risk_count", 0) + profile.get("negative_count", 0)) * 15
    total = max(0, round(base + quality + reach + event - risk_pen, 1))
    return {"ok": True, "author_id": author_id, "author_name": profile.get("author_nickname"),
            "period": period, "base_points": base, "quality_points": round(quality, 1),
            "reach_points": round(reach, 1), "event_points": event, "risk_penalty": risk_pen,
            "total_points": total, "tier": profile.get("kos_tier"),
            "note": "积分为可计算模型，奖励金额/权益需按品牌实际规则配置，不擅自承诺"}


__all__ = ["refresh_profiles", "get_stats", "list_profiles", "get_profile",
           "analyze_comments", "generate_outreach", "ad_candidate_score", "reward_calculate",
           "TIER_THRESHOLDS", "LIFECYCLE_STAGES", "COMMENT_CATEGORIES"]
