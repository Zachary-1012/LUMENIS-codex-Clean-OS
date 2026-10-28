"""Fresh Shared Database bootstrap stays isolated and reaches its current schema."""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys


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


def _assert_current_owner_schemas_and_idempotence(migrations, db_path):
    """Verify v20/v21 owner contracts and a no-op replay, including retained data."""
    with sqlite3.connect(db_path) as conn:
        assert {"id", "record_id", "content_json", "lifecycle_stage", "related_task_id"} <= set(
            _table_contract(conn, "agent_learning_records")
        )
        assert {"idx_agent_learning_type", "idx_agent_learning_stage", "idx_agent_learning_task",
                "idx_agent_learning_created"} <= _index_names(conn, "agent_learning_records")
        assert {"conversation_id", "actor_ref", "workspace_binding", "scope_json"} <= set(
            _table_contract(conn, "ai_conversations")
        )
        assert {"turn_id", "conversation_id", "idempotency_key", "request_sha256", "sequence"} <= set(
            _table_contract(conn, "ai_conversation_turns")
        )
        assert "idx_ai_conversation_owner" in _index_names(conn, "ai_conversations")
        assert "idx_ai_conversation_task" in _index_names(conn, "ai_conversation_turns")
        assert conn.execute(
            "SELECT version, COUNT(*) FROM schema_version WHERE version IN (20,21) GROUP BY version ORDER BY version"
        ).fetchall() == [(20, 1), (21, 1)]
        before = list(conn.iterdump())
    assert migrations.migrate() is True
    with sqlite3.connect(db_path) as conn:
        assert migrations.get_current_version(conn) == migrations.CURRENT_VERSION
        assert list(conn.iterdump()) == before


def test_migrate_output_handles_gbk_redirect_without_db_migration():
    """Startup migration status must not crash when redirected stdout uses GBK."""
    repo_root = os.path.dirname(os.path.dirname(__file__))
    script = "\n".join(
        (
            "import sqlite3",
            "from lumenis.shared.database import migrations",
            "migrations.get_connection = lambda: sqlite3.connect(':memory:')",
            "migrations.get_current_version = lambda _conn: migrations.CURRENT_VERSION",
            "raise SystemExit(0 if migrations.migrate() else 1)",
        )
    )
    child_env = os.environ.copy()
    child_env["PYTHONIOENCODING"] = "gbk"

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
        check=False,
    )

    stderr = result.stderr.decode("gbk", errors="replace")
    assert result.returncode == 0, stderr
    output = result.stdout.decode("gbk")
    assert "当前数据库版本" in output
    assert "数据库已是目标版本" in output
    assert "\\U0001f4ca" in output


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

    expected_version = 21
    assert migrations.CURRENT_VERSION == expected_version
    assert version == expected_version
    assert numeric_history == list(range(1, expected_version + 1))
    assert {"canonical_data", "zbc_evidence", "zbc_canonical_data"} <= tables
    assert "rule_version" in canonical_columns
    assert {"domain_id", "product_id"} <= evidence_canonical_columns
    assert row_counts == {
        "notes": 0,
        "canonical_data": 0,
        "zbc_evidence": 0,
        "zbc_canonical_data": 0,
    }

    pre_migration_backup = backup_dir / f"before_migration_v0_to_v{expected_version}.db"
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
    _assert_current_owner_schemas_and_idempotence(migrations, db_path)


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
    assert migrations.CURRENT_VERSION == 21
    assert numeric_history == list(range(9, migrations.CURRENT_VERSION + 1))
    _assert_current_owner_schemas_and_idempotence(migrations, db_path)


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

    assert migrations.migrate() is True
    database.init_db()

    with sqlite3.connect(db_path) as conn:
        version = conn.execute(
            "SELECT MAX(version) FROM schema_version WHERE typeof(version)='integer'"
        ).fetchone()[0]
        note_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(notes)")
        }

    assert version == migrations.CURRENT_VERSION
    assert {"publish_datetime", "captured_at", "rule_version"} <= note_columns


