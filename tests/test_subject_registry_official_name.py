"""record_official_name preserves source declarations and scoped provenance."""
from __future__ import annotations

import json
import pytest


@pytest.fixture
def reg(tmp_path, monkeypatch):
    db_path = tmp_path / "r.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", '{"official-name-test":"synthetic-test-key"}')
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "official-name-test")
    import subject_registry as registry
    from lumenis.shared.evidence.store import ensure_evidence_schema, init_evidence_store

    init_evidence_store(str(db_path))
    with registry._db_ready() as connection:
        ensure_evidence_schema(connection)
    return registry


def _add(registry):
    row, _ = registry.add_subject({"domain_id": "BMP", "subject_type": "brand",
                                   "name_en": "Sephora", "name_zh": "Sephora", "keywords": []})
    return row["subject_id"]


def test_records_official_name_and_alias_keeps_id(reg):
    from lumenis.shared.evidence.store import verify_evidence_record_integrity

    sid = _add(reg)
    source_url = "http://www.sephora.cn/official"
    out = reg.record_official_name("BMP", sid, source_url=source_url,
                                   name_zh="丝芙兰", keywords=["SEPHORA"])
    assert out["changed"] and out["after"]["subject_id"] == sid
    assert out["after"]["name_zh"] == "丝芙兰" and "SEPHORA" in out["after"]["keywords"]
    assert out["source_url"] == source_url
    provenance = out["source_provenance"]
    assert provenance["source_url"] == source_url
    assert provenance["evidence_ref"].startswith("app_evidence_records:")
    assert provenance["origin_verification"] == "NOT_INDEPENDENTLY_VERIFIED"
    assert provenance["identity_verification"] == "NOT_VERIFIED"

    evidence_id = int(provenance["evidence_ref"].rsplit(":", 1)[1])
    with reg._db_ready() as connection:
        evidence = connection.execute(
            "SELECT * "
            "FROM app_evidence_records WHERE id=?", (evidence_id,),
        ).fetchone()
    inputs = json.loads(evidence["inputs_json"])
    outputs = json.loads(evidence["outputs_json"])
    assert inputs["source_url"] == source_url
    assert inputs["_lumenis_scope"]["brand_focus_id"] == out["after"]["brand_focus_id"]
    assert inputs["keywords_before"] == []
    assert inputs["keywords_requested"] == ["SEPHORA"]
    assert outputs["source_url"] == source_url
    assert outputs["keywords_after"] == ["SEPHORA"]
    assert evidence["subject_scope"] == out["after"]["brand_focus_id"]
    assert outputs["authenticity_score_state"] == "NOT_ASSESSED"
    assert outputs["url_scheme_is_identity_proof"] is False
    assert outputs["network_fetch"] == "NOT_PERFORMED"
    assert evidence["domain_id"] == "zbmp" and evidence["product_id"] == "ZBMP"
    assert evidence["status"] == "pending" and evidence["result"] == "GAP"
    assert evidence["authenticity_score"] is None
    assert verify_evidence_record_integrity(evidence) is True

    again = reg.record_official_name("BMP", sid, source_url=source_url, name_zh="丝芙兰")
    assert again["changed"] is False


def test_existing_evidence_writer_preserves_unknown_authenticity(reg):
    from lumenis.shared.evidence.store import record_evidence

    with reg._db_ready() as connection:
        omitted_score_id = record_evidence(
            connection=connection,
            source="test",
            feature_id="FIX-025-UNKNOWN-SCORE-OMITTED",
            result="GAP",
            status="pending",
            authenticity_score=None,
        )
        default_score_id = record_evidence(
            connection=connection,
            source="test",
            feature_id="FIX-025-UNKNOWN-SCORE-DEFAULT",
            result="GAP",
            status="pending",
        )
        zero_score_id = record_evidence(
            connection=connection,
            source="test",
            feature_id="FIX-025-UNKNOWN-SCORE-ZERO",
            result="GAP",
            status="pending",
            authenticity_score=0.0,
        )
        omitted_score = connection.execute(
            "SELECT authenticity_score FROM app_evidence_records WHERE id=?",
            (omitted_score_id,),
        ).fetchone()[0]
        default_score = connection.execute(
            "SELECT authenticity_score FROM app_evidence_records WHERE id=?",
            (default_score_id,),
        ).fetchone()[0]
        zero_score = connection.execute(
            "SELECT authenticity_score FROM app_evidence_records WHERE id=?",
            (zero_score_id,),
        ).fetchone()[0]

    # Explicit NULL overrides the legacy DEFAULT 1.0; a numeric zero remains
    # a distinct measured value.
    assert omitted_score is None
    assert default_score is None
    assert zero_score == 0.0


