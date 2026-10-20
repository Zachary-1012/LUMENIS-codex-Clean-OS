import sqlite3

import pytest

import database as note_database
from canonical_data import ensure_canonical_table, note_to_canonical, persist_canonical
from lumenis.shared.database.business_schema import apply_business_schema


def _connect(path):
    connection = sqlite3.connect(path, timeout=0.05)
    connection.row_factory = sqlite3.Row
    return connection


def _new_notes_db(tmp_path):
    path = tmp_path / "notes.db"
    connection = _connect(path)
    try:
        apply_business_schema(connection)
        connection.commit()
    finally:
        connection.close()
    return path


def test_fix_024_metric_only_upsert_preserves_source_and_analysis(tmp_path):
    """FIX-024: a partial metric upsert must not erase stored source/derived data."""
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note(
            {
                "note_id": "fix-024-metric-only",
                "title": "Original title",
                "content": "Original source content",
                "body": "Original body",
                "source_keyword": "original keyword",
                "type": "video",
                "likes": 11,
                "comments": 4,
                "comments_collected": 2,
                "data_quality_status": "reviewed",
                "data_quality_score": 0.91,
            },
            connection=connection,
        )
        connection.execute(
            "UPDATE notes SET sentiment='negative', sentiment_score=0.8, "
            "risk_level='high', risk_score=71, summary='saved analysis', "
            "topics='[\"stored\"]', subject_type='media', content_type='review' "
            "WHERE note_id=?",
            ("fix-024-metric-only",),
        )
        before = dict(
            connection.execute(
                "SELECT title, note_type, content, body, source_keyword, comments, "
                "comments_collected, sentiment, sentiment_score, risk_level, "
                "risk_score, summary, topics, subject_type, content_type, "
                "data_quality_status, data_quality_score FROM notes WHERE note_id=?",
                ("fix-024-metric-only",),
            ).fetchone()
        )

        row_id, inserted = note_database.insert_note(
            {"note_id": "fix-024-metric-only", "likes": 19},
            connection=connection,
        )

        after = dict(
            connection.execute(
                "SELECT title, note_type, content, body, source_keyword, comments, "
                "comments_collected, sentiment, sentiment_score, risk_level, "
                "risk_score, summary, topics, subject_type, content_type, "
                "data_quality_status, data_quality_score, likes FROM notes "
                "WHERE note_id=?",
                ("fix-024-metric-only",),
            ).fetchone()
        )
        assert row_id > 0
        assert inserted is False
        assert {key: value for key, value in after.items() if key != "likes"} == before
        assert after["likes"] == 19
    finally:
        connection.close()


def test_fix_024_explicit_null_clears_only_present_nullable_fields(tmp_path):
    """FIX-024: explicit null is distinct from an omitted field."""
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note(
            {
                "note_id": "fix-024-null",
                "title": "Original title",
                "type": "article",
                "likes": 8,
                "comments": 5,
                "comments_collected": 3,
                "data_quality_status": "reviewed",
                "data_quality_score": 0.7,
            },
            connection=connection,
        )
        connection.execute(
            "UPDATE notes SET sentiment='positive', sentiment_score=0.6, "
            "risk_level='medium', risk_score=35 WHERE note_id=?",
            ("fix-024-null",),
        )
        connection.commit()

        note_database.insert_note(
            {
                "note_id": "fix-024-null",
                "title": "Updated source title",
                "likes": None,
                "comments_collected": None,
                "sentiment_score": None,
                "risk_score": None,
                "data_quality_status": None,
                "data_quality_score": None,
            },
            connection=connection,
        )

        row = connection.execute(
            "SELECT title, note_type, likes, comments, comments_collected, "
            "sentiment, sentiment_score, risk_level, risk_score, "
            "data_quality_status, data_quality_score FROM notes WHERE note_id=?",
            ("fix-024-null",),
        ).fetchone()
        assert row["title"] == "Updated source title"
        assert row["note_type"] == "article"
        assert row["likes"] is None
        assert row["comments"] == 5
        assert row["comments_collected"] is None
        assert row["sentiment"] == "positive"
        assert row["sentiment_score"] is None
        assert row["risk_level"] == "medium"
        assert row["risk_score"] is None
        assert row["data_quality_status"] is None
        assert row["data_quality_score"] is None
    finally:
        connection.close()


