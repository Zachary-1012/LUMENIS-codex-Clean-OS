# -*- coding: utf-8 -*-
"""
Specialist Registry — 专家定义与注册中心
内置 3 个默认专家（analyst/critic/validator），支持注册/注销/查找。
纯数据结构 + 注册表，无外部依赖，不调用 AI。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_id(prefix: str) -> str:
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class Specialist:
    """专家定义：specialist_id/name/role/domain/capabilities/prompt_template/enabled/priority。"""
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
        return asdict(self)


class SpecialistRegistry:
    """专家注册表：register/unregister/get/list/by_role，内置默认专家。"""

    def __init__(self) -> None:
        self._specialists: Dict[str, Specialist] = {}
        for sp in default_specialists():
            self._specialists[sp.specialist_id] = sp

    def register(self, specialist: Specialist) -> Specialist:
        self._specialists[specialist.specialist_id] = specialist
        return specialist

    def unregister(self, specialist_id: str) -> bool:
        if specialist_id in self._specialists:
            del self._specialists[specialist_id]
            return True
        return False

    def get(self, specialist_id: str) -> Optional[Specialist]:
        return self._specialists.get(specialist_id)

    def list(self, enabled_only: bool = False) -> List[Specialist]:
        items = list(self._specialists.values())
        if enabled_only:
            items = [s for s in items if s.enabled]
        items.sort(key=lambda s: s.priority)
        return items

    def by_role(self, role: str) -> List[Specialist]:
        return [s for s in self._specialists.values() if s.role == role]


def default_specialists() -> List[Specialist]:
    """返回内置默认专家列表 [analyst, critic, validator]。"""
    return [
        Specialist(
            specialist_id="analyst", name="分析员", role="analyst",
            domain="general_research",
            capabilities=["goal_decomposition", "hypothesis_generation", "structured_findings", "trend_identification"],
            prompt_template="作为分析员，针对目标「{goal}」分解关键维度，生成结构化假设并标注证据需求。",
            enabled=True, priority=10,
        ),
        Specialist(
            specialist_id="critic", name="评论员", role="critic",
            domain="general_research",
            capabilities=["hypothesis_challenge", "counterexample_generation", "gap_identification", "bias_detection"],
            prompt_template="作为评论员，对假设「{statement}」提出质疑，识别逻辑漏洞、证据不足和潜在偏差。",
            enabled=True, priority=20,
        ),
        Specialist(
            specialist_id="validator", name="验证员", role="validator",
            domain="general_research",
            capabilities=["evidence_verification", "consistency_check", "conclusion_validation", "lineage_audit"],
            prompt_template="作为验证员，验证发现「{finding}」的证据链完整性，检查内部一致性并确认结论可靠性。",
            enabled=True, priority=30,
        ),
    ]
