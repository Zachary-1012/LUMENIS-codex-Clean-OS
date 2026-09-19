# -*- coding: utf-8 -*-
"""LUMENIS Shared Learning operation-pattern adapter.

This module preserves the useful part of the retired ai_learning_engine:
operation outcomes can be recorded, summarized and turned into optimization
hints. It deliberately does not perform web retrieval and never writes
AI-generated material into Production Truth or canonical event tables.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .persistence import LearningPersistence


_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DATA_DIR = _REPO_ROOT / "data" / "learning"
_MAX_RECORDS = 1000
_MAX_EXAMPLES = 20


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OperationLearning:
    """Governed operation-pattern learning backed by Shared Learning storage."""

    def __init__(self, data_dir: Optional[str | Path] = None, enabled: bool = True):
        self.persistence = LearningPersistence()
        self.persistence.init(
            data_dir=Path(data_dir) if data_dir is not None else _DEFAULT_DATA_DIR,
            enabled=enabled,
            backup_count=5,
            auto_save=True,
        )
        self.enabled = bool(enabled)

    @staticmethod
    def _empty_state() -> Dict[str, Any]:
        return {
            "records": [],
            "patterns": {},
            "total_learning_count": 0,
            "last_learning_time": None,
        }

    def _load_state(self) -> Dict[str, Any]:
        raw = self.persistence.load_collection("learning_runs")
        if not isinstance(raw, dict):
            return self._empty_state()
        state = self._empty_state()
        state["records"] = raw.get("records") if isinstance(raw.get("records"), list) else []
        state["patterns"] = raw.get("patterns") if isinstance(raw.get("patterns"), dict) else {}
        state["total_learning_count"] = int(raw.get("total_learning_count") or 0)
        state["last_learning_time"] = raw.get("last_learning_time")
        return state

    def _save_state(self, state: Dict[str, Any]) -> bool:
        result = self.persistence.save_collection("learning_runs", state, immediate=True)
        return bool(result.get("ok"))

    def record_operation(
        self,
        operation_type: str,
        operation_details: Optional[Dict[str, Any]],
        result: Any,
        duration_ms: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Record an operation outcome without promoting it to Production Truth."""
        operation_type = str(operation_type or "unknown").strip() or "unknown"
        success = bool(result.get("ok", False)) if isinstance(result, dict) else False
        now = _utc_now_iso()
        record = {
            "id": f"op_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}",
            "timestamp": now,
            "operation_type": operation_type,
            "operation_details": operation_details or {},
            "result": result,
            "duration_ms": duration_ms,
            "success": success,
        }
        if not self.enabled:
            return record

        state = self._load_state()
        records = state["records"]
        records.append(record)
        state["records"] = records[-_MAX_RECORDS:]

        pattern = state["patterns"].setdefault(operation_type, {
            "total_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "avg_duration_ms": 0.0,
            "best_practices": [],
            "common_errors": [],
            "last_used": None,
        })
        previous_count = int(pattern.get("total_count") or 0)
        pattern["total_count"] = previous_count + 1
        pattern["last_used"] = now

        if success:
            pattern["success_count"] = int(pattern.get("success_count") or 0) + 1
            if operation_details:
                example = {
                    "timestamp": now,
                    "details": operation_details,
                    "duration_ms": duration_ms,
                }
                best = pattern.setdefault("best_practices", [])
                best.append(example)
                pattern["best_practices"] = best[-_MAX_EXAMPLES:]
        else:
            pattern["failure_count"] = int(pattern.get("failure_count") or 0) + 1
            error = result.get("error") if isinstance(result, dict) else None
            if error:
                errors = pattern.setdefault("common_errors", [])
                error_text = str(error)[:500]
                if error_text not in errors:
                    errors.append(error_text)
                pattern["common_errors"] = errors[-_MAX_EXAMPLES:]

        if duration_ms is not None:
            try:
                duration = float(duration_ms)
                old_avg = float(pattern.get("avg_duration_ms") or 0.0)
                pattern["avg_duration_ms"] = (
                    old_avg * previous_count + duration
                ) / pattern["total_count"]
            except (TypeError, ValueError):
                pass

        state["total_learning_count"] = int(state.get("total_learning_count") or 0) + 1
        state["last_learning_time"] = now
        self._save_state(state)
        return record

    def get_optimization_suggestion(self, operation_type: str) -> Optional[List[str]]:
        """Return evidence-bound hints from observed operation outcomes only."""
        pattern = self._load_state()["patterns"].get(str(operation_type or ""))
        if not isinstance(pattern, dict) or not pattern:
            return None

        total = int(pattern.get("total_count") or 0)
        success_count = int(pattern.get("success_count") or 0)
        success_rate = success_count / total if total else 0.0
        suggestions: List[str] = []

        if total and success_rate < 0.8:
            errors = [str(x) for x in pattern.get("common_errors", [])[-3:]]
            detail = f"；最近错误：{'、'.join(errors)}" if errors else ""
            suggestions.append(f"观察成功率 {success_rate:.1%}，需复核失败原因{detail}")

        avg_duration = float(pattern.get("avg_duration_ms") or 0.0)
        if avg_duration > 5000:
            suggestions.append(
                f"观察平均耗时 {avg_duration:.0f}ms，可对照已成功操作样本优化执行路径"
            )

        best = pattern.get("best_practices") or []
        if best:
            suggestions.append("存在已成功操作样本，可作为人工复核后的执行参考")

        return suggestions or None

    def get_learning_status(self) -> Dict[str, Any]:
        state = self._load_state()
        patterns = state["patterns"]
        total = sum(int(v.get("total_count") or 0) for v in patterns.values())
        success = sum(int(v.get("success_count") or 0) for v in patterns.values())
        return {
            "owner": "lumenis.shared.learning.operations",
            "enabled": self.enabled,
            "total_learning_count": int(state.get("total_learning_count") or 0),
            "last_learning_time": state.get("last_learning_time"),
            "learned_operation_types": sorted(patterns.keys()),
            "total_operation_records": len(state["records"]),
            "success_rate": success / total if total else 0.0,
            "production_truth_write": False,
        }

    def get_operation_history(
        self,
        operation_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit or 20), 1000))
        records = list(reversed(self._load_state()["records"]))
        if operation_type:
            records = [r for r in records if r.get("operation_type") == operation_type]
        return records[:limit]


_operation_learning: Optional[OperationLearning] = None


def get_operation_learning() -> OperationLearning:
    global _operation_learning
    if _operation_learning is None:
        _operation_learning = OperationLearning()
    return _operation_learning


def get_learning_status() -> Dict[str, Any]:
    return get_operation_learning().get_learning_status()


def get_optimization_suggestion(operation_type: str) -> Optional[List[str]]:
    return get_operation_learning().get_optimization_suggestion(operation_type)


def record_operation(
    operation_type: str,
    operation_details: Optional[Dict[str, Any]],
    result: Any,
    duration_ms: Optional[float] = None,
) -> Dict[str, Any]:
    return get_operation_learning().record_operation(
        operation_type, operation_details, result, duration_ms
    )


def get_operation_history(
    operation_type: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    return get_operation_learning().get_operation_history(operation_type, limit)
