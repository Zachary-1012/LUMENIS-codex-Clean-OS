# -*- coding: utf-8 -*-
"""Working Memory（工作记忆）— 当前任务上下文、最近N步执行记录、中间结果。

存储：内存 + ai_task_step 表（复用，不修改 schema）
生命周期：任务结束后归档到 Episodic Memory
与 OSAI memory_lifecycle.py 的 working dict 对齐。
"""
from __future__ import annotations

import json
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseMemoryLayer, MemoryRecord, get_db_connection, _utc_now_iso


class WorkingMemory(BaseMemoryLayer):
    """工作记忆：当前任务的短期上下文。

    - 内存中维护最近 N 步执行记录（deque）
    - 关键步骤持久化到 ai_task_step 表（复用现有表）
    - 任务结束后调用 archive_to_episodic() 归档
    """

    LAYER_NAME = "working"

    def __init__(self, db_path: Optional[str] = None, enabled: bool = False,
                 max_steps: int = 50):
        super().__init__(db_path=db_path, enabled=enabled)
        self.max_steps = max_steps
        self._steps: deque = deque(maxlen=max_steps)
        self._current_task_id: Optional[str] = None
        self._context: Dict[str, Any] = {}

    # ── 任务上下文 ───────────────────────────────────────────────

    def begin_task(self, task_id: str, goal: str,
                   context: Optional[Dict[str, Any]] = None) -> None:
        """开始新任务，初始化工作记忆。"""
        if not self.enabled:
            return
        self._current_task_id = task_id
        self._context = {
            "task_id": task_id,
            "goal": goal,
            "started_at": _utc_now_iso(),
            "step_count": 0,
            **(context or {}),
        }
        self._steps.clear()
        self.store(f"task:{task_id}:context", self._context,
                   metadata={"type": "task_context"}, ttl_seconds=3600)

    def end_task(self, result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """结束任务，返回归档摘要（不自动归档，由调用方决定是否归档到 Episodic）。"""
        if not self.enabled:
            return {}
        summary = {
            "task_id": self._current_task_id,
            "goal": self._context.get("goal", ""),
            "step_count": len(self._steps),
            "started_at": self._context.get("started_at"),
            "finished_at": _utc_now_iso(),
            "result": result or {},
        }
        self._current_task_id = None
        self._context = {}
        self._steps.clear()
        return summary

    # ── 步骤记录 ─────────────────────────────────────────────────

    def add_step(self, action: str, input_data: Optional[Dict[str, Any]] = None,
                 output_data: Optional[Dict[str, Any]] = None,
                 status: str = "completed",
                 error: Optional[str] = None,
                 persist: bool = True) -> Dict[str, Any]:
        """记录一个执行步骤。"""
        if not self.enabled:
            return {}
        step = {
            "step_id": uuid.uuid4().hex[:16],
            "task_id": self._current_task_id,
            "seq": len(self._steps) + 1,
            "action": action,
            "input": input_data or {},
            "output": output_data or {},
            "status": status,
            "error": error,
            "timestamp": _utc_now_iso(),
        }
        self._steps.append(step)
        if self._context:
            self._context["step_count"] = len(self._steps)

        # 持久化到 ai_task_step 表（复用）
        if persist and self.db_path and self._current_task_id:
            self._persist_step(step)

        return step

    def get_recent_steps(self, n: int = 10) -> List[Dict[str, Any]]:
        """获取最近 N 步。"""
        return list(self._steps)[-n:]

    def get_context(self) -> Dict[str, Any]:
        return dict(self._context)

    # ── 归档到 Episodic ──────────────────────────────────────────

    def archive_to_episodic(self, episodic_memory) -> Optional[str]:
        """将当前任务的工作记忆归档到情景记忆。

        Args:
            episodic_memory: EpisodicMemory 实例
        Returns:
            归档后的 episodic record_id，失败返回 None
        """
        if not self.enabled or not self._current_task_id:
            return None
        case_data = {
            "task_id": self._current_task_id,
            "goal": self._context.get("goal", ""),
            "steps": list(self._steps),
            "step_count": len(self._steps),
            "started_at": self._context.get("started_at"),
            "archived_at": _utc_now_iso(),
        }
        rec = episodic_memory.store(
            key=f"case:{self._current_task_id}",
            value=case_data,
            metadata={"type": "task_archive", "source": "working_memory"},
            ttl_seconds=0,  # 永久保留
        )
        return rec.record_id if rec else None

    # ── 持久化（复用 ai_task_step 表） ───────────────────────────

    def _persist_step(self, step: Dict[str, Any]) -> None:
        """将步骤写入 ai_task_step 表（复用现有表，仅 INSERT）。"""
        try:
            conn = get_db_connection(self.db_path)
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO ai_task_step
                       (step_id, task_id, phase, status, detail, agent_id,
                        skill_id, started_at, finished_at, duration_ms, error)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        step["step_id"], step["task_id"],
                        step["action"], step["status"],
                        json.dumps({"input": step["input"], "output": step["output"]},
                                   ensure_ascii=False, default=str)[:2000],
                        step.get("agent_id", "agent_runtime"),
                        step.get("skill_id", ""),
                        step["timestamp"], step["timestamp"], 0,
                        step.get("error"),
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception:
            pass  # 持久化失败不阻断主链路

    def stats(self) -> Dict[str, Any]:
        s = super().stats()
        s.update({
            "current_task_id": self._current_task_id,
            "steps_in_memory": len(self._steps),
            "max_steps": self.max_steps,
        })
        return s