def test_fix_024_same_label_analysis_upsert_preserves_omitted_scores(tmp_path):
    """FIX-024: an unchanged label keeps its previously paired score."""
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note(
            {
                "note_id": "fix-024-label-only-analysis",
                "sentiment": "positive",
                "sentiment_score": 0.65,
                "risk_level": "low",
                "risk_score": 18,
            },
            connection=connection,
        )

        note_database.insert_note(
            {
                "note_id": "fix-024-label-only-analysis",
                "sentiment": "positive",
                "risk_level": "low",
            },
            connection=connection,
        )

        row = connection.execute(
            "SELECT sentiment, sentiment_score, risk_level, risk_score "
            "FROM notes WHERE note_id=?",
            ("fix-024-label-only-analysis",),
        ).fetchone()
        assert tuple(row) == ("positive", 0.65, "low", 18)
    finally:
        connection.close()


def test_fix_024_changed_risk_label_clears_omitted_stale_score(tmp_path):
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note(
            {"note_id": "fix-024-risk-label", "risk_level": "low", "risk_score": 18},
            connection=connection,
        )
        note_database.insert_note(
            {"note_id": "fix-024-risk-label", "risk_level": "high"},
            connection=connection,
        )

        row = connection.execute(
            "SELECT risk_level, risk_score FROM notes WHERE note_id=?",
            ("fix-024-risk-label",),
        ).fetchone()
        assert tuple(row) == ("high", None)
    finally:
        connection.close()


def test_fix_024_incomplete_observation_preserves_explicit_unknown_metrics(tmp_path):
    """FIX-024: incomplete reads cannot turn old measurements into nulls."""
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note(
            {
                "note_id": "fix-024-incomplete",
                "likes": 12,
                "comments_collected": 6,
            },
            connection=connection,
        )
        note_database.insert_note(
            {
                "note_id": "fix-024-incomplete",
                "likes": None,
                "comments_collected": None,
                "_lumenis_metric_observation_complete": False,
            },
            connection=connection,
        )

        row = connection.execute(
            "SELECT likes, comments_collected FROM notes WHERE note_id=?",
            ("fix-024-incomplete",),
        ).fetchone()
        assert tuple(row) == (12, 6)
    finally:
        connection.close()


def test_fix_024_derived_body_update_keeps_omitted_original_title(tmp_path):
    """FIX-024: deriving classifications from a body update keeps its source title."""
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note(
            {
                "note_id": "fix-024-derived",
                "title": "Original title",
                "content": "Original source content",
                "body": "Original body",
                "type": "video",
                "data_quality_status": "reviewed",
                "data_quality_score": 0.91,
            },
            connection=connection,
        )
        note_database.insert_note(
            {"note_id": "fix-024-derived", "body": "Updated derived text"},
            connection=connection,
        )

        row = connection.execute(
            "SELECT title, note_type, content, body, data_quality_status, "
            "data_quality_score FROM notes WHERE note_id=?",
            ("fix-024-derived",),
        ).fetchone()
        assert row["title"] == "Original title"
        assert row["note_type"] == "video"
        assert row["content"] == "Original source content"
        assert row["body"] == "Updated derived text"
        assert row["data_quality_status"] == "reviewed"
        assert row["data_quality_score"] == 0.91
    finally:
        connection.close()


def test_fix_024_blank_quality_status_does_not_replace_saved_state(tmp_path):
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note(
            {
                "note_id": "fix-024-blank-quality",
                "title": "Reviewed title",
                "data_quality_status": "reviewed",
                "data_quality_score": 0.87,
            },
            connection=connection,
        )
        note_database.insert_note(
            {
                "note_id": "fix-024-blank-quality",
                "data_quality_status": "",
                # Existing collectors synthesize this zero when source score is absent.
                "data_quality_score": 0,
            },
            connection=connection,
        )

        row = connection.execute(
            "SELECT data_quality_status, data_quality_score FROM notes WHERE note_id=?",
            ("fix-024-blank-quality",),
        ).fetchone()
        assert tuple(row) == ("reviewed", 0.87)
    finally:
        connection.close()


@pytest.mark.parametrize("observation_complete", [True, False])
def test_fix_024_negative_comments_collected_sentinel_preserves_measurement(
    tmp_path, observation_complete,
):
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note(
            {"note_id": "fix-024-comments-sentinel", "comments_collected": 6},
            connection=connection,
        )
        note_database.insert_note(
            {
                "note_id": "fix-024-comments-sentinel",
                "comments_collected": -1,
                "_lumenis_metric_observation_complete": observation_complete,
            },
            connection=connection,
        )
        measured = connection.execute(
            "SELECT comments_collected FROM notes WHERE note_id=?",
            ("fix-024-comments-sentinel",),
        ).fetchone()[0]
        assert measured == 6

        if observation_complete:
            note_database.insert_note(
                {"note_id": "fix-024-comments-sentinel", "comments_collected": None},
                connection=connection,
            )
            explicit_unknown = connection.execute(
                "SELECT comments_collected FROM notes WHERE note_id=?",
                ("fix-024-comments-sentinel",),
            ).fetchone()[0]
            assert explicit_unknown is None
    finally:
        connection.close()


