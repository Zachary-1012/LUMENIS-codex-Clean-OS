"""Append-only, artifact-bound operator dispositions for Source Brief reports.

This records what an operator wants to do next. It does not record or infer a
business outcome, accept the report as market truth, or execute the requested
next step.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable

from lumenis.shared.database import get_repository
from lumenis.shared.evaluation.recorder import get_evaluation_record, record_evaluation
from lumenis.shared.evidence import store as evidence_store

_VERSION = "report-operator-review:v1"
_FEATURE = "REPORT_OPERATOR_REVIEW"
_SOURCE = "shared_reporting:operator_review"
_DECISIONS = {"use_for_next_step", "request_changes", "reject"}
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_AUDIT_MAX = 256


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _strict_object(value: Any) -> dict[str, Any]:
    def unique(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = item
        return result

    try:
        parsed = json.loads(value, object_pairs_hook=unique,
                            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("REPORT_OPERATOR_REVIEW_JSON_INVALID") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("REPORT_OPERATOR_REVIEW_JSON_INVALID")
    return parsed


def _authorize(authorize: Callable[[], dict[str, Any]], actor_id: str,
               expected_scope: dict[str, Any]) -> dict[str, str]:
    if not callable(authorize):
        raise PermissionError("REPORT_OPERATOR_REVIEW_AUTHORIZATION_REQUIRED")
    result = authorize()
    if (not isinstance(result, dict) or result.get("actor_id") != actor_id
            or result.get("scope") != expected_scope):
        raise PermissionError("REPORT_OPERATOR_REVIEW_AUTHORIZATION_MISMATCH")
    refs = {}
    for name in ("permission_audit_ref", "operation_audit_ref"):
        value = result.get(name)
        if (not isinstance(value, str) or not value.strip() or len(value) > _AUDIT_MAX
                or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value)):
            raise PermissionError("REPORT_OPERATOR_REVIEW_AUDIT_REQUIRED")
        refs[name] = value
    return refs


def _verified_report(job_id: str, actor_id: str, expected_scope: dict[str, Any]) -> dict[str, Any]:
    from .source_brief_job import _read_report, _verify_report

    row = _read_report(job_id)
    if row is None:
        raise LookupError("SOURCE_BRIEF_JOB_NOT_FOUND")
    return _verify_report(row, job_id=job_id, actor_id=actor_id, expected_scope=expected_scope)


def _identity(job_id: str, artifact_hash: str, actor_id: str, submission_id: str) -> tuple[str, str]:
    material = _json({"version": _VERSION, "job_id": job_id, "artifact_hash": artifact_hash,
                      "actor_id": actor_id, "submission_id": submission_id})
    review_id = hashlib.sha256(material.encode("utf-8")).hexdigest()
    evaluation_id = hashlib.sha256(f"{_VERSION}:evaluation:{review_id}".encode("utf-8")).hexdigest()
    return review_id, evaluation_id


def _evaluation_metadata(inputs: dict[str, Any], outputs: dict[str, Any], evidence_ref: str) -> dict[str, Any]:
    return {
        "version": _VERSION, "review_id": inputs["review_id"], "job_id": inputs["job_id"],
        "artifact_hash": inputs["artifact_hash"], "actor_id": inputs["actor_id"],
        "scope": inputs["scope"], "submission_id": inputs["submission_id"],
        "decision": outputs["decision"], "permission_audit_ref": inputs["permission_audit_ref"],
        "operation_audit_ref": inputs["operation_audit_ref"],
        "business_outcome": "NOT_OBSERVED", "review_evidence_ref": evidence_ref,
    }


def _validate_input(job_id: str, actor_id: str, expected_scope: dict[str, Any],
                    submission_id: str, decision: str, notes: str) -> str:
    if not isinstance(job_id, str) or not job_id.strip():
        raise ValueError("SOURCE_BRIEF_JOB_ID_REQUIRED")
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise ValueError("REPORT_OPERATOR_REVIEW_ACTOR_REQUIRED")
    if not isinstance(expected_scope, dict) or not expected_scope:
        raise ValueError("REPORT_OPERATOR_REVIEW_SCOPE_REQUIRED")
    if not isinstance(submission_id, str) or not _UUID.fullmatch(submission_id):
        raise ValueError("REPORT_OPERATOR_REVIEW_SUBMISSION_ID_INVALID")
    if not isinstance(decision, str) or decision not in _DECISIONS:
        raise ValueError("REPORT_OPERATOR_REVIEW_DECISION_INVALID")
    if not isinstance(notes, str):
        raise ValueError("REPORT_OPERATOR_REVIEW_NOTES_INVALID")
    notes = notes.strip()
    if (not notes or len(notes) > 2000
            or any((ord(char) < 32 and char not in "\n\t") or 127 <= ord(char) <= 159 for char in notes)):
        raise ValueError("REPORT_OPERATOR_REVIEW_NOTES_INVALID")
    return notes


def _expected_scope_marker(scope: dict[str, Any]) -> dict[str, Any]:
    return evidence_store._normalize_record_evidence_scope(
        product=scope.get("product_id"), domain_id=scope.get("domain_id"),
        subject_id=scope.get("subject_id"), brand_focus_id=scope.get("brand_focus_id"),
        global_scope=scope.get("global"),
    )


def _verify_record(row: dict[str, Any], *, job_id: str, artifact_hash: str,
                   actor_id: str, scope: dict[str, Any]) -> dict[str, Any] | None:
    if not evidence_store.verify_evidence_record_integrity(row):
        raise RuntimeError("REPORT_OPERATOR_REVIEW_SIGNATURE_INVALID")
    inputs, outputs = _strict_object(row.get("inputs_json")), _strict_object(row.get("outputs_json"))
    if (inputs.get("job_id") != job_id or inputs.get("artifact_hash") != artifact_hash
            or inputs.get("actor_id") != actor_id or inputs.get("scope") != scope):
        return None
    submission_id = inputs.get("submission_id")
    if not isinstance(submission_id, str) or not _UUID.fullmatch(submission_id):
        raise RuntimeError("REPORT_OPERATOR_REVIEW_IDENTITY_INVALID")
    review_id, evaluation_id = _identity(job_id, artifact_hash, actor_id, submission_id)
    if (inputs.get("version") != _VERSION or inputs.get("review_id") != review_id
            or row.get("feature_id") != _FEATURE or row.get("source") != "shared_reporting"
            or row.get("asset_id") != job_id or row.get("test_name") != review_id
            or row.get("product_id") != scope.get("product_id")
            or row.get("domain_id") != scope.get("domain_id")
            or inputs.get("_lumenis_scope") != _expected_scope_marker(scope)
            or inputs.get("business_outcome") != "NOT_OBSERVED"):
        raise RuntimeError("REPORT_OPERATOR_REVIEW_BINDING_INVALID")
    if set(inputs) != {"version", "review_id", "job_id", "artifact_hash", "actor_id", "scope",
                      "submission_id", "permission_audit_ref", "operation_audit_ref",
                      "business_outcome", "_lumenis_scope"}:
        raise RuntimeError("REPORT_OPERATOR_REVIEW_BINDING_INVALID")
    for name in ("permission_audit_ref", "operation_audit_ref"):
        ref = inputs.get(name)
        if not isinstance(ref, str) or not ref.strip() or len(ref) > _AUDIT_MAX:
            raise RuntimeError("REPORT_OPERATOR_REVIEW_BINDING_INVALID")
    decision, notes = outputs.get("decision"), outputs.get("notes")
    if (set(outputs) != {"decision", "notes", "business_outcome"}
            or decision not in _DECISIONS or not isinstance(notes, str) or not notes.strip()
            or len(notes) > 2000 or outputs.get("business_outcome") != "NOT_OBSERVED"
            or row.get("result") != "RECORDED" or row.get("status") != "derived"
            or row.get("capture_mode") != "operator_submission"
            or row.get("metric_name") != "operator_report_disposition"):
        raise RuntimeError("REPORT_OPERATOR_REVIEW_CONTENT_INVALID")
    return {
        "review_id": review_id, "evaluation_id": evaluation_id,
        "evidence_ref": f"app_evidence_records:{row['id']}", "job_id": job_id,
        "artifact_hash": artifact_hash, "actor_id": actor_id, "scope": scope,
        "submission_id": submission_id, "decision": decision, "notes": notes,
        "business_outcome": "NOT_OBSERVED", "recorded_at": row.get("captured_at"),
        "_inputs": inputs,
    }


def _record_evaluation(review: dict[str, Any]) -> None:
    inputs = review["_inputs"]
    outputs = {"decision": review["decision"]}
    metadata = _evaluation_metadata(inputs, outputs, review["evidence_ref"])
    record_evaluation(
        dimension="report", metric_name="operator_report_disposition", metric_value=None,
        pass_threshold=1.0, warn_threshold=0.8, source=_SOURCE,
        evidence_ref=f"daily_reports:{review['job_id']}:{review['artifact_hash']}", metadata=metadata,
        evaluation_id=review["evaluation_id"],
    )
    if _evaluation_state(review) != "recorded":
        raise RuntimeError("REPORT_OPERATOR_REVIEW_EVALUATION_REOPEN_FAILED")


def _evaluation_state(review: dict[str, Any]) -> str:
    persisted = get_evaluation_record(review["evaluation_id"])
    if persisted is None:
        return "pending_recovery"
    metadata = _evaluation_metadata(review["_inputs"], {"decision": review["decision"]}, review["evidence_ref"])
    if (persisted.get("dimension") != "report"
            or persisted.get("metric_name") != "operator_report_disposition"
            or persisted.get("metric_value") is not None or persisted.get("status") != "unknown"
            or persisted.get("source") != _SOURCE
            or persisted.get("evidence_ref") != f"daily_reports:{review['job_id']}:{review['artifact_hash']}"
            or _strict_object(persisted.get("metadata")) != metadata):
        raise RuntimeError("REPORT_OPERATOR_REVIEW_EVALUATION_REOPEN_FAILED")
    return "recorded"


def _projection(review: dict[str, Any]) -> dict[str, Any]:
    return {**{key: value for key, value in review.items() if not key.startswith("_")},
            "evaluation_state": _evaluation_state(review)}


def write_operator_review(job_id: str, *, actor_id: str, expected_scope: dict[str, Any],
                          submission_id: str, decision: str, notes: str,
                          authorize: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Record one authorized disposition; identical submissions are safely replayable."""
    notes = _validate_input(job_id, actor_id, expected_scope, submission_id, decision, notes)
    audit_refs = _authorize(authorize, actor_id, expected_scope)
    verified = _verified_report(job_id, actor_id, expected_scope)
    artifact_hash = verified["row"]["artifact_hash"]
    review_id, evaluation_id = _identity(job_id, artifact_hash, actor_id, submission_id)
    inputs = {
        "version": _VERSION, "review_id": review_id, "job_id": job_id,
        "artifact_hash": artifact_hash, "actor_id": actor_id, "scope": expected_scope,
        "submission_id": submission_id, **audit_refs, "business_outcome": "NOT_OBSERVED",
    }
    outputs = {"decision": decision, "notes": notes, "business_outcome": "NOT_OBSERVED"}

    with get_repository().transaction(timeout=10) as conn:
        conn.execute("BEGIN IMMEDIATE")
        current = conn.execute(
            "SELECT * FROM daily_reports WHERE report_id=? ORDER BY id DESC LIMIT 1", (job_id,)
        ).fetchone()
        if current is None:
            raise LookupError("SOURCE_BRIEF_JOB_NOT_FOUND")
        from .source_brief_job import _verify_report
        latest = _verify_report(dict(current), job_id=job_id, actor_id=actor_id,
                                expected_scope=expected_scope)
        if latest["row"]["artifact_hash"] != artifact_hash:
            raise RuntimeError("REPORT_OPERATOR_REVIEW_ARTIFACT_CHANGED")
        audit_refs = _authorize(authorize, actor_id, expected_scope)
        inputs.update(audit_refs)
        existing_rows = conn.execute(
            "SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=? AND test_name=?",
            (_FEATURE, job_id, review_id),
        ).fetchall()
        if len(existing_rows) > 1:
            raise RuntimeError("REPORT_OPERATOR_REVIEW_DUPLICATE_EVIDENCE")
        if existing_rows:
            existing = _verify_record(dict(existing_rows[0]), job_id=job_id,
                                      artifact_hash=artifact_hash, actor_id=actor_id,
                                      scope=expected_scope)
            if existing is None:
                raise RuntimeError("REPORT_OPERATOR_REVIEW_BINDING_INVALID")
            if existing["decision"] != decision or existing["notes"] != notes:
                raise ValueError("REPORT_OPERATOR_REVIEW_SUBMISSION_CONFLICT")
            review = existing  # Preserve the original authorization audit references.
        else:
            scope = expected_scope
            evidence_id = evidence_store.record_evidence(
                connection=conn, source="shared_reporting", project="LUMENIS",
                product=scope["product_id"], feature_id=_FEATURE, asset_id=job_id,
                version=_VERSION, level="operator_feedback", test_name=review_id,
                capture_mode="operator_submission", result="RECORDED", status="derived",
                inputs=inputs, outputs=outputs, expected="Operator disposition recorded; business outcome not observed.",
                actual=decision, notes=notes, metric_name="operator_report_disposition",
                topic="report", domain_id=scope["domain_id"],
                subject_id=scope.get("subject_id"), brand_focus_id=scope.get("brand_focus_id"),
                global_scope=scope["global"],
            )
            if type(evidence_id) is not int or evidence_id < 1:
                raise RuntimeError("REPORT_OPERATOR_REVIEW_EVIDENCE_WRITE_FAILED")
            stored = conn.execute(
                "SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)
            ).fetchone()
            if stored is None:
                raise RuntimeError("REPORT_OPERATOR_REVIEW_EVIDENCE_REOPEN_FAILED")
            review = _verify_record(dict(stored), job_id=job_id, artifact_hash=artifact_hash,
                                    actor_id=actor_id, scope=expected_scope)
            if (review is None or review["decision"] != decision or review["notes"] != notes
                    or review["_inputs"]["permission_audit_ref"] != audit_refs["permission_audit_ref"]
                    or review["_inputs"]["operation_audit_ref"] != audit_refs["operation_audit_ref"]):
                raise RuntimeError("REPORT_OPERATOR_REVIEW_EVIDENCE_REOPEN_FAILED")

    _authorize(authorize, actor_id, expected_scope)
    _record_evaluation(review)
    return _projection(review)


