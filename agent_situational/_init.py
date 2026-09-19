# -*- coding: utf-8 -*-
"""
ZBC × OSAI Agent Situational Awareness — 情境感知包
======================================================
Context → Situation → Intent → Action 推理链。

Agent 不只读取用户 Prompt，还实时理解当前页面、用户操作模块、
任务阶段、系统状态、历史上下文、风险状态、可用能力。

模块清单：
  - situation : 核心模块 — Situation dataclass / get_situation() / SituationAnalyzer / intent_from_situation()
  - adapters  : 集成适配器 — from_agent_loop() / from_observation() / merge_contexts()

设计原则：
  - 规则驱动为默认，AI 辅助为可插拔可选（不依赖外部 API）
  - 所有推断可解释、可追溯（evidence 字段）
  - 只读感知，不修改任何系统状态
  - 与 agent_runtime.observation / loop / planner 兼容（import 或 dict 兼容）
  - 不修改现有 agent_runtime 源码，仅 import 或 dict 兼容

Feature Flag：
  AGENT_SITUATIONAL_ENABLED=1 时启用；默认关闭，不影响现有功能。
"""
from __future__ import annotations

import os

# Feature Flag：默认不启用，不影响现有功能
AGENT_SITUATIONAL_ENABLED = os.environ.get("AGENT_SITUATIONAL_ENABLED", "0") == "1"

__version__ = "0.1.0"

from .situation import (
    Situation,
    SituationAnalyzer,
    get_situation,
    intent_from_situation,
    RISK_LOW,
    RISK_MEDIUM,
    RISK_HIGH,
    RISK_CRITICAL,
    SYS_HEALTHY,
    SYS_DEGRADED,
    SYS_UNAVAILABLE,
    SYS_UNKNOWN,
    PHASE_IDLE,
    PHASE_PLANNING,
    PHASE_EXECUTING,
    PHASE_OBSERVING,
    PHASE_REPLANNING,
    PHASE_WAITING_APPROVAL,
    PHASE_COMPLETED,
    PHASE_FAILED,
    INTENT_MONITOR,
    INTENT_ANALYZE,
    INTENT_REPORT,
    INTENT_COLLECT,
    INTENT_CONFIGURE,
    INTENT_TROUBLESHOOT,
    INTENT_QUERY,
    INTENT_UNKNOWN,
    ACTION_CONTINUE,
    ACTION_PAUSE,
    ACTION_REPLAN,
    ACTION_ESCALATE,
    ACTION_NOTIFY,
    ACTION_SWITCH_MODULE,
    ACTION_SEEK_APPROVAL,
    ACTION_NOOP,
)

from .adapters import (
    from_agent_loop,
    from_observation,
    merge_contexts,
)

__all__ = [
    "AGENT_SITUATIONAL_ENABLED",
    # core
    "Situation",
    "SituationAnalyzer",
    "get_situation",
    "intent_from_situation",
    # adapters
    "from_agent_loop",
    "from_observation",
    "merge_contexts",
    # constants — risk
    "RISK_LOW",
    "RISK_MEDIUM",
    "RISK_HIGH",
    "RISK_CRITICAL",
    # constants — system
    "SYS_HEALTHY",
    "SYS_DEGRADED",
    "SYS_UNAVAILABLE",
    "SYS_UNKNOWN",
    # constants — phase
    "PHASE_IDLE",
    "PHASE_PLANNING",
    "PHASE_EXECUTING",
    "PHASE_OBSERVING",
    "PHASE_REPLANNING",
    "PHASE_WAITING_APPROVAL",
    "PHASE_COMPLETED",
    "PHASE_FAILED",
    # constants — intent
    "INTENT_MONITOR",
    "INTENT_ANALYZE",
    "INTENT_REPORT",
    "INTENT_COLLECT",
    "INTENT_CONFIGURE",
    "INTENT_TROUBLESHOOT",
    "INTENT_QUERY",
    "INTENT_UNKNOWN",
    # constants — action
    "ACTION_CONTINUE",
    "ACTION_PAUSE",
    "ACTION_REPLAN",
    "ACTION_ESCALATE",
    "ACTION_NOTIFY",
    "ACTION_SWITCH_MODULE",
    "ACTION_SEEK_APPROVAL",
    "ACTION_NOOP",
]
