# -*- coding: utf-8 -*-
"""Facebook + X v4 adapter 单元测试（全 mock，不实际访问）"""
import sys, os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestFacebookAdapter:

    def test_init_auto_load_cookie(self):
        from lumenis.adapters.facebook import FacebookAdapter
        with patch("lumenis.adapters.facebook.FacebookAdapter._auto_load_cookie", return_value="c=1"):
            ad = FacebookAdapter()
            assert ad._cookie_string == "c=1"
            assert ad.platform_name == "facebook"

    def test_search_empty_keyword(self):
        from lumenis.adapters.facebook import FacebookAdapter
        ad = FacebookAdapter(cookie_string="test")
        r = ad.search("", max_results=5)
        assert r.success is False
        assert "关键词为空" in r.error

    @patch("lumenis.adapters.facebook.FacebookAdapter._search_browser")
    def test_search_success(self, mock_search):
        from lumenis.adapters.facebook import FacebookAdapter, CollectedNote
        mock_search.return_value = MagicMock(success=True, notes=[
            CollectedNote(title="test", content="content", url="https://fb.com/1",
                          author="user", likes=10, comments=2, source_platform="facebook")
        ], raw_count=1, error="", duration_seconds=1.0)
        ad = FacebookAdapter(cookie_string="test")
        r = ad.search("test", max_results=5)
        assert r.success is True
        assert len(r.notes) == 1

    def test_auto_load_cookie_missing_file(self):
        from lumenis.adapters.facebook import FacebookAdapter
        with patch("pathlib.Path.exists", return_value=False):
            result = FacebookAdapter._auto_load_cookie()
            assert result == ""

    def test_extract_metric(self):
        from lumenis.adapters.facebook import FacebookAdapter
        card = MagicMock()
        card.query_selector.return_value = None
        assert FacebookAdapter._extract_metric(card, "span") == 0


class TestXAdapter:

    def test_init_auto_load_cookie(self):
        from lumenis.adapters.x_platform import XAdapter
        with patch("lumenis.adapters.x_platform.XAdapter._auto_load_cookie", return_value="c=1"):
            ad = XAdapter()
            assert ad._cookie_string == "c=1"
            assert ad.platform_name == "x"

    def test_search_empty_keyword(self):
        from lumenis.adapters.x_platform import XAdapter
        ad = XAdapter(cookie_string="test")
        r = ad.search("", max_results=5)
        assert r.success is False
        assert "关键词为空" in r.error

    @patch("lumenis.adapters.x_platform.XAdapter._search_browser")
    def test_search_success(self, mock_search):
        from lumenis.adapters.x_platform import XAdapter, CollectedNote
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
        from lumenis.adapters.x_platform import XAdapter
        tweet = MagicMock()
        tweet.query_selector.return_value = None
        assert XAdapter._extract_metric(tweet, '[data-testid="like"]') is None

    def test_auto_load_cookie_list_format(self):
        """_auto_load_cookie 通过 cookie_vault.to_cookie_string 将 {name,value} 列表格式化为 name=value 字符串。

        直接 mock cookie_vault.load_cookies 返回测试 cookie 列表，避免依赖真实 cookie 文件。
        （历史版本 mock Path.read_text 无效，因为 load_cookies 内部用 open(p) 而非 p.read_text()）
        """
        from lumenis.adapters.x_platform import XAdapter
        with patch("lumenis.adapters.cookie_vault.load_cookies",
                   return_value=[{"name": "auth_token", "value": "abc"}]):
            result = XAdapter._auto_load_cookie()
            assert "auth_token=abc" in result


def _x_element(text="", **attributes):
    element = MagicMock()
    element.inner_text.return_value = text
    element.get_attribute.side_effect = attributes.get
    return element


