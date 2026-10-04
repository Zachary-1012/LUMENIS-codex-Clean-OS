from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone

import pytest

from lumenis.system.collector.adapters.multi_platform_import import (
    import_multi_platform_records,
)
from lumenis.system.collector.adapters.platform_naming import PLATFORM_NATIVE_FIELDS


SOURCE_INSTANT = datetime(2026, 9, 18, 4, 0, tzinfo=timezone.utc)
SOURCE_SECONDS = int(SOURCE_INSTANT.timestamp())
CAPTURED_AT = "2026-09-19T08:30:00+08:00"
SOURCE_ISO_WITH_OFFSET = "2026-09-18T12:00:00+08:00"
SOURCE_RFC2822 = "Fri, 18 Sep 2026 12:00:00 +0800"
SOURCE_WEIBO = "Fri Sep 18 12:00:00 +0800 2026"

# These units are supported by current source contracts: XHS exposes epoch
# milliseconds; Douyin, Bilibili, Reddit, and TikTok expose epoch seconds.
PROVEN_UNIX_UNITS = {
    "xiaohongshu": "milliseconds",
    "douyin": "seconds",
    "bilibili": "seconds",
    "reddit": "seconds",
    "tiktok": "seconds",
}


@pytest.fixture
def initialized_note_database(tmp_path, monkeypatch):
    """Use the canonical database layer against a test-owned disposable file."""
    db_path = tmp_path / "native-publication.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))

    import database
    from lumenis.shared.database.repository import get_repository

    # Rebind the cached canonical repository after selecting this test's path.
    get_repository(force_reload=True)
    database.init_db()
    connection = database.get_repository().connect()
    try:
        yield database, connection
    finally:
        if connection.in_transaction:
            connection.rollback()
        connection.close()


def _native_record(platform: str, case: str) -> tuple[dict, str]:
    spec = PLATFORM_NATIVE_FIELDS[platform]
    note_id = f"publication-{platform}-{case}"
    record = {
        "platform": platform,
        spec.content_id: note_id,
        spec.author_id: f"author-{platform}",
        "title": f"{platform} publication type case",
        "content": "Disposable parser acceptance input.",
        "captured_at": CAPTURED_AT,
    }
    return record, note_id


def _assert_source_instant(value: str, expected: datetime = SOURCE_INSTANT) -> None:
    assert isinstance(value, str)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed == expected
    assert parsed.date() == expected.date()


def test_native_publication_types_are_safe_across_all_platform_specs(
    initialized_note_database,
):
    database, connection = initialized_note_database
    records = []
    expected = {}
    object_sentinel = object()

    for platform, spec in PLATFORM_NATIVE_FIELDS.items():
        numeric_record, numeric_id = _native_record(platform, "numeric")
        unit = PROVEN_UNIX_UNITS.get(platform)
        if unit == "milliseconds":
            numeric_record[spec.published_at] = SOURCE_SECONDS * 1000
        else:
            numeric_record[spec.published_at] = SOURCE_SECONDS
        records.append(numeric_record)
        expected[numeric_id] = ("numeric", bool(unit))

        numeric_string_record, numeric_string_id = _native_record(
            platform, "numeric-string"
        )
        numeric_string_value = (
            SOURCE_SECONDS * 1000 if unit == "milliseconds" else SOURCE_SECONDS
        )
        numeric_string_record[spec.published_at] = str(numeric_string_value)
        records.append(numeric_string_record)
        expected[numeric_string_id] = ("numeric-string", bool(unit))

        if platform in {"douyin", "reddit"}:
            fractional_record, fractional_id = _native_record(
                platform, "numeric-float"
            )
            fractional_record[spec.published_at] = SOURCE_SECONDS + 0.125
            records.append(fractional_record)
            expected[fractional_id] = ("numeric-float", True)

        bool_record, bool_id = _native_record(platform, "bool")
        bool_record[spec.published_at] = True
        records.append(bool_record)
        expected[bool_id] = ("unknown", False)

        object_record, object_id = _native_record(platform, "object")
        object_record[spec.published_at] = object_sentinel
        records.append(object_record)
        expected[object_id] = ("unknown", False)

        nan_record, nan_id = _native_record(platform, "nan")
        nan_record[spec.published_at] = float("nan")
        records.append(nan_record)
        expected[nan_id] = ("unknown", False)

        out_of_range_record, out_of_range_id = _native_record(
            platform, "out-of-range"
        )
        out_of_range_record[spec.published_at] = 10**1000
        records.append(out_of_range_record)
        expected[out_of_range_id] = ("unknown", False)

        null_record, null_id = _native_record(platform, "null")
        null_record[spec.published_at] = None
        records.append(null_record)
        expected[null_id] = ("unknown", False)

        captured_record, captured_id = _native_record(platform, "captured-only")
        # No source publication field: capture time must not become publication.
        records.append(captured_record)
        expected[captured_id] = ("captured-only", False)

        update_record, update_id = _native_record(platform, "update-only")
        update_record["last_update_time"] = "2026-09-19T08:30:00+08:00"
        update_record["updated_at"] = "2026-09-19T08:30:00+08:00"
        records.append(update_record)
        expected[update_id] = ("update-only", False)

        string_record, string_id = _native_record(platform, "source-string")
        string_record[spec.published_at] = SOURCE_ISO_WITH_OFFSET
        records.append(string_record)
        expected[string_id] = ("source-string", True)

    snapshots = [dict(record) for record in records]
    result = import_multi_platform_records(records, connection=connection)
    connection.commit()

    assert result["total"] == 21 * 10 + 2
    failures = [
        {
            "platform": records[item["index"]]["platform"],
            "case": records[item["index"]][
                PLATFORM_NATIVE_FIELDS[records[item["index"]]["platform"]].content_id
            ].rsplit("-", 1)[-1],
            "error": item["error"],
        }
        for item in result["details"]
        if item["status"] == "failed"
    ]
    failure_summary = {
        "per_platform": dict(Counter(item["platform"] for item in failures)),
        "per_case": dict(Counter(item["case"] for item in failures)),
        "error_types": dict(Counter(item["error"] for item in failures)),
    }
    assert result["failed"] == 0, failure_summary
    assert result["imported"] == 21 * 10 + 2
    assert result["skipped"] == 0
    assert records == snapshots
    for record in records:
        if record.get("platform"):
            spec = PLATFORM_NATIVE_FIELDS[record["platform"]]
            if record.get(spec.published_at) is object_sentinel:
                assert record[spec.published_at] is object_sentinel

    rows = {
        row["note_id"]: row
        for row in connection.execute(
            "SELECT note_id, publish_date, publish_datetime, captured_at FROM notes"
        )
    }
    assert set(rows) == set(expected)

    for note_id, (case, has_source_time) in expected.items():
        row = rows[note_id]
        assert isinstance(row["publish_datetime"], str)
        assert isinstance(row["publish_date"], str)
        if case in {"numeric", "numeric-string"} and has_source_time:
            _assert_source_instant(row["publish_datetime"])
            assert row["publish_date"] == row["publish_datetime"]
        elif case == "numeric-float" and has_source_time:
            _assert_source_instant(
                row["publish_datetime"], SOURCE_INSTANT.replace(microsecond=125000)
            )
            assert row["publish_date"] == row["publish_datetime"]
        elif case == "source-string" and has_source_time:
            assert row["publish_datetime"] == SOURCE_ISO_WITH_OFFSET
            _assert_source_instant(row["publish_datetime"])
        else:
            assert row["publish_datetime"] == ""
            assert row["publish_date"] == ""

        assert row["captured_at"] == CAPTURED_AT


