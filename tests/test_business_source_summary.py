"""C3 source-summary/version regressions; generated inputs are not live acceptance."""
import copy

import pytest

from api_dual_domain import BusinessDecisionWorkflow
from tests.test_business_result_continuity import (
    add_material,
    adopt,
    make_options,
    save,
    selection,
)

pytest_plugins = (
    "tests.test_business_result_continuity",
    "tests.test_saved_document_workflow",
)


def test_saved_summary_stays_bound_to_explicitly_adopted_source_version(business):
    ws = business
    original = ws["current"]
    original_citation = copy.deepcopy(ws["citation"])
    summary = original["source_summary"]
    assert summary["source_report"] == original["source_report"]
    assert summary["content_hash"] == original["source_brief"]["content_hash"]
    assert summary["sample"] == original["source_brief"]["sample"]
    assert summary["status"] == "AVAILABLE"
    assert summary["coverage"] == summary["freshness"] == summary["collection_state"] == "UNKNOWN"
    assert "已验证返回样本：1" in original["usable_result"]["markdown"]
    assert "样本计数不代表市场覆盖、客流、需求或销量" in original["usable_result"]["markdown"]
    assert "范围证据未通过核验：0" in original["usable_result"]["markdown"]
    assert "未获准返回" not in original["usable_result"]["markdown"]
    assert summary["source_report"]["artifact_hash"] in original["usable_result"]["markdown"]
    assert "Original issuer disclosure. No consumer effect measured." not in original["usable_result"]["markdown"]

    first = save(ws, request_id="save-source-summary-01")["saved_work"]
    assert first["document"]["payload"]["business_work"]["source_summary"] == summary
    assert first["document"]["payload"]["brief"]["source_summary"] == summary

    report, citation = add_material(ws, "new-summary-source", "Revised issuer material. Demand remains unknown.")
    ws["current"] = adopt(ws, report, make_options(report["source_brief"]["records"][0]["source_id"]), selection("B", "100"))
    ws["citation"] = citation
    updated = ws["current"]["source_summary"]
    assert updated["source_report"] == ws["current"]["source_report"]
    assert updated["source_report"] != summary["source_report"]
    assert updated["content_hash"] == report["source_brief"]["content_hash"]
    second = save(ws, request_id="save-source-summary-02", parent=first["artifact"]["artifact_id"],
                  digest=first["document"]["draft_digest"])["saved_work"]
    assert second["document"]["payload"]["brief"]["source_summary"] == updated
    assert second["document"]["parent_sha256"] == first["artifact"]["sha256"]
    assert ws["work"].reopen_work(first["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"])["document"] == first["document"]

    old = ws["service"].reopen(original["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
                               authorize=ws["authorize"], revision=original["revision"])
    assert old["source_summary"] == summary
    assert save({**ws, "current": old, "citation": original_citation},
                request_id="save-source-summary-01")["saved_work"]["document"] == first["document"]


def test_legacy_signed_work_keeps_original_save_intent_after_formatter_upgrade(business, monkeypatch):
    ws = business
    transition = ws["service"]._transition

    def legacy_transition(*args, **kwargs):
        output = transition(*args, **kwargs)
        output.pop("result_projection_version", None)
        output.pop("domain_analysis", None)
        return output

    # Simulate the former writer's event shape; the real Evidence writer,
    # signatures, SourceBrief validation and Shared persistence still execute.
    with monkeypatch.context() as old_writer:
        old_writer.setattr(ws["service"], "_transition", legacy_transition)
        prepared = ws["service"].prepare(
            actor_ref=ws["actor_ref"], scope=ws["domain_scope"], submission_id="legacy-summary-prepare",
            source_job_id=ws["current"]["source_report"]["job_id"], kind=ws["current"]["kind"],
            question=ws["current"]["question"], options=copy.deepcopy(ws["options"]), authorize=ws["authorize"],
        )
        old = ws["service"].advance(
            prepared["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"],
            expected_revision=prepared["revision"], submission_id="legacy-summary-choose", operation="choose",
            payload=selection("A", "100"),
        )
        first = save({**ws, "current": old}, request_id="save-legacy-summary-01")["saved_work"]

    fresh = BusinessDecisionWorkflow(action_actor=ws["actor"])
    reopened = fresh.reopen(old["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"])
    assert "source_summary" not in reopened
    assert "source_summary" not in first["document"]["payload"]["business_work"]
    assert "source_summary" not in first["document"]["payload"]["brief"]
    replay = save({**ws, "service": fresh, "current": reopened}, request_id="save-legacy-summary-01")["saved_work"]
    assert replay["replayed"]
    assert replay["document"] == first["document"]
    assert replay["artifact"] == first["artifact"]


def test_two_sources_in_one_domain_preserve_counts_and_exact_saved_citations(business):
    ws = business
    original = ws["current"]
    first_source = original["source_brief"]["records"][0]["source_id"]
    first_citation = copy.deepcopy(ws["citation"])
    second, second_citation = add_material(ws, "second-summary-source", "Another source statement; demand is unmeasured.")
    source_ids = [first_source, second["source_brief"]["records"][0]["source_id"]]
    scope = ws["domain_scope"]
    with ws["repo"].transaction() as connection:
        report = ws["jobs"].create_source_brief_job(
            connection, product_id=scope["product_id"], subject_id=scope["subject_id"],
            brand_focus_id=scope["brand_focus_id"], global_scope=False, entity_label=scope["entity_label"],
            source_ids=source_ids, actor_id=ws["actor_ref"], permission_audit_ref="isolated-source-audit",
            trace_id="summary-two-source-trace", job_id="summary-two-source-job",
        )
    options = make_options(first_source)
    for option in options:
        option["source_ids"] = source_ids
    ws["current"] = adopt(ws, report, options, selection("A", "100"), request_id="adopt-two-summary-sources")
    summary = ws["current"]["source_summary"]
    assert summary["source_report"] == ws["current"]["source_report"]
    assert summary["sample"]["returned_verified_count"] == 2
    assert sum(summary["sample"]["source_type_counts_sample"].values()) == 2
    assert sum(summary["sample"]["platform_counts_sample"].values()) == 2
    assert "已验证返回样本：2" in ws["current"]["usable_result"]["markdown"]
    saved = save(ws, request_id="save-two-summary-sources", citations=[first_citation, second_citation])["saved_work"]
    payload = saved["document"]["payload"]
    assert payload["business_work"]["source_summary"] == payload["brief"]["source_summary"] == summary
    assert len(saved["document"]["citations"]) == 2
    assert {binding["source_id"] for binding in payload["business_work"]["source_bindings"]} == set(source_ids)

    def assert_metadata_only(value):
        if isinstance(value, dict):
            assert not {"records", "body", "text", "title", "url", "markdown", "business_analysis"} & value.keys()
            for child in value.values():
                assert_metadata_only(child)
        elif isinstance(value, list):
            for child in value:
                assert_metadata_only(child)

    assert_metadata_only(payload["business_work"]["source_summary"])
    assert_metadata_only(payload["brief"]["source_summary"])
    reopened = ws["work"].reopen_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"])
    assert reopened["document"] == saved["document"]
    historical = ws["service"].reopen(original["work_id"], actor_ref=ws["actor_ref"], scope=scope,
                                      authorize=ws["authorize"], revision=original["revision"])
    assert historical["source_summary"]["sample"]["returned_verified_count"] == 1
    assert historical["source_summary"]["source_report"] == original["source_report"]


@pytest.mark.parametrize("bad_projection", [None, "cth-bmp-source-summary/future"])
def test_signed_unknown_projection_is_rejected(business, monkeypatch, bad_projection):
    ws = business
    transition = ws["service"]._transition

    def incompatible_writer(*args, **kwargs):
        output = transition(*args, **kwargs)
        output["result_projection_version"] = bad_projection
        return output

    monkeypatch.setattr(ws["service"], "_transition", incompatible_writer)
    with pytest.raises(RuntimeError, match="BUSINESS_WORK_RESULT_PROJECTION_UNSUPPORTED"):
        ws["service"].advance(
            ws["current"]["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"],
            expected_revision=ws["current"]["revision"], submission_id="incompatible-summary-writer",
            operation="interrupt", payload={"reason": "Simulated incompatible writer."},
        )


def test_recovery_cannot_drop_signed_projection_contract(business, monkeypatch):
    ws = business
    interrupted = ws["service"].advance(
        ws["current"]["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"],
        expected_revision=ws["current"]["revision"], submission_id="interrupt-summary-test",
        operation="interrupt", payload={"reason": "Retryable local interruption."},
    )
    assert interrupted["source_summary"] == ws["current"]["source_summary"]
    transition = ws["service"]._transition

    def incompatible_recovery(*args, **kwargs):
        output = transition(*args, **kwargs)
        output.pop("result_projection_version")
        return output

    monkeypatch.setattr(ws["service"], "_transition", incompatible_recovery)
    with pytest.raises(RuntimeError, match="BUSINESS_WORK_RESULT_PROJECTION_CHANGED"):
        ws["service"].advance(
            ws["current"]["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"],
            expected_revision=interrupted["revision"], submission_id="resume-summary-test", operation="resume", payload={},
        )
