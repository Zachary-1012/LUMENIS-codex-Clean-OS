"""
双池增强模块 - 参考MediaCrawler架构
====================================
Cookie池 + IP代理池，解决小红书300012风控问题

设计目标：
1. Cookie池：多Cookie轮换，失效自动标记，健康检查，账号隔离
2. IP代理池：代理列表，失败自动切换，健康检查，按平台限流
3. 与现有risk_controller集成：不改动现有代码，作为增强层导入
4. 熔断联动：Cookie/IP失效时触发risk_controller的熔断降级

接入方式：
    from dual_pool import CookiePool, ProxyPool, DualPoolManager
    pool = DualPoolManager(cookie_dir="data/cookies", proxy_list=["http://ip:port"])
    cookie = pool.get_cookie("xiaohongshu")  # 获取一个健康Cookie
    proxy = pool.get_proxy("xiaohongshu")     # 获取一个健康代理
    pool.mark_cookie_failed(cookie.id)        # 标记Cookie失效
    pool.mark_proxy_failed(proxy.id)          # 标记代理失效

依赖：无额外依赖（纯标准库）
"""
import os
import json
import time
import random
import threading
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum


class CookieStatus(Enum):
    HEALTHY = "healthy"
    SUSPECT = "suspect"      # 疑似失效（触发验证码）
    FAILED = "failed"        # 确认失效
    COOLDOWN = "cooldown"    # 冷却中（频繁触发风控）


class ProxyStatus(Enum):
    HEALTHY = "healthy"
    SLOW = "slow"            # 响应慢
    FAILED = "failed"        # 不可用
    COOLDOWN = "cooldown"    # 冷却中


@dataclass
class CookieItem:
    id: str
    platform: str
    cookie_data: dict
    status: CookieStatus = CookieStatus.HEALTHY
    fail_count: int = 0
    success_count: int = 0
    last_used: float = 0
    last_verified: float = 0
    cooldown_until: float = 0
    max_fail: int = 3        # 连续失败3次标记失效
    cooldown_seconds: int = 300  # 冷却5分钟

    def is_available(self) -> bool:
        if self.status == CookieStatus.FAILED:
            return False
        if self.status == CookieStatus.COOLDOWN and time.time() < self.cooldown_until:
            return False
        if self.status == CookieStatus.COOLDOWN and time.time() >= self.cooldown_until:
            self.status = CookieStatus.HEALTHY
            self.fail_count = 0
        return True

    def mark_success(self):
        self.success_count += 1
        self.fail_count = 0
        self.last_used = time.time()
        if self.status == CookieStatus.SUSPECT:
            self.status = CookieStatus.HEALTHY

    def mark_failed(self, reason: str = ""):
        self.fail_count += 1
        self.last_used = time.time()
        if self.fail_count >= self.max_fail:
            self.status = CookieStatus.FAILED
        elif self.fail_count >= 1:
            self.status = CookieStatus.SUSPECT
        if "300012" in reason or "验证码" in reason:
            # 触发风控，直接冷却
            self.status = CookieStatus.COOLDOWN
            self.cooldown_until = time.time() + self.cooldown_seconds

    def to_dict(self) -> dict:
        return {
            "id": self.id, "platform": self.platform,
            "status": self.status.value, "fail_count": self.fail_count,
            "success_count": self.success_count, "last_used": self.last_used,
        }


@dataclass
class ProxyItem:
    id: str
    url: str
    platform: str = "all"
    status: ProxyStatus = ProxyStatus.HEALTHY
    fail_count: int = 0
    success_count: int = 0
    avg_latency: float = 0
    last_used: float = 0
    cooldown_until: float = 0
    max_fail: int = 3
    cooldown_seconds: int = 120  # 代理冷却2分钟

    def is_available(self) -> bool:
        if self.status == ProxyStatus.FAILED:
            return False
        if self.status == ProxyStatus.COOLDOWN and time.time() < self.cooldown_until:
            return False
        if self.status == ProxyStatus.COOLDOWN and time.time() >= self.cooldown_until:
            self.status = ProxyStatus.HEALTHY
            self.fail_count = 0
        return True

    def mark_success(self, latency: float = 0):
        self.success_count += 1
        self.fail_count = 0
        self.last_used = time.time()
        if latency > 0:
            self.avg_latency = (self.avg_latency * 0.7 + latency * 0.3)
        if self.avg_latency > 5:
            self.status = ProxyStatus.SLOW

    def mark_failed(self):
        self.fail_count += 1
        self.last_used = time.time()
        if self.fail_count >= self.max_fail:
            self.status = ProxyStatus.FAILED
        else:
            self.status = ProxyStatus.COOLDOWN
            self.cooldown_until = time.time() + self.cooldown_seconds

    def to_dict(self) -> dict:
        return {
            "id": self.id, "url": self.url, "status": self.status.value,
            "fail_count": self.fail_count, "success_count": self.success_count,
            "avg_latency": round(self.avg_latency, 2),
        }


