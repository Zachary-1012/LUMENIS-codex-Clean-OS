"""Focused result-state tests for the canonical Skill execution wrappers."""
from __future__ import annotations

import importlib
import sys
import types
from types import SimpleNamespace

import pytest

from lumenis.shared.agents.skills import execution


def _stub_osai(monkeypatch, *, available=False, result=None, error=None):
    class Adapter:
        def __init__(self):
            self.available = available

        def invoke_skill(self, **_kwargs):
            if error is not None:
                raise error
            return result

    module = types.ModuleType("lumenis_skill_adapter")
    module.get_skill_adapter = Adapter
    monkeypatch.setitem(sys.modules, "lumenis_skill_adapter", module)


def _stub_registry(monkeypatch, metadata=None):
    registry = importlib.import_module("lumenis.shared.agents.skills.registry")

    class FakeRegistry:
        def get(self, skill_id):
            return metadata if metadata and metadata.skill_id == skill_id else None

    monkeypatch.setattr(registry, "get_skill_registry", lambda: FakeRegistry())


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        pytest.param({"status": "completed", "result": "done"}, True, id="completed"),
        pytest.param({"status": "no_records", "records": []}, True, id="explicit-no-records"),
        pytest.param(0, True, id="numeric-zero-is-a-result"),
        pytest.param({"value": 0}, True, id="wrapped-numeric-zero-is-a-result"),
        pytest.param({"ok": True}, False, id="transport-metadata-only"),
        pytest.param({"status": "success"}, False, id="status-only"),
        pytest.param({"message": "done"}, False, id="message-only"),
        pytest.param({"ok": True, "value": None}, False, id="empty-value"),
        pytest.param({"status": "error", "message": "business error"}, False, id="error"),
        pytest.param({"status": "blocked"}, False, id="blocked"),
        pytest.param({"state": "pending"}, False, id="pending"),
        pytest.param({"status": "input_required"}, False, id="input-required"),
        pytest.param({"data_state": "partial"}, False, id="partial"),
        pytest.param(None, False, id="none"),
        pytest.param("  ", False, id="empty-string"),
        pytest.param([], False, id="empty-list"),
        pytest.param({}, False, id="empty-dict"),
        pytest.param({"result": {"status": "partial"}}, False, id="nested-business-state"),
    ],
)
def test_custom_handler_result_states(output, expected):
    result = execution.execute_skill(
        execution.SkillExecutionContext(skill_id="custom.test"),
        handler=lambda _ctx: output,
    )

    assert result["success"] is expected
    assert result["source"] == "custom_handler"
    assert result.get("result") == output


def test_custom_handler_exception_is_failure():
    result = execution.execute_skill(
        execution.SkillExecutionContext(skill_id="custom.test"),
        handler=lambda _ctx: (_ for _ in ()).throw(RuntimeError("handler failed")),
    )

    assert result["success"] is False
    assert result["source"] == "custom_handler"
    assert result["error"] == "handler failed"


@pytest.mark.parametrize(
    ("mcp_result", "expected"),
    [
        pytest.param(
            {"ok": True, "state": "CALLED", "result": {"result": {"structuredContent": {"value": 0}, "content": [{"text": "zero result"}]}}},
            True,
            id="structured-result",
        ),
        pytest.param(
            {"ok": True, "state": "CALLED", "result": {"result": {"structuredContent": {"status": "no_records", "records": []}}}},
            True,
            id="explicit-no-records",
        ),
        pytest.param(
            {"ok": True, "state": "CALLED", "result": {"result": {"structuredContent": {"status": "partial"}}}},
            False,
            id="business-partial",
        ),
        pytest.param(
            {"ok": True, "state": "CALLED", "result": {"result": {"isError": True, "content": [{"text": "tool error"}]}}},
            False,
            id="nested-json-rpc-is-error",
        ),
        pytest.param(
            {"ok": True, "state": "CALLED", "result": {"result": {"content": []}}},
            False,
            id="nested-empty-json-rpc-content",
        ),
        pytest.param(
            {"ok": False, "state": "BLOCKED", "result": None, "errors": ["approval required"]},
            False,
            id="transport-blocked",
        ),
        pytest.param({"ok": True, "state": "CALLED", "result": None}, False, id="missing-output"),
    ],
)
def test_registered_mcp_classifies_tool_result_without_invoking_provider(monkeypatch, mcp_result, expected):
    module = types.ModuleType("mcp_skill_runtime")
    module.invoke_registered_mcp = lambda _info, _payload: mcp_result
    monkeypatch.setitem(sys.modules, "mcp_skill_runtime", module)
    skill = execution.SkillRuntimeInfo(
        skill_id="mcp.test", config={"runtime": "mcp"}
    )

    result = execution.execute_skill(
        execution.SkillExecutionContext(skill_id="mcp.test"), skill_info=skill
    )

    assert result["success"] is expected
    assert result["source"] == "registered_mcp"


