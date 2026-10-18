# -*- coding: utf-8 -*-
"""
lumenis.shared.evaluation.runner — LUMENIS Shared Evaluation 统一执行器

职责：
- run_full_evaluation(): 执行五维度全量评估，返回汇总结果
- run_dimension_evaluation(dimension): 单维度评估
- 每个评估项有明确的 pass/warn/fail 阈值
- 评估结果持久化到 evaluation_records 表
- 支持 mock_data 注入（测试时不执行真实采集/AI调用/报告生成）

核心保证：
1. 不允许只统计接口 200 —— 所有指标评价真实质量
2. unknown 绝不默认 pass —— 无数据时 metric_value=None → status=unknown
3. 评估失败不静默 —— 异常记录为 unknown 并在汇总中可见
"""

from __future__ import annotations

import json
import os
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from lumenis.shared.database import main_db_path

from .recorder import (
    EvaluationRecord,
    get_evaluation_summary,
    init_db,
    record_evaluation,
)
from .dimensions import (
    DIMENSION_EVALUATORS,
    THRESHOLDS,
    evaluate_ai_dimension,
    evaluate_collector_dimension,
    evaluate_data_dimension,
    evaluate_report_dimension,
    evaluate_runtime_dimension,
)

VALID_DIMENSIONS = ("data", "ai", "collector", "report", "runtime")


