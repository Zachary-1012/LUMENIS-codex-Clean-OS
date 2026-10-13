# -*- coding: utf-8 -*-
"""Facebook + X v4 adapter 单元测试（全 mock，不实际访问）"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

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
        from lumenis.adapters.facebook import CollectedNote, FacebookAdapter
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
        from lumenis.adapters.x_platform import CollectedNote, XAdapter
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
    element.evaluate.return_value = False
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


def test_facebook_search_parser_keeps_long_text_marked_as_preview_and_preserves_metrics():
    import hashlib
    from types import SimpleNamespace

    from lumenis.adapters.facebook import FacebookAdapter
    from lumenis.system.collector.adapters.facebook import (
        FacebookAdapter as MainFacebookAdapter,
    )

    body = "原文段落\n" * 160 + "最后一段仍属同一帖子，不得截断。"
    post_id = "12345678901234567890"
    anchor = _x_element(href=f"/page/posts/{post_id}")
    card = MagicMock()
    card.query_selector.side_effect = {
        '[data-ad-preview="message"], .x1iorvi4, .x1pi30zi': _x_element(body),
        'h3 a, .xt0psk2 a, [role="link"] span': _x_element("Author"),
        'span[aria-label*="赞"], .x193iq5w span': _x_element("0", **{"aria-label": "0 Likes"}),
        'a[href*="comments"], span[aria-label*="评论"]': None,
        'span[aria-label*="分享"], a[href*="shares"]': _x_element("1.2K", **{"aria-label": "1.2K shares"}),
    }.get
    card.query_selector_all.side_effect = lambda selector: [anchor] if selector == (
        'a[href*="/posts/"], a[href*="/permalink.php"], a[href*="/story.php"]'
    ) else []
    note = FacebookAdapter(cookie_string="test-only")._parse_facebook_card(
        card, SimpleNamespace(url="https://www.facebook.com/search/top?q=brand")
    )
    item = MainFacebookAdapter(backend=object())._v4_notes_to_items([note])[0]

    assert note.content == item["content"] == body
    assert note.url == f"https://www.facebook.com/page/posts/{post_id}"
    assert note.raw_data["post_id"] == post_id
    assert note.raw_data["body_kind"] == item["raw"]["body_kind"] == "SEARCH_PREVIEW"
    assert item["raw"]["body_status"] == "SEARCH_PREVIEW_ONLY"
    assert note.raw_data["body_sha256"] == hashlib.sha256(body.encode("utf-8")).hexdigest()
    assert note.raw_data["body_state"] == "VISIBLE_DOM_TEXT_COMPLETENESS_UNKNOWN"
    assert item["raw"]["metric_display"]["shares"] == {"aria_label": "1.2K shares", "text": "1.2K"}
    assert note.likes == item["likes"] == 0
    assert item["comments"] is item["shares"] is item["collects"] is None
    assert item["platform_content_id"] == post_id
    assert item["publish_datetime"] == ""  # Capture time cannot fill publication time.


def _facebook_detail_fixture(post_id, *, initial_body, expanded_body, anchor_values=None,
                             expander_label="See more", include_expander=True):
    from lumenis.adapters.facebook import FacebookAdapter

    url = f"https://www.facebook.com/page/posts/{post_id}"
    article = MagicMock()
    body_state = {"text": initial_body}
    body = MagicMock()
    body.inner_text.side_effect = lambda: body_state["text"]
    expander = MagicMock()
    expander.inner_text.return_value = expander_label
    expander.get_attribute.return_value = None
    expander.click.side_effect = lambda **_kwargs: body_state.update(text=expanded_body)
    body.query_selector_all.return_value = [expander] if include_expander else []

    anchor = _x_element(href=f"/page/posts/{post_id}")
    if anchor_values is not None:
        anchor.get_attribute.side_effect = anchor_values
    like = _x_element("0", **{"aria-label": "0 Likes"})
    shares = _x_element("14 shares", **{"aria-label": "14 shares"})
    native_time = _x_element(datetime="2026-10-08T06:00:00Z")
    video = _x_element(src="https://video.xx.fbcdn.net/v/clip.mp4")

    def query_selector(selector):
        if selector in FacebookAdapter._DETAIL_BODY_SELECTORS or selector == (
            '[data-ad-preview="message"], .x1iorvi4, .x1pi30zi'
        ):
            return body
        if selector == 'span[aria-label*="赞"], .x193iq5w span':
            return like
        if selector == 'span[aria-label*="分享"], a[href*="shares"]':
            return shares
        return None

    permalink_selector = 'a[href*="/posts/"], a[href*="/permalink.php"], a[href*="/story.php"]'

    def query_selector_all(selector):
        if selector == permalink_selector or selector == "a[href]":
            return [anchor]
        if selector == "time[datetime]":
            return [native_time]
        if selector == "video[src]":
            return [video]
        return []

    article.query_selector.side_effect = query_selector
    article.query_selector_all.side_effect = query_selector_all
    page = MagicMock()
    page.url = url
    page.query_selector_all.return_value = [article]
    return FacebookAdapter(cookie_string="test-only"), page, article, body, expander, url


@pytest.mark.parametrize("observed,expected", [
    ("https://m.facebook.com/page/posts/123456789/?fbclid=transport#fragment",
     "https://www.facebook.com/page/posts/123456789"),
    ("https://www.facebook.com/permalink.php?story_fbid=123456789&id=456&token=transport",
     "https://www.facebook.com/permalink.php?story_fbid=123456789&id=456"),
])
def test_facebook_native_permalink_keeps_identity_and_discards_transport(observed, expected):
    from lumenis.adapters.facebook import FacebookAdapter

    identity = FacebookAdapter.observed_post_permalink(observed)
    assert identity["post_id"] == "123456789"
    assert identity["url"] == expected


def test_facebook_detail_does_not_promote_generic_article_text_to_message_body():
    from lumenis.adapters.facebook import FacebookAdapter

    generic_text = _x_element("A comment or unrelated article text")
    article = MagicMock()
    article.query_selector.side_effect = lambda selector: generic_text if selector == ".x1iorvi4" else None

    assert FacebookAdapter._detail_body_element(article) == (None, None)


def test_facebook_expansion_reacquires_replaced_message_with_bounded_wait():
    adapter, page, article, _body, expander, _url = _facebook_detail_fixture(
        "123456789", initial_body="Truncated prefix", expanded_body="Still old element"
    )
    replacement = _x_element("New rendered full message")
    original_query = article.query_selector.side_effect

    def render_after_click(*_args, **_kwargs):
        article.query_selector.side_effect = lambda selector: replacement if selector in (
            adapter._DETAIL_BODY_SELECTORS
        ) else original_query(selector)
        return MagicMock()

    page.wait_for_function.side_effect = render_after_click
    body, expansion = adapter._expand_detail_post_body(_body, article, page)

    assert body == "New rendered full message"
    assert expansion["status"] == "EXPANDED"
    assert expansion["click_count"] == expander.click.call_count == 1
    assert page.wait_for_function.call_args.kwargs["timeout"] == 2000


def test_facebook_detail_preserves_session_failure_after_expansion():
    from lumenis.adapters.facebook import FacebookAdapter

    adapter, page, _article, _body, _expander, url = _facebook_detail_fixture(
        "123456789", initial_body="Prefix", expanded_body="Expanded text"
    )
    with patch("lumenis.adapters.human_browser.HumanBrowser") as browser, \
            patch("lumenis.adapters.human_browser.configured_readonly_worker_url", return_value="http://worker"), \
            patch("lumenis.adapters.cookie_vault.inject_into_context"), \
            patch.object(FacebookAdapter, "_page_failure_state", side_effect=["", "SESSION_EXPIRED"]):
        browser.return_value.new_page.return_value = page
        result = adapter.detail(url)

    assert result.success is False
    assert result.error == "SESSION_EXPIRED"
    assert result.notes == []


def test_facebook_detail_expands_one_exact_body_control_and_keeps_completeness_unknown():
    from lumenis.adapters.facebook import FacebookAdapter

    post_id = "12345678901234567890"
    full_body = "The complete visible native body after expansion."
    adapter, page, _article, _body, expander, url = _facebook_detail_fixture(
        post_id, initial_body="Visible prefix", expanded_body=full_body
    )

    with patch("lumenis.adapters.human_browser.HumanBrowser") as browser, \
            patch("lumenis.adapters.human_browser.configured_readonly_worker_url", return_value="http://worker"), \
            patch("lumenis.adapters.cookie_vault.inject_into_context"), \
            patch.object(FacebookAdapter, "_page_failure_state", return_value=""):
        browser.return_value.new_page.return_value = page
        result = adapter.detail(url)

    assert result.success is True
    note = result.notes[0]
    assert note.content == full_body
    assert note.raw_data["body_kind"] == "NATIVE_POST_BODY"
    assert note.raw_data["body_status"] == "OBSERVED_COMPLETENESS_UNKNOWN"
    assert note.raw_data["body_completeness"] == "UNKNOWN"
    assert note.raw_data["body_expansion"] == {
        "status": "EXPANDED", "label": "see more", "click_count": 1,
        "render_wait": "BODY_CHANGED_OR_REPLACED",
    }
    assert expander.click.call_count == 1
    assert note.raw_data["post_id"] == post_id
    assert note.raw_data["native_time"] == "2026-10-08T06:00:00Z"
    assert note.raw_data["media_hints"] == [{
        "type": "video", "url_hint": "https://video.xx.fbcdn.net/v/clip.mp4",
        "source_locator": "video[src]@src",
    }]


def test_facebook_detail_rechecks_permalink_after_read_and_rejects_identity_change():
    from lumenis.adapters.facebook import FacebookAdapter

    post_id = "12345678901234567890"
    wrong_id = "99999999999999999999"
    adapter, page, _article, _body, expander, url = _facebook_detail_fixture(
        post_id, initial_body="Visible prefix", expanded_body="Expanded text",
        anchor_values=[f"/page/posts/{post_id}", f"/page/posts/{post_id}",
                       f"/page/posts/{wrong_id}"],
    )

    with patch("lumenis.adapters.human_browser.HumanBrowser") as browser, \
            patch("lumenis.adapters.human_browser.configured_readonly_worker_url", return_value="http://worker"), \
            patch("lumenis.adapters.cookie_vault.inject_into_context"), \
            patch.object(FacebookAdapter, "_page_failure_state", return_value=""):
        browser.return_value.new_page.return_value = page
        result = adapter.detail(url)

    assert result.success is False
    assert result.error == "IDENTITY_MISMATCH: TARGET_ARTICLE_POST_READ_ID_MISMATCH"
    assert result.notes == []
    assert expander.click.call_count == 1


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
    with patch("lumenis.adapters.human_browser.HumanBrowser") as browser, \
            patch("lumenis.adapters.human_browser.configured_readonly_worker_url", return_value="http://worker"), \
            patch("lumenis.adapters.cookie_vault.inject_into_context"):
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
    text_element = _x_element(body)
    tweet.query_selector_all.side_effect = lambda selector: [text_element] if selector == '[data-testid="tweetText"]' else []
    note = XAdapter(cookie_string="test-only")._parse_x_tweet(tweet)
    assert note.content == body
    assert note.raw_data["tweet_id"] is None
    assert note.publish_date == ""


def test_x_parser_preserves_native_id_explicit_zero_unknown_counts_and_publish_time():
    from lumenis.adapters.x_platform import XAdapter

    tweet = MagicMock()
    time_element = _x_element(datetime="2026-09-28T01:02:03Z")
    timestamp_anchor = _x_element(href="/brand/status/12345678901234567890?s=20")
    timestamp_anchor.query_selector.side_effect = lambda selector: time_element if selector == "time[datetime]" else None
    elements = {
        '[data-testid="tweetText"]': _x_element("A source post"),
        'a[href*="/status/"]': timestamp_anchor,
        '[data-testid="like"]': _x_element(**{"aria-label": "0 Likes"}),
        '[data-testid="reply"]': _x_element(**{"aria-label": "unavailable"}),
        '[data-testid="retweet"]': _x_element("1.2K", **{"aria-label": "1.2K Reposts"}),
    }
    tweet.query_selector_all.side_effect = lambda selector: [elements[selector]] if selector in elements else []

    note = XAdapter(cookie_string="test-only")._parse_x_tweet(tweet)

    assert note.raw_data["tweet_id"] == "12345678901234567890"
    assert note.likes == 0
    assert note.comments is None
    assert note.shares is None
    assert note.collects is None
    assert note.publish_date == "2026-09-28T01:02:03Z"
    assert note.raw_data["metric_display"]["shares"] == {
        "aria_label": "1.2K Reposts", "text": "1.2K",
        "locator": '[data-testid="retweet"]',
    }


def test_x_metric_parser_falls_back_to_text_and_rejects_approximate_or_bad_grouping():
    from lumenis.adapters.x_platform import XAdapter

    def extract(label, text):
        tweet = MagicMock()
        tweet.query_selector_all.return_value = [_x_element(text, **{"aria-label": label})]
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
    from lumenis.system.collector.adapters.x_platform import CollectionStatus, XAdapter

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

    from lumenis.system.collector.adapters.facebook import (
        CollectionStatus,
        FacebookAdapter,
    )

    post_id = "12345678901234567890"
    permalink = f"https://www.facebook.com/page/posts/{post_id}"
    search_note = SimpleNamespace(
        raw_data={"post_id": post_id, "body_kind": "SEARCH_PREVIEW",
                  "body_status": "SEARCH_PREVIEW_ONLY"},
        title="Preview", content="Search snippet",
        author_id="page-1", author="Brand", publish_date="2026-10-05T10:00:00Z",
        url=permalink, likes=None,
        comments=None, collects=None, shares=None,
    )
    detail_note = SimpleNamespace(
        raw_data={"post_id": post_id, "body_kind": "NATIVE_POST_BODY",
                  "body_status": "OBSERVED_COMPLETENESS_UNKNOWN",
                  "body_completeness": "UNKNOWN",
                  "detail_post_id_status": "OBSERVED_AND_MATCHED",
                  "body_locator": '[data-ad-preview="message"]',
                  "body_expansion": {"status": "NO_EXPANDER_OBSERVED", "click_count": 0},
                  "media_hints": [{"type": "image", "url_hint": "https://www.facebook.com/photo.jpg"}],
                  "native_time": "2026-10-05T10:00:00Z",
                  "metric_display": {"likes": {"aria_label": "0 Likes", "text": "0"}}},
        title="Post", content="Visible native detail body",
        author_id="page-1", author="Brand", publish_date="2026-10-05T10:00:00Z",
        url=permalink, likes=0, comments=None, collects=None, shares=None,
    )

    class Backend:
        def search(self, keyword, *, max_results):
            assert keyword == "brand update" and max_results == 12
            return SimpleNamespace(success=True, notes=[search_note], raw_count=1, error="")

        def detail(self, content_id):
            assert content_id == permalink
            return SimpleNamespace(success=True, notes=[detail_note], raw_count=1, error="")

        def comments(self, content_id, *, max_comments):
            return SimpleNamespace(success=True, notes=[], raw_count=0, error="")

        def creator(self, creator_id):
            return SimpleNamespace(success=True, notes=[], raw_count=0, error="")

    adapter = FacebookAdapter(backend=Backend())
    search = adapter.search("brand update", max_results=12)
    detail = adapter.detail(permalink)
    comments = adapter.comments("fb-post-123")
    creator = adapter.creator("page-1")

    assert search.platform == detail.platform == comments.platform == creator.platform == "facebook"
    assert search.status == detail.status == CollectionStatus.SUCCESS
    assert search.items[0]["platform_content_id"] == post_id
    assert search.items[0]["content"] == "Visible native detail body"
    assert search.items[0]["raw"]["search_summary_observation"]["text"] == "Search snippet"
    observation = search.items[0]["raw"]["detail_observation"]
    assert observation["body_kind"] == "NATIVE_POST_BODY"
    assert observation["body_completeness"] == "UNKNOWN"
    assert observation["body_expansion"]["status"] == "NO_EXPANDER_OBSERVED"
    assert observation["media_hints"] == detail_note.raw_data["media_hints"]
    assert observation["native_time"] == detail_note.raw_data["native_time"]
    assert observation["native_metrics"]["likes"] == 0
    assert search.metadata["detail"]["body_completeness"] == "UNKNOWN"
    assert search.items[0]["likes"] == 0


def test_main_facebook_adapter_never_promotes_nonempty_search_preview_to_detail_body():
    from types import SimpleNamespace

    from lumenis.system.collector.adapters.facebook import FacebookAdapter

    post_id = "12345678901234567890"
    permalink = f"https://www.facebook.com/page/posts/{post_id}"
    preview_note = SimpleNamespace(
        raw_data={"post_id": post_id, "body_kind": "SEARCH_PREVIEW",
                  "body_status": "SEARCH_PREVIEW_ONLY"},
        title="Search preview", content="Nonempty search preview text",
        author_id="page-1", author="Brand", publish_date="", url=permalink,
        likes=None, comments=None, collects=None, shares=None,
    )

    class Backend:
        def search(self, *_args, **_kwargs):
            return SimpleNamespace(success=True, notes=[preview_note], raw_count=1, error="")

        def detail(self, content_id):
            assert content_id == permalink
            return SimpleNamespace(success=True, notes=[preview_note], raw_count=1, error="")

    result = FacebookAdapter(backend=Backend()).search("brand")
    item = result.items[0]
    detail = item["raw"]["detail_observation"]

    assert item["raw"]["search_summary_observation"]["text"] == "Nonempty search preview text"
    assert item["content"] == ""
    assert detail["status"] == "DETAIL_NOT_RETURNED"
    assert detail["body_kind"] is None
    assert detail["observed_body_kind"] == "SEARCH_PREVIEW"
    assert detail["preview_text"] == "Nonempty search preview text"
    assert detail["body"] is None
    assert result.metadata["detail"]["failed"] == 1
    assert result.metadata["detail"]["body_completeness"] == "PARTIAL"


def test_main_facebook_adapter_errors_keep_platform_and_health_unverified(monkeypatch):
    from lumenis.system.collector.adapters.facebook import (
        CollectionStatus,
        FacebookAdapter,
    )

    class BrokenBackend:
        def search(self, *_args, **_kwargs):
            raise RuntimeError("collector unavailable")

    adapter = FacebookAdapter(backend=BrokenBackend())
    failed = adapter.search("brand")
    assert failed.platform == "facebook"
    assert failed.status == CollectionStatus.PROVIDER_UNAVAILABLE

    monkeypatch.setattr(
        "lumenis.adapters.human_browser.readonly_worker_health",
        lambda platform: {"status": "NEED_VERIFY", "ready": False,
                          "metadata": {"worker_binding_registered": True,
                                       "login_and_collection_verified": False}},
    )
    health = adapter.health_check()
    assert health.platform == "facebook"
    assert health.status == CollectionStatus.NEED_VERIFY
    assert "private-cookie-path" not in health.message
    assert health.metadata["login_and_collection_verified"] is False

    monkeypatch.setattr(
        "lumenis.adapters.human_browser.readonly_worker_health",
        lambda platform: {"status": "NOT_CONFIGURED", "ready": False,
                          "metadata": {"worker_binding_registered": False,
                                       "login_and_collection_verified": False}},
    )
    missing = adapter.health_check()
    assert missing.platform == "facebook"
    assert missing.status == CollectionStatus.NOT_CONFIGURED


def test_main_facebook_search_failure_retains_safe_backend_reason():
    from types import SimpleNamespace

    from lumenis.system.collector.adapters.facebook import (
        CollectionStatus,
        FacebookAdapter,
    )

    class Backend:
        def search(self, *_args, **_kwargs):
            return SimpleNamespace(success=False, notes=[], raw_count=0,
                                   error="PROVIDER_UNAVAILABLE: WORKER_DISCONNECTED")

    result = FacebookAdapter(backend=Backend()).search("广州太古汇 活动")
    assert result.status is CollectionStatus.PROVIDER_UNAVAILABLE
    detail = result.metadata["detail"]
    assert detail["search_failure"] == {"state": "PROVIDER_UNAVAILABLE", "reason": "WORKER_DISCONNECTED"}
    assert detail["attempted"] == 0 and detail["body_completeness"] == "NO_RESULTS"


def test_main_facebook_failure_observation_never_copies_unknown_error_text():
    from lumenis.system.collector.adapters.facebook import FacebookAdapter

    secret = "PRIVATE-CREDENTIAL-MUST-NOT-BE-COPIED"
    observation = FacebookAdapter._safe_failure_observation("PROVIDER_UNAVAILABLE: " + secret)
    assert observation == {"state": "PROVIDER_UNAVAILABLE", "reason": None}
    assert secret not in repr(observation)