def test_publication_display_text_accepts_only_explicit_absolute_formats(
    initialized_note_database,
):
    _, connection = initialized_note_database
    records = []
    expected = {}
    valid_by_platform = {
        platform: [
            ("calendar-date", "2026-09-18"),
            ("iso-with-zone", SOURCE_ISO_WITH_OFFSET),
        ]
        for platform in PLATFORM_NATIVE_FIELDS
    }
    valid_by_platform["web_rss"].append(("rfc2822-feed", SOURCE_RFC2822))
    valid_by_platform["web_atom"].append(("rfc2822-feed", SOURCE_RFC2822))
    valid_by_platform["weibo"].append(("weibo-full-year", SOURCE_WEIBO))
    unknown_displays = [
        "04-08",                         # yearless
        "2026-02-29",                    # impossible calendar date
        "2026-09-18T04:00:00",           # source timezone absent
        "2026-09-18T04:00:00+25:00",     # invalid source timezone
        "编辑于2026-09-29",                # update display, not publication
        "3天前",                          # relative display
        "刚刚",                           # relative display
    ]

    for platform, spec in PLATFORM_NATIVE_FIELDS.items():
        for case, value in valid_by_platform[platform]:
            record, note_id = _native_record(platform, case)
            record[spec.published_at] = value
            records.append(record)
            expected[note_id] = value

        for index, value in enumerate(unknown_displays):
            record, note_id = _native_record(platform, f"unknown-display-{index}")
            record[spec.published_at] = value
            records.append(record)
            expected[note_id] = ""

    snapshots = [dict(record) for record in records]
    result = import_multi_platform_records(records, connection=connection)
    connection.commit()

    assert result["total"] == len(records) == len(expected)
    failures = [item for item in result["details"] if item["status"] == "failed"]
    assert result["failed"] == 0, failures
    assert result["imported"] == len(records)
    assert records == snapshots

    rows = {
        row["note_id"]: row
        for row in connection.execute(
            "SELECT note_id, publish_date, publish_datetime, captured_at FROM notes"
        )
    }
    assert set(rows) == set(expected)
    for note_id, expected_publication in expected.items():
        row = rows[note_id]
        assert isinstance(row["publish_datetime"], str)
        assert isinstance(row["publish_date"], str)
        assert row["publish_datetime"] == expected_publication
        assert row["publish_date"] == expected_publication
        assert row["captured_at"] == CAPTURED_AT


def test_native_field_catalog_retains_twenty_platforms_and_adds_wechat():
    assert len(PLATFORM_NATIVE_FIELDS) == 21
    assert 'wechat' in PLATFORM_NATIVE_FIELDS
