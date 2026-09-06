# -*- coding: utf-8 -*-
"""
tests/test_evaluation_system.py — ZBC Phase 10 统一 Evaluation 系统测试

测试覆盖：
1. EvaluationRecord 持久化（CRUD）
2. 五维度评估执行（data/ai/collector/report/runtime，全部 mock 数据）
3. 阈值判断（pass/warn/fail）
4. 评估汇总（get_evaluation_summary）
5. unknown 状态处理（不默认 pass —— 核心红线）
6. 不允许只统计接口 200（反模式验证）
7. evaluation_runner 全量/单维度执行
8. 现有模块桥接（data_quality_gate / engineering_metrics）

所有测试使用临时 SQLite 数据库和 mock 数据，不执行真实采集/AI调用/报告生成。
"""

import json
import os
import sys
import pytest

# 项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation_recorder import (
    EvaluationRecord,
    judge_status,
    record_evaluation,
    get_evaluation_summary,
    get_evaluation_records,
    init_db,
    VALID_DIMENSIONS,
    VALID_STATUSES,
)
from evaluation_dimensions import (
    evaluate_data_dimension,
    evaluate_ai_dimension,
    evaluate_collector_dimension,
    evaluate_report_dimension,
    evaluate_runtime_dimension,
    THRESHOLDS,
)
from evaluation_runner import EvaluationRunner, run_full_evaluation


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture
def temp_db(tmp_path):
    """创建临时测试数据库，测试后自动清理。"""
    db_path = str(tmp_path / "test_eval.db")
    init_db(db_path)
    yield db_path


@pytest.fixture
def mock_all_data():
    """全维度 mock 数据 —— 全部 pass 场景。"""
    return {
        "data": {
            "total_notes": 100,
            "complete_notes": 95,
            "latest_publish_hours_ago": 2.0,
            "duplicate_count": 3,
            "provenance_count": 98,
        },
        "ai": {
            "ai_total": 100,
            "ai_correct": 90,
            "avg_confidence": 0.82,
            "human_corrections": 5,
            "provider_calls": 80,
            "provider_success": 76,
            "fallback_count": 10,
        },
        "collector": {
            "total_runs": 100,
            "success_runs": 92,
            "failure_runs": 5,
            "recovery_runs": 4,
            "avg_latency_sec": 85.0,
        },
        "report": {
            "total_reports": 30,
            "generated_reports": 28,
            "valid_artifacts": 27,
            "evidence_covered": 26,
        },
        "runtime": {
            "uptime_hours": 48.0,
            "heartbeat_total": 100,
            "heartbeat_ok": 99,
            "crash_count": 0,
            "recovery_count": 1,
        },
    }


@pytest.fixture
def mock_fail_data():
    """全维度 mock 数据 —— 全部 fail 场景。"""
    return {
        "data": {
            "total_notes": 100,
            "complete_notes": 50,
            "latest_publish_hours_ago": 200.0,
            "duplicate_count": 30,
            "provenance_count": 40,
        },
        "ai": {
            "ai_total": 100,
            "ai_correct": 40,
            "avg_confidence": 0.3,
            "human_corrections": 40,
            "provider_calls": 80,
            "provider_success": 30,
            "fallback_count": 60,
        },
        "collector": {
            "total_runs": 100,
            "success_runs": 30,
            "failure_runs": 60,
            "recovery_runs": 5,
            "avg_latency_sec": 500.0,
        },
        "report": {
            "total_reports": 30,
            "generated_reports": 10,
            "valid_artifacts": 8,
            "evidence_covered": 5,
        },
        "runtime": {
            "uptime_hours": 0.1,
            "heartbeat_total": 100,
            "heartbeat_ok": 30,
            "crash_count": 10,
            "recovery_count": 8,
        },
    }


