"""Collector quality logs preserve unknown comment counts separately from zero."""

import pytest

from lumenis.shared.database import DatabaseRepository


def _stored_count(db_path, note_id):
    with DatabaseRepository(str(db_path)).connection() as connection:
        row = connection.execute(
            "SELECT comments_collected FROM collector_quality_log WHERE note_id = ? ORDER BY id DESC LIMIT 1",
            (note_id,),
        ).fetchone()
    return row[0]


def test_save_collector_quality_preserves_unknown_blank_and_zero(tmp_path, monkeypatch):
    import database

    db_path = tmp_path / "collector-quality.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    database.init_db()

    with DatabaseRepository(str(db_path)).connection() as connection:
        field = next(
            row for row in connection.execute("PRAGMA table_info(collector_quality_log)")
            if row["name"] == "comments_collected"
        )
    assert field["notnull"] == 0
    assert field["dflt_value"] == "0"

    database.save_collector_quality("missing", {})
    database.save_collector_quality("null", {"comments_collected": None})
    database.save_collector_quality("blank", {"comments_collected": "  "})
    database.save_collector_quality("zero", {"comments_collected": 0})
    database.save_collector_quality("measured", {"comments_collected": "6"})

    assert _stored_count(db_path, "missing") is None
    assert _stored_count(db_path, "null") is None
    assert _stored_count(db_path, "blank") is None
    assert _stored_count(db_path, "zero") == 0
    assert _stored_count(db_path, "measured") == 6

    with pytest.raises(ValueError):
        database.save_collector_quality("invalid", {"comments_collected": "unknown"})
    with DatabaseRepository(str(db_path)).connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM collector_quality_log WHERE note_id = ?", ("invalid",)
        ).fetchone()[0] == 0
