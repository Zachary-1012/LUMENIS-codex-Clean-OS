"""C3 global SourceBrief rejection and exact-focus business-work continuity."""

import pytest

from tests.test_business_result_continuity import make_options, save, selection

pytest_plugins = ("tests.test_business_result_continuity", "tests.test_saved_document_workflow")


def test_global_report_is_rejected_for_exact_focus_business_work_and_focus_result_reopens(business):
    ws = business
    source_id = ws["current"]["options"][0]["source_ids"][0]
    with ws["repo"].transaction() as connection:
        global_report = ws["jobs"].create_source_brief_job(
            connection,
            product_id=ws["domain_scope"]["product_id"],
            subject_id=None,
            brand_focus_id=None,
            global_scope=True,
            entity_label="GLOBAL / ALL",
            source_ids=[source_id],
            actor_id=ws["actor_ref"],
            permission_audit_ref="isolated-global-source-read",
            trace_id="isolated-global-source-trace",
            job_id="isolated-global-source-report",
        )

    from api_dual_domain import BusinessDecisionWorkflow

    global_scope = global_report["source_brief"]["scope"]
    service = BusinessDecisionWorkflow(action_actor=ws["actor"])
    global_authorize = lambda operation: {
        "actor_id": ws["actor_ref"],
        "scope": global_scope,
        "operation": operation,
        "permission_audit_ref": "isolated-global-scope-audit",
        "operation_audit_ref": "isolated-global-operation-audit",
    }
    before = ws["repo"].query_one(
        "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id=?",
        (service.FEATURE,),
    )[0]

    with pytest.raises(PermissionError, match="BUSINESS_WORK_EXACT_FOCUS_REQUIRED"):
        service.prepare(
            actor_ref=ws["actor_ref"],
            scope=global_scope,
            submission_id="global-business-work-rejected",
            source_job_id=global_report["job_id"],
            kind=ws["current"]["kind"],
            question="source review",
            options=make_options(source_id),
            authorize=global_authorize,
        )

    after = ws["repo"].query_one(
        "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id=?",
        (service.FEATURE,),
    )[0]
    assert after == before

    prepared = ws["service"].prepare(
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        authorize=ws["authorize"],
        submission_id="exact-focus-planned-work",
        source_job_id=ws["current"]["source_report"]["job_id"],
        kind=ws["current"]["kind"],
        question="Review the permitted source material.",
        options=make_options(source_id),
        planning_constraints={},
    )
    assert prepared["domain_analysis"]["scope"] == ws["domain_scope"]
    assert prepared["domain_analysis"]["source_checks"][0]["state"] == "SOURCE_USE_VERIFIED"
    ws["current"] = ws["service"].advance(
        prepared["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], expected_revision=prepared["revision"],
        submission_id="exact-focus-planned-choice", operation="choose", payload=selection("A", "100"),
    )

    saved = save(ws, request_id="exact-focus-business-work-save")["saved_work"]
    reopened = ws["work"].reopen_work(
        saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
    )
    assert reopened["document"] == saved["document"]
    assert reopened["document"]["payload"]["brief"]["scope"] == ws["domain_scope"]