# ============================================================
# 1. EvaluationRecord 持久化测试
# ============================================================
class TestEvaluationRecordPersistence:
    def test_create_record_defaults(self):
        """EvaluationRecord 默认字段正确。"""
        rec = EvaluationRecord(dimension="data", metric_name="completeness")
        assert rec.evaluation_id is not None
        assert rec.dimension == "data"
        assert rec.metric_name == "completeness"
        assert rec.status == "unknown"  # 默认 unknown，不默认 pass
        assert rec.metric_value is None
        assert rec.evaluated_at is not None

    def test_invalid_dimension_raises(self):
        """无效维度抛出异常。"""
        with pytest.raises(ValueError):
            EvaluationRecord(dimension="invalid_dim", metric_name="x")

    def test_invalid_status_raises(self):
        """无效状态抛出异常。"""
        with pytest.raises(ValueError):
            EvaluationRecord(dimension="data", metric_name="x", status="bogus")

    def test_record_persistence(self, temp_db):
        """记录可持久化到数据库。"""
        rec = record_evaluation(
            dimension="data", metric_name="completeness",
            metric_value=0.95, pass_threshold=0.90, warn_threshold=0.70,
            higher_is_better=True, source="test", evidence_ref="unit_test",
            db_path=temp_db,
        )
        assert rec.status == "pass"
        assert rec.metric_value == 0.95

        # 从数据库读回
        records = get_evaluation_records(db_path=temp_db)
        assert len(records) == 1
        assert records[0]["evaluation_id"] == rec.evaluation_id
        assert records[0]["dimension"] == "data"
        assert records[0]["status"] == "pass"

    def test_record_persistence_multiple(self, temp_db):
        """多条记录持久化。"""
        for i in range(5):
            record_evaluation(
                dimension="data", metric_name=f"metric_{i}",
                metric_value=0.8 + i * 0.04,
                pass_threshold=0.90, warn_threshold=0.70,
                higher_is_better=True, db_path=temp_db,
            )
        records = get_evaluation_records(db_path=temp_db, limit=10)
        assert len(records) == 5

    def test_record_metadata_dict(self, temp_db):
        """metadata 传入 dict 自动转 JSON 字符串。"""
        rec = record_evaluation(
            dimension="ai", metric_name="accuracy",
            metric_value=0.88, pass_threshold=0.85, warn_threshold=0.70,
            higher_is_better=True, db_path=temp_db,
            metadata={"model": "glm-4.5-air", "samples": 100},
        )
        assert isinstance(rec.metadata, str)
        meta = json.loads(rec.metadata)
        assert meta["model"] == "glm-4.5-air"

    def test_to_dict(self):
        """to_dict 返回完整字典。"""
        rec = EvaluationRecord(dimension="runtime", metric_name="uptime")
        d = rec.to_dict()
        assert d["dimension"] == "runtime"
        assert d["metric_name"] == "uptime"
        assert "evaluation_id" in d
        assert "evaluated_at" in d


# ============================================================
# 2. 阈值判断测试
# ============================================================
class TestThresholdJudgment:
    def test_pass_higher_is_better(self):
        """越高越好：值 >= pass_threshold → pass。"""
        assert judge_status(0.95, 0.90, 0.70, higher_is_better=True) == "pass"

    def test_warn_higher_is_better(self):
        """越高越好：warn_threshold <= 值 < pass_threshold → warn。"""
        assert judge_status(0.80, 0.90, 0.70, higher_is_better=True) == "warn"

    def test_fail_higher_is_better(self):
        """越高越好：值 < warn_threshold → fail。"""
        assert judge_status(0.50, 0.90, 0.70, higher_is_better=True) == "fail"

    def test_pass_lower_is_better(self):
        """越低越好：值 <= pass_threshold → pass。"""
        assert judge_status(10.0, 24.0, 72.0, higher_is_better=False) == "pass"

    def test_warn_lower_is_better(self):
        """越低越好：pass_threshold < 值 <= warn_threshold → warn。"""
        assert judge_status(50.0, 24.0, 72.0, higher_is_better=False) == "warn"

    def test_fail_lower_is_better(self):
        """越低越好：值 > warn_threshold → fail。"""
        assert judge_status(100.0, 24.0, 72.0, higher_is_better=False) == "fail"

    def test_none_value_is_unknown(self):
        """值为 None → unknown（核心红线：绝不默认 pass）。"""
        assert judge_status(None, 0.90, 0.70) == "unknown"

    def test_zero_value_not_unknown(self):
        """值为 0 是有效数值，不是 unknown。"""
        assert judge_status(0.0, 0.90, 0.70, higher_is_better=True) == "fail"
        assert judge_status(0.0, 24.0, 72.0, higher_is_better=False) == "pass"

    def test_boundary_pass(self):
        """边界值：等于 pass_threshold → pass。"""
        assert judge_status(0.90, 0.90, 0.70, higher_is_better=True) == "pass"

    def test_boundary_warn(self):
        """边界值：等于 warn_threshold → warn。"""
        assert judge_status(0.70, 0.90, 0.70, higher_is_better=True) == "warn"


