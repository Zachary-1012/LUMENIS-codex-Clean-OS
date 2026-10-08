"""Real-owner isolated contracts; neither formal Source nor UI acceptance."""
from copy import deepcopy
import json

import pytest

from tests.test_saved_document_workflow import workspace, _source, _save
from lumenis.system.security.permission import OperationType

RETAINED_CAPTURE_CASES = (
    ("NIKE_PLAN", "2026-10-03T10:21:11", "2026-07-21T12:00:00-07:00",
     "2026-10-03T02:21:09.290167+00:00", "2026-10-03T02:21:11.244722+00:00"),
    ("NIKE_FILM", "2026-10-03T10:21:13", "2026-06-04T09:00:00-07:00",
     "2026-10-03T02:21:11.245717+00:00", "2026-10-03T02:21:13.469947+00:00"),
    ("LELABO_CITY", "2026-10-03T10:21:15", None,
     "2026-10-03T02:21:13.471272+00:00", "2026-10-03T02:21:15.513379+00:00"),
    ("LELABO_SHIU", "2026-10-03T10:21:17", None,
     "2026-10-03T02:21:15.514267+00:00", "2026-10-03T02:21:17.483872+00:00"),
)


def retained_times():
    return [(alias, {"native_literal": literal, "publication_literal": publication,
                     "separate_original_invocation_window": {"started_at": start, "finished_at": end}})
            for alias, literal, publication, start, end in RETAINED_CAPTURE_CASES]


def observed_provenance(alias, time):
    window = time["separate_original_invocation_window"]
    return {"source_url": "https://example.org/retained-public-material", "published_at": time["publication_literal"],
            "captured_at": time["native_literal"], "rights": "public-reference-only", "title": alias,
            "capture_observation": {"literal": time["native_literal"], "precision": "second", "utc_offset": None,
                "timezone": "UNKNOWN", "absolute_utc": None,
                "invocation_bounds": {"started_at": window["started_at"], "finished_at": window["finished_at"],
                                      "meaning": "original-invocation-bounds-not-exact-capture"}}}


