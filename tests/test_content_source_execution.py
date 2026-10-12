"""Execution-chain boundary for server-derived content source imports.

Account scope reads below are explicitly labeled fixtures. Permission audit,
exact approval, Action Firewall, and Effect Fence remain the real in-memory
owners; these tests are not account or user-work acceptance.
"""
import hashlib
import json
from dataclasses import replace
from datetime import timedelta

import pytest

from lumenis.shared.agents.skills import execution
from lumenis.system import security
from lumenis.system.security import permission as permission_module


def test_execution_serialization_never_traverses_server_only_context():
    class OpaqueContext:
        def __deepcopy__(self, _memo):
            pytest.fail("server-only context must not be traversed")

    opaque = OpaqueContext()
    context = execution.SkillExecutionContext(
        skill_id="shared.content_project", content_source_import=opaque,
        request_context=opaque, input_payload={"title": "Local edit"},
    )

    serialized = context.to_dict()

    assert "content_source_import" not in serialized
    assert "request_context" not in serialized
    assert serialized["input_payload"] == {"title": "Local edit"}
    assert context.request_context is opaque


@pytest.fixture
def source_import_boundary(monkeypatch):
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(permission_module, "_TESTING_BYPASS_ENABLED", False)
    reads = {
        "fixture_label": "test-only account content-scope fixture",
        "active": True,
        "calls": [],
    }

    def actor_has_scope(actor_id, product_id, module, action, *, connection=None):
        reads["calls"].append((actor_id, product_id, module, action))
        return reads["active"] and actor_id == 1 and module == "content" and action == "write"

    monkeypatch.setattr(permission_module, "_actor_has_scope_action", actor_has_scope)
    monkeypatch.setattr(
        permission_module, "_load_actor_scope_role",
        lambda _actor, *, connection=None: "user",
    )
    monkeypatch.setattr(
        permission_module, "_registered_resource_scope_exists", lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        permission_module,
        "_load_actor_scope_grants",
        lambda _actor, *, connection=None: [
            {
                "product_id": product,
                "module": "content",
                "action": "write",
                "data_scope": json.dumps({"global": True}),
            }
            for product in ("CTH", "ZBMP")
        ],
    )

    previous_bypass = permission_module._TESTING_BYPASS_ENABLED
    permission_module.set_testing_bypass(False)
    gate = permission_module.PermissionGate(
        enabled_permissions={permission_module.PermissionLevel.COMMIT},
    )
    monkeypatch.setattr(permission_module, "get_permission_gate", lambda: gate)
    monkeypatch.setattr(security, "get_permission_gate", lambda: gate)
    fence = security.get_effect_fence()
    fence.clear_for_testing()
    skill = execution.SkillRuntimeInfo(
        skill_id="shared.content_project",
        product="SHARED",
        enabled=True,
        state=execution.SkillState.ENABLED,
    )
    upload = permission_module.ContentSourceImport(
        actor_id=1,
        domain_id="cth",
        subject_id=None,
        brand_focus_id=None,
        global_scope=True,
        filename="source.mp4",
        size_bytes=3,
        body_sha256=hashlib.sha256(b"abc").hexdigest(),
    )
    yield gate, fence, skill, upload, reads
    fence.clear_for_testing()
    permission_module.set_testing_bypass(previous_bypass)


def _approve(gate, upload):
    scope = permission_module.check_actor_scope_permission(
        {"id": upload.actor_id},
        domain_id=upload.domain_id,
        action="write",
        module="content",
        subject_id=upload.subject_id,
        brand_focus_id=upload.brand_focus_id,
        global_scope=upload.global_scope,
        gate=gate,
    )
    resource = permission_module.content_source_import_resource(scope, upload, gate=gate)
    token = gate.grant_approval(
        permission_module.OperationType.DB_WRITE,
        resource=resource,
        granted_by="test-only approval fixture",
    )
    return resource, token


def _run(gate, skill, upload, handler, **overrides):
    values = {
        "skill_id": "shared.content_project",
        "task": "stage authorized content source",
        # These client fields must not choose the source identity or effect target.
        "input_payload": {"target": "production_db", "staging": False},
        "action_type": execution.ActionType.WRITE,
        "user_id": 1,
        "user_role": "user",
        "product": "CTH",
        "domain": "cth",
        "permission_role": "cth_operator",
        "skill_info": skill,
        "handler": handler,
        "content_source_import": upload,
    }
    values.update(overrides)
    return execution.run_execution_chain(**values)


