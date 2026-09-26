"""Shared migration prerequisites stay on the caller's transaction and database."""
from __future__ import annotations

import sqlite3


def _tables(connection):
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def test_prerequisites_use_supplied_connection_and_ignore_stale_path(
    tmp_path, monkeypatch
):
    from lumenis.shared.database import migrations

    custom_db = tmp_path / "custom-zbc.sqlite3"
    stale_decoy = tmp_path / "stale-main-db.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(custom_db))
    path_calls = []

    def stale_main_db_path():
        path_calls.append(True)
        return str(stale_decoy)

    monkeypatch.setattr(migrations, "main_db_path", stale_main_db_path)
    connection = sqlite3.connect(custom_db)
    try:
        current = migrations._ensure_migration_prerequisites(
            connection, current_version=10, target_version=11
        )
        assert current == 10
        assert connection.in_transaction
        tables = _tables(connection)
        assert {"canonical_data", "zbc_canonical_data"} <= tables
        connection.commit()
    finally:
        connection.close()

    assert path_calls == []
    assert not stale_decoy.exists()
    with sqlite3.connect(custom_db) as persisted:
        assert {"canonical_data", "zbc_canonical_data"} <= _tables(persisted)


def test_migrate_rolls_back_both_owner_schemas_after_prerequisite_failure(
    tmp_path, monkeypatch
):
    from lumenis.shared.database import migrations
    from lumenis.shared.evidence import chain

    custom_db = tmp_path / "custom-zbc.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(custom_db))
    monkeypatch.setattr(migrations, "DB_PATH", str(custom_db))
    monkeypatch.setattr(migrations, "BACKUP_DIR", str(tmp_path / "backups"))

    with sqlite3.connect(custom_db) as seed:
        migrations.init_version_table(seed)
        migrations.set_version(seed, 10, migrations.MIGRATION_HISTORY[10])

    original_init_db = chain.init_db
    observed = {}

    def fail_after_evidence_schema(*, connection=None):
        observed["connection_present"] = connection is not None
        observed["transaction_active"] = connection.in_transaction
        observed["custom_database"] = connection.execute(
            "PRAGMA database_list"
        ).fetchone()[2] == str(custom_db)
        observed["canonical_schema_before_evidence"] = (
            "canonical_data" in _tables(connection)
        )
        original_init_db(connection=connection)
        observed["evidence_schema_after_owner_init"] = (
            "zbc_canonical_data" in _tables(connection)
        )
        raise RuntimeError("injected evidence prerequisite failure")

    monkeypatch.setattr(chain, "init_db", fail_after_evidence_schema)

    assert migrations.migrate(target_version=11) is False
    assert observed == {
        "connection_present": True,
        "transaction_active": True,
        "custom_database": True,
        "canonical_schema_before_evidence": True,
        "evidence_schema_after_owner_init": True,
    }
    with sqlite3.connect(custom_db) as persisted:
        tables = _tables(persisted)
        assert "canonical_data" not in tables
        assert "zbc_canonical_data" not in tables
        assert persisted.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()[0] == 10
