# -*- coding: utf-8 -*-
"""
agent_research.runner 集成测试
==============================
覆盖：真实来源研究流程、专家计划兼容、假设生成、非事实验证、结果排序、
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
# Synthetic, already-resolved SourceBrief fixtures; not live research evidence.
RECORDS = [
    {"source_id": "source-one", "evidence_id": "scope:one", "scope_evidence_ref": "scope:one",
     "title": "抽样来源", "content_excerpt": "广州太古汇小红书舆情抽样显示排队投诉；样本不能证明总体趋势。"},
    {"source_id": "source-two", "evidence_id": "scope:two", "scope_evidence_ref": "scope:two",
     "title": "服务记录", "content_excerpt": "本来源仅记录服务体验，未开展平台全量统计。"},
]


class TestBasicResearchFlow:
    """基本研究流程测试。"""

    def test_run_research_returns_result(self):
        runner = ResearchRunner()
        result = runner.run_research(GOAL, records=RECORDS, max_rounds=1)
        assert isinstance(result, ResearchResult)
        assert result.research_id.startswith("research_")
        assert result.goal == GOAL and result.summary
        assert result.status == "research_draft"
        # Pure analysis does not invent execution timestamps.
        assert result.started_at == result.finished_at == ""
        assert result == runner.run_research(GOAL, records=RECORDS, max_rounds=1)

    def test_research_produces_findings(self):
        """研究应产出非空 findings。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, records=RECORDS, max_rounds=1)
        assert len(result.ranked_findings) > 0

    def test_research_produces_open_questions_without_simulated_debate(self):
        result = ResearchRunner().run_research(GOAL, records=RECORDS)
        assert result.debate_transcript == []
        assert result.hypotheses
        assert all(h["status"] == "proposed" for h in result.hypotheses)
        assert all(h["validation_needed"] for h in result.hypotheses)

    def test_every_finding_has_evidence_and_lineage(self):
        """每个 finding 必须带 evidence_refs 和 lineage_id。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, records=RECORDS, max_rounds=1)
        for f in result.ranked_findings:
            assert len(f["evidence_refs"]) > 0, f"finding {f.get('finding_id')} 缺少 evidence_refs"
            assert f.get("lineage_id"), f"finding {f.get('finding_id')} 缺少 lineage_id"


class TestParallelExploration:
    """多专家并行探索测试。"""

    def test_specialist_plan_does_not_claim_executed_contributions(self):
        runner = ResearchRunner()
        assert {s.specialist_id for s in runner._specialists} == {s.specialist_id for s in default_specialists()}
        result = runner.run_research(GOAL, records=RECORDS)
        assert result.specialist_contributions == {"source_reader": len(RECORDS)}
        # Configured specialists have not independently read/verified sources.
        assert not any(result.specialist_contributions.get(s.specialist_id, 0) for s in default_specialists())

    def test_findings_count_tracks_sources_not_specialist_multiplication(self):
        result = ResearchRunner().run_research(GOAL, records=RECORDS, max_rounds=1)
        assert len(result.ranked_findings) == len(RECORDS)
        assert {f["evidence_refs"][0] for f in result.ranked_findings} == {r["evidence_id"] for r in RECORDS}
        assert not ResearchRunner().run_research(GOAL).ranked_findings


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

    def test_citations_do_not_mark_findings_validated(self):
        result = ResearchRunner().run_research(GOAL, records=RECORDS)
        assert result.ranked_findings  # Do not let the negative assertion pass vacuously.
        for finding in result.ranked_findings:
            assert finding["validated"] is False
            assert finding["fact_verified"] is False
            assert finding["confidence"] is None
            assert finding["claim_type"] == "source_statement"

    def test_source_hypotheses_remain_proposed_without_independent_review(self):
        result = ResearchRunner().run_research(GOAL, records=RECORDS, max_rounds=2)
        assert result.hypotheses
        assert {h["status"] for h in result.hypotheses} == {"proposed"}
        assert all(h["evidence_refs"] for h in result.hypotheses)
        assert not result.debate_transcript  # No simulated independent approval/rejection.


class TestRanking:
    """结果排序测试。"""

    def test_findings_sorted_by_rank_score_desc(self):
        """ranked_findings 应按 rank_score 降序排列。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, records=RECORDS, max_rounds=2)
        scores = [f["rank_score"] for f in result.ranked_findings]
        assert scores == sorted(scores, reverse=True)

    def test_top_finding_has_highest_explainable_lexical_overlap(self):
        result = ResearchRunner().run_research(GOAL, records=RECORDS, max_rounds=1)
        top = result.ranked_findings[0]
        assert top["rank_score"] > 0
        assert top["rank_score"] == len(top["matched_terms"])
        assert top["source_id"] == "source-one"
        assert top["rank_method"] == "question_lexical_overlap"
        assert top["confidence"] is None