def test_fix_024_missing_platform_keeps_existing_source_platform(tmp_path):
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note(
            {
                "note_id": "fix-024-existing-platform",
                "source_platform": "douyin",
                "title": "Original",
            },
            connection=connection,
        )
        note_database.insert_note(
            {"note_id": "fix-024-existing-platform", "title": "Updated"},
            connection=connection,
        )

        row = connection.execute(
            "SELECT source_platform, title FROM notes WHERE note_id=?",
            ("fix-024-existing-platform",),
        ).fetchone()
        assert tuple(row) == ("douyin", "Updated")
    finally:
        connection.close()


def test_fix_024_partial_body_update_preserves_classification_without_context(tmp_path):
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note(
            {
                "note_id": "fix-024-classification-context",
                "author_nickname": "Synthetic Creator",
                "author_desc": "",
                "followers": 25000,
                "verified_type": "",
                "title": "Original creator post",
            },
            connection=connection,
        )
        before = connection.execute(
            "SELECT subject_type, content_type FROM notes WHERE note_id=?",
            ("fix-024-classification-context",),
        ).fetchone()
        assert before["subject_type"] == "kol"

        note_database.insert_note(
            {
                "note_id": "fix-024-classification-context",
                "body": "Updated source body",
            },
            connection=connection,
        )

        after = connection.execute(
            "SELECT subject_type, content_type, body FROM notes WHERE note_id=?",
            ("fix-024-classification-context",),
        ).fetchone()
        assert tuple(after) == (before["subject_type"], before["content_type"], "Updated source body")
    finally:
        connection.close()


def test_injected_connection_uses_caller_rollback_and_remains_open(tmp_path):
    path = _new_notes_db(tmp_path)
    connection = _connect(path)

    row_id, inserted = note_database.insert_note(
        {"note_id": "rollback-me", "title": "temporary"},
        connection=connection,
    )

    assert row_id > 0
    assert inserted is True
    assert connection.in_transaction is True
    assert connection.execute(
        "SELECT note_id FROM notes WHERE note_id=?", ("rollback-me",)
    ).fetchone()["note_id"] == "rollback-me"

    connection.rollback()
    assert connection.execute("SELECT 1").fetchone()[0] == 1
    connection.close()

    reopened = _connect(path)
    try:
        assert reopened.execute(
            "SELECT note_id FROM notes WHERE note_id=?", ("rollback-me",)
        ).fetchone() is None
    finally:
        reopened.close()


def test_injected_connection_commit_is_caller_controlled(tmp_path):
    path = _new_notes_db(tmp_path)
    connection = _connect(path)

    note_database.insert_note(
        {"note_id": "commit-me", "source_platform": "xhs", "title": "kept"},
        connection=connection,
    )
    assert connection.in_transaction is True
    assert connection.execute("SELECT 1").fetchone()[0] == 1
    connection.commit()
    assert connection.in_transaction is False
    assert connection.execute("SELECT 1").fetchone()[0] == 1
    connection.close()

    reopened = _connect(path)
    try:
        row = reopened.execute(
            "SELECT title FROM notes WHERE note_id=?", ("commit-me",)
        ).fetchone()
        assert row["title"] == "kept"
    finally:
        reopened.close()


def test_default_connection_still_commits_closes_and_preserves_note_fields(
    tmp_path, monkeypatch
):
    path = _new_notes_db(tmp_path)
    opened_connections = []

    def connect_disposable_db():
        connection = _connect(path)
        opened_connections.append(connection)
        return connection

    monkeypatch.setattr(note_database, "_db_connect_with_retry", connect_disposable_db)

    row_id, inserted = note_database.insert_note(
        {
            "note_id": "default-path",
            "title": "",
            "content": "First sentence。More content",
            "publish_date": "2026-09-30",
            "captured_at": "2026-10-01 12:30:00",
            "data_quality_status": "reviewed",
            "data_quality_score": 0.75,
        }
    )

    assert row_id > 0
    assert inserted is True
    with pytest.raises(sqlite3.ProgrammingError):
        opened_connections[0].execute("SELECT 1")

    reopened = _connect(path)
    try:
        row = reopened.execute(
            "SELECT title, likes, comments, collects, shares, comments_collected, "
            "publish_date, publish_datetime, captured_at, data_quality_status, "
            "data_quality_score FROM notes WHERE note_id=?",
            ("default-path",),
        ).fetchone()
        assert row["title"] == "Firstsentence"
        assert all(row[key] is None for key in ("likes", "comments", "collects", "shares"))
        assert row["comments_collected"] is None
        assert row["publish_date"] == "2026-09-30"
        assert row["publish_datetime"] == "2026-09-30"
        assert row["captured_at"] == "2026-10-01 12:30:00"
        assert row["data_quality_status"] == "reviewed"
        assert row["data_quality_score"] == 0.75
    finally:
        reopened.close()


