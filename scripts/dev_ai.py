# -*- coding: utf-8 -*-
"""Zachary AI 研发辅助 CLI（智谱算力优先，豆包最低辅助）。

默认使用智谱旗舰 glm-4.7（config/ai-quota.json 实证），失败自动回退 glm-4.5-air。
每次智谱调用自动记录到 AI Budget（staging/ai-budget.jsonl，gitignore）。

用法：
  python scripts/dev_ai.py health-capabilities [--model glm-4.7]
  python scripts/dev_ai.py summarize <file> <prompt> [--model glm-4.7]

智谱 key 仅从 .env 读取，绝不打印/入库。
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import ai_budget  # noqa: E402

DEFAULT_MODEL = "glm-4.7"   # 旗舰（500万 tokens 资源包，2026-09-03 生效）
FALLBACK_MODEL = "glm-4.5-air"


def _load_dotenv():
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, _, v = ln.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _chat_budgeted(system, user, task, model=None, max_tokens=1200):
    import intelligence
    chosen = model or DEFAULT_MODEL
    t0 = time.time()
    try:
        out, provider = intelligence._chat(system, user, max_tokens=max_tokens, model=chosen)
    except TypeError:
        # 旧签名无 model 参数（巡检未合入时）回退
        out, provider = intelligence._chat(system, user, max_tokens=max_tokens)
        chosen = None
    if not out and provider != "zhipu":
        out, provider = intelligence._chat(system, user, max_tokens=max_tokens, model=FALLBACK_MODEL)
        chosen = FALLBACK_MODEL
    elapsed = round(time.time() - t0, 2)
    model_name = chosen or ("glm-4.5-air" if provider == "zhipu" else provider)
    ai_budget.record(
        provider=provider or "local",
        model=model_name,
        task=task,
        ok=bool(out),
        elapsed_s=elapsed,
        tokens_est=(len(out or "") * 2) if out else 0,
        note=f"requested={chosen or 'default'}",
    )
    return out, provider, model_name


def main():
    _load_dotenv()
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    model = None
    if "--model" in args:
        i = args.index("--model")
        if i + 1 < len(args):
            model = args[i + 1]
            args = args[:i] + args[i + 2:]
    task = args[0]

    if task == "health-capabilities":
        files = [
            "health_check.py", "health.py", "health_center.py", "healthcheck.py",
            "_healthcheck.py", "_health_collect.py", "system_health_api.py",
            "resident_health.py", "metrics.py",
        ]
        system = (
            "你是 Zachary AI 的资深工程架构师。任务是做 Capability/Contract/Ownership 收敛分析，"
            "遵守：一个 Capability 一个 Canonical Implementation；功能零减配；删除需 Evidence。"
            "输出用紧凑中文分点，禁止编造函数名。"
        )
        user = "以下为 ZBC 仓库 health/监控相关模块候选文件（含路径与职责线索），请按 Capability 分组给出收敛建议：\n"
        for f in files:
            p = os.path.join(ROOT, f)
            if os.path.exists(p):
                head = open(p, encoding="utf-8", errors="replace").read(1200)
                user += f"\n--- {f} ---\n{head}\n"
        out, provider, mname = _chat_budgeted(system, user, task, model=model, max_tokens=1500)
        if not out:
            print("[dev_ai] zhipu 不可用，降级本地规则结论（见矩阵 P0-B）")
            return 1
        print(f"[provider={provider} model={mname}]")
        print(out)
        return 0

    if task == "summarize" and len(args) >= 3:
        path = args[1]
        prompt = args[2]
        content = open(path, encoding="utf-8", errors="replace").read(6000)
        system = "你是 Zachary AI 研发助理，输出精简中文结论。"
        out, provider, mname = _chat_budgeted(system, prompt + "\n\n" + content, task, model=model, max_tokens=1000)
        if not out:
            print("[dev_ai] zhipu 不可用")
            return 1
        print(f"[provider={provider} model={mname}]")
        print(out)
        return 0

    print("unknown task")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
