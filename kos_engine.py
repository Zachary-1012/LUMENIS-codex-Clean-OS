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


# ============== P1: 评论回复AI生成 + 内容基因提取 ==============

def generate_reply(comment_text: str, brand_name: str = "广州太古汇",
                   reply_style: str = "professional", risk_level: str = "low") -> dict:
    """生成评论回复建议（AI辅助，高风险NO_REPLY不自动回复）。

    原则：
    1. 高风险/投诉/法律问题 = NO_REPLY，禁止AI自动发言。
    2. 仅生成建议，不自动执行回复。
    3. 品牌口吻可配置。
    """
    if not comment_text:
        return {"ok": False, "error": "empty comment"}

    text_lower = comment_text.lower()
    # 高风险关键词检测
    high_risk_keywords = ["投诉", "起诉", "律师", "报警", "12315", "消协", "曝光", "维权",
                           "退款", "赔偿", "欺诈", "假货", "安全", "事故", "受伤", "法律"]
    is_high_risk = any(kw in text_lower for kw in high_risk_keywords) or risk_level in ("high", "critical")

    if is_high_risk:
        return {
            "ok": True,
            "action": "NO_REPLY",
            "reason": "高风险评论，禁止AI自动回复，需人工处理",
            "risk_level": "high",
            "suggested_action": "转人工客服/法务审核",
        }

    # 评论分类
    category = "general_interaction"
    if any(kw in text_lower for kw in ["多少钱", "价格", "怎么买", "哪里买", "链接", "购买"]):
        category = "purchase_intent"
    elif any(kw in text_lower for kw in ["活动", "时间", "什么时候", "地址", "在哪"]):
        category = "event_inquiry"
    elif any(kw in text_lower for kw in ["好用", "推荐", "不错", "喜欢", "赞"]):
        category = "positive_feedback"
    elif any(kw in text_lower for kw in ["不好", "差", "失望", "坑", "垃圾"]):
        category = "negative_feedback"
    elif any(kw in text_lower for kw in ["怎么用", "使用", "教程", "说明"]):
        category = "product_consult"

    # 基于规则的回复模板（AI Gateway 可用时可替换为真实AI生成）
    templates = {
        "purchase_intent": f"感谢关注{brand_name}！您可以通过官方渠道了解详情，我们的客服会为您提供专业咨询。",
        "event_inquiry": f"感谢关注{brand_name}活动！具体活动信息请以官方公告为准，我们会及时更新最新动态。",
        "positive_feedback": f"感谢您的认可与支持！{brand_name}会继续努力，为您带来更好的体验。",
        "negative_feedback": f"非常抱歉给您带来不好的体验，我们非常重视您的反馈，会认真改进。如需进一步沟通，请联系客服。",
        "product_consult": f"感谢咨询！关于产品使用，建议您查看官方说明或联系客服获取详细指导。",
        "general_interaction": f"感谢您的关注与互动！{brand_name}期待与您有更多交流。",
    }

    return {
        "ok": True,
        "action": "SUGGEST_REPLY",
        "category": category,
        "risk_level": risk_level,
        "reply_style": reply_style,
        "suggested_reply": templates.get(category, templates["general_interaction"]),
        "auto_reply": False,  # 默认不自动回复，需人工确认
        "requires_approval": category in ("negative_feedback", "purchase_intent"),
    }


