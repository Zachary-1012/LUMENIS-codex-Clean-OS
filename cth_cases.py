"""CTH working Cases over canonical Reporting, Database and signed Evidence.

Creating a Case records an operator's question and selected source references.
It never infers an Insight, approves an Action, or claims an observed Outcome.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

import canonical_data
from lumenis.shared.database import get_repository
from lumenis.shared.database.cth_cases import TABLE
from lumenis.shared.evidence import store
from lumenis.shared.reporting.operator_review import _expected_scope_marker
from lumenis.shared.reporting.source_brief_job import _read_report, _verify_report

VERSION = "cth-case:v1"
FEATURE = "CTH_CASE_CREATED"


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _scope(scope):
    if (not isinstance(scope, dict) or scope.get("product_id") != "CTH"
            or scope.get("domain_id") != "cth" or scope.get("global") is not False
            or not isinstance(scope.get("subject_id"), str) or not scope["subject_id"]
            or scope.get("brand_focus_id") is not None):
        raise PermissionError("CTH_CASE_FOCUSED_SUBJECT_REQUIRED")


def _sources(connection, refs, scope):
    if not isinstance(refs, list) or not 1 <= len(refs) <= 8:
        raise RuntimeError("CTH_CASE_SOURCE_REFS_INVALID")
    canonical_data.validate_source_ids([ref["source_id"] for ref in refs], limit=8)
    for ref in refs:
        record = canonical_data.CanonicalRecord(
            product_id="CTH", domain_id="cth", subject_id=scope["subject_id"],
            scope_status="VERIFIED", scope_evidence_ref=str(ref["scope_evidence_ref"]),
            source_id=ref["source_id"],
        )
        try:
            canonical_data._validate_canonical_scope(connection, record)
        except ValueError as exc:
            raise PermissionError("CTH_CASE_SOURCE_LINEAGE_INVALID") from exc


def _subject(connection, scope):
    # Registry's canonical availability rule is configured/non-archived.
    entry = connection.execute(
        "SELECT 1 FROM lumenis_subject_registry WHERE subject_id=? "
        "AND domain_id='CTH' AND subject_type='company' AND status != 'archived'",
        (scope["subject_id"],),
    ).fetchone()
    if entry is None:
        raise PermissionError("CTH_CASE_SUBJECT_NOT_ACTIVE")


def _authorized(authorize):
    audits = authorize()
    if (not isinstance(audits, dict) or set(audits) != {"permission_audit_ref", "operation_audit_ref"}
            or any(not isinstance(v, str) or not v for v in audits.values())):
        raise PermissionError("CTH_CASE_WRITE_NOT_AUTHORIZED")
    return audits


def _checked(connection, row, *, actor_ref, expected_scope):
    row = dict(row)
    signed = connection.execute("SELECT * FROM app_evidence_records WHERE id=?",
                                (row["creation_evidence_ref"],)).fetchone()
    if signed is None or not store.verify_evidence_record_integrity(dict(signed)):
        raise RuntimeError("CTH_CASE_SIGNATURE_INVALID")
    signed = dict(signed)
    inputs = json.loads(signed["inputs_json"])
    scope = inputs.get("scope")
    _scope(scope)
    if inputs.get("actor_ref") != actor_ref or scope != expected_scope:
        raise PermissionError("CTH_CASE_CONTEXT_MISMATCH")
    _subject(connection, scope)
    if (signed.get("feature_id") != FEATURE or signed.get("source") != "cth_case"
            or signed.get("asset_id") != row["case_id"] or signed.get("version") != VERSION
            or signed.get("product_id") != "CTH" or signed.get("domain_id") != "cth"
            or signed.get("status") != "derived" or signed.get("result") != "RECORDED"
            or inputs.get("_lumenis_scope") != _expected_scope_marker(scope)
            or any(inputs.get(key) != row[key] for key in ("case_id", "actor_ref", "submission_id", "title", "question", "created_at"))
            or scope["subject_id"] != row["subject_id"]
            or _json(inputs.get("source_refs")) != row["source_refs_json"]
            or row["state"] != "OPEN"
            or json.loads(signed["outputs_json"]) != {"state": "OPEN", "analysis_state": "NOT_REQUESTED", "business_outcome": "NOT_OBSERVED"}):
        raise RuntimeError("CTH_CASE_BINDING_INVALID")
    _sources(connection, inputs["source_refs"], scope)
    return {
        "case_id": row["case_id"], "title": row["title"], "question": row["question"],
        "state": "OPEN", "scope": scope, "created_at": row["created_at"],
        "source_refs": inputs["source_refs"], "source_job_id": inputs["source_job_id"],
        "source_report_hash": inputs["source_report_hash"],
        "creation_evidence_ref": f"app_evidence_records:{row['creation_evidence_ref']}",
        "analysis_state": "NOT_REQUESTED", "business_outcome": "NOT_OBSERVED",
        "timeline": [{"stage": "CASE", "state": "recorded", "occurred_at": row["created_at"]}],
    }


def create_cth_case(*, actor_ref, expected_scope, submission_id, title, question,
                    source_job_id, source_ids, authorize):
    """One exact internal Case write, atomically with its signed creation trace."""
    _scope(expected_scope)
    if (not isinstance(actor_ref, str) or not actor_ref or not callable(authorize)
            or not isinstance(submission_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", submission_id)):
        raise ValueError("CTH_CASE_INPUT_INVALID")
    for text, limit in ((title, 240), (question, 1500)):
        if (not isinstance(text, str) or not 4 <= len(text) <= limit or text != text.strip()
                or any(ord(c) < 32 and c not in "\n\t" for c in text)):
            raise ValueError("CTH_CASE_INPUT_INVALID")
    source_ids = canonical_data.validate_source_ids(source_ids, limit=8)
    if source_ids is None or not isinstance(source_job_id, str) or not source_job_id:
        raise ValueError("CTH_CASE_INPUT_INVALID")
    report = _read_report(source_job_id)
    if report is None:
        raise LookupError("CTH_CASE_SOURCE_JOB_NOT_FOUND")
    verified = _verify_report(report, job_id=source_job_id, actor_id=actor_ref, expected_scope=expected_scope)
    available = {r["source_id"]: r for r in verified["source_brief"]["records"]}
    if any(source_id not in available for source_id in source_ids):
        raise PermissionError("CTH_CASE_SOURCE_NOT_IN_JOB")
    refs = [{"source_id": sid, "scope_evidence_ref": available[sid]["scope_evidence_ref"]} for sid in source_ids]
    case_id = "CASE-" + hashlib.sha256(_json([actor_ref, expected_scope["subject_id"], submission_id]).encode()).hexdigest()[:32]
    _authorized(authorize)
    with get_repository().transaction(timeout=10) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _subject(connection, expected_scope)
        _sources(connection, refs, expected_scope)
        existing = connection.execute(f"SELECT * FROM {TABLE} WHERE case_id=?", (case_id,)).fetchone()
        if existing is not None:
            _authorized(authorize)
            result = _checked(connection, existing, actor_ref=actor_ref, expected_scope=expected_scope)
            if any(result[k] != v for k, v in {"title": title, "question": question, "source_job_id": source_job_id, "source_refs": refs}.items()):
                raise ValueError("CTH_CASE_SUBMISSION_CONFLICT")
            return result
        current_report = connection.execute(
            "SELECT * FROM daily_reports WHERE report_id=? ORDER BY id DESC LIMIT 1", (source_job_id,),
        ).fetchone()
        if current_report is None:
            raise LookupError("CTH_CASE_SOURCE_JOB_NOT_FOUND")
        _verify_report(dict(current_report), job_id=source_job_id, actor_id=actor_ref, expected_scope=expected_scope)
        if current_report["artifact_hash"] != report["artifact_hash"]:
            raise RuntimeError("CTH_CASE_SOURCE_JOB_CHANGED")
        # Recheck after lock acquisition and all source/report validation,
        # immediately before the atomic Evidence + Case write.
        audits = _authorized(authorize)
        created_at = datetime.now(timezone.utc).isoformat()
        inputs = {"version": VERSION, "case_id": case_id, "actor_ref": actor_ref,
                  "scope": expected_scope, "submission_id": submission_id, "title": title,
                  "question": question, "source_job_id": source_job_id,
                  "source_report_hash": report["artifact_hash"], "source_refs": refs,
                  "created_at": created_at, **audits}
        ref = store.record_evidence(
            connection=connection, source="cth_case", project="LUMENIS", product="CTH",
            feature_id=FEATURE, asset_id=case_id, test_name=submission_id, version=VERSION,
            capture_mode="case_work", result="RECORDED", status="derived", inputs=inputs,
            outputs={"state": "OPEN", "analysis_state": "NOT_REQUESTED", "business_outcome": "NOT_OBSERVED"},
            domain_id="cth", subject_id=expected_scope["subject_id"], global_scope=False,
        )
        if type(ref) is not int or ref < 1:
            raise RuntimeError("CTH_CASE_EVIDENCE_WRITE_FAILED")
        connection.execute(
            f"INSERT INTO {TABLE}(case_id,actor_ref,subject_id,submission_id,title,question,source_refs_json,state,creation_evidence_ref,created_at) VALUES(?,?,?,?,?,?,?,'OPEN',?,?)",
            (case_id, actor_ref, expected_scope["subject_id"], submission_id, title, question, _json(refs), ref, created_at),
        )
        return _checked(connection, connection.execute(f"SELECT * FROM {TABLE} WHERE case_id=?", (case_id,)).fetchone(),
                        actor_ref=actor_ref, expected_scope=expected_scope)


def get_cth_case(case_id, *, actor_ref, expected_scope):
    _scope(expected_scope)
    with get_repository().connection(read_only=True, wal=False) as connection:
        row = connection.execute(f"SELECT * FROM {TABLE} WHERE case_id=?", (case_id,)).fetchone()
        if row is None:
            raise LookupError("CTH_CASE_NOT_FOUND")
        return _checked(connection, row, actor_ref=actor_ref, expected_scope=expected_scope)


def list_cth_cases(*, actor_ref, expected_scope, limit=25, before=None):
    """Read one principal's focused Cases, validating each signed source chain."""
    _scope(expected_scope)
    if not isinstance(actor_ref, str) or not actor_ref or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("CTH_CASE_LIST_INPUT_INVALID")
    if before is not None and (not isinstance(before, str) or not re.fullmatch(r"CASE-[0-9a-f]{32}", before)):
        raise ValueError("CTH_CASE_LIST_INPUT_INVALID")
    with get_repository().connection(read_only=True, wal=False) as connection:
        # Keep cursor, Case rows and their Evidence in one read snapshot.
        connection.execute("BEGIN")
        _subject(connection, expected_scope)
        params = [actor_ref, expected_scope["subject_id"]]
        query = f"SELECT * FROM {TABLE} WHERE actor_ref=? AND subject_id=?"
        if before is not None:
            cursor = connection.execute(query + " AND case_id=?", (*params, before)).fetchone()
            if cursor is None:
                # A missing cursor and another principal/Subject's cursor are indistinguishable.
                raise LookupError("CTH_CASE_CURSOR_NOT_FOUND")
            _checked(connection, cursor, actor_ref=actor_ref, expected_scope=expected_scope)
            query += " AND (created_at,case_id) < (?,?)"
            params.extend((cursor["created_at"], cursor["case_id"]))
        rows = connection.execute(
            query + " ORDER BY created_at DESC,case_id DESC LIMIT ?", (*params, limit + 1),
        ).fetchall()
        cases = [_checked(connection, row, actor_ref=actor_ref, expected_scope=expected_scope)
                 for row in rows[:limit]]
    return {"version": "cth-case-list:v1", "scope": expected_scope, "cases": cases,
            "next_cursor": cases[-1]["case_id"] if len(rows) > limit else None}
