# -*- coding: utf-8 -*-
"""
Hypothesis & Exploration — 假设与探索路径
===========================================
研究流程中的假设（Hypothesis）与探索路径（ExplorationPath）定义，
以及基于规则的假设生成器（HypothesisGenerator）。

假设生命周期：
  proposed（提出）→ challenged（被质疑）→ verified（验证通过）/ rejected（被否决）

设计原则：
  - 纯规则生成，不调用外部 AI
  - 每个假设绑定 specialist_id 和 evidence_refs
  - 探索路径记录完整 steps + findings + evidence_chain
  - 与 agent_runtime 风格一致
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agent_research.specialist import Specialist, _short_id, _utc_now_iso


# 假设状态枚举（用字符串常量，避免引入 Enum 依赖）
HYPOTHESIS_PROPOSED = "proposed"
HYPOTHESIS_CHALLENGED = "challenged"
HYPOTHESIS_VERIFIED = "verified"
HYPOTHESIS_REJECTED = "rejected"

VALID_HYPOTHESIS_STATUSES = {
    HYPOTHESIS_PROPOSED,
    HYPOTHESIS_CHALLENGED,
    HYPOTHESIS_VERIFIED,
    HYPOTHESIS_REJECTED,
}


@dataclass
class Hypothesis:
    """
    研究假设。

    Attributes:
        hypothesis_id: 假设唯一标识
        statement: 假设陈述
        specialist_id: 提出该假设的专家 ID
        evidence_refs: 关联证据引用列表
        confidence: 置信度（0.0 - 1.0）
        status: 状态（proposed / challenged / verified / rejected）
        created_at: 创建时间
    """
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
    """
    探索路径：记录某个专家对某个目标/假设的探索过程。

    Attributes:
        path_id: 路径唯一标识
        specialist_id: 执行探索的专家 ID
        steps: 探索步骤列表（每步为 dict，含 action / detail / result）
        findings: 探索发现列表（每步为 dict，含 content / confidence / evidence_refs）
        evidence_chain: 证据链（按顺序的 evidence_id 列表）
        status: 路径状态（exploring / completed / blocked）
    """
    path_id: str
    specialist_id: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    evidence_chain: List[str] = field(default_factory=list)
    status: str = "exploring"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HypothesisGenerator:
    """
    基于规则的假设生成器。

    从研究目标（goal）中提取关键词，结合专家角色生成初始假设。
    不调用外部 AI，完全基于模板和规则。

    生成策略：
      1. 对 goal 做简单分词（按标点和空格切分，保留中文词组）
      2. 为每个启用的专家生成 1-2 个角色相关假设
      3. 假设模板包含：目标陈述 + 维度 + 可验证方向
    """

    # 停用词（中文常见无意义词）
    _STOP_WORDS = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
        "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
        "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "什么",
        "怎么", "如何", "为什么", "是否", "可以", "能够", "应该", "需要",
        "the", "a", "an", "is", "are", "was", "were", "of", "to", "in",
        "for", "on", "with", "at", "by", "from", "as", "into", "through",
    }

    # 各角色的假设模板
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

    # 通用分析维度池
    _DIMENSION_POOL = [
        "时间趋势", "地域分布", "主体类型", "内容情感", "传播路径",
        "风险等级", "数据质量", "因果关系", "样本代表性", "外部影响",
    ]

    def __init__(self, specialists: Optional[List[Specialist]] = None) -> None:
        """
        Args:
            specialists: 参与假设生成的专家列表；为 None 时使用默认专家
        """
        if specialists is None:
            from agent_research.specialist import default_specialists
            specialists = default_specialists()
        self._specialists = [s for s in specialists if s.enabled]

    def _extract_keywords(self, goal: str) -> List[str]:
        """
        从 goal 中提取关键词（简单规则分词）。

        Args:
            goal: 研究目标文本

        Returns:
            关键词列表（去重、过滤停用词、按长度降序）
        """
        if not goal:
            return []
        # 按标点和空格切分
        tokens = re.split(r"[，。！？、；：,.!?;:\\s\\n\\t]+", goal)
        keywords = []
        seen = set()
        for tok in tokens:
            tok = tok.strip()
            if not tok or tok.lower() in self._STOP_WORDS:
                continue
            if len(tok) < 2:
                continue
            if tok not in seen:
                seen.add(tok)
                keywords.append(tok)
        keywords.sort(key=len, reverse=True)
        return keywords

    def generate(self, goal: str, max_per_specialist: int = 2) -> List[Hypothesis]:
        """
        从目标生成初始假设。

        Args:
            goal: 研究目标
            max_per_specialist: 每个专家最多生成的假设数

        Returns:
            假设列表（status 均为 proposed）
        """
        if not goal or not goal.strip():
            return []

        keywords = self._extract_keywords(goal)
        hypotheses: List[Hypothesis] = []

        for sp in self._specialists:
            templates = self._ROLE_TEMPLATES.get(sp.role, self._ROLE_TEMPLATES["analyst"])
            count = min(max_per_specialist, len(templates))
            for i in range(count):
                # 选择维度：优先用 goal 中的关键词，否则用维度池
                dimension = keywords[i % len(keywords)] if keywords else self._DIMENSION_POOL[i % len(self._DIMENSION_POOL)]
                statement = templates[i].format(goal=goal.strip(), dimension=dimension)
                hyp = Hypothesis(
                    hypothesis_id=_short_id("hyp"),
                    statement=statement,
                    specialist_id=sp.specialist_id,
                    evidence_refs=[],
                    confidence=0.4 + 0.1 * i,  # 0.4 / 0.5
                    status=HYPOTHESIS_PROPOSED,
                )
                hypotheses.append(hyp)

        return hypotheses
