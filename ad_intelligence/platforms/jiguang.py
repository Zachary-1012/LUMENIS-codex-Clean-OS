# -*- coding: utf-8 -*-
"""
小红书聚光广告数据只读采集
==========================
真实商业现实：
- API: 聚光平台API（需特批，配额严格）
- 无API权限时：浏览器cookie只读采集广告后台（跳过OAuth认证）
- 币种: CNY，预充值，最低充值5000元
- 数据粒度: 天级（API有限开放）
- 种草内容审核较严

本模块只做只读数据采集，不做任何写操作。
采集路径优先级：API（需特批） > 浏览器cookie（已登录态） > 不可用

【BLOCKED 条件】
- API模式：缺少 JIGUANG_ACCESS_TOKEN 或 JIGUANG_ADVERTISER_ID
- 浏览器模式：缺少 web_session / id_token cookie
- 无凭证时返回 status="blocked"，禁止返回空列表冒充成功
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import hashlib
import hmac
import json
import logging
import os
import time

logger = logging.getLogger(__name__)


class JiguangEndpoint(str, Enum):
    """聚光平台API端点。"""
    REPORT_ACCOUNT = "/api/jg/report/account"
    REPORT_PLAN = "/api/jg/report/plan"
    REPORT_CREATIVE = "/api/jg/report/creative"
    ACCOUNT_INFO = "/api/jg/account/info"
    PLAN_LIST = "/api/jg/plan/list"
    BALANCE = "/api/jg/account/balance"
    DASHBOARD = "/api/jg/dashboard"
    CAMPAIGN_LIST = "/api/jg/campaign/list"


@dataclass
class JiguangConfig:
    """聚光平台配置。"""
    access_token: str = ""
    advertiser_id: str = ""
    api_base: str = "https://ad.xiaohongshu.com"
    use_browser_fallback: bool = True
    cookie_path: str = "data/cookies/jiguang.json"
    agency_rebate_rate: float = 0.0
    # API签名密钥（聚光API特批后发放，用于HMAC-SHA256签名）
    api_secret: str = ""


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


class JiguangCollector:
    """小红书聚光广告数据只读采集器。"""

    def __init__(self, config: Optional[JiguangConfig] = None):
        self.config = config or JiguangConfig()
        self._cookies: Optional[Dict[str, str]] = None
        self._cookie_loaded = False

    def _has_api_access(self) -> bool:
        return bool(self.config.access_token and self.config.advertiser_id)

    def _load_cookies(self) -> Dict[str, str]:
        """从cookie文件加载浏览器cookie（跳过OAuth认证）。"""
        if self._cookie_loaded:
            return self._cookies or {}

        self._cookie_loaded = True
        cookie_path = Path(self.config.cookie_path)
        if not cookie_path.exists():
            logger.info(f"聚光cookie文件不存在: {cookie_path}")
            self._cookies = {}
            return {}

        try:
            raw = json.loads(cookie_path.read_text(encoding="utf-8"))
            cookies = {}
            for item in raw:
                name = item.get("name", "")
                value = item.get("value", "")
                if name and value:
                    cookies[name] = value
            self._cookies = cookies
            logger.info(f"已加载 {len(cookies)} 条聚光cookie")
            return cookies
        except Exception as e:
            logger.error(f"加载聚光cookie失败: {e}")
            self._cookies = {}
            return {}

    def _has_browser_access(self) -> bool:
        """检查是否有浏览器cookie访问权限（跳过API认证）。"""
        if not self.config.use_browser_fallback:
            return False
        cookies = self._load_cookies()
        return bool(cookies.get("web_session") or cookies.get("id_token"))

    def _get_collection_mode(self) -> str:
        """获取当前采集模式。"""
        if self._has_api_access():
            return "api"
        if self._has_browser_access():
            return "browser_cookie"
        return "unavailable"

    # ── API 签名（聚光平台 HMAC-SHA256）──────────────────────
    def _build_api_signature(self, method: str, endpoint: str,
                              params: Dict[str, Any], body: str = "") -> str:
        """构建聚光API请求签名。

        签名算法（聚光平台规范）：
        1. 拼接签名字符串: method + endpoint + sorted(params) + body
        2. 使用 api_secret 作为密钥，HMAC-SHA256 签名
        3. 返回 hex 摘要

        接入条件：聚光API特批后发放 api_secret；无 secret 时 API 模式不可用。
        """
        if not self.config.api_secret:
            return ""
        sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        sign_str = f"{method.upper()}{endpoint}{sorted_params}{body}"
        return hmac.new(
            self.config.api_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _build_api_headers(self) -> Dict[str, str]:
        """构建API请求头（含 access_token 和签名）。"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "access-token": self.config.access_token,
            "advertiser-id": self.config.advertiser_id,
            "User-Agent": "ZBC-AdIntelligence/2.0",
        }
        return headers

    def _api_request(self, method: str, endpoint: str,
                     params: Optional[Dict] = None,
                     body: Optional[Dict] = None) -> Dict[str, Any]:
        """执行聚光API请求（真实调用骨架）。

        前置条件检查：
        - access_token / advertiser_id 必须存在
        - api_secret 用于签名（部分接口必需）

        无凭证时返回 BLOCKED，不发起请求，不伪造数据。
        """
        if not self._has_api_access():
            return _blocked_response(
                reason="missing credentials: access_token or advertiser_id",
                required=["JIGUANG_ACCESS_TOKEN", "JIGUANG_ADVERTISER_ID"],
                note="聚光API需企业特批；无凭证时禁止返回空数据",
            )

        try:
            import requests
            params = params or {}
            params.setdefault("advertiser_id", self.config.advertiser_id)
            params.setdefault("timestamp", str(int(time.time())))

            body_str = json.dumps(body, ensure_ascii=False) if body else ""
            signature = self._build_api_signature(method, endpoint, params, body_str)
            if signature:
                params["signature"] = signature

            url = f"{self.config.api_base}{endpoint}"
            headers = self._build_api_headers()

            if method.upper() == "GET":
                resp = requests.get(url, headers=headers, params=params, timeout=20)
            else:
                resp = requests.post(url, headers=headers, params=params,
                                     data=body_str.encode("utf-8"), timeout=20)

            if resp.status_code == 200:
                data = resp.json()
                # 聚光API返回 code=0 表示成功
                if data.get("code", 0) != 0:
                    return {
                        "success": False,
                        "status": "api_error",
                        "error": data.get("msg", f"API返回错误 code={data.get('code')}"),
                        "data": None,
                        "raw": data,
                    }
                return {"success": True, "status": "ok", "data": data.get("data", data), "mode": "api"}
            return {
                "success": False,
                "status": "http_error",
                "error": f"HTTP {resp.status_code}",
                "data": None,
            }
        except ImportError:
            return {"success": False, "status": "dependency_error", "error": "requests 未安装", "data": None}
        except Exception as e:
            logger.error(f"聚光API请求失败: {e}")
            return {"success": False, "status": "request_error", "error": str(e), "data": None}

    def health_check(self) -> Dict[str, Any]:
        mode = self._get_collection_mode()
        cookies = self._load_cookies()
        blockers = []
        if mode == "unavailable":
            blockers.append("无API凭证且无浏览器cookie")
        if self._has_api_access() and not self.config.api_secret:
            blockers.append("API签名密钥(api_secret)未配置，部分接口无法签名")
        return {
            "platform": "xhs",
            "ad_system": "jiguang",
            "collection_mode": mode,
            "api_access": self._has_api_access(),
            "browser_cookie_access": self._has_browser_access(),
            "cookie_count": len(cookies),
            "has_web_session": bool(cookies.get("web_session")),
            "has_id_token": bool(cookies.get("id_token")),
            "currency": "CNY",
            "min_deposit": 5000,
            "agency_rebate_rate": self.config.agency_rebate_rate,
            "status": "ready" if mode != "unavailable" else "blocked",
            "blockers": blockers,
            "note": "聚光API需特批；无API时用浏览器cookie只读采集（跳过OAuth认证）",
        }

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头（浏览器cookie模式）。"""
        cookies = self._load_cookies()
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://ad.xiaohongshu.com/",
            "Cookie": cookie_str,
        }

    def get_balance(self) -> Dict[str, Any]:
        """获取账户余额（只读）。"""
        mode = self._get_collection_mode()
        if mode == "unavailable":
            return _blocked_response(
                reason="no collection access: API credentials and browser cookies both missing",
                required=["JIGUANG_ACCESS_TOKEN+JIGUANG_ADVERTISER_ID", "或 web_session/id_token cookie"],
                note="无凭证时禁止返回空余额数据",
            )

        if mode == "api":
            return self._api_request("GET", JiguangEndpoint.BALANCE.value)

        # 浏览器cookie模式
        try:
            import requests
            url = f"{self.config.api_base}{JiguangEndpoint.BALANCE.value}"
            resp = requests.get(url, headers=self._build_headers(), timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return {"success": True, "data": data, "mode": "browser_cookie"}
            return {"success": False, "error": f"HTTP {resp.status_code}", "data": None}
        except Exception as e:
            return {"success": False, "error": f"请求失败: {e}", "data": None}

    def get_dashboard(self) -> Dict[str, Any]:
        """获取仪表盘数据（只读，浏览器cookie模式）。"""
        if not self._has_browser_access():
            return _blocked_response(
                reason="browser cookie access required for dashboard",
                required=["web_session 或 id_token cookie (data/cookies/jiguang.json)"],
                note="仪表盘接口仅支持浏览器cookie模式",
            )

        try:
            import requests
            url = f"{self.config.api_base}{JiguangEndpoint.DASHBOARD.value}"
            resp = requests.get(url, headers=self._build_headers(), timeout=15)
            if resp.status_code == 200:
                return {"success": True, "data": resp.json(), "mode": "browser_cookie"}
            return {"success": False, "error": f"HTTP {resp.status_code}", "data": None}
        except Exception as e:
            return {"success": False, "error": f"请求失败: {e}", "data": None}

    def get_daily_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """获取广告主日报表（只读）。"""
        mode = self._get_collection_mode()
        if mode == "unavailable":
            return _blocked_response(
                reason="no collection access",
                required=["JIGUANG_ACCESS_TOKEN+JIGUANG_ADVERTISER_ID", "或浏览器cookie"],
            )

        if mode == "api":
            return self._api_request("GET", JiguangEndpoint.REPORT_ACCOUNT.value,
                                     params={"start_date": start_date, "end_date": end_date})

        # 浏览器cookie模式
        try:
            import requests
            url = f"{self.config.api_base}{JiguangEndpoint.REPORT_ACCOUNT.value}"
            params = {"start_date": start_date, "end_date": end_date}
            resp = requests.get(url, headers=self._build_headers(), params=params, timeout=15)
            if resp.status_code == 200:
                return {"success": True, "data": resp.json(), "mode": "browser_cookie"}
            return {"success": False, "error": f"HTTP {resp.status_code}", "data": None}
        except Exception as e:
            return {"success": False, "error": f"请求失败: {e}", "data": None}

    def get_campaign_list(self) -> Dict[str, Any]:
        """获取广告计划列表（只读）。"""
        mode = self._get_collection_mode()
        if mode == "api":
            return self._api_request("GET", JiguangEndpoint.CAMPAIGN_LIST.value)
        if not self._has_browser_access():
            return _blocked_response(
                reason="no collection access for campaign list",
                required=["API凭证 或 浏览器cookie"],
                note="禁止返回空列表冒充成功",
            )
        try:
            import requests
            url = f"{self.config.api_base}{JiguangEndpoint.CAMPAIGN_LIST.value}"
            resp = requests.get(url, headers=self._build_headers(), timeout=15)
            if resp.status_code == 200:
                return {"success": True, "data": resp.json(), "mode": "browser_cookie"}
            return {"success": False, "error": f"HTTP {resp.status_code}", "data": None}
        except Exception as e:
            return {"success": False, "error": f"请求失败: {e}", "data": None}

    def calculate_actual_cost(self, nominal_cost: float) -> float:
        """计算实际成本（扣除代理商返点）。"""
        if self.config.agency_rebate_rate <= 0:
            return nominal_cost
        return nominal_cost * (1 - self.config.agency_rebate_rate)