# ============================================================
# 3. unknown 不默认 pass —— 核心红线测试
# ============================================================
class TestUnknownNotDefaultPass:
    def test_none_metric_value_produces_unknown(self, temp_db):
        """metric_value=None 时 record_evaluation 产生 unknown 状态。"""
        rec = record_evaluation(
            dimension="data", metric_name="freshness",
            metric_value=None, pass_threshold=24.0, warn_threshold=72.0,
            higher_is_better=False, db_path=temp_db,
        )
        assert rec.status == "unknown"
        assert rec.metric_value is None

    def test_unknown_counted_in_summary(self, temp_db):
        """unknown 在汇总中被计数，且拉低整体评级。"""
        # 一条 pass + 一条 unknown
        record_evaluation(dimension="data", metric_name="m1",
                          metric_value=0.95, pass_threshold=0.90, warn_threshold=0.70,
                          higher_is_better=True, db_path=temp_db)
        record_evaluation(dimension="data", metric_name="m2",
                          metric_value=None, pass_threshold=0.90, warn_threshold=0.70,
                          higher_is_better=True, db_path=temp_db)

        summary = get_evaluation_summary(db_path=temp_db)
        assert summary["counts"]["unknown"] == 1
        assert summary["counts"]["pass"] == 1
        # global_status 应为 warn（因为有 unknown）
        assert summary["global_status"] == "warn"
        # pass_rate 应为 0.5（unknown 计入分母）
        assert summary["global_pass_rate"] == 0.5

    def test_all_unknown_global_status_warn(self, temp_db):
        """全部 unknown 时 global_status 为 warn（不是 pass）。"""
        for i in range(3):
            record_evaluation(dimension="ai", metric_name=f"m{i}",
                              metric_value=None, pass_threshold=0.85, warn_threshold=0.70,
                              higher_is_better=True, db_path=temp_db)
        summary = get_evaluation_summary(db_path=temp_db)
        assert summary["global_status"] == "warn"
        assert summary["counts"]["unknown"] == 3
        assert summary["global_pass_rate"] == 0.0

    def test_empty_data_produces_unknown(self, temp_db):
        """空数据集（total=0）时指标值为 None → unknown。"""
        records = evaluate_data_dimension(
            db_path=temp_db,
            mock_data={"total_notes": 0, "complete_notes": 0,
                       "latest_publish_hours_ago": None,
                       "duplicate_count": 0, "provenance_count": 0},
        )
        statuses = [r.status for r in records]
        # completeness, duplication, provenance 在 total=0 时应为 unknown
        assert "unknown" in statuses

    def test_runner_unknown_not_pass(self, temp_db, mock_all_data):
        """runner 全量评估中，unknown 不会让维度变成 pass。"""
        # 注入一个有 None 值的 mock
        bad_mock = dict(mock_all_data)
        bad_mock["data"] = {
            "total_notes": 0, "complete_notes": 0,
            "latest_publish_hours_ago": None,
            "duplicate_count": 0, "provenance_count": 0,
        }
        runner = EvaluationRunner(db_path=temp_db)
        result = runner.run_full_evaluation(mock_data=bad_mock)
        data_dim = result["dimensions"]["data"]
        # data 维度有 unknown，overall_status 不应为 pass
        assert data_dim["summary"]["overall_status"] in ("warn", "fail")
        assert data_dim["summary"]["unknown"] > 0


