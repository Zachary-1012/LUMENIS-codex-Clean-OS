# -*- coding: utf-8 -*-
"""
Debate Orchestrator — 互相质疑与交叉质询
Critic 专家对假设进行交叉质询，按轮次组织为 DebateRound。
质疑基于假设可观测特征（置信度/证据数/陈述长度）规则生成，不调用 AI。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

from agent_research.specialist import Specialist, _short_id, _utc_now_iso
from agent_research.hypothesis import Hypothesis, HYPOTHESIS_CHALLENGED

SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"


@dataclass
class Critique:
    """质疑记录：from_specialist/to_hypothesis/content/severity/evidence_refs。"""
    critique_id: str
    from_specialist: str
    to_hypothesis: str
    content: str
    severity: str = SEVERITY_MEDIUM
    evidence_refs: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DebateRound:
    """一轮辩论：round_number/hypotheses/critiques/responses。"""
    round_number: int
    hypotheses: List[Hypothesis] = field(default_factory=list)
    critiques: List[Critique] = field(default_factory=list)
    responses: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_number": self.round_number,
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "critiques": [c.to_dict() for c in self.critiques],
            "responses": self.responses,
        }


class DebateOrchestrator:
    """辩论编排器：cross_examine 单假设质询，run_debate_round 整轮辩论。"""

    _TEMPLATES = {
        "no_evidence": "假设「{statement}」未提供任何证据引用（evidence_refs 为空），结论缺乏可追溯的事实支撑，建议补充原始数据或文献来源。",
        "low_confidence": "假设「{statement}」的置信度仅为 {confidence:.2f}，低于 0.5 阈值，核心判断的可靠性存疑，需提供更强的推理链或补充证据。",
        "too_brief": "假设「{statement}」陈述过于简略（仅 {length} 字），关键变量和边界条件未明确，可能导致后续验证方向模糊。",
        "general": "对假设「{statement}」提出一般性审查：需确认其前提假设是否成立、反例是否已被排除、以及结论是否可被独立复现。",
    }

    def cross_examine(self, hypothesis: Hypothesis, critic: Specialist) -> Critique:
        """对单个假设进行交叉质询，根据可观测特征决定严重度。"""
        statement = hypothesis.statement
        if not hypothesis.evidence_refs:
            severity, key = SEVERITY_CRITICAL, "no_evidence"
        elif hypothesis.confidence < 0.5:
            severity, key = SEVERITY_HIGH, "low_confidence"
        elif len(statement) < 20:
            severity, key = SEVERITY_MEDIUM, "too_brief"
        else:
            severity, key = SEVERITY_MEDIUM, "general"

        content = self._TEMPLATES[key].format(
            statement=statement, confidence=hypothesis.confidence, length=len(statement),
        )
        return Critique(
            critique_id=_short_id("crit"),
            from_specialist=critic.specialist_id,
            to_hypothesis=hypothesis.hypothesis_id,
            content=content,
            severity=severity,
        )

    def run_debate_round(
        self, hypotheses: List[Hypothesis], specialists: List[Specialist], round_number: int = 1,
    ) -> DebateRound:
        """执行一轮辩论：每个 critic 对每个假设质询，更新状态为 challenged，生成回应。"""
        debate_round = DebateRound(round_number=round_number, hypotheses=list(hypotheses))
        critics = [s for s in specialists if s.role == "critic" and s.enabled]
        if not critics:
            return debate_round

        hyp_count: Dict[str, int] = {}
        for h in hypotheses:
            hyp_count[h.specialist_id] = hyp_count.get(h.specialist_id, 0) + 1

        for hyp in hypotheses:
            for critic in critics:
                if critic.specialist_id == hyp.specialist_id and len(critics) == 1:
                    continue
                debate_round.critiques.append(self.cross_examine(hyp, critic))
            hyp.status = HYPOTHESIS_CHALLENGED
            debate_round.responses[hyp.hypothesis_id] = self._response(hyp, hyp_count.get(hyp.specialist_id, 1))
        return debate_round

    def _response(self, hypothesis: Hypothesis, hyp_count: int) -> str:
        if not hypothesis.evidence_refs:
            return f"承认假设「{hypothesis.statement[:30]}...」当前证据不足，将在下一轮探索中补充证据引用并重新评估置信度。"
        if hypothesis.confidence < 0.5:
            return f"注意到置信度（{hypothesis.confidence:.2f}）偏低，将通过增加验证步骤和交叉比对来提升结论可靠性。"
        if hyp_count > 2:
            return "承认存在假设冗余风险，将在后续轮次中合并相似假设并聚焦核心验证方向。"
        return "已记录质疑意见，将在验证阶段逐项检查前提假设、排除反例并确认可复现性。"
