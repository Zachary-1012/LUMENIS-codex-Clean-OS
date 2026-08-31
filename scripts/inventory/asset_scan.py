# -*- coding: utf-8 -*-
"""
ZBC 资产收敛 - 静态依赖/能力扫描器（只读，不修改任何业务文件）
输出：
  docs/governance/consolidation-002/raw/module_graph.json   机器可读全量图
  docs/governance/consolidation-002/raw/ASSET-IMPORT-MATRIX.md  每个模块 行数/被依赖/可达性
  docs/governance/consolidation-002/raw/CAPABILITY-CLUSTERS.md  同能力多实现聚类
用法：python scripts/inventory/asset_scan.py
"""
import ast, os, re, json, sys
from collections import defaultdict, deque

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "docs", "governance", "consolidation-002", "raw")
os.makedirs(OUT, exist_ok=True)

EXCLUDE_DIRS = {".venv", "node_modules", "nodejs", ".trae-cn", ".git", "__pycache__",
                "backups", "data", "chrome-cdp-profile", "edge-cdp-profile",
                "edge-cdp-newaccount", "edge-cdp-proxy", ".skills-router", "staging",
                ".pytest_cache", ".ollama", "dependencies", ".vscode", ".github",
                "ref_gpt_v2", "_ref_frames", "_shots", "_u", "logs", "collector_guard_backup"}
TEST_DIR = os.path.join(ROOT, "tests")

# ---------- 1. 收集全部本地 python 模块 ----------
def rel(p): return os.path.relpath(p, ROOT).replace("\\", "/")

py_files = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
    for f in filenames:
        if f.endswith(".py"):
            py_files.append(os.path.join(dirpath, f))

# modname(dotted) -> filepath ; topname -> set(modname)
mod2file, top2mods, file2mod = {}, defaultdict(set), {}
for fp in py_files:
    r = rel(fp)[:-3]  # strip .py
    if r.endswith("/__init__"):
        mod = r[: -len("/__init__")]
    elif r == "__init__":
        mod = ""  # root init unlikely
    else:
        mod = r.replace("/", ".")
    mod2file[mod] = fp
    file2mod[fp] = mod
    top2mods[mod.split(".")[0]].add(mod)

LOCAL_TOP = set(top2mods.keys())

DYN_RE = re.compile(r"(?:import_module|__import__)\(\s*['\"]([\w\.]+)['\"]")

def resolve(modname):
    """把一个 dotted 名尽量解析到真实文件模块；返回 modname 或包名或 None"""
    if modname in mod2file:
        return modname
    # from pkg import sub  -> pkg.sub
    if modname in top2mods:
        # 是个包
        if modname in mod2file:
            return modname
    # 逐级回退到存在的前缀
    parts = modname.split(".")
    while parts:
        cand = ".".join(parts)
        if cand in mod2file:
            return cand
        parts.pop()
    top = modname.split(".")[0]
    return top if top in LOCAL_TOP else None

# ---------- 2. 解析每个文件的本地依赖 ----------
file_deps = defaultdict(set)   # fp -> set(mod)
dyn_hits = defaultdict(set)
subprocess_py = defaultdict(set)
has_main = set()
line_count = {}
parse_err = {}

for fp in py_files:
    try:
        src = open(fp, encoding="utf-8-sig").read()  # utf-8-sig 兼容 BOM
    except Exception as e:
        parse_err[rel(fp)] = str(e); continue
    line_count[fp] = src.count("\n") + 1
    if re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", src):
        has_main.add(fp)
    for m in DYN_RE.finditer(src):
        r = resolve(m.group(1))
        if r: dyn_hits[fp].add(r)
    # subprocess 调起的本地 .py
    for m in re.finditer(r"(?:python(?:w)?(?:\.exe)?|sys\.executable)[^\n;]{0,120}?([\w\\/\-\.]+\.py)", src):
        subprocess_py[fp].add(m.group(1).replace("\\", "/").split("/")[-1])
    try:
        tree = ast.parse(src)
    except Exception as e:
        parse_err[rel(fp)] = f"AST {e}"; continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                r = resolve(a.name)
                if r: file_deps[fp].add(r)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            top = mod.split(".")[0] if mod else ""
            if node.level and node.level > 0:
                # 相对导入，按文件所在包推断
                base = file2mod.get(fp, "").split(".")[:-node.level]
                mod = ".".join(base + ([node.module] if node.module else []))
            if mod and (mod.split(".")[0] in LOCAL_TOP):
                base_res = resolve(mod)
                # from pkg import name 且 pkg/name 是子模块
                for a in node.names:
                    sub = (mod + "." + a.name) if mod else a.name
                    rs = resolve(sub)
                    if rs and rs != base_res:
                        file_deps[fp].add(rs)
                if base_res:
                    file_deps[fp].add(base_res)
            elif top in LOCAL_TOP:
                r = resolve(mod)
                if r: file_deps[fp].add(r)
    file_deps[fp] |= dyn_hits[fp]

# ---------- 3. 反向图 & 从 app.py 可达 ----------
rev = defaultdict(set)
for fp, deps in file_deps.items():
    for d in deps:
        tgt = mod2file.get(d)
        if tgt: rev[tgt].add(fp)