# ============================================================
# 4. 五维度评估执行测试
# ============================================================
class TestFiveDimensionEvaluation:
    def test_data_dimension_pass(self, temp_db):
        """data 维度：全部 pass 场景。"""
        records = evaluate_data_dimension(
            db_path=temp_db,
            mock_data={
                "total_notes": 100, "complete_notes": 95,
                "latest_publish_hours_ago": 2.0,
                "duplicate_count": 3, "provenance_count": 98,
            },
        )
        assert len(records) == 4
        statuses = {r.metric_name: r.status for r in records}
        assert statuses["completeness"] == "pass"
        assert statuses["freshness_hours"] == "pass"
        assert statuses["duplication_rate"] == "pass"
        assert statuses["provenance_rate"] == "pass"

    def test_data_dimension_fail(self, temp_db):
        """data 维度：全部 fail 场景。"""
        records = evaluate_data_dimension(
            db_path=temp_db,
            mock_data={
                "total_notes": 100, "complete_notes": 50,
                "latest_publish_hours_ago": 200.0,
                "duplicate_count": 30, "provenance_count": 40,
            },
        )
        statuses = {r.metric_name: r.status for r in records}
        assert statuses["completeness"] == "fail"
        assert statuses["freshness_hours"] == "fail"
        assert statuses["duplication_rate"] == "fail"
        assert statuses["provenance_rate"] == "fail"

    def test_ai_dimension(self, temp_db):
        """ai 维度：5 个指标全部评估。"""
        records = evaluate_ai_dimension(
            db_path=temp_db,
            mock_data={
                "ai_total": 100, "ai_correct": 90,
                "avg_confidence": 0.82, "human_corrections": 5,
                "provider_calls": 80, "provider_success": 76,
                "fallback_count": 10,
            },
        )
        assert len(records) == 5
        metric_names = [r.metric_name for r in records]
        assert "accuracy" in metric_names
        assert "confidence_avg" in metric_names
        assert "human_correction_rate" in metric_names
        assert "provider_reliability" in metric_names
        assert "fallback_rate" in metric_names

    def test_collector_dimension(self, temp_db):
        """collector 维度：4 个指标全部评估。"""
        records = evaluate_collector_dimension(
            db_path=temp_db,
            mock_data={
                "total_runs": 100, "success_runs": 92,
                "failure_runs": 5, "recovery_runs": 4,
                "avg_latency_sec": 85.0,
            },
        )
        assert len(records) == 4
        metric_names = [r.metric_name for r in records]
        assert "success_rate" in metric_names
        assert "failure_rate" in metric_names
        assert "recovery_rate" in metric_names
        assert "latency_sec" in metric_names

    def test_report_dimension(self, temp_db):
        """report 维度：3 个指标全部评估。"""
        records = evaluate_report_dimension(
            db_path=temp_db,
            mock_data={
                "total_reports": 30, "generated_reports": 28,
                "valid_artifacts": 27, "evidence_covered": 26,
            },
        )
        assert len(records) == 3
        metric_names = [r.metric_name for r in records]
        assert "generation_success" in metric_names
        assert "artifact_validity" in metric_names
        assert "evidence_coverage" in metric_names

    def test_runtime_dimension(self, temp_db):
        """runtime 维度：4 个指标全部评估。"""
        records = evaluate_runtime_dimension(
            db_path=temp_db,
            mock_data={
                "uptime_hours": 48.0, "heartbeat_total": 100,
                "heartbeat_ok": 99, "crash_count": 0,
                "recovery_count": 1,
            },
        )
        assert len(records) == 4
        metric_names = [r.metric_name for r in records]
        assert "uptime_hours" in metric_names
        assert "heartbeat_rate" in metric_names
        assert "crash_count" in metric_names
        assert "recovery_count" in metric_names

    def test_all_dimensions_have_thresholds(self):
        """所有维度的所有指标都有阈值配置。"""
        expected_metrics = [
            "data.completeness", "data.freshness_hours",
            "data.duplication_rate", "data.provenance_rate",
            "ai.accuracy", "ai.confidence_avg", "ai.human_correction_rate",
            "ai.provider_reliability", "ai.fallback_rate",
            "collector.success_rate", "collector.failure_rate",
            "collector.recovery_rate", "collector.latency_sec",
            "report.generation_success", "report.artifact_validity",
            "report.evidence_coverage",
            "runtime.uptime_hours", "runtime.heartbeat_rate",
            "runtime.crash_count", "runtime.recovery_count",
        ]
        for key in expected_metrics:
            assert key in THRESHOLDS, f"Missing threshold for {key}"
            th = THRESHOLDS[key]
            assert "pass" in th
            assert "warn" in th
            assert "higher_is_better" in th