def _track_persistent_bridges(monkeypatch):
    calls = {"trace": [], "evidence": []}
    monkeypatch.setattr(execution, "write_trace", lambda ctx, *_a: calls["trace"].append(ctx))
    monkeypatch.setattr(
        execution, "record_execution_evidence",
        lambda ctx: calls["evidence"].append(ctx) or {"ok": True},
    )
    return calls


@pytest.fixture
def shared_source_boundary(source_import_boundary, monkeypatch):
    _legacy_gate, fence, skill, _legacy_upload, reads = source_import_boundary
    gate = permission_module.PermissionGate(
        enabled_permissions={permission_module.PermissionLevel.READ},
    )
    monkeypatch.setattr(permission_module, "get_permission_gate", lambda: gate)
    monkeypatch.setattr(security, "get_permission_gate", lambda: gate)
    monkeypatch.setattr(permission_module, "_load_actor_scope_grants", lambda _actor, *, connection=None: [{
        "product_id": "SHARED", "module": "content", "action": "write",
        "data_scope": None, "time_range": None,
    }])
    upload = permission_module.make_shared_content_source_import(
        {"id": 1}, {"scope_kind": "shared_workspace", "version": 1},
        filename="draft.txt", size_bytes=3,
        body_sha256=hashlib.sha256(b"abc").hexdigest(), gate=gate,
    )
    return gate, fence, skill, upload, reads


def _confirm_shared(gate, upload, *, principal=None):
    actor = {"id": upload.actor_id} if upload.actor_id is not None else None
    pending = permission_module.prepare_content_source_import_confirmation(
        actor, upload, principal=principal, gate=gate,
    )
    assert pending["allowed"] is True
    approved = permission_module.confirm_content_source_import(
        actor, pending["confirmation_id"], domain_id=None,
        workspace_scope={"scope_kind": "shared_workspace", "version": 1},
        confirmed=True, principal=principal, gate=gate,
    )
    assert approved.allowed is True
    assert approved.approval_token is None


def test_confirmed_shared_import_runs_without_domain_role_or_general_write(
    shared_source_boundary, monkeypatch,
):
    gate, _fence, skill, upload, reads = shared_source_boundary
    _confirm_shared(gate, upload)
    persistence = _track_persistent_bridges(monkeypatch)
    result = _run(gate, skill, upload, lambda ctx: {
        "ok": True, "artifact_id": "isolated-shared-staged-result",
    }, domain=None, product="SHARED", permission_role=None)

    assert result.status is execution.ExecutionStatus.COMPLETED
    assert result.domain is None and result.product == "SHARED"
    assert result.permission_result["verification_state"] == "verified"
    assert result.permission_result["approval_token"] is None
    assert result.effect_fence_result["target"].startswith("content-source-import:shared-workspace:v1:")
    assert not gate.has_permission(permission_module.PermissionLevel.COMMIT)
    assert all(call[1:4] == ("SHARED", "content", "write") for call in reads["calls"])
    assert persistence == {"trace": [result], "evidence": [result]}


@pytest.mark.parametrize("changes", [
    {"domain": "shared"}, {"domain": "cth"}, {"product": "SYSTEM"},
    {"permission_role": "system_writer"}, {"user_id": 2},
    {"action_type": execution.ActionType.COMMIT},
])
def test_shared_import_context_changes_cannot_use_the_private_grant(
    shared_source_boundary, monkeypatch, changes,
):
    gate, _fence, skill, upload, _reads = shared_source_boundary
    _confirm_shared(gate, upload)
    persistence = _track_persistent_bridges(monkeypatch)
    calls = []
    result = _run(gate, skill, upload, lambda ctx: calls.append(ctx), **{
        "domain": None, "product": "SHARED", "permission_role": None, **changes,
    })

    assert result.status is execution.ExecutionStatus.REJECTED
    assert calls == []
    assert persistence == {"trace": [], "evidence": []}


def test_shared_scope_revocation_after_fence_prevents_handler(
    shared_source_boundary, monkeypatch,
):
    gate, _fence, skill, upload, reads = shared_source_boundary
    _confirm_shared(gate, upload)
    persistence = _track_persistent_bridges(monkeypatch)
    original = execution.effect_fence

    def revoke_scope(ctx):
        receipt = original(ctx)
        reads["active"] = False
        return receipt

    monkeypatch.setattr(execution, "effect_fence", revoke_scope)
    calls = []
    result = _run(gate, skill, upload, lambda ctx: calls.append(ctx),
                  domain=None, product="SHARED", permission_role=None)

    assert result.status is execution.ExecutionStatus.REJECTED
    assert calls == []
    assert persistence == {"trace": [], "evidence": []}


