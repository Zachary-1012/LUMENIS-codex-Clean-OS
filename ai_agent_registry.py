# -*- coding: utf-8 -*-
"""ZBC AI Agent Registry — Agent 注册中心（Production-Ready）

调用链位置：Task Parser → Intent → Agent Registry → Skill Selection → Permission Gate

每个 Agent 声明：
  - agent_id / name / description
  - capabilities: 能处理的 Intent 列表
  - required_permissions: 执行所需最低权限等级
  - risk_level: 该 Agent 操作的基础风险等级
  - preferred_skills: 优先使用的 Skill ID 列表（含 fallback 链）
  - timeout_seconds / max_retries

设计原则：
  1. Agent 不直接执行业务逻辑，只负责编排 Skill。
  2. Agent 声明的权限/风险是 Permission Gate 的输入，Agent 自身不得绕过。
  3. 未注册的 Intent → fail-closed，不自动分配 Agent。
  4. 自研实现，不依赖任何第三方 Agent 框架。
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from ai_task_parser import Intent, TaskRiskLevel

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 1. AgentSpec
# ═══════════════════════════════════════════════════════════════

@dataclass
class AgentSpec:
    """Agent 规格声明。"""
    agent_id: str
    name: str
    description: str
    capabilities: List[str]                       # 能处理的 Intent.value 列表
    required_permission: str                      # 所需最低权限等级 (permission_gate.PermissionLevel.value)
    risk_level: TaskRiskLevel                     # 基础风险等级
    preferred_skills: List[str] = field(default_factory=list)  # 优先 Skill ID（含 fallback 链）
    timeout_seconds: int = 60
    max_retries: int = 3
    owner: str = "core-team"
    version: str = "1.0.0"
    enabled: bool = True
    # 该 Agent 是否允许外部副作用（浏览器/网络）
    allows_external_side_effect: bool = False
    # 该 Agent 是否需要人工审批（L3+）
    requires_human_approval: bool = False

    def can_handle(self, intent: Intent) -> bool:
        return intent.value in self.capabilities

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["risk_level"] = self.risk_level.value
        return d


# ═══════════════════════════════════════════════════════════════
# 2. 内置 Agent 定义
# ═══════════════════════════════════════════════════════════════

def _builtin_agents() -> List[AgentSpec]:
    return [
        AgentSpec(
            agent_id="data_query_agent",
            name="数据查询 Agent",
            description="只读查询 ZBC 数据库中的舆情/事件/笔记/统计数据，不修改任何生产数据。",
            capabilities=[
                Intent.QUERY_DATA.value,
                Intent.SUMMARIZE.value,
                Intent.CLASSIFY.value,
                Intent.COMPARE.value,
            ],
            required_permission="READ",
            risk_level=TaskRiskLevel.L0,
            preferred_skills=[
                "zbc.subject_authority_read",
                "zbc.skill_registry_snapshot",
            ],
            timeout_seconds=30,
            max_retries=2,
            allows_external_side_effect=False,
            requires_human_approval=False,
        ),
        AgentSpec(
            agent_id="analysis_agent",
            name="分析推理 Agent",
            description="对已有数据进行推理/异常发现/风险解释/趋势分析，纯内存计算，不写生产库。",
            capabilities=[
                Intent.REASON.value,
                Intent.ANOMALY_DETECTION.value,
                Intent.RISK_EXPLAIN.value,
            ],
            required_permission="ANALYZE",
            risk_level=TaskRiskLevel.L1,
            preferred_skills=[
                "zbc.agent_boundary_audit",
            ],
            timeout_seconds=60,
            max_retries=3,
            allows_external_side_effect=False,
            requires_human_approval=False,
        ),
        AgentSpec(
            agent_id="report_agent",
            name="报告生成 Agent",
            description="基于已有数据生成日报/周报/月报/专题报告，只读聚合，不修改源数据。",
            capabilities=[
                Intent.GENERATE_REPORT.value,
            ],
            required_permission="ANALYZE",
            risk_level=TaskRiskLevel.L1,
            preferred_skills=[],
            timeout_seconds=120,
            max_retries=2,
            allows_external_side_effect=False,
            requires_human_approval=False,
        ),
        AgentSpec(
            agent_id="browser_agent",
            name="浏览器 Agent",
            description="操作系统内浏览器进行只读浏览/搜索/页面操作。严格遵守官方账号只读保护，禁止任何写操作。",
            capabilities=[
                Intent.OPEN_BROWSER.value,
                Intent.WEB_SEARCH.value,
                Intent.PAGE_OPERATION.value,
            ],
            required_permission="VERIFY",
            risk_level=TaskRiskLevel.L2,
            preferred_skills=[],
            timeout_seconds=90,
            max_retries=2,
            allows_external_side_effect=True,
            requires_human_approval=False,
        ),
    ]


# ═══════════════════════════════════════════════════════════════
# 3. AgentRegistry
# ═══════════════════════════════════════════════════════════════

class AgentRegistry:
    """Agent 注册中心。

    用法：
        registry = AgentRegistry()
        agents = registry.find_agents_for_intent(Intent.QUERY_DATA)
        best = registry.select_best_agent(Intent.QUERY_DATA, context={})
    """

    def __init__(self, auto_register_builtins: bool = True):
        self._agents: Dict[str, AgentSpec] = {}
        self._lock = threading.Lock()
        if auto_register_builtins:
            for agent in _builtin_agents():
                self.register(agent)

    def register(self, spec: AgentSpec) -> bool:
        """注册 Agent。返回 True 表示成功。"""
        if not spec.agent_id or not spec.name:
            logger.warning(f"[AgentRegistry] 注册失败: agent_id/name 为空")
            return False
        with self._lock:
            self._agents[spec.agent_id] = spec
        logger.info(f"[AgentRegistry] Agent 已注册: {spec.agent_id} "
                     f"(capabilities={len(spec.capabilities)}, risk={spec.risk_level.value})")
        return True

    def unregister(self, agent_id: str) -> bool:
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                return True
        return False

    def get(self, agent_id: str) -> Optional[AgentSpec]:
        return self._agents.get(agent_id)

    def has(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def list_all(self) -> List[AgentSpec]:
        with self._lock:
            return list(self._agents.values())

    def list_enabled(self) -> List[AgentSpec]:
        return [a for a in self.list_all() if a.enabled]

    # ──────────────────────────────────────────────────────────
    # Intent → Agent 匹配
    # ──────────────────────────────────────────────────────────

    def find_agents_for_intent(self, intent: Intent) -> List[AgentSpec]:
        """找出所有能处理该 Intent 的已启用 Agent。"""
        return [
            a for a in self.list_enabled()
            if a.can_handle(intent)
        ]

    def select_best_agent(
        self,
        intent: Intent,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentSpec]:
        """选择最优 Agent。

        选择策略：
          1. 能处理该 Intent
          2. 风险等级最低（优先 L0/L1）
          3. 超时时间最短（优先快速 Agent）
          4. 若上下文包含 browser/page 相关信号，优先 browser_agent
        """
        candidates = self.find_agents_for_intent(intent)
        if not candidates:
            return None

        ctx = context or {}

        def score(agent: AgentSpec) -> tuple:
            # 风险等级排序：L0 < L1 < L2 < L3 < L4
            risk_order = ["L0", "L1", "L2", "L3", "L4"]
            risk_idx = risk_order.index(agent.risk_level.value)
            # 上下文偏好：如果当前页面是 browser 相关，browser_agent 加分
            ctx_bonus = 0
            current_page = str(ctx.get("current_page", "")).lower()
            if agent.agent_id == "browser_agent":
                if any(k in current_page for k in ("browser", "search", "web")):
                    ctx_bonus = -1  # 负分 = 更优先
            return (risk_idx, ctx_bonus, agent.timeout_seconds, agent.agent_id)

        candidates.sort(key=score)
        return candidates[0]

    # ──────────────────────────────────────────────────────────
    # Skill Selection（基于 Intent + Context，支持 fallback 链）
    # ──────────────────────────────────────────────────────────

    def select_skills(
        self,
        agent: AgentSpec,
        intent: Intent,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """为 Agent + Intent 选择 Skill 执行链（含 fallback）。

        返回 Skill ID 列表，按优先级排序。执行时依次尝试，失败则 fallback 到下一个。
        """
        skills = list(agent.preferred_skills)
        # 根据 Intent 动态补充
        intent_skill_hints: Dict[str, List[str]] = {
            Intent.QUERY_DATA.value: ["zbc.subject_authority_read"],
            Intent.SUMMARIZE.value: [],
            Intent.GENERATE_REPORT.value: [],
        }
        for hint in intent_skill_hints.get(intent.value, []):
            if hint not in skills:
                skills.append(hint)
        return skills

    # ──────────────────────────────────────────────────────────
    # 统计 / 能力清单
    # ──────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        agents = self.list_all()
        return {
            "total": len(agents),
            "enabled": len([a for a in agents if a.enabled]),
            "by_risk": {
                r: len([a for a in agents if a.risk_level.value == r])
                for r in ["L0", "L1", "L2", "L3", "L4"]
            },
            "capabilities_covered": sorted({
                c for a in agents for c in a.capabilities
            }),
        }

    def get_capabilities_matrix(self) -> Dict[str, Any]:
        """获取能力矩阵（用于 /api/ai/capabilities）。"""
        agents = self.list_enabled()
        intent_to_agents: Dict[str, List[str]] = {}
        for a in agents:
            for cap in a.capabilities:
                intent_to_agents.setdefault(cap, []).append(a.agent_id)
        return {
            "agents": [a.to_dict() for a in agents],
            "intent_to_agents": intent_to_agents,
            "stats": self.stats(),
        }


# ═══════════════════════════════════════════════════════════════
# 4. 全局单例
# ═══════════════════════════════════════════════════════════════

_default_registry: Optional[AgentRegistry] = None
_registry_lock = threading.Lock()


def get_agent_registry() -> AgentRegistry:
    global _default_registry
    if _default_registry is None:
        with _registry_lock:
            if _default_registry is None:
                _default_registry = AgentRegistry()
    return _default_registry


def reset_agent_registry() -> None:
    global _default_registry
    with _registry_lock:
        _default_registry = None


__all__ = [
    "AgentSpec",
    "AgentRegistry",
    "get_agent_registry",
    "reset_agent_registry",
]
