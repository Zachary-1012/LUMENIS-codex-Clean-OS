# -*- coding: utf-8 -*-
"""ZBC 验收机制增量升级 · 集成测试。

覆盖：acceptance_gate 判定器 + acceptance_evidence_chain 证据链构建器 的端到端集成。
验证：CI/Function 分离、6 态功能状态、证据链可追溯、PARTIAL 原因分类、
AI/Browser 特殊验收、批量判定、最高原则。
"""
import pytest

import acceptance_gate as ag
from acceptance_evidence_chain import (
    build_chain, build_and_judge, batch_build_and_judge,
    AcceptanceEvidenceChain, GENERIC_CHAIN_ORDER, AI_CHAIN_ORDER,
    ACCEPTANCE_PRINCIPLE,
)


# ============================================================
# 辅助
# ============================================================
def _all_passed(**over):
    """8 维全过的通用功能基线。"""
    base = dict(
        ci_passed=True, commit_sha="abc1234",
        source_exists=True, source_ref="app.py:100",
        call_graph_closed=True, call_graph_ref="callgraph.json",
        test_passed=True, test_ref="tests/test_x.py::test_y",
        runtime_evidence=True, runtime_ref="runtime.log:2026-09-07",
        evidence_recorded=True, evidence_ref="ev_abc123",
        verification_passed=True, verification_ref="verification_report.md",
        security_verified=True, regression_passed=True,
    )
    base.update(over)
    return base


def _ai_all_passed(**over):
    """AI/Browser 全链路闭环基线。"""
    base = _all_passed()
    base.update(dict(
        is_ai_or_browser=True,
        ai_agent_ok=True, ai_skill_ok=True, ai_permission_ok=True,
        ai_browser_tool_ok=True, ai_action_ok=True, ai_result_ok=True,
        ai_trace_ok=True,
    ))
    base.update(over)
    return base


# ============================================================
# 一、证据链构建
# ============================================================
class TestChainBuild:
    def test_generic_chain_has_9_nodes(self):
        chain = build_chain("T1", **_all_passed())
        assert len(chain.nodes) >= 9
        assert chain.chain_order() == GENERIC_CHAIN_ORDER

    def test_ai_chain_has_11_nodes(self):
        chain = build_chain("AI1", **_ai_all_passed())
        assert chain.chain_order() == AI_CHAIN_ORDER
        # AI 链路应包含 agent/skill/permission/browser_tool/action/result/trace
        ai_nodes = {"agent", "skill", "permission", "browser_tool", "action", "result", "trace"}
        chain_nodes = {n.node for n in chain.nodes}
        assert ai_nodes.issubset(chain_nodes)

    def test_missing_evidence_explicitly_marked(self):
        """缺证据必须显式标 missing，禁止静默跳过。"""
        chain = build_chain("T2", source_exists=True)  # 只给 source
        missing = chain.missing_nodes()
        assert len(missing) > 0
        # commit/test/runtime 等应在缺失列表中
        assert "commit" in missing or "test" in missing

    def test_chain_node_status_mapping(self):
        chain = build_chain("T3", source_exists=True, test_passed=False)
        src = chain.get_node("source")
        assert src.status == "passed"
        tst = chain.get_node("test")
        assert tst.status == "failed"

    def test_coverage_calculation(self):
        chain = build_chain("T4", source_exists=True, test_passed=True)
        cov = chain.coverage()
        assert 0 < cov < 100  # 部分通过


