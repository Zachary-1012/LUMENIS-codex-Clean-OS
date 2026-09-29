# -*- coding: utf-8 -*-
"""browser_runtime Policy + Router 单元测试（P0-3 / P0-4）"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lumenis.system.browser.runtime.policy import (
    BrowserPolicyEngine, PolicyDecision, browser_policy_engine,
)
from lumenis.system.browser.runtime.router import BrowserRouter, BrowserRouterError, browser_router
from lumenis.system.browser.runtime.contract import BrowserContract


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
        with pytest.raises(BrowserRouterError) as error:
            browser_router.policy_gate("navigate", url="https://evil.com/x?token=private-token")
        assert "private-token" not in str(error.value)
        assert "evil.com" not in str(error.value)

    def test_policy_gate_allows(self):
        r = browser_router.policy_gate("read", url="https://github.com")
        assert r.decision == PolicyDecision.ALLOW

    def test_registration_requires_the_full_runtime_contract(self):
        class IncompleteAdapter:
            def navigate(self, url):
                return {"ok": True}

        router = BrowserRouter()
        with pytest.raises(BrowserRouterError, match="BrowserContract methods"):
            router.register("incomplete", IncompleteAdapter)

    def test_opt_in_fallback_does_not_switch_a_disconnected_session(self):
        class DisconnectedAdapter(BrowserContract):
            def navigate(self, url, **kw):
                return {"ok": False}

            def snapshot(self, **kw):
                return {}

            def screenshot(self, path=None, **kw):
                return {"ok": False}

            def click(self, selector, **kw):
                return {"ok": False}

            def type_text(self, selector, text, **kw):
                return {"ok": False}

            def get_text(self, selector, **kw):
                return ""

            def wait_for(self, selector, timeout=10, **kw):
                return False

            def evaluate(self, js, **kw):
                return None

            def health(self):
                return {"state": "unavailable", "available": False}

            def close(self, **kw):
                return None

        class AvailableAdapter(BrowserContract):
            navigate = DisconnectedAdapter.navigate
            snapshot = DisconnectedAdapter.snapshot
            screenshot = DisconnectedAdapter.screenshot
            click = DisconnectedAdapter.click
            type_text = DisconnectedAdapter.type_text
            get_text = DisconnectedAdapter.get_text
            wait_for = DisconnectedAdapter.wait_for
            evaluate = DisconnectedAdapter.evaluate
            close = DisconnectedAdapter.close

            def health(self):
                return {"state": "available", "available": True}

        router = BrowserRouter()
        router.register("cdp", DisconnectedAdapter)
        router.register("playwright", AvailableAdapter)

        selected = router.get_with_fallback(
            preferred="cdp", fallback="playwright", enable_fallback=True
        )
        assert isinstance(selected, DisconnectedAdapter)
