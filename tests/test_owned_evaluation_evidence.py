"""Hermetic C2 evaluator-packet capture through canonical signed Evidence."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
import sqlite3
import uuid

import pytest

from lumenis.shared.database import get_repository
from lumenis.shared.evidence import store
from lumenis.shared.reporting.source_brief_job import _scope_material
from lumenis.system.ai_gateway import owned_evaluation as evaluation
from lumenis.system.security import permission


@pytest.fixture(autouse=True)
def strict_permission(monkeypatch):
    previous = permission._TESTING_BYPASS_ENABLED
    permission.set_testing_bypass(False)
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    permission.reset_permission_gate()
    yield
    permission.reset_permission_gate()
    permission.set_testing_bypass(previous)


@pytest.fixture
def capture_db(tmp_path, monkeypatch):
    baseline_db = os.environ.get("ZBC_DB_PATH", "")
    path = tmp_path / "owned-evaluation-capture.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"owned-evaluation-test": "ephemeral-owned-evaluation-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "owned-evaluation-test")
    import subject_registry

    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE v4_users (
                id INTEGER PRIMARY KEY, role TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE v4_member_authorizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                module TEXT NOT NULL,
                action TEXT NOT NULL,
                data_scope TEXT,
                time_range TEXT,
                granted_by INTEGER,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(user_id, product_id, module, action, data_scope)
            );
            INSERT INTO v4_users VALUES (1, 'owner', 'active');
        """)
        subject_registry.ensure_schema(connection)
        connection.executemany("""
            INSERT INTO lumenis_subject_registry (
                subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh,
                name_en_norm, name_zh_norm, industry, keywords_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ("SUBJ-EVAL-A", None, "CTH", "company", "Eval A", "评估 A", "eval a", "评估 a",
             "retail", "[]", "configured", "2026-10-08", "2026-10-08"),
            ("SUBJ-EVAL-B", None, "CTH", "company", "Eval B", "评估 B", "eval b", "评估 b",
             "retail", "[]", "configured", "2026-10-08", "2026-10-08"),
        ])
        store.ensure_evidence_schema(connection)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(app_evidence_records)")}
        for name, kind, default in store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if name not in columns:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                connection.execute(f"ALTER TABLE app_evidence_records ADD COLUMN {name} {kind}{suffix}")
    with sqlite3.connect(path) as connection:
        connection.execute("""
            INSERT INTO v4_member_authorizations (user_id, product_id, module, action, data_scope)
            VALUES (1, 'CTH', 'owned_model_admission', 'write', ?)
        """, (json.dumps({"subject_ids": ["SUBJ-EVAL-A", "SUBJ-EVAL-B"]}),))

    get_repository(force_reload=True)
    yield path
    if baseline_db:
        monkeypatch.setenv("ZBC_DB_PATH", baseline_db)
    else:
        monkeypatch.delenv("ZBC_DB_PATH", raising=False)
    get_repository(force_reload=True)


def _scope(subject_id="SUBJ-EVAL-A"):
    return _scope_material(
        product_id="CTH", global_scope=False, entity_label="Registered subject",
        subject_id=subject_id, brand_focus_id=None,
    )


def _packet(*, scope="SUBJ-EVAL-A", completion="COMPLETED_FINAL"):
    identity = {
        "status": "TRAINED_NOT_EVALUATED",
        "model_id": "lumenis-owned-test-model-模型",
        "model_revision": "测试-revision",
        "training_recipe": "approved-test-recipe",
        "base_revision_state": "verified",
        "manifest_sha256": "a" * 64,
        "train_sha256": "b" * 64,
        "heldout_sha256": "c" * 64,
        "train_case_count": 3,
        "heldout_case_count": 1,
        "scopes": [scope],
        "domain_id": "cth",
        "execution_state": "TRAINED_NOT_EVALUATED",
        "candidate_status": "NOT_EVALUATED",
        "training_status_sha256": "d" * 64,
        "adapter_sha256": "e" * 64,
        "adapter_config_sha256": "f" * 64,
    }
    identity_sha = hashlib.sha256(json.dumps(
        identity, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()
    completed = completion == "COMPLETED_FINAL"
    case = {
        "case_id": "case-eval-1",
        "domain_id": "cth",
        "scope": scope,
        "source_evidence_refs": ["app_evidence_records:17"],
        "heldout_origin": {
            "dataset_role": "heldout", "dataset_sha256": "c" * 64,
            "record_sha256": "1" * 64,
        },
        "prompt_sha256": "2" * 64,
        "completion_state": completion,
        "final_text": "评估结果 [[app_evidence_records:17]]." if completed else "",
        "raw_output_sha256": "3" * 64 if completed else "",
        "citation_state": "PRESENT" if completed else "MISSING",
        "termination_token": "<|return|>" if completed else "",
        "cited_source_refs": ["app_evidence_records:17"] if completed else [],
        "unresolved_citation_refs": [],
        "business_review": {
            "state": "HUMAN_REVIEW_REQUIRED",
            "criteria": {key: "PENDING" for key, _ in evaluation.BUSINESS_REVIEW_RUBRIC},
        },
    }
    return {
        "evaluation_status": "STRUCTURAL_OUTPUTS_CAPTURED" if completed else "INCOMPLETE_OUTPUTS_RECORDED",
        "candidate_status": "NOT_ACCEPTED",
        "business_acceptance": "HUMAN_REVIEW_REQUIRED",
        "runtime_verification": "CALLER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED",
        "generation_config": {
            "max_new_tokens": 128,
            "accepted_termination_tokens": sorted({"<|return|>", "<|fim_suffix|>"}),
        },
        "promotion_status": "NOT_PROMOTED",
        "candidate_identity": identity,
        "candidate_identity_sha256": identity_sha,
        "heldout_case_count": 1,
        "completed_final_count": 1 if completed else 0,
        "business_review_rubric": [
            {"criterion": key, "question": question}
            for key, question in evaluation.BUSINESS_REVIEW_RUBRIC
        ],
        "cases": [case],
    }


def _authorized_capture(path, packet, *, submission_id=None, scope=None):
    actor = {"id": 1}
    expected_scope = scope or _scope()
    submission = submission_id or str(uuid.uuid4())
    gate = permission.get_permission_gate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    resource = evaluation.owned_evaluation_capture_approval_resource(
        authenticated_actor=actor,
        expected_scope=expected_scope,
        submission_id=submission,
        evaluation_packet=packet,
    )
    token = gate.grant_approval(
        permission.OperationType.DB_WRITE.value,
        resource=resource,
        granted_by="isolated-test-reviewer",
    )
    return actor, expected_scope, submission, gate, resource, token


def _evidence_rows(path):
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM app_evidence_records WHERE feature_id=?",
            ("OWNED_MODEL_EVALUATION_PACKET",),
        ).fetchall()
        return [dict(row) for row in rows]


def test_records_exact_scoped_packet_with_signed_readback_and_idempotent_reopen(capture_db):
    packet = _packet()
    actor, scope, submission, _gate, _resource, _token = _authorized_capture(capture_db, packet)

    first = evaluation.record_owned_evaluation_evidence(
        authenticated_actor=actor, expected_scope=scope, submission_id=submission,
        evaluation_packet=packet,
    )
    second = evaluation.record_owned_evaluation_evidence(
        authenticated_actor=actor, expected_scope=scope, submission_id=submission,
        evaluation_packet=packet,
    )

    assert first["state"] == "recorded"
    assert second["state"] == "already_recorded"
    assert first["evaluation_ref"] == second["evaluation_ref"]
    assert first["content_sha256"] == hashlib.sha256(
        json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    assert first["content_sha256"] != hashlib.sha256(
        json.dumps(packet, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    assert packet["candidate_identity_sha256"] == hashlib.sha256(json.dumps(
        packet["candidate_identity"], ensure_ascii=True, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
    assert packet["candidate_identity_sha256"] != hashlib.sha256(json.dumps(
        packet["candidate_identity"], ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
    assert first["integrity_verified"] is True
    assert first["candidate_status"] == "NOT_ACCEPTED"
    assert first["business_acceptance"] == "HUMAN_REVIEW_REQUIRED"
    assert first["promotion_status"] == "NOT_PROMOTED"
    rows = _evidence_rows(capture_db)
    assert len(rows) == 1
    row = rows[0]
    assert (row["result"], row["status"], row["domain_id"], row["product_id"]) == (
        "RECORDED", "derived", "cth", "CTH",
    )
    assert store.verify_evidence_record_integrity(row) is True
    assert json.loads(row["outputs_json"])["evaluation_packet"] == packet


def test_incomplete_evaluator_output_is_recorded_without_quality_promotion(capture_db):
    packet = _packet(completion="INFERENCE_ERROR:RuntimeError")
    actor, scope, submission, _gate, _resource, _token = _authorized_capture(capture_db, packet)

    result = evaluation.record_owned_evaluation_evidence(
        authenticated_actor=actor, expected_scope=scope, submission_id=submission,
        evaluation_packet=packet,
    )

    assert result["state"] == "recorded"
    assert result["evidence_result"] == "RECORDED"
    assert result["candidate_status"] == "NOT_ACCEPTED"
    assert result["business_acceptance"] == "HUMAN_REVIEW_REQUIRED"
    assert result["promotion_status"] == "NOT_PROMOTED"


def test_denied_exact_write_approval_has_no_evidence_effect(capture_db):
    packet = _packet()
    gate = permission.get_permission_gate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)

    with pytest.raises(PermissionError, match="EXACT_DB_WRITE_APPROVAL_REQUIRED"):
        evaluation.record_owned_evaluation_evidence(
            authenticated_actor={"id": 1}, expected_scope=_scope(),
            submission_id=str(uuid.uuid4()), evaluation_packet=packet,
        )

    assert _evidence_rows(capture_db) == []


@pytest.mark.parametrize("invalid_packet", [None, {"evaluation_status": "PASS"}])
def test_null_or_arbitrary_packet_is_rejected_without_evidence(capture_db, invalid_packet):
    gate = permission.get_permission_gate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)

    with pytest.raises(ValueError):
        evaluation.record_owned_evaluation_evidence(
            authenticated_actor={"id": 1}, expected_scope=_scope(),
            submission_id=str(uuid.uuid4()), evaluation_packet=invalid_packet,
        )

    assert _evidence_rows(capture_db) == []


def test_mixed_scope_and_contradictory_positive_or_candidate_status_are_denied(capture_db):
    mixed = _packet()
    extra = json.loads(json.dumps(mixed["cases"][0]))
    extra["case_id"] = "case-eval-2"
    extra["scope"] = "SUBJ-EVAL-B"
    mixed["cases"].append(extra)
    mixed["heldout_case_count"] = 2
    mixed["candidate_identity"]["heldout_case_count"] = 2
    mixed["candidate_identity_sha256"] = hashlib.sha256(json.dumps(
        mixed["candidate_identity"], sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
    positive = _packet()
    positive["business_acceptance"] = "ACCEPTED"
    contradictory = _packet()
    contradictory["candidate_identity"]["candidate_status"] = "ACCEPTED"
    contradictory["candidate_identity_sha256"] = hashlib.sha256(json.dumps(
        contradictory["candidate_identity"], sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()

    for invalid in (mixed, positive, contradictory):
        with pytest.raises(ValueError):
            evaluation.owned_evaluation_capture_approval_resource(
                authenticated_actor={"id": 1}, expected_scope=_scope(),
                submission_id=str(uuid.uuid4()), evaluation_packet=invalid,
            )
    assert _evidence_rows(capture_db) == []


def test_expired_approval_denies_before_write(capture_db):
    packet = _packet()
    actor, scope, submission = {"id": 1}, _scope(), str(uuid.uuid4())
    gate = permission.get_permission_gate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    resource = evaluation.owned_evaluation_capture_approval_resource(
        authenticated_actor=actor, expected_scope=scope, submission_id=submission,
        evaluation_packet=packet,
    )
    expired_token = gate.grant_approval(
        permission.OperationType.DB_WRITE.value, duration_minutes=-1,
        resource=resource, granted_by="isolated-test-reviewer",
    )

    with pytest.raises(PermissionError, match="EXACT_DB_WRITE_APPROVAL_REQUIRED"):
        evaluation.record_owned_evaluation_evidence(
            authenticated_actor=actor, expected_scope=scope, submission_id=submission,
            evaluation_packet=packet,
        )
    assert gate.get_valid_approval_token(
        permission.OperationType.DB_WRITE.value, resource, exact=True,
    ) is None
    assert expired_token
    assert _evidence_rows(capture_db) == []


def test_scope_or_caller_mismatch_cannot_reuse_an_exact_capture_grant(capture_db):
    packet = _packet()
    actor, scope, submission, _gate, _resource, _token = _authorized_capture(capture_db, packet)

    with pytest.raises(ValueError, match="SCOPE_MISMATCH"):
        evaluation.owned_evaluation_capture_approval_resource(
            authenticated_actor=actor, expected_scope=_scope("SUBJ-EVAL-B"),
            submission_id=submission, evaluation_packet=packet,
        )
    with pytest.raises(PermissionError):
        evaluation.record_owned_evaluation_evidence(
            authenticated_actor={"id": 2}, expected_scope=scope,
            submission_id=submission, evaluation_packet=packet,
        )
    assert _evidence_rows(capture_db) == []


def test_revoked_approval_after_insert_rolls_back_evidence(capture_db, monkeypatch):
    packet = _packet()
    actor, scope, submission, gate, _resource, token = _authorized_capture(capture_db, packet)
    original = store.record_evidence

    def write_then_revoke(**kwargs):
        row_id = original(**kwargs)
        assert gate.revoke_approval(token) is True
        return row_id

    monkeypatch.setattr(store, "record_evidence", write_then_revoke)
    with pytest.raises(PermissionError, match="EXACT_DB_WRITE_APPROVAL_REQUIRED"):
        evaluation.record_owned_evaluation_evidence(
            authenticated_actor=actor, expected_scope=scope, submission_id=submission,
            evaluation_packet=packet,
        )
    assert _evidence_rows(capture_db) == []


def test_revocation_at_transaction_commit_boundary_cannot_leave_evidence(capture_db, monkeypatch):
    """Expose a revoke after the final Permission recheck, before repository commit."""
    packet = _packet()
    actor, scope, submission, gate, _resource, token = _authorized_capture(capture_db, packet)
    repository = get_repository()
    original_transaction = repository.transaction
    revocations = []

    @contextmanager
    def revoke_before_commit(**kwargs):
        with original_transaction(**kwargs) as connection:
            yield connection
            # The producer has left its transaction body and completed its final
            # _authorize call. The underlying repository context commits next.
            revocations.append(gate.revoke_approval(token))

    monkeypatch.setattr(repository, "transaction", revoke_before_commit)
    result = evaluation.record_owned_evaluation_evidence(
        authenticated_actor=actor, expected_scope=scope, submission_id=submission,
        evaluation_packet=packet,
    )

    assert revocations == [True]
    assert result["evaluation_ref"]
    assert gate.get_valid_approval_token(
        permission.OperationType.DB_WRITE.value,
        _resource,
        exact=True,
    ) is None
    assert _evidence_rows(capture_db) == []


def test_tampered_hmac_row_after_insert_rolls_back_evidence(capture_db, monkeypatch):
    packet = _packet()
    actor, scope, submission, _gate, _resource, _token = _authorized_capture(capture_db, packet)
    original = store.record_evidence

    def write_then_tamper(**kwargs):
        row_id = original(**kwargs)
        kwargs["connection"].execute(
            "UPDATE app_evidence_records SET outputs_json=? WHERE id=?",
            (json.dumps({"evaluation_packet": {"tampered": True}}), row_id),
        )
        return row_id

    monkeypatch.setattr(store, "record_evidence", write_then_tamper)
    with pytest.raises(RuntimeError, match="INTEGRITY_FAILED|BINDING_INVALID"):
        evaluation.record_owned_evaluation_evidence(
            authenticated_actor=actor, expected_scope=scope, submission_id=submission,
            evaluation_packet=packet,
        )
    assert _evidence_rows(capture_db) == []
