"""Deterministic episode-runtime primitives.

Keeps playback/runtime facts separate from AI interpretation. Consumers can
attach transcript, story and evidence adapters without changing this contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SegmentKind(str, Enum):
    OPENING = "opening"
    STORY = "story"
    CONFLICT = "conflict"
    QUESTION = "question"
    INSIGHT = "insight"
    EMOTION = "emotion"
    QUOTE = "quote"
    TRANSITION = "transition"
    ENDING = "ending"


@dataclass(frozen=True)
class RuntimeSegment:
    segment_id: str
    start_ms: int
    end_ms: int
    kind: SegmentKind
    speaker_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("segment time range is invalid")

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


def validate_segments(segments: list[RuntimeSegment]) -> None:
    """Reject overlapping segments only when they are exact same-layer nodes.

    Different semantic layers may intentionally overlap (e.g. EMOTION inside
    STORY), so callers should provide one semantic layer per validation pass.
    """
    ordered = sorted(segments, key=lambda s: (s.start_ms, s.end_ms))
    for previous, current in zip(ordered, ordered[1:]):
        if current.start_ms < previous.end_ms:
            raise ValueError(
                f"overlapping runtime segments: {previous.segment_id} / {current.segment_id}"
            )
