"""Isolated tests for signed Source Brief operator dispositions."""
import json
import sqlite3
import uuid

import pytest

from tests.test_source_brief_job import _request, job_db
import lumenis.shared.reporting.operator_review as reviews
import lumenis.shared.reporting.source_brief_job as jobs
from lumenis.shared.evaluation.recorder import get_evaluation_record


def _report(job_db):
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        return _request(conn)


def _authorize(actor_id, scope, suffix="first"):
    return lambda: {
        "actor_id": actor_id,
        "scope": scope,
        "permission_audit_ref": f"permission:{suffix}",
        "operation_audit_ref": f"operation:{suffix}",
    }


def _write(result, *, submission_id=None, decision="request_changes", notes="Revise the proposed content test.", authorize=None):
    return reviews.write_operator_review(
        result["job_id"], actor_id="workspace:local",
        expected_scope=result["source_brief"]["scope"],
        submission_id=submission_id or str(uuid.uuid4()), decision=decision, notes=notes,
        authorize=authorize or _authorize("workspace:local", result["source_brief"]["scope"]),
    )


def _verified(result):
    return jobs._verify_report(
        jobs._read_report(result["job_id"]), job_id=result["job_id"],
        actor_id="workspace:local", expected_scope=result["source_brief"]["scope"],
    )


def _counts(db_path, job_id):
    with sqlite3.connect(db_path) as conn:
        evidence = conn.execute(
            "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='REPORT_OPERATOR_REVIEW' AND asset_id=?",
            (job_id,),
        ).fetchone()[0]
        evaluations = conn.execute(
            "SELECT COUNT(*) FROM evaluation_records WHERE metric_name='operator_report_disposition' "
            "AND json_extract(metadata,'$.job_id')=?", (job_id,),
        ).fetchone()[0]
    return evidence, evaluations


@pytest.mark.parametrize("decision", ["use_for_next_step", "request_changes", "reject"])
def test_operator_dispositions_are_derived_and_do_not_assert_business_outcome(job_db, decision):
    result = _report(job_db)
    review = _write(result, decision=decision)

    assert review["decision"] == decision
    assert review["business_outcome"] == "NOT_OBSERVED"
    assert get_evaluation_record(review["evaluation_id"])["metric_value"] is None
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM app_evidence_records WHERE id=?",
                           (int(review["evidence_ref"].rsplit(":", 1)[1]),)).fetchone()
        inputs, outputs = json.loads(row["inputs_json"]), json.loads(row["outputs_json"])
        evaluation = get_evaluation_record(review["evaluation_id"])
    assert row["status"] == "derived"
    assert row["result"] == "RECORDED"
    assert inputs["business_outcome"] == outputs["business_outcome"] == "NOT_OBSERVED"
    assert evaluation["status"] == "unknown"
    assert evaluation["evidence_ref"] == f"daily_reports:{result['job_id']}:{review['artifact_hash']}"
    assert json.loads(evaluation["metadata"])["review_evidence_ref"] == review["evidence_ref"]
    reopened = reviews.read_operator_reviews(_verified(result))
    assert reopened["state"] == "recorded"
    assert reopened["latest"]["review_id"] == review["review_id"]
    assert reopened["latest"]["business_outcome"] == "NOT_OBSERVED"


def test_identical_submission_replays_once_and_changed_replay_conflicts(job_db):
    result = _report(job_db)
    submission_id = str(uuid.uuid4())
    first = _write(result, submission_id=submission_id)
    replay = _write(result, submission_id=submission_id,
                    authorize=_authorize("workspace:local", result["source_brief"]["scope"], "retry"))

    assert replay["evidence_ref"] == first["evidence_ref"]
    assert replay["evaluation_id"] == first["evaluation_id"]
    assert _counts(job_db, result["job_id"]) == (1, 1)
    with pytest.raises(ValueError, match="SUBMISSION_CONFLICT"):
        _write(result, submission_id=submission_id, decision="reject")
    assert _counts(job_db, result["job_id"]) == (1, 1)
    with sqlite3.connect(job_db) as conn:
        inputs = json.loads(conn.execute(
            "SELECT inputs_json FROM app_evidence_records WHERE feature_id='REPORT_OPERATOR_REVIEW' AND asset_id=?",
            (result["job_id"],),
        ).fetchone()[0])
    assert inputs["permission_audit_ref"] == "permission:first"
    assert inputs["operation_audit_ref"] == "operation:first"


@pytest.mark.parametrize("mismatch", ["actor", "scope"])
def test_wrong_actor_or_scope_is_denied_without_evidence(job_db, mismatch):
    result = _report(job_db)
    actor_id = "workspace:other" if mismatch == "actor" else "workspace:local"
    scope = dict(result["source_brief"]["scope"])
    if mismatch == "scope":
        scope["entity_label"] = "Other registered subject"
    with pytest.raises(PermissionError):
        reviews.write_operator_review(
            result["job_id"], actor_id=actor_id, expected_scope=scope,
            submission_id=str(uuid.uuid4()), decision="request_changes", notes="Revise.",
            authorize=_authorize(actor_id, scope),
        )
    assert _counts(job_db, result["job_id"]) == (0, 0)


