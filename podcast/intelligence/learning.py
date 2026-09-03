"""Promote validated Podcast observations into reusable learning assets."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum


class LearningState(StrEnum):
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    PROMOTED = "promoted"
    REJECTED = "rejected"


@dataclass(frozen=True)
class LearningCandidate:
    candidate_id: str
    statement: str
    evidence_ids: tuple[str, ...]
    validation_count: int = 0
    contradiction_count: int = 0


def promote(candidate: LearningCandidate, *, min_validations: int = 2) -> LearningState:
    if not candidate.evidence_ids:
        return LearningState.CANDIDATE
    if candidate.contradiction_count > 0:
        return LearningState.REJECTED
    if candidate.validation_count < min_validations:
        return LearningState.VALIDATED if candidate.validation_count else LearningState.CANDIDATE
    return LearningState.PROMOTED
