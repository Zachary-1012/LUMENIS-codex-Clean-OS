from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask

from account import authorization
from lumenis.system.security import permission as p

SCOPE = {"scope_kind": "shared_workspace", "version": 1}


@pytest.fixture(autouse=True)
def strict_permission_mode(monkeypatch):
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    previous = p._TESTING_BYPASS_ENABLED
    p.set_testing_bypass(False)
    yield
    p.set_testing_bypass(previous)


def _gate(*, commit=False):
    levels = {
        p.PermissionLevel.READ,
        p.PermissionLevel.AUDIT,
        p.PermissionLevel.ANALYZE,
        p.PermissionLevel.RESEARCH,
        p.PermissionLevel.PLAN,
        p.PermissionLevel.PATCH_PREVIEW,
        p.PermissionLevel.TEST,
        p.PermissionLevel.VERIFY,
    }
    if commit:
        levels.add(p.PermissionLevel.COMMIT)
    return p.PermissionGate(enabled_permissions=levels)


def _account(monkeypatch, *, allowed=True, role="user", grants=()):
    state = {
        "allowed": allowed,
        "role": role,
        "grants": [dict(grant) for grant in grants],
        "calls": [],
        "role_calls": [],
        "grant_calls": [],
    }

    def has_scope(actor_id, product_id, module, action, *, connection=None):
        state["calls"].append(
            (actor_id, product_id, module, action, connection)
        )
        return state["allowed"]

    def load_role(actor_id, *, connection=None):
        state.setdefault("role_calls", []).append((actor_id, connection))
        return state["role"]

    def load_grants(actor_id, *, connection=None):
        state.setdefault("grant_calls", []).append((actor_id, connection))
        return [dict(grant) for grant in state["grants"]]

    monkeypatch.setattr(p, "_actor_has_scope_action", has_scope)
    monkeypatch.setattr(p, "_load_actor_scope_role", load_role)
    monkeypatch.setattr(p, "_load_actor_scope_grants", load_grants)
    return state


def _grant(*, product="SHARED", module="content", action="write",
           data_scope=None, time_range=None):
    return {
        "product_id": product,
        "module": module,
        "action": action,
        "data_scope": data_scope,
        "time_range": time_range,
    }


def _app():
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    return app


@contextmanager
def _request(app, *, host="localhost", origin=None, remote_addr="127.0.0.1",
             headers=None):
    request_headers = {"Host": host}
    if origin is not None:
        request_headers["Origin"] = origin
    if headers:
        request_headers.update(headers)
    with app.test_request_context(
        "/",
        headers=request_headers,
        environ_overrides={"REMOTE_ADDR": remote_addr},
    ):
        yield


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {"scope_kind": "shared_workspace"},
        {"scope_kind": "shared_workspace", "version": True},
        {"scope_kind": "shared_workspace", "version": 1.0},
        {"scope_kind": "shared_workspace", "version": 2},
        {"scope_kind": "cth", "version": 1},
        {"scope_kind": "shared_workspace", "version": 1, "actor_id": 9},
        {"scope_kind": "shared_workspace", "version": 1, "domain_id": "cth"},
        {"scope_kind": "shared_workspace", "version": 1, "project_id": "p1"},
        {"scope_kind": "shared_workspace", "version": 1, "workspace_id": "w1"},
    ],
)
def test_scope_wire_accepts_only_the_exact_versioned_discriminator(value):
    with pytest.raises(ValueError, match="SHARED_WORKSPACE_SCOPE_INVALID"):
        p.validate_shared_workspace_scope(value)
    assert p.validate_shared_workspace_scope(dict(SCOPE)) == SCOPE


def test_account_admission_uses_active_server_role_and_shared_module_action(
    monkeypatch,
):
    connection = object()
    state = _account(
        monkeypatch,
        role="user",
        grants=[_grant(module="*", action="write")],
    )
    gate = _gate()
    context = p.authorize_shared_workspace(
        {"id": 23, "role": "owner"}, SCOPE,
        module="content", action="write", connection=connection, gate=gate,
    )
    assert context == {**SCOPE, "actor_id": 23}
    assert state["calls"] == [
        (23, "SHARED", "content", "write", connection),
    ]
    assert state["role_calls"] == [(23, connection)]
    assert state["grant_calls"] == [(23, connection)]
    audits = gate.get_audit_log(
        operation_type="shared_workspace_scope_write",
        result_filter="allowed",
    )
    assert len(audits) == 1
    assert audits[0]["caller"] == "actor:23"
    assert audits[0]["permission_required"] == "SHARED/content:write"


