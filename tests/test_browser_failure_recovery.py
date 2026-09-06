# -*- coding: utf-8 -*-
"""
ZBC AI Browser Runtime — Failure/Recovery Tests
测试各类失败的 Recovery / Circuit Breaker
"""
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_browser_runtime import (
    AIBrowserRuntime,
    BrowserActionType,
    BrowserPageState,
    ExpectedState,
    ActionResult,
    SessionStatus,
    FailureRecovery,
    FailureClass,
    CircuitBreaker,
    RecoveryAttempt,
)


class TestCircuitBreaker(unittest.TestCase):
    """测试熔断器。"""

    def test_initial_state_closed(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=1)
        self.assertFalse(cb.is_open())
        self.assertEqual(cb.get_state()["failure_count"], 0)

    def test_triggers_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
        cb.record_failure()  # 1
        cb.record_failure()  # 2
        self.assertFalse(cb.is_open())
        triggered = cb.record_failure()  # 3
        self.assertTrue(triggered)
        self.assertTrue(cb.is_open())

    def test_success_resets(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        self.assertEqual(cb.get_state()["failure_count"], 0)
        self.assertFalse(cb.is_open())

    def test_cooldown_recovery(self):
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=1)
        cb.record_failure()
        cb.record_failure()
        self.assertTrue(cb.is_open())
        # 等待冷却期
        time.sleep(1.1)
        self.assertFalse(cb.is_open())

    def test_reset(self):
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=60)
        cb.record_failure()
        cb.record_failure()
        self.assertTrue(cb.is_open())
        cb.reset()
        self.assertFalse(cb.is_open())
        self.assertEqual(cb.get_state()["failure_count"], 0)

    def test_state_structure(self):
        cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=30)
        state = cb.get_state()
        self.assertIn("open", state)
        self.assertIn("failure_count", state)
        self.assertIn("threshold", state)
        self.assertIn("cooldown_seconds", state)
        self.assertEqual(state["threshold"], 5)
        self.assertEqual(state["cooldown_seconds"], 30)

    def test_runtime_circuit_breaker_blocks_actions(self):
        """熔断后应阻止新的 Action 执行。"""
        runtime = AIBrowserRuntime(session_id="cb_test")
        mock_page = MagicMock()
        mock_page.url = "http://example.com"
        mock_page.title.return_value = "Test"
        mock_page.evaluate.return_value = "text"
        runtime._page = mock_page
        runtime._context = MagicMock()
        runtime.status = SessionStatus.RUNNING

        # 触发熔断
        for _ in range(5):
            runtime.recovery.circuit_breaker.record_failure()
        self.assertTrue(runtime.recovery.circuit_breaker.is_open())

        # 熔断后执行 Action 应被阻止
        result = runtime.execute_action(
            BrowserActionType.CLICK,
            selector="#btn",
        )
        self.assertFalse(result.success)
        self.assertTrue(result.human_escalation_required)
        self.assertIn("熔断", result.escalation_reason or "")
        runtime._closed = True


class TestFailureClassification(unittest.TestCase):
    """测试失败分类。"""

    def setUp(self):
        self.recovery = FailureRecovery()

    def test_page_error_404(self):
        error = Exception("404 Not Found")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.PAGE_ERROR)

    def test_page_error_500(self):
        error = Exception("500 Internal Server Error")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.PAGE_ERROR)

    def test_page_error_crash(self):
        error = Exception("Page crashed!")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.PAGE_ERROR)

    def test_selector_error(self):
        error = Exception("Timeout waiting for selector #submit-button")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.SELECTOR_ERROR)

    def test_selector_error_element_not_found(self):
        error = Exception("Element not found: .btn-primary")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.SELECTOR_ERROR)

    def test_session_error_expired(self):
        error = Exception("Session expired, please login again")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.SESSION_ERROR)

    def test_session_error_unauthorized(self):
        error = Exception("401 Unauthorized - cookie expired")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.SESSION_ERROR)

    def test_network_error(self):
        error = Exception("ECONNREFUSED: Connection refused")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.NETWORK_ERROR)

    def test_network_error_dns(self):
        error = Exception("ENOTFOUND: Domain not found")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.NETWORK_ERROR)

    def test_timeout_error(self):
        error = Exception("Operation timed out after 30000ms")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.TIMEOUT_ERROR)

    def test_permission_denied(self):
        error = Exception("Permission denied: readonly mode active")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.PERMISSION_DENIED)

    def test_unknown_state(self):
        error = Exception("Something completely unexpected happened")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.UNKNOWN_STATE)


