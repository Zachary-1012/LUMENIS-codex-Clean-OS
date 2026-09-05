# -*- coding: utf-8 -*-
"""
Meta Ads（Facebook/Instagram）广告数据只读采集
==============================================
真实商业现实：
- API: Meta Marketing API（需App审核，有速率限制）
- 无API权限时：浏览器只读采集Ads Manager
- 币种: USD（可切换多币种），信用卡后付费，无最低充值
- 数据粒度: 小时级
- 中国大陆需代理
- 政治广告需身份验证
- 受限行业多（成人/烟草/武器/加密货币受限）

本模块只做只读数据采集，不做任何写操作。
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MetaAdsEndpoint(str, Enum):
    """Meta Marketing API端点。"""
    AD_ACCOUNT_INSIGHTS = "/v18.0/{ad_account_id}/insights"
    AD_ACCOUNT = "/v18.0/{ad_account_id}"
    CAMPAIGNS = "/v18.0/{ad_account_id}/campaigns"
    ADSETS = "/v18.0/{ad_account_id}/adsets"
    ADS = "/v18.0/{ad_account_id}/ads"
    CREATIVES = "/v18.0/{ad_account_id}/adcreatives"


@dataclass
class MetaAdsConfig:
    """Meta Ads配置。"""
    access_token: str = ""              # User Access Token（从.env读取）
    ad_account_id: str = ""             # 广告账户ID（act_xxxxxx）
    app_id: str = ""                    # Facebook App ID
    app_secret: str = ""                # App Secret
    api_base: str = "https://graph.facebook.com"
    use_browser_fallback: bool = True
    requires_proxy: bool = True         # 中国大陆必须代理
    proxy_url: str = ""                 # 代理地址（从.env读取）


class MetaAdsCollector:
    """Meta Ads广告数据只读采集器。"""

    def __init__(self, config: Optional[MetaAdsConfig] = None):
        self.config = config or MetaAdsConfig()

    def _has_api_access(self) -> bool:
        return bool(self.config.access_token and self.config.ad_account_id)

    def _has_proxy(self) -> bool:
        import os
        return bool(
            self.config.proxy_url
            or os.environ.get("OPENAI_PROXY")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("HTTP_PROXY")
        )

    def health_check(self) -> Dict[str, Any]:
        has_api = self._has_api_access()
        has_proxy = self._has_proxy()
        blockers = []
        if not has_api:
            blockers.append("API未配置（access_token/ad_account_id）")
        if not has_proxy:
            blockers.append("需要代理但未检测到代理配置")
        return {
            "platform": "facebook/instagram",
            "ad_system": "meta_ads",
            "api_access": has_api,
            "proxy_available": has_proxy,
            "browser_fallback": self.config.use_browser_fallback,
            "currency": "USD",
            "min_deposit": 0,
            "status": "ready" if not blockers else "blocked",
            "blockers": blockers,
            "note": "Meta Ads需企业BM+公共主页；政治广告需身份验证",
        }

    def get_account_insights(self, date_preset: str = "last_7d") -> Dict[str, Any]:
        """获取账户洞察数据（只读）。"""
        if not self._has_api_access():
            return {"success": False, "error": "API未配置", "data": None}
        if not self._has_proxy():
            return {"success": False, "error": "需要代理", "data": None}
        return {
            "success": True,
            "data": {
                "date_preset": date_preset,
                "metrics": ["impressions", "clicks", "spend", "cpc", "cpm", "ctr", "conversions", "roas"],
                "note": "API调用待实现，需access_token+代理",
            },
        }

    def get_campaigns(self) -> Dict[str, Any]:
        if not self._has_api_access():
            return {"success": False, "error": "API未配置", "data": None}
        return {"success": True, "data": [], "note": "API调用待实现"}
