"""Existing learning schema must be installed by the sole startup migrator."""
import importlib
import sqlite3

import pytest

from lumenis.shared.database import migrations


def seed_v19(path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    with sqlite3.connect(path) as connection:
        migrations.init_version_table(connection)
        migrations.set_version(connection, 19, migrations.MIGRATION_HISTORY[19])
        connection.execute("CREATE TABLE existing_business(value TEXT)")
        connection.execute("INSERT INTO existing_business VALUES ('retained')")


def test_default_migration_installs_memory_and_reopens(tmp_path, monkeypatch):
    path = tmp_path / "v19.db"
    seed_v19(path, monkeypatch)
    assert migrations.migrate() is True
    with sqlite3.connect(path) as connection:
        assert migrations.get_current_version(connection) == migrations.CURRENT_VERSION
        connection.execute(
            "INSERT INTO agent_learning_records(record_id,content_json) VALUES (?,?)",
            ("isolated-fixture", '{"value":"retained memory"}'),
        )
        assert connection.execute("SELECT value FROM existing_business").fetchone()[0] == "retained"
    assert migrations.migrate() is True
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM agent_learning_records").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM schema_version WHERE version=20").fetchone()[0] == 1
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(agent_learning_records)")}
        assert {"idx_agent_learning_type", "idx_agent_learning_stage", "idx_agent_learning_task",
                "idx_agent_learning_created"} <= indexes


def test_preexisting_standalone_memory_is_preserved(tmp_path, monkeypatch):
    path = tmp_path / "standalone.db"
    seed_v19(path, monkeypatch)
    old = importlib.import_module("migrations.011_create_agent_learning_records")
    assert old.upgrade(str(path)) is True
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO agent_learning_records(record_id) VALUES ('keep')")
    assert migrations.migrate() is True
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT record_id FROM agent_learning_records").fetchall() == [("keep",)]


def test_failed_memory_migration_rolls_back_schema_and_version(tmp_path, monkeypatch):
    path = tmp_path / "failure.db"
    seed_v19(path, monkeypatch)
    original = migrations.MIGRATIONS[19]

    def fail_after_creation(connection):
        original(connection)
        raise RuntimeError("isolated injected migration failure")

    monkeypatch.setitem(migrations.MIGRATIONS, 19, fail_after_creation)
    assert migrations.migrate() is False
    with sqlite3.connect(path) as connection:
        assert migrations.get_current_version(connection) == 19
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='agent_learning_records'").fetchone() is None
        assert connection.execute("SELECT value FROM existing_business").fetchone()[0] == "retained"


def test_incompatible_existing_memory_schema_does_not_advance(tmp_path, monkeypatch):
    path = tmp_path / "incompatible.db"
    seed_v19(path, monkeypatch)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE agent_learning_records(record_id TEXT, learning_type TEXT, lifecycle_stage TEXT, related_task_id TEXT, created_at TEXT)")
        connection.execute("INSERT INTO agent_learning_records(record_id) VALUES ('preserve')")
    assert migrations.migrate() is False
    with sqlite3.connect(path) as connection:
        assert migrations.get_current_version(connection) == 19
        assert connection.execute("SELECT record_id FROM agent_learning_records").fetchall() == [("preserve",)]
        assert connection.execute("PRAGMA index_list(agent_learning_records)").fetchall() == []


def test_missing_learning_identity_constraint_refuses_upgrade(tmp_path, monkeypatch):
    path = tmp_path / "no-unique-key.db"
    seed_v19(path, monkeypatch)
    schema = importlib.import_module("migrations.011_create_agent_learning_records")
    with sqlite3.connect(path) as connection:
        connection.execute(schema.CREATE_TABLE_SQL.replace("record_id TEXT UNIQUE NOT NULL", "record_id TEXT NOT NULL"))
        connection.execute("INSERT INTO agent_learning_records(record_id) VALUES ('preserve')")
    assert migrations.migrate() is False
    with sqlite3.connect(path) as connection:
        assert migrations.get_current_version(connection) == 19
        assert connection.execute("SELECT record_id FROM agent_learning_records").fetchall() == [("preserve",)]
