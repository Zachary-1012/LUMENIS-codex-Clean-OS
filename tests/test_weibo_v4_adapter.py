# -*- coding: utf-8 -*-
"""
微博 v4 adapter 单元测试（全 mock，不实际访问微博 API）
覆盖：成功/空结果/登录失效/风控/HTML清洗/日期解析/registry 注册
"""
import sys, os
import pytest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from v4_upgrade.adapters.weibo import WeiboAdapter


def _make_manager(logged_in=True, cookie="SUB=abc; SSOLoginState=xyz"):
    m = MagicMock()
    m.check_login_status.return_value = {"logged_in": logged_in}
    m.get_cookie_string.return_value = cookie
    return m


def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = status_code
    return resp


class TestWeiboAdapterSearch:

    @patch("v4_upgrade.adapters.weibo.requests.get")
    def test_search_success_returns_notes(self, mock_get):
        """成功搜索：返回标准化 CollectedNote。"""
        mock_get.return_value = _mock_response({
            "ok": 1,
            "data": {
                "cards": [
                    {"mblog": {
                        "mid": "12345", "id": "12345",
                        "text": "<a href='#'>#广州太古汇#</a> 今天开业了",
                        "created_at": "Tue Sep 03 12:00:00 +0800 2024",
                        "user": {"id": 999, "screen_name": "测试用户"},
                        "attitudes_count": 100, "comments_count": 20,
                        "reposts_count": 10, "source": "iPhone客户端",
                    }},
                    {"mblog": {
                        "mid": "67890", "id": "67890",
                        "text": "第二条微博",
                        "created_at": "Wed Sep 04 08:30:00 +0800 2024",
                        "user": {"id": 888, "screen_name": "另一个用户"},
                        "attitudes_count": 5, "comments_count": 1,
                        "reposts_count": 0,
                    }},
                ]
            }
        })
        ad = WeiboAdapter(manager=_make_manager())
        result = ad.search("广州太古汇", max_results=10)

        assert result.success is True
        assert result.raw_count == 2
        assert len(result.notes) == 2
        # HTML 标签应被清洗，保留话题文本
        assert "#广州太古汇#" in result.notes[0].content
        assert "<a" not in result.notes[0].content
        assert result.notes[0].author == "测试用户"
        assert result.notes[0].author_id == "999"
        assert result.notes[0].likes == 100
        assert result.notes[0].comments == 20
        assert result.notes[0].shares == 10
        assert result.notes[0].url == "https://m.weibo.cn/status/12345"
        assert result.notes[0].source_platform == "weibo"
        assert result.notes[0].publish_date.startswith("2024-09-03")

    @patch("v4_upgrade.adapters.weibo.requests.get")
    def test_search_empty_returns_success(self, mock_get):
        """正常无内容：success=True 但空。"""
        mock_get.return_value = _mock_response({"ok": 1, "data": {"cards": []}})
        ad = WeiboAdapter(manager=_make_manager())
        result = ad.search("不存在的词", max_results=5)
        assert result.success is True
        assert len(result.notes) == 0

    def test_search_not_logged_in(self):
        """登录失效：如实返回失败。"""
        ad = WeiboAdapter(manager=_make_manager(logged_in=False))
        result = ad.search("test", max_results=5)
        assert result.success is False
        assert "登录" in result.error

    def test_search_empty_cookie(self):
        """cookie 为空：失败。"""
        ad = WeiboAdapter(manager=_make_manager(cookie=""))
        result = ad.search("test", max_results=5)
        assert result.success is False

    @patch("v4_upgrade.adapters.weibo.requests.get")
    def test_search_api_error_login(self, mock_get):
        """API 返回登录失效。"""
        mock_get.return_value = _mock_response({"ok": 0, "msg": "请先登录"})
        ad = WeiboAdapter(manager=_make_manager())
        result = ad.search("test", max_results=5)
        assert result.success is False
        assert "登录" in result.error

    @patch("v4_upgrade.adapters.weibo.requests.get")
    def test_search_api_error_captcha(self, mock_get):
        """API 返回风控/验证。"""
        mock_get.return_value = _mock_response({"ok": 0, "msg": "需要验证"})
        ad = WeiboAdapter(manager=_make_manager())
        result = ad.search("test", max_results=5)
        assert result.success is False
        assert "验证" in result.error or "风控" in result.error

    def test_search_empty_keyword(self):
        ad = WeiboAdapter(manager=_make_manager())
        result = ad.search("", max_results=5)
        assert result.success is False
        assert "关键词" in result.error

    @patch("v4_upgrade.adapters.weibo.requests.get")
    def test_search_max_results_truncation(self, mock_get):
        cards = [{"mblog": {"mid": str(i), "text": f"微博{i}",
                            "created_at": "Tue Sep 03 12:00:00 +0800 2024",
                            "user": {"id": i, "screen_name": f"u{i}"}}}
                 for i in range(10)]
        mock_get.return_value = _mock_response({"ok": 1, "data": {"cards": cards}})
        ad = WeiboAdapter(manager=_make_manager())
        result = ad.search("test", max_results=3)
        assert len(result.notes) == 3

    @patch("v4_upgrade.adapters.weibo.requests.get")
    def test_search_exception_handled(self, mock_get):
        """网络异常：捕获返回失败，不崩溃。"""
        mock_get.side_effect = RuntimeError("网络中断")
        ad = WeiboAdapter(manager=_make_manager())
        result = ad.search("test", max_results=5)
        assert result.success is False
        assert "异常" in result.error


class TestWeiboAdapterHtmlClean:

    def test_clean_html_removes_tags(self):
        assert WeiboAdapter._clean_html("<p>hello</p>") == "hello"

    def test_clean_html_keeps_link_text(self):
        assert "#话题# 正文" in WeiboAdapter._clean_html("<a href='#'>#话题#</a> 正文")

    def test_clean_html_entities(self):
        assert WeiboAdapter._clean_html("a &amp; b") == "a & b"

    def test_clean_html_empty(self):
        assert WeiboAdapter._clean_html("") == ""
        assert WeiboAdapter._clean_html(None) == ""


class TestWeiboAdapterDate:

    def test_parse_standard_date(self):
        result = WeiboAdapter._parse_weibo_date("Tue Sep 03 12:00:00 +0800 2024")
        assert result.startswith("2024-09-03T12:00:00")

    def test_parse_none(self):
        assert WeiboAdapter._parse_weibo_date(None) == ""

    def test_parse_relative_returns_empty(self):
        """相对时间（刚刚/x分钟前）不臆造，返回空。"""
        assert WeiboAdapter._parse_weibo_date("刚刚") == ""
        assert WeiboAdapter._parse_weibo_date("5分钟前") == ""


class TestWeiboAdapterRegistry:

    def test_registry_can_get_weibo(self):
        from v4_upgrade.adapters.registry import registry, register_default_adapters
        register_default_adapters()
        ad = registry.get("weibo")
        assert ad is not None
        assert ad.platform_name == "weibo"
        assert ad.platform_display == "微博"

    def test_adapter_has_circuit_breaker(self):
        ad = WeiboAdapter(manager=_make_manager())
        assert ad.breaker is not None
        assert ad.rate_limiter is not None
        assert ad.metrics is not None
