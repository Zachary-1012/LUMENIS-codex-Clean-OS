"""Durable, scoped Source Brief jobs over the existing Reporting artifact owner.

This binds the source-only projection to ``daily_reports``; it does not create a
second job store. A persisted artifact can be reopened by its server-issued job
id and is evaluated only after its stored bytes and scope have been re-verified.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

import database as report_database

from lumenis.shared.database import get_repository
from lumenis.shared.evaluation.recorder import (
    get_artifact_evaluations, get_evaluation_record, record_evaluation,
)
from .artifact import compute_scoped_scope_key
from .operational_brief import build_scoped_source_brief

JOB_SCHEMA = "source-brief-job:v1"
GENERATOR_VERSION = "source-brief-job/1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$")
_ACTOR_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/@-]{0,159}$")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_artifact(*, report_id: str, report_type: str, report_date: str,
                   total_notes: int, summary: str, source_snapshot: str) -> str:
    material = {
        "report_id": report_id, "report_type": report_type, "report_date": report_date,
        "total_notes": total_notes, "summary": summary, "source_snapshot": source_snapshot,
        "generator_version": GENERATOR_VERSION,
    }
    return hashlib.sha256(_json(material).encode("utf-8")).hexdigest()


def _scope_material(*, product_id: str, global_scope: bool, entity_label: str,
                    subject_id: str | None, brand_focus_id: str | None) -> dict[str, Any]:
    if product_id not in {"CTH", "ZBMP"} or type(global_scope) is not bool:
        raise ValueError("SOURCE_BRIEF_SCOPE_INVALID")
    if not isinstance(entity_label, str) or not entity_label or entity_label != entity_label.strip():
        raise ValueError("SOURCE_BRIEF_ENTITY_LABEL_REQUIRED")
    if global_scope and (subject_id is not None or brand_focus_id is not None):
        raise ValueError("SOURCE_BRIEF_GLOBAL_SCOPE_HAS_FOCUS")
    if not global_scope and product_id == "CTH" and (
        not isinstance(subject_id, str) or not subject_id.strip() or brand_focus_id is not None
    ):
        raise ValueError("SOURCE_BRIEF_CTH_FOCUS_REQUIRED")
    if not global_scope and product_id == "ZBMP" and (
        not isinstance(brand_focus_id, str) or not brand_focus_id.strip() or subject_id is not None
    ):
        raise ValueError("SOURCE_BRIEF_BMP_FOCUS_REQUIRED")
    domain_id = "cth" if product_id == "CTH" else "zbmp"
    return {
        "product_id": product_id, "domain_id": domain_id, "global": global_scope,
        "subject_id": subject_id, "brand_focus_id": brand_focus_id,
        "entity_label": entity_label,
        "scope_key": compute_scoped_scope_key(
            domain_id, subject_id, brand_focus_id, global_scope, None, None, "zh-CN", "markdown"
        ),
    }


def _validate_actor_refs(actor_id: str, permission_audit_ref: str, trace_id: str, job_id: str) -> None:
    if not isinstance(actor_id, str) or not _ACTOR_ID.fullmatch(actor_id):
        raise ValueError("SOURCE_BRIEF_ACTOR_REQUIRED")
    if (not isinstance(permission_audit_ref, str) or not permission_audit_ref.strip()
            or len(permission_audit_ref) > 256):
        raise ValueError("SOURCE_BRIEF_PERMISSION_AUDIT_REQUIRED")
    if not isinstance(trace_id, str) or not trace_id.strip() or len(trace_id) > 160:
        raise ValueError("SOURCE_BRIEF_TRACE_REQUIRED")
    if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id):
        raise ValueError("SOURCE_BRIEF_SERVER_JOB_ID_INVALID")


def _media_scope(scope: dict[str, Any]) -> dict[str, Any]:
    return {"domain_id": scope["domain_id"], "global_scope": scope["global"],
            "subject_id": scope["subject_id"], "brand_focus_id": scope["brand_focus_id"]}


def _multimodal_snapshot(result, *, job_id, actor_id, scope):
    """Only the signed analyzer execution can establish a completed derivative."""
    if isinstance(result, dict) and result.get("evidence_ref"):
        from .media_brief import read_verified_report_media
        return read_verified_report_media(
            result["evidence_ref"], job_id=job_id, actor_ref=actor_id, scope=_media_scope(scope),
        )
    if isinstance(result, dict) and result.get("state") in {"unavailable", "error"}:
        return {"state": result["state"], "reason": result.get("reason", "MEDIA_UNAVAILABLE"),
                "real_input_bound": False, "review_status": "HUMAN_PENDING"}
    return {
        "state": "unavailable", "reason": "MULTIMODAL_ANALYZER_OWNER_NOT_BOUND",
        "real_input_bound": False,
    }


def _read_report(job_id: str) -> dict[str, Any] | None:
    conn = get_repository().connect(timeout=10, read_only=True, wal=False)
    try:
        row = conn.execute(
            "SELECT * FROM daily_reports WHERE report_id=? ORDER BY id DESC LIMIT 1", (job_id,)
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def _verify_report(row: dict[str, Any], *, job_id: str, actor_id: str,
                   expected_scope: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        snapshot = json.loads(row.get("source_snapshot") or "")
    except (TypeError, ValueError) as exc:
        raise RuntimeError("SOURCE_BRIEF_STORED_SNAPSHOT_INVALID") from exc
    if not isinstance(snapshot, dict) or snapshot.get("schema") != JOB_SCHEMA:
        raise RuntimeError("SOURCE_BRIEF_STORED_JOB_SCHEMA_INVALID")
    if row.get("report_id") != job_id or snapshot.get("job_id") != job_id:
        raise PermissionError("SOURCE_BRIEF_JOB_ID_MISMATCH")
    if snapshot.get("actor_id") != actor_id:
        raise PermissionError("SOURCE_BRIEF_ACTOR_MISMATCH")
    scope = snapshot.get("scope")
    if not isinstance(scope, dict):
        raise RuntimeError("SOURCE_BRIEF_STORED_SCOPE_INVALID")
    if expected_scope is not None and scope != expected_scope:
        raise PermissionError("SOURCE_BRIEF_SCOPE_MISMATCH")
    count = row.get("total_notes")
    if type(count) is not int or count < 0:
        raise RuntimeError("SOURCE_BRIEF_STORED_SOURCE_COUNT_INVALID")
    summary = row.get("summary")
    source_snapshot = row.get("source_snapshot")
    if not isinstance(summary, str) or not isinstance(source_snapshot, str):
        raise RuntimeError("SOURCE_BRIEF_STORED_ARTIFACT_INVALID")
    expected_hash = _hash_artifact(
        report_id=job_id, report_type=str(row.get("report_type") or ""),
        report_date=str(row.get("report_date") or ""), total_notes=count,
        summary=summary, source_snapshot=source_snapshot,
    )
    if not _SHA256.fullmatch(str(row.get("artifact_hash") or "")) or row["artifact_hash"] != expected_hash:
        raise RuntimeError("SOURCE_BRIEF_ARTIFACT_HASH_MISMATCH")
    brief = snapshot.get("source_brief")
    if not isinstance(brief, dict) or brief.get("scope") != scope:
        raise RuntimeError("SOURCE_BRIEF_STORED_BRIEF_SCOPE_INVALID")
    records = brief.get("records")
    sample = brief.get("sample")
    if not isinstance(records, list) or not isinstance(sample, dict):
        raise RuntimeError("SOURCE_BRIEF_STORED_BRIEF_INVALID")
    if type(sample.get("returned_verified_count")) is not int or sample["returned_verified_count"] != count or len(records) != count:
        raise RuntimeError("SOURCE_BRIEF_STORED_SOURCE_COUNT_MISMATCH")
    if brief.get("markdown") != summary:
        raise RuntimeError("SOURCE_BRIEF_STORED_SUMMARY_MISMATCH")
    expected_content_hash = hashlib.sha256(summary.encode("utf-8")).hexdigest()
    if brief.get("content_hash") != expected_content_hash:
        raise RuntimeError("SOURCE_BRIEF_STORED_CONTENT_HASH_MISMATCH")
    for record in records:
        if (not isinstance(record, dict) or not record.get("source_id")
                or not record.get("evidence_id") or not record.get("scope_evidence_ref")
                or record["evidence_id"] != record["scope_evidence_ref"]):
            raise RuntimeError("SOURCE_BRIEF_STORED_EVIDENCE_INVALID")
    multimodal = snapshot.get("multimodal")
    if isinstance(multimodal, dict) and multimodal.get("state") == "complete":
        if _multimodal_snapshot(multimodal, job_id=job_id, actor_id=actor_id, scope=scope) != multimodal:
            raise RuntimeError("SOURCE_BRIEF_MEDIA_EVIDENCE_MISMATCH")
    return {"row": row, "snapshot": snapshot, "source_brief": brief}


def _evaluation_ids(job_id: str) -> dict[str, str]:
    return {
        name: hashlib.sha256(f"{JOB_SCHEMA}:{job_id}:{name}".encode("utf-8")).hexdigest()
        for name in ("report_artifact_integrity", "source_evidence_grounding", "multimodal_analysis_integrity")
    }


def _record_evaluations(verified: dict[str, Any]) -> list[dict[str, Any]]:
    row, snapshot, brief = verified["row"], verified["snapshot"], verified["source_brief"]
    job_id = snapshot["job_id"]
    evaluation_ids = snapshot["evaluation_ids"]
    refs = [record["scope_evidence_ref"] for record in brief["records"]]
    common = {
        "job_id": job_id, "report_id": row["report_id"], "artifact_hash": row["artifact_hash"],
        "scope": snapshot["scope"], "actor_id": snapshot["actor_id"],
        "permission_audit_ref": snapshot["permission_audit_ref"],
        "trace_id": snapshot["trace_id"], "source_evidence_refs": refs,
        "review_status": "HUMAN_PENDING",
    }
    source_value = (len(refs) / len(brief["records"])) if brief["records"] else None
    multi = snapshot["multimodal"]
    multi_value = 1.0 if multi.get("state") == "complete" and multi.get("real_input_bound") is True else None
    specifications = (
        ("report_artifact_integrity", 1.0, "Persisted daily_reports artifact hash and report_id were reopened and verified."),
        ("source_evidence_grounding", source_value, "Verified Canonical source Evidence linkage; empty samples remain unknown."),
        ("multimodal_analysis_integrity", multi_value, "Real media input and analysis execution binding; unavailable stays unknown."),
    )
    records = []
    for metric, value, description in specifications:
        record = record_evaluation(
            dimension="report", metric_name=metric, metric_value=value,
            pass_threshold=1.0, warn_threshold=0.8, source="daily_reports:source_brief_job",
            evidence_ref=f"daily_reports:{row['report_id']}:{row['artifact_hash']}",
            metadata={**common, "evaluation_basis": description}, evaluation_id=evaluation_ids[metric],
        )
        persisted = get_evaluation_record(record.evaluation_id)
        if not persisted or persisted.get("evidence_ref") != record.evidence_ref:
            raise RuntimeError("SOURCE_BRIEF_EVALUATION_REOPEN_FAILED")
        records.append(persisted)
    return records


def _quality_reviews(verified: dict[str, Any]) -> dict[str, Any]:
    row, snapshot = verified["row"], verified["snapshot"]
    evidence_refs = {f"daily_reports:{row['report_id']}:{row['artifact_hash']}"}
    media = snapshot["multimodal"]
    if media.get("state") == "complete" and media.get("evidence_ref"):
        evidence_refs.add(media["evidence_ref"])
    records = get_artifact_evaluations(
        job_id=snapshot["job_id"], artifact_hash=row["artifact_hash"],
        scope=snapshot["scope"], actor_id=snapshot["actor_id"], evidence_refs=evidence_refs,
    )
    reviews = []
    for record in records:
        if record["evaluation_id"] in snapshot["evaluation_ids"].values():
            continue
        metadata = json.loads(record["metadata"])
        # Expose business feedback, not arbitrary internal evaluation metadata.
        review = {key: record[key] for key in (
            "evaluation_id", "metric_name", "metric_value", "status", "evaluated_at",
            "source", "evidence_ref",
        )}
        observations = metadata.get("observations")
        review["observations"] = [item for item in observations if isinstance(item, str)] if isinstance(observations, list) else []
        for key in ("required_followup", "evaluator"):
            review[key] = metadata.get(key) if isinstance(metadata.get(key), str) else None
        reviews.append(review)
    return {"state": "recorded" if reviews else "not_recorded", "records": reviews,
            "review_status": "HUMAN_PENDING"}


def _response(verified: dict[str, Any], evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    row, snapshot, brief = verified["row"], verified["snapshot"], verified["source_brief"]
    return {
        "job_id": snapshot["job_id"], "job_state": "completed",
        "artifact_outcome": {
            "state": "persisted_and_reopened_verified", "report_id": row["report_id"],
            "artifact_hash": row["artifact_hash"], "source_count": row["total_notes"],
        },
        "source_brief": brief, "multimodal": snapshot["multimodal"],
        "evaluation": {"state": "recorded", "records": evaluations,
                       "quality_review": _quality_reviews(verified)},
        "requested_image_source_ref": snapshot.get("requested_image_source_ref"),
        "retry_of_job_id": snapshot.get("retry_of_job_id"),
        "review_status": "HUMAN_PENDING",
    }


def create_source_brief_job(
    con, *, product_id: str, global_scope: bool, entity_label: str, actor_id: str,
    permission_audit_ref: str, trace_id: str, job_id: str,
    subject_id: str | None = None, brand_focus_id: str | None = None,
    limit: int = 30, multimodal_result: dict[str, Any] | None = None,
    image_source_ref: str | None = None, image_actor: Any = None,
    retry_of_job_id: str | None = None,
) -> dict[str, Any]:
    """Create or recover a server-authorized scoped Source Brief report job.

    ``con`` must be the caller's authorized canonical read connection. Permission
    enforcement remains at the API/Permission boundary; this owner records its
    real audit reference and binds all reads/evaluations to actor and exact scope.
    """
    _validate_actor_refs(actor_id, permission_audit_ref, trace_id, job_id)
    scope = _scope_material(
        product_id=product_id, global_scope=global_scope, entity_label=entity_label,
        subject_id=subject_id, brand_focus_id=brand_focus_id,
    )
    existing = _read_report(job_id)
    if existing:
        verified = _verify_report(existing, job_id=job_id, actor_id=actor_id, expected_scope=scope)
        evaluations = _record_evaluations(verified)
        return _response(verified, evaluations)

    brief = build_scoped_source_brief(
        con, product_id=product_id, global_scope=global_scope, entity_label=entity_label,
        subject_id=subject_id, brand_focus_id=brand_focus_id, limit=limit,
    )
    if brief.get("scope") != scope:
        raise RuntimeError("SOURCE_BRIEF_CANONICAL_SCOPE_MISMATCH")
    records, sample = brief.get("records"), brief.get("sample")
    if not isinstance(records, list) or not isinstance(sample, dict):
        raise RuntimeError("SOURCE_BRIEF_CANONICAL_RESULT_INVALID")
    count = sample.get("returned_verified_count")
    if type(count) is not int or count < 0 or count != len(records):
        raise RuntimeError("SOURCE_BRIEF_CANONICAL_COUNT_INVALID")
    for record in records:
        if (not isinstance(record, dict) or not record.get("source_id")
                or not record.get("evidence_id") or not record.get("scope_evidence_ref")
                or record["evidence_id"] != record["scope_evidence_ref"]):
            raise RuntimeError("SOURCE_BRIEF_CANONICAL_EVIDENCE_INVALID")
    if not isinstance(brief.get("markdown"), str) or not isinstance(brief.get("content_hash"), str):
        raise RuntimeError("SOURCE_BRIEF_CANONICAL_ARTIFACT_INVALID")
    if brief["content_hash"] != hashlib.sha256(brief["markdown"].encode("utf-8")).hexdigest():
        raise RuntimeError("SOURCE_BRIEF_CANONICAL_CONTENT_HASH_MISMATCH")

    if image_source_ref is not None:
        from .media_brief import analyze_report_media
        multimodal_result = analyze_report_media(
            image_source_ref, actor=image_actor, scope=_media_scope(scope), job_id=job_id,
            brief_context={"scope": scope, "markdown": _json({
                "entity": scope["entity_label"], "verified_source_count": count,
                "coverage": brief.get("coverage", "UNKNOWN"),
                "sample_titles": [str(record.get("title") or "")[:100] for record in records[:3]],
            })},
        )
    multimodal = _multimodal_snapshot(
        multimodal_result, job_id=job_id, actor_id=actor_id, scope=scope,
    )
    # daily_reports is unique on (report_type, report_date), so identity must
    # include this job as well as its scope; otherwise same-scope jobs today
    # would overwrite one another through the legacy report writer.
    report_type = (
        "source_brief_job:" + scope["domain_id"] + ":" + scope["scope_key"] + ":"
        + hashlib.sha256(job_id.encode("utf-8")).hexdigest()
    )
    evaluation_ids = _evaluation_ids(job_id)
    snapshot_data = {
        "schema": JOB_SCHEMA, "job_id": job_id, "trace_id": trace_id,
        "actor_id": actor_id, "permission_audit_ref": permission_audit_ref,
        "scope": scope,
        "source_brief": {
            "status": brief.get("status"), "scope": brief["scope"],
            "coverage": brief.get("coverage", "UNKNOWN"),
            "freshness": brief.get("freshness", "UNKNOWN"),
            "collection_state": brief.get("collection_state", "UNKNOWN"),
            "sample": sample, "records": records, "markdown": brief["markdown"],
            "content_hash": brief["content_hash"],
        },
        "multimodal": multimodal, "evaluation_ids": evaluation_ids,
        "requested_image_source_ref": image_source_ref, "retry_of_job_id": retry_of_job_id,
        "review_status": "HUMAN_PENDING",
    }
    source_snapshot = _json(snapshot_data)
    report_date = datetime.now(timezone.utc).date().isoformat()
    artifact_hash = _hash_artifact(
        report_id=job_id, report_type=report_type, report_date=report_date,
        total_notes=count, summary=brief["markdown"], source_snapshot=source_snapshot,
    )
    report_database.save_daily_report({
        "report_type": report_type, "report_date": report_date,
        "period_start": "", "period_end": "", "total_notes": count,
        "positive_count": None, "neutral_count": None, "negative_count": None,
        "high_risk_count": None, "medium_risk_count": None, "low_risk_count": None,
        "total_likes": None, "total_comments": None, "total_engagements": None,
        "top_topics": [], "hot_notes": [], "risk_alerts": [], "key_events": [],
        "event_summary": "", "sentiment_analysis": "", "summary": brief["markdown"],
        "report_id": job_id, "artifact_hash": artifact_hash,
        "generator_version": GENERATOR_VERSION,
        "data_version": "canonical-source-brief:" + brief["content_hash"],
        "source_snapshot": source_snapshot,
    })
    reopened = _read_report(job_id)
    if not reopened:
        raise RuntimeError("SOURCE_BRIEF_REPORT_REOPEN_FAILED")
    verified = _verify_report(reopened, job_id=job_id, actor_id=actor_id, expected_scope=scope)
    evaluations = _record_evaluations(verified)
    return _response(verified, evaluations)


def get_source_brief_job(job_id: str, *, actor_id: str,
                         expected_scope: dict[str, Any] | None = None) -> dict[str, Any]:
    """Reopen a persisted job for the same actor and, when supplied, exact scope."""
    if not isinstance(actor_id, str) or not _ACTOR_ID.fullmatch(actor_id):
        raise ValueError("SOURCE_BRIEF_ACTOR_REQUIRED")
    if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id):
        raise ValueError("SOURCE_BRIEF_SERVER_JOB_ID_INVALID")
    row = _read_report(job_id)
    if not row:
        raise LookupError("SOURCE_BRIEF_JOB_NOT_FOUND")
    verified = _verify_report(row, job_id=job_id, actor_id=actor_id, expected_scope=expected_scope)
    evaluation_ids = verified["snapshot"].get("evaluation_ids")
    evaluations = [get_evaluation_record(evaluation_ids[name]) for name in _evaluation_ids(job_id)]
    present = [record for record in evaluations if record]
    state = "recorded" if len(present) == len(evaluations) else "pending_recovery"
    result = _response(verified, present)
    result["evaluation"]["state"] = state
    return result
