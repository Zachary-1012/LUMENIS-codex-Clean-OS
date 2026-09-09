from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ResearchBudget:
    max_iterations: int = 3
    max_runtime_seconds: float = 30
    max_model_calls: int = 0
    max_resource_mb: int = 512


class ResearchOptimizer:
    """Shadow-only experiment runner; it never mutates Production state."""

    def __init__(self, budget: ResearchBudget | None = None):
        self.budget = budget or ResearchBudget()

    def run(self, name: str, baseline: Callable[[], Any], candidate: Callable[[], Any], quality: Callable[[Any, Any], bool]) -> dict[str, Any]:
        started = time.perf_counter()
        before_started = time.perf_counter()
        before = baseline()
        before_ms = (time.perf_counter() - before_started) * 1000
        after_started = time.perf_counter()
        after = candidate()
        after_ms = (time.perf_counter() - after_started) * 1000
        equivalent = bool(quality(before, after))
        within_time = (time.perf_counter() - started) <= self.budget.max_runtime_seconds
        keep = equivalent and within_time and after_ms <= before_ms
        return {"name": name, "before_ms": before_ms, "after_ms": after_ms, "quality_equivalence": equivalent, "within_budget": within_time, "result": "KEEP" if keep else "REJECT", "production_mutation": False}
