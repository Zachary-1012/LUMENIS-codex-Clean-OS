"""Isolated Permission regressions for owned-model runtime admission."""

from dataclasses import replace
from datetime import datetime, timedelta
import hashlib
import json
import sqlite3

from flask import Flask
import pytest

from agent_capability.formation import implementation_identity
from lumenis.system.ai_gateway.owned_service import OwnedModelAdmissionRequest
from lumenis.system.security import owned_model_admission as admission
from lumenis.system.security import permission as p


@pytest.fixture(autouse=True)
def _strict_permission(monkeypatch):
    previous = p._TESTING_BYPASS_ENABLED
    p.set_testing_bypass(False)
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    yield
    p.set_testing_bypass(previous)


@pytest.fixture
def scope_db(tmp_path, monkeypatch):
    path = tmp_path / "owned-model-admission.sqlite3"
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
            INSERT INTO v4_users (id, role, status)
            VALUES (1, 'user', 'active'), (2, 'user', 'active');
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
            "2026-10-08", "2026-10-08",
        ))
    return path


def _grant_scope(path, actor_id=1, *, data_scope=None):
    with sqlite3.connect(path) as conn:
        conn.execute("""
            INSERT INTO v4_member_authorizations (
                user_id, product_id, module, action, data_scope, time_range
            ) VALUES (?, 'CTH', 'owned_model_admission', 'write', ?, NULL)
        """, (actor_id, json.dumps(data_scope or {"global": True})))


def _context(scope="GLOBAL / ALL", *, global_scope=True, domain="cth"):
    product_id = "CTH" if domain == "cth" else "ZBMP"
    return {"scope_descriptors": {scope: {
        "domain_id": domain, "product_id": product_id,
        "global_scope": global_scope,
        "subject_id": None if global_scope or domain != "cth" else scope,
        "brand_focus_id": scope if not global_scope and domain == "bmp" else None,
    }}}


def _review_true(_request):
    return True


def _review_false(_request):
    return False


def _review_non_boolean(_request):
    return 1


def _request(**changes):
    reviewer = changes.pop("_review_validator", _review_true)
    values = {
        "action": "admit",
        "model_id": "lumenis/owned-base",
        "model_revision": "revision-1",
        "recipe": "canonical-recipe-v1",
        "domain_id": "cth",
        "scopes": ("GLOBAL / ALL",),
        "manifest_sha256": "1" * 64,
        "train_sha256": "2" * 64,
        "heldout_sha256": "3" * 64,
        "candidate_identity_sha256": "4" * 64,
        "adapter_sha256": "5" * 64,
        "adapter_config_sha256": "6" * 64,
        "training_run_sha256": "7" * 64,
        "checkpoint_recovery_sha256": "8" * 64,
        "evaluation_sha256": "9" * 64,
        "quality_review_sha256": "a" * 64,
        "source_use_sha256": "b" * 64,
        "source_use_version": "source-use-v1",
        "evaluation_ref": "evaluation:case-1",
        "quality_review_ref": "quality-review:case-1",
        "runtime_sha256": "c" * 64,
        "executor_sha256": "d" * 64,
        "review_validator_sha256": implementation_identity(reviewer),
        "source_validator_sha256": "e" * 64,
        "allowed_operations": ("inference_generate",),
        "context_window_tokens": 4096,
        "output_token_limit": 512,
        "prior_binding_sha256": None,
    }
    values.update(changes)
    return OwnedModelAdmissionRequest(**values)


def _gate(monkeypatch):
    gate = p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT})
    monkeypatch.setattr(p, "get_permission_gate", lambda: gate)
    return gate


def _verifier(gate, request, *, actor_id=1, context=None, reviewer=_review_true):
    return admission.make_owned_model_admission_verifier(
        gate, request, actor_id=actor_id, domain_id="cth",
        context=context or _context(), review_validator=reviewer,
    )


