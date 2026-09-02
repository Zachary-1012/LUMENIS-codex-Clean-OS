# -*- coding: utf-8 -*-
"""采集运维控制面 CLI（研究自 baldur System-Control，落地 ZBC）。

用法：
  python scripts/runtime_switch_ops.py status                      # 当前状态
  python scripts/runtime_switch_ops.py disable <reason>           # Kill Switch（必填 reason）
  python scripts/runtime_switch_ops.py enable                      # 重新启用
  python scripts/runtime_switch_ops.py dry-run on | off            # 演练/观察模式
  python scripts/runtime_switch_ops.py audit [limit]               # 翻转审计轨迹
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from collector_guard.runtime_switch import get_switch  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "disable", "enable", "dry-run", "audit"])
    ap.add_argument("arg", nargs="?", default="")
    ap.add_argument("--actor", default="cli")
    args = ap.parse_args()

    sw = get_switch()
    if args.cmd == "status":
        print(json.dumps(sw.status(), ensure_ascii=False, indent=1))
    elif args.cmd == "disable":
        print(json.dumps(sw.set_enabled(False, reason=args.arg, actor=args.actor), ensure_ascii=False))
    elif args.cmd == "enable":
        print(json.dumps(sw.set_enabled(True, confirm=True, reason=args.arg, actor=args.actor), ensure_ascii=False))
    elif args.cmd == "dry-run":
        on = args.arg == "on"
        print(json.dumps(sw.set_dry_run(on, confirm=(not on)), ensure_ascii=False))
    elif args.cmd == "audit":
        for r in sw.audit_trail(limit=int(args.arg or 20)):
            print("%s  %-12s actor=%s reason=%s" % (r["ts"], r["action"], r.get("actor"), r.get("reason")))


if __name__ == "__main__":
    main()
