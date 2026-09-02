# -*- coding: utf-8 -*-
"""browser_runtime Policy + Router 单元测试（P0-3 / P0-4）"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from browser_runtime.policy import (
    BrowserPolicyEngine, PolicyDecision, browser_policy_engine,
)
from browser_runtime.router import BrowserRouter, BrowserRouterError, browser_router
from browser_runtime.contract import BrowserContract


class TestPolicyEngine:
    def test_nav_allowed_domain(self):
        r = browser_policy_engine.check_navigation("https://github.com/zachary")
        assert r.decision == PolicyDecision.ALLOW

    def test_nav_unknown_domain_blocked(self):
        r = browser_policy_engine.check_navigation("https://evil-example.com/x")
        assert r.decision == PolicyDecision.SAFE_STOP

    def test_nav_non_http_blocked(self):
        r = browser_policy_engine.check_navigation("file:///etc/passwd")
        assert r.decision == PolicyDecision.SAFE_STOP

    def test_dangerous_action_blocked(self):
        assert browser_policy_engine.check_action("steal cookie").decision == PolicyDecision.SAFE_STOP
        assert browser_policy_engine.check_action("extract password").decision == PolicyDecision.SAFE_STOP
        assert browser_policy_engine.check_action("bypass captcha").decision == PolicyDecision.SAFE_STOP

    def test_delete_needs_confirm(self):
        assert browser_policy_engine.check_action("delete record").decision == PolicyDecision.NEED_CONFIRM

    def test_read_allowed(self):
        assert browser_policy_engine.check_action("read note").decision == PolicyDecision.ALLOW

    def test_regular_write_caution(self):
        assert browser_policy_engine.check_action("click button").decision == PolicyDecision.CAUTION

    def test_target_safe(self):
        assert browser_policy_engine.check_target("https://x.com/data.json").decision == PolicyDecision.ALLOW
        assert browser_policy_engine.check_target("note.txt").decision == PolicyDecision.ALLOW

    def test_target_dangerous(self):
        assert browser_policy_engine.check_target("https://x.com?token=abc").decision == PolicyDecision.SAFE_STOP

    def test_evaluate_full_gate(self):
        # 合法操作 + 合法目标
        r = browser_policy_engine.evaluate("read", url="https://github.com", target="search note")
        assert r.decision in (PolicyDecision.ALLOW, PolicyDecision.CAUTION)
        # 危险操作被拦
        r2 = browser_policy_engine.evaluate("extract cookie", target="cookie jar")
        assert r2.decision == PolicyDecision.SAFE_STOP


class TestRouter:
    def test_providers_registered(self):
        ps = browser_router.providers()
        assert "cdp" in ps
        assert "playwright" in ps

    def test_default_provider_is_cdp(self):
        assert browser_router.default_provider() == "cdp"

    def test_unknown_provider_raises(self):
        with pytest.raises(BrowserRouterError):
            browser_router.get("nonexistent")

    def test_get_cdp_returns_contract(self):
        inst = browser_router.get("cdp")
        assert hasattr(inst, "navigate") and hasattr(inst, "health")

    def test_get_with_fallback_no_fallback(self):
        # 默认不降级，未知 provider 报错
        with pytest.raises(BrowserRouterError):
            browser_router.get_with_fallback(preferred="nope", enable_fallback=False)

    def test_policy_gate_blocks(self):
        with pytest.raises(BrowserRouterError):
            browser_router.policy_gate("navigate", url="https://evil.com/x")

    def test_policy_gate_allows(self):
        r = browser_router.policy_gate("read", url="https://github.com")
        assert r.decision == PolicyDecision.ALLOW