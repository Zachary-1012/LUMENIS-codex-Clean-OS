# -*- coding: utf-8 -*-
"""
Specialist Registry — 专家定义与注册中心
==========================================
探索式 Agent 研究模式中的 Specialist（专家角色）定义。

每个 Specialist 代表一个研究视角（分析员 / 评论员 / 验证员），
拥有独立的 capabilities、prompt_template 和 priority，可被 ResearchRunner
调度参与假设生成、并行探索、交叉质疑与验证。

设计原则：
  - 纯数据结构 + 注册表，无外部依赖
  - 内置 3 个默认专家，可注册/注销自定义专家
  - 不调用外部 AI，prompt_template 仅用于规则模板渲染
  - 与 agent_runtime 风格一致：utf-8、dataclass、type hints
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    """返回当前 UTC 时间的 ISO 格式字符串。"""
    return datetime.now(timezone.utc).isoformat()


def _short_id(prefix: str) -> str:
    """生成带前缀的短 ID。"""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class Specialist:
    """
    专家定义。

    Attributes:
        specialist_id: 专家唯一标识
        name: 专家显示名称
        role: 角色描述（analyst / critic / validator / custom）
        domain: 领域标签
        capabilities: 能力列表
        prompt_template: 规则模板（用于生成 findings / critiques，非 AI 调用）
        enabled: 是否启用
        priority: 调度优先级（数值越小越优先）
        created_at: 创建时间
    """
    specialist_id: str
    name: str
    role: str
    domain: str
    capabilities: List[str] = field(default_factory=list)
    prompt_template: str = ""
    enabled: bool = True
    priority: int = 100
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典。"""
        return asdict(self)


class SpecialistRegistry:
    """
    专家注册表。

    支持注册、注销、查找、列举专家。内置 3 个默认专家：
      - analyst   分析员：分解目标、生成假设、结构化发现
      - critic    评论员：质疑假设、识别漏洞、提出反例
      - validator 验证员：验证证据、检查一致性、确认结论
    """

    def __init__(self) -> None:
        self._specialists: Dict[str, Specialist] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """注册内置默认专家。"""
        for sp in default_specialists():
            self._specialists[sp.specialist_id] = sp

    def register(self, specialist: Specialist) -> Specialist:
        """
        注册一个专家。若 specialist_id 已存在则覆盖。

        Args:
            specialist: 待注册的专家

        Returns:
            注册后的专家对象
        """
        self._specialists[specialist.specialist_id] = specialist
        return specialist

    def unregister(self, specialist_id: str) -> bool:
        """
        注销专家。

        Args:
            specialist_id: 专家 ID

        Returns:
            是否成功注销（ID 不存在返回 False）
        """
        if specialist_id in self._specialists:
            del self._specialists[specialist_id]
            return True
        return False

    def get(self, specialist_id: str) -> Optional[Specialist]:
        """
        按 ID 查找专家。

        Args:
            specialist_id: 专家 ID

        Returns:
            专家对象，不存在返回 None
        """
        return self._specialists.get(specialist_id)

    def list(self, enabled_only: bool = False) -> List[Specialist]:
        """
        列举所有专家。

        Args:
            enabled_only: 是否仅返回启用的专家

        Returns:
            按 priority 排序的专家列表
        """
        items = list(self._specialists.values())
        if enabled_only:
            items = [s for s in items if s.enabled]
        items.sort(key=lambda s: s.priority)
        return items

    def by_role(self, role: str) -> List[Specialist]:
        """按角色筛选专家。"""
        return [s for s in self._specialists.values() if s.role == role]


def default_specialists() -> List[Specialist]:
    """
    返回内置默认专家列表（3 个）。

    Returns:
        [analyst, critic, validator]
    """
    return [
        Specialist(
            specialist_id="analyst",
            name="分析员",
            role="analyst",
            domain="general_research",
            capabilities=[
                "goal_decomposition",
                "hypothesis_generation",
                "structured_findings",
                "trend_identification",
            ],
            prompt_template=(
                "作为分析员，针对目标「{goal}」分解关键维度，"
                "生成结构化假设并标注证据需求。"
            ),
            enabled=True,
            priority=10,
        ),
        Specialist(
            specialist_id="critic",
            name="评论员",
            role="critic",
            domain="general_research",
            capabilities=[
                "hypothesis_challenge",
                "counterexample_generation",
                "gap_identification",
                "bias_detection",
            ],
            prompt_template=(
                "作为评论员，对假设「{statement}」提出质疑，"
                "识别逻辑漏洞、证据不足和潜在偏差。"
            ),
            enabled=True,
            priority=20,
        ),
        Specialist(
            specialist_id="validator",
            name="验证员",
            role="validator",
            domain="general_research",
            capabilities=[
                "evidence_verification",
                "consistency_check",
                "conclusion_validation",
                "lineage_audit",
            ],
            prompt_template=(
                "作为验证员，验证发现「{finding}」的证据链完整性，"
                "检查内部一致性并确认结论可靠性。"
            ),
            enabled=True,
            priority=30,
        ),
    ]
