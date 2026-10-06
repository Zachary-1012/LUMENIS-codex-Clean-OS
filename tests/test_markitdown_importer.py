from __future__ import annotations

import sys
import types
import builtins
import hashlib
import io
import json
import uuid
from flask import Flask

import pytest

from lumenis.importer.parser import parse_file


def _install_fake_markitdown(monkeypatch, markdown: str = "# Imported\n\nBody"):
    class Converted:
        def __init__(self):
            self.markdown = markdown

    class FakeMarkItDown:
        def __init__(self, *, enable_plugins):
            assert enable_plugins is False

        def convert_local(self, path):
            assert isinstance(path, str)
            assert not path.startswith(("http://", "https://"))
            return Converted()

    module = types.ModuleType("markitdown")
    module.MarkItDown = FakeMarkItDown
    module.__version__ = "test-version"
    monkeypatch.setitem(sys.modules, "markitdown", module)


def test_markitdown_importer_is_local_only_and_records_fingerprint(tmp_path, monkeypatch):
    source = tmp_path / "brief.html"
    source.write_text("<html><body><h1>Brief</h1></body></html>", encoding="utf-8")
    _install_fake_markitdown(monkeypatch)

    result = parse_file(str(source))

    assert result.text == "# Imported\n\nBody"
    assert result.paragraphs == ["# Imported", "Body"]
    assert result.metadata["format"] == "html"
    assert result.metadata["parser"] == "markitdown"
    assert result.metadata["network_mode"] == "local_only"
    assert result.metadata["source_name"] == "brief.html"
    assert len(result.metadata["source_fingerprint"]) == 64
    assert result.metadata["parser_version"] == "test-version"


def test_markitdown_missing_dependency_is_honest(tmp_path, monkeypatch):
    source = tmp_path / "deck.pptx"
    source.write_bytes(b"not-a-real-pptx")
    monkeypatch.delitem(sys.modules, "markitdown", raising=False)
    original_import = builtins.__import__

    def reject_optional(name, *args, **kwargs):
        if name == "markitdown":
            raise ImportError("simulated optional dependency absence")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_optional)

    # The test runtime does not install the optional converter.  A missing
    # dependency must be visible to the caller rather than becoming success.
    with pytest.raises(ImportError, match="markitdown"):
        parse_file(str(source))


def test_upload_preview_binds_file_hash_actor_scope_and_capture_time(tmp_path, monkeypatch):
    import lumenis.importer.service as service
    from lumenis.importer.parser import ParseResult

    app = Flask("import-preview-test")
    monkeypatch.setattr(service, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(
        service, "_current_import_actor_scope",
        lambda: ("actor:17", {
            "domain_id": "cth", "subject_id": "subject-1",
            "brand_focus_id": None, "global_scope": False,
        }, object()),
    )
    monkeypatch.setattr(service, "log_audit", lambda *_args, **_kwargs: None)
    parsed = ParseResult()
    parsed.metadata["format"] = "txt"
    parsed.text = "source text"
    monkeypatch.setattr(service, "parse_file", lambda _path: parsed)
    note = service.AnalyzedNote()
    note.title, note.content = "Source", "source text"
    monkeypatch.setattr(service, "analyze_parsed", lambda *_args, **_kwargs: [note])

    with app.test_request_context(
        "/v4/importer/upload", method="POST",
        data={"file": (io.BytesIO(b"source text"), "brief.txt")},
        content_type="multipart/form-data",
    ):
        response = service.upload_file.__wrapped__()

    body = response.get_json()
    task_id = body["task_id"]
    task_dir = tmp_path / task_id
    manifest = json.loads((task_dir / "preview.json").read_text(encoding="utf-8"))
    assert body["success"] is True
    assert manifest["actor_ref"] == "actor:17"
    assert manifest["scope"]["subject_id"] == "subject-1"
    assert manifest["source_sha256"] == hashlib.sha256(b"source text").hexdigest()
    assert manifest["preview_note_count"] == 1
    assert manifest["uploaded_at"].endswith("Z")


def test_existing_parser_stays_authoritative_for_docx(tmp_path):
    source = tmp_path / "brief.txt"
    source.write_text("existing parser", encoding="utf-8")
    result = parse_file(str(source))

    assert result.metadata["format"] == "txt"
    assert result.metadata.get("parser") is None


def test_document_analyzer_uses_owned_gateway_and_keeps_unavailable_truthful(monkeypatch):
    import lumenis.importer.analyzer as analyzer
    from lumenis.system.ai_gateway import core

    calls = []
    monkeypatch.setattr(
        core, "run_owned_analysis",
        lambda **kwargs: calls.append(kwargs) or {
            "ok": False, "status": "UNAVAILABLE", "code": "OWNED_RUNTIME_NOT_BOUND",
            "provider": "owned", "analysis": None,
        },
    )
    monkeypatch.setattr(core, "chat", lambda *_args, **_kwargs: pytest.fail("retired/provider fallback was called"))
    original_import = builtins.__import__

    def reject_retired(name, *args, **kwargs):
        if name == "ark_llm":
            pytest.fail("importer must not call the retired Ark route")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_retired)

    note = analyzer.analyze_text("广州太古汇的访客今天反馈排队较长。", ["广州太古汇"])[0]

    assert calls and "source text" in calls[0]["text"].casefold()
    assert note.analysis_status == "UNAVAILABLE"
    assert note.analysis_code == "OWNED_RUNTIME_NOT_BOUND"
    assert note.ai_provider == "unknown"
    assert note.sentiment == "unknown" and note.sentiment_score is None
    assert note.risk_level == "unknown" and note.risk_score is None
    assert note.summary == ""


