"""Bounded deterministic CTH/BMP domain-analysis regressions."""
import copy

import pytest

from tests import test_business_approved_source_continuity as approved_source
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


def _assert_analysis(work, expected_source_ids):
    analysis = work["domain_analysis"]
    assert analysis["version"] == "cth-bmp-domain-analysis/1"
    assert analysis["state"] == "ANALYZED_WITH_LIMITATIONS"
    assert analysis["source_report"] == work["source_report"]
    assert analysis["question"] == work["question"]
    assert analysis["kind"] == work["kind"]
    assert [item["source_id"] for item in analysis["source_checks"]] == sorted(expected_source_ids)
    assert all(item["state"] in {"SOURCE_USE_VERIFIED", "UNAVAILABLE"}
               for item in analysis["source_checks"])

    def keys(value):
        if isinstance(value, dict):
            for key, nested in value.items():
                yield key
                yield from keys(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from keys(nested)

    assert not {"text", "quote", "body"}.intersection(keys(analysis))
    return analysis


def _current_report(ws):
    with ws["repo"].connection(read_only=True, wal=False) as connection:
        return ws["service"]._report(
            connection,
            ws["current"]["source_report"]["job_id"],
            ws["actor_ref"],
            ws["domain_scope"],
        )


def _prepare_derived(ws, submission_id, question, *, source_job_id=None, planning_constraints=None):
    arguments = {
        "actor_ref": ws["actor_ref"],
        "scope": ws["domain_scope"],
        "submission_id": submission_id,
        "source_job_id": source_job_id or ws["current"]["source_report"]["job_id"],
        "kind": ws["current"]["kind"],
        "question": question,
        "authorize": ws["authorize"],
    }
    if planning_constraints is not None:
        arguments["planning_constraints"] = planning_constraints
    return ws["service"].prepare(**arguments)


def _source_report(ws, source_ids, suffix):
    scope = ws["domain_scope"]
    with ws["repo"].transaction() as connection:
        report = ws["jobs"].create_source_brief_job(
            connection,
            product_id=scope["product_id"],
            subject_id=scope["subject_id"],
            brand_focus_id=scope["brand_focus_id"],
            global_scope=False,
            entity_label=scope["entity_label"],
            source_ids=source_ids,
            actor_id=ws["actor_ref"],
            permission_audit_ref="isolated-source-audit",
            trace_id="analysis-two-source-" + suffix,
            job_id="analysis-two-source-" + suffix,
        )
    return report


_CANONICAL_ANALYSIS_FIELDS = (
    "canonical_id", "source_id", "source_platform", "subject_id", "brand_focus_id",
    "publish_datetime", "captured_at", "sentiment", "risk_level",
    "engagement_likes", "engagement_comments", "engagement_collects", "engagement_shares",
)


def _canonical_analysis_input(ws, source_id):
    with ws["repo"].connection(read_only=True, wal=False) as connection:
        row = ws["service"]._canonical_source(connection, source_id, ws["domain_scope"])
    return {field: row.get(field) for field in _CANONICAL_ANALYSIS_FIELDS}


def _set_canonical_analysis_fields(ws, source_id, **fields):
    if not fields or set(fields) - set(_CANONICAL_ANALYSIS_FIELDS):
        raise AssertionError("test fixture may update only declared canonical analysis fields")
    names = sorted(fields)
    with ws["repo"].transaction() as connection:
        cursor = connection.execute(
            "UPDATE canonical_data SET " + ", ".join(f"{name}=?" for name in names)
            + " WHERE source_id=? AND product_id=? AND domain_id=?",
            tuple(fields[name] for name in names) + (
                source_id, ws["domain_scope"]["product_id"], ws["domain_scope"]["domain_id"],
            ),
        )
        if cursor.rowcount != 1:
            raise AssertionError("expected exactly one isolated canonical source row")


def _set_signed_source_role_annotation(ws, source_id, role):
    import json

    from lumenis.shared.evidence import store

    canonical = ws["repo"].query_one(
        "SELECT scope_evidence_ref FROM canonical_data WHERE source_id=? AND product_id=? AND domain_id=?",
        (source_id, ws["domain_scope"]["product_id"], ws["domain_scope"]["domain_id"]),
    )
    evidence_id = str(canonical[0]).rsplit(":", 1)[-1]
    if not evidence_id.isdecimal():
        raise AssertionError("fixture source has no scoped Evidence record")
    with ws["repo"].transaction() as connection:
        evidence = connection.execute(
            "SELECT inputs_json FROM app_evidence_records WHERE id=?", (int(evidence_id),),
        ).fetchone()
        if evidence is None:
            raise AssertionError("fixture scope Evidence record is missing")
        inputs = json.loads(evidence["inputs_json"])
        inputs["source_role"] = role
        connection.execute(
            "UPDATE app_evidence_records SET inputs_json=? WHERE id=?",
            (json.dumps(inputs, ensure_ascii=False, sort_keys=True, separators=(",", ":")), int(evidence_id)),
        )
        store._sign_evidence_record(connection, int(evidence_id))
    return row


def _revocable_source_reference(ws, monkeypatch, suffix):
    approved_source._install_test_source_scope_declaration(ws, monkeypatch)
    if ws["domain_scope"]["domain_id"] == "cth":
        source = approved_source._seed_cth_notes_parent(ws)
    else:
        source = approved_source._seed_bmp_evidence_parent(ws)
    approved_source._install_test_receipt(monkeypatch, source["entry"])
    request_id = "domain-analysis-source-reference-" + suffix
    request = approved_source._confirm_source_reference_import(
        ws, source, request_id=request_id,
    )
    from lumenis.importer import documents

    created = documents.create_approved_source_reference(
        **request, actor=ws["actor"], scope=ws["scope"],
    )
    assert created["ok"] is True
    return source


def _two_source_report(ws, suffix):
    original = ws["current"]
    first_source = original["source_brief"]["records"][0]["source_id"]
    first_citation = copy.deepcopy(ws["citation"])
    second_report, second_citation = add_material(
        ws,
        "analysis-second",
        "Another permitted source statement; demand remains unknown.",
    )
    second_source = second_report["source_brief"]["records"][0]["source_id"]
    source_ids = [first_source, second_source]
    return {
        "first_source": first_source,
        "first_citation": first_citation,
        "second_source": second_source,
        "second_citation": second_citation,
        "source_ids": source_ids,
        "report": _source_report(ws, source_ids, suffix),
    }


def test_domain_analysis_runs_without_model_and_is_saved_with_business_work(business):
    ws = business
    source_ids = [item["source_id"] for item in ws["current"]["source_brief"]["records"]]

    prepared = ws["service"].prepare(
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        submission_id="prepare-analysis-" + ws["domain_scope"]["domain_id"],
        source_job_id=ws["current"]["source_report"]["job_id"],
        kind=ws["current"]["kind"],
        question=ws["current"]["question"],
        options=copy.deepcopy(ws["options"]),
        authorize=ws["authorize"],
    )
    prepared_analysis = _assert_analysis(prepared, source_ids)
    assert prepared_analysis["scope"] == ws["domain_scope"]

    analysis = _assert_analysis(ws["current"], source_ids)
    metric = analysis["metric_snapshot"]
    assert metric["source_count"] == len(source_ids)
    assert metric["complete_engagement_source_count"] == 0
    assert metric["total_engagement_complete_sources"] is None
    assert analysis["resource_assessment"]["budget_remaining_amount"] == "50"
    assert analysis["resource_assessment"]["currency"] == "CNY"
    assert analysis["resource_assessment"]["claim_type"] == "OPERATOR_CONSTRAINT_AND_ESTIMATE"

    saved = save(ws, request_id="save-analysis-" + ws["domain_scope"]["domain_id"])["saved_work"]
    document = saved["document"]
    business_analysis = document["payload"]["business_work"]["domain_analysis"]
    brief_analysis = document["payload"]["brief"]["domain_analysis"]
    assert business_analysis == analysis
    assert brief_analysis == analysis
    assert document["markdown"].startswith(ws["current"]["usable_result"]["markdown"])


def test_calendar_dates_are_source_bound_and_invalid_dates_are_omitted(business):
    ws = business
    body = "Issuer schedule states a planned date: 2026-10-12; invalid source date: 2026-02-30."
    report, citation = add_material(ws, "domain-analysis-calendar", body)
    source_id = report["source_brief"]["records"][0]["source_id"]
    ws["current"] = adopt(
        ws,
        report,
        make_options(source_id),
        selection("A", "100"),
        request_id="adopt-analysis-calendar",
    )
    ws["citation"] = citation

    analysis = _assert_analysis(ws["current"], [source_id])
    valid_start = body.index("2026-10-12")
    source_check = analysis["source_checks"][0]
    assert source_check["state"] == "SOURCE_USE_VERIFIED", source_check
    assert source_check["source_reported_dates"] == [{
        "date": "2026-10-12",
        "start": valid_start,
        "end": valid_start + len("2026-10-12"),
    }]
    assert source_check["selection"]["start"] <= valid_start
    assert source_check["selection"]["end"] >= valid_start + len("2026-10-12")
    assert body[valid_start:valid_start + len("2026-10-12")] == "2026-10-12"
    assert source_check["date_interpretation"] == "SOURCE_REPORTED_MENTION_NOT_CONFIRMED_EVENT"
    assert analysis["judgment"]["date_confirmation"] == "REVIEW_REQUIRED"

    document = save(ws, request_id="save-analysis-calendar")["saved_work"]["document"]
    assert document["payload"]["business_work"]["domain_analysis"] == analysis
    assert document["payload"]["brief"]["domain_analysis"] == analysis
    from lumenis.shared.reporting.operational_brief import _markdown_text
    assert _markdown_text("2026-10-12") in document["markdown"]
    assert _markdown_text("2026-02-30") not in document["markdown"]


def test_budget_revision_changes_only_resource_assessment_and_preserves_saved_version(business):
    ws = business
    first = save(ws, request_id="save-analysis-budget-v1")["saved_work"]
    first_document = first["document"]
    first_analysis = first_document["payload"]["business_work"]["domain_analysis"]
    assert first_analysis["resource_assessment"]["budget_remaining_amount"] == "50"

    report = _current_report(ws)
    ws["current"] = adopt(
        ws,
        report["snapshot"],
        copy.deepcopy(ws["options"]),
        selection("A", "30"),
        request_id="adopt-analysis-budget-v2",
    )
    revised_analysis = _assert_analysis(
        ws["current"],
        [item["source_id"] for item in ws["current"]["source_brief"]["records"]],
    )
    revised_resources = revised_analysis["resource_assessment"]
    assert revised_resources["budget_amount"] == "30"
    assert revised_resources["estimated_cost_amount"] == "50"
    assert revised_resources["budget_remaining_amount"] == "-20"
    assert revised_resources["currency"] == "CNY"
    assert revised_resources["claim_type"] == "OPERATOR_CONSTRAINT_AND_ESTIMATE"
    assert revised_analysis["source_checks"] == first_analysis["source_checks"]
    assert {
        key: value for key, value in revised_analysis.items()
        if key not in {"resource_assessment", "content_sha256"}
    } == {
        key: value for key, value in first_analysis.items()
        if key not in {"resource_assessment", "content_sha256"}
    }

    second = save(
        ws,
        request_id="save-analysis-budget-v2",
        parent=first["artifact"]["artifact_id"],
        digest=first_document["draft_digest"],
    )["saved_work"]
    second_document = second["document"]
    assert second_document["version"] == 2
    assert second_document["payload"]["business_work"]["domain_analysis"] == revised_analysis
    assert second_document["payload"]["brief"]["domain_analysis"] == revised_analysis

    reopened_first = ws["work"].reopen_work(
        first["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
    )["document"]
    assert reopened_first == first_document
    assert reopened_first["payload"]["brief"]["domain_analysis"]["resource_assessment"][
        "budget_remaining_amount"
    ] == "50"


def test_legacy_signed_work_without_domain_analysis_keeps_legacy_saved_shape(business, monkeypatch):
    ws = business
    service = ws["service"]
    original_transition = service._transition

    # This isolated monkeypatch emits the prior v1 transition shape; it checks
    # signed legacy compatibility and is not a real product E2E.
    def legacy_transition(connection, history, operation, payload, actor_ref, scope, authorize):
        assert operation == "prepare"
        report = service._report(connection, payload["source_job_id"], actor_ref, scope)
        source_ids = {item["source_id"] for item in report["source_brief"]["records"]}
        return {
            "state": "PREPARED",
            "options": service._options(payload["options"], source_ids),
            "decision": None,
            "source_report_hash": report["row"]["artifact_hash"],
            "case_id": None,
            "case_evidence_ref": None,
            "resume_count": 0,
            "outcome_state": "NOT_OBSERVED",
            "business_outcome": "NOT_OBSERVED",
            "action_state": "NOT_EXECUTED",
        }

    monkeypatch.setattr(service, "_transition", legacy_transition)
    legacy_prepared = service.prepare(
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        submission_id="legacy-prepare-analysis",
        source_job_id=ws["current"]["source_report"]["job_id"],
        kind=ws["current"]["kind"],
        question=ws["current"]["question"],
        options=copy.deepcopy(ws["options"]),
        authorize=ws["authorize"],
    )
    monkeypatch.setattr(service, "_transition", original_transition)
    assert "domain_analysis" not in legacy_prepared

    legacy_decided = service.advance(
        legacy_prepared["work_id"],
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        authorize=ws["authorize"],
        expected_revision=legacy_prepared["revision"],
        submission_id="legacy-choose-analysis",
        operation="choose",
        payload=selection("A", "100"),
    )
    assert "domain_analysis" not in legacy_decided
    with ws["repo"].connection(read_only=True, wal=False) as connection:
        signed_legacy_rows = [tuple(row) for row in connection.execute(
            "SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=? ORDER BY id",
            (service.FEATURE, legacy_prepared["work_id"]),
        ).fetchall()]
    legacy_ws = {**ws, "current": legacy_decided}
    legacy_saved = save(legacy_ws, request_id="legacy-save-analysis")["saved_work"]
    legacy_document = legacy_saved["document"]
    assert "domain_analysis" not in legacy_document["payload"]["business_work"]
    assert "domain_analysis" not in legacy_document["payload"]["brief"]
    legacy_export = ws["work"].export_work(
        legacy_saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
    )["content"]

    reopened = ws["work"].reopen_work(
        legacy_saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
    )["document"]
    assert reopened == legacy_document
    assert ws["work"].export_work(
        legacy_saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
    )["content"] == legacy_export
    with ws["repo"].connection(read_only=True, wal=False) as connection:
        assert [tuple(row) for row in connection.execute(
            "SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=? ORDER BY id",
            (service.FEATURE, legacy_prepared["work_id"]),
        ).fetchall()] == signed_legacy_rows


def test_unknown_budget_amount_stays_unknown(business):
    ws = business
    report = _current_report(ws)
    ws["current"] = adopt(
        ws,
        report["snapshot"],
        copy.deepcopy(ws["options"]),
        selection("B", None),
        request_id="adopt-analysis-budget-unknown",
    )
    analysis = ws["current"]["domain_analysis"]
    resources = analysis["resource_assessment"]
    assert resources["budget_amount"] is None
    assert resources["budget_remaining_amount"] is None


def test_analysis_sources_are_required_for_saved_citations(business):
    ws = business
    sources = _two_source_report(ws, "required-citations")
    first_source = sources["first_source"]
    options = make_options(first_source)
    assert all(option["source_ids"] == [first_source] for option in options)
    ws["current"] = adopt(
        ws,
        sources["report"],
        options,
        selection("A", "100"),
        request_id="adopt-analysis-two-sources",
    )
    analysis = ws["current"]["domain_analysis"]
    assert {item["source_id"] for item in analysis["source_checks"]} == set(sources["source_ids"])

    with pytest.raises(ValueError, match="BUSINESS_WORK_SAVE_SOURCE_CITATION_MISSING"):
        save(ws, request_id="save-analysis-missing-source", citations=[sources["first_citation"]])

    saved = save(
        ws,
        request_id="save-analysis-two-sources",
        citations=[sources["first_citation"], sources["second_citation"]],
    )["saved_work"]
    payload = saved["document"]["payload"]
    business_work = payload["business_work"]
    assert business_work["domain_analysis"] == payload["brief"]["domain_analysis"] == analysis
    assert {binding["source_id"] for binding in business_work["source_bindings"]} == set(sources["source_ids"])


def test_unavailable_secondary_analysis_source_does_not_block_valid_source_save(business, monkeypatch):
    ws = business
    first_source = ws["current"]["source_brief"]["records"][0]["source_id"]
    withdrawn = _revocable_source_reference(ws, monkeypatch, "partial")
    second_source = withdrawn["source_id"]
    report = _source_report(ws, [first_source, second_source], "withdrawn-secondary")
    assert {item["source_id"] for item in report["source_brief"]["records"]} == {
        first_source, second_source,
    }
    approved_source._revoke_current_source_rights(ws, withdrawn)

    from lumenis.shared.reporting import operational_brief

    real_builder = operational_brief.build_scoped_source_brief
    builder_calls = []

    def spy_builder(connection, **kwargs):
        builder_calls.append({
            "source_ids": list(kwargs.get("source_ids") or []),
            "include_analysis_text": kwargs.get("include_analysis_text"),
            "analysis_question": kwargs.get("analysis_question"),
        })
        return real_builder(connection, **kwargs)

    monkeypatch.setattr(operational_brief, "build_scoped_source_brief", spy_builder)
    options = make_options(first_source)
    assert all(option["source_ids"] == [first_source] for option in options)
    ws["current"] = adopt(
        ws,
        report,
        options,
        selection("A", "100"),
        request_id="adopt-analysis-withdrawn-source",
    )
    analysis = ws["current"]["domain_analysis"]
    checks = {item["source_id"]: item for item in analysis["source_checks"]}
    assert set(checks) == {first_source, second_source}
    assert checks[first_source]["state"] == "SOURCE_USE_VERIFIED", checks[first_source]
    assert checks[second_source]["state"] == "UNAVAILABLE", checks[second_source]
    assert analysis["metric_snapshot"]["source_count"] == 1
    assert analysis["metric_snapshot"]["unavailable_source_count"] == 1
    assert {item["source_id"] for item in ws["current"]["material_review"]["sources"]} == {first_source}
    question_windows = [
        call for call in builder_calls
        if call["include_analysis_text"] is True
        and call["analysis_question"] == ws["current"]["question"]
    ]
    assert question_windows
    assert all(second_source not in call["source_ids"] for call in question_windows)
    assert any(call["source_ids"] == [first_source] for call in question_windows)

    saved = save(
        ws,
        request_id="save-analysis-withdrawn-source",
        citations=[ws["citation"]],
    )["saved_work"]
    payload = saved["document"]["payload"]
    business_work = payload["business_work"]
    assert business_work["domain_analysis"] == payload["brief"]["domain_analysis"] == analysis
    assert {binding["source_id"] for binding in business_work["source_bindings"]} == {first_source}


def test_unavailable_sources_leave_date_claims_unknown_and_checks_minimal(business, monkeypatch):
    ws = business
    withdrawn = _revocable_source_reference(ws, monkeypatch, "all-unavailable")
    source_id = withdrawn["source_id"]
    report = _source_report(ws, [source_id], "all-unavailable")
    approved_source._revoke_current_source_rights(ws, withdrawn)

    from lumenis.shared.reporting import operational_brief

    real_builder = operational_brief.build_scoped_source_brief
    builder_calls = []

    def spy_builder(connection, **kwargs):
        builder_calls.append({
            "source_ids": list(kwargs.get("source_ids") or []),
            "include_analysis_text": kwargs.get("include_analysis_text"),
            "analysis_question": kwargs.get("analysis_question"),
        })
        return real_builder(connection, **kwargs)

    monkeypatch.setattr(operational_brief, "build_scoped_source_brief", spy_builder)
    ws["current"] = adopt(
        ws,
        report,
        make_options(source_id),
        selection("A", "100"),
        request_id="adopt-analysis-all-unavailable",
    )

    analysis = ws["current"]["domain_analysis"]
    assert analysis["judgment"]["sources_with_reported_dates"] is None
    assert analysis["judgment"]["date_confirmation"] == "NOT_ANALYZED"
    assert len(analysis["source_checks"]) == 1
    assert analysis["source_checks"][0]["source_id"] == source_id
    assert analysis["source_checks"][0]["state"] == "UNAVAILABLE"
    assert set(analysis["source_checks"][0]) == {"source_id", "state", "reason"}
    assert analysis["metric_snapshot"]["source_count"] == 0
    assert analysis["metric_snapshot"]["total_engagement_complete_sources"] is None
    assert analysis["material_review"]["sources"] == []
    assert not any(
        call["include_analysis_text"] is True and source_id in call["source_ids"]
        for call in builder_calls
    )


def test_omitted_options_derive_one_source_review_and_save_reopen(business):
    ws = business
    prepared = _prepare_derived(
        ws,
        "prepare-derived-source-review",
        "source review",
    )
    analysis = prepared["domain_analysis"]
    assert prepared["state"] == "PREPARED"
    assert prepared["decision"] is None
    assert analysis["version"] == "cth-bmp-domain-analysis/3"
    assert analysis["question_result"]["generation"] == "SYSTEM_DERIVED_RECOMMENDATIONS"
    assert [option["option_id"] for option in prepared["options"]] == ["source-review"]
    assert prepared["options"][0]["claim_type"] == "SYSTEM_DERIVED_RECOMMENDATION"
    assert prepared["options"][0]["claim_type"] != "OPERATOR_PROPOSAL"

    chosen = ws["service"].advance(
        prepared["work_id"],
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        authorize=ws["authorize"],
        expected_revision=prepared["revision"],
        submission_id="choose-derived-source-review",
        operation="choose",
        payload=selection("source-review", "100"),
    )
    ws["current"] = chosen
    saved = save(ws, request_id="save-derived-source-review")["saved_work"]
    document = saved["document"]
    assert document["payload"]["business_work"]["domain_analysis"] == chosen["domain_analysis"]
    assert document["payload"]["brief"]["domain_analysis"] == chosen["domain_analysis"]
    reopened = ws["work"].reopen_work(
        saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
    )["document"]
    assert reopened == document


def test_chinese_calendar_review_binds_valid_date_offsets_and_leaves_no_date_gap(business):
    ws = business
    dated_body = "品牌方公布日程：2026年10月12日；另有无效日期：2026年2月30日。"
    dated_report, _ = add_material(ws, "analysis-calendar-cn", dated_body)
    dated_source_id = dated_report["source_brief"]["records"][0]["source_id"]
    dated = _prepare_derived(
        ws,
        "prepare-derived-calendar-cn",
        "请核验活动日期",
        source_job_id=dated_report["job_id"],
    )
    dated_analysis = dated["domain_analysis"]
    dated_check = next(
        item for item in dated_analysis["source_checks"] if item["source_id"] == dated_source_id
    )
    expected_start = dated_body.index("2026年10月12日")
    assert dated_check["source_reported_dates"] == [{
        "date": "2026-10-12",
        "start": expected_start,
        "end": expected_start + len("2026年10月12日"),
    }]
    assert dated_check["state"] == "SOURCE_USE_VERIFIED"
    assert dated_check["binding"]["source_id"] == dated_source_id
    assert dated_check["selection"]["start"] <= expected_start
    assert dated_check["selection"]["end"] >= expected_start + len("2026年10月12日")
    assert dated_body[expected_start:expected_start + len("2026年10月12日")] == "2026年10月12日"
    assert dated_check["date_interpretation"] == "SOURCE_REPORTED_MENTION_NOT_CONFIRMED_EVENT"
    assert dated_analysis["question_result"]["findings"]["reported_dates"] == [{
        "source_id": dated_source_id,
        "date": "2026-10-12",
        "start": expected_start,
        "end": expected_start + len("2026年10月12日"),
    }]
    calendar_option = next(option for option in dated["options"] if option["option_id"] == "calendar-review")
    assert calendar_option["source_ids"] == [dated_source_id]
    assert "2026-02-30" not in {
        mention["date"] for mention in dated_analysis["question_result"]["findings"]["reported_dates"]
    }

    no_date_body = "本材料描述品牌背景和门店服务，没有列出活动的年月日。"
    no_date_report, _ = add_material(ws, "analysis-calendar-gap", no_date_body)
    no_date_source_id = no_date_report["source_brief"]["records"][0]["source_id"]
    no_date = _prepare_derived(
        ws,
        "prepare-derived-calendar-gap",
        "请核验活动日期",
        source_job_id=no_date_report["job_id"],
    )
    no_date_analysis = no_date["domain_analysis"]
    no_date_check = next(
        item for item in no_date_analysis["source_checks"] if item["source_id"] == no_date_source_id
    )
    assert no_date_check["source_reported_dates"] == []
    assert no_date_analysis["judgment"]["date_confirmation"] == "NOT_FOUND_IN_ANALYZED_WINDOWS"
    assert no_date_analysis["question_result"]["findings"]["reported_dates"] == []
    gap_option = next(option for option in no_date["options"] if option["option_id"] == "calendar-review")
    assert gap_option["source_ids"] == [no_date_source_id]
    assert gap_option["proposal"] == "核对当前材料未提供的活动日期"


@pytest.mark.parametrize(
    ("question", "expected_option_id", "source_review_is_positive"),
    [
        ("不要整理来源，请预测销量", None, False),
        ("根据来源预测销量", "source-review", True),
        ("source review", "source-review", True),
    ],
)
def test_research_intent_requires_supported_positive_question(
    business, question, expected_option_id, source_review_is_positive,
):
    ws = business
    prepared = _prepare_derived(ws, "prepare-intent-question", question)
    goals = {item["goal"] for item in prepared["domain_analysis"]["question_result"]["goal_matches"]}
    assert ("SOURCE_REVIEW" in goals) is source_review_is_positive
    if expected_option_id is None:
        assert prepared["state"] == "NOT_READY"
        assert prepared["options"] == []
        assert prepared["decision"] is None
        assert prepared["domain_analysis"]["state"] == "NOT_READY"
        assert prepared["domain_analysis"]["question_result"]["state"] == "NOT_READY"
        assert prepared["domain_analysis"]["question_result"]["reason"] == "BUSINESS_QUESTION_METHOD_UNSUPPORTED"
        with pytest.raises(ValueError, match="BUSINESS_WORK_DECISION_INVALID"):
            ws["service"].advance(
                prepared["work_id"],
                actor_ref=ws["actor_ref"],
                scope=ws["domain_scope"],
                authorize=ws["authorize"],
                expected_revision=prepared["revision"],
                submission_id="choose-unsupported-intent",
                operation="choose",
                payload=selection("source-review", "100"),
            )
        ws["current"] = prepared
        with pytest.raises(RuntimeError, match="BUSINESS_WORK_SAVE_DECISION_REQUIRED"):
            save(ws, request_id="save-unsupported-intent")
        return

    assert prepared["state"] == "PREPARED"
    assert [option["option_id"] for option in prepared["options"]] == [expected_option_id]
    assert prepared["options"][0]["claim_type"] == "SYSTEM_DERIVED_RECOMMENDATION"
    assert prepared["domain_analysis"]["question_result"]["state"] == "RESEARCH_ACTIONS_PROPOSED"
    if question == "根据来源预测销量":
        report = prepared["domain_analysis"]["question_result"]["business_report"]
        unsupported = next(answer for answer in report["answers"] if answer["goal"] == "BUSINESS_RESULT")
        assert report["state"] == "PARTIAL"
        assert unsupported["state"] == "UNAVAILABLE"
        assert "销量" in unsupported["summary"]
        assert unsupported["limitations"] and unsupported["next_action"]


def test_v3_mixed_supported_and_unavailable_goals_save_a_useful_report(business):
    ws = business
    sources = _two_source_report(ws, "v3-mixed-goals")
    domain = ws["domain_scope"]["domain_id"]
    roles = (("VENUE_OPERATOR_DISCLOSURE", "CONSUMER_FEEDBACK") if domain == "cth" else
             ("OFFICIAL_BRAND_SELF_DESCRIPTION", "MARKET_DISCLOSURE"))
    _set_signed_source_role_annotation(ws, sources["first_source"], roles[0])
    _set_signed_source_role_annotation(ws, sources["second_source"], roles[1])
    _set_canonical_analysis_fields(
        ws, sources["first_source"], engagement_likes=8, engagement_comments=None,
        engagement_collects=0, engagement_shares=1,
    )
    # The second source remains genuinely unobserved in all four counters.
    _set_canonical_analysis_fields(
        ws, sources["second_source"], engagement_likes=None, engagement_comments=None,
        engagement_collects=None, engagement_shares=None,
    )

    prepared = _prepare_derived(
        ws, "prepare-v3-mixed-goals", "请整理来源并核对互动，然后预测销量",
        source_job_id=sources["report"]["job_id"],
    )
    analysis = prepared["domain_analysis"]
    assert analysis["version"] == "cth-bmp-domain-analysis/3"
    assert prepared["state"] == "PREPARED"
    result = analysis["question_result"]
    assert result["state"] == "RESEARCH_ACTIONS_PROPOSED"
    answers = {item["goal"]: item for item in result["business_report"]["answers"]}
    assert result["business_report"]["state"] == "PARTIAL"
    assert answers["SOURCE_REVIEW"]["state"] == "AVAILABLE"
    assert set(answers["SOURCE_REVIEW"]["source_ids"]) == set(sources["source_ids"])
    assert answers["INTERACTION_REVIEW"]["state"] == "PARTIAL"
    assert answers["BUSINESS_RESULT"]["state"] == "UNAVAILABLE"
    assert answers["BUSINESS_RESULT"]["source_ids"] == []
    assert all(item["summary"] and item["limitations"] and item["next_action"]
               for item in answers.values())
    assert result["unsupported_requests"]
    assert analysis["judgment"]["business_outcome"] == "NOT_OBSERVED"

    chosen = ws["service"].advance(
        prepared["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], expected_revision=prepared["revision"],
        submission_id="choose-v3-mixed-source-review", operation="choose",
        payload=selection("source-review", "100"),
    )
    ws["current"] = chosen
    saved = save(
        ws, request_id="save-v3-mixed-report",
        citations=[sources["first_citation"], sources["second_citation"]],
    )["saved_work"]
    saved_analysis = saved["document"]["payload"]["business_work"]["domain_analysis"]
    assert saved_analysis == saved["document"]["payload"]["brief"]["domain_analysis"]
    assert saved_analysis["question_result"]["business_report"] == result["business_report"]
    reopened = ws["work"].reopen_work(
        saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
    )["document"]
    assert reopened == saved["document"]


def test_v3_canonical_inputs_use_platform_cohorts_and_known_null_denominators(business):
    ws = business
    sources = _two_source_report(ws, "v3-cohort-metrics")
    third_report, _third_citation = add_material(
        ws, "analysis-v3-third", "A separately scoped platform statement; outcomes unknown.",
    )
    third_source = third_report["source_brief"]["records"][0]["source_id"]
    all_source_ids = [sources["first_source"], sources["second_source"], third_source]
    report = _source_report(ws, all_source_ids, "v3-cohort-metrics-all")
    _set_canonical_analysis_fields(
        ws, sources["first_source"], source_platform="fixture_platform_alpha",
        sentiment="negative", risk_level="high", engagement_likes=7,
        engagement_comments=None, engagement_collects=0, engagement_shares=2,
    )
    _set_canonical_analysis_fields(
        ws, sources["second_source"], source_platform="fixture_platform_alpha",
        sentiment=None, risk_level=None, engagement_likes=None,
        engagement_comments=None, engagement_collects=None, engagement_shares=None,
    )
    _set_canonical_analysis_fields(
        ws, third_source, source_platform="fixture_platform_beta",
        sentiment="positive", risk_level="low", engagement_likes=0,
        engagement_comments=0, engagement_collects=0, engagement_shares=0,
    )

    prepared = _prepare_derived(
        ws, "prepare-v3-cohort-metrics", "请整理来源并核对互动、情感与风险标签及品牌比较",
        source_job_id=report["job_id"],
    )
    analysis = prepared["domain_analysis"]
    assert analysis["version"] == "cth-bmp-domain-analysis/3"
    business_report = analysis["question_result"]["business_report"]
    actual_inputs = {item["source_id"]: item for item in business_report["canonical_inputs"]}
    assert set(actual_inputs) == set(all_source_ids)
    for source_id in all_source_ids:
        assert actual_inputs[source_id] == _canonical_analysis_input(ws, source_id)
    cohorts = {item["source_platform"]: item for item in business_report["cohorts"]}
    assert set(cohorts) == {"fixture_platform_alpha", "fixture_platform_beta"}

    alpha = cohorts["fixture_platform_alpha"]
    assert alpha["source_ids"] == sorted(all_source_ids[:2])
    assert alpha["source_count"] == 2
    assert alpha["engagement"]["sum"] is None
    assert alpha["engagement"]["observed_sum"] == 9
    assert alpha["engagement"]["quality"]["state"] == "PARTIAL"
    assert alpha["engagement"]["quality"]["known_field_count"] == 3
    assert alpha["engagement"]["quality"]["expected_field_count"] == 8
    assert alpha["sentiment"]["negative"] == 1
    assert alpha["sentiment"]["unknown"] == 1
    assert alpha["sentiment"]["known"] == 1
    assert alpha["negative_label_ratio"] == 1.0
    assert alpha["risk"]["high"] == 1 and alpha["risk"]["missing"] == 1

    beta = cohorts["fixture_platform_beta"]
    assert beta["source_ids"] == [third_source]
    assert beta["engagement"]["quality"]["state"] == "COMPLETE"
    assert beta["engagement"]["quality"]["known_field_count"] == 4
    assert beta["engagement"]["sum"] == 0
    assert beta["sentiment"]["positive"] == 1
    assert beta["negative_label_ratio"] == 0.0
    assert beta["risk"]["low"] == 1

    assert all(item["label_interpretation"] == "STORED_ANNOTATIONS_NOT_OBSERVED_CONSUMER_FACTS"
               for item in cohorts.values())
    assert all(item["comparison_state"] == "SAMPLE_FRAME_AND_METRIC_OBSERVATION_TIME_NOT_ESTABLISHED"
               for item in cohorts.values())
    assert analysis["material_review"]["consumer_conclusion"] == "NOT_ESTABLISHED"
    assert any("不跨组排名" in item for item in business_report["limitations"])
    assert any("不比较增长" in item for item in business_report["next_actions"])


def test_v3_publication_period_and_role_annotations_do_not_assert_consumer_facts(business):
    ws = business
    sources = _two_source_report(ws, "v3-publication-period")
    domain = ws["domain_scope"]["domain_id"]
    self_role = "VENUE_OPERATOR_DISCLOSURE" if domain == "cth" else "OFFICIAL_BRAND_SELF_DESCRIPTION"
    first_source, second_source = sources["first_source"], sources["second_source"]
    _set_signed_source_role_annotation(ws, first_source, self_role)
    _set_signed_source_role_annotation(ws, second_source, self_role)
    _set_canonical_analysis_fields(
        ws, first_source, source_platform="fixture_platform_time",
        publish_datetime="2026-10-01T04:00:00Z", captured_at="2026-10-04T12:00:00+08:00",
        sentiment="negative", risk_level="high", engagement_likes=4,
        engagement_comments=1, engagement_collects=0, engagement_shares=2,
    )
    _set_canonical_analysis_fields(
        ws, second_source, source_platform="fixture_platform_time",
        publish_datetime="2026-09-30T15:59:59Z", captured_at="2026-10-01T12:00:00+08:00",
        sentiment="negative", risk_level="high", engagement_likes=4,
        engagement_comments=1, engagement_collects=0, engagement_shares=2,
    )
    planning = {"time_range": {"start": "2026-10-01T00:00:00+08:00",
                               "end": "2026-10-01T23:59:59+08:00"}}
    prepared = _prepare_derived(
        ws, "prepare-v3-publication-period", "请核对品牌情感反馈和活动期间互动",
        source_job_id=sources["report"]["job_id"], planning_constraints=planning,
    )
    analysis = prepared["domain_analysis"]
    report = analysis["question_result"]["business_report"]
    assert analysis["version"] == "cth-bmp-domain-analysis/3"
    assert report["period"]["basis"] == "NATIVE_PUBLICATION_COHORT_NOT_INTERACTION_OBSERVATION"
    assert report["period"]["time_range"] == planning["time_range"]
    assert report["period"]["included_source_ids"] == [first_source]
    assert report["period"]["excluded"] == [{
        "source_id": second_source, "reason": "OUTSIDE_PUBLICATION_PERIOD",
    }]
    assert len(report["cohorts"]) == 1
    assert report["cohorts"][0]["source_ids"] == [first_source]
    assert {item["source_id"] for item in report["canonical_inputs"]} == {first_source, second_source}
    material = {item["source_id"]: item for item in analysis["material_review"]["sources"]}
    assert material[first_source]["declared_role"] == self_role
    assert material[first_source]["role_status"] == "CAPTURE_ANNOTATION_ONLY"
    assert material[second_source]["declared_role"] == self_role
    assert material[second_source]["role_status"] == "CAPTURE_ANNOTATION_ONLY"
    feedback_check = next(item for item in analysis["material_review"]["checks"]
                          if item["required_role"] == "CONSUMER_FEEDBACK")
    assert feedback_check["state"] == "MISSING_MATERIAL"
    assert feedback_check["source_ids"] == []
    assert analysis["material_review"]["consumer_conclusion"] == "NOT_ESTABLISHED"
    label_answer = next(item for item in report["answers"] if item["goal"] == "LABEL_REVIEW")
    assert label_answer["state"] == "PARTIAL"
    assert label_answer["source_ids"] == [first_source]
    assert "不能作为已核实消费者情绪" in "；".join(label_answer["limitations"])
    assert any("采集时间不替代发布时间" in item for item in report["limitations"])
    assert any("当前互动不代表期间内发生" in item for item in report["limitations"])


def test_v3_canonical_snapshot_requires_adoption_and_v1_v2_saved_versions_reopen(business, monkeypatch):
    ws = business
    service = ws["service"]
    initial_v1 = ws["current"]
    assert initial_v1["domain_analysis"]["version"] == "cth-bmp-domain-analysis/1"
    saved_v1 = save(ws, request_id="save-v1-compatibility")["saved_work"]
    assert saved_v1["document"]["payload"]["business_work"]["domain_analysis"] == initial_v1["domain_analysis"]
    assert ws["work"].reopen_work(
        saved_v1["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
    )["document"] == saved_v1["document"]

    def legacy_v2_analysis(connection, analysis, selected_sources, planning, manual):
        return service._question_analysis(analysis, selected_sources, planning, manual)

    with monkeypatch.context() as scoped:
        scoped.setattr(service, "_business_question_analysis", legacy_v2_analysis)
        prepared_v2 = _prepare_derived(ws, "prepare-v2-history", "source review")
    assert prepared_v2["domain_analysis"]["version"] == "cth-bmp-domain-analysis/2"
    chosen_v2 = service.advance(
        prepared_v2["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], expected_revision=prepared_v2["revision"],
        submission_id="choose-v2-history", operation="choose",
        payload=selection("source-review", "100"),
    )
    ws["current"] = chosen_v2
    saved_v2 = save(ws, request_id="save-v2-compatibility")["saved_work"]
    v2_analysis = chosen_v2["domain_analysis"]
    assert "business_report" not in v2_analysis["question_result"]
    assert saved_v2["document"]["payload"]["business_work"]["domain_analysis"] == v2_analysis
    assert ws["work"].reopen_work(
        saved_v2["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
    )["document"] == saved_v2["document"]
    reopened_v2 = service.reopen(
        chosen_v2["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], revision=chosen_v2["revision"],
    )
    assert reopened_v2["domain_analysis"] == v2_analysis
    assert "analysis_input_status" not in reopened_v2

    source_id = ws["current"]["source_brief"]["records"][0]["source_id"]
    _set_canonical_analysis_fields(
        ws, source_id, source_platform="fixture_snapshot_platform", sentiment="neutral",
        risk_level="low", publish_datetime="2026-10-01T04:00:00Z",
        captured_at="2026-10-01T12:00:00Z", engagement_likes=3, engagement_comments=1,
        engagement_collects=0, engagement_shares=0,
    )
    budget = "9" * 40
    estimate = "1" * 40
    planning = {"resource_constraints": {
        "budget_amount": budget, "estimated_cost_amount": estimate, "currency": "CNY",
        "as_of": "2026-10-01T00:00:00+08:00", "limits": ["Fixture constraint; no purchase or execution."],
    }}
    prepared_v3 = _prepare_derived(
        ws, "prepare-v3-immutable-snapshot", "source review and interaction check; forecast sales",
        planning_constraints=planning,
    )
    assert prepared_v3["domain_analysis"]["version"] == "cth-bmp-domain-analysis/3"
    old_analysis = prepared_v3["domain_analysis"]
    old_input = next(item for item in old_analysis["question_result"]["business_report"]["canonical_inputs"]
                     if item["source_id"] == source_id)
    assert old_input["engagement_likes"] == 3
    assert old_analysis["question_result"]["business_report"]["resource_assessment"][
        "budget_remaining_amount"
    ] == "8" * 40
    chosen_v3 = service.advance(
        prepared_v3["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], expected_revision=prepared_v3["revision"],
        submission_id="choose-v3-immutable-snapshot", operation="choose",
        payload=selection("source-review", "100"),
    )
    ws["current"] = chosen_v3
    saved_v3 = save(ws, request_id="save-v3-immutable-snapshot")["saved_work"]
    original_document = saved_v3["document"]

    _set_canonical_analysis_fields(ws, source_id, engagement_likes=9, sentiment="negative")
    reopened_v3 = service.reopen(
        chosen_v3["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], revision=chosen_v3["revision"],
    )
    assert reopened_v3["analysis_input_status"] == {
        "state": "CURRENT_INPUTS_CHANGED", "affected_source_ids": [source_id],
        "snapshot_immutable": True, "adoption_required": True,
    }
    assert reopened_v3["domain_analysis"] == old_analysis
    assert reopened_v3["domain_analysis"]["question_result"]["business_report"]["canonical_inputs"]
    assert ws["work"].reopen_work(
        saved_v3["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
    )["document"] == original_document

    report = _current_report(ws)
    adopted = adopt(ws, report["snapshot"], None, None, request_id="explicit-v3-input-adoption")
    new_analysis = adopted["domain_analysis"]
    new_input = next(item for item in new_analysis["question_result"]["business_report"]["canonical_inputs"]
                     if item["source_id"] == source_id)
    assert new_input["engagement_likes"] == 9
    assert new_input["sentiment"] == "negative"
    assert new_analysis["content_sha256"] != old_analysis["content_sha256"]
    assert new_analysis["question_result"]["business_report"]["resource_assessment"][
        "budget_remaining_amount"
    ] == "8" * 40
    assert old_input["engagement_likes"] == 3
    assert saved_v3["document"] == original_document


def test_all_source_use_unavailable_prevents_derived_options_and_save(business, monkeypatch):
    ws = business
    withdrawn = _revocable_source_reference(ws, monkeypatch, "no-derived-source")
    source_id = withdrawn["source_id"]
    report = _source_report(ws, [source_id], "no-derived-source")
    approved_source._revoke_current_source_rights(ws, withdrawn)

    prepared = _prepare_derived(
        ws,
        "prepare-no-derived-source",
        "请核验活动日期",
        source_job_id=report["job_id"],
    )
    assert prepared["state"] == "NOT_READY"
    assert prepared["options"] == []
    assert prepared["decision"] is None
    assert len(prepared["domain_analysis"]["source_checks"]) == 1
    unavailable = prepared["domain_analysis"]["source_checks"][0]
    assert unavailable["source_id"] == source_id
    assert unavailable["state"] == "UNAVAILABLE"
    assert isinstance(unavailable["reason"], str) and unavailable["reason"]
    assert prepared["domain_analysis"]["question_result"]["reason"] == "NO_AUTHORIZED_ANALYSIS_SOURCE"
    with pytest.raises(ValueError, match="BUSINESS_WORK_DECISION_INVALID"):
        ws["service"].advance(
            prepared["work_id"],
            actor_ref=ws["actor_ref"],
            scope=ws["domain_scope"],
            authorize=ws["authorize"],
            expected_revision=prepared["revision"],
            submission_id="choose-no-derived-source",
            operation="choose",
            payload=selection("calendar-review", "100"),
        )
    ws["current"] = prepared
    with pytest.raises(RuntimeError, match="BUSINESS_WORK_SAVE_DECISION_REQUIRED"):
        save(ws, request_id="save-no-derived-source")


def test_manual_options_with_planning_cannot_use_withdrawn_source_and_remain_in_signed_intent(business, monkeypatch):
    ws = business
    withdrawn = _revocable_source_reference(ws, monkeypatch, "manual-planning-unavailable")
    source_id = withdrawn["source_id"]
    report = _source_report(ws, [source_id], "manual-planning-unavailable")
    approved_source._revoke_current_source_rights(ws, withdrawn)
    options = make_options(source_id)
    planning = {
        "time_range": {
            "start": "2026-10-01T00:00:00+08:00",
            "end": "2026-10-31T23:59:59+08:00",
        },
        "resource_constraints": copy.deepcopy(selection("A", "100")["resource_constraints"]),
    }
    prepared = ws["service"].prepare(
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        submission_id="prepare-manual-withdrawn-source",
        source_job_id=report["job_id"],
        kind=ws["current"]["kind"],
        question="source review",
        options=options,
        planning_constraints=planning,
        authorize=ws["authorize"],
    )
    assert prepared["state"] == "NOT_READY"
    assert prepared["options"] == []
    assert prepared["decision"] is None
    analysis = prepared["domain_analysis"]
    assert analysis["question_result"]["state"] == "NOT_READY"
    assert analysis["question_result"]["reason"] == "OPERATOR_PROPOSAL_SOURCE_USE_UNAVAILABLE"
    assert analysis["source_checks"] == [{
        "source_id": source_id,
        "state": "UNAVAILABLE",
        "reason": analysis["source_checks"][0]["reason"],
    }]
    with ws["repo"].connection(read_only=True, wal=False) as connection:
        signed_inputs = connection.execute(
            "SELECT inputs_json FROM app_evidence_records WHERE feature_id=? AND asset_id=? ORDER BY id LIMIT 1",
            (ws["service"].FEATURE, prepared["work_id"]),
        ).fetchone()["inputs_json"]
    import json
    signed_payload = json.loads(signed_inputs)["payload"]
    assert signed_payload["options"] == options
    assert signed_payload["planning_constraints"] == planning


def test_prepare_replay_and_conflicting_question_or_constraints(business):
    ws = business
    question = "source review"
    first = _prepare_derived(ws, "prepare-replay-question", question)
    replay = _prepare_derived(ws, "prepare-replay-question", question)
    assert replay["revision"] == first["revision"]
    assert replay["options"] == first["options"]
    assert replay["domain_analysis"]["question_result"]["basis_sha256"] == first["domain_analysis"]["question_result"]["basis_sha256"]
    with pytest.raises(ValueError, match="BUSINESS_WORK_SUBMISSION_CONFLICT"):
        _prepare_derived(ws, "prepare-replay-question", "calendar review")

    constraints = {
        "time_range": {
            "start": "2026-10-01T00:00:00+08:00",
            "end": "2026-10-31T23:59:59+08:00",
        },
        "resource_constraints": copy.deepcopy(selection("A", "100")["resource_constraints"]),
    }
    planned = _prepare_derived(
        ws,
        "prepare-replay-planning",
        question,
        planning_constraints=constraints,
    )
    with pytest.raises(ValueError, match="BUSINESS_WORK_SUBMISSION_CONFLICT"):
        _prepare_derived(
            ws,
            "prepare-replay-planning",
            question,
            planning_constraints={**constraints, "time_range": {
                "start": "2026-10-02T00:00:00+08:00",
                "end": "2026-10-31T23:59:59+08:00",
            }},
        )
    assert planned["domain_analysis"]["question_result"]["planning_constraints"]["time_range"] == constraints["time_range"]


def test_planning_constraints_bind_candidates_and_adopt_clears_choice_without_rewriting_history(business):
    ws = business
    planning = {
        "time_range": {
            "start": "2026-10-01T00:00:00+08:00",
            "end": "2026-10-31T23:59:59+08:00",
        },
        "resource_constraints": copy.deepcopy(selection("A", "100")["resource_constraints"]),
    }
    prepared = _prepare_derived(
        ws,
        "prepare-planning-bound-candidates",
        "source review",
        planning_constraints=planning,
    )
    before_result = prepared["domain_analysis"]["question_result"]
    option = prepared["options"][0]
    assert before_result["planning_constraints"]["time_range"] == planning["time_range"]
    assert before_result["planning_constraints"]["resource_constraints"]["budget_amount"] == "100"
    assert option["basis_sha256"] == before_result["basis_sha256"]
    assert option["source_ids"] == before_result["verified_source_ids"]
    assert option["cost_estimate"] is None
    assert option["budget_fit"] == "UNKNOWN"

    chosen = ws["service"].advance(
        prepared["work_id"],
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        authorize=ws["authorize"],
        expected_revision=prepared["revision"],
        submission_id="choose-planning-budget",
        operation="choose",
        payload=selection("source-review", "30"),
    )
    assert chosen["options"] == prepared["options"]
    assert chosen["domain_analysis"]["question_result"] == before_result
    assert chosen["domain_analysis"]["resource_assessment"]["budget_remaining_amount"] == "-20"
    prior_revision = chosen["revision"]
    prior_analysis = copy.deepcopy(chosen["domain_analysis"])
    ws["current"] = chosen
    adopted = ws["service"].advance(
        chosen["work_id"],
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        authorize=ws["authorize"],
        expected_revision=chosen["revision"],
        submission_id="adopt-clear-derived-choice",
        operation="adopt",
        payload={
            "source_job_id": chosen["source_report"]["job_id"],
            "question": chosen["question"],
            "options": None,
            "decision": None,
            "reason": "Explicitly remove the selected resource plan.",
        },
    )
    assert adopted["state"] == "PREPARED"
    assert adopted["decision"] is None
    assert adopted["domain_analysis"]["resource_assessment"] is None
    assert adopted["domain_analysis"]["question_result"]["planning_constraints"] == before_result["planning_constraints"]
    assert adopted["domain_analysis"]["question_result"]["basis_sha256"] == before_result["basis_sha256"]

    changed_planning = {
        **planning,
        "time_range": {
            "start": "2026-10-02T00:00:00+08:00",
            "end": "2026-10-31T23:59:59+08:00",
        },
    }
    changed = ws["service"].advance(
        adopted["work_id"],
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        authorize=ws["authorize"],
        expected_revision=adopted["revision"],
        submission_id="adopt-changed-planning-period",
        operation="adopt",
        payload={
            "source_job_id": adopted["source_report"]["job_id"],
            "question": adopted["question"],
            "options": None,
            "decision": None,
            "reason": "Explicitly revise the research period.",
            "planning_constraints": changed_planning,
        },
    )
    assert changed["domain_analysis"]["question_result"]["planning_constraints"]["time_range"] == changed_planning["time_range"]
    assert changed["domain_analysis"]["question_result"]["basis_sha256"] != before_result["basis_sha256"]
    assert changed["options"][0]["basis_sha256"] == changed["domain_analysis"]["question_result"]["basis_sha256"]

    old_version = ws["service"].reopen(
        chosen["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], revision=prior_revision,
    )
    assert old_version["revision"] == prior_revision
    assert old_version["decision"] == chosen["decision"]
    assert old_version["domain_analysis"] == prior_analysis


def test_cth_case_subset_stays_source_bound_through_same_report_adopt_and_saved_work(business, monkeypatch):
    ws = business
    if ws["domain_scope"]["domain_id"] != "cth":
        pytest.skip("Case continuation is CTH-owned")

    first_source = ws["current"]["source_brief"]["records"][0]["source_id"]
    withdrawn = _revocable_source_reference(ws, monkeypatch, "case-subset")
    second_source = withdrawn["source_id"]
    report = _source_report(ws, [first_source, second_source], "case-subset")
    assert {item["source_id"] for item in report["source_brief"]["records"]} == {
        first_source, second_source,
    }

    import cth_cases
    from lumenis.shared.database.cth_cases import ensure_cth_case_schema

    monkeypatch.setattr(cth_cases, "get_repository", lambda: ws["repo"])
    with ws["repo"].transaction() as connection:
        ensure_cth_case_schema(connection)

    def authorize_case():
        return {
            "permission_audit_ref": "isolated-case-permission",
            "operation_audit_ref": "isolated-case-operation",
        }

    case = cth_cases.create_cth_case(
        actor_ref=ws["actor_ref"],
        expected_scope=ws["domain_scope"],
        submission_id="analysis-case-subset",
        title="Review source-bounded venue materials",
        question="source review",
        source_job_id=report["job_id"],
        source_ids=[first_source],
        authorize=authorize_case,
    )
    assert [item["source_id"] for item in case["source_refs"]] == [first_source]
    approved_source._revoke_current_source_rights(ws, withdrawn)

    from lumenis.shared.reporting import operational_brief

    real_builder = operational_brief.build_scoped_source_brief
    question_windows = []

    def spy_builder(connection, **kwargs):
        if kwargs.get("include_analysis_text") is True:
            question_windows.append(list(kwargs.get("source_ids") or []))
        return real_builder(connection, **kwargs)

    monkeypatch.setattr(operational_brief, "build_scoped_source_brief", spy_builder)
    planning = {
        "time_range": {
            "start": "2026-10-01T00:00:00+08:00",
            "end": "2026-10-31T23:59:59+08:00",
        },
        "resource_constraints": copy.deepcopy(selection("A", "100")["resource_constraints"]),
    }
    prepared = ws["service"].prepare_from_case(
        case["case_id"],
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        submission_id="prepare-case-analysis-subset",
        kind="venue_operations",
        planning_constraints=planning,
        authorize=ws["authorize"],
    )
    assert prepared["case_id"] == case["case_id"]
    assert [option["option_id"] for option in prepared["options"]] == ["source-review"]
    assert prepared["options"][0]["source_ids"] == [first_source]
    assert {item["source_id"] for item in prepared["domain_analysis"]["source_checks"]} == {first_source}
    assert {item["source_id"] for item in prepared["domain_analysis"]["material_review"]["sources"]} == {first_source}

    chosen = ws["service"].advance(
        prepared["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], expected_revision=prepared["revision"],
        submission_id="choose-case-analysis-subset", operation="choose",
        payload=selection("source-review", "100"),
    )
    changed_planning = {
        **planning,
        "time_range": {
            "start": "2026-10-02T00:00:00+08:00",
            "end": "2026-10-31T23:59:59+08:00",
        },
    }
    adopted = ws["service"].advance(
        chosen["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], expected_revision=chosen["revision"],
        submission_id="adopt-case-analysis-subset", operation="adopt",
        payload={
            "source_job_id": report["job_id"],
            "question": "source review after focus confirmation",
            "options": None,
            "decision": None,
            "reason": "Keep the case's selected source while revising the question.",
            "planning_constraints": changed_planning,
        },
    )
    assert adopted["state"] == "PREPARED"
    assert adopted["decision"] is None
    reopened = ws["service"].reopen(
        adopted["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"],
    )
    assert {item["source_id"] for item in reopened["domain_analysis"]["source_checks"]} == {first_source}
    assert reopened["domain_analysis"]["question_result"]["selected_source_ids"] == [first_source]
    assert {item["source_id"] for item in reopened["domain_analysis"]["material_review"]["sources"]} == {first_source}
    assert question_windows
    assert all(source_ids == [first_source] for source_ids in question_windows)

    ws["current"] = ws["service"].advance(
        adopted["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], expected_revision=adopted["revision"],
        submission_id="choose-case-analysis-adopted", operation="choose",
        payload=selection("source-review", "100"),
    )
    saved = save(
        ws,
        request_id="save-case-analysis-adopted",
        citations=[ws["citation"]],
    )["saved_work"]
    payload = saved["document"]["payload"]
    assert payload["business_work"]["domain_analysis"] == payload["brief"]["domain_analysis"]
    assert {binding["source_id"] for binding in payload["business_work"]["source_bindings"]} == {first_source}


def _business_work_evidence_count(ws, work_id):
    with ws["repo"].connection(read_only=True, wal=False) as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id=? AND asset_id=?",
            (ws["service"].FEATURE, work_id),
        ).fetchone()[0]


def _saved_business_artifact_count(ws, work_id):
    return ws["repo"].query_one(
        "SELECT COUNT(*) FROM lumenis_shared_artifacts "
        "WHERE kind='saved_document' AND source_execution_id=?",
        (work_id,),
    )[0]


def _prepare_approved_source_for_outcome(ws, monkeypatch, suffix):
    from lumenis.importer import documents

    source = _revocable_source_reference(ws, monkeypatch, suffix)
    report = _source_report(ws, [source["source_id"]], suffix)
    resolved = approved_source._resolve(documents, ws, source)
    evidence_id = resolved["evidence_id"]
    assert len(source["body"]) >= 161

    def citation(start, end):
        return documents.locate_quote(
            evidence_id, actor=ws["actor"], scope=ws["scope"], start=start, end=end,
        )["citation"]

    outcome_citation = citation(0, 100)
    different_citation = citation(100, 140)
    aggregate_citation = citation(100, 161)
    assert different_citation["evidence_id"] == outcome_citation["evidence_id"]
    assert different_citation["quote"] != outcome_citation["quote"]
    assert len(outcome_citation["quote"]) + len(aggregate_citation["quote"]) == 161
    options = make_options(source["source_id"])
    prepared = ws["service"].prepare(
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        submission_id="prepare-source-outcome-" + suffix,
        source_job_id=report["job_id"],
        kind=ws["current"]["kind"],
        question=ws["current"]["question"],
        options=options,
        authorize=ws["authorize"],
    )
    chosen = ws["service"].advance(
        prepared["work_id"],
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        authorize=ws["authorize"],
        expected_revision=prepared["revision"],
        submission_id="choose-source-outcome-" + suffix,
        operation="choose",
        payload=selection("A", "100"),
    )
    ws.update(current=chosen, options=options, citation=outcome_citation)
    return source, report, chosen, outcome_citation, different_citation, aggregate_citation


def _prepare_revocable_source_analysis(ws, monkeypatch, suffix):
    source = _revocable_source_reference(ws, monkeypatch, suffix)
    report = _source_report(ws, [source["source_id"]], suffix)
    prepared = ws["service"].prepare(
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        submission_id="prepare-revocable-" + suffix,
        source_job_id=report["job_id"],
        kind=ws["current"]["kind"],
        question="source review",
        authorize=ws["authorize"],
    )
    assert prepared["state"] == "PREPARED"
    assert prepared["options"]
    check = prepared["domain_analysis"]["source_checks"]
    assert len(check) == 1 and check[0]["source_id"] == source["source_id"]
    assert check[0]["state"] == "SOURCE_USE_VERIFIED", check[0]
    return source, prepared


def test_withdrawn_analysis_source_blocks_choose_without_committing_revision(business, monkeypatch):
    ws = business
    source, prepared = _prepare_revocable_source_analysis(ws, monkeypatch, "choose-withdrawn")
    approved_source._revoke_current_source_rights(ws, source)

    evidence_count = _business_work_evidence_count(ws, prepared["work_id"])
    decision = selection(prepared["options"][0]["option_id"], "100")
    for _ in range(2):
        with pytest.raises(
            PermissionError,
            match="BUSINESS_WORK_ANALYSIS_SOURCE_USE_UNAVAILABLE",
        ):
            ws["service"].advance(
                prepared["work_id"],
                actor_ref=ws["actor_ref"],
                scope=ws["domain_scope"],
                authorize=ws["authorize"],
                expected_revision=prepared["revision"],
                submission_id="choose-withdrawn-analysis-source",
                operation="choose",
                payload=decision,
            )

    assert _business_work_evidence_count(ws, prepared["work_id"]) == evidence_count
    with ws["repo"].connection(read_only=True, wal=False) as connection:
        history = ws["service"]._history(
            connection, prepared["work_id"], ws["actor_ref"], ws["domain_scope"],
        )
    assert len(history) == 1
    assert history[-1]["outputs"]["state"] == "PREPARED"
    assert history[-1]["outputs"]["decision"] is None


def test_authorization_callback_withdrawal_rolls_back_the_decision(business, monkeypatch):
    import json
    from contextlib import contextmanager

    ws = business
    source, prepared = _prepare_revocable_source_analysis(ws, monkeypatch, "callback-withdrawal")
    original_rights = approved_source._source_rights(ws, source)
    original_transaction = ws["repo"].transaction
    active = {"connection": None, "revoked": False}

    @contextmanager
    def tracked_transaction(**kwargs):
        with original_transaction(**kwargs) as connection:
            previous = active["connection"]
            active["connection"] = connection
            try:
                yield connection
            finally:
                active["connection"] = previous

    monkeypatch.setattr(ws["repo"], "transaction", tracked_transaction)

    def authorize_with_withdrawal(operation):
        connection = active["connection"]
        if operation == "choose" and connection is not None and not active["revoked"]:
            if source["note_pk"] is not None:
                connection.execute(
                    f"UPDATE notes SET {source['rights_column']}='WITHDRAWN' WHERE id=?",
                    (source["note_pk"],),
                )
            else:
                row = connection.execute(
                    "SELECT collection_metadata FROM app_evidence_records WHERE id=?",
                    (source["content_evidence_id"],),
                ).fetchone()
                metadata = json.loads(row[0])
                metadata["provenance"]["rights"] = "WITHDRAWN"
                connection.execute(
                    "UPDATE app_evidence_records SET collection_metadata=? WHERE id=?",
                    (approved_source._json(metadata), source["content_evidence_id"]),
                )
                from lumenis.shared.evidence import store

                store._sign_evidence_record(connection, source["content_evidence_id"])
            active["revoked"] = True
        return ws["authorize"](operation)

    evidence_count = _business_work_evidence_count(ws, prepared["work_id"])
    with pytest.raises(
        PermissionError,
        match="BUSINESS_WORK_ANALYSIS_SOURCE_USE_UNAVAILABLE",
    ):
        ws["service"].advance(
            prepared["work_id"],
            actor_ref=ws["actor_ref"],
            scope=ws["domain_scope"],
            authorize=authorize_with_withdrawal,
            expected_revision=prepared["revision"],
            submission_id="choose-callback-withdrawal-analysis",
            operation="choose",
            payload=selection(prepared["options"][0]["option_id"], "100"),
        )

    assert active["revoked"] is True
    assert approved_source._source_rights(ws, source) == original_rights
    assert _business_work_evidence_count(ws, prepared["work_id"]) == evidence_count
    with ws["repo"].connection(read_only=True, wal=False) as connection:
        history = ws["service"]._history(
            connection, prepared["work_id"], ws["actor_ref"], ws["domain_scope"],
        )
    assert len(history) == 1
    assert history[-1]["outputs"]["state"] == "PREPARED"
    assert history[-1]["outputs"]["decision"] is None


@pytest.mark.parametrize("operation", ["cancel", "interrupt"])
def test_withdrawn_analysis_source_allows_redacted_idempotent_stop(business, monkeypatch, operation):
    ws = business
    suffix = "stop-" + operation + "-" + ws["domain_scope"]["domain_id"]
    source, prepared = _prepare_revocable_source_analysis(ws, monkeypatch, suffix)
    approved_source._revoke_current_source_rights(ws, source)

    submission_id = "stop-withdrawn-analysis-source"
    payload = {"reason": "Stop the source review."}
    stopped = ws["service"].advance(
        prepared["work_id"],
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        authorize=ws["authorize"],
        expected_revision=prepared["revision"],
        submission_id=submission_id,
        operation=operation,
        payload=payload,
    )
    evidence_count = _business_work_evidence_count(ws, prepared["work_id"])

    assert set(stopped) == {
        "work_id", "scope", "revision", "state", "options", "decision",
        "derived_content", "action_state", "business_outcome",
    }
    assert stopped["state"] == ("CANCELLED" if operation == "cancel" else "INTERRUPTED")
    assert stopped["options"] == []
    assert stopped["decision"] is None
    assert stopped["derived_content"] == "WITHHELD_SOURCE_USE_UNAVAILABLE"
    assert source["source_id"] not in repr(stopped)

    replay = ws["service"].advance(
        prepared["work_id"],
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        authorize=ws["authorize"],
        expected_revision=prepared["revision"],
        submission_id=submission_id,
        operation=operation,
        payload=payload,
    )
    assert replay == stopped
    assert _business_work_evidence_count(ws, prepared["work_id"]) == evidence_count


def test_approved_source_outcome_requires_matching_citation_and_shared_quote_budget(
        business, monkeypatch):
    from lumenis.importer.documents import SavedWorkError

    ws = business
    (source, report, chosen, outcome_citation, different_citation,
     aggregate_citation) = _prepare_approved_source_for_outcome(
         ws, monkeypatch, "outcome-save-" + ws["domain_scope"]["domain_id"],
     )
    work_id = chosen["work_id"]
    evidence_count = _business_work_evidence_count(ws, work_id)

    with pytest.raises(PermissionError, match="BUSINESS_WORK_OUTCOME_QUOTE_LIMIT"):
        ws["service"].advance(
            work_id,
            actor_ref=ws["actor_ref"],
            scope=ws["domain_scope"],
            authorize=ws["authorize"],
            expected_revision=chosen["revision"],
            submission_id="outcome-overlimit-" + ws["domain_scope"]["domain_id"],
            operation="outcome",
            payload={
                "source_job_id": report["job_id"],
                "source_id": source["source_id"],
                "quote": source["body"][:161],
                "limits": "No measured business effect or causation.",
            },
        )
    assert _business_work_evidence_count(ws, work_id) == evidence_count

    outcome = ws["service"].advance(
        work_id,
        actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"],
        authorize=ws["authorize"],
        expected_revision=chosen["revision"],
        submission_id="outcome-source-" + ws["domain_scope"]["domain_id"],
        operation="outcome",
        payload={
            "source_job_id": report["job_id"],
            "source_id": source["source_id"],
            "quote": outcome_citation["quote"],
            "limits": "No measured business effect or causation.",
        },
    )
    assert outcome["state"] == "OUTCOME_RECORDED"
    assert outcome["outcome"]["quote"] == outcome_citation["quote"]
    ws["current"] = outcome

    assert _saved_business_artifact_count(ws, work_id) == 0
    evidence_count = _business_work_evidence_count(ws, work_id)
    with pytest.raises(ValueError, match="BUSINESS_WORK_SAVE_OUTCOME_CITATION_MISSING"):
        save(
            ws,
            request_id="save-outcome-wrong-citation-" + ws["domain_scope"]["domain_id"],
            citations=[different_citation],
        )
    assert _saved_business_artifact_count(ws, work_id) == 0
    assert _business_work_evidence_count(ws, work_id) == evidence_count

    with pytest.raises(SavedWorkError, match="SOURCE_USE_QUOTE_LIMIT_EXCEEDED"):
        save(
            ws,
            request_id="save-outcome-shared-limit-" + ws["domain_scope"]["domain_id"],
            citations=[outcome_citation, aggregate_citation],
        )
    assert _saved_business_artifact_count(ws, work_id) == 0

    saved = save(
        ws,
        request_id="save-outcome-matching-citation-" + ws["domain_scope"]["domain_id"],
        citations=[outcome_citation],
    )["saved_work"]
    document = saved["document"]
    assert document["payload"]["business_work"]["outcome"]["quote"] == outcome_citation["quote"]
    assert document["citations"][0]["quote"] == outcome_citation["quote"]
    reopened = ws["work"].reopen_work(
        saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
    )["document"]
    assert reopened == document