def test_evidence_failure_rolls_back_name_change_and_allows_retry(reg, monkeypatch):
    from lumenis.shared.evidence import store as evidence_store

    sid = _add(reg)
    original_record_evidence = evidence_store.record_evidence

    def fail_evidence_write(**_kwargs):
        raise RuntimeError("synthetic evidence write failure")

    monkeypatch.setattr(evidence_store, "record_evidence", fail_evidence_write)
    with pytest.raises(RuntimeError, match="synthetic evidence write failure"):
        reg.record_official_name(
            "BMP", sid, source_url="https://official.example/brand",
            name_zh="新名称",
        )

    unchanged = reg.get_subject_by_id("BMP", sid)
    assert unchanged["name_zh"] == "Sephora"
    with reg._db_ready() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id=?",
            (reg.OFFICIAL_NAME_SOURCE_FEATURE_ID,),
        ).fetchone()[0]
    assert count == 0

    monkeypatch.setattr(evidence_store, "record_evidence", original_record_evidence)
    recovered = reg.record_official_name(
        "BMP", sid, source_url="https://official.example/brand",
        name_zh="新名称",
    )
    assert recovered["after"]["name_zh"] == "新名称"
    assert recovered["source_provenance"]["identity_verification"] == "NOT_VERIFIED"


@pytest.mark.parametrize("url", ["", "www.sephora.cn", "ftp://x"])
def test_requires_official_source_url(reg, url):
    sid = _add(reg)
    with pytest.raises(reg.SubjectValidationError):
        reg.record_official_name("BMP", sid, source_url=url, name_zh="丝芙兰")


@pytest.mark.parametrize("url", [
    "https://user:secret@official.example/brand",
    "https://official.example/brand?token=secret",
    "https://official.example/brand?API_KEY=secret",
    "https://official.example/brand?refresh_token=secret",
    "https://official.example/brand?client_secret=private-value",
    "https://official.example/brand?clientSecret=private-value",
    "https://official.example/brand?accessToken=private-value",
    "https://official.example/brand?privateKey=private-value",
    "https://official.example/brand?secret=private-value",
    "https://official.example/brand?private_key=private-value",
    "https://official.example/brand?AWS-ACCESS-KEY=private-value",
    "https://official.example/brand?redirect=https%3A%2F%2Flogin.example%2Fcb%3Faccess_token%3Dsynthetic",
    "https://official.example/brand?campaign=x;client_secret=synthetic",
    "https://official.example/brand?redirect=https%3A%2F%2Fuser%3Apassword%40login.example%2F",
    "https://official.example/brand?next=https%253A%252F%252Fuser%253Apw%2540login.example%252F",
    "https://official.example/brand#private-fragment",
])
def test_rejects_credential_bearing_source_url(reg, url):
    sid = _add(reg)
    with pytest.raises(reg.SubjectValidationError):
        reg.record_official_name("BMP", sid, source_url=url, name_zh="丝芙兰")
    assert reg.get_subject_by_id("BMP", sid)["name_zh"] == "Sephora"
    with reg._db_ready() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id=?",
            (reg.OFFICIAL_NAME_SOURCE_FEATURE_ID,),
        ).fetchone()[0]
    assert count == 0


def test_unversioned_registry_bootstraps_canonical_evidence_schema(reg):
    sid = _add(reg)
    with reg._db_ready() as connection:
        connection.execute("DROP TABLE app_evidence_records")

    out = reg.record_official_name(
        "BMP", sid, source_url="https://official.example/brand?campaign=spring",
        keywords=["official alias"],
    )
    assert out["after"]["keywords"] == ["official alias"]
    with reg._db_ready() as connection:
        columns = {
            row[1] for row in connection.execute(
                "PRAGMA table_info(app_evidence_records)"
            ).fetchall()
        }
        evidence = connection.execute(
            "SELECT * FROM app_evidence_records WHERE feature_id=?",
            (reg.OFFICIAL_NAME_SOURCE_FEATURE_ID,),
        ).fetchone()
    assert {"domain_id", "product_id", "integrity_digest"} <= columns
    assert evidence is not None


def test_versioned_registry_leaves_evidence_schema_to_migrator(reg):
    _add(reg)
    with reg._db_ready() as connection:
        connection.execute("DROP TABLE app_evidence_records")
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version (version) VALUES (17)")

    reg._ensure_legacy_evidence_schema()
    with reg._db_ready() as connection:
        evidence_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='app_evidence_records'"
        ).fetchone()
    assert evidence_exists is None


