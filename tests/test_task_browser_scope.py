"""Isolated C2 dispatch regressions; no browser, model, worker or DB is started."""
import pytest

from agent_runtime import agent_zero_gui_executor as retired_worker
from ai_task_engine import TaskEngine


@pytest.fixture
def engine():
    # These dispatch/readback boundaries do not need a database or runtime.
    return object.__new__(TaskEngine)


def withdrawn_task():
    return {
        "task_id": "historical-computer-task", "agent_id": "browser_agent",
        "context": {
            "execution_mode": "agent_zero_gui",
            "execution_schema": "lumenis.computer-execution-request/v1",
        },
        "parameters": {"_agent_zero_gui": {"state": "submitted"}},
    }


def test_withdrawn_marker_never_dispatches_a_configured_os_worker(engine, monkeypatch):
    def forbidden():
        pytest.fail("withdrawn OS executor was resolved")

    monkeypatch.setattr(retired_worker, "get_agent_zero_gui_executor", forbidden)
    result = engine._execute_browser(withdrawn_task(), "browser_read")
    assert result["task_outcome"] == "UNAVAILABLE"
    assert result["failure_code"] == "GENERAL_OS_EXECUTION_WITHDRAWN"
    assert result["external_submission"] is False


def test_historical_model_result_cannot_accept_withdrawn_os_outcome(engine, monkeypatch):
    monkeypatch.setattr(retired_worker, "get_agent_zero_gui_executor",
                        lambda: pytest.fail("OS verification executor was resolved"))
    accepted, scope = engine._verify_owner_outcome(
        withdrawn_task(), {"executor": "agent_zero_gui", "task_outcome": "COMPLETED"},
    )
    assert accepted is False
    assert scope == "GENERAL_OS_EXECUTION_WITHDRAWN"


def test_unbound_product_browser_is_an_explicit_execution_failure(engine):
    task = {"task_id": "normal-browser-task", "agent_id": "browser_agent", "context": {}}
    result = engine._execute_browser(task, "browser_read")
    assert result["status"] == "unavailable"
    assert result["error"] == "INTERNAL_BROWSER_TASK_BINDING_NOT_BOUND"
    assert result["external_submission"] is False
    assert engine._verify_owner_outcome(task, result)[0] is False
