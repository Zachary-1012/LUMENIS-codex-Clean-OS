# -*- coding: utf-8 -*-
"""ZBC→OSAI 证据流转自动化（P1 全序列后的闭环扩展）。

把 ZBC 本地分散的 Evidence（git 头 / 生产基线 / Lean 度量 / AI 预算 / 测试收集）
聚合成一份 OSAI 可消费的证据快照，供 observatory-feed / learning 直接读取。

输出（staging/evidence-export/，gitignore）：
  evidence-snapshot-latest.json  最新快照（OSAI 引用入口）
  evidence-snapshot-<ts>.json    时间戳归档副本

用法：
  python scripts/evidence_export.py            # 生成快照并打印 JSON
  python scripts/evidence_export.py verify     # 校验最新快照结构，供 CI/E2E

全部数据均来自真实产物：不伪造任何字段；缺项写 {"error": "..."} 或空表。
"""
import datetime as _dt
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "staging", "evidence-export")
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
if not os.path.exists(PY):
    PY = sys.executable


def _read_json(path):
    try:
        with io_open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


def io_open(path, mode, encoding):
    return open(path, mode, encoding=encoding)


def _git_head():
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%H|%s|%ci"],
                             cwd=ROOT, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=10)
        h, s, c = out.stdout.strip().split("|", 2)
        return {"hash": h, "subject": s, "date": c}
    except Exception as e:
        return {"error": str(e)}


def _baseline():
    d = os.path.join(ROOT, "staging", "baseline-evidence")
    files = sorted([f for f in os.listdir(d) if f.endswith(".json")]) if os.path.isdir(d) else []
    if not files:
        return {"error": "no baseline-evidence"}
    p = os.path.join(d, files[-1])
    j = _read_json(p)
    return {
        "file": files[-1],
        "overall": j.get("overall"),
        "segments": j.get("segment_results"),
        "route_count": j.get("runtime", {}).get("checks", {}).get("route_count", {}).get("value"),
        "db": j.get("data", {}).get("row_counts"),
        "tests_collected": j.get("tests", {}).get("checks", {}).get("collected", {}).get("value"),
    }


def _lean():
    j = _read_json(os.path.join(ROOT, "staging", "lean-metrics.json"))
    if "error" in j:
        return j
    return {
        "ts": j.get("ts"),
        "py_files": j.get("source", {}).get("py_files"),
        "total_lines": j.get("source", {}).get("total_lines"),
        "unique_imports": j.get("source", {}).get("unique_top_imports"),
        "routes": j.get("runtime", {}).get("routes"),
        "tests_collected": j.get("tests", {}).get("collected"),
        "db_bytes": j.get("db", {}).get("db_bytes"),
        "tables": j.get("db", {}).get("tables"),
        "import_ms": j.get("runtime", {}).get("import_ms"),
    }


def _budget():
    try:
        out = subprocess.run([PY, os.path.join(ROOT, "scripts", "ai_budget.py"), "summary"],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=30)
        raw = out.stdout.strip()
        try:
            return json.loads(raw)
        except Exception:
            i = raw.find("{")
            return json.loads(raw[i:]) if i >= 0 else {"error": "unparseable: " + raw[:80]}
    except Exception as e:
        return {"error": str(e)}


def build(osai_dir=None):
    now = _dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    snap = {
        "ts": now,
        "source": "ZBC evidence_export (P1 closed-loop extension)",
        "git": _git_head(),
        "baseline": _baseline(),
        "lean": _lean(),
        "ai_budget": _budget(),
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    latest = os.path.join(OUT_DIR, "evidence-snapshot-latest.json")
    with io_open(latest, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    arch = os.path.join(OUT_DIR, "evidence-snapshot-%s.json" % now.replace(":", "").replace("-", "").replace("T", "-"))
    with io_open(arch, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    # ZBC→OSAI 证据流转：同步到 OSAI 仓库（git 管理，供 Observatory 消费）
    if osai_dir:
        o = os.path.join(osai_dir, "osai-ui", "evidence-snapshot.json")
        os.makedirs(os.path.dirname(o), exist_ok=True)
        with io_open(o, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=1)
        print("[evidence_export] synced -> %s" % o)
    return snap


def verify():
    p = os.path.join(OUT_DIR, "evidence-snapshot-latest.json")
    j = _read_json(p)
    errs = []
    for k in ("ts", "git", "baseline", "lean", "ai_budget"):
        if k not in j:
            errs.append("missing %s" % k)
    if "error" in j.get("git", {}):
        errs.append("git: " + str(j["git"]["error"]))
    if "error" in j.get("baseline", {}):
        errs.append("baseline: " + str(j["baseline"]["error"]))
    if "error" in j.get("ai_budget", {}):
        errs.append("ai_budget: " + str(j["ai_budget"]["error"]))
    return errs, j


def main():
    osai_dir = None
    args = [a for a in sys.argv[1:]]
    if "--osai" in args:
        i = args.index("--osai")
        osai_dir = args[i + 1] if i + 1 < len(args) else None
        args = args[:i] + args[i + 2:]
    snap = build(osai_dir=osai_dir)
    print(json.dumps(snap, ensure_ascii=False, indent=1))
    if args and args[0] == "verify":
        errs, _ = verify()
        print("EVIDENCE VERIFY:", "PASS" if not errs else "FAIL %s" % errs)
        sys.exit(0 if not errs else 1)


if __name__ == "__main__":
    main()
