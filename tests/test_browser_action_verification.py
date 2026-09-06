# -*- coding: utf-8 -*-
"""
ZBC AI Browser Runtime — Action Verification Tests
测试 Action→Expected→Actual→Verify→PASS/FAIL 闭环，以及失败 Recovery 链
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_browser_runtime import (
    AIBrowserRuntime,
    BrowserActionType,
    BrowserPageState,
    ExpectedState,
    ActionVerifier,
    VerificationResult,
    ActionResult,
    SessionStatus,
    FailureRecovery,
    FailureClass,
)


class TestExpectedState(unittest.TestCase):
    """测试 ExpectedState 数据类。"""

    def test_default_expected(self):
        exp = ExpectedState()
        self.assertIsNone(exp.url_contains)
        self.assertTrue(exp.loading_complete)

    def test_custom_expected(self):
        exp = ExpectedState(
            url_contains="/search",
            title_contains="搜索结果",
            element_visible="#results",
            text_present="找到",
        )
        self.assertEqual(exp.url_contains, "/search")
        self.assertEqual(exp.title_contains, "搜索结果")


class TestActionVerifier(unittest.TestCase):
    """测试 Action 验证器。"""

    def setUp(self):
        self.verifier = ActionVerifier()

    def test_url_contains_pass(self):
        expected = ExpectedState(url_contains="/dashboard")
        actual = {"url": "http://example.com/dashboard", "title": "Dashboard", "loading": False}
        result = self.verifier.verify(expected, actual)
        self.assertTrue(result.passed)
        self.assertEqual(len(result.differences), 0)

    def test_url_contains_fail(self):
        expected = ExpectedState(url_contains="/dashboard")
        actual = {"url": "http://example.com/login", "title": "Login", "loading": False}
        result = self.verifier.verify(expected, actual)
        self.assertFalse(result.passed)
        self.assertTrue(any("URL" in d for d in result.differences))

    def test_url_equals_pass(self):
        expected = ExpectedState(url_equals="http://example.com/page")
        actual = {"url": "http://example.com/page", "title": "Page", "loading": False}
        result = self.verifier.verify(expected, actual)
        self.assertTrue(result.passed)

    def test_title_contains_pass(self):
        expected = ExpectedState(title_contains="搜索结果")
        actual = {"url": "http://example.com", "title": "搜索结果 - 示例", "loading": False}
        result = self.verifier.verify(expected, actual)
        self.assertTrue(result.passed)

    def test_title_contains_fail(self):
        expected = ExpectedState(title_contains="搜索结果")
        actual = {"url": "http://example.com", "title": "首页", "loading": False}
        result = self.verifier.verify(expected, actual)
        self.assertFalse(result.passed)

    def test_element_visible_pass(self):
        expected = ExpectedState(element_visible="#submit")
        actual = {
            "url": "http://example.com", "title": "Form", "loading": False,
            "elements": {"#submit": {"visible": True, "text": "提交"}},
        }
        result = self.verifier.verify(expected, actual)
        self.assertTrue(result.passed)

    def test_element_visible_fail(self):
        expected = ExpectedState(element_visible="#submit")
        actual = {
            "url": "http://example.com", "title": "Form", "loading": False,
            "elements": {"#submit": {"visible": False}},
        }
        result = self.verifier.verify(expected, actual)
        self.assertFalse(result.passed)

    def test_input_value_pass(self):
        expected = ExpectedState(input_value=("#username", "testuser"))
        actual = {
            "url": "http://example.com", "title": "Login", "loading": False,
            "elements": {"#username": {"value": "testuser"}},
        }
        result = self.verifier.verify(expected, actual)
        self.assertTrue(result.passed)

    def test_input_value_fail(self):
        expected = ExpectedState(input_value=("#username", "testuser"))
        actual = {
            "url": "http://example.com", "title": "Login", "loading": False,
            "elements": {"#username": {"value": "wronguser"}},
        }
        result = self.verifier.verify(expected, actual)
        self.assertFalse(result.passed)

    def test_text_present_pass(self):
        expected = ExpectedState(text_present="操作成功")
        actual = {"url": "http://example.com", "title": "Result", "loading": False, "body_text": "操作成功！您的请求已处理。"}
        result = self.verifier.verify(expected, actual)
        self.assertTrue(result.passed)

    def test_text_absent_pass(self):
        expected = ExpectedState(text_absent="错误")
        actual = {"url": "http://example.com", "title": "OK", "loading": False, "body_text": "一切正常"}
        result = self.verifier.verify(expected, actual)
        self.assertTrue(result.passed)

    def test_text_absent_fail(self):
        expected = ExpectedState(text_absent="错误")
        actual = {"url": "http://example.com", "title": "Error", "loading": False, "body_text": "发生错误"}
        result = self.verifier.verify(expected, actual)
        self.assertFalse(result.passed)

    def test_loading_complete_fail(self):
        expected = ExpectedState(loading_complete=True)
        actual = {"url": "http://example.com", "title": "Loading", "loading": True}
        result = self.verifier.verify(expected, actual)
        self.assertFalse(result.passed)
        self.assertTrue(any("加载" in d for d in result.differences))

    def test_multiple_checks_all_pass(self):
        expected = ExpectedState(
            url_contains="/success",
            title_contains="成功",
            text_present="操作完成",
        )
        actual = {
            "url": "http://example.com/success",
            "title": "操作成功",
            "loading": False,
            "body_text": "操作完成！",
        }
        result = self.verifier.verify(expected, actual)
        self.assertTrue(result.passed)

    def test_multiple_checks_partial_fail(self):
        expected = ExpectedState(
            url_contains="/success",
            title_contains="成功",
        )
        actual = {
            "url": "http://example.com/success",
            "title": "错误页面",
            "loading": False,
        }
        result = self.verifier.verify(expected, actual)
        self.assertFalse(result.passed)
        self.assertEqual(len(result.differences), 1)  # 只有 title 失败

    def test_verification_result_structure(self):
        expected = ExpectedState(url_contains="/test")
        actual = {"url": "http://example.com/test", "title": "Test", "loading": False}
        result = self.verifier.verify(expected, actual)
        self.assertIsInstance(result, VerificationResult)
        self.assertIn("expected", result.to_dict())
        self.assertIn("actual", result.to_dict())
        self.assertIn("differences", result.to_dict())
        self.assertIn("timestamp", result.to_dict())

    def test_no_expected_always_pass(self):
        """没有期望状态时，验证器不应失败。"""
        expected = ExpectedState()
        actual = {"url": "http://example.com", "title": "Anything", "loading": False}
        result = self.verifier.verify(expected, actual)
        self.assertTrue(result.passed)


class TestActionVerificationWithRuntime(unittest.TestCase):
    """测试 Runtime 中的完整 Verification 闭环（mock Playwright）。"""

    def setUp(self):
        self.runtime = AIBrowserRuntime(session_id="verify_test")
        self.mock_page = MagicMock()
        self.mock_page.url = "http://example.com"
        self.mock_page.title.return_value = "Example"
        self.mock_page.evaluate.return_value = "text"
        self.runtime._page = self.mock_page
        self.runtime._context = MagicMock()
        self.runtime.status = SessionStatus.RUNNING

    def tearDown(self):
        self.runtime._closed = True

    def test_action_with_passing_verification(self):
        """Action 执行后状态符合期望 → PASS。"""
        self.mock_page.evaluate.side_effect = [
            "before", 2,   # before observe
            "after success", 5,  # after observe
        ]
        expected = ExpectedState(text_present="after success")
        result = self.runtime.execute_action(
            BrowserActionType.CLICK,
            selector="#btn",
            expected=expected,
        )
        self.assertTrue(result.success)
        self.assertEqual(result.result, ActionResult.PASS)
        self.assertIsNotNone(result.verification)
        self.assertTrue(result.verification.passed)

    def test_action_with_failing_verification(self):
        """Action 执行后状态不符合期望 → FAIL + Recovery。"""
        self.mock_page.evaluate.side_effect = [
            "before", 2,
            "wrong page", 3,
            "wrong page", 3,  # recovery retry
            "wrong page", 3,  # recovery retry 2
        ]
        expected = ExpectedState(text_present="success")
        result = self.runtime.execute_action(
            BrowserActionType.CLICK,
            selector="#btn",
            expected=expected,
        )
        # 验证失败后会尝试 Recovery，最终可能 FAIL 或 HUMAN_ESCALATION
        self.assertIn(result.result, [ActionResult.FAIL, ActionResult.HUMAN_ESCALATION, ActionResult.RETRY])
        self.assertIsNotNone(result.verification)
        if result.verification:
            self.assertFalse(result.verification.passed)

    def test_action_without_expected_passes(self):
        """没有期望状态时，执行无异常即 PASS。"""
        self.mock_page.evaluate.side_effect = ["before", 2, "after", 3]
        result = self.runtime.execute_action(
            BrowserActionType.CLICK,
            selector="#btn",
        )
        self.assertTrue(result.success)
        self.assertEqual(result.result, ActionResult.PASS)

    def test_evidence_recorded_for_action(self):
        """每个 Action 都应记录 Evidence。"""
        self.mock_page.evaluate.side_effect = ["before", 2, "after", 3]
        result = self.runtime.execute_action(
            BrowserActionType.CLICK,
            selector="#btn",
            task_id="task_001",
        )
        self.assertGreater(result.evidence_id, 0)

    def test_before_after_state_captured(self):
        """Action 执行前后状态应被捕获。"""
        self.mock_page.evaluate.side_effect = ["before text", 2, "after text", 3]
        result = self.runtime.execute_action(
            BrowserActionType.CLICK,
            selector="#btn",
        )
        self.assertIsNotNone(result.before_state)
        self.assertIsNotNone(result.after_state)
        self.assertIsInstance(result.before_state, BrowserPageState)
        self.assertIsInstance(result.after_state, BrowserPageState)


class TestFailureRecoveryChain(unittest.TestCase):
    """测试失败 Recovery 链。"""

    def setUp(self):
        self.recovery = FailureRecovery(max_retries=2)

    def test_classify_page_error(self):
        error = Exception("404 Not Found")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.PAGE_ERROR)

    def test_classify_selector_error(self):
        error = Exception("Timeout waiting for selector #btn")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.SELECTOR_ERROR)

    def test_classify_session_error(self):
        error = Exception("Session expired, need login")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.SESSION_ERROR)

    def test_classify_network_error(self):
        error = Exception("ECONNREFUSED connection failed")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.NETWORK_ERROR)

    def test_classify_timeout_error(self):
        error = Exception("Operation timed out after 30000ms")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.TIMEOUT_ERROR)

    def test_classify_permission_denied(self):
        error = Exception("Permission denied: readonly mode")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.PERMISSION_DENIED)

    def test_classify_unknown(self):
        error = Exception("Something weird happened")
        fc = self.recovery.classify_failure(error, {"url": "http://example.com"})
        self.assertEqual(fc, FailureClass.UNKNOWN_STATE)

    def test_recovery_strategies_for_selector_error(self):
        strategies = self.recovery.get_recovery_strategies(FailureClass.SELECTOR_ERROR)
        self.assertIn("retry_same_selector", strategies)
        self.assertIn("alternative_css_selector", strategies)
        self.assertIn("xpath_selector", strategies)
        self.assertIn("text_match", strategies)
        self.assertIn("coordinate_click", strategies)
        self.assertIn("human_escalation", strategies)

    def test_recovery_strategies_for_permission_denied(self):
        """权限拒绝应直接升级人工，不重试。"""
        strategies = self.recovery.get_recovery_strategies(FailureClass.PERMISSION_DENIED)
        self.assertEqual(strategies, ["human_escalation"])

    def test_recovery_strategies_for_session_error(self):
        strategies = self.recovery.get_recovery_strategies(FailureClass.SESSION_ERROR)
        self.assertIn("mark_need_verify", strategies)
        self.assertIn("human_escalation", strategies)

    def test_log_recovery(self):
        self.recovery.log_recovery("retry_same_selector", True, "clicked successfully")
        stats = self.recovery.get_recovery_stats()
        self.assertEqual(stats["total_attempts"], 1)
        self.assertEqual(stats["success_count"], 1)

    def test_circuit_breaker_in_recovery(self):
        self.assertIsNotNone(self.recovery.circuit_breaker)
        self.assertFalse(self.recovery.circuit_breaker.is_open())


if __name__ == "__main__":
    unittest.main()
