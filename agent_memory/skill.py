# -*- coding: utf-8 -*-
"""Skill Memory（技能记忆）— 已注册Skill、使用统计、成功率、版本。

存储：复用 skills_registry 表（12行）+ skill_executions 表（18行）
能力：Skill使用反馈 → 更新成功率 → 影响Skill选择
与 OSAI skill_registry.py + skill_invocation.py 对齐。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseMemoryLayer, MemoryRecord, get_db_connection


class SkillMemory(BaseMemoryLayer):
    """技能记忆：Skill 注册表 + 执行统计 + 成功率追踪。

    两个数据源：
      1. skills_registry — 已注册 Skill 元数据（12条）
      2. skill_executions — Skill 执行记录（18条，含六域审计字段）
    """

    LAYER_NAME = "skill"

    def __init__(self, db_path: Optional[str] = None, enabled: bool = False):
        super().__init__(db_path=db_path, enabled=enabled)
        self._success_cache: Dict[str, Dict[str, float]] = {}  # skill_id -> {total, success, rate}

    # ── Skill 注册表查询（基于 skills_registry） ─────────────────

    def list_skills(self, status: Optional[str] = None,
                    product: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出已注册 Skill。"""
        if not self.enabled or not self.db_path:
            return []
        try:
            conn = get_db_connection(self.db_path)
            try:
                sql = "SELECT * FROM skills_registry WHERE 1=1"
                params: list = []
                if status:
                    sql += " AND status=?"
                    params.append(status)
                if product:
                    sql += " AND product=?"
                    params.append(product)
                sql += " ORDER BY skill_id"
                rows = conn.execute(sql, params).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception:
            return []

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """按 skill_id 获取 Skill 元数据。"""
        if not self.enabled or not self.db_path:
            return None
        try:
            conn = get_db_connection(self.db_path)
            try:
                row = conn.execute(
                    "SELECT * FROM skills_registry WHERE skill_id=?", (skill_id,)
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()
        except Exception:
            return None

    # ── 执行统计（基于 skill_executions） ────────────────────────

    def get_skill_stats(self, skill_id: str) -> Dict[str, Any]:
        """获取 Skill 的执行统计（总次数、成功次数、成功率、平均耗时）。"""
        if not self.enabled or not self.db_path:
            return {"skill_id": skill_id, "total": 0, "success": 0, "success_rate": 0.0}
        try:
            conn = get_db_connection(self.db_path)
            try:
                row = conn.execute(
                    """SELECT COUNT(*) as total,
                              SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as success,
                              AVG(duration_ms) as avg_duration
                       FROM skill_executions WHERE skill_id=?""",
                    (skill_id,),
                ).fetchone()
                total = row["total"] or 0
                success = row["success"] or 0
                rate = (success / total) if total > 0 else 0.0
                return {
                    "skill_id": skill_id,
                    "total": total,
                    "success": success,
                    "failed": total - success,
                    "success_rate": round(rate, 4),
                    "avg_duration_ms": row["avg_duration"] or 0,
                }
            finally:
                conn.close()
        except Exception:
            return {"skill_id": skill_id, "total": 0, "success": 0, "success_rate": 0.0}

    def get_all_skill_stats(self) -> List[Dict[str, Any]]:
        """获取所有 Skill 的执行统计。"""
        skills = self.list_skills()
        return [self.get_skill_stats(s["skill_id"]) for s in skills]

    def get_recent_executions(self, skill_id: Optional[str] = None,
                              limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近的 Skill 执行记录。"""
        if not self.enabled or not self.db_path:
            return []
        try:
            conn = get_db_connection(self.db_path)
            try:
                sql = "SELECT * FROM skill_executions"
                params: list = []
                if skill_id:
                    sql += " WHERE skill_id=?"
                    params.append(skill_id)
                sql += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                rows = conn.execute(sql, params).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception:
            return []

    # ── 反馈更新成功率（影响 Skill 选择） ────────────────────────

    def record_feedback(self, skill_id: str, success: bool,
                        duration_ms: int = 0,
                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """记录 Skill 使用反馈，更新成功率缓存。

        注意：不直接写 skill_executions 表（该表由 skill_execution_chain 写入），
        仅更新内存缓存供 Skill 选择参考。
        """
        if not self.enabled:
            return False
        cache = self._success_cache.setdefault(skill_id, {"total": 0, "success": 0})
        cache["total"] += 1
        if success:
            cache["success"] += 1
        cache["rate"] = cache["success"] / cache["total"] if cache["total"] > 0 else 0.0
        return True

    def select_best_skill(self, candidates: List[str],
                          context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """基于成功率选择最优 Skill。

        选择策略：
          1. 有执行记录的优先（成功率 > 0）
          2. 成功率高的优先
          3. 执行次数多的优先（有统计基础）
          4. 无记录的按原顺序 fallback
        """
        if not candidates:
            return None
        if not self.enabled:
            return candidates[0]

        def score(sid: str) -> Tuple[float, int]:
            stats = self.get_skill_stats(sid)
            cache = self._success_cache.get(sid, {})
            rate = max(stats["success_rate"], cache.get("rate", 0.0))
            total = stats["total"] + cache.get("total", 0)
            # 成功率优先，执行次数作为置信度
            return (rate, total)

        scored = [(score(sid), sid) for sid in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else None

    def stats(self) -> Dict[str, Any]:
        s = super().stats()
        if self.db_path:
            try:
                conn = get_db_connection(self.db_path)
                try:
                    sr = conn.execute("SELECT COUNT(*) FROM skills_registry").fetchone()[0]
                    se = conn.execute("SELECT COUNT(*) FROM skill_executions").fetchone()[0]
                    s["skills_registry_total"] = sr
                    s["skill_executions_total"] = se
                finally:
                    conn.close()
            except Exception:
                pass
        s["cached_skills"] = len(self._success_cache)
        return s
