"""Disposable regressions for reads of signed, exact-scope Canonical rows."""
import json
import sqlite3

import pytest

from canonical_data import (
    CanonicalRecord,
    ensure_canonical_table,
    list_scoped_canonical,
    persist_canonical,
    validate_source_ids,
)
from lumenis.shared.evidence import store as evidence_store


@pytest.fixture
def scope_db(tmp_path, monkeypatch):
    path = tmp_path / "canonical-scope-read.sqlite3"
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
        feature_id="CANONICAL_SCOPE_READ_TEST", test_name="source_scope",
        result="PASS", status="verified", inputs={"source_ids": [source_id]},
        outputs={"source_read": True}, domain_id=domain,
        subject_id=subject, brand_focus_id=brand,
    )


def _persist_verified(conn, source_id, *, product, domain, subject=None, brand=None,
                      captured_at="2026-09-28T01:00:00Z"):
    evidence_id = _signed_scope_evidence(
        source_id, product=product, domain=domain, subject=subject, brand=brand,
    )
    record = CanonicalRecord(
        canonical_id=f"can-{source_id}", product_id=product, domain_id=domain,
        subject_id=subject or "", brand_focus_id=brand or "",
        scope_status="VERIFIED", scope_evidence_ref=str(evidence_id),
        source_id=source_id, external_id=source_id, title=source_id,
        captured_at=captured_at,
    )
    persist_canonical(conn, record)
    conn.commit()
    return record.canonical_id, evidence_id


def test_reads_global_and_exact_focus_with_safe_scope_proofs(scope_db):
    with sqlite3.connect(scope_db) as conn:
        _persist_verified(
            conn, "raw-cth-a", product="CTH", domain="cth", subject="SUBJ-A",
        )
        _persist_verified(
            conn, "raw-cth-b", product="CTH", domain="cth", subject="SUBJ-B",
        )
        _persist_verified(
            conn, "raw-bmp-a", product="ZBMP", domain="zbmp", brand="BRAND-A",
        )
        persist_canonical(conn, CanonicalRecord(
            canonical_id="can-cth-unassigned", product_id="CTH", domain_id="cth",
            scope_status="UNASSIGNED", source_id="raw-cth-unassigned",
            external_id="raw-cth-unassigned", title="unassigned",
            captured_at="9999-12-31T00:00:00Z",
        ))
        conn.commit()
        conn.row_factory = sqlite3.Row

        cth_focus = list_scoped_canonical(conn, product_id="CTH", subject_id="SUBJ-A")
        cth_global = list_scoped_canonical(conn, product_id="cth")
        cth_global_none = list_scoped_canonical(conn, product_id="cth", source_ids=None)
        cth_limited = list_scoped_canonical(conn, product_id="CTH", limit=1)
        bmp_focus = list_scoped_canonical(conn, product_id="ZBMP", brand_focus_id="BRAND-A")
        bmp_global = list_scoped_canonical(conn, product_id="zbmp")
        bmp_alias_focus = list_scoped_canonical(conn, product_id="BMP", brand_focus_id="BRAND-A")
        bmp_alias_global = list_scoped_canonical(conn, product_id="bmp")
        selected_focus = list_scoped_canonical(
            conn, product_id="CTH", subject_id="SUBJ-A",
            source_ids=["raw-cth-a", "raw-cth-b", "raw-bmp-a"],
        )
        injected_focus = list_scoped_canonical(
            conn, product_id="CTH", subject_id="SUBJ-A' OR 1=1 --",
        )

    assert [row["source_id"] for row in cth_focus["records"]] == ["raw-cth-a"]
    assert cth_focus["candidate_count"] == cth_focus["returned_count"] == 1
    assert [row["source_id"] for row in cth_global["records"]] == [
        "raw-cth-a", "raw-cth-b",
    ]
    assert cth_global == {
        "records": cth_global["records"], "candidate_count": 3, "scanned_count": 3,
        "rejected_count": 1, "returned_count": 2, "limit": 30, "truncated": False,
    }
    assert cth_global_none == cth_global
    assert [row["source_id"] for row in selected_focus["records"]] == ["raw-cth-a"]
    assert selected_focus["candidate_count"] == selected_focus["returned_count"] == 1
    assert cth_limited["candidate_count"] == 3
    assert cth_limited["scanned_count"] == 1
    assert cth_limited["rejected_count"] == 1
    assert cth_limited["returned_count"] == 0
    assert cth_limited["truncated"] is True
    assert [row["source_id"] for row in bmp_focus["records"]] == ["raw-bmp-a"]
    assert [row["source_id"] for row in bmp_global["records"]] == ["raw-bmp-a"]
    assert bmp_global["candidate_count"] == 1
    assert bmp_alias_focus == bmp_focus
    assert bmp_alias_global == bmp_global
    assert bmp_alias_global["records"][0]["product_id"] == "ZBMP"
    assert bmp_alias_global["records"][0]["domain_id"] == "zbmp"
    assert injected_focus["records"] == []
    assert injected_focus["candidate_count"] == 0

    proof = cth_focus["records"][0]["scope_evidence"]
    assert set(proof) == {"id", "source_id", "stored_scope", "integrity"}
    assert proof["source_id"] == "raw-cth-a"
    assert proof["stored_scope"] == {
        "product_id": "CTH", "domain_id": "cth", "subject_id": "SUBJ-A",
        "brand_focus_id": "", "scope_status": "VERIFIED",
    }
    assert proof["integrity"]["verified"] is True
    assert proof["integrity"]["lineage_verified"] is True
    assert proof["integrity"]["assurance"] == "writer-authenticated"
    assert not {"inputs_json", "headers", "cookies", "key_id"}.intersection(proof)
    assert not {"inputs_json", "headers", "cookies", "integrity_key_id"}.intersection(
        cth_focus["records"][0]
    )


