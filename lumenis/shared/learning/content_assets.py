"""Content pattern candidates persisted by the canonical Shared Learning owner."""
from __future__ import annotations

import datetime as _dt
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from .persistence import LearningPersistence

PATTERN_CANDIDATE_DECISION = "EXPERIMENT"
CONTENT_PATTERN_RECORD_KIND = "content_pattern"
_EVALUATION_STATUSES = frozenset({"unknown", "pass", "fail"})
_CREATOR_STYLE_MARKERS = (
    "不知名鸽子",
    "itsrae",
    "燃烧的陀螺仪",
    "沢人",
    "风格生成器",
    "style clone",
    "creator style",
)


class LearningAssetError(ValueError):
    """Raised when a learning asset would copy a creator or bypass review."""


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _refs(values: Iterable[Any]) -> Tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = (values,)
    return tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


@dataclass(frozen=True)
class ContentLearningAsset:
    asset_id: str
    asset_type: str
    title: str
    source_kind: str
    source_refs: Tuple[str, ...]
    evaluation_refs: Tuple[str, ...] = field(default_factory=tuple)
    evaluation_status: str = "unknown"
    platform_scope: Tuple[str, ...] = field(default_factory=tuple)
    format_scope: Tuple[str, ...] = field(default_factory=tuple)
    audience_scope: Tuple[str, ...] = field(default_factory=tuple)
    objective_scope: Tuple[str, ...] = field(default_factory=tuple)
    observed_problem: str = ""
    extracted_principle: str = ""
    reusable_pattern: Mapping[str, Any] = field(default_factory=dict)
    evidence_requirements: Tuple[str, ...] = field(default_factory=tuple)
    originality_boundary: str = ""
    legal_or_compliance_boundary: str = ""
    counterexamples: Tuple[str, ...] = field(default_factory=tuple)
    quality_score: Optional[float] = None
    confidence: Optional[float] = None
    decision: str = "EXPERIMENT"
    version: str = "1.0.0"
    reviewer: Optional[str] = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def validate(self) -> None:
        searchable = " ".join((self.title, self.extracted_principle, str(dict(self.reusable_pattern)))).lower()
        if any(marker.lower() in searchable for marker in _CREATOR_STYLE_MARKERS):
            raise LearningAssetError("CREATOR_SPECIFIC_STYLE_NOT_ALLOWED")
        if self.decision != PATTERN_CANDIDATE_DECISION:
            raise LearningAssetError("PATTERN_CANDIDATE_MUST_REMAIN_EXPERIMENT")
        if not self.source_refs or not self.extracted_principle:
            raise LearningAssetError("LEARNING_ASSET_REQUIRES_SOURCE_AND_PRINCIPLE")
        if not any((self.platform_scope, self.format_scope, self.audience_scope, self.objective_scope)):
            raise LearningAssetError("LEARNING_ASSET_REQUIRES_SCOPE")
        if not self.originality_boundary or not self.legal_or_compliance_boundary:
            raise LearningAssetError("LEARNING_ASSET_REQUIRES_ORIGINALITY_AND_LEGAL_BOUNDARY")
        if not self.counterexamples:
            raise LearningAssetError("LEARNING_ASSET_REQUIRES_COUNTEREXAMPLES")
        if self.evaluation_status not in _EVALUATION_STATUSES:
            raise LearningAssetError("INVALID_EVALUATION_STATUS")
        for value in (self.quality_score, self.confidence):
            if value is not None:
                try:
                    score = float(value)
                except (TypeError, ValueError) as exc:
                    raise LearningAssetError("LEARNING_SCORES_MUST_BE_0_TO_1") from exc
                if not 0 <= score <= 1:
                    raise LearningAssetError("LEARNING_SCORES_MUST_BE_0_TO_1")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_kind": CONTENT_PATTERN_RECORD_KIND,
            "id": self.asset_id,
            "type": self.asset_type,
            "title": self.title,
            "source_kind": self.source_kind,
            "source_refs": list(self.source_refs),
            "evaluation_refs": list(self.evaluation_refs),
            "evaluation_status": self.evaluation_status,
            "platform_scope": list(self.platform_scope),
            "format_scope": list(self.format_scope),
            "audience_scope": list(self.audience_scope),
            "objective_scope": list(self.objective_scope),
            "observed_problem": self.observed_problem,
            "extracted_principle": self.extracted_principle,
            "reusable_pattern": dict(self.reusable_pattern),
            "evidence_requirements": list(self.evidence_requirements),
            "originality_boundary": self.originality_boundary,
            "legal_or_compliance_boundary": self.legal_or_compliance_boundary,
            "counterexamples": list(self.counterexamples),
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "decision": self.decision,
            "version": self.version,
            "reviewer": self.reviewer,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def create_pattern_candidate(
    *,
    asset_type: str,
    title: str,
    source_kind: str,
    source_refs: Sequence[str],
    evaluation_refs: Sequence[str] = (),
    extracted_principle: str,
    reusable_pattern: Mapping[str, Any],
    evidence_requirements: Sequence[str],
    originality_boundary: str,
    legal_or_compliance_boundary: str,
    counterexamples: Sequence[str],
    platform_scope: Sequence[str] = (),
    format_scope: Sequence[str] = (),
    audience_scope: Sequence[str] = (),
    objective_scope: Sequence[str] = (),
) -> ContentLearningAsset:
    candidate = ContentLearningAsset(
        asset_id=f"CLA-{uuid.uuid4().hex[:12]}",
        asset_type=str(asset_type),
        title=str(title),
        source_kind=str(source_kind),
        source_refs=_refs(source_refs),
        evaluation_refs=_refs(evaluation_refs),
        platform_scope=_refs(platform_scope),
        format_scope=_refs(format_scope),
        audience_scope=_refs(audience_scope),
        objective_scope=_refs(objective_scope),
        extracted_principle=str(extracted_principle),
        reusable_pattern=dict(reusable_pattern),
        evidence_requirements=_refs(evidence_requirements),
        originality_boundary=str(originality_boundary),
        legal_or_compliance_boundary=str(legal_or_compliance_boundary),
        counterexamples=_refs(counterexamples),
    )
    candidate.validate()
    return candidate


