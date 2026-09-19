"""LUMENIS Shared Evaluation contract for resumable, evidence-aware benchmark tasks.

This is deliberately platform-neutral. It is a contract for our own runner,
not an imported agent framework.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class BenchmarkTask:
    task_id: str
    input_payload: Dict[str, Any]
    timeout_seconds: int = 300
    state: str = "PENDING"
    attempts: int = 0
    evidence: List[Dict[str, Any]] = field(default_factory=list)

    def transition(self, new_state: str) -> None:
        allowed = {
            "PENDING": {"RUNNING", "CANCELLED"},
            "RUNNING": {"PAUSED", "SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELLED"},
            "PAUSED": {"RUNNING", "CANCELLED"},
            "FAILED": {"RUNNING", "CANCELLED"},
            "TIMED_OUT": {"RUNNING", "CANCELLED"},
            "SUCCEEDED": set(),
            "CANCELLED": set(),
        }
        if new_state not in allowed.get(self.state, set()):
            raise ValueError(f"invalid transition: {self.state} -> {new_state}")
        self.state = new_state

    def record_evidence(self, kind: str, payload: Dict[str, Any]) -> None:
        self.evidence.append({"kind": kind, "payload": payload})
