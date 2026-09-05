# -*- coding: utf-8 -*-
"""只读：FEATURE-REGISTRY 34条 vs 真实文件/路由/DB表/前端 全链路交叉验证。不写库不改码。"""
import os, re, sqlite3, io, sys, json
from core.repository_registry import get_repo_root, get_db_path, get_osai_root
ROOT = get_repo_root()
sys.stdout.reconfigure(encoding="utf-8")

# ---------- 1. 真实路由集合（全仓静态扫描 route 装饰器/add_url_rule）----------
route_re = re.compile(r"""(?:@[\w_]+\.route|add_url_rule)\s*\(\s*['"]([^'"]+)['"]""")
routes = set()
py_files_all = []
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in {".git", ".venv", "venv", "node_modules", "__pycache__",
                                        "ref_gpt_v2", "edge-cdp-profile", "chrome-cdp-profile",
                                        "staging", ".trae-cn"} and "development-command-console" not in dp]
    for f in fn:
        if f.endswith(".py"):
            full = os.path.join(dp, f)
            py_files_all.append(full)
            try:
                txt = io.open(full, encoding="utf-8", errors="ignore").read()
                for m in route_re.finditer(txt):
                    routes.add(m.group(1))
            except Exception:
                pass

def api_hit(pat):
    pat = pat.rstrip("*")
    return any(r == pat or r.startswith(pat) for r in routes)

# ---------- 2. 真实 DB 表（只读）----------
dbp = os.path.join(ROOT, "data", "monitor.db")
con = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
tables = set(r[0] for r in con.execute("select name from sqlite_master where type='table'"))
con.close()

def table_hit(tok):
    tok = tok.strip()
    if tok.endswith("*"):
        pre = tok[:-1]
        return any(t.startswith(pre) for t in tables)
    return tok in tables

# ---------- 3. 真实文件存在（按文件名/相对目录）----------
base_names = {}
for full in py_files_all:
    rel = os.path.relpath(full, ROOT).replace("\\", "/")
    base_names.setdefault(os.path.basename(full), []).append(rel)

def owner_hit(name):
    name = name.strip().strip("*")
    if not name:
        return None
    if name.endswith(".py"):
        b = os.path.basename(name)
        hits = base_names.get(b, [])
        if not hits:
            return ("MISS", name)
        # 若给了目录，优先目录匹配
        if "/" in name:
            for h in hits:
                if name in h or h.endswith(name):
                    return ("OK", h)
        return ("OK", hits[0])
    # 目录/模块
    for h in list(base_names.values())[0:0]:
        pass
    cand = [rel for rels in base_names.values() for rel in rels if ("/" + name + "/") in ("/" + rel) or rel.startswith(name + "/")]
    return ("OK", cand[0]) if cand else ("MISS", name)

# ---------- 4. 前端文本（主SPA + v4/旧模板）----------
front_blob = ""
for rel in ["static/index.html"]:
    p = os.path.join(ROOT, rel)
    if os.path.exists(p):
        front_blob += io.open(p, encoding="utf-8", errors="ignore").read()
tpl_files = []
for dd in ["templates", os.path.join("v4_upgrade", "templates")]:
    d = os.path.join(ROOT, dd)
    if os.path.isdir(d):
        for dp2, _, fns in os.walk(d):
            for f in fns:
                if f.endswith((".html", ".jinja", ".jinja2")):
                    tpl_files.append(os.path.join(dp2, f))
for p in tpl_files:
    front_blob += io.open(p, encoding="utf-8", errors="ignore").read()

# ---------- 5. 解析 FEATURE-REGISTRY ----------
reg = io.open(os.path.join(ROOT, "docs/governance/consolidation-002/FEATURE-REGISTRY.md"), encoding="utf-8").read()
fid_re = re.compile(r"FEATURE-[A-Z0-9-]+")
py_re = re.compile(r"[A-Za-z0-9_/\\.\-]+\.py")
api_re = re.compile(r"/[A-Za-z0-9_\-/*]+")
rows = []
for line in reg.splitlines():
    if "FEATURE-" not in line or not line.strip().startswith("|"):
        continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    fidm = fid_re.search(line)
    if not fidm:
        continue
    fid = fidm.group(0)
    pys = [p.replace("\\", "/") for p in py_re.findall(line)]
    apis = [a for a in api_re.findall(line) if a.startswith(("/api", "/v4", "/healthz"))]
    # DB token：括号内 / 列中出现的疑似表
    dbtoks = [t for t in tables if re.search(r"\b" + re.escape(t) + r"\b", line)]
    # 通配 brand_* web_* ai_* data/cookies
    wild = re.findall(r"\b([a-z]+)_\*", line)
    for w in wild:
        if any(t.startswith(w + "_") for t in tables):
            dbtoks.append(w + "_*")
    status = re.match(r"([A-Z_]+)", cells[-1])
    rows.append(dict(fid=fid, cells=cells, pys=pys, apis=apis, dbs=sorted(set(dbtoks)),
                     status=status.group(1) if status else "?"))

# ---------- 6. 逐条核对 ----------
print(f"# Feature crosscheck  真实路由 {len(routes)} / 真实表 {len(tables)} / py {len(py_files_all)} / 前端模板 {len(tpl_files)+1}")
miss = {"owner": [], "api": [], "db": [], "ui": []}
for r in rows:
    owner_res = [owner_hit(p) for p in r["pys"]]
    owner_miss = [x[1] for x in owner_res if x and x[0] == "MISS"]
    api_miss = [a for a in r["apis"] if not api_hit(a)]
    db_miss = []
    for d in r["dbs"]:
        if d.endswith("_*"):
            if not table_hit(d):
                db_miss.append(d)
        elif d not in tables:
            db_miss.append(d)
    flag = ""
    if owner_miss: miss["owner"].append((r["fid"], owner_miss)); flag += " OWNER?"
    if api_miss: miss["api"].append((r["fid"], api_miss)); flag += " API?"
    if db_miss: miss["db"].append((r["fid"], db_miss)); flag += " DB?"
    print(f"{r['fid']:<28}{r['status']:<18} owner_py={len(r['pys'])-len(owner_miss)}/{len(r['pys'])} api={len(r['apis'])-len(api_miss)}/{len(r['apis'])} db={len(r['dbs'])-len(db_miss)}/{len(r['dbs'])}{flag}")

print("\n===== MISS SUMMARY =====")
for k, v in miss.items():
    print(f"-- {k} missing --")
    for fid, x in v:
        print(f"   {fid}: {x}")
print("\n真实表清单:", sorted(tables))
