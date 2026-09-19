"""LUMENIS Shared Evaluation deterministic benchmark primitives for collection quality.

This module intentionally evaluates records only; it never collects data and
never changes production state.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List


def field_accuracy(predicted: Iterable[Dict[str, Any]], truth: Iterable[Dict[str, Any]], field: str) -> float:
    p = list(predicted)
    t = list(truth)
    if len(p) != len(t) or not p:
        return 0.0
    return sum(pv.get(field) == tv.get(field) for pv, tv in zip(p, t)) / len(p)


def binary_metrics(predicted: Iterable[bool], truth: Iterable[bool]) -> Dict[str, float]:
    p, t = list(predicted), list(truth)
    if len(p) != len(t):
        raise ValueError("predicted/truth length mismatch")
    tp = sum(a and b for a, b in zip(p, t))
    fp = sum(a and not b for a, b in zip(p, t))
    fn = sum((not a) and b for a, b in zip(p, t))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def summarize(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {"sample_count": 0, "collection_success_rate": 0.0}
    success = sum(r.get("collection_state", "SUCCESS") == "SUCCESS" for r in records)
    return {
        "sample_count": len(records),
        "collection_success_rate": success / len(records),
        "blocked_count": sum(r.get("collection_state") == "BLOCKED" for r in records),
        "auth_required_count": sum(r.get("collection_state") == "AUTH_REQUIRED" for r in records),
    }
