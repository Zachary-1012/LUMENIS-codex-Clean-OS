# -*- coding: utf-8 -*-
"""
巨量引擎（抖音）广告数据只读采集
================================
真实商业现实：
- API: 巨量引擎 Marketing API（需企业资质审核，有QPS限制）
- 无API权限时：浏览器只读采集广告后台
- 币种: CNY，预充值，最低充值10000元
- 数据粒度: 小时级
- 代理商体系成熟，返点3%-15%

本模块只做只读数据采集，不做任何写操作（创建计划/修改出价/暂停等）。
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OceanEngineEndpoint(str, Enum):
    """巨量引擎API端点。"""
    REPORT_ADVERTISER = "/2/report/advertiser/get/"          # 广告主报表
    REPORT_CAMPAIGN = "/2/report/campaign/get/"              # 广告组报表
    REPORT_CREATIVE = "/2/report/creative/get/"              # 创意报表
    ADVERTISER_INFO = "/2/advertiser/info/"                  # 广告主信息
    CAMPAIGN_LIST = "/2/campaign/get/"                       # 广告组列表
    BALANCE = "/2/advertiser/balance/"                       # 账户余额


@dataclass
class OceanEngineConfig:
    """巨量引擎配置。"""
    access_token: str = ""                # API access_token（从.env读取，不写源码）
    advertiser_id: str = ""               # 广告主ID
    api_base: str = "https://api.oceanengine.com/open_api"
    use_browser_fallback: bool = True     # 无API时是否用浏览器只读采集
    agency_rebate_rate: float = 0.0       # 代理商返点率（0-1），影响实际成本


class OceanEngineCollector:
    """巨量引擎广告数据只读采集器。"""

    def __init__(self, config: Optional[OceanEngineConfig] = None):
        self.config = config or OceanEngineConfig()
        self._session = None

    def _has_api_access(self) -> bool:
        """检查是否有API访问权限。"""
        return bool(self.config.access_token and self.config.advertiser_id)

    def health_check(self) -> Dict[str, Any]:
        """健康检查（只读，不调用计费接口）。"""
        return {
            "platform": "douyin",
            "ad_system": "ocean_engine",
            "api_access": self._has_api_access(),
            "browser_fallback": self.config.use_browser_fallback,
            "currency": "CNY",
            "min_deposit": 10000,
            "agency_rebate_rate": self.config.agency_rebate_rate,
            "status": "ready" if self._has_api_access() else "need_credentials",
        }

    def get_balance(self) -> Dict[str, Any]:
        """获取账户余额（只读）。"""
        if not self._has_api_access():
            return {
                "success": False,
                "error": "API未配置（access_token/advertiser_id），需浏览器采集或配置API",
                "data": None,
            }
        # API调用占位（实际实现需签名）
        return {
            "success": True,
            "data": {
                "balance": None,
                "currency": "CNY",
                "note": "API调用待实现，需access_token签名",
            },
        }

    def get_daily_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """获取广告主日报表（只读）。"""
        if not self._has_api_access():
            return {
                "success": False,
                "error": "API未配置",
                "data": None,
            }
        return {
            "success": True,
            "data": {
                "start_date": start_date,
                "end_date": end_date,
                "metrics": ["impressions", "clicks", "cost", "conversions", "revenue"],
                "note": "API调用待实现",
            },
        }

    def get_campaign_list(self) -> Dict[str, Any]:
        """获取广告组列表（只读）。"""
        if not self._has_api_access():
            return {
                "success": False,
                "error": "API未配置",
                "data": None,
            }
        return {"success": True, "data": [], "note": "API调用待实现"}

    def calculate_actual_cost(self, nominal_cost: float) -> float:
        """计算实际成本（扣除代理商返点）。

        真实商业现实：代理商返点3%-15%，实际成本 = 消耗 × (1 - 返点率)
        """
        if self.config.agency_rebate_rate <= 0:
            return nominal_cost
        return nominal_cost * (1 - self.config.agency_rebate_rate)
