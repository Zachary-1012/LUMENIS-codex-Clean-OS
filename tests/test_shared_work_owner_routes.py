"""Full upload/citation/version/search/export chain using actual C5 owners."""
import hashlib
import io
import json

import pytest

from tests.test_saved_document_workflow import workspace
from tests.test_source_brief_job_routes import GLOBAL

MATERIALS = "/api/experience/materials/documents"
WORKS = "/api/experience/saved-work"


@pytest.fixture
def route_workspace(workspace):
    import ast
    import re
    from pathlib import Path
    from flask import request, jsonify
    import experience_runtime
    from lumenis.system.security import permission
    ws = workspace
    ws["app"].register_blueprint(experience_runtime.experience_bp)
    nodes = [n for n in ast.parse(Path("app.py").read_text(encoding="utf-8-sig")).body
             if isinstance(n, ast.FunctionDef) and n.name in {"_pg_resolve_operation_type", "_permission_gate_write_check"}]
    for node in nodes:
        node.decorator_list = []
    namespace = dict(request=request, jsonify=jsonify, re=re, OperationType=permission.OperationType,
                     _PG_WRITE_METHODS={"POST", "PUT", "PATCH", "DELETE"}, _PG_BYPASS_PATHS=set(), _pg=ws["gate"])
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "app.py", "exec"), namespace)
    ws["app"].before_request(namespace["_permission_gate_write_check"])
    ws["api"] = ws["app"].test_client()
    return ws


def approved_upload(ws, filename="自己的材料.txt"):
    text = "Owned material 中文.\nNo real-world consumer claim.\n"
    raw = text.encode()
    provenance = {"source_url": None, "published_at": None, "captured_at": "2026-10-03T00:00:00Z",
                  "rights": "owner-approved", "title": "Owned engineering material",
                  "intended_use": "research_reference", "content_origin": {"kind": "self-authored", "claim_type": "synthetic_sample"},
                  "rights_statement": "Self-authored isolated engineering sample; not product factual acceptance."}
    path = ws["root"] / filename
    path.write_bytes(raw)
    prepared_provenance = {**provenance, "source_origin": {"kind": "approved-file", "ref": "file-upload-" + hashlib.sha256(raw).hexdigest()}}
    resource = ws["documents"].document_import_resource(str(path), actor=ws["actor"], scope=ws["scope"], provenance=prepared_provenance)
    ws["gate"].grant_approval("data_import", resource=MATERIALS, granted_by="isolated-engineering-review")
    ws["gate"].grant_approval("data_import", resource=resource, granted_by="isolated-engineering-review")
    result = ws["api"].post(MATERIALS, headers=GLOBAL, data={"file": (io.BytesIO(raw), filename),
                           "provenance": json.dumps(provenance)}, content_type="multipart/form-data")
    assert result.status_code == 200, result.get_json()
    return result.get_json()["result"], text


@pytest.mark.parametrize("format", ["json", "md", "txt", "docx", "pdf", "xlsx"])
def test_material_citation_version_search_reopen_and_actual_export(route_workspace, format):
    ws = route_workspace
    material, text = approved_upload(ws)
    assert material["source_boundaries"]["training_eligible"] is False
    reopened_source = ws["api"].get(MATERIALS + "/" + str(material["evidence_id"]), headers=GLOBAL)
    assert reopened_source.status_code == 200
    quote = ws["api"].get(MATERIALS + "/" + str(material["evidence_id"]) + "/quote", headers=GLOBAL,
                           query_string={"start": 0, "end": len("Owned material 中文.")})
    assert quote.status_code == 200, quote.get_json()
    citation = quote.get_json()["result"]["citation"]
    assert citation["quote"] == "Owned material 中文."
    body = {"title": "Material research result", "markdown": "A bounded original review. 中文",
            "kind": "research", "payload": {"constraints": {"budget": None}, "sample_type": "synthetic_engineering"},
            "citations": [citation], "request_id": "shared-route-save-001"}
    first = ws["api"].post(WORKS, headers=GLOBAL, json=body)
    assert first.status_code == 200, first.get_json()
    first = first.get_json()["result"]
    saved = first["artifact"]["artifact_id"]
    body.update(work_id=first["document"]["work_id"], previous_artifact_id=saved,
                expected_draft_digest=first["document"]["draft_digest"], request_id="shared-route-save-002",
                markdown="Revised bounded review, original quote retained. 中文")
    second = ws["api"].post(WORKS, headers=GLOBAL, json=body)
    assert second.status_code == 200, second.get_json()
    second = second.get_json()["result"]
    assert second["document"]["version"] == 2
    assert second["receipt"]["parent"]["ref"] == saved
    found = ws["api"].get(WORKS, headers=GLOBAL, query_string={"query": "Material research"})
    assert found.status_code == 200 and found.get_json()["result"]["items"]
    ref = second["artifact"]["artifact_id"]
    reopened = ws["api"].get(WORKS + "/" + ref, headers=GLOBAL)
    assert reopened.status_code == 200 and reopened.get_json()["result"]["artifact"] == second["artifact"]
    exported = ws["api"].get(WORKS + "/" + ref + "/export", headers=GLOBAL, query_string={"format": format})
    assert exported.status_code == 200, exported.get_json()
    assert hashlib.sha256(exported.data).hexdigest() == exported.headers["X-Content-SHA256"]
    assert exported.headers["X-Source-Artifact-ID"] == ref and len(exported.data) > 50


