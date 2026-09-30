"""Real isolated report route, canonical data, principal and recovery chain."""
import ast
import sqlite3
from pathlib import Path

import pytest
from flask import Flask, jsonify, request

from tests.test_source_brief_job import job_db, _source
from lumenis.system import security
from lumenis.system.security import permission as p

URL = "/api/experience/reports/source-brief"
GLOBAL = {"X-Domain-Id": "CTH", "X-Product-Id": "CTH", "X-Lumenis-Context-Mode": "GLOBAL_ALL"}


@pytest.fixture
def client(job_db, monkeypatch):
    import experience_runtime
    import lumenis.auth.service
    import subject_registry

    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(p, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.setattr(lumenis.auth.service, "get_current_user", lambda: None)
    gate = p.PermissionGate()
    monkeypatch.setattr(p, "get_permission_gate", lambda: gate)
    monkeypatch.setattr(security, "get_permission_gate", lambda: gate)
    entry, _ = subject_registry.add_subject({
        "domain_id": "CTH", "subject_type": "company",
        "name_en": "Registered Venue", "name_zh": "已注册商业主体",
    })
    with sqlite3.connect(job_db) as con:
        con.row_factory = sqlite3.Row
        _source(con, subject=entry["subject_id"])
        con.commit()
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    app.register_blueprint(experience_runtime.experience_bp)
    # Include the actual app operation resolver and gate, without importing startup.
    tree = ast.parse(Path("app.py").read_text(encoding="utf-8-sig"))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and
             node.name in {"_pg_resolve_operation_type", "_permission_gate_write_check"}]
    for node in nodes:
        node.decorator_list = []
    namespace = dict(request=request, jsonify=jsonify, OperationType=p.OperationType,
                     _PG_WRITE_METHODS={"POST", "PUT", "PATCH", "DELETE"},
                     _PG_BYPASS_PATHS=set(), _pg=gate)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "app.py", "exec"), namespace)
    app.before_request(namespace["_permission_gate_write_check"])
    return app.test_client(), app, job_db, entry, gate


def test_generate_reopen_focus_global_and_recovery(client):
    api, app, db, entry, _gate = client
    focus = {**GLOBAL, "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": entry["subject_id"]}
    first = api.post(URL + "/generate", headers=focus, json={})
    assert first.status_code == 200, first.get_json()
    result = first.get_json()["result"]
    assert result["artifact_outcome"]["source_count"] == 1
    assert result["review_status"] == "HUMAN_PENDING"
    assert result["multimodal"]["state"] == "unavailable"
    job_id = result["job_id"]
    reopened = app.test_client().get(URL + "/jobs/" + job_id, headers=focus)
    assert reopened.status_code == 200 and reopened.get_json()["result"] == result
    assert api.get(URL + "/jobs/" + job_id, headers=GLOBAL).status_code == 403
    recovered = api.post(URL + "/generate", headers=focus, json={"resume_job_id": job_id})
    assert recovered.status_code == 200, recovered.get_json()
    assert recovered.get_json()["result"] == result
    global_job = api.post(URL + "/generate", headers=GLOBAL, json={})
    assert global_job.status_code == 200
    assert global_job.get_json()["result"]["source_brief"]["scope"]["global"] is True
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM evaluation_records").fetchone()[0] == 6
        assert con.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0] == 2


@pytest.mark.parametrize("body", [{"actor_id": "owner"}, {"multimodal_result": {"state": "complete"}},
                                   {"limit": True}, {"limit": 0}, {"job_id": "chosen-id"}])
def test_client_cannot_supply_trust_or_invalid_limits(client, body):
    api, _app, db, _entry, _gate = client
    response = api.post(URL + "/generate", headers=GLOBAL, json=body)
    assert response.status_code == 400
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0] == 0


@pytest.mark.parametrize("extra", [{"Origin": "https://foreign.invalid"}, {"X-Actor-ID": "23"},
                                   {"X-Forwarded-For": "127.0.0.1"}])
def test_remote_or_forged_identity_cannot_write_report(client, extra):
    api, _app, db, _entry, _gate = client
    result = api.post(URL + "/generate", headers={**GLOBAL, **extra}, json={})
    assert result.status_code in {401, 403}
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0] == 0


def test_report_effect_denied_and_nonexistent_resume_never_creates(client):
    api, _app, db, _entry, gate = client
    missing = api.post(URL + "/generate", headers=GLOBAL, json={"resume_job_id": "brief-not-found"})
    assert missing.status_code == 404
    gate.revoke_permission(p.PermissionLevel.ANALYZE)
    denied = api.post(URL + "/generate", headers=GLOBAL, json={})
    assert denied.status_code == 403
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0] == 0
