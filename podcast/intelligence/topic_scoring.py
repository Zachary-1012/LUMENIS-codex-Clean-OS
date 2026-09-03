"""Deterministic topic scoring; AI may suggest inputs, but never owns the final score."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TopicSignals:
    demand: float = 0.0
    timeliness: float = 0.0
    novelty: float = 0.0
    human_relevance: float = 0.0
    guest_fit: float = 0.0
    evidence: float = 0.0
    content_yield: float = 0.0
    distribution: float = 0.0
    risk: float = 0.0
    cost: float = 0.0


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def score_topic(signals: TopicSignals) -> float:
    """Return a 0..100 priority score using stable, inspectable weights."""
    positive = (
        0.16 * signals.demand
        + 0.12 * signals.timeliness
        + 0.10 * signals.novelty
        + 0.14 * signals.human_relevance
        + 0.12 * signals.guest_fit
        + 0.10 * signals.evidence
        + 0.10 * signals.content_yield
        + 0.06 * signals.distribution
    )
    penalty = 0.05 * signals.risk + 0.05 * signals.cost
    return round(100 * _clamp(positive - penalty), 2)


def classify_topic(score: float, timeliness: float) -> str:
    """Map score and freshness into a review stage; thresholds are deterministic."""
    if score < 35:
        return "rejected"
    if timeliness >= 0.85:
        return "now"
    if score >= 75:
        return "soon"
    if score >= 55:
        return "evergreen"
    return "watch"
