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
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json
import logging
import os

logger = logging.getLogger(__name__)


class JiguangEndpoint(str, Enum):
    """聚光平台API端点。"""
    REPORT_ACCOUNT = "/api/jg/report/account"
    REPORT_PLAN = "/api/jg/report/plan"
    REPORT_CREATIVE = "/api/jg/report/creative"
    ACCOUNT_INFO = "/api/jg/account/info"
    PLAN_LIST = "/api/jg/plan/list"
    BALANCE = "/api/jg/account/balance"
    DASHBOARD = "/api/jg/dashboard"               # 仪表盘数据
    CAMPAIGN_LIST = "/api/jg/campaign/list"       # 广告计划列表


@dataclass
class JiguangConfig:
    """聚光平台配置。"""
    access_token: str = ""
    advertiser_id: str = ""
    api_base: str = "https://ad.xiaohongshu.com"
    use_browser_fallback: bool = True
    cookie_path: str = "data/cookies/jiguang.json"
    agency_rebate_rate: float = 0.0


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
        # 聚光后台需要web_session或id_token
        return bool(cookies.get("web_session") or cookies.get("id_token"))

    def _get_collection_mode(self) -> str:
        """获取当前采集模式。"""
        if self._has_api_access():
            return "api"
        if self._has_browser_access():
            return "browser_cookie"
        return "unavailable"

    def health_check(self) -> Dict[str, Any]:
        mode = self._get_collection_mode()
        cookies = self._load_cookies()
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
            "status": "ready" if mode != "unavailable" else "need_credentials",
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
            return {"success": False, "error": "无API权限且无浏览器cookie", "data": None}

        if mode == "api":
            return {"success": True, "data": {"balance": None, "currency": "CNY", "note": "API调用待实现"}}

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
            return {"success": False, "error": "无浏览器cookie，无法采集仪表盘", "data": None}

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
            return {"success": False, "error": "无采集权限", "data": None}

        if mode == "api":
            return {
                "success": True,
                "data": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "metrics": ["impressions", "clicks", "cost", "interactions", "follows"],
                    "note": "API调用待实现",
                },
            }

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
        if not self._has_browser_access():
            return {"success": False, "error": "无浏览器cookie", "data": None}

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
