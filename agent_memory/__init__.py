# -*- coding: utf-8 -*-
"""LUMENIS Agent Runtime — 分层 Memory Layer（ZBC PARTIAL 项补齐）。

六层记忆：
  Working  → 当前任务上下文（内存 + ai_task_step）
  Task     → 任务级记忆（ai_task + ai_task_evidence）
  Episodic → 情景记忆（ai_task_evidence + note_review_history）
  Semantic → 语义记忆（intelligence_assets + rule_version_registry）
  Skill    → 技能记忆（skills_registry + skill_executions）
  Learning → 由 lumenis.shared.learning 唯一拥有；Agent Memory 仅提供通用记忆基础设施

设计原则：
  - 优先复用现有表，不修改生产 DB schema
  - 新表只写迁移脚本到 migrations/，不执行
  - 统一 Memory 接口（store/retrieve/query/forget/TTL）
  - 默认不启用，通过 Feature Flag AGENT_MEMORY_ENABLED 控制
  - 与 OSAI memory_lifecycle.py 通过 Contract 对齐，不 import OSAI 代码
"""
from __future__ import annotations

import os

# Feature Flag：默认关闭，需显式启用
AGENT_MEMORY_ENABLED = os.environ.get("AGENT_MEMORY_ENABLED", "0") == "1"

# 各层记忆的最大保留条数（内存层）
DEFAULT_WORKING_MAX_STEPS = 50
DEFAULT_EPISODIC_MAX_CASES = 500
DEFAULT_SEMANTIC_MAX_ITEMS = 1000

# 记忆层标识（与 OSAI C-06 Memory Contract 对齐）
MEMORY_LAYER_WORKING = "working"
MEMORY_LAYER_TASK = "task"
MEMORY_LAYER_EPISODIC = "episodic"
MEMORY_LAYER_SEMANTIC = "semantic"
MEMORY_LAYER_SKILL = "skill"
MEMORY_LAYER_LEARNING = "learning"

ALL_MEMORY_LAYERS = (
    MEMORY_LAYER_WORKING, MEMORY_LAYER_TASK, MEMORY_LAYER_EPISODIC,
    MEMORY_LAYER_SEMANTIC, MEMORY_LAYER_SKILL, MEMORY_LAYER_LEARNING,
)

__all__ = [
    "AGENT_MEMORY_ENABLED",
    "DEFAULT_WORKING_MAX_STEPS",
    "DEFAULT_EPISODIC_MAX_CASES",
    "DEFAULT_SEMANTIC_MAX_ITEMS",
    "MEMORY_LAYER_WORKING",
    "MEMORY_LAYER_TASK",
    "MEMORY_LAYER_EPISODIC",
    "MEMORY_LAYER_SEMANTIC",
    "MEMORY_LAYER_SKILL",
    "MEMORY_LAYER_LEARNING",
    "ALL_MEMORY_LAYERS",
]