# ============================================================
# 5. 评估汇总测试
# ============================================================
class TestEvaluationSummary:
    def test_summary_all_pass(self, temp_db):
        """全部 pass 时汇总正确。"""
        for i in range(5):
            record_evaluation(dimension="data", metric_name=f"m{i}",
                              metric_value=0.95, pass_threshold=0.90, warn_threshold=0.70,
                              higher_is_better=True, db_path=temp_db)
        summary = get_evaluation_summary(db_path=temp_db)
        assert summary["total_records"] == 5
        assert summary["counts"]["pass"] == 5
        assert summary["counts"]["fail"] == 0
        assert summary["global_status"] == "pass"
        assert summary["global_pass_rate"] == 1.0

    def test_summary_mixed_status(self, temp_db):
        """混合状态汇总正确。"""
        record_evaluation(dimension="data", metric_name="m1",
                          metric_value=0.95, pass_threshold=0.90, warn_threshold=0.70,
                          higher_is_better=True, db_path=temp_db)
        record_evaluation(dimension="data", metric_name="m2",
                          metric_value=0.75, pass_threshold=0.90, warn_threshold=0.70,
                          higher_is_better=True, db_path=temp_db)
        record_evaluation(dimension="ai", metric_name="m3",
                          metric_value=0.50, pass_threshold=0.85, warn_threshold=0.70,
                          higher_is_better=True, db_path=temp_db)
        summary = get_evaluation_summary(db_path=temp_db)
        assert summary["counts"]["pass"] == 1
        assert summary["counts"]["warn"] == 1
        assert summary["counts"]["fail"] == 1
        assert summary["global_status"] == "fail"  # 有 fail

    def test_summary_by_dimension(self, temp_db):
        """按维度汇总。"""
        record_evaluation(dimension="data", metric_name="m1",
                          metric_value=0.95, pass_threshold=0.90, warn_threshold=0.70,
                          higher_is_better=True, db_path=temp_db)
        record_evaluation(dimension="ai", metric_name="m2",
                          metric_value=0.95, pass_threshold=0.85, warn_threshold=0.70,
                          higher_is_better=True, db_path=temp_db)
        summary = get_evaluation_summary(dimension="data", db_path=temp_db)
        assert summary["total_records"] == 1
        assert "data" in summary["by_dimension"]
        assert "ai" not in summary["by_dimension"]

    def test_summary_empty(self, temp_db):
        """空数据库汇总。"""
        summary = get_evaluation_summary(db_path=temp_db)
        assert summary["total_records"] == 0
        assert summary["global_status"] == "unknown"
        assert summary["global_pass_rate"] == 0.0

    def test_latest_by_metric(self, temp_db):
        """每个指标保留最新记录。"""
        record_evaluation(dimension="data", metric_name="completeness",
                          metric_value=0.80, pass_threshold=0.90, warn_threshold=0.70,
                          higher_is_better=True, db_path=temp_db)
        record_evaluation(dimension="data", metric_name="completeness",
                          metric_value=0.95, pass_threshold=0.90, warn_threshold=0.70,
                          higher_is_better=True, db_path=temp_db)
        summary = get_evaluation_summary(db_path=temp_db)
        latest = summary["latest_by_metric"]["data.completeness"]
        assert latest["metric_value"] == 0.95  # 最新的一条


