# -*- coding: utf-8 -*-
"""采集器接入层：让现有 requests 调用零改造地走 ProxyPool。"""
import requests
from .manager import proxy_manager


def create_session(platform: str = "general", timeout: int = 30):
    session = requests.Session()
    proxies = proxy_manager.get_requests_proxies(platform=platform)
    if proxies:
        session.proxies.update(proxies)
    session.request_timeout = timeout
    return session


def request(method, url, platform: str = "general", timeout: int = 30, **kwargs):
    proxies = proxy_manager.get_requests_proxies(platform=platform)
    if proxies:
        kwargs["proxies"] = proxies
    kwargs.setdefault("timeout", timeout)
    return requests.request(method, url, **kwargs)


def safe_request(method, url, platform: str = "general", timeout: int = 30,
                 allow_direct: bool = True, **kwargs):
    """代理失败自动按策略回退直连；强制出海平台可传 allow_direct=False。"""
    return proxy_manager.safe_request(method, url, platform=platform, timeout=timeout,
                                      allow_direct=allow_direct, **kwargs)
