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

【BLOCKED 条件】
- 缺少 OCEAN_ENGINE_ACCESS_TOKEN 或 OCEAN_ENGINE_ADVERTISER_ID
- 无凭证时返回 status="blocked"，禁止返回空列表冒充成功

【接入条件】
1. 巨量引擎企业账户（需营业执照审核）
2. Marketing API 应用（需开发者资质审核）
3. access_token（OAuth2 授权获取，有效期需刷新）
4. advertiser_id（广告主ID）
5. API 有 QPS 限制（默认 10 QPS，可申请提升）
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import logging
import time

logger = logging.getLogger(__name__)


class OceanEngineEndpoint(str, Enum):
    """巨量引擎API端点。"""
    REPORT_ADVERTISER = "/2/report/advertiser/get/"
    REPORT_CAMPAIGN = "/2/report/campaign/get/"
    REPORT_CREATIVE = "/2/report/creative/get/"
    ADVERTISER_INFO = "/2/advertiser/info/"
    CAMPAIGN_LIST = "/2/campaign/get/"
    BALANCE = "/2/advertiser/balance/"


@dataclass
class OceanEngineConfig:
    """巨量引擎配置。"""
    access_token: str = ""                # API access_token（从.env读取，不写源码）
    advertiser_id: str = ""               # 广告主ID
    api_base: str = "https://api.oceanengine.com/open_api"
    use_browser_fallback: bool = True     # 无API时是否用浏览器只读采集
    agency_rebate_rate: float = 0.0       # 代理商返点率（0-1），影响实际成本
    qps_limit: int = 10                    # API QPS 限制


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


