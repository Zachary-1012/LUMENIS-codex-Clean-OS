"""Isolated SourceReference route composition checks.

These route tests keep the real server-issued local-workspace principal and
request-scope resolver, while replacing Permission/C5 callbacks. They do not
exercise C5 persistence, the full app startup path, or product E2E.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from types import CodeType, FunctionType, SimpleNamespace

import pytest
from flask import Flask, jsonify, request

import experience_runtime as runtime
from lumenis.shared import database as shared_database
from lumenis.system.security import permission as p

SOURCE_URL = "/api/experience/materials/source-references"
PREPARE_URL = SOURCE_URL + "/prepare"
CONFIRMATION_ID = "c" * 43
CONFIRM_URL = SOURCE_URL + "/confirmations/" + CONFIRMATION_ID
GLOBAL = {
    "Host": "localhost",
    "X-Domain-Id": "CTH",
    "X-Product-Id": "CTH",
    "X-Lumenis-Context-Mode": "GLOBAL_ALL",
}
REQUEST = {
    "source_id": "source-17",
    "canonical_id": "canonical-17",
    "expected_body_sha256": hashlib.sha256(b"approved source snapshot").hexdigest(),
    "request_id": "source-reference-request-17",
}
EXPECTED_SCOPE = {
    "domain_id": "cth",
    "subject_id": None,
    "brand_focus_id": None,
    "global_scope": True,
}
RAW_BODY_SENTINEL = "RAW_SOURCE_BODY_MUST_NOT_REACH_ROUTE_RESPONSE"
APPROVAL_TOKEN_SENTINEL = "CLIENT_APPROVAL_TOKEN_MUST_NOT_BE_ECHOED"


def _install_scope_stub(monkeypatch):
    """Avoid the local-workspace audit persistence path without faking identity."""
    calls = []

    def check_scope(
        principal,
        *,
        domain_id,
        action,
        module,
        subject_id=None,
        brand_focus_id=None,
        global_scope=False,
        gate=None,
        connection=None,
    ):
        scope = {
            "domain_id": domain_id,
            "subject_id": subject_id,
            "brand_focus_id": brand_focus_id,
            "global_scope": global_scope,
        }
        calls.append((principal, module, action, scope))
        assert type(principal) is p.LocalWorkspacePrincipal
        assert principal.principal_ref == "workspace:local"
        assert module == "reports" and action == "write"
        assert scope == EXPECTED_SCOPE
        return SimpleNamespace(
            allowed=True,
            verification_state="verified",
            principal_ref="workspace:local",
            actor_id=None,
            audit_id="route-test-scope-audit",
        )

    monkeypatch.setattr(p, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(p, "check_local_workspace_scope_permission", check_scope)
    return calls


def _isolated_app(monkeypatch, *, register_routes=True):
    scope_checks = _install_scope_stub(monkeypatch)
    from lumenis.importer import documents
    from lumenis.shared.reporting import saved_work

    def forbid_database_access(*args, **kwargs):
        pytest.fail("SourceReference route tests must not open a database")

    monkeypatch.setattr(shared_database, "get_repository", forbid_database_access)
    monkeypatch.setattr(documents, "get_repository", forbid_database_access)
    monkeypatch.setattr(saved_work, "get_repository", forbid_database_access)
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    if register_routes:
        app.register_blueprint(runtime.experience_bp)
    return app, scope_checks


@pytest.fixture
def route(monkeypatch):
    app, scope_checks = _isolated_app(monkeypatch)
    return app.test_client(), scope_checks


class _AuditedDenyGate:
    """In-memory stand-in that records every generic gate decision as denied."""

    def __init__(self):
        self.calls = []

    def check(self, **kwargs):
        self.calls.append(dict(kwargs))
        return SimpleNamespace(
            allowed=False,
            reason="ROUTE_TEST_GATE_DENIED",
            requires_approval=True,
            risk_level="high",
            permission_required="COMMIT",
        )


def _install_extracted_main_gate(app, gate, monkeypatch):
    import domain_isolation

    monkeypatch.setattr(
        domain_isolation, "get_domain_context", lambda: SimpleNamespace(domain_id="cth"),
    )
    app_source = Path(__file__).resolve().parents[1] / "app.py"
    tree = ast.parse(app_source.read_text(encoding="utf-8-sig"))
    names = {"_pg_resolve_operation_type", "_permission_gate_write_check"}
    nodes = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    for node in nodes:
        node.decorator_list = []
    namespace = {
        "request": request,
        "jsonify": jsonify,
        "re": re,
        "OperationType": p.OperationType,
        "_PG_WRITE_METHODS": {"POST", "PUT", "PATCH", "DELETE"},
        "_PG_BYPASS_PATHS": set(),
        "_pg": gate,
    }
    functions = _compile_ast_functions(nodes, names, str(app_source), namespace)
    app.before_request(functions["_permission_gate_write_check"])


def _compile_ast_functions(nodes, names, filename, namespace):
    module_code = compile(ast.Module(body=nodes, type_ignores=[]), filename, "exec")
    functions = {
        code.co_name: FunctionType(code, namespace)
        for code in module_code.co_consts
        if isinstance(code, CodeType) and code.co_name in names
    }
    if set(functions) != set(names):
        raise AssertionError("could not extract the requested app functions")
    namespace.update(functions)
    return functions


@pytest.fixture
def main_gate_route(monkeypatch):
    app, scope_checks = _isolated_app(monkeypatch)
    gate = _AuditedDenyGate()
    _install_extracted_main_gate(app, gate, monkeypatch)
    return app.test_client(), gate, scope_checks


def _assert_server_scope(actor, scope):
    assert type(actor) is p.LocalWorkspacePrincipal
    assert actor.principal_kind == "local_workspace"
    assert actor.principal_ref == "workspace:local"
    assert actor.actor_id is None
    assert dict(scope) == EXPECTED_SCOPE


def _fail_if_owner_called(events, name):
    def fail(*args, **kwargs):
        events.append(name)
        raise AssertionError(f"unexpected owner callback: {name}")

    return fail


def _install_no_owner_calls(monkeypatch, events):
    from lumenis.importer import documents

    for module, name in (
        (documents, "prepare_approved_source_reference"),
        (documents, "create_approved_source_reference"),
        (p, "check_approved_source_reference_import"),
        (p, "prepare_approved_source_reference_confirmation"),
        (p, "confirm_approved_source_reference_confirmation"),
    ):
        monkeypatch.setattr(module, name, _fail_if_owner_called(events, name))


def test_source_post_denial_only_prepares_confirmation_and_never_creates(route, monkeypatch):
    from lumenis.importer import documents

    client, scope_checks = route
    events = []
    prepared_descriptor = {
        "prepared": True,
        "resource": "approved-internal-source-reference:v2:" + "a" * 64,
        "parsed_text": RAW_BODY_SENTINEL,
    }
    pending = {
        "allowed": True,
        "code": "APPROVED_SOURCE_REFERENCE_CONFIRMATION_PENDING",
        "state": "pending",
        "confirmation_id": CONFIRMATION_ID,
        "expires_at": "2026-10-11T00:05:00Z",
        "resource": prepared_descriptor["resource"],
    }

    def prepare_source(*, source_id, canonical_id, expected_body_sha256, request_id, actor, scope):
        events.append("c5_prepare")
        _assert_server_scope(actor, scope)
        assert (source_id, canonical_id, expected_body_sha256, request_id) == tuple(REQUEST.values())
        return prepared_descriptor

    def deny_import(*, actor, scope, prepared):
        events.append("permission_check")
        _assert_server_scope(actor, scope)
        assert prepared is prepared_descriptor
        return SimpleNamespace(allowed=False, requires_approval=True)

    def prepare_confirmation(*, actor, scope, request):
        events.append("permission_prepare_confirmation")
        _assert_server_scope(actor, scope)
        assert dict(request) == REQUEST
        return pending

    def forbidden_create(**kwargs):
        events.append("c5_create")
        raise AssertionError("denied source request reached C5 create")

    monkeypatch.setattr(documents, "prepare_approved_source_reference", prepare_source)
    monkeypatch.setattr(documents, "create_approved_source_reference", forbidden_create)
    monkeypatch.setattr(p, "check_approved_source_reference_import", deny_import)
    monkeypatch.setattr(p, "prepare_approved_source_reference_confirmation", prepare_confirmation)

    response = client.post(SOURCE_URL, headers=GLOBAL, json=REQUEST)

    assert response.status_code == 403
    result = response.get_json()
    assert result["ok"] is False
    assert result["code"] == "SOURCE_REFERENCE_APPROVAL_REQUIRED"
    assert result["requires_approval"] is True
    assert result["publish_status"] == "not_performed"
    assert result["confirmation"]["state"] == "pending"
    assert response.headers["Cache-Control"] == "no-store"
    assert events == ["c5_prepare", "permission_check", "permission_prepare_confirmation"]
    assert scope_checks
    assert "approval_token" not in response.get_data(as_text=True)
    assert RAW_BODY_SENTINEL not in response.get_data(as_text=True)


def test_prepare_route_delegates_exact_request_to_permission_owner(route, monkeypatch):
    client, scope_checks = route
    calls = []
    pending = {
        "allowed": True,
        "code": "APPROVED_SOURCE_REFERENCE_CONFIRMATION_PENDING",
        "state": "pending",
        "confirmation_id": CONFIRMATION_ID,
        "expires_at": "2026-10-11T00:05:00Z",
        "resource": "approved-internal-source-reference:v2:" + "b" * 64,
    }

    def owner_prepare(*, actor, scope, request):
        calls.append((actor, dict(scope), dict(request)))
        _assert_server_scope(actor, scope)
        return pending

    monkeypatch.setattr(p, "prepare_approved_source_reference_confirmation", owner_prepare)

    response = client.post(PREPARE_URL, headers=GLOBAL, json=REQUEST)

    assert response.status_code == 200
    result = response.get_json()["result"]
    assert result["state"] == "pending"
    assert result["allowed"] is True
    assert len(calls) == 1
    assert calls[0][1:] == (EXPECTED_SCOPE, REQUEST)
    assert scope_checks
    assert "approval_token" not in response.get_data(as_text=True)
    assert RAW_BODY_SENTINEL not in response.get_data(as_text=True)


@pytest.mark.parametrize(
    ("path", "body", "raw"),
    [
        (SOURCE_URL, {**REQUEST, "approval_token": APPROVAL_TOKEN_SENTINEL}, None),
        (SOURCE_URL, None, json.dumps(REQUEST)[:-1] + ',"source_id":"duplicate"}'),
        (CONFIRM_URL, {"confirmed": 1}, None),
    ],
    ids=("extra-token-key", "duplicate-json-key", "nonliteral-confirm-bool"),
)
def test_malformed_body_rejected_before_any_owner_or_scope_callback(
    route, monkeypatch, path, body, raw,
):
    client, scope_checks = route
    events = []
    _install_no_owner_calls(monkeypatch, events)
    kwargs = {"headers": GLOBAL}
    if raw is None:
        kwargs["json"] = body
    else:
        kwargs.update(data=raw, content_type="application/json")

    response = client.post(path, **kwargs)

    assert response.status_code == 400
    assert response.get_json()["ok"] is False
    assert not events
    assert not scope_checks
    assert APPROVAL_TOKEN_SENTINEL not in response.get_data(as_text=True)


@pytest.mark.parametrize(
    ("path", "body"),
    [
        (SOURCE_URL, REQUEST),
        (PREPARE_URL, REQUEST),
        (CONFIRM_URL, {"confirmed": True}),
    ],
    ids=("create-request", "prepare-request", "confirm-request"),
)
def test_cross_origin_rejected_before_owner_or_scope_callback(route, monkeypatch, path, body):
    client, scope_checks = route
    events = []
    _install_no_owner_calls(monkeypatch, events)

    response = client.post(
        path,
        headers={**GLOBAL, "Origin": "https://untrusted.example"},
        json=body,
    )

    assert response.status_code == 403
    assert response.get_json()["code"] == "SOURCE_REFERENCE_ORIGIN_DENIED"
    assert not events
    assert not scope_checks


def test_confirm_route_calls_permission_owner_with_server_actor_scope_and_typed_flag(route, monkeypatch):
    client, scope_checks = route
    calls = []

    def owner_confirm(*, actor, scope, confirmation_id, confirmed):
        calls.append((actor, dict(scope), confirmation_id, confirmed))
        _assert_server_scope(actor, scope)
        assert type(confirmed) is bool
        return {
            "allowed": True,
            "code": "APPROVED_SOURCE_REFERENCE_CONFIRMATION_CONFIRMED",
            "state": "confirmed",
            "confirmation_id": confirmation_id,
        }

    monkeypatch.setattr(p, "confirm_approved_source_reference_confirmation", owner_confirm)

    response = client.post(CONFIRM_URL, headers=GLOBAL, json={"confirmed": True})

    assert response.status_code == 200
    assert response.get_json()["result"]["state"] == "confirmed"
    assert len(calls) == 1
    assert calls[0][1:] == (EXPECTED_SCOPE, CONFIRMATION_ID, True)
    assert scope_checks
    assert "approval_token" not in response.get_data(as_text=True)
    assert RAW_BODY_SENTINEL not in response.get_data(as_text=True)


def test_confirm_route_preserves_explicit_cancellation_as_normal_denied_result(route, monkeypatch):
    client, scope_checks = route

    def owner_cancel(*, actor, scope, confirmation_id, confirmed):
        _assert_server_scope(actor, scope)
        assert confirmation_id == CONFIRMATION_ID and confirmed is False
        return {
            "allowed": False,
            "code": "APPROVED_SOURCE_REFERENCE_CONFIRMATION_CANCELLED",
            "state": "cancelled",
            "confirmation_id": confirmation_id,
        }

    monkeypatch.setattr(p, "confirm_approved_source_reference_confirmation", owner_cancel)

    response = client.post(CONFIRM_URL, headers=GLOBAL, json={"confirmed": False})

    assert response.status_code == 200
    result = response.get_json()["result"]
    assert result["allowed"] is False
    assert result["state"] == "cancelled"
    assert result["code"] == "APPROVED_SOURCE_REFERENCE_CONFIRMATION_CANCELLED"
    assert scope_checks


@pytest.mark.parametrize(
    ("owner_result", "status"),
    [
        ({"allowed": False, "code": "APPROVED_SOURCE_REFERENCE_CONFIRMATION_UNKNOWN"}, 403),
        ({
            "allowed": False,
            "code": "APPROVED_SOURCE_REFERENCE_PERMISSION_UNAVAILABLE",
            "verification_state": "unavailable",
        }, 503),
    ],
    ids=("owner-denial", "owner-unavailable"),
)
def test_confirm_route_preserves_permission_owner_denial_status(route, monkeypatch, owner_result, status):
    client, scope_checks = route

    def owner_confirm(*, actor, scope, confirmation_id, confirmed):
        _assert_server_scope(actor, scope)
        assert confirmation_id == CONFIRMATION_ID and confirmed is True
        return owner_result

    monkeypatch.setattr(p, "confirm_approved_source_reference_confirmation", owner_confirm)

    response = client.post(CONFIRM_URL, headers=GLOBAL, json={"confirmed": True})

    assert response.status_code == status
    assert response.get_json() == {
        "ok": False,
        "code": owner_result["code"],
        "publish_status": "not_performed",
    }
    assert scope_checks


def test_retry_create_delegates_exact_c5_signature_after_private_checker_allows(route, monkeypatch):
    from lumenis.importer import documents

    client, scope_checks = route
    calls = []
    prepared_descriptor = {
        "prepared": True,
        "resource": "approved-internal-source-reference:v2:" + "d" * 64,
        "parsed_text": RAW_BODY_SENTINEL,
    }
    created = {"ok": True, "replayed": False, "request_id": REQUEST["request_id"]}

    def c5_prepare(*, source_id, canonical_id, expected_body_sha256, request_id, actor, scope):
        calls.append(("prepare", source_id, canonical_id, expected_body_sha256, request_id, actor, dict(scope)))
        _assert_server_scope(actor, scope)
        return prepared_descriptor

    def owner_allows(*, actor, scope, prepared):
        calls.append(("check", actor, dict(scope), prepared))
        _assert_server_scope(actor, scope)
        assert prepared is prepared_descriptor
        return SimpleNamespace(allowed=True, requires_approval=False)

    def c5_create(*, source_id, canonical_id, expected_body_sha256, request_id, actor, scope):
        calls.append(("create", source_id, canonical_id, expected_body_sha256, request_id, actor, dict(scope)))
        _assert_server_scope(actor, scope)
        return created

    monkeypatch.setattr(documents, "prepare_approved_source_reference", c5_prepare)
    monkeypatch.setattr(documents, "create_approved_source_reference", c5_create)
    monkeypatch.setattr(p, "check_approved_source_reference_import", owner_allows)

    response = client.post(SOURCE_URL, headers=GLOBAL, json=REQUEST)

    assert response.status_code == 200
    assert response.get_json()["result"] == created
    assert [call[0] for call in calls] == ["prepare", "check", "create"]
    assert calls[0][1:5] == tuple(REQUEST.values())
    assert calls[0][5] is calls[1][1] is calls[2][5]
    assert calls[0][6] == calls[1][2] == calls[2][6] == EXPECTED_SCOPE
    assert calls[1][3] is prepared_descriptor
    assert scope_checks
    assert "approval_token" not in response.get_data(as_text=True)
    assert RAW_BODY_SENTINEL not in response.get_data(as_text=True)


def test_main_write_gate_dispatches_only_the_three_registered_source_reference_owners(
    main_gate_route, monkeypatch,
):
    from lumenis.importer import documents

    client, gate, scope_checks = main_gate_route
    events = []
    prepared_descriptor = {
        "prepared": True,
        "resource": "approved-internal-source-reference:v2:" + "e" * 64,
        "parsed_text": RAW_BODY_SENTINEL,
    }
    pending = {
        "allowed": True,
        "code": "APPROVED_SOURCE_REFERENCE_CONFIRMATION_PENDING",
        "state": "pending",
        "confirmation_id": CONFIRMATION_ID,
    }
    confirmed_response = {
        "allowed": True,
        "code": "APPROVED_SOURCE_REFERENCE_CONFIRMATION_CONFIRMED",
        "state": "confirmed",
        "confirmation_id": CONFIRMATION_ID,
    }

    def c5_prepare(*, source_id, canonical_id, expected_body_sha256, request_id, actor, scope):
        events.append("c5_prepare")
        _assert_server_scope(actor, scope)
        assert (source_id, canonical_id, expected_body_sha256, request_id) == tuple(REQUEST.values())
        return prepared_descriptor

    def deny_import(*, actor, scope, prepared):
        events.append("permission_check")
        _assert_server_scope(actor, scope)
        assert prepared is prepared_descriptor
        return SimpleNamespace(allowed=False, requires_approval=True)

    def permission_prepare(*, actor, scope, request):
        events.append("permission_prepare")
        _assert_server_scope(actor, scope)
        assert dict(request) == REQUEST
        return pending

    def permission_confirm(*, actor, scope, confirmation_id, confirmed):
        events.append("permission_confirm")
        _assert_server_scope(actor, scope)
        assert confirmation_id == CONFIRMATION_ID and confirmed is True
        return confirmed_response

    def forbidden_create(**kwargs):
        events.append("c5_create")
        raise AssertionError("denied source request reached C5 create")

    monkeypatch.setattr(documents, "prepare_approved_source_reference", c5_prepare)
    monkeypatch.setattr(documents, "create_approved_source_reference", forbidden_create)
    monkeypatch.setattr(p, "check_approved_source_reference_import", deny_import)
    monkeypatch.setattr(p, "prepare_approved_source_reference_confirmation", permission_prepare)
    monkeypatch.setattr(p, "confirm_approved_source_reference_confirmation", permission_confirm)

    create_response = client.post(SOURCE_URL, headers=GLOBAL, json=REQUEST)
    assert create_response.status_code == 403
    assert create_response.get_json()["code"] == "SOURCE_REFERENCE_APPROVAL_REQUIRED"
    assert gate.calls == []

    prepare_response = client.post(PREPARE_URL, headers=GLOBAL, json=REQUEST)
    assert prepare_response.status_code == 200
    assert prepare_response.get_json()["result"]["state"] == "pending"
    assert gate.calls == []

    confirm_response = client.post(CONFIRM_URL, headers=GLOBAL, json={"confirmed": True})
    assert confirm_response.status_code == 200
    assert confirm_response.get_json()["result"]["state"] == "confirmed"
    assert gate.calls == []
    assert events == [
        "c5_prepare", "permission_check", "permission_prepare",
        "permission_prepare", "permission_confirm",
    ]
    assert scope_checks
    for response in (create_response, prepare_response, confirm_response):
        assert "approval_token" not in response.get_data(as_text=True)
        assert RAW_BODY_SENTINEL not in response.get_data(as_text=True)


@pytest.mark.parametrize(
    ("path", "body"),
    [
        (SOURCE_URL + "/confirmations/short", {"confirmed": True}),
        (SOURCE_URL + "/prepare/extra", REQUEST),
    ],
    ids=("malformed-confirmation-id", "lookalike-route"),
)
def test_main_gate_denies_malformed_confirmation_and_lookalike_before_owner(
    main_gate_route, monkeypatch, path, body,
):
    client, gate, scope_checks = main_gate_route
    events = []
    _install_no_owner_calls(monkeypatch, events)

    response = client.post(path, headers=GLOBAL, json=body)

    assert response.status_code == 403
    assert response.get_json()["status"] == "BLOCKED"
    assert len(gate.calls) == 1
    assert gate.calls[0]["operation_type"] is p.OperationType.DB_WRITE
    assert gate.calls[0]["resource"] == path
    assert not events
    assert not scope_checks


def test_main_gate_with_wrong_endpoint_fails_closed_on_none_operation(monkeypatch):
    app, scope_checks = _isolated_app(monkeypatch, register_routes=False)
    gate = _AuditedDenyGate()
    owner_calls = []

    def wrong_endpoint():
        owner_calls.append("view")
        return jsonify({"ok": True})

    app.add_url_rule(
        SOURCE_URL,
        endpoint="test.source_reference_wrong_endpoint",
        view_func=wrong_endpoint,
        methods=["POST"],
    )
    _install_extracted_main_gate(app, gate, monkeypatch)
    events = []
    _install_no_owner_calls(monkeypatch, events)

    response = app.test_client().post(SOURCE_URL, headers=GLOBAL, json=REQUEST)

    assert response.status_code == 503
    assert response.get_json()["status"] == "BLOCKED"
    assert len(gate.calls) == 1
    assert gate.calls[0]["operation_type"] is None
    assert owner_calls == []
    assert not events
    assert not scope_checks


def test_app_operation_classifier_reserves_only_exact_source_reference_posts():
    app_source = Path(__file__).resolve().parents[1] / "app.py"
    tree = ast.parse(app_source.read_text(encoding="utf-8-sig"))
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_pg_resolve_operation_type"
    )
    function.decorator_list = []
    namespace = {"re": re, "OperationType": p.OperationType, "request": request}
    functions = _compile_ast_functions(
        [function], {"_pg_resolve_operation_type"}, str(app_source), namespace,
    )
    resolver = functions["_pg_resolve_operation_type"]

    assert resolver(SOURCE_URL, "POST") is None
    assert resolver(PREPARE_URL, "POST") is None
    assert resolver(CONFIRM_URL, "POST") is None
    assert resolver(SOURCE_URL + "/prepare/extra", "POST") is p.OperationType.DB_WRITE
