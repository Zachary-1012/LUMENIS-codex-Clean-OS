# -*- coding: utf-8 -*-
"""SYSTEM Collector DLQ 的运维 CLI。

用法：
  python scripts/dlq_ops.py stats                       # DLQ 统计（pending/done/dead）
  python scripts/dlq_ops.py list [--limit 20]           # 列出 pending 任务
  python scripts/dlq_ops.py enqueue <keyword> --error <err> [--context <json>]
  python scripts/dlq_ops.py replay <module:handler> [--max 50]
        # handler(keyword, context) -> 成功 ack / 失败 fail_retry
        # 将已审核的应用 handler 以 module:handler 形式传入。
  python scripts/dlq_ops.py ack <task_id>
"""
import argparse
import importlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lumenis.system.collector.guard.dlq_replay import DeadLetterQueue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stats", "list", "enqueue", "replay", "ack"])
    ap.add_argument("arg", nargs="?", default="")
    ap.add_argument("--error", default="")
    ap.add_argument("--context", default="{}")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--max", type=int, default=50)
    args = ap.parse_args()

    dq = DeadLetterQueue()
    if args.cmd == "stats":
        print(json.dumps(dq.stats(), ensure_ascii=False, indent=1))
    elif args.cmd == "list":
        for r in dq.list_pending()[:args.limit]:
            print("%s  kw=%s  err=%s  at=%s  attempts=%s" % (
                r["task_id"], r.get("keyword"), r.get("error"), r.get("created_at"), r.get("attempts")))
    elif args.cmd == "enqueue":
        tid = dq.enqueue(args.arg, error=args.error, context=json.loads(args.context or "{}"))
        print("enqueued:", tid)
    elif args.cmd == "ack":
        print("acked:", dq.ack(args.arg))
    elif args.cmd == "replay":
        mod_name, _, fn = args.arg.partition(":")
        if not fn:
            print("need module:handler for an approved replay handler"); sys.exit(2)
        mod = importlib.import_module(mod_name)
        ok, fail = dq.replay(getattr(mod, fn), max_items=args.max)
        print("replayed ok=%d fail=%d" % (ok, fail))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
