"""Existing-owner local revision and explicit source adoption in isolated DBs."""
from copy import deepcopy
import hashlib
import json

import pytest

from tests.test_saved_document_workflow import workspace, _source, _save
from tests.test_shared_work_owner_routes import route_workspace
from lumenis.system.security.permission import OperationType


def original(ws):
    _, _, source = _source(ws)
    quote = ws["documents"].locate_quote(source["evidence_id"], actor=ws["actor"], scope=ws["scope"], start=0, end=20)["citation"]
    text = "😀 Keep first sentence.\nUpdate this claim.\nKeep final sentence."
    payload = {"sections": [{"title": "Keep", "body": "Original unchanged section"},
                            {"title": "Budget", "body": "A proposed experiment, not an observed outcome"}],
               "resource_constraints": {"currency": "GBP", "maximum": 2700}, "a/b": {"~key": 1}}
    saved = _save(ws, request_id="original-revision-01", markdown=text, payload=payload, citations=[quote])
    return saved, quote


def request(saved):
    text = saved["document"]["markdown"]
    start = text.index("Update this claim.")
    return {"request_id": "local-edit-request-01", "expected_sha256": saved["artifact"]["sha256"],
            "reason": "Adopt the revised source and reduce the proposed budget; preserve all other work.",
            "edits": [{"pointer": "/markdown", "start": start, "end": start + len("Update this claim."),
                       "expected": "Update this claim.", "replacement": "Revised attributed source statement."},
                      {"pointer": "/payload/resource_constraints/maximum", "expected": 2700, "value": 1200},
                      {"pointer": "/payload/a~1b/~0key", "expected": 1, "value": 2}]}


def replacement(ws):
    path = ws["root"] / "source-correction.txt"
    path.write_text("Replacement source statement\nSeparate new observation.\n", encoding="utf-8")
    provenance = {"source_url": "https://example.org/new-original", "published_at": None,
                  "captured_at": "2026-10-04T00:00:00Z", "rights": "public-reference-only", "title": "Generated corrected source"}
    args = {"actor": ws["actor"], "scope": ws["scope"], "provenance": provenance}
    resource = ws["documents"].document_import_resource(str(path), **args)
    ws["gate"].grant_approval(OperationType.DATA_IMPORT.value, resource=resource, granted_by="isolated-engineering")
    source = ws["documents"].import_document(str(path), **args)
    return ws["documents"].locate_quote(source["evidence_id"], actor=ws["actor"], scope=ws["scope"], start=0, end=28)["citation"]


