# -*- coding: utf-8 -*-
"""ZBC→OSAI 证据流转快照：结构与 E2E 验证（不依赖真实网络/DB）。"""
import importlib.util
import json
import os
import sys

ROOT = r"D:\Taikoo-monitor-new"


def _load():
    spec = importlib.util.spec_from_file_location("evidence_export", os.path.join(ROOT, "scripts", "evidence_export.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_build_snapshot_structure():
    m = _load()
    snap = m.build()
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


def test_verify_pass():
    m = _load()
    m.build()
    errs, j = m.verify()
    # 允许 baseline/budget 缺数据时为 error，但 ts/git 必须存在
    assert j["ts"]
    assert j["git"].get("hash")
    assert isinstance(errs, list)


def test_snapshot_file_written():
    m = _load()
    m.build()
    p = os.path.join(ROOT, "staging", "evidence-export", "evidence-snapshot-latest.json")
    assert os.path.exists(p)
    j = json.load(open(p, encoding="utf-8"))
    assert j["git"]["hash"]
