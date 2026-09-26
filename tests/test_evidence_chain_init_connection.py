import sqlite3

import pytest

from lumenis.shared.evidence import chain as evidence_chain


def test_init_db_injected_connection_keeps_schema_in_caller_transaction(tmp_path):
    db_path = tmp_path / "injected.sqlite3"
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("CREATE TABLE caller_rows (value TEXT NOT NULL)")
        connection.commit()
        connection.execute("BEGIN")
        connection.execute("INSERT INTO caller_rows VALUES ('pending')")

        evidence_chain.init_db(connection=connection)

        assert connection.in_transaction
        assert connection.execute("SELECT 1").fetchone() == (1,)
        connection.rollback()

        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "caller_rows" in tables
        assert "zbc_evidence" not in tables
        assert connection.execute("SELECT COUNT(*) FROM caller_rows").fetchone() == (0,)
    finally:
        connection.close()


def test_init_db_injected_connection_propagates_legacy_alter_failure(tmp_path):
    db_path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("CREATE TABLE caller_rows (value TEXT NOT NULL)")
        connection.execute(
            "CREATE TABLE zbc_evidence ("
            "evidence_id TEXT PRIMARY KEY, source_type TEXT, content_hash TEXT, "
            "subject_scope TEXT, domain_id TEXT, product_id TEXT, trace_id TEXT)"
        )
        connection.commit()
        connection.execute("BEGIN")
        connection.execute("INSERT INTO caller_rows VALUES ('pending')")

        def deny_alter(action, _arg1, _arg2, _database, _trigger):
            if action == sqlite3.SQLITE_ALTER_TABLE:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        connection.set_authorizer(deny_alter)
        with pytest.raises(sqlite3.DatabaseError):
            evidence_chain.init_db(connection=connection)

        assert connection.in_transaction
        connection.set_authorizer(None)
        connection.rollback()

        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert tables == {"caller_rows", "zbc_evidence"}
        assert connection.execute("SELECT COUNT(*) FROM caller_rows").fetchone() == (0,)
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(zbc_evidence)")
        }
        assert "source_id" not in columns
    finally:
        connection.close()


def test_init_db_standalone_uses_explicit_custom_path(tmp_path, monkeypatch):
    db_path = tmp_path / "custom.sqlite3"
    monkeypatch.setattr(
        evidence_chain,
        "main_db_path",
        lambda: (_ for _ in ()).throw(AssertionError("unexpected default database path")),
    )

    evidence_chain.init_db(str(db_path))

    with sqlite3.connect(db_path) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='zbc_evidence'"
        ).fetchone() == (1,)