def read_operator_reviews(verified: dict[str, Any]) -> dict[str, Any]:
    """Project only signed dispositions for the already verified report binding."""
    if not isinstance(verified, dict) or not isinstance(verified.get("row"), dict):
        raise ValueError("VERIFIED_SOURCE_BRIEF_REQUIRED")
    snapshot, row = verified.get("snapshot"), verified["row"]
    if not isinstance(snapshot, dict):
        raise ValueError("VERIFIED_SOURCE_BRIEF_REQUIRED")
    job_id, actor_id, scope = snapshot.get("job_id"), snapshot.get("actor_id"), snapshot.get("scope")
    if not isinstance(scope, dict) or not isinstance(actor_id, str) or not isinstance(job_id, str):
        raise RuntimeError("REPORT_OPERATOR_REVIEW_BINDING_INVALID")
    artifact_hash = row.get("artifact_hash")
    if not isinstance(artifact_hash, str) or len(artifact_hash) != 64:
        raise RuntimeError("REPORT_OPERATOR_REVIEW_BINDING_INVALID")
    conn = get_repository().connect(timeout=10, read_only=True, wal=False)
    try:
        rows = conn.execute(
            """SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=?
               AND json_extract(CASE WHEN json_valid(inputs_json) THEN inputs_json ELSE '{}' END, '$.actor_id')=?
               AND json_extract(CASE WHEN json_valid(inputs_json) THEN inputs_json ELSE '{}' END, '$.artifact_hash')=?
               AND json_extract(CASE WHEN json_valid(inputs_json) THEN inputs_json ELSE '{}' END, '$.scope.scope_key')=?
               ORDER BY id DESC LIMIT 51""",
            (_FEATURE, job_id, actor_id, artifact_hash, scope["scope_key"]),
        ).fetchall()
    finally:
        conn.close()
    records = []
    for raw in rows:
        review = _verify_record(dict(raw), job_id=job_id, artifact_hash=artifact_hash,
                                actor_id=actor_id, scope=scope)
        if review is not None:
            records.append(_projection(review))
            if len(records) > 50:
                break
    truncated = len(records) > 50
    records = records[:50]
    state = ("pending_recovery" if any(r["evaluation_state"] == "pending_recovery" for r in records)
             else "recorded") if records else "not_recorded"
    return {"state": state,
            "latest": records[0] if records else None, "records": records,
            "truncated": truncated}