def reachable_from(entry_mod):
    seen=set(); dq=deque()
    start=mod2file.get(entry_mod)
    if not start: return seen
    dq.append(start)
    while dq:
        cur=dq.popleft()
        if cur in seen: continue
        seen.add(cur)
        for d in file_deps.get(cur,()):
            f=mod2file.get(d)
            if f and f not in seen: dq.append(f)
    return seen

app_reach = reachable_from("app")

# ---------- 4. 能力聚类 ----------
CAPS = {
 "报告/导出": ["report","export","weekly","daily_report"],
 "采集器": ["collect","xhs_campaign","rednote","web_monitor","web_topic","monitor_pipeline"],
 "AI/大模型": ["ai_","ark","llm","intelligence","adaptive_engine","local_ai"],
 "主体/分类": ["subject"],
 "风险": ["risk"],
 "事件": ["event"],
 "品牌/案例/知识": ["brand","case","swire","public_opinion","pr_","knowledge"],
 "恢复/守护/稳定": ["recover","guard","watchdog","stability","auto_recovery","safety"],
 "Cookie/登录": ["cookie","login","import_cookies","auth"],
 "网络/代理/隧道": ["network","proxy","tunnel","cloudflare","browser_discovery"],
 "缓存/内存": ["cache","memory"],
 "数据库/迁移": ["database","migration","reprocess","populate","recompute"],
 "平台适配": ["platform_adapters","adapter"],
 "证据/评审流": ["evidence","review_workflow"],
 "通知": ["notif","wechat_notifier","email"],
 "配置/设置": ["config","settings"],
 "评测/验证": ["eval","verify","check_","evaluate","ci_cd"],
}
cap_clusters = defaultdict(list)
for fp in py_files:
    name = os.path.basename(fp).lower(); rname = rel(fp)
    for cap, kws in CAPS.items():
        if any(k in name for k in kws):
            cap_clusters[cap].append(rname); break

# ---------- 5. 输出 ----------
graph = {"modules":{}}
for fp in sorted(py_files):
    m = file2mod.get(fp, rel(fp))
    graph["modules"][rel(fp)] = {
      "module": m, "lines": line_count.get(fp),
      "deps": sorted(file_deps.get(fp,())),
      "imported_by": sorted(rel(x) for x in rev.get(fp,())),
      "app_reachable": fp in app_reach,
      "has_main": fp in has_main,
      "is_test": fp.startswith(TEST_DIR),
      "subprocess_calls_py": sorted(subprocess_py.get(fp,())),
    }
graph["entry_reachable_count"] = len(app_reach)
graph["total_py"] = len(py_files)
json.dump(graph, open(os.path.join(OUT,"module_graph.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)

# Markdown 矩阵
def sortkey(fp): return (not fp.startswith(TEST_DIR), rel(fp))
lines=["# 资产静态依赖矩阵（机器生成，只读扫描）","",
 f"- 扫描本地 Python 文件：**{len(py_files)}**（已排除 venv/node_modules/浏览器profile/data/backups 等）",
 f"- 从 `app.py` 静态可达模块：**{len(app_reach)}**",
 f"- AST 解析失败：**{len(parse_err)}**","",
 "列含义：reach=app运行时静态可达；in=被几个本地模块依赖；main=含独立入口；test=测试","",
 "| 文件 | 行数 | reach | in | main | 依赖的本地模块 |","|---|--:|:--:|--:|:--:|---|"]
for fp in sorted(py_files,key=sortkey):
    g=graph["modules"][rel(fp)]
    deps=", ".join(os.path.basename(d.replace(".","/")) for d in g["deps"])[:160]
    lines.append(f"| `{rel(fp)}` | {g['lines']} | {'✅' if g['app_reachable'] else '—'} | {len(g['imported_by'])} | {'⚑' if g['has_main'] else ''} | {deps} |")
open(os.path.join(OUT,"ASSET-IMPORT-MATRIX.md"),"w",encoding="utf-8").write("\n".join(lines))

# 能力聚类
cl=["# 同能力多实现聚类（机器初筛，供唯一 Owner 判定）",""]
for cap,items in cap_clusters.items():
    if len(items)>=1:
        cl.append(f"## {cap}（{len(items)}）")
        for it in sorted(items): cl.append(f"- `{it}`")
        cl.append("")
open(os.path.join(OUT,"CAPABILITY-CLUSTERS.md"),"w",encoding="utf-8").write("\n".join(cl))

# 控制台摘要
unreachable=[rel(fp) for fp in py_files if fp not in app_reach and not fp.startswith(TEST_DIR)]
standalone_main=[rel(fp) for fp in has_main if fp not in app_reach and not fp.startswith(TEST_DIR)]
print("TOTAL_PY",len(py_files),"APP_REACH",len(app_reach))
print("UNREACHABLE_non_test",len(unreachable))
print("PARSE_ERR",parse_err)
print("=== 不可达且非测试（LEGACY/STANDALONE/TOOL 候选）===")
for u in sorted(unreachable): print("  ",u)
print("=== 能力簇规模 ===")
for k,v in sorted(cap_clusters.items(),key=lambda x:-len(x[1])): print(f"  {k}: {len(v)}")
print("OUT ->",OUT)
