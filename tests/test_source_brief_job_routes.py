"""Real isolated report route, canonical data, principal and recovery chain."""
import ast
import re
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
    namespace = dict(request=request, jsonify=jsonify, re=re, OperationType=p.OperationType,
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


def test_generate_permission_is_bound_to_server_resolved_domain(client, monkeypatch):
    api, _app, _db, _entry, gate = client
    calls = []
    check = gate.check

    def record_check(*args, **kwargs):
        calls.append(kwargs.copy())
        return check(*args, **kwargs)

    monkeypatch.setattr(gate, "check", record_check)
    response = api.post(URL + "/generate", headers=GLOBAL, json={})

    assert response.status_code == 200, response.get_json()
    generate_checks = [
        call for call in calls
        if call.get("resource") == URL + "/generate"
        and not str(call.get("caller") or "").startswith("http:")
    ]
    assert generate_checks, calls
    assert all(call.get("domain_id") == "cth" for call in generate_checks)


def test_explicit_older_materials_preserve_order_and_reopen(client):
    api, app, db, entry, _gate = client
    with sqlite3.connect(db) as con:
        _source(con, "older-selected", subject=entry["subject_id"])
        _source(con, "new-unselected", subject=entry["subject_id"])
        con.execute("UPDATE canonical_data SET captured_at='2020-01-01' WHERE source_id='older-selected'")
    focus = {**GLOBAL, "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": entry["subject_id"]}
    selected = ["older-selected", "brief-job-source"]
    response = api.post(URL + "/generate", headers=focus, json={"limit": 2, "source_ids": selected})
    assert response.status_code == 200, response.get_json()
    result = response.get_json()["result"]
    assert result["requested_source_ids"] == selected
    assert [r["source_id"] for r in result["source_brief"]["records"]] == selected
    assert result["artifact_outcome"]["source_count"] == 2
    assert app.test_client().get(URL + "/jobs/" + result["job_id"], headers=focus).get_json()["result"] == result


@pytest.mark.parametrize("invalid", ["foreign", "missing", "tampered"])
def test_selected_materials_are_all_or_nothing_before_analysis_or_artifact(client, monkeypatch, invalid):
    import lumenis.shared.reporting.business_brief as business
    api, _app, db, entry, _gate = client
    with sqlite3.connect(db) as con:
        _source(con, "foreign", subject="OTHER-SUBJECT")
        _source(con, "tampered", subject=entry["subject_id"])
        con.execute("UPDATE app_evidence_records SET inputs_json='{}' WHERE id=(SELECT scope_evidence_ref FROM canonical_data WHERE source_id='tampered')")
    monkeypatch.setattr(business, "analyze_business_brief", lambda **kwargs: pytest.fail("invalid materials reached model"))
    focus = {**GLOBAL, "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": entry["subject_id"]}
    response = api.post(URL + "/generate", headers=focus, json={
        "source_ids": ["brief-job-source", invalid], "business_question": "Create an activity plan.",
    })
    assert response.status_code == 403
    assert response.get_json()["code"] == "SOURCE_BRIEF_SELECTED_SOURCE_UNAVAILABLE"
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0] == 0


@pytest.mark.parametrize("body", [{"actor_id": "owner"}, {"multimodal_result": {"state": "complete"}},
                                   {"limit": True}, {"limit": 0}, {"job_id": "chosen-id"},
                                   {"source_ids": None}, {"source_ids": []},
                                   {"source_ids": ["same", "same"]},
                                   {"source_ids": [str(i) for i in range(9)], "business_question": "Analyze the materials."}])
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


