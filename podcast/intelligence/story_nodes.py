"""Business-level story node primitives, independent from any ASR vendor."""
from dataclasses import dataclass, field
from typing import Literal

NodeType = Literal["story", "conflict", "reveal", "emotion_peak", "insight_peak", "quote", "problem"]


@dataclass(frozen=True)
class Segment:
    segment_id: str
    start_ms: int
    end_ms: int
    speaker_id: str
    text: str


@dataclass(frozen=True)
class StoryNode:
    node_id: str
    node_type: NodeType
    start_ms: int
    end_ms: int
    segment_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = field(default_factory=tuple)
    confidence: float = 0.0
    rationale: str = ""


def make_node(
    node_id: str,
    node_type: NodeType,
    start_ms: int,
    end_ms: int,
    segment_ids: list[str] | tuple[str, ...],
    *,
    evidence_ids: list[str] | tuple[str, ...] = (),
    confidence: float = 0.0,
    rationale: str = "",
) -> StoryNode:
    if start_ms < 0 or end_ms < start_ms:
        raise ValueError("invalid story node time range")
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    return StoryNode(
        node_id=node_id,
        node_type=node_type,
        start_ms=start_ms,
        end_ms=end_ms,
        segment_ids=tuple(segment_ids),
        evidence_ids=tuple(evidence_ids),
        confidence=confidence,
        rationale=rationale,
    )
