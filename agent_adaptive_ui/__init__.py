# -*- coding: utf-8 -*-
"""
Agent Adaptive UI — 任务即界面（后端 API 部分）
================================================
根据当前 Goal / Agent Run / Evidence / Decision 动态生成最需要的操作面板、
数据卡片、证据视图和下一步动作的 API 数据。

前端已有 adaptive-motion.js 底座，本包提供后端数据。

设计原则：
  - 只读：不修改 agent_runtime / agent_memory / agent_capability 源码
  - 旁路：作为独立包接入，不改变现有主链路
  - 可解释：每个面板都有 source_run_id 和 evidence_refs 可追溯
  - 异常降级：路由失败返回 {error, panels: []}，不抛 500

集成点（只读，不修改）：
  - agent_runtime.loop.AgentResult / AgentLoop 状态结构
  - agent_runtime.evaluation.TrajectoryEvaluation
  - agent_runtime.durable_adapter.Checkpoint
"""
from __future__ import annotations

__version__ = "0.1.0"
__all__ = [
    "panel",
    "routes",
    "PanelType",
    "AdaptivePanel",
    "PanelComponent",
    "AdaptivePanelGenerator",
    "get_adaptive_panel",
    "adaptive_ui_bp",
]

from .panel import (
    PanelType,
    AdaptivePanel,
    PanelComponent,
    AdaptivePanelGenerator,
    get_adaptive_panel,
)
from .routes import adaptive_ui_bp
