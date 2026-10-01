"""Isolated tests for signed, read-only owned-training case export."""
from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from lumenis.shared.evidence import store
from lumenis.shared.learning.training_cases import export_reviewed_training_records
from lumenis.shared.reporting.source_brief_job import _scope_material
from lumenis.system.ai_gateway import owned_training
from lumenis.system.security import permission

ACTOR = "workspace:reviewer"


@pytest.fixture
def evidence_db(tmp_path, monkeypatch):
    path = tmp_path / "owned-training-cases.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({"test-key": "temporary-owned-training-test-key"}))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "test-key")
    with sqlite3.connect(path) as connection:
        store.ensure_evidence_schema(connection)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(app_evidence_records)")}
        for name, kind, default in store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if name not in columns:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                connection.execute(f"ALTER TABLE app_evidence_records ADD COLUMN {name} {kind}{suffix}")
    return path


def _scope(*, domain="cth", global_scope=False, focus="SUBJECT-A"):
    bmp = domain in {"bmp", "zbmp"}
    return _scope_material(
        product_id="ZBMP" if bmp else "CTH", global_scope=global_scope,
        entity_label="Global coverage" if global_scope else "Registered focus",
        subject_id=None if global_scope or bmp else focus,
        brand_focus_id=None if global_scope or not bmp else focus,
    )


def _insert(connection, scope, *, source, feature, result, status, inputs, outputs,
            capture_mode="automated", case_id="source"):
    row_id = store.record_evidence(
        connection=connection, source=source, project="LUMENIS", product=scope["product_id"],
        feature_id=feature, asset_id=case_id, test_name=case_id, version="test:v1",
        capture_mode=capture_mode, result=result, status=status, inputs=inputs, outputs=outputs,
        domain_id=scope["domain_id"], subject_id=scope["subject_id"],
        brand_focus_id=scope["brand_focus_id"], global_scope=scope["global"],
    )
    assert type(row_id) is int and row_id > 0
    return f"app_evidence_records:{row_id}"


def _case(connection, scope, *, case_id="case-001", prompt="How should this be handled?",
          actor=ACTOR, source_scope=None, source_result="PASS", source_status="verified",
          rights_result="APPROVED", rights_status="derived", rights_disposition="permitted",
          rights_purpose="model_training", review_feature="OWNED_TRAINING_TARGET_REVIEW",
          review_result="APPROVED", review_status="derived", review_capture="reviewer_submission",
          target_review_status="REVIEWER_APPROVED", source_missing=False):
    source_scope = source_scope or scope
    if source_missing:
        source_ref = "app_evidence_records:999999"
    else:
        source_ref = _insert(
            connection, source_scope, source="public_http", feature="SOURCE_TEST",
            result=source_result, status=source_status, inputs={"source_id": "source-001"},
            outputs={"observed": True}, case_id=case_id,
        )
    source_refs = [source_ref]
    rights_ref = _insert(
        connection, scope, source="shared_learning", feature="OWNED_TRAINING_RIGHTS_APPROVAL",
        result=rights_result, status=rights_status,
        inputs={"actor_id": actor, "scope": scope, "source_evidence_refs": source_refs},
        outputs={"purpose": rights_purpose, "rights_disposition": rights_disposition},
        capture_mode="reviewer_submission", case_id=case_id,
    )
    review_ref = _insert(
        connection, scope, source="shared_learning", feature=review_feature,
        result=review_result, status=review_status,
        inputs={
            "actor_id": actor, "scope": scope, "source_evidence_refs": source_refs,
            "rights_evidence_ref": rights_ref,
            "permission_audit_ref": "permission-audit:review-001",
            "operation_audit_ref": "operation-audit:review-001", "case_id": case_id,
            "context": "Approved CTH decision task", "prompt_messages": [{"role": "user", "content": prompt}],
        },
        outputs={"review_status": target_review_status,
                 "reviewer_approved_target": "Use the verified source and report the result."},
        capture_mode=review_capture, case_id=case_id,
    )
    return review_ref, source_ref, rights_ref


def _authorize(scope, actor=ACTOR):
    calls = {"count": 0}

    def authorize():
        calls["count"] += 1
        return {
            "actor_id": actor, "scope": scope,
            "permission_audit_ref": f"permission-audit:export-{calls['count']}",
            "operation_audit_ref": f"operation-audit:export-{calls['count']}",
        }

    return authorize, calls


def _export(scope, review_refs, *, actor=ACTOR, authorize=None):
    callback = authorize or _authorize(scope, actor)[0]
    return export_reviewed_training_records(
        review_refs, actor_id=actor, expected_scope=scope, authorize=callback,
    )


