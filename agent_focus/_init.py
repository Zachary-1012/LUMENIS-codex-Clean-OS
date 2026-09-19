# -*- coding: utf-8 -*-
"""
Agent Focus — 保护用户注意力能力包
====================================
系统负责复杂过程，用户只负责目标、判断和关键授权。
默认隐藏低价值执行细节，仅在异常、决策点、审批点、结果和证据处打断用户。

三层通知机制：
  - SILENT_PROGRESS  : 静默进度（只写日志，不打扰用户）
  - IMPORTANT_SIGNAL : 重要信号（弹 toast，非阻塞）
  - HUMAN_DECISION   : 人工决策（弹 modal，阻塞等待用户输入）

模块清单：
  - notification : 核心通知模块（FocusProtector / NotificationRouter）
  - policy       : 通知策略（FocusPolicy / default_policy / load_policy）

设计原则：
  - 默认抑制低价值通知，保护用户注意力
  - HUMAN_DECISION 级别必须通知，不可被抑制
  - 频率控制防止通知轰炸
  - 静默期内仅 HUMAN_DECISION 可穿透
  - 不修改 agent_runtime / agent_memory / agent_capability 源码

Feature Flag：
  AGENT_FOCUS_ENABLED=1 时启用；默认关闭，不影响现有功能。
"""
from __future__ import annotations

import os

AGENT_FOCUS_ENABLED = os.environ.get("AGENT_FOCUS_ENABLED", "0") == "1"

__version__ = "0.1.0"
__all__ = [
    "AGENT_FOCUS_ENABLED",
    "notification",
    "policy",
]
