"""Additive Shared Evidence integrity schema owner regressions."""
from __future__ import annotations

import sqlite3

from lumenis.shared.evidence import store


INTEGRITY_COLUMNS = {
    "integrity_version",
    "integrity_algorithm",
    "integrity_key_id",
    "integrity_digest",
}
SCOPE_COLUMNS = {"domain_id", "product_id"}


def _legacy_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE app_evidence_records (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            actual TEXT,
            topic TEXT,
            status TEXT,
            evidence_hash TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO app_evidence_records "
        "(id, source, actual, topic, status, evidence_hash, created_at) "
        "VALUES (41, 'archive', 'kept value', 'topic-a', 'verified', 'hash-a', '2024-01-02')"
    )
    conn.commit()
    return conn


def test_integrity_schema_adds_nullable_fields_without_rewriting_legacy_row():
    conn = _legacy_db()
    try:
        result = store.ensure_evidence_schema(conn)
        columns = {
            row[1]: row
            for row in conn.execute("PRAGMA table_info(app_evidence_records)")
        }
        row = conn.execute(
            "SELECT id, source, actual, topic, status, evidence_hash, created_at, "
            "integrity_version, integrity_algorithm, integrity_key_id, integrity_digest "
            "FROM app_evidence_records WHERE id=41"
        ).fetchone()
        indexes = {
            row[1]
            for row in conn.execute("PRAGMA index_list(app_evidence_records)")
        }

        assert (INTEGRITY_COLUMNS | SCOPE_COLUMNS) <= set(columns)
        assert all(columns[name][3] == 0 for name in INTEGRITY_COLUMNS | SCOPE_COLUMNS)
        assert row == (
            41, "archive", "kept value", "topic-a", "verified", "hash-a",
            "2024-01-02", None, None, None, None,
        )
        assert set(result["added"]) == INTEGRITY_COLUMNS | SCOPE_COLUMNS
        assert conn.execute(
            "SELECT domain_id, product_id FROM app_evidence_records WHERE id=41"
        ).fetchone() == (None, None)
        assert {"idx_app_evidence_integrity_digest", "idx_app_evidence_integrity_scheme"} <= indexes
    finally:
        conn.close()


def test_integrity_schema_respects_caller_transaction_and_rolls_back_atomically():
    conn = _legacy_db()
    try:
        before = {
            row[1]
            for row in conn.execute("PRAGMA table_info(app_evidence_records)")
        }
        conn.execute("BEGIN")
        store.ensure_evidence_schema(conn)
        assert conn.in_transaction
        assert (INTEGRITY_COLUMNS | SCOPE_COLUMNS) <= {
            row[1]
            for row in conn.execute("PRAGMA table_info(app_evidence_records)")
        }

        conn.rollback()
        after = {
            row[1]
            for row in conn.execute("PRAGMA table_info(app_evidence_records)")
        }
        indexes = {
            row[1]
            for row in conn.execute("PRAGMA index_list(app_evidence_records)")
        }

        assert after == before
        assert not ({"idx_app_evidence_integrity_digest", "idx_app_evidence_integrity_scheme"} & indexes)
        assert conn.execute(
            "SELECT id, source, actual FROM app_evidence_records WHERE id=41"
        ).fetchone() == (41, "archive", "kept value")
    finally:
        conn.close()


def test_integrity_schema_is_idempotent_and_creates_fresh_table():
    conn = sqlite3.connect(":memory:")
    try:
        first = store.ensure_evidence_schema(conn)
        conn.commit()
        second = store.ensure_evidence_schema(conn)
        indexes = {
            row[1]
            for row in conn.execute("PRAGMA index_list(app_evidence_records)")
        }

        assert set(first["added"]) == INTEGRITY_COLUMNS | SCOPE_COLUMNS
        assert second["added"] == []
        assert set(second["skipped"]) == INTEGRITY_COLUMNS | SCOPE_COLUMNS
        assert (INTEGRITY_COLUMNS | SCOPE_COLUMNS) <= {
            row[1]
            for row in conn.execute("PRAGMA table_info(app_evidence_records)")
        }
        assert {
            "idx_app_evidence_topic",
            "idx_app_evidence_status",
            "idx_app_evidence_hash",
            "idx_app_evidence_integrity_digest",
            "idx_app_evidence_integrity_scheme",
        } <= indexes
    finally:
        conn.close()