def test_exports_signed_review_and_rights_as_permission_compatible_jsonl_record(evidence_db):
    scope = _scope()
    with sqlite3.connect(evidence_db) as connection:
        review_ref, source_ref, rights_ref = _case(connection, scope)
    before = hashlib.sha256(evidence_db.read_bytes()).hexdigest()

    records = _export(scope, [review_ref])

    assert len(records) == 1
    record = records[0]
    identity, normalized_prompt = owned_training._validate_record(record)
    assert record["scope"] == "SUBJECT-A"
    assert record["domain"] == "CTH"
    assert record["source_evidence_refs"] == [source_ref]
    assert record["rights_ref"] == rights_ref
    assert record["review_status"] == "REVIEWER_APPROVED" and record["training_eligible"] is True
    assert record["messages"][-1] == {
        "role": "assistant", "content": record["reviewer_approved_target"], "channel": "final",
    }
    assert normalized_prompt == "how should this be handled?"

    request = owned_training.TrainingApprovalRequest(
        model_id=owned_training.MODEL_ID, model_revision=owned_training.MODEL_REVISION,
        train_sha256="a" * 64, heldout_sha256="b" * 64,
        scopes=(record["scope"],), recipe=owned_training.H100_RECIPE,
        manifest_sha256="c" * 64, domain_id="cth",
    )
    descriptor = {
        "domain_id": "cth", "product_id": "CTH", "global_scope": False,
        "subject_id": "SUBJECT-A", "brand_focus_id": None,
    }
    resource = permission.owned_training_approval_resource(
        request, actor_id=17, domain_id="cth",
        context={"scope_descriptors": {record["scope"]: descriptor}},
    )
    assert resource.startswith("owned_training:v1:")
    assert hashlib.sha256(evidence_db.read_bytes()).hexdigest() == before


def test_global_scope_exports_exact_permission_scope_label(evidence_db):
    scope = _scope(global_scope=True)
    with sqlite3.connect(evidence_db) as connection:
        review_ref, _, _ = _case(connection, scope)
    record = _export(scope, [review_ref])[0]
    assert record["scope"] == "GLOBAL / ALL"
    request = owned_training.TrainingApprovalRequest(
        model_id=owned_training.MODEL_ID, model_revision=owned_training.MODEL_REVISION,
        train_sha256="a" * 64, heldout_sha256="b" * 64,
        scopes=(record["scope"],), recipe=owned_training.H100_RECIPE,
        manifest_sha256="c" * 64, domain_id="cth",
    )
    descriptor = {
        "domain_id": "cth", "product_id": "CTH", "global_scope": True,
        "subject_id": None, "brand_focus_id": None,
    }
    assert permission.owned_training_approval_resource(
        request, actor_id=17, domain_id="cth",
        context={"scope_descriptors": {record["scope"]: descriptor}},
    ).startswith("owned_training:v1:")


def test_bmp_export_uses_exact_brand_focus_permission_label(evidence_db):
    scope = _scope(domain="zbmp", focus="BRAND-A")
    with sqlite3.connect(evidence_db) as connection:
        review_ref, _, _ = _case(connection, scope)
    record = _export(scope, [review_ref])[0]
    assert record["scope"] == "BRAND-A" and record["domain"] == "BMP"
    request = owned_training.TrainingApprovalRequest(
        model_id=owned_training.MODEL_ID, model_revision=owned_training.MODEL_REVISION,
        train_sha256="a" * 64, heldout_sha256="b" * 64,
        scopes=(record["scope"],), recipe=owned_training.H100_RECIPE,
        manifest_sha256="c" * 64, domain_id="bmp",
    )
    descriptor = {
        "domain_id": "bmp", "product_id": "ZBMP", "global_scope": False,
        "subject_id": None, "brand_focus_id": "BRAND-A",
    }
    assert permission.owned_training_approval_resource(
        request, actor_id=17, domain_id="bmp",
        context={"scope_descriptors": {record["scope"]: descriptor}},
    ).startswith("owned_training:v1:")


def test_rejects_existing_report_learning_case_and_pending_review(evidence_db):
    scope = _scope()
    with sqlite3.connect(evidence_db) as connection:
        raw_ref, _, _ = _case(
            connection, scope, review_feature="REPORT_LEARNING_CASE", review_result="RECORDED",
            review_status="derived", review_capture="report_review", target_review_status="HUMAN_PENDING",
        )
        pending_ref, _, _ = _case(connection, scope, case_id="case-002", review_result="RECORDED",
                                  target_review_status="HUMAN_PENDING")
    for ref in (raw_ref, pending_ref):
        with pytest.raises((PermissionError, RuntimeError)):
            _export(scope, [ref])


