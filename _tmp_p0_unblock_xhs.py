"""P0: Unblock XHS. Step order: probe state → resume + reset stop_request + start collector → verify."""
import requests, json, time, sys
from requests.auth import HTTPBasicAuth
BASE = "http://127.0.0.1:8200"
AUTH = HTTPBasicAuth("Zachary", "ID082610")
sess = requests.Session()
sess.auth = AUTH

def GET(tag, path):
    t0 = time.time()
    try:
        r = sess.get(BASE + path, timeout=12)
    except Exception as e:
        print(f"[{tag}] GET EXC {type(e).__name__}: {e}")
        return None
    print(f"[{tag}] HTTP {r.status_code}  ({time.time()-t0:.1f}s)  len={len(r.content)}")
    try:
        body = r.json()
        print(json.dumps(body, indent=2, ensure_ascii=False)[:1500])
    except Exception:
        print(r.text[:600])
    return r

def POST(tag, path, payload=None):
    t0 = time.time()
    try:
        r = sess.post(BASE + path, json=payload or {}, timeout=30)
    except Exception as e:
        print(f"\n[{tag}] POST EXC {type(e).__name__}: {e}")
        return None
    print(f"\n[{tag}] HTTP {r.status_code}  ({time.time()-t0:.1f}s)  len={len(r.content)}")
    try:
        body = r.json()
        print(json.dumps(body, indent=2, ensure_ascii=False)[:1500])
    except Exception:
        print(r.text[:600])
    return r

print("=" * 80)
print("STEP 1: BEFORE state snapshot")
print("=" * 80)
GET("A1 xhs_pause_state",   "/api/xhs/collect-pause-state")
GET("A2 platform_health",    "/api/platform-health")
GET("A3 collector_status",   "/api/collector/status")
GET("A4 health_summary",     "/api/system/health/summary")
# A5: notes count raw
r = GET("A5 notes-count",    "/api/stats")
try:
    before_notes = r.json().get('total_notes') or r.json().get('notes_count') or (r.json().get('stats') or {}).get('total_notes')
except:
    before_notes = None
print(f"\n>>> BEFORE notes_count (baseline for growth check) = {before_notes}")

print("\n\n" + "=" * 80)
print("STEP 2: UNBLOCK actions")
print("=" * 80)
# 2a) XHS resume — clears any "paused" flag on XHS path
POST("B1 POST /xhs/collect-resume",              "/api/xhs/collect-resume")

# 2b) Try v4 recovery check — /v4/ endpoints need v4 session so Basic Auth alone will 401. Skip.
#     Instead try architecture recovery run-cycle + auth-recovery task creation
POST("B2 POST /recovery/run-cycle",              "/api/recovery/run-cycle")
# POST topic recover (topic campaign path)
POST("B3 POST /topic-campaign/recover",          "/api/topic-campaign/recover")

# 2c) Start collector main loop (will read platform scheduling state and should pick up resumed XHS)
POST("B4 POST /collector/start",                 "/api/collector/start")

# 2d) Optional: POST collector browser start (already running but no harm)
# POST("B5 POST /collector/browser/start — SKIP already running")

print("\n\n" + "=" * 80)
print("STEP 3: Wait 10s for recovery pipeline to settle, then verify")
print("=" * 80)
time.sleep(10)

GET("C1 xhs_pause_state",   "/api/xhs/collect-pause-state")
GET("C2 platform_health",    "/api/platform-health")
GET("C3 collector_status",   "/api/collector/status")
GET("C4 recovery_stats",     "/api/recovery/stats")
GET("C5 health_summary",     "/api/system/health/summary")
GET("C6 notes_count",        "/api/stats")
try:
    r = sess.get(BASE + "/api/stats", timeout=10)
    j = r.json()
    after_notes = j.get('total_notes') or j.get('notes_count') or (j.get('stats') or {}).get('total_notes')
except:
    after_notes = None
print(f"\n>>> AFTER notes_count = {after_notes}  (before = {before_notes})")
print(f">>> NOTE: Immediate notes growth NOT expected immediately; XHS search/details/comment chain takes 2-5 min.")
print(f">>> Next scheduled auto-collect was 08:00 — we started collector early so results will arrive in background.")
