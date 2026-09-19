# -*- coding: utf-8 -*-
"""
Agent Bridge — 计算与执行环境解耦
==================================
Agent 的 Reasoning / Context / Execution 不绑定单一运行环境。
支持 checkpoint / rehydrate / resume，与现有 durable_adapter.py 兼容。

保持 Identity / Memory / State / Evidence / Permission 连续。

设计原则：
  - 不修改 agent_runtime / agent_memory / agent_capability 源码
  - 与 agent_runtime.durable_adapter.Checkpoint 字段兼容（可互相转换）
  - 不绕过 Permission / Action Firewall / Effect Fence
  - 所有主动行为可解释、可追踪、可撤销
  - 每个 Agent Run 都可以暂停、恢复、回溯、审计

模块清单：
  - serializer    : RunBundle 序列化/反序列化/迁移
  - checkpoint    : BridgeCheckpoint + CheckpointStore + rehydrate/resume
  - env_registry  : ExecutionEnvironment + EnvironmentRegistry
"""
from __future__ import annotations

__version__ = "0.1.0"
__all__ = [
    "serializer",
    "checkpoint",
    "env_registry",
    "RunBundle",
    "serialize_run",
    "deserialize_run",
    "migrate_run",
    "BridgeCheckpoint",
    "CheckpointStore",
    "ExecutionEnvironment",
    "EnvironmentRegistry",
]

from .serializer import (
    RunBundle,
    serialize_run,
    deserialize_run,
    migrate_run,
)
from .checkpoint import (
    BridgeCheckpoint,
    CheckpointStore,
)
from .env_registry import (
    ExecutionEnvironment,
    EnvironmentRegistry,
)