def test_normal_source_budget_local_revision_replay_export_and_preserved_parent(route_workspace):
    ws = route_workspace
    saved, old_cite = original(ws)
    new_cite = replacement(ws)
    before = ws["work"].export_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"], format="json")["content"]
    body = {**request(saved), "citations": [new_cite],
            "source_adoptions": [{"from_evidence_id": old_cite["evidence_id"], "to_evidence_id": new_cite["evidence_id"]}]}
    url = f"/api/experience/saved-work/{saved['artifact']['artifact_id']}/revise"
    headers = {"X-Domain-Id": "CTH", "X-Lumenis-Context-Mode": "GLOBAL_ALL"}
    result = ws["api"].post(url, headers=headers, json=body)
    assert result.status_code == 200, result.json
    revised = result.json["result"]
    assert revised["document"]["version"] == 2 and revised["document"]["parent_artifact_id"] == saved["artifact"]["artifact_id"]
    assert revised["document"]["markdown"] == saved["document"]["markdown"].replace("Update this claim.", "Revised attributed source statement.")
    payload = revised["document"]["payload"]
    assert payload["sections"] == saved["document"]["payload"]["sections"]
    assert payload["resource_constraints"] == {"currency": "GBP", "maximum": 1200}
    assert payload["a/b"]["~key"] == 2
    assert payload["revision_note"]["reason"] == body["reason"] and payload["revision_note"]["source_adoptions"] == body["source_adoptions"]
    assert payload["revision_note"]["offset_unit"] == "unicode_codepoint"
    replay = ws["api"].post(url, headers=headers, json=body)
    assert replay.status_code == 200 and replay.json["result"]["replayed"]
    assert replay.json["result"]["artifact"]["artifact_id"] == revised["artifact"]["artifact_id"]
    old = ws["work"].export_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"], format="json")["content"]
    assert old == before and hashlib.sha256(old).hexdigest() == saved["artifact"]["sha256"]
    reopened = ws["work"].read_committed_work(revised["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"])
    assert reopened["document"] == revised["document"] and reopened["receipt"]["sources"][0]["evidence_id"] == new_cite["evidence_id"]
    old_impact = ws["work"].search_work(actor=ws["actor"], scope=ws["scope"], evidence_id=old_cite["evidence_id"])
    new_impact = ws["work"].search_work(actor=ws["actor"], scope=ws["scope"], evidence_id=new_cite["evidence_id"])
    assert [item["artifact"]["artifact_id"] for item in old_impact["items"]] == [saved["artifact"]["artifact_id"]]
    assert [item["artifact"]["artifact_id"] for item in new_impact["items"]] == [revised["artifact"]["artifact_id"]]
    current_text = revised["document"]["markdown"]
    start = current_text.index("Revised attributed source statement.")
    rollback_body = {"request_id": "explicit-rollback-01", "expected_sha256": revised["artifact"]["sha256"],
                     "reason": "Explicitly restore the earlier source and budget while preserving both previous versions.",
                     "edits": [{"pointer": "/markdown", "start": start,
                                "end": start + len("Revised attributed source statement."),
                                "expected": "Revised attributed source statement.", "replacement": "Update this claim."},
                               {"pointer": "/payload/resource_constraints/maximum", "expected": 1200, "value": 2700},
                               {"pointer": "/payload/a~1b/~0key", "expected": 2, "value": 1}],
                     "citations": [old_cite], "source_adoptions": [{"from_evidence_id": new_cite["evidence_id"], "to_evidence_id": old_cite["evidence_id"]}]}
    restored = ws["api"].post(f"/api/experience/saved-work/{revised['artifact']['artifact_id']}/revise", headers=headers, json=rollback_body)
    assert restored.status_code == 200, restored.json
    assert restored.json["result"]["document"]["version"] == 3
    assert restored.json["result"]["document"]["markdown"] == saved["document"]["markdown"]
    assert restored.json["result"]["document"]["parent_artifact_id"] == revised["artifact"]["artifact_id"]
    assert restored.json["result"]["document"]["payload"]["revision_note"]["reason"] == rollback_body["reason"]
    assert ws["work"].read_committed_work(revised["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"])["document"]["payload"]["resource_constraints"]["maximum"] == 1200


@pytest.mark.parametrize("pointer", ["/context/domain_id", "/citations/0/quote", "/payload", "/payload/sections",
                                     "/payload/sections/01/body", "/payload/sections/-/body", "/payload/a~2b/x",
                                     "/payload/missing", "/payload/revision_note"])