def test_default_connection_still_rolls_back_and_closes_on_conflict(tmp_path, monkeypatch):
    path = _new_notes_db(tmp_path)
    opened_connections = []

    def connect_disposable_db():
        connection = _connect(path)
        opened_connections.append(connection)
        return connection

    monkeypatch.setattr(note_database, "_db_connect_with_retry", connect_disposable_db)
    note_database.insert_note(
        {
            "note_id": "default-conflict",
            "source_platform": "xhs",
            "title": "Original title",
            "content": "Original content",
        }
    )

    with pytest.raises(ValueError, match="^SOURCE_ID_PLATFORM_CONFLICT$"):
        note_database.insert_note(
            {
                "note_id": "default-conflict",
                "source_platform": "douyin",
                "title": "Replacement title",
                "content": "Replacement content",
            }
        )

    assert len(opened_connections) == 2
    with pytest.raises(sqlite3.ProgrammingError):
        opened_connections[-1].execute("SELECT 1")
    reopened = _connect(path)
    try:
        row = reopened.execute(
            "SELECT source_platform, title, content FROM notes WHERE note_id=?",
            ("default-conflict",),
        ).fetchone()
        assert tuple(row) == ("xhs", "Original title", "Original content")
    finally:
        reopened.close()


def test_same_canonical_platform_alias_updates_without_rewriting_source_spelling(
    tmp_path
):
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note(
            {
                "note_id": "same-platform",
                "source_platform": "xiaohongshu",
                "title": "before",
                "likes": 2,
            },
            connection=connection,
        )
        connection.commit()

        row_id, inserted = note_database.insert_note(
            {"note_id": "same-platform", "title": "after", "likes": 4},
            connection=connection,
        )

        assert row_id > 0
        assert inserted is False
        row = connection.execute(
            "SELECT source_platform, title, likes FROM notes WHERE note_id=?",
            ("same-platform",),
        ).fetchone()
        assert row["source_platform"] == "xiaohongshu"
        assert row["title"] == "after"
        assert row["likes"] == 4
        connection.commit()
    finally:
        connection.close()


@pytest.mark.parametrize("incoming_platform", ["douyin", "unregistered-platform"])
def test_platform_conflict_keeps_note_and_canonical_hash_unchanged(
    tmp_path, incoming_platform
):
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note(
            {
                "note_id": "immutable-source-id",
                "source_platform": "xhs",
                "title": "Original title",
                "content": "Original content",
                "url": "https://example.invalid/original",
            },
            connection=connection,
        )
        connection.commit()

        ensure_canonical_table(connection=connection)
        original_note = connection.execute(
            "SELECT * FROM notes WHERE note_id=?", ("immutable-source-id",)
        ).fetchone()
        persist_canonical(connection, note_to_canonical(dict(original_note)))
        connection.commit()
        before_note = dict(original_note)
        before_canonical = dict(
            connection.execute(
                "SELECT source_platform, content_hash FROM canonical_data "
                "WHERE canonical_id=?",
                ("can_note_immutable-source-id",),
            ).fetchone()
        )

        with pytest.raises(ValueError, match="^SOURCE_ID_PLATFORM_CONFLICT$"):
            note_database.insert_note(
                {
                    "note_id": "immutable-source-id",
                    "source_platform": incoming_platform,
                    "title": "Must not replace original",
                    "content": "Must not replace original",
                },
                connection=connection,
            )
        connection.rollback()
    finally:
        connection.close()

    reopened = _connect(path)
    try:
        after_note = dict(
            reopened.execute(
                "SELECT * FROM notes WHERE note_id=?", ("immutable-source-id",)
            ).fetchone()
        )
        after_canonical = dict(
            reopened.execute(
                "SELECT source_platform, content_hash FROM canonical_data "
                "WHERE canonical_id=?",
                ("can_note_immutable-source-id",),
            ).fetchone()
        )
        assert after_note == before_note
        assert after_note["source_platform"] == "xhs"
        assert after_canonical == before_canonical
        assert after_canonical["content_hash"]
    finally:
        reopened.close()


