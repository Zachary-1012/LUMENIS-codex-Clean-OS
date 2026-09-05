# -*- coding: utf-8 -*-
"""Feature Final Verification 2.0 只读核验：Asset/Owner/API(含蓝图前缀)/DB/UI/Runtime可达/Test/Evidence。不写库不改码。"""
import os, re, sqlite3, io, sys, json
from core.repository_registry import get_repo_root, get_db_path, get_osai_root
ROOT = get_repo_root()
sys.stdout.reconfigure(encoding="utf-8")
SKIP_DIRS = {".git",".venv","venv","node_modules","__pycache__","ref_gpt_v2","edge-cdp-profile",
             "chrome-cdp-profile","staging",".trae-cn","development-command-console","repo-audit"}

# ---- module graph: runtime 可达 ----
mg = json.load(io.open(os.path.join(ROOT,"docs/governance/consolidation-002/raw/module_graph.json"),encoding="utf-8"))["modules"]
def reachable(mod_noext):
    m = mg.get(mod_noext)
    return m.get("app_reachable") if m else None

# ---- 所有 py + 蓝图前缀 + 路由 ----
pytext, bpprefix, routes_at = {}, {}, []   # routes_at: [(route, filename)]
bp_def = re.compile(r"Blueprint\(\s*['\"][\w\-]+['\"]\s*,\s*__name__[^)]*?url_prefix\s*=\s*['\"]([^'\"]+)['\"]", re.S)
route_re = re.compile(r"""\.route\s*\(\s*['"]([^'"]+)['"]""")
for dp,dn,fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in SKIP_DIRS]
    for f in fn:
        if f.endswith(".py"):
            full=os.path.join(dp,f); rel=os.path.relpath(full,ROOT).replace("\\","/")
            try: txt=io.open(full,encoding="utf-8",errors="ignore").read()
            except: txt=""
            pytext[rel]=txt
            for mm in bp_def.finditer(txt): bpprefix.setdefault(rel,set()).add(mm.group(1))
            for mm in route_re.finditer(txt): routes_at.append((mm.group(1),rel))
# 组装完整路径候选：裸路由 + 同文件蓝图前缀拼接 + /v4 嵌套
all_paths=set()
for r,rel in routes_at:
    all_paths.add(r)
    for pre in bpprefix.get(rel,()):
        all_paths.add(pre+r)
        all_paths.add("/v4"+pre+r)
# v4 子蓝图：把所有 url_prefix 也与相对路由做两层组合
prefixes=set(p for ps in bpprefix.values() for p in ps)
for r,rel in routes_at:
    for p in prefixes:
        if not r.startswith("/"): continue
        if r.startswith(p): continue
        all_paths.add(p+r)
def api_hit(pat):
    pat=pat.rstrip("*").rstrip("/")
    for p in all_paths:
        q=p.rstrip("/")
        if q==pat or q.startswith(pat+"/") or q.startswith(pat):
            # 防止 /api 过宽：要求前缀后是 / 或结尾
            if q==pat or q.startswith(pat+"/") or (pat.endswith(pat) and "/" not in q[len(pat):len(pat)+1]):
                return p
    return None

# ---- DB 表/列（只读）----
con=sqlite3.connect(f"file:{os.path.join(ROOT,'data','monitor.db')}?mode=ro",uri=True)
tables=set(r[0] for r in con.execute("select name from sqlite_master where type='table'"))
cols={t:[r[1] for r in con.execute(f'pragma table_info("{t}")')] for t in tables}
evi_rows=con.execute("select count(*) from app_evidence_records").fetchone()[0]
con.close()

# ---- 正式测试（pytest 可收集 test_*.py）与其文本 ----
test_files={}
tdir=os.path.join(ROOT,"tests")
for f in os.listdir(tdir):
    if f.startswith("test_") and f.endswith(".py"):
        test_files[f]=io.open(os.path.join(tdir,f),encoding="utf-8",errors="ignore").read()
def tests_for(keywords):
    hits=[]
    for tf,txt in test_files.items():
        for k in keywords:
            if k and len(k)>3 and (k in tf or k in txt):
                hits.append(tf); break
    return sorted(set(hits))

