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

【BLOCKED 条件】
- 缺少 OAuth 1.0a 四元组（consumer_key/consumer_secret/access_token/access_token_secret）
- 缺少 account_id
- 中国大陆需代理
- 无凭证时返回 status="blocked"，禁止返回空列表冒充成功

【接入条件】
1. X Developer Portal 账户（需开发者审核）
2. OAuth 1.0a 应用（需 Read/Write/Direct Message 权限）
3. Consumer Key + Consumer Secret
4. Access Token + Access Token Secret（用户授权获取）
5. Ads Account ID（需开通 X Ads 广告账户）
6. 中国大陆需 HTTPS 代理访问 api.x.com
7. API 配额严格（Basic tier: 10000 tweets/month，Ads API 需单独申请）
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import base64
import hashlib
import hmac
import logging
import os
import time
import urllib.parse

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


class XAdsCollector:
    """X Ads广告数据只读采集器（OAuth 1.0a 签名）。"""

    # X Ads API 标准指标
    ANALYTICS_METRICS = [
        "impressions", "clicks", "spend", "engagements", "follows",
        "conversions", "retweets", "likes", "replies", "qualified_impressions",
    ]

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
        return bool(
            self.config.proxy_url
            or os.environ.get("OPENAI_PROXY")
            or os.environ.get("HTTPS_PROXY")
        )

    def _get_proxies(self) -> Optional[Dict[str, str]]:
        proxy = (self.config.proxy_url
                 or os.environ.get("OPENAI_PROXY")
                 or os.environ.get("HTTPS_PROXY"))
        if proxy:
            return {"http": proxy, "https": proxy}
        return None

    # ── OAuth 1.0a 签名（X/Twitter API 规范）──────────────────
    @staticmethod
    def _percent_encode(s: str) -> str:
        """OAuth 1.0a 百分号编码（RFC 3986）。"""
        return urllib.parse.quote(s, safe="")

    def _build_oauth_signature(self, method: str, url: str,
                                 params: Dict[str, str]) -> str:
        """构建 OAuth 1.0a 签名（HMAC-SHA1）。

        签名算法（OAuth 1.0a RFC 5849）：
        1. 收集所有参数（OAuth 参数 + 请求参数）
        2. 按 key 字典序排序，百分号编码后拼接为 k=v&k=v
        3. 构建签名基串: METHOD&ENCODED_URL&ENCODED_PARAMS
        4. 签名密钥: ENCODED(consumer_secret)&ENCODED(token_secret)
        5. HMAC-SHA1 签名后 Base64 编码
        """
        # 1. 收集所有参数
        all_params = dict(params)

        # 2. 排序并编码
        sorted_items = sorted(all_params.items(), key=lambda x: x[0])
        encoded_params = "&".join(
            f"{self._percent_encode(k)}={self._percent_encode(str(v))}"
            for k, v in sorted_items
        )

        # 3. 签名基串
        base_string = "&".join([
            method.upper(),
            self._percent_encode(url),
            self._percent_encode(encoded_params),
        ])

        # 4. 签名密钥
        signing_key = "&".join([
            self._percent_encode(self.config.consumer_secret),
            self._percent_encode(self.config.access_token_secret),
        ])

        # 5. HMAC-SHA1 + Base64
        signature = hmac.new(
            signing_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        return base64.b64encode(signature).decode("utf-8")

    def _build_oauth_headers(self, method: str, url: str,
                              extra_params: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """构建 OAuth 1.0a 认证头。

        返回包含 Authorization 头的字典。
        """
        oauth_params = {
            "oauth_consumer_key": self.config.consumer_key,
            "oauth_nonce": hashlib.md5(str(time.time()).encode()).hexdigest(),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self.config.access_token,
            "oauth_version": "1.0",
        }

        # 合并所有参数用于签名
        all_params = dict(oauth_params)
        if extra_params:
            all_params.update(extra_params)

        # 计算签名
        signature = self._build_oauth_signature(method, url, all_params)
        oauth_params["oauth_signature"] = signature

        # 构建 Authorization 头
        auth_parts = ", ".join(
            f'{self._percent_encode(k)}="{self._percent_encode(str(v))}"'
            for k, v in sorted(oauth_params.items())
        )
        return {
            "Authorization": f"OAuth {auth_parts}",
            "Accept": "application/json",
            "User-Agent": "ZBC-AdIntelligence/2.0",
        }

    def _api_request(self, endpoint: str, params: Optional[Dict] = None,
                      method: str = "GET") -> Dict[str, Any]:
        """执行 X Ads API 请求（真实调用骨架，含 OAuth 1.0a 签名）。

        前置条件检查：
        - OAuth 四元组 + account_id 必须存在
        - 中国大陆需代理

        无凭证时返回 BLOCKED，不发起请求，不伪造数据。
        """
        if not self._has_api_access():
            missing = []
            if not self.config.consumer_key:
                missing.append("X_ADS_CONSUMER_KEY")
            if not self.config.consumer_secret:
                missing.append("X_ADS_CONSUMER_SECRET")
            if not self.config.access_token:
                missing.append("X_ADS_ACCESS_TOKEN")
            if not self.config.access_token_secret:
                missing.append("X_ADS_ACCESS_TOKEN_SECRET")
            if not self.config.account_id:
                missing.append("X_ADS_ACCOUNT_ID")
            return _blocked_response(
                reason=f"missing credentials: {', '.join(missing)}",
                required=missing,
                note="X Ads API需OAuth 1.0a四元组+account_id；无凭证禁止返回空数据",
            )
        if self.config.requires_proxy and not self._has_proxy():
            return _blocked_response(
                reason="proxy required for accessing api.x.com from mainland China",
                required=["HTTPS_PROXY 或 OPENAI_PROXY 环境变量"],
                note="中国大陆直连 api.x.com 不可达；需配置代理",
            )

        try:
            import requests
            params = params or {}
            params.setdefault("account_id", self.config.account_id)

            # 替换 URL 中的 account_id 占位符
            url_path = endpoint.format(account_id=self.config.account_id)
            url = f"{self.config.api_base}{url_path}"

            # 构建 OAuth 头（需要 query params 参与签名）
            str_params = {k: str(v) for k, v in params.items()}
            headers = self._build_oauth_headers(method, url, extra_params=str_params)
            proxies = self._get_proxies()

            if method.upper() == "GET":
                resp = requests.get(url, headers=headers, params=params,
                                     proxies=proxies, timeout=30)
            else:
                resp = requests.post(url, headers=headers, data=params,
                                      proxies=proxies, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                # X API 返回 {data: {...}, request: {...}}
                return {
                    "success": True,
                    "status": "ok",
                    "data": data.get("data", data),
                    "request_id": data.get("request", {}).get("request_id", ""),
                    "mode": "api",
                }
            # X API 错误处理
            try:
                err_data = resp.json()
                errors = err_data.get("errors", [])
                err_msg = "; ".join(e.get("message", str(e)) for e in errors) if errors else f"HTTP {resp.status_code}"
            except Exception:
                err_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
            return {
                "success": False,
                "status": "api_error",
                "error": err_msg,
                "http_status": resp.status_code,
                "data": None,
            }
        except ImportError:
            return {"success": False, "status": "dependency_error", "error": "requests 未安装", "data": None}
        except Exception as e:
            logger.error(f"X Ads API请求失败: {e}")
            return {"success": False, "status": "request_error", "error": str(e), "data": None}

    def health_check(self) -> Dict[str, Any]:
        has_api = self._has_api_access()
        has_proxy = self._has_proxy()
        blockers = []
        if not has_api:
            blockers.append("API未配置（OAuth 1.0a 四元组 + account_id）")
        if self.config.requires_proxy and not has_proxy:
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
            "auth_method": "OAuth 1.0a (HMAC-SHA1)",
            "note": "X Ads API需开发者审核，配额严格；政治广告需特批",
        }

    def get_analytics(self, start_time: str, end_time: str,
                       granularity: str = "DAY") -> Dict[str, Any]:
        """获取广告数据分析（只读，真实API调用）。

        Args:
            start_time: 开始时间 ISO 8601
            end_time: 结束时间 ISO 8601
            granularity: HOUR/DAY/TOTAL
        """
        params = {
            "start_time": start_time,
            "end_time": end_time,
            "granularity": granularity,
            "metric_groups": "BILLING,ENGAGEMENT,VIDEO",
            "placement": "ALL_ON_X",
        }
        return self._api_request(XAdsEndpoint.ANALYTICS.value, params=params)

    def get_campaigns(self) -> Dict[str, Any]:
        """获取广告计划列表（只读，真实API调用）。

        无凭证时返回 BLOCKED，禁止返回空列表冒充成功。
        """
        params = {"count": 100, "sort_by": "created_at-desc"}
        return self._api_request(XAdsEndpoint.CAMPAIGNS.value, params=params)

    def get_ad_groups(self) -> Dict[str, Any]:
        """获取广告组列表（只读）。"""
        params = {"count": 100}
        return self._api_request(XAdsEndpoint.AD_GROUPS.value, params=params)

    def get_funding_instruments(self) -> Dict[str, Any]:
        """获取资金工具（余额/支付方式）（只读）。"""
        return self._api_request(XAdsEndpoint.FUNDING_INSTRUMENTS.value)

    def parse_analytics_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析 X Ads Analytics API 响应为标准化指标列表。

        X API 返回: {data: {id: ..., id_data: [{metrics: {...}, segment: {...}}]}}
        """
        if not isinstance(data, dict):
            return []
        inner = data.get("data", data)
        records = inner.get("id_data", []) if isinstance(inner, dict) else []
        parsed = []
        for rec in records:
            metrics = rec.get("metrics", {})
            parsed.append({
                "date": rec.get("segment", {}).get("date", ""),
                "impressions": int(metrics.get("impressions", 0)),
                "clicks": int(metrics.get("clicks", 0)),
                "spend": float(metrics.get("spend", 0)),
                "engagements": int(metrics.get("engagements", 0)),
                "follows": int(metrics.get("follows", 0)),
                "retweets": int(metrics.get("retweets", 0)),
                "likes": int(metrics.get("likes", 0)),
                "replies": int(metrics.get("replies", 0)),
            })
        return parsed
