from contextlib import contextmanager

import pytest
from flask import Flask

from lumenis.system.security import permission as p


@pytest.fixture
def app():
    value = Flask(__name__)
    value.config["LUMENIS_OPEN_WORKSPACE"] = True
    return value


@pytest.fixture(autouse=True)
def strict_permission_mode(monkeypatch):
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    previous = p._TESTING_BYPASS_ENABLED
    p.set_testing_bypass(False)
    yield
    p.set_testing_bypass(previous)


@contextmanager
def _request(app, *, headers=None, remote_addr="127.0.0.1"):
    request_headers = {"Host": "localhost"}
    if headers:
        request_headers.update(headers)
    with app.test_request_context(
        "/",
        headers=request_headers,
        environ_overrides={"REMOTE_ADDR": remote_addr},
    ):
        yield


def _principal(app):
    with _request(app):
        value = p.resolve_local_workspace_principal(module="content", action="write")
    assert type(value) is p.LocalWorkspacePrincipal
    return value


def _scope(app, principal, *, gate=None, **kwargs):
    with _request(app):
        return p.check_local_workspace_scope_permission(
            principal,
            domain_id=kwargs.pop("domain_id", "cth"),
            action=kwargs.pop("action", "read"),
            module=kwargs.pop("module", "content"),
            gate=gate,
            **kwargs,
        )


def test_principal_is_server_issued_and_scope_result_keeps_legacy_serializer(
    app, monkeypatch,
):
    monkeypatch.setattr(p, "_registered_resource_scope_exists", lambda *a, **k: True)
    principal = _principal(app)
    assert principal.principal_kind == "local_workspace"
    assert principal.principal_ref == "workspace:local"
    assert principal.actor_id is None
    with pytest.raises(TypeError):
        p.LocalWorkspacePrincipal(_issuer=object())

    gate = p.PermissionGate()
    result = _scope(
        app, principal, gate=gate, action="write", subject_id="subject-123"
    )
    assert result.allowed
    assert result.actor_id is None
    assert result.caller == "workspace:local"
    assert set(result.to_dict()) == set(p.PermissionResult.__dataclass_fields__)
    scope = result.to_scope_dict()
    assert scope["principal_kind"] == "local_workspace"
    assert scope["principal_ref"] == "workspace:local"
    assert scope["subject_id"] == "subject-123"
    assert gate.get_audit_log(operation_type="resource_scope_write")[-1]["caller"] == "workspace:local"


def test_json_shaped_identity_cannot_be_used_as_a_workspace_principal(app):
    forged = {
        "principal_kind": "local_workspace",
        "principal_ref": "workspace:local",
        "actor_id": None,
    }
    with _request(app):
        result = p.check_local_workspace_scope_permission(
            forged,
            domain_id="cth",
            action="read",
            module="content",
            global_scope=True,
        )
    assert not result.allowed
    assert result.actor_id is None
    assert result.principal_kind is None
    assert result.caller == "anonymous"


@pytest.mark.parametrize(
    "config,headers,remote_addr",
    [
        (False, {}, "127.0.0.1"),
        (True, {}, "192.0.2.7"),
        (True, {"X-Forwarded-For": "127.0.0.1"}, "127.0.0.1"),
        (True, {"Authorization": "Bearer ignored"}, "127.0.0.1"),
        (True, {"Cookie": "cth_poms_v4_session=present"}, "127.0.0.1"),
        (True, {"X-Actor-ID": "23"}, "127.0.0.1"),
        (True, {"X-Lumenis-User-ID": "23"}, "127.0.0.1"),
    ],
)
@pytest.mark.parametrize("module", ["content", "collector"])
def test_resolver_rejects_closed_remote_forwarded_and_identity_claims(
    app, config, headers, remote_addr, module,
):
    app.config["LUMENIS_OPEN_WORKSPACE"] = config
    with _request(app, headers=headers, remote_addr=remote_addr):
        assert p.resolve_local_workspace_principal(module=module) is None


@pytest.mark.parametrize("module", ["content", "collector"])
def test_scope_check_revalidates_open_workspace_and_transport(app, module):
    principal = _principal(app)
    gate = p.PermissionGate()
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    with _request(app):
        closed = p.check_local_workspace_scope_permission(
            principal,
            domain_id="cth",
            action="read",
            module=module,
            global_scope=True,
            gate=gate,
        )
    assert not closed.allowed
    assert closed.code == "workspace_unavailable"

    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    with _request(app, headers={"X-Actor-ID": "23"}):
        claimed = p.check_local_workspace_scope_permission(
            principal,
            domain_id="cth",
            action="read",
            module=module,
            global_scope=True,
            gate=gate,
        )
    assert not claimed.allowed
    assert claimed.caller == "workspace:local"


