# -*- coding: utf-8 -*-
"""Observatory 数据源（P0-D 最小可运行版）。

聚合 AI Budget + ZELL Trace + 生产基线 Evidence + Git 状态 + 测试汇总，
输出统一 JSON，供 Observatory UI 消费。所有数据来自真实 Runtime/Evidence，禁止硬编码。

用法：
  python scripts/observatory_feed.py [--out <json>]
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import ai_budget  # noqa: E402


def _latest_baseline():
    d = os.path.join(ROOT, "staging", "baseline-evidence")
    if not os.path.isdir(d):
        return None
    files = sorted(os.listdir(d))
    if not files:
        return None
    p = os.path.join(d, files[-1])
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def _git_head():
    try:
        r = subprocess.run(["git", "-C", ROOT, "log", "--oneline", "-1"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else "n/a"
    except Exception:
        return "n/a"


def _zell():
    p = os.path.join(ROOT, "staging", "zell-trace.jsonl")
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def main():
    feed = {
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S"),
        "git_head": _git_head(),
        "ai_budget": ai_budget.summary(),
        "zell_phases": {},
        "baseline": _latest_baseline(),
    }
    zell = _zell()
    for r in zell:
        ph = r["event"]
        feed["zell_phases"].setdefault(ph, 0)
        feed["zell_phases"][ph] += 1
    feed["zell_total"] = len(zell)

    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    blob = json.dumps(feed, ensure_ascii=False, indent=1)
    if out:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w", encoding="utf-8").write(blob)
        print(f"written {out}")
    else:
        print(blob)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
