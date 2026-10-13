# -*- coding: utf-8 -*-
"""
Unit tests for agent_runtime.planner
覆盖：规划生成（mock AI）、JSON解析、降级规划、计划验证、模型选择
"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_runtime.planner import (
    Planner, Plan, PlanStep, PlanMode, RiskLevel,
)


def _mock_ai_chat(system, user, model=None, temperature=0.1, max_tokens=1200, timeout=None):
    """Mock AI 调用，返回固定规划 JSON。"""
    plan = {
        "steps": [
            {
                "action": "查询今日笔记数据",
                "tool": "db_query",
                "params": {"table": "notes", "date": "today"},
                "expected_output": "笔记列表",
                "risk_level": "low",
            },
            {
                "action": "分析舆情趋势",
                "tool": "ai_analysis",
                "params": {"notes": "from_step_1"},
                "expected_output": "趋势分析报告",
                "risk_level": "medium",
            },
            {
                "action": "生成日报",
                "tool": "report_generator",
                "params": {"analysis": "from_step_2"},
                "expected_output": "日报文档",
                "risk_level": "low",
            },
        ]
    }
    return json.dumps(plan, ensure_ascii=False), "zhipu"


def _mock_ai_chat_empty(system, user, model=None, **kwargs):
    """Mock AI 返回空。"""
    return None, "rule"


def _mock_ai_chat_invalid_json(system, user, model=None, **kwargs):
    """Mock AI 返回无效 JSON。"""
    return "这不是JSON", "zhipu"


def _mock_ai_chat_with_wrapper(system, user, model=None, **kwargs):
    """Mock AI 返回带 markdown 包装的 JSON。"""
    plan = {"steps": [{"action": "test", "tool": "t", "params": {}, "expected_output": "o", "risk_level": "low"}]}
    return f"```json\n{json.dumps(plan)}\n```", "zhipu"


class TestPlannerInit:
    def test_default_mode(self):
        planner = Planner()
        assert planner._default_mode == PlanMode.ROUTINE

    def test_custom_ai_func(self):
        planner = Planner(ai_chat_func=_mock_ai_chat)
        assert planner._ai_chat_func == _mock_ai_chat


class TestPlanGeneration:
    def test_routine_plan(self):
        planner = Planner(ai_chat_func=_mock_ai_chat)
        plan = planner.plan("分析今日舆情", mode=PlanMode.ROUTINE)
        assert plan.goal == "分析今日舆情"
        assert plan.mode == "routine"
        assert plan.model == "glm-4.5-air"
        assert len(plan.steps) == 3
        assert plan.steps[0].action == "查询今日笔记数据"
        assert plan.steps[0].tool == "db_query"
        assert plan.is_fallback is False

    def test_deep_plan(self):
        planner = Planner(ai_chat_func=_mock_ai_chat)
        plan = planner.plan("深度分析", mode=PlanMode.DEEP)
        assert plan.mode == "deep"
        assert plan.model == "glm-5.3"

    def test_plan_step_structure(self):
        planner = Planner(ai_chat_func=_mock_ai_chat)
        plan = planner.plan("test")
        for step in plan.steps:
            assert step.action
            assert step.tool
            assert isinstance(step.params, dict)
            assert step.expected_output
            assert step.risk_level in ("low", "medium", "high", "critical")
            assert step.status == "pending"

    def test_plan_max_steps(self):
        planner = Planner(ai_chat_func=_mock_ai_chat)
        plan = planner.plan("test", max_steps=2)
        assert len(plan.steps) <= 2

    def test_plan_id_unique(self):
        planner = Planner(ai_chat_func=_mock_ai_chat)
        p1 = planner.plan("test1")
        p2 = planner.plan("test2")
        assert p1.plan_id != p2.plan_id


class TestFallbackPlanning:
    def test_empty_response_fallback(self):
        planner = Planner(ai_chat_func=_mock_ai_chat_empty)
        plan = planner.plan("test")
        assert plan.is_fallback is True
        assert "empty" in plan.fallback_reason.lower()
        assert len(plan.steps) == 1
        assert plan.steps[0].tool == "direct_execution"

    def test_invalid_json_fallback(self):
        planner = Planner(ai_chat_func=_mock_ai_chat_invalid_json)
        plan = planner.plan("test")
        assert plan.is_fallback is True
        assert "parse" in plan.fallback_reason.lower()

    def test_ai_exception_fallback(self):
        def raising_chat(system, user, **kwargs):
            raise RuntimeError("AI service down")
        planner = Planner(ai_chat_func=raising_chat)
        plan = planner.plan("test")
        assert plan.is_fallback is True
        assert "failed" in plan.fallback_reason.lower()

    def test_rule_based_mode(self):
        planner = Planner(ai_chat_func=_mock_ai_chat)
        plan = planner.plan("test", mode=PlanMode.RULE_BASED)
        assert plan.is_fallback is True
        assert plan.steps[0].tool == "rule_engine"


class TestJsonExtraction:
    def test_extract_plain_json(self):
        text = '{"steps": []}'
        assert Planner._extract_json(text) == text

    def test_extract_wrapped_json(self):
        text = 'Here is the plan:\n{"steps": [{"a": 1}]}\nDone.'
        result = Planner._extract_json(text)
        assert result is not None
        data = json.loads(result)
        assert data["steps"][0]["a"] == 1

    def test_extract_markdown_json(self):
        planner = Planner(ai_chat_func=_mock_ai_chat_with_wrapper)
        plan = planner.plan("test")
        assert len(plan.steps) == 1
        assert plan.steps[0].action == "test"

    def test_extract_no_json(self):
        assert Planner._extract_json("no json here") is None


class TestPlanValidation:
    def test_valid_plan(self):
        planner = Planner(ai_chat_func=_mock_ai_chat)
        plan = planner.plan("test")
        issues = planner.validate_plan(plan)
        assert issues == []

    def test_empty_goal(self):
        plan = Plan(goal="", steps=[PlanStep(action="a", tool="t")])
        planner = Planner()
        issues = planner.validate_plan(plan)
        assert any("goal" in i for i in issues)

    def test_empty_steps(self):
        plan = Plan(goal="test", steps=[])
        planner = Planner()
        issues = planner.validate_plan(plan)
        assert any("steps" in i for i in issues)

    def test_high_risk_no_tool(self):
        plan = Plan(goal="test", steps=[
            PlanStep(action="dangerous", tool="", risk_level="high")
        ])
        planner = Planner()
        issues = planner.validate_plan(plan)
        assert any("high risk" in i for i in issues)


class TestPlanProperties:
    def test_total_steps(self):
        plan = Plan(steps=[PlanStep(), PlanStep(), PlanStep()])
        assert plan.total_steps == 3

    def test_max_risk(self):
        plan = Plan(steps=[
            PlanStep(risk_level="low"),
            PlanStep(risk_level="high"),
            PlanStep(risk_level="medium"),
        ])
        assert plan.max_risk == "critical" or plan.max_risk == "high"

    def test_to_dict(self):
        planner = Planner(ai_chat_func=_mock_ai_chat)
        plan = planner.plan("test")
        d = plan.to_dict()
        assert d["goal"] == "test"
        assert isinstance(d["steps"], list)
        assert len(d["steps"]) == 3
