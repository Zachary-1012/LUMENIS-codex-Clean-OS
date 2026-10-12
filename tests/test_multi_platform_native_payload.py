from __future__ import annotations

from copy import deepcopy

import pytest

from lumenis.system.collector.adapters.multi_platform_import import (
    _normalize_source_publication,
    _to_note_payload,
)
from lumenis.system.collector.adapters.platform_naming import to_canonical_record


@pytest.mark.parametrize(
    ("platform", "raw", "expected_content"),
    [
        (
            "instagram",
            {"media_id": "ig-1", "username": "author", "caption": "Instagram caption"},
            "Instagram caption",
        ),
        (
            "reddit",
            {"post_id": "reddit-1", "author_fullname": "t2_author", "selftext": "Reddit selftext"},
            "Reddit selftext",
        ),
        (
            "linkedin",
            {"post_id": "urn:li:activity:1", "author_id": "author", "commentary": "LinkedIn commentary"},
            "LinkedIn commentary",
        ),
    ],
)
def test_native_only_body_fields_reach_note_payload(platform, raw, expected_content):
    original = deepcopy(raw)
    canonical = to_canonical_record(raw, platform)

    payload = _to_note_payload(canonical, raw)

    assert payload["content"] == expected_content
    assert raw == original


def test_generic_payload_body_keeps_priority_over_platform_native_body():
    raw = {
        "media_id": "ig-2",
        "username": "author",
        "caption": "Native caption",
        "content": "Generic content",
        "body": "Generic body",
        "desc": "Generic description",
        "text": "Generic text",
        "description": "Generic fallback",
    }
    original = deepcopy(raw)
    canonical = to_canonical_record(raw, "instagram")

    payload = _to_note_payload(canonical, raw)

    assert payload["content"] == "Generic content"
    assert raw == original


def test_unmapped_platform_keeps_content_unknown():
    raw = {"platform": "unlisted_platform", "caption": "Unmapped caption"}
    original = deepcopy(raw)
    canonical = to_canonical_record(raw)

    payload = _to_note_payload(canonical, raw)

    assert canonical["platform"] is None
    assert payload["source_platform"] == "unknown"
    assert payload["content"] == ""
    assert raw == original


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1767225600, "2026-01-01T00:00:00+00:00"),
        (1767225600.25, "2026-01-01T00:00:00.250000+00:00"),
        ("2026-01-01T08:00:00+08:00", "2026-01-01T08:00:00+08:00"),
    ],
)
def test_instagram_native_publication_accepts_proven_seconds_and_explicit_iso(
    value, expected,
):
    assert _normalize_source_publication(value, "instagram") == expected


@pytest.mark.parametrize("value", [None, True, False, float("nan"), float("inf"), float("-inf")])
def test_instagram_unobserved_or_invalid_native_time_is_unknown(value):
    assert _normalize_source_publication(value, "instagram") == ""


def test_instagram_native_publication_stays_separate_from_capture_time():
    raw = {
        "media_id": "17800000000000000",
        "taken_at": 1767225600,
        "publish_datetime": "2026-01-01T00:00:00+00:00",
        "captured_at": "2026-01-02T00:00:00+00:00",
    }
    original = deepcopy(raw)
    canonical = to_canonical_record(raw, "instagram")

    payload = _to_note_payload(canonical, raw)

    assert payload["publish_datetime"] == "2026-01-01T00:00:00+00:00"
    assert payload["captured_at"] == "2026-01-02T00:00:00+00:00"
    assert raw == original


@pytest.mark.parametrize("native_zero", [0, "0"])
def test_douyin_zero_native_publication_stays_unknown_and_raw_is_preserved(native_zero):
    raw = {
        "aweme_id": "7770000000000000000",
        "create_time": native_zero,
        "captured_at": "2026-01-02T00:00:00Z",
    }
    original = deepcopy(raw)
    canonical = to_canonical_record(raw, "douyin")

    payload = _to_note_payload(canonical, raw)

    assert _normalize_source_publication(native_zero, "douyin") == ""
    assert payload["publish_datetime"] == ""
    assert payload["captured_at"] == "2026-01-02T00:00:00Z"
    assert raw == original
    assert raw["create_time"] == native_zero


@pytest.mark.parametrize("native_time", [1767225600, "1767225600"])
def test_douyin_nonzero_native_epoch_normalization_is_unchanged(native_time):
    assert _normalize_source_publication(
        native_time, "douyin",
    ) == "2026-01-01T00:00:00Z"
