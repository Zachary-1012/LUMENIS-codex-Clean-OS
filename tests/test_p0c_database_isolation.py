"""P0-C database isolation and migration-path acceptance tests."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

import database
import database_migrations as migrations
from database_isolation import (
    DatabaseEnvironment,
    backup_to_isolated_copy,
    database_identity,
    environment_directories,
    foreign_key_rows,
    resolve_database_path,
)


def _bind(path: Path) -> None:
    database.DB_PATH = str(path)
    migrations.DB_PATH = str(path)
    migrations.BACKUP_DIR = str(path.parent / "backups")


def _base_database(path: Path, version: int = 0) -> Path:
    _bind(path)
    database.init_db()
    if version:
        connection = sqlite3.connect(path)
        try:
            migrations.init_version_table(connection)
            connection.execute("DELETE FROM schema_version")
            connection.execute(
                "INSERT INTO schema_version(version, description) VALUES (?, ?)",
                (version, f"test historical v{version}"),
            )
            connection.commit()
        finally:
            connection.close()
    return path


def _version(path: Path) -> int:
    connection = sqlite3.connect(path)
    try:
        return migrations.get_current_version(connection)
    finally:
        connection.close()


def _columns(path: Path, table: str):
    connection = sqlite3.connect(path)
    try:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    finally:
        connection.close()


def test_environment_paths_are_physically_separate(tmp_path):
    paths = environment_directories(tmp_path)
    assert len({str(path) for path in paths.values()}) == 3
    assert resolve_database_path(tmp_path, environment=DatabaseEnvironment.PRODUCTION.value) == tmp_path / "data" / "monitor.db"
    assert resolve_database_path(tmp_path, environment=DatabaseEnvironment.TEST.value) == tmp_path / "data" / "test" / "monitor.db"
    assert resolve_database_path(tmp_path, environment=DatabaseEnvironment.EXPERIMENT.value) == tmp_path / "data" / "experiment" / "monitor.db"


def test_pytest_rejects_direct_connection_to_repository_database():
    protected = Path(__file__).resolve().parents[1] / "data" / "monitor.db"
    with pytest.raises(RuntimeError, match="pytest 禁止连接受保护数据库"):
        sqlite3.connect(protected)
    with pytest.raises(RuntimeError, match="pytest 禁止连接受保护数据库"):
        sqlite3.connect(f"file:{protected.as_posix()}?mode=ro", uri=True)


def test_clean_bootstrap_to_current(tmp_path):
    target = _base_database(tmp_path / "clean.db")
    assert migrations.migrate() is True
    assert _version(target) == migrations.CURRENT_VERSION
    assert "rule_version" in _columns(target, "canonical_data")
    assert {"domain_id", "product_id"}.issubset(_columns(target, "zbc_canonical_data"))
    assert database_identity(target).integrity == "ok"


def test_historical_v9_upgrade_preserves_rows(tmp_path):
    target = _base_database(tmp_path / "historical-v9.db", version=9)
    connection = sqlite3.connect(target)
    connection.execute(
        "INSERT INTO notes(note_id, title, content) VALUES ('p0c-note', '广州太古汇', '历史样本')"
    )
    connection.commit()
    connection.close()
    assert migrations.migrate() is True
    connection = sqlite3.connect(target)
    try:
        assert connection.execute(
            "SELECT title FROM notes WHERE note_id='p0c-note'"
        ).fetchone()[0] == "广州太古汇"
    finally:
        connection.close()
    assert _version(target) == migrations.CURRENT_VERSION
    assert "rule_version" in _columns(target, "canonical_data")


def test_isolated_copy_migrates_without_source_change(tmp_path):
    source = _base_database(tmp_path / "source" / "production-candidate.db", version=9)
    before = database_identity(source)
    destination = backup_to_isolated_copy(source, tmp_path / "copy" / "migration.db")
    _bind(destination)
    assert migrations.migrate() is True
    after = database_identity(source)
    assert after == before
    assert _version(destination) == migrations.CURRENT_VERSION


def test_failed_migration_rolls_back_schema_and_version(tmp_path, monkeypatch):
    target = _base_database(tmp_path / "rollback.db", version=9)

    def fail_after_ddl(connection):
        connection.execute("ALTER TABLE notes ADD COLUMN should_rollback TEXT")
        raise RuntimeError("fault injection")

    monkeypatch.setitem(migrations.MIGRATIONS, 9, fail_after_ddl)
    assert migrations.migrate(target_version=10) is False
    assert _version(target) == 9
    assert "should_rollback" not in _columns(target, "notes")
    connection = sqlite3.connect(target)
    try:
        assert connection.execute("SELECT COUNT(*) FROM notes").fetchone()[0] >= 0
    finally:
        connection.close()


def test_foreign_key_rows_are_read_only_and_row_level(tmp_path):
    target = tmp_path / "fk.db"
    connection = sqlite3.connect(target)
    connection.executescript(
        """
        PRAGMA foreign_keys=OFF;
        CREATE TABLE parent(id INTEGER PRIMARY KEY);
        CREATE TABLE child(id INTEGER PRIMARY KEY, parent_id INTEGER,
                           FOREIGN KEY(parent_id) REFERENCES parent(id));
        INSERT INTO child(id, parent_id) VALUES (7, 99);
        """
    )
    connection.commit()
    connection.close()
    before = database_identity(target)
    rows = foreign_key_rows(target)
    after = database_identity(target)
    assert rows == [{"table": "child", "rowid": 7, "parent": "parent", "fkid": 0}]
    assert after == before