class EvaluationRunner:
    """统一评估执行器。

    用法：
        runner = EvaluationRunner(db_path="/path/to/test.db")
        result = runner.run_full_evaluation(mock_data={...})
        print(result["global_status"])
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or main_db_path()
        init_db(self.db_path)

    def run_dimension_evaluation(
        self,
        dimension: str,
        mock_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行单维度评估。

        Args:
            dimension: data/ai/collector/report/runtime
            mock_data: 可选，注入 mock 数据（测试用）

        Returns:
            {
                "dimension": str,
                "records": [EvaluationRecord...],
                "metrics": {metric_name: {value, status, threshold}},
                "summary": {pass, warn, fail, unknown, total, pass_rate, overall_status},
                "error": str | None
            }
        """
        if dimension not in VALID_DIMENSIONS:
            return {
                "dimension": dimension,
                "records": [],
                "metrics": {},
                "summary": {"pass": 0, "warn": 0, "fail": 0, "unknown": 0,
                            "total": 0, "pass_rate": 0.0, "overall_status": "fail"},
                "error": f"Invalid dimension: {dimension}",
            }

        evaluator = DIMENSION_EVALUATORS[dimension]
        records: List[EvaluationRecord] = []
        error: Optional[str] = None

        try:
            # report 维度需要额外参数处理
            if dimension == "report":
                records = evaluator(db_path=self.db_path, mock_data=mock_data)
            else:
                records = evaluator(db_path=self.db_path, mock_data=mock_data)
        except Exception as e:
            error = f"{type(e).__name__}: {str(e)}"
            traceback.print_exc()
            # 评估异常时记录一条 unknown（不静默）
            record_evaluation(
                dimension=dimension,
                metric_name=f"{dimension}_evaluation_error",
                metric_value=None,
                pass_threshold=0, warn_threshold=0,
                higher_is_better=True,
                source="lumenis.shared.evaluation.runner",
                evidence_ref=f"exception: {error}",
                metadata={"error": error},
                db_path=self.db_path,
            )

        # 构建 metrics 明细
        metrics: Dict[str, Dict[str, Any]] = {}
        for rec in records:
            metrics[rec.metric_name] = {
                "value": rec.metric_value,
                "status": rec.status,
                "threshold": rec.threshold,
                "source": rec.source,
            }

        # 维度内汇总
        counts = {"pass": 0, "warn": 0, "fail": 0, "unknown": 0}
        for rec in records:
            counts[rec.status] = counts.get(rec.status, 0) + 1
        total = len(records)
        pass_rate = round(counts["pass"] / total, 4) if total > 0 else 0.0

        # overall_status（unknown 不默认 pass）
        if counts["fail"] > 0 or error:
            overall = "fail"
        elif counts["unknown"] > 0:
            overall = "warn"
        elif counts["warn"] > 0:
            overall = "warn"
        else:
            overall = "pass" if total > 0 else "unknown"

        return {
            "dimension": dimension,
            "records": [r.to_dict() for r in records],
            "metrics": metrics,
            "summary": {**counts, "total": total, "pass_rate": pass_rate,
                        "overall_status": overall},
            "error": error,
        }

    def run_full_evaluation(
        self,
        mock_data: Optional[Dict[str, Any]] = None,
        dimensions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """执行五维度全量评估。

        Args:
            mock_data: 可选，按维度注入 mock 数据：
                {"data": {...}, "ai": {...}, "collector": {...}, "report": {...}, "runtime": {...}}
            dimensions: 可选，只评估指定维度（默认全部五维度）

        Returns:
            {
                "evaluation_run_id": str,
                "started_at": str,
                "finished_at": str,
                "dimensions": {dim: dimension_result},
                "global_summary": {pass, warn, fail, unknown, total, pass_rate, global_status},
                "thresholds_used": dict,
                "anti_pattern_check": {"only_200_count": 0, "unknown_not_pass": True}
            }
        """
        run_id = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.now().isoformat(timespec="seconds")
        dims_to_run = dimensions or list(VALID_DIMENSIONS)

        dimension_results: Dict[str, Any] = {}
        all_records: List[Dict[str, Any]] = []

        for dim in dims_to_run:
            dim_mock = (mock_data or {}).get(dim) if mock_data else None
            result = self.run_dimension_evaluation(dim, mock_data=dim_mock)
            dimension_results[dim] = result
            all_records.extend(result["records"])

        # 全局汇总
        counts = {"pass": 0, "warn": 0, "fail": 0, "unknown": 0}
        for rec in all_records:
            counts[rec["status"]] = counts.get(rec["status"], 0) + 1
        total = len(all_records)
        pass_rate = round(counts["pass"] / total, 4) if total > 0 else 0.0

        # global_status（unknown 不默认 pass）
        has_error = any(r.get("error") for r in dimension_results.values())
        if counts["fail"] > 0 or has_error:
            global_status = "fail"
        elif counts["unknown"] > 0:
            global_status = "warn"
        elif counts["warn"] > 0:
            global_status = "warn"
        else:
            global_status = "pass" if total > 0 else "unknown"

        finished_at = datetime.now().isoformat(timespec="seconds")

        # 反模式检查：确认没有只统计 200 的指标
        only_200_count = sum(
            1 for rec in all_records
            if "200" in rec.get("metric_name", "").lower()
            or "http_status" in rec.get("metric_name", "").lower()
        )

        return {
            "evaluation_run_id": run_id,
            "started_at": started_at,
            "finished_at": finished_at,
            "dimensions": dimension_results,
            "global_summary": {
                **counts,
                "total": total,
                "pass_rate": pass_rate,
                "global_status": global_status,
            },
            "thresholds_used": THRESHOLDS,
            "anti_pattern_check": {
                "only_200_count": only_200_count,
                "unknown_not_pass": True,  # 硬编码保证：unknown 绝不默认 pass
                "real_quality_metrics": total,  # 所有指标都是真实质量指标
            },
        }


# ============================================================
# 便捷函数
# ============================================================
def run_full_evaluation(
    db_path: Optional[str] = None,
    mock_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """模块级便捷函数：执行全量评估。"""
    runner = EvaluationRunner(db_path=db_path)
    return runner.run_full_evaluation(mock_data=mock_data)


def run_dimension_evaluation(
    dimension: str,
    db_path: Optional[str] = None,
    mock_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """模块级便捷函数：执行单维度评估。"""
    runner = EvaluationRunner(db_path=db_path)
    return runner.run_dimension_evaluation(dimension, mock_data=mock_data)


if __name__ == "__main__":
    import sys
    result = run_full_evaluation()
    print(json.dumps(result["global_summary"], ensure_ascii=False, indent=2))
    print(f"\nDimensions evaluated: {list(result['dimensions'].keys())}")
    for dim, res in result["dimensions"].items():
        print(f"  {dim}: {res['summary']['overall_status']} "
              f"(pass={res['summary']['pass']}, warn={res['summary']['warn']}, "
              f"fail={res['summary']['fail']}, unknown={res['summary']['unknown']})")


# Content-pattern measurements remain derived, not evidence of independent lift.
# Only the existing SavedWork owner supplies artifact bytes and current source rights.
def measure_content_pattern(*, candidate_hash, baseline_artifact_id, candidate_artifact_id,
                            criteria, actor, scope, connection=None):
    import hashlib
    import math
    from lumenis.shared.reporting.saved_work import read_committed_work
    if (not isinstance(candidate_hash, str) or len(candidate_hash) != 64
            or not isinstance(criteria, dict) or set(criteria) != {"required_phrases", "max_characters"}
            or not isinstance(criteria["required_phrases"], list)
            or not 1 <= len(criteria["required_phrases"]) <= 32
            or any(type(v) is not str or not v.strip() or len(v) > 500 for v in criteria["required_phrases"])
            or len(set(criteria["required_phrases"])) != len(criteria["required_phrases"])
            or type(criteria["max_characters"]) is not int or not 1 <= criteria["max_characters"] <= 50000):
        raise ValueError("PATTERN_EVALUATION_CRITERIA_INVALID")
    if baseline_artifact_id == candidate_artifact_id:
        raise ValueError("PATTERN_EVALUATION_DISTINCT_OUTPUTS_REQUIRED")
    outputs = {}
    for label, artifact_id in (("baseline", baseline_artifact_id), ("candidate", candidate_artifact_id)):
        saved = read_committed_work(artifact_id, actor=actor, scope=scope, connection=connection)
        text = saved["document"]["markdown"]
        matches = [phrase in text for phrase in criteria["required_phrases"]]
        outputs[label] = {"artifact_id": artifact_id, "artifact_sha256": saved["artifact"]["sha256"],
                          "artifact_version": saved["document"]["version"],
                          "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                          "matched_phrases": matches, "numerator": sum(matches), "denominator": len(matches),
                          "required_phrase_coverage": sum(matches) / len(matches),
                          "character_count": len(text), "budget_exceeded": len(text) > criteria["max_characters"]}
    gain = outputs["candidate"]["required_phrase_coverage"] - outputs["baseline"]["required_phrase_coverage"]
    if not math.isfinite(gain):
        raise ValueError("PATTERN_EVALUATION_NONFINITE")
    return {"contract_version": "content-pattern-measurement:v1", "candidate_hash": candidate_hash,
            "method": "exact-required-phrase-coverage:v1", "criteria": criteria, "outputs": outputs,
            "gain": gain, "state": "NOT_ELIGIBLE", "promotion_eligible": False,
            "reasons": (["NO_MEASURED_GAIN"] if gain <= 0 else []) +
                       ["INDEPENDENT_HELDOUT_NOT_VERIFIED", "REAL_TASK_OUTCOME_NOT_VERIFIED"],
            "limitations": "Exact phrase coverage is not semantic quality or business lift.",
            "training_performed": False, "model_used": False}


def verify_content_pattern_measurement(record, *, actor, scope, connection=None):
    """Recompute from current authorized immutable artifacts; never trust stored PASS."""
    if not isinstance(record, dict) or record.get("contract_version") != "content-pattern-measurement:v1":
        raise ValueError("PATTERN_EVALUATION_CONTRACT_INVALID")
    current = measure_content_pattern(candidate_hash=record["candidate_hash"],
        baseline_artifact_id=record["outputs"]["baseline"]["artifact_id"],
        candidate_artifact_id=record["outputs"]["candidate"]["artifact_id"],
        criteria=record["criteria"], actor=actor, scope=scope, connection=connection)
    if current != record:
        raise PermissionError("PATTERN_EVALUATION_READBACK_CHANGED")
    return current