def test_tampered_evidence_and_source_mismatch_are_rejected(scope_db):
    with sqlite3.connect(scope_db) as conn:
        tampered_id, tampered_evidence = _persist_verified(
            conn, "raw-tampered", product="CTH", domain="cth", subject="SUBJ-A",
        )
        mismatched_id, _ = _persist_verified(
            conn, "raw-original", product="CTH", domain="cth", subject="SUBJ-A",
        )
        conn.execute(
            "UPDATE app_evidence_records SET inputs_json=? WHERE id=?",
            (json.dumps({"source_ids": ["raw-other"]}), tampered_evidence),
        )
        conn.execute(
            "UPDATE canonical_data SET source_id=? WHERE canonical_id=?",
            ("raw-not-signed", mismatched_id),
        )
        conn.commit()

        result = list_scoped_canonical(
            conn, product_id="CTH", source_ids=["raw-tampered", "raw-not-signed"],
        )

    assert tampered_id != mismatched_id
    assert result["candidate_count"] == 2
    assert result["scanned_count"] == 2
    assert result["rejected_count"] == 2
    assert result["returned_count"] == 0
    assert result["records"] == []


def test_selected_older_source_is_filtered_before_limit(scope_db):
    with sqlite3.connect(scope_db) as conn:
        _persist_verified(
            conn, "raw-old-selected", product="CTH", domain="cth", subject="SUBJ-A",
            captured_at="2020-01-01T00:00:00Z",
        )
        _persist_verified(
            conn, "raw-newer-a", product="CTH", domain="cth", subject="SUBJ-A",
            captured_at="2026-09-28T02:00:00Z",
        )
        _persist_verified(
            conn, "raw-newer-b", product="CTH", domain="cth", subject="SUBJ-A",
            captured_at="2026-09-28T03:00:00Z",
        )
        conn.row_factory = sqlite3.Row
        latest = list_scoped_canonical(
            conn, product_id="CTH", subject_id="SUBJ-A", limit=1,
        )
        selected = list_scoped_canonical(
            conn, product_id="CTH", subject_id="SUBJ-A", limit=1,
            source_ids=["raw-old-selected"],
        )

    assert [row["source_id"] for row in latest["records"]] == ["raw-newer-b"]
    assert [row["source_id"] for row in selected["records"]] == ["raw-old-selected"]
    assert selected["candidate_count"] == selected["scanned_count"] == selected["returned_count"] == 1
    assert selected["truncated"] is False


def test_validate_source_ids_returns_a_detached_exact_selection():
    supplied = ["raw-source-a"]
    selected = validate_source_ids(supplied, limit=1)
    assert selected == supplied and selected is not supplied
    selected.append("local-only")
    assert supplied == ["raw-source-a"]
    assert validate_source_ids(None) is None
    assert validate_source_ids(["x" * 512]) == ["x" * 512]
    assert len(validate_source_ids([f"raw-{index}" for index in range(100)])) == 100


@pytest.mark.parametrize(
    ("source_ids", "limit"),
    [
        ("raw-source", 30),
        ((), 30),
        ([], 30),
        (["raw-source", "raw-source"], 30),
        ([None], 30),
        (["   "], 30),
        (["x" * 513], 30),
        (["raw\x01source"], 30),
        ([f"raw-{index}" for index in range(101)], 100),
        (["raw-a", "raw-b"], 1),
    ],
)
def test_source_ids_inputs_are_strict(scope_db, source_ids, limit):
    with sqlite3.connect(scope_db) as conn:
        with pytest.raises(ValueError, match="source_ids"):
            list_scoped_canonical(
                conn, product_id="CTH", limit=limit, source_ids=source_ids,
            )


@pytest.mark.parametrize(
    ("kwargs", "error", "message"),
    [
        ({"product_id": "OTHER"}, ValueError, "product_id"),
        ({"product_id": "CTH", "subject_id": "SUBJ", "brand_focus_id": "BRAND"}, ValueError, "mixed"),
        ({"product_id": "CTH", "brand_focus_id": "BRAND"}, ValueError, "CTH"),
        ({"product_id": "ZBMP", "subject_id": "SUBJ"}, ValueError, "ZBMP"),
        ({"product_id": "CTH", "limit": True}, TypeError, "integer"),
        ({"product_id": "CTH", "limit": 0}, ValueError, "between"),
        ({"product_id": "CTH", "limit": 101}, ValueError, "between"),
        ({"product_id": "CTH", "subject_id": ""}, ValueError, "non-empty"),
        ({"product_id": "CTH", "subject_id": " SUBJ"}, ValueError, "exact"),
    ],
)
def test_scope_and_limit_inputs_are_strict(scope_db, kwargs, error, message):
    with sqlite3.connect(scope_db) as conn:
        with pytest.raises(error, match=message):
            list_scoped_canonical(conn, **kwargs)


def test_storage_errors_propagate_instead_of_becoming_empty_results():
    with sqlite3.connect(":memory:") as conn:
        with pytest.raises(sqlite3.OperationalError, match="no such table"):
            list_scoped_canonical(conn, product_id="CTH")


def test_missing_evidence_verifier_propagates_as_unavailable(scope_db, monkeypatch):
    with sqlite3.connect(scope_db) as conn:
        _persist_verified(
            conn, "raw-cth", product="CTH", domain="cth", subject="SUBJ-A",
        )
        conn.commit()
        monkeypatch.delattr(evidence_store, "classify_evidence_integrity")
        with pytest.raises(RuntimeError, match="verification is unavailable"):
            list_scoped_canonical(conn, product_id="CTH")