def test_podcast_plan_contract_reaches_normal_saved_work_route(route_workspace):
    from dataclasses import replace
    from podcast.intelligence.episode_runtime import PodcastPlan, PodcastSegment

    ws = route_workspace
    material, _ = approved_upload(ws, filename="podcast-contract-source.txt")
    quote = ws["api"].get(
        MATERIALS + "/" + str(material["evidence_id"]) + "/quote",
        headers=GLOBAL,
        query_string={"start": 0, "end": len("Owned material 中文.")},
    )
    assert quote.status_code == 200, quote.get_json()
    citation = quote.get_json()["result"]["citation"]
    first_plan = PodcastPlan(
        title="Route-backed episode",
        description="A source-bound editable episode plan.",
        language="en",
        segments=(PodcastSegment(
            segment_id="route-segment", media_asset_id="MEDIA-route", source_in=0, source_out=3,
            original_text="Owned material 中文.", corrected_text="Reviewed route narration",
            speaker="Host", chapter_title="Opening", evidence_refs=(f"evidence:{material['evidence_id']}",),
        ),),
    )
    contract = {"id": "lumenis.podcast-plan", "version": "1", "required_payload_paths": ["podcast_plan"]}
    body = {
        "title": first_plan.title,
        "markdown": first_plan.script_text(),
        "kind": "podcast_episode",
        "payload": {"podcast_plan": first_plan.to_dict()},
        "citations": [citation],
        "request_id": "route-podcast-plan-001",
        "contract": contract,
    }
    first = ws["api"].post(WORKS, headers=GLOBAL, json=body)
    assert first.status_code == 200, first.get_json()
    first = first.get_json()["result"]
    assert first["document"]["payload"]["podcast_plan"] == first_plan.to_dict()

    second_plan = replace(first_plan, revision=2, segments=(replace(
        first_plan.segments[0], corrected_text="Reviewed route revision",
    ),))
    second = ws["api"].post(
        WORKS,
        headers=GLOBAL,
        json={
            **body,
            "markdown": second_plan.script_text(),
            "payload": {"podcast_plan": second_plan.to_dict()},
            "request_id": "route-podcast-plan-002",
            "work_id": first["document"]["work_id"],
            "previous_artifact_id": first["artifact"]["artifact_id"],
            "expected_draft_digest": first["document"]["draft_digest"],
        },
    )
    assert second.status_code == 200, second.get_json()
    second = second.get_json()["result"]
    assert second["document"]["version"] == 2
    original = ws["api"].get(WORKS + "/" + first["artifact"]["artifact_id"], headers=GLOBAL)
    assert original.status_code == 200
    assert original.get_json()["result"]["document"]["payload"]["podcast_plan"] == first_plan.to_dict()


def test_unapproved_upload_and_client_identity_do_not_commit(route_workspace):
    ws = route_workspace
    before = ws["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0]
    response = ws["api"].post(MATERIALS, headers=GLOBAL, data={"file": (io.BytesIO(b"Unapproved input"), "input.txt"),
        "provenance": json.dumps({"source_url": None, "published_at": None, "captured_at": "2026-10-03T00:00:00Z",
                                  "rights": "owner-approved", "title": "Unapproved"})}, content_type="multipart/form-data")
    assert response.status_code == 403, response.get_json()
    assert ws["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0] == before
    response = ws["api"].post(WORKS, headers=GLOBAL, json={"actor": {"id": 1}, "scope": ws["scope"]})
    assert response.status_code == 400
    assert ws["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0] == before


def test_path_source_origin_and_duplicate_provenance_are_rejected(route_workspace):
    ws = route_workspace
    ws["gate"].grant_approval("data_import", resource=MATERIALS, granted_by="isolated-engineering-review")
    for filename, provenance in (("../escape.txt", "{}"), ("owned.txt", '{"title":"a","title":"b"}'),
                                  ("owned.txt", '{"source_origin":{"kind":"approved-file","ref":"forged-ref"}}')):
        response = ws["api"].post(MATERIALS, headers=GLOBAL, data={"file": (io.BytesIO(b"input"), filename),
                                   "provenance": provenance}, content_type="multipart/form-data")
        assert response.status_code == 400, response.get_json()
    assert ws["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0] == 0