@pytest.mark.parametrize("role", ["owner", "admin"])
def test_active_server_owner_and_admin_can_open_shared_workspace_without_member_grant(
    monkeypatch, role,
):
    state = _account(monkeypatch, role=role, grants=[])
    context = p.authorize_shared_workspace(
        {"id": 23, "role": "user"}, SCOPE,
        module="reports", action="read", gate=_gate(),
    )
    assert context == {**SCOPE, "actor_id": 23}
    assert state["grant_calls"] == []


def test_client_owner_role_cannot_replace_missing_server_member_grant(monkeypatch):
    state = _account(monkeypatch, role="user", grants=[])
    gate = _gate()
    with pytest.raises(PermissionError, match="SHARED_WORKSPACE_ACCESS_DENIED"):
        p.authorize_shared_workspace(
            {"id": 23, "role": "owner"}, SCOPE,
            module="content", action="write", gate=gate,
        )
    assert state["calls"][0][1:4] == ("SHARED", "content", "write")
    assert gate.get_audit_log(
        operation_type="shared_workspace_scope_write",
        result_filter="denied",
    )


@pytest.mark.parametrize(
    "grant",
    [
        _grant(product="CTH"),
        _grant(module="reports", action="write"),
        _grant(module="content", action="read"),
        _grant(data_scope={"global": True}),
        _grant(time_range="last_30_days"),
    ],
)
def test_member_requires_matching_unscoped_shared_grant(monkeypatch, grant):
    _account(monkeypatch, role="user", grants=[grant])
    with pytest.raises(PermissionError, match="SHARED_WORKSPACE_ACCESS_DENIED"):
        p.authorize_shared_workspace(
            {"id": 31, "role": "admin"}, SCOPE,
            module="content", action="write", gate=_gate(),
        )


def test_account_status_and_unknown_server_role_fail_closed(monkeypatch):
    state = _account(monkeypatch, allowed=False, role="user", grants=[_grant()])
    with pytest.raises(PermissionError, match="SHARED_WORKSPACE_ACCESS_DENIED"):
        p.authorize_shared_workspace(
            {"id": 31}, SCOPE, module="content", action="write", gate=_gate(),
        )
    assert state["grant_calls"] == []

    _account(monkeypatch, allowed=True, role="suspended", grants=[_grant()])
    with pytest.raises(PermissionError, match="SHARED_WORKSPACE_PERMISSION_UNAVAILABLE"):
        p.authorize_shared_workspace(
            {"id": 31}, SCOPE, module="content", action="write", gate=_gate(),
        )


@pytest.mark.parametrize("actor", [None, {}, {"id": 0}, {"id": True}, {"role": "owner"}])
def test_missing_or_invalid_server_actor_never_uses_claimed_role(monkeypatch, actor):
    state = _account(monkeypatch, role="owner")
    gate = _gate()
    with pytest.raises(PermissionError, match="SHARED_WORKSPACE_ACCESS_DENIED"):
        p.authorize_shared_workspace(
            actor, SCOPE, module="content", action="write", gate=gate,
        )
    assert state["calls"] == []
    assert gate.get_audit_log(
        operation_type="shared_workspace_scope_write",
        result_filter="denied",
    )


@pytest.mark.parametrize(
    "module,action",
    [
        ("collector", "read"),
        ("content", "export"),
        ("reports", "delete"),
        ("*", "write"),
    ],
)
def test_invalid_module_or_action_is_audited_and_never_uses_account_scope(
    monkeypatch, module, action,
):
    state = _account(monkeypatch, role="owner")
    gate = _gate()
    with pytest.raises(PermissionError, match="SHARED_WORKSPACE_REQUEST_INVALID"):
        p.authorize_shared_workspace(
            {"id": 31}, SCOPE,
            module=module, action=action, gate=gate,
        )
    assert state["calls"] == []
    audit_operation = (
        f"shared_workspace_scope_{action}"
        if action in {"read", "write"}
        else "shared_workspace_scope_invalid"
    )
    assert gate.get_audit_log(
        operation_type=audit_operation, result_filter="denied",
    )


def test_local_workspace_admission_requires_live_loopback_transport_and_sealed_actor():
    app = _app()
    gate = _gate()
    with _request(app):
        principal = p.resolve_local_workspace_principal(
            module="content", action="write",
        )
        assert type(principal) is p.LocalWorkspacePrincipal
        context = p.authorize_shared_workspace(
            principal, SCOPE, module="content", action="write", gate=gate,
        )
        assert context == {
            **SCOPE,
            "principal_kind": "local_workspace",
            "principal_ref": "workspace:local",
        }
        with pytest.raises(PermissionError, match="SHARED_WORKSPACE_ACCESS_DENIED"):
            p.authorize_shared_workspace(
                {
                    "principal_kind": "local_workspace",
                    "principal_ref": "workspace:local",
                    "actor_id": None,
                },
                SCOPE, module="content", action="write", gate=gate,
            )

    with _request(app, origin="https://example.com"), pytest.raises(
        PermissionError, match="SHARED_WORKSPACE_WORKSPACE_UNAVAILABLE",
    ):
        p.authorize_shared_workspace(
            principal, SCOPE, module="content", action="write", gate=gate,
        )