class CookiePool:
    """Cookie池：多Cookie轮换，失效自动标记"""

    def __init__(self, cookie_dir: str = "data/cookies"):
        self.cookie_dir = cookie_dir
        self.cookies: Dict[str, List[CookieItem]] = {}  # platform -> [CookieItem]
        self._lock = threading.Lock()
        self._load_from_dir()

    def _load_from_dir(self):
        """从目录加载Cookie文件（JSON格式）"""
        if not os.path.exists(self.cookie_dir):
            os.makedirs(self.cookie_dir, exist_ok=True)
            return
        for filename in os.listdir(self.cookie_dir):
            if not filename.endswith(".json"):
                continue
            # 文件名格式: platform_name.json 或 platform_name_id.json
            parts = filename.replace(".json", "").split("_")
            platform = parts[0] if parts else "unknown"
            try:
                with open(os.path.join(self.cookie_dir, filename), encoding="utf-8") as f:
                    data = json.load(f)
                cookie = CookieItem(
                    id=filename.replace(".json", ""),
                    platform=platform,
                    cookie_data=data,
                    last_verified=time.time(),
                )
                self.cookies.setdefault(platform, []).append(cookie)
            except Exception:
                continue

    def add_cookie(self, platform: str, cookie_data: dict, cookie_id: str = None) -> str:
        """添加Cookie到池中"""
        with self._lock:
            cid = cookie_id or f"{platform}_{int(time.time())}"
            cookie = CookieItem(id=cid, platform=platform, cookie_data=cookie_data)
            self.cookies.setdefault(platform, []).append(cookie)
            # 持久化
            self._save_cookie(cookie)
            return cid

    def _save_cookie(self, cookie: CookieItem):
        """持久化Cookie到文件"""
        path = os.path.join(self.cookie_dir, f"{cookie.id}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cookie.cookie_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_cookie(self, platform: str) -> Optional[CookieItem]:
        """获取一个健康的Cookie（轮询+最少使用策略）"""
        with self._lock:
            pool = self.cookies.get(platform, [])
            available = [c for c in pool if c.is_available()]
            if not available:
                return None
            # 优先选成功率高、最近未使用的
            available.sort(key=lambda c: (c.fail_count, c.last_used))
            cookie = available[0]
            cookie.last_used = time.time()
            return cookie

    def mark_cookie_result(self, cookie_id: str, success: bool, reason: str = ""):
        """标记Cookie使用结果"""
        with self._lock:
            for pool in self.cookies.values():
                for c in pool:
                    if c.id == cookie_id:
                        if success:
                            c.mark_success()
                        else:
                            c.mark_failed(reason)
                        return

    def get_stats(self, platform: str = None) -> dict:
        """获取池统计"""
        with self._lock:
            stats = {}
            targets = {platform: self.cookies[platform]} if platform else self.cookies
            for plat, pool in targets.items():
                stats[plat] = {
                    "total": len(pool),
                    "healthy": sum(1 for c in pool if c.status == CookieStatus.HEALTHY),
                    "suspect": sum(1 for c in pool if c.status == CookieStatus.SUSPECT),
                    "failed": sum(1 for c in pool if c.status == CookieStatus.FAILED),
                    "cooldown": sum(1 for c in pool if c.status == CookieStatus.COOLDOWN),
                    "details": [c.to_dict() for c in pool],
                }
            return stats


class ProxyPool:
    """IP代理池：代理列表，失败自动切换"""

    def __init__(self, proxy_list: List[str] = None, proxy_file: str = None):
        self.proxies: List[ProxyItem] = []
        self._lock = threading.Lock()
        if proxy_list:
            for i, url in enumerate(proxy_list):
                self.proxies.append(ProxyItem(id=f"proxy_{i}", url=url))
        if proxy_file and os.path.exists(proxy_file):
            self._load_from_file(proxy_file)

    def _load_from_file(self, path: str):
        """从文件加载代理列表（每行一个代理URL）"""
        try:
            with open(path, encoding="utf-8") as f:
                for i, line in enumerate(f):
                    url = line.strip()
                    if url and not url.startswith("#"):
                        self.proxies.append(ProxyItem(id=f"file_{i}", url=url))
        except Exception:
            pass

    def add_proxy(self, url: str, platform: str = "all") -> str:
        """添加代理"""
        with self._lock:
            pid = f"proxy_{int(time.time())}"
            self.proxies.append(ProxyItem(id=pid, url=url, platform=platform))
            return pid

    def get_proxy(self, platform: str = "all") -> Optional[ProxyItem]:
        """获取一个健康代理（轮询+低延迟优先）"""
        with self._lock:
            available = [p for p in self.proxies if p.is_available() and (p.platform == "all" or p.platform == platform)]
            if not available:
                return None
            available.sort(key=lambda p: (p.avg_latency, p.last_used))
            proxy = available[0]
            proxy.last_used = time.time()
            return proxy

    def mark_proxy_result(self, proxy_id: str, success: bool, latency: float = 0):
        """标记代理使用结果"""
        with self._lock:
            for p in self.proxies:
                if p.id == proxy_id:
                    if success:
                        p.mark_success(latency)
                    else:
                        p.mark_failed()
                    return

    def get_stats(self) -> dict:
        return {
            "total": len(self.proxies),
            "healthy": sum(1 for p in self.proxies if p.status == ProxyStatus.HEALTHY),
            "failed": sum(1 for p in self.proxies if p.status == ProxyStatus.FAILED),
            "details": [p.to_dict() for p in self.proxies],
        }


class DualPoolManager:
    """双池管理器：Cookie池 + 代理池 统一调度"""

    def __init__(self, cookie_dir: str = "data/cookies",
                 proxy_list: List[str] = None,
                 proxy_file: str = None,
                 risk_callback=None):
        self.cookie_pool = CookiePool(cookie_dir)
        self.proxy_pool = ProxyPool(proxy_list, proxy_file)
        self.risk_callback = risk_callback  # 风控回调，接入现有risk_controller

    def get_credentials(self, platform: str) -> dict:
        """获取一组凭证（Cookie+代理），用于采集请求"""
        cookie = self.cookie_pool.get_cookie(platform)
        proxy = self.proxy_pool.get_proxy(platform)
        return {
            "cookie": cookie,
            "proxy": proxy,
            "cookie_id": cookie.id if cookie else None,
            "proxy_url": proxy.url if proxy else None,
            "has_cookie": cookie is not None,
            "has_proxy": proxy is not None,
        }

    def report_result(self, platform: str, cookie_id: str = None,
                      proxy_id: str = None, success: bool = True,
                      reason: str = "", latency: float = 0):
        """上报采集结果，自动更新双池状态"""
        if cookie_id:
            self.cookie_pool.mark_cookie_result(cookie_id, success, reason)
        if proxy_id:
            self.proxy_pool.mark_proxy_result(proxy_id, success, latency)
        # 触发风控回调
        if not success and self.risk_callback:
            try:
                self.risk_callback(platform=platform, reason=reason,
                                   cookie_id=cookie_id, proxy_id=proxy_id)
            except Exception:
                pass

    def health_check(self) -> dict:
        """双池健康检查"""
        return {
            "cookie_pool": self.cookie_pool.get_stats(),
            "proxy_pool": self.proxy_pool.get_stats(),
            "timestamp": time.time(),
        }


# 与现有risk_controller集成的回调示例
def risk_controller_callback(platform: str, reason: str, **kwargs):
    """
    接入现有risk_controller的回调函数示例
    在现有代码中：
        from dual_pool import DualPoolManager, risk_controller_callback
        pool = DualPoolManager(risk_callback=risk_controller_callback)
    """
    print(f"[风控回调] platform={platform}, reason={reason}, kwargs={kwargs}")
    # 这里调用现有risk_controller的熔断/降频/告警逻辑
    # 例如：risk_controller.trigger_circuit_breaker(platform, reason)


if __name__ == "__main__":
    # 自测
    print("=== 双池模块自测 ===")
    pool = DualPoolManager(cookie_dir="data/cookies_test")

    # 添加测试Cookie
    cid1 = pool.cookie_pool.add_cookie("xiaohongshu", {"SUB": "test123"})
    cid2 = pool.cookie_pool.add_cookie("xiaohongshu", {"SUB": "test456"})
    print(f"添加Cookie: {cid1}, {cid2}")

    # 添加测试代理
    pid1 = pool.proxy_pool.add_proxy("http://127.0.0.1:8080")
    pid2 = pool.proxy_pool.add_proxy("http://127.0.0.1:8081")
    print(f"添加代理: {pid1}, {pid2}")

    # 获取凭证
    cred = pool.get_credentials("xiaohongshu")
    print(f"获取凭证: cookie={cred['cookie_id']}, proxy={cred['proxy_url']}")

    # 上报成功
    pool.report_result("xiaohongshu", cookie_id=cid1, proxy_id=pid1, success=True, latency=0.5)
    print("上报成功")

    # 上报失败（触发风控）
    pool.report_result("xiaohongshu", cookie_id=cid2, proxy_id=pid2, success=False, reason="300012风控")
    print("上报失败(300012)")

    # 健康检查
    stats = pool.health_check()
    print(f"Cookie池统计: {json.dumps(stats['cookie_pool'], ensure_ascii=False, indent=2)}")
    print(f"代理池统计: {json.dumps(stats['proxy_pool'], ensure_ascii=False, indent=2)}")

    # 清理测试目录
    import shutil
    shutil.rmtree("data/cookies_test", ignore_errors=True)
    print("自测完成")
