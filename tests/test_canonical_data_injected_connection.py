import hashlib
import sqlite3

import pytest

import canonical_data


def _table_exists(connection, name):
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _index_names(connection):
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
    }


def test_ensure_canonical_table_uses_caller_connection_and_rollback(tmp_path, monkeypatch):
    target_path = tmp_path / "custom" / "canonical.db"
    target_path.parent.mkdir()
    unrelated_path = tmp_path / "unrelated.db"

    unrelated = sqlite3.connect(unrelated_path)
    try:
        unrelated.execute("CREATE TABLE sentinel (value TEXT NOT NULL)")
        unrelated.execute("INSERT INTO sentinel VALUES ('keep')")
        unrelated.commit()
    finally:
        unrelated.close()
    unrelated_hash = hashlib.sha256(unrelated_path.read_bytes()).hexdigest()

    def reject_repository_connection(*_args, **_kwargs):
        pytest.fail("injected connection must not open another database")

    monkeypatch.setattr(
        canonical_data.DatabaseRepository,
        "connect",
        reject_repository_connection,
    )

    connection = sqlite3.connect(target_path)
    try:
        connection.execute("BEGIN")
        canonical_data.ensure_canonical_table(connection=connection)

        assert connection.in_transaction
        assert _table_exists(connection, canonical_data.CANONICAL_TABLE)
        assert "idx_canonical_source" in _index_names(connection)

        # The caller can still use and roll back the same connection. All DDL
        # performed by ensure_canonical_table belongs to this transaction.
        connection.rollback()
        assert not connection.in_transaction
        assert not _table_exists(connection, canonical_data.CANONICAL_TABLE)
        assert "idx_canonical_source" not in _index_names(connection)
        assert connection.execute("SELECT 1").fetchone() == (1,)

        # A legacy table missing product_id triggers a partial domain_id repair
        # before backfill fails. The injected path must expose that error so
        # the caller can roll the whole repair back.
        connection.execute(
            """CREATE TABLE canonical_data (
                canonical_id TEXT PRIMARY KEY,
                source_type TEXT, source_table TEXT, source_id TEXT,
                source_platform TEXT, publish_datetime TEXT, captured_at TEXT,
                subject_type TEXT, content_type TEXT, content_hash TEXT,
                risk_level TEXT, sentiment TEXT
            )"""
        )
        connection.execute(
            "INSERT INTO canonical_data (canonical_id) VALUES ('legacy-row')"
        )
        connection.commit()

        connection.execute("BEGIN")
        with pytest.raises(sqlite3.OperationalError, match="product_id"):
            canonical_data.ensure_canonical_table(connection=connection)

        assert connection.in_transaction
        assert "domain_id" in {
            row[1] for row in connection.execute("PRAGMA table_info(canonical_data)")
        }
        assert "idx_canonical_source" in _index_names(connection)

        connection.rollback()
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(canonical_data)")
        }
        assert "domain_id" not in columns
        assert "idx_canonical_source" not in _index_names(connection)
        assert connection.execute(
            "SELECT canonical_id FROM canonical_data"
        ).fetchall() == [("legacy-row",)]
    finally:
        connection.close()

    assert hashlib.sha256(unrelated_path.read_bytes()).hexdigest() == unrelated_hash
