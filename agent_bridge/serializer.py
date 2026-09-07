# -*- coding: utf-8 -*-
"""
Run Bundle Serializer — 运行状态序列化与迁移
============================================
将 Agent Loop 运行状态序列化为可迁移的 RunBundle，支持：
  - serialize_run   : 运行状态 → RunBundle
  - deserialize_run : RunBundle → 运行状态 dict
  - migrate_run     : 迁移到目标环境，更新 env 标记，保留所有状态
  - to_json / from_json : JSON 序列化

保持 Identity / Memory / State / Evidence / Permission 连续。

与 agent_runtime.durable_adapter.Checkpoint 兼容：
  RunBundle 可从 Checkpoint.state / context / plan_snapshot 构建，
  也可导出为 Checkpoint 兼容的 dict。
"""
from __future__ import annotations

import copy
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────────────────────
# RunBundle 数据类
# ──────────────────────────────────────────────────────────────

@dataclass
class RunBundle:
    """可迁移的运行状态包。

    包含完整的 Identity / Memory / State / Evidence / Permission 上下文，
    支持在不同执行环境之间迁移而不丢失任何状态。
    """
    bundle_id: str = field(
        default_factory=lambda: f"bundle_{uuid.uuid4().hex[:16]}")
    agent_id: str = ""
    task_id: str = ""
    identity: Dict[str, Any] = field(default_factory=dict)
    memory_snapshot: Dict[str, Any] = field(default_factory=dict)
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    evidence_chain: List[Dict[str, Any]] = field(default_factory=list)
    permission_context: Dict[str, Any] = field(default_factory=dict)
    source_env: str = "local"
    target_env: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（深拷贝，避免外部修改影响内部状态）。"""
        return copy.deepcopy(asdict(self))

    def to_json(self, indent: Optional[int] = None) -> str:
        """序列化为 JSON 字符串。"""
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            default=str,
            indent=indent,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "RunBundle":
        """从 JSON 字符串反序列化。"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunBundle":
        """从字典构建 RunBundle（忽略未知字段，保持向后兼容）。"""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    def to_durable_checkpoint_dict(self) -> Dict[str, Any]:
        """导出为 agent_runtime.durable_adapter.Checkpoint 兼容的 dict。

        字段对齐：checkpoint_id, agent_id, task_id, step_index, state,
                  plan_snapshot, context, created_at, metadata
        """
        state = self.state_snapshot or {}
        return {
            "checkpoint_id": self.bundle_id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "step_index": int(state.get("current_step", state.get("step_index", 0))),
            "state": state.get("status", state.get("state", "")),
            "plan_snapshot": self.memory_snapshot.get("plan", {}),
            "context": {
                "identity": self.identity,
                "memory": self.memory_snapshot,
                "state": self.state_snapshot,
                "evidence": self.evidence_chain,
                "permission": self.permission_context,
                "source_env": self.source_env,
                "target_env": self.target_env,
                "bundle_version": self.version,
            },
            "created_at": self.created_at,
            "metadata": {
                "bundle_id": self.bundle_id,
                "source_env": self.source_env,
                "target_env": self.target_env,
                "evidence_count": len(self.evidence_chain),
            },
        }

    @classmethod
    def from_durable_checkpoint(cls, checkpoint: Any) -> "RunBundle":
        """从 agent_runtime.durable_adapter.Checkpoint（或其 dict）构建 RunBundle。

        Args:
            checkpoint: Checkpoint 实例或包含相同字段的 dict
        """
        if hasattr(checkpoint, "to_dict"):
            cp = checkpoint.to_dict()
        elif isinstance(checkpoint, dict):
            cp = checkpoint
        else:
            raise TypeError(f"unsupported checkpoint type: {type(checkpoint)}")

        context = cp.get("context", {}) or {}
        return cls(
            bundle_id=cp.get("checkpoint_id", f"bundle_{uuid.uuid4().hex[:16]}"),
            agent_id=cp.get("agent_id", ""),
            task_id=cp.get("task_id", ""),
            identity=context.get("identity", {}),
            memory_snapshot=context.get("memory", context.get("plan_snapshot", {})),
            state_snapshot={
                "status": cp.get("state", ""),
                "step_index": cp.get("step_index", 0),
                **context.get("state", {}),
            },
            evidence_chain=context.get("evidence", []),
            permission_context=context.get("permission", {}),
            source_env=context.get("source_env", "unknown"),
            target_env=context.get("target_env", ""),
            created_at=cp.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


# ──────────────────────────────────────────────────────────────
# 序列化函数
# ──────────────────────────────────────────────────────────────

def serialize_run(
    loop_state: Dict[str, Any],
    memory: Optional[Dict[str, Any]] = None,
    evidence: Optional[List[Dict[str, Any]]] = None,
    agent_id: str = "",
    task_id: str = "",
    identity: Optional[Dict[str, Any]] = None,
    permission_context: Optional[Dict[str, Any]] = None,
    source_env: str = "local",
) -> RunBundle:
    """将运行状态序列化为可迁移 bundle。

    Args:
        loop_state: Agent Loop 状态字典（AgentResult 或运行时状态）
        memory: 内存快照（None 则从 loop_state 提取）
        evidence: 证据链（None 则从 loop_state 提取）
        agent_id: Agent ID（空则从 loop_state 提取）
        task_id: 任务 ID（空则从 loop_state 提取）
        identity: 身份上下文
        permission_context: 权限上下文
        source_env: 源环境标识

    Returns:
        RunBundle 包含完整运行状态
    """
    loop_state = loop_state or {}
    memory = memory or loop_state.get("memory", {}) or {}
    evidence = evidence or loop_state.get("evidence", []) or []
    identity = identity or loop_state.get("identity", {}) or {}
    permission_context = permission_context or loop_state.get("permission", {}) or {}

    return RunBundle(
        agent_id=agent_id or loop_state.get("agent_id", ""),
        task_id=task_id or loop_state.get("task_id", ""),
        identity=copy.deepcopy(identity),
        memory_snapshot=copy.deepcopy(memory),
        state_snapshot=copy.deepcopy(loop_state),
        evidence_chain=copy.deepcopy(evidence),
        permission_context=copy.deepcopy(permission_context),
        source_env=source_env,
    )


def deserialize_run(bundle: RunBundle) -> Dict[str, Any]:
    """反序列化为运行状态 dict。

    Args:
        bundle: RunBundle 实例

    Returns:
        运行状态字典，包含 state / memory / evidence / identity / permission
    """
    state = copy.deepcopy(bundle.state_snapshot)
    # 确保关键字段存在
    state.setdefault("agent_id", bundle.agent_id)
    state.setdefault("task_id", bundle.task_id)
    state["_bundle"] = {
        "bundle_id": bundle.bundle_id,
        "source_env": bundle.source_env,
        "target_env": bundle.target_env,
        "created_at": bundle.created_at,
        "version": bundle.version,
    }
    return {
        "state": state,
        "memory": copy.deepcopy(bundle.memory_snapshot),
        "evidence": copy.deepcopy(bundle.evidence_chain),
        "identity": copy.deepcopy(bundle.identity),
        "permission": copy.deepcopy(bundle.permission_context),
    }


def migrate_run(bundle: RunBundle, target_env: str) -> RunBundle:
    """迁移到目标环境，更新 env 标记，保留所有状态。

    Args:
        bundle: 原始 RunBundle
        target_env: 目标环境标识（local / remote / hybrid / ...）

    Returns:
        新的 RunBundle，source_env 更新为原 target_env，target_env 更新为目标
    """
    new_bundle = RunBundle(
        bundle_id=f"bundle_{uuid.uuid4().hex[:16]}",
        agent_id=bundle.agent_id,
        task_id=bundle.task_id,
        identity=copy.deepcopy(bundle.identity),
        memory_snapshot=copy.deepcopy(bundle.memory_snapshot),
        state_snapshot=copy.deepcopy(bundle.state_snapshot),
        evidence_chain=copy.deepcopy(bundle.evidence_chain),
        permission_context=copy.deepcopy(bundle.permission_context),
        source_env=bundle.target_env or bundle.source_env,
        target_env=target_env,
        version=bundle.version,
    )
    # 记录迁移历史
    if "migration_history" not in new_bundle.state_snapshot:
        new_bundle.state_snapshot["migration_history"] = []
    new_bundle.state_snapshot["migration_history"].append({
        "from_bundle": bundle.bundle_id,
        "from_env": bundle.source_env,
        "to_env": target_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return new_bundle
