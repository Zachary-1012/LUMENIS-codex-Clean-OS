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
import math

logger = logging.getLogger(__name__)


def _observed_number(value: Any) -> Optional[float]:
    """返回有效有限数值，保留已观测的零。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _observed_count(value: Any) -> Optional[int]:
    """返回非负的已观测整数计数。"""
    number = _observed_number(value)
    if number is None or number < 0 or not number.is_integer():
        return None
    return int(number)


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
    total_spend: Optional[float]
    total_revenue: Optional[float]
    roas: Optional[float]
    target_roas: float
    status: str               # good/warning/bad/partial/unavailable
    breakdown_by_campaign: Dict[str, float]
    trend: List[Optional[float]]
    recommendation: str


@dataclass
class FunnelAnalysis:
    """漏斗分析结果。"""
    platform: str
    stages: Dict[str, Optional[int]]
    rates: Dict[str, float]   # 各阶段转化率
    drop_off_points: List[str]
    bottleneck: str
    recommendation: str
    status: str = "unknown"  # complete/partial/unavailable


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
        """ROAS分析（只读）。缺少的指标不按零处理。"""
        observed_spend = []
        for item in spend_data:
            value = _observed_number(item.get("spend"))
            if value is not None and value >= 0:
                observed_spend.append(value)

        observed_revenue = []
        for item in revenue_data:
            value = _observed_number(item.get("revenue"))
            if value is not None:
                observed_revenue.append(value)

        spend_complete = bool(spend_data) and len(observed_spend) == len(spend_data)
        revenue_complete = (
            bool(revenue_data)
            and len(observed_revenue) == len(revenue_data)
        )
        total_spend = sum(observed_spend) if observed_spend else None
        total_revenue = sum(observed_revenue) if observed_revenue else None
        inputs_complete = spend_complete and revenue_complete
        has_observation = bool(observed_spend or observed_revenue)

        roas = None
        if not has_observation:
            status = "unavailable"
            recommendation = "未提供有效花费或收入数据，无法计算ROAS"
        elif not inputs_complete:
            status = "partial"
            recommendation = "花费或收入数据不完整，无法判断ROAS"
        elif total_spend is None or total_spend <= 0:
            status = "unavailable"
            recommendation = "已观测花费为0，无法计算ROAS"
        else:
            roas = total_revenue / total_spend
            if roas >= target_roas:
                status = "good"
            elif roas >= target_roas * 0.7:
                status = "warning"
            else:
                status = "bad"
            recommendation = self._roas_recommendation(status, roas, target_roas)

        # 按计划汇总仅使用花费、收入均已观测且分母有效的记录。
        breakdown = {}
        for item in spend_data:
            spend = _observed_number(item.get("spend"))
            revenue = _observed_number(item.get("revenue"))
            if spend is not None and spend > 0 and revenue is not None:
                campaign = item.get("campaign", "unknown")
                breakdown[campaign] = revenue / spend

        # 保留输入时间槽；无法计算的比率标记为不可用。
        trend = []
        for item in spend_data[:7]:
            spend = _observed_number(item.get("spend"))
            revenue = _observed_number(item.get("revenue"))
            if spend is not None and spend > 0 and revenue is not None:
                trend.append(revenue / spend)
            else:
                trend.append(None)

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
        """漏斗分析（只读）。缺失阶段保持未知，不按零处理。"""
        stage_inputs = {
            "impression": "impressions",
            "click": "clicks",
            "landing": "landings",
            "engagement": "engagements",
            "conversion": "conversions",
        }
        stages = {
            stage: _observed_count(funnel_data.get(input_name))
            for stage, input_name in stage_inputs.items()
        }

        observed_count = sum(count is not None for count in stages.values())
        if observed_count == 0:
            status = "unavailable"
        elif observed_count < len(stages):
            status = "partial"
        else:
            status = "complete"

        # 仅计算前后阶段均有观测、且前一阶段非零的转化率。
        rates = {}
        previous_stage = None
        previous_count = None
        for stage, count in stages.items():
            if (
                previous_stage
                and previous_count is not None
                and previous_count > 0
                and count is not None
            ):
                rates[f"{previous_stage}_to_{stage}"] = count / previous_count * 100
            previous_stage = stage
            previous_count = count

        drop_off = [rate_name for rate_name, rate in rates.items() if rate < 50]
        bottleneck = min(rates, key=rates.get) if rates else "unknown"

        if status == "unavailable":
            recommendation = "未提供漏斗阶段数据，无法分析"
        elif status == "partial":
            recommendation = "漏斗阶段数据不完整，无法给出优化建议"
        elif not rates:
            recommendation = "漏斗阶段数据完整，但没有可计算的转化率"
        else:
            recommendation = self._funnel_recommendation(bottleneck, rates)

        return FunnelAnalysis(
            platform=platform,
            stages=stages,
            rates=rates,
            drop_off_points=drop_off,
            bottleneck=bottleneck,
            recommendation=recommendation,
            status=status,
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

        def observed_rate(creative: Dict, field: str) -> Optional[float]:
            value = creative.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            rate = float(value)
            return rate if math.isfinite(rate) and rate >= 0 else None

        # Public competitor creatives commonly have no performance metrics.
        # Only an actually observed CTR can participate in a performance rank.
        measured = [c for c in creative_data if observed_rate(c, "ctr") is not None]
        sorted_by_ctr = sorted(
            measured, key=lambda c: observed_rate(c, "ctr"), reverse=True
        )
        best = sorted_by_ctr[:3]
        worst = sorted_by_ctr[-3:] if len(sorted_by_ctr) >= 3 else sorted_by_ctr

        # 按类型统计
        ctr_by_type = {}
        cvr_by_type = {}
        for c in creative_data:
            ctype = c.get("type", "unknown")
            ctr = observed_rate(c, "ctr")
            cvr = observed_rate(c, "cvr")
            if ctr is not None:
                ctr_by_type.setdefault(ctype, []).append(ctr)
            if cvr is not None:
                cvr_by_type.setdefault(ctype, []).append(cvr)

        avg_ctr = {k: sum(v) / len(v) for k, v in ctr_by_type.items() if v}
        avg_cvr = {k: sum(v) / len(v) for k, v in cvr_by_type.items() if v}

        if avg_ctr:
            best_type = max(avg_ctr, key=avg_ctr.get)
            recommendation = (
                f"已观测素材中{best_type}类型CTR最高；需结合样本量和真实业务结果评估"
            )
        else:
            recommendation = "未提供真实CTR，无法判断素材表现"

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
