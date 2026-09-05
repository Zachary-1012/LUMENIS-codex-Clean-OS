# -*- coding: utf-8 -*-
"""
多平台账号保活系统
==================
系统内置AI浏览器工作，不跳转站外，但保留跳转选项。
定期检查cookie有效性，自动刷新登录态，失效时通知用户。

支持平台：小红书/抖音/B站/微博/知乎/Instagram/X/Facebook
保活方式：
1. 健康检查：访问平台首页，检测登录态
2. 自动刷新：浏览器访问首页保持会话活跃
3. 失效检测：cookie过期/被踢/需要验证
4. 通知机制：系统内弹窗+日志，不跳转站外
5. 手动跳转：保留"去登录"按钮选项
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import logging
import time
import os

logger = logging.getLogger(__name__)


class AccountStatus(str, Enum):
    """账号状态。"""
    ACTIVE = "active"               # 正常
    EXPIRING = "expiring"           # 即将过期（7天内）
    EXPIRED = "expired"             # 已过期
    NEED_VERIFY = "need_verify"     # 需要验证
    BLOCKED = "blocked"             # 被封禁/风控
    UNKNOWN = "unknown"             # 未知
    NO_COOKIE = "no_cookie"         # 无cookie


@dataclass
class AccountInfo:
    """账号信息。"""
    platform: str
    account_id: str = ""
    account_name: str = ""
    cookie_path: str = ""
    cookie_count: int = 0
    status: AccountStatus = AccountStatus.UNKNOWN
    last_check: float = 0
    last_refresh: float = 0
    expires_at: Optional[float] = None
    health_url: str = ""
    note: str = ""


@dataclass
class KeepAliveConfig:
    """保活配置。"""
    check_interval: int = 3600          # 检查间隔（秒），默认1小时
    refresh_interval: int = 7200        # 刷新间隔（秒），默认2小时
    expire_warning_days: int = 7        # 过期预警天数
    max_retries: int = 3                # 最大重试次数
    use_builtin_browser: bool = True    # 使用系统内置浏览器
    allow_external_redirect: bool = False  # 允许跳转站外（默认关闭）
    platforms: List[str] = field(default_factory=list)


class AccountKeepAlive:
    """多平台账号保活管理器。"""

    # 各平台健康检查URL和关键cookie
    PLATFORM_CONFIG = {
        "xhs": {
            "name": "小红书",
            "health_url": "https://www.xiaohongshu.com/",
            "key_cookies": ["web_session", "webId"],
            "cookie_path": "data/xhs_cookies.json",
        },
        "douyin": {
            "name": "抖音",
            "health_url": "https://www.douyin.com/",
            "key_cookies": ["sessionid", "sid_guard"],
            "cookie_path": "data/cookies/douyin.json",
        },
        "bilibili": {
            "name": "B站",
            "health_url": "https://www.bilibili.com/",
            "key_cookies": ["SESSDATA", "bili_jct"],
            "cookie_path": "data/bilibili_cookies.json",
        },
        "weibo": {
            "name": "微博",
            "health_url": "https://m.weibo.cn/",
            "key_cookies": ["SUB", "SUBP"],
            "cookie_path": "data/weibo_cookies.json",
        },
        "zhihu": {
            "name": "知乎",
            "health_url": "https://www.zhihu.com/",
            "key_cookies": ["z_c0", "_xsrf"],
            "cookie_path": "data/zhihu_cookies.json",
        },
        "instagram": {
            "name": "Instagram",
            "health_url": "https://www.instagram.com/",
            "key_cookies": ["sessionid", "ds_user_id"],
            "cookie_path": "data/cookies/instagram.json",
        },
        "x": {
            "name": "X(Twitter)",
            "health_url": "https://x.com/home",
            "key_cookies": ["auth_token", "ct0"],
            "cookie_path": "data/cookies/x.json",
        },
        "facebook": {
            "name": "Facebook",
            "health_url": "https://www.facebook.com/",
            "key_cookies": ["c_user", "xs"],
            "cookie_path": "data/cookies/facebook.json",
        },
        "jiguang": {
            "name": "聚光(小红书广告)",
            "health_url": "https://ad.xiaohongshu.com/",
            "key_cookies": ["web_session", "id_token"],
            "cookie_path": "data/cookies/jiguang.json",
        },
    }

    def __init__(self, config: Optional[KeepAliveConfig] = None):
        self.config = config or KeepAliveConfig()
        self.accounts: Dict[str, AccountInfo] = {}
        self._init_accounts()

    def _init_accounts(self):
        """初始化所有平台账号。"""
        platforms = self.config.platforms or list(self.PLATFORM_CONFIG.keys())
        for platform in platforms:
            if platform in self.PLATFORM_CONFIG:
                cfg = self.PLATFORM_CONFIG[platform]
                account = AccountInfo(
                    platform=platform,
                    health_url=cfg["health_url"],
                    cookie_path=cfg["cookie_path"],
                )
                self.accounts[platform] = account

    def _load_cookies(self, cookie_path: str) -> List[Dict]:
        """加载cookie文件。"""
        path = Path(cookie_path)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "cookies" in data:
                return data["cookies"]
        except Exception as e:
            logger.error(f"加载cookie失败 {cookie_path}: {e}")
        return []

    def _check_cookie_expiry(self, cookies: List[Dict]) -> Optional[float]:
        """检查cookie最早过期时间。"""
        earliest = None
        for c in cookies:
            expires = c.get("expires") or c.get("expiry")
            if expires and isinstance(expires, (int, float)):
                if earliest is None or expires < earliest:
                    earliest = expires
        return earliest

    def check_account(self, platform: str) -> AccountInfo:
        """检查单个平台账号状态。"""
        if platform not in self.accounts:
            return AccountInfo(platform=platform, status=AccountStatus.UNKNOWN)

        account = self.accounts[platform]
        cfg = self.PLATFORM_CONFIG.get(platform, {})
        cookies = self._load_cookies(account.cookie_path)
        account.cookie_count = len(cookies)
        account.last_check = time.time()

        if not cookies:
            account.status = AccountStatus.NO_COOKIE
            account.note = "无cookie文件"
            return account

        # 检查关键cookie是否存在
        key_cookies = cfg.get("key_cookies", [])
        cookie_names = {c.get("name", "") for c in cookies}
        missing_key = [k for k in key_cookies if k not in cookie_names]

        if missing_key:
            account.status = AccountStatus.EXPIRED
            account.note = f"缺少关键cookie: {', '.join(missing_key)}"
            return account

        # 检查过期时间
        expires_at = self._check_cookie_expiry(cookies)
        account.expires_at = expires_at

        if expires_at:
            days_left = (expires_at - time.time()) / 86400
            if days_left <= 0:
                account.status = AccountStatus.EXPIRED
                account.note = "cookie已过期"
            elif days_left <= self.config.expire_warning_days:
                account.status = AccountStatus.EXPIRING
                account.note = f"cookie将在{days_left:.1f}天后过期"
            else:
                account.status = AccountStatus.ACTIVE
                account.note = f"cookie有效，剩余{days_left:.1f}天"
        else:
            # session cookie（无过期时间），标记为active但需浏览器验证
            account.status = AccountStatus.ACTIVE
            account.note = "session cookie，需浏览器验证登录态"

        return account

    def check_all(self) -> Dict[str, AccountInfo]:
        """检查所有平台账号。"""
        results = {}
        for platform in self.accounts:
            results[platform] = self.check_account(platform)
        return results

    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态汇总。"""
        results = self.check_all()
        summary = {
            "total": len(results),
            "active": 0,
            "expiring": 0,
            "expired": 0,
            "need_verify": 0,
            "no_cookie": 0,
            "unknown": 0,
            "platforms": {},
        }
        for platform, account in results.items():
            status = account.status.value
            summary[status] = summary.get(status, 0) + 1
            cfg = self.PLATFORM_CONFIG.get(platform, {})
            summary["platforms"][platform] = {
                "name": cfg.get("name", platform),
                "status": status,
                "cookie_count": account.cookie_count,
                "note": account.note,
                "expires_at": account.expires_at,
            }
        return summary

    def get_login_url(self, platform: str) -> Optional[str]:
        """获取登录URL（保留跳转选项）。"""
        login_urls = {
            "xhs": "https://www.xiaohongshu.com/",
            "douyin": "https://www.douyin.com/",
            "bilibili": "https://passport.bilibili.com/login",
            "weibo": "https://m.weibo.cn/",
            "zhihu": "https://www.zhihu.com/signin",
            "instagram": "https://www.instagram.com/accounts/login/",
            "x": "https://x.com/i/flow/login",
            "facebook": "https://www.facebook.com/login",
            "jiguang": "https://ad.xiaohongshu.com/",
        }
        return login_urls.get(platform)

    def should_redirect_external(self, platform: str) -> bool:
        """是否允许跳转站外（默认不允许，保留选项）。"""
        return self.config.allow_external_redirect
