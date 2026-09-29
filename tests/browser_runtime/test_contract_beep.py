# -*- coding: utf-8 -*-
"""browser_runtime Contract + BEEP 单元测试（P0-2）"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lumenis.system.browser.runtime.contract import (
    BrowserContract, BrowserState, FailureClass, FAILURE_POLICY,
    BEEPExecutor, BEEPTrace, BEEPStep, MAX_RETRY,
    browser_health_result, safe_browser_url, sanitize_runtime_value,
)
import json
from pathlib import Path


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

    def test_rate_limit_is_platform_risk(self):
        assert BrowserContract.classify_failure("HTTP 429 Too Many Requests") == FailureClass.PLATFORM_RISK

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

    def test_verify_fail_does_not_repeat_action(self):
        calls = {"count": 0}

        def action():
            calls["count"] += 1
            return True

        ex = BEEPExecutor(max_retry=3)
        trace = ex.run("click_save", action, verify_fn=lambda r: False)
        assert trace.result == "VERIFY_FAILED"
        assert trace.retry_count == 1
        assert calls["count"] == 1
        assert trace.failure_class == FailureClass.PAGE_CHANGED.value

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

    def test_transient_failure_is_retried_but_rate_limit_is_not(self):
        transient_calls = {"count": 0}

        def transient_action():
            transient_calls["count"] += 1
            if transient_calls["count"] == 1:
                raise RuntimeError("connection reset")
            return {"ok": True}

        transient_trace = BEEPExecutor(max_retry=3).run(
            "read", transient_action, retry_safe=True
        )
        assert transient_trace.result == "SUCCESS"
        assert transient_calls["count"] == 2

        limited_calls = {"count": 0}

        def limited_action():
            limited_calls["count"] += 1
            raise RuntimeError("429 too many requests; retry-after=60")

        limited_trace = BEEPExecutor(max_retry=3).run("read", limited_action)
        assert limited_trace.result == "VERIFY_FAILED"
        assert limited_trace.failure_class == FailureClass.PLATFORM_RISK.value
        assert limited_calls["count"] == 1

    def test_transient_action_is_not_retried_without_idempotency_opt_in(self):
        calls = {"count": 0}

        def action_may_have_landed():
            calls["count"] += 1
            raise RuntimeError("connection reset after submit")

        trace = BEEPExecutor(max_retry=3).run("submit", action_may_have_landed)
        assert trace.failure_class == FailureClass.TRANSIENT.value
        assert trace.retry_count == 1
        assert calls["count"] == 1

    def test_nested_token_fields_are_redacted_before_evidence(self):
        secret_payload = {
            "result": {
                "token": "private-token",
                "id_token": "private-id-token",
                "safe": "visible",
            }
        }
        assert sanitize_runtime_value(secret_payload) == {
            "result": {
                "token": "[redacted]",
                "id_token": "[redacted]",
                "safe": "visible",
            }
        }
        sanitized_text = sanitize_runtime_value(
            "id_token=private-id-token token=private-token"
        )
        assert "private-token" not in sanitized_text
        assert "private-id-token" not in sanitized_text

        captured = {}
        trace = BEEPExecutor(max_retry=1).run(
            "read",
            lambda: secret_payload,
            on_evidence=lambda evidence: captured.update(evidence),
        )
        assert trace.result == "SUCCESS"
        assert "private-token" not in str(captured)
        assert "private-id-token" not in str(captured)

    def test_session_failure_stops_without_retry(self):
        calls = {"count": 0}

        def action():
            calls["count"] += 1
            raise RuntimeError("401 session expired")

        trace = BEEPExecutor(max_retry=3).run("read", action)
        assert trace.result == "VERIFY_FAILED"
        assert trace.failure_class == FailureClass.SESSION.value
        assert calls["count"] == 1

    def test_failure_evidence_redacts_browser_secrets(self):
        secret_url = "ws://127.0.0.1:9222/devtools/browser/debugger-secret?token=secret-token"
        captured = {}
        trace = BEEPExecutor(max_retry=3).run(
            "read session=private-session",
            lambda: (_ for _ in ()).throw(RuntimeError(
                f"connection reset at {secret_url} Cookie: auth=private-cookie"
            )),
            url="https://www.rednote.com/item/123?token=private-token#session=private",
            on_evidence=lambda evidence: captured.update(evidence),
        )

        blob = str(captured).lower()
        assert trace.failure_class == FailureClass.TRANSIENT.value
        assert "debugger-secret" not in blob
        assert "private-session" not in blob
        assert "private-cookie" not in blob
        assert "private-token" not in blob

    def test_health_contract_hides_provider_endpoints_and_uses_business_state(self):
        secret = "ws://127.0.0.1:9222/devtools/browser/debugger-secret"
        health = browser_health_result("playwright", "disconnected", error=secret)

        assert health["display_name"] == {
            "zh-CN": "内部浏览器",
            "en": "Internal Browser",
            "ko": "내부 브라우저",
        }
        assert health["state"] == "unavailable"
        assert health["available"] is False
        assert health["diagnostics"]["provider"] == "playwright"
        assert health["diagnostics"]["connection_state"] == "disconnected"
        assert "debugger-secret" not in str(health)

        degraded = browser_health_result("playwright", "degraded")
        assert degraded["state"] == "degraded"
        assert degraded["available"] is False
        assert degraded["diagnostics"]["status"] == "degraded"

        repo = Path(__file__).parents[2]
        expected = {
            "zh-CN": json.loads((repo / "contracts/experience/i18n/zh-CN.delta.json").read_text(encoding="utf-8"))["delta"]["screen.SYS-06"],
            "en": json.loads((repo / "contracts/experience/i18n/en.delta.json").read_text(encoding="utf-8"))["delta"]["screen.SYS-06"],
            "ko": json.loads((repo / "contracts/experience/i18n/ko.delta.json").read_text(encoding="utf-8"))["delta"]["screen.SYS-06"],
        }
        assert health["display_name"] == expected

    def test_safe_browser_url_drops_credentials_query_and_debugger_id(self):
        assert safe_browser_url(
            "https://user:pass@www.rednote.com/item/123?token=secret#private"
        ) == "https://www.rednote.com/item/123"
        assert safe_browser_url(
            "ws://127.0.0.1:9222/devtools/browser/debugger-secret"
        ) == "ws://127.0.0.1:9222/[redacted]"

    def test_max_retry_constant(self):
        assert MAX_RETRY == 3

    def test_requested_retry_count_is_capped(self):
        assert BEEPExecutor(max_retry=999).max_retry == MAX_RETRY
        assert BEEPExecutor(max_retry=0).max_retry == 1
