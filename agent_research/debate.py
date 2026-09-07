# -*- coding: utf-8 -*-
"""
Debate Orchestrator — 互相质疑与交叉质询
===========================================
研究流程中的多专家辩论机制。

Critic 专家对其他专家提出的假设进行交叉质询（cross_examine），
生成 Critique（质疑），并按轮次组织为 DebateRound。

设计原则：
  - 纯规则生成质疑内容，不调用外部 AI
  - 质疑基于假设的置信度、证据数量、陈述长度等可观测特征
  - 每个 Critique 绑定 from_specialist / to_hypothesis / severity
  - 与 agent_runtime 风格一致
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agent_research.specialist import Specialist, _short_id, _utc_now_iso
from agent_research.hypothesis import (
    Hypothesis,
    HYPOTHESIS_CHALLENGED,
    HYPOTHESIS_PROPOSED,
)


# 质疑严重度
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"

VALID_SEVERITIES = {SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL}


@dataclass
class Critique:
    """
    质疑记录。

    Attributes:
        critique_id: 质疑唯一标识
        from_specialist: 提出质疑的专家 ID
        to_hypothesis: 被质疑的假设 ID
        content: 质疑内容
        severity: 严重度（low / medium / high / critical）
        evidence_refs: 质疑引用的证据列表
        created_at: 创建时间
    """
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
    """
    一轮辩论。

    Attributes:
        round_number: 轮次编号（从 1 开始）
        hypotheses: 本轮参与辩论的假设列表
        critiques: 本轮产生的质疑列表
        responses: 被质疑专家的回应列表（dict: hypothesis_id -> response_text）
    """
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
    """
    辩论编排器。

    调度 critic 角色的专家对其他专家的假设进行交叉质询，
    并组织为 DebateRound。

    质疑生成规则（基于可观测特征，非 AI）：
      - 假设 confidence < 0.5 → high 严重度质疑"置信度不足"
      - 假设 evidence_refs 为空 → critical 严重度质疑"缺乏证据支撑"
      - 假设陈述长度 < 20 字 → medium 严重度质疑"陈述过于简略"
      - 同一专家提出多个相似假设 → low 严重度质疑"假设冗余"
      - 默认 → medium 严重度一般性质疑
    """

    def __init__(self) -> None:
        self._critique_templates = {
            "no_evidence": (
                "假设「{statement}」未提供任何证据引用（evidence_refs 为空），"
                "结论缺乏可追溯的事实支撑，建议补充原始数据或文献来源。"
            ),
            "low_confidence": (
                "假设「{statement}」的置信度仅为 {confidence:.2f}，低于 0.5 阈值，"
                "核心判断的可靠性存疑，需提供更强的推理链或补充证据。"
            ),
            "too_brief": (
                "假设「{statement}」陈述过于简略（仅 {length} 字），"
                "关键变量和边界条件未明确，可能导致后续验证方向模糊。"
            ),
            "redundant": (
                "假设「{statement}」与同专家此前提出的假设存在语义重叠，"
                "建议合并或明确区分各自的验证维度，避免探索资源浪费。"
            ),
            "general": (
                "对假设「{statement}」提出一般性审查：需确认其前提假设是否成立、"
                "反例是否已被排除、以及结论是否可被独立复现。"
            ),
        }

    def cross_examine(self, hypothesis: Hypothesis, critic: Specialist) -> Critique:
        """
        对单个假设进行交叉质询。

        Args:
            hypothesis: 被质疑的假设
            critic: 执行质询的评论专家

        Returns:
            Critique 对象
        """
        statement = hypothesis.statement
        severity = SEVERITY_MEDIUM
        template_key = "general"

        # 规则 1：无证据 → critical
        if not hypothesis.evidence_refs:
            severity = SEVERITY_CRITICAL
            template_key = "no_evidence"
        # 规则 2：低置信度 → high
        elif hypothesis.confidence < 0.5:
            severity = SEVERITY_HIGH
            template_key = "low_confidence"
        # 规则 3：陈述过短 → medium
        elif len(statement) < 20:
            severity = SEVERITY_MEDIUM
            template_key = "too_brief"
        # 规则 4：默认一般性质疑
        else:
            severity = SEVERITY_MEDIUM
            template_key = "general"

        content = self._critique_templates[template_key].format(
            statement=statement,
            confidence=hypothesis.confidence,
            length=len(statement),
        )

        return Critique(
            critique_id=_short_id("crit"),
            from_specialist=critic.specialist_id,
            to_hypothesis=hypothesis.hypothesis_id,
            content=content,
            severity=severity,
            evidence_refs=[],
        )

    def run_debate_round(
        self,
        hypotheses: List[Hypothesis],
        specialists: List[Specialist],
        round_number: int = 1,
    ) -> DebateRound:
        """
        执行一轮辩论。

        流程：
          1. 筛选出 role == "critic" 且 enabled 的专家作为质询方
          2. 对每个非 critic 专家提出的假设，由每个 critic 进行交叉质询
          3. 被质疑的假设状态更新为 challenged
          4. 生成被质疑专家的简要回应（规则模板）

        Args:
            hypotheses: 参与辩论的假设列表
            specialists: 所有参与专家列表
            round_number: 轮次编号

        Returns:
            DebateRound 对象
        """
        debate_round = DebateRound(
            round_number=round_number,
            hypotheses=list(hypotheses),
        )

        critics = [s for s in specialists if s.role == "critic" and s.enabled]
        if not critics:
            return debate_round

        # 记录每个专家的假设数量，用于冗余检测
        specialist_hyp_count: Dict[str, int] = {}
        for h in hypotheses:
            specialist_hyp_count[h.specialist_id] = specialist_hyp_count.get(h.specialist_id, 0) + 1

        for hyp in hypotheses:
            # critic 自己的假设也可以被其他 critic 质疑，但跳过无意义的自我质询
            for critic in critics:
                if critic.specialist_id == hyp.specialist_id and len(critics) == 1:
                    continue
                critique = self.cross_examine(hyp, critic)
                debate_round.critiques.append(critique)

            # 更新假设状态为 challenged
            hyp.status = HYPOTHESIS_CHALLENGED

            # 生成被质疑专家的简要回应
            response = self._generate_response(hyp, specialist_hyp_count.get(hyp.specialist_id, 1))
            debate_round.responses[hyp.hypothesis_id] = response

        return debate_round

    def _generate_response(self, hypothesis: Hypothesis, hyp_count: int) -> str:
        """
        生成被质疑专家的简要回应（规则模板）。

        Args:
            hypothesis: 被质疑的假设
            hyp_count: 该专家提出的假设总数

        Returns:
            回应文本
        """
        if not hypothesis.evidence_refs:
            return (
                f"承认假设「{hypothesis.statement[:30]}...」当前证据不足，"
                "将在下一轮探索中补充证据引用并重新评估置信度。"
            )
        if hypothesis.confidence < 0.5:
            return (
                f"注意到置信度（{hypothesis.confidence:.2f}）偏低，"
                "将通过增加验证步骤和交叉比对来提升结论可靠性。"
            )
        if hyp_count > 2:
            return (
                "承认存在假设冗余风险，将在后续轮次中合并相似假设并聚焦核心验证方向。"
            )
        return (
            "已记录质疑意见，将在验证阶段逐项检查前提假设、排除反例并确认可复现性。"
        )
