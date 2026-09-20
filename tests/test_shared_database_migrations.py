"""Fresh Shared Database bootstrap stays isolated and reaches its current schema."""
from __future__ import annotations

import sqlite3


def test_empty_database_migrates_through_canonical_and_evidence_owners(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "lumenis-empty.sqlite3"
    backup_dir = tmp_path / "backups"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))

    import database
    from lumenis.shared.database import migrations

    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "BACKUP_DIR", str(backup_dir))

    database.init_db()
    with sqlite3.connect(db_path) as conn:
        initial_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "canonical_data" not in initial_tables
    assert "zbc_canonical_data" not in initial_tables

    assert migrations.migrate() is True

    with sqlite3.connect(db_path) as conn:
        version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        canonical_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(canonical_data)")
        }
        evidence_canonical_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(zbc_canonical_data)")
        }
        row_counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("notes", "canonical_data", "zbc_evidence", "zbc_canonical_data")
        }

    assert version == migrations.CURRENT_VERSION
    assert {"canonical_data", "zbc_evidence", "zbc_canonical_data"} <= tables
    assert "rule_version" in canonical_columns
    assert {"domain_id", "product_id"} <= evidence_canonical_columns
    assert row_counts == {
        "notes": 0,
        "canonical_data": 0,
        "zbc_evidence": 0,
        "zbc_canonical_data": 0,
    }

    pre_migration_backup = backup_dir / "before_migration_v0_to_v13.db"
    assert pre_migration_backup.is_file()
    with sqlite3.connect(pre_migration_backup) as conn:
        backup_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "canonical_data" not in backup_tables
    assert "zbc_canonical_data" not in backup_tables
