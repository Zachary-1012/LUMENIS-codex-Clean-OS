"""Direct C3 regressions for GLOBAL report envelopes over scoped sources."""

import pytest
from tests.test_business_result_continuity import add_material, make_options, save, selection

pytest_plugins = ("tests.test_business_result_continuity", "tests.test_saved_document_workflow")


def _focus_scope(domain_id, entity):
    return {
        "domain_id": "cth" if domain_id == "CTH" else "zbmp",
        "global_scope": False,
        "subject_id": entity.get("subject_id") if domain_id == "CTH" else None,
        "brand_focus_id": entity.get("brand_focus_id") if domain_id == "BMP" else None,
    }


def _add_second_focus(ws, domain_id):
    import subject_registry

    entity, created = subject_registry.add_subject({
        "domain_id": domain_id,
        "subject_type": "company" if domain_id == "CTH" else "brand",
        "name_en": "Second isolated business source",
        "name_zh": "第二个隔离业务来源",
    })
    assert created
    focus = {**ws, "scope": _focus_scope(domain_id, entity)}
    report, citation = add_material(
        focus, "second-global-source", "A second issuer statement; no consumer outcome is measured."
    )
    return entity, focus, report, citation


def _create_global_report(ws, product_id, source_ids, job_id):
    with ws["repo"].transaction() as connection:
        return ws["jobs"].create_source_brief_job(
            connection,
            product_id=product_id,
            global_scope=True,
            entity_label="GLOBAL / ALL",
            actor_id=ws["actor"].principal_ref,
            permission_audit_ref="isolated-global-report-read",
            trace_id="isolated-global-trace-" + job_id,
            job_id=job_id,
            source_ids=source_ids,
        )


def _global_authorizer(actor_ref, scope):
    def authorize(operation):
        return {
            "actor_id": actor_ref,
            "scope": scope,
            "operation": operation,
            "permission_audit_ref": "isolated-global-scope-audit",
            "operation_audit_ref": "isolated-global-operation-audit",
        }
    return authorize


def test_global_business_report_preserves_original_source_scopes_and_reopens(business):
    from api_dual_domain import BusinessDecisionWorkflow

    ws = business
    domain = "CTH" if ws["domain_scope"]["domain_id"] == "cth" else "BMP"
    first_source = ws["citation"]["source_id"]
    second_entity, _second_focus, second_report, second_citation = _add_second_focus(ws, domain)
    second_source = second_report["source_brief"]["records"][0]["source_id"]
    product_id = "CTH" if domain == "CTH" else "ZBMP"
    report = _create_global_report(
        ws, product_id, [first_source, second_source], "isolated-global-prepare-01"
    )

    envelope = report["source_brief"]["scope"]
    assert envelope["global"] is True
    assert envelope["product_id"] == product_id
    assert envelope["domain_id"] == ws["domain_scope"]["domain_id"]
    assert envelope["subject_id"] is None and envelope["brand_focus_id"] is None
    records = {item["source_id"]: item for item in report["source_brief"]["records"]}
    assert set(records) == {first_source, second_source}
    assert records[first_source]["subject_id"] == ws["scope"]["subject_id"]
    assert records[first_source]["brand_focus_id"] == ws["scope"]["brand_focus_id"]
    if domain == "CTH":
        assert records[second_source]["subject_id"] == second_entity["subject_id"]
        assert records[second_source]["brand_focus_id"] is None
    else:
        assert records[second_source]["brand_focus_id"] == second_entity["brand_focus_id"]
        assert records[second_source]["subject_id"] is None
    assert records[first_source]["scope_evidence_ref"]
    assert records[second_source]["scope_evidence_ref"]

    authorize = _global_authorizer(ws["actor"].principal_ref, envelope)
    service = BusinessDecisionWorkflow(action_actor=ws["actor"])
    prepared = service.prepare(
        actor_ref=ws["actor"].principal_ref,
        scope=envelope,
        submission_id="global-source-review-01",
        source_job_id=report["job_id"],
        kind="venue_operations" if domain == "CTH" else "brand_market",
        question="source review",
        options=make_options(first_source),
        authorize=authorize,
    )
    assert prepared["state"] == "PREPARED"
    analysis = prepared["domain_analysis"]
    assert analysis["scope"]["global"] is True
    checks = {item["source_id"]: item for item in analysis["source_checks"]}
    assert set(checks) == {first_source, second_source}
    assert all(item["state"] == "SOURCE_USE_VERIFIED" for item in checks.values())

    global_saved_scope = {
        "domain_id": envelope["domain_id"], "subject_id": None, "brand_focus_id": None,
        "global_scope": True,
    }
    ws.update({"scope": global_saved_scope, "domain_scope": envelope, "authorize": authorize,
               "service": service, "current": prepared, "actor_ref": ws["actor"].principal_ref,
               "citation": ws["citation"]})
    chosen = service.advance(
        prepared["work_id"], actor_ref=ws["actor"].principal_ref, scope=envelope,
        authorize=authorize, expected_revision=prepared["revision"],
        submission_id="global-source-review-choice-01", operation="choose",
        payload=selection("A", "100"),
    )
    ws["current"] = chosen
    saved = save(ws, request_id="global-source-review-save-01")["saved_work"]
    reopened = ws["work"].reopen_work(
        saved["artifact"]["artifact_id"], actor=ws["actor"], scope=global_saved_scope
    )
    assert reopened["document"] == saved["document"]
    assert reopened["document"]["citations"][0]["source_id"] == first_source
    assert second_citation["source_id"] == second_source


