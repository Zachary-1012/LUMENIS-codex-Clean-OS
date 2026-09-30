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
        lambda: {"enabled": True, "provider": "ollama", "model": "qwen3:4b"},
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


def test_bridge_uses_canonical_chat_and_preserves_provider(monkeypatch):
    calls = []

    def fake_chat(system, user, **kwargs):
        calls.append((system, user, kwargs))
        return "Model answer", "ollama", {"model": "qwen3:4b"}

    monkeypatch.setattr(ai_gateway, "chat", fake_chat)

    result = TaskEngine._call_ai_with_fallback(
        _engine(), "analyze", "question", {"items": 2}
    )

    assert result == {
        "status": "completed",
        "provider": "ollama",
        "response": "Model answer",
        "model": "qwen3:4b",
    }
    system, user, kwargs = calls[0]
    assert "analyze" in user and "question" in user and '"items": 2' in user
    assert "LUMENIS task assistant" in system
    assert kwargs == {
        "level": "medium",
        "use_cache": False,
        "track": True,
        "capability": "daily",
    }


def test_explicit_cloud_selection_remains_owned_by_gateway(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "zhipu")
    calls = []

    def fake_chat(*_args, **_kwargs):
        calls.append(True)
        return "Model answer", "zhipu", {"model": "glm-test"}

    monkeypatch.setattr(ai_gateway, "chat", fake_chat)

    result = TaskEngine._call_ai_with_fallback(_engine(), "analyze", "input", {})

    assert calls == [True]
    assert result["status"] == "completed"
    assert result["provider"] == "zhipu"


@pytest.mark.parametrize(
    ("response", "provider", "metadata", "expected_status"),
    [
        (None, "rule", {"model": "deterministic_rule"}, "rule"),
        (None, "budget_blocked", {}, "budget_blocked"),
        ("   ", "ollama", {"model": "qwen3:4b"}, "empty"),
        (None, "ollama", {"model": "qwen3:4b"}, "empty"),
        (None, "error", {}, "error"),
    ],
)
def test_gateway_noncompletion_states_are_not_model_success(
    monkeypatch, response, provider, metadata, expected_status
):
    monkeypatch.setattr(ai_gateway, "chat", lambda *_args, **_kwargs: (response, provider, metadata))

    result = TaskEngine._call_ai_with_fallback(_engine(), "analyze", "input", {})

    assert result["status"] == expected_status
    assert result["provider"] == provider
    assert result["response"] is None


def test_gateway_exception_is_safe_error_state(monkeypatch):
    def fail(*_args, **_kwargs):
        raise RuntimeError("secret=must-not-be-recorded")

    monkeypatch.setattr(ai_gateway, "chat", fail)

    result = TaskEngine._call_ai_with_fallback(_engine(), "analyze", "input", {})

    assert result["status"] == "error"
    assert result["provider"] == "unknown"
    assert result["error"] == "RuntimeError"
    assert "must-not-be-recorded" not in repr(result)


@pytest.mark.parametrize("requested_provider", ["auto", "ollama"])
def test_disabled_auto_or_unavailable_local_route_skips_chat(monkeypatch, requested_provider):
    monkeypatch.setenv("AI_PROVIDER", requested_provider)
    monkeypatch.setenv("ZHIPU_API_KEY", "placeholder-test-key-never-used")
    monkeypatch.setattr(ai_gateway, "ai_status", lambda: {"enabled": False})
    monkeypatch.setattr(
        ai_gateway,
        "chat",
        lambda *_args, **_kwargs: pytest.fail("disabled local route reached Gateway chat"),
    )

    result = TaskEngine._call_ai_with_fallback(_engine(), "analyze", "input", {})

    assert result["status"] == "rule"
    assert result["provider"] == "rule"
    assert result["response"] is None


def test_gateway_timeout_is_reported(monkeypatch):
    release_call = threading.Event()

    def slow_chat(*_args, **_kwargs):
        release_call.wait(timeout=1)
        return "late answer", "ollama", {"model": "qwen3:4b"}

    monkeypatch.setattr(ai_gateway, "chat", slow_chat)
    monkeypatch.setattr(task_engine_module, "_AI_CALL_TIMEOUT_SECONDS", 0.01)

    result = TaskEngine._call_ai_with_fallback(_engine(), "analyze", "input", {})
    release_call.set()

    assert result["status"] == "timeout"
    assert result["provider"] == "unknown"
    assert result["response"] is None


@pytest.mark.parametrize(
    ("status", "provider", "error"),
    [
        ("rule", "rule", None),
        ("empty", "ollama", None),
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
    assert analysis["ai_analysis_status"] == status
    assert analysis["analysis_provider"] == provider
    assert assist["ai_response"] is None
    assert assist["ai_status"] == status
    assert assist["provider"] == provider
    if error:
        assert analysis["ai_analysis_error"] == error
        assert assist["ai_error"] == error


def test_data_query_exposes_summary_rule_state_without_summary(monkeypatch):
    class _Row:
        def fetchone(self):
            return (3,)

    class _Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, *_args):
            return _Row()

    monkeypatch.setattr(task_engine_module, "get_db", _Connection)
    engine = _engine()
    engine._try_ai_summarize = lambda *_args: {
        "status": "rule",
        "provider": "rule",
        "response": None,
        "model": "deterministic_rule",
    }

    result = engine._execute_data_query({"user_input": "count"}, "query_data")

    assert result["ai_summary"] is None
    assert result["ai_summary_status"] == "rule"
    assert result["ai_summary_provider"] == "rule"