def test_unconfirmed_shared_descriptor_has_no_generic_write_fallback(
    shared_source_boundary, monkeypatch,
):
    gate, _fence, skill, upload, _reads = shared_source_boundary
    persistence = _track_persistent_bridges(monkeypatch)
    calls = []
    result = _run(gate, skill, upload, lambda ctx: calls.append(ctx),
                  domain=None, product="SHARED", permission_role=None)

    assert result.status is execution.ExecutionStatus.REJECTED
    assert calls == []
    assert persistence == {"trace": [], "evidence": []}


def test_unverified_shared_permission_receipt_never_reaches_handler(
    shared_source_boundary, monkeypatch,
):
    gate, _fence, skill, upload, _reads = shared_source_boundary
    _confirm_shared(gate, upload)
    persistence = _track_persistent_bridges(monkeypatch)
    check = security.check_content_source_import_permission

    def unverified_receipt(*args, **kwargs):
        return replace(check(*args, **kwargs), verification_state="unavailable")

    monkeypatch.setattr(security, "check_content_source_import_permission", unverified_receipt)
    calls = []
    result = _run(gate, skill, upload, lambda ctx: calls.append(ctx),
                  domain=None, product="SHARED", permission_role=None)

    assert result.status is execution.ExecutionStatus.REJECTED
    assert result.permission_result["allowed"] is False
    assert result.permission_result["code"] == "PERMISSION_UNAVAILABLE"
    assert result.permission_result["verification_state"] == "unavailable"
    assert calls == []
    assert persistence == {"trace": [], "evidence": []}


def test_current_local_shared_principal_uses_the_same_private_confirmation(
    shared_source_boundary, monkeypatch,
):
    from flask import Flask

    gate, _fence, skill, _account_upload, _reads = shared_source_boundary
    persistence = _track_persistent_bridges(monkeypatch)
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    with app.test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        principal = permission_module.resolve_local_workspace_principal(action="write")
        upload = permission_module.make_shared_content_source_import(
            None, {"scope_kind": "shared_workspace", "version": 1},
            filename="draft.txt", size_bytes=3,
            body_sha256=hashlib.sha256(b"abc").hexdigest(),
            principal=principal, gate=gate,
        )
        _confirm_shared(gate, upload, principal=principal)
        result = _run(gate, skill, upload, lambda _ctx: {
            "ok": True, "artifact_id": "isolated-local-shared-staged-result",
        }, domain=None, product="SHARED", permission_role=None,
            user_id=None, workspace_principal=principal)

    assert result.status is execution.ExecutionStatus.COMPLETED
    assert result.permission_result["caller"] == "workspace:local"
    assert result.permission_result["approval_token"] is None
    assert "workspace_principal" not in result.to_dict()
    assert persistence == {"trace": [result], "evidence": [result]}


def test_unapproved_import_rejects_without_handler_evidence_or_trace(
    source_import_boundary, monkeypatch,
):
    gate, _fence, skill, upload, reads = source_import_boundary
    persistence = _track_persistent_bridges(monkeypatch)
    handler_calls = []

    result = _run(gate, skill, upload, lambda ctx: handler_calls.append(ctx))

    assert result.status is execution.ExecutionStatus.REJECTED
    assert result.permission_result["requires_approval"] is True
    assert handler_calls == []
    assert persistence == {"trace": [], "evidence": []}
    assert reads["fixture_label"] == "test-only account content-scope fixture"
    assert reads["calls"]
    assert gate.get_audit_log(result_filter="denied")


@pytest.mark.parametrize("mismatch", [
    {"user_id": 2},
    {"domain": "zbmp", "product": "ZBMP"},
    {"product": "SYSTEM"},
    {"permission_role": "cth_analyst"},
    {"skill_info": execution.SkillRuntimeInfo(
        skill_id="shared.content_project", product="SHARED", enabled=False,
    )},
    {"action_type": execution.ActionType.ANALYZE},
])
def test_context_mismatch_never_reaches_handler_or_persistent_bridges(
    source_import_boundary, monkeypatch, mismatch,
):
    gate, _fence, skill, upload, _reads = source_import_boundary
    _approve(gate, upload)
    persistence = _track_persistent_bridges(monkeypatch)
    handler_calls = []

    result = _run(
        gate, skill, upload, lambda ctx: handler_calls.append(ctx), **mismatch,
    )

    assert result.status is execution.ExecutionStatus.REJECTED
    assert handler_calls == []
    assert persistence == {"trace": [], "evidence": []}


