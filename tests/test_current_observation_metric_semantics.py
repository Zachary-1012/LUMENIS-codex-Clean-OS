"""Current observation metrics preserve unknown-vs-zero and Evidence lineage."""
from __future__ import annotations

import json
import sqlite3

import pytest

from tests.test_social_observation_transaction import (
    _bind,
    _capture,
    _insert_note,
    _prepared,
    _snapshot,
    social_case,
)
from tests.test_collector_transaction_truth import (
    _approve_and_collect_once,
    _pipeline_counts,
    _post,
    _snapshot as _collector_snapshot,
    collector_case,
)


@pytest.mark.parametrize(
    ("current_likes", "expected_likes"),
    [(None, None), (0, 0)],
    ids=["unknown-does-not-retain-stale-value", "measured-zero-is-preserved"],
)
def test_current_observation_does_not_reuse_stale_metric(
    social_case, current_likes, expected_likes,
):
    case = social_case
    note_id = "hk-current-metric-semantics-001"
    first = _prepared(case, _capture(note_id, likes=17))
    with case["database"].get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _insert_note(case, first, connection=connection)
        bound_first = _bind(case, first, connection=connection)
        assert connection.in_transaction is True
    assert bound_first["ok"] is True, bound_first

    current = _prepared(case, _capture(
        note_id,
        title="广州太古汇当前观察",
        content="广州太古汇当前来源观察记录",
        likes=current_likes,
        partial_comment_rows=0,
        total_comments=0,
        collects=0,
        shares=0,
    ))
    with case["database"].get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _insert_note(case, current, connection=connection)
        bound_current = _bind(case, current, connection=connection)
        assert connection.in_transaction is True

    assert bound_current["ok"] is True, bound_current
    assert bound_current["observation_changed"] is True
    after = _snapshot(case["db_path"], note_id)
    assert after["note"][6:10] == (expected_likes, 0, 0, 0)
    assert after["canonical"][7:11] == (expected_likes, 0, 0, 0)
    assert after["native"][5:9] == (expected_likes, 0, 0, 0)
    assert after["note"][-2:] == ("VERIFIED", str(bound_first["evidence_ref"]))
    assert after["canonical"][-2:] == (
        "VERIFIED", str(bound_first["evidence_ref"]),
    )
    raw_native = json.loads(after["native"][9])
    assert raw_native["_lumenis_evidence_id"] == bound_current["evidence_ref"]
    assert raw_native["liked_count"] == expected_likes


def test_changed_observation_updates_canonical_current_evidence_keeps_scope_evidence(
    social_case,
):
    case = social_case
    note_id = "hk-current-evidence-lineage-001"
    first = _prepared(case, _capture(note_id, likes=17))
    with case["database"].get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _insert_note(case, first, connection=connection)
        bound_first = _bind(case, first, connection=connection)
        assert connection.in_transaction is True
    assert bound_first["ok"] is True, bound_first

    current = _prepared(case, _capture(
        note_id,
        title="广州太古汇最新来源观察",
        content="广州太古汇最新来源正文与互动数据",
        likes=29,
        total_comments=42,
        collects=13,
        shares=7,
    ))
    with case["database"].get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _insert_note(case, current, connection=connection)
        bound_current = _bind(case, current, connection=connection)
        assert connection.in_transaction is True

    assert bound_current["ok"] is True, bound_current
    assert bound_current["observation_changed"] is True
    with sqlite3.connect(str(case["db_path"])) as connection:
        canonical_evidence = connection.execute(
            "SELECT evidence_ref,scope_evidence_ref FROM canonical_data "
            "WHERE source_id=? AND product_id='CTH'", (note_id,),
        ).fetchone()
    assert canonical_evidence == (
        str(bound_current["evidence_ref"]), str(bound_first["evidence_ref"]),
    )


