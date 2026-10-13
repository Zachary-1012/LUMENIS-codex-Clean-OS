# -*- coding: utf-8 -*-
"""AI Usage Budget Manager.

自动记录每次 AI 调用（provider/model/task/成功失败/耗时/估算token），
落盘 staging/ai-budget.jsonl（gitignore），并提供汇总 CLI 供 Observatory 消费。

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


def _ensure():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)


def record(provider, model, task, ok, elapsed_s, tokens_est, note="",
           in_tokens=None, out_tokens=None, cache_hit=None):
    """记录一次 AI 调用。in_tokens/out_tokens/cache_hit 为 prompt-cache 可观测（可选）。

    cache_hit: True=命中缓存 / False=未命中 / None=未知。
    研究自 llm-api-pricing：cached input 定价远低于非缓存（agent mix 约 95.6% 缓存占比），
    固定 system 前缀最大化缓存命中是降本关键。
    """
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
    if in_tokens is not None:
        row["in_tokens"] = int(in_tokens)
    if out_tokens is not None:
        row["out_tokens"] = int(out_tokens)
    if cache_hit is not None:
        row["cache_hit"] = bool(cache_hit)
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
    # prompt-cache 可观测：cache_hit 占比 + input/output token 分离
    cache_known = [r for r in rows if r.get("cache_hit") is not None]
    cache_hits = sum(1 for r in cache_known if r["cache_hit"])
    in_tok = sum(r.get("in_tokens", 0) for r in rows)
    out_tok = sum(r.get("out_tokens", 0) for r in rows)
    return {
        "total_calls": n,
        "success_rate": round(ok_n / n, 3) if n else 0.0,
        "total_tokens_est": total_tok,
        "by_provider": by_provider,
        "cache": {
            "known": len(cache_known),
            "hit": cache_hits,
            "hit_rate": round(cache_hits / len(cache_known), 3) if cache_known else None,
            "in_tokens": in_tok,
            "out_tokens": out_tok,
            "cacheable_input_share": round(in_tok / total_tok, 3) if total_tok else None,
        },
    }


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: ai_budget.py record|summary|status ...")
        return 1
    cmd = args[0]
    if cmd == "record" and len(args) >= 7:
        # 可选: --in <int> --out <int> --cache <1|0> --note <text>
        in_t = out_t = cache = None
        note = ""
        rest = args[7:]
        i = 0
        while i < len(rest):
            if rest[i] == "--in" and i + 1 < len(rest):
                in_t = int(rest[i + 1]); i += 2
            elif rest[i] == "--out" and i + 1 < len(rest):
                out_t = int(rest[i + 1]); i += 2
            elif rest[i] == "--cache" and i + 1 < len(rest):
                cache = rest[i + 1] == "1"; i += 2
            elif rest[i] == "--note" and i + 1 < len(rest):
                note = rest[i + 1]; i += 2
            else:
                note = (note + " " + rest[i]).strip(); i += 1
        r = record(args[1], args[2], args[3], args[4] == "1", args[5], args[6], note,
                   in_tokens=in_t, out_tokens=out_t, cache_hit=cache)
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
