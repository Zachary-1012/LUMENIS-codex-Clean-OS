# -*- coding: utf-8 -*-
"""启动时加载代理节点：本机付费主代理（env）+ 人工审核节点（本地 JSON）。绝不自动抓取未知免费节点。"""
import os
import json
from .config import ProxyConfig
from .manager import proxy_manager
from .models import ProxyNode


def load_proxy_nodes(path: str = "config/proxy_nodes.json") -> dict:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # 1) 本机付费主代理（v2rayN/Xray 本地端口），只从环境变量读取，不硬编码任何 UUID/密钥
    local_urls = []
    for u in (ProxyConfig.HTTP_PROXY, ProxyConfig.SOCKS_PROXY, ProxyConfig.LEGACY_PROXY):
        u = (u or "").strip()
        if u and u not in local_urls:
            local_urls.append(u)
    for i, u in enumerate(local_urls):
        proxy_manager.add_node(ProxyNode(
            name="local-primary" if i == 0 else f"local-{i + 1}",
            url=u, platform="general", priority=200 - i, source="local"), replace=True)

    # 2) 人工审核后的节点（付费备用 / 已审核公开节点）。文件缺失属正常，不报错、不影响启动。
    try:
        abs_path = path if os.path.isabs(path) else os.path.join(root, path)
        if os.path.exists(abs_path):
            with open(abs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("nodes", []):
                if not item.get("name") or not item.get("url"):
                    continue
                proxy_manager.add_node(ProxyNode(
                    name=item["name"], url=item["url"],
                    platform=item.get("platform", "general"),
                    priority=item.get("priority", 100),
                    enabled=item.get("enabled", True),
                    source=item.get("source", "manual")))
    except Exception as exc:
        print("[ProxyPool] load manual nodes failed:", exc)

    return proxy_manager.status()