def test_audit_failure_makes_workspace_admission_unavailable(monkeypatch):
    _account(monkeypatch, role="owner")
    gate = _gate()

    def fail_audit(*args, **kwargs):
        raise OSError("audit unavailable")

    monkeypatch.setattr(gate, "_write_audit", fail_audit)
    with pytest.raises(PermissionError, match="SHARED_WORKSPACE_AUDIT_UNAVAILABLE"):
        p.authorize_shared_workspace(
            {"id": 4}, SCOPE, module="reports", action="read", gate=gate,
        )


def test_shared_db_write_keeps_commit_and_exact_manual_approval_requirements(
    monkeypatch,
):
    _account(monkeypatch, role="owner")
    gate = _gate(commit=True)
    resource = "SHARED:shared_workspace:content:document-7"
    denied = p.check_shared_workspace_effect(
        {"id": 4}, SCOPE, p.OperationType.DB_WRITE, resource,
        module="content", action="write", gate=gate,
    )
    assert not denied.allowed
    assert denied.requires_approval is True
    assert denied.approval_token is None
    assert denied.permission_required == p.PermissionLevel.COMMIT.value
    assert denied.operation_id is None

    token = gate.grant_approval(
        p.OperationType.DB_WRITE.value, resource=resource, granted_by="test-human",
    )
    approved = p.check_shared_workspace_effect(
        {"id": 4}, SCOPE, p.OperationType.DB_WRITE, resource,
        module="content", action="write", gate=gate,
    )
    assert approved.allowed
    assert approved.approval_token == token


@pytest.mark.parametrize(
    "operation,action",
    [
        (p.OperationType.DATA_EXPORT, "write"),
        (p.OperationType.DB_WRITE, "read"),
        (p.OperationType.DATA_IMPORT, "read"),
        (p.OperationType.REPORT_GENERATE, "read"),
        (p.OperationType.COLLECTOR_START, "write"),
        (p.OperationType.MODEL_TRAIN, "write"),
        (p.OperationType.BROWSER_OPERATION, "write"),
    ],
)
def test_operation_module_and_action_must_match_the_shared_effect_arm(
    monkeypatch, operation, action,
):
    _account(monkeypatch, role="owner")
    result = p.check_shared_workspace_effect(
        {"id": 4}, SCOPE, operation, "SHARED:shared_workspace:content:item",
        module="content", action=action, gate=_gate(commit=True),
    )
    assert not result.allowed
    assert result.domain_id is None


def test_gate_reauthorizes_revocation_and_disables_private_arm_idempotency(
    monkeypatch,
):
    state = _account(monkeypatch, role="owner")
    actor = {"id": 19}
    gate = _gate(commit=True)
    resource = "SHARED:shared_workspace:content:document-19"
    p.authorize_shared_workspace(
        actor, SCOPE, module="content", action="write", gate=gate,
    )
    admission = p._issue_shared_workspace_gate_admission(
        gate, actor, SCOPE, module="content", action="write",
        authorized_context={**SCOPE, "actor_id": 19},
    )
    token = gate.grant_approval(
        p.OperationType.DB_WRITE.value, resource=resource, granted_by="test-human",
    )
    first = gate.check(
        p.OperationType.DB_WRITE,
        resource=resource,
        caller="actor:19",
        operation_id="replayed-operation",
        _shared_workspace_admission=admission,
    )
    assert first.allowed and first.approval_token == token
    assert first.operation_id is None and not first.idempotent_hit

    state["allowed"] = False
    second = gate.check(
        p.OperationType.DB_WRITE,
        resource=resource,
        caller="actor:19",
        operation_id="replayed-operation",
        _shared_workspace_admission=admission,
    )
    assert not second.allowed and not second.idempotent_hit
    assert second.domain_id is None
    assert len(state["calls"]) == 3


