"""Disposable regressions for the Canonical exact-scope writer."""
import json
import sqlite3

import pytest

from canonical_data import (
    CanonicalRecord,
    ensure_canonical_table,
    note_to_canonical,
    persist_canonical,
)
from lumenis.shared.evidence import store as evidence_store


@pytest.fixture
def scope_db(tmp_path, monkeypatch):
    path = tmp_path / "canonical-scope.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"canonical-test": "ephemeral-disposable-test-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "canonical-test")
    with sqlite3.connect(path) as conn:
        evidence_store.ensure_evidence_schema(conn)
        evidence_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(app_evidence_records)")
        }
        for column, kind, default in evidence_store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if column not in evidence_columns:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                conn.execute(
                    f"ALTER TABLE app_evidence_records ADD COLUMN {column} {kind}{suffix}"
                )
        ensure_canonical_table(connection=conn)
    return path


def _signed_scope_evidence(source_id, *, product, domain, subject=None, brand=None):
    return evidence_store.record_evidence(
        source="public_http", project="LUMENIS", product=product,
        feature_id="CANONICAL_SCOPE_TEST", test_name="source_scope",
        result="PASS", status="verified", inputs={"source_ids": [source_id]},
        outputs={"source_read": True}, domain_id=domain,
        subject_id=subject, brand_focus_id=brand,
    )


def test_note_scope_roundtrips_for_cth_subject_and_bmp_brand_focus(scope_db):
    rows = (
        ("raw-cth", "CTH", "cth", "SUBJ-C", ""),
        ("raw-bmp", "ZBMP", "zbmp", "", "BRAND-B"),
    )
    evidence_ids = [
        _signed_scope_evidence(
            source_id, product=product, domain=domain,
            subject=subject or None, brand=brand or None,
        )
        for source_id, product, domain, subject, brand in rows
    ]
    with sqlite3.connect(scope_db) as conn:
        for (source_id, product, domain, subject, brand), evidence_id in zip(rows, evidence_ids):
            raw = {
                "note_id": source_id, "product_id": product, "domain_id": domain,
                "subject_id": subject, "brand_focus_id": brand,
                "scope_status": "VERIFIED", "scope_evidence_ref": str(evidence_id),
                "publish_datetime": "", "captured_at": "2026-09-27T01:00:00Z",
            }
            persist_canonical(conn, note_to_canonical(raw, product_id=product))
        conn.commit()
        stored = conn.execute(
            "SELECT external_id, product_id, domain_id, subject_id, brand_focus_id, "
            "scope_status, scope_evidence_ref, publish_datetime, captured_at "
            "FROM canonical_data ORDER BY external_id"
        ).fetchall()
    assert stored == [
        ("raw-bmp", "ZBMP", "zbmp", "", "BRAND-B", "VERIFIED", "2", "", "2026-09-27T01:00:00Z"),
        ("raw-cth", "CTH", "cth", "SUBJ-C", "", "VERIFIED", "1", "", "2026-09-27T01:00:00Z"),
    ]


def test_verified_scope_rejects_tampered_signed_evidence(scope_db):
    evidence_id = _signed_scope_evidence(
        "raw-cth", product="CTH", domain="cth", subject="SUBJ-C",
    )
    with sqlite3.connect(scope_db) as conn:
        conn.execute(
            "UPDATE app_evidence_records SET inputs_json=? WHERE id=?",
            (json.dumps({"source_ids": ["other-raw"]}), evidence_id),
        )
        raw = {
            "note_id": "raw-cth", "product_id": "CTH", "domain_id": "cth",
            "subject_id": "SUBJ-C", "scope_status": "VERIFIED",
            "scope_evidence_ref": str(evidence_id),
        }
        with pytest.raises(ValueError, match="signed and verified"):
            persist_canonical(conn, note_to_canonical(raw))
        assert conn.execute("SELECT count(*) FROM canonical_data").fetchone()[0] == 0


def test_verified_scope_fails_closed_without_shared_evidence_verifier(scope_db, monkeypatch):
    evidence_id = _signed_scope_evidence(
        "raw-cth", product="CTH", domain="cth", subject="SUBJ-C",
    )
    monkeypatch.delattr(evidence_store, "classify_evidence_integrity")
    with sqlite3.connect(scope_db) as conn:
        raw = {
            "note_id": "raw-cth", "product_id": "CTH", "domain_id": "cth",
            "subject_id": "SUBJ-C", "scope_status": "VERIFIED",
            "scope_evidence_ref": str(evidence_id),
        }
        with pytest.raises(RuntimeError, match="verification is unavailable"):
            persist_canonical(conn, note_to_canonical(raw))
        assert conn.execute("SELECT count(*) FROM canonical_data").fetchone()[0] == 0


@pytest.mark.parametrize(
    ("product", "domain", "subject", "brand"),
    [
        ("CTH", "zbmp", "SUBJ-C", ""),
        ("CTH", "cth", "SUBJ-C", "BRAND-B"),
        ("ZBMP", "cth", "", "BRAND-B"),
    ],
)
def test_mixed_or_mismatched_domain_scope_is_rejected(
    scope_db, product, domain, subject, brand,
):
    with sqlite3.connect(scope_db) as conn:
        record = CanonicalRecord(
            canonical_id="CAN-invalid-scope", product_id=product, domain_id=domain,
            subject_id=subject, brand_focus_id=brand,
        )
        with pytest.raises(ValueError):
            persist_canonical(conn, record)
        assert conn.execute("SELECT count(*) FROM canonical_data").fetchone()[0] == 0
