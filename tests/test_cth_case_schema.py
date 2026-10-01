"""Canonical CTH Case schema and v19 migration contracts."""
from __future__ import annotations

import sqlite3

import pytest


def _create_prerequisites(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "CREATE TABLE lumenis_subject_registry "
        "(subject_id TEXT PRIMARY KEY, domain_id TEXT NOT NULL)"
    )
    conn.execute("CREATE TABLE app_evidence_records (id INTEGER PRIMARY KEY)")
    conn.execute(
        "INSERT INTO lumenis_subject_registry(subject_id, domain_id) VALUES ('subject-1', 'CTH')"
    )
    conn.execute("INSERT INTO app_evidence_records(id) VALUES (41)")


def _insert_case(
    conn: sqlite3.Connection,
    *,
    case_id: str = "case-1",
    actor_ref: str = "actor-1",
    subject_id: str = "subject-1",
    submission_id: str = "submission-1",
    title: str = "Case title",
    question: str = "Case question",
    source_refs_json: str = "[]",
    state: str = "OPEN",
    creation_evidence_ref: int | None = 41,
) -> None:
    conn.execute(
        """INSERT INTO lumenis_cth_cases (
            case_id, actor_ref, subject_id, submission_id, title, question,
            source_refs_json, state, creation_evidence_ref
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            case_id, actor_ref, subject_id, submission_id, title, question,
            source_refs_json, state, creation_evidence_ref,
        ),
    )


def test_schema_requires_canonical_subject_and_evidence_prerequisites():
    from lumenis.shared.database.cth_cases import ensure_cth_case_schema

    for missing_table in ("lumenis_subject_registry", "app_evidence_records"):
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            if missing_table != "lumenis_subject_registry":
                conn.execute(
                    "CREATE TABLE lumenis_subject_registry "
                    "(subject_id TEXT PRIMARY KEY)"
                )
            if missing_table != "app_evidence_records":
                conn.execute("CREATE TABLE app_evidence_records (id INTEGER PRIMARY KEY)")

            with pytest.raises(RuntimeError, match="CTH Case prerequisite"):
                ensure_cth_case_schema(conn)

            assert conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='lumenis_cth_cases'"
            ).fetchone() is None
        finally:
            conn.close()


def test_schema_is_idempotent_and_keeps_caller_transaction():
    from lumenis.shared.database.cth_cases import ensure_cth_case_schema

    conn = sqlite3.connect(":memory:")
    try:
        _create_prerequisites(conn)
        conn.commit()
        conn.execute("BEGIN")

        ensure_cth_case_schema(conn)
        ensure_cth_case_schema(conn)

        assert conn.in_transaction
        columns = {
            row[1]: row
            for row in conn.execute("PRAGMA table_info(lumenis_cth_cases)")
        }
        assert set(columns) == {
            "case_id", "actor_ref", "subject_id", "submission_id", "title",
            "question", "source_refs_json", "state", "creation_evidence_ref",
            "created_at",
        }
        assert columns["created_at"][4] == "CURRENT_TIMESTAMP"
        assert {
            (row[2], row[3], row[4])
            for row in conn.execute("PRAGMA foreign_key_list(lumenis_cth_cases)")
        } == {
            ("lumenis_subject_registry", "subject_id", "subject_id"),
            ("app_evidence_records", "creation_evidence_ref", "id"),
        }

        conn.commit()
        assert conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
            "AND name='lumenis_cth_cases'"
        ).fetchone()[0] == 1
    finally:
        conn.close()


def test_case_constraints_require_open_state_keys_and_unique_submission():
    from lumenis.shared.database.cth_cases import ensure_cth_case_schema

    conn = sqlite3.connect(":memory:")
    try:
        _create_prerequisites(conn)
        ensure_cth_case_schema(conn)
        conn.commit()

        _insert_case(conn)
        state, created_at = conn.execute(
            "SELECT state, created_at FROM lumenis_cth_cases WHERE case_id='case-1'"
        ).fetchone()
        assert state == "OPEN"
        assert created_at

        with pytest.raises(sqlite3.IntegrityError):
            _insert_case(conn, case_id="bad-state", state="COMPLETED")
        with pytest.raises(sqlite3.IntegrityError):
            _insert_case(conn, case_id=None)  # type: ignore[arg-type]
        with pytest.raises(sqlite3.IntegrityError):
            _insert_case(conn, case_id="duplicate-submission")

        for field in (
            "actor_ref", "subject_id", "submission_id", "title", "question",
            "source_refs_json", "state", "creation_evidence_ref",
        ):
            values = {field: None}
            with pytest.raises(sqlite3.IntegrityError):
                _insert_case(conn, case_id=f"null-{field}", **values)

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO lumenis_cth_cases (
                    case_id, actor_ref, subject_id, submission_id, title, question,
                    source_refs_json, state, creation_evidence_ref, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
                (
                    "null-created-at", "actor-1", "subject-1", "submission-2",
                    "Case title", "Case question", "[]", "OPEN", 41,
                ),
            )
    finally:
        conn.close()


def test_case_foreign_keys_require_subject_and_creation_evidence():
    from lumenis.shared.database.cth_cases import ensure_cth_case_schema

    conn = sqlite3.connect(":memory:")
    try:
        _create_prerequisites(conn)
        ensure_cth_case_schema(conn)
        conn.commit()

        with pytest.raises(sqlite3.IntegrityError):
            _insert_case(conn, case_id="bad-subject", subject_id="unknown-subject")
        with pytest.raises(sqlite3.IntegrityError):
            _insert_case(conn, case_id="bad-evidence", creation_evidence_ref=404)
    finally:
        conn.close()


def _seed_v18_database(db_path, migrations) -> None:
    with sqlite3.connect(db_path) as conn:
        _create_prerequisites(conn)
        migrations.init_version_table(conn)
        migrations.set_version(conn, 18, migrations.MIGRATION_HISTORY[18])


def _bind_isolated_database(monkeypatch, migrations, db_path) -> None:
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DB_PATH", str(db_path))


def test_v19_migration_is_additive_and_preserves_existing_rows(tmp_path, monkeypatch):
    from lumenis.shared.database import migrations

    db_path = tmp_path / "cth-case-v18.sqlite3"
    _seed_v18_database(db_path, migrations)
    _bind_isolated_database(monkeypatch, migrations, db_path)

    assert migrations.CURRENT_VERSION == 19
    assert 18 in migrations.MIGRATIONS
    assert migrations.migrate(target_version=19) is True

    with sqlite3.connect(db_path) as conn:
        assert migrations.get_current_version(conn) == 19
        assert conn.execute(
            "SELECT subject_id, domain_id FROM lumenis_subject_registry"
        ).fetchall() == [("subject-1", "CTH")]
        assert conn.execute("SELECT id FROM app_evidence_records").fetchall() == [(41,)]
        assert conn.execute(
            "SELECT COUNT(*) FROM lumenis_cth_cases"
        ).fetchone()[0] == 0


def test_v19_migration_failure_rolls_back_case_schema_and_version(
    tmp_path, monkeypatch
):
    from lumenis.shared.database import migrations

    db_path = tmp_path / "cth-case-v18-rollback.sqlite3"
    _seed_v18_database(db_path, migrations)
    _bind_isolated_database(monkeypatch, migrations, db_path)
    original = migrations.MIGRATIONS[18]

    def fail_after_schema(conn):
        original(conn)
        raise RuntimeError("forced migration failure")

    monkeypatch.setitem(migrations.MIGRATIONS, 18, fail_after_schema)

    assert migrations.migrate(target_version=19) is False

    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT MAX(version) FROM schema_version WHERE typeof(version)='integer'"
        ).fetchone()[0] == 18
        assert conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='lumenis_cth_cases'"
        ).fetchone() is None
        assert conn.execute(
            "SELECT subject_id, domain_id FROM lumenis_subject_registry"
        ).fetchall() == [("subject-1", "CTH")]
        assert conn.execute("SELECT id FROM app_evidence_records").fetchall() == [(41,)]
