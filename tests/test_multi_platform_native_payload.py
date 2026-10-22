from __future__ import annotations

from copy import deepcopy

import pytest

from lumenis.system.collector.adapters.multi_platform_import import (
    _format_epoch_publication,
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


def test_douyin_zero_publication_timestamp_remains_unknown():
    assert _format_epoch_publication(0, "douyin") == ""
    assert _format_epoch_publication(1_700_000_000, "douyin").startswith("2023-")