def test_tabular_import_keeps_source_fields_separate_from_analysis():
    from lumenis.importer.analyzer import analyze_parsed
    from lumenis.importer.parser import ParseResult
    from lumenis.importer.service import _analysis_summary_payload, _note_to_dict

    parsed = ParseResult()
    parsed.metadata["format"] = "csv"
    parsed.tables = [[
        ["标题", "内容", "作者", "发布时间"],
        ["排队反馈", "今天排队时间太长，服务很好。", "访客A", "2026-10-05"],
    ]]

    notes = analyze_parsed(parsed, ["广州太古汇"])
    note = notes[0]
    payload = _note_to_dict(note)

    assert note.sentiment == "unknown" and note.sentiment_score is None
    assert note.risk_level == "unknown" and note.risk_score is None
    assert note.summary == ""
    assert note.analysis_status == "NOT_RUN"
    assert note.analysis_code == "STRUCTURED_ROW_ANALYSIS_NOT_RUN"
    assert note.keyword_method == "deterministic_source_terms"
    assert payload["analysis_status"] == "NOT_RUN"
    assert _analysis_summary_payload(notes) == {
        "analysis_status": "NOT_RUN",
        "analysis_completed_count": 0,
        "analysis_unavailable_count": 0,
        "analysis_not_run_count": 1,
    }


def test_import_analysis_summary_distinguishes_partial_from_not_run():
    from lumenis.importer.analyzer import AnalyzedNote
    from lumenis.importer.service import _analysis_summary_payload

    completed = AnalyzedNote()
    completed.analysis_status = "COMPLETED"
    unavailable = AnalyzedNote()
    unavailable.analysis_status = "UNAVAILABLE"
    not_run = AnalyzedNote()
    not_run.analysis_status = "NOT_RUN"

    assert _analysis_summary_payload([completed, unavailable]) == {
        "analysis_status": "PARTIAL",
        "analysis_completed_count": 1,
        "analysis_unavailable_count": 1,
        "analysis_not_run_count": 0,
    }
    assert _analysis_summary_payload([completed, not_run]) == {
        "analysis_status": "PARTIAL",
        "analysis_completed_count": 1,
        "analysis_unavailable_count": 0,
        "analysis_not_run_count": 1,
    }


def test_direct_notes_import_helper_is_retired():
    import lumenis.importer.service as service
    with pytest.raises(RuntimeError, match="DIRECT_NOTES_IMPORT_RETIRED_USE_CANONICAL_DOCUMENT_IMPORT"):
        service._insert_notes([])


