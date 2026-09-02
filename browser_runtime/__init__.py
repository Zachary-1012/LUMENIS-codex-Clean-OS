# -*- coding: utf-8 -*-
"""Zachary OS AI · Browser Runtime（统一浏览器运行时层）
对齐 CTR-BROWSER-RUNTIME-P0-01：Browser Contract → Router → Adapter → Provider。
默认 Provider = CDP（保持现有驻场浏览器行为），环境变量 BRC_PROVIDER 可切换 Playwright。
"""
from __future__ import annotations

from .contract import (
    BrowserContract, BrowserState, FailureClass, FAILURE_POLICY,
    BEEPExecutor, BEEPTrace, BEEPStep, MAX_RETRY,
)
from .policy import (
    BrowserPolicyEngine, PolicyDecision, PolicyCheckResult, browser_policy_engine,
)
from .router import BrowserRouter, BrowserRouterError, browser_router

# 注册默认 Adapter（惰性 import，避免破坏现有启动）
try:
    from .adapters.cdp_adapter import CDPAdapter
    browser_router.register("cdp", CDPAdapter)
except Exception:
    pass
try:
    from .adapters.playwright_adapter import PlaywrightAdapter
    browser_router.register("playwright", PlaywrightAdapter)
except Exception:
    pass

__all__ = [
    "BrowserContract", "BrowserState", "FailureClass", "FAILURE_POLICY",
    "BEEPExecutor", "BEEPTrace", "BEEPStep", "MAX_RETRY",
    "BrowserPolicyEngine", "PolicyDecision", "PolicyCheckResult", "browser_policy_engine",
    "BrowserRouter", "BrowserRouterError", "browser_router",
]