def test_gate_rejects_borrowed_mixed_or_cross_gate_private_admission(monkeypatch):
    _account(monkeypatch, role="owner")
    gate = _gate(commit=True)
    actor = {"id": 19}
    context = p.authorize_shared_workspace(
        actor, SCOPE, module="content", action="write", gate=gate,
    )
    admission = p._issue_shared_workspace_gate_admission(
        gate, actor, SCOPE, module="content", action="write",
        authorized_context=context,
    )
    resource = "SHARED:shared_workspace:content:document-19"

    for target_gate, kwargs in (
        (p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT}), {}),
        (gate, {"caller": "actor:20"}),
        (gate, {"domain_id": "cth"}),
        (gate, {"role": "cth_admin"}),
        (gate, {"content_import_grant": "claimed"}),
        (gate, {"source_reference_grant": "claimed"}),
        (gate, {"risk_level": p.RiskLevel.LOW}),
    ):
        target_gate._current_check_domain = "cth"
        call_kwargs = {"caller": "actor:19", **kwargs}
        result = target_gate.check(
            p.OperationType.DB_WRITE,
            resource=resource,
            _shared_workspace_admission=admission,
            **call_kwargs,
        )
        assert not result.allowed
        assert result.domain_id is None
        assert not result.idempotent_hit


def test_confirmed_source_reference_grant_stays_on_its_original_domain_arm(
    monkeypatch,
):
    _account(monkeypatch, role="owner")
    gate = _gate(commit=True)
    actor = {"id": 19}
    caller = "actor:19"
    descriptor_sha256 = "a" * 64
    resource = p._APPROVED_SOURCE_REFERENCE_RESOURCE_PREFIX + descriptor_sha256
    token = gate.grant_approval(
        p.OperationType.DATA_IMPORT.value,
        resource=resource,
        granted_by="test-human",
    )
    confirmation_id = "confirmed-source-reference"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    gate._approved_source_reference_grants[token] = (
        p._ApprovedSourceReferenceGrant(
            token=token,
            confirmation_id=confirmation_id,
            caller=caller,
            resource=resource,
            descriptor_sha256=descriptor_sha256,
            expires_at=expires_at,
        )
    )
    gate._approved_source_reference_confirmations[confirmation_id] = (
        p._ApprovedSourceReferenceConfirmation(
            confirmation_id=confirmation_id,
            request={},
            scope={},
            context={},
            caller=caller,
            resource=resource,
            descriptor_sha256=descriptor_sha256,
            body_sha256=descriptor_sha256,
            receipt_descriptor_sha256=descriptor_sha256,
            expires_at=expires_at,
            state="confirmed",
            approval_token=token,
            grant_expires_at=expires_at,
        )
    )
    assert gate._approved_source_reference_grant_is_valid(
        token,
        p.OperationType.DATA_IMPORT,
        resource,
        caller,
        descriptor_sha256,
    )

    original_path = gate.check(
        p.OperationType.DATA_IMPORT,
        resource=resource,
        caller=caller,
        domain_id="cth",
        source_reference_grant=token,
    )
    assert original_path.allowed
    assert original_path.domain_id == "cth"

    context = p.authorize_shared_workspace(
        actor, SCOPE, module="content", action="write", gate=gate,
    )
    admission = p._issue_shared_workspace_gate_admission(
        gate, actor, SCOPE, module="content", action="write",
        authorized_context=context,
    )
    mixed_path = gate.check(
        p.OperationType.DATA_IMPORT,
        resource=resource,
        caller=caller,
        source_reference_grant=token,
        _shared_workspace_admission=admission,
    )
    assert not mixed_path.allowed
    assert mixed_path.reason == "SHARED_WORKSPACE_MIXED_PERMISSION_SCOPE"
    assert mixed_path.domain_id is None


def test_testing_bypass_does_not_bypass_shared_commit_or_approval(monkeypatch):
    _account(monkeypatch, role="owner")
    gate = _gate(commit=True)
    p.set_testing_bypass(True)
    result = p.check_shared_workspace_effect(
        {"id": 4}, SCOPE, p.OperationType.DB_WRITE,
        "SHARED:shared_workspace:content:document-7",
        module="content", action="write", gate=gate,
    )
    assert not result.allowed
    assert result.requires_approval


def test_shared_arm_does_not_change_legacy_domain_permission_behavior(monkeypatch):
    _account(monkeypatch, role="owner")
    gate = _gate()
    shared = p.check_shared_workspace_effect(
        {"id": 4}, SCOPE, p.OperationType.DATA_EXPORT,
        "SHARED:shared_workspace:reports:report-3",
        module="reports", action="read", gate=gate,
    )
    assert shared.allowed and shared.domain_id is None

    legacy = gate.check(
        p.OperationType.DATA_EXPORT,
        resource="cth:legacy-export",
        domain_id="cth",
    )
    assert legacy.allowed
    assert legacy.domain_id == "cth"


def test_account_writer_allows_only_explicit_shared_product_label():
    assert set(authorization.VALID_PRODUCTS) == {"ZBMP", "CTH", "SYSTEM", "SHARED"}
