"""Content pattern candidates persisted by the canonical Shared Learning owner."""
from __future__ import annotations

import datetime as _dt
import errno
import uuid
import hashlib
import json
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import replace
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from .persistence import LearningPersistence

PATTERN_CANDIDATE_DECISION = "EXPERIMENT"
CONTENT_PATTERN_RECORD_KIND = "content_pattern"
_PATTERN_LOCK = threading.RLock()
_PATTERN_LOCK_STATE = threading.local()
PATTERN_TYPES = frozenset({"narrative", "copy", "visual", "motion", "campaign", "evaluation"})

# Six explicit schemas share the existing registry; absent dimensions stay UNKNOWN.
PATTERN_FIELDS = {
    "narrative": ("opening_pattern", "tension_or_question", "progression", "emotional_curve",
        "proof_or_evidence_position", "resolution", "CTA_or_next_action", "avoid_patterns"),
    "copy": ("language", "tone", "title_logic", "opening_logic", "sentence_rhythm", "information_density",
        "proof_requirement", "CTA_logic", "prohibited_phrasing", "multilingual_notes"),
    "visual": ("hierarchy", "focal_object", "composition_logic", "typography_role", "material_role",
        "palette_role", "image_text_relationship", "responsive_or_crop_rules", "accessibility_constraints"),
    "motion": ("before_state", "trigger_or_story_beat", "continuity_principle", "after_state", "timing_range",
        "pacing", "audio_or_text_role", "reduced_motion_or_static_fallback"),
    "campaign": ("campaign_type", "audience_segments", "channels", "narrative_arc", "content_matrix",
        "asset_matrix", "timeline_logic", "evidence_inputs", "decision_points", "measurement_plan",
        "evaluation_plan", "reusable_learnings"),
    "evaluation": ("content_type", "quality_dimensions", "factuality_gate", "brand_fit_gate",
        "originality_gate", "platform_fit_gate", "accessibility_gate", "performance_metrics",
        "human_review_required", "promotion_threshold", "retirement_threshold"),
}


