# -*- coding: utf-8 -*-
"""UDIP V1.0 P6: Cross-surface metric consistency checks.

The fixture uses the current Shared Database repository and reporting owner,
with a disposable database so every SQL comparison sees the same deterministic
rows and cannot read the workstation's production database.
"""
import importlib
import json

import pytest

from lumenis.shared.database import DatabaseRepository, apply_business_schema, migrations


REPORT_DATE = "2026-10-08"
SCOPE = {"product_id": "CTH", "domain_id": "cth", "subject_id": "UDIP-SYNTHETIC",
         "brand_focus_id": None, "global_scope": False}
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
    # Bring the synthetic workspace to the same canonical schema as normal
    # startup before recording any signed Evidence. Startup migration backups
    # must never encounter a fixture-created signature in an unversioned DB.
    assert migrations.migrate() is True
    with repository.connection() as connection:
        assert migrations.get_current_version(connection) == migrations.CURRENT_VERSION

    from canonical_data import CanonicalRecord, ensure_canonical_table, persist_canonical
    from lumenis.shared.database.business_schema import ensure_business_scope_storage
    from lumenis.shared.evidence import store as evidence_store
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({
        "udip-test": "isolated-udip-synthetic-signing-key",
    }))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "udip-test")
    evidence_store.init_evidence_store(str(db_path))
    with repository.transaction() as connection:
        evidence_store.ensure_evidence_schema(connection)
        ensure_business_scope_storage(connection)
        ensure_canonical_table(connection=connection)

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
        for note_id, title, *_ in notes:
            evidence_id = evidence_store.record_evidence(
                connection=connection, source="public_http", project="LUMENIS",
                product="CTH", domain_id="cth", subject_id=SCOPE["subject_id"],
                feature_id="UDIP_SQL_PARITY_TEST", test_name="synthetic_scope_binding",
                result="PASS", status="verified", inputs={"source_ids": [note_id]},
                outputs={"scope_admitted": True},
            )
            connection.execute(
                "UPDATE notes SET subject_id=?,scope_status='VERIFIED',scope_evidence_ref=? WHERE note_id=?",
                (SCOPE["subject_id"], str(evidence_id), note_id),
            )
            persist_canonical(connection, CanonicalRecord(
                canonical_id=f"canonical-{note_id}", product_id="CTH", domain_id="cth",
                subject_id=SCOPE["subject_id"], scope_status="VERIFIED", scope_evidence_ref=str(evidence_id),
                source_id=note_id, external_id=note_id, source_type="note", source_table="notes",
                source_platform="synthetic", title=title, content=title,
                captured_at=REPORT_DATE + " 12:00:00", publish_datetime=REPORT_DATE,
                raw_ref=json.dumps({"table": "notes", "note_id": note_id}),
            ))
    # Use the real scoped writer rather than an unsigned direct events INSERT.
    exact = daily.db._normalize_event_scope(SCOPE, allow_global=False)
    daily.db.upsert_event({
        "event_key": daily.db._event_scope_token(exact) + ".udip-event",
        "title": "广州太古汇停车体验反馈", "summary": "固定日期的一致性夹具事件",
        "first_seen": REPORT_DATE, "last_seen": REPORT_DATE, "event_date": REPORT_DATE,
        "risk_level": "medium", "risk_score": 20, "status": "active",
    }, scope=exact, mentions=[{"source_type": "note", "source_id": row[0]} for row in notes[:2]])

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
    summary = daily.generate_today_summary(REPORT_DATE, scope=SCOPE)

    notes = daily.db.get_scoped_event_source_rows(
        SCOPE, source_types=("note",), date_start=REPORT_DATE, date_end=REPORT_DATE
    )["sources"]
    effective_notes = [
        note for note in notes if note.get("ai_filter_status") == "accepted"
    ]
    if not effective_notes and notes:
        effective_notes = notes
    events = daily.db.get_scoped_events(20, scope=SCOPE,
                                        date_start=REPORT_DATE, date_end=REPORT_DATE)["events"]
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
    # One unclassified sentiment is not a measured zero: composite scores stay unknown.
    assert summary["risk_index"] is None
    assert summary["brand_health_score"] is None
    assert summary["sentiment_coverage"] == {"known": 3, "total": 4, "unknown": 1}
    assert summary["source_coverage"]["complete"] is True
    assert summary["event_coverage"]["complete"] is True
    assert summary["collection_health"] == {**OFFLINE_COLLECTION_HEALTH, "scope": "system-global"}


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


def test_daily_summary_requires_scope(env):
    _, daily, _ = env
    with pytest.raises(ValueError, match='REPORT_SCOPE_OR_DATE_INVALID'):
        daily.generate_today_summary(REPORT_DATE)


def test_daily_summary_complete_dimensions_match_scoped_owner(env):
    _, daily, repository = env
    with repository.transaction() as connection:
        connection.execute("UPDATE notes SET sentiment='neutral' WHERE note_id='udip-unknown'")
        connection.execute('UPDATE notes SET is_official=0')
    notes = daily.db.get_scoped_event_source_rows(SCOPE, source_types=('note',),
                                                date_start=REPORT_DATE, date_end=REPORT_DATE)['sources']
    events = daily.db.get_scoped_events(20, scope=SCOPE)['events']
    summary = daily.generate_today_summary(REPORT_DATE, scope=SCOPE)
    expected_risk = daily.calculate_risk_index(notes, events)
    expected_health = daily.calculate_brand_health_score(notes, expected_risk)
    assert summary['risk_index'] == expected_risk
    assert summary['brand_health_score'] == expected_health
    assert 0.0 <= expected_risk <= 100.0
    assert 0.0 <= expected_health <= 100.0
    assert summary['effective_count'] == 4 and summary['events_count'] == 1


def test_daily_summary_rejects_unsigned_source_projection(env):
    _, daily, repository = env
    with repository.transaction() as connection:
        connection.execute("UPDATE notes SET scope_evidence_ref='999999' WHERE note_id='udip-positive'")
    summary = daily.generate_today_summary(REPORT_DATE, scope=SCOPE)
    assert summary['source_coverage']['complete'] is False
    assert summary['source_rejected_count'] >= 1
    assert summary['total_found'] is None
    assert summary['risk_index'] is None
