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


def test_empty_v0_owner_failure_rolls_back_bootstrap_and_version(tmp_path, monkeypatch):
    from lumenis.shared.database import migrations
    from lumenis.shared.evidence import chain as evidence_chain

    db_path = tmp_path / "empty-v0.sqlite3"
    backup_dir = tmp_path / "backups"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DB_PATH", str(db_path))

    original_init_db = evidence_chain.init_db

    def fail_after_owner_schema(db_path=None, *, connection=None):
        original_init_db(db_path=db_path, connection=connection)
        raise RuntimeError("forced failure after Evidence owner schema")

    monkeypatch.setattr(evidence_chain, "init_db", fail_after_owner_schema)

    assert migrations.migrate(target_version=11) is False

    with sqlite3.connect(db_path) as conn:
        user_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        versions = conn.execute(
            "SELECT version FROM schema_version "
            "WHERE typeof(version)='integer' ORDER BY id"
        ).fetchall()

    assert user_tables == {"schema_version"}
    assert versions == []

    backup_path = backup_dir / "before_migration_v0_to_v11.db"
    assert backup_path.is_file()
    with sqlite3.connect(backup_path) as conn:
        backup_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        backup_versions = conn.execute(
            "SELECT version FROM schema_version "
            "WHERE typeof(version)='integer' ORDER BY id"
        ).fetchall()
    assert backup_tables == {"schema_version"}
    assert backup_versions == []


def test_empty_v0_first_migration_failure_rolls_back_bootstrap_and_version(
    tmp_path, monkeypatch
):
    from lumenis.shared.database import migrations

    db_path = tmp_path / "empty-v0-first-step.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DB_PATH", str(db_path))

    def fail_first_migration(connection):
        raise RuntimeError("forced first migration failure")

    monkeypatch.setitem(migrations.MIGRATIONS, 1, fail_first_migration)

    assert migrations.migrate(target_version=2) is False

    with sqlite3.connect(db_path) as conn:
        user_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        versions = conn.execute(
            "SELECT version FROM schema_version "
            "WHERE typeof(version)='integer' ORDER BY id"
        ).fetchall()

    assert user_tables == {"schema_version"}
    assert versions == []


def test_empty_v0_target_v1_commits_complete_base_bootstrap(tmp_path, monkeypatch):
    from lumenis.shared.database import migrations

    db_path = tmp_path / "empty-v0-target-v1.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DB_PATH", str(db_path))

    assert migrations.migrate(target_version=1) is True

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        versions = conn.execute(
            "SELECT version FROM schema_version "
            "WHERE typeof(version)='integer' ORDER BY id"
        ).fetchall()

    assert {"notes", "daily_reports", "collection_logs"} <= tables
    assert versions == [(1,)]


def test_existing_v0_owner_failure_preserves_base_rows_and_v0(tmp_path, monkeypatch):
    from lumenis.shared.database import migrations
    from lumenis.shared.evidence import chain as evidence_chain

    db_path = tmp_path / "existing-v0-owner-failure.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    with sqlite3.connect(db_path) as conn:
        business_schema.apply_business_schema(conn)
        conn.execute(
            "INSERT INTO notes (note_id, title) VALUES (?, ?)",
            ("preexisting-v0", "must survive"),
        )
        conn.commit()

    original_init = evidence_chain.init_db

    def fail_after_evidence_schema(db_path=None, *, connection=None):
        original_init(db_path=db_path, connection=connection)
        raise RuntimeError("forced Evidence owner failure")

    monkeypatch.setattr(evidence_chain, "init_db", fail_after_evidence_schema)
    assert migrations.migrate(target_version=11) is False

    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT title FROM notes WHERE note_id='preexisting-v0'"
        ).fetchone() == ("must survive",)
        assert conn.execute(
            "SELECT version FROM schema_version WHERE typeof(version)='integer'"
        ).fetchall() == []
        assert conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='zbc_canonical_data'"
        ).fetchone() is None


def test_existing_v0_first_step_failure_preserves_base_rows_and_v0(
    tmp_path, monkeypatch
):
    from lumenis.shared.database import migrations

    db_path = tmp_path / "existing-v0-first-step.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    with sqlite3.connect(db_path) as conn:
        business_schema.apply_business_schema(conn)
        conn.execute(
            "INSERT INTO notes (note_id, title) VALUES (?, ?)",
            ("preexisting-v0", "must survive"),
        )
        conn.commit()

    def fail_first_step(conn):
        conn.execute("CREATE TABLE partial_first_step (value TEXT)")
        raise RuntimeError("forced first migration failure")

    monkeypatch.setitem(migrations.MIGRATIONS, 1, fail_first_step)
    assert migrations.migrate(target_version=2) is False

    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT title FROM notes WHERE note_id='preexisting-v0'"
        ).fetchone() == ("must survive",)
        assert conn.execute(
            "SELECT version FROM schema_version WHERE typeof(version)='integer'"
        ).fetchall() == []
        assert conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='partial_first_step'"
        ).fetchone() is None
