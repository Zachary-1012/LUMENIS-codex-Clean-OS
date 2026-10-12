"""Bounded planner/Gateway contract regressions; mocks do not prove live inference."""
import json
import os
import sys
from dataclasses import replace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_runtime.planner import PlanMode, Planner
from lumenis.system.ai_gateway import core as ai_gateway
from lumenis.system.ai_gateway.owned_service import OwnedServiceRequest


def _step(**overrides):
    value = {
        "action": "read source",
        "tool": "source_read",
        "params": {"source": "existing"},
        "expected_output": "source summary",
        "risk_level": "low",
    }
    value.update(overrides)
    return value


def _json_steps(*steps):
    return json.dumps({"steps": list(steps)}, ensure_ascii=False, allow_nan=False)


def _request_factory(*, system_prompt, user_payload, response_schema_json, max_output_tokens):
    return OwnedServiceRequest(
        operation="agent_plan",
        request_id="unit-agent-plan-request",
        job_id="unit-agent-plan-job",
        actor_ref="unit-actor",
        domain_id="cth",
        scope="subject:unit-subject",
        source_use_policy_version="unit-policy-v1",
        source_use_policy_sha256="a" * 64,
        source_binding_sha256="b" * 64,
        source_evidence_refs=("unit-evidence",),
        input_revision_sha256="c" * 64,
        system_prompt=system_prompt,
        user_payload=user_payload,
        response_schema_json=response_schema_json,
        max_output_tokens=max_output_tokens,
    )


def _completed_result(analysis):
    return {
        "ok": True,
        "status": "COMPLETED",
        "code": "OWNED_INFERENCE_COMPLETED",
        "provider": "owned",
        "request_id": "unit-agent-plan-request",
        "request_digest": "d" * 64,
        "run_id": "unit-run-7",
        "model_id": "owned-model-1",
        "model_revision": "revision-7",
        "recipe": "approved-planning-recipe",
        "source_use_policy_version": "unit-policy-v1",
        "source_use_policy_sha256": "a" * 64,
        "source_binding_sha256": "b" * 64,
        "input_revision_sha256": "c" * 64,
        "source_evidence_refs": ["unit-evidence"],
        "source_audit_ids": {
            "scope_before": "scope-before",
            "source_before": "source-before",
            "scope_after": "scope-after",
            "source_after": "source-after",
        },
        "prompt_tokens": 31,
        "completion_tokens": 17,
        "total_tokens": 48,
        "text": None,
        "analysis": analysis,
        "runtime": {"private": "omitted from planner receipt"},
    }


