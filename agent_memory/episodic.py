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

    def search_cases(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """按关键词检索历史任务案例。

        检索策略：在 ai_task_evidence.content 中做关键词匹配，
        按匹配度排序返回。
        """
        if not self.enabled or not self.db_path or not query:
            return []
        tokens = [t for t in re.split(r"[\s,，。！？、/|:：;；]+", query.lower()) if len(t) >= 2]
        if not tokens:
            return []
        try:
            conn = get_db_connection(self.db_path)
            try:
                # 先取最近的 evidence 做匹配（避免全表扫描）
                rows = conn.execute(
                    """SELECT evidence_id, task_id, evidence_type, content, source,
                              authenticity_score, created_at
                       FROM ai_task_evidence
                       ORDER BY created_at DESC LIMIT 2000"""
                ).fetchall()
                scored: List[Tuple[int, Dict[str, Any]]] = []
                for row in rows:
                    content = (row["content"] or "").lower()
                    score = sum(1 for t in tokens if t in content)
                    if score > 0:
                        scored.append((score, dict(row)))
                scored.sort(key=lambda x: x[0], reverse=True)
                return [r for _, r in scored[:limit]]
            finally:
                conn.close()
        except Exception:
            return []

    def get_success_patterns(self, limit: int = 20) -> List[Dict[str, Any]]:
        """检索成功模式（高 authenticity_score 的 evidence）。"""
        if not self.enabled or not self.db_path:
            return []
        try:
            conn = get_db_connection(self.db_path)
            try:
                rows = conn.execute(
                    """SELECT evidence_id, task_id, evidence_type, content, source,
                              authenticity_score, created_at
                       FROM ai_task_evidence
                       WHERE authenticity_score >= 0.8
                       ORDER BY authenticity_score DESC, created_at DESC LIMIT ?""",
                    (limit,),
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception:
            return []

    def get_failure_patterns(self, limit: int = 20) -> List[Dict[str, Any]]:
        """检索失败模式（低 authenticity_score 或 error evidence）。"""
        if not self.enabled or not self.db_path:
            return []
        try:
            conn = get_db_connection(self.db_path)
            try:
                rows = conn.execute(
                    """SELECT evidence_id, task_id, evidence_type, content, source,
                              authenticity_score, created_at
                       FROM ai_task_evidence
                       WHERE evidence_type LIKE '%error%'
                          OR evidence_type LIKE '%fail%'
                          OR authenticity_score < 0.3
                       ORDER BY created_at DESC LIMIT ?""",
                    (limit,),
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception:
            return []

    # ── 人工审核经验（基于 note_review_history） ─────────────────

    def get_review_experience(self, note_id: Optional[str] = None,
                              provider: Optional[str] = None,
                              limit: int = 50) -> List[Dict[str, Any]]:
        """检索人工审核经验（AI判定→人审修正的 diff）。

        这是 Learning Loop 的核心数据源：8387 条人审记录。
        """
        if not self.enabled or not self.db_path:
            return []
        try:
            conn = get_db_connection(self.db_path)
            try:
                sql = "SELECT * FROM note_review_history WHERE 1=1"
                params: list = []
                if note_id:
                    sql += " AND note_id=?"
                    params.append(note_id)
                if provider:
                    sql += " AND provider=?"
                    params.append(provider)
                sql += " ORDER BY reviewed_at DESC LIMIT ?"
                params.append(limit)
                rows = conn.execute(sql, params).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception:
            return []

    def get_correction_patterns(self, limit: int = 50) -> List[Dict[str, Any]]:
        """检索人审修正模式（old != new 的记录）。"""
        if not self.enabled or not self.db_path:
            return []
        try:
            conn = get_db_connection(self.db_path)
            try:
                rows = conn.execute(
                    """SELECT * FROM note_review_history
                       WHERE old_relevance != new_relevance
                          OR old_sentiment != new_sentiment
                          OR old_risk != new_risk
                       ORDER BY reviewed_at DESC LIMIT ?""",
                    (limit,),
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception:
            return []

    # ── 案例存储（内存 + 可选持久化到 ai_task_evidence） ─────────

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
        if rec and persist and self.db_path:
            self._persist_case(case_key, case_data, outcome)
        return rec

    def _persist_case(self, case_key: str, case_data: Dict[str, Any],
                      outcome: str) -> None:
        """持久化案例到 ai_task_evidence 表（复用）。"""
        try:
            import uuid
            conn = get_db_connection(self.db_path)
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO ai_task_evidence
                       (evidence_id, task_id, step_id, evidence_type, content,
                        source, authenticity_score, created_at, previous_hash, current_hash)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        uuid.uuid4().hex[:16],
                        case_data.get("task_id", ""),
                        case_data.get("step_id", ""),
                        f"episodic_{outcome}",
                        json.dumps(case_data, ensure_ascii=False, default=str)[:4000],
                        "episodic_memory",
                        1.0 if outcome == "success" else 0.5,
                        case_data.get("archived_at", ""),
                        "", "",
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception:
            pass

    def stats(self) -> Dict[str, Any]:
        s = super().stats()
        if self.db_path:
            try:
                conn = get_db_connection(self.db_path)
                try:
                    ev = conn.execute("SELECT COUNT(*) FROM ai_task_evidence").fetchone()[0]
                    rv = conn.execute("SELECT COUNT(*) FROM note_review_history").fetchone()[0]
                    s["ai_task_evidence_total"] = ev
                    s["note_review_history_total"] = rv
                finally:
                    conn.close()
            except Exception:
                pass
        return s
