# -*- coding: utf-8 -*-
"""LUMENIS BMP KOS Engine compatibility module

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
import subject_rules as sr  # KOS 主体归属硬规则（Contract 第六条）

from lumenis.shared.database import get_repository, main_db_path

DB_PATH = main_db_path()

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


_KOS_SCHEMA_ENSURED = False


def _ensure_table(conn):
    """幂等创建 kos_profiles 表（KOS_PROFILES_SCHEMA_v1）。
    基础列在此创建，账号资产扩展列由 _ensure_asset_columns 幂等 ALTER 补齐。
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kos_profiles (
            author_id TEXT PRIMARY KEY,
            author_nickname TEXT DEFAULT '',
            author_avatar TEXT DEFAULT '',
            note_count INTEGER DEFAULT 0,
            total_likes INTEGER DEFAULT 0,
            total_comments INTEGER DEFAULT 0,
            total_collects INTEGER DEFAULT 0,
            total_shares INTEGER DEFAULT 0,
            total_engagement REAL DEFAULT 0,
            avg_likes REAL DEFAULT 0,
            avg_comments REAL DEFAULT 0,
            avg_engagement REAL DEFAULT 0,
            subject_type TEXT DEFAULT '',
            brand_relevance_score REAL DEFAULT 0,
            content_quality_avg REAL DEFAULT 0,
            positive_count INTEGER DEFAULT 0,
            neutral_count INTEGER DEFAULT 0,
            negative_count INTEGER DEFAULT 0,
            risk_count INTEGER DEFAULT 0,
            first_publish_at TEXT DEFAULT '',
            last_publish_at TEXT DEFAULT '',
            active_days INTEGER DEFAULT 0,
            growth_trend TEXT DEFAULT 'stable',
            kos_tier TEXT DEFAULT 'C',
            kos_score REAL DEFAULT 0,
            lifecycle_stage TEXT DEFAULT 'discovered',
            is_potential INTEGER DEFAULT 0,
            is_risk INTEGER DEFAULT 0,
            is_top INTEGER DEFAULT 0,
            content_tags TEXT DEFAULT '',
            top_topics TEXT DEFAULT '',
            ai_insight TEXT DEFAULT '',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT '',
            identity_label TEXT DEFAULT 'UNKNOWN',
            is_kos INTEGER DEFAULT 0
        )
    """)
    conn.commit()


def _get_conn() -> sqlite3.Connection:
    global _KOS_SCHEMA_ENSURED
    conn = get_repository().connect(timeout=10)
    conn.row_factory = sqlite3.Row
    if not _KOS_SCHEMA_ENSURED:
        _ensure_table(conn)
        _ensure_asset_columns(conn)
        _KOS_SCHEMA_ENSURED = True
    return conn


# KOS 账号资产字段（KOS_ACCOUNT_ASSET_TEMPLATE_v1）：幂等 ALTER，不破坏既有数据
_ASSET_COLUMNS = [
    # 主体归属（P0）
    ("ownership_type", "TEXT", "'UNKNOWN'"),
    ("ownership_confidence", "REAL", "0.0"),
    ("ownership_evidence_ids", "TEXT", "''"),
    ("merchant_entity", "TEXT", "''"),
    ("brand_entity", "TEXT", "''"),
    ("relationship_status", "TEXT", "'UNVERIFIED'"),
    # 留资（P1）
    ("contact_name", "TEXT", "''"),
    ("phone", "TEXT", "''"),
    ("wechat", "TEXT", "''"),
    ("email", "TEXT", "''"),
    ("mcn", "TEXT", "''"),
    ("company", "TEXT", "''"),
    # 合作（P1）
    ("budget", "REAL", "0.0"),
    ("quote", "REAL", "0.0"),
    ("cooperation_status", "TEXT", "'NONE'"),
    ("cooperation_history", "TEXT", "''"),
    # 高级表现（P2）
    ("follower_count", "INTEGER", "0"),
    ("follower_growth_rate", "REAL", "0.0"),
    ("engagement_rate", "REAL", "0.0"),
    ("content_match_score", "REAL", "0.0"),
    ("expertise_score", "REAL", "0.0"),
    ("consistency_score", "REAL", "0.0"),
    # 身份标签（与 kos_intel._ensure_identity_columns 对齐）
    ("identity_label", "TEXT", "'UNKNOWN'"),
    ("is_kos", "INTEGER", "0"),
]


def _ensure_asset_columns(conn):
    """幂等补齐 kos_profiles 账号资产列（KOS_ACCOUNT_ASSET_TEMPLATE_v1）。"""
    _ensure_table(conn)  # 先确保基础表存在
    cols = {r[1] for r in conn.execute("PRAGMA table_info(kos_profiles)").fetchall()}
    for name, typ, default in _ASSET_COLUMNS:
        if name not in cols:
            conn.execute(f"ALTER TABLE kos_profiles ADD COLUMN {name} {typ} DEFAULT {default}")


def refresh_profiles() -> dict:
    """从 notes 重新聚合作者数据，刷新 kos_profiles 表。"""
    conn = _get_conn()
    _ensure_asset_columns(conn)  # 幂等补齐账号资产字段（KOS_ACCOUNT_ASSET_TEMPLATE_v1）
    cur = conn.cursor()
    cur.execute("""
        SELECT author_id, MAX(author_nickname) as author_nickname, MAX(author_avatar) as author_avatar,
            COUNT(*) as note_count, COALESCE(SUM(likes),0) as total_likes,
            COALESCE(SUM(comments),0) as total_comments, COALESCE(SUM(collects),0) as total_collects,
            COALESCE(SUM(shares),0) as total_shares, COALESCE(AVG(content_quality_score),0) as content_quality_avg,
            MAX(subject_type) as subject_type,
            GROUP_CONCAT(title, ' || ') as note_titles,
            GROUP_CONCAT(COALESCE(source_platform,'xiaohongshu'), ',') as platforms,
            SUM(CASE WHEN sentiment='positive' THEN 1 ELSE 0 END) as positive_count,
            SUM(CASE WHEN sentiment='neutral' THEN 1 ELSE 0 END) as neutral_count,
            SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) as negative_count,
            SUM(CASE WHEN risk_level IN ('high','medium') THEN 1 ELSE 0 END) as risk_count,
            MIN(publish_datetime) as first_publish_at, MAX(publish_datetime) as last_publish_at
        FROM notes WHERE author_id IS NOT NULL AND author_id != '' AND subject_type IN ('kos', 'official') GROUP BY author_id
    """)
    authors = cur.fetchall()
    profiles = []
    for a in authors:
        d = dict(a)
        # 主体归属 Gate（Contract 第六条）：只保留通过当前品牌 subject_hit 的作者
        # 商业体本身不建 KOS；normal_user/media/institution 已在 SQL 层排除
        note_titles = d.get('note_titles') or ''
        if not sr.subject_hit(title=note_titles, body='', content='', source_keyword=''):
            continue
        nc = d['note_count'] or 0
        tl = d['total_likes'] or 0
        tc = d['total_comments'] or 0
        tcol = d['total_collects'] or 0
        ts = d['total_shares'] or 0
        # P0 红线：互动量权重从平台规则读取，禁止硬编码 2/1.5/2 等系数
        from kos_metrics import platform_engagement, platform_kos_score
        platforms_str = d.get('platforms') or 'xiaohongshu'
        platform_list = [p for p in str(platforms_str).split(',') if p]
        author_platform = platform_list[0] if platform_list else 'xiaohongshu'
        eng = platform_engagement(author_platform, tl, tc, tcol, ts)
        avg_eng = eng / nc if nc > 0 else 0
        st = d.get('subject_type') or ''
        cq = d.get('content_quality_avg') or 0
        risk_cnt = d.get('risk_count') or 0
        neg_cnt = d.get('negative_count') or 0
        # P0 红线：KOS 得分从平台规则计算，禁止硬编码系数
        score_result = platform_kos_score(
            author_platform, engagement=eng, note_count=nc,
            subject_type=st, content_quality=cq,
            risk_count=risk_cnt, negative_count=neg_cnt,
        )
        score = score_result['score']
        brand_rel = score_result['brand_relevance']
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
        # 主体归属类型映射（KOS_ACCOUNT_ASSET_TEMPLATE_v1）
        _st = p.get('subject_type') or ''
        ownership_type = {'official': 'OFFICIAL', 'kos': 'INDEPENDENT_KOL_KOC', 'media': 'MEDIA'}.get(_st, 'UNKNOWN')
        ownership_confidence = 0.8 if _st in ('official', 'kos') else 0.5
        cur.execute("""INSERT OR REPLACE INTO kos_profiles
            (author_id, author_nickname, author_avatar, note_count, total_likes, total_comments,
             total_collects, total_shares, total_engagement, avg_likes, avg_comments, avg_engagement,
             subject_type, brand_relevance_score, content_quality_avg, positive_count, neutral_count,
             negative_count, risk_count, first_publish_at, last_publish_at, active_days, growth_trend,
             kos_tier, kos_score, lifecycle_stage, is_potential, is_risk, is_top, content_tags,
             top_topics, ai_insight, created_at, updated_at, identity_label, is_kos, ownership_type, ownership_confidence, ownership_evidence_ids, merchant_entity, brand_entity, relationship_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (p['author_id'], p.get('author_nickname') or '', p.get('author_avatar') or '', p['note_count'],
             p['total_likes'], p['total_comments'], p['total_collects'], p['total_shares'], p['total_engagement'],
             round(p['total_likes'] / max(p['note_count'], 1), 1), round(p['total_comments'] / max(p['note_count'], 1), 1),
             round(p['avg_engagement'], 1), p.get('subject_type') or '', p['brand_relevance_score'],
             round(p.get('content_quality_avg') or 0, 2), p.get('positive_count') or 0, p.get('neutral_count') or 0,
             p.get('negative_count') or 0, p.get('risk_count') or 0, p.get('first_publish_at'),
             p.get('last_publish_at'), p['active_days'], 'stable', tier, p['kos_score'], p['lifecycle_stage'],
             p['is_potential'], p['is_risk'], 1 if tier == 'S' else 0, '', '', '', now_str, now_str, sr.get_active_brand(), 1, ownership_type, ownership_confidence, '', '', sr.get_active_brand(), 'UNVERIFIED'))
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
    """KOS 列表只读查询；空库不会因读取而创建业务表。"""
    conds, params = [], []
    if tier: conds.append("kos_tier = ?"); params.append(tier)
    if lifecycle: conds.append("lifecycle_stage = ?"); params.append(lifecycle)
    if potential_only: conds.append("is_potential = 1")
    if risk_only: conds.append("is_risk = 1")
    if search: conds.append("(author_nickname LIKE ? OR subject_type LIKE ?)"); params.extend([f"%{search}%"] * 2)
    where = " WHERE " + " AND ".join(conds) if conds else ""
    sort_col = sort_by if sort_by in ["kos_score", "total_engagement", "note_count", "total_likes", "avg_engagement"] else "kos_score"
    conn = get_repository().connect(timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='kos_profiles'"
        ).fetchone()
        if exists is None:
            return {
                "total": 0,
                "returned": 0,
                "limit": limit,
                "offset": offset,
                "profiles": [],
                "schema_status": "unavailable",
            }
        total = conn.execute(f"SELECT COUNT(*) FROM kos_profiles{where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM kos_profiles{where} ORDER BY {sort_col} DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        return {
            "total": total,
            "returned": len(rows),
            "limit": limit,
            "offset": offset,
            "profiles": [dict(r) for r in rows],
            "schema_status": "available",
        }
    finally:
        conn.close()


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


