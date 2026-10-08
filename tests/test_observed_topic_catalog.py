from copy import deepcopy

from lumenis.system.collector.acquisition_plan import build_observed_topic_catalog


def source(**changes):
    row = {
        "platform": "douyin", "platform_content_id": "native-123",
        "source_url": "https://www.douyin.com/video/123",
        "native_publication": "2026-04-02T04:00:00+00:00",
        "capture_observation_utc": "2026-10-03T18:00:00+00:00",
        "native_raw_ref": {"path": "raw-123.json", "sha256": "a" * 64},
        "native_topics": [{"text": "中国香氛", "native_topic_id": "42",
                           "native_locator": "/native_public_aweme/text_extra/0/hashtag_name"}],
        "rights": {"TRAIN": "NOT_GRANTED", "commercial": "UNKNOWN"},
    }
    return {**row, **changes}


def test_same_content_in_multiple_queries_is_one_sample_with_versioned_observations():
    a = source()
    b = source(capture_observation_utc="2026-10-04T18:00:00+00:00",
               native_raw_ref={"path": "raw-123-fresh.json", "sha256": "b" * 64})
    before = deepcopy([a, b])
    catalog = build_observed_topic_catalog([a, b])
    term = catalog["terms"][0]
    assert term["sample_distinct_content_count"] == 1
    assert len(term["observations"]) == 2
    assert term["native_topic_ids"] == ["42"]
    assert term["canonical_entity_refs"] is None and term["admitted"] is False
    assert term["observations"][0]["rights"]["TRAIN"] == "NOT_GRANTED"
    assert [a, b] == before
    assert catalog["platform_heat"] is None


def test_unknown_and_future_times_stay_reviewable_without_excluding_history():
    rows = [source(native_publication=None),
            source(native_publication="2025-03-01T12:00:00+08:00"),
            source(native_publication="2026-12-01T12:00:00+08:00"),
            source(native_publication="2026-09-01T12:00:00")]
    result = build_observed_topic_catalog(rows)
    assert len(result["terms"]) == 1 and len(result["review"]) == 3
    assert result["publication_since"] is None
    assert result["terms"][0]["observations"][0]["native_publication"] == "2025-03-01T12:00:00+08:00"


def test_explicit_task_period_filters_history_without_changing_originals():
    rows = [source(native_publication="2025-03-01T12:00:00+08:00"),
            source(), source(native_publication="2026-09-01T12:00:00+08:00")]
    before = deepcopy(rows)
    result = build_observed_topic_catalog(rows, publication_since="2026-01-01",
                                         publication_until="2026-08-31")
    assert len(result["terms"]) == 1 and len(result["terms"][0]["observations"]) == 1
    assert [r["reason"] for r in result["review"]] == ["OUTSIDE_REQUESTED_PUBLICATION_PERIOD"] * 2
    assert rows == before


def test_distinct_platform_identity_and_missing_topic_locator_stay_separate():
    a = source()
    b = source(platform="x", source_url="https://x.com/test/status/123")
    c = source(native_topics=[{"text": "unsupported supposed trend"}])
    result = build_observed_topic_catalog([a, b, c])
    assert {row["platform"] for row in result["terms"]} == {"x", "douyin"}
    assert all(row["sample_distinct_content_count"] == 1 for row in result["terms"])
    assert result["review"][0]["reason"] == "NATIVE_TOPIC_LOCATOR_OR_TEXT_INVALID"


def test_private_source_and_missing_raw_lineage_cannot_seed_public_queries():
    result = build_observed_topic_catalog([
        source(source_url="http://127.0.0.1/internal"),
        source(native_raw_ref={"path": "unproved.json"}),
    ])
    assert result["terms"] == [] and len(result["review"]) == 2