def test_revoked_authorization_has_no_write(job_db):
    result = _report(job_db)

    def revoked():
        raise PermissionError("REPORT_REVIEW_DENIED")

    with pytest.raises(PermissionError, match="REPORT_REVIEW_DENIED"):
        _write(result, authorize=revoked)
    assert _counts(job_db, result["job_id"]) == (0, 0)


@pytest.mark.parametrize("revoke_at,expected_counts", [(2, (0, 0)), (3, (1, 0)), (4, (1, 1))])
def test_permission_is_rechecked_at_each_persistence_boundary(job_db, revoke_at, expected_counts):
    result = _report(job_db)
    attempts = 0

    def authorize():
        nonlocal attempts
        attempts += 1
        if attempts == revoke_at:
            raise PermissionError("REVOKED_BEFORE_EFFECT")
        return _authorize("workspace:local", result["source_brief"]["scope"])()

    with pytest.raises(PermissionError, match="REVOKED_BEFORE_EFFECT"):
        _write(result, authorize=authorize)
    assert _counts(job_db, result["job_id"]) == expected_counts
    with sqlite3.connect(job_db) as conn:
        assert conn.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id='REPORT_LEARNING_CASE'").fetchone()[0] == 0


def _learning_count(db_path):
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id='REPORT_LEARNING_CASE'").fetchone()[0]


def test_review_case_replays_and_reopens_without_training_promotion(job_db):
    result = _report(job_db)
    submission_id = str(uuid.uuid4())
    first = _write(result, submission_id=submission_id, decision="use_for_next_step")
    from lumenis.shared.learning.report_cases import record_report_case
    record_report_case(_verified(result), first)
    case = first["learning_case"]
    assert case["state"] == "recorded"
    assert case["training_eligible"] is False
    assert case["lifecycle_stage"] == "RAW" and case["review_status"] == "HUMAN_PENDING"
    assert _write(result, submission_id=submission_id, decision="use_for_next_step")["learning_case"] == case
    assert _learning_count(job_db) == 1 and _counts(job_db, result["job_id"]) == (1, 1)
    reopened = reviews.read_operator_reviews(_verified(result))
    assert reopened["latest"]["learning_case"] == case
    assert _learning_count(job_db) == 1  # GET/read never performs the missing side-write.


@pytest.mark.parametrize("failure", [OSError("isolated case failure"), LookupError("report temporarily unreadable")])
def test_learning_failure_is_explicit_and_same_review_repairs(job_db, monkeypatch, failure):
    from lumenis.shared.learning import report_cases

    result = _report(job_db)
    submission_id = str(uuid.uuid4())
    original = report_cases.record_report_case
    monkeypatch.setattr(report_cases, "record_report_case",
                        lambda *args: (_ for _ in ()).throw(failure))
    failed = _write(result, submission_id=submission_id)
    assert failed["learning_case"]["state"] == "pending_recovery"
    assert _counts(job_db, result["job_id"]) == (1, 1) and _learning_count(job_db) == 0
    assert reviews.read_operator_reviews(_verified(result))["latest"]["learning_case"]["state"] == "pending_recovery"
    assert _learning_count(job_db) == 0
    monkeypatch.setattr(report_cases, "record_report_case", original)
    repaired = _write(result, submission_id=submission_id)
    assert repaired["learning_case"]["state"] == "recorded"
    assert repaired["evidence_ref"] == failed["evidence_ref"]
    assert _counts(job_db, result["job_id"]) == (1, 1) and _learning_count(job_db) == 1


def test_signed_evidence_tampering_is_rejected_on_reopen(job_db):
    result = _report(job_db)
    review = _write(result)
    record_id = int(review["evidence_ref"].rsplit(":", 1)[1])
    with sqlite3.connect(job_db) as conn:
        conn.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?", (record_id,))
        conn.commit()

    with pytest.raises(RuntimeError, match="SIGNATURE_INVALID"):
        reviews.read_operator_reviews(_verified(result))


def test_evaluation_failure_is_pending_then_same_submission_repairs_without_duplicates(job_db, monkeypatch):
    result = _report(job_db)
    submission_id = str(uuid.uuid4())
    original = reviews.record_evaluation
    monkeypatch.setattr(reviews, "record_evaluation",
                        lambda **kwargs: (_ for _ in ()).throw(OSError("evaluation unavailable")))
    with pytest.raises(OSError, match="evaluation unavailable"):
        _write(result, submission_id=submission_id)
    assert _counts(job_db, result["job_id"]) == (1, 0)
    pending = reviews.read_operator_reviews(_verified(result))
    assert pending["state"] == "pending_recovery"
    assert pending["latest"]["evaluation_state"] == "pending_recovery"

    monkeypatch.setattr(reviews, "record_evaluation", original)
    repaired = _write(
        result, submission_id=submission_id,
        authorize=_authorize("workspace:local", result["source_brief"]["scope"], "recovery"),
    )
    assert repaired["business_outcome"] == "NOT_OBSERVED"
    assert _counts(job_db, result["job_id"]) == (1, 1)
    reopened = reviews.read_operator_reviews(_verified(result))
    assert reopened["state"] == "recorded"
    assert reopened["latest"]["review_id"] == repaired["review_id"]
