# -*- coding: utf-8 -*-
"""Zachary AI 研发辅助 CLI（智谱算力，豆包少用）。

用法：
  python scripts/dev_ai.py health-capabilities        # P0-B：健康/监控模块 Capability 收敛分析
  python scripts/dev_ai.py summarize <file> <prompt>  # 用智谱总结/分析指定文件

智谱 key 仅从 .env 读取，绝不打印/入库。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load_dotenv():
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, _, v = ln.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main():
    _load_dotenv()
    import intelligence
    if len(sys.argv) < 2:
        print("usage: dev_ai.py <task>")
        return 1
    task = sys.argv[1]

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
        out, provider = intelligence._chat(system, user, max_tokens=1500)
        if not out:
            print("[dev_ai] zhipu 不可用，降级本地规则结论（见矩阵 P0-B）")
            return 1
        print(f"[provider={provider}]")
        print(out)
        return 0

    if task == "summarize" and len(sys.argv) >= 4:
        path = sys.argv[2]
        prompt = sys.argv[3]
        content = open(path, encoding="utf-8", errors="replace").read(6000)
        system = "你是 Zachary AI 研发助理，输出精简中文结论。"
        out, provider = intelligence._chat(system, prompt + "\n\n" + content, max_tokens=1000)
        if not out:
            print("[dev_ai] zhipu 不可用")
            return 1
        print(f"[provider={provider}]")
        print(out)
        return 0

    print("unknown task")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
