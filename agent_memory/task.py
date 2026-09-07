# -*- coding: utf-8 -*-
"""Task Memory（任务记忆）— 任务级记忆：目标、规划、执行历史、最终结果。

存储：复用 ai_task 表（2252行）+ ai_task_evidence 表（3146行）
检索：按 task_id / intent / status / 时间范围查询
与 OSAI memory_lifecycle.py 的 task dict 对齐。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .base import BaseMemoryLayer, MemoryRecord, get_db_connection


class TaskMemory(BaseMemoryLayer):
    """任务记忆：基于 ai_task + ai_task_evidence 表的任务级持久化记忆。

    所有写操作通过 ai_task_engine 现有链路完成，本层只做读取和轻量写入。
    """

    LAYER_NAME = "task"

    def __init__(self, db_path: Optional[str] = None, enabled: bool = False):
        super().__init__(db_path=db_path, enabled=enabled)

    # ── 任务查询 ─────────────────────────────────────────────────

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """按 task_id 获取任务详情（复用 ai_task 表）。"""
        if not self.enabled or not self.db_path:
            return None
        try:
            conn = get_db_connection(self.db_path)
            try:
                row = conn.execute(
                    "SELECT * FROM ai_task WHERE task_id=?", (task_id,)
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()
        except Exception:
            return None

    def get_task_steps(self, task_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取任务的所有步骤（复用 ai_task_step 表）。"""
        if not self.enabled or not self.db_path:
            return []
        try:
            conn = get_db_connection(self.db_path)
            try:
                rows = conn.execute(
                    """SELECT * FROM ai_task_step
                       WHERE task_id=? ORDER BY started_at ASC LIMIT ?""",
                    (task_id, limit),
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception:
            return []

    def get_task_evidence(self, task_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取任务的证据链（复用 ai_task_evidence 表）。"""
        if not self.enabled or not self.db_path:
            return []
        try:
            conn = get_db_connection(self.db_path)
            try:
                rows = conn.execute(
                    """SELECT * FROM ai_task_evidence
                       WHERE task_id=? ORDER BY created_at ASC LIMIT ?""",
                    (task_id, limit),
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception:
            return []

    def query_tasks(self, intent: Optional[str] = None,
                    status: Optional[str] = None,
                    limit: int = 50) -> List[Dict[str, Any]]:
        """按意图/状态查询历史任务。"""
        if not self.enabled or not self.db_path:
            return []
        try:
            conn = get_db_connection(self.db_path)
            try:
                sql = "SELECT * FROM ai_task WHERE 1=1"
                params: list = []
                if intent:
                    sql += " AND intent LIKE ?"
                    params.append(f"%{intent}%")
                if status:
                    sql += " AND status=?"
                    params.append(status)
                sql += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                rows = conn.execute(sql, params).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception:
            return []

    def get_task_summary(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务完整摘要（task + steps + evidence）。"""
        task = self.get_task(task_id)
        if not task:
            return None
        return {
            "task": task,
            "steps": self.get_task_steps(task_id),
            "evidence": self.get_task_evidence(task_id),
        }

    # ── 轻量写入（仅记录任务结果摘要，不修改 ai_task 主表） ──────

    def record_task_outcome(self, task_id: str, outcome: str,
                            result_summary: str,
                            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """记录任务结果到内存（不直接写 ai_task 表，避免干扰主链路）。"""
        if not self.enabled:
            return False
        rec = self.store(
            key=f"outcome:{task_id}",
            value={
                "task_id": task_id,
                "outcome": outcome,
                "result_summary": result_summary,
                "metadata": metadata or {},
            },
            metadata={"type": "task_outcome"},
        )
        return rec is not None

    def stats(self) -> Dict[str, Any]:
        s = super().stats()
        if self.db_path:
            try:
                conn = get_db_connection(self.db_path)
                try:
                    total = conn.execute("SELECT COUNT(*) FROM ai_task").fetchone()[0]
                    s["ai_task_total"] = total
                finally:
                    conn.close()
            except Exception:
                pass
        return s
