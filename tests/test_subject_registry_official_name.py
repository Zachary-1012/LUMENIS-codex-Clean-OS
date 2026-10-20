"""record_official_name stores only official names with official-site evidence."""
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
    assert outputs["source_url"] == source_url
    assert outputs["authenticity_score_state"] == "NOT_ASSESSED"
    assert outputs["url_scheme_is_identity_proof"] is False
    assert outputs["network_fetch"] == "NOT_PERFORMED"
    assert evidence["domain_id"] == "zbmp" and evidence["product_id"] == "ZBMP"
    assert evidence["status"] == "pending" and evidence["result"] == "GAP"
    assert evidence["authenticity_score"] == 0.0
    assert verify_evidence_record_integrity(evidence) is True

    again = reg.record_official_name("BMP", sid, source_url=source_url, name_zh="丝芙兰")
    assert again["changed"] is False


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
