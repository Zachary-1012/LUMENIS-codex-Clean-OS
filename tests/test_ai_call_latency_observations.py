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


def test_recorded_correction_count_does_not_invent_review_denominator(temp_ai_call_db):
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
    assert result["human_correction_rate"] is None
    assert result["human_correction_state"] == "REVIEW_DENOMINATOR_NOT_RECORDED"
    assert result["metric_definitions"]["human_correction_rate"] == {
        "numerator": "calls_with_nonempty_human_correction",
        "denominator": "reviewed_calls_not_recorded",
        "meaning": (
            "rate is unavailable because the reviewed-call denominator "
            "is not recorded; the numerator is an observed correction count"
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
    assert result["avg_latency_ms"] is None
    assert result["metric_samples"]["avg_latency_ms"]["valid_samples"] == 0
    assert result["metric_samples"]["avg_latency_ms"]["unknown_samples"] == 1
    assert result["metric_samples"]["avg_latency_ms"]["zero_value_samples"] == 1
    assert result["metric_samples"]["avg_latency_ms"]["zero_value_provenance"] == (
        "unresolved_legacy_default_or_measured_zero"
    )


def test_quality_average_uses_observed_positive_samples_only(temp_ai_call_db):
    for latency in (None, 0, 10, 30):
        assert acl.log_call(provider="latency_mixed_test", latency_ms=latency)
    result = LearningLoop(db_path=temp_ai_call_db, enabled=True).analyze_call_quality(
        days=7, provider="latency_mixed_test",
    )
    assert result["total_calls"] == 4
    assert result["avg_latency_ms"] == 20.0
    samples = result["metric_samples"]["avg_latency_ms"]
    assert samples["valid_samples"] == 2
    assert samples["unknown_samples"] == 2
    assert samples["state"] == "partial"
    assert samples["zero_value_samples"] == 1
