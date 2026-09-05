# -*- coding: utf-8 -*-
"""
X Ads（Twitter）广告数据只读采集
================================
真实商业现实：
- API: X Ads API（需开发者审核，配额严格）
- 无API权限时：浏览器只读采集X Ads Manager
- 币种: USD，信用卡后付费，无最低充值
- 数据粒度: 小时级
- 中国大陆需代理
- 政治广告需特批
- API配额严格（开发者审核）

本模块只做只读数据采集，不做任何写操作。
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class XAdsEndpoint(str, Enum):
    """X Ads API端点。"""
    ACCOUNTS = "/2/ads/accounts"
    CAMPAIGNS = "/2/ads/campaigns"
    AD_GROUPS = "/2/ads/ad_groups"
    ADS = "/2/ads/ads"
    ANALYTICS = "/2/stats/accounts/{account_id}"
    FUNDING_INSTRUMENTS = "/2/ads/funding_instruments"


@dataclass
class XAdsConfig:
    """X Ads配置。"""
    consumer_key: str = ""
    consumer_secret: str = ""
    access_token: str = ""
    access_token_secret: str = ""
    account_id: str = ""
    api_base: str = "https://api.x.com"
    use_browser_fallback: bool = True
    requires_proxy: bool = True
    proxy_url: str = ""


class XAdsCollector:
    """X Ads广告数据只读采集器。"""

    def __init__(self, config: Optional[XAdsConfig] = None):
        self.config = config or XAdsConfig()

    def _has_api_access(self) -> bool:
        return all([
            self.config.consumer_key,
            self.config.consumer_secret,
            self.config.access_token,
            self.config.access_token_secret,
            self.config.account_id,
        ])

    def _has_proxy(self) -> bool:
        import os
        return bool(
            self.config.proxy_url
            or os.environ.get("OPENAI_PROXY")
            or os.environ.get("HTTPS_PROXY")
        )

    def health_check(self) -> Dict[str, Any]:
        has_api = self._has_api_access()
        has_proxy = self._has_proxy()
        blockers = []
        if not has_api:
            blockers.append("API未配置（OAuth 1.0a 四元组 + account_id）")
        if not has_proxy:
            blockers.append("需要代理但未检测到代理配置")
        return {
            "platform": "x",
            "ad_system": "x_ads",
            "api_access": has_api,
            "proxy_available": has_proxy,
            "browser_fallback": self.config.use_browser_fallback,
            "currency": "USD",
            "min_deposit": 0,
            "status": "ready" if not blockers else "blocked",
            "blockers": blockers,
            "note": "X Ads API需开发者审核，配额严格；政治广告需特批",
        }

    def get_analytics(self, start_time: str, end_time: str) -> Dict[str, Any]:
        if not self._has_api_access():
            return {"success": False, "error": "API未配置", "data": None}
        if not self._has_proxy():
            return {"success": False, "error": "需要代理", "data": None}
        return {
            "success": True,
            "data": {
                "start_time": start_time,
                "end_time": end_time,
                "metrics": ["impressions", "clicks", "spend", "engagements", "follows", "conversions"],
                "note": "API调用待实现，需OAuth 1.0a签名+代理",
            },
        }

    def get_campaigns(self) -> Dict[str, Any]:
        if not self._has_api_access():
            return {"success": False, "error": "API未配置", "data": None}
        return {"success": True, "data": [], "note": "API调用待实现"}
