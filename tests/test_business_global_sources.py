"""Existing GLOBAL report context keeps each real focus; isolated inputs, no live acquisition."""
import json
import socket
from types import SimpleNamespace

import pytest

from api_dual_domain import BusinessDecisionWorkflow, authorize_business_related_read
from tests.test_business_result_continuity import business as business, add_material
from tests.test_saved_document_workflow import workspace as workspace


@pytest.fixture
def global_context(business, monkeypatch):
    import subject_registry
    ws = business
    def no_network(*args, **kwargs):
        raise AssertionError("isolated domain source context must not access a network")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    cth = ws["scope"]["domain_id"] == "cth"
    other, _ = subject_registry.add_subject({"domain_id": "CTH" if cth else "BMP",
        "subject_type": "company" if cth else "brand", "name_en": "Another disclosed entity",
        "name_zh": "另一已披露主体"})
    other_scope = {"domain_id": ws["scope"]["domain_id"], "global_scope": False,
        "subject_id": other["subject_id"] if cth else None,
        "brand_focus_id": other["brand_focus_id"] if not cth else None}
    report, _ = add_material({**ws, "scope": other_scope}, "other-focus",
        "Separately scoped issuer statement. This is background and does not establish a relationship.")
    first = ws["options"][0]["source_ids"][0]
    second = report["source_brief"]["records"][0]["source_id"]
    with ws["repo"].transaction() as con:
        background = ws["jobs"].create_source_brief_job(con,
            product_id="CTH" if cth else "ZBMP", global_scope=True, subject_id=None,
            brand_focus_id=None, entity_label="All authorized sources", source_ids=[first, second],
            actor_id=ws["actor_ref"], permission_audit_ref="isolated-global-context",
            trace_id="global-context-trace", job_id="global-background-job")
    original = background["source_brief"]["scope"]
    descriptor = {"job_id": background["job_id"], "original_scope": original,
                  "purpose": "Read source scope and limits without transferring facts into this work."}
    def authorize_related(scope, operation):
        return authorize_business_related_read(ws["actor"], actor_ref=ws["actor_ref"],
                                               original_scope=scope, operation=operation)
    args = {"actor_ref": ws["actor_ref"], "scope": ws["domain_scope"], "authorize": ws["authorize"],
            "related_reports": [descriptor], "authorize_related": authorize_related}
    return ws, args, other_scope


def test_global_background_reads_every_original_focus_without_changing_the_work(global_context):
    ws, args, other_scope = global_context
    before = ws["repo"].query_one("SELECT COUNT(*) FROM app_evidence_records")[0]
    lens = ws["service"].focus_lens(ws["current"]["work_id"], **args)
    context = lens["related_context"][0]
    assert context["original_scope"]["global"] is True
    assert context["source_scope_policy"] == "EACH_ORIGINAL_FOCUS_REAUTHORIZED"
    assert context["source_brief"]["view_kind"] == "METADATA_INDEX_ONLY"
    assert context["interpretation"] == "BACKGROUND_ONLY_NOT_FOCUS_FACT_OR_CAUSATION"
    assert context["relationship_state"] == "OPERATOR_CONTEXT_REQUEST_NOT_VERIFIED_RELATION"
    records = context["source_brief"]["records"]
    key = "subject_id" if ws["scope"]["domain_id"] == "cth" else "brand_focus_id"
    assert {row[key] for row in records} == {ws["scope"][key], other_scope[key]}
    assert all("content" not in row and "profile_research" not in row for row in records)
    assert lens["focus_work"]["revision"] == ws["current"]["revision"]
    assert lens["truth_rewritten"] is False and lens["collection_triggered"] is False
    cold = BusinessDecisionWorkflow(action_actor=ws["actor"])
    assert cold.focus_lens(ws["current"]["work_id"], **args) == lens
    assert ws["repo"].query_one("SELECT COUNT(*) FROM app_evidence_records")[0] == before


@pytest.mark.parametrize("during_read", [False, True])
def test_global_permission_never_substitutes_for_a_current_source_focus_grant(
        global_context, monkeypatch, during_read):
    from lumenis.system.security import permission
    ws, args, other_scope = global_context
    checker = permission.check_local_workspace_scope_permission
    revoked = {"value": not during_read}
    def check(actor, **scope):
        if revoked["value"] and scope.get("subject_id") == other_scope["subject_id"] and scope.get("brand_focus_id") == other_scope["brand_focus_id"] and scope.get("global_scope") is False:
            return SimpleNamespace(allowed=False, verification_state="verified", audit_id="isolated-denial")
        return checker(actor, **scope)
    monkeypatch.setattr(permission, "check_local_workspace_scope_permission", check)
    owner = ws["service"]._report
    if during_read:
        def read_then_revoke(*args, **kwargs):
            value = owner(*args, **kwargs)
            if value["source_brief"]["scope"]["global"]:
                revoked["value"] = True
            return value
        monkeypatch.setattr(ws["service"], "_report", read_then_revoke)
    with pytest.raises(PermissionError):
        ws["service"].focus_lens(ws["current"]["work_id"], **args)
    revoked["value"] = False
    monkeypatch.setattr(ws["service"], "_report", owner)
    assert ws["service"].focus_lens(ws["current"]["work_id"], **args)["related_context"]