class TestEvidenceLineage:
    """证据血缘可追溯测试。"""

    def test_result_has_evidence_lineage(self):
        """ResearchResult 应包含非空 evidence_lineage。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, records=RECORDS, max_rounds=1)
        assert len(result.evidence_lineage) > 0

    def test_lineage_records_have_required_fields(self):
        result = ResearchRunner().run_research(GOAL, records=RECORDS)
        assert len(result.evidence_lineage) == len(RECORDS)
        for record in result.evidence_lineage:
            assert record["lineage_id"].startswith("lineage_")
            assert record["evidence_id"] in {r["evidence_id"] for r in RECORDS}
            assert record["source"] in {r["source_id"] for r in RECORDS}
            assert record["lineage_steps"][:2] == [record["source"], record["evidence_id"]]
            finding = next(f for f in result.ranked_findings if f["lineage_id"] == record["lineage_id"])
            assert record["lineage_steps"][-1] == finding["finding_id"]
            assert record["provenance"]["fact_verified"] is False

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
        result = ResearchRunner().run_research("", max_rounds=1)
        assert result.goal == ""
        assert result.ranked_findings == result.debate_transcript == []
        assert result.confidence is None
        assert result.status == "needs_sources"
        assert result.metrics["evaluation_status"] == "NO_DATA"

    def test_whitespace_goal_returns_empty_result(self):
        """纯空格 goal 应返回空结果。"""
        runner = ResearchRunner()
        result = runner.run_research("   ", max_rounds=1)
        assert len(result.ranked_findings) == 0


class TestCustomSpecialists:
    """自定义专家列表测试。"""

    def test_custom_specialist_configuration_preserved_without_fake_work(self):
        custom = Specialist(specialist_id="market_researcher", name="市场研究员", role="analyst", domain="market", capabilities=["market_analysis"])
        runner = ResearchRunner(specialists=[custom])
        assert runner._specialists == [custom]
        result = runner.run_research(GOAL, specialists=[custom], records=RECORDS, max_rounds=1)
        assert result.specialist_contributions == {"source_reader": len(RECORDS)}
        assert result.status == "research_draft"

    def test_module_level_function_with_custom_specialists(self):
        custom = Specialist(specialist_id="custom_analyst", name="自定义分析员", role="analyst", domain="custom", capabilities=["custom_cap"])
        result = run_research(GOAL, specialists=[custom], records=RECORDS)
        assert isinstance(result, ResearchResult)
        assert result.specialist_contributions == {"source_reader": len(RECORDS)}
        assert all(f["validated"] is False for f in result.ranked_findings)


class TestMaxRounds:
    """max_rounds 限制测试。"""

    def test_one_round_does_not_invent_debate(self):
        result = ResearchRunner().run_research(GOAL, records=RECORDS, max_rounds=1)
        assert result.debate_transcript == []
        assert len(result.ranked_findings) == len(RECORDS)

    def test_three_rounds_do_not_invent_debate(self):
        result = ResearchRunner().run_research(GOAL, records=RECORDS, max_rounds=3)
        assert result.debate_transcript == []
        assert len(result.ranked_findings) == len(RECORDS)
        assert result.confidence is None

    def test_max_rounds_zero_treated_as_one(self):
        runner = ResearchRunner()
        assert runner.run_research(GOAL, records=RECORDS, max_rounds=0) == runner.run_research(GOAL, records=RECORDS, max_rounds=1)

    def test_more_rounds_do_not_inflate_findings(self):
        runner = ResearchRunner()
        result_1 = runner.run_research(GOAL, records=RECORDS, max_rounds=1)
        result_3 = runner.run_research(GOAL, records=RECORDS, max_rounds=3)
        assert result_3 == result_1
        assert len(result_3.ranked_findings) == len(RECORDS)


class TestResearchResultSerialization:
    """ResearchResult JSON 序列化测试。"""

    def test_to_dict_returns_serializable_dict(self):
        """ResearchResult.to_dict() 应返回可 JSON 序列化的字典。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, records=RECORDS, max_rounds=1)
        d = result.to_dict()
        assert isinstance(d, dict)
        # 应能被 json.dumps 序列化
        json_str = json.dumps(d, ensure_ascii=False)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_to_json_returns_valid_json(self):
        """ResearchResult.to_json() 应返回合法 JSON 字符串。"""
        runner = ResearchRunner()
        result = runner.run_research(GOAL, records=RECORDS, max_rounds=1)
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
        result = runner.run_research(GOAL, records=RECORDS, max_rounds=1)
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
        result = run_research(GOAL, records=RECORDS)
        assert isinstance(result, ResearchResult)
        assert result.goal == GOAL
        assert len(result.ranked_findings) > 0

    def test_run_research_empty_goal(self):
        """模块级函数处理空 goal。"""
        result = run_research("")
        assert isinstance(result, ResearchResult)
        assert len(result.ranked_findings) == 0
