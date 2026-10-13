"""PPTX text-export regressions; library readback is not Office-app acceptance."""
import builtins
import io
import json
import os
import socket
import sqlite3
import zipfile

import pytest

from lumenis.shared.reporting.word_pdf_export import (
    ReportExporter,
)


def snapshot():
    long_line = "长文本片段🙂 / 中文 / café / tab\t保留。" * 220
    return {
        "schema": "lumenis.saved-work/v1",
        "title": "标题 / Research / 자료 😀\t完整保留",
        "markdown": (
            "首段：来源和范围保留。\n"
            + long_line
            + "\n한국어와中文段落、emoji 🧭、literal <tag> & 原样。"
        ),
        "kind": "research",
        "payload": {"saved_marker": "SNAPSHOT-COMPLETE-7", "long_text": long_line},
        "citations": [],
        "context": {
            "domain_id": "cth",
            "subject_id": "subject-7",
            "brand_focus_id": None,
            "global_scope": False,
            "actor_id": 19,
        },
        "work_id": "WORK-0123456789abcdef01234567",
        "version": 3,
        "request_id": "pptx-export-0001",
        "parent_artifact_id": "ART-0123456789abcdef",
    }


def source_rows():
    return [{
        "evidence_id": 71,
        "source_id": "SRC-PPTX-7",
        "source_url": "https://example.invalid/source/中文?q=editable",
        "scope": {"domain_id": "cth", "subject_id": "subject-7",
                  "brand_focus_id": None, "global_scope": False},
        "rights": "owner-approved test text; no product-fact claim",
        "quote": "引用内容：完整来源文字 😀",
    }]


def _read_sections(raw):
    from pptx import Presentation

    presentation = Presentation(io.BytesIO(raw))
    content = {}
    for slide in presentation.slides:
        assert len(slide.shapes) == 2
        heading, body = slide.shapes[0], slide.shapes[1]
        heading_text = heading.text_frame.text
        assert heading_text.startswith("Saved document | ")
        label = heading_text.removeprefix("Saved document | ").split(" (continued ", 1)[0]
        content.setdefault(label, []).extend(p.text for p in body.text_frame.paragraphs)
    return presentation, content


def _expected_paragraphs(text):
    lines = text.splitlines()
    if not lines:
        lines = [""]
    if text.endswith(("\n", "\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029")):
        lines.append("")
    result = []
    for line in lines:
        if not line:
            result.append("")
        else:
            result.extend(line[start:start + 64] for start in range(0, len(line), 64))
    return result or [""]


def test_saved_work_pptx_is_editable_and_preserves_every_section_in_memory(
    monkeypatch, tmp_path,
):
    import pptx
    import lumenis.shared.database as database

    assert pptx.__version__ == "1.0.2"

    def forbidden(*args, **kwargs):
        raise AssertionError("PPTX memory export must not access a path, database, or network")

    original_open = builtins.open
    original_io_open = io.open

    def no_path_write(open_fn):
        def guarded(path, mode="r", *args, **kwargs):
            if any(flag in mode for flag in ("w", "a", "x", "+")):
                forbidden(path, mode, *args, **kwargs)
            return open_fn(path, mode, *args, **kwargs)
        return guarded

    monkeypatch.setattr(os, "makedirs", forbidden)
    monkeypatch.setattr(builtins, "open", no_path_write(original_open))
    monkeypatch.setattr(io, "open", no_path_write(original_io_open))
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    monkeypatch.setattr(database, "get_repository", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)

    document, sources = snapshot(), source_rows()
    before = set(tmp_path.iterdir())
    raw = ReportExporter.export_saved_document(document, sources=sources, format="pptx")
    assert set(tmp_path.iterdir()) == before
    assert raw.startswith(b"PK")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert archive.testzip() is None
        assert "ppt/presentation.xml" in archive.namelist()

    presentation, exported = _read_sections(raw)
    assert len(presentation.slides) > 1
    for slide in presentation.slides:
        for shape in slide.shapes:
            assert 0 <= shape.left < presentation.slide_width
            assert 0 <= shape.top < presentation.slide_height
            assert shape.left + shape.width <= presentation.slide_width
            assert shape.top + shape.height <= presentation.slide_height
    expected = dict(zip(
        ("Title", "Report", "Lineage", "Sources", "Snapshot", "JSON"),
        (document["title"], document["markdown"],
         "Sources / original scope / rights",
         json.dumps(sources, ensure_ascii=False, indent=2),
         "Complete saved snapshot",
         json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)),
    ))
    assert set(exported) == set(expected)
    for label, text in expected.items():
        assert exported[label] == _expected_paragraphs(text)
    assert "标题 / Research / 자료 😀\t完整保留" in "".join(exported["Title"])
    assert "Sources / original scope / rights" in "".join(exported["Lineage"])
    assert "https://example.invalid/source/中文?q=editable" in "".join(exported["Sources"])
    assert "SNAPSHOT-COMPLETE-7" in "".join(exported["JSON"])
    assert any(shape.has_text_frame and shape.text_frame.text
               for slide in presentation.slides for shape in slide.shapes)


def test_saved_work_pptx_rejects_oversized_snapshot_without_partial_bytes():
    document = snapshot()
    document["markdown"] = "超大输出" * 250_000
    with pytest.raises(ValueError, match="^WORK_EXPORT_PPTX_TOO_LARGE$"):
        ReportExporter.export_saved_document(document, sources=source_rows(), format="pptx")


def test_saved_work_export_still_rejects_unsupported_format():
    with pytest.raises(ValueError, match="^unsupported saved document export format$"):
        ReportExporter.export_saved_document(snapshot(), sources=source_rows(), format="keynote")
