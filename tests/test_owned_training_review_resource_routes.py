"""Read-only review-resource preparation never grants training or records reviews."""
import ast
import hashlib
import json
import re
from pathlib import Path
import sqlite3
import uuid

from flask import Flask
import pytest

import experience_runtime as runtime
from lumenis.shared.database import repository
from lumenis.shared.learning import training_review
from lumenis.system.security import permission as p
from tests.test_owned_training_review import review_db, strict_permission, _scope, _source

URL = "/api/experience/owned-training/review-resources"
GLOBAL = {"Host": "localhost", "X-Domain-Id": "CTH", "X-Product-Id": "CTH", "X-Lumenis-Context-Mode": "GLOBAL_ALL"}


@pytest.fixture
def route(review_db, monkeypatch):
    monkeypatch.setattr(repository, "_default_repository", repository.DatabaseRepository())
    gate = p.PermissionGate()
    monkeypatch.setattr(p, "_default_gate", gate)
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    app.register_blueprint(runtime.experience_bp)
    with repository.get_repository().transaction() as conn:
        ref = _source(conn, _scope(global_scope=True))
    body = dict(submission_id=str(uuid.uuid4()), source_evidence_refs=[ref],
                prompt_messages=[{"role": "user", "content": "Original fictional pipeline smoke question."}],
                proposed_target=f"Candidate answer, awaiting human review. [[{ref}]]",
                context="Original fictional training pipeline smoke only; no business fact acceptance.",
                proposed_rights_declaration={"purpose": "model_training", "rights_disposition": "permitted"})
    return app.test_client(), app, gate, body, review_db


def counts(path):
    with sqlite3.connect(path) as conn:
        return tuple(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                     for table in ("app_evidence_records", "lumenis_subject_registry"))


def test_real_request_prepares_exact_resource_without_approval_or_database_write(route):
    client, app, gate, body, path = route
    before = counts(path)
    response = client.post(URL, headers=GLOBAL, json=body)
    assert response.status_code == 200
    result = response.get_json()
    assert result["state"] == "REVIEW_RESOURCE_PREPARED"
    assert result["approval_issued"] is False and result["training_eligible"] is False
    assert result["training_started"] is False
    assert result["human_rights_decision"] == result["human_target_decision"] == "PENDING"
    assert result["input_sha256"] == hashlib.sha256(json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    with app.test_request_context(URL, headers=GLOBAL, environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        principal = p.resolve_local_workspace_principal(module="owned_training", action="write")
        expected = training_review.training_review_approval_resource(
            principal=principal, expected_scope={**_scope(global_scope=True), "entity_label": "GLOBAL / ALL"},
            submission_id=body["submission_id"], source_evidence_refs=body["source_evidence_refs"],
            prompt_messages=body["prompt_messages"], reviewer_approved_target=body["proposed_target"],
            context=body["context"], rights_declaration=body["proposed_rights_declaration"],
        )
    assert result["resource"] == expected
    assert result["source_evidence"][0]["evidence_ref"] == body["source_evidence_refs"][0]
    assert result["scope_permission_audit_id"] and result["preview_permission_audit_id"]
    assert counts(path) == before and gate._approvals == {}
    assert not gate.check(p.OperationType.MODEL_TRAIN, resource=expected, exact_approval_required=True).allowed


@pytest.mark.parametrize("extra", ["actor_id", "principal", "approval_token", "training_eligible", "expected_scope"])
def test_client_authority_fields_are_rejected(route, extra):
    client, _, gate, body, path = route
    before = counts(path)
    assert client.post(URL, headers=GLOBAL, json={**body, extra: True}).status_code == 400
    assert counts(path) == before and gate._approvals == {}


@pytest.mark.parametrize("remote,headers,open_workspace", [
    ("192.0.2.5", {}, True), ("127.0.0.1", {"X-Forwarded-For": "127.0.0.1"}, True),
    ("127.0.0.1", {"X-Actor-ID": "1"}, True), ("127.0.0.1", {}, False),
])
def test_untrusted_transport_cannot_prepare_resource(route, remote, headers, open_workspace):
    client, app, _, body, path = route
    app.config["LUMENIS_OPEN_WORKSPACE"] = open_workspace
    before = counts(path)
    response = client.post(URL, headers={**GLOBAL, **headers}, json=body,
                           environ_overrides={"REMOTE_ADDR": remote})
    assert response.status_code == 401 and response.get_json()["code"] == "AUTH_REQUIRED"
    assert counts(path) == before


def test_wrong_domain_or_tampered_source_denies(route):
    client, _, _, body, path = route
    result = client.post(URL, headers={**GLOBAL, "X-Domain-Id": "BMP", "X-Product-Id": "BMP"}, json=body)
    assert result.status_code == 400
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE app_evidence_records SET outputs_json='{}'")
    result = client.post(URL, headers=GLOBAL, json=body)
    assert result.status_code == 400 and result.get_json()["ok"] is False


def test_changed_target_changes_resource_and_neither_is_approved(route):
    client, _, gate, body, _ = route
    first = client.post(URL, headers=GLOBAL, json=body).get_json()
    second = client.post(URL, headers=GLOBAL, json={**body, "proposed_target": body["proposed_target"] + " Revised."}).get_json()
    assert first["resource"] != second["resource"] and gate._approvals == {}


def test_duplicate_keys_and_oversized_body_are_rejected(route):
    client, _, _, body, path = route
    before = counts(path)
    duplicate = json.dumps(body)[:-1] + ',"context":"different"}'
    assert client.post(URL, headers=GLOBAL, data=duplicate, content_type="application/json").status_code == 400
    assert client.post(URL, headers=GLOBAL, data=b" " * 65537, content_type="application/json").status_code == 400
    assert counts(path) == before


def test_canonical_preview_denial_is_enforced(route):
    client, _, gate, body, path = route
    gate.revoke_permission(p.PermissionLevel.PLAN)
    before = counts(path)
    result = client.post(URL, headers=GLOBAL, json=body)
    assert result.status_code == 403 and result.get_json()["code"] == "OWNED_TRAINING_PREVIEW_DENIED"
    assert counts(path) == before


def test_app_write_router_maps_only_exact_preparation_path():
    module = ast.parse(Path("app.py").read_text(encoding="utf-8-sig"))
    function = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "_pg_resolve_operation_type")
    namespace = {"OperationType": p.OperationType, "re": re}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "app.py", "exec"), namespace)
    resolve = namespace["_pg_resolve_operation_type"]
    assert resolve(URL, "POST") is p.OperationType.OWNED_TRAINING_REVIEW_PREVIEW
    assert resolve(URL + "/submit", "POST") is p.OperationType.DB_WRITE
    assert resolve("/api/model-train", "POST") is not p.OperationType.OWNED_TRAINING_REVIEW_PREVIEW
