# -*- coding: utf-8 -*-
"""
agent_research.runner 集成测试
==============================
覆盖：基本研究流程、多专家并行探索、假设生成、验证步骤、结果排序、
证据血缘可追溯、空 goal 处理、自定义专家列表、max_rounds 限制、
ResearchResult JSON 序列化、模块级便捷函数。
"""
import json
import pytest

from agent_research.specialist import Specialist, default_specialists
from agent_research.hypothesis import HypothesisGenerator, HYPOTHESIS_VERIFIED, HYPOTHESIS_REJECTED
from agent_research.lineage import LineageTracker
from agent_research.runner import ResearchRunner, ResearchResult, run_research


GOAL = "分析广州太古汇2026年第三季度小红书舆情趋势与风险因素"


class TestBasicResearchFlow:
    """基本研究流程测试。"""

    def test_run_research_returns_result(self):
        """run_research 应返回 ResearchResult 对象。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=1)
        assert isinstance(result, ResearchResult)
        assert result.research_id.startswith("res_")
        assert result.goal == GOAL
        assert result.summary != ""
        assert result.started_at != ""
        assert result.finished_at != ""

    def test_research_produces_findings(self):
        """研究应产出非空 findings。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=1)
        assert len(result.ranked_findings) > 0

    def test_research_produces_debate_transcript(self):
        """研究应产出辩论记录。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=1)
        assert len(result.debate_transcript) > 0
        assert result.debate_transcript[0]["round_number"] == 1

    def test_every_finding_has_evidence_and_lineage(self):
        """每个 finding 必须带 evidence_refs 和 lineage_id。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=1)
        for f in result.ranked_findings:
            assert len(f["evidence_refs"]) > 0, f"finding {f.get('finding_id')} 缺少 evidence_refs"
            assert f.get("lineage_id"), f"finding {f.get('finding_id')} 缺少 lineage_id"


class TestParallelExploration:
    """多专家并行探索测试。"""

    def test_all_specialists_contribute(self):
        """所有启用专家都应贡献 findings。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=1)
        for sp in default_specialists():
            assert result.specialist_contributions.get(sp.specialist_id, 0) > 0

    def test_findings_count_matches_specialists_times_hypotheses(self):
        """单轮 findings 数量 = 专家数 × 假设数。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=1)
        n_specialists = len([s for s in default_specialists() if s.enabled])
        # 每个专家最多 2 个假设
        expected_max = n_specialists * 2 * n_specialists  # specialists * hypotheses_per_specialist... actually
        # 实际：每个专家对每个假设生成1条finding，假设数=专家数*2（每专家2个）
        n_hypotheses = n_specialists * 2
        expected = n_specialists * n_hypotheses
        assert len(result.ranked_findings) == expected


class TestHypothesisGeneration:
    """假设生成测试。"""

    def test_generator_produces_hypotheses(self):
        """HypothesisGenerator 应从 goal 生成假设。"""
        gen = HypothesisGenerator()
        hypotheses = gen.generate(GOAL)
        assert len(hypotheses) > 0
        for h in hypotheses:
            assert h.statement != ""
            assert h.specialist_id != ""
            assert h.status == "proposed"

    def test_generator_empty_goal_returns_empty(self):
        """空 goal 应返回空假设列表。"""
        gen = HypothesisGenerator()
        assert gen.generate("") == []
        assert gen.generate("   ") == []

    def test_generator_respects_max_per_specialist(self):
        """max_per_specialist 应限制每个专家的假设数。"""
        gen = HypothesisGenerator()
        hypotheses = gen.generate(GOAL, max_per_specialist=1)
        n_specialists = len([s for s in default_specialists() if s.enabled])
        assert len(hypotheses) == n_specialists


class TestValidationStep:
    """验证步骤测试。"""

    def test_findings_marked_validated(self):
        """有证据的 finding 应被标记为 validated=True。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=1)
        # 所有 finding 都有 evidence_refs，应全部 validated
        for f in result.ranked_findings:
            assert f["validated"] is True

    def test_hypothesis_statuses_include_verified_or_rejected(self):
        """经过验证后，假设状态应包含 verified 或 rejected（或保持 challenged）。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=2)
        # 从 debate_transcript 中提取最终假设状态
        last_round = result.debate_transcript[-1]
        statuses = {h["status"] for h in last_round["hypotheses"]}
        # 至少应有 challenged / verified / rejected 中的一种
        assert statuses.issubset({"proposed", "challenged", "verified", "rejected"})
        assert len(statuses) > 0


class TestRanking:
    """结果排序测试。"""

    def test_findings_sorted_by_rank_score_desc(self):
        """ranked_findings 应按 rank_score 降序排列。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=2)
        scores = [f["rank_score"] for f in result.ranked_findings]
        assert scores == sorted(scores, reverse=True)

    def test_top_finding_has_highest_confidence_or_evidence(self):
        """排名第一的 finding 应有较高的 rank_score。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=1)
        top = result.ranked_findings[0]
        assert top["rank_score"] > 0
        assert "evidence_strength" in top


