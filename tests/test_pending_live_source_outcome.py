import sqlite3
from types import SimpleNamespace

import pytest

from lumenis.shared.evidence import store
from lumenis.system.collector.adapters import secondary_collection as collection


def _run_pending_intake(monkeypatch, records, reviews, source_result=None):
    source_calls = []
    evidence_calls = []

    def persist_source(connection, *, source_id, **kwargs):
        source_calls.append(source_id)
        if isinstance(source_result, Exception):
            raise source_result
        return dict(source_result or {})

    def record_evidence(**kwargs):
        evidence_calls.append(kwargs)
        return 73

    monkeypatch.setattr(collection, "_persist_pending_live_source_original", persist_source)
    monkeypatch.setattr(
        collection, "_cleanup_collected_source_paths",
        lambda paths: True if not paths else pytest.fail("unexpected staged-file cleanup"),
    )
    monkeypatch.setattr(store, "record_evidence", record_evidence)

    connection = sqlite3.connect(":memory:")
    try:
        result = collection._persist_pending_live_observations(
            connection, platform="douyin", records=records,
            collection_evidence_id=41,
            context={"domain_id": "cth", "subject_id": "SUBJ-1",
                     "brand_focus_id": None, "global_scope": False},
            staged_paths=[], scope={"domain_id": "cth", "subject_id": "SUBJ-1"},
            keyword="task topic",
            authorization=SimpleNamespace(plan_id="plan-1", authorization_ref="auth-1"),
            business_query=object(), max_results=20, reviews=reviews, saved_ids=set(),
        )
    finally:
        connection.close()

    assert len(evidence_calls) == 1
    return result, source_calls, evidence_calls[0]


def _saved_source_result():
    return {
        "status": "SAVED",
        "source_evidence_ref": "app_evidence_records:81",
        "source_artifact_ref": "artifact-81",
        "source_fingerprint": "a" * 64,
    }


def test_expected_exclusion_does_not_fail_saved_pending_intake(monkeypatch):
    result, source_calls, outcome = _run_pending_intake(
        monkeypatch,
        records=[{"content_id": "in-window"}, {"content_id": "out-window"}],
        reviews=[{"platform_content_id": "out-window",
                  "status": "OUTSIDE_REQUESTED_PUBLICATION_PERIOD"}],
        source_result=_saved_source_result(),
    )

    assert source_calls == ["in-window"]
    assert result["summary"]["eligible_pending_records"] == 1
    assert result["summary"]["unassigned_originals_saved"] == 1
    excluded = next(row for row in result["original_refs"] if row["status"] == "EXCLUDED")
    assert excluded["original_observation_ref"] == "app_evidence_records:41"
    assert outcome["result"] == "PASS"
    assert outcome["actual"] == "PENDING_ORIGINALS_PRESERVED"


def test_unavailable_eligible_source_remains_a_partial_failure(monkeypatch):
    result, source_calls, outcome = _run_pending_intake(
        monkeypatch,
        records=[{"content_id": "unavailable"}], reviews=[],
        source_result=ValueError("LIVE_NATIVE_BODY_NOT_VERIFIED"),
    )

    assert source_calls == ["unavailable"]
    assert result["summary"]["eligible_pending_records"] == 1
    assert result["summary"]["unassigned_originals_unavailable"] == 1
    assert outcome["result"] == "FAIL"
    assert outcome["actual"] == "PARTIAL_PENDING_SOURCE_PRESERVATION"


def test_all_excluded_reports_no_eligible_pending_originals(monkeypatch):
    result, source_calls, outcome = _run_pending_intake(
        monkeypatch,
        records=[{"content_id": "boundary"}, {"content_id": "period"}],
        reviews=[
            {"platform_content_id": "boundary", "status": "EXCLUDED_TASK_BOUNDARY"},
            {"platform_content_id": "period",
             "status": "OUTSIDE_REQUESTED_PUBLICATION_PERIOD"},
        ],
    )

    assert source_calls == []
    assert result["summary"]["eligible_pending_records"] == 0
    assert result["summary"]["unassigned_originals_saved"] == 0
    assert outcome["result"] == "PASS"
    assert outcome["actual"] == "NO_ELIGIBLE_PENDING_ORIGINALS"