def extract_content_dna(author_id: str, limit: int = 20) -> dict:
    """提取KOS内容基因：选题/标题结构/内容主题/场景/品牌/产品/情绪/用户需求。

    从现有notes数据提取，不调用AI（AI可用时可增强语义标签）。
    """
    import sqlite3
    from pathlib import Path
    db = Path(__file__).parent / "data" / "monitor.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        notes = conn.execute(
            "SELECT note_id, title, body, content, likes, comments, collects, shares, sentiment, content_type, publish_datetime FROM notes WHERE author_id=? ORDER BY publish_datetime DESC LIMIT ?",
            (author_id, limit)
        ).fetchall()

        if not notes:
            return {"ok": False, "error": "no notes for this KOS"}

        # 标题结构分析
        title_patterns = {"question": 0, "exclamation": 0, "number": 0, "guide": 0, "plain": 0}
        topics = {}
        scenes = {"shopping": 0, "food": 0, "beauty": 0, "fashion": 0, "travel": 0, "lifestyle": 0, "other": 0}
        emotions = {"positive": 0, "neutral": 0, "negative": 0}
        products = set()
        brands_mentioned = set()

        scene_keywords = {
            "shopping": ["购物", "买", "商场", "店", "专柜", "品牌"],
            "food": ["吃", "美食", "餐厅", "咖啡", "甜品", "日料"],
            "beauty": ["美妆", "护肤", "化妆", "口红", "面膜", "精华"],
            "fashion": ["穿搭", "衣服", "时尚", "搭配", "包包", "鞋"],
            "travel": ["旅行", "旅游", "打卡", "探店", "攻略", "出行"],
            "lifestyle": ["生活", "日常", "vlog", "分享", "体验"],
        }
        product_keywords = ["LV", "香奈儿", "迪奥", "Dior", "Gucci", "Prada", "Hermes", "爱马仕",
                            "苹果", "华为", "小米", "耐克", "阿迪", "星巴克", "喜茶", "奈雪"]
        brand_keywords = ["太古汇", "中免", "CDF", "海南", "广州", "三亚", "海口"]

        for n in notes:
            title = n["title"] or ""
            body = (n["body"] or n["content"] or "")[:500]
            full = title + " " + body

            # 标题结构
            if "?" in title or "？" in title:
                title_patterns["question"] += 1
            elif "!" in title or "！" in title:
                title_patterns["exclamation"] += 1
            elif any(c.isdigit() for c in title):
                title_patterns["number"] += 1
            elif any(kw in title for kw in ["攻略", "指南", "教程", "怎么", "如何"]):
                title_patterns["guide"] += 1
            else:
                title_patterns["plain"] += 1

            # 场景
            for scene, kws in scene_keywords.items():
                if any(kw in full for kw in kws):
                    scenes[scene] += 1
                    break
            else:
                scenes["other"] += 1

            # 情绪
            sent = (n["sentiment"] or "neutral").lower()
            if sent in emotions:
                emotions[sent] += 1
            else:
                emotions["neutral"] += 1

            # 产品/品牌
            for p in product_keywords:
                if p.lower() in full.lower():
                    products.add(p)
            for b in brand_keywords:
                if b.lower() in full.lower():
                    brands_mentioned.add(b)

            # 主题（简化：高频词）
            for kw in ["探店", "打卡", "测评", "分享", "推荐", "攻略", "活动", "优惠", "新品", "限定"]:
                if kw in full:
                    topics[kw] = topics.get(kw, 0) + 1

        total = len(notes)
        dominant_scene = max(scenes, key=scenes.get)
        dominant_emotion = max(emotions, key=emotions.get)
        dominant_title_style = max(title_patterns, key=title_patterns.get)

        return {
            "ok": True,
            "author_id": author_id,
            "sample_size": total,
            "content_dna": {
                "dominant_scene": dominant_scene,
                "scene_distribution": {k: round(v / total * 100, 1) for k, v in scenes.items() if v > 0},
                "dominant_emotion": dominant_emotion,
                "emotion_distribution": {k: round(v / total * 100, 1) for k, v in emotions.items() if v > 0},
                "dominant_title_style": dominant_title_style,
                "title_style_distribution": {k: round(v / total * 100, 1) for k, v in title_patterns.items() if v > 0},
                "top_topics": sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5],
                "products_mentioned": list(products)[:10],
                "brands_mentioned": list(brands_mentioned),
            },
            "user_demand_signals": {
                "purchase_intent": topics.get("推荐", 0) + topics.get("测评", 0),
                "information_demand": topics.get("攻略", 0) + topics.get("分享", 0),
                "experience_demand": topics.get("探店", 0) + topics.get("打卡", 0),
                "promotion_sensitivity": topics.get("优惠", 0) + topics.get("活动", 0),
            }
        }
    finally:
        conn.close()

# -*- coding: utf-8 -*-
"""KOS 品牌隔离聚合（方案 A：source_keyword 品牌隔离，不写 kos_profiles 主表，不污染广州）。
由施工追加到 kos_engine.py 末尾。
"""


def _brand_source_filter(brand: str) -> tuple:
    """品牌笔记过滤条件：source_keyword ∈ 品牌采集词（品牌隔离标记，复用 collect_keywords_for）。"""
    from subject_rules import collect_keywords_for
    kws = [k for k in collect_keywords_for(brand) if k]
    if not kws:
        return "1=0", []
    ph = ",".join("?" for _ in kws)
    return f"source_keyword IN ({ph})", list(kws)


def brand_collection_stats(brand: str) -> dict:
    """品牌采集状态：笔记数 / 作者数 / 最新采集时间。"""
    conn = _get_conn()
    try:
        cond, params = _brand_source_filter(brand)
        row = conn.execute(
            f"SELECT COUNT(*) AS note_count, COUNT(DISTINCT author_id) AS author_count, "
            f"MAX(captured_at) AS last_captured_at FROM notes WHERE {cond}",
            params,
        ).fetchone()
        return {
            "brand": brand,
            "note_count": int(row["note_count"] or 0),
            "author_count": int(row["author_count"] or 0),
            "last_captured_at": row["last_captured_at"],
        }
    finally:
        conn.close()


def brand_profiles(brand: str, limit: int = 20) -> list:
    """品牌 KOS 作者实时聚合（不写 kos_profiles，与广州主链隔离）。"""
    conn = _get_conn()
    try:
        cond, params = _brand_source_filter(brand)
        rows = conn.execute(
            f"""
            SELECT author_id, MAX(author_nickname) AS author_nickname, COUNT(*) AS note_count,
                   COALESCE(SUM(likes),0) AS total_likes, COALESCE(SUM(comments),0) AS total_comments,
                   COALESCE(SUM(collects),0) AS total_collects, COALESCE(SUM(shares),0) AS total_shares,
                   SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) AS negative_count
            FROM notes
            WHERE {cond} AND author_id IS NOT NULL AND author_id != ''
            GROUP BY author_id
            ORDER BY (COALESCE(SUM(likes),0) + COALESCE(SUM(comments),0) * 2) DESC
            LIMIT ?
            """,
            params + [int(limit)],
        ).fetchall()
        n = len(rows)
        profiles = []
        for i, r in enumerate(rows):
            eng = (r["total_likes"] or 0) + (r["total_comments"] or 0) * 2 \
                + (r["total_collects"] or 0) * 1.5 + (r["total_shares"] or 0) * 2
            pct = (i + 1) / n if n else 1
            tier = "S" if pct <= 0.05 else "A" if pct <= 0.20 else "B" if pct <= 0.50 else "C"
            profiles.append({
                "author_id": r["author_id"],
                "author_nickname": r["author_nickname"] or "",
                "note_count": int(r["note_count"] or 0),
                "total_engagement": round(eng, 1),
                "kos_tier": tier,
                "risk": 1 if (r["negative_count"] or 0) > 0 else 0,
            })
        return profiles
    finally:
        conn.close()
