"""Private Shared custody uses real immutable SavedWork and no model call."""
import hashlib
import pytest
from tests.test_saved_document_workflow import workspace

SCOPE = {"scope_kind": "shared_workspace", "version": 1}


def test_default_analysis_does_not_call_model(monkeypatch):
    from lumenis.importer import analyzer
    from lumenis.importer.parser import ParseResult
    monkeypatch.setattr(analyzer, "_ai_analyze", lambda *a, **k: pytest.fail("unexpected model call"))
    notes = analyzer.analyze_text("Original text and repeated text.")
    assert notes[0].analysis_status == "NOT_RUN"
    parsed = ParseResult()
    parsed.text = "Alpha Alpha\nSecond line."
    value = analyzer.analyze_source_basics(parsed)
    assert value["character_count"] == len(parsed.text)
    assert value["ai_state"] == "NOT_RUN"
    assert value["author"] is None and value["risk"] is None
    for item in value["source_excerpts"]:
        assert parsed.text[item["start"]:item["end"]] == item["text"]


def test_private_original_save_reopen_revision_export(workspace, monkeypatch):
    ws = workspace
    from lumenis.importer import analyzer
    monkeypatch.setattr(analyzer, "_ai_analyze", lambda *a, **k: pytest.fail("unexpected model call"))
    path = ws["root"] / "ordinary.txt"
    raw = "Private source, unknown author.\nAlpha Alpha\n".encode()
    path.write_bytes(raw)
    first = ws["documents"].save_private_document(str(path), actor=ws["actor"], scope=SCOPE, request_id="private-upload-001")
    ref = first["artifact"]["artifact_id"]
    reopened = ws["work"].reopen_work(ref, actor=ws["actor"], scope=SCOPE)
    payload = reopened["document"]["payload"]
    assert payload["source_material"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert payload["source_material"]["rights"] == "UNKNOWN"
    assert payload["source_material"]["author"] is None
    assert not payload["source_material"]["canonical_admitted"]
    assert reopened["document"]["citations"] == []
    assert payload["parsed_source"]["text"] == raw.decode()
    replay = ws["documents"].save_private_document(str(path), actor=ws["actor"], scope=SCOPE, request_id="private-upload-001")
    assert replay["artifact"]["artifact_id"] == ref and replay["replayed"]
    revised = ws["work"].save_work(title="Revised review", markdown="My private analysis revision.", kind="research", payload=payload,
        citations=[], request_id="private-revision-001", actor=ws["actor"], scope=SCOPE,
        work_id=reopened["document"]["work_id"], previous_artifact_id=ref,
        expected_draft_digest=reopened["document"]["draft_digest"])
    assert revised["document"]["version"] == 2
    assert revised["document"]["attachments"] == first["document"]["attachments"]
    original = ws["work"].download_attachment(revised["artifact"]["artifact_id"],
        name=first["document"]["attachments"][0]["name"], actor=ws["actor"], scope=SCOPE)
    assert original["content"] == raw
    exported = ws["work"].export_work(revised["artifact"]["artifact_id"], actor=ws["actor"], scope=SCOPE, format="json")
    assert b"unknown author" in exported["content"]
    assert ws["work"].reopen_work(ref, actor=ws["actor"], scope=SCOPE)["document"]["version"] == 1


@pytest.mark.parametrize("name,mime,raw", [
    ("original.txt", "text/plain", b"hello"),
    ("original.csv", "text/csv", b"a,b\n1,2"),
    ("original.html", "application/octet-stream", b"<script>alert(1)</script>"),
])
def test_original_custody_format_is_validated(name, mime, raw):
    from lumenis.shared.reporting import saved_work as owner
    assert owner._valid_ooxml_attachment(raw, owner._attachment_spec(name, mime))
    assert owner._attachment_spec("../" + name, mime) is None
    assert owner._attachment_spec(name, "text/html") is None
    assert not owner._valid_ooxml_attachment(b"binary\0blob", owner._attachment_spec(name, mime))


def test_private_http_upload_reopen_and_original_download(workspace):
    import io
    import json
    import experience_runtime
    ws = workspace
    ws["app"].register_blueprint(experience_runtime.experience_bp)
    client = ws["app"].test_client()
    headers = {"X-Lumenis-Workspace-Scope": json.dumps(SCOPE)}
    response = client.post("/api/experience/materials/documents", headers=headers,
        data={"file": (io.BytesIO(b"Private original source."), "source.txt"), "request_id": "http-upload-0001"})
    assert response.status_code == 200, response.get_json()
    saved = response.get_json()["result"]
    artifact = saved["artifact"]["artifact_id"]
    attachment = saved["document"]["attachments"][0]
    base = "/api/experience/saved-work/" + artifact
    reopened = client.get(base, headers=headers)
    assert reopened.status_code == 200, reopened.get_json()
    original = client.get(base + "/attachments/" + attachment["name"], headers=headers)
    assert original.status_code == 200, original.get_json()
    assert original.data == b"Private original source."
    assert original.headers["X-Content-Type-Options"] == "nosniff"
    assert "attachment" in original.headers["Content-Disposition"]
    denied = client.get(base + "/attachments/" + attachment["name"], headers=headers,
                        environ_overrides={"REMOTE_ADDR": "203.0.113.1"})
    assert denied.status_code in {401, 403}, denied.get_json()
