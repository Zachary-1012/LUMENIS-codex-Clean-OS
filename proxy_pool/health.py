# -*- coding: utf-8 -*-
"""代理节点健康检查（只做连通性/延迟探测，不做任何风控对抗）。"""
import time
import requests


class ProxyHealthChecker:
    def __init__(self, timeout=8, healthcheck_url="https://www.gstatic.com/generate_204"):
        self.timeout = timeout
        self.healthcheck_url = healthcheck_url

    def check(self, proxy_url: str) -> dict:
        proxies = {"http": proxy_url, "https": proxy_url}
        start = time.perf_counter()
        try:
            resp = requests.get(self.healthcheck_url, proxies=proxies,
                                timeout=self.timeout, allow_redirects=False)
            elapsed = (time.perf_counter() - start) * 1000
            if 200 <= resp.status_code < 400:
                return {"ok": True, "latency_ms": round(elapsed, 2), "error": None}
            return {"ok": False, "latency_ms": round(elapsed, 2), "error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            return {"ok": False, "latency_ms": None, "error": str(exc)}