def typed_pattern_payload(kind, payload):
    if kind not in PATTERN_FIELDS or not isinstance(payload, Mapping):
        raise LearningAssetError("PATTERN_TYPED_PAYLOAD_REQUIRED")
    value = dict(payload)
    if kind == "narrative" and "sequence" in value:
        if "progression" in value:
            raise LearningAssetError("PATTERN_PROGRESSION_AMBIGUOUS")
        value["progression"] = value.pop("sequence")
    if set(value) - set(PATTERN_FIELDS[kind]) or not any(v not in (None, "", []) for v in value.values()):
        raise LearningAssetError("PATTERN_TYPED_FIELDS_INVALID")
    # Preserve unknown fields explicitly; these are creative aids, not facts.
    return {key: value.get(key) for key in PATTERN_FIELDS[kind]}


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
    access_context: Mapping[str, Any] = field(default_factory=dict)
    source_bindings: Tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    lifecycle_state: str = "candidate"
    previous_version_hash: Optional[str] = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def validate(self) -> None:
        if self.lifecycle_state not in {"candidate", "retired"}:
            raise LearningAssetError("PATTERN_LIFECYCLE_INVALID")
        if self.access_context:
            if self.asset_type not in PATTERN_TYPES or not self.source_bindings:
                raise LearningAssetError("PATTERN_TYPED_SOURCE_REQUIRED")
            if dict(self.reusable_pattern) != typed_pattern_payload(self.asset_type, self.reusable_pattern):
                raise LearningAssetError("PATTERN_TYPED_FIELDS_INVALID")
            if tuple(str(x.get("evidence_id")) for x in self.source_bindings) != self.source_refs:
                raise LearningAssetError("PATTERN_SOURCE_BINDING_MISMATCH")
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
            "access_context": dict(self.access_context),
            "source_bindings": [dict(x) for x in self.source_bindings],
            "lifecycle_state": self.lifecycle_state,
            "previous_version_hash": self.previous_version_hash,
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
    access_context: Optional[Mapping[str, Any]] = None,
    source_bindings: Sequence[Mapping[str, Any]] = (),
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
        reusable_pattern=typed_pattern_payload(asset_type, reusable_pattern) if access_context else dict(reusable_pattern),
        evidence_requirements=_refs(evidence_requirements),
        originality_boundary=str(originality_boundary),
        legal_or_compliance_boundary=str(legal_or_compliance_boundary),
        counterexamples=_refs(counterexamples),
        access_context=dict(access_context or {}),
        source_bindings=tuple(dict(x) for x in source_bindings),
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
        access_context=record.get("access_context") or {},
        source_bindings=tuple(record.get("source_bindings") or ()),
        lifecycle_state=record.get("lifecycle_state", "candidate"),
        previous_version_hash=record.get("previous_version_hash"),
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

    @contextmanager
    def mutation_guard(self):
        """Serialize this canonical collection across threads and worker processes."""
        with _PATTERN_LOCK:
            if not self._persistence._initialized or not self._persistence._enabled:
                raise LearningAssetError("PATTERN_PERSISTENCE_UNAVAILABLE")
            path = str(self._persistence._path("patterns")) + ".lock"
            held = getattr(_PATTERN_LOCK_STATE, "held", set())
            if path in held:
                yield
                return
            with open(path, "a+b") as lock_file:
                if os.name == "nt":
                    import msvcrt

                    # msvcrt locks from the current offset, including beyond
                    # EOF. All writers lock byte zero without racing to fill it.
                    lock_file.seek(0)
                    while True:
                        try:
                            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                            break
                        except OSError as exc:
                            # LK_LOCK gives up after ten retries. Preserve the
                            # blocking flock contract, but fail closed for
                            # invalid handles and other non-contention errors.
                            if exc.errno != errno.EACCES:
                                raise
                            time.sleep(0.05)
                else:
                    import fcntl

                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                _PATTERN_LOCK_STATE.held = held | {path}
                try:
                    yield
                finally:
                    _PATTERN_LOCK_STATE.held = held
                    if os.name == "nt":
                        lock_file.seek(0)
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def snapshot(self):
        return json.loads(json.dumps(self._persistence.load_collection("patterns") or {}))

    def restore_snapshot(self, snapshot):
        # Caller holds mutation_guard throughout snapshot/write/restore. Never
        # replace an unrelated worker's later update with an old collection.
        result = self._persistence.save_collection("patterns", snapshot, immediate=True)
        if result.get("ok") is not True or result.get("skipped") or self.snapshot() != snapshot:
            raise LearningAssetError("PATTERN_RECOVERY_REQUIRED")

    def save_candidate(self, asset: ContentLearningAsset) -> ContentLearningAsset:
        with self.mutation_guard():
            return self._save_candidate(asset)

    def _save_candidate(self, asset: ContentLearningAsset) -> ContentLearningAsset:
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

    @staticmethod
    def fingerprint(asset: ContentLearningAsset) -> str:
        return hashlib.sha256(json.dumps(asset.to_dict(), sort_keys=True, ensure_ascii=False,
                                        separators=(",", ":"), allow_nan=False).encode()).hexdigest()

    def scoped_candidate(self, asset_id, *, context, current_sources, expected_hash=None):
        stored = self._persistence.load_collection("patterns") or {}
        record = stored.get(asset_id)
        if not isinstance(record, dict) or record.get("access_context") != context or not context:
            raise LearningAssetError("PATTERN_NOT_FOUND")
        asset = _asset_from_record(record)
        asset.validate()
        if asset.lifecycle_state != "candidate":
            raise LearningAssetError("PATTERN_LIFECYCLE_CONFLICT")
        if expected_hash is not None and expected_hash != self.fingerprint(asset):
            raise LearningAssetError("PATTERN_VERSION_CONFLICT")
        if list(asset.source_bindings) != current_sources([int(x) for x in asset.source_refs]):
            raise LearningAssetError("PATTERN_SOURCE_STALE")
        return asset

    def scoped_candidates(self, *, context, current_sources, **filters):
        stored = self._persistence.load_collection("patterns") or {}
        result = []
        for asset_id, record in stored.items():
            if not isinstance(record, dict) or record.get("access_context") != context:
                continue
            try:
                result.append(self.scoped_candidate(asset_id, context=context, current_sources=current_sources))
            except (ValueError, PermissionError, RuntimeError):
                continue
        return retrieve_pattern_candidates(result, **filters)

    def retire(self, asset_id, *, context, current_sources, expected_hash):
        with self.mutation_guard():
            asset = self.scoped_candidate(asset_id, context=context, current_sources=current_sources,
                                          expected_hash=expected_hash)
            retired = replace(asset, lifecycle_state="retired", version=asset.version + ".retired",
                              previous_version_hash=self.fingerprint(asset), updated_at=_now())
            stored = self._persistence.load_collection("patterns") or {}
            stored[asset_id] = retired.to_dict()
            result = self._persistence.save_collection("patterns", stored, immediate=True)
            if result.get("ok") is not True or result.get("skipped") is True:
                raise LearningAssetError("PATTERN_PERSISTENCE_UNAVAILABLE")
            if self._persistence.load_collection("patterns").get(asset_id) != retired.to_dict():
                raise LearningAssetError("PATTERN_PERSISTENCE_READBACK_MISMATCH")
            return retired

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
    admission=None,
    connection=None,
    fence_decision=None,
):
    """Only a server-issued, transaction-bound admission may append a decision.

    Compatibility callers/self-reported ratings cannot promote a candidate.
    """
    if (admission is None or connection is None or fence_decision is None
            or any(value is not None for value in (decision, reviewer, evaluation_status, quality_score))
            or evaluation_refs):
        raise LearningAssetError("CANONICAL_PROMOTION_GATE_NOT_CONNECTED")
    if asset is None or asset.decision != PATTERN_CANDIDATE_DECISION:
        raise LearningAssetError("PATTERN_CANDIDATE_REQUIRED")
    binding = json.loads(admission.binding_json)
    if binding.get("pattern_id") != asset.asset_id or binding.get("candidate_hash") != ContentPatternRegistry.fingerprint(asset):
        raise LearningAssetError("PATTERN_VERSION_CONFLICT")
    return record_pattern_transition(connection, admission=admission, fence_decision=fence_decision)


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
        return asset.lifecycle_state == "candidate" and all(not wanted or wanted in scope or "*" in scope for wanted, scope in checks)

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


