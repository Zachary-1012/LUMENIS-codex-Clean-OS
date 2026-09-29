# -*- coding: utf-8 -*-
"""Zachary OS AI · Browser Runtime（统一浏览器运行时层）
对齐 CTR-BROWSER-RUNTIME-P0-01：Browser Contract → Router → Adapter → Provider。
默认 Provider = CDP（保持现有驻场浏览器行为），环境变量 BRC_PROVIDER 可切换 Playwright。
"""
from __future__ import annotations

from .contract import (
    BrowserContract, BrowserState, BrowserAvailability, FailureClass, FAILURE_POLICY,
    BEEPExecutor, BEEPTrace, BEEPStep, MAX_RETRY,
    browser_health_result, safe_browser_error, safe_browser_url, sanitize_runtime_value,
)
from .policy import (
    BrowserPolicyEngine, PolicyDecision, PolicyCheckResult, browser_policy_engine,
)
from .router import BrowserRouter, BrowserRouterError, browser_router

# Register adapter classes explicitly. Provider dependencies remain lazy inside
# adapter construction, where their failures can be reported through health().
from .adapters.cdp_adapter import CDPAdapter
from .adapters.playwright_adapter import PlaywrightAdapter

browser_router.register("cdp", CDPAdapter)
browser_router.register("playwright", PlaywrightAdapter)

__all__ = [
    "BrowserContract", "BrowserState", "BrowserAvailability", "FailureClass", "FAILURE_POLICY",
    "BEEPExecutor", "BEEPTrace", "BEEPStep", "MAX_RETRY",
    "browser_health_result", "safe_browser_error", "safe_browser_url", "sanitize_runtime_value",
    "BrowserPolicyEngine", "PolicyDecision", "PolicyCheckResult", "browser_policy_engine",
    "BrowserRouter", "BrowserRouterError", "browser_router",
]
