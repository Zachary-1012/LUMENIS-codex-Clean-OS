"""Durable, scoped Source Brief jobs over the existing Reporting artifact owner.

This binds the source-only projection to ``daily_reports``; it does not create a
second job store. A persisted artifact can be reopened by its server-issued job
id and is evaluated only after its stored bytes and scope have been re-verified.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any

import database as report_database

from lumenis.shared.database import get_repository
from lumenis.shared.evaluation.recorder import (
    get_artifact_evaluations, get_evaluation_record, record_evaluation,
    threshold_to_str,
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


def _scope_material(*, product_id=None, global_scope=None, entity_label=None,
                    subject_id=None, brand_focus_id=None, scope_kind=None, version=None) -> dict[str, Any]:
    if scope_kind is not None or version is not None:
        if (scope_kind != "shared_workspace" or type(version) is not int or version != 1
                or any(value is not None for value in (product_id, global_scope, entity_label, subject_id, brand_focus_id))):
            raise ValueError("SOURCE_BRIEF_SCOPE_INVALID")
        return {"scope_kind": "shared_workspace", "version": 1}
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


def _read_report(job_id: str, *, connection=None) -> dict[str, Any] | None:
    if connection is None:
        conn = get_repository().connect(timeout=10, read_only=True, wal=False)
    else:
        from lumenis.system.security.permission import _require_canonical_scope_connection
        conn = _require_canonical_scope_connection(connection)
    try:
        row = conn.execute(
            "SELECT * FROM daily_reports WHERE report_id=? ORDER BY id DESC LIMIT 1", (job_id,)
        ).fetchone()
    finally:
        if connection is None:
            conn.close()
    return dict(row) if row else None


def _verify_report(row: dict[str, Any], *, job_id: str, actor_id: str,
                   expected_scope: dict[str, Any] | None = None, actor=None, connection=None) -> dict[str, Any]:
    try:
        snapshot = json.loads(row.get("source_snapshot") or "")
    except (TypeError, ValueError) as exc:
        raise RuntimeError("SOURCE_BRIEF_STORED_SNAPSHOT_INVALID") from exc
    if isinstance(snapshot, dict) and snapshot.get("schema") == SHARED_JOB_SCHEMA:
        return _verify_shared_report(row, snapshot, job_id=job_id, actor_id=actor_id,
                                     expected_scope=expected_scope, actor=actor, connection=connection)
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
    selected_ids = snapshot.get("requested_source_ids")
    if selected_ids is not None:
        from canonical_data import validate_source_ids
        validate_source_ids(selected_ids)
        if selected_ids != [record.get("source_id") for record in records]:
            raise RuntimeError("SOURCE_BRIEF_STORED_SELECTION_MISMATCH")
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
        canonical_id = record.get("canonical_id")
        if canonical_id is not None and (
            not isinstance(canonical_id, str) or not canonical_id
            or canonical_id != canonical_id.strip() or len(canonical_id) > 512
            or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in canonical_id)
        ):
            raise RuntimeError("SOURCE_BRIEF_STORED_CANONICAL_ID_INVALID")
    multimodal = snapshot.get("multimodal")
    if isinstance(multimodal, dict) and multimodal.get("state") == "complete":
        expected_multimodal = _multimodal_snapshot(
            multimodal, job_id=job_id, actor_id=actor_id, scope=scope,
        )
        if expected_multimodal.get("historical_provider") is True:
            # Preserve the immutable historical snapshot/hash on disk while
            # returning the verified result with its current assurance state.
            persisted_view = {
                **multimodal,
                "state": expected_multimodal["state"],
            }
            expected_persisted_view = {
                key: value for key, value in expected_multimodal.items()
                if key not in {
                    "source_hash_bound", "inference_status", "current_inference_verified",
                    "historical_provider",
                }
            }
            if expected_persisted_view != persisted_view:
                raise RuntimeError("SOURCE_BRIEF_MEDIA_EVIDENCE_MISMATCH")
            snapshot = {**snapshot, "multimodal": expected_multimodal}
        elif expected_multimodal != multimodal:
            raise RuntimeError("SOURCE_BRIEF_MEDIA_EVIDENCE_MISMATCH")
    business = snapshot.get("business_analysis")
    if snapshot.get("revision") is not None:
        from .operator_review import verify_revision_feedback
        verify_revision_feedback(snapshot["revision"], actor_id=actor_id, expected_scope=scope)
    if isinstance(business, dict) and business.get("state") == "draft":
        from .business_brief import read_business_brief
        expected = read_business_brief(
            business.get("evidence_ref"), job_id=job_id, actor_ref=actor_id, scope=_media_scope(scope),
            actor=actor,
        )
        comparable = business
        if expected.get('provider') == 'ollama':
            comparable = {**business, 'real_input_bound': False, 'source_use_state': 'HISTORICAL_NOT_REVERIFIED'}
        if expected != comparable or business.get("question") != snapshot.get("business_question"):
            raise RuntimeError("SOURCE_BRIEF_BUSINESS_EVIDENCE_MISMATCH")
        if business.get("revision") != snapshot.get("revision"):
            raise RuntimeError("SOURCE_BRIEF_REVISION_EVIDENCE_MISMATCH")
        # Preserve the immutable historical snapshot and hash on disk; readback
        # reflects its current source-use assurance instead of promoting it.
        if expected.get('provider') == 'ollama':
            snapshot = {**snapshot, 'business_analysis': expected}
    return {"row": row, "snapshot": snapshot, "source_brief": brief}


def _evaluation_ids(job_id: str) -> dict[str, str]:
    return {
        name: hashlib.sha256(f"{JOB_SCHEMA}:{job_id}:{name}".encode("utf-8")).hexdigest()
        for name in ("report_artifact_integrity", "source_evidence_grounding", "multimodal_analysis_integrity")
    }


def _evaluation_expectations(verified: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    row, snapshot, brief = verified["row"], verified["snapshot"], verified["source_brief"]
    job_id = snapshot["job_id"]
    evaluation_ids = snapshot.get("evaluation_ids")
    if evaluation_ids != _evaluation_ids(job_id):
        raise RuntimeError("SOURCE_BRIEF_EVALUATION_REOPEN_FAILED")
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
        ("source_evidence_grounding", source_value, "Verified private custody bytes, not external fact." if snapshot.get("schema") == SHARED_JOB_SCHEMA else "Verified Canonical source Evidence linkage; empty samples remain unknown."),
        ("multimodal_analysis_integrity", multi_value, "Real media input and analysis execution binding; unavailable stays unknown."),
    )
    return tuple({
        "evaluation_id": evaluation_ids[metric],
        "dimension": "report",
        "metric_name": metric,
        "metric_value": value,
        "threshold": threshold_to_str(1.0, 0.8),
        "status": _evaluation_status(value),
        "source": "daily_reports:source_brief_job",
        "evidence_ref": f"daily_reports:{row['report_id']}:{row['artifact_hash']}",
        "metadata": {**common, "evaluation_basis": description},
        "historical_media": metric == "multimodal_analysis_integrity" and multi.get("historical_provider") is True,
    } for metric, value, description in specifications)


def _evaluation_status(value: float | None) -> str:
    if value is None:
        return "unknown"
    if type(value) not in {int, float} or not math.isfinite(value):
        raise RuntimeError("SOURCE_BRIEF_EVALUATION_REOPEN_FAILED")
    return "pass" if value >= 1.0 else "warn" if value >= 0.8 else "fail"


def _read_evaluation(evaluation_id: str, *, connection=None):
    if connection is None:
        return get_evaluation_record(evaluation_id)
    cursor = connection.execute("SELECT * FROM evaluation_records WHERE evaluation_id=?", (evaluation_id,))
    row = cursor.fetchone()
    return dict(zip((column[0] for column in cursor.description), row)) if row else None


def _validate_evaluation_record(record: dict[str, Any], expected: dict[str, Any]) -> None:
    for field in ("evaluation_id", "dimension", "metric_name", "threshold", "source", "evidence_ref"):
        if record.get(field) != expected[field]:
            raise RuntimeError("SOURCE_BRIEF_EVALUATION_REOPEN_FAILED")
    evaluated_at = record.get("evaluated_at")
    if (not isinstance(evaluated_at, str) or not evaluated_at
            or evaluated_at != evaluated_at.strip() or "T" not in evaluated_at):
        raise RuntimeError("SOURCE_BRIEF_EVALUATION_REOPEN_FAILED")
    try:
        # EvaluationRecord's existing writer emits ISO-8601 with a ``T``
        # separator. It currently uses a naive local timestamp, so validate
        # parseability without inventing a timezone for historical records.
        datetime.fromisoformat(evaluated_at)
    except ValueError:
        raise RuntimeError("SOURCE_BRIEF_EVALUATION_REOPEN_FAILED") from None
    try:
        metadata = record.get("metadata")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
    except (TypeError, ValueError):
        raise RuntimeError("SOURCE_BRIEF_EVALUATION_REOPEN_FAILED") from None
    if metadata != expected["metadata"]:
        raise RuntimeError("SOURCE_BRIEF_EVALUATION_REOPEN_FAILED")

    if (expected["metric_name"] == "multimodal_analysis_integrity"
            and record.get("current_inference_verified") is False):
        historical_value = record.get("historical_metric_value")
        historical_status = record.get("historical_record_status")
        if (historical_value is not None
                and (type(historical_value) not in {int, float} or not math.isfinite(historical_value))):
            raise RuntimeError("SOURCE_BRIEF_EVALUATION_REOPEN_FAILED")
        expected_historical_status = _evaluation_status(historical_value)
        expected_projected_status = "unknown" if historical_status == "pass" else historical_status
        if (historical_value not in (None, 1.0) or historical_status != expected_historical_status
                or record.get("metric_value") is not None
                or record.get("status") != expected_projected_status):
            raise RuntimeError("SOURCE_BRIEF_EVALUATION_REOPEN_FAILED")
        return

    if (record.get("metric_value") != expected["metric_value"]
            or record.get("status") != expected["status"]):
        raise RuntimeError("SOURCE_BRIEF_EVALUATION_REOPEN_FAILED")


def _read_verified_evaluations(verified: dict[str, Any], *, connection=None) -> list[dict[str, Any]]:
    """Return only exact artifact-bound checks; malformed checks remain pending."""
    records = []
    for expected in _evaluation_expectations(verified):
        record = _read_evaluation(expected["evaluation_id"], connection=connection)
        if record is None:
            continue
        try:
            _validate_evaluation_record(record, expected)
        except RuntimeError as exc:
            if str(exc) != "SOURCE_BRIEF_EVALUATION_REOPEN_FAILED":
                raise
            continue
        records.append(record)
    return records


def _record_evaluations(verified: dict[str, Any], *, connection=None) -> list[dict[str, Any]]:
    for expected in _evaluation_expectations(verified):
        prior = _read_evaluation(expected["evaluation_id"], connection=connection)
        if expected["historical_media"] and prior:
            # Historical provider results stay immutable; readback validates
            # the recorded contract while projecting current assurance.
            continue
        record_evaluation(
            connection=connection,
            dimension=expected["dimension"], metric_name=expected["metric_name"],
            metric_value=expected["metric_value"], pass_threshold=1.0, warn_threshold=0.8,
            source=expected["source"], evidence_ref=expected["evidence_ref"],
            metadata=expected["metadata"], evaluation_id=expected["evaluation_id"],
        )
    return _read_verified_evaluations(verified, connection=connection)


def _evaluation_state(job_id: str, records: list[dict[str, Any]]) -> str:
    expected = set(_evaluation_ids(job_id).values())
    present = {
        record.get("evaluation_id") for record in records
        if isinstance(record, dict)
    }
    return "recorded" if expected <= present else "pending_recovery"


def _quality_reviews(verified: dict[str, Any]) -> dict[str, Any]:
    row, snapshot = verified["row"], verified["snapshot"]
    evidence_refs = {f"daily_reports:{row['report_id']}:{row['artifact_hash']}"}
    media = snapshot["multimodal"]
    if media.get("state") == "complete" and media.get("evidence_ref"):
        evidence_refs.add(media["evidence_ref"])
    business = snapshot.get("business_analysis") or {}
    if business.get("state") == "draft" and business.get("evidence_ref"):
        evidence_refs.add(business["evidence_ref"])
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
    from .operator_review import read_operator_reviews
    row, snapshot, brief = verified["row"], verified["snapshot"], verified["source_brief"]
    if snapshot.get("schema") == SHARED_JOB_SCHEMA:
        return _shared_response(verified, evaluations)
    return {
        "job_id": snapshot["job_id"], "job_state": "completed",
        "artifact_outcome": {
            "state": "persisted_and_reopened_verified", "report_id": row["report_id"],
            "artifact_hash": row["artifact_hash"], "source_count": row["total_notes"],
        },
        "source_brief": brief, "multimodal": snapshot["multimodal"],
        "business_analysis": snapshot.get("business_analysis", {"state": "not_requested"}),
        "research_analysis": snapshot.get("research_analysis"), "research": snapshot.get("research"),
        "hypothesis_review_origin": snapshot.get("hypothesis_review_origin"),
        "reference": snapshot.get("reference"), "reference_context": snapshot.get("reference_context"),
        "reference": snapshot.get("reference"),
        "business_question": snapshot.get("business_question"),
        "requested_source_ids": snapshot.get("requested_source_ids"),
        "revision": snapshot.get("revision"),
        "operator_review": read_operator_reviews(verified),
        "evaluation": {
            "state": _evaluation_state(snapshot["job_id"], evaluations),
            "records": evaluations,
            "quality_review": _quality_reviews(verified),
        },
        "requested_image_source_ref": snapshot.get("requested_image_source_ref"),
        "retry_of_job_id": snapshot.get("retry_of_job_id"),
        "review_status": "HUMAN_PENDING",
    }


def create_source_brief_job(
    con, *, product_id=None, global_scope=None, entity_label=None, actor_id: str,
    permission_audit_ref: str, trace_id: str, job_id: str,
    subject_id: str | None = None, brand_focus_id: str | None = None,
    limit: int = 30, multimodal_result: dict[str, Any] | None = None,
    image_source_ref: str | None = None, image_actor: Any = None,
    retry_of_job_id: str | None = None,
    business_question: str | None = None,
    source_ids: list[str] | None = None,
    revision_reference: dict | None = None,
    before_persist=None, scope_kind=None, version=None, research=None, task_guard=None, reference=None,
) -> dict[str, Any]:
    """Create or recover a server-authorized scoped Source Brief report job.

    ``con`` must be the caller's authorized canonical read connection. Permission
    enforcement remains at the API/Permission boundary; this owner records its
    real audit reference and binds all reads/evaluations to actor and exact scope.
    """
    _validate_actor_refs(actor_id, permission_audit_ref, trace_id, job_id)
    if research is not None and (type(research) is not dict or set(research) - {'dimension','regions','languages','decision_brief'}):
        raise ValueError('RESEARCH_METADATA_INVALID')
    if scope_kind is not None or version is not None:
        scope = _scope_material(product_id=product_id, global_scope=global_scope,
            entity_label=entity_label, subject_id=subject_id, brand_focus_id=brand_focus_id,
            scope_kind=scope_kind, version=version)
        return _create_shared_report(actor=image_actor, actor_id=actor_id, scope=scope,
            job_id=job_id, permission_audit_ref=permission_audit_ref, trace_id=trace_id,
            source_ids=source_ids, question=business_question, limit=limit,
            revision=revision_reference, before_persist=before_persist, research=research, task_guard=task_guard, reference=reference)

    from canonical_data import validate_source_ids
    source_ids = validate_source_ids(source_ids, limit=min(limit, 8) if business_question is not None else limit)
    if business_question is not None and (
        not isinstance(business_question, str) or not 4 <= len(business_question.strip()) <= 1500
    ):
        raise ValueError("SOURCE_BRIEF_BUSINESS_QUESTION_INVALID")
    scope = _scope_material(
        product_id=product_id, global_scope=global_scope, entity_label=entity_label,
        subject_id=subject_id, brand_focus_id=brand_focus_id,
    )
    reference_work = _read_research_reference(reference, actor=image_actor, scope=scope)
    existing = _read_report(job_id)
    if existing:
        verified = _verify_report(existing, job_id=job_id, actor_id=actor_id, expected_scope=scope, actor=image_actor)
        if before_persist is not None:
            before_persist()
        evaluations = _record_evaluations(verified)
        return _response(verified, evaluations)

    revision = None
    if revision_reference is not None:
        from .operator_review import resolve_report_revision
        if not isinstance(revision_reference, dict):
            raise ValueError("REPORT_REVISION_REFERENCE_INVALID")
        if revision_reference.get("parent_job_id") == job_id:
            raise ValueError("REPORT_REVISION_SELF_PARENT")
        inherited = resolve_report_revision(revision_reference, actor_id=actor_id, expected_scope=scope)
        parent = get_source_brief_job(revision_reference['parent_job_id'], actor_id=actor_id,
                                     expected_scope=scope, actor=image_actor)
        if research != parent.get('research') or reference != parent.get('reference'):
            raise PermissionError('REPORT_REVISION_INPUT_MISMATCH')
        if (business_question != inherited["business_question"] or source_ids != inherited["source_ids"]
                or image_source_ref != inherited["image_source_ref"]):
            raise PermissionError("REPORT_REVISION_INPUT_MISMATCH")
        revision = inherited["revision_context"]

    def before_evidence():
        _read_research_reference(reference, actor=image_actor, scope=scope)
        if before_persist is not None:
            before_persist()
        if revision is not None:
            current = resolve_report_revision(revision_reference, actor_id=actor_id, expected_scope=scope)
            if current["revision_context"] != revision:
                raise RuntimeError("REPORT_REVISION_PARENT_CHANGED")

    brief = build_scoped_source_brief(
        con, product_id=product_id, global_scope=global_scope, entity_label=entity_label,
        subject_id=subject_id, brand_focus_id=brand_focus_id, limit=limit,
        include_analysis_text=business_question is not None,
        source_ids=source_ids,
        analysis_question=business_question,
        actor_ref=actor_id,
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
                or not record.get("canonical_id")
                or record["evidence_id"] != record["scope_evidence_ref"]):
            raise RuntimeError("SOURCE_BRIEF_CANONICAL_EVIDENCE_INVALID")
    if not isinstance(brief.get("markdown"), str) or not isinstance(brief.get("content_hash"), str):
        raise RuntimeError("SOURCE_BRIEF_CANONICAL_ARTIFACT_INVALID")
    if brief["content_hash"] != hashlib.sha256(brief["markdown"].encode("utf-8")).hexdigest():
        raise RuntimeError("SOURCE_BRIEF_CANONICAL_CONTENT_HASH_MISMATCH")

    from agent_research.source_bound import analyze_source_records
    analyze_source_records(business_question or "Source review", [], **(research or {}))
    try:
        admitted = _resolve_source_records({"source_brief": brief}, actor=image_actor)
        research_analysis = analyze_source_records(business_question or "Source review", admitted["records"],
            actor_id=actor_id, scope=scope, **(research or {}))
    except (ValueError, LookupError, PermissionError, RuntimeError):
        research_analysis = {"status": "source_use_unavailable", "ranked_findings": [],
            "reason": "ORIGINAL_SOURCE_USE_NOT_VERIFIED", "fact_verified": False,
            "limitations": ["Source metadata is available; original content use has not been authorized and verified."]}

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
    business_analysis = {"state": "not_requested"}
    if business_question is not None:
        from .business_brief import analyze_business_brief
        sources = brief.pop("_analysis_sources", [])
        if source_ids is not None and len(sources) != len(source_ids):
            business_analysis = {"state": "unavailable", "reason": "SOURCE_BRIEF_SELECTED_BODY_UNAVAILABLE",
                                 "real_input_bound": False, "review_status": "HUMAN_PENDING"}
        try:
            if business_analysis["state"] == "not_requested":
                business_analysis = analyze_business_brief(
                    question=business_question, sources=sources, scope=_media_scope(scope),
                    job_id=job_id, actor_ref=actor_id,
                    revision=revision, before_evidence=before_evidence, actor=image_actor,
                    sample={"available_brief_count": count, "analyzed_source_count": len(sources),
                            "selection": ("explicit operator-selected verified sources; task-term window up to 1200 characters each"
                                          if source_ids is not None else
                                          "latest verified nonempty bodies; at most 8, task-term window up to 1200 characters each"),
                            "omitted_source_count": count - len(sources),
                            "has_truncated_bodies": any(source["truncated"] for source in sources),
                            "coverage": "PARTIAL"},
                )
        except Exception:
            business_analysis = {"state": "error", "reason": "BUSINESS_BRIEF_EXECUTION_OR_PERSISTENCE_FAILED",
                                 "real_input_bound": False, "review_status": "HUMAN_PENDING"}
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
        "business_analysis": business_analysis, "business_question": business_question,
        "research_analysis": research_analysis, "research": research, "reference": reference,
        "hypothesis_review_origin": ({"parent_job_id":revision_reference["parent_job_id"],"reference":parent.get("hypothesis_review")} if revision_reference else None),
        "reference_context": _reference_context(reference, actor=image_actor, scope=scope),
        "requested_source_ids": source_ids,
        "revision": revision,
        "requested_image_source_ref": image_source_ref, "retry_of_job_id": retry_of_job_id,
        "review_status": "HUMAN_PENDING",
    }
    source_snapshot = _json(snapshot_data)
    report_date = datetime.now(timezone.utc).date().isoformat()
    artifact_hash = _hash_artifact(
        report_id=job_id, report_type=report_type, report_date=report_date,
        total_notes=count, summary=brief["markdown"], source_snapshot=source_snapshot,
    )
    before_evidence()
    _persist_report({
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
    }, task_guard=task_guard)
    reopened = _read_report(job_id)
    if not reopened:
        raise RuntimeError("SOURCE_BRIEF_REPORT_REOPEN_FAILED")
    verified = _verify_report(reopened, job_id=job_id, actor_id=actor_id, expected_scope=scope, actor=image_actor)
    evaluations = _record_evaluations(verified)
    return _response(verified, evaluations)


def get_source_brief_job(job_id: str, *, actor_id: str,
                         expected_scope: dict[str, Any] | None = None,
                         actor=None, connection=None) -> dict[str, Any]:
    """Reopen a persisted job for the same actor and, when supplied, exact scope."""
    if not isinstance(actor_id, str) or not _ACTOR_ID.fullmatch(actor_id):
        raise ValueError("SOURCE_BRIEF_ACTOR_REQUIRED")
    if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id):
        raise ValueError("SOURCE_BRIEF_SERVER_JOB_ID_INVALID")
    if connection is not None and actor is None:
        raise PermissionError("SOURCE_BRIEF_SERVER_ACTOR_REQUIRED")
    options = {} if connection is None else {"connection": connection}
    row = _read_report(job_id, **options)
    if not row:
        raise LookupError("SOURCE_BRIEF_JOB_NOT_FOUND")
    verified = _verify_report(row, job_id=job_id, actor_id=actor_id, expected_scope=expected_scope, actor=actor, connection=connection)
    if verified["snapshot"].get("schema") == SHARED_JOB_SCHEMA:
        if actor is None:
            raise PermissionError("SOURCE_BRIEF_SERVER_ACTOR_REQUIRED")
        view = _shared_response(verified, _read_verified_evaluations(verified, connection=connection))
        if len(view["evaluation"]["records"]) != len(_evaluation_ids(job_id)):
            view["evaluation"]["state"] = "pending_recovery"
        return _with_hypothesis_reviews(view, actor=actor, actor_id=actor_id, scope=SHARED_SCOPE, connection=connection)

    if connection is not None:
        committed = _read_report(job_id)
        if committed is None or any(committed.get(key) != row.get(key) for key in (
            "report_id", "artifact_hash", "source_snapshot", "summary", "total_notes", "generator_version"
        )):
            raise RuntimeError("SOURCE_BRIEF_NOT_COMMITTED")
    if actor is not None:
        from contextlib import nullcontext
        from lumenis.shared.reporting.saved_work import authorize
        import canonical_data
        scope = verified["snapshot"]["scope"]
        target = _media_scope(scope)
        identity = authorize(actor, target, action="read", **options)
        current_ref = identity.get("principal_ref") or f"actor:{identity.get('actor_id')}"
        if current_ref != actor_id:
            raise PermissionError("SOURCE_BRIEF_ACTOR_MISMATCH")
        reader = get_repository().connection(read_only=True, wal=False) if connection is None else nullcontext(connection)
        with reader as con:
            for source in verified["source_brief"]["records"]:
                item = _resolve_current_source(con, source, scope["product_id"])
                original = {"domain_id": item[4], "subject_id": item[5] or None,
                            "brand_focus_id": item[6] or None, "global_scope": not bool(item[5] or item[6])}
                authorize(actor, original, action="read", connection=con)
                canonical_data._validate_canonical_scope(con, canonical_data.CanonicalRecord(
                    canonical_id=item[0], source_id=item[1], source_type=item[2],
                    product_id=item[3], domain_id=item[4], subject_id=item[5],
                    brand_focus_id=item[6], scope_status=item[7],
                    scope_evidence_ref=str(item[8])))
                if source.get("profile_research") is not None:
                    from .operational_brief import project_profile_research
                    cursor = con.execute("SELECT * FROM canonical_data WHERE canonical_id=?", (item[0],))
                    raw = cursor.fetchone()
                    current = dict(zip((column[0] for column in cursor.description), raw)) if raw else None
                    if current is None or project_profile_research(
                        con, current, item[8], actor_ref=actor_id
                    ) != source["profile_research"]:
                        raise PermissionError("SOURCE_BRIEF_PROFILE_SOURCE_CHANGED")
    if verified["snapshot"].get("research_analysis", {}).get("ranked_findings"):
        if actor is None:
            raise PermissionError("SOURCE_BRIEF_SERVER_ACTOR_REQUIRED")
        admitted = _resolve_source_records({"source_brief": verified["source_brief"]}, actor=actor, connection=connection)
        from agent_research.source_bound import analyze_source_records
        expected_analysis = analyze_source_records(verified["snapshot"].get("business_question") or "Source review",
            admitted["records"], actor_id=actor_id, scope=verified["snapshot"]["scope"],
            **(verified["snapshot"].get("research") or {}))
        if expected_analysis != verified["snapshot"]["research_analysis"]:
            raise PermissionError("SOURCE_BRIEF_RESEARCH_SOURCE_CHANGED")
    _read_research_reference(verified["snapshot"].get("reference"), actor=actor, scope=verified["snapshot"]["scope"], connection=connection)
    present = _read_verified_evaluations(verified)
    state = "recorded" if len(present) == len(_evaluation_ids(job_id)) else "pending_recovery"
    result = _response(verified, present)
    result["evaluation"]["state"] = state
    if actor is not None:
        authorize(actor, target, action="read", **options)
    return _with_hypothesis_reviews(result, actor=actor, actor_id=actor_id,
        scope=verified['snapshot']['scope'], connection=connection)


def _resolve_current_source(con, source: dict[str, Any], product_id: str):
    """Resolve the report's exact Canonical row, including legacy snapshots.

    New snapshots pin ``canonical_id``. Older snapshots are still recoverable by
    their stored source type and signed Evidence reference. For legacy document
    records, the unique parent document disambiguates its selected-row children.
    """
    columns = (
        "canonical_id,source_id,source_type,product_id,domain_id,subject_id,"
        "brand_focus_id,scope_status,scope_evidence_ref"
    )
    expected_id = source.get("canonical_id")
    if expected_id is not None:
        rows = con.execute(
            f"SELECT {columns} FROM canonical_data WHERE canonical_id=? AND source_id=? AND product_id=?",
            (expected_id, source["source_id"], product_id),
        ).fetchall()
    else:
        rows = con.execute(
            f"SELECT {columns} FROM canonical_data WHERE source_id=? AND product_id=?",
            (source["source_id"], product_id),
        ).fetchall()
    if not rows:
        raise RuntimeError("SOURCE_BRIEF_CURRENT_SOURCE_INVALID")

    evidence_ref = str(source["scope_evidence_ref"])
    matching = [row for row in rows if str(row[8] or "") == evidence_ref]
    if not matching:
        raise RuntimeError("SOURCE_BRIEF_CURRENT_SOURCE_CHANGED")
    expected_type = source.get("source_type")
    if expected_type is not None:
        matching = [row for row in matching if row[2] == expected_type]
    if expected_id is None and expected_type == "document":
        # Older reports did not store canonical_id. The signed parent document
        # is the logical source; selected document_row records are projections.
        matching = [row for row in matching if row[2] == "document"]
    if len(matching) != 1:
        raise RuntimeError("SOURCE_BRIEF_CURRENT_SOURCE_INVALID")
    return matching[0]


def list_source_brief_jobs(*, actor, scope: dict[str, Any], limit: int = 30, cursor: str | None = None) -> dict[str, Any]:
    """Discover only the current actor's exact-scope report artifacts, bounded.

    SavedWork documents are a different resource type. This owner reopens each
    candidate and matches evaluations to its current artifact bytes; it never
    assigns daily_reports evaluations to a SavedWork artifact.
    """
    from .saved_work import authorize
    if scope == SHARED_SCOPE:
        return _list_shared_reports(actor=actor, scope=scope, limit=limit, cursor=cursor)
    if cursor is not None and (not isinstance(cursor, str) or not cursor.isdigit() or int(cursor) < 1):
        raise ValueError("SOURCE_BRIEF_CURSOR_INVALID")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("SOURCE_BRIEF_LIST_LIMIT_INVALID")
    context = authorize(actor, scope, action="read")
    actor_ref = context.get("principal_ref") or f"actor:{context.get('actor_id')}"
    selected = {key: context[key] for key in ("domain_id", "subject_id", "brand_focus_id", "global_scope")}
    product = "CTH" if selected["domain_id"] == "cth" else "ZBMP"
    with get_repository().connection(read_only=True, wal=False) as con:
        columns = {row[1] for row in con.execute("PRAGMA table_info(daily_reports)")}
        evaluation_columns = {row[1] for row in con.execute("PRAGMA table_info(evaluation_records)")}
        missing_reason = ("SOURCE_BRIEF_STORAGE_NOT_INITIALIZED"
                          if not {"id", "report_id", "source_snapshot", "artifact_hash"} <= columns
                          else "SOURCE_BRIEF_EVALUATION_STORAGE_NOT_INITIALIZED"
                          if not {"evaluation_id", "dimension", "metadata", "evidence_ref"} <= evaluation_columns
                          else None)
        if missing_reason:
            if authorize(actor, selected, action="read") != context:
                raise PermissionError("SOURCE_BRIEF_PRINCIPAL_CHANGED")
            return {"resource_type": "source_brief_job", "items": [], "state": "UNAVAILABLE",
                    "reason": missing_reason, "scanned_count": 0,
                    "returned_count": 0, "rejected_count": 0, "read_complete": False,
                    "has_more": None, "limit": limit}
        snapshot = "CASE WHEN json_valid(source_snapshot) THEN source_snapshot ELSE '{}' END"
        # Restrict identity and all authorization dimensions before reading or
        # counting candidates. No global population count is exposed.
        rows = con.execute(f"""SELECT id,report_id,source_snapshot FROM daily_reports
            WHERE json_extract({snapshot},'$.schema')=?
              AND json_extract({snapshot},'$.actor_id')=?
              AND json_extract({snapshot},'$.scope.domain_id')=?
              AND json_extract({snapshot},'$.scope.product_id')=?
              AND json_extract({snapshot},'$.scope.global')=?
              AND json_extract({snapshot},'$.scope.subject_id') IS ?
              AND json_extract({snapshot},'$.scope.brand_focus_id') IS ?
            AND (? IS NULL OR id < ?)
            ORDER BY id DESC LIMIT ?""",
            (JOB_SCHEMA, actor_ref, selected["domain_id"], product, int(selected["global_scope"]),
             selected["subject_id"], selected["brand_focus_id"], cursor, cursor, limit + 1)).fetchall()
    items = []
    rejected = 0
    for row in rows[:limit]:
        try:
            stored_scope = json.loads(row["source_snapshot"])["scope"]
            if _media_scope(stored_scope) != selected:
                raise PermissionError("SOURCE_BRIEF_SCOPE_MISMATCH")
            job = get_source_brief_job(row["report_id"], actor_id=actor_ref,
                                      expected_scope=stored_scope, actor=actor)
            artifact = job["artifact_outcome"]
            expected = set(_evaluation_ids(job["job_id"]).values())
            # Reuse the report owner's exact validated checks. A second broad
            # artifact query could re-attach a stable ID whose metric fields or
            # timestamp no longer match the persisted report contract.
            job_evaluation = job["evaluation"]
            checks = job_evaluation["records"]
            matching = {item["evaluation_id"] for item in checks}
            quality_review = job_evaluation.get("quality_review") or {}
            evaluations = checks + list(quality_review.get("records") or [])
            # Counts are current artifact-bound evaluation checks, never report
            # quality, market effect, or a global evaluation-table population.
            counts = dict.fromkeys(("pass", "warn", "fail", "unknown"), 0)
            for evaluation_record in evaluations:
                status = evaluation_record.get("status")
                counts[status if status in counts else "unknown"] += 1
            missing_evaluations = len(expected - matching)
            counts["unknown"] += missing_evaluations
            # Reopen after evaluation lookup: withdrawal or artifact replacement
            # during the read cannot leave a stale successful distribution.
            current_job = get_source_brief_job(job["job_id"], actor_id=actor_ref,
                                               expected_scope=stored_scope, actor=actor)
            if current_job["artifact_outcome"]["artifact_hash"] != artifact["artifact_hash"]:
                raise RuntimeError("SOURCE_BRIEF_ARTIFACT_CHANGED")
            items.append({"resource_type": "source_brief_job", "job_id": job["job_id"],
                "artifact_hash": artifact["artifact_hash"], "revision": job.get("revision"),
                "source_count": artifact["source_count"], "review_status": job["review_status"],
                "evaluation_state": job_evaluation["state"],
                "evaluation_counts": counts, "missing_evaluation_count": missing_evaluations,
                "evaluation_count_unit": "artifact_bound_check",
                "evaluations": [{key: item.get(key) for key in
                    ("evaluation_id", "metric_name", "status", "evaluated_at", "evidence_ref")}
                    for item in evaluations]})
        except (ValueError, LookupError, PermissionError, RuntimeError):
            rejected += 1
    if authorize(actor, selected, action="read") != context:
        raise PermissionError("SOURCE_BRIEF_PRINCIPAL_CHANGED")
    more = len(rows) > limit
    complete = not more and rejected == 0
    return {"resource_type": "source_brief_job", "items": items,
            "state": "PARTIAL" if not complete else "READY" if items else "EMPTY",
            "scanned_count": min(len(rows), limit), "returned_count": len(items),
            "rejected_count": rejected, "read_complete": complete, "has_more": more, "limit": limit,
            "next_cursor": str(rows[limit - 1]["id"]) if more else None}


SHARED_JOB_SCHEMA = "source-brief-shared-job:v1"
SHARED_SCOPE = {"scope_kind": "shared_workspace", "version": 1}


def _shared_identity(actor, actor_id, *, action="read", connection=None):
    from .saved_work import authorize_saved_work
    if actor is None:
        raise PermissionError("SOURCE_BRIEF_SERVER_ACTOR_REQUIRED")
    identity = authorize_saved_work(actor, SHARED_SCOPE, action=action, connection=connection)
    if (identity.get("principal_ref") or f"actor:{identity.get('actor_id')}") != actor_id:
        raise PermissionError("SOURCE_BRIEF_ACTOR_MISMATCH")
    return identity


def _shared_typed_analysis(brief, *, actor, connection=None):
    """Current original-byte projection; supplied SavedWork parsed payload is ignored."""
    from lumenis.importer.documents import read_private_document_typed_source
    from .business_brief import analyze_shared_typed_source_records
    sources, omitted = [], []
    for record in brief["records"]:
        source = read_private_document_typed_source(record["source_id"], actor=actor,
                                                    scope=SHARED_SCOPE, connection=connection)
        if source["source_record"] != record:
            raise PermissionError("SOURCE_BRIEF_CURRENT_SOURCE_CHANGED")
        if source["format"] not in {"excel", "word", "pdf", "csv"} or not source["source_rows"]:
            omitted.append({"source_id": record["source_id"], "reason": "NO_TYPED_ROWS"})
        else:
            sources.append(source)
    result = (analyze_shared_typed_source_records(question="Review explicit source fields", sources=sources)
              if sources else {"schema": "lumenis.shared-typed-source-analysis/v1",
                               "state": "NOT_APPLICABLE", "ai_analysis": "NOT_PERFORMED"})
    return {**result, "omitted_sources": omitted,
            "coverage": "PARTIAL" if omitted else "COMPLETE_INPUTS_ONLY"}


def _append_typed_summary(brief, analysis):
    """Human-readable deterministic results on the existing report artifact."""
    from .operational_brief import _markdown_text
    if "row_coverage" not in analysis:
        return brief
    coverage = analysis["row_coverage"]
    lines = [brief["markdown"], "", "## Explicit source fields (not independently verified facts)",
             "Data rows: " + str(coverage["total_rows"]),
             "Preserved header rows: " + str(coverage["preserved_header_rows"]),
             "Formula values are not evaluated; missing values are not zero."]
    for metric in analysis["metrics"]:
        for field in metric["explicit_fields"]:
            label = _markdown_text(str(field["table_locator"]))
            lines.append(f"{metric['metric']} / {label} / column {field['column_index']}: "
                         f"known={field['known_count']}, missing={field['missing_count']}, "
                         f"formula={field['formula_count']}, invalid={field['invalid_count']}, "
                         f"sum of imported known values={field['sum_of_known_imported_values']}")
    lines.append("These counts do not establish audience, demand, causality, sales or outcomes.")
    markdown = "\n".join(lines)
    return {**brief, "markdown": markdown, "content_hash": hashlib.sha256(markdown.encode()).hexdigest()}


def _verify_shared_report(row, snapshot, *, job_id, actor_id, expected_scope, actor, connection=None):
    _shared_identity(actor, actor_id, connection=connection)
    if (snapshot.get("actor_id") != actor_id or snapshot.get("job_id") != job_id
            or row.get("report_id") != job_id):
        raise PermissionError("SOURCE_BRIEF_ACTOR_MISMATCH")
    if snapshot.get("scope") != SHARED_SCOPE or (expected_scope is not None and expected_scope != SHARED_SCOPE):
        raise PermissionError("SOURCE_BRIEF_SCOPE_MISMATCH")
    digest = _hash_artifact(report_id=job_id, report_type=row["report_type"],
        report_date=row["report_date"], total_notes=row["total_notes"], summary=row["summary"],
        source_snapshot=row["source_snapshot"])
    if row.get("artifact_hash") != digest:
        raise RuntimeError("SOURCE_BRIEF_ARTIFACT_HASH_MISMATCH")
    brief = snapshot.get("source_brief")
    if (not isinstance(brief, dict) or brief.get("scope") != SHARED_SCOPE
            or brief.get("markdown") != row["summary"]
            or brief.get("content_hash") != hashlib.sha256(row["summary"].encode()).hexdigest()
            or not isinstance(brief.get("records"), list)
            or row["total_notes"] != len(brief["records"])
            or snapshot.get("requested_source_ids") != [r.get("source_id") for r in brief["records"]]):
        raise RuntimeError("SOURCE_BRIEF_STORED_BRIEF_INVALID")
    from lumenis.importer.documents import read_private_document_source
    for source in brief["records"]:
        current = read_private_document_source(source["source_id"], actor=actor, scope=SHARED_SCOPE, connection=connection)
        if current != source:
            raise PermissionError("SOURCE_BRIEF_CURRENT_SOURCE_CHANGED")
    if "typed_source_analysis" in snapshot:
        current_typed = _shared_typed_analysis(brief, actor=actor, connection=connection)
        if current_typed != snapshot["typed_source_analysis"]:
            raise PermissionError("SOURCE_BRIEF_TYPED_SOURCE_CHANGED")
    _read_research_reference(snapshot.get("reference"), actor=actor, scope=SHARED_SCOPE, connection=connection)
    _shared_identity(actor, actor_id, connection=connection)
    return {"row": row, "snapshot": snapshot, "source_brief": brief, "actor": actor}


def _shared_response(verified, evaluations):
    snapshot, row, brief = verified["snapshot"], verified["row"], verified["source_brief"]
    return {"job_id": snapshot["job_id"],
            "job_state": "completed" if brief["records"] else "needs_sources",
            "artifact_outcome": {"state": "persisted_and_reopened_verified", "report_id": row["report_id"],
                                 "artifact_hash": row["artifact_hash"], "source_count": len(brief["records"])},
            "source_brief": brief, "business_question": snapshot.get("business_question"),
            "typed_source_analysis": snapshot.get("typed_source_analysis"),
            "business_analysis": snapshot.get("business_analysis"), "research": snapshot.get("research"), "reference": snapshot.get("reference"),
            "hypothesis_review_origin": snapshot.get("hypothesis_review_origin"),
            "reference_context": snapshot.get("reference_context"),
            "requested_source_ids": snapshot["requested_source_ids"], "revision": snapshot.get("revision"),
            "multimodal": snapshot["multimodal"], "requested_image_source_ref": None,
            "retry_of_job_id": None, "review_status": "HUMAN_PENDING",
            "operator_review": {"state": "use_saved_work_review", "records": []},
            "evaluation": {"state": "recorded" if len(evaluations) == 3 else "pending_recovery",
                           "records": evaluations, "quality_review": {"state": "not_recorded", "records": []}}}


def _create_shared_report(*, actor, actor_id, scope, job_id, permission_audit_ref, trace_id,
                          source_ids, question, limit, revision, before_persist, research, task_guard=None, reference=None):
    _shared_identity(actor, actor_id, action="write")
    _read_research_reference(reference, actor=actor, scope=scope)
    existing = _read_report(job_id)
    if existing:
        return get_source_brief_job(job_id, actor_id=actor_id, expected_scope=scope, actor=actor)
    from .operational_brief import build_shared_source_brief
    if question is not None and (not isinstance(question, str) or not 4 <= len(question.strip()) <= 1500):
        raise ValueError("SOURCE_BRIEF_BUSINESS_QUESTION_INVALID")
    revision_context = None
    hypothesis_origin = None
    if revision is not None:
        inherited = resolve_shared_report_revision(revision, actor=actor, actor_id=actor_id)
        if (question != inherited["business_question"] or source_ids != inherited["source_ids"]
                or research != inherited.get("research") or reference != inherited.get("reference")):
            raise PermissionError("REPORT_REVISION_INPUT_MISMATCH")
        revision_context = inherited["revision_context"]
        hypothesis_origin = inherited["hypothesis_review_origin"]
    brief = build_shared_source_brief(actor=actor, source_ids=source_ids, limit=limit, question=question)
    typed_analysis = _shared_typed_analysis(brief, actor=actor)
    brief = _append_typed_summary(brief, typed_analysis)
    from agent_research.source_bound import analyze_source_records
    analysis = analyze_source_records(question or "Review the selected sources", brief["records"],
                                     actor_id=actor_id, scope=scope, **(research or {}))
    snapshot = {"schema": SHARED_JOB_SCHEMA, "job_id": job_id, "actor_id": actor_id,
        "permission_audit_ref": permission_audit_ref, "trace_id": trace_id, "scope": scope,
        "source_brief": brief, "requested_source_ids": source_ids or [],
        "typed_source_analysis": typed_analysis,
        "business_question": question, "business_analysis": analysis, "research": research, "reference": reference,
        "hypothesis_review_origin": hypothesis_origin,
        "reference_context": _reference_context(reference, actor=actor, scope=scope),
        "revision": revision_context, "multimodal": {"state": "not_requested"},
        "evaluation_ids": _evaluation_ids(job_id)}
    encoded = _json(snapshot)
    date = datetime.now(timezone.utc).date().isoformat()
    report_type = "source_brief_job:shared:" + hashlib.sha256((actor_id + job_id).encode()).hexdigest()
    digest = _hash_artifact(report_id=job_id, report_type=report_type, report_date=date,
        total_notes=len(brief["records"]), summary=brief["markdown"], source_snapshot=encoded)
    if before_persist:
        before_persist()
    # Revalidate each original after analysis and immediately before persistence.
    current = build_shared_source_brief(actor=actor, source_ids=source_ids, limit=limit, question=question)
    current_typed = _shared_typed_analysis(current, actor=actor)
    current = _append_typed_summary(current, current_typed)
    if current != brief or current_typed != typed_analysis:
        raise PermissionError("SOURCE_BRIEF_CURRENT_SOURCE_CHANGED")
    _shared_identity(actor, actor_id, action="write")
    if before_persist:
        before_persist()
    _persist_report({"report_id": job_id, "report_type": report_type,
        "report_date": date, "total_notes": len(brief["records"]), "summary": brief["markdown"],
        "source_snapshot": encoded, "artifact_hash": digest, "generator_version": GENERATOR_VERSION,
        "data_version": "private-source-brief:" + brief["content_hash"]}, task_guard=task_guard,
        actor_guard={"actor": actor, "actor_id": actor_id, "sources": brief["records"], "reference": reference})
    verified = _verify_report(_read_report(job_id), job_id=job_id, actor_id=actor_id,
                              expected_scope=scope, actor=actor)
    with get_repository().transaction() as con:
        con.execute('BEGIN IMMEDIATE')
        _shared_identity(actor, actor_id, action='write', connection=con)
        get_source_brief_job(job_id, actor=actor, actor_id=actor_id, expected_scope=scope, connection=con)
        evaluations = _record_evaluations(verified, connection=con)
        _shared_identity(actor, actor_id, action='write', connection=con)
    return _shared_response(verified, evaluations)


def write_shared_report_review(job_id, *, actor, actor_id, submission_id, decision, notes):
    from .operator_review import _validate_input
    from .saved_work import save_work
    notes = _validate_input(job_id, actor_id, SHARED_SCOPE, submission_id, decision, notes)
    _shared_identity(actor, actor_id, action="write")
    report = get_source_brief_job(job_id, actor_id=actor_id, expected_scope=SHARED_SCOPE, actor=actor)
    payload = {"shared_report_review": {"schema": "shared-report-review/v1", "job_id": job_id,
        "artifact_hash": report["artifact_outcome"]["artifact_hash"], "decision": decision,
        "notes": notes, "actor_id": actor_id, "fact_verification": "NOT_ESTABLISHED"}}
    saved = save_work(title="Research review", markdown=notes, kind="research", payload=payload,
        citations=[], request_id="review-" + submission_id, actor=actor, scope=SHARED_SCOPE)
    review_id = saved["artifact"]["artifact_id"]
    review_hash = saved["artifact"]["sha256"]
    evaluation_id = hashlib.sha256(("shared-report-review:" + review_id + ":" + review_hash).encode()).hexdigest()
    with get_repository().transaction() as con:
        con.execute("BEGIN IMMEDIATE")
        _shared_identity(actor, actor_id, action="write", connection=con)
        get_source_brief_job(job_id, actor_id=actor_id, expected_scope=SHARED_SCOPE,
                             actor=actor, connection=con)
        record_evaluation(connection=con, dimension="report", metric_name="operator_disposition", metric_value=None, pass_threshold=1.0, warn_threshold=0.8,
            source="shared_report_review", evidence_ref="saved_work:" + review_id + ":" + review_hash,
            evaluation_id=evaluation_id, metadata={**payload["shared_report_review"],
                "scope": SHARED_SCOPE, "review_id": review_id, "review_artifact_hash": review_hash,
                "evaluation_basis": "Operator feedback only; business effect and fact verification unknown."})
        _shared_identity(actor, actor_id, action="write", connection=con)
    read_shared_report_review(job_id, review_id, actor=actor, actor_id=actor_id)
    return {**payload["shared_report_review"], "review_id": review_id,
            "review_artifact_hash": review_hash, "evaluation_id": evaluation_id, "state": "recorded"}


def resolve_shared_report_revision(reference, *, actor, actor_id):
    from .saved_work import read_committed_work
    if not isinstance(reference, dict) or set(reference) != {"parent_job_id", "review_id"}:
        raise ValueError("REPORT_REVISION_REFERENCE_INVALID")
    review = read_committed_work(reference["review_id"], actor=actor, scope=SHARED_SCOPE)
    binding = review["document"]["payload"].get("shared_report_review", {})
    parent = get_source_brief_job(reference["parent_job_id"], actor_id=actor_id,
                                 expected_scope=SHARED_SCOPE, actor=actor)
    if (binding.get("schema") != "shared-report-review/v1" or binding.get("actor_id") != actor_id
            or binding.get("job_id") != parent["job_id"]
            or binding.get("artifact_hash") != parent["artifact_outcome"]["artifact_hash"]
            or binding.get("decision") != "request_changes"):
        raise PermissionError("REPORT_REVISION_REVIEW_MISMATCH")
    return {"business_question": parent["business_question"], "source_ids": parent["requested_source_ids"],
            "image_source_ref": None, "research": parent.get("research"), "reference": parent.get("reference"),
            "hypothesis_review_origin": {"parent_job_id":parent["job_id"],"reference":parent.get("hypothesis_review")}, "revision_context": {**reference,
                "parent_artifact_hash": parent["artifact_outcome"]["artifact_hash"],
                "review_artifact_hash": review["artifact"]["sha256"], "feedback": binding["notes"]}}


def _persist_report(report, *, task_guard=None, actor_guard=None):
    """Serialize cancellation versus report commit in the same SQLite writer.

    Synchronous calls retain the existing Reporting writer. Managed tasks use
    this owner-owned insert and verify the exact current worker before writing.
    A cancellation can win before this transaction, or fail after a real result;
    it cannot cancel and then allow an orphaned result to appear later.
    """
    if task_guard is None and actor_guard is None:
        return report_database.save_daily_report(report)
    from ai_task_engine import _MANAGED_REPORT_TASK_CREATOR
    with get_repository().transaction() as con:
        con.execute("BEGIN IMMEDIATE")
        if actor_guard is not None:
            _shared_identity(actor_guard["actor"], actor_guard["actor_id"], action="write", connection=con)
            _read_research_reference(actor_guard.get("reference"), actor=actor_guard["actor"], scope=SHARED_SCOPE, connection=con)
            from lumenis.importer.documents import read_private_document_source
            for source in actor_guard["sources"]:
                if read_private_document_source(source["source_id"], actor=actor_guard["actor"],
                        scope=SHARED_SCOPE, connection=con) != source:
                    raise PermissionError("SOURCE_BRIEF_CURRENT_SOURCE_CHANGED")
        if task_guard is not None:
            row = con.execute("SELECT context_json,status,parameters_json FROM ai_task WHERE task_id=? AND created_by=?",
                              (task_guard["task_id"], _MANAGED_REPORT_TASK_CREATOR)).fetchone()
            if (row is None or row[1] != "running" or row[2] != task_guard["parameters_json"]
                    or json.loads(row[0]).get("job_id") != report["report_id"]):
                raise RuntimeError("SOURCE_BRIEF_TASK_STATE_CONFLICT")
        prior = con.execute("SELECT artifact_hash FROM daily_reports WHERE report_id=?", (report["report_id"],)).fetchone()
        if prior is not None:
            if prior[0] != report["artifact_hash"]:
                raise RuntimeError("SOURCE_BRIEF_TASK_ARTIFACT_CONFLICT")
            return
        fields = ("report_type", "report_date", "total_notes", "summary", "report_id", "artifact_hash",
                  "generator_version", "data_version", "source_snapshot")
        con.execute("INSERT INTO daily_reports(" + ",".join(fields) + ") VALUES (" + ",".join("?" for _ in fields) + ")",
                    tuple(report.get(key) for key in fields))


def _list_shared_reports(*, actor, scope, limit, cursor):
    from .saved_work import authorize_saved_work
    identity = authorize_saved_work(actor, scope, action="read")
    actor_id = identity.get("principal_ref") or f"actor:{identity.get('actor_id')}"
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("SOURCE_BRIEF_LIST_LIMIT_INVALID")
    if cursor is not None and (not isinstance(cursor, str) or not cursor.isdigit() or int(cursor) < 1):
        raise ValueError("SOURCE_BRIEF_CURSOR_INVALID")
    with get_repository().connection(read_only=True, wal=False) as con:
        rows = con.execute("""SELECT id,report_id FROM daily_reports
            WHERE json_valid(source_snapshot)
            AND json_extract(source_snapshot,'$.schema')=?
            AND json_extract(source_snapshot,'$.actor_id')=?
            AND (? IS NULL OR id<?) ORDER BY id DESC LIMIT ?""",
            (SHARED_JOB_SCHEMA, actor_id, cursor, cursor, limit + 1)).fetchall()
    items, rejected = [], 0
    for row in rows[:limit]:
        try:
            job = get_source_brief_job(row[1], actor_id=actor_id, expected_scope=scope, actor=actor)
            items.append({"job_id": job["job_id"], "job_state": job["job_state"],
                          **job["artifact_outcome"], "revision": job["revision"]})
        except (ValueError, LookupError, PermissionError, RuntimeError):
            rejected += 1
    authorize_saved_work(actor, scope, action="read")
    more = len(rows) > limit
    return {"items": items, "has_more": more, "next_cursor": str(rows[limit-1][0]) if more else None,
            "rejected_count": rejected, "read_complete": not more and not rejected,
            "resource_type": "source_brief_job", "returned_count": len(items)}


def resolve_report_sources(job_id, *, actor, actor_id, expected_scope, connection=None):
    """Business/learning admission: fresh original bytes, exact scope and use rights.

    SourceBrief metadata integrity alone is insufficient for downstream content
    use. This reader reopens each original through the existing Source owner.
    """
    from contextlib import nullcontext
    report = get_source_brief_job(job_id, actor_id=actor_id, expected_scope=expected_scope,
                                 actor=actor, connection=connection)
    if report.get('hypothesis_review_state') == 'requires_reassessment':
        raise PermissionError('SOURCE_BRIEF_RESEARCH_REASSESSMENT_REQUIRED')
    return _resolve_source_records(report, actor=actor, connection=connection)


def _resolve_source_records(report, *, actor, connection=None):
    from contextlib import nullcontext
    scope = report["source_brief"]["scope"]
    if scope == SHARED_SCOPE:
        return {"report": report, "records": report["source_brief"]["records"],
                "scope": scope, "allowed_use": "private_custody_and_analysis"}
    from .saved_work import authorize, _verified_evidence
    from .operational_brief import _content_evidence_ref
    reader = get_repository().connection(read_only=True, wal=False) if connection is None else nullcontext(connection)
    resolved = []
    with reader as con:
        for source in report["source_brief"]["records"]:
            identity = _resolve_current_source(con, source, scope["product_id"])
            cursor = con.execute("SELECT * FROM canonical_data WHERE canonical_id=?", (identity[0],))
            raw = cursor.fetchone()
            row = dict(zip((column[0] for column in cursor.description), raw))
            original_scope = {"domain_id": identity[4], "subject_id": identity[5] or None,
                "brand_focus_id": identity[6] or None, "global_scope": not bool(identity[5] or identity[6])}
            context = authorize(actor, original_scope, action="read", connection=con)
            ref = _content_evidence_ref(con, row, str(identity[8]))
            if ref is None:
                raise PermissionError("SOURCE_BRIEF_SOURCE_USE_UNAVAILABLE")
            original = _verified_evidence(con, int(ref.split(":")[-1]), context, actor)
            if (original["asset_id"] != source["source_id"]
                    or original["raw_content"] != row.get("content")
                    or hashlib.sha256(original["raw_content"].encode()).hexdigest() != original["content_hash"]):
                raise PermissionError("SOURCE_BRIEF_ORIGINAL_SOURCE_CHANGED")
            if original["provenance"].get("research_origin") is not None:
                from lumenis.importer.documents import validate_shared_research_origin
                validate_shared_research_origin(original["provenance"]["research_origin"], actor=actor, connection=con)
            provenance = original["provenance"]["provenance"]
            resolved.append({**source, "content_excerpt": original["raw_content"][:1200],
                "truncated": len(original["raw_content"]) > 1200, "character_count": len(original["raw_content"]),
                "content_hash": original["content_hash"], "source_version": original["version"],
                "source_scope": original_scope, "content_evidence_ref": ref,
                "source_artifact_ref": original["provenance"]["source_artifact_ref"],
                "rights": provenance["rights"], "claim_type": "SOURCE_STATEMENT", "fact_verified": False})
        authorize(actor, _media_scope(scope), action="read", connection=con)
    return {"report": report, "records": resolved, "scope": scope,
            "allowed_use": "research_reference"}


def read_shared_report_review(job_id, review_id, *, actor, actor_id):
    """Read an actor-bound disposition and its separate unknown-value Evaluation.

    Missing evaluation is pending recovery, never repaired by a GET.
    """
    from .saved_work import read_committed_work
    report = get_source_brief_job(job_id, actor_id=actor_id, expected_scope=SHARED_SCOPE, actor=actor)
    work = read_committed_work(review_id, actor=actor, scope=SHARED_SCOPE)
    binding = work["document"]["payload"].get("shared_report_review")
    if (not isinstance(binding, dict) or binding.get("schema") != "shared-report-review/v1"
            or binding.get("actor_id") != actor_id or binding.get("job_id") != job_id
            or binding.get("artifact_hash") != report["artifact_outcome"]["artifact_hash"]
            or binding.get("decision") not in {"use_for_next_step", "request_changes", "reject"}):
        raise PermissionError("REPORT_REVIEW_BINDING_MISMATCH")
    digest = work["artifact"]["sha256"]
    evaluation_id = hashlib.sha256(("shared-report-review:" + review_id + ":" + digest).encode()).hexdigest()
    evaluation = get_evaluation_record(evaluation_id)
    if evaluation is not None:
        metadata = json.loads(evaluation["metadata"])
        if (evaluation.get("evidence_ref") != "saved_work:" + review_id + ":" + digest
                or evaluation.get("metric_name") != "operator_disposition"
                or evaluation.get("metric_value") is not None
                or any(metadata.get(key) != value for key, value in binding.items())
                or metadata.get("scope") != SHARED_SCOPE):
            raise PermissionError("REPORT_REVIEW_EVALUATION_MISMATCH")
    return {**binding, "review_id": review_id, "review_artifact_hash": digest,
            "evaluation_id": evaluation_id, "evaluation": evaluation,
            "state": "recorded" if evaluation is not None else "pending_recovery"}


def _read_research_reference(reference, *, actor, scope, connection=None):
    if reference is None:
        return None
    if actor is None:
        raise PermissionError("RESEARCH_REFERENCE_ACTOR_REQUIRED")
    from agent_research.reference_work import read_reference_work
    target = scope if scope == SHARED_SCOPE else _media_scope(scope)
    result = read_reference_work(reference["artifact_id"], actor=actor, scope=target,
        expected_sha256=reference["sha256"], require_current=True, connection=connection)
    if result["reference"] != reference:
        raise PermissionError("RESEARCH_REFERENCE_BINDING_MISMATCH")
    return result


def _reference_context(reference, *, actor, scope):
    item = _read_research_reference(reference, actor=actor, scope=scope)
    if item is None:
        return None
    body = item['document']['payload']['research_reference']
    return {'asset_id': body['asset_id'], 'parameters': body['current'],
            'classification': 'USER_SELECTED_REFERENCE_PARAMETERS',
            'rights': 'UNKNOWN', 'fact_verified': False,
            'reference': item['reference']}


def _hypothesis_work_id(job_id, actor_id, scope):
    return 'WORK-' + hashlib.sha256(_json({'kind':'research_hypothesis_review/v1',
        'job_id':job_id,'actor_id':actor_id,'scope':scope}).encode()).hexdigest()[:24]


def _hypothesis_versions(report, *, actor, actor_id, scope, connection=None):
    from contextlib import nullcontext
    from . import saved_work
    target = scope if scope == SHARED_SCOPE else _media_scope(scope)
    reader = get_repository().connection(read_only=True, wal=False) if connection is None else nullcontext(connection)
    with reader as con:
        context = saved_work.authorize_saved_work(actor, target, action='read', connection=con)
        if (context.get('principal_ref') or f"actor:{context.get('actor_id')}") != actor_id:
            raise PermissionError('HYPOTHESIS_REVIEW_ACTOR_MISMATCH')
        if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(saved_work._TABLE,)).fetchone() is None:
            return []
        return saved_work._versions(con, _hypothesis_work_id(report['job_id'],actor_id,scope), context, actor)


def _hypothesis_analysis(report, *, actor, reviews=None, connection=None):
    from agent_research.source_bound import analyze_source_records
    base = report.get('historical_research_analysis') or report.get('research_analysis') or report.get('business_analysis') or {}
    if base.get('schema') != 'source_bound_research.v1':
        raise ValueError('HYPOTHESIS_REVIEW_RESEARCH_UNAVAILABLE')
    resolved = _resolve_source_records(report, actor=actor, connection=connection)
    if reviews is None:
        reviews = _inherited_hypothesis_reviews(report,actor=actor,actor_id=base['actor_id'],scope=base['scope'],connection=connection)
    analysis = analyze_source_records(base['goal'], resolved['records'], actor_id=base['actor_id'],
        scope=base['scope'], dimension=base['dimension'], regions=base['regions'], languages=base['languages'],
        hypothesis_reviews=reviews, decision_brief=base.get('decision_brief', {}).get('input'))
    digest = hashlib.sha256(_json(resolved['records']).encode()).hexdigest()
    return analysis, digest


def _with_hypothesis_reviews(report, *, actor, actor_id, scope, connection=None):
    """Project current manual challenges without mutating the original report.

    Raw source statements remain historical evidence, not verified conclusions.
    Challenge/rejection removes support eligibility; reinstatement is pending.
    """
    if actor is None:
        return report
    versions = _hypothesis_versions(report, actor=actor, actor_id=actor_id, scope=scope, connection=connection)
    inherited = _inherited_hypothesis_reviews(report,actor=actor,actor_id=actor_id,scope=scope,connection=connection)
    if not versions:
        if not inherited:
            return report
        analysis,_ = _hypothesis_analysis(report,actor=actor,reviews=inherited,connection=connection)
        return _project_hypothesis_analysis(report,analysis,report['hypothesis_review_origin']['reference'],scope)
    prior_reviews = inherited
    for index,item in enumerate(versions):
        entry = item['document']['payload'].get('research_hypothesis_review', {})
        reviews = entry.get('reviews')
        command = entry.get('command', {})
        expected_id = 'review_'+hashlib.sha256(_json({'job_id':report['job_id'],'actor_id':actor_id,
            'scope':scope,'request_id':item['document']['request_id']}).encode()).hexdigest()[:24]
        expected_parent = versions[index-1]['artifact']['sha256'] if index else None
        if (not isinstance(reviews,list) or len(reviews) != len(inherited)+index+1 or reviews[:-1] != prior_reviews
                or reviews[-1].get('review_id') != expected_id
                or command.get('expected_revision') != expected_parent
                or {k:v for k,v in reviews[-1].items() if k != 'review_id'} !=
                   {k:v for k,v in command.items() if k != 'expected_revision'}):
            raise PermissionError('HYPOTHESIS_REVIEW_HISTORY_INVALID')
        prior_reviews = reviews
    latest = versions[-1]
    body = latest['document']['payload'].get('research_hypothesis_review', {})
    if (body.get('schema') != 'research_hypothesis_review/v1' or body.get('job_id') != report['job_id']
            or body.get('actor_id') != actor_id or body.get('scope') != scope
            or body.get('report_hash') != report['artifact_outcome']['artifact_hash']):
        raise PermissionError('HYPOTHESIS_REVIEW_BINDING_MISMATCH')
    analysis, source_digest = _hypothesis_analysis(report, actor=actor, reviews=body.get('reviews'), connection=connection)
    if body.get('source_digest') != source_digest or body.get('analysis') != analysis:
        raise PermissionError('HYPOTHESIS_REVIEW_SOURCE_CHANGED')
    reference = {'artifact_id':latest['artifact']['artifact_id'], 'sha256':latest['artifact']['sha256'],
                 'version':latest['document']['version'], 'work_id':latest['document']['work_id']}
    return _project_hypothesis_analysis(report,analysis,reference,scope)


def _project_hypothesis_analysis(report,analysis,reference,scope):
    effective = {**analysis, 'ranked_findings':analysis['effective_findings'],
                 'hypotheses':analysis['effective_hypotheses'],
                 'summary':'Current source-bound support after operator review; challenged and rejected hypotheses are excluded.'}
    pending = any(item['review_status'] in {'challenged','rejected'} for item in analysis['hypotheses'])
    view = {**report, 'hypothesis_review':reference, 'reviewed_research_analysis':analysis,
            'historical_research_analysis':report.get('research_analysis') or report.get('business_analysis'),
            'research_analysis':effective, 'hypothesis_review_state':'requires_reassessment' if pending else 'reviewed_pending_verification'}
    if scope == SHARED_SCOPE:
        view['business_analysis'] = effective
    elif pending and report.get('business_analysis'):
        view['historical_business_analysis'] = report['business_analysis']
        view['business_analysis'] = {'state':'requires_reassessment','reason':'SOURCE_BOUND_COUNTEREVIDENCE_REVIEW',
                                    'fact_verified':False,'review_reference':reference}
    return view


def get_hypothesis_review(job_id, *, actor, actor_id, expected_scope):
    report = get_source_brief_job(job_id, actor=actor, actor_id=actor_id, expected_scope=expected_scope)
    analysis = report.get('reviewed_research_analysis')
    if analysis is None:
        analysis, _ = _hypothesis_analysis(report, actor=actor)
    versions = _hypothesis_versions(report,actor=actor,actor_id=actor_id,scope=expected_scope)
    reference = ({'artifact_id':versions[-1]['artifact']['artifact_id'],'sha256':versions[-1]['artifact']['sha256'],
                  'version':versions[-1]['document']['version'],'work_id':versions[-1]['document']['work_id']} if versions else None)
    return {'job_id':job_id, 'report_hash':report['artifact_outcome']['artifact_hash'],
            'reference':reference, 'expected_revision':reference['sha256'] if reference else None,
            'analysis':analysis, 'inherited_reference':report.get('hypothesis_review_origin'), 'fact_verified':False, 'review_basis':'OPERATOR_SOURCE_BOUND_OPINION'}


def write_hypothesis_review(job_id, *, actor, actor_id, expected_scope, request_id,
                            expected_revision, hypothesis_id, disposition, rationale, evidence_refs):
    """Append an explicitly requested manual challenge under SavedWork CAS.

    Counterevidence must already be among the report's freshly admitted sources.
    New counterevidence is selected into a new report, never silently rebound.
    """
    from . import saved_work
    target = expected_scope if expected_scope == SHARED_SCOPE else _media_scope(expected_scope)
    saved_work.authorize_saved_work(actor, target, action='write')
    report = get_source_brief_job(job_id, actor=actor, actor_id=actor_id, expected_scope=expected_scope)
    versions = _hypothesis_versions(report, actor=actor, actor_id=actor_id, scope=expected_scope)
    latest = versions[-1] if versions else None
    command = {'hypothesis_id':hypothesis_id, 'disposition':disposition, 'rationale':rationale,
               'evidence_refs':evidence_refs, 'expected_revision':expected_revision}
    for item in versions:
        if item['document']['request_id'] == request_id:
            if item['document']['payload'].get('research_hypothesis_review',{}).get('command') != command:
                raise ValueError('HYPOTHESIS_REVIEW_SUBMISSION_CONFLICT')
            return {**get_hypothesis_review(job_id,actor=actor,actor_id=actor_id,expected_scope=expected_scope),'replayed':True}
    if expected_revision != (latest['artifact']['sha256'] if latest else None):
        raise RuntimeError('HYPOTHESIS_REVIEW_REVISION_CONFLICT')
    reviews = (list(latest['document']['payload']['research_hypothesis_review']['reviews']) if latest else
               _inherited_hypothesis_reviews(report,actor=actor,actor_id=actor_id,scope=expected_scope))
    review = {'review_id':'review_'+hashlib.sha256(_json({'job_id':job_id,'actor_id':actor_id,
        'scope':expected_scope,'request_id':request_id}).encode()).hexdigest()[:24],
        'hypothesis_id':hypothesis_id,'disposition':disposition,'rationale':rationale,'evidence_refs':evidence_refs}
    reviews.append(review)
    analysis, source_digest = _hypothesis_analysis(report, actor=actor, reviews=reviews)
    body = {'schema':'research_hypothesis_review/v1','job_id':job_id,'actor_id':actor_id,
            'scope':expected_scope,'report_hash':report['artifact_outcome']['artifact_hash'],
            'source_digest':source_digest,'reviews':reviews,'analysis':analysis,'command':command,
            'fact_verified':False,'review_basis':'OPERATOR_SOURCE_BOUND_OPINION'}
    def current(con, _record, _document):
        saved_work.authorize_saved_work(actor,target,action='write',connection=con)
        # Read the immutable report directly: the newly staged review is not yet
        # a committed public artifact and must not be read through projection.
        raw = _read_report(job_id,connection=con)
        if raw is None or raw['artifact_hash'] != body['report_hash']:
            raise PermissionError('HYPOTHESIS_REVIEW_REPORT_CHANGED')
        _verify_report(raw,job_id=job_id,actor_id=actor_id,expected_scope=expected_scope,actor=actor,connection=con)
        _inherited_hypothesis_reviews(report,actor=actor,actor_id=actor_id,scope=expected_scope,connection=con)
        observed, digest = _hypothesis_analysis(report,actor=actor,reviews=reviews,connection=con)
        if observed != analysis or digest != source_digest:
            raise PermissionError('HYPOTHESIS_REVIEW_SOURCE_CHANGED')
        saved_work.authorize_saved_work(actor,target,action='write',connection=con)
    try:
        saved_work.save_work(title='Research hypothesis review',markdown='Source-bound operator review; no fact verification.\n\n'+_json(review),
        kind='research',payload={'research_hypothesis_review':body},citations=[],request_id=request_id,
        actor=actor,scope=target,work_id=_hypothesis_work_id(job_id,actor_id,expected_scope),
        previous_artifact_id=latest['artifact']['artifact_id'] if latest else None,
        expected_draft_digest=latest['document']['draft_digest'] if latest else None,before_commit=current)
    except saved_work.SavedWorkError as exc:
        if str(exc) in {'WORK_REVISION_CONFLICT','WORK_DRAFT_REVISION_CONFLICT'}:
            raise RuntimeError('HYPOTHESIS_REVIEW_REVISION_CONFLICT') from exc
        raise
    return {**get_hypothesis_review(job_id,actor=actor,actor_id=actor_id,expected_scope=expected_scope),'replayed':False}


def _inherited_hypothesis_reviews(report,*,actor,actor_id,scope,connection=None):
    origin = report.get('hypothesis_review_origin')
    if origin is None:
        return []
    if (not isinstance(origin,dict) or set(origin) != {'parent_job_id','reference'}
            or origin['parent_job_id'] == report['job_id']):
        raise PermissionError('HYPOTHESIS_REVIEW_PARENT_INVALID')
    parent = get_source_brief_job(origin['parent_job_id'],actor=actor,actor_id=actor_id,
                                 expected_scope=scope,connection=connection)
    if parent.get('hypothesis_review') != origin['reference']:
        raise PermissionError('HYPOTHESIS_REVIEW_PARENT_CHANGED')
    versions = _hypothesis_versions(parent,actor=actor,actor_id=actor_id,scope=scope,connection=connection)
    if versions:
        return list(versions[-1]['document']['payload']['research_hypothesis_review']['reviews'])
    return _inherited_hypothesis_reviews(parent,actor=actor,actor_id=actor_id,scope=scope,connection=connection)


DOMAIN_REPORT_ADOPTION_KEY = 'domain_report_adoption'


def _domain_report_adoption_material(job_id, *, actor, connection=None):
    """Reopen all original sources in their own scopes, including undisplayed rows."""
    from .saved_work import authorize_saved_work
    from lumenis.system.security.permission import LocalWorkspacePrincipal
    if type(actor) is not LocalWorkspacePrincipal:
        from lumenis.auth.service import get_current_user
        from flask import has_request_context
        if not has_request_context() or not isinstance(actor, dict) or not actor.get('token'):
            raise PermissionError('SOURCE_BRIEF_ADOPTION_SERVER_SESSION_REQUIRED')
        current = get_current_user(read_only=True, connection=connection)
        if current is None or current.get('id') != actor.get('id') or current.get('token') != actor.get('token'):
            raise PermissionError('SOURCE_BRIEF_ADOPTION_SESSION_REVOKED')
    context = authorize_saved_work(actor, SHARED_SCOPE, action='read', connection=connection)
    actor_id = context.get('principal_ref') or f"actor:{context['actor_id']}"
    report = get_source_brief_job(job_id, actor=actor, actor_id=actor_id, connection=connection)
    scope = report['source_brief']['scope']
    if scope == SHARED_SCOPE:
        raise ValueError('SOURCE_BRIEF_DOMAIN_REPORT_REQUIRED')
    material = resolve_report_sources(job_id, actor=actor, actor_id=actor_id,
                                      expected_scope=scope, connection=connection)
    records = material['records']
    if not records or report.get('job_state') != 'completed':
        raise ValueError('SOURCE_BRIEF_ADOPTION_SOURCES_REQUIRED')
    # The digest covers every owner-resolved row, original content hash, version,
    # rights, evidence reference and original scope. A display cap is not a guard cap.
    binding = {'schema': 'domain-report-adoption/v1', 'job_id': job_id,
        'actor_id': actor_id, 'source_scope': scope, 'target_scope': SHARED_SCOPE,
        'report_hash': report['artifact_outcome']['artifact_hash'],
        'hypothesis_review': report.get('hypothesis_review'),
        'source_count': len(records), 'sources_sha256': hashlib.sha256(_json(records).encode()).hexdigest(),
        'authority': 'SOURCE_REFERENCE_ONLY', 'semantic_verification': 'NOT_PERFORMED'}
    return binding, report, records


def validate_domain_report_adoption(binding, *, actor, connection=None):
    if not isinstance(binding, dict) or binding.get('schema') != 'domain-report-adoption/v1':
        raise PermissionError('SOURCE_BRIEF_ADOPTION_BINDING_INVALID')
    expected, report, records = _domain_report_adoption_material(binding.get('job_id'), actor=actor,
                                                               connection=connection)
    if binding != expected:
        raise PermissionError('SOURCE_BRIEF_ADOPTION_SOURCE_CHANGED')
    return report


def adopt_domain_report(*, job_id, request_id, actor, target_scope, mode='prepare', title=None):
    """Explicit domain report -> Shared SavedWork, using the existing export gate."""
    from . import saved_work
    from lumenis.system.security import permission
    if (target_scope != SHARED_SCOPE or not isinstance(mode, str) or mode not in {'prepare', 'save'}
            or not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,128}', request_id)):
        raise ValueError('SOURCE_BRIEF_ADOPTION_REQUEST_INVALID')
    saved_work.authorize_saved_work(actor, target_scope, action='write')
    binding, report, records = _domain_report_adoption_material(job_id, actor=actor)
    if title is None:
        source_scope = report['source_brief']['scope']
        focus = source_scope.get('entity_label')
        domain = 'CTH' if source_scope.get('product_id') == 'CTH' else 'BMP'
        title = f'{focus} · 来源简报' if isinstance(focus, str) and focus.strip() else f'{domain} 来源简报'
    if not isinstance(title, str) or not title.strip() or len(title) > 300:
        raise ValueError('WORK_INPUT_INVALID')
    citations = []
    for record in records[:8]:
        text = record['content_excerpt']
        if not text:
            raise PermissionError('SOURCE_BRIEF_ADOPTION_SOURCE_EMPTY')
        ref = record.get('content_evidence_ref', '')
        if not re.fullmatch(r'app_evidence_records:[1-9][0-9]*', ref):
            raise PermissionError('SOURCE_BRIEF_ADOPTION_SOURCE_UNAVAILABLE')
        citations.append({'evidence_id': int(ref.split(':')[1]), 'start': 0, 'end': len(text),
                          'quote': text, 'source_scope': record['source_scope']})
    args = {'title': title, 'markdown': report['source_brief']['markdown'],
        'kind': 'report', 'payload': {DOMAIN_REPORT_ADOPTION_KEY: binding,
            'source_report': report, 'displayed_citations': len(citations),
            'undisplayed_source_count': len(records) - len(citations)},
        'citations': citations, 'request_id': request_id, 'actor': actor, 'scope': target_scope,
        'work_id': None, 'previous_artifact_id': None}
    resource = saved_work.work_write_resource(**args)
    if mode == 'prepare':
        return {'state': 'requires_explicit_export_approval', 'resource': resource,
                'operation': permission.OperationType.DATA_EXPORT.value, 'binding': binding,
                'displayed_citations': len(citations), 'guarded_source_count': len(records),
                'title': title}
    gate = permission.get_permission_gate()
    def guard(con, _record, _document):
        saved_work.authorize_saved_work(actor, target_scope, action='write', connection=con)
        validate_domain_report_adoption(binding, actor=actor, connection=con)
        if not gate.get_valid_approval_token(permission.OperationType.DATA_EXPORT.value, resource=resource, exact=True):
            raise PermissionError('SOURCE_BRIEF_ADOPTION_EXACT_APPROVAL_REQUIRED')
    guard(None, None, None)
    return saved_work.save_work(**args, before_commit=guard)
