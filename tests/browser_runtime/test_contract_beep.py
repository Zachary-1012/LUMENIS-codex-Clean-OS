# -*- coding: utf-8 -*-
"""browser_runtime Contract + BEEP 单元测试（P0-2）"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from browser_runtime.contract import (
    BrowserContract, BrowserState, FailureClass, FAILURE_POLICY,
    BEEPExecutor, BEEPTrace, BEEPStep, MAX_RETRY,
)


class TestBrowserState:
    def test_success_path_order(self):
        seq = BrowserContract.state_sequence()
        assert seq[0] == "INIT"
        assert seq[-1] == "SUCCESS"
        assert len(seq) == 8
        assert "ACTION" in seq and "VERIFY" in seq

    def test_failure_states_present(self):
        assert BrowserState.VERIFY_FAILED.value == "VERIFY_FAILED"
        assert BrowserState.CLASSIFY_FAILURE.value == "CLASSIFY_FAILURE"


class TestFailureClassification:
    def test_transient(self):
        assert BrowserContract.classify_failure("connection reset by peer") == FailureClass.TRANSIENT

    def test_session(self):
        assert BrowserContract.classify_failure("session expired, please login") == FailureClass.SESSION

    def test_page_changed(self):
        assert BrowserContract.classify_failure("no such element found") == FailureClass.PAGE_CHANGED

    def test_permission(self):
        assert BrowserContract.classify_failure("permission denied") == FailureClass.PERMISSION

    def test_platform_risk(self):
        assert BrowserContract.classify_failure("account blocked by risk control") == FailureClass.PLATFORM_RISK

    def test_unknown(self):
        assert BrowserContract.classify_failure("something completely weird") == FailureClass.UNKNOWN

    def test_failure_policy_mapping(self):
        # 每个失败分类都有处理策略，且不无限重试
        for fc in FailureClass:
            assert fc in FAILURE_POLICY
            assert "retry" not in FAILURE_POLICY[fc] or "limited" in FAILURE_POLICY[fc]


class TestBEEPExecutor:
    def test_success_full_trace(self):
        ex = BEEPExecutor(max_retry=2)
        trace = ex.run("click_save", lambda: "clicked", verify_fn=lambda r: r == "clicked")
        assert trace.result == "SUCCESS"
        steps = [s["step"] for s in trace.steps]
        assert "plan" in steps and "action" in steps and "post_condition" in steps
        assert "evidence" in steps and "decision" in steps

    def test_verify_fail_limited_retry(self):
        ex = BEEPExecutor(max_retry=3)
        trace = ex.run("click_save", lambda: True, verify_fn=lambda r: False)
        assert trace.result == "VERIFY_FAILED"
        assert trace.retry_count == 3  # 有限重试，不无限

    def test_precondition_skip(self):
        ex = BEEPExecutor(max_retry=2)
        trace = ex.run("op", lambda: True, precondition_fn=lambda: False)
        assert trace.result == "SKIP_PRECONDITION"
        assert trace.retry_count == 0

    def test_evidence_callback_no_secrets(self):
        ex = BEEPExecutor(max_retry=1)
        captured = {}
        def on_ev(ev):
            captured.update(ev)
        ex.run("click_save", lambda: True, verify_fn=lambda r: True,
               url="https://x.com/note/1", provider="cdp", on_evidence=on_ev)
        assert captured["action"] == "click_save"
        assert captured["result"] == "SUCCESS"
        blob = str(captured)
        # 禁止任何密钥特征
        for secret in ("cookie=", "token=", "password=", "session=", "Bearer "):
            assert secret.lower() not in blob.lower()

    def test_max_retry_constant(self):
        assert MAX_RETRY == 3