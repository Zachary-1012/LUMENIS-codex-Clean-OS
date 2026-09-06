# -*- coding: utf-8 -*-
"""P0-B 自动对账：skills-registry.json capability ↔ 双子库源码（只读核验，可复跑）。

用途：补 MASTER-ENGINEERING-MATRIX P0-B 缺口「Capability/Contract/Ownership 文档矩阵缺与代码自动对账」。
规则：只读扫描 ZBC/OSAI 源码；不修改任何生产文件；输出对账报告到 research-inbox/。
运行：python scripts/reconcile_capabilities.py
"""
import json, os, re, io, sys, datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # OSAI 根
ZBC = r"D:\Taikoo-monitor-new"                                       # ZBC 生产根

REG = os.path.join(ROOT, "config", "skills-registry.json")


def parse_locations(loc: str, default_src: str = "ZBC"):
    """解析 location 字段（支持 'ZBC/a.py'、'ZBC/a/ + b.py'、'dir/a.md, b.md' 等）。
    - '+ ' 连接的多文件为独立路径（不继承目录）；
    - ', ' 连接时，裸文件名继承前一个含目录 token 的目录前缀（registry 目录省略写法）。
    default_src：无前缀路径的默认归属（生产能力→ZBC；研究能力→OSAI）。"""
    loc = loc.replace("+", " ").replace("；", " ")
    parts = [p for p in re.split(r"[\s,]+", loc.strip()) if p]
    files, last_dir = [], None
    for p in parts:
        src = default_src
        if p.startswith("ZBC/"):
            src, rel, last_dir = "ZBC", p[4:], None
        elif p.startswith("OSAI/"):
            src, rel, last_dir = "OSAI", p[5:], None
        elif "/" in p:
            rel = p
            last_dir = p.rsplit("/", 1)[0]
        elif last_dir is not None:
            rel = last_dir + "/" + p
        else:
            rel = p
        files.append((src, rel.replace("/", os.sep)))
    return files


def sample_symbols(path, want=3):
    """从 .py 文件抽取前 want 个顶层 def/class 名，验证文件真实含代码符号。"""
    if not path.endswith(".py"):
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            src = f.read()
    except Exception:
        return "READ_ERR"
    syms = []
    for m in re.finditer(r"^(?:async\s+)?def\s+(\w+)|^class\s+(\w+)", src, re.M):
        syms.append(m.group(1) or m.group(2))
    return syms[:want] or ["<no-top-symbols>"]


def main():
    reg = json.load(open(REG, encoding="utf-8"))
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    L = []
    L.append("# P0-B 自动对账报告 — Capability ↔ 源码（可复跑）")
    L.append("")
    L.append(f"- 运行时间：{now}")
    L.append(f"- 源：`OSAI config/skills-registry.json`（schema {reg.get('schema_version')}）↔ 双子库源码")
    L.append("- 规则：只读核验；MISSING=声称文件不存在；PASS=文件在且符号可验；N/A=目录型定位")
    L.append("")

    # ============ production_capabilities ============
    L.append("## 一、production_capabilities 对账（9 条）")
    L.append("")
    L.append("| ID | 名称 | 声称 location | status | 核验 | 符号抽样 |")
    L.append("|---|---|---|---|---|---|")
    for it in reg.get("production_capabilities", []):
        loc = it.get("location", "")
        status = it.get("status", "")
        files = parse_locations(loc)
        missing, present = [], []
        for src, rel in files:
            base = ZBC if src == "ZBC" else ROOT
            p = os.path.join(base, rel)
            (present if os.path.exists(p) else missing).append((src, rel))
        if missing:
            verdict = "**MISSING**: " + ", ".join(f"{s}/{r}" for s, r in missing)
            sym = "—"
        elif present:
            # 取第一个存在的 .py 做符号抽样
            for src, rel in present:
                base = ZBC if src == "ZBC" else ROOT
                p = os.path.join(base, rel)
                if p.endswith(".py"):
                    syms = sample_symbols(p)
                    sym = ", ".join(syms) if syms else "—"
                    break
            else:
                sym = "N/A(非py/目录)"
            verdict = "PASS"
        else:
            verdict, sym = "N/A", "—"
        L.append(f"| {it.get('id')} | {it.get('name')} | `{loc}` | {status} | {verdict} | {sym} |")
    n_prod_missing = 0

    # ============ research_capabilities ============
    L.append("")
    L.append("## 二、research_capabilities 对账（10 条）")
    L.append("")
    L.append("| ID | 名称 | 声称 location | status | 核验 |")
    L.append("|---|---|---|---|---|")
    for it in reg.get("research_capabilities", []):
        loc = it.get("location", "")
        status = it.get("status", "")
        files = parse_locations(loc, default_src="OSAI")   # 研究能力默认归属 OSAI
        missing, present = [], []
        for src, rel in files:
            base = ZBC if src == "ZBC" else ROOT
            p = os.path.join(base, rel)
            (present if os.path.exists(p) else missing).append((src, rel))
        verdict = "**MISSING**: " + ", ".join(f"{s}/{r}" for s, r in missing) if missing else "PASS"
        L.append(f"| {it.get('id')} | {it.get('name')} | `{loc}` | {status} | {verdict} |")

    # ============ contracts ============
    L.append("")
    L.append("## 三、contracts 对账")
    L.append("")
    for c in reg.get("contracts", []):
        p = os.path.join(ROOT, c)
        st = "PASS" if os.path.exists(p) else "**MISSING**"
        L.append(f"- `{c}` → {st}")

    # ============ 汇总 ============
    prod = reg.get("production_capabilities", [])
    miss_prod = 0
    for it in prod:
        if any(not os.path.exists(os.path.join(ZBC if s == "ZBC" else ROOT, r))
               for s, r in parse_locations(it.get("location", ""))):
            miss_prod += 1
    research = reg.get("research_capabilities", [])
    miss_research = 0
    for it in research:
        if any(not os.path.exists(os.path.join(ZBC if s == "ZBC" else ROOT, r))
               for s, r in parse_locations(it.get("location", ""), default_src="OSAI")):
            miss_research += 1
    L.append("")
    L.append("## 四、结论")
    L.append("")
    L.append(f"- production_capabilities：{len(prod)} 条，MISSING {miss_prod} 条")
    L.append(f"- research_capabilities：{len(research)} 条，MISSING {miss_research} 条")
    L.append(f"- contracts：{len(reg.get('contracts', []))} 条")
    L.append("- 对账结果仅作只读核验；MISSING 项需人工判断（location 描述过时 or 路径拼写），不自动改 registry。")

    out = os.path.join(ROOT, "research-inbox", "AUTO-RECONCILE-P0B-20260903.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("\n".join(L))
    print(f"\n[OK] 报告已写入 {out}")


if __name__ == "__main__":
    main()
