# -*- coding: utf-8 -*-
"""ZELL Trace（Evidence-driven Engineering Learning Loop）。

程序自动记录每次施工的 Task→Research→Architecture→Code→Test→Runtime→Evidence→Evaluation→Learning，
落盘 staging/zell-trace.jsonl（gitignore）。由施工方在关键节点调用，无需人工维护。

用法：
  python scripts/zell_trace.py begin <task> [note]
  python scripts/zell_trace.py phase <task> <phase> <detail>
  python scripts/zell_trace.py done <task> <outcome>
  python scripts/zell_trace.py show [--last N]
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "staging", "zell-trace.jsonl")
PHASES = ("research", "architecture", "code", "test", "runtime", "evidence", "evaluation", "learning")


def _ensure():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)


def _append(row):
    _ensure()
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def begin(task, note=""):
    _append({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "task": task, "event": "begin", "note": note})
    print(f"[zell] begin {task}")


def phase(task, ph, detail):
    if ph not in PHASES:
        print(f"[zell] unknown phase {ph}, skip")
        return
    _append({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "task": task, "event": ph, "detail": detail})
    print(f"[zell] {ph} <- {detail[:80]}")


def done(task, outcome):
    _append({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "task": task, "event": "done", "outcome": outcome})
    print(f"[zell] done {task}: {outcome[:80]}")


def show(last=None):
    if not os.path.exists(LOG):
        print("[]")
        return
    rows = [json.loads(l) for l in open(LOG, encoding="utf-8") if l.strip()]
    if last:
        rows = rows[-int(last):]
    print(json.dumps(rows, ensure_ascii=False, indent=1))


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    c = args[0]
    if c == "begin" and len(args) >= 2:
        begin(args[1], args[2] if len(args) > 2 else "")
    elif c == "phase" and len(args) >= 4:
        phase(args[1], args[2], args[3])
    elif c == "done" and len(args) >= 3:
        done(args[1], args[2])
    elif c == "show":
        show(args[1] if len(args) > 1 else None)
    else:
        print("bad args")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