def test_permission_revocation_after_fence_is_rechecked_before_handler(
    source_import_boundary, monkeypatch,
):
    gate, _fence, skill, upload, _reads = source_import_boundary
    _resource, token = _approve(gate, upload)
    persistence = _track_persistent_bridges(monkeypatch)
    handler_calls = []
    real_fence = execution.effect_fence

    def fence_then_cancel(ctx):
        decision = real_fence(ctx)
        assert gate.revoke_approval(token)
        return decision

    monkeypatch.setattr(execution, "effect_fence", fence_then_cancel)
    result = _run(gate, skill, upload, lambda ctx: handler_calls.append(ctx))

    assert result.status is execution.ExecutionStatus.REJECTED
    assert result.error
    assert handler_calls == []
    assert result.firewall_result["allowed"] is True
    assert result.effect_fence_result["allowed"] is True
    assert persistence == {"trace": [], "evidence": []}


def test_account_scope_revocation_after_fence_is_rechecked_before_handler(
    source_import_boundary, monkeypatch,
):
    gate, _fence, skill, upload, reads = source_import_boundary
    _approve(gate, upload)
    persistence = _track_persistent_bridges(monkeypatch)
    handler_calls = []
    real_fence = execution.effect_fence

    def fence_then_revoke_account(ctx):
        decision = real_fence(ctx)
        reads["active"] = False
        return decision

    monkeypatch.setattr(execution, "effect_fence", fence_then_revoke_account)
    result = _run(gate, skill, upload, lambda ctx: handler_calls.append(ctx))

    assert result.status is execution.ExecutionStatus.REJECTED
    assert handler_calls == []
    assert persistence == {"trace": [], "evidence": []}


def test_descriptor_replacement_after_fence_never_reaches_handler(
    source_import_boundary, monkeypatch,
):
    gate, _fence, skill, upload, _reads = source_import_boundary
    _approve(gate, upload)
    persistence = _track_persistent_bridges(monkeypatch)
    handler_calls = []
    changed = replace(upload, filename="changed.mp4")
    real_fence = execution.effect_fence

    def fence_then_replace_descriptor(ctx):
        decision = real_fence(ctx)
        ctx.content_source_import = changed
        return decision

    monkeypatch.setattr(execution, "effect_fence", fence_then_replace_descriptor)
    result = _run(gate, skill, upload, lambda ctx: handler_calls.append(ctx))

    assert result.status is execution.ExecutionStatus.REJECTED
    assert "descriptor changed" in result.error
    assert handler_calls == []
    assert persistence == {"trace": [], "evidence": []}


def test_success_consumes_approval_in_handler_without_post_handler_recheck(
    source_import_boundary, monkeypatch,
):
    gate, _fence, skill, upload, _reads = source_import_boundary
    resource, token = _approve(gate, upload)
    persistence = _track_persistent_bridges(monkeypatch)
    permission_calls = []
    original_check = security.check_content_source_import_permission

    def counted_check(actor, descriptor, **kwargs):
        result = original_check(actor, descriptor, **kwargs)
        permission_calls.append((descriptor, result.allowed))
        return result

    monkeypatch.setattr(security, "check_content_source_import_permission", counted_check)
    handler_calls = []
    request_context = {
        "domain_id": "cth",
        "subject_id": None,
        "brand_focus_id": None,
        "global_scope": True,
        "source": "server-created test fixture",
    }

    def stage_handler(ctx):
        handler_calls.append(ctx)
        assert ctx.request_context is request_context
        # The owning stage handler performs its own live pre-write check, then
        # consumes the exact single-use approval on successful registry insert.
        assert original_check({"id": 1}, ctx.content_source_import, gate=gate).allowed
        assert gate.revoke_approval(token)
        return {"ok": True, "artifact_id": "fixture-artifact"}

    result = _run(
        gate, skill, upload, stage_handler, request_context=request_context,
    )

    assert result.status is execution.ExecutionStatus.COMPLETED
    assert result.permission_result["resource"] == resource
    assert result.firewall_result["allowed"] is True
    assert result.effect_fence_result["allowed"] is True
    assert result.effect_fence_result["target"] == resource
    assert len(permission_calls) == 2  # both chain checks precede the handler
    assert len(handler_calls) == 1
    assert persistence == {"trace": [result], "evidence": [result]}
    assert not gate.get_valid_approval_token("db_write", resource, exact=True)
    assert "content_source_import" not in result.to_dict()
    assert "request_context" not in result.to_dict()


