# -*- coding: utf-8 -*-
"""
Unit tests for agent_runtime.evaluation
覆盖：四维评分、综合评分、等级、改进建议、轨迹对比
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lumenis.shared.evaluation.trajectory import (
    TrajectoryEvaluator, TrajectoryMetrics, TrajectoryEvaluation, DimensionScore,
)


class TestDimensionScore:
    def test_default_values(self):
        ds = DimensionScore(name="test", score=0.5, weight=0.25)
        assert ds.name == "test"
        assert ds.score == 0.5
        assert ds.weight == 0.25
        assert ds.details == {}
        assert ds.reasoning == ""

    def test_to_dict(self):
        ds = DimensionScore(name="test", score=0.8, weight=0.3, reasoning="good")
        d = ds.to_dict()
        assert d["name"] == "test"
        assert d["score"] == 0.8
        assert d["reasoning"] == "good"


class TestGoalCompletion:
    def test_goal_achieved(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(goal_achieved=True, total_steps=5, completed_steps=5)
        result = evaluator._score_goal_completion(metrics)
        assert result.score == 1.0
        assert "业务结果须独立核验" in result.reasoning
        assert result.details["business_outcome_verified"] is False

    def test_partial_completion(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(goal_achieved=False, total_steps=10, completed_steps=5)
        result = evaluator._score_goal_completion(metrics)
        assert 0.0 < result.score < 1.0
        assert "部分达成" in result.reasoning

    def test_no_completion(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(goal_achieved=False, total_steps=5, completed_steps=0)
        result = evaluator._score_goal_completion(metrics)
        assert result.score == 0.0

    def test_failed_steps_penalty(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(goal_achieved=True, total_steps=5, completed_steps=5, failed_steps=2)
        result = evaluator._score_goal_completion(metrics)
        assert result.score < 1.0  # 有失败步骤扣分


class TestStepEfficiency:
    def test_fewer_steps_than_expected(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(total_steps=3, expected_steps=5, retry_count=0, replan_count=0)
        result = evaluator._score_step_efficiency(metrics)
        assert result.score == 1.0

    def test_more_steps_than_expected(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(total_steps=10, expected_steps=5, retry_count=0, replan_count=0)
        result = evaluator._score_step_efficiency(metrics)
        assert result.score < 1.0

    def test_no_expected_steps(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(total_steps=5, expected_steps=0, retry_count=1, replan_count=0)
        result = evaluator._score_step_efficiency(metrics)
        assert 0.0 < result.score <= 1.0

    def test_replan_penalty(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(total_steps=3, expected_steps=3, retry_count=0, replan_count=2)
        result = evaluator._score_step_efficiency(metrics)
        assert result.score < 1.0


class TestCostEfficiency:
    def test_under_budget(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(estimated_cost=0.5, budget_cost=2.0)
        result = evaluator._score_cost_efficiency(metrics)
        assert result.score > 0.7

    def test_over_budget(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(estimated_cost=5.0, budget_cost=2.0)
        result = evaluator._score_cost_efficiency(metrics)
        assert result.score < 0.5

    def test_no_budget(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(estimated_cost=100.0, budget_cost=0)
        result = evaluator._score_cost_efficiency(metrics)
        assert result.score == 1.0


class TestSafetyCompliance:
    def test_no_safety_issues(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(
            permission_denied_count=0, firewall_blocked_count=0,
            effect_fence_triggered_count=0, total_steps=5,
        )
        result = evaluator._score_safety_compliance(metrics)
        assert result.score == 1.0
        assert "无安全拦截" in result.reasoning

    def test_with_safety_interceptions(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(
            permission_denied_count=2, firewall_blocked_count=1,
            effect_fence_triggered_count=0, total_steps=5,
        )
        result = evaluator._score_safety_compliance(metrics)
        # 权限拒绝和防火墙拦截是正常安全行为，不扣分
        assert result.score == 1.0

    def test_effect_fence_triggered(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(
            permission_denied_count=0, firewall_blocked_count=0,
            effect_fence_triggered_count=3, total_steps=5,
        )
        result = evaluator._score_safety_compliance(metrics)
        assert result.score < 1.0


class TestOverallEvaluation:
    def test_perfect_execution(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(
            total_steps=5, completed_steps=5, failed_steps=0,
            replan_count=0, retry_count=0, estimated_cost=0.1,
            budget_cost=2.0, expected_steps=5, goal_achieved=True,
        )
        result = evaluator.evaluate(metrics, agent_id="a1", task_id="t1")
        assert result.overall_score >= 0.9
        assert result.grade in ("S", "A")
        assert result.goal_completion.score == 1.0

    def test_failed_execution(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(
            total_steps=5, completed_steps=1, failed_steps=4,
            replan_count=2, retry_count=5, estimated_cost=3.0,
            budget_cost=2.0, expected_steps=5, goal_achieved=False,
        )
        result = evaluator.evaluate(metrics)
        assert result.overall_score < 0.6
        assert result.grade in ("C", "D", "F")

    def test_evaluation_structure(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(goal_achieved=True, total_steps=1, completed_steps=1)
        result = evaluator.evaluate(metrics)
        assert result.evaluation_id
        assert result.timestamp
        assert result.method == "deterministic"
        assert isinstance(result.recommendations, list)
        assert len(result.recommendations) > 0

    def test_weights_sum_to_one(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(goal_achieved=True, total_steps=1, completed_steps=1)
        result = evaluator.evaluate(metrics)
        total_weight = (
            result.goal_completion.weight
            + result.step_efficiency.weight
            + result.cost_efficiency.weight
            + result.safety_compliance.weight
        )
        assert abs(total_weight - 1.0) < 0.001

    def test_to_dict(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(goal_achieved=True, total_steps=1, completed_steps=1)
        result = evaluator.evaluate(metrics)
        d = result.to_dict()
        assert d["overall_score"] == result.overall_score
        assert d["grade"] == result.grade
        assert "goal_completion" in d
        assert isinstance(d["goal_completion"], dict)

    def test_to_json(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(goal_achieved=True, total_steps=1, completed_steps=1)
        result = evaluator.evaluate(metrics)
        j = result.to_json()
        assert '"overall_score"' in j
        assert '"grade"' in j


class TestGradeThresholds:
    def test_s_grade(self):
        evaluator = TrajectoryEvaluator()
        assert evaluator._compute_grade(0.95) == "S"

    def test_a_grade(self):
        evaluator = TrajectoryEvaluator()
        assert evaluator._compute_grade(0.85) == "A"

    def test_f_grade(self):
        evaluator = TrajectoryEvaluator()
        assert evaluator._compute_grade(0.1) == "F"


class TestRecommendations:
    def test_low_goal_completion_recommendation(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(
            goal_achieved=False, total_steps=5, completed_steps=1,
            expected_steps=5, estimated_cost=0.1, budget_cost=2.0,
        )
        result = evaluator.evaluate(metrics)
        assert any("目标达成" in r for r in result.recommendations)

    def test_high_replan_recommendation(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(
            goal_achieved=True, total_steps=10, completed_steps=10,
            replan_count=3, expected_steps=5, estimated_cost=0.1, budget_cost=2.0,
        )
        result = evaluator.evaluate(metrics)
        assert any("重规划" in r for r in result.recommendations)

    def test_good_execution_recommendation(self):
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(
            goal_achieved=True, total_steps=3, completed_steps=3,
            replan_count=0, retry_count=0, estimated_cost=0.05,
            budget_cost=2.0, expected_steps=3,
        )
        result = evaluator.evaluate(metrics)
        assert any("良好" in r or "保持" in r for r in result.recommendations)


class TestCompareTrajectories:
    def test_comparison(self):
        evaluator = TrajectoryEvaluator()
        m1 = TrajectoryMetrics(goal_achieved=False, total_steps=5, completed_steps=2, expected_steps=5)
        m2 = TrajectoryMetrics(goal_achieved=True, total_steps=5, completed_steps=5, expected_steps=5)
        e1 = evaluator.evaluate(m1, agent_id="agent_1")
        e2 = evaluator.evaluate(m2, agent_id="agent_2")
        comparison = evaluator.compare_trajectories(e1, e2)
        assert comparison["overall_delta"] > 0
        assert comparison["better"] == "agent_2"
