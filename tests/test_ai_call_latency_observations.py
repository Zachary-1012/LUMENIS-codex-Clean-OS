"""Observed latency values stay distinct from missing or invalid inputs."""
from __future__ import annotations

import sqlite3

import pytest

import ai_call_logger as acl
from lumenis.shared.evaluation.ai import record_rule_vs_ai
from lumenis.shared.database.repository import DatabaseRepository
from lumenis.shared.learning.loop import LearningLoop


@pytest.fixture
def temp_ai_call_db(tmp_path, monkeypatch):
    path = str(tmp_path / "ai_call_latency.db")
    repository = DatabaseRepository(path)
    monkeypatch.setattr(acl, "get_repository", lambda: repository)
    assert acl.init_db() is True
    return path


def _stored_latency(db_path, call_id):
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT latency_ms FROM ai_call_logs WHERE id=?", (call_id,),
        ).fetchone()
    assert row is not None
    return row[0]


def test_omitted_latency_is_stored_as_unknown_not_schema_default_zero(temp_ai_call_db):
    call_id = acl.log_call(provider="latency_default_test")

    assert call_id is not None
    assert _stored_latency(temp_ai_call_db, call_id) is None


def test_record_rule_vs_ai_preserves_unknown_and_measured_zero_latency(temp_ai_call_db):
    omitted_id = record_rule_vs_ai(
        provider="wrapper_latency_test",
        model="test-model",
        rule_result="rule",
        ai_result="ai",
        final_result="final",
    )
    zero_id = record_rule_vs_ai(
        provider="wrapper_latency_test",
        model="test-model",
        rule_result="rule",
        ai_result="ai",
        final_result="final",
        latency_ms=0,
    )

    assert omitted_id is not None
    assert zero_id is not None
    assert _stored_latency(temp_ai_call_db, omitted_id) is None
    assert _stored_latency(temp_ai_call_db, zero_id) == 0


@pytest.mark.parametrize(
    ("latency", "expected"),
    [
        (None, None),
        (-1, None),
        ("12", None),
        (True, None),
        (False, None),
        (float("inf"), None),
        (float("-inf"), None),
        (float("nan"), None),
        (2**63, None),
        (0, 0),
        (125, 125),
        (1.75, 1.75),
    ],
)
def test_log_call_keeps_only_finite_nonnegative_real_latency(
    temp_ai_call_db, latency, expected,
):
    call_id = acl.log_call(provider="latency_value_test", latency_ms=latency)

    assert call_id is not None
    assert _stored_latency(temp_ai_call_db, call_id) == expected


def test_recorded_correction_rate_is_incidence_not_review_accuracy(temp_ai_call_db):
    no_record_id = acl.log_call(provider="correction_incidence_test", latency_ms=4)
    corrected_id = acl.log_call(
        provider="correction_incidence_test",
        human_correction="recorded reviewer correction",
        latency_ms=8,
    )
    assert no_record_id is not None
    assert corrected_id is not None

    with sqlite3.connect(temp_ai_call_db) as connection:
        no_record = connection.execute(
            "SELECT human_correction FROM ai_call_logs WHERE id=?", (no_record_id,),
        ).fetchone()
    assert no_record == ("",)

    result = LearningLoop(db_path=temp_ai_call_db, enabled=True).analyze_call_quality(
        days=7, provider="correction_incidence_test",
    )
    assert result["human_correction_count"] == 1
    assert result["human_correction_rate"] == 0.5
    assert result["metric_definitions"]["human_correction_rate"] == {
        "numerator": "calls_with_nonempty_human_correction",
        "denominator": "calls_with_known_recorded_correction_state",
        "meaning": (
            "recorded correction incidence among calls with a known "
            "correction state; not review accuracy"
        ),
    }
    assert result["human_review_coverage"] == {
        "state": "unknown", "reviewed_calls": None, "coverage_rate": None,
    }


def test_logged_zero_is_preserved_and_analyzer_marks_provenance_unresolved(temp_ai_call_db):
    call_id = acl.log_call(provider="latency_zero_test", latency_ms=0)
    assert call_id is not None
    assert _stored_latency(temp_ai_call_db, call_id) == 0

    result = LearningLoop(db_path=temp_ai_call_db, enabled=True).analyze_call_quality(
        days=7, provider="latency_zero_test",
    )
    assert result["avg_latency_ms"] == 0.0
    assert result["metric_samples"]["avg_latency_ms"]["zero_value_samples"] == 1
    assert result["metric_samples"]["avg_latency_ms"]["zero_value_provenance"] == (
        "unresolved_legacy_default_or_measured_zero"
    )
