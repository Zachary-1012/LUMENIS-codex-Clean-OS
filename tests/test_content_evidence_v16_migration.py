"""Isolated acceptance for the Shared Database v15-to-v16 migration."""
from __future__ import annotations

import sqlite3

import pytest


def _bind_database(monkeypatch, migrations, path):
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setattr(migrations, "DB_PATH", str(path))
    monkeypatch.setattr(migrations, "BACKUP_DIR", str(path.parent / "backups"))


def _create_v15_database(path, migrations):
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE canonical_data (id TEXT);
            CREATE TABLE zbc_canonical_data (id TEXT);
            CREATE TABLE content_generation_evidence (
                evidence_id TEXT PRIMARY KEY,
                content_type TEXT NOT NULL,
                input_json TEXT NOT NULL,
                prompt TEXT NOT NULL,
                output_text TEXT,
                status TEXT DEFAULT 'success',
                parent_evidence_id TEXT,
                iteration INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (parent_evidence_id)
                    REFERENCES content_generation_evidence(evidence_id)
            );
            CREATE TABLE content_evaluation (
                eval_id TEXT PRIMARY KEY,
                evidence_id TEXT NOT NULL,
                overall REAL,
                created_at TEXT NOT NULL
            );
            INSERT INTO content_generation_evidence
                (evidence_id, content_type, input_json, prompt, output_text,
                 status, parent_evidence_id, iteration, created_at)
            VALUES
                ('PARENT', 'ad_copy', '{"brief":"parent"}', 'parent prompt',
                 'parent output', 'success', NULL, 1, '2026-09-01'),
                ('CGE-LEGACY', 'ad_copy', '{"brief":"keep"}', 'keep prompt',
                 'keep output', 'success', '', 1, '2026-09-02'),
                ('CHILD', 'ad_copy', '{"brief":"child"}', 'child prompt',
                 'child output', 'success', 'PARENT', 2, '2026-09-03');
            INSERT INTO content_evaluation
                (eval_id, evidence_id, overall, created_at)
            VALUES ('EVAL-LEGACY', 'CGE-LEGACY', 0.75, '2026-09-02');
            """
        )
        migrations.init_version_table(conn)
        migrations.set_version(conn, 15, migrations.MIGRATION_HISTORY[15])
    finally:
        conn.close()


def _index_names(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA index_list({table})")}


def test_v15_to_v16_preserves_rows_normalizes_parent_and_is_idempotent(
    tmp_path, monkeypatch
):
    from lumenis.shared.database import migrations

    path = tmp_path / "v15-content.sqlite3"
    _bind_database(monkeypatch, migrations, path)
    _create_v15_database(path, migrations)

    assert 16 in migrations.MIGRATION_HISTORY
    assert 15 in migrations.MIGRATIONS

    assert migrations.migrate(target_version=16) is True
    assert migrations.migrate(target_version=16) is True

    conn = sqlite3.connect(path)
    try:
        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(content_generation_evidence)"
            )
        }
        indexes = _index_names(conn, "content_generation_evidence")
        evaluation_indexes = _index_names(conn, "content_evaluation")
        rows = conn.execute(
            """SELECT evidence_id, input_json, prompt, output_text, status,
                      parent_evidence_id, iteration, created_at,
                      source_evidence_ref
                 FROM content_generation_evidence
                ORDER BY evidence_id"""
        ).fetchall()
        evaluations = conn.execute(
            "SELECT eval_id, evidence_id, overall, created_at "
            "FROM content_evaluation"
        ).fetchall()
        version = conn.execute(
            "SELECT MAX(version) FROM schema_version "
            "WHERE typeof(version)='integer'"
        ).fetchone()[0]
        version_16_count = conn.execute(
            "SELECT COUNT(*) FROM schema_version WHERE version=16"
        ).fetchone()[0]
    finally:
        conn.close()

    assert "source_evidence_ref" in columns
    assert {
        "idx_cge_type",
        "idx_cge_created",
        "idx_cge_source_evidence_ref",
    } <= indexes
    assert "idx_ce_evidence" in evaluation_indexes
    assert rows == [
        (
            "CGE-LEGACY", '{"brief":"keep"}', "keep prompt", "keep output",
            "success", None, 1, "2026-09-02", None,
        ),
        (
            "CHILD", '{"brief":"child"}', "child prompt", "child output",
            "success", "PARENT", 2, "2026-09-03", None,
        ),
        (
            "PARENT", '{"brief":"parent"}', "parent prompt", "parent output",
            "success", None, 1, "2026-09-01", None,
        ),
    ]
    assert evaluations == [
        ("EVAL-LEGACY", "CGE-LEGACY", 0.75, "2026-09-02")
    ]
    assert version == 16
    assert version_16_count == 1


def test_v15_to_v16_rolls_back_ddl_rows_and_version_on_failure(
    tmp_path, monkeypatch
):
    from lumenis.shared.database import migrations

    path = tmp_path / "v15-rollback.sqlite3"
    _bind_database(monkeypatch, migrations, path)
    _create_v15_database(path, migrations)
    original = migrations.MIGRATIONS[15]

    def fail_after_schema_changes(conn):
        original(conn)
        raise RuntimeError("injected v16 failure")

    monkeypatch.setitem(migrations.MIGRATIONS, 15, fail_after_schema_changes)
    assert migrations.migrate(target_version=16) is False

    conn = sqlite3.connect(path)
    try:
        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(content_generation_evidence)"
            )
        }
        indexes = _index_names(conn, "content_generation_evidence")
        evaluation_indexes = _index_names(conn, "content_evaluation")
        parent = conn.execute(
            "SELECT parent_evidence_id FROM content_generation_evidence "
            "WHERE evidence_id='CGE-LEGACY'"
        ).fetchone()[0]
        version = conn.execute(
            "SELECT MAX(version) FROM schema_version "
            "WHERE typeof(version)='integer'"
        ).fetchone()[0]
        migration_rows = conn.execute(
            "SELECT COUNT(*) FROM schema_version WHERE version=16"
        ).fetchone()[0]
    finally:
        conn.close()

    assert "source_evidence_ref" not in columns
    assert not {
        "idx_cge_type",
        "idx_cge_created",
        "idx_cge_source_evidence_ref",
    } & indexes
    assert "idx_ce_evidence" not in evaluation_indexes
    assert parent == ""
    assert version == 15
    assert migration_rows == 0


def test_content_evidence_read_does_not_run_or_apply_schema_migration(
    tmp_path, monkeypatch
):
    from lumenis.shared.database import migrations
    from lumenis.shared.database.repository import DatabaseRepository
    import content_generation as generation

    path = tmp_path / "read-only-contract.sqlite3"
    _bind_database(monkeypatch, migrations, path)
    _create_v15_database(path, migrations)
    monkeypatch.setattr(
        generation, "get_repository", lambda: DatabaseRepository(str(path))
    )

    def unexpected_migration(*args, **kwargs):
        pytest.fail("content read unexpectedly invoked schema migration")

    monkeypatch.setattr(migrations, "migrate", unexpected_migration)
    result = generation.get_evidence("CGE-LEGACY")
    assert result is not None
    assert result["parent_evidence_id"] == ""

    conn = sqlite3.connect(path)
    try:
        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(content_generation_evidence)"
            )
        }
        parent = conn.execute(
            "SELECT parent_evidence_id FROM content_generation_evidence "
            "WHERE evidence_id='CGE-LEGACY'"
        ).fetchone()[0]
        version = conn.execute(
            "SELECT MAX(version) FROM schema_version "
            "WHERE typeof(version)='integer'"
        ).fetchone()[0]
    finally:
        conn.close()

    assert "source_evidence_ref" not in columns
    assert parent == ""
    assert version == 15
