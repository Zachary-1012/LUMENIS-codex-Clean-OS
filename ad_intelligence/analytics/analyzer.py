# -*- coding: utf-8 -*-
"""
广告数据分析框架
================
ROAS分析、漏斗分析、竞品分析、素材分析。
所有分析只读，不修改原始数据。
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FunnelStage(str, Enum):
    """漏斗阶段。"""
    IMPRESSION = "impression"    # 曝光
    CLICK = "click"              # 点击
    LANDING = "landing"          # 落地页访问
    ENGAGEMENT = "engagement"    # 互动
    CONVERSION = "conversion"    # 转化
    PURCHASE = "purchase"        # 购买


@dataclass
class ROASAnalysis:
    """ROAS分析结果。"""
    platform: str
    period: str
    total_spend: float
    total_revenue: float
    roas: float
    target_roas: float
    status: str               # good/warning/bad
    breakdown_by_campaign: Dict[str, float]
    trend: List[float]
    recommendation: str


@dataclass
class FunnelAnalysis:
    """漏斗分析结果。"""
    platform: str
    stages: Dict[str, int]
    rates: Dict[str, float]   # 各阶段转化率
    drop_off_points: List[str]
    bottleneck: str
    recommendation: str


@dataclass
class CreativeAnalysis:
    """素材分析结果。"""
    platform: str
    total_creatives: int
    best_performing: List[Dict]
    worst_performing: List[Dict]
    avg_ctr_by_type: Dict[str, float]
    avg_cvr_by_type: Dict[str, float]
    recommendation: str


class AdAnalytics:
    """广告数据分析器（只读）。"""

    def __init__(self):
        pass

    def analyze_roas(
        self,
        platform: str,
        spend_data: List[Dict],
        revenue_data: List[Dict],
        target_roas: float = 2.0,
    ) -> ROASAnalysis:
        """ROAS分析（只读）。"""
        total_spend = sum(d.get("spend", 0) for d in spend_data)
        total_revenue = sum(d.get("revenue", 0) for d in revenue_data)
        roas = total_revenue / total_spend if total_spend > 0 else 0

        if roas >= target_roas:
            status = "good"
        elif roas >= target_roas * 0.7:
            status = "warning"
        else:
            status = "bad"

        # 按计划分解
        breakdown = {}
        for d in spend_data:
            campaign = d.get("campaign", "unknown")
            spend = d.get("spend", 0)
            revenue = d.get("revenue", 0)
            if spend > 0:
                breakdown[campaign] = revenue / spend

        # 趋势（最近7天）
        trend = []
        for i in range(min(7, len(spend_data))):
            s = spend_data[i].get("spend", 0)
            r = spend_data[i].get("revenue", 0)
            trend.append(r / s if s > 0 else 0)

        recommendation = self._roas_recommendation(status, roas, target_roas)

        return ROASAnalysis(
            platform=platform,
            period="last_7d",
            total_spend=total_spend,
            total_revenue=total_revenue,
            roas=roas,
            target_roas=target_roas,
            status=status,
            breakdown_by_campaign=breakdown,
            trend=trend,
            recommendation=recommendation,
        )

    def analyze_funnel(
        self,
        platform: str,
        funnel_data: Dict[str, int],
    ) -> FunnelAnalysis:
        """漏斗分析（只读）。"""
        stages = {
            "impression": funnel_data.get("impressions", 0),
            "click": funnel_data.get("clicks", 0),
            "landing": funnel_data.get("landings", 0),
            "engagement": funnel_data.get("engagements", 0),
            "conversion": funnel_data.get("conversions", 0),
        }

        # 计算各阶段转化率
        rates = {}
        prev_stage = None
        prev_count = 0
        for stage, count in stages.items():
            if prev_stage and prev_count > 0:
                rates[f"{prev_stage}_to_{stage}"] = count / prev_count * 100
            prev_stage = stage
            prev_count = count

        # 找出流失最严重的点
        drop_off = []
        for rate_name, rate in rates.items():
            if rate < 50:
                drop_off.append(rate_name)

        bottleneck = min(rates, key=rates.get) if rates else "unknown"

        recommendation = self._funnel_recommendation(bottleneck, rates)

        return FunnelAnalysis(
            platform=platform,
            stages=stages,
            rates=rates,
            drop_off_points=drop_off,
            bottleneck=bottleneck,
            recommendation=recommendation,
        )

    def analyze_creatives(
        self,
        platform: str,
        creative_data: List[Dict],
    ) -> CreativeAnalysis:
        """素材分析（只读）。"""
        if not creative_data:
            return CreativeAnalysis(
                platform=platform,
                total_creatives=0,
                best_performing=[],
                worst_performing=[],
                avg_ctr_by_type={},
                avg_cvr_by_type={},
                recommendation="无素材数据",
            )

        # 按CTR排序
        sorted_by_ctr = sorted(creative_data, key=lambda x: x.get("ctr", 0), reverse=True)
        best = sorted_by_ctr[:3]
        worst = sorted_by_ctr[-3:] if len(sorted_by_ctr) >= 3 else sorted_by_ctr

        # 按类型统计
        ctr_by_type = {}
        cvr_by_type = {}
        for c in creative_data:
            ctype = c.get("type", "unknown")
            ctr_by_type.setdefault(ctype, []).append(c.get("ctr", 0))
            cvr_by_type.setdefault(ctype, []).append(c.get("cvr", 0))

        avg_ctr = {k: sum(v) / len(v) for k, v in ctr_by_type.items() if v}
        avg_cvr = {k: sum(v) / len(v) for k, v in cvr_by_type.items() if v}

        best_type = max(avg_ctr, key=avg_ctr.get) if avg_ctr else "unknown"
        recommendation = f"建议增加{best_type}类型素材，当前CTR最高"

        return CreativeAnalysis(
            platform=platform,
            total_creatives=len(creative_data),
            best_performing=best,
            worst_performing=worst,
            avg_ctr_by_type=avg_ctr,
            avg_cvr_by_type=avg_cvr,
            recommendation=recommendation,
        )

    def _roas_recommendation(self, status: str, roas: float, target: float) -> str:
        if status == "good":
            return f"ROAS {roas:.2f} 达标（目标{target}），可考虑增加预算"
        elif status == "warning":
            return f"ROAS {roas:.2f} 接近目标（{target}），建议优化素材和定向"
        else:
            return f"ROAS {roas:.2f} 未达标（目标{target}），建议暂停低效计划，优化落地页"

    def _funnel_recommendation(self, bottleneck: str, rates: Dict[str, float]) -> str:
        if "click_to_landing" in bottleneck:
            return "点击到落地页流失严重，检查落地页加载速度和相关性"
        elif "landing_to_engagement" in bottleneck:
            return "落地页到互动流失严重，优化内容和CTA按钮"
        elif "engagement_to_conversion" in bottleneck:
            return "互动到转化流失严重，优化转化路径和优惠力度"
        else:
            return "曝光到点击流失严重，优化素材和定向"
