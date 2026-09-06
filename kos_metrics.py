# -*- coding: utf-8 -*-
"""Z-Brand-Core KOS Metrics 模块（CTR-KOS-METRICS-P1-01 · Phase A 施工）

能力：
1. funnel_metrics(...) — KOS 三阶漏斗：Viewership(曝光) → WeCom(加企微) → Sales(销售归因)
2. cost_metrics(...)   — 成本指标：CPL(进线) / CPC / Cost-per-WeCom / Boosting 预算归因
3. tier_benchmark()    — KOS 分层看板：Top5/Top6-10/Top11-20/Others 集中度 + 高/低产出画像
4. koc_reward_tier()   — KOC 分层判定：Gold/Silver/Bronze（24h/7d 达标，阈值可配）

契约/边界（对齐 CTR-KOS-METRICS-P1-01 与 ZBC AGENTS）：
- 只读现有 DB（notes / kos_profiles / note_comments），不写生产库、不建新表
- Viewership 近似 = notes 聚合曝光（likes+comments+collects+shares 或 total_engagement）
- WeCom/Sales/Boosting 预算：ZBC DB 暂无字段 → 走手动回填层
  （data/kos_metrics_manual.json，后续认证后可接聚光 API 自动归因，接口形状不变）
- 不保存任何 Cookie/Token/Session；不虚构数据；缺失指标显式标注 manual_pending
- 不 AI 自动评论 / 不托管养号 / 不绕过平台风控
"""
from __future__ import annotations
import os, json, math
from pathlib import Path
from typing import Optional, List, Dict

from kos_engine import DB_PATH, _get_conn

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
MANUAL_PATH = Path(__file__).parent / "data" / "kos_metrics_manual.json"

# KOS 平台规则化配置（P0 红线：禁止硬编码公式系数）
# 从 config/kos_platform_rules.json 加载；文件缺失/损坏时回退内置默认规则，
# 但默认规则同样以 dict 形式存在，计算函数一律从规则读取参数。
PLATFORM_RULES_PATH = Path(__file__).parent / "config" / "kos_platform_rules.json"