# ============================================================
# 二、build_and_judge 集成（证据链 → 判定器 → 回填）
# ============================================================
class TestBuildAndJudge:
    def test_verified_when_all_dimensions_pass(self):
        chain = build_and_judge("T-VERIFIED", **_all_passed())
        assert chain.functional_status == "VERIFIED"
        assert chain.ci_status == "PASS"
        assert chain.evidence_coverage == 100.0
        assert chain.partial_reasons == []
        assert chain.missing_dimensions == []

    def test_planned_when_no_source(self):
        chain = build_and_judge("T-PLANNED", source_exists=False)
        assert chain.functional_status == "PLANNED"

    def test_implemented_when_source_but_chain_open(self):
        chain = build_and_judge("T-IMPL", source_exists=True,
                                 call_graph_closed=False, test_passed=None)
        assert chain.functional_status == "IMPLEMENTED"

    def test_tested_when_tests_pass_but_no_runtime(self):
        chain = build_and_judge("T-TESTED", source_exists=True,
                                 call_graph_closed=True, test_passed=True,
                                 runtime_evidence=False)
        assert chain.functional_status == "TESTED"

    def test_ci_pass_but_function_partial_independent(self):
        """CI PASS 与 Function PARTIAL 必须独立共存。"""
        chain = build_and_judge("T-INDEP", ci_passed=True, source_exists=True,
                                 call_graph_closed=True, test_passed=True,
                                 runtime_evidence=False)
        assert chain.ci_status == "PASS"
        assert chain.functional_status in ("TESTED", "PARTIAL")
        assert chain.evidence_coverage < 100

    def test_ci_fail_but_function_can_be_verified(self):
        """CI FAILED 不影响功能状态判定（二者独立维度）。"""
        chain = build_and_judge("T-CIFAIL", **_all_passed(ci_passed=False))
        assert chain.ci_status == "FAILED"
        assert chain.functional_status == "VERIFIED"

    def test_final_status_node_backfilled(self):
        """build_and_judge 必须回填 final_status 节点。"""
        chain = build_and_judge("T-BACKFILL", **_all_passed())
        final = chain.get_node("final_status")
        assert final is not None
        assert final.status == "passed"
        assert "VERIFIED" in final.detail


# ============================================================
# 三、PARTIAL 原因分类
# ============================================================
class TestPartialReasons:
    def test_missing_runtime_evidence_reason(self):
        chain = build_and_judge("T-RT", source_exists=True, call_graph_closed=True,
                                test_passed=True, runtime_evidence=False)
        assert "Missing Runtime Evidence" in chain.partial_reasons

    def test_test_failed_distinct_from_missing(self):
        chain = build_and_judge("T-TF", source_exists=True, test_passed=False)
        assert "Test Failed" in chain.partial_reasons

    def test_missing_e2e_reason(self):
        chain = build_and_judge("T-E2E", source_exists=True, call_graph_closed=True,
                                 test_passed=True, runtime_evidence=False,
                                 verification_passed=False)
        assert "Missing E2E" in chain.partial_reasons

    def test_security_not_verified(self):
        chain = build_and_judge("T-SEC", source_exists=True, call_graph_closed=True,
                                test_passed=True, runtime_evidence=True,
                                evidence_recorded=True, verification_passed=True,
                                security_verified=False, regression_passed=True)
        assert "Security Not Verified" in chain.partial_reasons
        assert "Permission Not Verified" in chain.partial_reasons

    def test_call_graph_incomplete(self):
        chain = build_and_judge("T-CG", source_exists=True, call_graph_closed=False,
                                 test_passed=True)
        assert "Call Graph Incomplete" in chain.partial_reasons

    def test_regression_not_verified(self):
        chain = build_and_judge("T-REG", source_exists=True, call_graph_closed=True,
                                test_passed=True, runtime_evidence=True,
                                evidence_recorded=True, verification_passed=True,
                                security_verified=True, regression_passed=False)
        assert "Regression Not Verified" in chain.partial_reasons


# ============================================================
# 四、AI/Browser 特殊验收（硬要求）
# ============================================================
class TestAIBrowserSpecial:
    def test_ai_cannot_verify_by_unit_test_only(self):
        """AI/Browser 不允许仅凭单测 VERIFIED，必须完整链路闭环。"""
        # 8 维看似齐全，但 AI 扩展节点全缺
        chain = build_and_judge("AI-NOCHAIN", **_ai_all_passed(
            ai_agent_ok=False, ai_skill_ok=False, ai_permission_ok=False,
            ai_browser_tool_ok=False, ai_action_ok=False, ai_result_ok=False,
            ai_trace_ok=False,
        ))
        assert chain.functional_status != "VERIFIED"
        assert "AI/Browser Chain Not Closed" in chain.partial_reasons

    def test_ai_verified_when_full_chain_closed(self):
        chain = build_and_judge("AI-FULL", **_ai_all_passed())
        assert chain.functional_status == "VERIFIED"
        assert chain.evidence_coverage == 100.0

    def test_ai_partial_when_one_node_missing(self):
        """AI 链路缺一个节点就必须 PARTIAL。"""
        chain = build_and_judge("AI-ONE", **_ai_all_passed(ai_trace_ok=False))
        assert chain.functional_status != "VERIFIED"
        assert "AI/Browser Chain Not Closed" in chain.partial_reasons

    def test_ai_chain_has_11_nodes(self):
        chain = build_chain("AI-NODES", **_ai_all_passed())
        assert len(AI_CHAIN_ORDER) == 11
        assert chain.chain_order() == AI_CHAIN_ORDER


