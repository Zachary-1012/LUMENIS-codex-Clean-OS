# -*- coding: utf-8 -*-
"""Shared Learning operation-pattern tests."""
from __future__ import annotations

from lumenis.shared.learning.operations import OperationLearning


def test_operation_learning_records_grounded_status(tmp_path):
    learning = OperationLearning(data_dir=tmp_path, enabled=True)

    learning.record_operation(
        "collector_refresh",
        {"subject": "test"},
        {"ok": True, "count": 3},
        duration_ms=120,
    )
    learning.record_operation(
        "collector_refresh",
        {"subject": "test"},
        {"ok": False, "error": "timeout"},
        duration_ms=6100,
    )

    status = learning.get_learning_status()
    assert status["owner"] == "lumenis.shared.learning.operations"
    assert status["total_learning_count"] == 2
    assert status["total_operation_records"] == 2
    assert status["production_truth_write"] is False
    assert status["success_rate"] == 0.5

    suggestions = learning.get_optimization_suggestion("collector_refresh")
    assert suggestions
    assert any("成功率" in item for item in suggestions)
    assert any("耗时" in item for item in suggestions)


def test_operation_learning_persists_across_instances(tmp_path):
    first = OperationLearning(data_dir=tmp_path, enabled=True)
    first.record_operation(
        "report_generation",
        {"report_type": "daily"},
        {"ok": True},
        duration_ms=200,
    )

    restarted = OperationLearning(data_dir=tmp_path, enabled=True)
    history = restarted.get_operation_history("report_generation", limit=10)
    assert len(history) == 1
    assert history[0]["operation_type"] == "report_generation"
    assert history[0]["success"] is True


def test_operation_learning_never_claims_web_retrieval(tmp_path):
    learning = OperationLearning(data_dir=tmp_path, enabled=True)
    status = learning.get_learning_status()
    assert status["production_truth_write"] is False
    assert learning.get_operation_history("web_sentiment_search") == []
