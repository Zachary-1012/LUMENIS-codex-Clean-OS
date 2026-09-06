# -*- coding: utf-8 -*-
"""验收判定器状态分层测试：CI Status 与 Functional Status 必须独立。"""
import pytest

from acceptance_gate import (
    AcceptanceInput, judge, judge_batch, FunctionalStatus, CIStatus,
    PartialReason, REQUIRED_DIMENSIONS,
)


def _all_true(**over):
    """8 维全成立的 VERIFIED 基线输入。"""
    base = dict(
        task_id="T", ci_passed=True, commit_sha="abc1234",
        source_exists=True, call_graph_closed=True, runtime_evidence=True,
        test_passed=True, evidence_recorded=True, verification_passed=True,
        security_verified=True, regression_passed=True,
    )
    base.update(over)
    return AcceptanceInput(**base)


class TestStatusLayering:
    def test_ci_pass_but_function_partial_are_independent(self):
        # CI PASS 但缺运行证据 → Function=TESTED/PARTIAL，证明两者独立
        inp = AcceptanceInput(
            task_id="ci-only", ci_passed=True, source_exists=True,
            call_graph_closed=True, test_passed=True,
            runtime_evidence=False, evidence_recorded=False,
            verification_passed=False, security_verified=False, regression_passed=False,
        )
        v = judge(inp)
        assert v.ci_status == CIStatus.PASS.value
        assert v.functional_status in (FunctionalStatus.TESTED.value, FunctionalStatus.PARTIAL.value)
        assert v.evidence_coverage < 100
        assert PartialReason.MISSING_RUNTIME_EVIDENCE.value in v.partial_reasons

    def test_ci_fail_can_still_have_functional_evidence(self):
        # CI 失败是独立维度（这里功能维度也不全，但 ci_status 必须独立显示 FAILED）
        inp = _all_true(ci_passed=False)
        v = judge(inp)
        assert v.ci_status == CIStatus.FAILED.value
        assert v.functional_status == FunctionalStatus.VERIFIED.value  # 功能证据齐全

    def test_planned_when_no_source(self):
        inp = AcceptanceInput(task_id="p", source_exists=False)
        v = judge(inp)
        assert v.functional_status == FunctionalStatus.PLANNED.value
        assert PartialReason.MISSING_SOURCE.value in v.partial_reasons

    def test_implemented_when_source_but_chain_open(self):
        inp = AcceptanceInput(task_id="i", source_exists=True,
                              call_graph_closed=False, test_passed=None)
        v = judge(inp)
        assert v.functional_status == FunctionalStatus.IMPLEMENTED.value
        assert PartialReason.CALL_GRAPH_INCOMPLETE.value in v.partial_reasons

    def test_tested_when_tests_pass_but_no_runtime(self):
        inp = AcceptanceInput(task_id="t", source_exists=True, call_graph_closed=True,
                              test_passed=True, runtime_evidence=False)
        v = judge(inp)
        assert v.functional_status == FunctionalStatus.TESTED.value

    def test_verified_requires_all_eight_dimensions(self):
        v = judge(_all_true(task_id="v"))
        assert v.functional_status == FunctionalStatus.VERIFIED.value
        assert v.evidence_coverage == 100.0
        assert v.missing_dimensions == []
        assert v.partial_reasons == []

    @pytest.mark.parametrize("dim", REQUIRED_DIMENSIONS)
    def test_any_missing_dimension_blocks_verified(self, dim):
        # 维度名 → AcceptanceInput 字段名
        field_map = {
            "source": "source_exists", "call_graph": "call_graph_closed",
            "runtime": "runtime_evidence", "test": "test_passed",
            "evidence": "evidence_recorded", "verification": "verification_passed",
            "security": "security_verified", "regression": "regression_passed",
        }
        kwargs = {
            "source_exists": True, "call_graph_closed": True, "runtime_evidence": True,
            "test_passed": True, "evidence_recorded": True, "verification_passed": True,
            "security_verified": True, "regression_passed": True,
        }
        kwargs[field_map[dim]] = False
        v = judge(AcceptanceInput(task_id="m", ci_passed=True, **kwargs))
        assert v.functional_status != FunctionalStatus.VERIFIED.value
        assert v.evidence_coverage < 100.0

    def test_released_then_operating(self):
        rel = judge(_all_true(task_id="r", is_released=True))
        assert rel.functional_status == FunctionalStatus.RELEASED.value
        op = judge(_all_true(task_id="o", is_released=True, has_continuous_runtime=True))
        assert op.functional_status == FunctionalStatus.OPERATING.value


class TestAIBrowserSpecial:
    def test_ai_browser_cannot_verify_by_unit_test_only(self):
        # 8 维看似齐全，但 AI 链路未闭环 → 不得 VERIFIED
        inp = _all_true(task_id="ai", is_ai_or_browser=True, ai_chain_closed=False)
        v = judge(inp)
        assert v.functional_status != FunctionalStatus.VERIFIED.value
        assert PartialReason.AI_CHAIN_NOT_CLOSED.value in v.partial_reasons

    def test_ai_browser_verified_when_chain_closed(self):
        inp = _all_true(task_id="ai2", is_ai_or_browser=True, ai_chain_closed=True)
        v = judge(inp)
        assert v.functional_status == FunctionalStatus.VERIFIED.value


class TestBatch:
    def test_batch_summary_and_partial_reasons(self):
        items = [
            _all_true(task_id="ok1"),
            _all_true(task_id="ok2"),
            AcceptanceInput(task_id="bad", source_exists=True, test_passed=True,
                            runtime_evidence=False),
        ]
        r = judge_batch(items)
        assert r["total"] == 3
        assert r["by_functional_status"].get(FunctionalStatus.VERIFIED.value) == 2
        partial = [p for p in r["partial_detail"] if p["task_id"] == "bad"][0]
        assert PartialReason.MISSING_RUNTIME_EVIDENCE.value in partial["reasons"]
        assert "ci_status" in partial and "evidence_coverage" in partial

    def test_test_failed_distinct_from_missing(self):
        inp = AcceptanceInput(task_id="tf", source_exists=True, test_passed=False)
        v = judge(inp)
        assert PartialReason.TEST_FAILED.value in v.partial_reasons
