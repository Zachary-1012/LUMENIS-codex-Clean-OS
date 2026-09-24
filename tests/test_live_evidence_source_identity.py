"""Mock-only regression for the live XHS Evidence side-write binding."""
import importlib
import sys
import tempfile
import types
from pathlib import Path


def test_live_persist_binds_source_scoped_evidence_dedupe(monkeypatch):
    isolated_db_path = Path(tempfile.gettempdir()) / "lumenis-live-evidence-unused.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(isolated_db_path))
    runtime_bin = types.ModuleType("runtime_bin")
    runtime_bin.resolve_node = lambda: "node"
    monkeypatch.setitem(sys.modules, "runtime_bin", runtime_bin)

    runtime = importlib.import_module("lumenis.system.collector.runtime")
    package_name = "lumenis.system.collector.runtime.xhs"
    package = types.ModuleType(package_name)
    package.__path__ = [str(Path(parent) / "xhs") for parent in runtime.__path__]
    monkeypatch.setitem(sys.modules, package_name, package)
    monkeypatch.delitem(sys.modules, package_name + ".live_engine", raising=False)
    live_engine = importlib.import_module(package_name + ".live_engine")

    import canonical_data
    import database
    from lumenis.shared import evidence

    captured = {}

    class CaptureOnlyEvidenceChain:
        def __init__(self, db_path):
            captured["db_path"] = db_path

        def capture_and_canonicalize(self, **kwargs):
            captured["evidence_call"] = kwargs

    class NoopConnection:
        def commit(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(evidence, "EvidenceChain", CaptureOnlyEvidenceChain)
    monkeypatch.setattr(live_engine, "normalize_note", lambda note: dict(note))
    monkeypatch.setattr(live_engine, "deduplicate", lambda notes: notes)
    monkeypatch.setattr(live_engine, "filter_subject", lambda notes, _predicate: notes)
    monkeypatch.setattr(database, "DB_PATH", str(isolated_db_path))
    monkeypatch.setattr(database, "insert_note", lambda _note: None)
    monkeypatch.setattr(database, "save_collector_quality", lambda *_args: None)
    monkeypatch.setattr(database, "upsert_note_comments", lambda *_args: None)
    monkeypatch.setattr(canonical_data, "ensure_canonical_table", lambda _path: None)
    monkeypatch.setattr(canonical_data, "note_to_canonical", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(canonical_data, "get_connection", lambda _path: NoopConnection())
    monkeypatch.setattr(canonical_data, "persist_canonical", lambda *_args: "inserted")

    note = {
        "note_id": "source-a",
        "url": "https://public.example.test/source-a",
        "title": "same title",
        "content": "same content",
        "data_quality": {},
        "comments_data": [],
    }
    result = live_engine.persist_live({"notes": [note]}, lambda _text: True)

    assert result["ok"] is True
    assert result["persisted"] == 1
    assert captured["evidence_call"]["source_id"] == "source-a"
    assert captured["evidence_call"]["source_url"] == note["url"]
    assert captured["evidence_call"]["dedupe_by_source"] is True
