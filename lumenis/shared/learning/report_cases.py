"""Scoped report learning material over the existing signed Evidence owner.

Cases reference original artifacts; they are neither model training nor accepted
answers. Only the authorized Reporting write path creates them; reads never do.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3

from lumenis.shared.database import get_repository
from lumenis.shared.evidence import store

VERSION = "report-learning-case:v1"
FEATURE = "REPORT_LEARNING_CASE"


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _material(verified, review):
    from lumenis.shared.reporting import operator_review as owner
    from lumenis.shared.reporting.media_brief import _read_row
    from lumenis.shared.reporting.source_brief_job import _media_scope

    report = owner._verified_report(review["job_id"], review["actor_id"], review["scope"])
    if verified is not None and verified["row"]["artifact_hash"] != report["row"]["artifact_hash"]:
        raise RuntimeError("REPORT_LEARNING_ARTIFACT_CHANGED")
    signed = owner._verify_record(
        _read_row(review["evidence_ref"]), job_id=review["job_id"],
        artifact_hash=report["row"]["artifact_hash"], actor_id=review["actor_id"], scope=review["scope"],
    )
    if signed is None:
        raise PermissionError("REPORT_LEARNING_REVIEW_SCOPE_DENIED")
    if any(signed[key] != review[key] for key in ("review_id", "artifact_hash", "decision", "notes")):
        raise RuntimeError("REPORT_LEARNING_REVIEW_CHANGED")
    if owner._evaluation_state(signed) != "recorded":
        raise RuntimeError("REPORT_LEARNING_EVALUATION_PENDING")
    snapshot, scope = report["snapshot"], signed["scope"]
    identity = {"version": VERSION, "job_id": signed["job_id"],
                "artifact_hash": signed["artifact_hash"], "actor_id": signed["actor_id"],
                "scope": scope, "review_id": signed["review_id"]}
    case_id = hashlib.sha256(_json(identity).encode("utf-8")).hexdigest()
    inputs = {**identity, "case_id": case_id, "review_evidence_ref": signed["evidence_ref"],
              "report_ref": f"daily_reports:{signed['job_id']}:{signed['artifact_hash']}",
              **{key: signed["_inputs"][key] for key in ("permission_audit_ref", "operation_audit_ref")}}
    business = snapshot.get("business_analysis") or {}
    rejected_ref = business.get("rejected_candidate_evidence_ref")
    if rejected_ref is not None:
        rejected = _read_row(rejected_ref)
        rejected_inputs = json.loads(rejected["inputs_json"])
        if (not store.verify_evidence_record_integrity(rejected)
                or rejected.get("feature_id") != "REPORT_BUSINESS_ANALYSIS_REJECTED"
                or rejected_inputs.get("job_id") != signed["job_id"]
                or rejected_inputs.get("actor_ref") != signed["actor_id"]
                or rejected_inputs.get("scope") != _media_scope(scope)):
            raise RuntimeError("REPORT_LEARNING_REJECTED_BINDING_INVALID")
    outputs = {
        "lifecycle_stage": "RAW", "review_status": "HUMAN_PENDING", "training_eligible": False,
        "business_outcome": "NOT_OBSERVED", "material_state": "REFERENCED_NOT_TRAINED",
        "source_refs": [{"source_id": item["source_id"], "evidence_ref": item["scope_evidence_ref"]}
                        for item in report["source_brief"]["records"]],
        "business_question": snapshot.get("business_question"),
        "analysis_state": business.get("state", "not_requested"),
        "analysis_evidence_ref": business.get("evidence_ref"),
        "rejected_candidate_evidence_ref": rejected_ref,
        "revision": snapshot.get("revision"),
        "operator_feedback": {"decision": signed["decision"], "notes": signed["notes"],
                              "evidence_ref": signed["evidence_ref"]},
    }
    return inputs, outputs


def _rows(connection, inputs):
    return connection.execute(
        "SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=? AND test_name=? LIMIT 2",
        (FEATURE, inputs["job_id"], inputs["case_id"]),
    ).fetchall()


def _checked(row, inputs, outputs):
    from lumenis.shared.reporting.operator_review import _expected_scope_marker

    row = dict(row)
    scope = inputs["scope"]
    expected_inputs = {**inputs, "_lumenis_scope": _expected_scope_marker(scope)}
    if (not store.verify_evidence_record_integrity(row)
            or row.get("source") != "shared_learning" or row.get("feature_id") != FEATURE
            or row.get("asset_id") != inputs["job_id"] or row.get("test_name") != inputs["case_id"]
            or row.get("product_id") != scope["product_id"] or row.get("domain_id") != scope["domain_id"]
            or row.get("status") != "derived" or row.get("result") != "RECORDED"
            or json.loads(row["inputs_json"]) != expected_inputs or json.loads(row["outputs_json"]) != outputs):
        raise RuntimeError("REPORT_LEARNING_CASE_BINDING_INVALID")
    return {"state": "recorded", "case_id": inputs["case_id"],
            "evidence_ref": f"app_evidence_records:{row['id']}",
            "lifecycle_stage": "RAW", "review_status": "HUMAN_PENDING", "training_eligible": False}


def record_report_case(verified, review):
    """Called only after Reporting rechecks authorization for this write fence."""
    with get_repository().transaction(timeout=10) as connection:
        connection.execute("BEGIN IMMEDIATE")
        inputs, outputs = _material(verified, review)
        rows = _rows(connection, inputs)
        if len(rows) > 1:
            raise RuntimeError("REPORT_LEARNING_CASE_DUPLICATE")
        if rows:
            return _checked(rows[0], inputs, outputs)
        scope = inputs["scope"]
        record_id = store.record_evidence(
            connection=connection, source="shared_learning", project="LUMENIS", product=scope["product_id"],
            feature_id=FEATURE, asset_id=inputs["job_id"], test_name=inputs["case_id"], version=VERSION,
            capture_mode="report_review", result="RECORDED", status="derived", inputs=inputs, outputs=outputs,
            domain_id=scope["domain_id"], subject_id=scope.get("subject_id"),
            brand_focus_id=scope.get("brand_focus_id"), global_scope=scope["global"],
            notes="Derivative learning references; feedback is not correctness, training or observed outcome.",
        )
        if type(record_id) is not int or record_id < 1:
            raise RuntimeError("REPORT_LEARNING_CASE_WRITE_FAILED")
        rows = _rows(connection, inputs)
        if len(rows) != 1:
            raise RuntimeError("REPORT_LEARNING_CASE_REOPEN_FAILED")
        return _checked(rows[0], inputs, outputs)


def get_report_case(review):
    """Read through exact report/review owners; never repair during a read."""
    try:
        inputs, outputs = _material(None, review)
        with get_repository().connection(read_only=True, wal=False) as connection:
            rows = _rows(connection, inputs)
        if not rows:
            return {"state": "not_recorded"}
        if len(rows) != 1:
            raise RuntimeError("REPORT_LEARNING_CASE_DUPLICATE")
        return _checked(rows[0], inputs, outputs)
    except PermissionError:
        raise
    except (OSError, sqlite3.Error, ValueError, RuntimeError, LookupError):
        return {"state": "pending_recovery", "reason": "REPORT_LEARNING_CASE_READ_UNAVAILABLE"}
