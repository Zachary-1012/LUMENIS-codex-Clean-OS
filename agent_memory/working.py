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
from copy import deepcopy
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
        if type(max_steps) is not int or max_steps < 1:
            raise ValueError("working memory max_steps must be a positive integer")
        self.max_steps = max_steps
        self._steps: deque = deque(maxlen=max_steps)
        self._current_task_id: Optional[str] = None
        self._context: Dict[str, Any] = {}
        self._total_steps = 0
        self._persistence_requested = 0
        self._persisted_steps = 0
        self._persistence_failures = 0

    # ── 任务上下文 ───────────────────────────────────────────────

    def begin_task(self, task_id: str, goal: str,
                   context: Optional[Dict[str, Any]] = None) -> None:
        """开始新任务，初始化工作记忆。"""
        if not self.enabled:
            return
        from agent_runtime.durable_adapter import _sanitize_checkpoint_value
        safe_context, context_sanitized = _sanitize_checkpoint_value(deepcopy(context or {}))
        safe_goal, goal_sanitized = _sanitize_checkpoint_value(goal)
        self._current_task_id = task_id
        self._context = {
            **safe_context,
            "task_id": task_id,
            "goal": safe_goal,
            "started_at": _utc_now_iso(),
            "step_count": 0,
            "steps_in_memory": 0,
            "memory_sanitized": context_sanitized or goal_sanitized,
        }
        self._total_steps = self._persistence_requested = self._persisted_steps = self._persistence_failures = 0
        self._steps.clear()
        self.store(f"task:{task_id}:context", deepcopy(self._context),
                   metadata={"type": "task_context"}, ttl_seconds=3600)

    def end_task(self, result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """结束任务，返回归档摘要（不自动归档，由调用方决定是否归档到 Episodic）。"""
        if not self.enabled:
            return {}
        from agent_runtime.durable_adapter import _sanitize_checkpoint_value
        safe_result, result_sanitized = _sanitize_checkpoint_value(deepcopy(result or {}))
        summary = {
            "task_id": self._current_task_id,
            "goal": self._context.get("goal", ""),
            "step_count": self._total_steps,
            "steps_in_memory": len(self._steps),
            "persistence": self._persistence_summary(),
            "started_at": self._context.get("started_at"),
            "finished_at": _utc_now_iso(),
            "result": safe_result,
            "memory_sanitized": self._context.get("memory_sanitized", False) or result_sanitized,
        }
        self._current_task_id = None
        self._context = {}
        self._steps.clear()
        self._total_steps = self._persistence_requested = self._persisted_steps = self._persistence_failures = 0
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
        from agent_runtime.durable_adapter import _sanitize_checkpoint_value
        safe, sanitized = _sanitize_checkpoint_value(deepcopy({
            "action": action, "input": input_data or {}, "output": output_data or {}, "error": error,
        }))
        step = {
            "step_id": uuid.uuid4().hex[:16],
            "task_id": self._current_task_id,
            "seq": self._total_steps + 1,
            "action": safe["action"],
            "input": safe["input"],
            "output": safe["output"],
            "status": status,
            "error": safe["error"],
            "timestamp": _utc_now_iso(),
            "memory_sanitized": sanitized,
            "persistence": {"state": "NOT_REQUESTED", "checkpoint_resumable": False},
        }
        if persist:
            self._persistence_requested += 1
            if self.db_path and self._current_task_id:
                step["persistence"] = self._persist_step(step)
            else:
                step["persistence"] = {"state": "UNAVAILABLE", "code": "WORKING_MEMORY_PERSISTENCE_NOT_BOUND",
                                       "checkpoint_resumable": False}
            if step["persistence"]["state"] == "PERSISTED":
                self._persisted_steps += 1
            else:
                self._persistence_failures += 1
        self._total_steps += 1
        self._steps.append(step)
        if self._context:
            self._context["step_count"] = self._total_steps
            self._context["steps_in_memory"] = len(self._steps)
            self._context["persistence"] = self._persistence_summary()
        return deepcopy(step)

    def get_recent_steps(self, n: int = 10) -> List[Dict[str, Any]]:
        """获取最近 N 步。"""
        return deepcopy(list(self._steps)[-n:])

    def get_context(self) -> Dict[str, Any]:
        return deepcopy(self._context)

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
            "steps": deepcopy(list(self._steps)),
            "step_count": self._total_steps,
            "steps_in_memory": len(self._steps),
            "persistence": self._persistence_summary(),
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

    def _persistence_summary(self) -> Dict[str, Any]:
        return {"state": "UNAVAILABLE" if self._persistence_failures else
                         "PERSISTED" if self._persistence_requested else "NOT_REQUESTED",
                "requested_steps": self._persistence_requested, "persisted_steps": self._persisted_steps,
                "failed_steps": self._persistence_failures, "checkpoint_resumable": False}

    def _persist_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a Memory observation; only canonical TaskEngine checkpoints resume work.

        A failed ancillary write leaves the business step status intact and
        reports durability separately. No table creation, migration or retry.
        """
        try:
            detail = json.dumps({"format": "lumenis.agent_memory.working_step", "version": 1,
                                 "seq": step["seq"], "action": step["action"],
                                 "input": step["input"], "output": step["output"],
                                 "memory_sanitized": step["memory_sanitized"], "checkpoint_resumable": False},
                                ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            if len(detail.encode("utf-8")) > 128 * 1024:
                return {"state": "UNAVAILABLE", "code": "WORKING_MEMORY_DETAIL_TOO_LARGE",
                        "checkpoint_resumable": False}
            conn = get_db_connection(self.db_path)
            try:
                conn.execute(
                    """INSERT INTO ai_task_step
                       (step_id, task_id, phase, status, detail, agent_id,
                        skill_id, started_at, finished_at, duration_ms, error)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        step["step_id"], step["task_id"],
                        f"working_memory_step_{step['seq']}", step["status"],
                        detail,
                        step.get("agent_id", "agent_runtime"),
                        step.get("skill_id", ""),
                        step["timestamp"], step["timestamp"], 0,
                        step.get("error"),
                    ),
                )
                stored = conn.execute("SELECT detail FROM ai_task_step WHERE step_id=? AND task_id=?",
                                      (step["step_id"], step["task_id"])).fetchone()
                if stored is None or stored["detail"] != detail:
                    raise RuntimeError("Working Memory step readback mismatch")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
            return {"state": "PERSISTED", "step_ref": step["step_id"], "checkpoint_resumable": False}
        except Exception:
            return {"state": "UNAVAILABLE", "code": "WORKING_MEMORY_PERSISTENCE_FAILED",
                    "checkpoint_resumable": False}

    def stats(self) -> Dict[str, Any]:
        s = super().stats()
        s.update({
            "current_task_id": self._current_task_id,
            "steps_in_memory": len(self._steps),
            "max_steps": self.max_steps,
            "total_steps": self._total_steps,
            "persistence": self._persistence_summary(),
        })
        return s
