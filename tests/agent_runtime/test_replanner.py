# -*- coding: utf-8 -*-
"""
Unit tests for agent_runtime.replanner
覆盖：重规划触发条件、重规划策略、重规划次数限制、策略选择
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_runtime.replanner import (
    Replanner, ReplanTrigger, ReplanStrategy, ReplanDecision,
)
from agent_runtime.planner import Plan, PlanStep, Planner


def _make_plan(n=3):
    steps = [
        PlanStep(index=i, action=f"step_{i}", tool=f"tool_{i}",
                 params={"k": "v"}, expected_output=f"out_{i}", risk_level="low")
        for i in range(n)
    ]
    return Plan(goal="test goal", steps=steps)


def _make_observation(**kwargs):
    """构造 mock observation 对象。"""
    class MockObs:
        def __init__(self, **kw):
            self.db_status = kw.get("db_status", "ok")
            self.ai_status = kw.get("ai_status", "ok")
            self.ai_circuit_state = kw.get("ai_circuit_state", "CLOSED")
            self.collection_status = kw.get("collection_status", "unknown")
            self.environment_changed = kw.get("environment_changed", False)
            self.changed_fields = kw.get("changed_fields", [])
            self.previous_step_error = kw.get("previous_step_error")
    return MockObs(**kwargs)


class TestReplannerInit:
    def test_default_max_replans(self):
        r = Replanner()
        assert r._max_replans == 2
        assert r.replan_count == 0

    def test_custom_max_replans(self):
        r = Replanner(max_replans=5)
        assert r._max_replans == 5

    def test_can_replan(self):
        r = Replanner(max_replans=2)
        assert r.can_replan() is True


class TestShouldReplan:
    def test_step_failure_triggers_replan(self):
        r = Replanner(max_replans=3)
        step = PlanStep(index=0, action="fail step", tool="t", error="timeout")
        decision = r.should_replan(failed_step=step, retry_count=3, max_retries=3)
        assert decision is not None
        assert decision.trigger == ReplanTrigger.STEP_FAILURE.value
        assert "failed 3 times" in decision.reason

    def test_failure_below_max_retries_no_replan(self):
        r = Replanner(max_replans=3)
        step = PlanStep(index=0, action="fail step", error="timeout")
        decision = r.should_replan(failed_step=step, retry_count=1, max_retries=3)
        assert decision is None

    def test_environment_change_triggers(self):
        r = Replanner(max_replans=3)
        obs = _make_observation(environment_changed=True, changed_fields=["db_status"])
        decision = r.should_replan(observation=obs)
        assert decision is not None
        assert decision.trigger == ReplanTrigger.ENVIRONMENT_CHANGE.value

    def test_environment_change_non_critical_no_trigger(self):
        r = Replanner(max_replans=3)
        obs = _make_observation(environment_changed=True, changed_fields=["collection_status"])
        # collection_status 变化不在关键变化列表中
        decision = r.should_replan(observation=obs)
        # collection_status 不在触发列表中，应为 None
        assert decision is None

    def test_budget_exceeded_triggers(self):
        r = Replanner(max_replans=3)
        decision = r.should_replan(budget_exceeded=True)
        assert decision is not None
        assert decision.trigger == ReplanTrigger.BUDGET_EXCEEDED.value

    def test_low_confidence_triggers(self):
        r = Replanner(max_replans=3)
        decision = r.should_replan(low_confidence=True)
        assert decision is not None
        assert decision.trigger == ReplanTrigger.LOW_CONFIDENCE.value

    def test_max_replans_exceeded_no_trigger(self):
        r = Replanner(max_replans=1)
        r._replan_count = 1
        step = PlanStep(index=0, error="timeout")
        decision = r.should_replan(failed_step=step, retry_count=3, max_retries=3)
        assert decision is None

    def test_no_trigger_condition(self):
        r = Replanner(max_replans=3)
        obs = _make_observation(environment_changed=False)
        decision = r.should_replan(observation=obs)
        assert decision is None


class TestReplanStrategies:
    def test_full_replan(self):
        planner = Planner(ai_chat_func=lambda s, u, **kw: ('{"steps":[{"action":"new","tool":"nt","params":{},"expected_output":"o","risk_level":"low"}]}', 'zhipu'))
        r = Replanner(planner=planner, max_replans=3)
        plan = _make_plan()
        decision = ReplanDecision(
            trigger="step_failure", strategy="full_replan",
            reason="test", original_step_index=0,
        )
        new_plan = r.replan("test goal", plan, decision)
        assert new_plan.steps[0].action == "new"
        assert r.replan_count == 1

    def test_switch_tool_replan(self):
        r = Replanner(max_replans=3)
        plan = _make_plan()
        plan.steps[0].tool = "ai_analysis"
        decision = ReplanDecision(
            trigger="step_failure", strategy="switch_tool",
            reason="tool unavailable", original_step_index=0,
        )
        new_plan = r.replan("test", plan, decision)
        assert new_plan.is_fallback is True
        assert new_plan.steps[0].tool == "rule_based_analysis"
        assert "_replan_note" in new_plan.steps[0].params

    def test_adjust_params_replan(self):
        r = Replanner(max_replans=3)
        plan = _make_plan()
        plan.steps[0].params = {"batch_size": 100, "timeout": 30}
        decision = ReplanDecision(
            trigger="step_failure", strategy="adjust_params",
            reason="param error", original_step_index=0,
        )
        new_plan = r.replan("test", plan, decision)
        assert new_plan.steps[0].params["_retry_adjusted"] is True
        assert new_plan.steps[0].params["batch_size"] == 10  # reduced from 100
        assert new_plan.steps[0].params["timeout"] == 60  # doubled from 30

    def test_split_step_replan(self):
        r = Replanner(max_replans=3)
        plan = _make_plan(n=2)
        decision = ReplanDecision(
            trigger="step_failure", strategy="split_step",
            reason="timeout", original_step_index=0,
        )
        new_plan = r.replan("test", plan, decision)
        # step 0 拆为3个，step 1 保留 → 共4步
        assert len(new_plan.steps) == 4
        assert "[准备]" in new_plan.steps[0].action
        assert "[执行]" in new_plan.steps[1].action
        assert "[验证]" in new_plan.steps[2].action

    def test_simplify_goal_replan(self):
        r = Replanner(max_replans=3)
        plan = _make_plan(n=5)
        plan.steps[3].risk_level = "high"
        decision = ReplanDecision(
            trigger="budget_exceeded", strategy="simplify_goal",
            reason="budget", original_step_index=0,
        )
        new_plan = r.replan("test goal", plan, decision)
        assert "简化版" in new_plan.goal
        assert len(new_plan.steps) <= 5  # 只保留低风险步骤

    def test_skip_step_replan(self):
        r = Replanner(max_replans=3)
        plan = _make_plan(n=3)
        decision = ReplanDecision(
            trigger="step_failure", strategy="skip_step",
            reason="skip", original_step_index=1,
        )
        new_plan = r.replan("test", plan, decision)
        assert len(new_plan.steps) == 2
        assert new_plan.steps[0].action == "step_0"
        assert new_plan.steps[1].action == "step_2"


class TestStrategySelection:
    def test_tool_unavailable_selects_switch(self):
        r = Replanner(max_replans=3)
        step = PlanStep(index=0, error="tool not found")
        strategy = r._select_strategy_for_failure(step, None)
        assert strategy == ReplanStrategy.SWITCH_TOOL

    def test_param_error_selects_adjust(self):
        r = Replanner(max_replans=3)
        step = PlanStep(index=0, error="invalid param value")
        strategy = r._select_strategy_for_failure(step, None)
        assert strategy == ReplanStrategy.ADJUST_PARAMS

    def test_timeout_selects_split(self):
        r = Replanner(max_replans=3)
        step = PlanStep(index=0, error="request timeout")
        strategy = r._select_strategy_for_failure(step, None)
        assert strategy == ReplanStrategy.SPLIT_STEP

    def test_ai_circuit_open_selects_switch(self):
        r = Replanner(max_replans=3)
        step = PlanStep(index=0, error="unknown error")
        obs = _make_observation(ai_circuit_state="OPEN")
        strategy = r._select_strategy_for_failure(step, obs)
        assert strategy == ReplanStrategy.SWITCH_TOOL

    def test_unknown_error_selects_full_replan(self):
        r = Replanner(max_replans=3)
        step = PlanStep(index=0, error="mysterious failure")
        strategy = r._select_strategy_for_failure(step, None)
        assert strategy == ReplanStrategy.FULL_REPLAN


class TestReplanHistory:
    def test_history_records_decisions(self):
        r = Replanner(max_replans=3)
        plan = _make_plan()
        d1 = ReplanDecision(trigger="step_failure", strategy="switch_tool", reason="r1", original_step_index=0)
        d2 = ReplanDecision(trigger="environment_change", strategy="adjust_params", reason="r2", original_step_index=1)
        r.replan("test", plan, d1)
        r.replan("test", plan, d2)
        assert len(r.history) == 2
        assert r.history[0].reason == "r1"
        assert r.history[1].reason == "r2"

    def test_reset(self):
        r = Replanner(max_replans=3)
        plan = _make_plan()
        d = ReplanDecision(trigger="step_failure", strategy="switch_tool", reason="r", original_step_index=0)
        r.replan("test", plan, d)
        assert r.replan_count == 1
        r.reset()
        assert r.replan_count == 0
        assert len(r.history) == 0
