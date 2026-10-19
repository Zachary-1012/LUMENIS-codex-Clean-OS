"""Contract tests for the TaskEngine-to-canonical-Gateway bridge.

All Gateway calls are mocked: these tests never contact a model provider.
"""

import threading

import pytest

import ai_task_engine as task_engine_module
from ai_task_engine import TaskEngine
from lumenis.system.ai_gateway import core as ai_gateway


@pytest.fixture(autouse=True)
def _offline_provider_configuration(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "auto")
    monkeypatch.delenv("ALLOW_CLOUD_AI", raising=False)
    monkeypatch.setattr(
        ai_gateway,
        "ai_status",
        lambda: pytest.fail("TaskEngine must not inspect retired provider status"),
    )
    for key in (
        "ZHIPU_API_KEY",
        "ARK_API_KEY",
        "DASHSCOPE_API_KEY",
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)


def _engine():
    # The bridge and result mappers do not need TaskEngine's database lifecycle.
    return object.__new__(TaskEngine)


def test_bridge_uses_owned_gateway_and_preserves_task_context(monkeypatch):
    calls = []

    def fake_owned_analysis(**kwargs):
        calls.append(kwargs)
        return {
            "ok": True, "status": "COMPLETED", "provider": "owned",
            "analysis": "Model answer", "model": "owned-test",
        }

    monkeypatch.setattr(ai_gateway, "run_owned_analysis", fake_owned_analysis)
    monkeypatch.setattr(ai_gateway, "chat", lambda *_a, **_k: pytest.fail("legacy chat called"))

    result = TaskEngine._call_ai_with_fallback(
        _engine(), "analyze", "question", {"items": 2}
    )

    assert result == {
        "status": "completed",
        "provider": "owned",
        "response": "Model answer",
        "model": "owned-test",
    }
    assert calls[0]["analysis_type"] == "task_engine_analyze"
    assert "analyze" in calls[0]["text"] and "question" in calls[0]["text"]
    assert '"items": 2' in calls[0]["text"]


def test_explicit_retired_provider_selection_never_reaches_legacy_chat(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "zhipu")
    calls = []

    def fake_owned_analysis(**kwargs):
        calls.append(kwargs)
        return {
            "ok": False, "status": "UNAVAILABLE", "code": "OWNED_RUNTIME_NOT_BOUND",
            "provider": "owned", "analysis": None,
        }

    monkeypatch.setattr(ai_gateway, "run_owned_analysis", fake_owned_analysis)
    monkeypatch.setattr(ai_gateway, "chat", lambda *_a, **_k: pytest.fail("retired chat called"))

    result = TaskEngine._call_ai_with_fallback(_engine(), "analyze", "input", {})

    assert calls and calls[0]["analysis_type"] == "task_engine_analyze"
    assert result["status"] == "unavailable"
    assert result["provider"] == "owned"


@pytest.mark.parametrize(
    ("gateway_result", "expected_status", "expected_error"),
    [
        ({"ok": False, "status": "UNAVAILABLE", "code": "OWNED_RUNTIME_NOT_BOUND", "provider": "owned"}, "unavailable", "OWNED_RUNTIME_NOT_BOUND"),
        ({"ok": False, "status": "BUDGET_BLOCKED", "code": "AI_BUDGET_BLOCKED", "provider": "owned"}, "budget_blocked", "AI_BUDGET_BLOCKED"),
        ({"ok": True, "status": "COMPLETED", "provider": "owned", "analysis": "   "}, "error", "OWNED_ANALYSIS_NOT_COMPLETED"),
        ({"ok": False, "status": "ERROR", "code": "OWNED_EXECUTION_FAILED", "provider": "owned"}, "error", "OWNED_EXECUTION_FAILED"),
    ],
)
def test_gateway_noncompletion_states_are_not_model_success(
    monkeypatch, gateway_result, expected_status, expected_error
):
    monkeypatch.setattr(ai_gateway, "run_owned_analysis", lambda **_kwargs: gateway_result)
    monkeypatch.setattr(ai_gateway, "chat", lambda *_a, **_k: pytest.fail("legacy chat called"))

    result = TaskEngine._call_ai_with_fallback(_engine(), "analyze", "input", {})

    assert result["status"] == expected_status
    assert result["provider"] == "owned"
    assert result["response"] is None
    assert result["error"] == expected_error


def test_gateway_exception_is_safe_error_state(monkeypatch):
    def fail(*_args, **_kwargs):
        raise RuntimeError("secret=must-not-be-recorded")

    monkeypatch.setattr(ai_gateway, "run_owned_analysis", fail)

    result = TaskEngine._call_ai_with_fallback(_engine(), "analyze", "input", {})

    assert result["status"] == "error"
    assert result["provider"] == "unknown"
    assert result["error"] == "RuntimeError"
    assert "must-not-be-recorded" not in repr(result)


