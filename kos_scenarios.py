# -*- coding: utf-8 -*-
"""
序境-Core · IC-047 免税 KOS 场景标注（P1 落地）
================================================
契约依据：Cycle KK（IC-047，对齐海南中免第一验收主体）
目标：为"免税/海南中免"类品牌场景提供 KOS 候选 + 场景标签（免税承接/私域运营/高净值VIC/年轻入门），
      并输出运营建议（种草-转化-复购三段闭环视角）。

红线遵守：
- 复用 kos_engine 既有能力（brand_profiles/brand_collection_stats/_brand_source_filter），不重复造轮子
- 不写 kos_profiles 主表（与广州主链隔离，不污染生产 Truth）
- 不做主体归属硬判定（归属走 kos_engine.ownership_for / 主体归属 Gate），本模块仅作场景运营视角
- 市场数据为行业口径（贝恩/公开），仅作策略参考，不作生产指标输入

场景标签（Cycle KK 认知）：
- tax_free  免税承接：离岛免税购物者是高价值承接样本
- vip       高净值 VIC：私人导购/限量预定/专属服务（贡献过半利润）
- young     年轻入门：千元级品类/免税即时零售降低门槛
- private   私域运营：会员数据中枢/复购（Gucci 私域复购+28% 参考）
"""
import os
from typing import Any, Dict, List, Optional

import kos_engine


def _brand_keywords(brand: str) -> List[str]:
    """复用品牌采集词（含隔离标记）。"""
    try:
        from subject_rules import collect_keywords_for
        return [k for k in collect_keywords_for(brand) if k]
    except Exception:
        return []


# 海南中免默认采集词（第一验收主体；来源标注为手动登记，可随采集配置更新）
HN_CDF_DEFAULT_KEYWORDS = ["海南中免", "中免集团", "cdf", "中免海南", "三亚国际免税城", "海口免税", "离岛免税", "海南免税"]


def scenario_tags(brand: str) -> List[str]:
    """按品牌场景返回标签（增量，规则驱动；未命中返回空）。"""
    tags: List[str] = []
    b = brand.lower()
    # 免税场景：品牌名/采集词命中免税语义
    if any(k in brand for k in ["中免", "免税", "cdf"]) or any(k in brand.lower() for k in ["cdf", "duty"]):
        tags.append("tax_free")
        tags.append("vip")       # 免税高净值承接
        tags.append("young")     # 免税即时零售降低年轻门槛
        tags.append("private")   # 会员/私域复购
    elif "taikoo" in b or "太古汇" in brand:
        tags.append("private")   # 商业体私域承接
    return list(dict.fromkeys(tags))


def recommend(brand: str = "海南中免", limit: int = 20,
              filter_negative: bool = True) -> Dict[str, Any]:
    """
    免税/品牌场景 KOS 运营推荐（只读聚合，不写主表）。
    返回：品牌采集状态 + 场景标签 + KOS 候选（复用 brand_profiles 实时聚合）。
    """
    result: Dict[str, Any] = {
        "brand": brand,
        "tags": scenario_tags(brand),
        "keywords": _brand_keywords(brand) or HN_CDF_DEFAULT_KEYWORDS,
        "note_source": "brand_profiles 实时聚合（不写主表，与广州主链隔离）",
        # Keep the response contract stable without turning a missing/unready
        # collection schema into a fabricated zero-count result.
        "collection_stats": {
            "brand": brand,
            "status": "unavailable",
            "note_count": None,
            "author_count": None,
            "last_captured_at": None,
        },
    }
    try:
        stats = kos_engine.brand_collection_stats(brand)
        note_count = stats.get("note_count")
        stats["status"] = (
            "unavailable" if note_count is None
            else "available" if note_count > 0
            else "not_collected"
        )
        result["collection_stats"] = stats
        if note_count is None:
            result["message"] = "采集统计未提供笔记计数，无法确认是否已有采集笔记"
            result["profiles"] = []
            return result
        if note_count == 0:
            result["note_count"] = 0
            result["message"] = "当前品牌无已采集笔记（需真实采集；请勿用假数据填充）"
            result["profiles"] = []
            return result
        profiles = kos_engine.brand_profiles(brand, limit=limit)
        if filter_negative:
            profiles = [p for p in profiles if not p.get("risk")]
        # 场景运营视角增强（不改变 kos_tier 计算）
        for p in profiles:
            tier = p.get("kos_tier", "C")
            p["scenario_advice"] = _scenario_advice(tier, result["tags"])
        result["profiles"] = profiles
        result["note_count"] = stats.get("note_count", 0)
        result["message"] = "OK（只读聚合）"
        return result
    except Exception as e:
        if result["collection_stats"].get("status") == "unavailable":
            result["message"] = f"采集状态暂不可用，无法确认是否已有采集笔记：{e}"
        else:
            result["message"] = f"ERR: {e}"
        result["profiles"] = []
        return result


def _scenario_advice(tier: str, tags: List[str]) -> str:
    """按分层+场景给运营建议（种草-转化-复购三段闭环视角，Cycle KK）。"""
    t = set(tags)
    if tier in ("S", "A"):
        base = "高价值承接：优先邀约深度合作（体验/联动/长期KOS）"
        if "vip" in t:
            base += "；匹配 VIC 专属权益与限量款优先"
        if "private" in t:
            base += "；沉淀为私域会员数据中枢"
    elif tier == "B":
        base = "成长型：内容共创+活动参与，培育为腰部KOS"
        if "young" in t:
            base += "；面向年轻入门客群降低门槛"
    else:
        base = "观察/培育：监测内容质量与互动信号，暂不入核心合作"
    if "tax_free" in t:
        base += "｜免税场景建议走'种草-到店-复购'闭环"
    return base


def overview(brand: str = "海南中免") -> Dict[str, Any]:
    """场景总览（供运营面板/报告使用）。"""
    return {
        "brand": brand,
        "tags": scenario_tags(brand),
        "note": "IC-047 免税 KOS 场景标注（增量、只读、复用 kos_engine）",
        "recommend": recommend(brand, limit=20),
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="序境 IC-047 免税 KOS 场景标注")
    ap.add_argument("--brand", default="海南中免", help="品牌名")
    ap.add_argument("--tags", action="store_true", help="仅查看场景标签")
    a = ap.parse_args()
    if a.tags:
        print("tags:", scenario_tags(a.brand))
    else:
        import json
        print(json.dumps(recommend(a.brand), ensure_ascii=False, indent=2))
