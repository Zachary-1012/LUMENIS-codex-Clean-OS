# -*- coding: utf-8 -*-
"""
ZBC × OSAI Agent Smart Tool — 智能工具化包
==============================================
将复杂 Tool 包装成自解释、自校验、自恢复的小型执行单元。

核心能力：
  - self_describe()  : 自解释，返回 ToolDefinition 兼容 dict
  - validate_params() : 自校验，自动纠错可纠错参数
  - execute()         : 执行 + 异常捕获 + 自动重试
  - recover()         : 自恢复策略

模块清单：
  - base     : 核心模块 — SmartTool / wrap_tool / ToolExecutionResult / SmartToolRegistry / from_tool_definition
  - recovery : 恢复策略 — RetryPolicy / ParamCorrector / DEFAULT_RETRY_POLICY / NO_RETRY_POLICY

设计原则：
  - 与现有 Skill → Tool → Firewall → Effect Fence 兼容
  - 不绕过 Permission / Action Firewall / Effect Fence（存在则调用，不存在则仅记录）
  - 不改变 ZBC Production Truth
  - 所有行为可解释、可追踪（每个执行结果带 evidence 字段）
  - 不写任何 API Key 到代码
  - 与 agent_capability.router.ToolDefinition 兼容（可从 ToolDefinition 构建 SmartTool）
  - 不修改现有 agent_capability 源码，仅 import 或 dict 兼容

Feature Flag：
  AGENT_SMART_TOOL_ENABLED=1 时启用；默认关闭，不影响现有功能。
"""
from __future__ import annotations

import os

# Feature Flag：默认不启用，不影响现有功能
AGENT_SMART_TOOL_ENABLED = os.environ.get("AGENT_SMART_TOOL_ENABLED", "0") == "1"

__version__ = "0.1.0"

from .base import (
    SmartTool,
    wrap_tool,
    ToolExecutionResult,
    SmartToolRegistry,
    from_tool_definition,
)

from .recovery import (
    RetryPolicy,
    ParamCorrector,
    DEFAULT_RETRY_POLICY,
    NO_RETRY_POLICY,
)

__all__ = [
    "AGENT_SMART_TOOL_ENABLED",
    # core
    "SmartTool",
    "wrap_tool",
    "ToolExecutionResult",
    "SmartToolRegistry",
    "from_tool_definition",
    # recovery
    "RetryPolicy",
    "ParamCorrector",
    "DEFAULT_RETRY_POLICY",
    "NO_RETRY_POLICY",
]