# Decisions are immutable canonical Evidence rows, not mutations of candidate
# JSON. Candidate creation/application/retirement retain their existing contract.
_PATTERN_DECISION_FEATURE = "CONTENT_PATTERN_TRANSITION"


def pattern_decisions(connection, *, pattern_id, context):
    from lumenis.shared.evidence import store
    rows = connection.execute("SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=? ORDER BY id",
                              (_PATTERN_DECISION_FEATURE, pattern_id)).fetchall()
    decisions, previous = [], None
    for raw in rows:
        row = dict(raw)
        if (row.get("source") != "shared_learning" or row.get("provider") != __name__
                or row.get("version") != "content-pattern-transition:v1"
                or row.get("integrity_version") != 2 or not store.verify_evidence_record_integrity(row)):
            raise LearningAssetError("PATTERN_DECISION_INTEGRITY_FAILED")
        inputs = json.loads(row.get("inputs_json") or "{}")
        if inputs.get("context") != context:
            continue
        value = json.loads(row.get("outputs_json") or "{}")
        if (value.get("pattern_id") != pattern_id or value.get("previous_decision_id") != previous
                or value.get("action") not in {"promote", "rollback", "disable"}
                or value.get("context") != context):
            raise LearningAssetError("PATTERN_DECISION_CHAIN_INVALID")
        value = {**value, "decision_id": row["id"], "receipt_hash": row["integrity_digest"]}
        decisions.append(value)
        previous = row["id"]
    return decisions


def current_pattern_decision(connection, *, pattern_id, context):
    history = pattern_decisions(connection, pattern_id=pattern_id, context=context)
    return history[-1] if history else None


def record_pattern_transition(connection, *, admission, fence_decision):
    """One approved derived decision. No source facts, model or candidate is rewritten."""
    from lumenis.system.security import permission as p
    from lumenis.system.security.effect_fence import get_effect_fence
    from lumenis.shared.evidence import store
    p.validate_pattern_transition_admission(admission, connection=connection)
    checked = get_effect_fence().check_pattern_transition(admission, connection=connection, phase="before_write")
    if checked != fence_decision:
        raise PermissionError("PATTERN_FENCE_DECISION_CHANGED")
    binding = json.loads(admission.binding_json)
    value = {"pattern_id": binding["pattern_id"], "context": binding["context"],
             "candidate_hash": binding["candidate_hash"], "action": binding["action"],
             "previous_decision_id": binding["previous_decision_id"],
             "selected_evaluation_id": binding["selected_evaluation_id"],
             "target_decision_id": binding["target_decision_id"],
             "approval_id": admission.approval_id, "binding_hash": admission.binding_hash,
             "activation_resource": admission.activation_resource, "write_resource": admission.write_resource,
             "request_id": binding["request_id"], "truth_status": "DERIVED_REVIEWED_CAPABILITY",
             "effective": binding["action"] != "disable"}
    eid = store.record_evidence(connection=connection, source="shared_learning", product="SHARED",
        feature_id=_PATTERN_DECISION_FEATURE, asset_id=binding["pattern_id"], provider=__name__,
        version="content-pattern-transition:v1", inputs={"context": binding["context"]},
        outputs=value, result="RECORDED", status="derived")
    current = current_pattern_decision(connection, pattern_id=binding["pattern_id"], context=binding["context"])
    if not current or current["decision_id"] != eid:
        raise LearningAssetError("PATTERN_DECISION_READBACK_MISMATCH")
    return current
