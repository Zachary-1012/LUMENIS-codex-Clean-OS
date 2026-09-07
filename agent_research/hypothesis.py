# -*- coding: utf-8 -*-
"""
Hypothesis & Exploration — 假设与探索路径
假设生命周期：proposed → challenged → verified/rejected。
纯规则生成，不调用 AI。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from agent_research.specialist import Specialist, _short_id, _utc_now_iso

HYPOTHESIS_PROPOSED = "proposed"
HYPOTHESIS_CHALLENGED = "challenged"
HYPOTHESIS_VERIFIED = "verified"
HYPOTHESIS_REJECTED = "rejected"


@dataclass
class Hypothesis:
    """研究假设：statement/specialist_id/evidence_refs/confidence/status。"""
    hypothesis_id: str
    statement: str
    specialist_id: str
    evidence_refs: List[str] = field(default_factory=list)
    confidence: float = 0.5
    status: str = HYPOTHESIS_PROPOSED
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExplorationPath:
    """探索路径：specialist_id/steps/findings/evidence_chain/status。"""
    path_id: str
    specialist_id: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    evidence_chain: List[str] = field(default_factory=list)
    status: str = "exploring"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HypothesisGenerator:
    """基于规则的假设生成器：从 goal 提取关键词，按专家角色生成假设。"""

    _STOP_WORDS = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "上", "也", "很",
        "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "什么",
        "怎么", "如何", "为什么", "是否", "可以", "能够", "应该", "需要", "the", "a", "an", "is",
        "are", "was", "were", "of", "to", "in", "for", "on", "with", "at", "by", "from", "as",
    }

    _ROLE_TEMPLATES = {
        "analyst": [
            "目标「{goal}」的核心驱动因素可能是{dimension}，需验证其因果关系。",
            "围绕「{goal}」，{dimension}维度存在显著的结构化差异，值得深入分析。",
        ],
        "critic": [
            "「{goal}」的主流解释可能忽略了{dimension}这一反例维度，需检验其完备性。",
            "对「{goal}」的既有假设可能存在{dimension}方面的偏差，应进行反向验证。",
        ],
        "validator": [
            "「{goal}」的结论可靠性取决于{dimension}证据的充分性，需逐项核验。",
            "验证「{goal}」时，{dimension}维度的内部一致性是关键检查点。",
        ],
    }

    _DIMENSION_POOL = ["时间趋势", "地域分布", "主体类型", "内容情感", "传播路径",
                        "风险等级", "数据质量", "因果关系", "样本代表性", "外部影响"]

    def __init__(self, specialists: Optional[List[Specialist]] = None) -> None:
        if specialists is None:
            from agent_research.specialist import default_specialists
            specialists = default_specialists()
        self._specialists = [s for s in specialists if s.enabled]

    def _extract_keywords(self, goal: str) -> List[str]:
        if not goal:
            return []
        tokens = re.split(r"[，。！？、；：,.!?;:\\s\\n\\t]+", goal)
        keywords, seen = [], set()
        for tok in tokens:
            tok = tok.strip()
            if not tok or tok.lower() in self._STOP_WORDS or len(tok) < 2 or tok in seen:
                continue
            seen.add(tok)
            keywords.append(tok)
        keywords.sort(key=len, reverse=True)
        return keywords

    def generate(self, goal: str, max_per_specialist: int = 2) -> List[Hypothesis]:
        """从 goal 生成初始假设，每个专家最多 max_per_specialist 条。"""
        if not goal or not goal.strip():
            return []
        keywords = self._extract_keywords(goal)
        hypotheses: List[Hypothesis] = []
        for sp in self._specialists:
            templates = self._ROLE_TEMPLATES.get(sp.role, self._ROLE_TEMPLATES["analyst"])
            for i in range(min(max_per_specialist, len(templates))):
                dimension = keywords[i % len(keywords)] if keywords else self._DIMENSION_POOL[i % len(self._DIMENSION_POOL)]
                hypotheses.append(Hypothesis(
                    hypothesis_id=_short_id("hyp"),
                    statement=templates[i].format(goal=goal.strip(), dimension=dimension),
                    specialist_id=sp.specialist_id,
                    evidence_refs=[],
                    confidence=0.4 + 0.1 * i,
                    status=HYPOTHESIS_PROPOSED,
                ))
        return hypotheses