def test_registered_mcp_exception_is_failure(monkeypatch):
    module = types.ModuleType("mcp_skill_runtime")
    module.invoke_registered_mcp = lambda *_args: (_ for _ in ()).throw(RuntimeError("mcp failed"))
    monkeypatch.setitem(sys.modules, "mcp_skill_runtime", module)
    skill = execution.SkillRuntimeInfo(
        skill_id="mcp.test", config={"runtime": "mcp"}
    )

    result = execution.execute_skill(
        execution.SkillExecutionContext(skill_id="mcp.test"), skill_info=skill
    )

    assert result["success"] is False
    assert result["source"] == "registered_mcp"
    assert result["error"] == "mcp failed"


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        pytest.param({"status": "SUCCESS", "result": {"value": "done"}}, True, id="success"),
        pytest.param({"status": "no_records", "records": []}, True, id="explicit-no-records"),
        pytest.param({"status": "SUCCESS"}, False, id="status-only"),
        pytest.param({"status": "BLOCKED", "error": "approval required"}, False, id="blocked"),
        pytest.param({"status": "PENDING"}, False, id="pending"),
        pytest.param({"status": "PARTIAL"}, False, id="partial"),
        pytest.param(None, False, id="none"),
    ],
)
def test_connected_osai_payload_is_classified(monkeypatch, payload, expected):
    _stub_osai(
        monkeypatch,
        available=True,
        result={"connected": True, "status": "CONNECTED", "error": None, "osai": payload},
    )

    result = execution.execute_skill(
        execution.SkillExecutionContext(skill_id="osai.test")
    )

    assert result["success"] is expected
    assert result["source"] == "osai_adapter"
    assert result.get("result") == payload


def test_osai_exception_falls_through_without_fake_success(monkeypatch):
    _stub_osai(monkeypatch, available=True, error=RuntimeError("osai failed"))
    _stub_registry(monkeypatch)

    result = execution.execute_skill(
        execution.SkillExecutionContext(skill_id="missing.test")
    )

    assert result["success"] is False
    assert result["source"] == "none"
    assert result["code"] == "NO_HANDLER"


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        pytest.param({"status": "completed", "artifact": "draft"}, True, id="completed"),
        pytest.param({"status": "no_records", "records": []}, True, id="explicit-no-records"),
        pytest.param({"status": "input_required"}, False, id="input-required"),
        pytest.param({"status": "partial"}, False, id="partial"),
        pytest.param([], False, id="empty-list"),
    ],
)
def test_builtin_local_result_is_classified_without_external_calls(monkeypatch, output, expected):
    _stub_osai(monkeypatch, available=False)
    metadata = SimpleNamespace(skill_id="shared.sample")
    _stub_registry(monkeypatch, metadata)
    shared = types.ModuleType("lumenis_shared_skills")
    shared.run_shared_skill = lambda *_args, **_kwargs: output
    monkeypatch.setitem(sys.modules, "lumenis_shared_skills", shared)

    result = execution.execute_skill(
        execution.SkillExecutionContext(skill_id="shared.sample"),
        skill_info=execution.SkillRuntimeInfo(skill_id="shared.sample"),
    )

    assert result["success"] is expected
    assert result["source"] == "builtin_local"


def test_builtin_local_exception_and_no_handler_are_failures(monkeypatch):
    _stub_osai(monkeypatch, available=False)
    metadata = SimpleNamespace(skill_id="shared.sample")
    _stub_registry(monkeypatch, metadata)
    shared = types.ModuleType("lumenis_shared_skills")
    shared.run_shared_skill = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("local failed"))
    monkeypatch.setitem(sys.modules, "lumenis_shared_skills", shared)

    failed = execution.execute_skill(
        execution.SkillExecutionContext(skill_id="shared.sample"),
        skill_info=execution.SkillRuntimeInfo(skill_id="shared.sample"),
    )
    assert failed["success"] is False
    assert failed["source"] == "none"
    assert failed["code"] == "NO_HANDLER"

    _stub_registry(monkeypatch)
    missing = execution.execute_skill(
        execution.SkillExecutionContext(skill_id="missing.test")
    )
    assert missing["success"] is False
    assert missing["source"] == "none"
    assert missing["code"] == "NO_HANDLER"
