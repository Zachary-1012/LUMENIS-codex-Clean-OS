"""PO-provided Taikoo Hui directory: seed provenance and Evidence-backed tenant claims."""
from __future__ import annotations

import json
import sqlite3

import pytest

from scripts import import_subject_registry_seed as seed
from scripts import import_tkh_directory_relations as tkh


def test_tkh_seed_is_po_provided_pinned_and_unique():
    rows = seed.load_seed(*seed.SEEDS["tkh"])
    manifest = json.loads(seed.SEEDS["tkh"][1].read_text(encoding="utf-8"))
    assert manifest["approval_ref"] == "PO-20261013-TKH-DIRECTORY-INGEST"
    assert all(r["verification_status"] == seed.PO_PROVIDED for r in rows)
    assert all(r["source_url"] == manifest["source_uri"] for r in rows)
    assert all((r["domain_id"], r["subject_type"]) == ("BMP", "brand") for r in rows)
    names = [r["name_en"].casefold() for r in rows]
    assert len(names) == len(set(names))


def test_po_provided_row_without_pinned_manifest_is_rejected():
    row = {"verification_status": seed.PO_PROVIDED, "source_url": "po-provided://x#sha256=ab"}
    assert not seed._row_provenance_ok(row, {"source_class": "OTHER"})
    assert not seed._row_provenance_ok(row, {"source_class": seed.PO_PROVIDED, "approval_ref": "",
                                             "source_sha256": "ab", "source_uri": row["source_url"]})


def test_directory_excludes_mandarin_oriental_and_pins_literals():
    rows, manifest = tkh.load_directory()
    assert manifest["store_count"] == len(rows)
    assert len(manifest["excluded_mandarin_oriental"]) == 6
    assert not any(u.upper().startswith("MOH") for r in rows for u in r["units"])
    stores = {r["store_name"]: r for r in rows}
    assert [t["tenant_literal"] for t in stores["A BATHING APE、I.T"]["target_brands"]] == ["A BATHING APE", "I.T"]
    assert stores["DIOR"]["moh_units_excluded"] == ["MOH L102"]
    content = tkh.source_note_content(rows).casefold()
    for claim in tkh.tenant_claims(rows):
        assert claim["tenant_name"].casefold() in content and claim["floor"].casefold() in content


def test_dry_run_and_apply_requires_approval(monkeypatch):
    rows, manifest = tkh.load_directory()
    report = tkh.import_directory(rows, manifest)
    assert report["would_write"] == report["claims"] == len(tkh.tenant_claims(rows))
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    from lumenis.system.security import permission
    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False, raising=False)
    permission.reset_permission_gate()
    with pytest.raises(tkh.DirectoryApprovalRequired):
        tkh.import_directory(rows, manifest, apply=True)


@pytest.fixture
def product_db(tmp_path, monkeypatch):
    from canonical_data import ensure_canonical_scope_columns, ensure_canonical_table
    from lumenis.shared.database import DatabaseRepository
    from lumenis.shared.database.entity_relations import ensure_entity_relation_schema
    from lumenis.shared.evidence import store as evidence_store

    path = tmp_path / "tkh.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    repository = DatabaseRepository(str(path))
    monkeypatch.setattr(evidence_store, "get_repository", lambda: repository)
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({"tkh-test": "isolated-test-key"}))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "tkh-test")
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE lumenis_subject_registry (
            subject_id TEXT PRIMARY KEY, brand_focus_id TEXT UNIQUE, domain_id TEXT NOT NULL,
            subject_type TEXT NOT NULL, name_en TEXT NOT NULL, name_zh TEXT NOT NULL, status TEXT NOT NULL);
        INSERT INTO lumenis_subject_registry VALUES
            ('SUBJ-TKH', NULL, 'CTH', 'company', 'Guangzhou Taikoo Hui', '广州太古汇', 'configured'),
            ('SUBJ-LV', 'BRAND-LV', 'BMP', 'brand', 'Louis Vuitton', 'Louis Vuitton', 'configured');
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, note_id TEXT UNIQUE NOT NULL, title TEXT, content TEXT DEFAULT '', body TEXT, url TEXT NOT NULL,
            cover TEXT, author_id TEXT, author_nickname TEXT, likes INTEGER, comments INTEGER,
            collects INTEGER, shares INTEGER, publish_date TEXT, publish_datetime TEXT,
            source_platform TEXT, source_keyword TEXT, captured_at TEXT, last_seen_at TEXT, collected_at TEXT,
            collector_version TEXT, status TEXT, verification_status TEXT, ai_filter_status TEXT,
            is_taikoo_verified INTEGER, relevance_status TEXT, data_quality_status TEXT,
            product_id TEXT, domain_id TEXT, subject_id TEXT, brand_focus_id TEXT,
            scope_status TEXT NOT NULL DEFAULT 'UNASSIGNED', scope_evidence_ref TEXT NOT NULL DEFAULT '');
    """)
    evidence_store.ensure_evidence_schema(con)
    cols = {r[1] for r in con.execute("PRAGMA table_info(app_evidence_records)")}
    for column, kind, default in evidence_store.EVIDENCE_CHAIN_NEW_COLUMNS:
        if column not in cols:
            suffix = f" DEFAULT {default}" if default != "NULL" else ""
            con.execute(f"ALTER TABLE app_evidence_records ADD COLUMN {column} {kind}{suffix}")
    ensure_canonical_table(connection=con)
    ensure_canonical_scope_columns(con)
    con.commit()
    ensure_entity_relation_schema(con)
    con.commit()
    con.close()
    return path


def test_apply_writes_signed_unreviewed_claims_idempotently(product_db, monkeypatch):
    monkeypatch.setattr(tkh, "require_apply_approval", lambda gate=None: None)
    rows, manifest = tkh.load_directory()
    con = sqlite3.connect(product_db)
    first = tkh.import_directory(rows, manifest, apply=True, conn=con)
    assert first["written"] == first["claims"] and first["venue_subject_id"] == "SUBJ-TKH"
    second = tkh.import_directory(rows, manifest, apply=True, conn=sqlite3.connect(product_db))
    assert second["written"] == 0 and second["evidence_ref"] == first["evidence_ref"]
    from lumenis.shared.database.entity_relations import EntityRelationRepository
    read = sqlite3.connect(product_db)
    read.row_factory = sqlite3.Row
    statuses = {r[0] for r in read.execute(
        "SELECT review_status FROM lumenis_entity_relation_assertions")}
    assert statuses == {"UNREVIEWED"}
    lv = read.execute("SELECT COUNT(*) FROM lumenis_entity_relation_assertions a "
                      "JOIN lumenis_subject_registry s ON s.subject_id=a.target_subject_id "
                      "WHERE s.brand_focus_id='BRAND-LV'").fetchone()[0]
    assert lv == 4  # L101, L201, L202, L203
    claims = EntityRelationRepository(read).query_venue_tenant_claims(venue_subject_id="SUBJ-TKH")
    assert claims
