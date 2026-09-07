# -*- coding: utf-8 -*-
"""
ZBC × OSAI Agent Runtime Core
==============================
Goal-driven Agent Runtime 核心执行层。

模块清单：
  - state_machine : Agent 实例级状态机（IDLE→PLANNING→EXECUTING→OBSERVING→REPLANNING→WAITING_APPROVAL→COMPLETED/FAILED/CANCELLED）
  - observation   : 观察/感知层（ZBC MISSING 项补齐）— 感知 DB 状态、API 可用性、工具可用性、前一步执行结果
  - planner       : 基于 OSAI Contract 的规划器 — 调用智谱 GLM 将 goal 分解为步骤列表
  - replanner     : 重规划器（ZBC MISSING 项补齐）— 基于 observation 调整策略，非同参数 retry
  - evaluation    : 轨迹评估（ZBC MISSING 项补齐）— 步骤效率/工具选择/目标达成度/成本
  - durable_adapter: Durable Execution 适配器 — 复用 ai_task_engine 的 checkpoint/retry/recover/cancel
  - loop          : Agent Loop 主循环 — Plan→Execute→Observe→(Replan)→完成/失败/取消

复用原则（禁止重写）：
  - permission_gate        : from permission_gate import get_permission_gate, OperationType, RiskLevel
  - ai_gateway (intelligence): from intelligence import _chat as ai_chat  (智谱 GLM glm-5.3 / glm-4.5-air)
  - ai_task_engine         : from ai_task_engine import get_task_engine  (checkpoint/retry/recover/cancel)
  - runtime_guardian       : from runtime_guardian import CircuitBreaker  (熔断)
  - skill_execution_chain  : from skill_execution_chain import action_firewall, effect_fence, SkillExecutionContext, ActionType
  - evidence_chain         : from evidence_chain import EvidenceStore     (证据记录)

Feature Flag：
  AGENT_RUNTIME_ENABLED=1 时启用；默认关闭，不影响现有功能。
  新模块不修改任何现有生产代码、不修改 DB schema（迁移脚本见 migrations/011_agent_runtime_states.sql，不自动执行）。

安全约束：
  - COMMIT/PUSH/Production Write 默认 DENY（复用 permission_gate fail-closed）
  - AI 输出不直接成为 Production Truth，需人工确认或规则验证
  - 官方账号一律只读（AGENTS.md §7）
"""
from __future__ import annotations

import os

# Feature Flag：默认不启用，不影响现有功能
AGENT_RUNTIME_ENABLED = os.environ.get("AGENT_RUNTIME_ENABLED", "0") == "1"

__version__ = "0.1.0"
__all__ = [
    "AGENT_RUNTIME_ENABLED",
    "state_machine",
    "observation",
    "planner",
    "replanner",
    "evaluation",
    "durable_adapter",
    "loop",
]