def _approve(gate, verifier):
    return gate.grant_approval(
        p.OperationType.RUNTIME_OPERATION.value,
        resource=verifier.resource,
        granted_by="test-human-reviewer",
    )


def test_runtime_admission_requires_exact_manual_approval_and_redacts_token(
    scope_db, monkeypatch,
):
    _grant_scope(scope_db)
    gate = _gate(monkeypatch)
    request = _request()
    verifier = _verifier(gate, request)

    assert verifier.resource.startswith("owned_model_admission:v1:")
    denied = verifier.recheck()
    assert denied.allowed is False
    assert denied.code == "EXACT_RUNTIME_APPROVAL_REQUIRED"

    token = _approve(gate, verifier)
    decision = verifier.recheck()
    assert decision.allowed is True
    assert decision.code == "EXACT_RUNTIME_APPROVAL_VERIFIED"
    assert decision.permission_audit_id
    assert decision.scope_audit_ids
    assert decision.approval_token_sha256 == hashlib.sha256(token.encode()).hexdigest()
    assert token not in repr(decision.to_dict())
    assert verifier.public_identity["request_sha256"] == decision.request_sha256
    assert verifier.public_identity["resource"] == verifier.resource


def test_model_train_or_wildcard_approval_cannot_admit_a_runtime_binding(
    scope_db, monkeypatch,
):
    _grant_scope(scope_db)
    gate = _gate(monkeypatch)
    verifier = _verifier(gate, _request())
    gate.grant_approval(
        p.OperationType.MODEL_TRAIN.value,
        resource=verifier.resource,
        granted_by="test-human-reviewer",
    )
    gate.grant_approval("*", resource="*", granted_by="test-human-reviewer")

    decision = verifier.recheck()
    assert decision.allowed is False
    assert decision.code == "EXACT_RUNTIME_APPROVAL_REQUIRED"


def test_recheck_observes_live_scope_removal_and_approval_revocation(
    scope_db, monkeypatch,
):
    _grant_scope(scope_db)
    gate = _gate(monkeypatch)
    verifier = _verifier(gate, _request())
    token = _approve(gate, verifier)
    assert verifier.recheck().allowed is True

    assert gate.revoke_approval(token) is True
    assert verifier.recheck().allowed is False

    token = _approve(gate, verifier)
    assert verifier.recheck().allowed is True
    with sqlite3.connect(scope_db) as conn:
        conn.execute("DELETE FROM v4_member_authorizations WHERE user_id = 1")
    denied = verifier.recheck()
    assert denied.allowed is False
    assert denied.code == "ACTOR_SCOPE_DENIED"


@pytest.mark.parametrize("state", ["expired", "testing_bypass"])
def test_recheck_fails_when_approval_expires_or_test_bypass_is_enabled(
    scope_db, monkeypatch, state,
):
    _grant_scope(scope_db)
    gate = _gate(monkeypatch)
    verifier = _verifier(gate, _request())
    token = _approve(gate, verifier)

    if state == "expired":
        gate._approvals[token].expires_at = datetime.now() - timedelta(seconds=1)
    else:
        p.set_testing_bypass(True)

    decision = verifier.recheck()
    assert decision.allowed is False
    assert decision.code in {
        "EXACT_RUNTIME_APPROVAL_REQUIRED", "TESTING_BYPASS_ENABLED",
    }


