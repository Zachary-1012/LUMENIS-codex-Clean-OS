"""Shared Content & Creation contracts.

This package is a typed, non-persistent contract layer for Content Studio.
Evidence, Artifact, Permission, Evaluation and Learning remain owned by their
existing canonical packages; these helpers do not create a second truth store
or a publishing path.
"""

from .contracts import (
    EmotionExperiencePattern,
    NarrativePattern,
    Shot,
    ShotPlan,
    VisualMotifPattern,
    WhiteDescriptionPattern,
)
from .video_editing import (
    AudioMix,
    EditDecision,
    EditDecisionList,
    MediaAsset,
    Timeline,
    TimelineClip,
    TimelineTrack,
    VideoEditingError,
    apply_edl_suggestion,
    fingerprint_local_media,
    propose_edl,
)

__all__ = [
    "EmotionExperiencePattern",
    "NarrativePattern",
    "Shot",
    "ShotPlan",
    "VisualMotifPattern",
    "WhiteDescriptionPattern",
    "AudioMix",
    "EditDecision",
    "EditDecisionList",
    "MediaAsset",
    "Timeline",
    "TimelineClip",
    "TimelineTrack",
    "VideoEditingError",
    "apply_edl_suggestion",
    "fingerprint_local_media",
    "propose_edl",
]
