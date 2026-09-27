"""Isolated acceptance for Evidence-backed entity relations and tenants."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager

import pytest

from lumenis.shared.database import DatabaseRepository, migrations
from lumenis.shared.database.entity_relations import (
    EntityRelationError,
    EntityRelationRepository,
    country_bucket,
)
from lumenis.shared.evidence import store as evidence_store


@pytest.fixture
def country_client(relation_db, monkeypatch):
    from flask import Flask
    import subject_registry
    import lumenis.auth.service as auth
    import account.authorization as authorization

    @contextmanager
    def read_connection():
        conn = sqlite3.connect(f"file:{relation_db['path'].as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def list_subjects(domain):
        with read_connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM lumenis_subject_registry WHERE domain_id=?", (domain,)
            )]

    monkeypatch.setattr(subject_registry, "list_subjects", list_subjects)
    monkeypatch.setattr(auth, "get_current_user", lambda: {"id": 71})
    monkeypatch.setattr(authorization, "check_dual_domain_permission", lambda *a, **k: True)
    app = Flask(__name__)
    app.register_blueprint(subject_registry.subject_registry_bp)
    return app.test_client()


def test_country_selector_keeps_country_roles_separate_and_does_not_write(
    relation_db, country_client,
):
    conn = relation_db["conn"]
    repo = EntityRelationRepository(conn)
    for role, country in [("HQ", "US"), ("OPERATES_IN", "CN")]:
        repo.record_country_relation(
            domain_id="BMP", subject_id="SUBJ-BMP", relation_type=role,
            country_iso=country, source_evidence_ref=relation_db["bmp_ref"],
            source_note_id="note-bmp",
        )
    conn.commit()
    before = relation_db["path"].read_bytes()
    response = country_client.get(
        "/api/settings/subjects?domain_id=BMP&country_iso=US&relation_type=HQ"
    )
    assert response.status_code == 200
    result = response.get_json()
    assert len(result["country_categories"]) == 14
    assert [row["brand_focus_id"] for row in result["subjects"]] == ["BRAND-1"]
    projection = result["country_projection"]
    assert projection["status"] == "UNREVIEWED"
    assert projection["observed_entity_count"] == 1
    assert projection["coverage_total"] is None
    assert projection["coverage_status"] == "NOT_VERIFIED"
    assert projection["claims"][0]["source_evidence_ref"] == relation_db["bmp_ref"]
    response = country_client.get(
        "/api/settings/subjects?domain_id=BMP&country_iso=US&relation_type=OPERATES_IN"
    )
    result = response.get_json()
    assert result["subjects"] == []
    assert result["country_projection"]["status"] == "NOT_COLLECTED"
    assert result["country_projection"]["coverage_total"] is None
    assert relation_db["path"].read_bytes() == before


@pytest.mark.parametrize("query", [
    "country_iso=US", "domain_id=BMP&country_iso=US", "domain_id=BMP&relation_type=HQ",
    "domain_id=BMP&country_iso=OTHER&relation_type=TENANT_OF",
])
def test_country_selector_rejects_ambiguous_filters(country_client, query):
    response = country_client.get("/api/settings/subjects?" + query)
    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_COUNTRY_FILTER"


@pytest.mark.parametrize("signed_in,allowed,expected", [(False, True, 401), (True, False, 403)])
def test_country_selector_denies_before_read(country_client, monkeypatch, signed_in, allowed, expected):
    import subject_registry
    import lumenis.auth.service as auth
    import account.authorization as authorization

    monkeypatch.setattr(auth, "get_current_user", lambda: {"id": 71} if signed_in else None)
    monkeypatch.setattr(authorization, "check_dual_domain_permission", lambda *a, **k: allowed)
    def forbidden_read(*args):
        pytest.fail("denied request reached the relation reader")
    monkeypatch.setattr(subject_registry, "_country_subject_projection", forbidden_read)
    monkeypatch.setattr(subject_registry, "list_subjects", forbidden_read)
    assert country_client.get(
        "/api/settings/subjects?domain_id=CTH&country_iso=CN&relation_type=VENUE_LOCATION"
    ).status_code == expected


def test_country_selector_never_selects_rejected_membership(relation_db, country_client):
    conn = relation_db["conn"]
    relation_id = EntityRelationRepository(conn).record_country_relation(
        domain_id="BMP", subject_id="SUBJ-BMP", relation_type="HQ", country_iso="DE",
        source_evidence_ref=relation_db["bmp_ref"], source_note_id="note-bmp",
    )
    conn.execute("UPDATE lumenis_entity_relation_assertions SET review_status='REJECTED' WHERE assertion_id=?", (relation_id,))
    conn.commit()
    result = country_client.get(
        "/api/settings/subjects?domain_id=BMP&country_iso=OTHER&relation_type=HQ"
    ).get_json()
    assert result["subjects"] == []
    assert result["country_projection"]["observed_entity_count"] == 0
    assert result["country_projection"]["claims"][0]["country_iso"] == "DE"
    assert result["country_projection"]["claims"][0]["review_status"] == "REJECTED"


@pytest.fixture
def relation_db(tmp_path, monkeypatch):
    db_path = tmp_path / "entity-relations.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    repository = DatabaseRepository(str(db_path))
    monkeypatch.setattr(evidence_store, "get_repository", lambda: repository)
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"entity-relations-test": "isolated-test-signing-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "entity-relations-test")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
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
    conn.executescript("""
        CREATE TABLE lumenis_subject_registry (
            subject_id TEXT PRIMARY KEY,
            brand_focus_id TEXT UNIQUE,
            domain_id TEXT NOT NULL,
            subject_type TEXT NOT NULL,
            name_en TEXT NOT NULL,
            name_zh TEXT NOT NULL,
            status TEXT NOT NULL
        );
        CREATE TABLE notes (
            note_id TEXT UNIQUE NOT NULL,
            url TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            product_id TEXT,
            domain_id TEXT,
            subject_id TEXT,
            brand_focus_id TEXT,
            scope_status TEXT NOT NULL,
            scope_evidence_ref TEXT NOT NULL DEFAULT ''
        );
        INSERT INTO lumenis_subject_registry VALUES
            ('SUBJ-CTH', NULL, 'CTH', 'company', 'Taikoo Hui', '太古汇', 'configured'),
            ('SUBJ-BMP', 'BRAND-1', 'BMP', 'brand', 'Example Brand', '示例品牌', 'configured'),
            ('SUBJ-OTHER', NULL, 'CTH', 'company', 'Other Venue', '其他场地', 'configured');
        INSERT INTO notes VALUES
            ('note-cth-zh', 'https://mall.example/zh-cn/shopping/?page=0',
             'Apple B1 Electronics official store card', 'CTH', 'cth', 'SUBJ-CTH', NULL, 'VERIFIED', ''),
            ('note-cth-en', 'https://mall.example/en/shopping/?page=0',
             'Apple B1 Electronics official store card', 'CTH', 'cth', 'SUBJ-CTH', NULL, 'VERIFIED', ''),
            ('note-bmp', 'https://brand.example/company', 'Head office Beaverton',
             'ZBMP', 'zbmp', NULL, 'BRAND-1', 'VERIFIED', ''),
            ('note-other', 'https://other.example/', 'Other venue content',
             'CTH', 'cth', 'SUBJ-OTHER', NULL, 'VERIFIED', '');
    """)
    conn.commit()
    conn.close()

    def evidence_for(note_id, *, domain="cth", subject_id="SUBJ-CTH", brand_focus_id=None, captured_at="2026-09-27T10:00:00+08:00"):
        kwargs = {
            "source": "public_http",
            "project": "LUMENIS",
            "product": "CTH" if domain == "cth" else "BMP",
            "feature_id": "ENTITY-RELATION-TEST",
            "test_name": "entity_relation_source",
            "result": "PASS",
            "status": "verified",
            "capture_mode": "automated",
            "captured_at": captured_at,
            "inputs": {"source_ids": [note_id]},
            "outputs": {"source_read": True},
            "metric_name": "source_read",
            "metric_value": "PASS",
            "domain_id": domain,
        }
        if domain == "cth":
            kwargs["subject_id"] = subject_id
        else:
            kwargs["brand_focus_id"] = brand_focus_id
        ref = evidence_store.record_evidence(**kwargs)
        assert ref > 0
        conn = sqlite3.connect(db_path)
        conn.execute(
            "UPDATE notes SET scope_evidence_ref=? WHERE note_id=?", (str(ref), note_id)
        )
        conn.commit()
        conn.close()
        return ref

    cth_zh_ref = evidence_for("note-cth-zh")
    cth_en_ref = evidence_for("note-cth-en", captured_at="2026-09-27T10:05:00+08:00")
    bmp_ref = evidence_for("note-bmp", domain="zbmp", brand_focus_id="BRAND-1")
    other_ref = evidence_for("note-other", subject_id="SUBJ-OTHER")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrations.migration_17_to_18(conn)
    migrations.migration_17_to_18(conn)
    conn.commit()
    yield {
        "path": db_path,
        "conn": conn,
        "cth_zh_ref": cth_zh_ref,
        "cth_en_ref": cth_en_ref,
        "bmp_ref": bmp_ref,
        "other_ref": other_ref,
    }
    conn.close()


def test_v18_country_query_joins_exact_registry_and_derives_other_bucket(relation_db):
    conn = relation_db["conn"]
    repo = EntityRelationRepository(conn)
    assertion_id = repo.record_country_relation(
        domain_id="BMP",
        subject_id="SUBJ-BMP",
        relation_type="MARKET_ACTIVITY",
        country_iso="DE",
        source_evidence_ref=relation_db["bmp_ref"],
        source_note_id="note-bmp",
    )
    retry_id = repo.record_country_relation(
        domain_id="ZBMP",
        subject_id="SUBJ-BMP",
        relation_type="MARKET_ACTIVITY",
        country_iso="de",
        source_evidence_ref=relation_db["bmp_ref"],
        source_note_id="note-bmp",
    )
    assert retry_id == assertion_id
    assert conn.execute("SELECT COUNT(*) FROM lumenis_entity_relation_assertions").fetchone()[0] == 1

    result = repo.query_country_entities(
        domain_id="BMP", country_iso="OTHER", relation_type="MARKET_ACTIVITY"
    )
    assert result["status"] == "UNREVIEWED"
    assert result["country_bucket"] == "OTHER"
    assert result["entities"][0]["subject_id"] == "SUBJ-BMP"
    claim = result["entities"][0]["claims"][0]
    assert claim["country_iso"] == "DE"
    assert claim["evidence_ref_type"] == "app_evidence_records"
    assert claim["evidence_integrity"] == "VERIFIED"
    assert claim["source_note_id"] == "note-bmp"
    assert country_bucket("DE") == "OTHER"
    with pytest.raises(EntityRelationError):
        repo.record_country_relation(
            domain_id="BMP",
            subject_id="SUBJ-BMP",
            relation_type="HQ",
            country_iso="OTHER",
            source_evidence_ref=relation_db["bmp_ref"],
            source_note_id="note-bmp",
        )


def test_country_query_preserves_absence_capture_time_and_conflict_status(relation_db):
    conn = relation_db["conn"]
    repo = EntityRelationRepository(conn)
    assertion_id = repo.record_country_relation(
        domain_id="CTH",
        subject_id="SUBJ-CTH",
        relation_type="VENUE_LOCATION",
        country_iso="CN",
        source_evidence_ref=relation_db["cth_zh_ref"],
        source_note_id="note-cth-zh",
    )
    absent_id = repo.record_country_relation(
        domain_id="CTH",
        subject_id="SUBJ-CTH",
        relation_type="OPERATES_IN",
        country_iso="NO",
        source_evidence_ref=relation_db["cth_zh_ref"],
        source_note_id="note-cth-zh",
        claim_kind="EXPLICIT_ABSENCE",
    )
    assert assertion_id != absent_id
    cn = repo.query_country_entities(
        domain_id="CTH", country_iso="CN", relation_type="VENUE_LOCATION",
        as_of="2026-09-27",
    )
    assert cn["entities"][0]["subject_id"] == "SUBJ-CTH"
    assert cn["entities"][0]["claims"][0]["evidence_captured_at"].startswith("2026-09-27")
    assert repo.query_country_entities(
        domain_id="CTH", country_iso="CN", relation_type="VENUE_LOCATION",
        as_of="2026-09-28",
    )["status"] == "NOT_ESTABLISHED_FOR_AS_OF"
    no_result = repo.query_country_entities(
        domain_id="CTH", country_iso="NO", relation_type="OPERATES_IN"
    )
    assert no_result["status"] == "EXPLICIT_ABSENCE"
    assert not no_result["entities"]
    assert no_result["absence_claims"][0]["claim_kind"] == "EXPLICIT_ABSENCE"

    conn.execute(
        "UPDATE lumenis_entity_relation_assertions SET review_status='CONFLICTED', "
        "conflict_group='reviewed-conflict-1' WHERE assertion_id=?", (assertion_id,)
    )
    conn.commit()
    conflicted = repo.query_country_entities(
        domain_id="CTH", country_iso="CN", relation_type="VENUE_LOCATION"
    )
    assert conflicted["status"] == "CONFLICT"
    assert conflicted["entities"][0]["status"] == "CONFLICTED"


def test_tenant_claim_is_locale_specific_literal_and_source_bound(relation_db):
    conn = relation_db["conn"]
    repo = EntityRelationRepository(conn)
    values = {
        "venue_subject_id": "SUBJ-CTH",
        "source_evidence_ref": relation_db["cth_zh_ref"],
        "source_note_id": "note-cth-zh",
        "tenant_name": "Apple",
        "floor": "B1",
        "category": "Electronics",
        "detail_url": "https://mall.example/store/apple",
        "listing_url": "https://mall.example/zh-cn/shopping/?page=0",
        "source_locale": "zh-CN",
    }
    assertion_id = repo.record_venue_tenant_claim(**values)
    assert repo.record_venue_tenant_claim(**values) == assertion_id
    english = dict(values)
    english.update(
        source_evidence_ref=relation_db["cth_en_ref"],
        source_note_id="note-cth-en",
        listing_url="https://mall.example/en/shopping/?page=0",
        source_locale="en",
    )
    english_id = repo.record_venue_tenant_claim(**english)
    assert english_id != assertion_id

    result = repo.query_venue_tenant_claims(venue_subject_id="SUBJ-CTH")
    assert result["status"] == "UNREVIEWED"
    assert len(result["claims"]) == 2
    assert {claim["source_locale"] for claim in result["claims"]} == {"zh-CN", "en"}
    assert all(claim["target_subject_id"] is None for claim in result["claims"])
    assert all(claim["relation_type"] == "TENANT_OF" for claim in result["claims"])
    assert all(claim["evidence_ref_type"] == "app_evidence_records" for claim in result["claims"])
    assert all(claim["evidence_integrity"] == "VERIFIED" for claim in result["claims"])

    with pytest.raises(EntityRelationError, match="listing_url"):
        repo.record_venue_tenant_claim(**{**values, "listing_url": "https://wrong.example/"})
    with pytest.raises(EntityRelationError, match="tenant_name"):
        repo.record_venue_tenant_claim(**{**values, "tenant_name": "Invented Store"})
    with pytest.raises(EntityRelationError, match="target_brand_focus_id"):
        repo.record_venue_tenant_claim(**{**values, "target_brand_focus_id": "BRAND-MISSING"})
    conn.execute("UPDATE notes SET content='' WHERE note_id='note-cth-zh'")
    conn.commit()
    with pytest.raises(EntityRelationError, match="content is empty"):
        repo.record_venue_tenant_claim(**values)


def test_relation_writer_rejects_cross_identity_and_tampered_source(relation_db):
    conn = relation_db["conn"]
    repo = EntityRelationRepository(conn)
    with pytest.raises(EntityRelationError, match="_lumenis_scope"):
        repo.record_country_relation(
            domain_id="CTH",
            subject_id="SUBJ-OTHER",
            relation_type="HQ",
            country_iso="US",
            source_evidence_ref=relation_db["cth_zh_ref"],
            source_note_id="note-cth-zh",
        )

    repo.record_country_relation(
        domain_id="BMP",
        subject_id="SUBJ-BMP",
        relation_type="HQ",
        country_iso="US",
        source_evidence_ref=relation_db["bmp_ref"],
        source_note_id="note-bmp",
    )
    conn.execute(
        "UPDATE app_evidence_records SET inputs_json=? WHERE id=?",
        (json.dumps({"_lumenis_scope": {"domain_id": "zbmp", "product_id": "ZBMP", "global": False, "brand_focus_id": "BRAND-1"}, "source_ids": ["note-bmp"], "tampered": True}), relation_db["bmp_ref"]),
    )
    conn.commit()
    result = repo.query_country_entities(domain_id="BMP", country_iso="US", relation_type="HQ")
    assert result["status"] == "EVIDENCE_INVALID"
    assert not result["entities"]
    assert result["claims"][0]["evidence_integrity"] == "INVALID"
