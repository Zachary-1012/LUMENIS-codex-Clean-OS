"""Shared Database v17 delegates Evidence schema to its canonical owner."""
from __future__ import annotations

import sqlite3


def _legacy_evidence(conn):
    conn.execute(
        """CREATE TABLE app_evidence_records (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            actual TEXT,
            topic TEXT,
            status TEXT,
            evidence_hash TEXT,
            created_at TEXT
        )"""
    )
    conn.execute(
        "INSERT INTO app_evidence_records "
        "(id, source, actual, topic, status, evidence_hash, created_at) "
        "VALUES (41, 'archive', 'kept value', 'topic-a', 'verified', 'hash-a', '2024-01-02')"
    )


def _seed_v16_database(conn, migrations):
    conn.execute("CREATE TABLE canonical_data (id INTEGER PRIMARY KEY)")
    conn.execute("CREATE TABLE zbc_canonical_data (id INTEGER PRIMARY KEY)")
    migrations.init_version_table(conn)
    migrations.set_version(conn, 16, migrations.MIGRATION_HISTORY[16])
    _legacy_evidence(conn)
    conn.commit()


def _columns(conn):
    return {
        row[1]: row
        for row in conn.execute("PRAGMA table_info(app_evidence_records)")
    }


def _indexes(conn):
    return {
        row[1]
        for row in conn.execute("PRAGMA index_list(app_evidence_records)")
    }


def test_v17_uses_evidence_owner_and_preserves_the_callers_transaction():
    from lumenis.shared.database import migrations

    conn = sqlite3.connect(":memory:")
    try:
        _legacy_evidence(conn)
        conn.commit()
        conn.execute("BEGIN")

        migrations.migration_16_to_17(conn)

        assert conn.in_transaction
        columns = _columns(conn)
        integrity = {
            "integrity_version",
            "integrity_algorithm",
            "integrity_key_id",
            "integrity_digest",
        }
        scope = {"domain_id", "product_id"}
        assert (integrity | scope) <= set(columns)
        assert all(columns[name][3] == 0 for name in integrity | scope)
        assert all(columns[name][4] is None for name in integrity | scope)
        assert conn.execute(
            "SELECT id, source, actual, topic, status, evidence_hash, created_at, "
            "integrity_version, integrity_algorithm, integrity_key_id, integrity_digest, "
            "domain_id, product_id "
            "FROM app_evidence_records WHERE id=41"
        ).fetchone() == (
            41, "archive", "kept value", "topic-a", "verified", "hash-a",
            "2024-01-02", None, None, None, None, None, None,
        )
        assert {
            "idx_app_evidence_topic",
            "idx_app_evidence_status",
            "idx_app_evidence_hash",
            "idx_app_evidence_integrity_digest",
            "idx_app_evidence_integrity_scheme",
        } <= _indexes(conn)

        conn.rollback()
        assert not conn.in_transaction
        assert set(_columns(conn)) == {
            "id", "source", "actual", "topic", "status", "evidence_hash", "created_at"
        }
        assert not ({
            "idx_app_evidence_integrity_digest",
            "idx_app_evidence_integrity_scheme",
        } & _indexes(conn))
    finally:
        conn.close()


def test_v17_migration_runner_records_version_and_keeps_legacy_evidence(
    tmp_path, monkeypatch
):
    from lumenis.shared.database import migrations

    db_path = tmp_path / "v16-evidence.sqlite3"
    with sqlite3.connect(db_path) as conn:
        _seed_v16_database(conn, migrations)

    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DB_PATH", str(db_path))

    assert migrations.migrate(target_version=17) is True

    with sqlite3.connect(db_path) as conn:
        assert migrations.get_current_version(conn) == 17
        assert conn.execute(
            "SELECT id, source, actual, topic, status, evidence_hash, created_at, "
            "integrity_version, integrity_algorithm, integrity_key_id, integrity_digest, "
            "domain_id, product_id "
            "FROM app_evidence_records WHERE id=41"
        ).fetchone() == (
            41, "archive", "kept value", "topic-a", "verified", "hash-a",
            "2024-01-02", None, None, None, None, None, None,
        )
        assert {
            "idx_app_evidence_integrity_digest",
            "idx_app_evidence_integrity_scheme",
        } <= _indexes(conn)

    assert (tmp_path / "backups" / "before_migration_v16_to_v17.db").is_file()


def test_v17_migration_runner_rolls_back_helper_ddl_on_failure(
    tmp_path, monkeypatch
):
    from lumenis.shared.database import migrations

    db_path = tmp_path / "v16-evidence-rollback.sqlite3"
    with sqlite3.connect(db_path) as conn:
        _seed_v16_database(conn, migrations)

    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DB_PATH", str(db_path))
    original = migrations.migration_16_to_17

    def fail_after_helper(conn):
        original(conn)
        raise RuntimeError("forced post-helper failure")

    monkeypatch.setitem(migrations.MIGRATIONS, 16, fail_after_helper)

    assert migrations.migrate() is False

    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT MAX(version) FROM schema_version WHERE typeof(version)='integer'"
        ).fetchone()[0] == 16
        assert set(_columns(conn)) == {
            "id", "source", "actual", "topic", "status", "evidence_hash", "created_at"
        }
        assert not ({
            "idx_app_evidence_integrity_digest",
            "idx_app_evidence_integrity_scheme",
        } & _indexes(conn))
        assert conn.execute(
            "SELECT id, source, actual, topic, status, evidence_hash, created_at "
            "FROM app_evidence_records WHERE id=41"
        ).fetchone() == (
            41, "archive", "kept value", "topic-a", "verified", "hash-a", "2024-01-02"
        )
