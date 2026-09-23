import sqlite3

import pytest

from lumenis.shared.database import business_schema


def test_schema_application_preserves_callers_pending_write_for_rollback():
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE caller_row (value TEXT NOT NULL)")
        connection.commit()
        connection.execute("INSERT INTO caller_row (value) VALUES ('pending')")

        business_schema.apply_business_schema(connection)
        connection.rollback()

        assert connection.execute("SELECT value FROM caller_row").fetchall() == []
    finally:
        connection.close()


def test_schema_ddl_failure_rolls_back_with_callers_transaction(monkeypatch):
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("BEGIN")
        monkeypatch.setattr(
            business_schema,
            "SCHEMA",
            "CREATE TABLE atomicity_partial (value TEXT);"
            "CREATE TABLE broken (value TEXT DEFAULT 'unterminated);",
        )

        with pytest.raises(sqlite3.OperationalError):
            business_schema.apply_business_schema(connection)

        connection.rollback()
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        assert tables == []
    finally:
        connection.close()


def test_schema_bootstrap_and_repeat_application_preserve_existing_rows():
    connection = sqlite3.connect(":memory:")
    try:
        business_schema.apply_business_schema(connection)
        connection.commit()
        connection.execute(
            "INSERT INTO notes (note_id, title, content) VALUES (?, ?, ?)",
            ("schema-atomicity-probe", "preserved", "existing row"),
        )
        connection.commit()

        business_schema.apply_business_schema(connection)
        connection.commit()

        rows = connection.execute(
            "SELECT note_id, title, content FROM notes WHERE note_id = ?",
            ("schema-atomicity-probe",),
        ).fetchall()
        assert rows == [("schema-atomicity-probe", "preserved", "existing row")]
    finally:
        connection.close()
