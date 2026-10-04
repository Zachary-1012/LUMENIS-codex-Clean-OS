"""Current platform metrics retain source-backed, append-only history."""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path

_support_path = Path(__file__).with_name("test_social_observation_transaction.py")
_support_spec = importlib.util.spec_from_file_location(
    "_social_observation_transaction_support", _support_path,
)
assert _support_spec is not None and _support_spec.loader is not None
_support = importlib.util.module_from_spec(_support_spec)
_support_spec.loader.exec_module(_support)

TABLES = _support.TABLES
_bind = _support._bind
_capture = _support._capture
_connect = _support._connect
_insert_note = _support._insert_note
_prepared = _support._prepared
_signed_evidence = _support._signed_evidence
_snapshot = _support._snapshot
social_case = _support.social_case


METRIC_FIELDS = (
    "like_count",
    "comment_count",
    "collect_count",
    "share_count",
    "view_count",
)


def _metric_rows(connection, note_id: str):
    rows = connection.execute(
        "SELECT id, likes, comments, collects, shares, raw_json "
        "FROM metric_snapshots WHERE entity_type='platform_content' "
        "AND entity_key=? ORDER BY id",
        (f"xiaohongshu:{note_id}",),
    ).fetchall()
    return [(tuple(row[:5]), json.loads(row[5])) for row in rows]


def _metric_history(case, note_id: str):
    with _connect(case["db_path"]) as connection:
        return _metric_rows(connection, note_id)


def _all_rows(connection):
    return {
        table: [tuple(row) for row in connection.execute(
            f"SELECT * FROM {table} ORDER BY rowid",
        ).fetchall()]
        for table in TABLES
    }


def _persist(case, raw):
    observation = _prepared(case, raw)
    with case["database"].get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _insert_note(case, observation, connection=connection)
        result = _bind(case, observation, connection=connection)
        assert connection.in_transaction is True
    assert result["ok"] is True, result
    return observation, result


def _current_native_evidence(snapshot) -> int:
    native = json.loads(snapshot["native"][9])
    return int(native["_lumenis_evidence_id"])


def _assert_signed_evidence(case, evidence_id: int):
    rows = _signed_evidence(case["db_path"])
    matches = [record for record, _ in rows if int(record["id"]) == evidence_id]
    assert len(matches) == 1
    return matches[0]


def _assert_metric_payload(payload, expected, evidence_id):
    assert payload["schema_version"] == 2
    assert {name: payload[name] for name in METRIC_FIELDS} == expected
    assert payload["evidence_id"] == evidence_id
    assert payload["source_id"] == payload["canonical_source_id"]


def test_measured_unknown_and_zero_are_distinct_append_only_history(social_case):
    case = social_case
    note_id = "hk-metric-history-measured-unknown-zero"

    _, measured = _persist(case, _capture(note_id))
    measured_id = int(measured["evidence_ref"])
    measured_snapshot = _snapshot(case["db_path"], note_id)
    measured_history = _metric_history(case, note_id)
    assert len(measured_history) == 1
    original_metric_row, original_payload = measured_history[0]
    _assert_metric_payload(original_payload, {
        "like_count": 17,
        "comment_count": 31,
        "collect_count": 8,
        "share_count": 4,
        "view_count": None,
    }, measured_id)
    assert original_metric_row[1:] == (17, 31, 8, 4)
    original_evidence = _assert_signed_evidence(case, measured_id)
    assert _current_native_evidence(measured_snapshot) == measured_id

    _, unknown = _persist(case, _capture(
        note_id,
        likes=None,
        total_comments=None,
        collects=None,
        shares=None,
    ))
    unknown_id = int(unknown["evidence_ref"])
    unknown_history = _metric_history(case, note_id)
    assert len(unknown_history) == 2
    assert unknown_history[0] == (original_metric_row, original_payload)
    unknown_row, unknown_payload = unknown_history[1]
    _assert_metric_payload(unknown_payload, dict.fromkeys(METRIC_FIELDS), unknown_id)
    assert unknown_row[1:] == (None, None, None, None)
    assert _current_native_evidence(_snapshot(case["db_path"], note_id)) == unknown_id
    _assert_signed_evidence(case, unknown_id)

    _, zero = _persist(case, _capture(
        note_id,
        likes=0,
        total_comments=0,
        collects=0,
        shares=0,
    ))
    zero_id = int(zero["evidence_ref"])
    final_snapshot = _snapshot(case["db_path"], note_id)
    final_history = _metric_history(case, note_id)
    assert len(final_history) == 3
    assert final_history[0] == (original_metric_row, original_payload)
    zero_row, zero_payload = final_history[2]
    _assert_metric_payload(zero_payload, {
        "like_count": 0,
        "comment_count": 0,
        "collect_count": 0,
        "share_count": 0,
        "view_count": None,
    }, zero_id)
    assert zero_row[1:] == (0, 0, 0, 0)
    assert _current_native_evidence(final_snapshot) == zero_id
    assert _assert_signed_evidence(case, measured_id) == original_evidence
    _assert_signed_evidence(case, zero_id)
    assert len(_metric_history(case, note_id)) == 3


