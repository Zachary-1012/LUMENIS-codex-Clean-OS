# -*- coding: utf-8 -*-
"""
Agent State Machine — Agent 实例级状态机
=========================================
状态：IDLE → PLANNING → EXECUTING → OBSERVING → REPLANNING → WAITING_APPROVAL → COMPLETED / FAILED / CANCELLED

设计原则：
  - 纯 Python 实现，无 DB 依赖（核心逻辑可单测）
  - 非法转换拒绝并返回错误，不静默通过
  - 状态持久化可选：通过 AgentStateStore 写入 runtime_guardian_workers 表或 agent_runtime_states 表
  - 线程安全：状态转换加锁
  - 复用 runtime_guardian.LifecycleState 的转换思路，但定义 Agent 专用状态集

与 OSAI Contract 对齐点（C-01 Agent Runtime Contract）：
  - status 字段：idle/planning/executing/observing/replanning/waiting_approval/completed/failed/cancelled
  - 事件：agent.started / agent.step_completed / agent.replanning / agent.completed / agent.failed / agent.cancelled
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentState(str, Enum):
    """Agent 运行状态枚举。"""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    OBSERVING = "observing"
    REPLANNING = "replanning"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """是否为终态。"""
        return self in (AgentState.COMPLETED, AgentState.FAILED, AgentState.CANCELLED)

    @property
    def is_active(self) -> bool:
        """是否为活跃态（非终态、非 IDLE）。"""
        return self in (
            AgentState.PLANNING, AgentState.EXECUTING, AgentState.OBSERVING,
            AgentState.REPLANNING, AgentState.WAITING_APPROVAL,
        )


# 合法状态转换表
VALID_TRANSITIONS: Dict[AgentState, set] = {
    AgentState.IDLE: {AgentState.PLANNING, AgentState.CANCELLED},
    AgentState.PLANNING: {
        AgentState.EXECUTING, AgentState.WAITING_APPROVAL,
        AgentState.FAILED, AgentState.CANCELLED,
    },
    AgentState.EXECUTING: {
        AgentState.OBSERVING, AgentState.WAITING_APPROVAL,
        AgentState.REPLANNING, AgentState.COMPLETED,
        AgentState.FAILED, AgentState.CANCELLED,
    },
    AgentState.OBSERVING: {
        AgentState.EXECUTING, AgentState.REPLANNING,
        AgentState.COMPLETED, AgentState.FAILED, AgentState.CANCELLED,
    },
    AgentState.REPLANNING: {
        AgentState.EXECUTING, AgentState.WAITING_APPROVAL,
        AgentState.FAILED, AgentState.CANCELLED,
    },
    AgentState.WAITING_APPROVAL: {
        AgentState.EXECUTING, AgentState.REPLANNING,
        AgentState.CANCELLED, AgentState.FAILED,
    },
    AgentState.COMPLETED: set(),       # 终态，不可转换
    AgentState.FAILED: set(),          # 终态，不可转换
    AgentState.CANCELLED: set(),       # 终态，不可转换
}


class StateTransitionError(Exception):
    """非法状态转换异常。"""

    def __init__(self, current: AgentState, target: AgentState, reason: str = ""):
        self.current = current
        self.target = target
        self.reason = reason
        super().__init__(
            f"Illegal state transition: {current.value} -> {target.value}"
            + (f" ({reason})" if reason else "")
        )


@dataclass
class StateTransitionRecord:
    """单次状态转换记录。"""
    from_state: str
    to_state: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentStateSnapshot:
    """Agent 状态快照（用于持久化和观察）。"""
    agent_id: str
    state: str
    goal: str = ""
    current_step: int = 0
    total_steps: int = 0
    replan_count: int = 0
    retry_count: int = 0
    elapsed_seconds: float = 0.0
    estimated_cost: float = 0.0
    error: Optional[str] = None
    transitions: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AgentStateMachine:
    """Agent 实例级状态机。

    用法：
        sm = AgentStateMachine(agent_id="agent_001", goal="分析今日舆情")
        sm.transition_to(AgentState.PLANNING, reason="开始规划")
        sm.transition_to(AgentState.EXECUTING)
        ...
        snapshot = sm.snapshot()
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        goal: str = "",
        initial_state: AgentState = AgentState.IDLE,
        persist_callback: Optional[callable] = None,
    ):
        """
        Args:
            agent_id: Agent 唯一标识，None 则自动生成
            goal: 自然语言目标
            initial_state: 初始状态
            persist_callback: 状态变更时的持久化回调 callback(snapshot) -> None
        """
        self.agent_id = agent_id or f"agent_{uuid.uuid4().hex[:12]}"
        self.goal = goal
        self._state = initial_state
        self._lock = threading.RLock()
        self._transitions: List[StateTransitionRecord] = []
        self._created_at = time.time()
        self._current_step = 0
        self._total_steps = 0
        self._replan_count = 0
        self._retry_count = 0
        self._estimated_cost = 0.0
        self._error: Optional[str] = None
        self._persist_callback = persist_callback

    @property
    def state(self) -> AgentState:
        with self._lock:
            return self._state

    @property
    def is_terminal(self) -> bool:
        return self.state.is_terminal

    @property
    def is_active(self) -> bool:
        return self.state.is_active

    def can_transition_to(self, target: AgentState) -> bool:
        """检查是否可以转换到目标状态。"""
        with self._lock:
            return target in VALID_TRANSITIONS.get(self._state, set())

    def transition_to(
        self,
        target: AgentState,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentState:
        """执行状态转换。非法转换抛出 StateTransitionError。

        Args:
            target: 目标状态
            reason: 转换原因
            metadata: 附加元数据

        Returns:
            转换后的新状态

        Raises:
            StateTransitionError: 非法转换
        """
        with self._lock:
            if target not in VALID_TRANSITIONS.get(self._state, set()):
                raise StateTransitionError(self._state, target, reason)

            old = self._state
            self._state = target
            record = StateTransitionRecord(
                from_state=old.value,
                to_state=target.value,
                reason=reason,
                metadata=metadata or {},
            )
            self._transitions.append(record)

            # 元数据更新
            if metadata:
                if "step" in metadata:
                    self._current_step = int(metadata["step"])
                if "total_steps" in metadata:
                    self._total_steps = int(metadata["total_steps"])
                if "replan_count" in metadata:
                    self._replan_count = int(metadata["replan_count"])
                if "retry_count" in metadata:
                    self._retry_count = int(metadata["retry_count"])
                if "cost" in metadata:
                    self._estimated_cost = float(metadata["cost"])
                if "error" in metadata:
                    self._error = metadata["error"]

            # 持久化回调
            if self._persist_callback:
                try:
                    self._persist_callback(self.snapshot())
                except Exception:
                    pass  # 持久化失败不阻断状态机

            return target

    def cancel(self, reason: str = "user_cancelled") -> AgentState:
        """取消 Agent（从任意非终态可取消）。"""
        with self._lock:
            if self._state.is_terminal:
                return self._state
            old = self._state
            self._state = AgentState.CANCELLED
            self._transitions.append(StateTransitionRecord(
                from_state=old.value, to_state=AgentState.CANCELLED.value,
                reason=reason,
            ))
            if self._persist_callback:
                try:
                    self._persist_callback(self.snapshot())
                except Exception:
                    pass
            return AgentState.CANCELLED

    def fail(self, error: str, reason: str = "execution_failed") -> AgentState:
        """标记失败（从任意非终态可失败）。"""
        with self._lock:
            if self._state.is_terminal:
                return self._state
            old = self._state
            self._state = AgentState.FAILED
            self._error = error
            self._transitions.append(StateTransitionRecord(
                from_state=old.value, to_state=AgentState.FAILED.value,
                reason=reason, metadata={"error": error},
            ))
            if self._persist_callback:
                try:
                    self._persist_callback(self.snapshot())
                except Exception:
                    pass
            return AgentState.FAILED

    def complete(self, reason: str = "goal_achieved") -> AgentState:
        """标记完成。"""
        return self.transition_to(AgentState.COMPLETED, reason=reason)

    def update_progress(
        self,
        current_step: Optional[int] = None,
        total_steps: Optional[int] = None,
        replan_count: Optional[int] = None,
        retry_count: Optional[int] = None,
        cost: Optional[float] = None,
    ) -> None:
        """更新进度元数据（不改变状态）。"""
        with self._lock:
            if current_step is not None:
                self._current_step = current_step
            if total_steps is not None:
                self._total_steps = total_steps
            if replan_count is not None:
                self._replan_count = replan_count
            if retry_count is not None:
                self._retry_count = retry_count
            if cost is not None:
                self._estimated_cost = cost

    def snapshot(self) -> AgentStateSnapshot:
        """获取当前状态快照。"""
        with self._lock:
            return AgentStateSnapshot(
                agent_id=self.agent_id,
                state=self._state.value,
                goal=self.goal,
                current_step=self._current_step,
                total_steps=self._total_steps,
                replan_count=self._replan_count,
                retry_count=self._retry_count,
                elapsed_seconds=round(time.time() - self._created_at, 3),
                estimated_cost=round(self._estimated_cost, 4),
                error=self._error,
                transitions=[asdict(t) for t in self._transitions[-50:]],  # 最近50条
            )

    def transition_history(self) -> List[Dict[str, Any]]:
        """获取完整转换历史。"""
        with self._lock:
            return [asdict(t) for t in self._transitions]

    def reset(self) -> None:
        """重置为 IDLE（仅测试用）。"""
        with self._lock:
            self._state = AgentState.IDLE
            self._transitions.clear()
            self._current_step = 0
            self._replan_count = 0
            self._retry_count = 0
            self._estimated_cost = 0.0
            self._error = None


# ──────────────────────────────────────────────────────────────
# 状态持久化（可选，写入 DB 时使用）
# ──────────────────────────────────────────────────────────────

class AgentStateStore:
    """Agent 状态持久化存储。

    优先复用 runtime_guardian_workers 表；如需独立表，执行 migrations/011_agent_runtime_states.sql。
    本类只定义接口和内存实现，DB 写入通过注入的 db_writer 回调完成。
    """

    def __init__(self, db_writer: Optional[callable] = None):
        """
        Args:
            db_writer: 写入回调 callback(snapshot: AgentStateSnapshot) -> None
                       None 则仅内存存储
        """
        self._memory: Dict[str, AgentStateSnapshot] = {}
        self._lock = threading.Lock()
        self._db_writer = db_writer

    def save(self, snapshot: AgentStateSnapshot) -> None:
        """保存状态快照。"""
        with self._lock:
            self._memory[snapshot.agent_id] = snapshot
        if self._db_writer:
            try:
                self._db_writer(snapshot)
            except Exception:
                pass  # DB 写入失败不阻断

    def load(self, agent_id: str) -> Optional[AgentStateSnapshot]:
        """加载状态快照。"""
        with self._lock:
            return self._memory.get(agent_id)

    def list_active(self) -> List[AgentStateSnapshot]:
        """列出所有活跃 Agent。"""
        with self._lock:
            return [
                s for s in self._memory.values()
                if s.state not in ("completed", "failed", "cancelled")
            ]

    def remove(self, agent_id: str) -> None:
        """移除状态记录。"""
        with self._lock:
            self._memory.pop(agent_id, None)
