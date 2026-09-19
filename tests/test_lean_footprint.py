# -*- coding: utf-8 -*-
"""P0-F Lean Footprint 冒烟测试：脚本可运行且输出关键度量字段。"""
import importlib.util
import json
import os
import subprocess
import sys
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "lean_footprint.py")


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    out = tmp_path_factory.mktemp("lean") / "m.json"
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, SCRIPT, "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True, timeout=300, env=env)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.load(open(out, encoding="utf-8"))


def test_has_source_metrics(result):
    s = result["source"]
    assert s["py_files"] > 300
    assert s["total_lines"] > 30000
    assert s["unique_top_imports"] > 50


def test_has_runtime_metrics(result):
    rt = result["runtime"]
    assert rt["routes"] > 300


def test_has_test_metrics(result):
    assert result["tests"]["collected"] > 300


def test_has_db_and_frontend(result):
    assert result["db"]["tables"] >= 20
    # UI HARD RESET 后旧前端已清除，新前端待重建；frontend_bytes 允许为 0
    assert result["frontend"]["frontend_bytes"] >= 0