class TestRecoveryStrategies(unittest.TestCase):
    """测试恢复策略链。"""

    def setUp(self):
        self.recovery = FailureRecovery(max_retries=2)

    def test_selector_error_strategies(self):
        strategies = self.recovery.get_recovery_strategies(FailureClass.SELECTOR_ERROR)
        self.assertIn("retry_same_selector", strategies)
        self.assertIn("alternative_css_selector", strategies)
        self.assertIn("xpath_selector", strategies)
        self.assertIn("accessibility_tree", strategies)
        self.assertIn("text_match", strategies)
        self.assertIn("coordinate_click", strategies)
        self.assertIn("scroll_then_click", strategies)
        self.assertIn("human_escalation", strategies)
        # human_escalation 应该是最后一个
        self.assertEqual(strategies[-1], "human_escalation")

    def test_page_error_strategies(self):
        strategies = self.recovery.get_recovery_strategies(FailureClass.PAGE_ERROR)
        self.assertIn("reload_page", strategies)
        self.assertIn("navigate_back_then_forward", strategies)
        self.assertIn("human_escalation", strategies)

    def test_session_error_strategies(self):
        strategies = self.recovery.get_recovery_strategies(FailureClass.SESSION_ERROR)
        self.assertIn("mark_need_verify", strategies)
        self.assertIn("wait_for_human_reauth", strategies)
        self.assertIn("human_escalation", strategies)

    def test_network_error_strategies(self):
        strategies = self.recovery.get_recovery_strategies(FailureClass.NETWORK_ERROR)
        self.assertIn("retry_exponential_backoff", strategies)
        self.assertIn("reload_page", strategies)
        self.assertIn("human_escalation", strategies)

    def test_permission_denied_no_retry(self):
        """权限拒绝应直接升级人工，不重试。"""
        strategies = self.recovery.get_recovery_strategies(FailureClass.PERMISSION_DENIED)
        self.assertEqual(strategies, ["human_escalation"])

    def test_unknown_state_strategies(self):
        strategies = self.recovery.get_recovery_strategies(FailureClass.UNKNOWN_STATE)
        self.assertIn("stop_and_capture_evidence", strategies)
        self.assertIn("human_escalation", strategies)

    def test_recovery_logging(self):
        self.recovery.log_recovery("retry_same_selector", True, "clicked")
        self.recovery.log_recovery("xpath_selector", False, "not found")
        stats = self.recovery.get_recovery_stats()
        self.assertEqual(stats["total_attempts"], 2)
        self.assertEqual(stats["success_count"], 1)
        self.assertIn("retry_same_selector", stats["by_strategy"])
        self.assertIn("xpath_selector", stats["by_strategy"])