def _comment_sentiment(content: str) -> str:
    """评论情感三维：positive/neutral/negative/mixed（确定性关键词，AI 仅增强不越权）。"""
    c = (content or "").strip()
    if not c:
        return "neutral"
    neg = ["不好", "垃圾", "投诉", "骗", "假", "差评", "失望", "坑", "差", "曝光", "维权", "退款", "欺诈", "假货", "别买", "踩雷"]
    pos = ["好用", "推荐", "不错", "喜欢", "赞", "很棒", "满意", "回购", "种草", "爱了", "好评", "yyds", "高级", "值得"]
    has_neg = any(k in c for k in neg)
    has_pos = any(k in c for k in pos)
    if has_neg and has_pos:
        return "mixed"
    if has_neg:
        return "negative"
    if has_pos:
        return "positive"
    return "neutral"


def _purchase_signal(content: str) -> str:
    """购买信号强度：strong/weak/none（KOS 评论承接价值）。"""
    c = (content or "").strip()
    strong = ["怎么买", "多少钱", "价格", "链接", "购买", "哪里买", "求购", "下单", "已买", "付款", "优惠券", "多少钱啊"]
    weak = ["想买", "考虑", "了解一下", "有兴趣", "贵吗", "值得买吗", "活动价", "划算吗"]
    if any(k in c for k in strong):
        return "strong"
    if any(k in c for k in weak):
        return "weak"
    return "none"


