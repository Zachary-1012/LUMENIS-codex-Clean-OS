# -*- coding: utf-8 -*-
"""UDIP V1.0 P6: Cross-surface metric consistency checks.

The fixture uses the current Shared Database repository and reporting owner,
with a disposable database so every SQL comparison sees the same deterministic
rows and cannot read the workstation's production database.
"""
import importlib

import pytest

from lumenis.shared.database import DatabaseRepository, apply_business_schema


REPORT_DATE = "2026-10-08"
OFFLINE_COLLECTION_HEALTH = {
    "complete": None,
    "state": "NOT_RUN",
    "detail": "offline parity fixture",
}


def _load():
    """Load the canonical metric functions and current Shared Reporting owner."""
    canonical_metrics = importlib.import_module("canonical_metrics")
    daily = importlib.import_module("lumenis.shared.reporting.daily")
    return canonical_metrics, daily


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """Bind production callers to a schema-backed, disposable Shared DB."""
    db_path = tmp_path / "udip-consistency.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    repository = DatabaseRepository(str(db_path))
    with repository.transaction() as connection:
        apply_business_schema(connection)

    canonical_metrics, daily = _load()
    # The compatibility database module used by daily.py resolves each query
    # through Shared DatabaseRepository. Pin that binding to this test DB.
    monkeypatch.setattr(daily.db, "get_repository", lambda: repository)

    notes = [
        ("udip-positive", "广州太古汇正面体验", "positive", "low", 10, 2, 1, 1),
        ("udip-neutral", "广州太古汇中性反馈", "neutral", "medium", 4, 1, 0, 2),
        ("udip-negative", "广州太古汇负面反馈", "negative", "high", 12, 3, 2, 1),
        ("udip-unknown", "广州太古汇待核反馈", "unknown", "critical", 3, 0, 1, 0),
    ]
    with repository.transaction() as connection:
        connection.executemany(
            """INSERT INTO notes (
                   note_id, title, body, content, source_keyword, matched_keywords,
                   publish_date, sentiment, risk_level, likes, comments, collects,
                   shares, is_taikoo_verified, relevance_status, ai_filter_status
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    note_id,
                    title,
                    title,
                    title,
                    "广州太古汇",
                    "太古汇",
                    REPORT_DATE,
                    sentiment,
                    risk_level,
                    likes,
                    comments,
                    collects,
                    shares,
                    1,
                    "relevant",
                    "accepted",
                )
                for (
                    note_id,
                    title,
                    sentiment,
                    risk_level,
                    likes,
                    comments,
                    collects,
                    shares,
                ) in notes
            ],
        )
        connection.execute(
            """INSERT INTO events (
                   event_key, title, summary, first_seen, last_seen, event_date,
                   mention_count, source_count, risk_level, risk_score, status,
                   keywords, translations, ai_provider
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "udip-event",
                "广州太古汇停车体验反馈",
                "固定日期的一致性夹具事件",
                REPORT_DATE,
                REPORT_DATE,
                REPORT_DATE,
                2,
                2,
                "medium",
                20,
                "active",
                "[]",
                "{}",
                "rule",
            ),
        )

    # The legacy collection-health check can import an XHS bridge. This SQL
    # parity fixture explicitly isolates that owner and never probes a profile.
    monkeypatch.setattr(
        daily,
        "_collection_health",
        lambda date_str=None: dict(OFFLINE_COLLECTION_HEALTH),
    )
    return canonical_metrics, daily, repository


def test_canonical_metrics_sentiment_matches_sql(env):
    """FN-SENTIMENT-COUNT agrees with direct SQL, including unknown values."""
    canonical_metrics, _, repository = env
    with repository.connection() as connection:
        rows = connection.execute(
            "SELECT sentiment, COUNT(*) AS count FROM notes GROUP BY sentiment"
        ).fetchall()
        sentiment_rows = connection.execute(
            "SELECT sentiment FROM notes"
        ).fetchall()

    sql_map = {row["sentiment"]: row["count"] for row in rows}
    notes = [{"sentiment": row["sentiment"]} for row in sentiment_rows]
    got = canonical_metrics.sentiment_count(notes)
    assert got["total"] == sum(sql_map.values())
    for sentiment, count in sql_map.items():
        assert got.get(sentiment) == count, (
            f"sentiment {sentiment}: canonical={got.get(sentiment)} sql={count}"
        )