@pytest.mark.parametrize(("result", "status"), [("FAIL", "verified"), ("PASS", "pending"), ("PASS", "unknown")])
def test_rejects_failed_or_pending_source_evidence(evidence_db, result, status):
    scope = _scope()
    with sqlite3.connect(evidence_db) as connection:
        ref, _, _ = _case(connection, scope, source_result=result, source_status=status)
    with pytest.raises(PermissionError, match="SOURCE_NOT_SUCCESSFULLY_VERIFIED"):
        _export(scope, [ref])


@pytest.mark.parametrize(("purpose", "disposition"), [
    ("model_training", "UNKNOWN"), ("evaluation", "permitted"), ("model_training", "denied"),
])
def test_rejects_unknown_unbound_or_denied_rights(evidence_db, purpose, disposition):
    scope = _scope()
    with sqlite3.connect(evidence_db) as connection:
        ref, _, _ = _case(connection, scope, rights_purpose=purpose, rights_disposition=disposition)
    with pytest.raises(PermissionError, match="RIGHTS_NOT_PERMITTED"):
        _export(scope, [ref])


def test_rejects_missing_source_actor_mismatch_and_mixed_scope(evidence_db):
    scope = _scope()
    other_scope = _scope(domain="bmp", focus="BRAND-A")
    with sqlite3.connect(evidence_db) as connection:
        missing_ref, _, _ = _case(connection, scope, source_missing=True)
        wrong_actor_ref, _, _ = _case(connection, scope, case_id="case-002", actor="workspace:other")
        mixed_ref, _, _ = _case(connection, scope, case_id="case-003", source_scope=other_scope)
    with pytest.raises(LookupError, match="EVIDENCE_NOT_FOUND"):
        _export(scope, [missing_ref])
    with pytest.raises(PermissionError, match="ACTOR_OR_SCHEMA"):
        _export(scope, [wrong_actor_ref])
    with pytest.raises(PermissionError, match="SOURCE_SCOPE_MISMATCH"):
        _export(scope, [mixed_ref])


@pytest.mark.parametrize("tamper", ["review", "source"])
def test_rejects_tampered_hmac_signed_evidence(evidence_db, tamper):
    scope = _scope()
    with sqlite3.connect(evidence_db) as connection:
        review_ref, source_ref, _ = _case(connection, scope)
    ref = review_ref if tamper == "review" else source_ref
    row_id = int(ref.split(":")[1])
    with sqlite3.connect(evidence_db) as connection:
        connection.execute("UPDATE app_evidence_records SET result='TAMPERED' WHERE id=?", (row_id,))
    with pytest.raises(RuntimeError, match="SIGNATURE_INVALID"):
        _export(scope, [review_ref])


@pytest.mark.parametrize(("same_case", "same_prompt"), [(True, False), (False, True)])
def test_rejects_duplicate_cases_and_nfkc_normalized_prompts(evidence_db, same_case, same_prompt):
    scope = _scope()
    with sqlite3.connect(evidence_db) as connection:
        first, _, _ = _case(connection, scope, case_id="same-case" if same_case else "case-001", prompt="ＡPPLE")
        second, _, _ = _case(connection, scope, case_id="same-case" if same_case else "case-002",
                             prompt="apple" if same_prompt else "another question")
    error = "DUPLICATE_CASE" if same_case else "DUPLICATE_PROMPT"
    with pytest.raises(ValueError, match=error):
        _export(scope, [first, second])


def test_rechecks_authorization_and_fails_on_revocation_before_return(evidence_db):
    scope = _scope()
    with sqlite3.connect(evidence_db) as connection:
        review_ref, _, _ = _case(connection, scope)
    calls = {"count": 0}

    def revoked():
        calls["count"] += 1
        if calls["count"] == 2:
            raise PermissionError("revoked")
        return {
            "actor_id": ACTOR, "scope": scope,
            "permission_audit_ref": "permission-audit:entry",
            "operation_audit_ref": "operation-audit:entry",
        }

    with pytest.raises(PermissionError):
        _export(scope, [review_ref], authorize=revoked)
    assert calls["count"] == 2


def test_rejects_unknown_scope_before_permission_or_data_read(evidence_db):
    scope = _scope()
    unknown = dict(scope, domain_id="unknown")
    called = {"value": False}

    def authorize():
        called["value"] = True
        return {}

    with pytest.raises(ValueError, match="SCOPE_INVALID"):
        _export(unknown, ["app_evidence_records:1"], authorize=authorize)
    assert called["value"] is False