def _cooperation_signal(content: str) -> str:
    """合作意图：发现潜在 KOS / 商务合作机会（KOS 评论智能核心信号）。"""
    c = (content or "").strip()
    coop = ["合作", "商务", "求合作", "可以合作", "联系合作", "推广", "报备", "档期", "博主合作", "kol", "koc", "mcn"]
    if any(k in c for k in coop):
        return "yes"
    return "no"


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
        # 情感-专业度二维 + 意图识别（确定性规则，AI 仅增强不越权）
        d["sentiment"] = _comment_sentiment(content)
        d["purchase_signal"] = _purchase_signal(content)
        d["cooperation_signal"] = _cooperation_signal(content)
        d["needs_review"] = risk_level == "high"
        # 真实回复模板（复用 generate_reply 单一事实源；高风险→NO_REPLY 空建议）
        _r = generate_reply(content, brand_name="", risk_level=risk_level, ai_enhance=False)
        d["reply_suggestion"] = _r.get("suggested_reply", "") if _r.get("action") == "SUGGEST_REPLY" else ""
        comments.append(d)
    cat_stats = {}
    for c in comments:
        cat_stats[c["category"]] = cat_stats.get(c["category"], 0) + 1
    return {"total": total, "returned": len(comments), "by_category": cat_stats, "comments": comments}