def test_unbound_default_fails_closed_without_compat_or_gateway_call(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("default planning must not call a compatibility or model route")

    monkeypatch.setattr(ai_gateway, "_chat", forbidden)
    monkeypatch.setattr(ai_gateway, "run_owned_analysis", forbidden)

    plan = Planner().plan("read source")

    assert plan.is_fallback is True
    assert plan.fallback_reason == "OWNED_PLANNING_REQUEST_NOT_BOUND"
    assert plan.steps == []
    assert plan.model == ""
    assert plan.token_usage == {}
    assert plan.inference_receipt == {}


def test_owned_factory_passes_exact_request_and_keeps_gateway_receipt(monkeypatch):
    calls = []

    def gateway(*, request, is_cancelled):
        assert type(request) is OwnedServiceRequest
        assert callable(is_cancelled)
        calls.append(request)
        return _completed_result({"steps": [_step()]})

    monkeypatch.setattr(ai_gateway, "run_owned_analysis", gateway)
    plan = Planner(owned_request_factory=_request_factory, is_cancelled=lambda: False).plan(
        "read source", mode=PlanMode.DEEP, context={"source_ref": "unit-evidence"},
    )

    assert len(calls) == 1
    request = calls[0]
    assert request.operation == "agent_plan"
    assert request.actor_ref == "unit-actor"
    assert request.domain_id == "cth"
    assert request.scope == "subject:unit-subject"
    assert request.source_evidence_refs == ("unit-evidence",)
    assert request.input_revision_sha256 == "c" * 64
    assert plan.model == "owned-model-1"
    assert plan.token_usage == {"prompt_tokens": 31, "completion_tokens": 17, "total_tokens": 48}
    assert plan.inference_receipt["model_revision"] == "revision-7"
    assert plan.inference_receipt["run_id"] == "unit-run-7"
    assert plan.inference_receipt["source_binding_sha256"] == "b" * 64
    assert plan.inference_receipt["source_audit_ids"]["source_after"] == "source-after"
    assert "analysis" not in plan.inference_receipt
    assert "text" not in plan.inference_receipt
    assert "runtime" not in plan.inference_receipt
    assert plan.steps[0].tool == "source_read"


def test_mismatched_owned_request_never_calls_gateway(monkeypatch):
    calls = []
    request_factory = lambda **kwargs: replace(
        _request_factory(**kwargs), operation="unrelated_operation",
    )
    monkeypatch.setattr(ai_gateway, "run_owned_analysis", lambda **kwargs: calls.append(kwargs))

    plan = Planner(owned_request_factory=request_factory).plan("read source")

    assert calls == []
    assert plan.steps == []
    assert plan.fallback_reason == "OWNED_PLANNING_REQUEST_MISMATCH"
    assert plan.inference_receipt == {}


def test_loop_default_uses_server_factory_and_current_cancel_signal(monkeypatch):
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    from agent_runtime.loop import AgentConfig, AgentLoop
    from tests.agent_runtime.formation_support import trusted_test_executor

    calls = []
    def gateway(*, request, is_cancelled):
        assert type(request) is OwnedServiceRequest
        assert is_cancelled() is False
        calls.append(request)
        return _completed_result({"steps": [_step()]})
    monkeypatch.setattr(ai_gateway, "run_owned_analysis", gateway)
    loop = AgentLoop(
        config=AgentConfig(enable_durable_execution=False, enable_evaluation=False),
        owned_request_factory=_request_factory,
        durable_adapter=DurableExecutionAdapter(enabled=False),
        tool_binding=trusted_test_executor(lambda step, context: {"success": True}),
    )
    result = loop.run("read admitted source", context={"actor_id": "client claim"})
    assert len(calls) == 1 and calls[0].actor_ref == "unit-actor"
    assert result.status == "completed"
    assert result.plan["inference_receipt"]["run_id"] == "unit-run-7"
    assert loop._durable.get_checkpoints(result.task_id)[-1].metadata["resumable"] is True


def test_loop_cancel_during_planning_does_not_form_or_dispatch_tool(monkeypatch):
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    from agent_runtime.loop import AgentConfig, AgentLoop

    class ForbiddenBinding:
        def form_step(self, *_args):
            pytest.fail("cancelled planning must not form tools")

    loop = AgentLoop(
        config=AgentConfig(enable_durable_execution=False, enable_evaluation=False),
        owned_request_factory=_request_factory, tool_binding=ForbiddenBinding(),
        durable_adapter=DurableExecutionAdapter(enabled=False),
    )
    def gateway(*, request, is_cancelled):
        loop.cancel()
        assert is_cancelled() is True
        return {"ok": False, "status": "CANCELLED", "code": "OWNED_INFERENCE_CANCELLED"}
    monkeypatch.setattr(ai_gateway, "run_owned_analysis", gateway)
    result = loop.run("cancel source task")
    assert result.status == "cancelled"
    assert result.plan["steps"] == []


@pytest.mark.parametrize("kwargs", [
    {"planner": Planner()}, {"ai_chat_func": lambda *_args: ("", "")},
])
def test_loop_rejects_ambiguous_planner_assembly(kwargs):
    from agent_runtime.loop import AgentLoop
    with pytest.raises(ValueError, match="default owned planner"):
        AgentLoop(owned_request_factory=_request_factory, **kwargs)


def test_prose_braces_do_not_hide_a_single_valid_plan():
    content = "Context {plain prose} then ```json\n" + _json_steps(_step(params={"text": "{quoted}"})) + "\n```"
    plan = Planner(ai_chat_func=lambda *_args, **_kwargs: (content, "unit")).plan("read source")
    assert len(plan.steps) == 1 and not plan.is_fallback


@pytest.mark.parametrize("content", [
    _json_steps(_step()) + "\n" + _json_steps(_step(action="other")),
    '{"broken": invalid, "nested": ' + _json_steps(_step()) + '}',
])
def test_ambiguous_or_malformed_enclosing_response_has_no_executable_fragment(content):
    plan = Planner(ai_chat_func=lambda *_args, **_kwargs: (content, "unit")).plan("read source")
    assert plan.steps == [] and plan.is_fallback


def test_numeric_overflow_inside_tool_params_rejects_entire_plan():
    content = _json_steps(_step(), _step(action="second", params={"limit": 1}))
    content = content.replace('"limit": 1', '"limit": 1e999')
    plan = Planner(ai_chat_func=lambda *_args, **_kwargs: (content, "unit")).plan("whole goal")
    assert plan.steps == []
    assert plan.is_fallback is True


def test_persistence_failure_never_returns_executable_steps_or_secret_error():
    def persist(_plan):
        raise RuntimeError("private-token-do-not-record")

    plan = Planner(
        ai_chat_func=lambda *_args, **_kwargs: (_json_steps(_step()), "unit"),
        persist_func=persist,
    ).plan("read source")
    assert plan.steps == []
    assert plan.fallback_reason == "PLANNING_PERSISTENCE_FAILED"
    assert "private-token" not in str(plan.to_dict())


@pytest.mark.parametrize("failure", [
    {"ok": False, "status": "UNAVAILABLE", "code": "OWNED_RUNTIME_NOT_BOUND"},
    RuntimeError("owned gateway unavailable"),
])
def test_gateway_failure_never_creates_executable_fallback(monkeypatch, failure):
    def gateway(**_kwargs):
        if isinstance(failure, Exception):
            raise failure
        return failure

    monkeypatch.setattr(ai_gateway, "run_owned_analysis", gateway)
    plan = Planner(owned_request_factory=_request_factory).plan("read source")

    assert plan.is_fallback is True
    assert plan.steps == []
    assert plan.model == ""
    assert plan.token_usage == {}


def test_owned_unparseable_result_keeps_provenance_but_has_no_steps(monkeypatch):
    result = _completed_result(None)
    result.update({"analysis": "not JSON", "text": "not JSON"})
    monkeypatch.setattr(ai_gateway, "run_owned_analysis", lambda **_kwargs: result)

    plan = Planner(owned_request_factory=_request_factory).plan("read source")

    assert plan.is_fallback is True
    assert plan.steps == []
    assert plan.model == "owned-model-1"
    assert plan.inference_receipt["run_id"] == "unit-run-7"
    assert plan.token_usage == {"prompt_tokens": 31, "completion_tokens": 17, "total_tokens": 48}


@pytest.mark.parametrize("steps, max_steps", [
    ([_step(), _step(action="second step")], 1),
    ([_step(), _step(risk_level="HIGH")], 2),
    ([_step(), _step(action=3)], 2),
    ([_step(), _step(tool="")], 2),
    ([_step(), _step(params=[])], 2),
    ([_step(), _step(expected_output=" ")], 2),
    ([_step(), _step(status="completed")], 2),
    ([_step(), _step(step_id="forged-step")], 2),
    ([_step(), _step(formation={"origin": "forged"})], 2),
])
def test_any_invalid_or_over_limit_step_rejects_the_whole_plan(steps, max_steps):
    callback = lambda *_args, **_kwargs: (_json_steps(*steps), "untrusted-provider-label")

    plan = Planner(ai_chat_func=callback).plan("read source", max_steps=max_steps)

    assert plan.is_fallback is True
    assert plan.steps == []
    assert plan.model == ""
    assert plan.token_usage == {}


@pytest.mark.parametrize("content", [
    '{"steps":[{"action":"first","action":"second","tool":"t","params":{},"expected_output":"o","risk_level":"low"}]}',
    '{"steps":[{"action":"read","tool":"t","params":{"score":NaN},"expected_output":"o","risk_level":"low"}]}',
])
def test_duplicate_keys_and_nonfinite_json_are_rejected(content):
    plan = Planner(ai_chat_func=lambda *_args, **_kwargs: (content, "test-label")).plan("read source")

    assert plan.is_fallback is True
    assert plan.steps == []


def test_injected_callback_receives_full_json_context_without_provider_inference():
    captured = {}

    def callback(_system, user, **kwargs):
        captured["user"] = user
        captured["kwargs"] = kwargs
        return _json_steps(_step()), "invented-provider"

    tail = "CONTEXT-TAIL-MUST-NOT-BE-TRUNCATED"
    context = {"long_value": "x" * 700 + tail}
    plan = Planner(ai_chat_func=callback).plan("read source", context=context)

    assert tail in captured["user"]
    assert captured["kwargs"].get("model") is None
    assert plan.model == ""
    assert plan.token_usage == {}
    assert plan.inference_receipt == {}


def test_nonfinite_context_fails_before_any_callback():
    calls = []

    def callback(*_args, **_kwargs):
        calls.append(True)
        return _json_steps(_step()), "test-fixture-provider"

    plan = Planner(ai_chat_func=callback).plan(
        "read source", context={"invalid": float("nan")},
    )

    assert calls == []
    assert plan.is_fallback is True
    assert plan.steps == []
