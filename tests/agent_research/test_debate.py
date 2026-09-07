# -*- coding: utf-8 -*-
"""
agent_research.debate 单元测试
==============================
覆盖：交叉质询、辩论轮次执行、质疑严重度规则、空假设处理、Critique 序列化。
"""
import pytest

from agent_research.specialist import Specialist, default_specialists
from agent_research.hypothesis import Hypothesis, HYPOTHESIS_PROPOSED, HYPOTHESIS_CHALLENGED
from agent_research.debate import (
    Critique,
    DebateRound,
    DebateOrchestrator,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
)


def _make_hypothesis(
    statement: str = "测试假设陈述内容足够长以避免过短检测",
    confidence: float = 0.6,
    evidence_refs: list = None,
    specialist_id: str = "analyst",
) -> Hypothesis:
    """构造测试用 Hypothesis。"""
    return Hypothesis(
        hypothesis_id="hyp_test_001",
        statement=statement,
        specialist_id=specialist_id,
        evidence_refs=evidence_refs if evidence_refs is not None else ["ev_001"],
        confidence=confidence,
        status=HYPOTHESIS_PROPOSED,
    )


class TestCrossExamine:
    """交叉质询测试。"""

    def test_cross_examine_returns_critique(self):
        """cross_examine 应返回 Critique 对象。"""
        orchestrator = DebateOrchestrator()
        critic = default_specialists()[1]  # critic
        hyp = _make_hypothesis()
        critique = orchestrator.cross_examine(hyp, critic)
        assert isinstance(critique, Critique)
        assert critique.from_specialist == "critic"
        assert critique.to_hypothesis == "hyp_test_001"
        assert critique.content != ""

    def test_no_evidence_triggers_critical(self):
        """无证据的假设应触发 critical 严重度质疑。"""
        orchestrator = DebateOrchestrator()
        critic = default_specialists()[1]
        hyp = _make_hypothesis(evidence_refs=[])
        critique = orchestrator.cross_examine(hyp, critic)
        assert critique.severity == SEVERITY_CRITICAL

    def test_low_confidence_triggers_high(self):
        """低置信度（<0.5）且有证据应触发 high 严重度。"""
        orchestrator = DebateOrchestrator()
        critic = default_specialists()[1]
        hyp = _make_hypothesis(confidence=0.3, evidence_refs=["ev_001"])
        critique = orchestrator.cross_examine(hyp, critic)
        assert critique.severity == SEVERITY_HIGH

    def test_brief_statement_triggers_medium(self):
        """陈述过短（<20字）且有证据、置信度正常应触发 medium。"""
        orchestrator = DebateOrchestrator()
        critic = default_specialists()[1]
        hyp = _make_hypothesis(statement="短假设", confidence=0.7, evidence_refs=["ev_001"])
        critique = orchestrator.cross_examine(hyp, critic)
        assert critique.severity == SEVERITY_MEDIUM

    def test_normal_hypothesis_triggers_medium(self):
        """正常假设应触发 medium 一般性质疑。"""
        orchestrator = DebateOrchestrator()
        critic = default_specialists()[1]
        hyp = _make_hypothesis(confidence=0.8, evidence_refs=["ev_001", "ev_002"])
        critique = orchestrator.cross_examine(hyp, critic)
        assert critique.severity == SEVERITY_MEDIUM

    def test_critique_has_id_and_timestamp(self):
        """Critique 应自动生成 ID 和时间戳。"""
        orchestrator = DebateOrchestrator()
        critic = default_specialists()[1]
        hyp = _make_hypothesis()
        critique = orchestrator.cross_examine(hyp, critic)
        assert critique.critique_id.startswith("crit_")
        assert critique.created_at != ""


class TestRunDebateRound:
    """辩论轮次测试。"""

    def test_run_debate_round_produces_critiques(self):
        """run_debate_round 应对假设产生质疑。"""
        orchestrator = DebateOrchestrator()
        specialists = default_specialists()
        hyp = _make_hypothesis()
        debate_round = orchestrator.run_debate_round([hyp], specialists, round_number=1)
        assert isinstance(debate_round, DebateRound)
        assert debate_round.round_number == 1
        assert len(debate_round.critiques) > 0
        assert len(debate_round.hypotheses) == 1

    def test_hypothesis_status_updated_to_challenged(self):
        """辩论后假设状态应更新为 challenged。"""
        orchestrator = DebateOrchestrator()
        specialists = default_specialists()
        hyp = _make_hypothesis()
        assert hyp.status == HYPOTHESIS_PROPOSED
        orchestrator.run_debate_round([hyp], specialists, round_number=1)
        assert hyp.status == HYPOTHESIS_CHALLENGED

    def test_responses_generated_for_each_hypothesis(self):
        """每个被质疑的假设应有回应。"""
        orchestrator = DebateOrchestrator()
        specialists = default_specialists()
        hyp1 = _make_hypothesis(statement="第一个假设陈述内容足够长", specialist_id="analyst")
        hyp1.hypothesis_id = "hyp_001"
        hyp2 = _make_hypothesis(statement="第二个假设陈述内容足够长", specialist_id="validator")
        hyp2.hypothesis_id = "hyp_002"
        debate_round = orchestrator.run_debate_round([hyp1, hyp2], specialists, round_number=1)
        assert "hyp_001" in debate_round.responses
        assert "hyp_002" in debate_round.responses
        assert debate_round.responses["hyp_001"] != ""

    def test_empty_hypotheses_returns_empty_round(self):
        """空假设列表应返回空辩论轮次。"""
        orchestrator = DebateOrchestrator()
        specialists = default_specialists()
        debate_round = orchestrator.run_debate_round([], specialists, round_number=1)
        assert len(debate_round.critiques) == 0
        assert len(debate_round.hypotheses) == 0

    def test_no_critics_returns_no_critiques(self):
        """无 critic 专家时不应产生质疑。"""
        orchestrator = DebateOrchestrator()
        only_analysts = [s for s in default_specialists() if s.role != "critic"]
        hyp = _make_hypothesis()
        debate_round = orchestrator.run_debate_round([hyp], only_analysts, round_number=1)
        assert len(debate_round.critiques) == 0

    def test_debate_round_to_dict(self):
        """DebateRound.to_dict() 应返回可序列化字典。"""
        orchestrator = DebateOrchestrator()
        specialists = default_specialists()
        hyp = _make_hypothesis()
        debate_round = orchestrator.run_debate_round([hyp], specialists, round_number=1)
        d = debate_round.to_dict()
        assert isinstance(d, dict)
        assert d["round_number"] == 1
        assert isinstance(d["hypotheses"], list)
        assert isinstance(d["critiques"], list)
        assert isinstance(d["responses"], dict)
