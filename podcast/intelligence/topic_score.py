"""Deterministic Podcast Topic Intelligence scorer.

AI may propose signal values, but this module owns the final score formula.
Inputs are normalized to [0, 1]. Risk and cost reduce priority.
"""

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


WEIGHTS = {
    "demand": 0.14,
    "timeliness": 0.12,
    "novelty": 0.10,
    "human_relevance": 0.14,
    "guest_fit": 0.10,
    "evidence": 0.12,
    "content_yield": 0.10,
    "distribution": 0.08,
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def score_topic(signals: TopicSignals) -> float:
    positive = sum(weight * _clamp(getattr(signals, key)) for key, weight in WEIGHTS.items())
    penalty = 0.06 * _clamp(signals.risk) + 0.04 * _clamp(signals.cost)
    return round(max(0.0, min(100.0, (positive - penalty) * 100)), 2)


def classify_stage(score: float, timeliness: float) -> str:
    if score < 35:
        return "rejected"
    if timeliness >= 0.85 and score >= 75:
        return "now"
    if score >= 70:
        return "soon"
    if timeliness < 0.35 and score >= 55:
        return "evergreen"
    return "watch"