def generate_outreach(author_id: str, brand_name: str, campaign_name: str = "", *,
                      profile: dict, ai_enhance: bool = False) -> dict:
    """生成博主触达邀约文案（DRAFT 状态，不伪造已发送）。"""
    if not isinstance(brand_name, str) or not brand_name.strip():
        return {"ok": False, "error": "BRAND_SCOPE_REQUIRED"}
    if not isinstance(profile, dict) or profile.get("author_id") != author_id:
        return {"ok": False, "error": "KOS 不存在"}
    name = profile.get("author_nickname") or "博主"
    tier = profile.get("kos_tier")
    notes = profile.get("notes", [])
    top_topic = notes[0].get("title", "品牌相关内容") if notes else "优质内容"
    content_direction = "围绕已核验内容主题进一步沟通合作方向"
    if tier in ["S", "A"]:
        content_direction = "探店体验 / 活动报道 / 品牌故事"
    elif tier:
        content_direction = "单品测评 / 场景种草"
    benefits = "合作范围、权益与费用需双方另行确认"
    template = f"""您好，{name}：

我们是{brand_name}品牌团队。基于您此前发布的「{top_topic[:30]}」内容以及与{brand_name}的匹配度，希望邀请您参与我们的内容合作。

合作方向：
{content_direction}

合作权益：
{benefits}

如您感兴趣，欢迎回复与我们沟通具体合作方式。期待与您合作。

{brand_name}品牌团队"""
    # AI is optional; scoped callers default to the deterministic draft.
    _ai_text = (_ai_generate_outreach(name, tier or "", top_topic, brand_name, campaign_name)
                if ai_enhance else "")
    _content = _ai_text or template
    return {"ok": True, "status": "DRAFT", "author_id": author_id, "author_name": name,
            "tier": tier, "brand_name": brand_name, "campaign_name": campaign_name,
            "content": _content, "ai_source": bool(_ai_text),
            "content_source": "ai_enhancement" if _ai_text else "deterministic_rule",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


def _ai_generate_outreach(name: str, tier: str, top_topic: str,
                          brand_name: str, campaign_name: str) -> str:
    """智谱 AI 生成博主触达邀约文案（DRAFT，不发送）。失败/不可用返回空串。

    边界：不承诺未确认的报酬金额；不伪造已发送；官方账号只读红线不受影响。
    """
    try:
        import intelligence
        if not intelligence.ai_enabled():
            return ""
        _sys = (
            "你是品牌方商务合作负责人，请基于博主信息生成一条个性化、真诚的站内邀约文案（DRAFT，不发送）。"
            "硬性要求：1) 中文、礼貌、自然；2) 突出合作方向与合作权益，简洁（≤200字）；"
            "3) 不得承诺未确认的报酬金额、不得虚构合作事实、不得泄露内部信息；"
            "4) 只输出文案正文，不要解释或前缀。"
        )
        _user = (
            f"博主昵称：{name}\n分层：{tier}\n代表内容：{top_topic}\n"
            f"品牌：{brand_name}\n活动：{campaign_name or '品牌内容合作'}\n请只输出邀约文案正文："
        )
        _content, _provider, _ = intelligence.chat(_sys, _user, level='medium', temperature=0.4, max_tokens=400, pack_id='glm_4_5_air')
        _text = (_content or "").strip()
        if not _text or _provider == "rule":
            return ""
        return _text[:600]
    except Exception:
        return ""


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
        # P0 红线：互动量权重从平台规则读取
        from kos_metrics import platform_engagement, platform_ad_score
        note_platform = n.get("source_platform") or "xiaohongshu"
        eng = platform_engagement(note_platform, likes, comments, collects, shares)
        quality = n.get("content_quality_score") or 0
        risk = 1 if n.get("risk_level") in ["high", "medium"] else 0
        neg = 1 if n.get("sentiment") == "negative" else 0
        # P0 红线：投流评分从平台规则计算，禁止硬编码系数
        ad_result = platform_ad_score(
            note_platform, engagement=eng, likes=likes,
            comments=comments, collects=collects, quality=quality,
            is_risk=bool(risk), is_negative=bool(neg),
        )
        ad_score = ad_result["ad_score"]
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

def generate_reply(comment_text: str, brand_name: str,
                   reply_style: str = "professional", risk_level: str = "low",
                   ai_enhance: bool = False) -> dict:
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

    # 智谱 AI 生成建议（仅建议，不自动回复；HIGH/CRITICAL 已在上方 NO_REPLY 拦截）。
    # 分层：negative_feedback / purchase_intent 走强模型 ZHIPU_STRONG_MODEL（glm-5.3），其余默认 glm-4.5-air。
    # 批量列表场景 ai_enhance=False 走确定性规则模板（0网络）；单条按需生成才调AI
    _ai_reply = _ai_generate_reply(comment_text, brand_name, category, reply_style) if ai_enhance else ""
    _suggested = _ai_reply or templates.get(category, templates["general_interaction"])

    return {
        "ok": True,
        "action": "SUGGEST_REPLY",
        "category": category,
        "risk_level": risk_level,
        "reply_style": reply_style,
        "suggested_reply": _suggested,
        "ai_source": bool(_ai_reply),
        "auto_reply": False,  # 默认不自动回复，需人工确认
        "requires_approval": category in ("negative_feedback", "purchase_intent"),
    }


def _ai_generate_reply(comment_text: str, brand_name: str, category: str, reply_style: str) -> str:
    """智谱 AI 生成评论回复建议（DRAFT）。失败/不可用时返回空串，调用方回退规则模板。

    边界：只生成建议文本，不发送；不虚构事实、不承诺未确认权益；官方账号只读红线不受影响。
    """
    try:
        import intelligence
        if not intelligence.ai_enabled():
            return ""
        # 分层：负面/购买意向等需谨慎的复杂分类走强模型 glm-5.3，其余默认 glm-4.5-air
        _strong = category in ("negative_feedback", "purchase_intent")
        _model = intelligence._strong_model() if _strong else None
        _sys = (
            "你是品牌方专业客服，请基于用户评论生成一条自然、真诚、专业的中文回复建议。"
            "硬性要求：1) 简洁（≤80字）一句话即可；2) 有针对性，贴合评论内容；"
            "3) 不得虚构事实、不得承诺未经确认的优惠/权益/赔偿、不得泄露内部信息；"
            "4) 只输出回复正文，不要任何解释或前缀。"
            f"品牌：{brand_name}。回复风格：{reply_style}。评论分类：{category}。"
        )
        _user = f"用户评论：{comment_text[:300]}\n请只输出回复建议正文："
        _content, _provider, _ = intelligence.chat(_sys, _user, level='medium', temperature=0.3, max_tokens=300, model=_model, pack_id='glm_4_5_air')
        _text = (_content or "").strip()
        if not _text or _provider == "rule":
            return ""
        # 去掉模型可能输出的引号包裹
        return _text.strip('“”"\' ')[:160]
    except Exception:
        return ""


def extract_content_dna(author_id: str, limit: int = 20) -> dict:
    """提取KOS内容基因：选题/标题结构/内容主题/场景/品牌/产品/情绪/用户需求。

    从现有notes数据提取，不调用AI（AI可用时可增强语义标签）。
    """
    conn = get_repository().connect()
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
    # This aggregate is a read path: never bootstrap the KOS write schema just
    # to answer whether source notes exist in an isolated or not-yet-migrated DB.
    conn = get_repository().connect(timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        notes_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='notes'"
        ).fetchone()
        if notes_table is None:
            return {
                "brand": brand,
                "status": "unavailable",
                "note_count": None,
                "author_count": None,
                "last_captured_at": None,
            }
        cond, params = _brand_source_filter(brand)
        row = conn.execute(
            f"SELECT COUNT(*) AS note_count, COUNT(DISTINCT author_id) AS author_count, "
            f"MAX(captured_at) AS last_captured_at FROM notes WHERE {cond}",
            params,
        ).fetchone()
        return {
            "brand": brand,
            "status": "available" if row["note_count"] else "not_collected",
            "note_count": int(row["note_count"] or 0),
            "author_count": int(row["author_count"] or 0),
            "last_captured_at": row["last_captured_at"],
        }
    finally:
        conn.close()


def brand_profiles(brand: str, limit: int = 20) -> list:
    """品牌 KOS 作者实时聚合（不写 kos_profiles，与广州主链隔离）。"""
    # Brand profiles are derived from source notes and must remain read-only.
    conn = get_repository().connect(timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        notes_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='notes'"
        ).fetchone()
        if notes_table is None:
            return []
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
        from kos_metrics import platform_engagement
        for i, r in enumerate(rows):
            # P0 红线：互动量权重从平台规则读取
            eng = platform_engagement(
                brand or "xiaohongshu",
                r["total_likes"] or 0, r["total_comments"] or 0,
                r["total_collects"] or 0, r["total_shares"] or 0,
            )
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

# -*- coding: utf-8 -*-
"""KOS 主体归属 Gate（KOS_ENTITY_OWNERSHIP_CONTRACT_v1 / KOS MASTER EXECUTION CONTRACT v1）。
内容相关 ≠ 主体归属；商户/品牌 KOS ≠ 目标主体 KOS；AI 不越权、规则优先。
本模块只做确定性判定视图，不写回 kos_profiles，不改广州现有口径。
由施工追加到 kos_engine.py 末尾。
"""

# 归属类别（契约固定）
OWNERSHIP_CLASSES = [
    "TARGET_ENTITY_KOS", "BRAND_KOS", "MERCHANT_KOS", "PARTNER_KOS",
    "INDEPENDENT_KOL_KOC", "UGC_CONSUMER", "MEDIA", "OFFICIAL", "UNKNOWN",
]

# 现有身份信号 → 归属类别（确定性映射；仅基于真实字段，不推测）
_OWNERSHIP_BY_SUBJECT_TYPE = {
    "official": "OFFICIAL",
    "media": "MEDIA",
    "institution": "MEDIA",
    "kos": "INDEPENDENT_KOL_KOC",      # 现有 kos 仅表示"内容相关且有传播力"，不构成目标主体归属
    "normal_user": "UGC_CONSUMER",
}

_OWNERSHIP_STATE = {
    "OFFICIAL": "DIRECT",
    "MEDIA": "DIRECT",
    "BRAND_KOS": "INDIRECT",
    "MERCHANT_KOS": "MERCHANT",
    "PARTNER_KOS": "PARTNER",
    "INDEPENDENT_KOL_KOC": "INDEPENDENT",
    "UGC_CONSUMER": "UGC",
    "TARGET_ENTITY_KOS": "DIRECT",
    "UNKNOWN": "UNKNOWN",
}

_OWNERSHIP_CONFIDENCE = {
    "OFFICIAL": 0.95, "MEDIA": 0.85, "BRAND_KOS": 0.7, "MERCHANT_KOS": 0.7,
    "PARTNER_KOS": 0.7, "TARGET_ENTITY_KOS": 0.8,
    "INDEPENDENT_KOL_KOC": 0.6, "UGC_CONSUMER": 0.6, "UNKNOWN": 0.3,
}

_OWNERSHIP_REASON = {
    "OFFICIAL": "官方账号（subject_type=official）",
    "MEDIA": "媒体/机构身份（subject_type=media/institution）",
    "INDEPENDENT_KOL_KOC": "内容相关但无目标主体归属证据（内容相关≠KOS归属），须人工复核",
    "UGC_CONSUMER": "普通消费者内容（subject_type=normal_user），非目标主体KOS",
    "UNKNOWN": "身份信号不足，归属未知",
}


OVERRIDE_PATH = Path(DB_PATH).parent / "private" / "kos_ownership_overrides.json"


def _load_overrides() -> dict:
    """读取人工确认的归属 override（幂等，损坏返回空）。"""
    try:
        if OVERRIDE_PATH.exists():
            return json.loads(OVERRIDE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_overrides(data: dict) -> None:
    OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ownership_confirm(brand, author_id, ownership_class, confirmed_by="zachary") -> dict:
    """人工确认 KOS 主体归属（VERIFIED）。写入 override 文件，不碰数据库表。
    AI 只给建议（AI_SUGGESTED），人工确认后才生效；广州口径/官方账号只读不受影响。"""
    if ownership_class not in OWNERSHIP_CLASSES:
        raise ValueError(f"ownership_class 必须在: {OWNERSHIP_CLASSES}")
    if not author_id:
        raise ValueError("author_id required")
    data = _load_overrides()
    key = f"{brand or ''}::{author_id}"
    rec = {"brand": brand or "", "author_id": author_id, "ownership_class": ownership_class,
           "confirmed_by": confirmed_by, "confirmed_at": datetime.now().isoformat()}
    data[key] = rec
    _save_overrides(data)
    return rec


def _ownership_override(author_id, brand=""):
    """按 (brand, author_id) 或全局 author_id 查人工确认归属；无则 None。"""
    if not author_id:
        return None
    data = _load_overrides()
    if brand:
        r = data.get(f"{brand}::{author_id}")
        if r:
            return r
    return data.get(f"::{author_id}")


def ownership_for(profile, brand="", subject_type="", identity_label="", is_kos=None) -> dict:
    """主体归属判定（确定性规则，AI 不越权）。
    返回 ownership_class / state / confidence / needs_manual_review / reason / evidence_hint。
    仅判定视图，不写任何表；广州历史数据不受影响。
    """
    # 人工确认优先（VERIFIED override；AI 只建议不越权，确认后作为正式归属）
    _ov = _ownership_override((profile or {}).get("author_id") or "", brand)
    if _ov:
        owner = _ov.get("ownership_class", "UNKNOWN")
        return {
            "target_entity": brand or "",
            "ownership_class": owner,
            "ownership_state": _OWNERSHIP_STATE.get(owner, "UNKNOWN"),
            "ownership_confidence": 0.9,
            "needs_manual_review": False,
            "reason": f"人工确认归属（{_ov.get('confirmed_by','')} @ {_ov.get('confirmed_at','')}）",
            "evidence_hint": "override:" + json.dumps(_ov, ensure_ascii=False),
            "ai_status": "VERIFIED",
            "confirmed_by": _ov.get("confirmed_by", ""),
            "confirmed_at": _ov.get("confirmed_at", ""),
        }
    st = subject_type or (profile or {}).get("subject_type") or ""
    label = identity_label or (profile or {}).get("identity_label") or ""
    if is_kos is None:
        is_kos = bool((profile or {}).get("is_kos"))
    owner = _OWNERSHIP_BY_SUBJECT_TYPE.get(st, "UNKNOWN")
    # 品牌采集来源（方案A：source_keyword 品牌词）默认内容相关，无归属证据 → INDEPENDENT/UNKNOWN，须人工复核
    if not st:
        owner = "INDEPENDENT_KOL_KOC" if is_kos else "UNKNOWN"
    needs_review = owner in ("INDEPENDENT_KOL_KOC", "UNKNOWN", "UGC_CONSUMER", "BRAND_KOS", "MERCHANT_KOS")
    return {
        "target_entity": brand or "",
        "ownership_class": owner,
        "ownership_state": _OWNERSHIP_STATE.get(owner, "UNKNOWN"),
        "ownership_confidence": _OWNERSHIP_CONFIDENCE.get(owner, 0.5),
        "needs_manual_review": needs_review,
        "reason": _OWNERSHIP_REASON.get(owner, "待人工判定"),
        "ai_status": "RULE",
        "evidence_hint": "subject_type=" + (st or "空")
                         + (("; identity_label=" + label) if label else "")
                         + ("; is_kos=1" if is_kos else ""),
    }

# -*- coding: utf-8 -*-
"""KOS 采集功能增强（智谱 2026-09-03 设计 + KOS Master Contract v1 落地）。
1) content_relevance_score：确定性 relevance 信号（0-1），仅作 KOS 排序/分层信号，
   不替代主体硬过滤(subject_hit)、不因低分拒绝入库（不丢数据）；排除词命中 → 0分+need_recheck。
2) get_interaction_pattern：账号互动模式聚合（KOS 识别证据，从现有 notes 聚合，不新增生产字段）。
3) ownership_for 增加 ai_status 支持：AI 只给建议(AI_SUGGESTED)，人工复核后才 VERIFIED，不越权。
"""


def content_relevance_score(note, brand_keywords, exclude_keywords):
    """确定性 relevance 分数（0-1）。返回 dict：score/segment/need_recheck/reason。
    纯规则、无 AI、无外部依赖。低分不拒入库，仅作 KOS 排序/分层/Precision 评估信号。"""
    title = str(note.get("title") or "")
    body = str(note.get("body") or note.get("content") or "")
    other = " ".join(str(note.get(k) or "") for k in ("author_nickname", "source_keyword", "matched_keywords"))
    text = f"{title} {body} {other}".lower()
    if exclude_keywords and any(str(e).lower() in text for e in exclude_keywords if e):
        return {"score": 0.0, "segment": "excluded", "need_recheck": True,
                "reason": "排除词命中，须人工复核（不自动拒入库）"}
    tl, bl, ol = title.lower(), body.lower(), other.lower()
    hits, max_possible = 0, max(len(brand_keywords) * 3, 1)
    for kw in brand_keywords:
        k = str(kw).lower()
        if not k:
            continue
        if k in tl:
            hits += 3
        elif k in bl:
            hits += 2
        elif k in ol:
            hits += 1
    score = round(min(hits / max_possible, 1.0), 3)
    segment = "high" if score >= 0.7 else ("medium" if score >= 0.3 else "low")
    return {"score": score, "segment": segment, "need_recheck": segment == "low",
            "reason": f"品牌词命中 {hits}/{max_possible}"}


def get_interaction_pattern(author_id, brand="", limit=30):
    """账号互动模式聚合（KOS 识别证据）。从 notes 按作者聚合互动数据，不新增生产字段。
    返回：likes/comments/collects/shares 均值与中位数、平均互动率、note_count、last_publish_at。"""
    conn = _get_conn()
    try:
        cond = "author_id = ?"
        params = [author_id]
        if brand:
            bcond, bparams = _brand_source_filter(brand)
            if bcond != "1=0":
                cond += f" AND {bcond}"
                params += bparams
        rows = conn.execute(
            f"""SELECT note_id, likes, comments, collects, shares, publish_datetime
                FROM notes WHERE {cond} ORDER BY captured_at DESC LIMIT ?""",
            params + [int(limit)],
        ).fetchall()
        if not rows:
            return {"author_id": author_id, "note_count": 0, "pattern": "insufficient",
                    "reason": "暂无该账号笔记"}
        likes = [int(r["likes"] or 0) for r in rows]
        comments = [int(r["comments"] or 0) for r in rows]
        collects = [int(r["collects"] or 0) for r in rows]
        shares = [int(r["shares"] or 0) for r in rows]
        # P0 红线：互动量权重从平台规则读取
        from kos_metrics import platform_engagement
        eng = [platform_engagement(brand or "xiaohongshu", likes[i], comments[i], collects[i], shares[i])
               for i in range(len(rows))]
        n = len(rows)

        def _median(xs):
            s = sorted(xs)
            m = len(s)
            return s[m // 2] if m % 2 else round((s[m // 2 - 1] + s[m // 2]) / 2, 1)

        return {
            "author_id": author_id,
            "note_count": n,
            "avg_likes": round(sum(likes) / n, 1),
            "avg_comments": round(sum(comments) / n, 1),
            "avg_collects": round(sum(collects) / n, 1),
            "avg_shares": round(sum(shares) / n, 1),
            "median_engagement": _median(eng),
            "avg_engagement": round(sum(eng) / n, 1),
            "last_publish_at": rows[0]["publish_datetime"] if rows else None,
            "pattern": ("active" if n >= 3 else "emerging") if any(e > 50 for e in eng) else "quiet",
        }
    finally:
        conn.close()


def brand_kos_account(brand, author_id, limit=20):
    """品牌 KOS 单个账号 360° 增强视图：ownership + relevance + interaction。
    纯视图，不写任何表；AI 不越权（ai_status 默认 RULE，AI 建议走 AI_SUGGESTED + 人工复核）。"""
    conn = _get_conn()
    try:
        bcond, bparams = _brand_source_filter(brand)
        if bcond == "1=0":
            return None
        rows = conn.execute(
            f"""SELECT * FROM notes WHERE {bcond} AND author_id = ? ORDER BY captured_at DESC LIMIT ?""",
            bparams + [author_id, int(limit)],
        ).fetchall()
        if not rows:
            return None
        notes = [dict(r) for r in rows]
        from subject_rules import collect_keywords_for, get_brand_config
        kws = [k for k in collect_keywords_for(brand) if k]
        ex = list((get_brand_config(brand) or {}).get("exclude_words", []))
        rels = [content_relevance_score(n, kws, ex) for n in notes]
        avg_rel = round(sum(r["score"] for r in rels) / len(rels), 3) if rels else 0.0
        base = {
            "author_id": author_id,
            "author_nickname": notes[0].get("author_nickname") or "",
            "note_count": len(notes),
            "avg_relevance": avg_rel,
            "relevance_segment": "high" if avg_rel >= 0.7 else ("medium" if avg_rel >= 0.3 else "low"),
        }
        base["interaction"] = get_interaction_pattern(author_id, brand=brand, limit=limit)
        base["ownership"] = ownership_for(notes[0], brand=brand)
        base["ownership"]["ai_status"] = "RULE"  # 规则判定；AI 建议须经人工复核转 VERIFIED
        return base
    finally:
        conn.close()


# ===== IC-040 · KOS/内容运营兴趣图谱信号（附加评估维度，不改 kos_score 主计算）=====
# 依据：PCCC IC-040 §5。从"粉丝数导向"转向"兴趣图谱信号"：
#   完播/停留、DM 分享、搜索命中、内容资产化（长尾）。
# 口径红线：所有信号必须标注来源与可得性；不可得信号不编造，用现有代理指标（engagement_rate 等）
# 标注"代理指标"；禁止刷量/模拟点击/绕过平台风控获取信号（采集安全红线）。
# 本函数为纯只读聚合，不写 kos_profiles，不改变既有 kos_score 与分层。


# 信号源与可得性标注（来源契约：真实可得 vs 代理指标 vs 暂不可得）
SIGNAL_AVAILABILITY = {
    "watch_completion": {"source": "platform_api", "available": False,
                         "proxy": "avg_engagement/avg_likes", "note": "视频平台完播率 API 如可得"},
    "dm_share": {"source": "platform_api", "available": False,
                 "proxy": "avg_shares", "note": "私信分享/关系传播 API 如可得"},
    "search_hit": {"source": "platform_search_index", "available": False,
                   "proxy": "collects_ratio", "note": "小红书搜索索引化内容（长尾资产信号）"},
    "content_asset": {"source": "content_lifecycle", "available": False,
                      "proxy": "content_retention_window", "note": "中腰部内容长尾价值（12-18 个月窗口）"},
}


def interest_signal(author_id: str, brand: str = "", limit: int = 30) -> dict:
    """KOS 账号兴趣图谱信号（附加维度）。

    返回：
      {
        "author_id", "note_count", "signal_status",   # 数据可得性
        "signals": { 完播代理 / DM分享代理 / 搜索命中代理 / 内容资产化代理 },
        "proxies": 使用代理指标的显式标注（契约红线：不可得不编造）,
        "source_availability": SIGNAL_AVAILABILITY 的可读版本,
        "no_blackhat": True,   # 采集安全红线声明
      }
    """
    conn = _get_conn()
    try:
        cond = "author_id = ?"
        params = [author_id]
        if brand:
            bcond, bparams = _brand_source_filter(brand)
            if bcond != "1=0":
                cond += f" AND {bcond}"
                params += bparams
        rows = conn.execute(
            f"""SELECT note_id, likes, comments, collects, shares, publish_datetime
                FROM notes WHERE {cond} ORDER BY captured_at DESC LIMIT ?""",
            params + [int(limit)],
        ).fetchall()
        if not rows:
            return {"author_id": author_id, "note_count": 0, "signal_status": "insufficient",
                    "reason": "暂无该账号笔记", "signals": {}, "proxies": [],
                    "source_availability": SIGNAL_AVAILABILITY, "no_blackhat": True}
        n = len(rows)
        likes = [int(r["likes"] or 0) for r in rows]
        comments = [int(r["comments"] or 0) for r in rows]
        collects = [int(r["collects"] or 0) for r in rows]
        shares = [int(r["shares"] or 0) for r in rows]
        avg_likes = round(sum(likes) / n, 1)
        avg_comments = round(sum(comments) / n, 1)
        avg_collects = round(sum(collects) / n, 1)
        avg_shares = round(sum(shares) / n, 1)
        total_eng = sum(likes) + sum(comments) + sum(collects) + sum(shares)
        eng_rate = round(total_eng / n, 1) if n else 0.0

        # 兴趣图谱代理信号（契约：明确标注"代理指标"）
        signals = {
            # 完播/停留深度：平均互动量越高 → 内容深度代理
            "watch_depth_proxy": {
                "value": eng_rate, "unit": "avg_engagement/note",
                "proxy_of": "watch_completion", "label": "完播/停留深度（代理）",
            },
            # DM 分享/关系传播：平均分享量（分享是主动关系传播最强信号）
            "dm_share_proxy": {
                "value": avg_shares, "unit": "avg_shares/note",
                "proxy_of": "dm_share", "label": "私信/关系分享（代理）",
            },
            # 搜索命中/资产化：收藏率（收藏 = 长尾搜索索引与复看信号）
            "search_asset_proxy": {
                "value": round(avg_collects / avg_likes, 3) if avg_likes else 0.0,
                "unit": "collects/likes_ratio",
                "proxy_of": "search_hit", "label": "搜索索引/内容资产化（代理）",
            },
        }
        # 信号强度分级（附加评估，不进 kos_score）
        strength = "high" if (eng_rate >= 100 and avg_shares >= 10) else (
            "medium" if (eng_rate >= 30 and avg_shares >= 3) else "low")
        return {
            "author_id": author_id,
            "note_count": n,
            "signal_status": "proxy_estimated",  # 契约：代理指标，非平台原生信号
            "signals": signals,
            "strength": strength,
            "proxies": [
                "完播率/停留时长/DM分享/搜索命中为平台原生信号，当前 API 未接入，使用现有互动数据代理（明确标注，不编造）",
                "avg_engagement 代理完播/停留；avg_shares 代理 DM 分享；collects/likes 代理搜索资产化",
            ],
            "source_availability": SIGNAL_AVAILABILITY,
            "no_blackhat": True,
            "note": "附加评估维度，未计入 kos_score 主计算（防数字真相漂移）",
        }
    finally:
        conn.close()


# ===== IC-041 · 达人分层运营策略（头部/腰部/尾部/KOC）=====
# 依据：PCCC IC-041。基于粉丝量+互动率可配置阈值的达人分层。
# 与现有 S/A/B/C 分层（TIER_THRESHOLDS，按百分位）互补：
#   S/A/B/C = 品牌相关性+内容质量分层（KOS 内部）
#   head/waist/tail/KOC = 市场影响力分层（粉丝量+互动率，行业通用）
# 口径红线：阈值可配置，不硬编码；缺失粉丝量显式标记 unknown，不伪造分层。

# 默认分层阈值（可通过 config/kos_tier_config.json 覆盖）
DEFAULT_KOL_TIER_CONFIG = {
    "head": {
        "label": "头部达人",
        "min_followers": 500000,       # 粉丝 >= 50万
        "min_engagement_rate": 0.01,    # 互动率 >= 1%
        "actions": ["品牌代言", "重磅合作", "首发阵地", "长期框架"],
        "priority": 1,
    },
    "waist": {
        "label": "腰部达人",
        "min_followers": 100000,        # 粉丝 10万-50万
        "max_followers": 500000,
        "min_engagement_rate": 0.02,     # 互动率 >= 2%
        "actions": ["种草合作", "内容共创", "活动参与", "投流放大"],
        "priority": 2,
    },
    "tail": {
        "label": "尾部达人",
        "min_followers": 10000,          # 粉丝 1万-10万
        "max_followers": 100000,
        "min_engagement_rate": 0.03,     # 互动率 >= 3%
        "actions": ["批量种草", "内容铺量", "口碑建设", "长尾覆盖"],
        "priority": 3,
    },
    "koc": {
        "label": "KOC（关键意见消费者）",
        "max_followers": 10000,          # 粉丝 < 1万
        "min_engagement_rate": 0.05,     # 互动率 >= 5%
        "actions": ["真实体验", "口碑扩散", "社群运营", "UGC激励"],
        "priority": 4,
    },
    "unknown": {
        "label": "数据不足/未分层",
        "actions": ["补充粉丝量数据", "观察期", "暂不投入"],
        "priority": 99,
    },
}


def load_kol_tier_config(config_path: str = "") -> dict:
    """加载达人分层配置（可配置，不硬编码）。"""
    import copy
    config = copy.deepcopy(DEFAULT_KOL_TIER_CONFIG)
    if not config_path:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "config", "kol_tier_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                custom = json.load(f)
            for tier, params in custom.items():
                if tier in config and isinstance(params, dict):
                    config[tier].update(params)
        except Exception as e:
            print(f"[KOS-IC041] 加载分层配置失败，使用默认: {e}")
    return config


def classify_kol_tier(followers=None, engagement_rate=None,
                       config: dict = None) -> dict:
    """基于粉丝量+互动率对达人分层（IC-041）。

    Args:
        followers: 粉丝量（int，None=未知）
        engagement_rate: 互动率（float 0-1，None=未知）
        config: 分层配置（默认加载 DEFAULT_KOL_TIER_CONFIG）

    Returns:
        {
            "tier": "head"/"waist"/"tail"/"koc"/"unknown",
            "label": str,
            "followers": int/None,
            "engagement_rate": float/None,
            "actions": list,
            "priority": int,
            "data_available": bool,   # 数据是否充足
            "reason": str,            # 分层依据
        }

    硬红线：
    - 粉丝量缺失 → unknown，不伪造分层
    - 互动率缺失 → 仅按粉丝量分层，标记 engagement_unknown
    - 阈值可配置，不硬编码
    """
    if config is None:
        config = load_kol_tier_config()

    # 数据可得性检查
    followers_available = followers is not None and isinstance(followers, (int, float)) and followers >= 0
    engagement_available = engagement_rate is not None and isinstance(engagement_rate, (int, float)) and engagement_rate >= 0

    if not followers_available:
        # 粉丝量缺失 → unknown（不伪造）
        tier_cfg = config.get("unknown", {})
        return {
            "tier": "unknown",
            "label": tier_cfg.get("label", "数据不足/未分层"),
            "followers": None,
            "engagement_rate": engagement_rate if engagement_available else None,
            "actions": tier_cfg.get("actions", []),
            "priority": tier_cfg.get("priority", 99),
            "data_available": False,
            "reason": "粉丝量数据缺失，无法分层（不伪造）",
            "engagement_unknown": not engagement_available,
        }

    followers = int(followers)
    eng_rate = float(engagement_rate) if engagement_available else None

    # 按粉丝量+互动率分层
    for tier_name in ["head", "waist", "tail", "koc"]:
        tier_cfg = config.get(tier_name, {})
        min_f = tier_cfg.get("min_followers", 0)
        max_f = tier_cfg.get("max_followers", float("inf"))
        min_er = tier_cfg.get("min_engagement_rate", 0)

        # 粉丝量范围检查
        if followers < min_f or followers > max_f:
            continue

        # 互动率检查（如果有数据）
        if eng_rate is not None and eng_rate < min_er:
            # 互动率不达标 → 降一级或标记 low_engagement
            continue

        # 命中分层
        reason = f"粉丝量 {followers:,} 落在 {tier_name} 区间"
        if eng_rate is not None:
            reason += f"，互动率 {eng_rate:.2%} >= 阈值 {min_er:.2%}"
        else:
            reason += "（互动率未知，仅按粉丝量分层）"

        return {
            "tier": tier_name,
            "label": tier_cfg.get("label", tier_name),
            "followers": followers,
            "engagement_rate": eng_rate,
            "actions": tier_cfg.get("actions", []),
            "priority": tier_cfg.get("priority", 99),
            "data_available": True,
            "reason": reason,
            "engagement_unknown": eng_rate is None,
        }

    # 未命中任何分层（如粉丝量在区间但互动率不达标）
    tier_cfg = config.get("unknown", {})
    return {
        "tier": "unknown",
        "label": "互动率不达标/未分层",
        "followers": followers,
        "engagement_rate": eng_rate,
        "actions": tier_cfg.get("actions", []),
        "priority": tier_cfg.get("priority", 99),
        "data_available": True,
        "reason": f"粉丝量 {followers:,} 但互动率 {eng_rate:.2% if eng_rate else 'N/A'} 未达分层阈值",
        "engagement_unknown": eng_rate is None,
    }


def batch_classify_kol_tiers(authors: list, config: dict = None) -> list:
    """批量对达人列表分层（IC-041）。

    Args:
        authors: 达人列表，每项需含 author_id/followers/engagement_rate 字段
        config: 分层配置

    Returns:
        分层结果列表（按 priority 排序）
    """
    if config is None:
        config = load_kol_tier_config()

    results = []
    for author in authors:
        author_id = author.get("author_id", author.get("id", ""))
        followers = author.get("followers", author.get("follower_count"))
        engagement_rate = author.get("engagement_rate", author.get("avg_engagement_rate"))
        tier_result = classify_kol_tier(followers, engagement_rate, config)
        tier_result["author_id"] = author_id
        tier_result["author_nickname"] = author.get("author_nickname", author.get("nickname", ""))
        results.append(tier_result)

    # 按 priority 排序
    results.sort(key=lambda x: x.get("priority", 99))
    return results


def get_kol_tier_summary(authors: list, config: dict = None) -> dict:
    """获取达人分层统计摘要（看板用）。"""
    if config is None:
        config = load_kol_tier_config()

    classified = batch_classify_kol_tiers(authors, config)
    summary = {tier: 0 for tier in ["head", "waist", "tail", "koc", "unknown"]}
    for item in classified:
        tier = item.get("tier", "unknown")
        summary[tier] = summary.get(tier, 0) + 1

    total = len(classified)
    return {
        "total": total,
        "distribution": summary,
        "percentages": {t: round(c / total * 100, 1) if total > 0 else 0.0
                         for t, c in summary.items()},
        "classified_list": classified,
        "config_used": {t: {"label": c.get("label"), "min_followers": c.get("min_followers"),
                              "max_followers": c.get("max_followers"),
                              "min_engagement_rate": c.get("min_engagement_rate")}
                         for t, c in config.items() if t != "unknown"},
    }
