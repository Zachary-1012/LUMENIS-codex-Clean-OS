"""Research reasoning levels shared by Podcast Case Library and Research Reader."""

from dataclasses import dataclass
from enum import Enum


class ResearchLevel(str, Enum):
    FACT = "fact"
    OBSERVATION = "observation"
    PATTERN = "pattern"
    HYPOTHESIS = "hypothesis"
    VALIDATION = "validation"
    TRANSFER = "transfer"
    DONT_COPY = "dont_copy"


class EvidenceStatus(str, Enum):
    OBSERVED = "observed"
    DERIVED = "derived"
    AI_SUGGESTED = "ai_suggested"
    HUMAN_VERIFIED = "human_verified"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class ResearchFinding:
    finding_id: str
    level: ResearchLevel
    statement: str
    evidence_ids: tuple[str, ...] = ()
    confidence: float = 0.0

    def promotable(self) -> bool:
        """Only evidence-backed findings can be promoted into reusable rules."""
        return bool(self.evidence_ids) and self.confidence >= 0.70
