"""Focused Permission checks for independent Shared content imports."""

import hashlib
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask

from lumenis.system.security import permission as p

SCOPE = {"scope_kind": "shared_workspace", "version": 1}
BODY = b"A permitted Shared workspace content source."


def _local_now_naive():
    return datetime.now(timezone.utc).astimezone().replace(tzinfo=None)


@pytest.fixture(autouse=True)
def strict_permission_mode(monkeypatch):
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    previous = p._TESTING_BYPASS_ENABLED
    p.set_testing_bypass(False)
    yield
    p.set_testing_bypass(previous)


def _account_permission(monkeypatch):
    state = {
        "active": True,
        "role": "user",
        "grants": [{
            "product_id": "SHARED",
            "module": "content",
            "action": "write",
            "data_scope": None,
            "time_range": None,
        }],
        "scope_calls": [],
    }

    def has_scope(actor_id, product_id, module, action, *, connection=None):
        state["scope_calls"].append(
            (actor_id, product_id, module, action, connection),
        )
        return state["active"]

    monkeypatch.setattr(p, "_actor_has_scope_action", has_scope)
    monkeypatch.setattr(
        p, "_load_actor_scope_role",
        lambda actor_id, *, connection=None: state["role"],
    )
    monkeypatch.setattr(
        p, "_load_actor_scope_grants",
        lambda actor_id, *, connection=None: [dict(grant) for grant in state["grants"]],
    )
    return state


def _actor(actor_id=23):
    # The role is intentionally client-shaped; Permission must use the server
    # role/grant readers above instead.
    return {"id": actor_id, "role": "owner"}


def _gate():
    # Content-source confirmation is the only authority for this import. The
    # normal user does not need a general COMMIT grant.
    return p.PermissionGate(enabled_permissions={p.PermissionLevel.READ})


def _upload(actor, gate, *, body=BODY, filename="draft.txt"):
    return p.make_shared_content_source_import(
        actor,
        dict(SCOPE),
        filename=filename,
        size_bytes=len(body),
        body_sha256=hashlib.sha256(body).hexdigest(),
        gate=gate,
    )


def _prepare(actor, upload, gate):
    return p.prepare_content_source_import_confirmation(actor, upload, gate=gate)


def _confirm(actor, confirmation_id, gate, **changes):
    kwargs = {
        "domain_id": None,
        "workspace_scope": dict(SCOPE),
        "confirmed": True,
        "gate": gate,
        **changes,
    }
    return p.confirm_content_source_import(
        actor,
        confirmation_id,
        **kwargs,
    )


def test_account_shared_import_prepare_confirm_and_check_use_the_exact_private_grant(
    monkeypatch,
):
    account = _account_permission(monkeypatch)
    actor = _actor()
    gate = _gate()
    upload = _upload(actor, gate)

    assert upload.actor_id == 23
    assert upload.domain_id is None
    assert upload.subject_id is None and upload.brand_focus_id is None
    assert upload.global_scope is False
    assert upload.scope_kind == "shared_workspace" and upload.scope_version == 1
    assert upload.principal_kind is None and upload.principal_ref is None
    assert not gate._approvals and not gate._content_import_grants

    pending = _prepare(actor, upload, gate)
    assert pending["allowed"]
    assert pending["code"] == "CONTENT_SOURCE_CONFIRMATION_PENDING"
    assert pending["resource"].startswith(
        "content-source-import:shared-workspace:v1:"
    )
    assert "approval_token" not in pending
    assert not p.check_content_source_import_permission(actor, upload, gate=gate).allowed

    confirmed = _confirm(actor, pending["confirmation_id"], gate)
    assert confirmed.allowed and confirmed.approval_token is None
    assert confirmed.code == "CONTENT_SOURCE_IMPORT_ALLOWED"
    assert confirmed.domain_id is None and confirmed.global_scope is False
    assert confirmed.caller == "actor:23"
    assert not gate.has_permission(p.PermissionLevel.COMMIT)

    receipt = p.check_content_source_import_permission(actor, upload, gate=gate)
    assert receipt.allowed and receipt.approval_token is None
    assert receipt.resource == pending["resource"]
    assert receipt.caller == "actor:23"
    assert receipt.permission_required == p.PermissionLevel.COMMIT.value
    assert account["scope_calls"]
    assert all(call[1:4] == ("SHARED", "content", "write") for call in account["scope_calls"])