def test_wrong_or_owner_structural_pointer_creates_no_version(workspace, pointer):
    ws = workspace
    saved, _ = original(ws)
    body = request(saved)
    body["edits"] = [{"pointer": pointer, "expected": "whatever", "value": "changed"}]
    before = ws["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0]
    with pytest.raises(ValueError):
        ws["work"].revise_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"], **body)
    assert ws["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0] == before


def test_multiple_ranges_old_value_and_stale_parent_conflicts(workspace):
    ws = workspace
    saved, _ = original(ws)
    body = request(saved)
    text = saved["document"]["markdown"]
    body["edits"] = [{"pointer": "/markdown", "start": 0, "end": 1, "expected": "😀", "replacement": "•"},
                     {"pointer": "/markdown", "start": len(text), "end": len(text), "expected": "", "replacement": "\nUser revision"}]
    revised = ws["work"].revise_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"], **body)
    assert revised["document"]["markdown"] == "•" + text[1:] + "\nUser revision"
    wrong = {**body, "request_id": "wrong-old-value-01", "edits": [{"pointer": "/title", "expected": "stale", "value": "new"}]}
    with pytest.raises(ValueError, match="WORK_EDIT_VALUE_CHANGED"):
        ws["work"].revise_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"], **wrong)
    with pytest.raises(ValueError, match="WORK_REVISION_CONFLICT"):
        ws["work"].revise_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"], **{**body, "request_id": "stale-parent-01"})
    overlap = deepcopy(body)
    overlap["edits"].append({"pointer": "/markdown", "start": 0, "end": 2, "expected": text[:2], "replacement": "bad"})
    with pytest.raises(ValueError, match="WORK_EDIT_RANGES_OVERLAP"):
        ws["work"].revise_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"], **overlap)


def test_new_sources_require_complete_explicit_adoption_and_private_fields_fail(workspace):
    ws = workspace
    saved, _ = original(ws)
    cite = replacement(ws)
    body = {**request(saved), "citations": [cite]}
    with pytest.raises(ValueError, match="WORK_SOURCE_ADOPTION_REQUIRED"):
        ws["work"].revise_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"], **body)
    with pytest.raises(ValueError, match="WORK_SOURCE_ADOPTION_INVALID"):
        ws["work"].revise_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"], **{**body, "source_adoptions": False})
    private = request(saved)
    private["edits"][0] = {"pointer": "/payload/sections/0/body", "expected": "Original unchanged section", "value": {"path": "C:/private"}}
    with pytest.raises(ValueError, match="WORK_EDIT_OVERLAP_OR_CONTAINER"):
        ws["work"].revise_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"], **private)


def test_task_and_creation_owner_contract_cannot_be_revised_through_generic_work(workspace):
    ws = workspace
    saved = _save(ws, request_id="task-owned-work-01", task_id="server-task", assertion_id="server-assertion")
    body = {"request_id": "task-override-01", "expected_sha256": saved["artifact"]["sha256"],
            "reason": "Must use the current task owner", "edits": [{"pointer": "/title", "expected": saved["document"]["title"], "value": "Changed"}]}
    with pytest.raises(ValueError, match="WORK_REVISION_OWNER_REQUIRED"):
        ws["work"].revise_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"], **body)


@pytest.mark.parametrize("domain", ["CTH", "BMP"])
def test_local_revision_same_transaction_withdrawal_keeps_original_and_no_new_work(workspace, monkeypatch, domain):
    from subject_registry import add_subject
    ws = workspace
    subject, _ = add_subject({"domain_id": domain, "subject_type": "company" if domain == "CTH" else "brand",
                             "name_en": "Scoped revision test", "name_zh": "局部修订范围"})
    ws["scope"] = {"domain_id": "cth" if domain == "CTH" else "zbmp", "global_scope": False,
                   "subject_id": subject["subject_id"] if domain == "CTH" else None,
                   "brand_focus_id": subject.get("brand_focus_id") if domain == "BMP" else None}
    saved, _ = original(ws)
    before = ws["work"].read_committed_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"])["content"]
    count = ws["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0]
    status = ws["repo"].query_one("SELECT status FROM lumenis_subject_registry WHERE subject_id=?", (subject["subject_id"],))[0]
    stage = ws["work"]._stage_bytes
    def withdraw(con, **kwargs):
        result = stage(con, **kwargs)
        con.execute("UPDATE lumenis_subject_registry SET status='inactive' WHERE subject_id=?", (subject["subject_id"],))
        return result
    monkeypatch.setattr(ws["work"], "_stage_bytes", withdraw)
    with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
        ws["work"].revise_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"], **request(saved))
    assert ws["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0] == count
    assert ws["repo"].query_one("SELECT status FROM lumenis_subject_registry WHERE subject_id=?", (subject["subject_id"],))[0] == status
    assert ws["work"].read_committed_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"])["content"] == before
    assert len(list((ws["root"] / "artifacts").glob("ART-*"))) == count


def test_normal_revision_rejects_injected_actor_and_wrong_parent_hash(route_workspace):
    ws = route_workspace
    saved, _ = original(ws)
    body = request(saved)
    url = f"/api/experience/saved-work/{saved['artifact']['artifact_id']}/revise"
    headers = {"X-Domain-Id": "CTH", "X-Lumenis-Context-Mode": "GLOBAL_ALL"}
    injected = ws["api"].post(url, headers=headers, json={**body, "actor": {"role": "admin"}})
    assert injected.status_code == 400 and injected.json["code"] == "WORK_REVISION_REQUEST_INVALID"
    changed = ws["api"].post(url, headers=headers, json={**body, "expected_sha256": "0" * 64})
    assert changed.status_code == 409 and changed.json["code"] == "WORK_REVISION_SOURCE_CHANGED"
    assert ws["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0] == 2