def test_unchanged_observation_repairs_canonical_link_and_preserves_analysis(social_case):
    case = social_case
    note_id = "hk-unchanged-canonical-reconciliation-001"
    observation = _prepared(case, _capture(note_id, likes=None))
    with case["database"].get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _insert_note(case, observation, connection=connection)
        initial = _bind(case, observation, connection=connection)
        assert connection.in_transaction is True
    assert initial["ok"] is True, initial

    with sqlite3.connect(str(case["db_path"])) as connection:
        connection.execute(
            "UPDATE canonical_data SET evidence_ref='',engagement_likes=17,"
            "captured_at='legacy-capture-time',publish_datetime='legacy-publish-time',"
            "sentiment='negative',ai_analysis='reviewed legacy analysis' "
            "WHERE source_id=? AND product_id='CTH'", (note_id,),
        )

    before_evidence_count = len(_snapshot(case["db_path"], note_id)["evidence"])
    with case["database"].get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        unchanged = _bind(case, observation, connection=connection)
        assert connection.in_transaction is True

    assert unchanged["ok"] is True, unchanged
    assert unchanged["observation_changed"] is False
    after = _snapshot(case["db_path"], note_id)
    assert len(after["evidence"]) == before_evidence_count == 1
    with sqlite3.connect(str(case["db_path"])) as connection:
        canonical = connection.execute(
            "SELECT evidence_ref,scope_evidence_ref,captured_at,publish_datetime,"
            "sentiment,ai_analysis,engagement_likes,engagement_comments,"
            "engagement_collects,engagement_shares FROM canonical_data "
            "WHERE source_id=? AND product_id='CTH'", (note_id,),
        ).fetchone()
    assert canonical == (
        str(initial["evidence_ref"]), str(initial["evidence_ref"]),
        "legacy-capture-time", "legacy-publish-time", "negative",
        "reviewed legacy analysis", None, 31, 8, 4,
    )


def test_unchanged_collect_search_reconciles_legacy_canonical_without_new_history(
    collector_case,
):
    case = collector_case
    first = _approve_and_collect_once(case)
    first_snapshot = _collector_snapshot(case)
    assert first_snapshot["note"] is not None
    source_id = first_snapshot["note"][0]
    with sqlite3.connect(str(case["db_path"])) as connection:
        initial_canonical = connection.execute(
            "SELECT evidence_ref,scope_evidence_ref,captured_at,publish_datetime,"
            "sentiment,ai_analysis,engagement_likes FROM canonical_data "
            "WHERE source_id=?", (source_id,),
        ).fetchone()
        note_times = connection.execute(
            "SELECT captured_at,publish_datetime,scope_evidence_ref FROM notes "
            "WHERE note_id=?", (source_id,),
        ).fetchone()
        connection.execute(
            "UPDATE canonical_data SET evidence_ref='',engagement_likes=17,"
            "sentiment='negative',ai_analysis='reviewed existing analysis' "
            "WHERE source_id=?", (source_id,),
        )
    assert initial_canonical is not None
    evidence_ref, scope_ref, canonical_captured, canonical_published, _, _, _ = initial_canonical
    assert evidence_ref == str(first["evidence_ref"])
    counts_before = _pipeline_counts(case["db_path"])
    history_before = _collector_snapshot(case)

    unchanged = _post(case).get_json()

    assert unchanged["ok"] is True, unchanged
    assert unchanged["refresh_verified"] is True, unchanged
    assert unchanged["canonical_synced"] == 1
    assert unchanged["evidence_ref"] == str(first["evidence_ref"])
    after = _collector_snapshot(case)
    assert _pipeline_counts(case["db_path"]) == counts_before
    assert after["metrics"] == history_before["metrics"]
    assert len(after["metrics"]) == 1
    assert after["note"] is not None
    assert after["canonical"] is not None
    assert after["note"][0] == after["canonical"][0] == source_id
    assert after["note"][-1] == after["canonical"][-1] == scope_ref
    with sqlite3.connect(str(case["db_path"])) as connection:
        canonical = connection.execute(
            "SELECT evidence_ref,scope_evidence_ref,captured_at,publish_datetime,"
            "sentiment,ai_analysis,engagement_likes FROM canonical_data "
            "WHERE source_id=?", (source_id,),
        ).fetchone()
        note_after_times = connection.execute(
            "SELECT captured_at,publish_datetime,scope_evidence_ref FROM notes "
            "WHERE note_id=?", (source_id,),
        ).fetchone()
    assert canonical == (
        str(first["evidence_ref"]), scope_ref, canonical_captured,
        canonical_published, "negative", "reviewed existing analysis", None,
    )
    # A genuine reread may advance Raw capture time; the saved Canonical
    # observation time, source publication and scope proof remain unchanged.
    assert note_after_times[0]
    assert note_after_times[1:] == note_times[1:]
