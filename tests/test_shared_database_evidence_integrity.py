"""Signed Evidence integrity uses the canonical Evidence owner and isolated v18 DB."""
from __future__ import annotations

import json
import sqlite3

import pytest


@pytest.fixture
def v18_db(tmp_path, monkeypatch):
    from canonical_data import ensure_canonical_table
    from lumenis.shared.database import migrations
    from lumenis.shared.database.business_schema import apply_business_schema
    from lumenis.shared.evidence.store import EVIDENCE_CHAIN_NEW_COLUMNS, ensure_evidence_schema
    import subject_registry

    path = tmp_path / "signed-evidence-v18.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"isolated-test-key": "test-only-signing-secret"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "isolated-test-key")
    with sqlite3.connect(path) as conn:
        apply_business_schema(conn)
        conn.execute("ALTER TABLE notes ADD COLUMN domain_id TEXT DEFAULT 'cth'")
        conn.execute("ALTER TABLE notes ADD COLUMN product_id TEXT DEFAULT 'CTH'")
        ensure_canonical_table(connection=conn)
        migrations.migration_13_to_14(conn)
        subject_registry.ensure_schema(conn)
        ensure_evidence_schema(conn)
        evidence_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(app_evidence_records)")
        }
        for column, kind, default in EVIDENCE_CHAIN_NEW_COLUMNS:
            if column not in evidence_columns:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                conn.execute(
                    f"ALTER TABLE app_evidence_records ADD COLUMN {column} {kind}{suffix}"
                )
        conn.execute(
            "INSERT INTO lumenis_subject_registry "
            "(subject_id, domain_id, subject_type, name_en, name_zh, "
            "name_en_norm, name_zh_norm, created_at, updated_at) "
            "VALUES ('SUBJ-SIGNED', 'CTH', 'company', 'Venue', '场地', 'venue', '场地', 'now', 'now')"
        )
        migrations.migration_17_to_18(conn)
        migrations.init_version_table(conn)
        migrations.set_version(conn, 18, migrations.MIGRATION_HISTORY[18])
    return path


def _record_scoped_evidence(store):
    return store.record_evidence(
        source="public_http",
        product="CTH",
        feature_id="scope-test",
        result="PASS",
        status="verified",
        metric_name="source_read",
        metric_value="PASS",
        inputs={
            "source_url": "https://source.example.test/",
            "source_ids": ["source-note-1"],
        },
        domain_id="cth",
        subject_id="SUBJ-SIGNED",
    )


def test_scoped_evidence_is_signed_and_scope_payload_is_covered(v18_db):
    from lumenis.shared.evidence import store

    evidence_id = _record_scoped_evidence(store)
    assert evidence_id > 0
    with sqlite3.connect(v18_db) as conn:
        conn.row_factory = sqlite3.Row
        record = conn.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)
        ).fetchone()
        assert record["integrity_version"] == store.EVIDENCE_INTEGRITY_VERSION
        assert record["integrity_algorithm"] == "hmac-sha256"
        assert record["integrity_key_id"] == "isolated-test-key"
        assert store.verify_evidence_record_integrity(record)
        assert store.classify_evidence_integrity(record) == {
            "version": 2, "algorithm": "hmac-sha256", "key_id": "isolated-test-key",
            "verified": True, "assurance": "writer-authenticated",
        }
        scoped_inputs = json.loads(record["inputs_json"])
        assert scoped_inputs["_lumenis_scope"] == {
            "domain_id": "cth", "product_id": "CTH", "global": False,
            "subject_id": "SUBJ-SIGNED",
        }
        assert scoped_inputs["source_ids"] == ["source-note-1"]


def test_tampered_scope_or_missing_verification_key_fails_closed(v18_db, monkeypatch):
    from lumenis.shared.evidence import store

    evidence_id = _record_scoped_evidence(store)
    assert evidence_id > 0
    with sqlite3.connect(v18_db) as conn:
        conn.row_factory = sqlite3.Row
        record = conn.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)
        ).fetchone()
        tampered = dict(record)
        inputs = json.loads(tampered["inputs_json"])
        inputs["_lumenis_scope"]["subject_id"] = "SUBJ-OTHER"
        tampered["inputs_json"] = json.dumps(inputs, sort_keys=True)
        assert not store.verify_evidence_record_integrity(tampered)
        assert store.classify_evidence_integrity(tampered)["assurance"] == "tampered"
        tampered_source_ids = dict(record)
        tampered_inputs = json.loads(tampered_source_ids["inputs_json"])
        tampered_inputs["source_ids"] = ["source-note-2"]
        tampered_source_ids["inputs_json"] = json.dumps(tampered_inputs, sort_keys=True)
        assert not store.verify_evidence_record_integrity(tampered_source_ids)

    monkeypatch.delenv("LUMENIS_EVIDENCE_HMAC_KEY_RING")
    monkeypatch.delenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID")
    with sqlite3.connect(v18_db) as conn:
        conn.row_factory = sqlite3.Row
        record = conn.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)
        ).fetchone()
        assert not store.verify_evidence_record_integrity(record)
        assert store.classify_evidence_integrity(record)["assurance"] == (
            "writer-authenticated-key-unavailable"
        )
    assert _record_scoped_evidence(store) == -1
    with sqlite3.connect(v18_db) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM app_evidence_records WHERE id>?", (evidence_id,)
        ).fetchone()[0] == 0


def test_legacy_evidence_without_integrity_fields_is_unverified():
    from lumenis.shared.evidence.store import (
        classify_evidence_integrity,
        verify_evidence_record_integrity,
    )

    record = {
        "id": 41,
        "integrity_version": None,
        "integrity_algorithm": None,
        "integrity_key_id": None,
        "integrity_digest": None,
    }
    assert not verify_evidence_record_integrity(record)
    assert classify_evidence_integrity(record)["assurance"] == "legacy-partial"