@pytest.mark.parametrize("change", [
    {"action": "rollback", "prior_binding_sha256": "f" * 64},
    {"model_id": "lumenis/owned-base-v2"},
    {"model_revision": "revision-2"},
    {"recipe": "canonical-recipe-v2"},
    {"manifest_sha256": "f" * 64},
    {"train_sha256": "f" * 64},
    {"heldout_sha256": "f" * 64},
    {"candidate_identity_sha256": "f" * 64},
    {"adapter_sha256": "f" * 64},
    {"adapter_config_sha256": "f" * 64},
    {"training_run_sha256": "f" * 64},
    {"checkpoint_recovery_sha256": "f" * 64},
    {"evaluation_sha256": "f" * 64},
    {"quality_review_sha256": "f" * 64},
    {"source_use_sha256": "f" * 64},
    {"source_use_version": "source-use-v2"},
    {"evaluation_ref": "evaluation:case-2"},
    {"quality_review_ref": "quality-review:case-2"},
    {"review_validator_sha256": "f" * 64},
    {"source_validator_sha256": "f" * 64},
    {"runtime_sha256": "f" * 64},
    {"executor_sha256": "f" * 64},
    {"allowed_operations": ("inference_generate", "inference_embed")},
    {"context_window_tokens": 8192},
    {"output_token_limit": 256},
    {"prior_binding_sha256": "f" * 64},
])
def test_resource_hash_binds_each_runtime_and_evidence_pin(change):
    original = _request()
    altered = replace(original, **change)

    assert admission.owned_model_admission_resource(
        original, actor_id=1, domain_id="cth", context=_context(),
    ) != admission.owned_model_admission_resource(
        altered, actor_id=1, domain_id="cth", context=_context(),
    )


def test_resource_hash_binds_exact_domain_and_canonical_scope_descriptors():
    request = _request()
    original = admission.owned_model_admission_resource(
        request, actor_id=1, domain_id="cth", context=_context(),
    )
    other_domain = replace(request, domain_id="bmp")
    bmp_context = _context(domain="bmp")
    assert admission.owned_model_admission_resource(
        other_domain, actor_id=1, domain_id="bmp", context=bmp_context,
    ) != original

    scoped = replace(request, scopes=("SUBJ-CTH-A",))
    subject_context = _context("SUBJ-CTH-A", global_scope=False)
    assert admission.owned_model_admission_resource(
        scoped, actor_id=1, domain_id="cth", context=subject_context,
    ) != original


@pytest.mark.parametrize("change", [
    {"manifest_sha256": "A" * 64},
    {"source_validator_sha256": "not-a-digest"},
    {"scopes": ("GLOBAL / ALL", "GLOBAL / ALL")},
    {"allowed_operations": ("*",)},
    {"context_window_tokens": True},
    {"output_token_limit": 4097},
])
def test_invalid_hash_scope_wildcard_and_token_limits_fail_closed(change):
    request = _request(**change)

    with pytest.raises(ValueError):
        admission.owned_model_admission_resource(
            request, actor_id=1, domain_id="cth", context=_context(),
        )


def test_request_mutation_after_verifier_creation_invalidates_binding(
    scope_db, monkeypatch,
):
    _grant_scope(scope_db)
    gate = _gate(monkeypatch)
    request = _request()
    verifier = _verifier(gate, request)
    _approve(gate, verifier)

    object.__setattr__(request, "runtime_sha256", "f" * 64)
    decision = verifier.recheck()
    assert decision.allowed is False
    assert decision.code == "REQUEST_OR_CONTEXT_CHANGED"


@pytest.mark.parametrize("reviewer", [_review_false, _review_non_boolean])
def test_quality_review_must_be_fresh_literal_true(scope_db, monkeypatch, reviewer):
    _grant_scope(scope_db)
    gate = _gate(monkeypatch)
    request = _request(_review_validator=reviewer)
    verifier = _verifier(gate, request, reviewer=reviewer)
    _approve(gate, verifier)

    decision = verifier.recheck()
    assert decision.allowed is False
    assert decision.code == "QUALITY_REVIEW_UNAVAILABLE_OR_FAILED"


def test_revoke_can_disable_a_binding_when_quality_review_fails_but_needs_exact_auth(
    scope_db, monkeypatch,
):
    _grant_scope(scope_db)
    gate = _gate(monkeypatch)
    request = _request(
        action="revoke",
        prior_binding_sha256="f" * 64,
        _review_validator=_review_false,
    )
    verifier = _verifier(gate, request, reviewer=_review_false)

    assert verifier.recheck().allowed is False
    _approve(gate, verifier)
    decision = verifier.recheck()
    assert decision.allowed is True
    assert decision.code == "EXACT_RUNTIME_APPROVAL_VERIFIED"


