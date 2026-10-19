# -*- coding: utf-8 -*-
"""Episodic Memory（情景记忆）— 历史任务案例、成功/失败模式、经验教训。

存储：复用 ai_task_evidence 表（3146行）+ note_review_history 表（8387行，含人工审核经验）
检索：按目标相似度/关键词检索历史案例
与 OSAI memory_lifecycle.py 的 episodic list 对齐。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseMemoryLayer, MemoryRecord, get_db_connection


class EpisodicMemory(BaseMemoryLayer):
    """情景记忆：历史任务案例库 + 人工审核经验库。

    两个数据源：
      1. ai_task_evidence — 历史任务的证据/结果（Agent 执行经验）
      2. note_review_history — 人工审核历史（AI判定→人审修正的完整 diff）
    """

    LAYER_NAME = "episodic"

    def __init__(self, db_path: Optional[str] = None, enabled: bool = False,
                 max_cases: int = 500):
        super().__init__(db_path=db_path, enabled=enabled)
        self.max_cases = max_cases

    # ── 历史案例检索（基于 ai_task_evidence） ────────────────────

    def _visible_evidence(self, limit=50):
        if not self.enabled or not self.db_path:
            return []
        try:
            from .task import TaskMemory
            binding = self._binding_context()
            return TaskMemory(self.db_path, enabled=True).bind_task(
                binding["task_id"], binding["actor_id"]).get_task_evidence(binding["task_id"], limit)
        except Exception:
            return []

    def search_cases(self, query, limit=20):
        tokens = [t for t in re.split(r"[\s,，。！？、/|:：;；]+", query.lower()) if len(t) >= 2]
        if not tokens:
            return []
        rows = self._visible_evidence(2000)
        scored = [(sum(t in (r.get("content") or "").lower() for t in tokens), r) for r in rows]
        return [r for score, r in sorted(scored, key=lambda x: x[0], reverse=True) if score][:limit]

    def get_success_patterns(self, limit=20):
        # Execution success is not proof of business success or fact authenticity.
        return [r for r in self.query({"outcome": "success"}, limit) if r.metadata.get("type") == "episodic_case"]

    def get_failure_patterns(self, limit=20):
        return [r for r in self.query({"outcome": "failure"}, limit) if r.metadata.get("type") == "episodic_case"]

    def get_review_experience(self, note_id=None, limit=50):
        if not self.enabled or not self.db_path:
            return []
        try:
            from .semantic import SemanticMemory
            binding = self._binding_context()
            canonical = SemanticMemory(self.db_path, enabled=True).bind_task(
                binding["task_id"], binding["actor_id"])._canonical_rows(100)
            note_ids = {row["source_id"] for row in canonical if row.get("source_table") == "notes"}
            if note_id is not None:
                note_ids.intersection_update({note_id})
            if not note_ids:
                return []
            conn = get_db_connection(self.db_path)
            try:
                rows = conn.execute("SELECT * FROM note_review_history WHERE note_id IN (" +
                    ",".join("?" for _ in note_ids) + ") ORDER BY id DESC LIMIT ?",
                    [*sorted(note_ids), limit]).fetchall()
                self._binding_context(conn)
                return [dict(row) for row in rows]
            finally:
                conn.close()
        except Exception:
            return []

    def get_correction_patterns(self, limit=50):
        reviews = [row for row in self.get_review_experience(limit=limit)
                   if any(row.get("old_" + field) != row.get("new_" + field) for field in ("risk", "sentiment"))]
        return reviews + [r.to_dict() for r in self.query({"type": "correction"}, limit=max(0, limit - len(reviews)))]

    def store_case(self, case_key: str, case_data: Dict[str, Any],
                   outcome: str = "unknown",
                   persist: bool = False) -> Optional[MemoryRecord]:
        """存储一个情景案例。

        Args:
            persist: 是否持久化到 ai_task_evidence 表（默认 False，仅内存）
        """
        rec = self.store(
            key=case_key,
            value=case_data,
            metadata={"type": "episodic_case", "outcome": outcome},
        )
        if rec and persist and self.db_path and self._task_binding is None:
            self._in_memory.pop(case_key, None)
            return None
        return rec

    def stats(self):
        return {**super().stats(), "visible_evidence_count": len(self._visible_evidence())}
