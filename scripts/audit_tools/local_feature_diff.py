import os

MAIN = r"D:\Taikoo-monitor-new"
SOURCES = {
    "security": r"D:\Taikoo-security",
    "staging-ui": r"D:\Taikoo-staging-ui",
    "audit-four-source": r"D:\audit-four-source",
    "OSAI": r"D:\Zachary OS AI",
    "ADRH": r"D:\AI-Development-Research-Hub",
    "KimiData": r"D:\KimiData",
    "CmdConsole": r"D:\Development-Command-Console",
    "GGI": r"D:\global-growth-intelligence",
    "SICI": r"D:\SICI-Core",
}
SKIP = (".venv", "node_modules", "__pycache__", "site-packages", ".git", "edge-cdp")

def py_modules(base):
    """返回 basename(无.py)->相对路径列表 """
    m = {}
    if not os.path.isdir(base):
        return m
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in SKIP]
        for f in fn:
            if f.endswith(".py"):
                m.setdefault(f, []).append(os.path.relpath(os.path.join(dp, f), base))
    return m

main_mods = py_modules(MAIN)
print(f"主线 Python 模块(去重文件名)数: {len(main_mods)}")

report = []
grand = {}
for label, path in SOURCES.items():
    src = py_modules(path)
    missing = sorted(set(src) - set(main_mods))
    # 过滤明显的无关/依赖/临时
    filtered = [m for m in missing if not m.startswith(("test_", "_", "tmp", "scratch", "setup", "conftest"))]
    for m in filtered:
        grand.setdefault(m, []).append(label)
    report.append((label, len(src), len(missing), len(filtered), filtered))
    print(f"\n### {label}  源模块={len(src)} 主线没有={len(missing)} 过滤候选={len(filtered)}")
    for m in filtered[:25]:
        print("   -", m)
    if len(filtered) > 25:
        print(f"   ... 其余 {len(filtered)-25} 个见台账草稿")

out = r"D:\Taikoo-monitor-new\audit\_LOCAL_FEATURE_DIFF_DRAFT.md"
with open(out, "w", encoding="utf-8") as f:
    f.write("# 本地已开发·主线缺失 候选台账草稿（自动交叉比对，需逐模块核内容判定）\n\n")
    f.write("> basename 级比对，仅为候选：同名可能不同实现、异名可能已被改名实现。逐项判定 直接复用/适配补入/真缺失/废弃，并标所属域。\n\n")
    for label, tot, miss, keep, files in report:
        f.write(f"\n## 源：{label}（源模块 {tot}，主线缺失候选 {keep}）\n")
        for m in files:
            f.write(f"- [ ] {m}\n")
    f.write(f"\n\n## 跨源汇总：主线没有的模块共 {len(grand)} 个（模块->出现于哪些源）\n")
    for m in sorted(grand):
        f.write(f"- {m}  <= {','.join(grand[m])}\n")
print("\n台账草稿已写:", out, " 跨源去重候选总数:", len(grand))
