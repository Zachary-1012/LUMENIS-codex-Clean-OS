"""Disposable exact-scope Raw/Evidence/Canonical acceptance for P0 public data."""
from __future__ import annotations

import json
import sqlite3

import pytest

from canonical_data import ensure_canonical_scope_columns, ensure_canonical_table
from lumenis.adapters.persist import persist_existing_note_scope
from lumenis.shared.database.scope import ScopeValidationError
from lumenis.shared.evidence import store as evidence_store


@pytest.fixture
def product_db(tmp_path, monkeypatch):
    path = tmp_path / "p0.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({"p0-test": "isolated-test-key"})
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "p0-test")
    with sqlite3.connect(path) as con:
        con.executescript("""
            CREATE TABLE lumenis_subject_registry (
                subject_id TEXT PRIMARY KEY, brand_focus_id TEXT UNIQUE,
                domain_id TEXT NOT NULL, status TEXT NOT NULL
            );
            INSERT INTO lumenis_subject_registry VALUES
                ('SUBJ-C', NULL, 'CTH', 'configured'),
                ('SUBJ-B', 'BRAND-B', 'BMP', 'configured');
            CREATE TABLE notes (
                note_id TEXT PRIMARY KEY, title TEXT, content TEXT, body TEXT,
                url TEXT, source_platform TEXT, source_keyword TEXT,
                publish_date TEXT, publish_datetime TEXT, captured_at TEXT,
                collected_at TEXT, product_id TEXT, domain_id TEXT,
                subject_id TEXT, brand_focus_id TEXT,
                scope_status TEXT DEFAULT 'UNASSIGNED', scope_evidence_ref TEXT
            );
            INSERT INTO notes(note_id,title,content,url,source_platform,captured_at)
            VALUES ('raw-c','Mall','Mall source','https://example.org/c','public_http','2026-09-27T01:00:00Z');
            INSERT INTO notes(note_id,title,content,url,source_platform,captured_at)
            VALUES ('raw-b','Brand','Brand source','https://example.org/b','public_http','2026-09-27T02:00:00Z');
        """)
        evidence_store.ensure_evidence_schema(con)
        evidence_columns = {
            row[1] for row in con.execute("PRAGMA table_info(app_evidence_records)")
        }
        for column, kind, default in evidence_store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if column not in evidence_columns:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                con.execute(
                    f"ALTER TABLE app_evidence_records ADD COLUMN {column} {kind}{suffix}"
                )
        ensure_canonical_table(connection=con)
        ensure_canonical_scope_columns(con)
        con.commit()
    return path


def _evidence(path, *, domain, raw_id, subject_id=None, brand_focus_id=None):
    return evidence_store.record_evidence(
        source="public_http", project="LUMENIS",
        product="CTH" if domain == "cth" else "BMP",
        feature_id="P0-BIND-TEST", test_name="public_source",
        result="PASS", status="verified",
        inputs={"source_ids": [raw_id]}, outputs={"source_read": True},
        domain_id=domain, subject_id=subject_id,
        brand_focus_id=brand_focus_id,
    )


def test_cth_and_bmp_bind_exactly_and_reopen_without_fabricated_publish_time(product_db):
    cth_ref = _evidence(product_db, domain="cth", raw_id="raw-c", subject_id="SUBJ-C")
    bmp_ref = _evidence(product_db, domain="zbmp", raw_id="raw-b", brand_focus_id="BRAND-B")
    with sqlite3.connect(product_db) as con:
        assert persist_existing_note_scope(
            con, ["raw-c"], product_id="CTH", domain_id="cth",
            subject_id="SUBJ-C", scope_evidence_ref=cth_ref,
        ) == 1
        assert persist_existing_note_scope(
            con, ["raw-b"], product_id="ZBMP", domain_id="zbmp",
            brand_focus_id="BRAND-B", scope_evidence_ref=bmp_ref,
        ) == 1
        assert persist_existing_note_scope(
            con, ["raw-b"], product_id="ZBMP", domain_id="zbmp",
            brand_focus_id="BRAND-B", scope_evidence_ref=bmp_ref,
        ) == 0
        con.commit()
    with sqlite3.connect(product_db) as con:
        rows = con.execute(
            "SELECT n.note_id,n.subject_id,n.brand_focus_id,n.scope_status,"
            "n.scope_evidence_ref,c.subject_id,c.brand_focus_id,c.scope_status,"
            "c.scope_evidence_ref,c.publish_datetime "
            "FROM notes n JOIN canonical_data c ON c.external_id=n.note_id "
            "ORDER BY n.note_id"
        ).fetchall()
    assert rows == [
        ("raw-b", None, "BRAND-B", "VERIFIED", str(bmp_ref), "", "BRAND-B", "VERIFIED", str(bmp_ref), ""),
        ("raw-c", "SUBJ-C", None, "VERIFIED", str(cth_ref), "SUBJ-C", "", "VERIFIED", str(cth_ref), ""),
    ]


def test_tampered_evidence_cannot_promote_raw_or_canonical(product_db):
    ref = _evidence(product_db, domain="cth", raw_id="raw-c", subject_id="SUBJ-C")
    with sqlite3.connect(product_db) as con:
        con.execute(
            "UPDATE app_evidence_records SET inputs_json=? WHERE id=?",
            (json.dumps({"source_ids": ["raw-b"]}), ref),
        )
        with pytest.raises(ScopeValidationError):
            persist_existing_note_scope(
                con, ["raw-c"], product_id="CTH", domain_id="cth",
                subject_id="SUBJ-C", scope_evidence_ref=ref,
            )
        assert con.execute("SELECT scope_status FROM notes WHERE note_id='raw-c'").fetchone()[0] == "UNASSIGNED"
        assert con.execute("SELECT count(*) FROM canonical_data").fetchone()[0] == 0


def test_batch_failure_rolls_back_raw_and_canonical_together(product_db):
    ref = evidence_store.record_evidence(
        source="public_http", project="LUMENIS", product="CTH",
        feature_id="P0-BIND-TEST", result="PASS", status="verified",
        inputs={"source_ids": ["raw-c", "missing-raw"]},
        outputs={"source_read": True}, domain_id="cth", subject_id="SUBJ-C",
    )
    assert ref > 0
    with sqlite3.connect(product_db) as con:
        with pytest.raises(ScopeValidationError, match="raw note is missing"):
            persist_existing_note_scope(
                con, ["raw-c", "missing-raw"], product_id="CTH",
                domain_id="cth", subject_id="SUBJ-C", scope_evidence_ref=ref,
            )
        assert con.execute("SELECT scope_status FROM notes WHERE note_id='raw-c'").fetchone()[0] == "UNASSIGNED"
        assert con.execute("SELECT count(*) FROM canonical_data").fetchone()[0] == 0


def test_cross_domain_evidence_cannot_bind_another_subject(product_db):
    ref = _evidence(product_db, domain="zbmp", raw_id="raw-c", brand_focus_id="BRAND-B")
    assert ref > 0
    with sqlite3.connect(product_db) as con:
        with pytest.raises(ScopeValidationError):
            persist_existing_note_scope(
                con, ["raw-c"], product_id="CTH", domain_id="cth",
                subject_id="SUBJ-C", scope_evidence_ref=ref,
            )
        assert con.execute("SELECT scope_status FROM notes WHERE note_id='raw-c'").fetchone()[0] == "UNASSIGNED"
