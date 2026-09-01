"""P0: Synchronous direct call to xhs_cookie_bridge.sync() — bypass Flask, bypass threading. Find root cause."""
import sys, os, json, time, datetime
sys.path.insert(0, r'd:\Taikoo-monitor-new')

print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] Direct xhs_cookie_bridge.sync probe ...")
try:
    import xhs_cookie_bridge
    print(f"  ✓ import ok, has sync = {hasattr(xhs_cookie_bridge,'sync')}")
    print(f"  ✓ cookie_configured() = {xhs_cookie_bridge.cookie_configured()}")
    if hasattr(xhs_cookie_bridge, 'verify_account'):
        v = xhs_cookie_bridge.verify_account()
        print(f"  ✓ verify_account() = {v}")
    if hasattr(xhs_cookie_bridge, 'get_circuit_state'):
        print(f"  circuit_state = {json.dumps(xhs_cookie_bridge.get_circuit_state(), ensure_ascii=False, indent=2)}")
except Exception as e:
    print(f"  ✗ import FAIL: {e}")
    import traceback; traceback.print_exc(); sys.exit(1)

KEYWORDS = ['广州太古汇', '太古汇', '广州太古汇 舆情']
print(f"\n[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] Calling sync(keywords={KEYWORDS}, max_scroll=5)...")
try:
    t0 = time.time()
    result = xhs_cookie_bridge.sync(keywords=KEYWORDS, max_scroll=5)
    dt = time.time() - t0
    print(f"\n[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] ✓ sync() completed in {dt:.1f}s.")
    print("Result (top-level keys):")
    for k in sorted(result.keys()):
        v = result[k]
        if isinstance(v, (list, dict)) and len(json.dumps(v, ensure_ascii=False)) > 300:
            print(f"  {k:<20}: <{type(v).__name__} size={len(v)} preview[:300]> {json.dumps(v, ensure_ascii=False)[:300]}")
        else:
            print(f"  {k:<20}: {json.dumps(v, ensure_ascii=False)}")
except Exception as e:
    print(f"\n✗ sync() FAILED after {time.time()-t0:.1f}s: {e}")
    import traceback; traceback.print_exc()

# Final DB snapshot
print(f"\n[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] Final DB snapshot:")
import sqlite3
conn = sqlite3.connect(r'd:\Taikoo-monitor-new\data\monitor.db'); c = conn.cursor()
c.execute("SELECT COUNT(*), MAX(collected_at) FROM notes"); n_cnt, n_max = c.fetchone()
c.execute("SELECT id, status, keyword, notes_count, error_msg, finished_at FROM collection_logs ORDER BY id DESC LIMIT 6")
logs = c.fetchall(); conn.close()
print(f"  notes COUNT={n_cnt}  max_collected={n_max}")
for r in logs:
    emsg = (r[4] or '')[:60].replace('\n',' ')
    print(f"  log#{r[0]:>3} {str(r[1]):<13} kw={str(r[2]):<22} notes={r[3]}  err=\"{emsg}\"  @{r[5]}")