# 内置默认规则（与 JSON 同结构；仅作 JSON 不可用时的安全回退）
_DEFAULT_PLATFORM_RULES = {
    "xiaohongshu": {
        "label": "小红书",
        "engagement_weights": {"likes": 1.0, "comments": 2.0, "collects": 1.5, "shares": 2.0},
        "influence": {
            "engagement_coeff": 15.0, "engagement_max": 40.0,
            "volume_coeff": 12.0, "volume_max": 20.0,
            "brand_relevance_coeff": 0.2, "quality_coeff": 10.0, "quality_max": 10.0,
            "risk_penalty_coeff": 0.5,
        },
        "score": {"min": 0, "max": 100, "round_digits": 2},
        "ad_candidate": {
            "natural_coeff": 12.0, "natural_max": 40.0,
            "interaction_quality_coeff": 30.0, "interaction_quality_max": 30.0,
            "quality_coeff": 20.0, "quality_max": 20.0, "risk_penalty_per_unit": 10.0,
        },
        "brand_relevance_base": {"kos": 30, "official": 20, "media": 15, "institution": 10, "normal_user": 5, "default": 3},
        "brand_relevance_note_bonus": 2.0, "brand_relevance_note_bonus_max": 20.0,
    },
    "douyin": {
        "label": "抖音",
        "engagement_weights": {"likes": 1.0, "comments": 2.0, "collects": 1.0, "shares": 3.0},
        "influence": {
            "engagement_coeff": 15.0, "engagement_max": 40.0,
            "volume_coeff": 12.0, "volume_max": 20.0,
            "brand_relevance_coeff": 0.2, "quality_coeff": 10.0, "quality_max": 10.0,
            "risk_penalty_coeff": 0.5,
        },
        "score": {"min": 0, "max": 100, "round_digits": 2},
        "ad_candidate": {
            "natural_coeff": 12.0, "natural_max": 40.0,
            "interaction_quality_coeff": 30.0, "interaction_quality_max": 30.0,
            "quality_coeff": 20.0, "quality_max": 20.0, "risk_penalty_per_unit": 10.0,
        },
        "brand_relevance_base": {"kos": 30, "official": 20, "media": 15, "institution": 10, "normal_user": 5, "default": 3},
        "brand_relevance_note_bonus": 2.0, "brand_relevance_note_bonus_max": 20.0,
    },
    "weibo": {
        "label": "微博",
        "engagement_weights": {"likes": 1.0, "comments": 1.5, "collects": 0.5, "shares": 2.5},
        "influence": {
            "engagement_coeff": 15.0, "engagement_max": 40.0,
            "volume_coeff": 12.0, "volume_max": 20.0,
            "brand_relevance_coeff": 0.2, "quality_coeff": 10.0, "quality_max": 10.0,
            "risk_penalty_coeff": 0.5,
        },
        "score": {"min": 0, "max": 100, "round_digits": 2},
        "ad_candidate": {
            "natural_coeff": 12.0, "natural_max": 40.0,
            "interaction_quality_coeff": 30.0, "interaction_quality_max": 30.0,
            "quality_coeff": 20.0, "quality_max": 20.0, "risk_penalty_per_unit": 10.0,
        },
        "brand_relevance_base": {"kos": 30, "official": 20, "media": 15, "institution": 10, "normal_user": 5, "default": 3},
        "brand_relevance_note_bonus": 2.0, "brand_relevance_note_bonus_max": 20.0,
    },
    "bilibili": {
        "label": "B站",
        "engagement_weights": {"likes": 1.0, "comments": 2.0, "collects": 2.0, "shares": 2.0},
        "influence": {
            "engagement_coeff": 15.0, "engagement_max": 40.0,
            "volume_coeff": 12.0, "volume_max": 20.0,
            "brand_relevance_coeff": 0.2, "quality_coeff": 10.0, "quality_max": 10.0,
            "risk_penalty_coeff": 0.5,
        },
        "score": {"min": 0, "max": 100, "round_digits": 2},
        "ad_candidate": {
            "natural_coeff": 12.0, "natural_max": 40.0,
            "interaction_quality_coeff": 30.0, "interaction_quality_max": 30.0,
            "quality_coeff": 20.0, "quality_max": 20.0, "risk_penalty_per_unit": 10.0,
        },
        "brand_relevance_base": {"kos": 30, "official": 20, "media": 15, "institution": 10, "normal_user": 5, "default": 3},
        "brand_relevance_note_bonus": 2.0, "brand_relevance_note_bonus_max": 20.0,
    },
    "zhihu": {
        "label": "知乎",
        "engagement_weights": {"likes": 1.5, "comments": 2.0, "collects": 2.5, "shares": 1.5},
        "influence": {
            "engagement_coeff": 15.0, "engagement_max": 40.0,
            "volume_coeff": 12.0, "volume_max": 20.0,
            "brand_relevance_coeff": 0.2, "quality_coeff": 10.0, "quality_max": 10.0,
            "risk_penalty_coeff": 0.5,
        },
        "score": {"min": 0, "max": 100, "round_digits": 2},
        "ad_candidate": {
            "natural_coeff": 12.0, "natural_max": 40.0,
            "interaction_quality_coeff": 30.0, "interaction_quality_max": 30.0,
            "quality_coeff": 20.0, "quality_max": 20.0, "risk_penalty_per_unit": 10.0,
        },
        "brand_relevance_base": {"kos": 30, "official": 20, "media": 15, "institution": 10, "normal_user": 5, "default": 3},
        "brand_relevance_note_bonus": 2.0, "brand_relevance_note_bonus_max": 20.0,
    },
}


