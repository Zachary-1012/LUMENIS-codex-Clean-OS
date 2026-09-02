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
from typing import Optional, Type

from .contract import BrowserContract
from .policy import browser_policy_engine, PolicyDecision


class BrowserRouterError(Exception):
    pass


class BrowserRouter:
    """Provider 注册 + 选择 + 降级。"""

    def __init__(self):
        self._registry: dict[str, Type[BrowserContract]] = {}
        self._instances: dict[str, BrowserContract] = {}

    # ---------- 注册 ----------
    def register(self, name: str, adapter_cls: Type[BrowserContract]):
        """注册 Adapter 类。"""
        if not isinstance(name, str) or not name:
            raise BrowserRouterError("provider name must be non-empty string")
        if not callable(getattr(adapter_cls, "navigate", None)):
            raise BrowserRouterError(f"adapter {name} missing navigate() — not a BrowserContract")
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
        return os.environ.get("BRC_PROVIDER", "cdp").lower()

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
        """带降级的选择：enable_fallback=True 时，首选失败可降级到备用。

        默认 enable_fallback=False（保证生产稳定性，避免误切 Provider）。
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
            raise BrowserRouterError(f"policy safe_stop: {result.reason}")
        return result


# 全局实例
browser_router = BrowserRouter()