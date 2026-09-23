"""Fresh Shared Database bootstrap stays isolated and reaches its current schema."""
from __future__ import annotations

import sqlite3


def _bind_migration_db(monkeypatch, migrations, db_path, backup_dir):
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "BACKUP_DIR", str(backup_dir))


def _table_contract(conn, table):
    return {
        row[1]: (row[2], row[3], row[4], row[5])
        for row in conn.execute(f"PRAGMA table_info({table})")
    }


def _index_names(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA index_list({table})")}


def test_business_schema_preserves_backfills_indexes_and_event_date(tmp_path):
    from lumenis.shared.database import apply_business_schema

    db_path = tmp_path / "business-schema.sqlite3"
    with sqlite3.connect(db_path) as conn:
        apply_business_schema(conn)
        conn.execute(
            """INSERT INTO notes (
                note_id, content, collected_at, publish_date, status,
                last_seen_at, source_platform, relevance_status, body
            ) VALUES (?, ?, ?, ?, NULL, '', '', '', '')""",
            ("note-1", "body source", "2026-09-20 08:00:00", "2026-09-19"),
        )
        conn.execute(
            "INSERT INTO events (event_key, first_seen, event_date) VALUES (?, ?, '')",
            ("event-1", "2026-09-20"),
        )
        event_id = conn.execute(
            "SELECT id FROM events WHERE event_key='event-1'"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO event_mentions (event_id, source_type, source_id) VALUES (?, ?, ?)",
            (event_id, "note", "note-1"),
        )

        apply_business_schema(conn)

        note = conn.execute(
            """SELECT status, last_seen_at, source_platform,
                      relevance_status, body
               FROM notes WHERE note_id='note-1'"""
        ).fetchone()
        event_date = conn.execute(
            "SELECT event_date FROM events WHERE event_key='event-1'"
        ).fetchone()[0]
        report_indexes = {
            row[1] for row in conn.execute("PRAGMA index_list(daily_reports)")
        }

    assert note == (
        "active",
        "2026-09-20 08:00:00",
        "xhs",
        "relevant",
        "body source",
    )
    assert event_date == "2026-09-19"
    assert "idx_reports_type_date" in report_indexes


def test_migrate_only_bootstraps_empty_database_through_canonical_owners(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "lumenis-empty.sqlite3"
    backup_dir = tmp_path / "backups"
    from lumenis.shared.database import migrations
    from lumenis.shared.database.business_schema import apply_business_schema

    _bind_migration_db(monkeypatch, migrations, db_path, backup_dir)

    assert migrations.migrate() is True

    reference_path = tmp_path / "business-owner-reference.sqlite3"
    with sqlite3.connect(reference_path) as reference:
        apply_business_schema(reference)
        reference.commit()
        owner_contracts = {
            table: _table_contract(reference, table)
            for table in ("notes", "daily_reports", "collection_logs")
        }
        owner_indexes = {
            table: _index_names(reference, table)
            for table in ("notes", "daily_reports", "collection_logs")
        }

    with sqlite3.connect(db_path) as conn:
        version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        numeric_history = [
            row[0]
            for row in conn.execute(
                "SELECT version FROM schema_version WHERE typeof(version)='integer' ORDER BY id"
            )
        ]
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
        for table, owner_contract in owner_contracts.items():
            migrated_contract = _table_contract(conn, table)
            assert {
                column: migrated_contract[column] for column in owner_contract
            } == owner_contract
            assert owner_indexes[table] <= _index_names(conn, table)

    assert version == migrations.CURRENT_VERSION
    assert numeric_history == list(range(1, migrations.CURRENT_VERSION + 1))
    assert {"canonical_data", "zbc_evidence", "zbc_canonical_data"} <= tables
    assert "rule_version" in canonical_columns
    assert {"domain_id", "product_id"} <= evidence_canonical_columns
    assert row_counts == {
        "notes": 0,
        "canonical_data": 0,
        "zbc_evidence": 0,
        "zbc_canonical_data": 0,
    }

    pre_migration_backup = backup_dir / "before_migration_v0_to_v15.db"
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


def test_existing_versioned_data_and_null_semantics_are_preserved(
    tmp_path, monkeypatch
):
    from lumenis.shared.database import migrations
    from lumenis.shared.database.business_schema import apply_business_schema

    db_path = tmp_path / "existing-v9.sqlite3"
    backup_dir = tmp_path / "backups"
    _bind_migration_db(monkeypatch, migrations, db_path, backup_dir)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        apply_business_schema(conn)
        migrations.init_version_table(conn)
        migrations.set_version(conn, 9, migrations.MIGRATION_HISTORY[9])
        conn.execute(
            """INSERT INTO notes (
                note_id, title, content, likes, publish_datetime, captured_at
            ) VALUES (?, ?, ?, NULL, NULL, '')""",
            ("historical-note", "historical-title", "historical-content"),
        )
        conn.commit()

    assert migrations.migrate() is True

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """SELECT title, content, likes, publish_datetime, captured_at,
                      rule_version, content_hash, provenance, product_id
               FROM notes WHERE note_id='historical-note'"""
        ).fetchone()
        numeric_history = [
            value
            for (value,) in conn.execute(
                "SELECT version FROM schema_version WHERE typeof(version)='integer' ORDER BY id"
            )
        ]

    assert row == (
        "historical-title",
        "historical-content",
        None,
        None,
        "",
        None,
        None,
        None,
        None,
    )
    assert numeric_history == [9, 10, 11, 12, 13, 14, 15]


def test_failed_migration_step_rolls_back_data_and_version(tmp_path, monkeypatch):
    from lumenis.shared.database import migrations
    from lumenis.shared.database.business_schema import apply_business_schema

    db_path = tmp_path / "rollback-v12.sqlite3"
    backup_dir = tmp_path / "backups"
    _bind_migration_db(monkeypatch, migrations, db_path, backup_dir)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        apply_business_schema(conn)
        migrations.init_version_table(conn)
        migrations.set_version(conn, 12, migrations.MIGRATION_HISTORY[12])
        conn.execute(
            "INSERT INTO notes (note_id, title) VALUES ('rollback-note', 'before')"
        )
        conn.commit()

    def failing_step(conn):
        conn.execute(
            "UPDATE notes SET title='must-rollback' WHERE note_id='rollback-note'"
        )
        raise RuntimeError("forced migration failure")

    monkeypatch.setitem(migrations.MIGRATIONS, 12, failing_step)
    assert migrations.migrate() is False

    with sqlite3.connect(db_path) as conn:
        title = conn.execute(
            "SELECT title FROM notes WHERE note_id='rollback-note'"
        ).fetchone()[0]
        version = conn.execute(
            "SELECT MAX(version) FROM schema_version WHERE typeof(version)='integer'"
        ).fetchone()[0]

    assert title == "before"
    assert version == 12


def test_partial_v0_schema_fails_closed_without_current_schema_repair(
    tmp_path, monkeypatch
):
    from lumenis.shared.database import migrations

    db_path = tmp_path / "partial-v0.sqlite3"
    backup_dir = tmp_path / "backups"
    _bind_migration_db(monkeypatch, migrations, db_path, backup_dir)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE notes (id INTEGER PRIMARY KEY, legacy_value TEXT)"
        )
        conn.execute("CREATE TABLE daily_reports (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE collection_logs (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO notes (legacy_value) VALUES ('preserve-me')")
        conn.commit()

    assert migrations.migrate() is False

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        note_columns = [
            row[1] for row in conn.execute("PRAGMA table_info(notes)")
        ]
        note_rows = conn.execute(
            "SELECT id, legacy_value FROM notes ORDER BY id"
        ).fetchall()
        numeric_versions = conn.execute(
            "SELECT version FROM schema_version WHERE typeof(version)='integer'"
        ).fetchall()

    assert tables == {
        "notes",
        "daily_reports",
        "collection_logs",
        "schema_version",
        "sqlite_sequence",
    }
    assert note_columns == ["id", "legacy_value"]
    assert note_rows == [(1, "preserve-me")]
    assert numeric_versions == []


def test_canonical_root_init_v0_path_still_migrates(tmp_path, monkeypatch):
    import database
    from lumenis.shared.database import migrations

    db_path = tmp_path / "canonical-init-v0.sqlite3"
    backup_dir = tmp_path / "backups"
    _bind_migration_db(monkeypatch, migrations, db_path, backup_dir)
    monkeypatch.setattr(database, "DB_PATH", str(db_path))

    database.init_db()
    assert migrations.migrate() is True

    with sqlite3.connect(db_path) as conn:
        version = conn.execute(
            "SELECT MAX(version) FROM schema_version WHERE typeof(version)='integer'"
        ).fetchone()[0]
        note_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(notes)")
        }

    assert version == migrations.CURRENT_VERSION
    assert {"publish_datetime", "captured_at", "rule_version"} <= note_columns
