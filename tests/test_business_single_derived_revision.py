"""Real domain/Shared service regressions on isolated synthetic source inputs."""
import copy

import pytest

from tests.test_business_domain_analysis_candidate import (
    _prepare_derived,
    _source_report,
)
from tests.test_business_result_continuity import business as _business
from tests.test_business_result_continuity import save, selection
from tests.test_saved_document_workflow import workspace as _workspace

business = _business
workspace = _workspace


def chosen(ws):
    prepared = _prepare_derived(ws, "prepare-single-revision", "source review")
    selected = ws["service"].advance(prepared["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], expected_revision=prepared["revision"], submission_id="choose-single-revision",
        operation="choose", payload=selection("source-review", "100"))
    return prepared, selected


def revision_payload(current):
    keys = ("option_id", "proposal", "rationale", "source_ids", "assumptions", "unknowns", "check")
    option = {key: copy.deepcopy(current["options"][0][key]) for key in keys}
    option["proposal"] = "Operator-refined internal source review with exact local notes."
    decision = {key: current["decision"][key] for key in ("option_id", "reason", "owner", "review_at")}
    if current["decision"].get("resource_constraints"):
        decision["resource_constraints"] = {key: current["decision"]["resource_constraints"][key]
            for key in ("budget_amount", "estimated_cost_amount", "currency", "as_of", "limits")}
    return {"source_job_id": current["source_report"]["job_id"], "question": current["question"],
            "options": [option], "decision": decision, "reason": "Refine the original research action only."}


def revise(ws, current, payload, request="adopt-single-revision"):
    return ws["service"].advance(current["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], expected_revision=current["revision"], submission_id=request,
        operation="adopt", payload=payload)


def count(ws):
    return ws["repo"].query_one("SELECT count(*) FROM app_evidence_records WHERE feature_id=?", (ws["service"].FEATURE,))[0]


def test_single_derived_action_revise_repeat_save_reopen_and_keep_parent(business):
    ws = business
    prepared, current = chosen(ws)
    assert len(current["options"]) == 1
    ws["current"] = current
    first = save(ws, request_id="save-single-before-revision")["saved_work"]
    payload = revision_payload(current)
    result = revise(ws, current, payload)
    analysis = result["domain_analysis"]
    root = prepared["domain_analysis"]
    assert analysis["version"] == root["version"]
    assert analysis["method"] == root["method"]
    assert analysis["source_report"] == root["source_report"]
    assert analysis["source_checks"] == root["source_checks"]
    assert analysis["question_result"]["basis_sha256"] == root["question_result"]["basis_sha256"]
    assert analysis["question_result"]["generation"] == "OPERATOR_REVISED_DERIVED_RECOMMENDATION"
    assert result["decision"]["resource_constraints"] == current["decision"]["resource_constraints"]
    binding = result["options"][0]["operator_revision"]
    assert binding["original_revision"] == prepared["revision"]
    assert binding["original_analysis_sha256"] == root["content_sha256"]
    assert binding["original_options_sha256"] == root["question_result"]["options_sha256"]
    assert binding["editor"] == ws["actor_ref"] and binding["parent_revision"] == current["revision"]
    assert result["options"][0]["source_ids"] == prepared["options"][0]["source_ids"]
    assert "人工修订" in result["usable_result"]["markdown"]
    assert revise(ws, current, payload)["revision"] == result["revision"]
    second_payload = revision_payload(result)
    second_payload["options"][0]["check"] += " Preserve the operator's additional stop condition."
    second = revise(ws, result, second_payload, "adopt-single-revision-again")
    assert second["options"][0]["operator_revision"]["original_revision"] == prepared["revision"]
    assert second["options"][0]["operator_revision"]["parent_revision"] == result["revision"]
    ws["current"] = second
    saved = save(ws, request_id="save-single-after-revision", parent=first["artifact"]["artifact_id"],
                 digest=first["document"]["draft_digest"])["saved_work"]
    assert saved["document"]["version"] == 2
    assert saved["document"]["parent_artifact_id"] == first["artifact"]["artifact_id"]
    assert saved["document"]["payload"]["business_work"]["options"] == second["options"]
    old = ws["service"].reopen(current["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
                              authorize=ws["authorize"], revision=current["revision"])
    assert old["options"] == prepared["options"]
    assert "operator_revision" not in old["options"][0]


@pytest.mark.parametrize("fault", ["identity", "source", "assumptions", "unknowns", "question", "report", "planning", "claimed_hash"])
def test_single_revision_rejects_changed_original_boundaries_without_write(business, fault):
    ws = business
    _, current = chosen(ws)
    payload = revision_payload(current)
    option = payload["options"][0]
    if fault == "identity":
        option["option_id"] = "replacement-action"
    elif fault == "source":
        option["source_ids"] = ["unadmitted-source"]
    elif fault == "assumptions":
        option["assumptions"] = ["An unrelated new assumption."]
    elif fault == "unknowns":
        option["unknowns"] = ["Replace the original method limitations."]
    elif fault == "question":
        payload["question"] = "source review for a different business objective"
    elif fault == "report":
        report = _source_report(ws, option["source_ids"], "single-revision-other-report")
        payload["source_job_id"] = report["job_id"]
    elif fault == "planning":
        payload["planning_constraints"] = {"time_range": {"start": "2026-10-01T00:00:00Z", "end": "2026-10-31T00:00:00Z"}}
    else:
        option["basis_sha256"] = "a" * 64
    before = count(ws)
    with pytest.raises((ValueError, PermissionError, RuntimeError)):
        revise(ws, current, payload)
    assert count(ws) == before


def test_new_explicit_single_option_guard_is_unchanged(business):
    ws = business
    _, current = chosen(ws)
    option = revision_payload(current)["options"]
    before = count(ws)
    with pytest.raises(ValueError, match="BUSINESS_WORK_COMPARABLE_OPTIONS_REQUIRED"):
        ws["service"].prepare(actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"],
            submission_id="prepare-new-manual-single", source_job_id=current["source_report"]["job_id"],
            kind=current["kind"], question=current["question"], options=option)
    assert count(ws) == before


def test_withdrawn_source_blocks_single_revision_without_write(business, monkeypatch):
    ws = business
    _, current = chosen(ws)
    before = count(ws)
    monkeypatch.setattr(ws["service"], "_bound_report", lambda *a, **k: (_ for _ in ()).throw(PermissionError("withdrawn source")))
    with pytest.raises(PermissionError, match="withdrawn source"):
        revise(ws, current, revision_payload(current))
    assert count(ws) == before


@pytest.mark.parametrize("question", ["source review", "source review and interaction feedback"])
def test_decision_only_revision_keeps_analysis_and_saved_parent(business, monkeypatch, question):
    ws = business
    prepared = _prepare_derived(ws, "prepare-decision-correction", question)
    current = ws["service"].advance(prepared["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], expected_revision=prepared["revision"], submission_id="choose-decision-correction",
        operation="choose", payload=selection(prepared["options"][0]["option_id"], "100"))
    ws["current"] = current
    first = save(ws, request_id="save-decision-before-correction")["saved_work"]
    payload = revision_payload(current)
    keys = ("option_id", "proposal", "rationale", "source_ids", "assumptions", "unknowns", "check")
    payload["options"] = [{key: copy.deepcopy(option[key]) for key in keys} for option in current["options"]]
    payload["decision"].update(owner="Reviewed operator", review_at="2026-10-25T03:00:00Z")
    payload["reason"] = "Correct the review date without changing the evidence or proposals."
    monkeypatch.setattr(ws["service"], "_prepare_analysis", lambda *a, **k: pytest.fail("Decision correction must not reanalyse sources"))
    updated = revise(ws, current, payload, "adopt-decision-correction")
    assert updated["options"] == current["options"]
    assert updated["domain_analysis"] == current["domain_analysis"]
    assert updated["adoption"]["analysis_retained"] is True
    assert updated["adoption"]["changed_option_ids"] == []
    assert updated["decision"]["review_at"] == "2026-10-25T03:00:00Z"
    assert updated["decision"]["resource_constraints"] == current["decision"]["resource_constraints"]
    assert revise(ws, current, payload, "adopt-decision-correction")["revision"] == updated["revision"]
    ws["current"] = updated
    saved = save(ws, request_id="save-decision-after-correction", parent=first["artifact"]["artifact_id"],
                 digest=first["document"]["draft_digest"])["saved_work"]
    assert saved["document"]["version"] == 2
    assert saved["document"]["parent_artifact_id"] == first["artifact"]["artifact_id"]
    reopened = ws["service"].reopen(current["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"])
    assert reopened["decision"] == updated["decision"]
    old = ws["service"].reopen(current["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"], revision=current["revision"])
    assert old["decision"] == current["decision"]
    before = count(ws)
    with pytest.raises(ValueError, match="BUSINESS_WORK_ADOPTION_HAS_NO_CHANGE"):
        revise(ws, updated, payload, "adopt-decision-unchanged")
    assert count(ws) == before
    if len(updated["options"]) == 1:
        amended = revise(ws, updated, revision_payload(updated), "revise-after-decision")
        assert amended["options"][0]["operator_revision"]["original_revision"] == prepared["revision"]


def test_revised_research_action_preserves_provenance_on_decision_edit(business):
    ws = business
    prepared, current = chosen(ws)
    revised = revise(ws, current, revision_payload(current))
    payload = revision_payload(revised)
    payload["decision"]["review_at"] = "2026-10-25T03:00:00Z"
    updated = revise(ws, revised, payload, "correct-revised-action-date")
    assert updated["options"] == revised["options"]
    assert updated["domain_analysis"] == revised["domain_analysis"]
    assert updated["options"][0]["operator_revision"]["original_revision"] == prepared["revision"]
    assert ws["service"].reopen(updated["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"])["decision"] == updated["decision"]