def test_canonical_metrics_risk_matches_sql(env):
    """FN-RISK-COUNT keeps high and critical as separate SQL-matched buckets."""
    canonical_metrics, _, repository = env
    with repository.connection() as connection:
        rows = connection.execute(
            "SELECT risk_level, COUNT(*) AS count FROM notes GROUP BY risk_level"
        ).fetchall()
        risk_rows = connection.execute(
            "SELECT risk_level FROM notes"
        ).fetchall()

    sql_map = {row["risk_level"]: row["count"] for row in rows}
    notes = [{"risk_level": row["risk_level"]} for row in risk_rows]
    got = canonical_metrics.risk_count(notes)
    for risk_level in ("high", "medium", "low", "critical"):
        assert got.get(risk_level) == sql_map.get(risk_level, 0), (
            f"risk {risk_level}: canonical={got.get(risk_level)} "
            f"sql={sql_map.get(risk_level, 0)}"
        )


def test_daily_summary_risk_metrics_match_owner_functions(env):
    """The dated daily summary matches its risk functions and canonical date."""
    _, daily, _ = env
    summary = daily.generate_today_summary(REPORT_DATE)

    notes = daily.db.get_notes_by_date_range(REPORT_DATE, REPORT_DATE)
    effective_notes = [
        note for note in notes if note.get("ai_filter_status") == "accepted"
    ]
    if not effective_notes and notes:
        effective_notes = notes
    events = daily.db.get_events(20)
    dated_events = [
        event
        for event in events
        if (event.get("last_seen") or "")[:10] >= REPORT_DATE
        or (event.get("first_seen") or "")[:10] <= REPORT_DATE
        <= (event.get("last_seen") or "")[:10]
    ]
    expected_risk = daily.calculate_risk_index(effective_notes, dated_events)
    expected_health = daily.calculate_brand_health_score(
        effective_notes, expected_risk
    )

    assert summary["date"] == REPORT_DATE
    assert summary["total_found"] == summary["effective_count"] == 4
    assert summary["positive_count"] == summary["neutral_count"] == 1
    assert summary["risk_count"] == 2
    assert summary["events_count"] == 1
    assert summary["risk_index"] == expected_risk
    assert summary["brand_health_score"] == expected_health
    assert 0.0 <= summary["risk_index"] <= 100.0
    assert 0.0 <= summary["brand_health_score"] <= 100.0
    assert summary["collection_health"] == OFFLINE_COLLECTION_HEALTH


def test_five_value_semantics_no_data(env):
    """Empty and missing values remain distinct from measured zero."""
    canonical_metrics, _, _ = env
    empty_sentiment = canonical_metrics.sentiment_count([])
    assert empty_sentiment["total"] == 0
    assert empty_sentiment["quality"]["empty"] is True

    missing_risk = canonical_metrics.risk_count(
        [{"risk_level": None}, {"risk_level": ""}]
    )
    assert missing_risk["missing"] == 2
    assert missing_risk["high"] == 0 and missing_risk["other"] == 0

    # Incomplete interaction totals stay unknown while observed values remain
    # visible; complete fixture rows above exercise the SQL parity case.
    engagement = canonical_metrics.engagement_stats(
        [{"likes": 1}, {"likes": None}]
    )
    assert engagement["sum"] is None
    assert engagement["observed_sum"] == 1
    assert engagement["quality"]["state"] == "PARTIAL"
    assert engagement["quality"]["missing_field_notes"] == 2


def test_engagement_stats_consistency(env):
    """FN-ENGAGEMENT equals SQL SUM over all four complete count fields."""
    canonical_metrics, _, repository = env
    with repository.connection() as connection:
        total_engagement = connection.execute(
            """SELECT SUM(likes + comments + collects + shares)
               FROM notes"""
        ).fetchone()[0]
        rows = connection.execute(
            "SELECT likes, comments, collects, shares FROM notes"
        ).fetchall()

    notes = [
        {
            "likes": row["likes"],
            "comments": row["comments"],
            "collects": row["collects"],
            "shares": row["shares"],
        }
        for row in rows
    ]
    got = canonical_metrics.engagement_stats(notes)
    assert got["count"] == 4
    assert got["quality"]["state"] == "COMPLETE"
    assert got["quality"]["known_field_count"] == got["quality"]["expected_field_count"] == 16
    assert got["sum"] == total_engagement, (
        f"engagement: canonical={got['sum']} sql={total_engagement}"
    )
