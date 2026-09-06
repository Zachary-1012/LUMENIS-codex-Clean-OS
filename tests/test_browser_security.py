# -*- coding: utf-8 -*-
"""
ZBC AI Browser Runtime — Security Tests
测试敏感凭证不进入Context、Session隔离、只读保护
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_browser_runtime import (
    AIBrowserRuntime,
    BrowserActionType,
    ActionFirewall,
    sanitize_sensitive,
    sanitize_dict,
    SessionStatus,
    get_action_firewall,
)


class TestCredentialSanitization(unittest.TestCase):
    """测试敏感凭证脱敏（不进入 AI Context / Evidence / Logs）。"""

    def test_cookie_not_in_context(self):
        """Cookie 不应出现在进入 AI Context 的文本中。"""
        raw = "Page loaded. Cookie: session_id=abc123def456; user_pref=dark"
        sanitized = sanitize_sensitive(raw)
        self.assertNotIn("abc123def456", sanitized)
        self.assertIn("[REDACTED]", sanitized)

    def test_token_not_in_context(self):
        raw = "Auth: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
        sanitized = sanitize_sensitive(raw)
        self.assertNotIn("eyJhbGci", sanitized)

    def test_password_not_in_context(self):
        raw = 'User entered password=SuperSecret123! in the form'
        sanitized = sanitize_sensitive(raw)
        self.assertNotIn("SuperSecret123", sanitized)

    def test_api_key_not_in_context(self):
        raw = "api_key=sk-abc123def456ghi789jkl012mno345pqr"
        sanitized = sanitize_sensitive(raw)
        self.assertIn("[REDACTED]", sanitized)

    def test_oauth_not_in_context(self):
        raw = "oauth_token=oauth_abc123def456, client_secret=cs_xyz789"
        sanitized = sanitize_sensitive(raw)
        self.assertNotIn("oauth_abc123def456", sanitized)
        self.assertNotIn("cs_xyz789", sanitized)

    def test_phone_not_in_context(self):
        raw = "用户手机号: 13812345678, 备用: 13987654321"
        sanitized = sanitize_sensitive(raw)
        self.assertNotIn("13812345678", sanitized)
        self.assertNotIn("13987654321", sanitized)

    def test_id_card_not_in_context(self):
        raw = "身份证号: 110101199001011234"
        sanitized = sanitize_sensitive(raw)
        self.assertIn("[ID_CARD_REDACTED]", sanitized)

    def test_email_partial_redaction(self):
        raw = "联系邮箱: testuser@example.com"
        sanitized = sanitize_sensitive(raw)
        self.assertNotIn("testuser@", sanitized)
        self.assertIn("***@example.com", sanitized)

    def test_nested_dict_sanitization(self):
        data = {
            "level1": {
                "level2": {
                    "cookie": "session=abc123",
                    "safe": "hello",
                },
                "token": "xyz789",
            },
            "list": [{"password": "secret123"}, "safe text"],
        }
        result = sanitize_dict(data)
        self.assertNotIn("abc123", str(result))
        self.assertNotIn("xyz789", str(result))
        self.assertNotIn("secret123", str(result))
        self.assertEqual(result["level1"]["level2"]["safe"], "hello")
        self.assertEqual(result["list"][1], "safe text")

    def test_safe_content_preserved(self):
        """非敏感内容应被完整保留。"""
        raw = "This is a normal page about technology and science. No secrets here."
        sanitized = sanitize_sensitive(raw)
        self.assertEqual(sanitized, raw)

    def test_multiple_sensitive_in_one_text(self):
        raw = "cookie=abc123, token=xyz789, password=secret123, phone=13812345678"
        sanitized = sanitize_sensitive(raw)
        self.assertNotIn("abc123", sanitized)
        self.assertNotIn("xyz789", sanitized)
        self.assertNotIn("secret123", sanitized)
        self.assertNotIn("13812345678", sanitized)


class TestSessionIsolation(unittest.TestCase):
    """测试 AI Browser Session 与用户日常浏览 Session 隔离。"""

    def test_independent_profile_dir(self):
        """AI Session 应使用独立的 profile 目录（或独立 session_id）。"""
        runtime = AIBrowserRuntime()  # 不指定 session_id，自动生成
        # 每个 session 有唯一 ID，与其他 session 隔离
        self.assertIsNotNone(runtime.session_id)
        self.assertTrue(runtime.session_id.startswith("bs_"))
        # user_data_dir 未指定时为 None（启动时自动生成独立路径）
        self.assertIsNone(runtime.user_data_dir)
        runtime._closed = True

    def test_session_has_unique_id(self):
        r1 = AIBrowserRuntime()
        r2 = AIBrowserRuntime()
        self.assertNotEqual(r1.session_id, r2.session_id)
        r1._closed = True
        r2._closed = True

    def test_session_lifecycle_config(self):
        runtime = AIBrowserRuntime(
            session_id="lifecycle_test",
            idle_timeout=300,
            max_lifetime=1800,
        )
        self.assertEqual(runtime.idle_timeout, 300)
        self.assertEqual(runtime.max_lifetime, 1800)
        runtime._closed = True

    def test_session_close_releases_resources(self):
        runtime = AIBrowserRuntime(session_id="close_test")
        mock_page = MagicMock()
        mock_pw = MagicMock()
        runtime._page = mock_page
        runtime._playwright = mock_pw
        runtime.close()
        self.assertEqual(runtime.status, SessionStatus.CLOSED)
        self.assertTrue(runtime._closed)
        mock_page.close.assert_called_once()
        mock_pw.stop.assert_called_once()

    def test_session_manager_isolation(self):
        from ai_browser_runtime import BrowserSessionManager
        mgr = BrowserSessionManager()
        s1 = mgr.create_session()
        s2 = mgr.create_session()
        self.assertNotEqual(s1.session_id, s2.session_id)
        # 关闭一个不影响另一个
        mgr.close_session(s1.session_id)
        self.assertIsNotNone(mgr.get_session(s2.session_id))
        mgr.close_session(s2.session_id)


class TestReadonlyProtection(unittest.TestCase):
    """测试小红书等平台官方账号只读保护（Action Firewall）。"""

    def setUp(self):
        self.firewall = ActionFirewall(readonly_mode=True)

    def test_follow_button_blocked(self):
        allowed, reason = self.firewall.check_action(
            BrowserActionType.CLICK,
            target="点击关注按钮",
            selector=".follow-btn",
        )
        self.assertFalse(allowed)
        self.assertIn("只读", reason)

    def test_like_button_blocked(self):
        allowed, reason = self.firewall.check_action(
            BrowserActionType.CLICK,
            selector=".like-button",
            text="点赞",
        )
        self.assertFalse(allowed)

    def test_collect_button_blocked(self):
        allowed, reason = self.firewall.check_action(
            BrowserActionType.CLICK,
            target="收藏按钮",
            selector="#collect",
        )
        self.assertFalse(allowed)

    def test_comment_input_blocked(self):
        allowed, reason = self.firewall.check_action(
            BrowserActionType.INPUT,
            selector=".comment-input",
            text="评论内容",
        )
        self.assertFalse(allowed)

    def test_publish_blocked(self):
        allowed, reason = self.firewall.check_action(
            BrowserActionType.CLICK,
            target="发布按钮",
            selector=".publish-btn",
        )
        self.assertFalse(allowed)

    def test_logout_blocked(self):
        allowed, reason = self.firewall.check_action(
            BrowserActionType.CLICK,
            target="退出登录",
            selector="#logout",
        )
        self.assertFalse(allowed)

    def test_switch_account_blocked(self):
        allowed, reason = self.firewall.check_action(
            BrowserActionType.CLICK,
            target="切换账号",
            selector=".switch-account",
        )
        self.assertFalse(allowed)

    def test_upload_always_blocked(self):
        """上传操作始终需要 L3 审批。"""
        allowed, reason = self.firewall.check_action(
            BrowserActionType.UPLOAD,
            target="文件上传",
        )
        self.assertFalse(allowed)
        self.assertIn("L3", reason)

    def test_normal_navigate_allowed(self):
        allowed, reason = self.firewall.check_action(
            BrowserActionType.NAVIGATE,
            url="http://example.com",
        )
        self.assertTrue(allowed)

    def test_normal_scroll_allowed(self):
        allowed, reason = self.firewall.check_action(
            BrowserActionType.SCROLL,
            text="500",
        )
        self.assertTrue(allowed)

    def test_normal_observe_allowed(self):
        allowed, reason = self.firewall.check_action(
            BrowserActionType.OBSERVE,
        )
        self.assertTrue(allowed)

    def test_readonly_mode_disabled(self):
        """readonly_mode=False 时应允许写操作（但仍需 Permission Gate）。"""
        firewall = ActionFirewall(readonly_mode=False)
        allowed, reason = firewall.check_action(
            BrowserActionType.CLICK,
            selector=".follow-btn",
        )
        self.assertTrue(allowed)

    def test_blocked_log_recorded(self):
        self.firewall.check_action(
            BrowserActionType.CLICK,
            target="关注",
            selector=".follow",
        )
        stats = self.firewall.get_blocked_stats()
        self.assertGreater(stats["total_blocked"], 0)

    def test_runtime_enforces_firewall(self):
        """Runtime 执行 Action 时应经过 Firewall。"""
        runtime = AIBrowserRuntime(session_id="firewall_test")
        mock_page = MagicMock()
        mock_page.url = "http://example.com"
        mock_page.title.return_value = "Test"
        mock_page.evaluate.return_value = "text"
        runtime._page = mock_page
        runtime._context = MagicMock()
        runtime.status = SessionStatus.RUNNING

        result = runtime.execute_action(
            BrowserActionType.CLICK,
            selector=".follow-button",
            target="关注按钮",
        )
        self.assertFalse(result.success)
        self.assertIn("只读", result.error or "")
        # Firewall 拦截后不应执行实际点击
        mock_page.click.assert_not_called()
        runtime._closed = True


class TestSessionSecurityHardening(unittest.TestCase):
    """测试 Session 安全加固。"""

    def test_ai_is_not_password_holder(self):
        """AI 不应持有密码。Runtime 中不应存储密码字段。"""
        runtime = AIBrowserRuntime(session_id="no_password_test")
        # 检查 runtime 属性中没有密码相关存储
        runtime_attrs = dir(runtime)
        self.assertNotIn("password", runtime_attrs)
        self.assertNotIn("_password", runtime_attrs)
        runtime._closed = True

    def test_browser_is_not_permission_amplifier(self):
        """Browser 不应成为权限放大器。越权操作应被拦截。"""
        runtime = AIBrowserRuntime(session_id="no_amplify_test")
        mock_page = MagicMock()
        mock_page.url = "http://example.com"
        mock_page.title.return_value = "Test"
        mock_page.evaluate.return_value = "text"
        runtime._page = mock_page
        runtime._context = MagicMock()
        runtime.status = SessionStatus.RUNNING

        # 尝试执行写操作应被拦截
        result = runtime.execute_action(
            BrowserActionType.CLICK,
            selector=".follow-btn",
            target="关注",
        )
        self.assertFalse(result.success)
        runtime._closed = True

    def test_session_timeout_auto_close(self):
        """Session 超时应自动关闭。"""
        runtime = AIBrowserRuntime(
            session_id="timeout_test",
            idle_timeout=1,  # 1秒超时
        )
        runtime._page = MagicMock()
        runtime._playwright = MagicMock()
        runtime.last_activity = __import__('time').time() - 2  # 2秒前活动
        alive = runtime.is_alive()
        self.assertFalse(alive)
        self.assertEqual(runtime.status, SessionStatus.CLOSED)

    def test_max_lifetime_auto_close(self):
        """Session 超过最大生命周期应自动关闭。"""
        runtime = AIBrowserRuntime(
            session_id="maxlife_test",
            max_lifetime=1,  # 1秒最大生命周期
        )
        runtime._page = MagicMock()
        runtime._playwright = MagicMock()
        runtime.created_at = __import__('time').time() - 2  # 2秒前创建
        alive = runtime.is_alive()
        self.assertFalse(alive)


if __name__ == "__main__":
    unittest.main()
