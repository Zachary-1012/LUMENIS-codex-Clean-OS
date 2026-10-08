# -*- coding: utf-8 -*-
"""Lean Engineering / Small Footprint 度量基线（P0-F）。

在功能不减、数据不丢前提下，量化 ZBC 源码体量/依赖/耦合/Runtime/Frontend/Test/DB，
产出可复现基线 staging/lean-metrics.json（gitignore），供后续瘦身对照与 Observatory 消费。

用法：
  python scripts/lean_footprint.py [--out <json>]
"""
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# 统计范围：顶层业务源码（排除 venv/.git/staging/tests/archive）
EXCLUDE_DIRS = {".git", ".venv", "staging", "archive", "node_modules", "static", "data", "logs", "docs-wps", "__pycache__"}
PY_EXT = {".py"}


def _iter_py():
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for fn in files:
            if fn.endswith(".py"):
                yield os.path.join(root, fn)


def measure_source():
    files = list(_iter_py())
    total_lines = 0
    total_bytes = 0
    import_counts = {}
    endpoint_count = {}
    longest = []
    for fp in files:
        try:
            sz = os.path.getsize(fp)
            n = sum(1 for _ in open(fp, encoding="utf-8", errors="replace"))
            total_bytes += sz
            total_lines += n
            rel = os.path.relpath(fp, ROOT)
            longest.append((n, rel))
            for ln in open(fp, encoding="utf-8", errors="replace"):
                s = ln.strip()
                if s.startswith("import ") or s.startswith("from "):
                    # 取顶层模块名
                    m = re.match(r"(?:import|from)\s+([A-Za-z_][A-Za-z0-9_.]*)", s)
                    if m:
                        top = m.group(1).split(".")[0]
                        import_counts[top] = import_counts.get(top, 0) + 1
        except Exception:
            continue
    longest.sort(reverse=True)
    return {
        "py_files": len(files),
        "total_lines": total_lines,
        "total_bytes": total_bytes,
        "avg_lines_per_file": round(total_lines / len(files), 1) if files else 0,
        "top_imports": sorted(import_counts.items(), key=lambda x: -x[1])[:15],
        "unique_top_imports": len(import_counts),
        "top10_largest_files": [(l, rel) for l, rel in longest[:10]],
    }


def measure_runtime():
    t0 = time.time()
    try:
        import app as A
        import_ms = round((time.time() - t0) * 1000)
        routes = len(list(A.app.url_map.iter_rules()))
        blueprints = len({r.endpoint.split(".")[0] for r in A.app.url_map.iter_rules() if "." in r.endpoint})
        return {"import_ms": import_ms, "routes": routes, "blueprint_prefixes": blueprints}
    except Exception as e:  # noqa: BLE001
        return {"import_ms": None, "error": repr(e)}


def measure_tests():
    # Retain schema/history without importing or collecting module test suites.
    return {"collected": None, "executed": False,
            "status": "NOT_REQUIRED_BY_PO_POLICY",
            "reason": "PO-20261008-REAL-OUTCOME-POLICY-C1-RESUME"}


def measure_db():
    try:
        import database
        import sqlite3
        p = database.DB_PATH
        if not os.path.exists(p):
            return {"db": None, "error": "db missing"}
        sz = os.path.getsize(p)
        con = sqlite3.connect(p, timeout=30)
        try:
            tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            rows = sum(con.execute(f"SELECT COUNT(*) FROM [{t[0]}]").fetchone()[0] for t in tables)
            return {"db_bytes": sz, "tables": len(tables), "total_rows": rows}
        finally:
            con.close()
    except Exception as e:  # noqa: BLE001
        return {"db": None, "error": repr(e)}


def measure_frontend():
    st = os.path.join(ROOT, "static")
    if not os.path.isdir(st):
        # The retired web client is intentionally absent. Keep the metric
        # schema stable so downstream reports can represent zero bytes.
        return {"frontend_bytes": 0, "frontend_files_by_ext": {}}
    total = 0
    counts = {}
    for root, _, files in os.walk(st):
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                total += os.path.getsize(fp)
            except Exception:
                continue
            ext = os.path.splitext(fn)[1].lower()
            counts[ext] = counts.get(ext, 0) + 1
    return {"frontend_bytes": total, "frontend_files_by_ext": counts}


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    report = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": measure_source(),
        "runtime": measure_runtime(),
        "tests": measure_tests(),
        "db": measure_db(),
        "frontend": measure_frontend(),
    }
    blob = json.dumps(report, ensure_ascii=False, indent=1)
    if out:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w", encoding="utf-8").write(blob)
        print(f"written {out}")
    else:
        print(blob)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