class OceanEngineCollector:
    """巨量引擎广告数据只读采集器。"""

    # 巨量引擎报表标准指标
    REPORT_METRICS = [
        "stat_cost", "show_cnt", "click_cnt", "ctr", "cpc", "cpm",
        "convert_cnt", "cvr", "cost_per_convert", "total_convert_cost",
        "dyun_follow_count", "dyun_like_count", "dyun_comment_count",
        "dyun_share_count",
    ]

    def __init__(self, config: Optional[OceanEngineConfig] = None):
        self.config = config or OceanEngineConfig()
        self._last_request_time = 0.0

    def _has_api_access(self) -> bool:
        """检查是否有API访问权限。"""
        return bool(self.config.access_token and self.config.advertiser_id)

    def _rate_limit_wait(self) -> None:
        """简单的 QPS 限流（巨量引擎默认 10 QPS）。"""
        min_interval = 1.0 / self.config.qps_limit
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    def _build_headers(self) -> Dict[str, str]:
        """构建API请求头（巨量引擎 Marketing API 规范）。"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Access-Token": self.config.access_token,
            "User-Agent": "ZBC-AdIntelligence/2.0",
        }

    def _api_request(self, endpoint: str, params: Optional[Dict] = None,
                      body: Optional[Dict] = None, method: str = "GET") -> Dict[str, Any]:
        """执行巨量引擎 Marketing API 请求（真实调用骨架）。

        前置条件检查：
        - access_token / advertiser_id 必须存在

        无凭证时返回 BLOCKED，不发起请求，不伪造数据。
        """
        if not self._has_api_access():
            return _blocked_response(
                reason="missing credentials: access_token or advertiser_id",
                required=["OCEAN_ENGINE_ACCESS_TOKEN", "OCEAN_ENGINE_ADVERTISER_ID"],
                note="巨量引擎Marketing API需企业资质审核；无凭证禁止返回空数据",
            )

        self._rate_limit_wait()

        try:
            import requests
            params = params or {}
            params.setdefault("advertiser_id", self.config.advertiser_id)

            url = f"{self.config.api_base}{endpoint}"
            headers = self._build_headers()

            if method.upper() == "GET":
                resp = requests.get(url, headers=headers, params=params, timeout=20)
            else:
                resp = requests.post(url, headers=headers, params=params,
                                     json=body or {}, timeout=20)

            if resp.status_code == 200:
                data = resp.json()
                # 巨量引擎 API 返回 code=0 表示成功
                if data.get("code", -1) != 0:
                    return {
                        "success": False,
                        "status": "api_error",
                        "error": data.get("message", f"API返回错误 code={data.get('code')}"),
                        "error_code": data.get("code"),
                        "request_id": data.get("request_id", ""),
                        "data": None,
                    }
                return {
                    "success": True,
                    "status": "ok",
                    "data": data.get("data", data),
                    "request_id": data.get("request_id", ""),
                    "mode": "api",
                }
            return {
                "success": False,
                "status": "http_error",
                "error": f"HTTP {resp.status_code}",
                "data": None,
            }
        except ImportError:
            return {"success": False, "status": "dependency_error", "error": "requests 未安装", "data": None}
        except Exception as e:
            logger.error(f"巨量引擎API请求失败: {e}")
            return {"success": False, "status": "request_error", "error": str(e), "data": None}

    def health_check(self) -> Dict[str, Any]:
        """健康检查（只读，不调用计费接口）。"""
        has_api = self._has_api_access()
        blockers = []
        if not has_api:
            blockers.append("API未配置（access_token/advertiser_id）")
        return {
            "platform": "douyin",
            "ad_system": "ocean_engine",
            "api_access": has_api,
            "browser_fallback": self.config.use_browser_fallback,
            "currency": "CNY",
            "min_deposit": 10000,
            "agency_rebate_rate": self.config.agency_rebate_rate,
            "qps_limit": self.config.qps_limit,
            "status": "ready" if has_api else "blocked",
            "blockers": blockers,
            "note": "巨量引擎Marketing API需企业资质审核；代理商返点3%-15%",
        }

    def get_balance(self) -> Dict[str, Any]:
        """获取账户余额（只读，真实API调用）。"""
        return self._api_request(OceanEngineEndpoint.BALANCE.value)

    def get_daily_report(self, start_date: str, end_date: str,
                          metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取广告主日报表（只读，真实API调用）。

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            metrics: 指标列表，默认使用标准指标集
        """
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "metrics": json.dumps(metrics or self.REPORT_METRICS),
            "page": 1,
            "page_size": 100,
        }
        return self._api_request(OceanEngineEndpoint.REPORT_ADVERTISER.value, params=params)

    def get_campaign_list(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """获取广告组列表（只读，真实API调用）。

        无凭证时返回 BLOCKED，禁止返回空列表冒充成功。
        """
        params = {
            "page": page,
            "page_size": page_size,
        }
        return self._api_request(OceanEngineEndpoint.CAMPAIGN_LIST.value, params=params)

    def get_advertiser_info(self) -> Dict[str, Any]:
        """获取广告主信息（只读）。"""
        return self._api_request(OceanEngineEndpoint.ADVERTISER_INFO.value)

    def parse_report_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析巨量引擎报表 API 响应为标准化指标列表。

        巨量引擎返回: {data: {list: [...], page_info: {...}}}
        """
        if not isinstance(data, dict):
            return []
        inner = data.get("data", data)
        records = inner.get("list", []) if isinstance(inner, dict) else []
        parsed = []
        for rec in records:
            parsed.append({
                "date": rec.get("stat_datetime", rec.get("date", "")),
                "cost": float(rec.get("stat_cost", 0)),
                "impressions": int(rec.get("show_cnt", 0)),
                "clicks": int(rec.get("click_cnt", 0)),
                "ctr": float(rec.get("ctr", 0)),
                "cpc": float(rec.get("cpc", 0)),
                "cpm": float(rec.get("cpm", 0)),
                "conversions": int(rec.get("convert_cnt", 0)),
                "cvr": float(rec.get("cvr", 0)),
                "follows": int(rec.get("dyun_follow_count", 0)),
                "likes": int(rec.get("dyun_like_count", 0)),
                "comments": int(rec.get("dyun_comment_count", 0)),
                "shares": int(rec.get("dyun_share_count", 0)),
            })
        return parsed

    def calculate_actual_cost(self, nominal_cost: float) -> float:
        """计算实际成本（扣除代理商返点）。

        真实商业现实：代理商返点3%-15%，实际成本 = 消耗 × (1 - 返点率)
        """
        if self.config.agency_rebate_rate <= 0:
            return nominal_cost
        return nominal_cost * (1 - self.config.agency_rebate_rate)