def test_real_backup_refusal_precedes_root_business_schema_initialization(
    tmp_path, monkeypatch, capsys
):
    import ast
    from pathlib import Path

    from lumenis.shared.database import migrations

    data_root = tmp_path / "workspace"
    data_root.mkdir()
    db_path = data_root / "monitor.sqlite3"
    backup_dir = data_root / "backups"
    _bind_migration_db(monkeypatch, migrations, db_path, backup_dir)
    monkeypatch.setenv("ZBC_DATA_DIR", str(data_root))

    # A v21 workspace with a signed Evidence key ID but no signing companion
    # exercises the real pre-migration backup refusal without any real key.
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        conn.execute("INSERT INTO schema_version(version) VALUES (21)")
        conn.execute(
            """CREATE TABLE notes (
                note_id TEXT PRIMARY KEY, content TEXT, body TEXT, status TEXT,
                last_seen_at TEXT, collected_at TEXT, source_platform TEXT,
                relevance_status TEXT
            )"""
        )
        conn.execute(
            """INSERT INTO notes VALUES
               ('note-1', 'content', '', NULL, '', 'captured-at', '', '')"""
        )
        conn.execute(
            """CREATE TABLE app_evidence_records (
                id INTEGER PRIMARY KEY, integrity_version INTEGER,
                integrity_algorithm TEXT, integrity_digest TEXT,
                integrity_key_id TEXT
            )"""
        )
        conn.execute(
            """INSERT INTO app_evidence_records VALUES
               (1, 1, 'hmac-sha256', 'test-digest', 'unavailable-test-key')"""
        )

    app_source = Path(__file__).resolve().parents[1] / "app.py"
    app_tree = ast.parse(app_source.read_text(encoding="utf-8"))
    call_lines = {}
    for node in ast.walk(app_tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        receiver = node.func.value
        if isinstance(receiver, ast.Name) and (receiver.id, node.func.attr) in {
            ("db", "init_db"), ("_dm", "migrate")
        }:
            call_lines[(receiver.id, node.func.attr)] = node.lineno
    assert call_lines[("_dm", "migrate")] < call_lines[("db", "init_db")]

    with sqlite3.connect(db_path) as conn:
        schema_before = conn.execute(
            "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
        ).fetchall()
        note_before = conn.execute(
            "SELECT status, last_seen_at, source_platform, relevance_status, body "
            "FROM notes WHERE note_id='note-1'"
        ).fetchone()

    assert migrations.migrate() is False
    assert "WORKSPACE_SIGNING_KEY_RECOVERY_REQUIRED" in capsys.readouterr().out

    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
        ).fetchall() == schema_before
        assert conn.execute(
            "SELECT status, last_seen_at, source_platform, relevance_status, body "
            "FROM notes WHERE note_id='note-1'"
        ).fetchone() == note_before
    assert not list(backup_dir.glob("before_migration_v21_to_v22.db"))
    assert not list(backup_dir.glob(".before_migration_v21_to_v22.db.*.tmp"))


def test_fresh_empty_business_registry_accepts_first_explicit_user_input(tmp_path, monkeypatch):
    import database
    from lumenis.shared.database import migrations

    db_path = tmp_path / "empty-business-workspace.sqlite3"
    _bind_migration_db(monkeypatch, migrations, db_path, tmp_path / "backups")
    monkeypatch.setattr(database, "DB_PATH", str(db_path))

    database.init_db()
    assert migrations.migrate() is True

    import subject_registry

    assert subject_registry.list_subjects() == []

    supplied_input = {
        "domain_id": "CTH",
        "subject_type": "company",
        "name_en": "North Star Operations",
        "name_zh": "北辰运营",
        "industry": "零售服务",
    }
    subject, created = subject_registry.add_subject(supplied_input)

    assert created is True
    assert subject["name_en"] == supplied_input["name_en"]
    assert subject_registry.list_subjects("CTH") == [subject]
