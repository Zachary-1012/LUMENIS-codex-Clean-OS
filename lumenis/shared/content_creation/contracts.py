"""Source-backed Content & Creation structures.

The structures are deliberately optional and composable.  They describe a
production artifact and its reasoning; they are not a UI schema, a model
prompt, or a replacement for Evidence/Permission truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


class ContentContractError(ValueError):
    """Raised when a content contract would lose provenance or intent."""


def _strings(values: Iterable[Any]) -> Tuple[str, ...]:
    return tuple(str(value).strip() for value in values if str(value).strip())


@dataclass(frozen=True)
class NarrativePattern:
    story_premise: str = ""
    observation: str = ""
    conflict: str = ""
    progression: str = ""
    resolution: str = ""
    script_first: bool = True
    experience_first: bool = False
    viewer_inference: str = ""
    source_refs: Tuple[str, ...] = field(default_factory=tuple)
    counterexamples: Tuple[str, ...] = field(default_factory=tuple)

    def validate(self) -> None:
        if not any((self.story_premise, self.observation, self.progression, self.resolution)):
            raise ContentContractError("NARRATIVE_PATTERN_REQUIRES_STORY_STRUCTURE")
        if not self.source_refs:
            raise ContentContractError("NARRATIVE_PATTERN_REQUIRES_SOURCE_REFS")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_premise": self.story_premise,
            "observation": self.observation,
            "conflict": self.conflict,
            "progression": self.progression,
            "resolution": self.resolution,
            "script_first": self.script_first,
            "experience_first": self.experience_first,
            "viewer_inference": self.viewer_inference,
            "source_refs": list(self.source_refs),
            "counterexamples": list(self.counterexamples),
        }


@dataclass(frozen=True)
class WhiteDescriptionPattern:
    concrete_object: str = ""
    action: str = ""
    dialogue: str = ""
    environmental_sound: str = ""
    silence: str = ""
    abstract_emotion_word_density: Optional[float] = None
    explanatory_narration_redundancy: Optional[float] = None
    image_text_duplication: Optional[float] = None
    source_refs: Tuple[str, ...] = field(default_factory=tuple)

    def validate(self) -> None:
        if not any((self.concrete_object, self.action, self.dialogue, self.environmental_sound)):
            raise ContentContractError("WHITE_DESCRIPTION_REQUIRES_CONCRETE_SIGNAL")
        if not self.source_refs:
            raise ContentContractError("WHITE_DESCRIPTION_REQUIRES_SOURCE_REFS")
        for value in (
            self.abstract_emotion_word_density,
            self.explanatory_narration_redundancy,
            self.image_text_duplication,
        ):
            if value is not None and not 0 <= float(value) <= 1:
                raise ContentContractError("WHITE_DESCRIPTION_METRICS_MUST_BE_0_TO_1")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concrete_object": self.concrete_object,
            "action": self.action,
            "dialogue": self.dialogue,
            "environmental_sound": self.environmental_sound,
            "silence": self.silence,
            "abstract_emotion_word_density": self.abstract_emotion_word_density,
            "explanatory_narration_redundancy": self.explanatory_narration_redundancy,
            "image_text_duplication": self.image_text_duplication,
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True)
class EmotionExperiencePattern:
    trigger: str = ""
    context: str = ""
    sensory_cue: str = ""
    relationship: str = ""
    contradiction: str = ""
    before: str = ""
    turning_point: str = ""
    after: str = ""
    expression_density: Optional[float] = None
    source_refs: Tuple[str, ...] = field(default_factory=tuple)
    counterexamples: Tuple[str, ...] = field(default_factory=tuple)

    def validate(self) -> None:
        if not self.trigger or not self.turning_point:
            raise ContentContractError("EMOTION_PATTERN_REQUIRES_TRIGGER_AND_TURNING_POINT")
        if not self.source_refs:
            raise ContentContractError("EMOTION_PATTERN_REQUIRES_SOURCE_REFS")
        if self.expression_density is not None and not 0 <= float(self.expression_density) <= 1:
            raise ContentContractError("EMOTION_EXPRESSION_DENSITY_MUST_BE_0_TO_1")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger": self.trigger,
            "context": self.context,
            "sensory_cue": self.sensory_cue,
            "relationship": self.relationship,
            "contradiction": self.contradiction,
            "before": self.before,
            "turning_point": self.turning_point,
            "after": self.after,
            "expression_density": self.expression_density,
            "source_refs": list(self.source_refs),
            "counterexamples": list(self.counterexamples),
        }


@dataclass(frozen=True)
class VisualMotifPattern:
    motif: str = ""
    first_meaning: str = ""
    recurrence: str = ""
    transformation: str = ""
    final_payoff: str = ""
    motif_kind: str = "object"
    source_refs: Tuple[str, ...] = field(default_factory=tuple)

    def validate(self) -> None:
        if not self.motif or not self.first_meaning or not self.final_payoff:
            raise ContentContractError("VISUAL_MOTIF_REQUIRES_MEANING_AND_PAYOFF")
        if not self.source_refs:
            raise ContentContractError("VISUAL_MOTIF_REQUIRES_SOURCE_REFS")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "motif": self.motif,
            "first_meaning": self.first_meaning,
            "recurrence": self.recurrence,
            "transformation": self.transformation,
            "final_payoff": self.final_payoff,
            "motif_kind": self.motif_kind,
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True)
class Shot:
    narrative_beat: str = ""
    emotional_beat: str = ""
    shot_purpose: str = ""
    visual_motif: str = ""
    shot_size: str = ""
    camera_motion: str = ""
    subject_action: str = ""
    continuity: str = ""
    audio_role: str = ""
    original_sound: str = ""
    voice_over: str = ""
    text_subtitles: str = ""
    transition_type: str = "cut"
    transition_reason: str = ""
    duration_sec: Optional[float] = None
    hold_sec: Optional[float] = None
    pacing: str = ""
    evidence_refs: Tuple[str, ...] = field(default_factory=tuple)

    def validate(self) -> None:
        for value in (self.duration_sec, self.hold_sec):
            if value is not None and float(value) < 0:
                raise ContentContractError("SHOT_TIMING_MUST_NOT_BE_NEGATIVE")
        if self.transition_type and self.transition_type != "cut" and not self.transition_reason:
            raise ContentContractError("TRANSITION_REASON_REQUIRED")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "narrative_beat": self.narrative_beat,
            "emotional_beat": self.emotional_beat,
            "shot_purpose": self.shot_purpose,
            "visual_motif": self.visual_motif,
            "shot_size": self.shot_size,
            "camera_motion": self.camera_motion,
            "subject_action": self.subject_action,
            "continuity": self.continuity,
            "audio_role": self.audio_role,
            "original_sound": self.original_sound,
            "voice_over": self.voice_over,
            "text_subtitles": self.text_subtitles,
            "transition_type": self.transition_type,
            "transition_reason": self.transition_reason,
            "duration_sec": self.duration_sec,
            "hold_sec": self.hold_sec,
            "pacing": self.pacing,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class ShotPlan:
    shots: Tuple[Shot, ...]
    brief_ref: str = ""
    evidence_refs: Tuple[str, ...] = field(default_factory=tuple)

    def validate(self) -> None:
        if not self.shots:
            raise ContentContractError("SHOT_PLAN_REQUIRES_SHOTS")
        for shot in self.shots:
            shot.validate()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brief_ref": self.brief_ref,
            "evidence_refs": list(self.evidence_refs),
            "shots": [shot.to_dict() for shot in self.shots],
        }


__all__ = [
    "ContentContractError",
    "EmotionExperiencePattern",
    "NarrativePattern",
    "Shot",
    "ShotPlan",
    "VisualMotifPattern",
    "WhiteDescriptionPattern",
]
