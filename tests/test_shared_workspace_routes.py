"""Route-composition tests for exact Shared SavedWork and Internal Pitch scope.

These tests stop in a Flask before-request probe after the app PermissionGate
handoff decision. They exercise current blueprints and owner admission, but do
not execute SavedWork/pitch persistence, Effect Fence commits, app startup, or
runtime acceptance.
"""
import ast
import json
import re
from pathlib import Path

import pytest
from flask import Flask, jsonify, request
from werkzeug.datastructures import Headers

from lumenis.system.security import permission

SCOPE = {"scope_kind": "shared_workspace", "version": 1}
SCOPE_HEADER = "X-Lumenis-Workspace-Scope"
TASK_ID = "task-pitch-" + "a" * 24
ARTIFACT_ID = "ART-" + "a" * 16


def _app_handoff_function():
    """Compile only the app resolver and guard; importing app.py starts DB work."""
    source = Path(__file__).resolve().parents[1] / "app.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    wanted = {"_pg_resolve_operation_type", "_shared_workspace_owner_http_handoff"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    if {node.name for node in nodes} != wanted:
        raise AssertionError("app Shared handoff functions are missing")
    namespace = {
        "OperationType": permission.OperationType,
        "re": re,
        "request": request,
    }
    module = ast.Module(body=nodes, type_ignores=[])
    exec(compile(module, str(source), "exec"), namespace)
    return namespace["_shared_workspace_owner_http_handoff"]


@pytest.fixture
def route_client(monkeypatch):
    """Use actual route maps and Permission admission without app startup or DB."""
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    previous_bypass = permission._TESTING_BYPASS_ENABLED
    permission.set_testing_bypass(False)
    gate = permission.PermissionGate()
    audit_calls = []

    def in_memory_audit(**fields):
        audit_calls.append(fields)
        return "route-test-audit"

    monkeypatch.setattr(gate, "_write_audit", in_memory_audit)
    monkeypatch.setattr(permission, "get_permission_gate", lambda: gate)

    from experience_runtime import experience_bp
    from lumenis_app_api import domain_api_bp

    app = Flask(__name__)
    app.config.update(TESTING=True, LUMENIS_OPEN_WORKSPACE=True)
    app.register_blueprint(experience_bp)
    app.register_blueprint(domain_api_bp)
    handoff = _app_handoff_function()

    @app.before_request
    def inspect_handoff_only():
        # Do not invoke route handlers or their persistence/effect paths here.
        return jsonify({"handoff": handoff()})

    yield app.test_client(), audit_calls
    permission.reset_permission_gate()
    permission.set_testing_bypass(previous_bypass)


def _shared_headers():
    return {SCOPE_HEADER: json.dumps(SCOPE, separators=(",", ":"))}


def test_saved_work_save_and_revise_handoff_only_after_current_local_admission(route_client):
    client, audit_calls = route_client
    saved = client.post("/api/experience/saved-work", headers=_shared_headers(), json={})
    revised = client.post(
        f"/api/experience/saved-work/{ARTIFACT_ID}/revise",
        headers=_shared_headers(), json={},
    )

    assert saved.get_json() == {"handoff": True}
    assert revised.get_json() == {"handoff": True}
    assert [call["operation_type"] for call in audit_calls] == [
        "shared_workspace_scope_write", "shared_workspace_scope_write",
    ]


def test_pitch_prepare_run_and_cancel_accept_exact_body_scope_and_owner_admission(route_client):
    client, audit_calls = route_client
    prepare = client.post(
        "/api/experience/creation/internal-pitches",
        json={"scope": SCOPE},
    )
    run = client.post(
        f"/api/experience/creation/internal-pitches/{TASK_ID}/run",
        json={"scope": SCOPE},
    )
    cancel = client.post(
        f"/api/experience/creation/internal-pitches/{TASK_ID}/cancel",
        headers=_shared_headers(), json={"scope": SCOPE},
    )

    assert prepare.get_json() == {"handoff": True}
    assert run.get_json() == {"handoff": True}
    assert cancel.get_json() == {"handoff": True}
    assert len(audit_calls) == 3
    assert {call["operation_type"] for call in audit_calls} == {"shared_workspace_scope_write"}


