# -*- coding: utf-8 -*-
"""
Agent Research — 探索式 Agent / Research & Exploration Mode
多 Specialist 并行探索 → 互相质疑 → 验证 → 排序 → 汇总，保留完整 Evidence/Lineage。
复用现有 agent_runtime/agent_memory/agent_capability，不重写其源码。
不调用外部 AI，不创建多进程/多线程，纯规则实现。
Feature Flag: AGENT_RESEARCH_ENABLED=1 启用，默认关闭。
"""
from __future__ import annotations

import os

AGENT_RESEARCH_ENABLED = os.environ.get("AGENT_RESEARCH_ENABLED", "0") == "1"
__version__ = "0.1.0"

from agent_research.specialist import Specialist, SpecialistRegistry, default_specialists
from agent_research.hypothesis import (
    Hypothesis, ExplorationPath, HypothesisGenerator,
    HYPOTHESIS_PROPOSED, HYPOTHESIS_CHALLENGED, HYPOTHESIS_VERIFIED, HYPOTHESIS_REJECTED,
)
from agent_research.debate import (
    Critique, DebateRound, DebateOrchestrator,
    SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL,
)
from agent_research.lineage import EvidenceLineage, LineageTracker
from agent_research.runner import ResearchResult, ResearchRunner, run_research

__all__ = [
    "AGENT_RESEARCH_ENABLED",
    "Specialist", "SpecialistRegistry", "default_specialists",
    "Hypothesis", "ExplorationPath", "HypothesisGenerator",
    "HYPOTHESIS_PROPOSED", "HYPOTHESIS_CHALLENGED", "HYPOTHESIS_VERIFIED", "HYPOTHESIS_REJECTED",
    "Critique", "DebateRound", "DebateOrchestrator",
    "SEVERITY_LOW", "SEVERITY_MEDIUM", "SEVERITY_HIGH", "SEVERITY_CRITICAL",
    "EvidenceLineage", "LineageTracker",
    "ResearchResult", "ResearchRunner", "run_research",
]
