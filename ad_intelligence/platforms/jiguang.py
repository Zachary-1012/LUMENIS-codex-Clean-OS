# -*- coding: utf-8 -*-
"""
小红书聚光广告数据只读采集
==========================
真实商业现实：
- API: 聚光平台API（需特批，配额严格）
- 无API权限时：浏览器只读采集广告后台
- 币种: CNY，预充值，最低充值5000元
- 数据粒度: 天级（API有限开放）
- 种草内容审核较严

本模块只做只读数据采集，不做任何写操作。
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class JiguangEndpoint(str, Enum):
    """聚光平台API端点（占位，实际需以官方文档为准）。"""
    REPORT_ACCOUNT = "/api/jg/report/account"        # 账户报表
    REPORT_PLAN = "/api/jg/report/plan"              # 计划报表
    REPORT_CREATIVE = "/api/jg/report/creative"      # 创意报表
    ACCOUNT_INFO = "/api/jg/account/info"            # 账户信息
    PLAN_LIST = "/api/jg/plan/list"                  # 计划列表
    BALANCE = "/api/jg/account/balance"              # 账户余额


@dataclass
class JiguangConfig:
    """聚光平台配置。"""
    access_token: str = ""
    advertiser_id: str = ""
    api_base: str = "https://ad.xiaohongshu.com/api"
    use_browser_fallback: bool = True
    agency_rebate_rate: float = 0.0


class JiguangCollector:
    """小红书聚光广告数据只读采集器。"""

    def __init__(self, config: Optional[JiguangConfig] = None):
        self.config = config or JiguangConfig()

    def _has_api_access(self) -> bool:
        return bool(self.config.access_token and self.config.advertiser_id)

    def health_check(self) -> Dict[str, Any]:
        return {
            "platform": "xhs",
            "ad_system": "jiguang",
            "api_access": self._has_api_access(),
            "browser_fallback": self.config.use_browser_fallback,
            "currency": "CNY",
            "min_deposit": 5000,
            "agency_rebate_rate": self.config.agency_rebate_rate,
            "status": "ready" if self._has_api_access() else "need_credentials",
            "note": "聚光API需特批，配额严格；无API时用浏览器只读采集",
        }

    def get_balance(self) -> Dict[str, Any]:
        if not self._has_api_access():
            return {"success": False, "error": "API未配置", "data": None}
        return {"success": True, "data": {"balance": None, "currency": "CNY", "note": "API调用待实现"}}

    def get_daily_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        if not self._has_api_access():
            return {"success": False, "error": "API未配置", "data": None}
        return {
            "success": True,
            "data": {
                "start_date": start_date,
                "end_date": end_date,
                "metrics": ["impressions", "clicks", "cost", "interactions", "follows"],
                "note": "小红书特色指标：互动量、涨粉量、种草价值",
            },
        }

    def calculate_actual_cost(self, nominal_cost: float) -> float:
        if self.config.agency_rebate_rate <= 0:
            return nominal_cost
        return nominal_cost * (1 - self.config.agency_rebate_rate)
