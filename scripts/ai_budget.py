# -*- coding: utf-8 -*-
"""AI Budget Manager（MAX-EFFICIENCY / LOW-Doubao-COST MODE 治理件）。

自动记录每次 AI 调用（provider/model/task/成功失败/耗时/估算token），
落盘 staging/ai-budget.jsonl（gitignore）。提供汇总 CLI 供 Observatory 消费。

用法：
  python scripts/ai_budget.py record <provider> <model> <task> <ok> <elapsed> <tokens> [note]
  python scripts/ai_budget.py summary [--last N]
  python scripts/ai_budget.py status            # 输出 JSON（Observatory 数据源）
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "staging", "ai-budget.jsonl")

# 豆包预算治理阈值：豆包占比上限，超出自动提示降级
DOUBAO_MAX_SHARE = 0.15


def _ensure():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)


def record(provider, model, task, ok, elapsed_s, tokens_est, note=""):
    _ensure()
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "provider": provider,
        "model": model or provider,
        "task": task,
        "ok": bool(ok),
        "elapsed_s": round(float(elapsed_s), 2),
        "tokens_est": int(tokens_est),
        "note": note,
    }
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def _read_all():
    if not os.path.exists(LOG):
        return []
    rows = []
    for ln in open(LOG, encoding="utf-8"):
        ln = ln.strip()
        if ln:
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return rows


def summary(last=None):
    rows = _read_all()
    if last:
        rows = rows[-int(last):]
    by_provider = {}
    total_tok = 0
    ok_n = 0
    for r in rows:
        p = r["provider"]
        by_provider.setdefault(p, {"calls": 0, "ok": 0, "tokens": 0, "elapsed": 0.0})
        by_provider[p]["calls"] += 1
        by_provider[p]["ok"] += 1 if r["ok"] else 0
        by_provider[p]["tokens"] += r["tokens_est"]
        by_provider[p]["elapsed"] += r["elapsed_s"]
        total_tok += r["tokens_est"]
        ok_n += 1 if r["ok"] else 0
    n = len(rows)
    doubao_calls = by_provider.get("doubao", {}).get("calls", 0)
    doubao_share = doubao_calls / n if n else 0.0
    return {
        "total_calls": n,
        "success_rate": round(ok_n / n, 3) if n else 0.0,
        "total_tokens_est": total_tok,
        "doubao_calls": doubao_calls,
        "doubao_share": round(doubao_share, 3),
        "doubao_over_threshold": doubao_share > DOUBAO_MAX_SHARE,
        "by_provider": by_provider,
    }


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: ai_budget.py record|summary|status ...")
        return 1
    cmd = args[0]
    if cmd == "record" and len(args) >= 7:
        r = record(args[1], args[2], args[3], args[4] == "1", args[5], args[6], args[7] if len(args) > 7 else "")
        print(json.dumps(r, ensure_ascii=False))
        return 0
    if cmd == "summary":
        s = summary(args[1] if len(args) > 1 else None)
        print(json.dumps(s, ensure_ascii=False, indent=1))
        return 0
    if cmd == "status":
        print(json.dumps(summary(), ensure_ascii=False))
        return 0
    print("unknown cmd")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
