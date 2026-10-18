"""Execution-chain boundary for server-derived content source imports.

Account scope reads below are explicitly labeled fixtures. Permission audit,
exact approval, Action Firewall, and Effect Fence remain the real in-memory
owners; these tests are not account or user-work acceptance.
"""
from dataclasses import replace
from datetime import datetime, timedelta
import hashlib
import json

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

    def actor_has_scope(actor_id, product_id, module, action):
        reads["calls"].append((actor_id, product_id, module, action))
        return reads["active"] and actor_id == 1 and module == "content" and action == "write"

    monkeypatch.setattr(permission_module, "_actor_has_scope_action", actor_has_scope)
    monkeypatch.setattr(permission_module, "_load_actor_scope_role", lambda _actor: "user")
    monkeypatch.setattr(
        permission_module, "_registered_resource_scope_exists", lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        permission_module,
        "_load_actor_scope_grants",
        lambda _actor: [
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
    monkeypatch.setattr(execution, "write_trace", lambda ctx, *_a: calls["trace"].append(ctx) or True)
    monkeypatch.setattr(
        execution, "record_execution_evidence",
        lambda ctx: calls["evidence"].append(ctx) or {"ok": True},
    )
    return calls


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
    gate, fence, skill, upload, _reads = source_import_boundary
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
    gate._approvals[token].expires_at = datetime.now() - timedelta(seconds=1)
    persistence = _track_persistent_bridges(monkeypatch)
    handler_calls = []

    result = _run(gate, skill, upload, lambda ctx: handler_calls.append(ctx))

    assert result.status is execution.ExecutionStatus.REJECTED
    assert handler_calls == []
    assert persistence == {"trace": [], "evidence": []}