def test_import_confirmation_uses_shared_document_owner_and_replays_receipt(tmp_path, monkeypatch):
    import lumenis.importer.documents as documents
    import lumenis.importer.service as service

    task_id = uuid.uuid4().hex
    task_dir = tmp_path / task_id
    task_dir.mkdir()
    source_path = task_dir / "brief.txt"
    source_bytes = b"Owner-approved source brief"
    source_path.write_bytes(source_bytes)
    scope = {
        "domain_id": "cth", "subject_id": "subject-1",
        "brand_focus_id": None, "global_scope": False,
    }
    manifest = {
        "schema": "import-preview/v1", "task_id": task_id, "state": "PREVIEWED",
        "actor_ref": "actor:17", "scope": scope, "original_filename": "brief.txt",
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_size_bytes": len(source_bytes), "uploaded_at": "2026-10-06T10:00:00Z",
        "preview_note_count": 1, "total_note_count": 1,
        "preview_analysis": {"analysis_status": "UNAVAILABLE"},
    }
    service._write_manifest(service._manifest_path(task_dir), manifest)
    monkeypatch.setattr(service, "UPLOAD_DIR", str(tmp_path))
    actor = object()
    calls = []

    def import_document(file_path, *, actor, scope, provenance):
        calls.append((file_path, actor, scope, provenance))
        return {
            "source_id": "DOC-123", "evidence_id": 42, "canonical_id": "CAN-123",
            "source_artifact_ref": "ART-123", "scope": scope, "replayed": False,
        }

    monkeypatch.setattr(documents, "import_document", import_document)
    body = {
        "task_id": task_id, "confirm_whole_source": True,
        "note_indices": [0], "target_table": "notes",
        "provenance": {
            "rights": "owner-approved",
            "content_origin": {"kind": "self-authored", "claim_type": "author_statement"},
        },
    }

    first = service._confirm_source_document(body, actor_ref="actor:17", scope=scope, actor=actor)
    second = service._confirm_source_document(body, actor_ref="actor:17", scope=scope, actor=actor)

    assert len(calls) == 1
    assert calls[0][1] is actor
    assert calls[0][2] == scope
    assert calls[0][3]["captured_at"] == "2026-10-06T10:00:00Z"
    assert calls[0][3]["source_origin"] == {
        "kind": "approved-file", "ref": "file-upload-" + hashlib.sha256(source_bytes).hexdigest(),
    }
    assert first["status"] == "SOURCE_IMPORTED"
    assert first["inserted_kind"] == "source_document"
    assert first["note_rows_inserted"] == 0
    assert first["document"]["canonical_id"] == "CAN-123"
    assert second["document"]["replayed"] is True
    assert second["inserted"] == 0
    assert not source_path.exists()


def test_import_confirmation_rejects_partial_note_selection(tmp_path, monkeypatch):
    import lumenis.importer.service as service

    task_id = uuid.uuid4().hex
    task_dir = tmp_path / task_id
    task_dir.mkdir()
    source_path = task_dir / "brief.txt"
    source_bytes = b"Source text"
    source_path.write_bytes(source_bytes)
    scope = {
        "domain_id": "cth", "subject_id": "subject-1",
        "brand_focus_id": None, "global_scope": False,
    }
    service._write_manifest(service._manifest_path(task_dir), {
        "schema": "import-preview/v1", "task_id": task_id, "state": "PREVIEWED",
        "actor_ref": "actor:17", "scope": scope, "original_filename": "brief.txt",
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_size_bytes": len(source_bytes), "uploaded_at": "2026-10-06T10:00:00Z",
        "preview_note_count": 2, "total_note_count": 2,
        "preview_analysis": {"analysis_status": "NOT_RUN"},
    })
    monkeypatch.setattr(service, "UPLOAD_DIR", str(tmp_path))

    with pytest.raises(ValueError, match="PARTIAL_NOTE_SELECTION_UNSUPPORTED_FOR_SOURCE_IMPORT"):
        service._confirm_source_document({
            "task_id": task_id, "confirm_whole_source": True, "note_indices": [0],
            "provenance": {
                "rights": "owner-approved",
                "content_origin": {"kind": "self-authored", "claim_type": "author_statement"},
            },
        }, actor_ref="actor:17", scope=scope, actor=object())