def test_insert_note_holds_write_lock_until_caller_ends_transaction(tmp_path):
    path = _new_notes_db(tmp_path)
    first = _connect(path)
    second = _connect(path)
    try:
        note_database.insert_note({"note_id": "locked-source"}, connection=first)
        assert first.in_transaction is True

        with pytest.raises(sqlite3.OperationalError, match="locked"):
            second.execute("BEGIN IMMEDIATE")

        first.rollback()
        second.execute("BEGIN IMMEDIATE")
        second.rollback()
    finally:
        first.close()
        second.close()


def _row(connection, note_id, cols):
    return dict(connection.execute(f"SELECT {cols} FROM notes WHERE note_id=?", (note_id,)).fetchone())


def test_sentiment_label_change_without_score_clears_old_score(tmp_path):
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note({"note_id": "s1", "title": "t", "content": "c"}, connection=connection)
        connection.execute("UPDATE notes SET sentiment='positive', sentiment_score=0.8 WHERE note_id='s1'")
        note_database.insert_note({"note_id": "s1", "sentiment": "negative"}, connection=connection)
        row = _row(connection, "s1", "sentiment, sentiment_score")
        assert row == {"sentiment": "negative", "sentiment_score": None}
        connection.execute("UPDATE notes SET sentiment_score=-0.6 WHERE note_id='s1'")
        note_database.insert_note({"note_id": "s1", "sentiment": "negative"}, connection=connection)
        assert _row(connection, "s1", "sentiment_score")["sentiment_score"] == -0.6
    finally:
        connection.close()


def test_quality_status_change_without_score_clears_stale_score(tmp_path):
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note(
            {"note_id": "q1", "title": "t", "content": "c",
             "data_quality_status": "reviewed", "data_quality_score": 0.87},
            connection=connection,
        )
        note_database.insert_note({"note_id": "q1", "data_quality_status": "error"}, connection=connection)
        row = _row(connection, "q1", "data_quality_status, data_quality_score")
        assert row == {"data_quality_status": "error", "data_quality_score": None}
    finally:
        connection.close()


def test_update_fills_missing_classification_without_author_trio(tmp_path, monkeypatch):
    import subject_classifier
    monkeypatch.setattr(subject_classifier, "enrich_note_types", lambda *a, **k: ("media", "review"))
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note({"note_id": "c1", "title": "t", "content": "c"}, connection=connection)
        connection.execute("UPDATE notes SET subject_type='', content_type='' WHERE note_id='c1'")
        note_database.insert_note(
            {"note_id": "c1", "title": "new title", "author_nickname": "a"}, connection=connection,
        )
        assert _row(connection, "c1", "subject_type, content_type") == {
            "subject_type": "media", "content_type": "review",
        }
        # A populated classification is not overwritten by an incomplete payload.
        monkeypatch.setattr(subject_classifier, "enrich_note_types", lambda *a, **k: ("brand", "ad"))
        note_database.insert_note({"note_id": "c1", "title": "again"}, connection=connection)
        assert _row(connection, "c1", "subject_type")["subject_type"] == "media"
    finally:
        connection.close()


def test_classifier_receives_real_is_official_flag(tmp_path, monkeypatch):
    import subject_classifier
    seen = []
    monkeypatch.setattr(subject_classifier, "enrich_note_types",
                        lambda *a, **k: seen.append(a[3]) or ("brand", "official"))
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note({"note_id": "o1", "title": "t", "content": "c",
                                   "author_nickname": "广州太古汇"}, connection=connection)
        connection.execute("UPDATE notes SET is_official=1, subject_type='' WHERE note_id='o1'")
        note_database.insert_note({"note_id": "o1", "title": "t2"}, connection=connection)
        assert seen and all(flag == 1 for flag in seen)
    finally:
        connection.close()


def test_fix_024_score_only_quality_patch_keeps_status_score_pair(tmp_path):
    """A score-only patch must not create a contradictory status/score pair."""
    path = _new_notes_db(tmp_path)
    connection = _connect(path)
    try:
        note_database.insert_note(
            {
                "note_id": "fix-024-score-only",
                "title": "Errored title",
                "data_quality_status": "error",
                "data_quality_score": 10,
            },
            connection=connection,
        )
        note_database.insert_note(
            {"note_id": "fix-024-score-only", "data_quality_score": 100},
            connection=connection,
        )
        row = connection.execute(
            "SELECT data_quality_status, data_quality_score FROM notes WHERE note_id=?",
            ("fix-024-score-only",),
        ).fetchone()
        assert tuple(row) == ("error", 10)
    finally:
        connection.close()
