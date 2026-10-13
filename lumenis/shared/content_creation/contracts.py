"""Source-backed Content & Creation structures.

The structures are deliberately optional and composable.  They describe a
production artifact and its reasoning; they are not a UI schema, a model
prompt, or a replacement for Evidence/Permission truth.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Tuple


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


@dataclass(frozen=True)
class AudiovisualPlan:
    """Immutable authoring intent over existing ShotPlan/PodcastPlan contracts.

    Method references are research provenance, never material Evidence or an
    execution grant. Predicate observations remain declarations to revalidate
    on actual media. This contract selects no footage and renders no output.
    """

    document: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.document, str):
            raise ContentContractError("AV_PLAN_INPUT_INVALID")

        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ContentContractError("AV_PLAN_DUPLICATE_KEY")
                result[key] = value
            return result

        def constant(_value):
            raise ContentContractError("AV_PLAN_NONFINITE_VALUE")

        try:
            if len(self.document.encode("utf-8")) > 512 * 1024:
                raise ContentContractError("AV_PLAN_INPUT_INVALID")
            value = json.loads(self.document, object_pairs_hook=pairs, parse_constant=constant)
            self._validate(value)
            serialized = json.dumps(value, ensure_ascii=False, allow_nan=False,
                                    sort_keys=True, separators=(",", ":"))
            serialized.encode("utf-8")
        except (TypeError, ValueError, RecursionError, OverflowError) as exc:
            if isinstance(exc, ContentContractError):
                raise
            raise ContentContractError("AV_PLAN_INPUT_INVALID") from exc
        object.__setattr__(self, "document", serialized)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> AudiovisualPlan:
        try:
            serialized = json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError, RecursionError, OverflowError) as exc:
            raise ContentContractError("AV_PLAN_INPUT_INVALID") from exc
        return cls(serialized)

    @staticmethod
    def _provenance(value, *, unknown=False):
        kinds = {"USER_EXPLICIT", "MEDIA_PROBE", "DIRECT_OBSERVATION", "VERIFIED_DOCUMENTATION",
                 "MEASURED", "PLANNER_PROPOSAL", "UNKNOWN"}
        if (not isinstance(value, dict) or set(value) != {"kind", "locator"}
                or value["kind"] not in kinds
                or (unknown and value["kind"] != "UNKNOWN")
                or (value["kind"] == "UNKNOWN" and value["locator"] is not None)
                or (value["kind"] != "UNKNOWN" and
                    (not isinstance(value["locator"], str) or not value["locator"].strip()))):
            raise ContentContractError("AV_PLAN_PROVENANCE_INVALID")

    @staticmethod
    def _seconds(value):
        if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
            raise ContentContractError("AV_PLAN_DURATION_INVALID")

    @classmethod
    def _plan_duration(cls, output):
        plan = output["plan"]
        if plan is None:
            return None
        if output["medium"] == "video":
            if not isinstance(plan, dict) or set(plan) != {"shots", "brief_ref", "evidence_refs"}:
                raise ContentContractError("AV_PLAN_SHOT_PLAN_INVALID")
            if not isinstance(plan["shots"], list) or not 1 <= len(plan["shots"]) <= 128:
                raise ContentContractError("AV_PLAN_SHOT_PLAN_INVALID")
            if (not isinstance(plan["brief_ref"], str)
                    or not isinstance(plan["evidence_refs"], list)
                    or any(not isinstance(ref, str) for ref in plan["evidence_refs"])):
                raise ContentContractError("AV_PLAN_SHOT_PLAN_INVALID")
            for fields in plan["shots"]:
                if (not isinstance(fields, dict)
                        or any(not isinstance(text, str) for name, text in fields.items()
                               if name not in {"duration_sec", "hold_sec", "evidence_refs"})
                        or not isinstance(fields.get("evidence_refs", []), list)
                        or any(not isinstance(ref, str) for ref in fields.get("evidence_refs", []))):
                    raise ContentContractError("AV_PLAN_SHOT_PLAN_INVALID")
            shot_plan = ShotPlan(tuple(Shot(**shot) for shot in plan["shots"]),
                                 brief_ref=plan["brief_ref"], evidence_refs=tuple(plan["evidence_refs"]))
            shot_plan.validate()
            if shot_plan.to_dict() != plan:
                raise ContentContractError("AV_PLAN_SHOT_PLAN_INVALID")
            durations = []
            for shot in shot_plan.shots:
                for seconds in (shot.duration_sec, shot.hold_sec):
                    if seconds is not None:
                        cls._seconds(seconds)
                if ((output["sound"]["voice"] == "forbidden"
                     and (shot.voice_over or shot.audio_role in {"voice", "voiceover", "voice_over"}))
                        or (output["sound"]["original"] == "forbidden"
                            and (shot.original_sound or shot.audio_role == "original"))
                        or (output["sound"]["music"] == "forbidden" and shot.audio_role in {"bgm", "music"})):
                    raise ContentContractError("AV_PLAN_SOUND_CONFLICT")
                durations.append(shot.duration_sec)
            return None if None in durations else math.fsum(durations)
        from podcast.intelligence.episode_runtime import PodcastPlan
        podcast = PodcastPlan.from_dict(plan)
        if all(policy == "forbidden" for policy in output["sound"].values()):
            raise ContentContractError("AV_PLAN_SOUND_CONFLICT")
        return math.fsum(segment.duration for segment in podcast.segments)

    @classmethod
    def _validate(cls, value):
        if (not isinstance(value, dict) or set(value) != {"schema", "brief_text", "method_source", "outputs", "rule_assessments"}
                or value["schema"] != "lumenis.audiovisual-plan/v1"
                or not isinstance(value["brief_text"], str) or not value["brief_text"].strip()):
            raise ContentContractError("AV_PLAN_INPUT_INVALID")
        method = value["method_source"]
        if (not isinstance(method, dict) or set(method) != {"reference", "sha256"}
                or not isinstance(method["reference"], str) or not method["reference"].strip()
                or not isinstance(method["sha256"], str) or len(method["sha256"]) != 64
                or any(char not in "0123456789abcdef" for char in method["sha256"])):
            raise ContentContractError("AV_PLAN_METHOD_SOURCE_INVALID")
        outputs = value["outputs"]
        if not isinstance(outputs, list) or not 1 <= len(outputs) <= 16:
            raise ContentContractError("AV_PLAN_OUTPUTS_INVALID")
        ids = set()
        for output in outputs:
            if (not isinstance(output, dict) or set(output) != {"output_id", "medium", "purpose", "canvas_ratio",
                    "duration", "sound", "languages", "constraints", "provenance", "plan"}
                    or not isinstance(output["output_id"], str) or not output["output_id"].strip()
                    or output["output_id"] in ids or output["medium"] not in {"video", "podcast"}
                    or not isinstance(output["purpose"], str) or not output["purpose"].strip()
                    or output["canvas_ratio"] not in {None, "16:9", "9:16", "1:1"}
                    or (output["medium"] == "podcast" and output["canvas_ratio"] is not None)
                    or not isinstance(output["languages"], list)
                    or any(not isinstance(language, str) or not language.strip() for language in output["languages"])
                    or len(set(output["languages"])) != len(output["languages"])
                    or not isinstance(output["constraints"], dict)):
                raise ContentContractError("AV_PLAN_OUTPUT_INVALID")
            ids.add(output["output_id"])
            duration, sound = output["duration"], output["sound"]
            if not isinstance(duration, dict) or set(duration) != {"min_seconds", "max_seconds", "tolerance_seconds"}:
                raise ContentContractError("AV_PLAN_DURATION_INVALID")
            for seconds in duration.values():
                if seconds is not None:
                    cls._seconds(seconds)
            if (duration["min_seconds"] is not None and duration["max_seconds"] is not None
                    and duration["min_seconds"] > duration["max_seconds"]):
                raise ContentContractError("AV_PLAN_DURATION_INVALID")
            if (not isinstance(sound, dict) or set(sound) != {"original", "voice", "music"}
                    or any(policy not in {"required", "optional", "forbidden", "unknown"} for policy in sound.values())):
                raise ContentContractError("AV_PLAN_SOUND_INVALID")
            provenance = output["provenance"]
            if not isinstance(provenance, dict) or set(provenance) != {"purpose", "canvas_ratio", "duration", "languages", "constraints", "original", "voice", "music"}:
                raise ContentContractError("AV_PLAN_PROVENANCE_INVALID")
            for name, source in provenance.items():
                unknown = ((name in sound and sound[name] == "unknown")
                           or (name == "duration" and all(seconds is None for seconds in duration.values()))
                           or (name == "languages" and not output["languages"])
                           or (name == "canvas_ratio" and output["medium"] == "video" and output[name] is None))
                cls._provenance(source, unknown=unknown)
            total = cls._plan_duration(output)
            tolerance = duration["tolerance_seconds"]
            if (total is not None and tolerance is not None
                    and ((duration["min_seconds"] is not None and total < duration["min_seconds"] - tolerance)
                         or (duration["max_seconds"] is not None and total > duration["max_seconds"] + tolerance))):
                raise ContentContractError("AV_PLAN_PLANNED_DURATION_CONFLICT")
        rules = value["rule_assessments"]
        if not isinstance(rules, list) or len(rules) > 128:
            raise ContentContractError("AV_PLAN_RULE_INVALID")
        seen = set()
        for rule in rules:
            if (not isinstance(rule, dict) or set(rule) != {"rule_ref", "output_ids", "required_conditions", "exclusions"}
                    or not isinstance(rule["rule_ref"], str) or not rule["rule_ref"].strip()
                    or rule["rule_ref"] in seen or not isinstance(rule["output_ids"], list)
                    or not rule["output_ids"] or any(item not in ids for item in rule["output_ids"])
                    or len(set(rule["output_ids"])) != len(rule["output_ids"])
                    or not isinstance(rule["required_conditions"], list) or not rule["required_conditions"]
                    or not isinstance(rule["exclusions"], list)):
                raise ContentContractError("AV_PLAN_RULE_INVALID")
            seen.add(rule["rule_ref"])
            for predicate in rule["required_conditions"] + rule["exclusions"]:
                if (not isinstance(predicate, dict) or set(predicate) != {"predicate", "value", "provenance"}
                        or not isinstance(predicate["predicate"], str) or not predicate["predicate"].strip()
                        or (predicate["value"] is not None and type(predicate["value"]) is not bool)):
                    raise ContentContractError("AV_PLAN_PREDICATE_INVALID")
                cls._provenance(predicate["provenance"], unknown=predicate["value"] is None)

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self.document)

    def snapshot(self) -> dict[str, Any]:
        value = self.to_dict()
        decisions = []
        for rule in value["rule_assessments"]:
            conditions, exclusions = rule["required_conditions"], rule["exclusions"]
            confirmed = lambda item: item["provenance"]["kind"] not in {"UNKNOWN", "PLANNER_PROPOSAL"}
            if any(item["value"] is True and confirmed(item) for item in exclusions):
                decision = "EXCLUDED"
            elif any(item["value"] is False and confirmed(item) for item in conditions):
                decision = "NOT_APPLICABLE"
            elif any(item["value"] is None or item["provenance"]["kind"] in {"UNKNOWN", "PLANNER_PROPOSAL"}
                     for item in conditions + exclusions):
                decision = "NEEDS_REVIEW"
            else:
                decision = "SELECTABLE_CANDIDATE"
            decisions.append({"rule_ref": rule["rule_ref"], "output_ids": rule["output_ids"], "decision": decision})
        return {"input": value, "input_sha256": hashlib.sha256(self.document.encode("utf-8")).hexdigest(),
                "brief_sha256": hashlib.sha256(value["brief_text"].encode("utf-8")).hexdigest(),
                "rule_decisions": decisions,
                "outputs": [{"output_id": output["output_id"], "medium": output["medium"],
                             "status": "NEEDS_MATERIAL" if output["plan"] is None else "PLANNED_NOT_EXECUTED",
                             "estimated_duration_seconds": self._plan_duration(output),
                             "constraints": "NOT_EVALUATED_ON_MEDIA"} for output in value["outputs"]],
                "execution": "NOT_EXECUTED", "predicate_evidence": "DECLARED_NOT_REVALIDATED",
                "reviews": {name: "NEEDS_REVIEW" for name in ("visual", "audio", "facts", "rights")},
                "rendition_binding": None}


__all__ = [
    "AudiovisualPlan",
    "ContentContractError",
    "EmotionExperiencePattern",
    "NarrativePattern",
    "Shot",
    "ShotPlan",
    "VisualMotifPattern",
    "WhiteDescriptionPattern",
]

def resolve_creation_upstream(reference, *, actor, scope, connection=None):
    """Resolve an immutable upstream through its canonical authorized reader.

    Caller references select bytes/versions; they never supply trusted body,
    receipts, source rights or a cross-work production revision parent.
    """
    import copy
    import re
    from lumenis.shared.reporting import saved_work

    if not isinstance(reference, dict) or reference.get("kind") not in {"saved_work", "source_brief_job"}:
        raise ContentContractError("CREATION_UPSTREAM_REFERENCE_INVALID")
    options = {"connection": connection} if connection is not None else {}
    context = saved_work.authorize(actor, scope, action="read", **options)
    if reference["kind"] == "saved_work":
        if (set(reference) != {"kind", "artifact_id", "expected_sha256", "expected_version"}
                or not isinstance(reference["artifact_id"], str)
                or not isinstance(reference["expected_sha256"], str)
                or re.fullmatch(r"[0-9a-f]{64}", reference["expected_sha256"]) is None
                or type(reference["expected_version"]) is not int or reference["expected_version"] < 1):
            raise ContentContractError("CREATION_UPSTREAM_REFERENCE_INVALID")
        result = saved_work.read_committed_work(reference["artifact_id"], actor=actor, scope=scope, **options)
        document, artifact = result["document"], result["artifact"]
        if (artifact["sha256"] != reference["expected_sha256"]
                or document["version"] != reference["expected_version"]):
            raise ContentContractError("CREATION_UPSTREAM_VERSION_CHANGED")
        snapshot = {
            "schema": "lumenis.creation-upstream/v1", "kind": "saved_work",
            "reference": copy.deepcopy(reference),
            "identity": {"artifact_id": artifact["artifact_id"], "sha256": artifact["sha256"],
                         "size_bytes": artifact["size_bytes"], "work_id": document["work_id"],
                         "version": document["version"], "draft_digest": document["draft_digest"],
                         "task_id": document.get("task_id"), "assertion_id": document.get("assertion_id")},
            "document": {key: copy.deepcopy(document[key]) for key in
                         ("schema", "kind", "title", "markdown", "payload", "contract", "citations")},
            "source_records": copy.deepcopy(result["receipt"]["sources"]),
            "return_ref": copy.deepcopy(result["return_ref"]),
            "scope": {key: context[key] for key in ("domain_id", "subject_id", "brand_focus_id", "global_scope")},
            "source_role": "committed_material_and_citations_not_new_capture_or_creation_grant",
        }
    else:
        if (set(reference) != {"kind", "job_id", "expected_artifact_hash"}
                or not isinstance(reference["job_id"], str)
                or not isinstance(reference["expected_artifact_hash"], str)
                or re.fullmatch(r"[0-9a-f]{64}", reference["expected_artifact_hash"]) is None):
            raise ContentContractError("CREATION_UPSTREAM_REFERENCE_INVALID")
        from lumenis.shared.reporting.source_brief_job import get_source_brief_job, _media_scope
        actor_ref = context.get("principal_ref") or f"actor:{context['actor_id']}"
        result = get_source_brief_job(reference["job_id"], actor_id=actor_ref, actor=actor, **options)
        original_scope = _media_scope(result["source_brief"]["scope"])
        target_scope = {key: context[key] for key in ("domain_id", "subject_id", "brand_focus_id", "global_scope")}
        if (original_scope["domain_id"] != target_scope["domain_id"]
                or (not target_scope["global_scope"] and original_scope != target_scope)):
            raise ContentContractError("CREATION_UPSTREAM_SCOPE_MISMATCH")
        if result["artifact_outcome"]["artifact_hash"] != reference["expected_artifact_hash"]:
            raise ContentContractError("CREATION_UPSTREAM_VERSION_CHANGED")
        snapshot = {
            "schema": "lumenis.creation-upstream/v1", "kind": "source_brief_job",
            "reference": copy.deepcopy(reference),
            "identity": {"job_id": result["job_id"], "report_id": result["artifact_outcome"]["report_id"],
                         "artifact_hash": result["artifact_outcome"]["artifact_hash"],
                         "revision": copy.deepcopy(result.get("revision"))},
            "document": {key: copy.deepcopy(result[key]) for key in
                         ("business_question", "requested_source_ids", "source_brief")},
            "source_records": copy.deepcopy(result["source_brief"]["records"]),
            "return_ref": {"job_id": result["job_id"], "scope": copy.deepcopy(result["source_brief"]["scope"])},
            "scope": target_scope,
            "source_role": "source_scope_proof_report_not_shared_artifact_or_new_observation",
        }
    saved_work._safe_payload(snapshot)
    if saved_work.authorize(actor, scope, action="read", **options) != context:
        raise ContentContractError("CREATION_UPSTREAM_SCOPE_MISMATCH")
    return snapshot
