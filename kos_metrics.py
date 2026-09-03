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
