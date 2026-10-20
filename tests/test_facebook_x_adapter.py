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
        assert FacebookAdapter._extract_metric(card, "span") is None


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


@pytest.mark.parametrize("label,text,count", [
    ("0 Likes", "0", 0),
    ("1,234 shares", "1,234", 1234),
    ("128条评论", "128", 128),
    ("0赞", "0", 0),
    ("Like", "2468", 2468),
    ("1.2K Likes", "1.2K", None),
    ("1.3万赞", "1.3万", None),
    ("1,2 shares", "1,2", None),
    ("-4 comments", "-4", None),
    ("01 comments", "01", None),
    ("2026 update 12", "unavailable", None),
    ("", "", None),
])
def test_facebook_observation_keeps_exact_zero_and_original_compact_or_invalid_display(label, text, count):
    from lumenis.adapters.facebook import FacebookAdapter

    card = MagicMock()
    card.query_selector.return_value = _x_element(text, **{"aria-label": label})
    actual, display = FacebookAdapter._extract_metric_observation(card, "metric")

    assert actual == count
    assert display == ({key: value for key, value in (("aria_label", label), ("text", text)) if value} or None)


def test_facebook_parser_preserves_long_body_and_metric_display_through_canonical_adapter():
    import hashlib
    from lumenis.adapters.facebook import FacebookAdapter
    from lumenis.system.collector.adapters.facebook import FacebookAdapter as MainFacebookAdapter
    from lumenis.system.collector.adapters.secondary_collection import _native_record

    body = "原文段落\n" * 160 + "最后一段仍属同一帖子，不得截断。"
    card = MagicMock()
    card.query_selector.side_effect = {
        '[data-ad-preview="message"], .x1iorvi4, .x1pi30zi': _x_element(body),
        'h3 a, .xt0psk2 a, [role="link"] span': _x_element("Author"),
        'a[href*="/posts/"], a[href*="/videos/"], a[href*="/photos/"]': _x_element(href="/page/posts/12345678901234567890"),
        'span[aria-label*="赞"], .x193iq5w span': _x_element("0", **{"aria-label": "0 Likes"}),
        'a[href*="comments"], span[aria-label*="评论"]': None,
        'span[aria-label*="分享"], a[href*="shares"]': _x_element("1.2K", **{"aria-label": "1.2K shares"}),
    }.get
    note = FacebookAdapter(cookie_string="test-only")._parse_facebook_card(card, None)
    item = MainFacebookAdapter(backend=object())._v4_notes_to_items([note])[0]
    native = _native_record(item, "facebook", "原文段落", "2026-10-08T06:00:00+08:00")

    assert note.content == item["content"] == native["content"] == body
    assert note.raw_data["body_sha256"] == hashlib.sha256(body.encode("utf-8")).hexdigest()
    assert note.raw_data["body_state"] == "VISIBLE_DOM_TEXT_COMPLETENESS_UNKNOWN"
    assert native["source_raw"]["metric_display"]["shares"] == {"aria_label": "1.2K shares", "text": "1.2K"}
    assert note.likes == item["likes"] == 0
    assert item["comments"] is item["shares"] is item["collects"] is None
    assert item["platform_content_id"] == ""  # No DOM-native ID was observed.
    assert item["publish_datetime"] == ""  # Capture time cannot fill publication time.


def test_facebook_main_mapping_does_not_invent_missing_backend_metrics():
    from types import SimpleNamespace
    from lumenis.system.collector.adapters.facebook import FacebookAdapter

    item = FacebookAdapter(backend=object())._v4_notes_to_items([
        SimpleNamespace(content="Body", raw_data={})
    ])[0]
    assert all(item[name] is None for name in ("likes", "comments", "collects", "shares"))


def test_facebook_comment_body_is_not_truncated_or_assigned_zero_metrics():
    from lumenis.adapters.facebook import FacebookAdapter

    body = "Comment source paragraph. " * 32
    comment = MagicMock()
    comment.query_selector.side_effect = {
        "h3 a, .xt0psk2 a": _x_element("Author"),
        '.x193iq5w, [dir="auto"]': _x_element(body),
        'span[aria-label*="赞"]': _x_element("1.2K", **{"aria-label": "1.2K Likes"}),
    }.get
    with patch("lumenis.adapters.human_browser.HumanBrowser") as browser, patch("lumenis.adapters.cookie_vault.inject_into_context"):
        page = browser.return_value.new_page.return_value
        page.query_selector.return_value = None
        page.query_selector_all.return_value = [comment]
        result = FacebookAdapter(cookie_string="test-only").comments("synthetic-post")

    assert result.success and len(result.notes) == 1
    note = result.notes[0]
    assert note.content == body.strip()
    assert note.likes is note.comments is note.collects is note.shares is None
    assert note.raw_data["metric_display"]["likes"] == {"aria_label": "1.2K Likes", "text": "1.2K"}


