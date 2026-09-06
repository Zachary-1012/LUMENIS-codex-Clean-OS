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

【BLOCKED 条件】
- 缺少 META_ADS_ACCESS_TOKEN 或 META_ADS_ACCOUNT_ID
- 中国大陆访问需代理（OPENAI_PROXY / HTTPS_PROXY / HTTP_PROXY）
- 无凭证时返回 status="blocked"，禁止返回空列表冒充成功

【接入条件】
1. Meta Business Manager 企业账户 + 公共主页
2. Facebook App（需通过 App Review 获取 ads_read 权限）
3. User Access Token（长期有效，需 offline_access）
4. Ad Account ID（act_xxxxxx 格式）
5. 中国大陆需 HTTPS 代理访问 graph.facebook.com
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
import os

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
    api_version: str = "v18.0"
    use_browser_fallback: bool = True
    requires_proxy: bool = True         # 中国大陆必须代理
    proxy_url: str = ""                 # 代理地址（从.env读取）


def _blocked_response(reason: str, required: List[str], note: str = "") -> Dict[str, Any]:
    """统一的 BLOCKED 响应格式（禁止伪造成功/空数据）。"""
    return {
        "success": False,
        "status": "blocked",
        "reason": reason,
        "required_credentials": required,
        "data": None,
        "note": note,
    }


