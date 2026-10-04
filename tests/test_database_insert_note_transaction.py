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