def test_x_parser_keeps_the_complete_observed_long_post():
    from lumenis.adapters.x_platform import XAdapter

    body = "Source text paragraph. " * 40 + "Final source paragraph."
    tweet = MagicMock()
    tweet.query_selector.side_effect = {'[data-testid="tweetText"]': _x_element(body)}.get
    tweet.query_selector_all.return_value = []
    note = XAdapter(cookie_string="test-only")._parse_x_tweet(tweet)
    assert note.content == body
    assert note.raw_data["tweet_id"] is None
    assert note.publish_date == ""


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


def test_main_facebook_adapter_constructs_search_and_detail_results():
    from types import SimpleNamespace
    from lumenis.system.collector.adapters.facebook import FacebookAdapter, CollectionStatus

    note = SimpleNamespace(
        raw_data={"post_id": "fb-post-123"}, title="Post", content="Body",
        author_id="page-1", author="Brand", publish_date="2026-10-05T10:00:00Z",
        url="https://www.facebook.com/page/posts/fb-post-123", likes=None,
        comments=None, collects=None, shares=None,
    )

    class Backend:
        def search(self, keyword, *, max_results):
            assert keyword == "brand update" and max_results == 12
            return SimpleNamespace(success=True, notes=[note], raw_count=1, error="")

        def detail(self, content_id):
            assert content_id == "fb-post-123"
            return SimpleNamespace(success=True, notes=[note], raw_count=1, error="")

        def comments(self, content_id, *, max_comments):
            return SimpleNamespace(success=True, notes=[], raw_count=0, error="")

        def creator(self, creator_id):
            return SimpleNamespace(success=True, notes=[], raw_count=0, error="")

    adapter = FacebookAdapter(backend=Backend())
    search = adapter.search("brand update", max_results=12)
    detail = adapter.detail("fb-post-123")
    comments = adapter.comments("fb-post-123")
    creator = adapter.creator("page-1")

    assert search.platform == detail.platform == comments.platform == creator.platform == "facebook"
    assert search.status == detail.status == CollectionStatus.SUCCESS
    assert search.items[0]["platform_content_id"] == "fb-post-123"
    assert search.items[0]["likes"] is None


def _facebook_detail_result(monkeypatch, article, final_url="https://www.facebook.com/page/posts/123456789"):
    from lumenis.adapters.facebook import FacebookAdapter

    page = MagicMock()
    page.url = final_url
    page.locator.return_value.inner_text.return_value = ""
    page.query_selector_all.return_value = [article]
    page.goto.return_value = None
    worker = MagicMock()
    worker.new_page.return_value = page
    with patch("lumenis.adapters.human_browser.HumanBrowser", return_value=worker), \
            patch("lumenis.adapters.human_browser.configured_readonly_worker_url", return_value="http://127.0.0.1:9223"), \
            patch("lumenis.adapters.cookie_vault.inject_into_context"):
        return FacebookAdapter(cookie_string="test-only").detail(final_url)


class _FacebookTextNode:
    def __init__(self, value="", *, href=None):
        self.value = value
        self.href = href

    def inner_text(self):
        return self.value

    def get_attribute(self, name):
        return self.href if name == "href" else None


class _FacebookDetailArticle:
    def __init__(self, body, preview, *, read_more=True, post_id="123456789"):
        self.body = body
        self.preview = preview
        self.expanded = False
        self.read_more = read_more
        self.anchor = _FacebookTextNode(href=f"/page/posts/{post_id}")
        self.button = _FacebookTextNode("See more")
        self.button.click = self._expand

    def _expand(self):
        self.expanded = True

    def query_selector_all(self, selector):
        if 'a[href*="/posts/"]' in selector:
            return [self.anchor]
        if selector == 'div[role="button"], button':
            return [self.button] if self.read_more else []
        return []

    def query_selector(self, selector):
        if selector == '[data-ad-preview="message"], [data-ad-comet-preview="message"]':
            return (_FacebookTextNode(self.body if self.expanded else self.body)
                    if self.body or self.expanded else None)
        if selector == '[data-ad-preview="message"], .x1iorvi4, .x1pi30zi':
            return _FacebookTextNode(self.body if self.expanded else self.preview)
        return None