def test_global_resolution_does_not_promote_unassigned_or_hide_an_invalid_focus_proof(global_context):
    ws, args, _ = global_context
    source_id = ws["options"][0]["source_ids"][0]
    global_scope = args["related_reports"][0]["original_scope"]
    with ws["repo"].transaction() as con:
        before = dict(con.execute("SELECT * FROM canonical_data WHERE source_id=?", (source_id,)).fetchone())
        con.execute("UPDATE canonical_data SET scope_status='UNASSIGNED' WHERE source_id=?", (source_id,))
    with ws["repo"].connection(read_only=True) as con:
        with pytest.raises(PermissionError, match="BUSINESS_WORK_SOURCE_SCOPE_INVALID"):
            ws["service"]._canonical_source(con, source_id, global_scope)
    with ws["repo"].transaction() as con:
        con.execute("UPDATE canonical_data SET scope_status='VERIFIED',scope_evidence_ref='999999999' WHERE source_id=?", (source_id,))
    with ws["repo"].connection(read_only=True) as con:
        with pytest.raises((PermissionError, ValueError)):
            ws["service"]._canonical_source(con, source_id, global_scope)
    with ws["repo"].transaction() as con:
        con.execute("UPDATE canonical_data SET scope_evidence_ref=? WHERE source_id=?", (before["scope_evidence_ref"], source_id))
    assert ws["service"].focus_lens(ws["current"]["work_id"], **args)["related_context"]


def test_existing_product_get_resolves_scopes_on_the_server_and_recovers_after_revocation(
        global_context, monkeypatch):
    import lumenis_app_api
    from lumenis.system.security import permission
    ws, args, other_scope = global_context
    ws["app"].register_blueprint(lumenis_app_api.domain_api_bp)
    client = ws["app"].test_client()
    base = "/api/experience/business-works/" + ws["current"]["work_id"]
    cth = ws["scope"]["domain_id"] == "cth"
    headers = {"X-Domain-Id": "CTH" if cth else "BMP", "X-Lumenis-Context-Mode": "FOCUS"}
    headers["X-Subject-ID" if cth else "X-Brand-Focus-ID"] = ws["scope"]["subject_id" if cth else "brand_focus_id"]
    related = [{key: args["related_reports"][0][key] for key in ("job_id", "purpose")}]
    query = {"related_reports": json.dumps(related)}
    ordinary = client.get(base, headers=headers)
    assert ordinary.status_code == 200, ordinary.get_json()
    result = client.get(base, headers=headers, query_string=query)
    assert result.status_code == 200, result.get_json()
    assert result.headers["Cache-Control"] == "no-store"
    context = result.get_json()["result"]["related_context"][0]
    assert context["original_scope"] == args["related_reports"][0]["original_scope"]
    assert context["source_scope_policy"] == "EACH_ORIGINAL_FOCUS_REAUTHORIZED"
    assert result.get_json()["result"]["focus_work"]["revision"] == ordinary.get_json()["result"]["revision"]
    original = permission.check_local_workspace_scope_permission
    def deny(actor, **scope):
        if scope.get("subject_id") == other_scope["subject_id"] and scope.get("brand_focus_id") == other_scope["brand_focus_id"] and scope.get("global_scope") is False:
            return SimpleNamespace(allowed=False, verification_state="verified", audit_id="http-isolated-denial")
        return original(actor, **scope)
    monkeypatch.setattr(permission, "check_local_workspace_scope_permission", deny)
    rejected = client.get(base, headers=headers, query_string=query)
    assert rejected.status_code == 403 and "result" not in rejected.get_json()
    monkeypatch.setattr(permission, "check_local_workspace_scope_permission", original)
    recovered = client.get(base, headers=headers, query_string=query)
    assert recovered.status_code == 200
    assert recovered.get_json()["result"]["related_context"] == result.get_json()["result"]["related_context"]
    injected = [{**related[0], "original_scope": ws["domain_scope"]}]
    assert client.get(base, headers=headers, query_string={"related_reports": json.dumps(injected)}).status_code == 400
    assert client.get(base, headers=headers, query_string={"related_reports": '[{"job_id":"one","job_id":"two","purpose":"x"}]'}).status_code == 400
    historical = client.get(base, headers=headers, query_string={**query, "revision": ws["current"]["revision"]})
    assert historical.status_code == 200
    assert historical.get_json()["result"]["focus_work"]["revision"] == ws["current"]["revision"]


def test_related_read_uses_the_current_product_session_and_rejects_another_claimed_actor(workspace):
    import account.models
    from lumenis.auth.service import get_current_user
    from lumenis.shared.reporting.source_brief_job import _scope_material
    ws = workspace
    with ws["repo"].transaction() as con:
        con.executescript(account.models.BASE_TABLES_SQL)
        con.executemany("INSERT INTO v4_users(id,username,password_hash,role,status) VALUES (?,?,?,'owner','active')",
                        [(1, "reader-one", "not-a-password"), (2, "reader-two", "not-a-password")])
        con.execute("INSERT INTO v4_sessions(user_id,token,expires_at) VALUES (1,?,'2099-01-01 00:00:00')",
                    ("isolated-business-reader-session",))
    original = _scope_material(product_id="CTH", global_scope=True, entity_label="Authorized source range")
    headers = {"Authorization": "Bearer isolated-business-reader-session"}
    with ws["app"].test_request_context("/", headers=headers):
        actor = get_current_user(read_only=True)
        assert actor["id"] == 1
        decision = authorize_business_related_read(actor, actor_ref="actor:1", original_scope=original, operation="read")
        assert decision["actor_id"] == "actor:1" and decision["scope"] == original
        with pytest.raises(PermissionError, match="READ_ONLY_PRINCIPAL_REQUIRED"):
            authorize_business_related_read({"id": 2}, actor_ref="actor:2", original_scope=original, operation="read")
    with ws["repo"].transaction() as con:
        con.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    with ws["app"].test_request_context("/", headers=headers):
        with pytest.raises(PermissionError):
            authorize_business_related_read(actor, actor_ref="actor:1", original_scope=original, operation="read")
