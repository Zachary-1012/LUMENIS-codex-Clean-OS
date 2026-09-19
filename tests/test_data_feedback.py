"""Isolated tests for the canonical shared-learning feedback loop."""
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from lumenis.shared.learning.feedback import DataFeedbackLoop


@pytest.fixture
def feedback_loop(tmp_path, monkeypatch):
    """Use temporary database and output files; never read or write product data."""
    monkeypatch.setattr(DataFeedbackLoop, "_load_feedback", lambda self: [])
    loop = DataFeedbackLoop()
    loop.db_path = str(tmp_path / "feedback-test.sqlite")
    loop.feedback_file = str(tmp_path / "feedback.json")
    loop.suggestions_file = str(tmp_path / "suggestions.json")

    today = datetime.now()
    yesterday = today - timedelta(days=1)
    loop.fixture_date = today.strftime("%Y-%m-%d")
    with sqlite3.connect(loop.db_path) as connection:
        connection.execute(
            "CREATE TABLE notes (note_id TEXT, sentiment TEXT, collected_at TEXT, brand TEXT)"
        )
        connection.execute(
            "INSERT INTO notes VALUES (?, ?, ?, ?)",
            ("previous-day", "negative", yesterday.strftime("%Y-%m-%d 10:00:00"), "太古汇"),
        )
        for note_id in ("a", "b", "c", "d", "d", "d", "d"):
            connection.execute(
                "INSERT INTO notes VALUES (?, ?, ?, ?)",
                (note_id, "negative", today.strftime("%Y-%m-%d 12:00:00"), "太古汇"),
            )
    return loop


def test_feedback_cycle_analyzes_generates_persists_and_reports(feedback_loop):
    today = feedback_loop.fixture_date

    anomalies = feedback_loop.analyze_report_anomalies(today)
    anomaly_types = {item["type"] for item in anomalies}
    assert {"negative_surge", "brand_complaint_cluster", "sentiment_imbalance",
            "high_duplicate_rate"}.issubset(anomaly_types)

    suggestions = feedback_loop.generate_strategy_suggestions(anomalies)
    assert len(suggestions) == len(anomalies)
    assert all(item["action_items"] for item in suggestions)

    result = feedback_loop.run_feedback_cycle(today)
    assert result["status"] == "feedback_applied"
    assert result["applied_count"] == len(result["suggestions"])
    assert result["applied_count"] > 0

    stats = feedback_loop.get_stats()
    pending = feedback_loop.get_pending_feedback()
    assert stats["total_feedback"] == result["applied_count"]
    assert stats["pending"] == len(pending) == result["applied_count"]
    assert stats["last_feedback"]
    assert len(feedback_loop.get_feedback_history(limit=20)) == result["applied_count"]
    assert json.loads(Path(feedback_loop.suggestions_file).read_text(encoding="utf-8"))