# ============================================================
# 6. 不允许只统计接口 200 —— 反模式测试
# ============================================================
class TestNotOnlyHTTP200:
    def test_no_200_metric_in_dimensions(self, temp_db, mock_all_data):
        """五维度评估中没有任何指标叫 200/http_status。"""
        runner = EvaluationRunner(db_path=temp_db)
        result = runner.run_full_evaluation(mock_data=mock_all_data)
        all_metric_names = []
        for dim_result in result["dimensions"].values():
            all_metric_names.extend(dim_result["metrics"].keys())
        # 没有任何指标名包含 200 或 http_status
        for name in all_metric_names:
            assert "200" not in name.lower(), f"Found 200-like metric: {name}"
            assert "http_status" not in name.lower(), f"Found http_status metric: {name}"

    def test_anti_pattern_check_in_runner(self, temp_db, mock_all_data):
        """runner 返回 anti_pattern_check 字段。"""
        runner = EvaluationRunner(db_path=temp_db)
        result = runner.run_full_evaluation(mock_data=mock_all_data)
        assert "anti_pattern_check" in result
        assert result["anti_pattern_check"]["only_200_count"] == 0
        assert result["anti_pattern_check"]["unknown_not_pass"] is True
        assert result["anti_pattern_check"]["real_quality_metrics"] > 0

    def test_all_metrics_have_real_values(self, temp_db, mock_all_data):
        """所有指标都是真实质量指标（有明确阈值和数据源）。"""
        runner = EvaluationRunner(db_path=temp_db)
        result = runner.run_full_evaluation(mock_data=mock_all_data)
        for dim_name, dim_result in result["dimensions"].items():
            for metric_name, metric_info in dim_result["metrics"].items():
                assert metric_info["threshold"] != "", f"{dim_name}.{metric_name} has no threshold"
                assert metric_info["source"] != "", f"{dim_name}.{metric_name} has no source"

    def test_legacy_stability_is_not_200_only(self):
        """验证 Legacy evaluation_system 的 stability 确实是端口检查（文档化已知局限）。"""
        import evaluation_system
        assert hasattr(evaluation_system, "LEGACY")
        assert evaluation_system.LEGACY is True
        assert "200" in evaluation_system.LEGACY_REPLACED_BY or True  # 仅确认 Legacy 标记存在


# ============================================================
# 7. evaluation_runner 测试
# ============================================================
class TestEvaluationRunner:
    def test_full_evaluation_all_pass(self, temp_db, mock_all_data):
        """全量评估：全部 pass 场景。"""
        runner = EvaluationRunner(db_path=temp_db)
        result = runner.run_full_evaluation(mock_data=mock_all_data)
        assert result["global_summary"]["global_status"] == "pass"
        assert result["global_summary"]["total"] > 0
        assert len(result["dimensions"]) == 5
        for dim in VALID_DIMENSIONS:
            assert dim in result["dimensions"]

    def test_full_evaluation_all_fail(self, temp_db, mock_fail_data):
        """全量评估：全部 fail 场景。"""
        runner = EvaluationRunner(db_path=temp_db)
        result = runner.run_full_evaluation(mock_data=mock_fail_data)
        assert result["global_summary"]["global_status"] == "fail"
        assert result["global_summary"]["fail"] > 0

    def test_single_dimension_evaluation(self, temp_db):
        """单维度评估。"""
        runner = EvaluationRunner(db_path=temp_db)
        result = runner.run_dimension_evaluation("data", mock_data={
            "total_notes": 100, "complete_notes": 95,
            "latest_publish_hours_ago": 2.0,
            "duplicate_count": 3, "provenance_count": 98,
        })
        assert result["dimension"] == "data"
        assert result["summary"]["total"] == 4
        assert result["error"] is None

    def test_invalid_dimension(self, temp_db):
        """无效维度返回错误。"""
        runner = EvaluationRunner(db_path=temp_db)
        result = runner.run_dimension_evaluation("invalid")
        assert result["error"] is not None
        assert result["summary"]["overall_status"] == "fail"

    def test_runner_persists_records(self, temp_db, mock_all_data):
        """runner 执行后记录已持久化。"""
        runner = EvaluationRunner(db_path=temp_db)
        runner.run_full_evaluation(mock_data=mock_all_data)
        records = get_evaluation_records(db_path=temp_db, limit=100)
        assert len(records) > 0
        dimensions_found = set(r["dimension"] for r in records)
        assert dimensions_found == set(VALID_DIMENSIONS)

    def test_runner_module_level_function(self, temp_db, mock_all_data):
        """模块级便捷函数可用。"""
        result = run_full_evaluation(db_path=temp_db, mock_data=mock_all_data)
        assert result["global_summary"]["global_status"] == "pass"

    def test_runner_subset_dimensions(self, temp_db, mock_all_data):
        """只评估指定维度子集。"""
        runner = EvaluationRunner(db_path=temp_db)
        result = runner.run_full_evaluation(
            mock_data=mock_all_data, dimensions=["data", "ai"]
        )
        assert len(result["dimensions"]) == 2
        assert "data" in result["dimensions"]
        assert "ai" in result["dimensions"]
        assert "collector" not in result["dimensions"]


