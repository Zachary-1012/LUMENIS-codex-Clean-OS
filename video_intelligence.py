"""Passive multimodal video understanding for already-rendered evidence.

Design boundary:
- This module NEVER downloads media from a platform.
- It NEVER fetches XHS media URLs.
- It only analyzes evidence explicitly supplied by an authorized browser/runtime.
- Subject ownership remains the responsibility of the existing hard-filter layer.

The engine is intentionally provider-agnostic. A provider may consume frames,
OCR text and/or ASR text, but the normalized result is deterministic and
traceable to the supplied evidence IDs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional


@dataclass(frozen=True)
class VideoEvidence:
    """Evidence already visible/rendered by an authorized runtime."""

    evidence_id: str
    note_id: str
    frame_refs: List[str] = field(default_factory=list)
    ocr_text: str = ""
    asr_text: str = ""
    duration_ms: Optional[int] = None
    captured_at: Optional[str] = None
    source: str = "browser_rendered"


@dataclass(frozen=True)
class VideoAnalysis:
    """Normalized multimodal analysis result; no platform-fetch metadata."""

    evidence_id: str
    note_id: str
    transcript: str
    on_screen_text: str
    scenes: List[Dict[str, Any]]
    entities: List[str]
    topics: List[str]
    sentiment: str
    risk_level: str
    marketing_signals: List[str]
    confidence: float
    provider: str = "none"
    model_version: str = "none"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "note_id": self.note_id,
            "transcript": self.transcript,
            "on_screen_text": self.on_screen_text,
            "scenes": self.scenes,
            "entities": self.entities,
            "topics": self.topics,
            "sentiment": self.sentiment,
            "risk_level": self.risk_level,
            "marketing_signals": self.marketing_signals,
            "confidence": self.confidence,
            "provider": self.provider,
            "model_version": self.model_version,
        }


class VideoIntelligenceEngine:
    """Provider-agnostic passive video analysis boundary.

    A provider callable receives only the evidence object. The callable is
    responsible for multimodal inference; this layer normalizes and validates
    the result. No network/platform access is performed here.
    """

    def __init__(self, provider: Any = None, provider_name: str = "none", model_version: str = "none") -> None:
        self.provider = provider
        self.provider_name = provider_name
        self.model_version = model_version

    def analyze(self, evidence: VideoEvidence) -> VideoAnalysis:
        if not evidence.evidence_id or not evidence.note_id:
            raise ValueError("evidence_id and note_id are required")
        if evidence.source != "browser_rendered":
            raise ValueError("video intelligence accepts browser-rendered evidence only")

        if self.provider is None:
            result: Mapping[str, Any] = {}
        elif hasattr(self.provider, "analyze_video"):
            result = self.provider.analyze_video(evidence)
        elif callable(self.provider):
            result = self.provider(evidence)
        else:
            raise TypeError("provider must be callable or implement analyze_video()")

        confidence = float(result.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))

        return VideoAnalysis(
            evidence_id=evidence.evidence_id,
            note_id=evidence.note_id,
            transcript=evidence.asr_text,
            on_screen_text=evidence.ocr_text,
            scenes=list(result.get("scenes", [])),
            entities=list(result.get("entities", [])),
            topics=list(result.get("topics", [])),
            sentiment=str(result.get("sentiment", "unknown")),
            risk_level=str(result.get("risk_level", "unknown")),
            marketing_signals=list(result.get("marketing_signals", [])),
            confidence=confidence,
            provider=self.provider_name,
            model_version=self.model_version,
        )
