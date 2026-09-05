# -*- coding: utf-8 -*-
"""Facebook + X v4 adapter 单元测试（全 mock，不实际访问）"""
import sys, os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestFacebookAdapter:

    def test_init_auto_load_cookie(self):
        from v4_upgrade.adapters.facebook import FacebookAdapter
        with patch("v4_upgrade.adapters.facebook.FacebookAdapter._auto_load_cookie", return_value="c=1"):
            ad = FacebookAdapter()
            assert ad._cookie_string == "c=1"
            assert ad.platform_name == "facebook"

    def test_search_empty_keyword(self):
        from v4_upgrade.adapters.facebook import FacebookAdapter
        ad = FacebookAdapter(cookie_string="test")
        r = ad.search("", max_results=5)
        assert r.success is False
        assert "关键词为空" in r.error

    @patch("v4_upgrade.adapters.facebook.FacebookAdapter._search_browser")
    def test_search_success(self, mock_search):
        from v4_upgrade.adapters.facebook import FacebookAdapter, CollectedNote
        mock_search.return_value = MagicMock(success=True, notes=[
            CollectedNote(title="test", content="content", url="https://fb.com/1",
                          author="user", likes=10, comments=2, source_platform="facebook")
        ], raw_count=1, error="", duration_seconds=1.0)
        ad = FacebookAdapter(cookie_string="test")
        r = ad.search("test", max_results=5)
        assert r.success is True
        assert len(r.notes) == 1

    def test_auto_load_cookie_missing_file(self):
        from v4_upgrade.adapters.facebook import FacebookAdapter
        with patch("pathlib.Path.exists", return_value=False):
            result = FacebookAdapter._auto_load_cookie()
            assert result == ""

    def test_extract_metric(self):
        from v4_upgrade.adapters.facebook import FacebookAdapter
        card = MagicMock()
        card.query_selector.return_value = None
        assert FacebookAdapter._extract_metric(card, "span") == 0


class TestXAdapter:

    def test_init_auto_load_cookie(self):
        from v4_upgrade.adapters.x_platform import XAdapter
        with patch("v4_upgrade.adapters.x_platform.XAdapter._auto_load_cookie", return_value="c=1"):
            ad = XAdapter()
            assert ad._cookie_string == "c=1"
            assert ad.platform_name == "x"

    def test_search_empty_keyword(self):
        from v4_upgrade.adapters.x_platform import XAdapter
        ad = XAdapter(cookie_string="test")
        r = ad.search("", max_results=5)
        assert r.success is False
        assert "关键词为空" in r.error

    @patch("v4_upgrade.adapters.x_platform.XAdapter._search_browser")
    def test_search_success(self, mock_search):
        from v4_upgrade.adapters.x_platform import XAdapter, CollectedNote
        mock_search.return_value = MagicMock(success=True, notes=[
            CollectedNote(title="test tweet", content="content", url="https://x.com/1",
                          author="user", author_id="@user", likes=100, comments=5,
                          shares=10, source_platform="x")
        ], raw_count=1, error="", duration_seconds=1.0)
        ad = XAdapter(cookie_string="test")
        r = ad.search("test", max_results=5)
        assert r.success is True
        assert len(r.notes) == 1
        assert r.notes[0].author_id == "@user"

    def test_extract_metric_no_element(self):
        from v4_upgrade.adapters.x_platform import XAdapter
        tweet = MagicMock()
        tweet.query_selector.return_value = None
        assert XAdapter._extract_metric(tweet, '[data-testid="like"]') == 0

    def test_auto_load_cookie_list_format(self):
        from v4_upgrade.adapters.x_platform import XAdapter
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value='[{"name":"auth_token","value":"abc"}]'):
                result = XAdapter._auto_load_cookie()
                assert "auth_token=abc" in result
