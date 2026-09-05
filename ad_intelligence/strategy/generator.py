# -*- coding: utf-8 -*-
"""
投流策略生成框架
================
AI辅助生成投流策略，默认只给建议不执行。
所有策略必须经过Permission Gate和人工确认才能执行。

策略维度：
- 受众定向：年龄/性别/地域/兴趣/行为/自定义人群
- 预算分配：日预算/总预算/平台分配/计划分配
- 出价策略：CPC/CPM/oCPM/智能出价
- 素材策略：素材类型/文案方向/落地页
- 时段策略：投放时段/频次控制
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BiddingStrategy(str, Enum):
    """出价策略。"""
    CPC = "cpc"              # 按点击付费
    CPM = "cpm"              # 按千次曝光付费
    OCPM = "ocpm"            # 优化千次曝光
    CPA = "cpa"              # 按转化付费
    SMART = "smart"          # 智能出价


class CampaignObjective(str, Enum):
    """广告目标。"""
    AWARENESS = "awareness"      # 品牌曝光
    CONSIDERATION = "consideration"  # 种草/互动
    CONVERSION = "conversion"    # 转化/下单
    FOLLOW = "follow"            # 涨粉
    TRAFFIC = "traffic"          # 引流


@dataclass
class AudienceTarget:
    """受众定向。"""
    age_range: tuple = (18, 45)
    gender: str = "all"          # all/male/female
    regions: List[str] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    behaviors: List[str] = field(default_factory=list)
    custom_audience: Optional[str] = None  # 自定义人群包ID


@dataclass
class BudgetAllocation:
    """预算分配。"""
    total_budget: float = 0
    daily_budget: float = 0
    platform_allocation: Dict[str, float] = field(default_factory=dict)
    campaign_allocation: Dict[str, float] = field(default_factory=dict)


@dataclass
class AdStrategy:
    """投流策略（AI生成，默认只建议不执行）。"""
    strategy_id: str = ""
    platform: str = ""
    objective: CampaignObjective = CampaignObjective.CONVERSION
    audience: AudienceTarget = field(default_factory=AudienceTarget)
    budget: BudgetAllocation = field(default_factory=BudgetAllocation)
    bidding_strategy: BiddingStrategy = BiddingStrategy.OCPM
    bid_amount: float = 0
    schedule_hours: List[int] = field(default_factory=list)
    frequency_cap: int = 0
    creative_directions: List[str] = field(default_factory=list)
    expected_ctr: float = 0
    expected_cvr: float = 0
    expected_roas: float = 0
    confidence: float = 0
    requires_human_approval: bool = True
    status: str = "draft"         # draft/approved/executing/completed/rejected


class StrategyGenerator:
    """投流策略生成器（AI辅助，默认只给建议）。"""

    def __init__(self):
        self._strategies: List[AdStrategy] = []

    def generate_strategy(
        self,
        platform: str,
        objective: str,
        budget: float,
        target_audience: Optional[Dict] = None,
        historical_data: Optional[Dict] = None,
    ) -> AdStrategy:
        """生成投流策略建议（只读，不执行）。"""
        # 基于历史数据和平台特性生成策略
        strategy = AdStrategy(
            platform=platform,
            objective=CampaignObjective(objective) if objective in [e.value for e in CampaignObjective] else CampaignObjective.CONVERSION,
            budget=BudgetAllocation(total_budget=budget, daily_budget=budget / 30 if budget > 0 else 0),
        )

        # 平台特性适配
        platform_templates = {
            "xhs": {
                "default_objective": CampaignObjective.CONSIDERATION,
                "default_bidding": BiddingStrategy.OCPM,
                "peak_hours": [12, 13, 20, 21, 22],
                "creative_directions": ["种草笔记", "测评对比", "使用教程", "KOL合作"],
            },
            "douyin": {
                "default_objective": CampaignObjective.CONVERSION,
                "default_bidding": BiddingStrategy.OCPM,
                "peak_hours": [12, 18, 19, 20, 21, 22],
                "creative_directions": ["短视频种草", "直播切片", "剧情植入", "达人合作"],
            },
            "facebook": {
                "default_objective": CampaignObjective.CONVERSION,
                "default_bidding": BiddingStrategy.OCPM,
                "peak_hours": [9, 12, 19, 20, 21],
                "creative_directions": ["视频广告", "轮播图", "单图", "Stories"],
            },
            "x": {
                "default_objective": CampaignObjective.AWARENESS,
                "default_bidding": BiddingStrategy.CPC,
                "peak_hours": [9, 12, 15, 18],
                "creative_directions": ["推文", "视频", "卡片", "话题"],
            },
        }

        template = platform_templates.get(platform, {})
        if template:
            strategy.bidding_strategy = template.get("default_bidding", BiddingStrategy.OCPM)
            strategy.schedule_hours = template.get("peak_hours", [])
            strategy.creative_directions = template.get("creative_directions", [])

        # 历史数据优化
        if historical_data:
            avg_ctr = historical_data.get("avg_ctr", 0.02)
            avg_cvr = historical_data.get("avg_cvr", 0.01)
            strategy.expected_ctr = avg_ctr
            strategy.expected_cvr = avg_cvr
            strategy.expected_roas = historical_data.get("avg_roas", 1.5)
            strategy.confidence = min(0.9, 0.5 + len(historical_data) * 0.01)

        # 受众定向
        if target_audience:
            strategy.audience = AudienceTarget(
                age_range=tuple(target_audience.get("age_range", (18, 45))),
                gender=target_audience.get("gender", "all"),
                regions=target_audience.get("regions", []),
                interests=target_audience.get("interests", []),
            )

        strategy.requires_human_approval = True
        strategy.status = "draft"
        self._strategies.append(strategy)
        return strategy

    def compare_strategies(self, strategies: List[AdStrategy]) -> Dict[str, Any]:
        """对比多个策略（只读分析）。"""
        if not strategies:
            return {"error": "无策略可对比"}

        comparison = {
            "total_strategies": len(strategies),
            "platforms": list(set(s.platform for s in strategies)),
            "total_budget": sum(s.budget.total_budget for s in strategies),
            "avg_expected_roas": sum(s.expected_roas for s in strategies) / len(strategies),
            "max_confidence": max(s.confidence for s in strategies),
            "recommendation": None,
        }

        # 推荐ROAS最高且置信度足够的策略
        valid = [s for s in strategies if s.confidence >= 0.6]
        if valid:
            best = max(valid, key=lambda s: s.expected_roas)
            comparison["recommendation"] = {
                "platform": best.platform,
                "expected_roas": best.expected_roas,
                "confidence": best.confidence,
                "reason": "ROAS预期最高且置信度足够",
            }

        return comparison

    def list_strategies(self, status: Optional[str] = None) -> List[AdStrategy]:
        """列出策略（只读）。"""
        if status:
            return [s for s in self._strategies if s.status == status]
        return self._strategies