def _asset_from_record(record: Mapping[str, Any]) -> ContentLearningAsset:
    return ContentLearningAsset(
        asset_id=str(record.get("id") or ""),
        asset_type=str(record.get("type") or ""),
        title=str(record.get("title") or ""),
        source_kind=str(record.get("source_kind") or ""),
        source_refs=_refs(record.get("source_refs") or ()),
        evaluation_refs=_refs(record.get("evaluation_refs") or ()),
        evaluation_status=str(record.get("evaluation_status") or "unknown").strip().lower(),
        platform_scope=_refs(record.get("platform_scope") or ()),
        format_scope=_refs(record.get("format_scope") or ()),
        audience_scope=_refs(record.get("audience_scope") or ()),
        objective_scope=_refs(record.get("objective_scope") or ()),
        observed_problem=str(record.get("observed_problem") or ""),
        extracted_principle=str(record.get("extracted_principle") or ""),
        reusable_pattern=record.get("reusable_pattern") if isinstance(record.get("reusable_pattern"), dict) else {},
        evidence_requirements=_refs(record.get("evidence_requirements") or ()),
        originality_boundary=str(record.get("originality_boundary") or ""),
        legal_or_compliance_boundary=str(record.get("legal_or_compliance_boundary") or ""),
        counterexamples=_refs(record.get("counterexamples") or ()),
        quality_score=record.get("quality_score"),
        confidence=record.get("confidence"),
        decision=str(record.get("decision") or PATTERN_CANDIDATE_DECISION),
        version=str(record.get("version") or "1.0.0"),
        reviewer=record.get("reviewer"),
        created_at=str(record.get("created_at") or _now()),
        updated_at=str(record.get("updated_at") or _now()),
    )


def _is_content_pattern_record(record: Mapping[str, Any]) -> bool:
    if record.get("record_kind") == CONTENT_PATTERN_RECORD_KIND:
        return True
    # Recognize the prior untagged asset shape so a forged ADOPT cannot hide as
    # an unrelated legacy pattern and be silently accepted or re-emitted.
    return all(key in record for key in ("decision", "source_refs", "extracted_principle"))


