# -*- coding: utf-8 -*-
"""
Bridge Checkpoint — 检查点管理
==============================
与 agent_runtime.durable_adapter.Checkpoint 字段兼容：
  checkpoint_id, agent_id, task_id, step_index, state,
  plan_snapshot, context, created_at, metadata

支持：
  - BridgeCheckpoint : 检查点数据类（字段对齐 Durable Checkpoint）
  - CheckpointStore  : save / load / list 检查点，支持内存和文件两种 backend
  - rehydrate        : 从检查点恢复运行状态
  - resume           : 恢复并继续（合并新上下文）

设计原则：
  - 不修改 agent_runtime.durable_adapter 源码
  - 字段完全对齐，可互相转换
  - 所有状态可追溯、可恢复
  - 不绕过 Permission / Action Firewall / Effect Fence
"""
from __future__ import annotations

import copy
import json
import os
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────────────────────
# BridgeCheckpoint 数据类
# ──────────────────────────────────────────────────────────────

@dataclass
class BridgeCheckpoint:
    """检查点数据。

    与 agent_runtime.durable_adapter.Checkpoint 字段完全对齐，
    可互相转换（to_durable_checkpoint / from_durable_checkpoint）。
    """
    checkpoint_id: str = field(
        default_factory=lambda: f"bcp_{uuid.uuid4().hex[:12]}")
    agent_id: str = ""
    task_id: str = ""
    step_index: int = 0
    state: str = ""
    plan_snapshot: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(asdict(self))

    def to_json(self, indent: Optional[int] = None) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "BridgeCheckpoint":
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BridgeCheckpoint":
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    # ── 与 Durable Checkpoint 兼容 ──

    def to_durable_checkpoint_dict(self) -> Dict[str, Any]:
        """转换为 agent_runtime.durable_adapter.Checkpoint 兼容的 dict。"""
        return self.to_dict()

    @classmethod
    def from_durable_checkpoint(cls, checkpoint: Any) -> "BridgeCheckpoint":
        """从 agent_runtime.durable_adapter.Checkpoint（或其 dict）构建。"""
        if hasattr(checkpoint, "to_dict"):
            cp = checkpoint.to_dict()
        elif isinstance(checkpoint, dict):
            cp = checkpoint
        else:
            raise TypeError(f"unsupported checkpoint type: {type(checkpoint)}")
        return cls.from_dict(cp)


# ──────────────────────────────────────────────────────────────
# CheckpointStore
# ──────────────────────────────────────────────────────────────

