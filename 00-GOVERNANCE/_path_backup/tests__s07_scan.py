# -*- coding: utf-8 -*-
import sys, io, json, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\Zachary OS AI")
from osai_engine.skills.source_skills import run_skill

zbc = r"D:\Taikoo-monitor-new"
res = run_skill("S07", repo_root=zbc)
routes = res["data"]["routes"]

# read-only = only GET (no POST/PUT/DELETE/PATCH)
def is_readonly(r):
    m = [x.upper() for x in r.get("methods", [])]
    return "GET" in m and not any(x in m for x in ("POST","PUT","DELETE","PATCH"))

ro = [r for r in routes if is_readonly(r)]
write = [r for r in routes if not is_readonly(r)]
print(f"total={len(routes)} readonly_GET={len(ro)} mutating={len(write)}")

# group readonly by source file
byfile = {}
for r in ro:
    byfile.setdefault(r["file"], []).append(r)
print("\n=== readonly GET endpoints by module ===")
for f in sorted(byfile):
    print(f"\n# {f} ({len(byfile[f])})")
    for r in sorted(byfile[f], key=lambda x:x["path"]):
        print("  ", r["path"])

# candidate feeders for dashboard zones
kw = re.compile(r"(stat|status|overview|summary|count|health|metric|trend|total|pulse|list|recent|alert|risk|task|evidence|dashboard)", re.I)
cand = [r for r in ro if kw.search(r["path"])]
print(f"\n\n=== candidate dashboard feeders ({len(cand)}) ===")
for r in sorted(cand, key=lambda x:x["path"]):
    print(f"{r['path']:<58} <- {r['file']}::{r['function']}")

# save full inventory
out = {"total": len(routes), "readonly": ro, "mutating": write}
with io.open(r"D:\Taikoo-monitor-new\docs\design\LUMENIS-API-INVENTORY-20260904.json","w",encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("\nsaved docs/design/LUMENIS-API-INVENTORY-20260904.json")
