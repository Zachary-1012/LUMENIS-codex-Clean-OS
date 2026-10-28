"""Exact SYSTEM Permission authorization for owned-model training."""
from dataclasses import replace
from datetime import datetime, timedelta
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from lumenis.system.security import permission as p
from lumenis.system.ai_gateway import owned_training as training


@pytest.fixture(autouse=True)
def _strict_permission(monkeypatch):
    previous = p._TESTING_BYPASS_ENABLED
    p.set_testing_bypass(False)
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    yield
    p.set_testing_bypass(previous)


@pytest.fixture
def scope_db(tmp_path, monkeypatch):
    path = tmp_path / "owned-training-permission.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE v4_users (
                id INTEGER PRIMARY KEY, role TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE v4_member_authorizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL, module TEXT NOT NULL, action TEXT NOT NULL,
                data_scope TEXT, time_range TEXT, granted_by INTEGER, created_at TEXT,
                updated_at TEXT, UNIQUE(user_id, product_id, module, action)
            );
            INSERT INTO v4_users (id, role, status) VALUES
                (1, 'user', 'active'), (2, 'user', 'active');
        """)
        import subject_registry
        subject_registry.ensure_schema(conn)
        conn.execute("""
            INSERT INTO lumenis_subject_registry (
                subject_id, brand_focus_id, domain_id, subject_type,
                name_en, name_zh, name_en_norm, name_zh_norm, industry,
                keywords_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "SUBJ-CTH-A", None, "CTH", "company", "North Center", "北区中心",
            "north center", "北区中心", "retail", "[]", "configured",
            "2026-09-24", "2026-09-24",
        ))
        conn.execute("""
            INSERT INTO lumenis_subject_registry (
                subject_id, brand_focus_id, domain_id, subject_type,
                name_en, name_zh, name_en_norm, name_zh_norm, industry,
                keywords_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "SUBJ-BMP-A", "BRAND-BMP-A", "BMP", "brand", "North Brand", "北方品牌",
            "north brand", "北方品牌", "beauty", "[]", "configured",
            "2026-09-24", "2026-09-24",
        ))
    return path


def _grant(path, actor_id, product_id, data_scope):
    with sqlite3.connect(path) as conn:
        conn.execute("""
            INSERT INTO v4_member_authorizations (
                user_id, product_id, module, action, data_scope, time_range
            ) VALUES (?, ?, 'owned_training', 'write', ?, NULL)
        """, (actor_id, product_id, json.dumps(data_scope)))


def _request(**changes):
    values = {
        "model_id": "openai/gpt-oss-20b",
        "model_revision": "6cee5e81ee83917806bbde320786a8fb61efebee",
        "train_sha256": "1" * 64,
        "heldout_sha256": "2" * 64,
        "domain_id": "cth",
        "scopes": ("GLOBAL / ALL",),
        "recipe": "openai-h100-bf16",
        "manifest_sha256": "3" * 64,
    }
    values.update(changes)
    return training.TrainingApprovalRequest(**values)


def _context(scope="GLOBAL / ALL", *, domain="cth", global_scope=True):
    product_id = "CTH" if domain == "cth" else "ZBMP"
    return {"scope_descriptors": {scope: {
        "domain_id": domain, "product_id": product_id,
        "global_scope": global_scope,
        "subject_id": None if global_scope or domain == "bmp" else scope,
        "brand_focus_id": scope if domain == "bmp" and not global_scope else None,
    }}}


def _gate():
    return p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT})


def _authorize(gate, request, *, actor_id=1, domain_id="cth", context=None):
    context = context or _context()
    resource = p.owned_training_approval_resource(
        request, actor_id=actor_id, domain_id=domain_id, context=context,
    )
    token = gate.grant_approval(
        p.OperationType.MODEL_TRAIN.value, resource=resource, granted_by="test-human",
    )
    verifier = p.make_owned_training_approval_verifier(
        gate, actor_id=actor_id, domain_id=domain_id, context=context,
    )
    return verifier, token, resource


def test_exact_training_approval_passes_and_binds_full_resource(scope_db):
    _grant(scope_db, 1, "CTH", {"global": True})
    gate, request = _gate(), _request()
    verifier, _, resource = _authorize(gate, request)

    assert resource.startswith("owned_training:v1:")
    assert verifier(request) is True
    audit = gate.get_audit_log(operation_type="model_train", result_filter="allowed")[-1]
    assert audit["resource"] == resource
    assert audit["caller"] == "actor:1"
    assert audit["permission_required"] == "commit"
    spec = gate._registry[p.OperationType.MODEL_TRAIN]
    assert spec.permission is p.PermissionLevel.COMMIT
    assert spec.risk is p.RiskLevel.HIGH
    assert spec.auto_allow is False


def test_unapproved_training_and_other_operation_approval_are_denied(scope_db):
    _grant(scope_db, 1, "CTH", {"global": True})
    gate, request = _gate(), _request()
    verifier = p.make_owned_training_approval_verifier(
        gate, actor_id=1, domain_id="cth", context=_context(),
    )
    assert verifier(request) is False
    resource = p.owned_training_approval_resource(
        request, actor_id=1, domain_id="cth", context=_context(),
    )
    gate.grant_approval(p.OperationType.AI_CALL.value, resource=resource)
    gate.grant_approval(p.OperationType.REPORT_REVIEW.value, resource=resource)
    assert verifier(request) is False


def test_exact_approval_cannot_be_reused_by_another_actor(scope_db):
    _grant(scope_db, 1, "CTH", {"global": True})
    _grant(scope_db, 2, "CTH", {"global": True})
    gate, request = _gate(), _request()
    _, _, _ = _authorize(gate, request, actor_id=1)
    other_actor = p.make_owned_training_approval_verifier(
        gate, actor_id=2, domain_id="cth", context=_context(),
    )
    assert other_actor(request) is False


def test_cth_approval_rejects_bmp_request_with_same_global_label(scope_db):
    _grant(scope_db, 1, "CTH", {"global": True})
    gate, request = _gate(), _request(domain_id="cth")
    verifier, _, resource = _authorize(gate, request, domain_id="cth")

    bmp_request = replace(request, domain_id="bmp")
    assert p.owned_training_approval_resource(
        bmp_request, actor_id=1, domain_id="bmp", context=_context(domain="bmp"),
    ) != resource
    assert verifier(bmp_request) is False


def test_scope_tuple_change_requires_new_exact_approval(scope_db):
    _grant(scope_db, 1, "CTH", {"global": True})
    gate, request = _gate(), _request()
    _, _, original_resource = _authorize(gate, request)
    changed = replace(request, scopes=("GLOBAL / ALL", "SUBJ-CTH-A"))
    changed_context = {"scope_descriptors": {
        "GLOBAL / ALL": _context()["scope_descriptors"]["GLOBAL / ALL"],
        "SUBJ-CTH-A": _context("SUBJ-CTH-A", global_scope=False)[
            "scope_descriptors"]["SUBJ-CTH-A"],
    }}
    verifier = p.make_owned_training_approval_verifier(
        gate, actor_id=1, domain_id="cth", context=changed_context,
    )

    assert p.owned_training_approval_resource(
        changed, actor_id=1, domain_id="cth", context=changed_context,
    ) != original_resource
    assert verifier(changed) is False


@pytest.mark.parametrize("change", [
    {"train_sha256": "4" * 64}, {"heldout_sha256": "5" * 64},
    {"model_id": "unsloth/gpt-oss-20b-unsloth-bnb-4bit"},
    {"model_revision": "different-revision"}, {"recipe": "unsloth-t4-nf4"},
    {"manifest_sha256": "6" * 64},
])
def test_approval_is_bound_to_exact_model_recipe_and_dataset_hashes(scope_db, change):
    _grant(scope_db, 1, "CTH", {"global": True})
    gate, request = _gate(), _request()
    verifier, _, original_resource = _authorize(gate, request)
    changed = replace(request, **change)

    assert p.owned_training_approval_resource(
        changed, actor_id=1, domain_id="cth", context=_context(),
    ) != original_resource
    assert verifier(changed) is False


@pytest.mark.parametrize("state", ["revoked", "expired"])
def test_verifier_rechecks_live_approval_state(scope_db, state):
    _grant(scope_db, 1, "CTH", {"global": True})
    gate, request = _gate(), _request()
    verifier, token, _ = _authorize(gate, request)
    assert verifier(request) is True
    if state == "revoked":
        assert gate.revoke_approval(token) is True
    else:
        gate._approvals[token].expires_at = datetime.now() - timedelta(seconds=1)
    assert verifier(request) is False


def test_verifier_rechecks_live_scope_grant_and_unknown_registered_scope(scope_db):
    _grant(scope_db, 1, "CTH", {"subject_ids": ["SUBJ-CTH-A"]})
    gate = _gate()
    request = _request(scopes=("SUBJ-CTH-A",))
    context = _context("SUBJ-CTH-A", global_scope=False)
    verifier, _, _ = _authorize(
        gate, request, domain_id="cth", context=context,
    )
    assert verifier(request) is True
    unknown_request = _request(scopes=("SUBJ-CTH-MISSING",))
    unknown_context = _context("SUBJ-CTH-MISSING", global_scope=False)
    unknown_verifier, _, _ = _authorize(
        gate, unknown_request, domain_id="cth", context=unknown_context,
    )
    assert unknown_verifier(unknown_request) is False
    with sqlite3.connect(scope_db) as conn:
        conn.execute("DELETE FROM v4_member_authorizations WHERE user_id = 1")
    assert verifier(request) is False


def test_bmp_descriptor_uses_registered_brand_focus_id(scope_db):
    _grant(scope_db, 1, "ZBMP", {"brand_focus_ids": ["BRAND-BMP-A"]})
    gate = _gate()
    request = _request(domain_id="bmp", scopes=("BRAND-BMP-A",))
    context = _context("BRAND-BMP-A", domain="bmp", global_scope=False)
    verifier, _, _ = _authorize(
        gate, request, domain_id="bmp", context=context,
    )

    assert verifier(request) is True
    invalid = _context("BRAND-BMP-MISSING", domain="bmp", global_scope=False)
    invalid_request = _request(domain_id="bmp", scopes=("BRAND-BMP-MISSING",))
    invalid_verifier, _, _ = _authorize(
        gate, invalid_request, domain_id="bmp", context=invalid,
    )
    assert invalid_verifier(invalid_request) is False


def test_unknown_or_inexact_scope_context_fails_closed():
    request = _request()
    with pytest.raises(ValueError, match="every training scope"):
        p.owned_training_approval_resource(
            request, actor_id=1, domain_id="cth",
            context={"scope_descriptors": {}},
        )
    with pytest.raises(ValueError, match="CTH training scope"):
        p.owned_training_approval_resource(
            request, actor_id=1, domain_id="cth",
            context={"scope_descriptors": {"GLOBAL / ALL": {
                "domain_id": "cth", "product_id": "CTH", "global_scope": False,
                "subject_id": "SUBJ-CTH-A", "brand_focus_id": None,
            }}},
        )
    with pytest.raises(ValueError, match="CTH or BMP"):
        p.make_owned_training_approval_verifier(
            _gate(), actor_id=1, domain_id="unknown", context=_context(),
        )


def _approved_training_inputs(root: Path):
    model = root / "snapshot"
    model.mkdir(parents=True)
    entries = {}
    for name in training._MODEL_FILES:
        raw = ("isolated-training-fixture:" + name).encode()
        (model / name).write_bytes(raw)
        entries[name] = {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    manifest = root / "config" / "ai-owned-foundation.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({
        "schema_version": 1, "owner": "SYSTEM AI Gateway",
        "model_id": training.MODEL_ID, "revision": training.MODEL_REVISION,
        "license": "Apache-2.0", "usage_policy_url": "https://huggingface.co/openai/gpt-oss-20b/blob/6cee5e81ee83917806bbde320786a8fb61efebee/USAGE_POLICY",
        "capability": "text", "format": "transformers_safetensors",
        "status": "APPROVED_FOUNDATION_NOT_TRAINED",
        "source_url": "https://huggingface.co/openai/gpt-oss-20b/tree/6cee5e81ee83917806bbde320786a8fb61efebee",
        "fine_tune_reference": "https://developers.openai.com/cookbook/articles/gpt-oss/fine-tune-transfomers",
        "files": entries,
    }), encoding="utf-8")
    row = {
        "case_id": "TRAIN-1", "source_evidence_refs": ["EVIDENCE-1"],
        "scope": "GLOBAL / ALL", "domain": "CTH", "context": "typed training test",
        "permission_ref": "PERMISSION-1", "rights_ref": "RIGHTS-1",
        "review_status": "REVIEWER_APPROVED", "reviewer_approval_ref": "REVIEW-1",
        "reviewer_approved_target": "Reviewed answer.", "training_eligible": True,
        "messages": [
            {"role": "user", "content": "Question."},
            {"role": "assistant", "content": "Reviewed answer.", "channel": "final"},
        ],
    }
    train, heldout = root / "train.jsonl", root / "heldout.jsonl"
    train.write_text(json.dumps(row) + "\n", encoding="utf-8")
    heldout.write_text(json.dumps({**row, "case_id": "HELDOUT-1",
                                   "source_evidence_refs": ["EVIDENCE-2"],
                                   "permission_ref": "PERMISSION-2",
                                   "rights_ref": "RIGHTS-2",
                                   "reviewer_approval_ref": "REVIEW-2",
                                   "messages": [
                                       {"role": "user", "content": "Different question."},
                                       {"role": "assistant", "content": "Reviewed answer.", "channel": "final"},
                                   ]}) + "\n", encoding="utf-8")
    return model, manifest, train, heldout, root / "candidate-output"


def test_withdrawn_gpu_training_stops_before_permission_or_output(scope_db, tmp_path, monkeypatch):
    _grant(scope_db, 1, "CTH", {"global": True})
    gate = _gate()
    verifier = p.make_owned_training_approval_verifier(
        gate, actor_id=1, domain_id="cth", context=_context(),
    )
    model, manifest, train, heldout, output = _approved_training_inputs(tmp_path)
    monkeypatch.setattr(training, "APPROVED_MANIFEST_PATH", manifest)

    def cuda_must_not_run(*_args, **_kwargs):
        raise AssertionError("CUDA/training was reached without approval")

    monkeypatch.setattr(training, "_require_cuda", cuda_must_not_run)
    with pytest.raises(training.TrainingBlocked, match="GPU_TRAINING_WITHDRAWN_BY_PO"):
        training.run_owned_lora_training(
            model, train, heldout, output, manifest_path=manifest,
            execute=True, approval_verifier=verifier,
        )
    assert not output.exists()
