"""Scoped Learning references consume actual Reporting owners on disposable DBs."""
import json
import sqlite3

import pytest

from tests.test_source_brief_job import job_db, _request, _source
from tests.test_report_operator_review import _report, _write, _verified, _learning_count
from lumenis.shared.learning.report_cases import get_report_case


@pytest.mark.parametrize("field,value", [("actor_id", "workspace:other"),
                                         ("scope", {"global": True})])
def test_foreign_context_cannot_read_a_learning_case(job_db, field, value):
    result = _report(job_db)
    review = _write(result)
    with pytest.raises(PermissionError):
        get_report_case({**review, field: value})
    assert _learning_count(job_db) == 1


def test_case_tampering_is_pending_and_never_promotes_training(job_db):
    review = _write(_report(job_db))
    case = review["learning_case"]
    with sqlite3.connect(job_db) as con:
        con.execute("UPDATE app_evidence_records SET outputs_json=? WHERE id=?",
                    ('{"training_eligible":true}', int(case["evidence_ref"].split(":")[1])))
    reopened = get_report_case(review)
    assert reopened["state"] == "pending_recovery"
    assert "training_eligible" not in reopened
    assert _learning_count(job_db) == 1


def test_missing_case_read_does_not_repair_or_duplicate_the_review(job_db):
    review = _write(_report(job_db))
    with sqlite3.connect(job_db) as con:
        con.execute("DELETE FROM app_evidence_records WHERE feature_id='REPORT_LEARNING_CASE'")
    assert get_report_case(review) == {"state": "not_recorded"}
    assert _learning_count(job_db) == 0


def test_rejected_inference_is_referenced_without_copying_source_or_training(job_db, monkeypatch):
    from lumenis.shared.reporting import business_brief

    monkeypatch.setattr(business_brief.ai_core, "local_structured_chat",
                        lambda *args, **kwargs: ('{"invalid":true}', "ollama", {"model": "isolated-mock"}))
    with sqlite3.connect(job_db) as con:
        con.row_factory = sqlite3.Row
        _source(con)
        con.commit()
        result = _request(con, business_question="Propose a source-grounded content experiment.")
    analysis = result["business_analysis"]
    assert analysis["state"] == "unavailable"
    assert analysis["rejected_candidate_evidence_ref"]
    review = _write(result, decision="reject", notes="The candidate did not pass its source contract.")
    case = review["learning_case"]
    assert case["state"] == "recorded" and case["training_eligible"] is False
    with sqlite3.connect(job_db) as con:
        outputs_text = con.execute("SELECT outputs_json FROM app_evidence_records WHERE id=?",
                                   (int(case["evidence_ref"].split(":")[1]),)).fetchone()[0]
        outputs = json.loads(outputs_text)
    assert outputs["analysis_state"] == "unavailable"
    assert outputs["rejected_candidate_evidence_ref"] == analysis["rejected_candidate_evidence_ref"]
    assert "Private source body is not part of the brief" not in outputs_text
    assert outputs["material_state"] == "REFERENCED_NOT_TRAINED"