class CheckpointStore:
    """检查点存储，支持内存和文件两种 backend。

    用法：
        # 内存 backend
        store = CheckpointStore(backend="memory")
        cp = BridgeCheckpoint(agent_id="a1", task_id="t1", state="running")
        store.save(cp)
        loaded = store.load(cp.checkpoint_id)

        # 文件 backend
        store = CheckpointStore(backend="file", directory="/tmp/checkpoints")
    """

    def __init__(
        self,
        backend: str = "memory",
        directory: Optional[str] = None,
    ):
        """
        Args:
            backend: "memory" 或 "file"
            directory: 文件 backend 的存储目录（仅 backend="file" 时需要）
        """
        if backend not in ("memory", "file"):
            raise ValueError(f"unsupported backend: {backend}, use 'memory' or 'file'")
        self.backend = backend
        self.directory = directory
        self._lock = threading.RLock()
        self._memory: Dict[str, BridgeCheckpoint] = {}

        if backend == "file":
            if not directory:
                raise ValueError("directory is required for file backend")
            os.makedirs(directory, exist_ok=True)

    def save(self, checkpoint: BridgeCheckpoint) -> str:
        """保存检查点，返回 checkpoint_id。"""
        with self._lock:
            if self.backend == "memory":
                self._memory[checkpoint.checkpoint_id] = checkpoint
            else:
                path = self._file_path(checkpoint.checkpoint_id)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(checkpoint.to_json(indent=2))
        return checkpoint.checkpoint_id

    def load(self, checkpoint_id: str) -> Optional[BridgeCheckpoint]:
        """加载检查点，不存在返回 None。"""
        with self._lock:
            if self.backend == "memory":
                cp = self._memory.get(checkpoint_id)
                return copy.deepcopy(cp) if cp else None
            else:
                path = self._file_path(checkpoint_id)
                if not os.path.exists(path):
                    return None
                with open(path, "r", encoding="utf-8") as f:
                    return BridgeCheckpoint.from_json(f.read())

    def list(
        self,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[BridgeCheckpoint]:
        """列出检查点，可按 agent_id / task_id 过滤。"""
        with self._lock:
            if self.backend == "memory":
                checkpoints = list(self._memory.values())
            else:
                checkpoints = []
                if os.path.exists(self.directory):
                    for fname in os.listdir(self.directory):
                        if fname.endswith(".json"):
                            try:
                                with open(os.path.join(self.directory, fname), "r", encoding="utf-8") as f:
                                    checkpoints.append(BridgeCheckpoint.from_json(f.read()))
                            except Exception:
                                continue

            if agent_id:
                checkpoints = [c for c in checkpoints if c.agent_id == agent_id]
            if task_id:
                checkpoints = [c for c in checkpoints if c.task_id == task_id]

            checkpoints.sort(key=lambda c: c.created_at)
            return [copy.deepcopy(c) for c in checkpoints]

    def delete(self, checkpoint_id: str) -> bool:
        """删除检查点，返回是否成功。"""
        with self._lock:
            if self.backend == "memory":
                return self._memory.pop(checkpoint_id, None) is not None
            else:
                path = self._file_path(checkpoint_id)
                if os.path.exists(path):
                    os.remove(path)
                    return True
                return False

    def clear(self) -> None:
        """清除所有检查点（测试用）。"""
        with self._lock:
            if self.backend == "memory":
                self._memory.clear()
            else:
                if os.path.exists(self.directory):
                    for fname in os.listdir(self.directory):
                        if fname.endswith(".json"):
                            os.remove(os.path.join(self.directory, fname))

    def _file_path(self, checkpoint_id: str) -> str:
        """获取检查点文件路径。"""
        safe_id = "".join(c for c in checkpoint_id if c.isalnum() or c in ("_", "-"))
        return os.path.join(self.directory, f"{safe_id}.json")


# ──────────────────────────────────────────────────────────────
# rehydrate / resume 函数
# ──────────────────────────────────────────────────────────────

def rehydrate(
    checkpoint_id: str,
    store: Optional[CheckpointStore] = None,
) -> Dict[str, Any]:
    """从检查点恢复运行状态。

    Args:
        checkpoint_id: 检查点 ID
        store: CheckpointStore 实例（None 则使用默认内存 store）

    Returns:
        恢复的运行状态字典：
        {
            "checkpoint_id": str,
            "agent_id": str,
            "task_id": str,
            "step_index": int,
            "state": str,
            "plan_snapshot": dict,
            "context": dict,
            "restored_at": str,
            "status": "restored",
        }

    Raises:
        KeyError: 检查点不存在时
    """
    if store is None:
        store = _default_store
    cp = store.load(checkpoint_id)
    if cp is None:
        raise KeyError(f"checkpoint not found: {checkpoint_id}")

    return {
        "checkpoint_id": cp.checkpoint_id,
        "agent_id": cp.agent_id,
        "task_id": cp.task_id,
        "step_index": cp.step_index,
        "state": cp.state,
        "plan_snapshot": copy.deepcopy(cp.plan_snapshot),
        "context": copy.deepcopy(cp.context),
        "metadata": copy.deepcopy(cp.metadata),
        "restored_at": datetime.now(timezone.utc).isoformat(),
        "status": "restored",
    }


def resume(
    checkpoint_id: str,
    new_context: Optional[Dict[str, Any]] = None,
    store: Optional[CheckpointStore] = None,
) -> Dict[str, Any]:
    """恢复并继续：从检查点恢复状态，合并新上下文。

    Args:
        checkpoint_id: 检查点 ID
        new_context: 新上下文（合并到恢复的 context 中，新值覆盖旧值）
        store: CheckpointStore 实例

    Returns:
        恢复后的运行状态字典，包含合并后的 context 和新的 step_index
    """
    state = rehydrate(checkpoint_id, store=store)

    if new_context:
        merged_context = copy.deepcopy(state.get("context", {}))
        merged_context.update(copy.deepcopy(new_context))
        state["context"] = merged_context

    state["resumed_at"] = datetime.now(timezone.utc).isoformat()
    state["status"] = "resumed"
    state["next_step_index"] = state["step_index"] + 1

    # 保存恢复后的检查点（用于审计和回溯）
    if store is not None:
        resume_cp = BridgeCheckpoint(
            agent_id=state["agent_id"],
            task_id=state["task_id"],
            step_index=state["next_step_index"],
            state="resumed",
            plan_snapshot=state.get("plan_snapshot", {}),
            context=state["context"],
            metadata={
                "resumed_from": checkpoint_id,
                "resumed_at": state["resumed_at"],
            },
        )
        store.save(resume_cp)
        state["resume_checkpoint_id"] = resume_cp.checkpoint_id

    return state


# 默认内存 store（模块级单例）
_default_store = CheckpointStore(backend="memory")