def test_all_unknown_first_observation_appends_unknown_baseline(social_case):
    case = social_case
    note_id = "hk-metric-history-unknown-baseline"
    _, result = _persist(case, _capture(
        note_id,
        likes=None,
        total_comments=None,
        collects=None,
        shares=None,
    ))
    evidence_id = int(result["evidence_ref"])
    snapshot = _snapshot(case["db_path"], note_id)
    history = _metric_history(case, note_id)

    assert len(history) == 1
    legacy_row, payload = history[0]
    assert legacy_row[1:] == (None, None, None, None)
    _assert_metric_payload(payload, dict.fromkeys(METRIC_FIELDS), evidence_id)
    assert snapshot["native"][5:9] == (None, None, None, None)
    assert _current_native_evidence(snapshot) == evidence_id
    _assert_signed_evidence(case, evidence_id)


def test_identical_source_repeat_does_not_append_duplicate_metric_history(social_case):
    case = social_case
    note_id = "hk-metric-history-identical-repeat"
    observation, first = _persist(case, _capture(note_id))
    first_id = int(first["evidence_ref"])
    before = _snapshot(case["db_path"], note_id)
    before_history = _metric_history(case, note_id)

    with case["database"].get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        repeated = _bind(case, observation, connection=connection)
        assert connection.in_transaction is True

    assert repeated["ok"] is True, repeated
    assert repeated["observation_changed"] is False
    assert int(repeated["evidence_ref"]) == first_id
    assert _snapshot(case["db_path"], note_id) == before
    assert _metric_history(case, note_id) == before_history


def test_content_only_change_refreshes_current_evidence_without_metric_row(social_case):
    case = social_case
    note_id = "hk-metric-history-content-only"
    _, first = _persist(case, _capture(note_id))
    first_id = int(first["evidence_ref"])
    before_history = _metric_history(case, note_id)
    changed_raw = _capture(
        note_id,
        title="广州太古汇春日活动服务更新",
        content="广州太古汇服务体验内容更新，互动指标保持不变",
    )

    _, changed = _persist(case, changed_raw)
    changed_id = int(changed["evidence_ref"])
    after = _snapshot(case["db_path"], note_id)
    after_history = _metric_history(case, note_id)

    assert changed["observation_changed"] is True
    assert changed_id != first_id
    assert after["note"][2:4] == (changed_raw["title"], changed_raw["content"])
    assert json.loads(after["native"][9])["title"] == changed_raw["title"]
    assert _current_native_evidence(after) == changed_id
    assert after_history == before_history
    assert after_history[0][1]["evidence_id"] == first_id
    assert _assert_signed_evidence(case, first_id)
    _assert_signed_evidence(case, changed_id)
    assert len(after_history) == 1


def test_caller_rollback_restores_all_tables_current_values_and_history(social_case):
    case = social_case
    note_id = "hk-metric-history-rollback"
    _, first = _persist(case, _capture(note_id))
    baseline = _snapshot(case["db_path"], note_id)
    first_id = int(first["evidence_ref"])
    with _connect(case["db_path"]) as connection:
        baseline_rows = _all_rows(connection)
        baseline_canonical_evidence_ref = connection.execute(
            "SELECT evidence_ref FROM canonical_data WHERE source_id=? AND product_id='CTH'",
            (note_id,),
        ).fetchone()[0]

    changed_raw = _capture(
        note_id,
        title="广州太古汇回滚验证更新",
        content="广州太古汇回滚验证内容及指标更新",
        likes=29,
        total_comments=42,
        collects=13,
        shares=7,
    )
    observation = _prepared(case, changed_raw)
    with case["database"].get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _insert_note(case, observation, connection=connection)
        staged = _bind(case, observation, connection=connection)
        assert staged["ok"] is True, staged
        assert connection.in_transaction is True
        capture_evidence_id = int(staged["evidence_ref"])
        staged_canonical_evidence_ref = connection.execute(
            "SELECT evidence_ref FROM canonical_data WHERE source_id=? AND product_id='CTH'",
            (note_id,),
        ).fetchone()[0]
        assert staged_canonical_evidence_ref == str(capture_evidence_id)
        assert staged_canonical_evidence_ref != baseline_canonical_evidence_ref
        from lumenis.shared.evidence.store import classify_evidence_integrity

        capture_evidence = connection.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (capture_evidence_id,),
        ).fetchone()
        integrity = classify_evidence_integrity(dict(capture_evidence))
        assert integrity["verified"] is True
        assert integrity["assurance"] == "writer-authenticated"
        staged_rows = _all_rows(connection)
        assert staged_rows != baseline_rows
        assert len(_metric_rows(connection, note_id)) == 2
        staged_native = connection.execute(
            "SELECT raw_data FROM platform_contents "
            "WHERE platform='xiaohongshu' AND platform_content_id=?",
            (note_id,),
        ).fetchone()
        assert int(json.loads(staged_native[0])["_lumenis_evidence_id"]) != first_id
        connection.rollback()

    with _connect(case["db_path"]) as connection:
        assert _all_rows(connection) == baseline_rows
        restored_canonical_evidence_ref = connection.execute(
            "SELECT evidence_ref FROM canonical_data WHERE source_id=? AND product_id='CTH'",
            (note_id,),
        ).fetchone()[0]
    assert restored_canonical_evidence_ref == baseline_canonical_evidence_ref
    assert _snapshot(case["db_path"], note_id) == baseline
    assert _metric_history(case, note_id)[0][1]["evidence_id"] == first_id
    assert len(_metric_history(case, note_id)) == 1
    assert [int(record["id"]) for record, _ in _signed_evidence(case["db_path"])] == [first_id]
