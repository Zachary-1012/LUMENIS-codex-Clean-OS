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

    def list_skills(self, status=None, product=None):
        if not self.enabled or not self.db_path:
            return []
        try:
            from .task import TaskMemory
            from agent_runtime.task_binding import _current_binding
            from account.skills import get_skill_info
            binding = self._binding_context()
            task = TaskMemory(self.db_path, enabled=True).bind_task(binding["task_id"], binding["actor_id"]).get_task(binding["task_id"])
            contract = json.loads(task["context_json"])["agent_runtime"]
            result = []
            for sid in contract["registry_bindings"]:
                _current_binding(binding["task_id"], sid)
                info = get_skill_info(sid)
                if status and info.get("status") != status or product and info.get("product") != product:
                    continue
                result.append({key: info.get(key) for key in ("skill_id", "name", "version", "product", "domain", "status")})
            return result
        except Exception:
            return []

    def get_skill(self, skill_id):
        return next((row for row in self.list_skills() if row["skill_id"] == skill_id), None)

    def get_skill_stats(self, skill_id):
        rows = self.get_recent_executions(skill_id, limit=10000)
        completed = sum(row.get("status") == "completed" for row in rows)
        failed = sum(row.get("status") == "failed" for row in rows)
        terminal = completed + failed
        return {"skill_id": skill_id, "total": len(rows), "success": completed,
                "failed": failed, "success_rate": completed / terminal if terminal else None,
                "avg_duration_ms": sum(row.get("duration_ms") or 0 for row in rows) / len(rows) if rows else None,
                "metric_kind": "execution_completion_only", "business_success_rate": None}

    def get_all_skill_stats(self):
        return [self.get_skill_stats(s["skill_id"]) for s in self.list_skills()]

    def get_recent_executions(self, skill_id=None, limit=20):
        if not self.enabled or not self.db_path:
            return []
        try:
            from .task import TaskMemory
            from agent_runtime.task_binding import _digest, _current_binding
            from lumenis.shared.agents.skills.execution import query_executions, verified_execution_scope
            binding = self._binding_context()
            task = TaskMemory(self.db_path, enabled=True).bind_task(binding["task_id"], binding["actor_id"]).get_task(binding["task_id"])
            context = json.loads(task["context_json"])
            entries = context["agent_runtime"]["steps"]
            # Gateway-planned steps are read from the original durable result,
            # never inferred from another task's executions.
            result = json.loads(task.get("result_json") or "{}")
            entries = entries + [{"skill_id": r.get("tool"), "input": r.get("params", {})}
                                 for r in (result.get("plan") or {}).get("steps", [])]
            if not entries:
                from agent_runtime.durable_adapter import DurableExecutionAdapter
                step_rows = TaskMemory(self.db_path, enabled=True).bind_task(
                    binding["task_id"], binding["actor_id"]).get_task_steps(binding["task_id"])
                checkpoints = DurableExecutionAdapter._db_checkpoints(step_rows)
                if checkpoints:
                    entries = [{"skill_id": r.get("tool"), "input": r.get("params", {})}
                               for r in checkpoints[-1].plan_snapshot.get("steps", [])]
            rows, seen = [], set()
            for entry in entries:
                sid = entry["skill_id"]
                if skill_id and sid != skill_id:
                    continue
                _current_binding(binding["task_id"], sid)
                execution_id = ("skillscope_" if binding["actor_id"] is not None else "") + "agentstep_" + _digest(
                    {"task": binding["task_id"], "skill": sid, "inputs": entry["input"]})[:32]
                if execution_id in seen:
                    continue
                seen.add(execution_id)
                for row in query_executions(execution_id=execution_id, limit=1, strict=True):
                    # Account Agent executions use the canonical signed scope
                    # receipt. A stale/legacy ID cannot downgrade that boundary.
                    if binding["actor_id"] is not None and not verified_execution_scope(
                            row, {"id": binding["actor_id"]}):
                        continue
                    rows.append(row)
            self._binding_context()
            return sorted(rows, key=lambda row: row.get("created_at") or "", reverse=True)[:limit]
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
        if self._task_binding is not None:
            import uuid
            if type(success) is not bool or type(duration_ms) is not int or duration_ms < 0:
                raise ValueError("SKILL_FEEDBACK_INVALID")
            self._binding_context(write=True)
            if not self.get_skill(skill_id):
                raise PermissionError("SKILL_FEEDBACK_SCOPE_DENIED")
            # Append immutable derived observations; no second execution truth or
            # unreviewed business-success percentage is written to Skill traces.
            return bool(self.store("feedback:" + uuid.uuid4().hex,
                {"skill_id": skill_id, "reported_success": success, "duration_ms": duration_ms,
                 "details": metadata or {}, "business_success_rate": None},
                metadata={"type": "skill_feedback", "skill_id": skill_id}))
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

        if self._task_binding is not None:
            allowed = {item["skill_id"] for item in self.list_skills()}
            candidates = [sid for sid in candidates if sid in allowed]

        def score(sid: str) -> Tuple[float, int]:
            stats = self.get_skill_stats(sid)
            cache = self._success_cache.get(sid, {}) if self._task_binding is None else {}
            if self._task_binding is not None:
                observations = self.query({"type": "skill_feedback", "skill_id": sid}, limit=1000)
                total = len(observations)
                positives = sum(item.value.get("reported_success") is True for item in observations)
                cache = {"rate": positives / total if total else 0.0, "total": total}
            rate = max(stats["success_rate"] or 0.0, cache.get("rate", 0.0))
            total = stats["total"] + cache.get("total", 0)
            # 成功率优先，执行次数作为置信度
            return (rate, total)

        scored = [(score(sid), sid) for sid in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else None

    def stats(self):
        return {**super().stats(), "visible_execution_count": len(self.get_recent_executions()),
                "cached_skills": len(self._success_cache)}