def test_global_report_reauthorizes_each_original_source_before_returning(business, monkeypatch):
    from lumenis.shared.reporting import saved_work

    ws = business
    domain = "CTH" if ws["domain_scope"]["domain_id"] == "cth" else "BMP"
    first_source = ws["citation"]["source_id"]
    _entity, _focus, second_report, _citation = _add_second_focus(ws, domain)
    second_source = second_report["source_brief"]["records"][0]["source_id"]
    report = _create_global_report(
        ws, "CTH" if domain == "CTH" else "ZBMP", [first_source, second_source],
        "isolated-global-denied-01",
    )
    service = ws["service"]
    original_authorize = saved_work.authorize
    observed_scopes = []

    def deny_second_source(actor, scope, *, action, connection=None):
        observed_scopes.append(dict(scope))
        if scope.get("subject_id") and scope.get("subject_id") != ws["scope"]["subject_id"]:
            raise PermissionError("ISOLATED_SECOND_SOURCE_SCOPE_DENIED")
        if scope.get("brand_focus_id") and scope.get("brand_focus_id") != ws["scope"]["brand_focus_id"]:
            raise PermissionError("ISOLATED_SECOND_SOURCE_SCOPE_DENIED")
        return original_authorize(actor, scope, action=action, connection=connection)

    monkeypatch.setattr(saved_work, "authorize", deny_second_source)
    before = ws["repo"].query_one("SELECT COUNT(*) FROM app_evidence_records")[0]
    with ws["repo"].connection(read_only=True, wal=False) as connection:
        with pytest.raises(PermissionError, match="ISOLATED_SECOND_SOURCE_SCOPE_DENIED"):
            service._report(connection, report["job_id"], ws["actor"].principal_ref,
                            report["source_brief"]["scope"])
    after = ws["repo"].query_one("SELECT COUNT(*) FROM app_evidence_records")[0]
    assert observed_scopes[0]["global_scope"] is True
    assert any(scope.get("subject_id") or scope.get("brand_focus_id") for scope in observed_scopes[1:])
    assert after == before


def test_global_report_rejects_selected_source_from_other_domain_before_report_write(business):
    import subject_registry

    ws = business
    current_domain = "CTH" if ws["domain_scope"]["domain_id"] == "cth" else "BMP"
    other_domain = "BMP" if current_domain == "CTH" else "CTH"
    entity, _created = subject_registry.add_subject({
        "domain_id": other_domain,
        "subject_type": "brand" if other_domain == "BMP" else "company",
        "name_en": "Wrong domain source",
        "name_zh": "错误领域来源",
    })
    other = {**ws, "scope": _focus_scope(other_domain, entity)}
    foreign_report, _citation = add_material(
        other, "wrong-domain-global-selection", "Source belongs to the other business domain."
    )
    foreign_source = foreign_report["source_brief"]["records"][0]["source_id"]
    before_reports = ws["repo"].query_one("SELECT COUNT(*) FROM daily_reports")[0]
    before_evidence = ws["repo"].query_one("SELECT COUNT(*) FROM app_evidence_records")[0]

    with pytest.raises((PermissionError, ValueError)):
        _create_global_report(
            ws, "CTH" if current_domain == "CTH" else "ZBMP", [foreign_source],
            "isolated-wrong-domain-global-01",
        )

    assert ws["repo"].query_one("SELECT COUNT(*) FROM daily_reports")[0] == before_reports
    assert ws["repo"].query_one("SELECT COUNT(*) FROM app_evidence_records")[0] == before_evidence