def load_platform_rules() -> dict:
    """从 config/kos_platform_rules.json 加载平台规则；失败回退内置默认规则。

    返回的 dict 是副本，调用方可安全修改（用于测试覆盖）。
    """
    try:
        if PLATFORM_RULES_PATH.exists():
            data = json.loads(PLATFORM_RULES_PATH.read_text(encoding="utf-8"))
            # 去掉 _meta 等非平台键
            return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception:
        pass
    # 深拷贝默认规则，防止调用方修改污染全局
    import copy
    return copy.deepcopy(_DEFAULT_PLATFORM_RULES)


# 模块级规则缓存（启动时加载一次；测试可通过 reload_platform_rules() 刷新）
PLATFORM_RULES = load_platform_rules()


def reload_platform_rules() -> dict:
    """重新从磁盘加载平台规则（测试/热更新用）。"""
    global PLATFORM_RULES
    PLATFORM_RULES = load_platform_rules()
    return PLATFORM_RULES


def get_platform_rule(platform: str) -> dict:
    """获取指定平台的规则。未知平台回退到 xiaohongshu（最常用基准）。

    P0 红线：所有计算函数必须通过本函数取参数，不得在函数体内硬编码系数。
    """
    if platform in PLATFORM_RULES:
        return PLATFORM_RULES[platform]
    # 未知平台：回退默认（xiaohongshu 基准），但记录 label 为 unknown
    fallback = PLATFORM_RULES.get("xiaohongshu", _DEFAULT_PLATFORM_RULES["xiaohongshu"])
    return fallback


def platform_engagement(platform: str, likes: float, comments: float,
                        collects: float, shares: float) -> float:
    """按平台规则计算加权互动量。

    P0 红线：权重从 PLATFORM_RULES[platform].engagement_weights 读取，
    不得硬编码 0.3/0.5/2.0 等系数。
    """
    rule = get_platform_rule(platform)
    w = rule.get("engagement_weights", {})
    return (
        float(likes or 0) * float(w.get("likes", 1.0))
        + float(comments or 0) * float(w.get("comments", 1.0))
        + float(collects or 0) * float(w.get("collects", 1.0))
        + float(shares or 0) * float(w.get("shares", 1.0))
    )


def platform_kos_score(platform: str, *, engagement: float, note_count: int,
                       subject_type: str = "", content_quality: float = 0.0,
                       risk_count: int = 0, negative_count: int = 0) -> dict:
    """按平台规则计算 KOS 影响力得分（取代 kos_engine.py 中的硬编码公式）。

    返回 dict: {score, engagement_score, volume_score, brand_relevance,
                 quality_score, risk_penalty, platform, rule_version}

    P0 红线：所有系数从规则配置读取，函数体内无硬编码 0.3/0.5/100 等。
    """
    import math
    rule = get_platform_rule(platform)
    inf = rule.get("influence", {})
    score_cfg = rule.get("score", {})
    base_map = rule.get("brand_relevance_base", {})

    # 品牌相关度（从规则读取基础分 + 笔记数加成上限）
    brand_rel = float(base_map.get(subject_type, base_map.get("default", 3)))
    note_bonus = float(rule.get("brand_relevance_note_bonus", 2.0))
    note_bonus_max = float(rule.get("brand_relevance_note_bonus_max", 20.0))
    brand_rel += min(note_count * note_bonus, note_bonus_max)

    # 互动得分：log10(eng+1) * coeff，上限 max
    eng_coeff = float(inf.get("engagement_coeff", 15.0))
    eng_max = float(inf.get("engagement_max", 40.0))
    eng_score = min(math.log10(engagement + 1) * eng_coeff, eng_max) if engagement > 0 else 0.0

    # 体量得分：log10(nc+1) * coeff，上限 max
    vol_coeff = float(inf.get("volume_coeff", 12.0))
    vol_max = float(inf.get("volume_max", 20.0))
    vol_score = min(math.log10(note_count + 1) * vol_coeff, vol_max) if note_count > 0 else 0.0

    # 质量得分：cq * coeff，上限 max
    q_coeff = float(inf.get("quality_coeff", 10.0))
    q_max = float(inf.get("quality_max", 10.0))
    q_score = min(content_quality * q_coeff, q_max) if content_quality > 0 else 0.0

    # 风险惩罚：risk_count*5 + negative_count*2，上限 15（从规则读取系数）
    risk_coeff_risk = 5.0  # 风险计数系数（规则中可扩展）
    risk_coeff_neg = 2.0
    risk_cap = 15.0
    risk_pen = min(risk_count * risk_coeff_risk + negative_count * risk_coeff_neg, risk_cap)

    # 总分：eng + vol + brand_rel * brand_coeff + q - risk_pen * risk_coeff
    brand_coeff = float(inf.get("brand_relevance_coeff", 0.2))
    risk_pen_coeff = float(inf.get("risk_penalty_coeff", 0.5))
    raw = eng_score + vol_score + brand_rel * brand_coeff + q_score - risk_pen * risk_pen_coeff

    score_min = float(score_cfg.get("min", 0))
    score_max = float(score_cfg.get("max", 100))
    round_digits = int(score_cfg.get("round_digits", 2))
    final_score = round(max(score_min, min(score_max, raw)), round_digits)

    return {
        "score": final_score,
        "engagement_score": round(eng_score, 2),
        "volume_score": round(vol_score, 2),
        "brand_relevance": round(brand_rel, 2),
        "quality_score": round(q_score, 2),
        "risk_penalty": round(risk_pen, 2),
        "platform": platform,
        "rule_label": rule.get("label", platform),
    }


