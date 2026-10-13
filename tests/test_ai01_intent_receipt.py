"""AI-01 submit receipt: ``evidence_recorded`` is true only after Evidence read-back.

AI-01.md sections 1-3: a real execution returns ``execution_id`` and states whether
Evidence was recorded; no fake AI output or fabricated trace. Signed: 阿康1（bot）.
"""
import dataclasses
import importlib
import json
import types

import pytest
from flask import Flask


@pytest.fixture
def intent_client(tmp_path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "ai01_receipt.db"))
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    import database
    importlib.reload(database)
    database.DB_PATH = str(tmp_path / "ai01_receipt.db")
    database.init_db()
    from lumenis.system import security as permission_gate
    importlib.reload(permission_gate)
    prior = permission_gate.is_testing_bypass_enabled()
    permission_gate.set_testing_bypass(False)
    import experience_runtime
    importlib.reload(experience_runtime)
    trusted = {"value": ("cth", "CTH", "actor:test")}
    monkeypatch.setattr(experience_runtime, "_ai_intent_trusted_domain", lambda: trusted["value"])
    app = Flask(__name__)
    app.register_blueprint(experience_runtime.experience_bp)
    gate = experience_runtime.get_permission_gate()
    gate._enabled_permissions = {
        permission_gate.PermissionLevel.READ, permission_gate.PermissionLevel.ANALYZE,
    }
    gate.revoke_all_approvals()
    state = {"mode": "real", "trusted": trusted, "calls": 0}

    def _fake_run(*_a, **_k):
        state["calls"] += 1
        state["kwargs"] = _k
        from lumenis.shared.evidence import EvidenceStore
        execution_id = "exec-receipt-1"
        bound = execution_id if state["mode"] != "foreign" else "exec-other"
        if state["mode"] == "missing":
            return types.SimpleNamespace(
                execution_id=execution_id, status=types.SimpleNamespace(value="completed"),
                evidence_record={"ok": True, "evidence_id": "ev-does-not-exist"})
        ev, _new = EvidenceStore().add_evidence(
            source_type="skill_execution", source_url=f"skill://zbc.generic_analysis/{bound}",
            source_id=bound, raw_content=json.dumps({"execution_id": bound, "status": "completed"}),
            subject_scope="GLOBAL / ALL", task_id=bound, trace_id=bound,
            provider="lumenis.shared.agents.skills.execution", domain_id="CTH", product_id="CTH",
        )
        return types.SimpleNamespace(
            execution_id=execution_id, status=types.SimpleNamespace(value="completed"),
            evidence_record={"ok": True, "evidence_id": ev.evidence_id, "is_new": True})

    from lumenis.shared.agents.skills import execution as skill_execution
    monkeypatch.setattr(skill_execution, "run_execution_chain", _fake_run)
    yield app.test_client(), state, experience_runtime
    permission_gate.set_testing_bypass(prior)


def _submit(cli):
    return cli.post("/api/experience/ai/intent", json={"task": "分析当前范围", "action_type": "ANALYZE"})


def test_evidence_read_back_for_same_execution_is_recorded(intent_client):
    cli, _state, _rt = intent_client
    body = _submit(cli).get_json()
    assert body["ok"] is True, body
    assert body["permission_status"] == "granted"
    assert body["execution_id"] == "exec-receipt-1"
    assert body["evidence_recorded"] is True
    assert body["ai_is_derivative"] is True


def test_ok_flag_without_stored_evidence_is_not_recorded(intent_client):
    cli, state, _rt = intent_client
    state["mode"] = "missing"
    body = _submit(cli).get_json()
    assert body["execution_id"] == "exec-receipt-1"
    assert body["evidence_recorded"] is False


def test_evidence_bound_to_another_execution_is_not_recorded(intent_client):
    cli, state, _rt = intent_client
    state["mode"] = "foreign"
    body = _submit(cli).get_json()
    assert body["evidence_recorded"] is False


def test_tampered_evidence_content_is_not_recorded(intent_client, monkeypatch):
    cli, _state, _rt = intent_client
    from lumenis.shared.evidence import EvidenceStore
    original = EvidenceStore.get_evidence

    def _tampered(self, evidence_id):
        ev = original(self, evidence_id)
        return dataclasses.replace(ev, raw_content=ev.raw_content + " ") if ev else ev

    monkeypatch.setattr(EvidenceStore, "get_evidence", _tampered)
    body = _submit(cli).get_json()
    assert body["evidence_recorded"] is False




def test_body_fields_beyond_task_and_action_type_are_rejected(intent_client):
    cli, state, _rt = intent_client
    for extra in ({"domain": "BMP"}, {"product": "CTH"}, {"user_id": "x"}, {"skill_id": "s"}, {"input": {}}):
        r = cli.post("/api/experience/ai/intent", json={"task": "分析", "action_type": "ANALYZE", **extra})
        assert r.status_code == 400 and r.get_json()["ok"] is False
    assert state["calls"] == 0


def test_global_or_unresolved_scope_is_not_executable_and_writes_no_evidence(intent_client):
    cli, state, _rt = intent_client
    from lumenis.shared.evidence import EvidenceStore
    before = len(EvidenceStore().list_evidence(source_type="skill_execution"))
    state["trusted"]["value"] = None
    body = _submit(cli).get_json()
    assert body["ok"] is False and body["status"] == "not_executable"
    assert body["code"] == "AI_INTENT_FOCUS_SCOPE_REQUIRED" and body["evidence_recorded"] is False
    assert "execution_id" not in body and state["calls"] == 0
    assert len(EvidenceStore().list_evidence(source_type="skill_execution")) == before


def test_bmp_focus_executes_under_zbmp_identity(intent_client):
    cli, state, _rt = intent_client
    state["trusted"]["value"] = ("zbmp", "ZBMP", "actor:test")
    body = _submit(cli).get_json()
    assert body["ok"] is True
    assert (state["kwargs"]["domain"], state["kwargs"]["product"]) == ("ZBMP", "ZBMP")
    assert state["kwargs"]["user_id"] == "actor:test" and state["kwargs"]["input_payload"] == {}


def test_trusted_domain_comes_only_from_server_scope_resolver(monkeypatch):
    import types as _t
    import experience_runtime as rt
    importlib.reload(rt)
    decision = _t.SimpleNamespace(principal_ref="actor:7", actor_id=7)

    def _resolver(scope=None, exc=None):
        def _call(action, *, module, include_decision):
            assert (action, module, include_decision) == ("read", "content", True)
            if exc:
                raise exc
            return {"id": 7}, scope, decision
        return _call

    monkeypatch.setattr(rt, "_content_project_scope", _resolver(exc=RuntimeError("AUTH_REQUIRED")))
    assert rt._ai_intent_trusted_domain() is None
    monkeypatch.setattr(rt, "_content_project_scope", _resolver({"domain_id": "cth", "global_scope": True}))
    assert rt._ai_intent_trusted_domain() is None
    monkeypatch.setattr(rt, "_content_project_scope", _resolver({"domain_id": "cth", "global_scope": False}))
    assert rt._ai_intent_trusted_domain() == ("cth", "CTH", "actor:7")
    monkeypatch.setattr(rt, "_content_project_scope", _resolver({"domain_id": "zbmp", "global_scope": False}))
    assert rt._ai_intent_trusted_domain() == ("zbmp", "ZBMP", "actor:7")
