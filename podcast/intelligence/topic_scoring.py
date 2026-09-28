"""Deterministic topic scoring; AI may suggest inputs, but never owns the final score."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TopicSignals:
    demand: float | None = None
    timeliness: float | None = None
    novelty: float | None = None
    human_relevance: float | None = None
    guest_fit: float | None = None
    evidence: float | None = None
    content_yield: float | None = None
    distribution: float | None = None
    risk: float | None = None
    cost: float | None = None

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            # Exact numeric types exclude bool; the closed interval also
            # rejects NaN/infinity without coercing missing or invalid input.
            if value is not None and (type(value) not in (int, float) or not 0 <= value <= 1):
                raise ValueError(f"INVALID_TOPIC_SIGNAL:{name}")


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def score_topic(signals: TopicSignals) -> float | None:
    """Score only complete observations; missing inputs are not negative evidence."""
    if any(getattr(signals, name) is None for name in signals.__dataclass_fields__):
        return None
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


def classify_topic(score: float | None, timeliness: float | None) -> str | None:
    """Map score and freshness into a review stage; thresholds are deterministic."""
    if score is None or timeliness is None:
        return None
    if (type(score) not in (int, float) or not 0 <= score <= 100
            or type(timeliness) not in (int, float) or not 0 <= timeliness <= 1):
        raise ValueError("INVALID_TOPIC_CLASSIFICATION_INPUT")
    if score < 35:
        return "rejected"
    if timeliness >= 0.85:
        return "now"
    if score >= 75:
        return "soon"
    if score >= 55:
        return "evergreen"
    return "watch"