@pytest.mark.parametrize(
    "path,headers,body",
    [
        ("/api/experience/saved-work", {}, {}),
        ("/api/experience/saved-work", {**_shared_headers(), "X-Domain-Id": "cth"}, {}),
        ("/api/experience/saved-work", {**_shared_headers(), "X-Product-Id": "SHARED"}, {}),
        ("/api/experience/saved-work", {**_shared_headers(), "X-Lumenis-Context-Mode": "domain"}, {}),
        ("/api/experience/saved-work", {**_shared_headers(), "X-Subject-ID": "subject-1"}, {}),
        ("/api/experience/saved-work", {**_shared_headers(), "X-Brand-Focus-ID": "brand-1"}, {}),
        ("/api/experience/saved-work", {SCOPE_HEADER: '{"scope_kind":"shared_workspace","version":true}'}, {}),
        ("/api/experience/saved-work", {SCOPE_HEADER: '{"scope_kind":"shared_workspace","version":1,"version":1}'}, {}),
        ("/api/experience/saved-work/preferences", _shared_headers(), {}),
        ("/api/experience/saved-work/ART-ABC/revise", _shared_headers(), {}),
        ("/api/experience/creation/internal-pitches", {}, {"scope": {**SCOPE, "actor_id": 7}}),
        ("/api/experience/creation/internal-pitches", _shared_headers(), {"scope": {"domain_id": "cth", "subject_id": "s1", "brand_focus_id": None, "global_scope": False}}),
        ("/api/experience/creation/internal-pitches?domain_id=cth", {}, {"scope": SCOPE}),
        ("/api/experience/creation/internal-pitches?scope_kind=shared_workspace&version=1", {}, {"scope": SCOPE}),
    ],
)
def test_invalid_mixed_legacy_or_unregistered_scope_never_gets_handoff(route_client, path, headers, body):
    client, audit_calls = route_client
    response = client.post(path, headers=headers, json=body)

    assert response.get_json() == {"handoff": False}
    assert audit_calls == []


def test_repeated_scope_headers_never_get_handoff(route_client):
    client, audit_calls = route_client
    headers = Headers([
        (SCOPE_HEADER, json.dumps(SCOPE)),
        (SCOPE_HEADER, json.dumps(SCOPE)),
    ])

    response = client.post("/api/experience/saved-work", headers=headers, json={})

    assert response.get_json() == {"handoff": False}
    assert audit_calls == []


def test_legacy_scope4_and_source_reference_remain_outside_shared_handoff(route_client):
    client, audit_calls = route_client
    legacy = client.post(
        "/api/experience/creation/internal-pitches",
        json={"scope": {"domain_id": "cth", "subject_id": "s1",
                        "brand_focus_id": None, "global_scope": False}},
    )
    source_reference = client.post(
        "/api/experience/materials/source-references",
        headers=_shared_headers(), json={},
    )

    assert legacy.get_json() == {"handoff": False}
    assert source_reference.get_json() == {"handoff": False}
    assert audit_calls == []


def test_owner_routes_reject_client_actor_project_and_workspace_fields_before_effects():
    from experience_runtime import experience_bp
    from lumenis_app_api import domain_api_bp

    app = Flask(__name__)
    app.register_blueprint(experience_bp)
    app.register_blueprint(domain_api_bp)
    client = app.test_client()
    saved_payload = {
        "title": "Independent document", "markdown": "Draft", "kind": "saved_document",
        "payload": {}, "citations": [], "request_id": "route-unit-1",
    }
    pitch_payload = {
        "scope": SCOPE, "manuscript": {}, "request_id": "route-unit-2", "shot_plan": {},
    }

    for field, value in (("actor_id", 73), ("project_id", "client-project"),
                         ("workspace_id", "client-workspace")):
        saved = client.post(
            "/api/experience/saved-work", headers=_shared_headers(),
            json={**saved_payload, field: value},
        )
        pitch = client.post(
            "/api/experience/creation/internal-pitches", json={**pitch_payload, field: value},
        )
        assert saved.status_code == 400
        assert saved.get_json()["code"] == "WORK_REQUEST_INVALID"
        assert pitch.status_code == 400
        assert pitch.get_json()["code"] == "INTERNAL_PITCH_REQUEST_INVALID"


def test_account_actor_uses_read_only_session_and_current_shared_permission(route_client, monkeypatch):
    client, audit_calls = route_client
    client.application.config["LUMENIS_OPEN_WORKSPACE"] = False
    actor_checks = []
    read_modes = []

    monkeypatch.setattr(
        permission, "_actor_has_scope_action",
        lambda actor_id, product_id, module, action, **kwargs: (
            actor_checks.append((actor_id, product_id, module, action)) or True
        ),
    )
    monkeypatch.setattr(permission, "_load_actor_scope_role", lambda actor_id, **kwargs: "owner")
    monkeypatch.setattr(permission, "_load_actor_scope_grants", lambda actor_id, **kwargs: [])
    import lumenis.auth.service as auth_service

    def current_actor(*, read_only=False):
        read_modes.append(read_only)
        return {"id": 73, "role": "user"}

    monkeypatch.setattr(auth_service, "get_current_user", current_actor)
    saved = client.post("/api/experience/saved-work", headers=_shared_headers(), json={})
    pitch = client.post(
        "/api/experience/creation/internal-pitches", json={"scope": SCOPE},
    )

    assert saved.get_json() == {"handoff": True}
    assert pitch.get_json() == {"handoff": True}
    assert actor_checks == [
        (73, "SHARED", "reports", "write"),
        (73, "SHARED", "reports", "write"),
    ]
    assert read_modes == [True, True]
    assert len(audit_calls) == 2
