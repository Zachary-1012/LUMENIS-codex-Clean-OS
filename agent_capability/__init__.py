# -*- coding: utf-8 -*-
"""ZBC×OSAI Agent Runtime — Capability Router（ZBC PARTIAL 项补齐）。

统一工具路由层：将 ZBC 的 API 路由/Skill/Function 注册为 Agent 可调用的 Tool。
- Tool 注册：名称、描述、参数schema、权限要求、风险等级、是否需要人工审批
- Tool 选择：基于 goal+context+Skill Memory 选择最合适的 Tool
- Tool 执行：permission_gate → action_firewall → effect_fence → 执行 → evidence记录
- 复用 skill_execution_chain 的执行链路，不重写
- 首批注册 10-15 个核心 Tool

设计原则：
  - 不修改现有 skills_registry 表结构，通过 adapter 层增强
  - 新模块默认不启用，通过 Feature Flag AGENT_CAPABILITY_ENABLED 控制
  - 与 OSAI tools.py 的 ToolRegistry 通过 Contract 对齐
"""
from __future__ import annotations

import os

AGENT_CAPABILITY_ENABLED = os.environ.get("AGENT_CAPABILITY_ENABLED", "0") == "1"

__all__ = ["AGENT_CAPABILITY_ENABLED"]