def test_review_callback_identity_must_match_the_pinned_server_implementation(
    scope_db, monkeypatch,
):
    _grant_scope(scope_db)
    gate = _gate(monkeypatch)
    request = _request()
    verifier = _verifier(gate, request, reviewer=_review_false)
    _approve(gate, verifier)

    decision = verifier.recheck()
    assert decision.allowed is False
    assert decision.code == "REVIEW_VALIDATOR_IDENTITY_MISMATCH"


def test_actor_identity_is_bound_into_the_exact_approval_resource(
    scope_db, monkeypatch,
):
    _grant_scope(scope_db, 1)
    _grant_scope(scope_db, 2)
    gate = _gate(monkeypatch)
    request = _request()
    first = _verifier(gate, request, actor_id=1)
    _approve(gate, first)
    second = _verifier(gate, request, actor_id=2)

    assert first.resource != second.resource
    assert second.recheck().allowed is False


def test_workspace_principal_fails_closed_until_admission_scope_is_registered(
    monkeypatch,
):
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    with app.test_request_context(
        "/", headers={"Host": "localhost"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ):
        principal = p.resolve_local_workspace_principal(
            module="owned_training", action="write",
        )
        assert type(principal) is p.LocalWorkspacePrincipal
        resolver = p.resolve_local_workspace_principal

        def unavailable_admission_route(*, module="content", action="read"):
            if module == "owned_model_admission":
                return None
            return resolver(module=module, action=action)

        monkeypatch.setattr(
            p, "resolve_local_workspace_principal", unavailable_admission_route,
        )
        gate = _gate(monkeypatch)
        verifier = admission.make_owned_model_admission_verifier(
            gate, _request(), domain_id="cth", context=_context(),
            principal=principal, review_validator=_review_true,
        )

        decision = verifier.recheck()
        assert decision.allowed is False
        assert decision.code == "WORKSPACE_ADMISSION_SCOPE_UNAVAILABLE"


def test_workspace_admission_uses_live_registered_scope_and_revocation(
    scope_db, monkeypatch,
):
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    request = _request(scopes=("SUBJ-CTH-A",))
    context = _context("SUBJ-CTH-A", global_scope=False)

    with app.test_request_context(
        "/", headers={"Host": "localhost"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ):
        principal = p.resolve_local_workspace_principal(
            module="owned_model_admission", action="write",
        )
        assert type(principal) is p.LocalWorkspacePrincipal

        gate = _gate(monkeypatch)
        verifier = admission.make_owned_model_admission_verifier(
            gate, request, domain_id="cth", context=context,
            principal=principal, review_validator=_review_true,
        )
        token = _approve(gate, verifier)

        allowed = verifier.recheck()
        assert allowed.allowed is True
        assert allowed.code == "EXACT_RUNTIME_APPROVAL_VERIFIED"
        assert allowed.scope_audit_ids
        assert allowed.approval_token_sha256 == hashlib.sha256(
            token.encode(),
        ).hexdigest()

        assert gate.revoke_approval(token) is True
        revoked = verifier.recheck()
        assert revoked.allowed is False
        assert revoked.code == "EXACT_RUNTIME_APPROVAL_REQUIRED"

        _approve(gate, verifier)
        assert verifier.recheck().allowed is True
        with sqlite3.connect(scope_db) as conn:
            conn.execute(
                "DELETE FROM lumenis_subject_registry WHERE subject_id = ?",
                ("SUBJ-CTH-A",),
            )
        scope_revoked = verifier.recheck()
        assert scope_revoked.allowed is False
        assert scope_revoked.code == "ACTOR_SCOPE_DENIED"
