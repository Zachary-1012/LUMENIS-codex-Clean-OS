# -*- coding: utf-8 -*-
"""
ZBC V2.0 性能隔离 — 基础限流中间件
====================================
CTH 大规模采集不得拖垮 ZBMP UI/API。
基础限流：采集 API QPS 限制，防止单域采集打爆全局。

定位：轻量级令牌桶限流，不依赖外部服务。
完整性能隔离（独立进程/资源配额）需部署层配合，此处为应用层基础保护。
"""
from __future__ import annotations

import time
import threading
from collections import defaultdict
from functools import wraps
from typing import Dict, Optional


class RateLimiter:
    """轻量级令牌桶限流器（按域+端点隔离）。

    每个 (domain, endpoint) 组合独立计数，防止 CTH 采集拖垮 ZBMP API。
    """

    def __init__(self, default_qps: int = 10):
        self._default_qps = default_qps
        self._limits: Dict[str, int] = {}  # key -> qps limit
        self._tokens: Dict[str, float] = defaultdict(float)
        self._last_refill: Dict[str, float] = {}
        self._lock = threading.Lock()

    def set_limit(self, domain: str, endpoint: str, qps: int):
        """设置特定域+端点的 QPS 限制。"""
        key = f"{domain}:{endpoint}"
        self._limits[key] = qps

    def _get_limit(self, key: str) -> int:
        return self._limits.get(key, self._default_qps)

    def acquire(self, domain: str, endpoint: str) -> bool:
        """尝试获取令牌。返回 True 表示允许，False 表示限流。"""
        key = f"{domain}:{endpoint}"
        now = time.time()
        with self._lock:
            limit = self._get_limit(key)
            if key not in self._last_refill:
                self._last_refill[key] = now
                self._tokens[key] = float(limit)
            # 补充令牌
            elapsed = now - self._last_refill[key]
            self._tokens[key] = min(
                float(limit),
                self._tokens[key] + elapsed * limit
            )
            self._last_refill[key] = now
            # 消费令牌
            if self._tokens[key] >= 1.0:
                self._tokens[key] -= 1.0
                return True
            return False

    def get_status(self) -> Dict[str, any]:
        """获取限流状态（用于 System 页监控）。"""
        with self._lock:
            return {
                "limits": dict(self._limits),
                "default_qps": self._default_qps,
                "tracked_keys": len(self._tokens),
            }


# 全局限流器实例
_global_limiter = RateLimiter(default_qps=10)


def get_global_limiter() -> RateLimiter:
    """获取全局限流器。"""
    return _global_limiter


def rate_limit(domain: str = "", endpoint: str = "", qps: Optional[int] = None):
    """限流装饰器。

    Args:
        domain: 域标识（zbmp/cth/system），空则从请求上下文推断
        endpoint: 端点标识，空则用函数名
        qps: 每秒请求数限制，None 则用默认值
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 推断域（从 Flask request 或参数）
            actual_domain = domain
            if not actual_domain:
                try:
                    from flask import request
                    actual_domain = request.headers.get("X-Domain-Id", "unknown")
                except Exception:
                    actual_domain = "unknown"
            actual_endpoint = endpoint or func.__name__
            if qps:
                _global_limiter.set_limit(actual_domain, actual_endpoint, qps)
            if not _global_limiter.acquire(actual_domain, actual_endpoint):
                from flask import jsonify
                resp = jsonify({
                    "success": False,
                    "error": f"rate_limited: domain={actual_domain}, endpoint={actual_endpoint}",
                    "domain_id": actual_domain,
                    "product_id": actual_domain.upper() if actual_domain in ("zbmp", "cth", "system") else "",
                })
                resp.status_code = 429
                resp.headers["X-RateLimit-Limit"] = str(qps or _global_limiter._default_qps)
                return resp
            return func(*args, **kwargs)
        return wrapper
    return decorator


# 预设采集 API 限流（CTH 采集更严格，防止拖垮 ZBMP）
def init_collection_rate_limits():
    """初始化采集 API 限流规则。"""
    limiter = get_global_limiter()
    # CTH 采集 API：5 QPS（严格限制）
    limiter.set_limit("cth", "collection", 5)
    limiter.set_limit("cth", "xhs_collection", 3)
    # ZBMP API：10 QPS（正常）
    limiter.set_limit("zbmp", "api", 10)
    # SYSTEM API：20 QPS
    limiter.set_limit("system", "api", 20)
    return limiter.get_status()
