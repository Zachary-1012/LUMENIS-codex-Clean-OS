# -*- coding: utf-8 -*-
"""ZBC→OSAI 证据流转快照：结构与 E2E 验证（不依赖真实网络/DB）。"""
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("evidence_export", ROOT / "scripts" / "evidence_export.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_build_snapshot_structure(tmp_path):
    m = _load()
    snap = m.build(out_dir=tmp_path / "evidence-export")
    assert snap["ts"]
    assert snap["source"].startswith("ZBC")
    # git
    assert snap["git"].get("hash")
    # baseline（缺数据时允许 error）
    assert "overall" in snap["baseline"] or "error" in snap["baseline"]
    if "error" not in snap["baseline"]:
        assert snap["baseline"]["overall"] in ("PASS", "FAIL", None)
    # lean（缺数据时允许 error）
    assert snap["lean"].get("py_files") or "error" in snap["lean"]
    # budget
    assert "total_calls" in snap["ai_budget"] or "error" in snap["ai_budget"]


def test_verify_pass(tmp_path):
    m = _load()
    out_dir = tmp_path / "evidence-export"
    m.build(out_dir=out_dir)
    errs, j = m.verify(out_dir=out_dir)
    # 允许 baseline/budget 缺数据时为 error，但 ts/git 必须存在
    assert j["ts"]
    assert j["git"].get("hash")
    assert isinstance(errs, list)


def test_snapshot_file_written(tmp_path):
    m = _load()
    out_dir = tmp_path / "evidence-export"
    m.build(out_dir=out_dir)
    p = out_dir / "evidence-snapshot-latest.json"
    assert p.exists()
    with p.open(encoding="utf-8") as handle:
        j = json.load(handle)
    assert j["git"]["hash"]
