"""Isolated v14 scope storage migration coverage."""
from __future__ import annotations

import sqlite3


def _bind_db(monkeypatch, migrations, db_path, backup_dir):
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DB_PATH", str(db_path))
    monkeypatch.setattr(migrations, "BACKUP_DIR", str(backup_dir))


def _create_v13_database(db_path):
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE notes (
                id INTEGER PRIMARY KEY,
                note_id TEXT NOT NULL,
                title TEXT,
                content TEXT
            );
            CREATE TABLE web_mentions (
                id INTEGER PRIMARY KEY,
                source_id TEXT NOT NULL,
                title TEXT,
                content TEXT
            );
            CREATE TABLE events (
                id INTEGER PRIMARY KEY,
                event_key TEXT NOT NULL,
                title TEXT,
                summary TEXT
            );
            CREATE TABLE canonical_data (
                canonical_id TEXT PRIMARY KEY,
                subject_id TEXT DEFAULT '',
                evidence_ref TEXT DEFAULT '',
                scope_status TEXT,
                title TEXT
            );
            CREATE TABLE zbc_canonical_data (id INTEGER PRIMARY KEY);
            CREATE TABLE schema_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                description TEXT,
                applied_at TEXT,
                applied_by TEXT DEFAULT 'system'
            );
            INSERT INTO notes (note_id, title, content)
                VALUES ('NOTE-real-001', NULL, '');
            INSERT INTO web_mentions (source_id, title, content)
                VALUES ('WEB-real-002', '', NULL);
            INSERT INTO events (event_key, title, summary)
                VALUES ('EVENT-real-003', NULL, '');
            INSERT INTO canonical_data
                (canonical_id, subject_id, evidence_ref, scope_status, title)
                VALUES ('CAN-real-004', NULL, NULL, NULL, 'legacy nulls');
            INSERT INTO canonical_data
                (canonical_id, subject_id, evidence_ref, scope_status, title)
                VALUES ('CAN-real-005', '', '', '', 'legacy empties');
            INSERT INTO schema_version (version, description)
                VALUES (13, 'v13 baseline');
            """
        )


def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _column_info(conn, table):
    return {
        row[1]: (row[2], row[3], row[4])
        for row in conn.execute(f"PRAGMA table_info({table})")
    }


def _scope_indexes(conn, table):
    prefix = "canonical" if table == "canonical_data" else table
    expected = {f"idx_{prefix}_scope_subject", f"idx_{prefix}_scope_brand"}
    return {
        row[1]
        for row in conn.execute(f"PRAGMA index_list({table})")
        if row[1] in expected
    }


def test_v13_upgrade_preserves_rows_and_leaves_scope_unassigned(
    tmp_path, monkeypatch
):
    from lumenis.shared.database import migrations
    db_path = tmp_path / "v13.sqlite3"
    _bind_db(monkeypatch, migrations, db_path, tmp_path / "backups")
    _create_v13_database(db_path)

    assert migrations.migrate(target_version=14) is True

    expected_keys = {"subject_id", "brand_focus_id", "scope_status", "scope_evidence_ref"}
    with sqlite3.connect(db_path) as conn:
        for table in ("notes", "web_mentions", "events", "canonical_data"):
            assert expected_keys <= _columns(conn, table)
            assert len(_scope_indexes(conn, table)) == 2
            info = _column_info(conn, table)
            assert info["brand_focus_id"] == ("TEXT", 0, None)
            if table != "canonical_data":
                assert info["scope_status"] == ("TEXT", 1, "'UNASSIGNED'")
                assert info["subject_id"] == ("TEXT", 0, None)
            assert info["scope_evidence_ref"] == ("TEXT", 0, None)
        assert conn.execute(
            "SELECT note_id, title, content, subject_id, brand_focus_id, "
            "scope_status, scope_evidence_ref FROM notes"
        ).fetchall() == [
            ("NOTE-real-001", None, "", None, None, "UNASSIGNED", None)
        ]
        assert conn.execute(
            "SELECT source_id, title, content, subject_id, brand_focus_id, "
            "scope_status, scope_evidence_ref FROM web_mentions"
        ).fetchall() == [
            ("WEB-real-002", "", None, None, None, "UNASSIGNED", None)
        ]
        assert conn.execute(
            "SELECT event_key, title, summary, subject_id, brand_focus_id, "
            "scope_status, scope_evidence_ref FROM events"
        ).fetchall() == [
            ("EVENT-real-003", None, "", None, None, "UNASSIGNED", None)
        ]
        assert conn.execute(
            "SELECT canonical_id, subject_id, brand_focus_id, scope_status, "
            "evidence_ref, scope_evidence_ref, title FROM canonical_data ORDER BY canonical_id"
        ).fetchall() == [
            ("CAN-real-004", None, None, "UNASSIGNED", None, None, "legacy nulls"),
            ("CAN-real-005", "", None, "UNASSIGNED", "", None, "legacy empties"),
        ]
        assert conn.execute(
            "SELECT version FROM schema_version WHERE typeof(version)='integer' "
            "ORDER BY id"
        ).fetchall() == [(13,), (14,)]

    # Blank status is normalized to UNASSIGNED; scope Evidence NULL/empty stays distinct.
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE notes SET scope_status='' WHERE note_id='NOTE-real-001'")
        conn.execute(
            "UPDATE canonical_data SET scope_evidence_ref='' "
            "WHERE canonical_id='CAN-real-005'"
        )
        migrations.migration_13_to_14(conn)
        conn.commit()
        for table in ("notes", "web_mentions", "events", "canonical_data"):
            assert expected_keys <= _columns(conn, table)
            assert len(_scope_indexes(conn, table)) == 2
        assert conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM web_mentions").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM canonical_data").fetchone()[0] == 2
        assert conn.execute(
            "SELECT scope_status FROM notes WHERE note_id='NOTE-real-001'"
        ).fetchone()[0] == "UNASSIGNED"
        assert conn.execute(
            "SELECT canonical_id, scope_evidence_ref FROM canonical_data "
            "ORDER BY canonical_id"
        ).fetchall() == [("CAN-real-004", None), ("CAN-real-005", "")]


def test_v0_bootstrap_reaches_v14_scope_contract(tmp_path, monkeypatch):
    from lumenis.shared.database import migrations
    db_path = tmp_path / "v0.sqlite3"
    _bind_db(monkeypatch, migrations, db_path, tmp_path / "backups")

    assert migrations.migrate(target_version=14) is True

    expected_keys = {"subject_id", "brand_focus_id", "scope_status", "scope_evidence_ref"}
    with sqlite3.connect(db_path) as conn:
        for table in ("notes", "web_mentions", "events", "canonical_data"):
            assert expected_keys <= _columns(conn, table)
            assert len(_scope_indexes(conn, table)) == 2
        assert conn.execute(
            "SELECT version FROM schema_version WHERE typeof(version)='integer' "
            "ORDER BY id"
        ).fetchall() == [(version,) for version in range(1, 15)]
        assert conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM canonical_data").fetchone()[0] == 0


def test_failed_v14_step_rolls_back_ddl_and_version_row(tmp_path, monkeypatch):
    from lumenis.shared.database import migrations
    db_path = tmp_path / "failed-v13.sqlite3"
    _bind_db(monkeypatch, migrations, db_path, tmp_path / "backups")
    _create_v13_database(db_path)
    original_step = migrations.MIGRATIONS[13]

    def fail_after_v14_ddl(conn):
        original_step(conn)
        raise RuntimeError("injected v14 failure after all DDL")

    monkeypatch.setitem(migrations.MIGRATIONS, 13, fail_after_v14_ddl)
    assert migrations.migrate(target_version=14) is False

    expected_added = {"brand_focus_id", "scope_status", "scope_evidence_ref"}
    with sqlite3.connect(db_path) as conn:
        for table in ("notes", "web_mentions", "events"):
            assert not (expected_added | {"subject_id"}) & _columns(conn, table)
            assert not _scope_indexes(conn, table)
        assert not (expected_added - {"scope_status"}) & _columns(conn, "canonical_data")
        assert not _scope_indexes(conn, "canonical_data")
        assert conn.execute(
            "SELECT version FROM schema_version WHERE typeof(version)='integer' "
            "ORDER BY id"
        ).fetchall() == [(13,)]
        assert conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM canonical_data").fetchone()[0] == 2
