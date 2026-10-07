"""Mock-only regression for XHS canonical-owner and DB-path binding.

The test executes only ``_bypass_evidence_canonical_live``. Canonical and
Evidence/lifecycle persistence are fakes, so no browser, account profile,
Cookie, or SQLite database is opened.
"""
import ast
import builtins
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace


def _source_functions(source_path: Path) -> list[ast.FunctionDef]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in {"resolve_live_scope", "_bypass_evidence_canonical_live"}]
    if {node.name for node in functions} != {"resolve_live_scope", "_bypass_evidence_canonical_live"}:
        raise AssertionError("live scope resolver and Evidence writer were not found")
    return functions


def test_bypass_uses_current_shared_database_path_for_both_side_writes(
    tmp_path, monkeypatch
):
    repo = Path(__file__).resolve().parents[1]
    source_path = repo / "lumenis/system/collector/runtime/xhs/live_engine.py"
    owner_path = repo / "lumenis/shared/database/paths.py"
    spec = importlib.util.spec_from_file_location("isolated_shared_db_paths", owner_path)
    assert spec is not None and spec.loader is not None
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)

    import_time_path = tmp_path / "captured-at-import.db"
    call_time_path = tmp_path / "selected-at-call.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(import_time_path))
    stale_database = SimpleNamespace(DB_PATH=owner.main_db_path())
    monkeypatch.setenv("ZBC_DB_PATH", str(call_time_path))

    observed = {"evidence_paths": [], "evidence_calls": [], "ensure": [], "connection": [], "persist": []}

    class FakeEvidenceChain:
        def __init__(self, db_path):
            observed["evidence_paths"].append(os.path.abspath(db_path))

        def capture_evidence_for_canonical(self, **kwargs):
            observed["evidence_calls"].append(kwargs)
            return {"evidence": SimpleNamespace(evidence_id="evidence-1")}

    class FakeConnection:
        def commit(self):
            pass

        def close(self):
            pass

    def ensure_canonical_table(db_path):
        observed["ensure"].append(os.path.abspath(db_path))

    def get_connection(db_path):
        observed["connection"].append(os.path.abspath(db_path))
        return FakeConnection()

    def persist_canonical(_connection, _record):
        observed["persist"].append(True)

    evidence_module = SimpleNamespace(EvidenceChain=FakeEvidenceChain)
    shared_database_module = SimpleNamespace(main_db_path=owner.main_db_path)
    canonical_module = SimpleNamespace(
        ensure_canonical_table=ensure_canonical_table,
        note_to_canonical=lambda _note, **_kwargs: SimpleNamespace(canonical_id="canonical-1"),
        get_connection=get_connection,
        persist_canonical=persist_canonical,
    )
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "lumenis.shared.evidence":
            return evidence_module
        if name == "lumenis.shared.database":
            return shared_database_module
        if name == "canonical_data":
            return canonical_module
        return original_import(name, globals, locals, fromlist, level)

    safe_builtins = dict(vars(builtins))
    safe_builtins["__import__"] = fake_import
    namespace = {"database": stale_database, "__builtins__": safe_builtins}
    function_module = ast.Module(body=_source_functions(source_path), type_ignores=[])
    exec(compile(function_module, str(source_path), "exec"), namespace)
    namespace["_bypass_evidence_canonical_live"](
        {
            "note_id": "synthetic-note-1",
            "title": "mock title",
            "content": "mock content",
            "url": "https://example.invalid/mock-note",
        },
        domain_id="cth", product_id="CTH", subject_id="GUANGZHOU_TAIKOO_HUI",
    )

    expected_path = os.path.abspath(str(call_time_path))
    stale_path = os.path.abspath(str(import_time_path))
    assert stale_database.DB_PATH == stale_path
    assert observed["evidence_paths"] == [expected_path]
    assert observed["evidence_calls"][0]["canonical_id"] == "canonical-1"
    assert observed["evidence_calls"][0]["source_id"] == "synthetic-note-1"
    assert observed["ensure"] == [expected_path]
    assert observed["connection"] == [expected_path]
    assert observed["persist"] == [True]
    assert not import_time_path.exists()
    assert not call_time_path.exists()
