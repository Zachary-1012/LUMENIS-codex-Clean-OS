"""Scoped Learning references consume actual Reporting owners on disposable DBs."""
import json
import sqlite3

import pytest

from tests.test_source_brief_job import job_db, _request, _source
from tests.test_report_operator_review import _report, _write, _verified, _learning_count
from lumenis.shared.learning.report_cases import get_report_case
from tests.test_saved_document_workflow import workspace


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


def test_rejected_inference_is_referenced_without_copying_source_or_training(workspace, monkeypatch):
    """Real import/source-use/rejection owners; only invalid inference is synthetic.

    The retired Ollama seam never produces an inference candidate now. Use the
    existing owned Gateway seam after actual original-byte/scope/rights checks,
    preserving the rejection-reference and no-training assertions below.
    """
    from lumenis.shared.reporting import business_brief, source_brief_job as jobs
    from lumenis.shared.database.business_schema import apply_business_schema
    from lumenis.shared.evaluation import recorder
    from lumenis.shared.evidence import store
    from tests.test_business_brief_typed_owned import _seed_source, _owned_result, _wire_repositories
    import subject_registry

    _wire_repositories(workspace, monkeypatch)
    with workspace["repo"].transaction() as con:
        apply_business_schema(con)
    recorder.init_db()
    entry, _ = subject_registry.add_subject({"domain_id": "CTH", "subject_type": "company",
        "name_en": "Synthetic rejected candidate subject", "name_zh": "合成拒绝候选测试主体"})
    workspace = {**workspace, "scope": {**workspace["scope"], "subject_id": entry["subject_id"], "global_scope": False}}
    source, _ = _seed_source(workspace)
    calls = []
    def invalid_owned_response(request):
        calls.append(request)
        return _owned_result(request, actor=workspace["actor"], analysis={"invalid": True})
    monkeypatch.setattr(business_brief.gateway, "run_owned_request", invalid_owned_response)
    with workspace["repo"].connection(read_only=True, wal=False) as con:
        result = jobs.create_source_brief_job(con, product_id="CTH", global_scope=False,
            entity_label=entry["name_en"], subject_id=entry["subject_id"], actor_id="workspace:local",
            image_actor=workspace["actor"], permission_audit_ref="test:rejected-candidate-source-read",
            trace_id="test:rejected-candidate", job_id="job-real-rejected-candidate-0001",
            source_ids=[source["source_id"]], business_question="Propose a source-grounded content experiment.")
    assert len(calls) == 1
    job_db = workspace["root"] / "isolated.sqlite3"
    analysis = result["business_analysis"]
    assert analysis["state"] == "unavailable"
    assert analysis["rejected_candidate_evidence_ref"]
    with workspace["repo"].connection(read_only=True, wal=False) as con:
        rejected = dict(con.execute("SELECT * FROM app_evidence_records WHERE id=?",
            (int(analysis["rejected_candidate_evidence_ref"].split(":")[1]),)).fetchone())
    assert store.verify_evidence_record_integrity(rejected)
    assert rejected["feature_id"] == "REPORT_BUSINESS_ANALYSIS_REJECTED"
    assert rejected["provider"] == "owned" and rejected["result"] == "FAIL"
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
    assert source["text"] not in outputs_text
    assert outputs["material_state"] == "REFERENCED_NOT_TRAINED"


def test_retired_provider_does_not_manufacture_generated_or_rejected_evidence(workspace, monkeypatch):
    from lumenis.shared.reporting import business_brief
    from tests.test_business_brief_typed_owned import _seed_source, _wire_repositories
    _wire_repositories(workspace, monkeypatch)
    source, _ = _seed_source(workspace)
    monkeypatch.setattr(business_brief, '_request_business_inference',
        lambda *args, **kwargs: ('{"invalid":true}', 'ollama', {'model': 'retired-test-only'}))
    result = business_brief.analyze_business_brief(question='Review the source wording.', sources=[source],
        sample={'coverage': 'PARTIAL'}, scope=workspace['scope'], job_id='retired-provider-no-candidate',
        actor_ref='workspace:local', actor=workspace['actor'])
    assert result['state'] == 'unavailable'
    assert result['reason'] == 'BUSINESS_BRIEF_RETIRED_OR_UNAVAILABLE_PROVIDER'
    assert 'rejected_candidate_evidence_ref' not in result
    assert workspace['repo'].query_one("SELECT count(*) FROM app_evidence_records WHERE feature_id IN "
        "('REPORT_BUSINESS_ANALYSIS','REPORT_BUSINESS_ANALYSIS_REJECTED')")[0] == 0
