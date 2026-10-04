"""Isolated source-time checks for the XHS response parser."""

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALIAS = "_isolated_xhs_parser_source_times"


def _load_source_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load source module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_parser_without_xhs_runtime():
    package_names = (
        ALIAS,
        f"{ALIAS}.system",
        f"{ALIAS}.system.collector",
        f"{ALIAS}.system.collector.runtime",
        f"{ALIAS}.system.collector.runtime.xhs",
    )
    for name in package_names:
        package = types.ModuleType(name)
        package.__path__ = []
        sys.modules[name] = package

    runtime_dir = ROOT / "lumenis" / "system" / "collector" / "runtime"
    xhs_dir = runtime_dir / "xhs"
    try:
        _load_source_module(f"{ALIAS}.system.collector.runtime.base", runtime_dir / "base.py")
        _load_source_module(f"{ALIAS}.system.collector.runtime.xhs.models", xhs_dir / "models.py")
        parser_module = _load_source_module(
            f"{ALIAS}.system.collector.runtime.xhs.parser", xhs_dir / "parser.py"
        )
        return parser_module.XHSParser
    finally:
        for name in tuple(sys.modules):
            if name == ALIAS or name.startswith(f"{ALIAS}."):
                sys.modules.pop(name, None)


XHSParser = _load_parser_without_xhs_runtime()


def test_ambiguous_or_invalid_creation_time_never_becomes_publication():
    for value in (True, "编辑于2026-10-02", "04-08", "今天", "3天前", "2026-02-30", {}, []):
        assert XHSParser._format_time(value) == ""


def test_epoch_creation_date_is_independent_of_host_timezone():
    assert XHSParser._format_time(1756945800000) == "2025-09-04"


def _parse(note_data):
    item = {"note_card": note_data}
    return XHSParser._parse_note_item(item), item


def test_creation_time_wins_while_both_original_times_remain_in_raw_data():
    note_data = {
        "note_id": "creation-and-update",
        "time": "2026-08-04",
        "last_update_time": "2026-10-02",
    }

    note, item = _parse(note_data)

    assert note.publish_date == "2026-08-04"
    assert note.raw_data is item
    assert note.raw_data["note_card"]["time"] == "2026-08-04"
    assert note.raw_data["note_card"]["last_update_time"] == "2026-10-02"
    assert note_data == item["note_card"]


def test_update_only_time_does_not_become_publication():
    note_data = {"note_id": "update-only", "last_update_time": "2026-10-02"}

    note, item = _parse(note_data)

    assert note.publish_date == ""
    assert note.raw_data is item
    assert note.raw_data["note_card"]["last_update_time"] == "2026-10-02"


def test_missing_null_and_empty_creation_times_stay_unknown_with_update_preserved():
    for creation_time in ("missing", None, ""):
        note_data = {"note_id": f"unknown-{creation_time}", "last_update_time": "2026-10-02"}
        if creation_time != "missing":
            note_data["time"] = creation_time

        note, item = _parse(note_data)

        assert note.publish_date == ""
        assert note.raw_data is item
        assert note.raw_data["note_card"]["last_update_time"] == "2026-10-02"
        assert note_data == item["note_card"]


def test_explicit_millisecond_creation_timestamp_is_converted_to_date():
    timestamp_ms = 1756987200000  # 2025-09-04 12:00:00 UTC
    note, _ = _parse({
        "note_id": "millisecond-creation-time",
        "time": timestamp_ms,
        "last_update_time": "2026-10-02",
    })

    assert note.publish_date == "2025-09-04"


def test_supported_calendar_creation_strings_are_normalized():
    for raw_time in ("2026-09-06", "2026/9/6"):
        note, _ = _parse({"note_id": raw_time, "time": raw_time})
        assert note.publish_date == "2026-09-06"


def test_cover_and_avatar_stay_in_raw_data_without_undefined_model_fields():
    item = {
        "note_card": {
            "note_id": "source-identity",
            "cover": {"url_default": "https://example.invalid/cover.jpg"},
            "user": {"nickname": "visible-name", "avatar": "avatar-url"},
        }
    }

    note = XHSParser._parse_note_item(item)

    assert note is not None
    assert note.author_id == ""
    assert note.author_nickname == "visible-name"
    assert note.image_list == ["https://example.invalid/cover.jpg"]
    assert note.raw_data is item
    assert note.raw_data["note_card"]["cover"] == item["note_card"]["cover"]
    assert note.raw_data["note_card"]["user"]["avatar"] == "avatar-url"


def test_unknown_interaction_counts_remain_none_and_measured_zero_stays_zero():
    unknown, _ = _parse({"note_id": "unknown-counts", "interact_info": {}})
    assert (unknown.likes, unknown.comments, unknown.collects, unknown.shares) == (
        None, None, None, None
    )

    zero, _ = _parse({
        "note_id": "zero-counts",
        "interact_info": {
            "liked_count": 0,
            "like_count": 7,
            "comment_count": 0,
            "collected_count": 0,
            "share_count": 0,
        },
    })
    assert (zero.likes, zero.comments, zero.collects, zero.shares) == (0, 0, 0, 0)


def test_invalid_interaction_counts_remain_none():
    note, _ = _parse({
        "note_id": "invalid-counts",
        "interact_info": {
            "liked_count": "invalid",
            "like_count": None,
            "comment_count": "",
            "collected_count": -1,
            "share_count": 1.5,
        },
    })

    assert (note.likes, note.comments, note.collects, note.shares) == (
        None, None, None, None
    )


def test_nickname_is_not_used_as_author_identity_and_alias_count_is_supported():
    note, _ = _parse({
        "note_id": "nickname-and-alias",
        "user": {"nickname": "visible-name"},
        "interact_info": {"liked_count": None, "like_count": 12},
    })

    assert note.author_id == ""
    assert note.author_nickname == "visible-name"
    assert note.likes == 12
