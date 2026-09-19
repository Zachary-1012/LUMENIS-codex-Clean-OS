# -*- coding: utf-8 -*-
"""
Agent Proactive — 主动式协助能力包
====================================
当系统发现异常、趋势变化、任务阻塞、风险升级、数据缺失或更优路径时，
生成 Signal → Explanation → Suggested Action → Approval。

默认建议，不默认执行：所有 SuggestedAction 的 action_type 默认 require_approval，
不得默认 auto_execute。

模块清单：
  - detector   : 信号检测器（纯规则，不依赖外部 AI API）
  - suggestion : 建议生成与审批流程状态机
  - routes     : Flask 蓝图（可选，GET signals / POST approve）

设计原则：
  - 纯规则检测，可解释、可追踪、可撤销
  - 不修改 agent_runtime / agent_memory / agent_capability 源码
  - 不绕过 Permission / Action Firewall / Effect Fence
  - 不改变 ZBC Production Truth
  - context 输入用 .get() 安全访问，缺失字段不抛异常

Feature Flag：
  AGENT_PROACTIVE_ENABLED=1 时启用；默认关闭，不影响现有功能。
"""
from __future__ import annotations

import os

AGENT_PROACTIVE_ENABLED = os.environ.get("AGENT_PROACTIVE_ENABLED", "0") == "1"

__version__ = "0.1.0"
__all__ = [
    "AGENT_PROACTIVE_ENABLED",
    "detector",
    "suggestion",
    "routes",
]
