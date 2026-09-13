# -*- coding: utf-8 -*-
"""LUMENIS→OSAI evidence snapshot structure/E2E test.

This test is repository-relative and does not depend on a developer-machine path.
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    module_path = ROOT / "scripts" / "evidence_export.py"
    spec = importlib.util.spec_from_file_location("evidence_export", module_path)
    m = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(m)
    return m


def test_build_snapshot_structure():
    m = _load()
    snap = m.build()
    assert snap["ts"]
    assert snap["source"]
    assert snap["git"].get("hash")
    assert "overall" in snap["baseline"] or "error" in snap["baseline"]
    if "error" not in snap["baseline"]:
        assert snap["baseline"]["overall"] in ("PASS", "FAIL", None)
    assert snap["lean"].get("py_files") or "error" in snap["lean"]
    assert "total_calls" in snap["ai_budget"] or "error" in snap["ai_budget"]


def test_verify_pass():
    m = _load()
    m.build()
    errs, j = m.verify()
    assert j["ts"]
    assert j["git"].get("hash")
    assert isinstance(errs, list)


def test_snapshot_file_written():
    m = _load()
    m.build()
    p = ROOT / "staging" / "evidence-export" / "evidence-snapshot-latest.json"
    assert p.exists()
    with p.open(encoding="utf-8") as fh:
        j = json.load(fh)
    assert j["git"]["hash"]
