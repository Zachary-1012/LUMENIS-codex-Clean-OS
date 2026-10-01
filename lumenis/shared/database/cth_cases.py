"""Canonical Shared Database schema for CTH Cases."""
from __future__ import annotations

import sqlite3


TABLE = "lumenis_cth_cases"


def _require_prerequisites(conn: sqlite3.Connection) -> None:
    """Require the canonical Subject Registry and Evidence key tables."""
    required_keys = {
        "lumenis_subject_registry": ("subject_id", "TEXT"),
        "app_evidence_records": ("id", "INTEGER"),
    }
    for table, (key_column, key_type) in required_keys.items():
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        if exists is None:
            raise RuntimeError(f"CTH Case prerequisite table is missing: {table}")

        columns = {
            row[1]: row
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        key = columns.get(key_column)
        if key is None or not key[5] or str(key[2]).upper() != key_type:
            raise RuntimeError(
                f"CTH Case prerequisite key is unavailable: {table}.{key_column}"
            )


def ensure_cth_case_schema(conn: sqlite3.Connection) -> None:
    """Create the additive Case table on the caller's canonical DB connection.

    Subject/domain authorization and all Case business behavior remain with
    their application owners. This schema only requires and references the
    existing Subject Registry and Evidence key owners.
    """
    _require_prerequisites(conn)
    if not conn.in_transaction:
        conn.execute("BEGIN")

    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS {TABLE} (
            case_id TEXT PRIMARY KEY NOT NULL,
            actor_ref TEXT NOT NULL,
            subject_id TEXT NOT NULL
                REFERENCES lumenis_subject_registry(subject_id),
            submission_id TEXT NOT NULL,
            title TEXT NOT NULL,
            question TEXT NOT NULL,
            source_refs_json TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state='OPEN'),
            creation_evidence_ref INTEGER NOT NULL
                REFERENCES app_evidence_records(id),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(actor_ref, subject_id, submission_id)
        )"""
    )