def test_cth_evidence_records_subject_scope(reg):
    row, _ = reg.add_subject({
        "domain_id": "CTH", "subject_type": "company",
        "name_en": "North Star Trading", "name_zh": "北辰商贸", "keywords": [],
    })
    out = reg.record_official_name(
        "CTH", row["subject_id"], source_url="https://official.example/company",
        name_en="North Star Trading Ltd",
    )
    evidence_id = int(out["source_provenance"]["evidence_ref"].rsplit(":", 1)[1])
    with reg._db_ready() as connection:
        evidence = connection.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)
        ).fetchone()
    assert evidence["subject_scope"] == row["subject_id"]
    assert json.loads(evidence["inputs_json"])["_lumenis_scope"]["subject_id"] == row["subject_id"]


def test_import_official_names_apply_needs_approval(reg, monkeypatch):
    from scripts import import_subject_registry_seed as seed
    from lumenis.system.security import permission
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False, raising=False)
    permission.reset_permission_gate()
    sid = _add(reg)
    rows = [{"domain_id": "BMP", "subject_id": sid, "name_zh": "丝芙兰", "source_url": "https://www.sephora.cn/"}]
    assert seed.import_official_names(rows)["mode"] == "dry_run"
    with pytest.raises(seed.SeedApprovalRequired):
        seed.import_official_names(rows, apply=True)
    with pytest.raises(seed.SeedIntegrityError):
        seed.import_official_names([{**rows[0], "source_url": ""}])


@pytest.mark.parametrize("invalid_second_row", [
    {"subject_id": "", "source_url": "https://official.example/"},
    {"subject_id": "missing-subject", "source_url": "https://official.example/"},
    {"subject_id": None, "source_url": "https://official.example/?clientSecret=synthetic"},
])
def test_official_name_batch_validates_all_rows_before_approval_or_writes(
        reg, monkeypatch, invalid_second_row):
    from scripts import import_subject_registry_seed as seed

    sid = _add(reg)
    approval_calls = []
    write_calls = []
    monkeypatch.setattr(seed, "require_apply_approval", lambda: approval_calls.append(True))
    monkeypatch.setattr(reg, "record_official_name", lambda *args, **kwargs: write_calls.append(args))
    rows = [
        {"domain_id": "BMP", "subject_id": sid, "name_zh": "丝芙兰", "source_url": "https://official.example/"},
        {"domain_id": "BMP", "subject_id": invalid_second_row["subject_id"], "name_zh": "Sephora",
         "source_url": invalid_second_row["source_url"]},
    ]

    with pytest.raises(seed.SeedIntegrityError, match="invalid official name row"):
        seed.import_official_names(rows, apply=True)

    assert approval_calls == []
    assert write_calls == []
    assert reg.get_subject_by_id("BMP", sid)["name_zh"] == "Sephora"


def test_official_name_apply_binds_permission_audit_to_signed_evidence(reg, monkeypatch):
    from scripts import import_subject_registry_seed as seed

    sid = _add(reg)
    approval = type("ApprovalReceipt", (), {
        "allowed": True,
        "audit_id": "permission-audit-123",
        "caller": seed.APPROVAL_CALLER,
    })()
    monkeypatch.setattr(seed, "require_apply_approval", lambda: approval)
    result = seed.import_official_names([{
        "domain_id": "BMP", "subject_id": sid, "name_zh": "丝芙兰",
        "source_url": "https://www.sephora.cn/",
    }], apply=True)

    evidence_ref = result["results"][0]["source_provenance"]["evidence_ref"]
    evidence_id = int(evidence_ref.rsplit(":", 1)[1])
    with reg._db_ready() as connection:
        row = connection.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)
        ).fetchone()
    inputs = json.loads(row["inputs_json"])
    assert inputs["permission_audit_id"] == "permission-audit-123"
    assert inputs["permission_caller"] == seed.APPROVAL_CALLER


def test_apply_denies_missing_permission_audit_receipt(reg, monkeypatch):
    from scripts import import_subject_registry_seed as seed

    sid = _add(reg)
    approval = type("ApprovalReceipt", (), {"allowed": True, "audit_id": None})()
    monkeypatch.setattr(seed, "require_apply_approval", lambda: approval)
    with pytest.raises(seed.SeedApprovalRequired, match="审计编号"):
        seed.import_official_names([{
            "domain_id": "BMP", "subject_id": sid, "name_zh": "丝芙兰",
            "source_url": "https://www.sephora.cn/",
        }], apply=True)
    assert reg.get_subject_by_id("BMP", sid)["name_zh"] == "Sephora"
