# -*- coding: utf-8 -*-
"""
广告投流基础数据结构
====================
定义广告平台、广告计划、广告指标、广告创意等基础数据类。
所有数据类为只读数据容器，不包含任何写操作。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any


@dataclass
class AdMetric:
    """广告指标（只读数据容器）。"""
    impressions: int = 0          # 曝光量
    clicks: int = 0               # 点击量
    ctr: float = 0.0              # 点击率 (%)
    cpc: float = 0.0              # 单次点击成本
    cpm: float = 0.0              # 千次曝光成本
    conversions: int = 0          # 转化量
    cvr: float = 0.0              # 转化率 (%)
    cost: float = 0.0             # 花费
    roas: float = 0.0             # 广告支出回报率
    revenue: float = 0.0          # 收入
    likes: int = 0                # 点赞
    comments: int = 0             # 评论
    shares: int = 0               # 分享
    follows: int = 0              # 关注
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "impressions": self.impressions,
            "clicks": self.clicks,
            "ctr": round(self.ctr, 4),
            "cpc": round(self.cpc, 4),
            "cpm": round(self.cpm, 4),
            "conversions": self.conversions,
            "cvr": round(self.cvr, 4),
            "cost": round(self.cost, 4),
            "roas": round(self.roas, 4),
            "revenue": round(self.revenue, 4),
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "follows": self.follows,
        }


@dataclass
class AdCreative:
    """广告创意（只读数据容器）。"""
    creative_id: str = ""
    title: str = ""
    description: str = ""
    image_url: str = ""
    video_url: str = ""
    landing_page: str = ""
    cta_text: str = ""
    format_type: str = ""          # image/video/carousel/story
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdCampaign:
    """广告计划（只读数据容器）。"""
    campaign_id: str = ""
    name: str = ""
    status: str = ""               # ACTIVE/PAUSED/ARCHIVED
    objective: str = ""            # 营销目标：曝光/点击/转化/互动
    budget_daily: float = 0.0
    budget_total: float = 0.0
    bid_strategy: str = ""         # CPC/CPM/oCPM/auto
    bid_amount: float = 0.0
    start_date: str = ""
    end_date: str = ""
    targeting: Dict[str, Any] = field(default_factory=dict)
    metrics: AdMetric = field(default_factory=AdMetric)
    creatives: List[AdCreative] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.status.upper() == "ACTIVE"


@dataclass
class AdPlatform:
    """广告平台（只读数据容器）。"""
    platform: str = ""             # facebook/x/douyin/xhs/bilibili
    display_name: str = ""
    ad_system: str = ""            # Meta Ads/X Ads/巨量引擎/聚光/花火
    currency: str = "CNY"
    timezone: str = "Asia/Shanghai"
    campaigns: List[AdCampaign] = field(default_factory=list)
    account_id: str = ""
    account_name: str = ""
    last_updated: str = ""

    def total_metrics(self) -> AdMetric:
        """汇总所有计划的指标。"""
        total = AdMetric()
        for c in self.campaigns:
            total.impressions += c.metrics.impressions
            total.clicks += c.metrics.clicks
            total.conversions += c.metrics.conversions
            total.cost += c.metrics.cost
            total.revenue += c.metrics.revenue
            total.likes += c.metrics.likes
            total.comments += c.metrics.comments
            total.shares += c.metrics.shares
        if total.impressions > 0:
            total.ctr = (total.clicks / total.impressions) * 100
        if total.clicks > 0:
            total.cpc = total.cost / total.clicks
        if total.impressions > 0:
            total.cpm = (total.cost / total.impressions) * 1000
        if total.clicks > 0:
            total.cvr = (total.conversions / total.clicks) * 100
        if total.cost > 0:
            total.roas = total.revenue / total.cost
        return total
