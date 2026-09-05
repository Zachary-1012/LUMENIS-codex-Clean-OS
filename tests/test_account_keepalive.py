# -*- coding: utf-8 -*-
"""账号保活系统测试"""
import sys, os, json, tempfile
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestAccountKeepAlive:

    def test_init_all_platforms(self):
        from account_keepalive import AccountKeepAlive
        ka = AccountKeepAlive()
        assert len(ka.accounts) >= 8
        assert "xhs" in ka.accounts
        assert "douyin" in ka.accounts
        assert "instagram" in ka.accounts
        assert "x" in ka.accounts

    def test_check_no_cookie(self):
        from account_keepalive import AccountKeepAlive, KeepAliveConfig
        ka = AccountKeepAlive(KeepAliveConfig(platforms=["nonexistent"]))
        # 用临时路径测试无cookie
        ka.accounts["test"] = type('obj', (object,), {
            "platform": "test", "cookie_path": "/nonexistent/path.json",
            "health_url": "", "cookie_count": 0, "status": None,
            "last_check": 0, "last_refresh": 0, "expires_at": None, "note": ""
        })()
        # 直接测试_load_cookies
        cookies = ka._load_cookies("/nonexistent/path.json")
        assert cookies == []

    def test_check_xhs_cookie(self):
        from account_keepalive import AccountKeepAlive
        ka = AccountKeepAlive()
        account = ka.check_account("xhs")
        assert account.platform == "xhs"
        assert account.cookie_count >= 0
        assert account.status.value in ["active", "expiring", "expired", "no_cookie", "unknown"]

    def test_check_x_cookie(self):
        from account_keepalive import AccountKeepAlive
        ka = AccountKeepAlive()
        account = ka.check_account("x")
        assert account.platform == "x"
        # X cookie刚保存，应该有cookie
        assert account.cookie_count > 0

    def test_check_jiguang_cookie(self):
        from account_keepalive import AccountKeepAlive
        ka = AccountKeepAlive()
        account = ka.check_account("jiguang")
        assert account.platform == "jiguang"
        assert account.cookie_count > 0

    def test_status_summary(self):
        from account_keepalive import AccountKeepAlive
        ka = AccountKeepAlive()
        summary = ka.get_status_summary()
        assert "total" in summary
        assert "active" in summary
        assert "platforms" in summary
        assert len(summary["platforms"]) >= 8

    def test_get_login_url(self):
        from account_keepalive import AccountKeepAlive
        ka = AccountKeepAlive()
        assert ka.get_login_url("xhs") is not None
        assert ka.get_login_url("x") is not None
        assert ka.get_login_url("instagram") is not None
        assert ka.get_login_url("nonexistent") is None

    def test_external_redirect_default_false(self):
        from account_keepalive import AccountKeepAlive
        ka = AccountKeepAlive()
        assert ka.should_redirect_external("xhs") is False

    def test_cookie_expiry_detection(self):
        from account_keepalive import AccountKeepAlive
        import time
        ka = AccountKeepAlive()
        # 模拟已过期cookie
        expired_cookies = [{"name": "web_session", "value": "test", "expires": time.time() - 100}]
        expires = ka._check_cookie_expiry(expired_cookies)
        assert expires is not None
        assert expires < time.time()

    def test_platform_config_complete(self):
        from account_keepalive.manager import AccountKeepAlive
        for platform, cfg in AccountKeepAlive.PLATFORM_CONFIG.items():
            assert "name" in cfg
            assert "health_url" in cfg
            assert "key_cookies" in cfg
            assert "cookie_path" in cfg
            assert len(cfg["key_cookies"]) >= 1
