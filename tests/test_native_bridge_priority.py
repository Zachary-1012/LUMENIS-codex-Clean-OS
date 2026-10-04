"""Pure source-contract regressions for the frozen secondary bridge.

These cases intentionally describe desired native-field priority. The current
bridge has known failures here; this file is a red-test handoff for the owner.
No adapter collection, persistence, browser, or network calls are made.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from lumenis.system.collector.adapters.platform_naming import (
    map_raw_to_normalized,
    to_canonical_record,
)
from lumenis.system.collector.adapters.secondary_collection import _native_record


def _record(platform: str, raw: dict, **fields):
    item = {"raw": raw, **fields}
    before = deepcopy(item)
    record = _native_record(item, platform, "fixture-query", "2026-10-02T00:00:00Z")
    assert item == before, "bridge must leave normalized input and raw source untouched"
    assert record["source_raw"] == raw
    return record


def test_weibo_post_identity_stays_distinct_from_native_author_identity():
    raw = {"mid": "post-100", "idstr": "post-100", "user_id": "author-200"}
    record = _record(
        "weibo", raw, platform_content_id="transport-post", author_id="adapter-author",
        publish_datetime="2026-10-01T12:00:00Z",
    )

    assert record["mid"] == "post-100"
    assert record["user_id"] == "author-200"
    assert to_canonical_record(record, "weibo")["content_id"] == "post-100"
    assert to_canonical_record(record, "weibo")["author_id"] == "author-200"


def test_zhihu_native_url_token_is_not_replaced_by_generic_author_id():
    record = _record(
        "zhihu", {"answer_id": "answer-10", "url_token": "source-token"},
        platform_content_id="answer-10", author_id="numeric-user-id",
    )

    assert record["url_token"] == "source-token"


def test_zhihu_numeric_author_id_is_not_promoted_to_url_token():
    # Current Zhihu adapter raw shape carries object id/type; author.id is
    # normalized separately and is not a url_token.
    record = _record(
        "zhihu", {"object_type": "answer", "id": "answer-11"},
        platform_content_id="answer-11", author_id="123456789",
    )

    assert record.get("url_token") is None
    assert to_canonical_record(record, "zhihu")["author_id"] is None


def test_zhihu_question_identity_is_not_labeled_as_answer_id():
    # The adapter emits questions as well as answers, and preserves object_type.
    record = _record(
        "zhihu", {"object_type": "question", "id": "question-12"},
        platform_content_id="question-12",
    )

    assert record.get("answer_id") is None
    assert to_canonical_record(record, "zhihu")["content_id"] is None


def test_instagram_shortcode_is_not_labeled_as_bigint_media_id():
    # Current adapter identity is raw_data.shortcode, not media_id.
    record = _record(
        "instagram", {"shortcode": "C4sourceCode", "media_type": "post"},
        platform_content_id="C4sourceCode", author_id="",
    )

    assert record["shortcode"] == "C4sourceCode"
    assert record.get("media_id") is None


def test_instagram_handle_is_not_replaced_by_numeric_author_id():
    record = _record(
        "instagram", {"shortcode": "C4sourceCode", "username": "source.handle"},
        platform_content_id="C4sourceCode", author_id="9007199254740993",
        author_nickname="source.handle",
    )

    assert record["username"] == "source.handle"
    assert to_canonical_record(record, "instagram")["author_id"] == "source.handle"


def test_x_adapter_handle_is_mapped_to_native_screen_name():
    # The existing X adapter emits raw.handle and normalized author_id.
    record = _record(
        "x", {"tweet_id": "tweet-20", "handle": "@source"},
        platform_content_id="tweet-20", author_id="@source",
    )

    assert record.get("screen_name") == "@source"
    assert to_canonical_record(record, "x")["author_id"] == "@source"


def test_rss_native_zero_and_publication_survive_absent_transport_values():
    record = _record(
        "web_rss",
        {"content_id": "rss-item-30", "published_at": "2026-09-30T00:00:00Z",
         "like_count": 0, "comment_count": 4},
        platform_content_id="transport-rss-item", publish_datetime=None,
        likes=None, comments=None,
    )

    canonical = to_canonical_record(record, "web_rss")
    assert record["like_count"] == 0
    assert record["comment_count"] == 4
    assert record["published_at"] == "2026-09-30T00:00:00Z"
    assert canonical["like_count"] == 0
    assert canonical["published_at"] == "2026-09-30T00:00:00Z"


def test_douyin_unknown_sec_uid_stays_unknown_when_adapter_only_has_uid():
    # Search adapter source shape exposes numeric uid as generic author_id and
    # does not provide sec_uid. Do not synthesize one from that different ID.
    record = _record(
        "douyin", {"aweme_id": "video-40", "author_id": "123456789"},
        platform_content_id="video-40", author_id="123456789",
    )

    assert to_canonical_record(record, "douyin")["author_id"] is None


def test_author_bigint_integer_is_canonicalized_as_exact_text():
    record = _record(
        "bilibili", {"bvid": "BV1source", "mid": 9007199254740993},
        platform_content_id="BV1source",
    )

    assert to_canonical_record(record, "bilibili")["author_id"] == "9007199254740993"


@pytest.mark.parametrize("bad_author_id", [True, float(9007199254740993)])
def test_author_bigint_bool_or_float_does_not_become_canonical_identity(bad_author_id):
    record = _record(
        "bilibili", {"bvid": "BV1source"}, platform_content_id="BV1source",
        author_id=bad_author_id,
    )

    assert to_canonical_record(record, "bilibili")["author_id"] is None


@pytest.mark.parametrize(
    ("author_value", "expected"),
    [
        ("opaque:@source.handle", "opaque:@source.handle"),
        ("  @source.handle  ", "  @source.handle  "),
        (9007199254740993123456789, "9007199254740993123456789"),
        (None, None),
        ("", None),
        ("   ", None),
        (True, None),
        (9007199254740992.0, None),
        (["author"], None),
        ({"id": "author"}, None),
    ],
    ids=["opaque-token", "exact-text", "arbitrary-int", "none", "empty", "blank",
         "bool", "float", "list", "mapping"],
)
def test_author_identity_normalization_is_shared_without_mutating_raw(author_value, expected):
    canonical_raw = {"bvid": "BV1source", "mid": author_value}
    normalized_raw = {"bvid": "BV1source", "owner_mid": author_value}
    canonical_before = deepcopy(canonical_raw)
    normalized_before = deepcopy(normalized_raw)

    canonical = to_canonical_record(canonical_raw, "bilibili")
    normalized = map_raw_to_normalized(normalized_raw, "bilibili")

    assert canonical["author_id"] == expected
    assert normalized["author_id"] == expected
    assert canonical_raw == canonical_before
    assert normalized_raw == normalized_before


def test_instagram_shortcode_is_canonical_identity_when_media_id_is_absent():
    raw = {"platform": "instagram", "shortcode": "C4sourceCode"}
    before = deepcopy(raw)

    canonical = to_canonical_record(raw, "instagram")
    normalized = map_raw_to_normalized(raw, "instagram")

    assert canonical["content_id"] == "C4sourceCode"
    assert normalized["platform_content_id"] == "C4sourceCode"
    assert "media_id" not in raw
    assert raw == before


def test_instagram_native_media_id_keeps_priority_over_shortcode():
    raw = {"platform": "instagram", "media_id": "900123456789", "shortcode": "C4sourceCode"}

    canonical = to_canonical_record(raw, "instagram")
    normalized = map_raw_to_normalized(raw, "instagram")

    assert canonical["content_id"] == "900123456789"
    assert normalized["platform_content_id"] == "900123456789"
