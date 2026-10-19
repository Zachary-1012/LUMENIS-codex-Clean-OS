"""Missing and invalid call-quality fields must remain distinct from zero."""
from __future__ import annotations

import sqlite3

from lumenis.shared.learning.loop import LearningLoop


LEGACY_RESULT_KEYS = {
    "period_days",
    "total_calls",
    "success_count",
    "success_rate",
    "human_correction_count",
    "human_correction_rate",
    "avg_latency_ms",
    "failure_reasons",
    "provider_filter",
}


def _insert_calls(db_path, rows):
    with sqlite3.connect(db_path) as connection:
        connection.executemany(
            """INSERT INTO ai_call_logs
               (provider, model, success, latency_ms, human_correction,
                failure_reason, created_at)
               VALUES ('learning_quality_test', 'fixture', ?, ?, ?, ?, datetime('now'))""",
            rows,
        )


def _analyze(db_path):
    return LearningLoop(db_path=db_path, enabled=True).analyze_call_quality(
        days=7, provider="learning_quality_test",
    )


def _correction_samples(result):
    return {"state": "no_data" if result["total_calls"] == 0 else "unknown",
            "valid_samples": 0, "unknown_samples": result["total_calls"],
            "observed_corrections": result["human_correction_count"],
            "denominator_state": "REVIEWED_CALLS_NOT_RECORDED"}


def _assert_legacy_shape(result):
    assert LEGACY_RESULT_KEYS <= result.keys()
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
    assert set(result["metric_samples"]) == {
        "success_rate", "human_correction_rate", "avg_latency_ms",
    }
    for name, metric in result["metric_samples"].items():
        expected = {"state", "valid_samples", "unknown_samples"}
        if name == "human_correction_rate":
            expected |= {"observed_corrections", "denominator_state"}
        if name == "avg_latency_ms":
            expected |= {"zero_value_samples", "zero_value_provenance"}
        assert set(metric) == expected


def test_no_rows_returns_null_metrics_and_zero_sample_counts(temp_db):
    result = _analyze(temp_db)

    _assert_legacy_shape(result)
    assert result["total_calls"] == 0
    assert result["success_count"] == 0
    assert result["success_rate"] is None
    assert result["human_correction_count"] == 0
    assert result["human_correction_rate"] is None
    assert result["avg_latency_ms"] is None
    assert result["failure_reasons"] == {}
    assert result["metric_samples"]["success_rate"] == {
        "state": "no_data", "valid_samples": 0, "unknown_samples": 0,
    }
    assert result["metric_samples"]["human_correction_rate"] == _correction_samples(result)
    assert result["metric_samples"]["avg_latency_ms"] == {
        "state": "no_data", "valid_samples": 0, "unknown_samples": 0,
        "zero_value_samples": 0, "zero_value_provenance": "no_zero_values",
    }


def test_all_null_samples_are_unknown_not_zero_or_known_failures(temp_db):
    _insert_calls(temp_db, [
        (None, None, None, "timeout"),
        (None, None, None, None),
    ])
    result = _analyze(temp_db)

    _assert_legacy_shape(result)
    assert result["total_calls"] == 2
    assert result["success_count"] == 0
    assert result["success_rate"] is None
    assert result["human_correction_count"] == 0
    assert result["human_correction_rate"] is None
    assert result["avg_latency_ms"] is None
    assert result["failure_reasons"] == {}
    assert result["metric_samples"]["success_rate"] == {
        "state": "unknown", "valid_samples": 0, "unknown_samples": 2,
    }
    assert result["metric_samples"]["human_correction_rate"] == _correction_samples(result)
    assert result["metric_samples"]["avg_latency_ms"] == {
        "state": "unknown", "valid_samples": 0, "unknown_samples": 2,
        "zero_value_samples": 0, "zero_value_provenance": "no_zero_values",
    }


def test_mixed_valid_and_null_samples_use_metric_specific_denominators(temp_db):
    _insert_calls(temp_db, [
        (1, 0, "", None),
        (0, 100, "corrected output", "timeout"),
        (None, None, None, "unknown-success-reason"),
    ])
    result = _analyze(temp_db)

    _assert_legacy_shape(result)
    assert result["total_calls"] == 3
    assert result["success_count"] == 1
    assert result["success_rate"] == 0.5
    assert result["human_correction_count"] == 1
    assert result["human_correction_rate"] is None
    assert result["avg_latency_ms"] == 100.0
    assert result["failure_reasons"] == {"timeout": 1}
    assert result["metric_samples"] == {
        "success_rate": {"state": "partial", "valid_samples": 2, "unknown_samples": 1},
        "human_correction_rate": _correction_samples(result),
        "avg_latency_ms": {
            "state": "partial", "valid_samples": 1, "unknown_samples": 2,
            "zero_value_samples": 1,
            "zero_value_provenance": "unresolved_legacy_default_or_measured_zero",
        },
    }


def test_explicit_zero_values_are_preserved_with_unresolved_latency_provenance(temp_db):
    _insert_calls(temp_db, [(0, 0, "", "timeout")])
    result = _analyze(temp_db)

    _assert_legacy_shape(result)
    assert result["success_count"] == 0
    assert result["success_rate"] == 0.0
    assert result["human_correction_count"] == 0
    assert result["human_correction_rate"] is None
    assert result["avg_latency_ms"] is None
    assert result["failure_reasons"] == {"timeout": 1}
    assert result["metric_samples"]["success_rate"] == {
        "state": "available", "valid_samples": 1, "unknown_samples": 0,
    }
    assert result["metric_samples"]["human_correction_rate"] == _correction_samples(result)
    assert result["metric_samples"]["avg_latency_ms"] == {
        "state": "unknown", "valid_samples": 0, "unknown_samples": 1,
        "zero_value_samples": 1,
        "zero_value_provenance": "unresolved_legacy_default_or_measured_zero",
    }


def test_invalid_latency_and_unknown_success_do_not_enter_denominators(temp_db):
    _insert_calls(temp_db, [
        (1, -1, None, "success-is-not-a-failure"),
        (0, "not-a-duration", None, "timeout"),
        (None, float("inf"), None, "unknown-success-is-not-a-failure"),
        (2, 100, None, "invalid-success-is-not-a-failure"),
        (0, None, None, ""),
    ])
    result = _analyze(temp_db)

    _assert_legacy_shape(result)
    assert result["total_calls"] == 5
    assert result["success_count"] == 1
    assert result["success_rate"] == round(1 / 3, 4)
    assert result["human_correction_rate"] is None
    assert result["avg_latency_ms"] == 100.0
    assert result["failure_reasons"] == {"timeout": 1}
    assert result["metric_samples"] == {
        "success_rate": {"state": "partial", "valid_samples": 3, "unknown_samples": 2},
        "human_correction_rate": _correction_samples(result),
        "avg_latency_ms": {
            "state": "partial", "valid_samples": 1, "unknown_samples": 4,
            "zero_value_samples": 0, "zero_value_provenance": "no_zero_values",
        },
    }


def test_correction_count_never_manufactures_a_review_denominator(temp_db):
    _insert_calls(temp_db, [(1, 10, "corrected", None), (1, 10, "", None)])
    result = _analyze(temp_db)
    assert result["human_correction_count"] == 1
    assert result["human_correction_rate"] is None
    assert result["human_review_coverage"]["reviewed_calls"] is None
    assert result["metric_samples"]["human_correction_rate"]["valid_samples"] == 0
