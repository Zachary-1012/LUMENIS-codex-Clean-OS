# -*- coding: utf-8 -*-
"""Failure Recovery Test（对齐 CTR-BROWSER-RUNTIME-P0-01）
覆盖：transient 有限重试（禁止无限重试）、policy 拒绝→platform_risk 冷却语义、
      BEEP 失败分类闭环、Safe Stop 语义。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pytest

from browser_runtime.contract import (
    BrowserContract, BrowserState, FailureClass, BEEPExecutor, MAX_RETRY,
)
from browser_runtime.policy import (
    BrowserPolicyEngine, PolicyDecision,
)


# ---------- FailureClass 分类 ----------
class TestFailureClassification:
    def test_transient_timeout(self):
        assert BrowserContract.classify_failure("connection timed out after 30s") == FailureClass.TRANSIENT

    def test_transient_network(self):
        assert BrowserContract.classify_failure("network unreachable") == FailureClass.TRANSIENT

    def test_session_expired(self):
        assert BrowserContract.classify_failure("session expired, please login") == FailureClass.SESSION

    def test_page_changed(self):
        assert BrowserContract.classify_failure("selector not found: #btn") == FailureClass.PAGE_CHANGED

    def test_policy_reject_is_platform_risk(self):
        """Policy Gate 拒绝 → platform_risk（Cooldown/Stop，不允许重试）"""
        assert BrowserContract.classify_failure(
            "policy safe_stop: domain not in whitelist: https://evil-example.com"
        ) == FailureClass.PLATFORM_RISK

    def test_captcha_is_platform_risk(self):
        assert BrowserContract.classify_failure("captcha required by platform") == FailureClass.PLATFORM_RISK

    def test_forbidden_is_permission(self):
        assert BrowserContract.classify_failure("403 forbidden") == FailureClass.PERMISSION


# ---------- BEEP 有限重试（禁止无限重试） ----------
class TestBEEPLimitedRetry:
    def test_transient_retry_then_success(self):
        """transient 失败后有限重试直至成功"""
        calls = {"n": 0}

        def action_fn():
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("connection timed out")
            return {"ok": True}

        ex = BEEPExecutor(max_retry=3)
        trace = ex.run("retry_test", action_fn)
        assert trace.result == "SUCCESS"
        assert calls["n"] == 3
        assert trace.retry_count == 3

    def test_no_infinite_retry(self):
        """持续失败时不超过 max_retry，返回 VERIFY_FAILED"""
        calls = {"n": 0}

        def action_fn():
            calls["n"] += 1
            raise RuntimeError("connection timed out")

        ex = BEEPExecutor(max_retry=MAX_RETRY)  # 3
        trace = ex.run("retry_fail", action_fn)
        assert trace.result == "VERIFY_FAILED"
        assert calls["n"] == MAX_RETRY  # 恰好 3 次，不无限
        assert trace.retry_count == MAX_RETRY

    def test_verify_failure_marks_failed(self):
        """verify 未通过 → VERIFY_FAILED"""
        ex = BEEPExecutor(max_retry=1)
        trace = ex.run("verify_test", lambda: {"done": True}, verify_fn=lambda r: r.get("done") is False)
        assert trace.result == "VERIFY_FAILED"
        assert trace.error is not None

    def test_precondition_skip(self):
        """precondition 未满足 → SKIP_PRECONDITION，不执行动作"""
        acted = {"n": 0}
        ex = BEEPExecutor(max_retry=3)
        trace = ex.run("pre_test", lambda: acted.__setitem__("n", 1), precondition_fn=lambda: False)
        assert trace.result == "SKIP_PRECONDITION"
        assert acted["n"] == 0

    def test_evidence_emitted(self):
        """每次执行结束回调 Evidence（无密钥）"""
        evidences = []
        ex = BEEPExecutor(max_retry=1)
        trace = ex.run("ev_test", lambda: {"ok": True}, on_evidence=lambda ev: evidences.append(ev))
        assert len(evidences) == 1
        ev = evidences[0]
        assert ev["action"] == "ev_test"
        assert "steps" in ev
        # Evidence 不含密钥类字段
        joined = str(ev).lower()
        assert "cookie" not in joined and "token" not in joined and "password" not in joined


# ---------- Policy 冷却语义（platform_risk → 不允许重试） ----------
class TestPolicyCooldownSemantics:
    def test_policy_reject_decision(self):
        eng = BrowserPolicyEngine()
        r = eng.check_navigation("https://evil-example.com")
        assert r.decision == PolicyDecision.SAFE_STOP
        assert "whitelist" in r.reason

    def test_safe_stop_maps_to_platform_risk(self):
        """Safe Stop 对应失败分类 = platform_risk（冷却/停止，而非重试）"""
        eng = BrowserPolicyEngine()
        r = eng.check_navigation("https://evil-example.com")
        assert r.decision == PolicyDecision.SAFE_STOP
        cls = BrowserContract.classify_failure(f"policy {r.decision.value}: {r.reason}")
        assert cls == FailureClass.PLATFORM_RISK
        # 处理策略：cooldown_or_stop（非 limited_retry）
        from browser_runtime.contract import FAILURE_POLICY
        assert FAILURE_POLICY[FailureClass.PLATFORM_RISK] == "cooldown_or_stop"

    def test_dangerous_action_safe_stop(self):
        """含危险模式（bypass/captcha）→ SAFE_STOP"""
        eng = BrowserPolicyEngine()
        r = eng.check_action("bypass captcha verification")
        assert r.decision == PolicyDecision.SAFE_STOP

    def test_confirm_action_needs_confirm(self):
        """delete 类操作 → NEED_CONFIRM（人工确认，非自动）"""
        eng = BrowserPolicyEngine()
        r = eng.check_action("delete row")
        assert r.decision == PolicyDecision.NEED_CONFIRM

    def test_whitelist_domain_allowed(self):
        eng = BrowserPolicyEngine()
        r = eng.check_navigation("https://www.xiaohongshu.com/explore")
        assert r.decision == PolicyDecision.ALLOW