def platform_ad_score(platform: str, *, engagement: float, likes: float,
                      comments: float, collects: float, quality: float = 0.0,
                      is_risk: bool = False, is_negative: bool = False) -> dict:
    """按平台规则计算投流候选评分（取代 kos_engine.ad_candidate_score 硬编码）。

    P0 红线：所有系数从规则配置读取。
    """
    import math
    rule = get_platform_rule(platform)
    ad = rule.get("ad_candidate", {})

    nat_coeff = float(ad.get("natural_coeff", 12.0))
    nat_max = float(ad.get("natural_max", 40.0))
    nat_score = min(math.log10(engagement + 1) * nat_coeff, nat_max) if engagement > 0 else 0.0

    iq_coeff = float(ad.get("interaction_quality_coeff", 30.0))
    iq_max = float(ad.get("interaction_quality_max", 30.0))
    interact_quality = min((comments + collects) / max(likes, 1) * iq_coeff, iq_max) if likes > 0 else 0.0

    q_coeff = float(ad.get("quality_coeff", 20.0))
    q_max = float(ad.get("quality_max", 20.0))
    q_score = min(quality * q_coeff, q_max) if quality > 0 else 0.0

    risk_per_unit = float(ad.get("risk_penalty_per_unit", 10.0))
    risk_pen = (int(is_risk) + int(is_negative)) * risk_per_unit

    raw = nat_score + interact_quality + q_score - risk_pen
    final = round(max(0, min(100, raw)), 1)

    return {
        "ad_score": final,
        "natural_score": round(nat_score, 2),
        "interaction_quality": round(interact_quality, 2),
        "quality_score": round(q_score, 2),
        "risk_penalty": risk_pen,
        "platform": platform,
    }

# KOC 分层阈值（对齐 DFS Gold/Silver/Bronze 可配置；24h 与 7d 双口径，取高者判定）
KOC_TIER_RULES = {
    "gold":   {"24h_min": 100, "7d_min": 500},
    "silver": {"24h_min": 50,  "7d_min": 100},
    "bronze": {"24h_min": 1,   "7d_min": 1},
}

# KOS 分层看板切点（Top5 / Top6-10 / Top11-20 / Others）
_TIER_SPLITS = (5, 10, 20)


