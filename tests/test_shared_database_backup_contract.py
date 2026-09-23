"""Isolated contracts for canonical database backups and migration refusal."""
from __future__ import annotations

import sqlite3

from lumenis.shared.database import migrations


def _database(path, version=13, payload="baseline"):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        conn.execute("INSERT INTO schema_version(version) VALUES (?)", (version,))
        conn.execute("CREATE TABLE payload (value TEXT)")
        conn.execute("INSERT INTO payload(value) VALUES (?)", (payload,))


def test_backup_includes_committed_wal_content_and_validates_snapshot(tmp_path, monkeypatch):
    source = tmp_path / "wal-source.sqlite3"
    backup_dir = tmp_path / "backups"
    monkeypatch.setenv("ZBC_DB_PATH", str(source))
    with sqlite3.connect(source) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("CREATE TABLE payload (value TEXT)")
        writer.execute("INSERT INTO payload VALUES ('committed-in-wal')")
        writer.commit()
        assert (tmp_path / "wal-source.sqlite3-wal").exists()
        backup = migrations.backup_database("wal-snapshot.db")
        assert backup == str(backup_dir / "wal-snapshot.db")
        assert writer.execute("SELECT value FROM payload").fetchone()[0] == "committed-in-wal"
    with sqlite3.connect(backup) as snapshot:
        assert snapshot.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert snapshot.execute("SELECT value FROM payload").fetchone()[0] == "committed-in-wal"


def test_backup_uses_call_time_zbc_db_path_and_keeps_explicit_name(tmp_path, monkeypatch):
    stale_dir = tmp_path / "stale"
    current_dir = tmp_path / "current"
    stale_dir.mkdir()
    current_dir.mkdir()
    stale = stale_dir / "import-time.sqlite3"
    current = current_dir / "current.sqlite3"
    _database(stale, payload="stale-database")
    _database(current, payload="call-time-database")
    monkeypatch.setattr(migrations, "DB_PATH", str(stale))
    monkeypatch.setenv("ZBC_DB_PATH", str(current))

    backup = migrations.backup_database("operator-requested.db")

    assert backup == str(current_dir / "backups" / "operator-requested.db")
    with sqlite3.connect(backup) as conn:
        assert conn.execute("SELECT value FROM payload").fetchone()[0] == "call-time-database"


def test_default_backup_name_closes_version_connection(tmp_path, monkeypatch):
    db_path = tmp_path / "default-name.sqlite3"
    _database(db_path, version=7)
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))

    class TrackedConnection:
        closed = False

        def close(self):
            self.closed = True

    version_connection = TrackedConnection()
    monkeypatch.setattr(migrations, "get_connection", lambda: version_connection)
    def current_version(conn):
        assert conn is version_connection
        return 7

    monkeypatch.setattr(migrations, "get_current_version", current_version)

    backup = migrations.backup_database()

    assert version_connection.closed is True
    assert backup.startswith(str(tmp_path / "backups" / "monitor_db_v7_"))
    assert backup.endswith(".db")
    with sqlite3.connect(backup) as snapshot:
        assert snapshot.execute("SELECT value FROM payload").fetchone()[0] == "baseline"


def test_backup_rejects_directory_components_in_explicit_name(tmp_path, monkeypatch):
    db_path = tmp_path / "traversal.sqlite3"
    _database(db_path)
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))

    for name in ("../escaped.db", "nested/escaped.db", "..\\escaped.db"):
        try:
            migrations.backup_database(name)
        except ValueError as exc:
            assert "filename" in str(exc)
        else:
            raise AssertionError(f"path traversal backup name was accepted: {name}")

    assert not (tmp_path / "escaped.db").exists()


def test_backup_failure_leaves_schema_and_version_unchanged(tmp_path, monkeypatch):
    db_path = tmp_path / "backup-failure.sqlite3"
    _database(db_path, version=12)
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))

    def fail_backup(_name=None):
        raise OSError("simulated backup failure")

    monkeypatch.setattr(migrations, "backup_database", fail_backup)
    with sqlite3.connect(db_path) as conn:
        before_schema = conn.execute(
            "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
        ).fetchall()
        before_version = conn.execute("SELECT version FROM schema_version").fetchall()

    assert migrations.migrate() is False

    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
        ).fetchall() == before_schema
        assert conn.execute("SELECT version FROM schema_version").fetchall() == before_version
        assert conn.execute("SELECT value FROM payload").fetchone()[0] == "baseline"


def test_lower_target_version_is_refused_without_changing_schema(tmp_path, monkeypatch):
    db_path = tmp_path / "downgrade.sqlite3"
    _database(db_path, version=13)
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    with sqlite3.connect(db_path) as conn:
        before = conn.execute(
            "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
        ).fetchall()
        before_versions = conn.execute("SELECT version FROM schema_version").fetchall()

    assert migrations.migrate(target_version=12) is False

    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
        ).fetchall() == before
        assert conn.execute("SELECT version FROM schema_version").fetchall() == before_versions


def test_rollback_refuses_until_reverse_migrations_exist(monkeypatch):
    def unexpected_connection():
        raise AssertionError("refused rollback must not open or modify a database")

    monkeypatch.setattr(migrations, "get_connection", unexpected_connection)
    assert migrations.rollback() is False
