"""Isolated API request regressions; no domain persistence or product E2E claim."""

import ast
import json
from pathlib import Path

import pytest
from flask import Blueprint, Flask, jsonify, request


@pytest.fixture
def routes():
    source_path = Path(__file__).resolve().parents[1] / "lumenis_app_api.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8-sig"))
    names = {
        "_internal_pitch_body", "_internal_pitch_response", "_business_work_body",
        "_business_work_response", "api_business_work_prepare",
    }
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == names
    blueprint = Blueprint("business_route_regression", __name__)
    calls = []
    actor_ref = {"kind": "user", "id": 17}
    scope = {"domain_id": "cth", "subject_id": "route-test-subject", "brand_focus_id": None,
             "global_scope": False}

    def authorize(*args, **kwargs):
        raise AssertionError("Route must forward authorization; domain owner executes it")

    class CaptureOwner:
        def prepare(self, *, actor_ref, scope, authorize, submission_id, source_job_id,
                    kind, question, options=None, planning_constraints=None):
            calls.append({"method": "prepare", "actor_ref": actor_ref, "scope": scope,
                          "authorize": authorize, "submission_id": submission_id,
                          "source_job_id": source_job_id, "kind": kind, "question": question,
                          "options": options, "planning_constraints": planning_constraints})
            return {"state": "PREPARED"}

        def prepare_from_case(self, case_id, *, actor_ref, scope, authorize, submission_id,
                              kind, options=None, planning_constraints=None):
            calls.append({"method": "prepare_from_case", "case_id": case_id,
                          "actor_ref": actor_ref, "scope": scope, "authorize": authorize,
                          "submission_id": submission_id, "kind": kind, "options": options,
                          "planning_constraints": planning_constraints})
            return {"state": "PREPARED"}

    def binding(operation):
        assert operation == "prepare"
        calls.append({"method": "binding"})
        return CaptureOwner(), actor_ref, scope, authorize

    namespace = {"json": json, "jsonify": jsonify, "request": request,
                 "domain_api_bp": blueprint, "_business_work_binding": binding}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source_path), "exec"), namespace)
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(blueprint)

    @app.post("/test/pitch-error")
    def pitch_error():
        def fail():
            raise PermissionError(request.get_json()["code"])
        return namespace["_internal_pitch_response"](fail)

    return app.test_client(), calls, actor_ref, scope, authorize


def source_request():
    return {"submission_id": "route-test-source", "source_job_id": "route-test-source-job",
            "kind": "cth_operations", "question": "哪些证据支持下月的运营安排？"}


@pytest.mark.parametrize("with_options", [False, True])
def test_question_can_reach_owner_without_operator_options(routes, with_options):
    client, calls, actor_ref, scope, authorize = routes
    body = source_request()
    if with_options:
        body["options"] = None
    response = client.post("/api/experience/business-works", json=body)
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.get_json()["publish_status"] == "not_performed"
    owner_call = calls[1]
    assert owner_call["method"] == "prepare"
    assert owner_call["question"] == body["question"]
    assert owner_call["source_job_id"] == body["source_job_id"]
    assert owner_call["options"] is None
    assert owner_call["actor_ref"] is actor_ref
    assert owner_call["scope"] is scope
    assert owner_call["authorize"] is authorize


@pytest.mark.parametrize("from_case", [False, True])
def test_initial_planning_constraints_are_forwarded_to_existing_owner(routes, from_case):
    client, calls, _, _, _ = routes
    body = ({"submission_id": "route-test-case", "case_id": "route-test-case-id",
             "kind": "cth_operations"} if from_case else source_request())
    constraints = {"time_range": {"start": "2026-10-01T00:00:00+08:00",
                                  "end": "2026-10-31T23:59:59+08:00"},
                   "resource_constraints": {"budget_amount": "100", "estimated_cost_amount": "50",
                                            "currency": "CNY", "as_of": "2026-10-08T08:00:00+08:00",
                                            "limits": ["Estimate only; no purchasing."]}}
    body["planning_constraints"] = constraints
    body["options"] = None
    response = client.post("/api/experience/business-works", json=body)
    assert response.status_code == 200
    assert calls[1]["method"] == ("prepare_from_case" if from_case else "prepare")
    assert calls[1]["planning_constraints"] == constraints
    assert calls[1]["options"] == body["options"]


@pytest.mark.parametrize("extra", [
    {"case_id": "mixed-case"}, {"actor_ref": {"id": 99}}, {"scope": {"domain_id": "zbmp"}},
    {"authorize": True}, {"principal": "client-principal"}, {"workspace_id": "client-workspace"},
    {"unknown": "field"},
])
def test_mixed_source_or_client_authority_is_rejected_before_owner_binding(routes, extra):
    client, calls, _, _, _ = routes
    response = client.post("/api/experience/business-works", json={**source_request(), **extra})
    assert response.status_code == 400
    assert response.get_json()["code"] == "BUSINESS_WORK_REQUEST_INVALID"
    assert calls == []


@pytest.mark.parametrize("body", [
    {"submission_id": "missing-kind", "case_id": "case"},
    {"submission_id": "missing-source", "kind": "cth_operations", "question": "question"},
    {"submission_id": "mixed-case", "kind": "cth_operations", "case_id": "case", "question": "question"},
])
def test_incomplete_or_mixed_case_shape_is_rejected_without_effect(routes, body):
    client, calls, _, _, _ = routes
    response = client.post("/api/experience/business-works", json=body)
    assert response.status_code == 400
    assert calls == []


def test_duplicate_json_key_is_rejected_before_binding(routes):
    client, calls, _, _, _ = routes
    raw = json.dumps(source_request())[:-1] + ',"question":"replacement"}'
    response = client.post("/api/experience/business-works", data=raw, content_type="application/json")
    assert response.status_code == 400
    assert response.get_json()["code"] == "BUSINESS_WORK_REQUEST_INVALID"
    assert calls == []


@pytest.mark.parametrize("code,status", [
    ("SHARED_WORKSPACE_PERMISSION_UNAVAILABLE", 503),
    ("SHARED_WORKSPACE_PERMISSION_DENIED", 403), ("AUTH_REQUIRED", 401),
])
def test_pitch_unavailable_is_distinct_from_denied_and_authentication(routes, code, status):
    client, _, _, _, _ = routes
    response = client.post("/test/pitch-error", json={"code": code})
    assert response.status_code == status
    assert response.get_json() == {"ok": False, "code": code}
    assert response.headers["Cache-Control"] == "no-store"