def test_x_parser_preserves_native_id_explicit_zero_unknown_counts_and_publish_time():
    from lumenis.adapters.x_platform import XAdapter

    tweet = MagicMock()
    tweet.query_selector.side_effect = {
        '[data-testid="tweetText"]': _x_element("A source post"),
        'a[href*="/status/"]': _x_element(href="/brand/status/12345678901234567890?s=20"),
        '[data-testid="like"]': _x_element(**{"aria-label": "0 Likes"}),
        '[data-testid="reply"]': _x_element(**{"aria-label": "unavailable"}),
        '[data-testid="retweet"]': _x_element("1.2K", **{"aria-label": "1.2K Reposts"}),
        "time": _x_element(**{"datetime": "2026-09-28T01:02:03Z"}),
    }.get
    tweet.query_selector_all.return_value = []

    note = XAdapter(cookie_string="test-only")._parse_x_tweet(tweet)

    assert note.raw_data["tweet_id"] == "12345678901234567890"
    assert note.likes == 0
    assert note.comments is None
    assert note.shares is None
    assert note.collects is None
    assert note.publish_date == "2026-09-28T01:02:03Z"
    assert note.raw_data["metric_display"]["shares"] == {
        "aria_label": "1.2K Reposts", "text": "1.2K",
    }


def test_x_metric_parser_falls_back_to_text_and_rejects_approximate_or_bad_grouping():
    from lumenis.adapters.x_platform import XAdapter

    def extract(label, text):
        tweet = MagicMock()
        tweet.query_selector.return_value = _x_element(text, **{"aria-label": label})
        return XAdapter._extract_metric_observation(tweet, "metric")

    approximate, approximate_display = extract("1.2K Likes", "1.2K")
    exact_grouped, _ = extract("Like", "1,234")
    malformed_grouped, malformed_display = extract("1,2 Likes", "1,2")

    assert approximate is None
    assert approximate_display["aria_label"] == "1.2K Likes"
    assert exact_grouped == 1234
    assert malformed_grouped is None
    assert malformed_display["aria_label"] == "1,2 Likes"


def test_x_parser_keeps_missing_identity_and_publish_time_unknown():
    from lumenis.adapters.x_platform import XAdapter

    tweet = MagicMock()
    tweet.query_selector.side_effect = {
        '[data-testid="tweetText"]': _x_element("Post without a status link"),
    }.get
    tweet.query_selector_all.return_value = []
    note = XAdapter(cookie_string="test-only")._parse_x_tweet(tweet)

    assert note.raw_data["tweet_id"] is None
    assert note.publish_date == ""
    assert note.likes is None


def test_main_x_adapter_maps_id_and_unknown_counts_without_zero_defaults():
    from types import SimpleNamespace
    from lumenis.system.collector.adapters.x_platform import XAdapter

    note = SimpleNamespace(
        raw_data={"tweet_id": "12345678901234567890"},
        title="Post", content="Body", author_id="@brand", author="Brand",
        publish_date="", url="https://x.com/brand/status/12345678901234567890",
        likes=0, comments=None, collects=None, shares=None,
    )

    item = XAdapter(backend=object())._v4_notes_to_items([note])[0]

    assert item["platform_content_id"] == "12345678901234567890"
    assert item["likes"] == 0
    assert item["comments"] is None
    assert item["collects"] is None
    assert item["shares"] is None
    assert item["publish_datetime"] == ""


def test_main_x_adapter_health_check_uses_vault_metadata(monkeypatch):
    from lumenis.system.collector.adapters.x_platform import XAdapter, CollectionStatus

    monkeypatch.setattr(
        "lumenis.adapters.cookie_vault.check_cookie_status",
        lambda platform: {"platform": platform, "has_auth_cookie": True},
    )

    result = XAdapter(backend=object()).health_check()

    assert result.status == CollectionStatus.NEED_VERIFY
    assert "need verification" in result.message

    monkeypatch.setattr(
        "lumenis.adapters.cookie_vault.check_cookie_status",
        lambda platform: {"platform": platform, "has_auth_cookie": False},
    )
    missing = XAdapter(backend=object()).health_check()

    assert missing.status == CollectionStatus.NOT_CONFIGURED
    assert missing.platform == "x"
    assert "metadata missing" in missing.message
