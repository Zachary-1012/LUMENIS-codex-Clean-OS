"""Missing comment-collection counts stay distinct from an observed zero."""

from lumenis.shared.database import DatabaseRepository


def _stored_count(db_path, note_id):
    with DatabaseRepository(str(db_path)).connection() as connection:
        row = connection.execute(
            "SELECT comments_collected FROM notes WHERE note_id = ?",
            (note_id,),
        ).fetchone()
    return row[0]


def test_insert_note_preserves_missing_and_explicit_comment_counts(tmp_path, monkeypatch):
    import database

    db_path = tmp_path / "comments-collected.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    database.init_db()

    with DatabaseRepository(str(db_path)).connection() as connection:
        field = next(
            row for row in connection.execute("PRAGMA table_info(notes)")
            if row["name"] == "comments_collected"
        )
    assert field["notnull"] == 0
    assert field["dflt_value"] == "0"

    _, inserted = database.insert_note({"note_id": "missing-on-insert"})
    assert inserted is True
    assert _stored_count(db_path, "missing-on-insert") is None

    _, inserted = database.insert_note(
        {"note_id": "explicit-zero-on-insert", "comments_collected": 0}
    )
    assert inserted is True
    assert _stored_count(db_path, "explicit-zero-on-insert") == 0

    database.insert_note({"note_id": "existing-count", "comments_collected": 7})
    database.insert_note({"note_id": "existing-count"})
    assert _stored_count(db_path, "existing-count") == 7

    database.insert_note({"note_id": "existing-count", "comments_collected": 0})
    assert _stored_count(db_path, "existing-count") == 0