class ContentPatternRegistry:
    """Narrow adapter over Shared Learning's existing ``patterns`` collection.

    The adapter accepts an initialized canonical LearningPersistence instance.
    It owns no path, database, or independent persistence format.
    """

    def __init__(self, persistence: LearningPersistence):
        self._persistence = persistence

    def save_candidate(self, asset: ContentLearningAsset) -> ContentLearningAsset:
        if not isinstance(asset, ContentLearningAsset):
            raise LearningAssetError("CONTENT_PATTERN_ASSET_REQUIRED")
        asset.validate()
        current = self._persistence.load_collection("patterns")
        if current is None:
            current = {}
        if not isinstance(current, dict):
            raise LearningAssetError("PATTERN_COLLECTION_INVALID")
        serialized = asset.to_dict()
        existing = current.get(asset.asset_id)
        if existing is not None and existing != serialized:
            raise LearningAssetError("PATTERN_ID_CONFLICT")
        current[asset.asset_id] = serialized
        result = self._persistence.save_collection("patterns", current, immediate=True)
        if not isinstance(result, dict) or result.get("ok") is not True or result.get("skipped") is True:
            raise LearningAssetError("PATTERN_PERSISTENCE_UNAVAILABLE")
        readback = self._persistence.load_collection("patterns")
        if not isinstance(readback, dict) or readback.get(asset.asset_id) != serialized:
            raise LearningAssetError("PATTERN_PERSISTENCE_READBACK_MISMATCH")
        readback_asset = _asset_from_record(readback[asset.asset_id])
        readback_asset.validate()
        return asset

    def retrieve_candidates(
        self,
        *,
        platform: str = "",
        format_name: str = "",
        audience: str = "",
        objective: str = "",
        limit: int = 20,
    ) -> Tuple[ContentLearningAsset, ...]:
        stored = self._persistence.load_collection("patterns")
        if stored is None:
            return ()
        if not isinstance(stored, dict):
            raise LearningAssetError("PATTERN_COLLECTION_INVALID")
        assets = []
        for record in stored.values():
            if not isinstance(record, dict) or not _is_content_pattern_record(record):
                continue
            asset = _asset_from_record(record)
            asset.validate()
            assets.append(asset)
        return retrieve_pattern_candidates(
            assets,
            platform=platform,
            format_name=format_name,
            audience=audience,
            objective=objective,
            limit=limit,
        )


def promote_pattern(
    asset: Optional[ContentLearningAsset] = None,
    *,
    decision: Optional[str] = None,
    reviewer: Optional[str] = None,
    evaluation_status: Optional[str] = None,
    evaluation_refs: Sequence[str] = (),
    quality_score: Optional[float] = None,
) -> ContentLearningAsset:
    """Fail closed until canonical Evaluation and Permission gates are connected."""
    raise LearningAssetError("CANONICAL_PROMOTION_GATE_NOT_CONNECTED")


def retrieve_pattern_candidates(
    assets: Iterable[ContentLearningAsset],
    *,
    platform: str = "",
    format_name: str = "",
    audience: str = "",
    objective: str = "",
    limit: int = 20,
) -> Tuple[ContentLearningAsset, ...]:
    """Return scoped, non-retired patterns for a real Brief."""
    def matches(asset: ContentLearningAsset) -> bool:
        asset.validate()
        checks = (
            (platform, asset.platform_scope),
            (format_name, asset.format_scope),
            (audience, asset.audience_scope),
            (objective, asset.objective_scope),
        )
        return all(not wanted or wanted in scope or "*" in scope for wanted, scope in checks)

    return tuple(asset for asset in assets if matches(asset))[: max(0, int(limit))]


__all__ = [
    "ContentLearningAsset",
    "ContentPatternRegistry",
    "CONTENT_PATTERN_RECORD_KIND",
    "LearningAssetError",
    "PATTERN_CANDIDATE_DECISION",
    "create_pattern_candidate",
    "promote_pattern",
    "retrieve_pattern_candidates",
]