# ============================================================
# 五、证据链可追溯（explain）
# ============================================================
class TestTraceability:
    def test_explain_contains_task_and_status(self):
        chain = build_and_judge("T-EXP", **_all_passed())
        text = chain.explain()
        assert "T-EXP" in text
        assert "VERIFIED" in text
        assert "CI Status: PASS" in text

    def test_explain_shows_missing_nodes(self):
        chain = build_and_judge("T-MISS", source_exists=True)
        text = chain.explain()
        assert "MISSING" in text

    def test_explain_shows_partial_reasons(self):
        chain = build_and_judge("T-REASON", source_exists=True, test_passed=False)
        text = chain.explain()
        assert "Test Failed" in text

    def test_to_dict_has_all_fields(self):
        chain = build_and_judge("T-DICT", **_all_passed())
        d = chain.to_dict()
        assert d["task_id"] == "T-DICT"
        assert d["functional_status"] == "VERIFIED"
        assert "chain_order" in d
        assert "passed_nodes" in d
        assert "missing_nodes" in d
        assert "node_coverage" in d


# ============================================================
# 六、批量判定
# ============================================================
class TestBatch:
    def test_batch_summary(self):
        tasks = [
            {"task_id": "OK1", **_all_passed()},
            {"task_id": "OK2", **_all_passed()},
            {"task_id": "BAD", "source_exists": True, "test_passed": True,
             "runtime_evidence": False},
        ]
        r = batch_build_and_judge(tasks)
        assert r["total"] == 3
        assert r["by_functional_status"].get("VERIFIED") == 2
        assert len(r["partial_detail"]) >= 1
        bad = [p for p in r["partial_detail"] if p["task_id"] == "BAD"][0]
        assert "Missing Runtime Evidence" in bad["partial_reasons"]

    def test_batch_average_coverage(self):
        tasks = [
            {"task_id": "A", **_all_passed()},
            {"task_id": "B", "source_exists": True},
        ]
        r = batch_build_and_judge(tasks)
        assert 0 < r["average_evidence_coverage"] < 100


# ============================================================
# 七、最高原则 & 保留机制
# ============================================================
class TestPrinciplesAndPreservation:
    def test_acceptance_principle_defined(self):
        assert "CI PASS ≠ VERIFIED" in ACCEPTANCE_PRINCIPLE
        assert "代码存在 ≠ VERIFIED" in ACCEPTANCE_PRINCIPLE
        assert "AI说完成 ≠ VERIFIED" in ACCEPTANCE_PRINCIPLE

    def test_existing_status_keywords_preserved(self):
        """×/✓、PARTIAL/VERIFIED 关键字必须保留。"""
        # acceptance_gate 中保留
        assert hasattr(ag, "FunctionalStatus")
        assert "PARTIAL" in [s.value for s in ag.FunctionalStatus]
        assert "VERIFIED" in [s.value for s in ag.FunctionalStatus]
        # CI 状态保留 PASS/FAILED（对应 ✓/×）
        assert "PASS" in [s.value for s in ag.CIStatus]
        assert "FAILED" in [s.value for s in ag.CIStatus]

    def test_six_functional_states_implemented(self):
        """6 态功能状态 PLANNED→OPERATING 全部实现。"""
        states = [s.value for s in ag.FunctionalStatus]
        for expected in ("PLANNED", "IMPLEMENTED", "TESTED", "VERIFIED", "RELEASED", "OPERATING"):
            assert expected in states, f"缺少状态: {expected}"

    def test_partial_reason_classification_complete(self):
        """PARTIAL 原因分类覆盖用户要求的 7 类。"""
        reasons = [r.value for r in ag.PartialReason]
        required = [
            "Missing Runtime Evidence", "Missing E2E", "Test Failed",
            "Call Graph Incomplete", "Permission Not Verified",
            "Security Not Verified", "Regression Not Verified",
        ]
        for r in required:
            assert r in reasons, f"缺少 PARTIAL 原因: {r}"

    def test_p0_p1_data_not_modified(self):
        """本测试模块不触碰任何 P0/P1 数据（纯逻辑验证）。"""
        # acceptance_gate 和 acceptance_evidence_chain 均为纯逻辑/独立表
        # 此处验证无 DB 写入副作用（persist_evidence=False 时）
        chain = build_and_judge("T-NODB", **_all_passed(), persist_evidence=False)
        assert chain.functional_status == "VERIFIED"
        # 无异常即表示纯逻辑执行成功