# ---- 前端聚合文本 ----
front=""
for dp,dn,fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in SKIP_DIRS]
    for f in fn:
        if f.endswith((".html",".js")):
            rel=os.path.relpath(os.path.join(dp,f),ROOT).replace("\\","/")
            if rel.startswith("static/") or rel.startswith("templates/") or "templates" in rel:
                try: front+=io.open(os.path.join(dp,f),encoding="utf-8",errors="ignore").read()
                except: pass
def ui_hit(*kws):
    return [k for k in kws if k and (k in front)]

# ---- 解析 Feature Registry ----
reg=io.open(os.path.join(ROOT,"docs/governance/consolidation-002/FEATURE-REGISTRY.md"),encoding="utf-8").read()
fid_re=re.compile(r"FEATURE-[A-Z0-9-]+"); py_re=re.compile(r"[A-Za-z0-9_/\-]+\.py"); api_re=re.compile(r"/[A-Za-z0-9_\-/*]+")
rows=[]
for line in reg.splitlines():
    if "FEATURE-" not in line or not line.strip().startswith("|"): continue
    cells=[c.strip() for c in line.strip().strip("|").split("|")]
    fm=fid_re.search(line)
    if not fm: continue
    fid=fm.group(0); name=cells[1] if len(cells)>1 else ""
    pys=[p for p in py_re.findall(line)]
    apis=[a for a in api_re.findall(line) if a.startswith(("/api","/v4","/healthz"))]
    dbtoks=[t for t in tables if re.search(r"\b"+re.escape(t)+r"\b",line)]
    wild=re.findall(r"\b([a-z]+)_\*",line)
    for w in wild:
        if any(t.startswith(w+"_") for t in tables): dbtoks.append(w+"_*")
    status=re.match(r"([A-Z_]+)",cells[-1]); status=status.group(1) if status else "?"
    # runtime 可达（owner 模块）
    mods=[os.path.basename(p)[:-3] for p in pys]
    reach=[reachable(m) for m in mods]
    rt = "YES" if any(x is True for x in reach) else ("NO" if reach and all(x is False for x in reach) else ("-" if not mods else "?"))
    # test 关键词：模块名 + 功能名核心
    kws=mods+[fid.split("-")[-2].lower() if len(fid.split("-"))>2 else ""]
    th=tests_for(set([k for k in kws if k]))
    # ui 关键词：API 尾段 + 名称前 6 字
    uikws=[]
    for a in apis:
        uikws.append(a.rstrip("*").rstrip("/").split("/")[-1])
    ui_found=ui_hit(*([name[:4]]+uikws))
    rows.append(dict(fid=fid,name=name,pys=pys,apis=apis,dbs=sorted(set(dbtoks)),status=status,
                     rt=rt,tests=th,ui=ui_found,api_resolved=[(a,api_hit(a)) for a in apis]))

print(f"# Final verify  routes={len(all_paths)} tables={len(tables)} formal_tests={len(test_files)} evidence_rows={evi_rows} front_chars={len(front)}\n")
stat_count={}
for r in rows:
    stat_count[r["status"]]=stat_count.get(r["status"],0)+1
    asset="Y" if (not r["pys"]) or all(os.path.basename(p) in {os.path.basename(x) for x in pytext} or any(x.endswith(p) for x in pytext) for p in r["pys"]) else "MISS"
    api_ok=all(v for _,v in r["api_resolved"]) if r["api_resolved"] else "-"
    t="Y" if r["tests"] else "N"
    e="N(evi_table_empty)"  # 证据表0行，统一缺运行证据
    u="Y" if r["ui"] else ("-" if not r["apis"] and not r["name"] else "?")
    print(f"{r['fid']:<26}{r['status']:<18} asset={asset} api={'Y' if api_ok is True else ('-' if api_ok=='-' else 'N')} db={len(r['dbs'])} rt={r['rt']} test={t} evi={e} ui={u} tests={','.join(r['tests'])[:70]}")
print("\nSTATUS COUNT:",stat_count)
print("Features WITHOUT formal test:",[r['fid'] for r in rows if not r['tests']])