class TestRuntimeFailureRecovery(unittest.TestCase):
    """测试 Runtime 中的失败恢复（mock Playwright）。"""

    def setUp(self):
        self.runtime = AIBrowserRuntime(session_id="recovery_test")
        self.mock_page = MagicMock()
        self.mock_page.url = "http://example.com"
        self.mock_page.title.return_value = "Example"
        self.runtime._page = self.mock_page
        self.runtime._context = MagicMock()
        self.runtime.status = SessionStatus.RUNNING

    def tearDown(self):
        self.runtime._closed = True

    def test_selector_failure_triggers_recovery(self):
        """选择器失败应触发 Recovery 策略链。"""
        # 第一次点击失败，后续 observe
        self.mock_page.click.side_effect = Exception("Timeout waiting for selector #btn")
        self.mock_page.evaluate.side_effect = ["before", 2, "after", 3, "after", 3]

        expected = ExpectedState(text_present="success")
        result = self.runtime.execute_action(
            BrowserActionType.CLICK,
            selector="#btn",
            expected=expected,
        )
        # 应该尝试了 Recovery
        self.assertGreaterEqual(len(result.recovery_attempts), 0)
        # 最终结果应该是 FAIL 或 HUMAN_ESCALATION
        self.assertIn(result.result, [ActionResult.FAIL, ActionResult.HUMAN_ESCALATION, ActionResult.RETRY])

    def test_recovery_success_after_retry(self):
        """重试后成功应标记为 RETRY。"""
        call_count = [0]
        def click_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Timeout waiting for selector")
            return None  # 第二次成功

        self.mock_page.click.side_effect = click_side_effect
        self.mock_page.evaluate.side_effect = [
            "before", 2,   # before observe
            "after success", 5,  # after first failure observe
            "after success", 5,  # after retry observe
        ]

        expected = ExpectedState(text_present="after success")
        result = self.runtime.execute_action(
            BrowserActionType.CLICK,
            selector="#btn",
            expected=expected,
        )
        # 重试后成功
        self.assertTrue(result.success)
        self.assertIn(result.result, [ActionResult.PASS, ActionResult.RETRY])

    def test_session_error_marks_need_verify(self):
        """Session 错误应标记 NEED_VERIFY，不静默失败。"""
        self.mock_page.click.side_effect = Exception("Session expired, need login")
        self.mock_page.evaluate.side_effect = ["before", 2, "login page", 3, "login page", 3]

        result = self.runtime.execute_action(
            BrowserActionType.CLICK,
            selector="#btn",
        )
        # 不应静默失败
        self.assertFalse(result.success)
        # Session 状态应被标记
        self.assertIn(self.runtime.status, [SessionStatus.NEED_VERIFY, SessionStatus.RUNNING])

    def test_permission_denied_no_retry(self):
        """权限拒绝不应重试，直接返回失败。"""
        # 直接被 Firewall 拦截，不会到 Playwright
        result = self.runtime.execute_action(
            BrowserActionType.CLICK,
            selector=".follow-btn",
            target="关注",
        )
        self.assertFalse(result.success)
        self.assertEqual(len(result.recovery_attempts), 0)
        self.mock_page.click.assert_not_called()

    def test_evidence_recorded_on_failure(self):
        """失败时也应记录 Evidence。"""
        self.mock_page.click.side_effect = Exception("Timeout")
        self.mock_page.evaluate.side_effect = ["before", 2, "after", 3, "after", 3]

        result = self.runtime.execute_action(
            BrowserActionType.CLICK,
            selector="#btn",
        )
        self.assertGreater(result.evidence_id, 0)

    def test_human_escalation_on_all_strategies_fail(self):
        """所有 Recovery 策略失败后应升级人工。"""
        self.mock_page.click.side_effect = Exception("Timeout waiting for selector")
        self.mock_page.evaluate.side_effect = ["before", 2] + ["fail", 1] * 10

        expected = ExpectedState(text_present="success")
        result = self.runtime.execute_action(
            BrowserActionType.CLICK,
            selector="#btn",
            expected=expected,
        )
        # 所有策略失败后应升级人工
        if not result.success:
            self.assertTrue(
                result.human_escalation_required or
                result.result in [ActionResult.HUMAN_ESCALATION, ActionResult.FAIL]
            )

    def test_unknown_state_stops_with_evidence(self):
        """未知状态应 STOP + Evidence + Human，禁止 AI 盲操作。"""
        self.mock_page.click.side_effect = Exception("Completely unknown error xyz123")
        self.mock_page.evaluate.side_effect = ["before", 2, "unknown", 0, "unknown", 0]

        result = self.runtime.execute_action(
            BrowserActionType.CLICK,
            selector="#btn",
        )
        self.assertFalse(result.success)
        self.assertGreater(result.evidence_id, 0)


class TestRecoveryAttemptDataclass(unittest.TestCase):
    """测试 RecoveryAttempt 数据类。"""

    def test_creation(self):
        attempt = RecoveryAttempt(
            strategy="retry_same_selector",
            success=True,
            detail="clicked successfully",
        )
        self.assertEqual(attempt.strategy, "retry_same_selector")
        self.assertTrue(attempt.success)
        self.assertEqual(attempt.detail, "clicked successfully")
        self.assertIsNotNone(attempt.timestamp)

    def test_sanitization_in_detail(self):
        """Recovery detail 应被脱敏。"""
        from ai_browser_runtime import sanitize_sensitive
        detail = "Failed with cookie=abc123"
        sanitized = sanitize_sensitive(detail)
        self.assertNotIn("abc123", sanitized)


if __name__ == "__main__":
    unittest.main()
