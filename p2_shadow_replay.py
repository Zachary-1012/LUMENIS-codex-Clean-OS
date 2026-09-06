# -*- coding: utf-8 -*-
"""P2 基础框架 — Shadow/Replay 对比（只建对比函数+测试，不做全量回放）。"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class ComparisonResult(str, Enum):
    IDENTICAL = "IDENTICAL"
    EQUIVALENT = "EQUIVALENT"
    DIFFERENT = "DIFFERENT"
    NEW_ONLY = "NEW_ONLY"
    OLD_ONLY = "OLD_ONLY"
    ERROR = "ERROR"


@dataclass
class ShadowComparison:
    case_id: str
    input_data: Dict[str, Any]
    old_result: Optional[Dict[str, Any]] = None
    new_result: Optional[Dict[str, Any]] = None
    comparison: ComparisonResult = ComparisonResult.ERROR
    diff_fields: List[str] = field(default_factory=list)
    old_error: Optional[str] = None
    new_error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_old_ms: int = 0
    duration_new_ms: int = 0

    def to_dict(self):
        return {"case_id": self.case_id, "comparison": self.comparison.value,
                "diff_fields": self.diff_fields, "old_error": self.old_error,
                "new_error": self.new_error, "duration_old_ms": self.duration_old_ms,
                "duration_new_ms": self.duration_new_ms, "timestamp": self.timestamp}


def _safe_call(fn, input_data):
    start = time.time()
    try:
        result = fn(input_data)
        if not isinstance(result, dict): result = {"result": result}
        return result, None, int((time.time() - start) * 1000)
    except Exception as e:
        return None, str(e), int((time.time() - start) * 1000)


def _compare_dicts(old, new):
    if old == new: return ComparisonResult.IDENTICAL, []
    diff_fields = []
    for key in set(old.keys()) | set(new.keys()):
        if old.get(key) != new.get(key): diff_fields.append(key)
    if diff_fields:
        semantic_eq = True
        for f in diff_fields:
            ov, nv = old.get(f), new.get(f)
            if ov is None or nv is None: semantic_eq = False; break
            try:
                if float(ov) != float(nv): semantic_eq = False; break
            except (ValueError, TypeError): semantic_eq = False; break
        if semantic_eq: return ComparisonResult.EQUIVALENT, diff_fields
    return ComparisonResult.DIFFERENT, diff_fields


def shadow_compare(case_id, input_data, old_fn, new_fn):
    comp = ShadowComparison(case_id=case_id, input_data=input_data)
    comp.old_result, comp.old_error, comp.duration_old_ms = _safe_call(old_fn, input_data)
    comp.new_result, comp.new_error, comp.duration_new_ms = _safe_call(new_fn, input_data)
    if comp.old_error and comp.new_error: comp.comparison = ComparisonResult.ERROR
    elif comp.old_error and not comp.new_error: comp.comparison = ComparisonResult.NEW_ONLY
    elif not comp.old_error and comp.new_error: comp.comparison = ComparisonResult.OLD_ONLY
    elif comp.old_result is None and comp.new_result is not None: comp.comparison = ComparisonResult.NEW_ONLY
    elif comp.old_result is not None and comp.new_result is None: comp.comparison = ComparisonResult.OLD_ONLY
    else: comp.comparison, comp.diff_fields = _compare_dicts(comp.old_result, comp.new_result)
    return comp


def replay_batch(cases, old_fn, new_fn):
    results = []
    stats = {r.value: 0 for r in ComparisonResult}
    for case in cases:
        cid = case.get("case_id", f"case_{len(results)}")
        comp = shadow_compare(cid, case.get("input", {}), old_fn, new_fn)
        results.append(comp)
        stats[comp.comparison.value] += 1
    total = len(results)
    pass_rate = (stats["IDENTICAL"] + stats["EQUIVALENT"]) / total if total > 0 else 0
    return {"total": total, "stats": stats, "pass_rate": round(pass_rate, 4),
            "differences": [r.to_dict() for r in results if r.comparison in (
                ComparisonResult.DIFFERENT, ComparisonResult.NEW_ONLY,
                ComparisonResult.OLD_ONLY, ComparisonResult.ERROR)],
            "all_results": [r.to_dict() for r in results]}