@contextmanager
def _local_request(app):
    with app.test_request_context(
        "/",
        headers={"Host": "localhost"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ):
        yield


def test_local_workspace_shared_import_prepare_confirm_and_check_remain_bound():
    """The request context below is an isolated principal callback fixture."""
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    gate = _gate()

    with _local_request(app):
        principal = p.resolve_local_workspace_principal(
            module="content", action="write",
        )
        assert type(principal) is p.LocalWorkspacePrincipal
        upload = p.make_shared_content_source_import(
            None,
            dict(SCOPE),
            filename="local.txt",
            size_bytes=len(BODY),
            body_sha256=hashlib.sha256(BODY).hexdigest(),
            principal=principal,
            gate=gate,
        )
        assert upload.actor_id is None
        assert upload.principal_kind == "local_workspace"
        assert upload.principal_ref == "workspace:local"

        pending = p.prepare_content_source_import_confirmation(
            None, upload, principal=principal, gate=gate,
        )
        assert pending["allowed"]
        assert pending["resource"].startswith(
            "content-source-import:shared-workspace:v1:"
        )
        confirmed = p.confirm_content_source_import(
            None,
            pending["confirmation_id"],
            domain_id=None,
            workspace_scope=dict(SCOPE),
            confirmed=True,
            principal=principal,
            gate=gate,
        )
        assert confirmed.allowed and confirmed.approval_token is None
        assert confirmed.caller == "workspace:local"

        checked = p.check_content_source_import_permission(
            None, upload, principal=principal, gate=gate,
        )
        assert checked.allowed and checked.resource == pending["resource"]
        assert checked.principal_kind == "local_workspace"
        assert checked.principal_ref == "workspace:local"


def test_local_workspace_shared_import_needs_a_current_server_principal():
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    gate = _gate()

    with _local_request(app):
        principal = p.resolve_local_workspace_principal(
            module="content", action="write",
        )
        assert type(principal) is p.LocalWorkspacePrincipal
        upload = p.make_shared_content_source_import(
            None,
            dict(SCOPE),
            filename="local-current.txt",
            size_bytes=len(BODY),
            body_sha256=hashlib.sha256(BODY).hexdigest(),
            principal=principal,
            gate=gate,
        )
        pending = p.prepare_content_source_import_confirmation(
            None, upload, principal=principal, gate=gate,
        )
        assert pending["allowed"]
        assert p.confirm_content_source_import(
            None,
            pending["confirmation_id"],
            domain_id=None,
            workspace_scope=dict(SCOPE),
            confirmed=True,
            principal=principal,
            gate=gate,
        ).allowed
        assert p.check_content_source_import_permission(
            None, upload, principal=principal, gate=gate,
        ).allowed
        pending_for_reauthorization = p.prepare_content_source_import_confirmation(
            None, upload, principal=principal, gate=gate,
        )
        assert pending_for_reauthorization["allowed"]

    unavailable_prepare = p.prepare_content_source_import_confirmation(
        None, upload, gate=gate,
    )
    assert not unavailable_prepare["allowed"]
    assert unavailable_prepare["code"] == "CONTENT_SOURCE_PERMISSION_UNAVAILABLE"
    assert unavailable_prepare["verification_state"] == "unavailable"

    unavailable_confirmation = p.confirm_content_source_import(
        None,
        pending_for_reauthorization["confirmation_id"],
        domain_id=None,
        workspace_scope=dict(SCOPE),
        confirmed=True,
        gate=gate,
    )
    assert not unavailable_confirmation.allowed
    assert unavailable_confirmation.code == "CONTENT_SOURCE_CONFIRMATION_INVALID"
    assert unavailable_confirmation.verification_state == "unavailable"

    missing = p.check_content_source_import_permission(None, upload, gate=gate)
    assert not missing.allowed
    assert missing.code == "CONTENT_SOURCE_PERMISSION_UNAVAILABLE"
    assert missing.verification_state == "unavailable"

    serialized = {
        "principal_kind": "local_workspace",
        "principal_ref": "workspace:local",
        "actor_id": None,
    }
    forged = p.check_content_source_import_permission(
        None, upload, principal=serialized, gate=gate,
    )
    assert not forged.allowed
    assert forged.code == "CONTENT_SOURCE_PERMISSION_UNAVAILABLE"
    assert forged.verification_state == "unavailable"

    with _local_request(app):
        current_principal = p.resolve_local_workspace_principal(
            module="content", action="write",
        )
        recovered = p.confirm_content_source_import(
            None,
            pending_for_reauthorization["confirmation_id"],
            domain_id=None,
            workspace_scope=dict(SCOPE),
            confirmed=True,
            principal=current_principal,
            gate=gate,
        )
        assert recovered.allowed


@pytest.mark.parametrize(
    "wire",
    [
        {"scope_kind": "shared_workspace", "version": True},
        {"scope_kind": "shared_workspace", "version": 1.0},
        {"scope_kind": "shared_workspace", "version": 1, "domain_id": "cth"},
    ],
)
def test_shared_descriptor_rejects_mixed_or_nonliteral_scope_wire(monkeypatch, wire):
    _account_permission(monkeypatch)
    with pytest.raises(ValueError, match="SHARED_WORKSPACE_SCOPE_INVALID"):
        p.make_shared_content_source_import(
            _actor(),
            wire,
            filename="draft.txt",
            size_bytes=len(BODY),
            body_sha256=hashlib.sha256(BODY).hexdigest(),
            gate=_gate(),
        )


def test_confirmation_rejects_mixed_domain_and_boolean_coercion_without_consuming_nonce(
    monkeypatch,
):
    _account_permission(monkeypatch)
    actor = _actor()
    gate = _gate()
    upload = _upload(actor, gate)
    pending = _prepare(actor, upload, gate)

    mixed = p.confirm_content_source_import(
        actor,
        pending["confirmation_id"],
        workspace_scope=dict(SCOPE),
        domain_id="cth",
        confirmed=True,
        gate=gate,
    )
    assert not mixed.allowed and mixed.code == "CONTENT_SOURCE_SCOPE_MISMATCH"
    assert not gate._approvals and not gate._content_import_grants

    malformed = replace(upload, scope_version=True)
    assert p._content_source_descriptor_kind(malformed) == "invalid"
    malformed_result = p.check_content_source_import_permission(
        actor, malformed, gate=gate,
    )
    assert not malformed_result.allowed
    malformed_boolean = replace(upload, global_scope=0)
    assert p._content_source_descriptor_kind(malformed_boolean) == "invalid"
    assert not p.check_content_source_import_permission(
        actor, malformed_boolean, gate=gate,
    ).allowed

    resumed = _confirm(actor, pending["confirmation_id"], gate)
    assert resumed.allowed


def test_identity_body_and_scope_are_bound_to_the_prepared_import(monkeypatch):
    _account_permission(monkeypatch)
    actor = _actor()
    gate = _gate()
    upload = _upload(actor, gate)
    pending = _prepare(actor, upload, gate)
    assert _confirm(actor, pending["confirmation_id"], gate).allowed

    wrong_actor = p.check_content_source_import_permission(
        _actor(24), upload, gate=gate,
    )
    assert not wrong_actor.allowed
    assert wrong_actor.code == "CONTENT_SOURCE_ACTOR_MISMATCH"

    changed_bytes = replace(
        upload,
        body_sha256=hashlib.sha256(b"different permitted bytes").hexdigest(),
    )
    changed_result = p.check_content_source_import_permission(
        actor, changed_bytes, gate=gate,
    )
    assert not changed_result.allowed
    assert p.check_content_source_import_permission(actor, upload, gate=gate).allowed

    mixed_scope = replace(upload, scope_kind="cth")
    assert not p.check_content_source_import_permission(
        actor, mixed_scope, gate=gate,
    ).allowed


def test_decline_is_terminal_for_its_owner_but_cannot_cancel_another_actor_nonce(
    monkeypatch,
):
    _account_permission(monkeypatch)
    actor = _actor()
    gate = _gate()
    upload = _upload(actor, gate)

    borrowed = _prepare(actor, upload, gate)
    wrong_actor_decline = p.confirm_content_source_import(
        _actor(24), borrowed["confirmation_id"], domain_id=None,
        workspace_scope=dict(SCOPE), confirmed=False, gate=gate,
    )
    assert not wrong_actor_decline.allowed
    assert gate._content_import_confirmations[
        borrowed["confirmation_id"]
    ].state == "pending"
    assert _confirm(actor, borrowed["confirmation_id"], gate).allowed
    existing_grants = set(gate._content_import_grants)

    declined = _prepare(actor, upload, gate)
    denial = p.confirm_content_source_import(
        actor, declined["confirmation_id"], domain_id=None,
        workspace_scope=dict(SCOPE), confirmed=False, gate=gate,
    )
    assert not denial.allowed and denial.code == "CONTENT_SOURCE_CONFIRMATION_DECLINED"
    assert gate._content_import_confirmations[declined["confirmation_id"]].state == "declined"
    retry = _confirm(actor, declined["confirmation_id"], gate)
    assert not retry.allowed and retry.code == "CONTENT_SOURCE_CONFIRMATION_NOT_PENDING"
    assert set(gate._content_import_grants) == existing_grants


def test_cancel_requires_exact_shared_scope_and_revokes_only_the_selected_upload(
    monkeypatch,
):
    _account_permission(monkeypatch)
    actor = _actor()
    gate = _gate()
    upload_a = _upload(actor, gate, body=b"first")
    upload_b = _upload(actor, gate, body=b"second")
    pending_a = _prepare(actor, upload_a, gate)
    pending_b = _prepare(actor, upload_b, gate)
    assert _confirm(actor, pending_b["confirmation_id"], gate).allowed

    assert not p.cancel_content_source_import_confirmation(
        _actor(24), pending_a["confirmation_id"], dict(SCOPE), gate=gate,
    )
    assert not p.cancel_content_source_import_confirmation(
        actor,
        pending_a["confirmation_id"],
        {"scope_kind": "shared_workspace", "version": True},
        gate=gate,
    )
    assert p.cancel_content_source_import_confirmation(
        actor, pending_a["confirmation_id"], dict(SCOPE), gate=gate,
    )
    assert not p.check_content_source_import_permission(actor, upload_a, gate=gate).allowed
    assert p.check_content_source_import_permission(actor, upload_b, gate=gate).allowed


@pytest.mark.parametrize("stage", ["confirmation", "grant", "approval"])
def test_expired_shared_confirmation_or_grant_never_authorizes(monkeypatch, stage):
    _account_permission(monkeypatch)
    actor = _actor()
    gate = _gate()
    upload = _upload(actor, gate)
    pending = _prepare(actor, upload, gate)

    if stage == "confirmation":
        gate._content_import_confirmations[pending["confirmation_id"]].expires_at = (
            _local_now_naive() - timedelta(seconds=1)
        )
        result = _confirm(actor, pending["confirmation_id"], gate)
        assert not result.allowed
        assert pending["confirmation_id"] not in gate._content_import_confirmations
        return

    assert _confirm(actor, pending["confirmation_id"], gate).allowed
    token = next(iter(gate._content_import_grants))
    if stage == "grant":
        gate._content_import_grants[token].expires_at = _local_now_naive() - timedelta(seconds=1)
    else:
        gate._approvals[token].expires_at = _local_now_naive() - timedelta(seconds=1)
    assert not p.check_content_source_import_permission(actor, upload, gate=gate).allowed
    gate._prune_content_source_import_state()
    assert token not in gate._content_import_grants
    assert gate._approvals[token].revoked
    assert not gate._approval_token_is_valid(
        token, p.OperationType.DB_WRITE.value, pending["resource"],
    )


def test_account_revocation_cancels_exact_grant_and_new_confirmation_recovers(monkeypatch):
    account = _account_permission(monkeypatch)
    actor = _actor()
    gate = _gate()
    upload = _upload(actor, gate)
    first = _prepare(actor, upload, gate)
    assert _confirm(actor, first["confirmation_id"], gate).allowed
    token = next(iter(gate._content_import_grants))

    account["active"] = False
    denied = p.check_content_source_import_permission(actor, upload, gate=gate)
    assert not denied.allowed
    assert gate._content_import_confirmations[first["confirmation_id"]].state == "cancelled"
    assert token not in gate._content_import_grants
    assert not gate._approval_token_is_valid(
        token, p.OperationType.DB_WRITE.value, denied.resource,
    )

    account["active"] = True
    assert not p.check_content_source_import_permission(actor, upload, gate=gate).allowed
    second = _prepare(actor, upload, gate)
    assert second["allowed"] and second["confirmation_id"] != first["confirmation_id"]
    assert _confirm(actor, second["confirmation_id"], gate).allowed
    assert p.check_content_source_import_permission(actor, upload, gate=gate).allowed


def _shared_admission(actor, gate):
    context = p.authorize_shared_workspace(
        actor, dict(SCOPE), module="content", action="write", gate=gate,
    )
    return p._issue_shared_workspace_gate_admission(
        gate,
        actor,
        dict(SCOPE),
        module="content",
        action="write",
        authorized_context=context,
    )


def test_generic_approval_data_import_and_other_gate_cannot_borrow_shared_grant(
    monkeypatch,
):
    _account_permission(monkeypatch)
    actor = _actor()
    gate = _gate()
    upload = _upload(actor, gate)
    pending = _prepare(actor, upload, gate)
    scope, _ = p._shared_content_source_scope_receipt(
        actor, dict(SCOPE), principal=None, gate=gate,
    )
    admission = _shared_admission(actor, gate)
    generic = gate.grant_approval(
        p.OperationType.DB_WRITE.value,
        duration_minutes=1,
        resource=pending["resource"],
        granted_by="actor:23",
    )

    generic_result = gate.check(
        p.OperationType.DB_WRITE,
        resource=pending["resource"],
        risk_level=p.RiskLevel.HIGH,
        caller=scope.caller,
        exact_approval_required=True,
        content_import_grant=generic,
        _shared_workspace_admission=admission,
    )
    assert not generic_result.allowed
    imported_as_data = gate.check(
        p.OperationType.DATA_IMPORT,
        resource=pending["resource"],
        caller=scope.caller,
        exact_approval_required=True,
        content_import_grant=generic,
        _shared_workspace_admission=admission,
    )
    assert not imported_as_data.allowed
    assert not p.check_content_source_import_permission(actor, upload, gate=gate).allowed

    assert _confirm(actor, pending["confirmation_id"], gate).allowed
    token = next(iter(gate._content_import_grants))
    other_gate = _gate()
    other_admission = _shared_admission(actor, other_gate)
    borrowed_source_reference = gate.check(
        p.OperationType.DB_WRITE,
        resource=pending["resource"],
        risk_level=p.RiskLevel.HIGH,
        caller=scope.caller,
        exact_approval_required=True,
        content_import_grant=token,
        source_reference_grant="not-a-shared-content-grant",
        _shared_workspace_admission=admission,
    )
    assert not borrowed_source_reference.allowed
    borrowed = other_gate.check(
        p.OperationType.DB_WRITE,
        resource=pending["resource"],
        risk_level=p.RiskLevel.HIGH,
        caller=scope.caller,
        exact_approval_required=True,
        content_import_grant=token,
        _shared_workspace_admission=other_admission,
    )
    assert not borrowed.allowed
    cross_gate_admission = gate.check(
        p.OperationType.DB_WRITE,
        resource=pending["resource"],
        risk_level=p.RiskLevel.HIGH,
        caller=scope.caller,
        exact_approval_required=True,
        content_import_grant=token,
        _shared_workspace_admission=other_admission,
    )
    assert not cross_gate_admission.allowed
    assert not p.check_content_source_import_permission(
        actor, upload, gate=other_gate,
    ).allowed
    assert other_gate._content_import_grants == {}
    assert p.check_content_source_import_permission(actor, upload, gate=gate).allowed


def test_shared_import_reauthorization_ignores_operation_id_cache(monkeypatch):
    account = _account_permission(monkeypatch)
    actor = _actor()
    gate = _gate()
    upload = _upload(actor, gate)
    pending = _prepare(actor, upload, gate)
    assert _confirm(actor, pending["confirmation_id"], gate).allowed
    token = next(iter(gate._content_import_grants))
    admission = _shared_admission(actor, gate)

    args = {
        "operation_type": p.OperationType.DB_WRITE,
        "resource": pending["resource"],
        "risk_level": p.RiskLevel.HIGH,
        "caller": "actor:23",
        "operation_id": "shared-content-import-recheck",
        "exact_approval_required": True,
        "content_import_grant": token,
        "_shared_workspace_admission": admission,
    }
    first = gate.check(**args)
    assert first.allowed and not first.idempotent_hit
    assert "shared-content-import-recheck" not in gate._idempotency_cache

    account["active"] = False
    second = gate.check(**args)
    assert not second.allowed and not second.idempotent_hit
    assert "shared-content-import-recheck" not in gate._idempotency_cache


def test_testing_bypass_cannot_prepare_confirm_or_use_shared_import(monkeypatch):
    _account_permission(monkeypatch)
    actor = _actor()
    gate = _gate()
    upload = _upload(actor, gate)
    issued_pending = _prepare(actor, upload, gate)
    assert issued_pending["allowed"]
    assert _confirm(actor, issued_pending["confirmation_id"], gate).allowed
    token = next(iter(gate._content_import_grants))
    scope, _ = p._shared_content_source_scope_receipt(
        actor, dict(SCOPE), principal=None, gate=gate,
    )
    admission = _shared_admission(actor, gate)
    direct_args = {
        "operation_type": p.OperationType.DB_WRITE,
        "resource": issued_pending["resource"],
        "risk_level": p.RiskLevel.HIGH,
        "caller": scope.caller,
        "exact_approval_required": True,
        "content_import_grant": token,
        "_shared_workspace_admission": admission,
    }
    assert gate.check(**direct_args).allowed
    pending = _prepare(actor, upload, gate)
    assert pending["allowed"]
    approvals_before_bypass = set(gate._approvals)

    p.set_testing_bypass(True)
    assert not _prepare(actor, upload, gate)["allowed"]
    bypassed_direct = gate.check(**direct_args)
    assert not bypassed_direct.allowed
    assert bypassed_direct.reason == "CONTENT_SOURCE_TESTING_BYPASS_FORBIDDEN"
    assert not p.check_content_source_import_permission(actor, upload, gate=gate).allowed
    denied = _confirm(actor, pending["confirmation_id"], gate)
    assert not denied.allowed
    assert not gate._content_import_grants
    assert set(gate._approvals) == approvals_before_bypass


def test_legacy_descriptor_defaults_and_resource_hash_remain_unchanged(monkeypatch):
    monkeypatch.setattr(p, "_actor_has_scope_action", lambda *args, **kwargs: True)
    monkeypatch.setattr(p, "_load_actor_scope_role", lambda *args, **kwargs: "admin")
    monkeypatch.setattr(p, "_registered_resource_scope_exists", lambda *args, **kwargs: True)
    gate = p.PermissionGate()
    upload = p.ContentSourceImport(
        actor_id=1,
        domain_id="bmp",
        subject_id=None,
        brand_focus_id="brand-a",
        global_scope=False,
        filename="source.mp4",
        size_bytes=3,
        body_sha256=hashlib.sha256(b"abc").hexdigest(),
    )
    assert upload.scope_kind is None and upload.scope_version is None
    scope = p.check_actor_scope_permission(
        {"id": 1},
        domain_id="bmp",
        action="write",
        module="content",
        brand_focus_id="brand-a",
        gate=gate,
    )
    assert p.content_source_import_resource(scope, upload, gate=gate) == (
        "content-source-import:v1:75dd3fdb4d04fffa2115a89d0d936bd1fb2b4175a2a5c8d542a728ca05498698"
    )