@pytest.mark.parametrize("alias,time", retained_times(), ids=lambda value: value if isinstance(value, str) else None)
def test_recorded_naive_time_survives_import_saved_work_reopen_and_retry(workspace, alias, time):
    ws = workspace
    path = ws["root"] / "retained.txt"
    path.write_text("Generated transport test, not the original publisher body.", encoding="utf-8")
    provenance = observed_provenance(alias, time)
    args = {"actor": ws["actor"], "scope": ws["scope"], "provenance": provenance}
    resource = ws["documents"].document_import_resource(str(path), **args)
    ws["gate"].grant_approval(OperationType.DATA_IMPORT.value, resource=resource, granted_by="isolated-engineering")
    first = ws["documents"].import_document(str(path), **args)
    again = ws["documents"].import_document(str(path), **args)
    assert again["replayed"] and first["evidence_id"] == again["evidence_id"]
    quote = ws["documents"].locate_quote(first["evidence_id"], actor=ws["actor"], scope=ws["scope"], start=0, end=19)
    assert quote["captured_at"] == time["native_literal"]
    assert quote["published_at"] == time["publication_literal"]
    assert quote["evidence_version"] == "document-import/2"
    assert quote["capture_absolute_time_status"] == "UNKNOWN"
    assert quote["capture_observation"] == provenance["capture_observation"]
    saved = _save(ws, request_id="retained-capture-01", citations=[quote["citation"]])
    reopened = ws["work"].read_committed_work(saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"])
    bound = reopened["receipt"]["sources"][0]
    assert bound["capture_observation"] == provenance["capture_observation"]
    assert bound["captured_at"] == time["native_literal"] and bound["capture_absolute_time_status"] == "UNKNOWN"
    row = ws["repo"].query_one("SELECT captured_at,publish_datetime,provenance FROM canonical_data")
    assert row[0] == time["native_literal"] and row[1] == (time["publication_literal"] or "")
    assert json.loads(row[2])["provenance"] == provenance
    assert json.loads(ws["repo"].query_one("SELECT collection_metadata FROM app_evidence_records")[0])["provenance"] == provenance


@pytest.mark.parametrize("change", ["missing", "guessed_utc", "guessed_offset", "guessed_zone", "literal_change",
                                   "precision_change", "reversed_bounds", "naive_bounds", "non_utc_bounds", "naive_publication"])
def test_naive_time_requires_exact_unknown_observation_not_an_inferred_point(workspace, change):
    ws = workspace
    alias, time = retained_times()[0]
    provenance = observed_provenance(alias, time)
    observation = provenance["capture_observation"]
    if change == "missing":
        del provenance["capture_observation"]
    elif change == "guessed_utc":
        observation["absolute_utc"] = time["separate_original_invocation_window"]["finished_at"]
    elif change == "guessed_offset":
        observation["utc_offset"] = "+08:00"
    elif change == "guessed_zone":
        observation["timezone"] = "Asia/Shanghai"
    elif change == "literal_change":
        observation["literal"] = "2026-10-03T10:21:12"
    elif change == "precision_change":
        observation["precision"] = "minute"
    elif change == "reversed_bounds":
        bounds = observation["invocation_bounds"]
        bounds["started_at"], bounds["finished_at"] = bounds["finished_at"], bounds["started_at"]
    elif change == "naive_bounds":
        observation["invocation_bounds"]["started_at"] = "2026-10-03T02:21:09"
    elif change == "non_utc_bounds":
        observation["invocation_bounds"]["started_at"] = "2026-10-03T10:21:09+08:00"
    elif change == "naive_publication":
        provenance["published_at"] = "2026-07-21T12:00:00"
    path = ws["root"] / "unadmitted.txt"
    path.write_text("No input has been admitted", encoding="utf-8")
    expected = "DOCUMENT_TIME_OFFSET_REQUIRED" if change in {"missing", "naive_publication"} else "DOCUMENT_CAPTURE_OBSERVATION_INVALID"
    with pytest.raises(ValueError, match=expected):
        ws["documents"].document_import_resource(str(path), actor=ws["actor"], scope=ws["scope"], provenance=provenance)
    assert ws["repo"].query_one("SELECT COUNT(*) FROM app_evidence_records")[0] == 0


def client(ws):
    from experience_runtime import experience_bp
    ws["app"].register_blueprint(experience_bp)
    return ws["app"].test_client(), {"X-Domain-Id": "CTH", "X-Lumenis-Context-Mode": "GLOBAL_ALL"}


@pytest.mark.parametrize("domain", ["CTH", "BMP"])
def test_import_final_scope_withdrawal_in_writer_transaction_rolls_back_every_owner(workspace, monkeypatch, domain):
    import canonical_data
    from subject_registry import add_subject
    ws = workspace
    subject, _ = add_subject({"domain_id": domain, "subject_type": "company" if domain == "CTH" else "brand",
                             "name_en": "Final import scope fixture", "name_zh": "导入范围测试"})
    original_status = ws["repo"].query_one("SELECT status FROM lumenis_subject_registry WHERE subject_id=?", (subject["subject_id"],))[0]
    scope = {"domain_id": "cth" if domain == "CTH" else "zbmp", "global_scope": False,
             "subject_id": subject["subject_id"] if domain == "CTH" else None,
             "brand_focus_id": subject.get("brand_focus_id") if domain == "BMP" else None}
    path = ws["root"] / "transaction-source.txt"
    path.write_text("Declared source must not commit after scope withdrawal.", encoding="utf-8")
    provenance = {"source_url": "https://example.org/transaction-source", "published_at": None,
                  "captured_at": "2026-10-02T17:00:00Z", "rights": "public-reference-only", "title": "Scope test"}
    args = {"actor": ws["actor"], "scope": scope, "provenance": provenance}
    resource = ws["documents"].document_import_resource(str(path), **args)
    ws["gate"].grant_approval(OperationType.DATA_IMPORT.value, resource=resource, granted_by="isolated-engineering")
    persist = canonical_data.persist_canonical
    def withdraw(con, record):
        result = persist(con, record)
        con.execute("UPDATE lumenis_subject_registry SET status='inactive' WHERE subject_id=?", (subject["subject_id"],))
        return result
    monkeypatch.setattr(canonical_data, "persist_canonical", withdraw)
    with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
        ws["documents"].import_document(str(path), **args)
    for table in ("app_evidence_records", "canonical_data", "lumenis_shared_artifacts"):
        assert ws["repo"].query_one("SELECT COUNT(*) FROM " + table)[0] == 0
    assert ws["repo"].query_one("SELECT status FROM lumenis_subject_registry WHERE subject_id=?", (subject["subject_id"],))[0] == original_status
    assert not list((ws["root"] / "artifacts").glob("ART-*"))


def test_evidence_query_locates_each_cited_version_with_scope_bound_pagination(workspace):
    ws = workspace
    _, _, source = _source(ws)
    cite = ws["documents"].locate_quote(source["evidence_id"], actor=ws["actor"], scope=ws["scope"], start=0, end=20)["citation"]
    first = _save(ws, request_id="source-linked-01", citations=[cite])
    second = _save(ws, request_id="source-linked-02", citations=[cite], markdown="Locally revised decision; original source retained.",
                   work_id=first["document"]["work_id"], previous_artifact_id=first["artifact"]["artifact_id"])
    unrelated = _save(ws, request_id="source-unrelated-01")
    http, headers = client(ws)
    one = http.get(f"/api/experience/saved-work?evidence_id={source['evidence_id']}&limit=1", headers=headers)
    assert one.status_code == 200
    page = one.json["result"]
    assert page["verification_complete"] and page["has_more"] and len(page["items"]) == 1
    two = http.get("/api/experience/saved-work", query_string={"evidence_id": source["evidence_id"], "limit": 1,
                                                             "cursor": page["next_cursor"]}, headers=headers)
    assert two.status_code == 200
    items = page["items"] + two.json["result"]["items"]
    assert {item["artifact"]["artifact_id"] for item in items} == {first["artifact"]["artifact_id"], second["artifact"]["artifact_id"]}
    for item in items:
        assert item["artifact"]["artifact_id"] != unrelated["artifact"]["artifact_id"]
        assert item["source_matches"]["citations"][0]["quote"] == cite["quote"]
        assert item["source_matches"]["uncited_dependencies"] == "NOT_VERIFIED"
    changed = http.get("/api/experience/saved-work", query_string={"evidence_id": source["evidence_id"] + 1,
                                                                 "cursor": page["next_cursor"]}, headers=headers)
    assert changed.status_code == 400 and changed.json["code"] == "WORK_CURSOR_INVALID"


def test_explicit_source_correction_adoption_preserves_parent_and_impact(workspace):
    ws = workspace
    _, _, original_source = _source(ws, filename="correction-original.txt",
                                    source_url="https://example.org/correction/v1")
    original_quote = ws["documents"].locate_quote(
        original_source["evidence_id"], actor=ws["actor"], scope=ws["scope"], start=0, end=20
    )["citation"]
    original_markdown = "The original source supports this statement."
    saved = _save(ws, request_id="correction-parent-01", markdown=original_markdown,
                  citations=[original_quote])

    corrected_text = "Corrected source text replaces the earlier statement."
    corrected_path = ws["root"] / "correction-v2.txt"
    corrected_path.write_text(corrected_text + "\n", encoding="utf-8")
    provenance = {
        "source_url": "https://example.org/correction/v2",
        "published_at": "2026-10-08T00:00:00Z",
        "captured_at": "2026-10-08T00:01:00Z",
        "rights": "public-reference-only",
        "title": "Corrected self-contained test source",
        "intended_use": "research_reference",
    }
    args = {"actor": ws["actor"], "scope": ws["scope"], "provenance": provenance}
    resource = ws["documents"].document_import_resource(str(corrected_path), **args)
    ws["gate"].grant_approval(OperationType.DATA_IMPORT.value, resource=resource,
                              granted_by="isolated-engineering")
    corrected_source = ws["documents"].import_document(str(corrected_path), **args)
    corrected_quote = ws["documents"].locate_quote(
        corrected_source["evidence_id"], actor=ws["actor"], scope=ws["scope"],
        start=0, end=len(corrected_text)
    )["citation"]

    revised_markdown = "The revised statement adopts the corrected source."
    revised = ws["work"].revise_work(
        saved["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"],
        request_id="correction-revision-01", expected_sha256=saved["artifact"]["sha256"],
        reason="Reviewed the corrected source and explicitly adopted its newer Evidence.",
        edits=[{"pointer": "/markdown", "start": 0, "end": len(original_markdown),
                "expected": original_markdown, "replacement": revised_markdown}],
        citations=[corrected_quote],
        source_adoptions=[{"from_evidence_id": original_source["evidence_id"],
                           "to_evidence_id": corrected_source["evidence_id"]}],
    )

    note = revised["document"]["payload"]["revision_note"]
    assert revised["document"]["version"] == 2
    assert revised["document"]["markdown"] == revised_markdown
    assert note["reason"] == "Reviewed the corrected source and explicitly adopted its newer Evidence."
    assert note["parent"] == {"artifact_id": saved["artifact"]["artifact_id"],
                              "sha256": saved["artifact"]["sha256"], "version": 1}
    assert note["source_adoptions"] == [{"from_evidence_id": original_source["evidence_id"],
                                         "to_evidence_id": corrected_source["evidence_id"]}]
    revised_citation = revised["document"]["citations"][0]
    assert revised_citation["evidence_id"] == corrected_source["evidence_id"]
    assert revised_citation["quote"] == corrected_quote["quote"]
    reopened_parent = ws["work"].reopen_work(saved["artifact"]["artifact_id"],
                                             actor=ws["actor"], scope=ws["scope"])
    parent_citation = reopened_parent["document"]["citations"][0]
    assert parent_citation["evidence_id"] == original_source["evidence_id"]
    assert parent_citation["quote"] == original_quote["quote"]

    old_impact = ws["work"].search_work(actor=ws["actor"], scope=ws["scope"],
                                         evidence_id=original_source["evidence_id"])
    new_impact = ws["work"].search_work(actor=ws["actor"], scope=ws["scope"],
                                         evidence_id=corrected_source["evidence_id"])
    assert [item["artifact"]["artifact_id"] for item in old_impact["items"]] == [saved["artifact"]["artifact_id"]]
    assert [item["artifact"]["artifact_id"] for item in new_impact["items"]] == [revised["artifact"]["artifact_id"]]
    assert old_impact["items"][0]["source_matches"]["uncited_dependencies"] == "NOT_VERIFIED"
    assert new_impact["items"][0]["source_matches"]["uncited_dependencies"] == "NOT_VERIFIED"


def test_normal_preferences_notifications_acknowledgement_and_replay(workspace):
    ws = workspace
    saved = _save(ws, request_id="notification-work-01")
    http, headers = client(ws)
    read = http.get("/api/experience/saved-work/preferences", headers=headers)
    assert read.status_code == 200 and read.json["result"]["persisted"] is False
    values = deepcopy(read.json["result"]["preferences"])
    values.update(language="ko", export_format="docx", notifications_enabled=False,
                  acknowledged_artifact_ids=[saved["artifact"]["artifact_id"]])
    body = {"preferences": values, "request_id": "normal-preferences-01"}
    written = http.post("/api/experience/saved-work/preferences", headers=headers, json=body)
    assert written.status_code == 200
    replay = http.post("/api/experience/saved-work/preferences", headers=headers, json=body)
    assert replay.status_code == 200 and replay.json["result"]["replayed"] is True
    reopened = http.get("/api/experience/saved-work/preferences", headers=headers)
    assert reopened.json["result"]["preferences"] == values and reopened.json["result"]["version"] == 1
    feed = http.get("/api/experience/saved-work/notifications", headers=headers)
    assert feed.status_code == 200 and feed.json["result"]["delivery"] == "in-product-projection"
    event = next(item for item in feed.json["result"]["notifications"] if item["return_ref"]["artifact_id"] == saved["artifact"]["artifact_id"])
    assert event["acknowledged"] is True and event["visible"] is False
    assert event["return_ref"]["scope"] == ws["scope"]
    injection = http.post("/api/experience/saved-work/preferences", headers=headers, json={**body, "actor": {"role": "admin"}})
    assert injection.status_code == 400 and injection.json["code"] == "DELIVERY_PREFERENCES_REQUEST_INVALID"