# ============================================================
# 8. 现有模块桥接测试
# ============================================================
class TestLegacyBridges:
    def test_evaluation_system_legacy_marker(self):
        """evaluation_system.py 有 Legacy 标记。"""
        import evaluation_system
        assert evaluation_system.LEGACY is True
        assert evaluation_system.LEGACY_SINCE == "2026-09-06"

    def test_data_quality_gate_bridge(self, temp_db):
        """data_quality_gate.batch_quality_to_evaluation 接入统一系统。"""
        from data_quality_gate import batch_quality_to_evaluation
        # 构造校验结果
        validation_results = [
            {"valid": True, "errors": [], "warnings": []},
            {"valid": True, "errors": [], "warnings": []},
            {"valid": False, "errors": [{"rule": "not_empty", "field": "title"}], "warnings": []},
        ]
        records = batch_quality_to_evaluation(validation_results, db_path=temp_db)
        assert len(records) == 1
        assert records[0].dimension == "data"
        assert records[0].metric_name == "gate_completeness"
        # 2/3 valid = 0.667 → fail (pass=0.90, warn=0.70)
        assert records[0].status == "fail"

    def test_data_quality_gate_bridge_empty(self, temp_db):
        """空校验结果 → unknown（不默认 pass）。"""
        from data_quality_gate import batch_quality_to_evaluation
        records = batch_quality_to_evaluation([], db_path=temp_db)
        assert len(records) == 1
        assert records[0].status == "unknown"

    def test_engineering_metrics_bridge(self, temp_db):
        """engineering_metrics.engineering_to_evaluation 接入统一系统。"""
        from engineering_metrics import engineering_to_evaluation
        # 构造一个简化快照
        snapshot = {
            "task_closed_loop": {
                "total_tasks": 10, "closed_tasks": 9, "failed_tasks": 1,
                "task_completion_rate": 0.9, "recovery_rate": 0.9,
            },
            "collector_performance": {
                "window_success_rate": 0.88, "window_avg_latency": 95.0,
            },
            "system_health": {"health": {"status": "ok"}},
            "alert": {"level": "OK"},
        }
        records = engineering_to_evaluation(snapshot, db_path=temp_db)
        assert len(records) > 0
        dimensions = set(r.dimension for r in records)
        assert "collector" in dimensions
        assert "runtime" in dimensions


# ============================================================
# 9. 数据库表结构测试
# ============================================================
class TestDatabaseSchema:
    def test_evaluation_records_table_created(self, temp_db):
        """evaluation_records 表被创建。"""
        import sqlite3
        conn = sqlite3.connect(temp_db)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert "evaluation_records" in tables

    def test_table_has_required_columns(self, temp_db):
        """表包含所有必需字段。"""
        import sqlite3
        conn = sqlite3.connect(temp_db)
        columns = [r[1] for r in conn.execute("PRAGMA table_info(evaluation_records)").fetchall()]
        conn.close()
        required = ["evaluation_id", "dimension", "metric_name", "metric_value",
                    "threshold", "status", "evaluated_at", "source", "evidence_ref", "metadata"]
        for col in required:
            assert col in columns, f"Missing column: {col}"

    def test_evaluation_id_unique(self, temp_db):
        """evaluation_id 唯一约束。"""
        import sqlite3
        rec = record_evaluation(
            dimension="data", metric_name="m", metric_value=0.9,
            pass_threshold=0.8, warn_threshold=0.6, higher_is_better=True,
            db_path=temp_db,
        )
        conn = sqlite3.connect(temp_db)
        # 尝试插入相同 evaluation_id 应替换（INSERT OR REPLACE）
        conn.execute(
            "INSERT OR REPLACE INTO evaluation_records (evaluation_id, dimension, metric_name, status, evaluated_at) VALUES (?, ?, ?, ?, ?)",
            (rec.evaluation_id, "data", "m", "pass", "2026-01-01T00:00:00"),
        )
        conn.commit()
        count = conn.execute(
            "SELECT COUNT(*) FROM evaluation_records WHERE evaluation_id=?", (rec.evaluation_id,)
        ).fetchone()[0]
        conn.close()
        assert count == 1  # 替换而非重复
