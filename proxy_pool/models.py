# -*- coding: utf-8 -*-
"""代理节点数据模型。"""
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProxyNode:
    """单个代理节点。

    url 示例：
      http://127.0.0.1:10809
      socks5h://127.0.0.1:10808
    platform: general / xhs / weibo / bilibili / instagram / google / github ...
              general 表示对所有平台通用。
    """
    name: str
    url: str
    enabled: bool = True
    priority: int = 100
    platform: str = "general"
    source: str = "manual"          # local(本机付费主代理) / manual(人工审核导入) / quarantine(隔离)
    failures: int = 0
    successes: int = 0
    latency_ms: Optional[float] = None
    last_check: Optional[float] = None
    cooldown_until: float = 0.0
    healthy: bool = False           # 尚未做过健康检查时为 False（冷启动由 manager 允许“未知节点”试一次）

    def available(self) -> bool:
        if not self.enabled:
            return False
        if time.time() < self.cooldown_until:
            return False
        return True

    def mark_success(self, latency_ms: float):
        self.successes += 1
        self.failures = 0
        self.latency_ms = latency_ms
        self.last_check = time.time()
        self.healthy = True

    def mark_failure(self, cooldown_seconds: int):
        self.failures += 1
        self.last_check = time.time()
        self.healthy = False
        self.cooldown_until = time.time() + cooldown_seconds