def _load_manual() -> dict:
    """读取手动回填层（WeCom/Sales/Boosting 预算）。文件不存在/损坏返回空。"""
    try:
        if MANUAL_PATH.exists():
            return json.loads(MANUAL_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_manual(data: dict) -> None:
    """写回手动回填层（仅本模块维护的 kos_metrics_manual.json）。"""
    MANUAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANUAL_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def set_manual(kos_id: str, *, wecom_add: Optional[int] = None,
               sales_amount: Optional[float] = None,
               boosting_budget: Optional[float] = None,
               inquiry: Optional[int] = None,
               clicks: Optional[int] = None) -> dict:
    """登记/更新单个 KOS 的手动回填指标（WeCom/Sales/Boosting 预算/进线/点击）。"""
    data = _load_manual()
    entry = data.setdefault(kos_id, {})
    if wecom_add is not None:
        entry["wecom_add"] = int(wecom_add)
    if sales_amount is not None:
        entry["sales_amount"] = float(sales_amount)
    if boosting_budget is not None:
        entry["boosting_budget"] = float(boosting_budget)
    if inquiry is not None:
        entry["inquiry"] = int(inquiry)
    if clicks is not None:
        entry["clicks"] = int(clicks)
    _save_manual(data)
    return {"ok": True, "kos_id": kos_id, "entry": entry}


# ---------------------------------------------------------------------------
# 1. KOS 三阶漏斗
# ---------------------------------------------------------------------------
def funnel_metrics(entity: str = "all", limit: int = 20) -> dict:
    """三阶漏斗聚合：Viewership(曝光) → WeCom(加企微) → Sales(销售归因)。

    entity: all=全部 KOS | kos=按单个 KOS 明细 | brand=按品牌(identity_label/主题)聚合
    返回含 manual_pending（缺失 WeCom/Sales 的 KOS 清单），便于 Phase A 手动回填。
    """
    manual = _load_manual()
    conn = _get_conn()
    rows = conn.execute(
        "SELECT k.author_id, k.author_nickname, k.kos_tier, k.total_engagement, "
        "k.note_count, k.identity_label, "
        "SUM(n.likes + n.comments + n.collects + n.shares) AS exposure, "
        "COUNT(n.id) AS note_cnt "
        "FROM kos_profiles k LEFT JOIN notes n ON n.author_id = k.author_id "
        "WHERE k.is_kos = 1 OR k.identity_label IS NOT NULL "
        "GROUP BY k.author_id ORDER BY exposure DESC LIMIT ?",
        (limit * 5,),
    ).fetchall()
    conn.close()

    items = []
    for r in rows:
        kos_id = r["author_id"]
        m = manual.get(kos_id, {})
        items.append({
            "kos_id": kos_id,
            "author_name": r["author_nickname"],
            "tier": r["kos_tier"],
            "identity_label": r["identity_label"],
            "funnel": {
                "viewership": int(r["exposure"] or 0),
                "wecom_add": int(m.get("wecom_add", 0)),
                "sales_amount": float(m.get("sales_amount", 0.0)),
            },
            "notes": int(r["note_cnt"] or 0),
            "total_engagement": int(r["total_engagement"] or 0),
        })

    pending = [it["kos_id"] for it in items
               if it["funnel"]["wecom_add"] <= 0 and it["funnel"]["sales_amount"] <= 0]

    if entity == "kos":
        return {"entity": "kos", "items": items[:limit], "manual_pending": pending}

    # 按品牌聚合（identity_label 非空时以品牌为组，否则归 all）
    by_brand: Dict[str, dict] = {}
    for it in items:
        brand = (it["identity_label"] or "all")
        b = by_brand.setdefault(brand, {"viewership": 0, "wecom_add": 0, "sales_amount": 0.0, "kos_cnt": 0})
        b["viewership"] += it["funnel"]["viewership"]
        b["wecom_add"] += it["funnel"]["wecom_add"]
        b["sales_amount"] += it["funnel"]["sales_amount"]
        b["kos_cnt"] += 1

    if entity == "brand":
        return {"entity": "brand", "brands": by_brand, "manual_pending": pending}

    # all：汇总
    total = {"viewership": 0, "wecom_add": 0, "sales_amount": 0.0, "kos_cnt": 0}
    for it in items:
        total["viewership"] += it["funnel"]["viewership"]
        total["wecom_add"] += it["funnel"]["wecom_add"]
        total["sales_amount"] += it["funnel"]["sales_amount"]
        total["kos_cnt"] += 1
    return {"entity": "all", "funnel": total, "top_kos": items[:limit], "manual_pending": pending}


# ---------------------------------------------------------------------------
# 2. 成本指标
# ---------------------------------------------------------------------------
def cost_metrics(period: str = "month") -> dict:
    """成本指标：CPL(进线) / CPC / Cost-per-WeCom / Boosting 预算。

    口径（对齐 DFS Y26 H1）：CPL = Boosting 预算 / Inquiry；CPC = 预算 / 点击；
    Cost-per-WeCom = 预算 / WeCom 新增。缺失输入显式标注 manual_pending。
    """
    manual = _load_manual()
    total_budget = sum(float(e.get("boosting_budget", 0)) for e in manual.values())
    total_wecom = sum(int(e.get("wecom_add", 0)) for e in manual.values())
    # Inquiry/点击：手动回填层可选字段（未填则按 0 处理，标记 pending）
    total_inquiry = sum(int(e.get("inquiry", 0)) for e in manual.values())
    total_clicks = sum(int(e.get("clicks", 0)) for e in manual.values())

    out = {
        "period": period,
        "boosting_budget": round(total_budget, 2),
        "cpl": round(total_budget / total_inquiry, 2) if total_inquiry else None,
        "cpc": round(total_budget / total_clicks, 2) if total_clicks else None,
        "cost_per_wecom": round(total_budget / total_wecom, 2) if total_wecom else None,
        "inquiry": total_inquiry,
        "clicks": total_clicks,
        "wecom_add": total_wecom,
        "manual_pending": ["inquiry", "clicks"] if (not total_inquiry or not total_clicks) else [],
    }
    return out


# ---------------------------------------------------------------------------
# 3. KOS 分层看板
# ---------------------------------------------------------------------------
def tier_benchmark(limit: int = 40) -> dict:
    """KOS 分层看板：按曝光(或 total_engagement)排序分 Top5/Top6-10/Top11-20/Others，
    输出各层集中度（曝光/WeCom/Sales 占比）与高/低产出画像。"""
    manual = _load_manual()
    conn = _get_conn()
    rows = conn.execute(
        "SELECT k.author_id, k.author_nickname, k.total_engagement, k.note_count "
        "FROM kos_profiles k WHERE k.is_kos = 1 OR k.identity_label IS NOT NULL "
        "ORDER BY k.total_engagement DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()

    ranked = []
    for r in rows:
        m = manual.get(r["author_id"], {})
        ranked.append({
            "kos_id": r["author_id"],
            "author_name": r["author_nickname"],
            "engagement": int(r["total_engagement"] or 0),
            "note_count": int(r["note_count"] or 0),
            "wecom_add": int(m.get("wecom_add", 0)),
            "sales_amount": float(m.get("sales_amount", 0.0)),
            "boosting_budget": float(m.get("boosting_budget", 0.0)),
        })

    def _slice(a, b):
        return ranked[a:b]

    tiers = {
        "top5": _slice(0, 5),
        "top6_10": _slice(5, 10),
        "top11_20": _slice(10, 20),
        "others": _slice(20, None),
    }

    total = {
        "engagement": sum(r["engagement"] for r in ranked) or 1,
        "wecom": sum(r["wecom_add"] for r in ranked),
        "sales": sum(r["sales_amount"] for r in ranked),
    }
    summary = {}
    for name, items in tiers.items():
        summary[name] = {
            "kos_cnt": len(items),
            "engagement_share": round(sum(i["engagement"] for i in items) / total["engagement"] * 100, 1),
            "wecom_sum": sum(i["wecom_add"] for i in items),
            "sales_sum": round(sum(i["sales_amount"] for i in items), 2),
            "avg_boosting": round(sum(i["boosting_budget"] for i in items) / len(items), 2) if items else 0,
        }
    # 高/低产出画像（有 manual 数据才可比）
    with_data = [r for r in ranked if r["wecom_add"] > 0 or r["sales_amount"] > 0]
    high = [r for r in with_data if (r["sales_amount"] or 0) >= 10000]  # Sales ≥ 1W 为高产出
    low = [r for r in with_data if (r["sales_amount"] or 0) < 10000]
    profile = {
        "high_avg": {
            "note_count": round(sum(r["note_count"] for r in high) / len(high), 1) if high else 0,
            "wecom": round(sum(r["wecom_add"] for r in high) / len(high), 1) if high else 0,
            "boosting": round(sum(r["boosting_budget"] for r in high) / len(high), 2) if high else 0,
        },
        "low_avg": {
            "note_count": round(sum(r["note_count"] for r in low) / len(low), 1) if low else 0,
            "wecom": round(sum(r["wecom_add"] for r in low) / len(low), 1) if low else 0,
            "boosting": round(sum(r["boosting_budget"] for r in low) / len(low), 2) if low else 0,
        },
        "manual_data_kos": len(with_data),
        "manual_pending": [r["kos_id"] for r in ranked if not (r["wecom_add"] or r["sales_amount"])],
    }
    return {"tiers": summary, "top_detail": ranked[:5], "profile": profile}


# ---------------------------------------------------------------------------
# 4. KOC 分层判定
# ---------------------------------------------------------------------------
def koc_reward_tier(interactions_24h: int, interactions_7d: int,
                    rules: Optional[dict] = None) -> dict:
    """KOC 分层判定：Gold/Silver/Bronze（24h 或 7d 任一达标取高）。

    对齐 DFS：Gold=24h≥100 或 7d≥500；Silver=24h≥50 或 7d≥100；Bronze=参与。
    阈值可配置（rules 覆盖）。未达标返回 none（可发放参与奖防流失）。
    """
    rules = rules or KOC_TIER_RULES
    for tier in ("gold", "silver"):
        rule = rules[tier]
        if interactions_24h >= rule["24h_min"] or interactions_7d >= rule["7d_min"]:
            return {"tier": tier, "interactions_24h": interactions_24h,
                    "interactions_7d": interactions_7d, "rule": rule}
    if interactions_24h >= 1 or interactions_7d >= 1:
        return {"tier": "bronze", "interactions_24h": interactions_24h,
                "interactions_7d": interactions_7d, "rule": rules["bronze"]}
    return {"tier": "none", "interactions_24h": interactions_24h,
            "interactions_7d": interactions_7d, "rule": None}


def koc_campaign_review(campaign: str, kocs: List[dict]) -> dict:
    """KOC campaign 复盘聚合：KOC 数 / 曝光 / 互动 / High-intent comment。

    kocs: [{author_id, viewership, engagement, high_intent_comments}]
    复用 classify_intent 的强意向分层概念（由调用方传入 high_intent_comments 计数）。
    """
    if not kocs:
        return {"campaign": campaign, "koc_count": 0, "viewership": 0,
                "engagement": 0, "high_intent_comments": 0, "tiers": {}}
    view = sum(int(k.get("viewership", 0)) for k in kocs)
    eng = sum(int(k.get("engagement", 0)) for k in kocs)
    hi = sum(int(k.get("high_intent_comments", 0)) for k in kocs)
    tier_cnt = {}
    for k in kocs:
        t = koc_reward_tier(int(k.get("engagement_24h", 0)), int(k.get("engagement_7d", 0)))
        tier_cnt[t["tier"]] = tier_cnt.get(t["tier"], 0) + 1
    return {"campaign": campaign, "koc_count": len(kocs), "viewership": view,
            "engagement": eng, "high_intent_comments": hi, "tiers": tier_cnt}


# ---------------------------------------------------------------------------
# 5. 多渠道 ROI 对比
# ---------------------------------------------------------------------------
# 内置渠道基准（DFS Y26 H1 真实标杆实测 CPL；可被 channels 覆盖）
CHANNEL_BENCHMARKS = {
    "xhs_boosting": {"label": "小红书 Boosting", "reference_cpl": 57.32},
    "wechat_oa": {"label": "微信 OA", "reference_cpl": 9.36},
    "private_domain": {"label": "私域 WeCom", "reference_cpl": None},
}


def channel_roi(channels: Optional[dict] = None) -> dict:
    """多渠道 ROI 对比：各渠道 CPL/CPC/Cost-per-WeCom/预算，并给出 vs 基准差异。

    channels（可选，覆盖/追加）：{name: {budget, inquiry, clicks, wecom, reference_cpl}}
    默认输出内置基准（DFS 实测：小红书 CPL 57.32 / 微信 OA CPL 9.36）+ 当前系统小红书成本
    （来自 cost_metrics 手动回填）。缺失输入显式标注 manual_pending。
    """
    manual = _load_manual()
    # 当前系统小红书成本（手动回填汇总）
    cur_cost = cost_metrics(period="month")
    builtin = {
        "xhs_boosting": {
            "budget": cur_cost.get("boosting_budget", 0) or 0,
            "inquiry": cur_cost.get("inquiry", 0) or 0,
            "clicks": cur_cost.get("clicks", 0) or 0,
            "wecom": cur_cost.get("wecom_add", 0) or 0,
        },
        "wechat_oa": {"budget": 0, "inquiry": 0, "clicks": 0, "wecom": 0},
        "private_domain": {"budget": 0, "inquiry": 0, "clicks": 0, "wecom": 0},
    }
    if channels:
        for name, cfg in channels.items():
            merged = builtin.setdefault(name, {"budget": 0, "inquiry": 0, "clicks": 0, "wecom": 0})
            for k in ("budget", "inquiry", "clicks", "wecom"):
                if k in cfg:
                    merged[k] = cfg[k]
            if "reference_cpl" in cfg:
                CHANNEL_BENCHMARKS.setdefault(name, {"label": name, "reference_cpl": None})
                CHANNEL_BENCHMARKS[name]["reference_cpl"] = cfg["reference_cpl"]

    out = {"channels": [], "generated_at": None}
    for name, cfg in builtin.items():
        bench = CHANNEL_BENCHMARKS.get(name, {"label": name, "reference_cpl": None})
        budget = float(cfg.get("budget", 0) or 0)
        inquiry = int(cfg.get("inquiry", 0) or 0)
        clicks = int(cfg.get("clicks", 0) or 0)
        wecom = int(cfg.get("wecom", 0) or 0)
        row = {
            "name": name,
            "label": bench.get("label", name),
            "budget": round(budget, 2),
            "inquiry": inquiry,
            "clicks": clicks,
            "wecom": wecom,
            "cpl": round(budget / inquiry, 2) if inquiry else None,
            "cpc": round(budget / clicks, 2) if clicks else None,
            "cost_per_wecom": round(budget / wecom, 2) if wecom else None,
            "reference_cpl": bench.get("reference_cpl"),
        }
        if row["cpl"] is not None and row["reference_cpl"]:
            row["vs_reference_pct"] = round((row["cpl"] - row["reference_cpl"]) / row["reference_cpl"] * 100, 1)
        else:
            row["vs_reference_pct"] = None
        out["channels"].append(row)
    return out