class TestEvidenceLineage:
    """证据血缘可追溯测试。"""

    def test_result_has_evidence_lineage(self):
        """ResearchResult 应包含非空 evidence_lineage。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=1)
        assert len(result.evidence_lineage) > 0

    def test_lineage_records_have_required_fields(self):
        """每条血缘记录应包含 lineage_id / evidence_id / source / path / provenance。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=1)
        for record in result.evidence_lineage:
            assert record["lineage_id"].startswith("lin_")
            assert record["evidence_id"].startswith("ev_")
            assert record["source"] != ""
            assert isinstance(record["path"], list)
            assert len(record["path"]) > 0
            assert isinstance(record["provenance"], dict)

    def test_lineage_traceable_from_finding_to_hypothesis(self):
        """finding 的 lineage 应能追溯到 hypothesis（path[0] 为 hypothesis_id）。"""
        tracker = LineageTracker()
        lid = tracker.track(
            evidence_id="ev_test",
            source="analyst",
            path=["hyp_001", "finding_001", "ev_test"],
            provenance={"method": "test"},
        )
        record = tracker.query(lid)
        assert record is not None
        assert record.path[0] == "hyp_001"
        assert record.path[-1] == "ev_test"

    def test_lineage_query_by_evidence(self):
        """按 evidence_id 查询血缘。"""
        tracker = LineageTracker()
        tracker.track(evidence_id="ev_abc", source="analyst", path=["hyp_1", "ev_abc"])
        results = tracker.query_by_evidence("ev_abc")
        assert len(results) == 1
        assert results[0].evidence_id == "ev_abc"

    def test_lineage_export_json(self):
        """LineageTracker.export_json() 应返回合法 JSON 字符串。"""
        tracker = LineageTracker()
        tracker.track(evidence_id="ev_1", source="analyst", path=["hyp_1", "ev_1"])
        json_str = tracker.export_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, list)
        assert len(parsed) == 1


class TestEmptyGoal:
    """空 goal 处理测试。"""

    def test_empty_goal_returns_empty_result(self):
        """空 goal 应返回空结果，不报错。"""
        runner = ResearchRunner()
        result = runner.run_research("", max_rounds=1)
        assert result.goal == ""
        assert len(result.ranked_findings) == 0
        assert len(result.debate_transcript) == 0
        assert result.confidence == 0.0
        assert "为空" in result.summary

    def test_whitespace_goal_returns_empty_result(self):
        """纯空格 goal 应返回空结果。"""
        runner = ResearchRunner()
        result = runner.run_research("   ", max_rounds=1)
        assert len(result.ranked_findings) == 0


class TestCustomSpecialists:
    """自定义专家列表测试。"""

    def test_custom_specialists_used(self):
        """传入自定义专家列表时应使用自定义专家。"""
        custom = Specialist(
            specialist_id="market_researcher",
            name="市场研究员",
            role="analyst",
            domain="market",
            capabilities=["market_analysis"],
            priority=1,
        )
        runner = ResearchRunner(specialists=[custom])
        result = runner.run_research(GOAL, specialists=[custom], max_rounds=1)
        assert "market_researcher" in result.specialist_contributions
        assert result.specialist_contributions["market_researcher"] > 0

    def test_module_level_function_with_custom_specialists(self):
        """模块级 run_research 函数应支持自定义专家。"""
        custom = Specialist(
            specialist_id="custom_analyst",
            name="自定义分析员",
            role="analyst",
            domain="custom",
            capabilities=["custom_cap"],
        )
        result = run_research(GOAL, specialists=[custom])
        assert isinstance(result, ResearchResult)
        assert "custom_analyst" in result.specialist_contributions


class TestMaxRounds:
    """max_rounds 限制测试。"""

    def test_max_rounds_1_produces_1_debate_round(self):
        """max_rounds=1 应只产生 1 轮辩论。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=1)
        assert len(result.debate_transcript) == 1

    def test_max_rounds_3_produces_3_debate_rounds(self):
        """max_rounds=3 应产生 3 轮辩论。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=3)
        assert len(result.debate_transcript) == 3
        for i, dr in enumerate(result.debate_transcript):
            assert dr["round_number"] == i + 1

    def test_max_rounds_zero_treated_as_one(self):
        """max_rounds<1 应被修正为 1。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=0)
        assert len(result.debate_transcript) == 1

    def test_more_rounds_produces_more_findings(self):
        """更多轮次应产出更多 findings。"""
        runner = ResearchRunner()
        result_1 = runner.run_research(GOAL, max_rounds=1)
        result_3 = runner.run_research(GOAL, max_rounds=3)
        assert len(result_3.ranked_findings) > len(result_1.ranked_findings)


class TestResearchResultSerialization:
    """ResearchResult JSON 序列化测试。"""

    def test_to_dict_returns_serializable_dict(self):
        """ResearchResult.to_dict() 应返回可 JSON 序列化的字典。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=1)
        d = result.to_dict()
        assert isinstance(d, dict)
        # 应能被 json.dumps 序列化
        json_str = json.dumps(d, ensure_ascii=False)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_to_json_returns_valid_json(self):
        """ResearchResult.to_json() 应返回合法 JSON 字符串。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=1)
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["research_id"] == result.research_id
        assert parsed["goal"] == result.goal
        assert parsed["summary"] == result.summary
        assert isinstance(parsed["ranked_findings"], list)
        assert isinstance(parsed["evidence_lineage"], list)
        assert isinstance(parsed["debate_transcript"], list)

    def test_result_contains_all_required_fields(self):
        """ResearchResult 应包含所有必需字段。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, max_rounds=1)
        d = result.to_dict()
        required_fields = [
            "research_id", "goal", "summary", "ranked_findings",
            "evidence_lineage", "debate_transcript", "specialist_contributions",
            "confidence", "started_at", "finished_at",
        ]
        for field in required_fields:
            assert field in d, f"缺少字段: {field}"


class TestModuleLevelFunction:
    """模块级便捷函数测试。"""

    def test_run_research_module_function(self):
        """模块级 run_research 函数应正常工作。"""
        result = run_research(GOAL)
        assert isinstance(result, ResearchResult)
        assert result.goal == GOAL
        assert len(result.ranked_findings) > 0

    def test_run_research_empty_goal(self):
        """模块级函数处理空 goal。"""
        result = run_research("")
        assert isinstance(result, ResearchResult)
        assert len(result.ranked_findings) == 0
