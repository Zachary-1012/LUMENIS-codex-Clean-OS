"""Actual Router/Loop dispatch drift, not a second permission implementation."""
from copy import deepcopy
import hashlib
from types import SimpleNamespace

import pytest

from agent_capability.formation import FormationError, digest, implementation_identity
from agent_capability.router import CapabilityRouter, ToolDefinition, ToolActorContext
from agent_runtime.durable_adapter import DurableExecutionAdapter
from agent_runtime.loop import AgentConfig, AgentLoop
from agent_runtime.planner import Plan, PlanStep, Planner


def state(config=None):
    return {"configuration": config or {}, "environment": {"network": "disabled"},
            "origin_scope_id": "test-origin-scope-v1", "implementation_revision": "test-owner-v1",
            "available": True}


class StaticPlanner:
    def __init__(self, plan):
        self.value = plan

    def plan(self, *args, **kwargs):
        return self.value


class Gate:
    def __init__(self, on_admission=lambda: None, allowed=True):
        self.on_admission = on_admission
        self.allowed = allowed
        self.calls = 0

    def check(self, *args, **kwargs):
        self.calls += 1
        self.on_admission()
        return SimpleNamespace(allowed=self.allowed, reason="test admission", to_dict=lambda: {},
                               audit_id="fixture-admission", operation_id="fixture-operation",
                               requires_approval=False, approval_token=None)


def tool(handler, identity_provider=lambda: state(), **kwargs):
    return ToolDefinition(tool_id="source_read", name="read source", description="read original source",
                          handler=handler, origin="lumenis-test-owner", resource_uri="skill://test/source-read",
                          identity_provider=identity_provider, **kwargs)


def plan():
    return Plan(goal="read original source", steps=[PlanStep(
        step_id="read-original", action="read original source", tool="source_read", params={},
        expected_output="source bytes with preserved identity")])


def run(router, gate=None, p=None):
    p = p or plan()
    loop = AgentLoop(config=AgentConfig(enable_evaluation=False, max_replans=0),
                     planner=StaticPlanner(p), durable_adapter=DurableExecutionAdapter(enabled=False),
                     permission_gate=gate or Gate(), tool_binding=router)
    return loop.run(p.goal, context={"domain_id": "cth", "scope": {"subject_id": "subject-a"}})


@pytest.mark.parametrize("drift", ["handler", "configuration", "origin_scope", "dependency", "registry"])
def test_actual_drift_during_admission_never_invokes_either_handler(drift, tmp_path):
    called = []
    owner_state = state({"effects_allowed": False})
    dep = tmp_path / "owner_config.py"
    dep.write_text("EFFECTS_ALLOWED = False\n", encoding="utf-8")
    first = tool(lambda: called.append("first"), lambda: owner_state, dependency_paths=(str(dep),))
    router = CapabilityRouter(enabled=True)
    assert router.register_tool(first)

    def mutate():
        if drift == "handler":
            first.handler = lambda: called.append("replacement")
        elif drift == "configuration":
            owner_state["configuration"]["effects_allowed"] = True
        elif drift == "origin_scope":
            owner_state["origin_scope_id"] = "another-origin-scope"
        elif drift == "dependency":
            dep.write_text("EFFECTS_ALLOWED = True\n", encoding="utf-8")
        else:
            router.register_tool(tool(lambda: called.append("replacement"), lambda: owner_state))

    gate = Gate(mutate)
    result = run(router, gate)
    assert gate.calls == 1
    assert result.status == "reconciliation_required", (result.error, result.plan)
    assert called == []
    assert result.error in {"TOOL_FORMATION_CHANGED", "TOOL_IMPLEMENTATION_CHANGED"}


def test_same_checked_callable_and_immutable_arguments_survive_admission():
    calls = []
    router = CapabilityRouter(enabled=True)
    router.register_tool(tool(lambda: calls.append("source") or {"identity": "original"}))
    result = run(router)
    assert result.status == "completed", (result.error, result.plan["steps"][0]["error"])
    assert calls == ["source"]
    assert result.plan["steps"][0]["formation"]["origin"] == "lumenis-test-owner"
    assert result.result["final_step_results"][0]["result"]["result"]["identity"] == "original"


def test_unavailable_is_reconciliation_and_cannot_choose_same_label_successor():
    calls = []
    owner_state = state()
    router = CapabilityRouter(enabled=True)
    original = tool(lambda: calls.append("original"), lambda: owner_state)
    router.register_tool(original)
    step = plan().steps[0]
    formed = router.form_step(step, {})
    owner_state["available"] = False
    with pytest.raises(FormationError, match="TOOL_RUNTIME_UNAVAILABLE"):
        router.form_step(step, {}, expected=formed.binding)
    shadow = deepcopy(original)
    shadow.origin = "other-server"
    shadow.resource_uri = "skill://other-server/same-name"
    assert not router.register_tool(shadow)
    assert router.get_tool(step.tool) is original
    assert calls == []


