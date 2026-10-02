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
import re
import uuid
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from agent_capability.formation import digest


@dataclass(frozen=True)
class OutcomeAssertion:
    """Requirement supplied by the existing authenticated task/artifact owner.

    Expected values are task intent, never observations. Known artifacts keep
    their expected digest. A newly generated artifact instead freezes an exact
    canonical-committed-artifact:v1 requirement in expected_value. Only the
    committed Task/Artifact owner may subsequently bind its unknown bytes.
    """
    assertion_id: str
    kind: str  # evidence / artifact / effect / environment / user_constraint
    reference: str
    expected_sha256: Optional[str] = None
    expected_value: Any = None


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
    score_scope: str = "OPERATIONAL_TRAJECTORY_ONLY"
    outcome_verification: Dict[str, Any] = field(default_factory=dict)

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

    def __init__(self, persist_func: Optional[Callable] = None,
                 outcome_contract_func: Optional[Callable] = None,
                 outcome_resolver: Optional[Callable] = None,
                 committed_artifact_resolver: Optional[Callable] = None):
        """
        Args:
            persist_func: 评估结果持久化回调 callback(evaluation) -> None
                          可传入 ai_task_engine._db_add_evidence 的包装
        """
        self._persist_func = persist_func
        self._outcome_contract_func = outcome_contract_func
        self._outcome_resolver = outcome_resolver
        # Server-injected canonical read path, never model/tool output or a
        # caller-supplied receipt. It adds no store, writer or approval owner.
        self._committed_artifact_resolver = committed_artifact_resolver

    @property
    def has_outcome_contract(self):
        return (self._outcome_contract_func is not None or self._outcome_resolver is not None
                or self._committed_artifact_resolver is not None)

    @staticmethod
    def _generated_spec(row):
        if row.kind != "artifact" or row.expected_sha256 is not None:
            return None
        spec = row.expected_value
        fields = {"schema", "domain_id", "scope", "output_type", "parent_version_id", "requirements"}
        if (type(spec) is not dict or set(spec) != fields
                or spec["schema"] != "canonical-committed-artifact:v1"
                or any(type(spec[key]) is not str or not spec[key].strip()
                       for key in ("domain_id", "output_type"))
                or type(spec["scope"]) is not dict or not spec["scope"]
                or type(spec["requirements"]) is not dict or not spec["requirements"]
                or (spec["parent_version_id"] is not None and
                    (type(spec["parent_version_id"]) is not str or not spec["parent_version_id"].strip()))):
            raise ValueError("OUTCOME_GENERATED_REQUIREMENT_INVALID")
        # Validate canonical JSON shape without converting missing/bool to zero.
        digest(spec)
        return spec

    def _outcome_contract(self, task_id):
        if not callable(self._outcome_contract_func) or not callable(self._outcome_resolver):
            raise ValueError("OUTCOME_OWNER_NOT_BOUND")
        assertions = self._outcome_contract_func(task_id)
        allowed = {"evidence", "artifact", "effect", "environment", "user_constraint"}
        if (not isinstance(assertions, (list, tuple)) or not assertions
                or any(not isinstance(row, OutcomeAssertion) or not row.assertion_id
                       or row.kind not in allowed or not row.reference for row in assertions)
                or len({r.assertion_id for r in assertions}) != len(assertions)
                or not any(r.kind in {"evidence", "artifact"} for r in assertions)):
            raise ValueError("OUTCOME_CONTRACT_INVALID")
        for row in assertions:
            if row.kind == "artifact" and row.expected_sha256 is None:
                self._generated_spec(row)
                continue
            if row.kind in {"evidence", "artifact"} and (
                    not isinstance(row.expected_sha256, str)
                    or not re.fullmatch(r"[0-9a-f]{64}", row.expected_sha256)):
                raise ValueError("OUTCOME_EXPECTED_IDENTITY_MISSING")
        return tuple(deepcopy(assertions))

    def form_outcome_contract(self, task_id):
        if not self.has_outcome_contract:
            return None
        return digest([asdict(r) for r in self._outcome_contract(task_id)])

    def _committed_output(self, row, task_id, identity, expected_bindings, require_bound):
        spec = self._generated_spec(row)
        if not callable(self._committed_artifact_resolver):
            raise ValueError("OUTCOME_COMMITTED_OWNER_NOT_BOUND")

        def read_receipt():
            receipt = self._committed_artifact_resolver(row, task_id, identity)
            if type(receipt) is not dict or receipt.get("state") != "COMMITTED":
                raise ValueError("OUTCOME_COMMIT_UNAVAILABLE")
            exact = {"schema": "canonical-committed-output-receipt:v1", "task_id": task_id,
                     "assertion_id": row.assertion_id, "contract_sha256": identity,
                     "domain_id": spec["domain_id"], "scope": spec["scope"],
                     "output_type": spec["output_type"], "parent_version_id": spec["parent_version_id"]}
            if any(key not in receipt or not canonical_equal(receipt[key], value)
                   for key, value in exact.items()):
                raise ValueError("OUTCOME_COMMIT_LINEAGE_MISMATCH")
            if (any(type(receipt.get(key)) is not str or not receipt[key].strip()
                    for key in ("artifact_ref", "version_id"))
                    or receipt["version_id"] == spec["parent_version_id"]
                    or not isinstance(receipt.get("sha256"), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", receipt["sha256"])
                    or type(receipt.get("byte_length")) is not int or receipt["byte_length"] <= 0):
                raise ValueError("OUTCOME_COMMIT_IDENTITY_INVALID")
            constraints = receipt.get("constraint_observations")
            if (type(constraints) is not dict or any(key not in constraints
                    or not canonical_equal(constraints[key], value)
                    for key, value in spec["requirements"].items())):
                raise ValueError("OUTCOME_COMMIT_CONSTRAINT_MISMATCH")
            # Exclude volatile access metadata; retain all immutable lineage,
            # constraints, identity and bytes for subsequent completed readback.
            retained = {**exact, **{key: receipt[key] for key in
                        ("artifact_ref", "version_id", "sha256", "byte_length", "constraint_observations")}}
            return deepcopy(retained)

        receipt = read_receipt()
        binding = {"receipt_sha256": digest(receipt), "artifact_ref": receipt["artifact_ref"],
                   "version_id": receipt["version_id"], "sha256": receipt["sha256"]}
        previous = (expected_bindings or {}).get(row.assertion_id)
        if require_bound and previous is None:
            raise ValueError("OUTCOME_COMMIT_BINDING_MISSING")
        if previous is not None and not canonical_equal(previous, binding):
            raise ValueError("OUTCOME_COMMIT_BINDING_CHANGED")
        # The canonical owner reopens these actual committed bytes/version. A
        # receipt alone, tool result or content hash alone cannot pass this read.
        actual = self._outcome_resolver(row, task_id, committed_receipt=deepcopy(receipt))
        if type(actual) is not dict or actual.get("state") != "AVAILABLE":
            raise ValueError("OUTCOME_UNAVAILABLE")
        expected_read = {"reference": row.reference, "kind": "artifact", "sha256": receipt["sha256"],
                         "artifact_ref": receipt["artifact_ref"], "version_id": receipt["version_id"],
                         "task_id": task_id, "domain_id": spec["domain_id"], "scope": spec["scope"],
                         "parent_version_id": spec["parent_version_id"], "byte_length": receipt["byte_length"]}
        if any(key not in actual or not canonical_equal(actual[key], value)
               for key, value in expected_read.items()):
            raise ValueError("OUTCOME_COMMITTED_READBACK_MISMATCH")
        if not canonical_equal(read_receipt(), receipt):
            raise ValueError("OUTCOME_COMMIT_CHANGED_DURING_READ")
        return binding

    def verify_outcome(self, task_id, expected_contract_sha256=None, *,
                       expected_output_receipts=None, require_bound_receipts=False):
        result = {"state": "NOT_VERIFIED", "verified_goal_achieved": False,
                  "user_verified": False, "checks": [], "reason": "OUTCOME_OWNER_NOT_BOUND",
                  "committed_output_bindings": {}}
        if not self.has_outcome_contract:
            return result
        try:
            if expected_output_receipts is not None and type(expected_output_receipts) is not dict:
                raise ValueError("OUTCOME_COMMIT_BINDING_INVALID")
            expected_output_receipts = deepcopy(expected_output_receipts)
            assertions = self._outcome_contract(task_id)
            identity = digest([asdict(r) for r in assertions])
            if expected_contract_sha256 is None:
                raise ValueError("OUTCOME_CONTRACT_MISSING")
            if identity != expected_contract_sha256:
                raise ValueError("OUTCOME_CONTRACT_CHANGED")
            for row in assertions:
                check = {"assertion_id": row.assertion_id, "kind": row.kind,
                         "reference": row.reference, "state": "NOT_VERIFIED"}
                try:
                    if row.kind == "artifact" and row.expected_sha256 is None:
                        binding = self._committed_output(row, task_id, identity,
                                                         expected_output_receipts, require_bound_receipts)
                        result["committed_output_bindings"][row.assertion_id] = binding
                        check.update(state="VERIFIED", reason="CANONICAL_COMMIT_AND_REOPEN_MATCHED")
                        result["checks"].append(check)
                        continue
                    actual = self._outcome_resolver(row, task_id)
                    if not isinstance(actual, dict) or actual.get("state") != "AVAILABLE":
                        check["reason"] = "OUTCOME_UNAVAILABLE"
                    elif actual.get("reference") != row.reference or actual.get("kind") != row.kind:
                        check.update(state="FAILED", reason="OUTCOME_IDENTITY_MISMATCH")
                    elif row.kind in {"evidence", "artifact"} and actual.get("sha256") != row.expected_sha256:
                        check.update(state="FAILED", reason="OUTCOME_DIGEST_MISMATCH")
                    elif row.kind not in {"evidence", "artifact"} and (
                            "value" not in actual or canonical_equal(actual["value"], row.expected_value) is not True):
                        check.update(state="FAILED", reason="OUTCOME_EXPECTATION_MISMATCH")
                    else:
                        check.update(state="VERIFIED", reason="CANONICAL_OBSERVATION_MATCHED")
                except Exception as exc:
                    safe = str(exc)
                    known = {"OUTCOME_COMMITTED_OWNER_NOT_BOUND", "OUTCOME_COMMIT_UNAVAILABLE", "OUTCOME_UNAVAILABLE"}
                    failures = {"OUTCOME_COMMIT_LINEAGE_MISMATCH", "OUTCOME_COMMIT_IDENTITY_INVALID",
                                "OUTCOME_COMMIT_CONSTRAINT_MISMATCH", "OUTCOME_COMMIT_BINDING_MISSING",
                                "OUTCOME_COMMIT_BINDING_CHANGED", "OUTCOME_COMMITTED_READBACK_MISMATCH",
                                "OUTCOME_COMMIT_CHANGED_DURING_READ"}
                    check["reason"] = safe if safe in known | failures else "OUTCOME_OWNER_UNAVAILABLE"
                    if safe in failures:
                        check["state"] = "FAILED"
                result["checks"].append(check)
            # Detect a requirement/configuration change during owner reads.
            if self.form_outcome_contract(task_id) != identity:
                raise ValueError("OUTCOME_CONTRACT_CHANGED")
            states = {check["state"] for check in result["checks"]}
            result["state"] = "FAILED" if "FAILED" in states else (
                "VERIFIED" if states == {"VERIFIED"} else "NOT_VERIFIED")
            result["verified_goal_achieved"] = result["state"] == "VERIFIED"
            if result["state"] != "VERIFIED":
                result["committed_output_bindings"] = {}
            result["reason"] = "CANONICAL_OUTCOME_CHECKS"  # no user material or owner errors
        except Exception as exc:
            safe = str(exc)
            result.update(state="BLOCKED", reason=safe if safe in {
                "OUTCOME_OWNER_NOT_BOUND", "OUTCOME_CONTRACT_INVALID", "OUTCOME_EXPECTED_IDENTITY_MISSING",
                "OUTCOME_CONTRACT_MISSING", "OUTCOME_CONTRACT_CHANGED",
                "OUTCOME_GENERATED_REQUIREMENT_INVALID", "OUTCOME_COMMIT_BINDING_INVALID"} else "OUTCOME_OWNER_UNAVAILABLE")
            result["committed_output_bindings"] = {}
        return result

    def evaluate(
        self,
        metrics: TrajectoryMetrics,
        agent_id: str = "",
        task_id: str = "",
        expected_contract_sha256: Optional[str] = None,
        expected_output_receipts: Optional[Dict[str, Any]] = None,
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
        result.outcome_verification = self.verify_outcome(
            task_id, expected_contract_sha256, expected_output_receipts=expected_output_receipts)

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
            reasoning = "执行器报告步骤完成；业务结果须独立核验"
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
                "claim_source": "EXECUTION_METRICS",
                "business_outcome_verified": False,
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


def canonical_equal(actual, expected):
    # Strict JSON comparison distinguishes false/zero, missing/zero and values
    # from their string representations; no missing-to-zero transformations.
    return digest(actual) == digest(expected)
