"""Evidence-aware Podcast research pipeline.

This module deliberately separates observation, derivation and AI suggestion.
It is a deterministic orchestration layer; model calls belong behind adapters.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Any, Iterable


class EvidenceStatus(str, Enum):
    OBSERVED = "observed"
    DERIVED = "derived"
    AI_SUGGESTED = "ai_suggested"
    HUMAN_VERIFIED = "human_verified"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class SourceObservation:
    source_id: str
    source_type: str
    locator: str
    observed_at: datetime
    content_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResearchClaim:
    claim_id: str
    text: str
    evidence_ids: tuple[str, ...]
    status: EvidenceStatus
    confidence: float

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.status != EvidenceStatus.UNVERIFIED and not self.evidence_ids:
            raise ValueError("non-unverified claims require evidence")


def stable_id(*parts: str) -> str:
    payload = "|".join(parts).encode("utf-8")
    return sha256(payload).hexdigest()[:16]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def classify_freshness(published_at: datetime | None, now: datetime | None = None) -> str:
    if published_at is None:
        return "unknown"
    now = now or utc_now()
    age_days = max(0, (now - published_at).total_seconds() / 86400)
    if age_days <= 1:
        return "breaking"
    if age_days <= 7:
        return "current"
    if age_days <= 30:
        return "recent"
    if age_days <= 365:
        return "background"
    return "evergreen"


def evidence_gate(claims: Iterable[ResearchClaim], minimum_confidence: float = 0.7, *,
                  artifact_id: str | None = None, review_evidence_id: str | None = None) -> list[ResearchClaim]:
    """Only current signed human review makes a claim eligible for reuse.

    Ordinary draft claims remain usable as drafts, including UNKNOWN. Self-reported
    status, source identifiers and model confidence are never approval receipts.
    Even an eligible claim remains a human-reviewed assertion, not automatic truth.
    """
    if not artifact_id or not review_evidence_id:
        return []
    from content_generation import _review_approved_claim_ids, _context
    if _context() is None:
        return []
    approved = _review_approved_claim_ids(artifact_id, review_evidence_id)
    return [claim for claim in claims if claim.claim_id in approved
            and claim.text == approved[claim.claim_id]["text"]
            and list(claim.evidence_ids) == approved[claim.claim_id]["evidence_ids"]]