def test_report_route_reopens_bound_quality_feedback_without_new_generation(client):
    from lumenis.shared.evaluation.recorder import record_evaluation
    api, _app, db, entry, _gate = client
    focus = {**GLOBAL, "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": entry["subject_id"]}
    result = api.post(URL + "/generate", headers=focus, json={}).get_json()["result"]
    before = result["artifact_outcome"]
    record_evaluation(
        dimension="report", metric_name="business_usefulness", metric_value=None,
        pass_threshold=1, warn_threshold=0.8, source="engineering_runtime_review",
        evidence_ref=f"daily_reports:{result['job_id']}:{before['artifact_hash']}",
        metadata={"job_id": result["job_id"], "artifact_hash": before["artifact_hash"],
                  "scope": result["source_brief"]["scope"],
                  "observations": ["Review a business inference before use."]},
    )
    reopened = api.get(URL + "/jobs/" + result["job_id"], headers=focus)
    assert reopened.status_code == 200
    data = reopened.get_json()["result"]
    assert data["evaluation"]["quality_review"]["records"][0]["status"] == "unknown"
    assert data["artifact_outcome"] == before and data["review_status"] == "HUMAN_PENDING"
    assert api.get(URL + "/jobs/" + result["job_id"], headers=GLOBAL).status_code == 403
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM evaluation_records").fetchone()[0] == 4


@pytest.mark.parametrize("resume", [False, True])
def test_report_recovery_rechecks_each_original_source_scope(client, monkeypatch, resume):
    from lumenis.shared.reporting import saved_work

    api, _app, db, entry, _gate = client
    result = api.post(URL + "/generate", headers=GLOBAL, json={}).get_json()["result"]
    real_authorize = saved_work.authorize

    def authorize(actor, scope, *, action, connection=None):
        if scope["subject_id"] == entry["subject_id"]:
            raise saved_work.SavedWorkError("WORK_PERMISSION_DENIED")
        return real_authorize(actor, scope, action=action, connection=connection)

    monkeypatch.setattr(saved_work, "authorize", authorize)
    if resume:
        response = api.post(URL + "/generate", headers=GLOBAL,
                            json={"resume_job_id": result["job_id"]})
    else:
        response = api.get(URL + "/jobs/" + result["job_id"], headers=GLOBAL)
    assert response.status_code == 403, response.get_json()
    assert response.get_json()["code"] == "WORK_PERMISSION_DENIED"
    assert "result" not in response.get_json()
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM evaluation_records").fetchone()[0] == 3


@pytest.mark.parametrize("change,code", [
    ("denied", "CONTENT_SCOPE_DENIED"),
    ("actor", "SOURCE_BRIEF_ACTOR_MISMATCH"),
    ("scope", "SOURCE_BRIEF_SCOPE_MISMATCH"),
])
def test_reopen_checks_current_context_after_render(client, monkeypatch, change, code):
    import experience_runtime

    api, _app, _db, entry, _gate = client
    result = api.post(URL + "/generate", headers=GLOBAL, json={}).get_json()["result"]
    real_jsonify = experience_runtime.jsonify
    real_context = experience_runtime._source_brief_context
    rendered = False

    def render(*args, **kwargs):
        nonlocal rendered
        response = real_jsonify(*args, **kwargs)
        if args and isinstance(args[0], dict) and args[0].get("ok") is True:
            rendered = True
        return response

    def current_context(*args, **kwargs):
        context = real_context(*args, **kwargs)
        if not rendered:
            return context
        if change == "denied":
            raise PermissionError("CONTENT_SCOPE_DENIED")
        actor_ref, audit_ref, scope, actor = context
        if change == "actor":
            actor_ref = "workspace:changed"
        else:
            scope = {**scope, "global_scope": False, "subject_id": entry["subject_id"]}
        return actor_ref, audit_ref, scope, actor

    monkeypatch.setattr(experience_runtime, "jsonify", render)
    monkeypatch.setattr(experience_runtime, "_source_brief_context", current_context)
    response = api.get(URL + "/jobs/" + result["job_id"], headers=GLOBAL)
    assert response.status_code == 403, response.get_json()
    assert response.get_json()["code"] == code
    assert "result" not in response.get_json()


def test_generate_rechecks_permission_after_projection_before_persistence(client, monkeypatch):
    from lumenis.shared.reporting import source_brief_job

    api, _app, db, _entry, gate = client
    real_build = source_brief_job.build_scoped_source_brief

    def build(*args, **kwargs):
        brief = real_build(*args, **kwargs)
        gate.revoke_permission(p.PermissionLevel.ANALYZE)
        return brief

    monkeypatch.setattr(source_brief_job, "build_scoped_source_brief", build)
    response = api.post(URL + "/generate", headers=GLOBAL, json={})
    assert response.status_code == 403, response.get_json()
    assert "result" not in response.get_json()
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM evaluation_records").fetchone()[0] == 0