def test_fix_098_facebook_detail_expands_and_binds_native_body_to_exact_post(monkeypatch):
    body = "Native post paragraph. " * 80 + "Full final paragraph."
    article = _FacebookDetailArticle(body, "Truncated search preview…")
    result = _facebook_detail_result(monkeypatch, article)
    assert result.success is True
    assert result.raw_count == 1
    note = result.notes[0]
    assert article.expanded is True
    assert note.content == body
    assert note.raw_data["body_kind"] == "NATIVE_POST_BODY"
    assert note.raw_data["body_status"] == "NATIVE_DETAIL_BODY_OBSERVED_COMPLETENESS_UNKNOWN"
    assert note.raw_data["body_state"] == "EXPANDED_NATIVE_ARTICLE_DOM_COMPLETENESS_UNKNOWN"
    assert note.raw_data["native_identity"] == {
        "post_id": "123456789", "requested_post_id": "123456789",
        "observed_post_id": "123456789", "status": "OBSERVED_MATCH",
        "locator": "article a[href]",
    }
    assert note.raw_data["body_sha256"]
    assert "Truncated search preview" not in note.content


def test_fix_098_facebook_search_preview_is_not_detail_when_native_body_missing(monkeypatch):
    article = _FacebookDetailArticle("", "Truncated search preview…", read_more=False)
    result = _facebook_detail_result(monkeypatch, article)
    assert result.success is False
    assert result.error == "DETAIL_NOT_RETURNED: NATIVE_POST_BODY_NOT_OBSERVED"
    assert result.diagnostics["body_status"] == "NATIVE_BODY_NOT_OBSERVED"
    assert result.notes == []


def test_fix_098_facebook_detail_rejects_other_post_article(monkeypatch):
    article = _FacebookDetailArticle("Other post body", "Other preview", post_id="999999999")
    result = _facebook_detail_result(monkeypatch, article)
    assert result.success is False
    assert result.error == "IDENTITY_MISMATCH: TARGET_ARTICLE_NOT_OBSERVED"
    assert result.notes == []


def test_fix_098_facebook_does_not_accept_preview_when_expansion_fails(monkeypatch):
    article = _FacebookDetailArticle("Full native body", "Truncated search preview…")

    def fail_click():
        raise RuntimeError("synthetic click failure")

    article.button.click = fail_click
    result = _facebook_detail_result(monkeypatch, article)
    assert result.success is False
    assert result.error == "DETAIL_NOT_RETURNED: NATIVE_POST_BODY_NOT_OBSERVED"
    assert result.notes == []


def test_fix_098_facebook_post_permalink_canonicalization_uses_exact_native_identity():
    from lumenis.adapters.facebook import FacebookAdapter

    path_identity = FacebookAdapter.observed_post_permalink(
        "https://m.facebook.com/page/posts/123456789?ref=search")
    query_identity = FacebookAdapter.observed_post_permalink(
        "https://facebook.com/permalink.php?story_fbid=123456789&id=987654321&ref=search")
    assert path_identity == {
        "post_id": "123456789",
        "url": "https://www.facebook.com/page/posts/123456789",
        "id_locator": "permalink_path.posts",
    }
    assert query_identity == {
        "post_id": "123456789",
        "url": "https://www.facebook.com/permalink.php?story_fbid=123456789&id=987654321",
        "id_locator": "permalink_query.story_fbid",
    }


def test_main_facebook_adapter_errors_keep_platform_and_health_unverified(monkeypatch):
    from lumenis.system.collector.adapters.facebook import FacebookAdapter, CollectionStatus

    class BrokenBackend:
        def search(self, *_args, **_kwargs):
            raise RuntimeError("collector unavailable")

    adapter = FacebookAdapter(backend=BrokenBackend())
    failed = adapter.search("brand")
    assert failed.platform == "facebook"
    assert failed.status == CollectionStatus.COLLECT_ERROR

    monkeypatch.setattr(
        "lumenis.adapters.cookie_vault.check_cookie_status",
        lambda platform: {"platform": platform, "has_auth_cookie": True,
                          "cookie_file": "private-cookie-path"},
    )
    health = adapter.health_check()
    assert health.platform == "facebook"
    assert health.status == CollectionStatus.NEED_VERIFY
    assert "private-cookie-path" not in health.message

    monkeypatch.setattr(
        "lumenis.adapters.cookie_vault.check_cookie_status",
        lambda platform: {"platform": platform, "has_auth_cookie": False},
    )
    missing = adapter.health_check()
    assert missing.platform == "facebook"
    assert missing.status == CollectionStatus.NOT_CONFIGURED
