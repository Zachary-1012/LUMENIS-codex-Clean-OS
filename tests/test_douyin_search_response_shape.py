"""Regression for the current Douyin search/single response and honest empty state."""

import os
import time

import pytest

from lumenis.adapters.douyin import DouyinAdapter


def _live_shaped_bag():
    # The current official search/single response places each video under
    # data[].aweme_info; data can also contain non-video related-word cards.
    return {
        "status_code": 0,
        "data": [
            {"aweme_info": {
                "aweme_id": "7684561511709344369",
                "desc": "15年的广州太古汇坚持隐奢",
                "create_time": 1789171200,
                "statistics": {
                    "digg_count": 167, "comment_count": 23,
                    "collect_count": 28, "share_count": 51,
                },
                "author": {"nickname": "WOOTII", "uid": "author-1"},
            }},
            {"aweme_info": {
                "aweme_id": "6975362581787593992",
                "desc": "广州富人的购物天堂",
                "create_time": 1624060800,
                "statistics": {
                    "digg_count": 8994, "comment_count": 890,
                    "collect_count": 302, "share_count": 852,
                },
                "author": {"nickname": "航拍摄影HANG", "uid": "author-2"},
            }},
            {"aweme_info": {
                "aweme_id": "7649033622729780838",
                "desc": "广州太古汇综合商业旗舰",
                "create_time": 1780876800,
                "statistics": {
                    "digg_count": 896, "comment_count": 31,
                    "collect_count": 112, "share_count": 108,
                },
                "author": {"nickname": "一只大棒", "uid": "author-3"},
            }},
            {"card_type": "related_words", "aweme_list": [], "data": []},
        ],
    }


def test_current_search_single_shape_produces_real_video_fields():
    notes = DouyinAdapter()._notes_from_bags([_live_shaped_bag()], 3)

    assert len(notes) == 3
    assert notes[0].raw_data["aweme_id"] == "7684561511709344369"
    assert notes[0].url == "https://www.douyin.com/video/7684561511709344369"
    assert notes[0].author == "WOOTII"
    assert notes[0].likes == 167
    assert notes[0].comments == 23
    assert notes[0].collects == 28
    assert notes[0].shares == 51
    assert notes[0].publish_date == "2026-09-12"


def test_missing_or_unparseable_search_response_is_not_reported_as_empty():
    assert not DouyinAdapter._has_verified_empty_search_response([])
    assert not DouyinAdapter._has_verified_empty_search_response([{"status_code": 0}])
    assert not DouyinAdapter._has_verified_empty_search_response([
        {"status_code": 0, "data": [{"aweme_info": {"desc": "unparseable"}}]},
    ])


def test_only_successful_explicit_empty_data_is_a_verified_empty_search():
    assert DouyinAdapter._has_verified_empty_search_response([
        {"status_code": 0, "data": []},
    ])
    assert not DouyinAdapter._has_verified_empty_search_response([
        {"status_code": 1, "data": []},
    ])
    assert not DouyinAdapter._has_verified_empty_search_response([
        {"status_code": 0, "data": []},
        {"status_code": 0, "data": [{"aweme_info": {"desc": "not parsed"}}]},
    ])


@pytest.mark.parametrize("host_tz", ["UTC0", "EST5", "JST-9"])
def test_source_calendar_date_is_host_timezone_independent(host_tz):
    if not hasattr(time, "tzset"):
        pytest.skip("host does not expose tzset")
    previous = os.environ.get("TZ")
    try:
        os.environ["TZ"] = host_tz
        time.tzset()
        # The original midnight-UTC sample must not move back a date on US hosts.
        notes = DouyinAdapter()._notes_from_bags([_live_shaped_bag()], 3)
        assert notes[0].publish_date == "2026-09-12"
        assert notes[0].raw_data["create_time"] == 1789171200
        from lumenis.system.collector.adapters.douyin import DouyinAdapter as MainAdapter
        item = MainAdapter()._v4_notes_to_items(notes)[0]
        assert item["publish_datetime"] == "2026-09-12"
        assert item["raw"]["create_time"] == 1789171200
    finally:
        if previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous
        time.tzset()


@pytest.mark.parametrize("invalid", [None, "", "unknown", 0, -1, float("inf"), 10**100])
def test_invalid_source_timestamp_stays_unknown(invalid):
    assert DouyinAdapter._ts_to_date(invalid) == ""


def test_source_calendar_boundary_differs_from_utc_event_date():
    # 2026-09-11 15:59:59/16:00:00 UTC straddle midnight in UTC+08.
    assert DouyinAdapter._ts_to_date(1789142399) == "2026-09-11"
    assert DouyinAdapter._ts_to_date(1789142400) == "2026-09-12"