def test_pending_or_failed_handler_result_has_no_persistent_bridges(
    source_import_boundary, monkeypatch,
):
    gate, _fence, skill, upload, _reads = source_import_boundary
    _approve(gate, upload)
    persistence = _track_persistent_bridges(monkeypatch)

    result = _run(
        gate, skill, upload,
        lambda _ctx: {"status": "pending", "error": "approval was withdrawn"},
    )

    assert result.status is execution.ExecutionStatus.FAILED
    assert persistence == {"trace": [], "evidence": []}


def test_non_typed_descriptor_and_missing_handler_fail_without_persistence(
    source_import_boundary, monkeypatch,
):
    gate, _fence, skill, upload, _reads = source_import_boundary
    _approve(gate, upload)
    persistence = _track_persistent_bridges(monkeypatch)
    handler_calls = []

    forged = _run(
        gate, skill, upload, lambda ctx: handler_calls.append(ctx),
        content_source_import={
            "actor_id": upload.actor_id,
            "domain_id": upload.domain_id,
            "filename": upload.filename,
            "approval_token": next(iter(gate._approvals)),
        },
    )
    no_handler = _run(gate, skill, upload, None)

    assert forged.status is execution.ExecutionStatus.REJECTED
    assert no_handler.status is execution.ExecutionStatus.REJECTED
    assert handler_calls == []
    assert persistence == {"trace": [], "evidence": []}


def test_expired_exact_approval_never_invokes_handler_or_writes_trace(
    source_import_boundary, monkeypatch,
):
    gate, _fence, skill, upload, _reads = source_import_boundary
    _resource, token = _approve(gate, upload)
    approval = gate._approvals[token]
    approval.expires_at -= timedelta(days=1)
    persistence = _track_persistent_bridges(monkeypatch)
    handler_calls = []

    result = _run(gate, skill, upload, lambda ctx: handler_calls.append(ctx))

    assert result.status is execution.ExecutionStatus.REJECTED
    assert handler_calls == []
    assert persistence == {"trace": [], "evidence": []}


def test_effect_finalization_failure_retains_result_without_claiming_completion(
    source_import_boundary, monkeypatch, caplog,
):
    gate, fence, skill, upload, _reads = source_import_boundary
    _approve(gate, upload)
    persistence = _track_persistent_bridges(monkeypatch)
    payload = {"status": "completed", "artifact": {"id": "isolated-staged-result"}}

    def failed_completion(*_args, **_kwargs):
        raise RuntimeError("synthetic-private-effect-error")

    monkeypatch.setattr(fence, "complete", failed_completion)
    result = _run(gate, skill, upload, lambda _ctx: payload)

    assert result.status is execution.ExecutionStatus.FAILED
    assert result.error == "EFFECT_FENCE_FINALIZATION_FAILED"
    assert result.execute_result["result"] is payload
    assert result.effect_fence_result["retry_safe"] is False
    assert result.evaluation["success"] is False
    assert result.evaluation["validation_status"] == "failed_effect_fence"
    assert persistence == {"trace": [], "evidence": []}
    assert "synthetic-private-effect-error" not in caplog.text


@pytest.mark.parametrize("user_role", ["user", "owner"])
@pytest.mark.parametrize("domain,product", [
    ("missing", "MISSING"),
    ("system", "SYSTEM"),
    (None, "MISSING"),
    ("missing", "SHARED"),
])
def test_unrecognized_context_cannot_match_a_null_descriptor_domain(
    monkeypatch, user_role, domain, product,
):
    """Context validation only; no Scope, approval, runtime or Artifact claim."""
    upload = permission_module.ContentSourceImport(
        actor_id=1, domain_id=None, subject_id=None, brand_focus_id=None,
        global_scope=False, filename="source.mp4", size_bytes=3,
        body_sha256=hashlib.sha256(b"abc").hexdigest(),
    )
    skill = execution.SkillRuntimeInfo(
        skill_id="shared.content_project", product="SHARED", enabled=True,
    )
    context = execution.SkillExecutionContext(
        skill_id=skill.skill_id, user_id=1, action_type=execution.ActionType.WRITE,
        domain=domain, product=product, content_source_import=upload,
    )

    def unexpected_permission_call(*_args, **_kwargs):
        pytest.fail("unrecognized context reached the canonical import checker")

    monkeypatch.setattr(
        security, "check_content_source_import_permission", unexpected_permission_call,
    )
    result = execution.check_permission(context, user_role=user_role, skill_info=skill)
    assert result["allowed"] is False
    assert result["code"] in {"CONTENT_SOURCE_CONTEXT_MISMATCH", "INSUFFICIENT_ROLE"}
