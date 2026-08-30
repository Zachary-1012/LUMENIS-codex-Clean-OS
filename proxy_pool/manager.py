# -*- coding: utf-8 -*-
"""ProxyManager：节点注册、健康检查、评分选路、冷却切换、失败回退、状态快照。线程安全。"""
import threading
import time
from typing import Dict, Optional

from .config import ProxyConfig
from .health import ProxyHealthChecker
from .models import ProxyNode


class ProxyUnavailable(RuntimeError):
    """强制走代理的平台在“无任何可用代理节点”时抛出，避免登录态/敏感流量裸奔到直连。"""


class ProxyManager:
    def __init__(self):
        self.nodes: Dict[str, ProxyNode] = {}
        self.lock = threading.RLock()
        self.checker = ProxyHealthChecker(timeout=ProxyConfig.HEALTHCHECK_TIMEOUT,
                                          healthcheck_url=ProxyConfig.HEALTHCHECK_URL)
        self.current_node: Dict[str, str] = {}  # platform -> node.name

    # ---------------- 节点管理 ----------------
    def add_node(self, node: ProxyNode, replace: bool = True):
        with self.lock:
            if node.name in self.nodes and not replace:
                return
            self.nodes[node.name] = node

    def remove_node(self, name: str):
        with self.lock:
            self.nodes.pop(name, None)

    def enable_node(self, name: str):
        with self.lock:
            n = self.nodes.get(name)
            if n: n.enabled = True

    def disable_node(self, name: str):
        with self.lock:
            n = self.nodes.get(name)
            if n: n.enabled = False

    # ---------------- 健康检查 ----------------
    def check_node(self, name: str) -> dict:
        with self.lock:
            node = self.nodes.get(name)
        if node is None:
            return {"ok": False, "error": "node_not_found"}
        result = self.checker.check(node.url)
        with self.lock:
            if result["ok"]:
                node.mark_success(result["latency_ms"])
            else:
                node.mark_failure(ProxyConfig.COOLDOWN_SECONDS)
        return result

    def check_all(self) -> dict:
        out = {}
        for name in list(self.nodes.keys()):
            out[name] = self.check_node(name)
        return out

    # ---------------- 选路 ----------------
    @staticmethod
    def _score(node: ProxyNode):
        latency = node.latency_ms if node.latency_ms is not None else 999999
        success_rate = node.successes / max(1, node.successes + node.failures)
        return node.priority, success_rate, -latency  # 优先级高 > 成功率高 > 延迟低

    def get_node(self, platform: str = "general") -> Optional[ProxyNode]:
        with self.lock:
            cands = [n for n in self.nodes.values()
                     if n.available() and (n.platform == platform or n.platform == "general")]
            if not cands:
                return None
            healthy = [n for n in cands if n.healthy]
            # 冷启动：一个已验证健康节点都没有时，允许“未知节点”试一次，成功后即转健康；否则永远无法首验。
            pool = healthy if healthy else cands
            pool.sort(key=self._score, reverse=True)
            chosen = pool[0]
            self.current_node[platform] = chosen.name
            return chosen

    def get_requests_proxies(self, platform: str = "general"):
        if not ProxyConfig.ENABLED:
            return None
        node = self.get_node(platform)
        if node is None:
            return None
        return {"http": node.url, "https": node.url}

    # ---------------- 带兜底的请求（供采集器直接调用） ----------------
    def safe_request(self, method, url, platform: str = "general", timeout: int = 30,
                     allow_direct: bool = True, **kwargs):
        import requests

        def _direct():
            kwargs.pop("proxies", None)
            kwargs.setdefault("timeout", timeout)
            return requests.request(method, url, **kwargs)

        def _direct_allowed() -> bool:
            return allow_direct and ProxyConfig.ALLOW_DIRECT_FALLBACK

        proxies = self.get_requests_proxies(platform)
        if not proxies:
            # 无任何可用代理节点：普通平台按策略直连；强制出海平台直接报错，绝不裸奔直连
            if _direct_allowed():
                return _direct()
            raise ProxyUnavailable(f"无可用代理节点且该平台禁止直连: {platform}")

        node = self.get_node(platform)
        t0 = time.perf_counter()
        try:
            kwargs["proxies"] = proxies
            kwargs.setdefault("timeout", timeout)
            resp = requests.request(method, url, **kwargs)
            if node: node.mark_success((time.perf_counter() - t0) * 1000)
            return resp
        except Exception:
            if node: node.mark_failure(ProxyConfig.COOLDOWN_SECONDS)
            if not _direct_allowed():
                raise  # 强制出海平台不允许悄悄漏到直连
            return _direct()

    # ---------------- 状态快照 ----------------
    def status(self) -> dict:
        with self.lock:
            now = time.time()
            nodes = []
            for n in self.nodes.values():
                nodes.append({
                    "name": n.name, "url": _mask(n.url), "enabled": n.enabled, "healthy": n.healthy,
                    "platform": n.platform, "source": n.source, "priority": n.priority,
                    "latency_ms": n.latency_ms, "successes": n.successes, "failures": n.failures,
                    "in_cooldown": now < n.cooldown_until,
                    "cooldown_remain_s": max(0, int(n.cooldown_until - now)),
                })
            return {"enabled": ProxyConfig.ENABLED, "mode": ProxyConfig.MODE,
                    "allow_direct_fallback": ProxyConfig.ALLOW_DIRECT_FALLBACK,
                    "current_node": dict(self.current_node), "nodes": nodes}


def _mask(url: str) -> str:
    """状态展示时只保留协议与端口，不回显任何可能内嵌的账号信息。"""
    try:
        if "@" in url:
            tail = url.split("@", 1)[1]
            scheme = url.split("://", 1)[0]
            return f"{scheme}://***@{tail}"
    except Exception:
        pass
    return url


proxy_manager = ProxyManager()