@pytest.mark.parametrize(
    "domain_id,scope",
    [("cth", {"global_scope": True}), ("bmp", {"global_scope": True})],
)
def test_only_explicit_cth_or_bmp_global_scope_is_admitted(app, domain_id, scope):
    principal = _principal(app)
    result = _scope(app, principal, domain_id=domain_id, **scope)
    assert result.allowed
    assert result.global_scope is True
    assert result.actor_id is None


def test_focus_requires_one_registered_exact_resource(app, monkeypatch):
    principal = _principal(app)
    monkeypatch.setattr(
        p,
        "_registered_resource_scope_exists",
        lambda domain, *, subject_id, brand_focus_id: (
            domain == "cth" and subject_id == "subject-123" and brand_focus_id is None
        ),
    )
    accepted = _scope(app, principal, subject_id="subject-123")
    rejected = _scope(app, principal, subject_id="subject-missing")
    assert accepted.allowed
    assert not rejected.allowed
    assert rejected.code == "scope_not_registered"


@pytest.mark.parametrize(
    "changes",
    [
        {"domain_id": "other", "global_scope": True},
        {"module": "unknown_module", "global_scope": True},
        {"action": "export", "global_scope": True},
        {"global_scope": 1},
        {"global_scope": True, "subject_id": "subject-123"},
        {"subject_id": "subject-123", "brand_focus_id": "brand-123"},
    ],
)
def test_invalid_or_cross_scope_requests_are_denied(app, changes):
    principal = _principal(app)
    defaults = {"global_scope": False}
    defaults.update(changes)
    result = _scope(app, principal, **defaults)
    assert not result.allowed


def test_scope_admission_does_not_grant_effect_gate_or_change_account_actor_path(
    app, monkeypatch,
):
    principal = _principal(app)
    monkeypatch.setattr(p, "_registered_resource_scope_exists", lambda *a, **k: True)
    gate = p.PermissionGate()
    admitted = _scope(
        app,
        principal,
        gate=gate,
        action="write",
        subject_id="subject-123",
    )
    assert admitted.allowed
    effect = gate.check(
        p.OperationType.DB_WRITE,
        resource=admitted.resource,
        caller=admitted.caller,
    )
    assert not effect.allowed

    monkeypatch.setattr(p, "_actor_has_scope_action", lambda *a: True)
    monkeypatch.setattr(p, "_load_actor_scope_role", lambda *a: "admin")
    account_scope = p.check_actor_scope_permission(
        {"id": 23},
        domain_id="cth",
        action="read",
        module="content",
        subject_id="subject-123",
        gate=gate,
    )
    assert account_scope.allowed
    assert account_scope.actor_id == 23
    assert account_scope.caller == "actor:23"


@pytest.mark.parametrize("action", ["read", "write"])
def test_reports_reuses_scoped_workspace_without_granting_effects(app, action):
    with _request(app):
        principal = p.resolve_local_workspace_principal(module="reports", action=action)
    result = _scope(app, principal, module="reports", action=action, global_scope=True)
    assert result.allowed and result.caller == "workspace:local"
    assert result.audit_id and result.actor_id is None
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    assert not _scope(app, principal, module="reports", global_scope=True).allowed


def test_collector_scope_requires_registry_and_does_not_approve_import(app, monkeypatch):
    with _request(app):
        principal = p.resolve_local_workspace_principal(module="collector", action="write")
    assert type(principal) is p.LocalWorkspacePrincipal
    monkeypatch.setattr(
        p, "_registered_resource_scope_exists",
        lambda domain, *, subject_id, brand_focus_id: (
            domain == "cth" and subject_id == "subject-123" and brand_focus_id is None
        ),
    )
    gate = p.PermissionGate()
    admitted = _scope(
        app, principal, gate=gate, module="collector", action="write", subject_id="subject-123",
    )
    assert admitted.allowed and admitted.audit_id
    missing = _scope(app, principal, module="collector", action="write", subject_id="subject-missing")
    assert not missing.allowed and missing.code == "scope_not_registered"
    effect = gate.check(p.OperationType.DATA_IMPORT, resource=admitted.resource, caller=admitted.caller)
    assert not effect.allowed
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    assert not _scope(app, principal, module="collector", action="write", subject_id="subject-123").allowed
