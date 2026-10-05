from types import SimpleNamespace

import pytest
from flask import Flask

import ai_api
from lumenis.shared.agents.skills import execution as skill_execution


@pytest.fixture
def ai_client():
    app = Flask("ai-api-route-contract")
    ai_api.register_ai_api(app)
    return app.test_client()


def test_ai_analyze_requires_real_source_text(ai_client, monkeypatch):
    monkeypatch.setattr(
        ai_api.intelligence,
        "run_owned_analysis",
        lambda **_kwargs: pytest.fail("Gateway must not run without source text"),
    )

    response = ai_client.post("/api/ai/analyze", json={"note_id": "note-1"})

    assert response.status_code == 400
    assert response.get_json() == {
        "ok": False,
        "status": "INVALID_INPUT",
        "code": "ANALYSIS_TEXT_REQUIRED",
        "provider": "owned",
        "note_id": "note-1",
        "analysis": None,
    }


def test_ai_analyze_returns_owned_runtime_unavailable_without_provider_fallback(ai_client, monkeypatch):
    monkeypatch.setattr(ai_api.intelligence, "chat", lambda *_a, **_k: pytest.fail("provider fallback called"))

    response = ai_client.post("/api/ai/analyze", json={
        "note_id": "note-1", "text": "真实来源正文", "type": "sentiment", "provider": "ollama",
    })

    assert response.status_code == 503
    body = response.get_json()
    assert body["ok"] is False
    assert body["status"] == "UNAVAILABLE"
    assert body["code"] == "OWNED_RUNTIME_NOT_BOUND"
    assert body["provider"] == "owned"
    assert body["note_id"] == "note-1"
    assert body["analysis"] is None


def test_ai_analyze_rejects_unknown_analysis_type(ai_client, monkeypatch):
    monkeypatch.setattr(
        ai_api.intelligence,
        "run_owned_analysis",
        lambda **_kwargs: pytest.fail("Gateway must not run for an unsupported analysis type"),
    )

    response = ai_client.post("/api/ai/analyze", json={"text": "source", "type": "invented"})

    assert response.status_code == 400
    assert response.get_json()["code"] == "ANALYSIS_TYPE_UNSUPPORTED"


def test_ai_tasks_shared_route_preserves_task_engine_and_skill_execution(ai_client, monkeypatch):
    class FakeEngine:
        def create_task(self, user_input, *, context, created_by):
            return {"task_id": "task-1", "input": user_input, "context": context, "created_by": created_by}

    monkeypatch.setattr(ai_api, "_get_engine", lambda: FakeEngine())
    seen = []

    def run_execution_chain(**kwargs):
        seen.append(kwargs)
        return SimpleNamespace(
            execution_id="exec-1", status=SimpleNamespace(value="completed"),
            evidence_record={"ok": True},
        )

    monkeypatch.setattr(skill_execution, "run_execution_chain", run_execution_chain)

    task_response = ai_client.post("/api/ai/tasks", json={
        "input": "Create a task", "context": {"domain": "cth"}, "created_by": "user-1",
    })
    skill_response = ai_client.post("/api/ai/tasks", json={
        "skill_id": "shared.content_project", "task": "Create a project", "input": {"brief": "b1"},
    })

    assert task_response.status_code == 200
    assert task_response.get_json()["task"]["task_id"] == "task-1"
    assert skill_response.status_code == 200
    assert skill_response.get_json() == {
        "ok": True, "execution_id": "exec-1", "status": "completed", "evidence_recorded": True,
    }
    assert seen[0]["skill_id"] == "shared.content_project"
    assert seen[0]["input_payload"] == {"brief": "b1"}


def test_ai_tasks_list_combines_owners_and_surfaces_storage_failures(ai_client, monkeypatch):
    class FakeEngine:
        def list_tasks(self, *, status, limit, offset):
            return [{"task_id": "task-1", "status": status or "ready", "created_at": "2026-10-06T01:00:00Z"}]

    monkeypatch.setattr(ai_api, "_get_engine", lambda: FakeEngine())
    monkeypatch.setattr(
        skill_execution, "query_executions",
        lambda **kwargs: [{"execution_id": "exec-1", "status": kwargs.get("status") or "completed",
                           "created_at": "2026-10-06T02:00:00Z"}],
    )

    response = ai_client.get("/api/ai/tasks?limit=10")

    assert response.status_code == 200
    body = response.get_json()
    assert [item["task_kind"] for item in body["tasks"]] == ["SKILL_EXECUTION", "TASK_ENGINE"]
    assert len(body["task_engine_tasks"]) == 1
    assert len(body["skill_executions"]) == 1

    def failed_query(**_kwargs):
        raise OSError("database path detail must not be returned")

    monkeypatch.setattr(skill_execution, "query_executions", failed_query)
    failed = ai_client.get("/api/ai/tasks")
    assert failed.status_code == 503
    assert failed.get_json() == {"ok": False, "code": "AI_TASK_LIST_UNAVAILABLE"}


def test_application_registers_one_ai_tasks_rule(app):
    rules = [rule for rule in app.url_map.iter_rules() if rule.rule == "/api/ai/tasks"]

    assert len(rules) == 1
    assert {"GET", "POST"}.issubset(rules[0].methods)
