"""Original Source/SavedWork consumer for explicitly selected title/cover variants.

No exposure allocation, new persistence owner, publication or observation-truth claim.
"""
from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime
import hashlib
import json
import re

from lumenis.shared.database import get_repository
from . import saved_work
from .statistics_methods import _statistics_experiment

SCHEMA = "lumenis.artifact-experiment/v1"


def capabilities():
    return {
        "business_purpose": "choose_content_variant",
        "input_schema": SCHEMA,
        "variant_kinds": ["saved_work_title", "media_cover", "content_variant"],
        "observation_inputs": ["source_evidence", "USER_RECORDED_SAVED_WORK"],
        "method": "beta-bernoulli-thompson@1",
        "source_contract": "Unique user-declared observation IDs, arm binding, offset timestamp and boolean outcome; retained source custody does not authenticate audience observations.",
        "scope": "Current actor and exact scope; immutable referenced versions remain selectable if still authorized.",
        "ai_required": False,
        "external_allocation": "NOT_IMPLEMENTED",
        "business_acceptance": "NOT_VERIFIED",
    }


def _instant(value):
    if not isinstance(value, str):
        raise ValueError("ARTIFACT_EXPERIMENT_TIME_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("ARTIFACT_EXPERIMENT_TIME_INVALID") from exc
    if parsed.tzinfo is None:
        raise ValueError("ARTIFACT_EXPERIMENT_TIMEZONE_REQUIRED")
    return parsed


def _variant(binding, *, actor, scope, connection):
    common = {"kind", "artifact_id", "sha256", "version"}
    if (not isinstance(binding, dict) or not common <= set(binding)
            or not isinstance(binding["artifact_id"], str)
            or re.fullmatch(r"ART-[0-9a-f]{16}", binding["artifact_id"]) is None
            or not isinstance(binding["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", binding["sha256"]) is None
            or type(binding["version"]) is not int or binding["version"] < 1):
        raise ValueError("ARTIFACT_EXPERIMENT_VARIANT_INVALID")
    if binding["kind"] == "content_variant":
        if (set(binding) != common | {"variant_id", "body_sha256"}
                or not isinstance(binding["variant_id"], str)
                or re.fullmatch(r"[A-Za-z0-9_-]{1,40}", binding["variant_id"]) is None
                or not isinstance(binding["body_sha256"], str)
                or re.fullmatch(r"[0-9a-f]{64}", binding["body_sha256"]) is None):
            raise ValueError("ARTIFACT_EXPERIMENT_VARIANT_INVALID")
        from lumenis.shared.content_creation.multiplatform import read_variant
        return read_variant(binding, actor=actor, scope=scope, connection=connection)
    if binding["kind"] == "saved_work_title":
        if set(binding) != common:
            raise ValueError("ARTIFACT_EXPERIMENT_VARIANT_INVALID")
        work = saved_work.read_committed_work(
            binding["artifact_id"], actor=actor, scope=scope, connection=connection
        )
        if (work["artifact"]["sha256"] != binding["sha256"]
                or work["document"]["version"] != binding["version"]):
            raise ValueError("ARTIFACT_EXPERIMENT_VARIANT_VERSION_MISMATCH")
        title = work["document"]["title"]
        return {**binding, "title": title, "work_id": work["document"]["work_id"],
                "content_sha256": hashlib.sha256(title.encode()).hexdigest(),
                "meaning": "Exact saved document title; not proof this headline was externally displayed."}
    if binding["kind"] == "media_cover":
        if (set(binding) != common | {"filename", "member_sha256"}
                or not isinstance(binding["filename"], str)
                or re.fullmatch(r"cover-0[1-9]\.png|podcast-cover\.png", binding["filename"]) is None):
            raise ValueError("ARTIFACT_EXPERIMENT_COVER_INVALID")
        from shared_artifacts import _verified_content_project

        project, render, record, _ = _verified_content_project(
            binding["artifact_id"], actor=actor, read_only_registry=True,
            **({"shared_workspace_scope": scope} if saved_work._shared_scope_requested(scope) else scope)
        )
        member = project.get("delivery_manifest", {}).get(binding["filename"])
        if (record["sha256"] != binding["sha256"]
                or project["timeline"]["version"] != binding["version"]
                or not isinstance(member, dict)
                or member.get("sha256") != binding["member_sha256"]):
            raise ValueError("ARTIFACT_EXPERIMENT_VARIANT_VERSION_MISMATCH")
        report = render.get("delivery_reports", {}).get(
            "podcast_cover" if binding["filename"] == "podcast-cover.png" else "cover"
        )
        if not isinstance(report, dict):
            raise ValueError("ARTIFACT_EXPERIMENT_COVER_REPORT_REQUIRED")
        if binding["filename"] != "podcast-cover.png" and not any(
            row.get("filename") == binding["filename"] and row.get("sha256") == binding["member_sha256"]
            for row in report.get("candidates", [])
        ):
            raise ValueError("ARTIFACT_EXPERIMENT_COVER_CANDIDATE_MISMATCH")
        return {**binding, "content_sha256": member["sha256"],
                "copy": report.get("copy"),
                "meaning": "Verified rendered package cover member; exposure and external display remain unverified."}
    raise ValueError("ARTIFACT_EXPERIMENT_VARIANT_KIND_UNSUPPORTED")


def analyze(evidence_id=None, *, actor, scope, observation_artifact_id=None,
            observation_sha256=None, connection=None):
    if (evidence_id is None) == (observation_artifact_id is None):
        raise ValueError("ARTIFACT_EXPERIMENT_EXACTLY_ONE_INPUT_REQUIRED")
    if evidence_id is not None and (type(evidence_id) is not int or evidence_id <= 0
                                    or observation_sha256 is not None):
        raise ValueError("ARTIFACT_EXPERIMENT_SOURCE_REQUIRED")
    if observation_artifact_id is not None and (
        not isinstance(observation_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", observation_sha256) is None
    ):
        raise ValueError("ARTIFACT_EXPERIMENT_OBSERVATION_HASH_REQUIRED")
    manager = (get_repository().connection(read_only=True, wal=False)
               if connection is None else nullcontext(connection))
    with manager as con:
        if evidence_id is not None:
            context = saved_work.authorize(actor, scope, action="read", connection=con)
            evidence = saved_work._verified_evidence(con, evidence_id, context, actor)
            raw = evidence["raw_content"]
            input_binding = {"kind": "source_evidence", "evidence_id": evidence_id,
                             "sha256": evidence["content_hash"]}
        else:
            observation = saved_work.read_committed_work(
                observation_artifact_id, actor=actor, scope=scope, connection=con
            )
            if observation["artifact"]["sha256"] != observation_sha256:
                raise ValueError("ARTIFACT_EXPERIMENT_OBSERVATION_VERSION_MISMATCH")
            recorded = observation["document"]["payload"].get("artifact_experiment_input")
            if not isinstance(recorded, dict):
                raise ValueError("ARTIFACT_EXPERIMENT_RECORDED_INPUT_REQUIRED")
            raw = json.dumps(recorded, ensure_ascii=False, sort_keys=True, allow_nan=False)
            input_binding = {"kind": "USER_RECORDED_SAVED_WORK", "artifact_id": observation_artifact_id,
                             "sha256": observation_sha256, "work_id": observation["document"]["work_id"],
                             "version": observation["document"]["version"],
                             "origin": "USER_RECORDED; not external SourceRaw/Evidence or independently observed delivery"}
        if len(raw.encode()) > 512000:
            raise ValueError("ARTIFACT_EXPERIMENT_SOURCE_TOO_LARGE")

        def unique(pairs):
            out = {}
            for key, value in pairs:
                if key in out:
                    raise ValueError("ARTIFACT_EXPERIMENT_DUPLICATE_KEY")
                out[key] = value
            return out

        try:
            data = json.loads(raw, object_pairs_hook=unique,
                              parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        except (ValueError, TypeError) as exc:
            raise ValueError("ARTIFACT_EXPERIMENT_JSON_INVALID") from exc
        if (not isinstance(data, dict)
                or set(data) != {"schema", "metric", "observation_origin", "window", "arms", "observations", "decision"}
                or data["schema"] != SCHEMA
                or not isinstance(data["observation_origin"], str)
                or data["observation_origin"] not in {"engineering_fixture", "user_declared_observations"}
                or not isinstance(data["metric"], dict)
                or set(data["metric"]) != {"name", "trial_definition", "success_definition"}
                or any(not isinstance(v, str) or not 1 <= len(v.strip()) <= 1000 for v in data["metric"].values())
                or not isinstance(data["window"], dict) or set(data["window"]) != {"start", "end"}
                or not isinstance(data["arms"], list) or not 2 <= len(data["arms"]) <= 20
                or not isinstance(data["observations"], list) or len(data["observations"]) > 10000
                or not isinstance(data["decision"], dict)
                or set(data["decision"]) != {"minimum_trials", "stop_probability", "enable_thompson"}):
            raise ValueError("ARTIFACT_EXPERIMENT_INPUT_INVALID")
        start, end = _instant(data["window"]["start"]), _instant(data["window"]["end"])
        if start >= end:
            raise ValueError("ARTIFACT_EXPERIMENT_WINDOW_INVALID")
        variants, counts, content = [], {}, set()
        for arm in data["arms"]:
            if (not isinstance(arm, dict) or set(arm) != {"id", "variant"}
                    or not isinstance(arm["id"], str)
                    or re.fullmatch(r"[A-Za-z0-9_-]{1,60}", arm["id"]) is None
                    or arm["id"] in counts):
                raise ValueError("ARTIFACT_EXPERIMENT_ARM_INVALID")
            variant = _variant(arm["variant"], actor=actor, scope=scope, connection=con)
            signature = (variant["kind"], variant["content_sha256"])
            if signature in content:
                raise ValueError("ARTIFACT_EXPERIMENT_IDENTICAL_VARIANTS")
            content.add(signature)
            variants.append({"id": arm["id"], "variant": variant})
            counts[arm["id"]] = {"id": arm["id"], "successes": 0, "trials": 0}
        if len({arm["variant"]["kind"] for arm in variants}) != 1:
            raise ValueError("ARTIFACT_EXPERIMENT_MIXED_VARIANT_KINDS")
        seen = set()
        for observation in data["observations"]:
            if (not isinstance(observation, dict)
                    or set(observation) != {"event_id", "arm_id", "observed_at", "outcome"}
                    or not isinstance(observation["event_id"], str)
                    or not 1 <= len(observation["event_id"]) <= 100
                    or observation["event_id"] in seen
                    or not isinstance(observation["arm_id"], str)
                    or observation["arm_id"] not in counts
                    or type(observation["outcome"]) is not bool):
                raise ValueError("ARTIFACT_EXPERIMENT_OBSERVATION_INVALID")
            if not start <= _instant(observation["observed_at"]) < end:
                raise ValueError("ARTIFACT_EXPERIMENT_OBSERVATION_OUTSIDE_WINDOW")
            seen.add(observation["event_id"])
            counts[observation["arm_id"]]["trials"] += 1
            counts[observation["arm_id"]]["successes"] += int(observation["outcome"])
        result = _statistics_experiment({"arms": list(counts.values()),
                                        **data["decision"], "seed": 20261017})
        for arm in data["arms"]:
            _variant(arm["variant"], actor=actor, scope=scope, connection=con)
        if evidence_id is not None:
            after = saved_work._verified_evidence(con, evidence_id, context, actor)
            if after["content_hash"] != evidence["content_hash"]:
                raise ValueError("ARTIFACT_EXPERIMENT_SOURCE_CHANGED")
        else:
            after = saved_work.read_committed_work(
                observation_artifact_id, actor=actor, scope=scope, connection=con
            )
            if after["artifact"]["sha256"] != observation_sha256:
                raise ValueError("ARTIFACT_EXPERIMENT_OBSERVATION_CHANGED")
    payload = {"artifact_experiment": {
        "schema": SCHEMA, "source_evidence_id": evidence_id,
        "dataset_sha256": hashlib.sha256(raw.encode()).hexdigest(), "variants": variants,
        "observation_input": input_binding,
        "metric": data["metric"], "window": data["window"],
        "observation_origin": data["observation_origin"], "counts": list(counts.values()),
        "selection_origin": "EXPLICIT_SOURCE_DECLARED_VARIANT_BINDING",
        "measurement_truth": "NOT_INDEPENDENTLY_VERIFIED",
        "assignment_randomization": "NOT_VERIFIED", "external_allocation": "NOT_PERFORMED",
        "interpretation": "Internal selection recommendation conditional on declared observations; no causal or live conversion claim.",
        "variant_verification": "Snapshot at analysis/save; use the typed experiment reader for current authorization checks.",
        "statistics": result,
    }}
    draft = {"title": ("Saved content variant experiment comparison" if variants[0]["variant"]["kind"] == "content_variant"
                       else "Saved title/cover experiment comparison"), "kind": "report",
             "markdown": "# Saved variant comparison\n\n" + json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
             "payload": payload,
             "citations": ([{"evidence_id": evidence_id, "start": 0, "end": len(raw), "quote": raw}]
                           if evidence_id is not None else [])}
    return {"state": result["state"], "result": payload["artifact_experiment"],
            "saved_work_draft": draft, "ai_used": False, "publish_status": "not_performed"}


def save(evidence_id=None, *, actor, scope, request_id, work_id=None, previous_artifact_id=None,
         observation_artifact_id=None, observation_sha256=None):
    inputs = {"evidence_id": evidence_id, "observation_artifact_id": observation_artifact_id,
              "observation_sha256": observation_sha256}
    analyzed = analyze(**inputs, actor=actor, scope=scope)

    def before_commit(con, record, document):
        current = analyze(**inputs, actor=actor, scope=scope, connection=con)
        if current["saved_work_draft"] != analyzed["saved_work_draft"]:
            raise ValueError("ARTIFACT_EXPERIMENT_CHANGED_BEFORE_COMMIT")

    return saved_work.save_work(
        **analyzed["saved_work_draft"], actor=actor, scope=scope, request_id=request_id,
        work_id=work_id, previous_artifact_id=previous_artifact_id, before_commit=before_commit,
    )


def read(artifact_id, *, actor, scope):
    saved = saved_work.read_committed_work(artifact_id, actor=actor, scope=scope)
    experiment = saved["document"]["payload"].get("artifact_experiment")
    if not isinstance(experiment, dict) or experiment.get("schema") != SCHEMA:
        raise ValueError("ARTIFACT_EXPERIMENT_REPORT_REQUIRED")
    binding = experiment.get("observation_input", {})
    if not isinstance(binding, dict):
        raise ValueError("ARTIFACT_EXPERIMENT_INPUT_BINDING_INVALID")
    if binding.get("kind") == "USER_RECORDED_SAVED_WORK":
        current = analyze(observation_artifact_id=binding.get("artifact_id"),
                          observation_sha256=binding.get("sha256"), actor=actor, scope=scope)
    else:
        current = analyze(experiment.get("source_evidence_id"), actor=actor, scope=scope)
    draft = current["saved_work_draft"]
    # v1 source-Evidence reports predate the optional Shared-input descriptor.
    # Preserve their exact historical representation after revalidating the same
    # original source and all immutable variants; never drop numeric/binding fields.
    if ("observation_input" not in experiment
            and type(experiment.get("source_evidence_id")) is int):
        draft["payload"]["artifact_experiment"].pop("observation_input", None)
    if "variant_verification" not in experiment:
        draft["payload"]["artifact_experiment"].pop("variant_verification", None)
    draft["markdown"] = "# Saved variant comparison\n\n" + json.dumps(
        draft["payload"], ensure_ascii=False, indent=2, allow_nan=False
    )
    stored_citations = saved["document"].get("citations", [])
    projected_citations = [
        {key: row.get(key) for key in ("evidence_id", "start", "end", "quote")}
        for row in stored_citations
    ]
    if (any(saved["document"].get(key) != draft[key]
            for key in ("title", "kind", "markdown", "payload"))
            or projected_citations != draft["citations"]
            or any(row.get("purpose", "quote_reference") != "quote_reference" for row in stored_citations)):
        raise ValueError("ARTIFACT_EXPERIMENT_REPORT_BINDING_MISMATCH")
    saved.pop("content", None)
    return {**saved, "variant_binding_state": "CURRENT_AUTHORIZATION_AND_EXACT_VERSION_VERIFIED",
            "business_acceptance": "NOT_VERIFIED"}
