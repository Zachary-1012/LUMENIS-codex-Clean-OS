# -*- coding: utf-8 -*-
"""Zachary OS AI · Browser Router（浏览器路由层）
对齐 CTR-BROWSER-RUNTIME-P0-01：Browser Contract → Router → Adapter → Provider。
Router 职责：
  - Provider 注册表（CDP / Playwright）
  - 按配置选择 Provider（feature flag 默认 CDP，不改变现有驻场浏览器行为）
  - 首选 Provider 失败时可降级到备用（可配置，默认不降级以保证稳定性）
  - 未知 Provider 报错

红线：不包含 ZBC 产品业务规则；不读写 Cookie/Token/密钥。
"""
from __future__ import annotations
import os
from typing import Any, Optional, Type

from .contract import BrowserContract, safe_browser_error
from .policy import browser_policy_engine, PolicyDecision


class BrowserRouterError(Exception):
    pass


class BrowserRouter:
    """Provider 注册 + 选择 + 降级。"""

    _REQUIRED_METHODS = (
        "navigate", "snapshot", "screenshot", "click", "type_text",
        "get_text", "wait_for", "evaluate", "health", "close",
    )

    def __init__(self):
        self._registry: dict[str, Type[BrowserContract]] = {}
        self._instances: dict[str, BrowserContract] = {}

    # ---------- 注册 ----------
    def register(self, name: str, adapter_cls: Type[BrowserContract]):
        """注册 Adapter 类。"""
        if not isinstance(name, str) or not name:
            raise BrowserRouterError("provider name must be non-empty string")
        missing = [
            method for method in self._REQUIRED_METHODS
            if not callable(getattr(adapter_cls, method, None))
            or getattr(adapter_cls, method, None) is getattr(BrowserContract, method, None)
        ]
        if missing:
            raise BrowserRouterError(
                f"adapter {name} is missing BrowserContract methods: {', '.join(missing)}"
            )
        self._registry[name.lower()] = adapter_cls

    def unregister(self, name: str):
        self._registry.pop(name.lower(), None)
        self._instances.pop(name.lower(), None)

    def providers(self) -> list[str]:
        return sorted(self._registry.keys())

    # ---------- 选择 ----------
    @staticmethod
    def default_provider() -> str:
        """默认 Provider：环境变量 BRC_PROVIDER 可覆盖；默认 cdp（保持现有驻场行为）。"""
        return os.environ.get("BRC_PROVIDER", "cdp").strip().lower() or "cdp"

    def get(self, name: Optional[str] = None, **adapter_kwargs) -> BrowserContract:
        """获取 Provider 实例（惰性创建）。未知 Provider 报错。"""
        provider = (name or self.default_provider()).lower()
        if provider not in self._registry:
            raise BrowserRouterError(
                f"unknown browser provider: {provider} (registered: {self.providers()})"
            )
        if provider not in self._instances:
            self._instances[provider] = self._registry[provider](**adapter_kwargs)
        return self._instances[provider]

    # ---------- 降级 ----------
    def get_with_fallback(self, preferred: Optional[str] = None,
                          fallback: Optional[str] = None,
                          enable_fallback: bool = False,
                          **adapter_kwargs) -> BrowserContract:
        """Select a registered provider, with opt-in fallback for an unknown name.

        A disconnected provider is returned as disconnected by ``health()``;
        this method never switches browser sessions after a live probe. CDP and
        Playwright may hold different authentication state, so silently moving
        between them would turn an unavailable session into a misleading result.
        """
        preferred = (preferred or self.default_provider()).lower()
        if preferred in self._registry:
            return self.get(preferred, **adapter_kwargs)
        if enable_fallback:
            fb = (fallback or "cdp").lower()
            if fb in self._registry:
                return self.get(fb, **adapter_kwargs)
            raise BrowserRouterError(f"no available provider (preferred={preferred}, fallback={fb})")
        raise BrowserRouterError(
            f"unknown browser provider: {preferred} (registered: {self.providers()})"
        )

    # ---------- 策略前置（统一入口） ----------
    @staticmethod
    def policy_gate(operation: str, url: Optional[str] = None, target: Any = None):
        """Router 层策略门：任何浏览器操作先过 Policy Engine。"""
        result = browser_policy_engine.evaluate(operation, url=url, target=target)
        if result.decision == PolicyDecision.SAFE_STOP:
            raise BrowserRouterError(safe_browser_error(f"policy safe_stop: {result.reason}"))
        return result


# 全局实例
browser_router = BrowserRouter()
