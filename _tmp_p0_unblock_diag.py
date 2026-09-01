"""P0 fast: Read collection_logs schema + last row; read planning store state file; read state_map CS definitions & is_stop_request"""
import sqlite3, json, os, sys, time
sys.path.insert(0, r'd:\Taikoo-monitor-new')

# 1. Collection logs — real schema & last 3 rows
conn = sqlite3.connect(r'd:\Taikoo-monitor-new\data\monitor.db')
c = conn.cursor()
c.execute("PRAGMA table_info(collection_logs)")
cols = c.fetchall()
print("=" * 80)
print("COLLECTION_LOGS schema:")
for col in cols:
    print(f"  cid={col[0]} name={col[1]:<22} type={col[2]}  notnull={col[3]}  pk={col[5]}")
c.execute("SELECT * FROM collection_logs ORDER BY id DESC LIMIT 5")
rows = c.fetchall()
col_names = [x[1] for x in cols]
print(f"\nCOLLECTION_LOGS last 5 rows:")
for r in rows:
    d = dict(zip(col_names, r))
    print("  ", json.dumps(d, ensure_ascii=False, default=str))

# 2. Planner store — find state files
print("\n" + "=" * 80)
print("Searching scheduling state store JSON files...")
candidates = []
for root, dirs, files in os.walk(r'd:\Taikoo-monitor-new\data'):
    for f in files:
        p = os.path.join(root, f)
        rel = os.path.relpath(p, r'd:\Taikoo-monitor-new').replace('\\','/')
        if any(kw in f.lower() for kw in ['schedule', 'state', 'planner', 'gate', 'circuit', 'store', 'xhs']) and f.endswith('.json'):
            sz = os.path.getsize(p)
            try:
                content = open(p, 'r', encoding='utf-8', errors='replace').read(3000)
                if any(kw in content[:1500] for kw in ['BLOCKED', 'stop_request', 'cooldown_until', 'platform', 'xhs', 'risk_status']):
                    candidates.append((rel, sz, content[:1500]))
            except: pass
print(f"Found {len(candidates)} suspicious state JSONs:")
for rel, sz, cont in candidates:
    print(f"\n  [{sz:>6}B] {rel}")
    print(f"  {cont[:500]}")

# Also check /data/ root for any platform state JSON
print("\n\nSearching xhs_runtime / planner state in non-json (py .dat/.pkl etc) ... skip binary.\n")

# 3. state_map CS definition & function list
print("=" * 80)
print("platform_adapters.scheduling.state_map function/class listing:")
import ast
src = open(r'd:\Taikoo-monitor-new\platform_adapters\scheduling\state_map.py', 'r', encoding='utf-8', errors='replace').read()
tree = ast.parse(src)
classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
for cl in classes:
    print(f"\n  CLASS {cl.name}")
    for sub in cl.body:
        if isinstance(sub, ast.FunctionDef):
            print(f"      - method {sub.name}({', '.join(a.arg for a in sub.args.args[:4])})")
for fn in funcs:
    print(f"  FUNC def {fn.name}({', '.join(a.arg for a in fn.args.args[:5])})")