def test_discovery_is_metadata_only_and_supporting_bytes_are_lazy_and_checked(monkeypatch):
    import lumenis.shared.agents.skills.execution as execution
    monkeypatch.setattr(execution, "check_permission", lambda ctx, user_role: {"allowed": True})
    monkeypatch.setattr(execution, "action_firewall", lambda ctx: {"allowed": True})
    monkeypatch.setattr(execution, "effect_fence", lambda ctx: {"allowed": True})
    calls = []
    content = b"# supporting nested SKILL.md; reading is not activation"
    manifest = [{"uri": "skill://test/source-read/support/SKILL.md", "size": len(content),
                 "sha256": hashlib.sha256(content).hexdigest()}]
    owner_state = state()
    owner_state["content_manifest_digest"] = digest(manifest)
    entry = tool(lambda: calls.append("execute"), lambda: owner_state,
                 resource_manifest=manifest, resource_reader=lambda uri: calls.append(uri) or content)
    router = CapabilityRouter(enabled=True, actor_authorizer=lambda actor, selected: actor.user_id == 7)
    actor = ToolActorContext(7, "user", "CTH", "cth", "cth_analyst")
    router.register_tool(entry)
    assert router.select_tools("read source")
    assert calls == []
    step = plan().steps[0]
    formed = router.form_step(step, {})
    assert calls == []
    with pytest.raises(FormationError, match="TOOL_CONTENT_ACTOR_NOT_AUTHORIZED"):
        router.read_supporting_resource(step, {}, formed.binding, manifest[0]["uri"])
    assert calls == []
    assert router.read_supporting_resource(step, {}, formed.binding, manifest[0]["uri"], actor_context=actor) == content
    assert calls == [manifest[0]["uri"]]
    entry.resource_reader = lambda uri: b"changed bytes"
    with pytest.raises(FormationError, match="TOOL_CONTENT_INTEGRITY_FAILED"):
        router.read_supporting_resource(step, {}, formed.binding, manifest[0]["uri"], actor_context=actor)
    entry.resource_manifest.append({"uri": "skill://test/new", "size": 0,
                                    "sha256": hashlib.sha256(b"").hexdigest()})
    with pytest.raises(FormationError, match="TOOL_CONTENT_REAPPROVAL_REQUIRED"):
        router.form_step(step, {}, expected=formed.binding)
    owner_state["content_manifest_digest"] = digest(sorted(entry.resource_manifest, key=lambda row: row["uri"]))
    with pytest.raises(FormationError, match="TOOL_FORMATION_CHANGED"):
        router.form_step(step, {}, expected=formed.binding)
    assert "execute" not in calls


def test_unformed_direct_executor_cannot_execute():
    called = []
    p = plan()
    loop = AgentLoop(planner=StaticPlanner(p), tool_executor=lambda step, ctx: called.append(True),
                     durable_adapter=DurableExecutionAdapter(enabled=False))
    result = loop.run(p.goal)
    assert result.status == "blocked" and result.error == "TOOL_FORMATION_NOT_BOUND"
    assert called == []


def test_model_output_cannot_supply_formation():
    import json
    planner = Planner(ai_chat_func=lambda *args, **kwargs: (json.dumps({"steps": [
        {"action": "read", "tool": "source_read", "params": {}, "risk_level": "low",
         "expected_output": "source bytes",
         "formation": {"origin": "forged", "effect": "READ"}}]}), "fixture"))
    result = planner.plan("read")
    assert result.steps == []
    assert result.is_fallback is True


def test_formed_write_is_not_downgraded_by_model_read_label():
    step = PlanStep(tool="unknown", params={"action_type": "READ"}, risk_level="low")
    step.formation = {"effect": "WRITE"}
    assert AgentLoop._security_action(step).value == "WRITE"
    step.params["action_type"] = "DEPLOY"
    with pytest.raises(FormationError, match="TOOL_EFFECT_DECLARATION_CONFLICT"):
        AgentLoop._security_action(step)


def test_retaining_exception_or_result_cannot_change_the_same_implementation_identity():
    def fails():
        raise RuntimeError("unit failure")

    code = fails.__code__
    before = implementation_identity(fails)
    retained = []
    for _ in range(3):
        try:
            fails()
        except RuntimeError as exc:
            retained.append(exc)
            assert fails.__code__ is code
            assert implementation_identity(fails) == before


def test_cancellation_during_admission_never_calls_handler():
    calls = []
    router = CapabilityRouter(enabled=True)
    router.register_tool(tool(lambda: calls.append("called")))
    p = plan()
    gate = Gate()
    loop = AgentLoop(planner=StaticPlanner(p), tool_binding=router, permission_gate=gate,
                     durable_adapter=DurableExecutionAdapter(enabled=False))
    gate.on_admission = loop.cancel
    result = loop.run(p.goal)
    assert result.status == "cancelled"
    assert calls == []
