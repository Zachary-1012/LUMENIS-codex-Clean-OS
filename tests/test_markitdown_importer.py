from __future__ import annotations

import sys
import types
import builtins
import sqlite3

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


def test_tabular_import_persists_unknown_analysis_without_claiming_ai(tmp_path, monkeypatch):
    from lumenis.importer.analyzer import analyze_parsed
    from lumenis.importer.parser import ParseResult
    import lumenis.importer.service as service
    from lumenis.shared.database.business_schema import apply_business_schema

    database_path = tmp_path / "importer.db"
    with sqlite3.connect(database_path) as connection:
        apply_business_schema(connection)

    class IsolatedRepository:
        def connect(self):
            return sqlite3.connect(database_path)

    monkeypatch.setattr(service, "get_repository", IsolatedRepository)
    parsed = ParseResult()
    parsed.metadata["format"] = "csv"
    parsed.tables = [[
        ["标题", "内容"],
        ["餐饮体验", "口味不错，但排队很久。"],
    ]]
    note = analyze_parsed(parsed)[0]

    assert service._insert_notes([note]) == 1
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT sentiment, sentiment_score, risk_level, risk_score, ai_provider, ai_analyzed_at, summary "
            "FROM notes"
        ).fetchone()

    assert row == ("unknown", None, "unknown", None, "unknown", "", "")
