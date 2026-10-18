"""Local principal/confirmation execution checks, not real Artifact acceptance."""
from dataclasses import replace
import hashlib

import pytest
from flask import Flask

from lumenis.shared.agents.skills import execution as e
from lumenis.system import security
from lumenis.system.security import permission as p


@pytest.fixture
def boundary(monkeypatch):
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(p, "_TESTING_BYPASS_ENABLED", False)
    gate = p.PermissionGate()
    monkeypatch.setattr(p, "get_permission_gate", lambda: gate)
    monkeypatch.setattr(security, "get_permission_gate", lambda: gate)
    calls = {"trace": [], "evidence": [], "handler": []}
    monkeypatch.setattr(e, "write_trace", lambda ctx, *_: calls["trace"].append(ctx) or True)
    monkeypatch.setattr(
        e, "record_execution_evidence",
        lambda ctx: calls["evidence"].append(ctx) or {"ok": True},
    )
    fence = security.get_effect_fence()
    fence.clear_for_testing()
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    with app.test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        principal = p.resolve_local_workspace_principal(action="write")
        upload = p.ContentSourceImport(
            actor_id=None, domain_id="cth", subject_id=None, brand_focus_id=None,
            global_scope=True, filename="input.wav", size_bytes=3,
            body_sha256=hashlib.sha256(b"abc").hexdigest(),
            principal_kind="local_workspace", principal_ref="workspace:local",
        )
        yield app, gate, principal, upload, calls
    fence.clear_for_testing()


def confirm(principal, upload):
    pending = p.prepare_content_source_import_confirmation(None, upload, principal=principal)
    assert pending["allowed"] is True
    result = p.confirm_content_source_import(
        None, pending["confirmation_id"], principal=principal,
        domain_id="cth", global_scope=True, confirmed=True,
    )
    assert result.allowed is True


def run(boundary, **overrides):
    _app, gate, principal, upload, calls = boundary

    def handler(ctx):
        calls["handler"].append(ctx)
        decision = p.check_content_source_import_permission(None, upload, principal=principal)
        assert decision.allowed
        gate.revoke_approval(decision.approval_token)
        return {"ok": True, "artifact_id": "explicit-test-handler-only"}

    args = dict(
        skill_id="shared.content_project", product="CTH", domain="cth",
        action_type=e.ActionType.WRITE, user_id=None, user_role="user",
        permission_role="cth_operator", content_source_import=upload,
        workspace_principal=principal, handler=handler,
        skill_info=e.SkillRuntimeInfo(skill_id="shared.content_project", product="SHARED", enabled=True),
    )
    args.update(overrides)
    return e.run_execution_chain(**args)


def test_explicit_local_confirmation_runs_without_actor_or_general_write_grant(boundary):
    _app, gate, principal, upload, calls = boundary
    confirm(principal, upload)
    result = run(boundary)
    assert result.status is e.ExecutionStatus.COMPLETED
    assert result.user_id is None
    assert result.permission_result["caller"] == "workspace:local"
    assert len(calls["handler"]) == 1
    assert not gate.has_permission(p.PermissionLevel.COMMIT)
    assert "workspace_principal" not in result.to_dict()
    assert run(boundary).status is e.ExecutionStatus.REJECTED
    assert len(calls["handler"]) == 1


@pytest.mark.parametrize("change", ["user", "scope", "fake_principal", "no_confirmation"])
def test_local_context_or_confirmation_mismatch_never_executes(boundary, change):
    _app, _gate, principal, upload, calls = boundary
    if change != "no_confirmation":
        confirm(principal, upload)
    args = {}
    if change == "user":
        args["user_id"] = 1
    elif change == "scope":
        args["content_source_import"] = replace(upload, global_scope=False, subject_id="SUBJ-OTHER")
    elif change == "fake_principal":
        args["workspace_principal"] = {"principal_ref": "workspace:local"}
    result = run(boundary, **args)
    assert result.status is e.ExecutionStatus.REJECTED
    assert calls == {"trace": [], "evidence": [], "handler": []}


def test_workspace_closure_after_fence_stops_handler(boundary, monkeypatch):
    app, _gate, principal, upload, calls = boundary
    confirm(principal, upload)
    original = e.effect_fence

    def close_after_fence(ctx):
        decision = original(ctx)
        app.config["LUMENIS_OPEN_WORKSPACE"] = False
        return decision

    monkeypatch.setattr(e, "effect_fence", close_after_fence)
    assert run(boundary).status is e.ExecutionStatus.REJECTED
    assert calls == {"trace": [], "evidence": [], "handler": []}


def test_workspace_principal_cannot_authorize_a_different_skill(boundary):
    _app, _gate, principal, upload, calls = boundary
    confirm(principal, upload)
    result = run(boundary, skill_id="other.skill")
    assert result.status is e.ExecutionStatus.REJECTED
    assert calls == {"trace": [], "evidence": [], "handler": []}


def test_serialization_never_deepcopies_server_principal():
    class Opaque:
        def __deepcopy__(self, _memo):
            pytest.fail("server principal must never be serialized")

    context = e.SkillExecutionContext(workspace_principal=Opaque())
    assert "workspace_principal" not in context.to_dict()

def test_effectful_success_never_reports_completed_without_required_evidence(boundary, monkeypatch):
    _app, _gate, principal, upload, calls = boundary
    confirm(principal, upload)
    monkeypatch.setattr(
        e, "record_execution_evidence",
        lambda ctx: {"ok": False, "error": "INJECTED_EVIDENCE_FAILURE"},
    )

    result = run(boundary)

    assert len(calls["handler"]) == 1
    assert result.status is e.ExecutionStatus.FAILED
    assert result.error == "EVIDENCE_RECORD_FAILED"
    assert result.evaluation["success"] is False
    assert result.evaluation["quality_score"] == 0.0
    assert result.evaluation["validation_status"] == "failed_no_evidence"
