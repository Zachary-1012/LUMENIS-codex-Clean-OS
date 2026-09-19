# -*- coding: utf-8 -*-
"""
LUMENIS Shared Evaluation — Agent Trajectory Evaluation
======================================================
执行完成后评估：步骤效率、工具选择质量、目标达成度、成本。

评分维度：
  - goal_completion   : 目标达成度（0-1）
  - step_efficiency   : 步骤效率（实际步数 vs 预期步数）
  - cost_efficiency   : 成本效率（实际成本 vs 预算）
  - safety_compliance : 安全合规（权限/防火墙/围栏通过率）

结果写入 ai_task_evidence（复用 ai_task_engine._db_add_evidence）。

设计原则：
  - 确定性评分，不依赖 AI
  - 可追溯：每个评分维度有计算依据
  - 可人工修正
  - 由 Shared Evaluation 唯一拥有；Agent Runtime 仅消费此能力

与 OSAI Contract 对齐点（C-08 Trace & Evaluation Contract）：
  - evaluation.score / evaluation.dimensions / evaluation.method
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


@dataclass
class TrajectoryMetrics:
    """轨迹指标（评估输入）。"""
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    replan_count: int = 0
    retry_count: int = 0
    total_duration_ms: float = 0.0
    estimated_cost: float = 0.0
    budget_cost: float = 2.0
    expected_steps: int = 0
    permission_denied_count: int = 0
    firewall_blocked_count: int = 0
    effect_fence_triggered_count: int = 0
    goal_achieved: bool = False
    final_error: Optional[str] = None
    tool_usage: Dict[str, int] = field(default_factory=dict)


@dataclass
class DimensionScore:
    """单维度评分。"""
    name: str
    score: float                    # 0.0 - 1.0
    weight: float                   # 权重
    details: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrajectoryEvaluation:
    """完整轨迹评估结果。"""
    evaluation_id: str = field(default_factory=lambda: f"eval_{uuid.uuid4().hex[:12]}")
    agent_id: str = ""
    task_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    method: str = "deterministic"   # deterministic / llm / human

    # 四维评分
    goal_completion: DimensionScore = field(default_factory=lambda: DimensionScore(
        name="goal_completion", score=0.0, weight=0.35))
    step_efficiency: DimensionScore = field(default_factory=lambda: DimensionScore(
        name="step_efficiency", score=0.0, weight=0.25))
    cost_efficiency: DimensionScore = field(default_factory=lambda: DimensionScore(
        name="cost_efficiency", score=0.0, weight=0.20))
    safety_compliance: DimensionScore = field(default_factory=lambda: DimensionScore(
        name="safety_compliance", score=0.0, weight=0.20))

    # 综合评分
    overall_score: float = 0.0
    grade: str = "F"                # S/A/B/C/D/F
    metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["goal_completion"] = self.goal_completion.to_dict()
        d["step_efficiency"] = self.step_efficiency.to_dict()
        d["cost_efficiency"] = self.cost_efficiency.to_dict()
        d["safety_compliance"] = self.safety_compliance.to_dict()
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class TrajectoryEvaluator:
    """轨迹评估器。

    用法：
        evaluator = TrajectoryEvaluator()
        metrics = TrajectoryMetrics(total_steps=5, completed_steps=5, goal_achieved=True, ...)
        result = evaluator.evaluate(metrics)
        print(result.overall_score, result.grade)
    """

    # 评分等级阈值
    GRADE_THRESHOLDS = [
        (0.90, "S"),
        (0.80, "A"),
        (0.70, "B"),
        (0.60, "C"),
        (0.40, "D"),
        (0.0, "F"),
    ]

    def __init__(self, persist_func: Optional[Callable] = None):
        """
        Args:
            persist_func: 评估结果持久化回调 callback(evaluation) -> None
                          可传入 ai_task_engine._db_add_evidence 的包装
        """
        self._persist_func = persist_func

    def evaluate(
        self,
        metrics: TrajectoryMetrics,
        agent_id: str = "",
        task_id: str = "",
    ) -> TrajectoryEvaluation:
        """执行轨迹评估。

        Args:
            metrics: 轨迹指标
            agent_id: Agent ID
            task_id: 任务 ID

        Returns:
            TrajectoryEvaluation 评估结果
        """
        result = TrajectoryEvaluation(
            agent_id=agent_id,
            task_id=task_id,
            metrics=asdict(metrics),
        )

        # 1. 目标达成度
        result.goal_completion = self._score_goal_completion(metrics)

        # 2. 步骤效率
        result.step_efficiency = self._score_step_efficiency(metrics)

        # 3. 成本效率
        result.cost_efficiency = self._score_cost_efficiency(metrics)

        # 4. 安全合规
        result.safety_compliance = self._score_safety_compliance(metrics)

        # 综合评分（加权平均）
        result.overall_score = round(
            result.goal_completion.score * result.goal_completion.weight
            + result.step_efficiency.score * result.step_efficiency.weight
            + result.cost_efficiency.score * result.cost_efficiency.weight
            + result.safety_compliance.score * result.safety_compliance.weight,
            4,
        )

        # 等级
        result.grade = self._compute_grade(result.overall_score)

        # 改进建议
        result.recommendations = self._generate_recommendations(metrics, result)

        # 持久化
        if self._persist_func:
            try:
                self._persist_func(result)
            except Exception:
                pass

        return result

    def _score_goal_completion(self, metrics: TrajectoryMetrics) -> DimensionScore:
        """目标达成度评分。"""
        if metrics.goal_achieved:
            score = 1.0
            reasoning = "目标达成"
        elif metrics.completed_steps > 0 and metrics.total_steps > 0:
            completion_ratio = metrics.completed_steps / metrics.total_steps
            score = min(completion_ratio * 0.8, 0.8)  # 未完全达成最高0.8
            reasoning = f"部分达成：完成 {metrics.completed_steps}/{metrics.total_steps} 步"
        else:
            score = 0.0
            reasoning = "目标未达成"

        # 失败步骤扣分
        if metrics.failed_steps > 0:
            penalty = min(metrics.failed_steps * 0.1, 0.3)
            score = max(0.0, score - penalty)
            reasoning += f"，{metrics.failed_steps} 步失败扣 {penalty:.1f}"

        return DimensionScore(
            name="goal_completion",
            score=round(score, 4),
            weight=0.35,
            details={
                "goal_achieved": metrics.goal_achieved,
                "completed_steps": metrics.completed_steps,
                "total_steps": metrics.total_steps,
                "failed_steps": metrics.failed_steps,
            },
            reasoning=reasoning,
        )

    def _score_step_efficiency(self, metrics: TrajectoryMetrics) -> DimensionScore:
        """步骤效率评分。"""
        if metrics.expected_steps <= 0:
            # 无预期步数时，按重试和重规划扣分
            base = 1.0
            retry_penalty = min(metrics.retry_count * 0.05, 0.2)
            replan_penalty = min(metrics.replan_count * 0.1, 0.3)
            score = max(0.0, base - retry_penalty - replan_penalty)
            reasoning = f"无预期步数；重试 {metrics.retry_count} 次扣 {retry_penalty:.2f}，重规划 {metrics.replan_count} 次扣 {replan_penalty:.2f}"
        else:
            # 实际步数 vs 预期步数
            actual = metrics.total_steps
            expected = metrics.expected_steps
            if actual <= expected:
                score = 1.0
                reasoning = f"实际 {actual} 步 ≤ 预期 {expected} 步"
            else:
                ratio = expected / actual
                score = max(0.3, ratio)
                reasoning = f"实际 {actual} 步 > 预期 {expected} 步，效率比 {ratio:.2f}"

            # 重规划扣分
            if metrics.replan_count > 0:
                penalty = min(metrics.replan_count * 0.1, 0.2)
                score = max(0.0, score - penalty)
                reasoning += f"，重规划扣 {penalty:.2f}"

        return DimensionScore(
            name="step_efficiency",
            score=round(score, 4),
            weight=0.25,
            details={
                "total_steps": metrics.total_steps,
                "expected_steps": metrics.expected_steps,
                "retry_count": metrics.retry_count,
                "replan_count": metrics.replan_count,
            },
            reasoning=reasoning,
        )

    def _score_cost_efficiency(self, metrics: TrajectoryMetrics) -> DimensionScore:
        """成本效率评分。"""
        if metrics.budget_cost <= 0:
            score = 1.0
            reasoning = "无预算限制"
        elif metrics.estimated_cost <= metrics.budget_cost:
            ratio = metrics.estimated_cost / metrics.budget_cost
            score = 1.0 - ratio * 0.3  # 用得越少分越高，最多扣0.3
            reasoning = f"成本 ${metrics.estimated_cost:.4f} / 预算 ${metrics.budget_cost:.2f}（{ratio*100:.1f}%）"
        else:
            over_ratio = metrics.estimated_cost / metrics.budget_cost
            score = max(0.0, 1.0 - (over_ratio - 1.0) * 0.5)
            reasoning = f"超预算：${metrics.estimated_cost:.4f} / ${metrics.budget_cost:.2f}（{over_ratio*100:.1f}%）"

        return DimensionScore(
            name="cost_efficiency",
            score=round(score, 4),
            weight=0.20,
            details={
                "estimated_cost": metrics.estimated_cost,
                "budget_cost": metrics.budget_cost,
            },
            reasoning=reasoning,
        )

    def _score_safety_compliance(self, metrics: TrajectoryMetrics) -> DimensionScore:
        """安全合规评分。"""
        total_checks = (
            metrics.permission_denied_count
            + metrics.firewall_blocked_count
            + metrics.effect_fence_triggered_count
        )

        if total_checks == 0:
            score = 1.0
            reasoning = "无安全拦截记录"
        else:
            # 权限拒绝和防火墙拦截是正常安全行为，不扣分
            # 但如果有 effect_fence 触发（写操作被围栏），需要关注
            fence_ratio = (
                metrics.effect_fence_triggered_count / max(metrics.total_steps, 1)
            )
            score = max(0.5, 1.0 - fence_ratio * 0.5)
            reasoning = (
                f"权限拒绝 {metrics.permission_denied_count} 次，"
                f"防火墙拦截 {metrics.firewall_blocked_count} 次，"
                f"效果围栏触发 {metrics.effect_fence_triggered_count} 次"
            )

        return DimensionScore(
            name="safety_compliance",
            score=round(score, 4),
            weight=0.20,
            details={
                "permission_denied": metrics.permission_denied_count,
                "firewall_blocked": metrics.firewall_blocked_count,
                "effect_fence_triggered": metrics.effect_fence_triggered_count,
            },
            reasoning=reasoning,
        )

    def _compute_grade(self, score: float) -> str:
        """计算等级。"""
        for threshold, grade in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "F"

    def _generate_recommendations(
        self,
        metrics: TrajectoryMetrics,
        result: TrajectoryEvaluation,
    ) -> List[str]:
        """生成改进建议。"""
        recs = []

        if result.goal_completion.score < 0.7:
            recs.append("目标达成度低，建议优化规划步骤分解或增加验证环节")

        if result.step_efficiency.score < 0.7:
            if metrics.replan_count > 0:
                recs.append(f"重规划 {metrics.replan_count} 次，建议提升初始规划质量")
            if metrics.retry_count > 3:
                recs.append(f"重试 {metrics.retry_count} 次，建议检查工具稳定性和参数合理性")

        if result.cost_efficiency.score < 0.7:
            recs.append("成本效率低，建议优化模型选择（日常用 glm-4.5-air，仅深度规划用 glm-5.3）")

        if metrics.effect_fence_triggered_count > 0:
            recs.append("存在写操作被效果围栏拦截，建议确认是否需要人工审批后执行")

        if metrics.failed_steps > 0:
            recs.append(f"有 {metrics.failed_steps} 个失败步骤，建议分析失败原因并优化工具选择")

        if not recs:
            recs.append("执行质量良好，保持当前策略")

        return recs

    def compare_trajectories(
        self,
        eval1: TrajectoryEvaluation,
        eval2: TrajectoryEvaluation,
    ) -> Dict[str, Any]:
        """比较两次轨迹评估结果。"""
        return {
            "overall_delta": round(eval2.overall_score - eval1.overall_score, 4),
            "goal_completion_delta": round(
                eval2.goal_completion.score - eval1.goal_completion.score, 4),
            "step_efficiency_delta": round(
                eval2.step_efficiency.score - eval1.step_efficiency.score, 4),
            "cost_efficiency_delta": round(
                eval2.cost_efficiency.score - eval1.cost_efficiency.score, 4),
            "safety_compliance_delta": round(
                eval2.safety_compliance.score - eval1.safety_compliance.score, 4),
            "better": eval2.agent_id if eval2.overall_score > eval1.overall_score else eval1.agent_id,
        }
