"""P0 Bypass: Temporarily prepend Doubao Node 22.23.2 bin dir to PATH, then rerun direct sync() probe."""
import sys, os
NODE_DIR = r'c:\Users\28049\AppData\Local\Doubao\User Data\sandbox_runtime\bases\c98c5042338ed152c6f10ecd8591889f\node'
assert os.path.isdir(NODE_DIR), f"Node dir missing: {NODE_DIR}"
assert os.path.exists(os.path.join(NODE_DIR, 'node.exe')), f"node.exe missing in {NODE_DIR}"
# PREPEND to PATH so subprocess Popen(cmd=['node',...]) finds it FIRST
os.environ['PATH'] = NODE_DIR + os.pathsep + (os.environ.get('PATH', ''))
# Verify it
import subprocess
r = subprocess.run(['node','--version'], capture_output=True, text=True, env=os.environ)
print(f"PATH PREPEND OK: node --version = {r.stdout.strip()}")
print(f"PATH node first hit dir = {NODE_DIR}")

# Reuse exact probe
sys.path.insert(0, r'd:\Taikoo-monitor-new')
import json, time, datetime, sqlite3

print(f"\n[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] Rerun sync probe (PATH patched)")
import xhs_cookie_bridge
t0 = time.time()
try:
    result = xhs_cookie_bridge.sync(keywords=['广州太古汇', '太古汇', '广州太古汇 舆情'], max_scroll=4)
    dt = time.time() - t0
    print(f"\n✓ sync() OK in {dt:.1f}s")
    for k in sorted(result.keys()):
        v = result[k]
        s = json.dumps(v, ensure_ascii=False)
        print(f"  {k:<18}: {s if len(s)<400 else s[:399]+'…'}")
except Exception as e:
    print(f"\n✗ sync FAIL {time.time()-t0:.1f}s: {e}")
    import traceback; traceback.print_exc()

# Final DB
print(f"\nDB snapshot:")
conn = sqlite3.connect(r'd:\Taikoo-monitor-new\data\monitor.db'); c = conn.cursor()
c.execute("SELECT COUNT(*), MAX(collected_at) FROM notes"); nc, mc = c.fetchone()
c.execute("SELECT id,status,keyword,notes_count,finished_at FROM collection_logs ORDER BY id DESC LIMIT 6")
logs = c.fetchall(); conn.close()
print(f"  notes = {nc}, max_collected = {mc}")
for r in logs:
    print(f"  log#{r[0]:>3} {str(r[1]):<13} kw={str(r[2]):<22} notes_cnt={r[3]} fin={r[4]}")
print(f"\nΔnotes vs frozen 957 = {nc - 957}")