class MetaAdsCollector:
    """Meta Ads广告数据只读采集器。"""

    # Meta Marketing API 标准指标字段
    INSIGHT_FIELDS = (
        "impressions,clicks,spend,cpc,cpm,ctr,conversions,"
        "cost_per_conversion,roas,reach,frequency,video_play"
    )
    CAMPAIGN_FIELDS = "id,name,status,objective,daily_budget,lifetime_budget,bid_strategy"

    def __init__(self, config: Optional[MetaAdsConfig] = None):
        self.config = config or MetaAdsConfig()

    def _has_api_access(self) -> bool:
        return bool(self.config.access_token and self.config.ad_account_id)

    def _has_proxy(self) -> bool:
        return bool(
            self.config.proxy_url
            or os.environ.get("OPENAI_PROXY")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("HTTP_PROXY")
        )

    def _get_proxies(self) -> Optional[Dict[str, str]]:
        """获取 requests 代理配置。"""
        proxy = (self.config.proxy_url
                 or os.environ.get("OPENAI_PROXY")
                 or os.environ.get("HTTPS_PROXY")
                 or os.environ.get("HTTP_PROXY"))
        if proxy:
            return {"http": proxy, "https": proxy}
        return None

    def _build_url(self, endpoint_template: str) -> str:
        """构建完整API URL。"""
        path = endpoint_template.format(ad_account_id=self.config.ad_account_id)
        return f"{self.config.api_base}{path}"

    def _api_request(self, endpoint: str, params: Optional[Dict] = None,
                      method: str = "GET") -> Dict[str, Any]:
        """执行 Meta Marketing API 请求（真实调用骨架）。

        前置条件检查：
        - access_token / ad_account_id 必须存在
        - 中国大陆需代理（graph.facebook.com 被墙）

        无凭证时返回 BLOCKED，不发起请求，不伪造数据。
        """
        if not self._has_api_access():
            return _blocked_response(
                reason="missing credentials: access_token or ad_account_id",
                required=["META_ADS_ACCESS_TOKEN", "META_ADS_ACCOUNT_ID (act_xxxxxx)"],
                note="Meta Ads需企业BM+公共主页+App Review(ads_read权限)；无凭证禁止返回空数据",
            )
        if self.config.requires_proxy and not self._has_proxy():
            return _blocked_response(
                reason="proxy required for accessing graph.facebook.com from mainland China",
                required=["HTTPS_PROXY 或 OPENAI_PROXY 环境变量"],
                note="中国大陆直连 graph.facebook.com 不可达；需配置代理",
            )

        try:
            import requests
            params = params or {}
            params["access_token"] = self.config.access_token

            url = self._build_url(endpoint)
            proxies = self._get_proxies()

            if method.upper() == "GET":
                resp = requests.get(url, params=params, proxies=proxies, timeout=30)
            else:
                resp = requests.post(url, data=params, proxies=proxies, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                return {"success": True, "status": "ok", "data": data, "mode": "api"}
            # Meta API 错误处理
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", f"HTTP {resp.status_code}")
                err_type = err_data.get("error", {}).get("type", "")
                err_code = err_data.get("error", {}).get("code", 0)
            except Exception:
                err_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                err_type = ""
                err_code = 0
            return {
                "success": False,
                "status": "api_error",
                "error": err_msg,
                "error_type": err_type,
                "error_code": err_code,
                "http_status": resp.status_code,
                "data": None,
            }
        except ImportError:
            return {"success": False, "status": "dependency_error", "error": "requests 未安装", "data": None}
        except Exception as e:
            logger.error(f"Meta Ads API请求失败: {e}")
            return {"success": False, "status": "request_error", "error": str(e), "data": None}

    def health_check(self) -> Dict[str, Any]:
        has_api = self._has_api_access()
        has_proxy = self._has_proxy()
        blockers = []
        if not has_api:
            blockers.append("API未配置（access_token/ad_account_id）")
        if self.config.requires_proxy and not has_proxy:
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
            "api_version": self.config.api_version,
            "note": "Meta Ads需企业BM+公共主页；政治广告需身份验证；App Review需ads_read权限",
        }

    def get_account_insights(self, date_preset: str = "last_7d",
                              level: str = "account") -> Dict[str, Any]:
        """获取账户洞察数据（只读，真实API调用）。

        Args:
            date_preset: today/last_7d/last_30d/last_quarter/maximum
            level: account/campaign/adset/ad
        """
        params = {
            "fields": self.INSIGHT_FIELDS,
            "date_preset": date_preset,
            "level": level,
            "time_increment": 1,
        }
        return self._api_request(MetaAdsEndpoint.AD_ACCOUNT_INSIGHTS.value, params=params)

    def get_campaigns(self, effective_status: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取广告计划列表（只读，真实API调用）。

        无凭证时返回 BLOCKED，禁止返回空列表冒充成功。
        """
        params = {"fields": self.CAMPAIGN_FIELDS, "limit": 100}
        if effective_status:
            params["effective_status"] = json.dumps(effective_status)
        return self._api_request(MetaAdsEndpoint.CAMPAIGNS.value, params=params)

    def get_adsets(self) -> Dict[str, Any]:
        """获取广告组列表（只读）。"""
        params = {"fields": "id,name,status,campaign_id,daily_budget,bid_amount,optimization_goal", "limit": 100}
        return self._api_request(MetaAdsEndpoint.ADSETS.value, params=params)

    def get_ads(self) -> Dict[str, Any]:
        """获取广告列表（只读）。"""
        params = {"fields": "id,name,status,adset_id,creative,effective_status", "limit": 100}
        return self._api_request(MetaAdsEndpoint.ADS.value, params=params)

    def parse_insights_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析 Meta Insights API 响应为标准化指标列表。

        Meta API 返回分页结构: {data: [...], paging: {...}}
        每条记录包含 date/impressions/clicks/spend 等字段。
        """
        records = data.get("data", []) if isinstance(data, dict) else []
        parsed = []
        for rec in records:
            parsed.append({
                "date": rec.get("date_start", ""),
                "impressions": int(rec.get("impressions", 0)),
                "clicks": int(rec.get("clicks", 0)),
                "spend": float(rec.get("spend", 0)),
                "cpc": float(rec.get("cpc", 0)),
                "cpm": float(rec.get("cpm", 0)),
                "ctr": float(rec.get("ctr", 0)),
                "conversions": int(rec.get("conversions", 0)),
                "reach": int(rec.get("reach", 0)),
                "frequency": float(rec.get("frequency", 0)),
            })
        return parsed


# 延迟导入 json（用于 parse 方法）
import json  # noqa: E402
