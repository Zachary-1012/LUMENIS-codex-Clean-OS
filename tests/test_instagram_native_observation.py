"""Native DOM result semantics; no platform, profile, cookie or browser access."""
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.parametrize("value,expected", [
    (None, None), ("", None), (True, None), (-1, None), (1.2, None),
    ("1.2K", None), ("1.3万", None), ("1,2", None), ("01", None),
    ("unavailable", None), ("0", 0), (0, 0), ("1,234", 1234),
    ("12345678901234567890", 12345678901234567890),
])
def test_instagram_display_counts_are_exact_or_unknown(value, expected):
    from lumenis.adapters.instagram import InstagramAdapter
    assert InstagramAdapter._ig_num(value) == expected


def _detail_result(data):
    from lumenis.adapters.instagram import InstagramAdapter
    with patch("lumenis.adapters.instagram.HumanBrowser") as browser, patch("lumenis.adapters.instagram.inject_into_context"), patch("lumenis.adapters.instagram.configured_readonly_worker_url", return_value="http://127.0.0.1:1"):
        data = {**data, "article_observed": True}
        page = browser.return_value.new_page.return_value
        page.url = "https://www.instagram.com/p/synthetic-post/"
        page.evaluate.return_value = data
        result = InstagramAdapter()._detail_browser("synthetic-post", "post", "test-only")
    return result


def test_instagram_detail_keeps_full_caption_null_counts_and_distinct_image_alt():
    body = "Original source paragraph. " * 40 + "Final source paragraph."
    result = _detail_result({
        "caption": body, "caption_source": "article h1",
        "image_alts": ["An image description, not the post caption."],
        "publish_time": "2026-10-08T00:00:00Z",
    })
    assert result.success and len(result.notes) == 1
    note = result.notes[0]
    assert note.content == body
    assert note.likes is note.comments is note.collects is note.shares is None
    assert note.author == ""
    assert note.raw_data["image_alts"] == ["An image description, not the post caption."]
    assert note.raw_data["body_state"] == "NATIVE_CAPTION_DOM_COMPLETENESS_UNKNOWN"


def test_instagram_detail_preserves_observed_zero_compact_display_and_original_publication():
    result = _detail_result({
        "caption": "Source body", "publish_time": "2026-10-08T01:02:03+09:00",
        "likes": "0", "likes_display": "0 likes",
        "comment_count": "1.2K", "comment_count_display": "1.2K comments",
    })
    note = result.notes[0]
    assert note.likes == 0 and note.comments is None
    assert note.publish_date == "2026-10-08T01:02:03+09:00"
    assert note.raw_data["metric_display"] == {"likes": "0 likes", "comments": "1.2K comments"}


def test_instagram_image_alt_and_publication_metadata_do_not_replace_missing_caption():
    result = _detail_result({
        "caption": "", "image_alts": ["Image-only description"],
        "publish_time": "2026-10-08T01:02:03Z",
    })
    note = result.notes[0]
    assert note.content == ""
    assert note.raw_data["body_state"] == "NATIVE_BODY_UNAVAILABLE"
    assert note.raw_data["needs_detail"] is True
    assert note.raw_data["image_alts"] == ["Image-only description"]


def test_instagram_discovery_preserves_source_cover_and_unmeasured_fields():
    from lumenis.adapters.instagram import InstagramAdapter
    page = MagicMock()
    cover = "https://example.test/image?source=" + "a" * 400
    page.evaluate.return_value = [{"code": "synthetic-code", "kind": "p", "lines": [],
                                   "alt": "Observed image description", "cover": cover}]
    note = InstagramAdapter()._parse_cards(page.evaluate.return_value, 1)[0]
    assert note.likes is None and note.author == "" and note.publish_date == ""
    assert note.raw_data["cover"] == cover
    assert note.raw_data["body_state"] == "SEARCH_PREVIEW_ONLY_NOT_NATIVE_FULL_POST"
    assert note.raw_data["needs_detail"] is True
    assert note.raw_data["image_alt"] == "Observed image description"


def test_instagram_discovery_prefers_observed_text_and_keeps_compact_metric_display():
    from lumenis.adapters.instagram import InstagramAdapter
    page = MagicMock()
    page.evaluate.return_value = [{"code": "synthetic-code", "kind": "p",
        "lines": ["author", "1.2K", "Observed discovery text"],
        "alt": "Different image description", "cover": ""}]
    note = InstagramAdapter()._parse_cards(page.evaluate.return_value, 1)[0]
    assert note.content == "Observed discovery text" and note.likes is None
    assert note.raw_data["metric_display"]["likes"] == "1.2K"
    assert note.raw_data["image_alt"] == "Different image description"