@pytest.mark.parametrize("requested_provider", ["auto", "ollama", "zhipu"])
def test_provider_selection_does_not_change_owned_taskengine_route(monkeypatch, requested_provider):
    monkeypatch.setenv("AI_PROVIDER", requested_provider)
    monkeypatch.setenv("ZHIPU_API_KEY", "placeholder-test-key-never-used")
    monkeypatch.setattr(
        ai_gateway,
        "chat",
        lambda *_args, **_kwargs: pytest.fail("legacy provider route reached from TaskEngine"),
    )
    monkeypatch.setattr(ai_gateway, "run_owned_analysis", lambda **_kwargs: {
        "ok": False, "status": "UNAVAILABLE", "code": "OWNED_RUNTIME_NOT_BOUND",
        "provider": "owned", "analysis": None,
    })

    result = TaskEngine._call_ai_with_fallback(_engine(), "analyze", "input", {})

    assert result["status"] == "unavailable"
    assert result["provider"] == "owned"
    assert result["response"] is None


def test_gateway_timeout_is_reported(monkeypatch):
    release_call = threading.Event()

    def slow_owned_analysis(**_kwargs):
        release_call.wait(timeout=1)
        return {
            "ok": True, "status": "COMPLETED", "provider": "owned",
            "analysis": "late answer", "model": "owned-test",
        }

    monkeypatch.setattr(ai_gateway, "run_owned_analysis", slow_owned_analysis)
    monkeypatch.setattr(task_engine_module, "_AI_CALL_TIMEOUT_SECONDS", 0.01)

    result = TaskEngine._call_ai_with_fallback(_engine(), "analyze", "input", {})
    release_call.set()

    assert result["status"] == "timeout"
    assert result["provider"] == "unknown"
    assert result["response"] is None


@pytest.mark.parametrize(
    ("status", "provider", "error"),
    [
        ("unavailable", "owned", "OWNED_RUNTIME_NOT_BOUND"),
        ("error", "owned", "OWNED_ANALYSIS_RESULT_INVALID"),
        ("error", "unknown", "RuntimeError"),
        ("timeout", "unknown", "Gateway timeout"),
    ],
)
def test_noncompletion_state_reaches_task_without_fake_ai_response(status, provider, error):
    outcome = {"status": status, "provider": provider, "response": None}
    if error:
        outcome["error"] = error
    engine = _engine()
    engine._try_ai_analyze = lambda _text: outcome

    analysis = engine._execute_analysis({"user_input": "question"}, "reason")
    assist = engine._execute_ai_assist({"user_input": "question"}, "reason")

    assert analysis["ai_analysis"] is None
    assert analysis["ai_analysis_status"] == "not_requested"
    assert analysis["analysis_provider"] == "unavailable"
    assert assist["ai_response"] is None
    assert assist["ai_status"] == status
    assert assist["provider"] == provider
    if error:
        assert not analysis.get("ai_analysis_error")
        assert assist["ai_error"] == error


@pytest.mark.parametrize(
    ("agent_id", "result_data", "expected_code"),
    [
        ("assistant_agent", {
            "ai_response": None, "ai_status": "unavailable", "provider": "owned",
            "ai_error": "OWNED_RUNTIME_NOT_BOUND",
        }, "OWNED_RUNTIME_NOT_BOUND"),
        ("analysis_agent", {
            "ai_analysis": None, "ai_analysis_status": "unavailable",
            "analysis_provider": "owned", "ai_analysis_error": "OWNED_RUNTIME_NOT_BOUND", "ai_required": True,
        }, "OWNED_RUNTIME_NOT_BOUND"),
    ],
)
def test_ai_dependent_task_is_not_marked_succeeded_without_owned_result(
    monkeypatch, agent_id, result_data, expected_code,
):
    monkeypatch.setattr(task_engine_module, "_guard_generic_task_access", lambda *_args: None)
    engine = _engine()
    task = {
        "task_id": "task-1", "agent_id": agent_id, "intent": "analyze",
        "user_input": "question", "skill_id": None,
    }
    state = {"status": "ready"}
    evidence = []
    traces = []
    engine._db_get_task = lambda _task_id: {**task, **state}
    engine._db_add_step = lambda *_args, **_kwargs: "step-1"
    engine._now = lambda: "2026-10-06T00:00:00Z"
    engine._db_update_task = lambda _task_id, **kwargs: state.update(kwargs)
    engine._db_update_step = lambda *_args, **_kwargs: None
    engine._db_add_evidence = lambda *args, **kwargs: evidence.append((args, kwargs))
    engine._db_add_trace = lambda *args, **kwargs: traces.append((args, kwargs))
    engine._dispatch_execution = lambda *_args: result_data
    engine._verify_result = lambda *_args: pytest.fail("unavailable AI must not pass result verification")

    result = engine._execute_once("task-1", 0)

    assert state["status"] == "failed"
    assert state["error"] == expected_code
    assert result["status"] == "failed"
    assert '"execution_status": "FAILED"' in result["result_json"]
    assert evidence and evidence[0][0][1] == "owned_ai_unavailable"
    assert traces and traces[0][0][3] == "error"


def test_unscoped_data_query_never_reads_business_database_or_calls_ai(monkeypatch):
    monkeypatch.setattr(task_engine_module, "get_db", lambda: pytest.fail("unscoped database read"))
    engine = _engine()
    engine._try_ai_summarize = lambda *_args: pytest.fail("unscoped AI call")
    for method in (engine._execute_data_query, engine._execute_report):
        result = method({"user_input": "count"}, "query_data")
        assert result["error"] == "SCOPED_SOURCE_OWNER_REQUIRED"
        assert result["business_outcome"] == "NOT_OBSERVED"
        assert result["next_action"]["path"] == "/api/experience/reports/source-brief/start"
