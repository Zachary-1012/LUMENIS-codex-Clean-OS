from __future__ import annotations

import sys
import types
import builtins

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
