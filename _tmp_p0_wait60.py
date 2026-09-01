"""P0: 60s wait + check if collector actually produced notes, plus re-check platform_health XHS BLOCKED status."""
import requests, json, time
from requests.auth import HTTPBasicAuth
BASE = "http://127.0.0.1:8200"
AUTH = HTTPBasicAuth("Zachary", "ID082610")
sess = requests.Session()
sess.auth = AUTH

# baseline — DB path direct query to avoid API stats confusion
import sqlite3, os
conn = sqlite3.connect(r'd:\Taikoo-monitor-new\data\monitor.db')
c = conn.cursor()
c.execute("SELECT COUNT(*), MAX(collected_at) FROM notes")
cnt_before, last_before = c.fetchone()
conn.close()
print(f"[BASELINE DB] notes COUNT = {cnt_before}, MAX(collected_at) = {last_before}")
print(f"[BASELINE] Waiting 60 seconds for XHS collector round-trip...")

time.sleep(60)

conn = sqlite3.connect(r'd:\Taikoo-monitor-new\data\monitor.db')
c = conn.cursor()
c.execute("SELECT COUNT(*), MAX(collected_at) FROM notes")
cnt_after, last_after = c.fetchone()
# recent XHS BLOCKED in collection_logs
c.execute("SELECT id, started_at, finished_at, status, notes_collected, message FROM collection_logs ORDER BY id DESC LIMIT 5")
logs = c.fetchall()
conn.close()

print(f"\n[AFTER 60s DB] notes COUNT   = before={cnt_before}  →  after={cnt_after}   ⇒ GROWTH = {cnt_after - cnt_before}")
print(f"[AFTER 60s DB] MAX collected = before={last_before}  →  after={last_after}")
print(f"\n[COLLECTION_LOGS last 5]")
for row in logs:
    print(f"    {row}")

# Re-check platform_health XHS status + stop_request
r = sess.get(BASE + "/api/platform-health", timeout=10)
ph = r.json()
xhs = next((p for p in ph['platforms'] if p['platform']=='xhs'), None)
print(f"\n[PLATFORM_HEALTH XHS] overall={ph['overall']} counts={ph['counts']}")
if xhs:
    print(json.dumps(xhs, indent=2, ensure_ascii=False))

# Collector current task
r = sess.get(BASE + "/api/collector/status", timeout=10)
cs = r.json()
ct = cs.get('current_task') or {}
print(f"\n[COLLECTOR STATUS] is_running={cs.get('is_running')} browser={cs.get('browser_running')}")
if ct:
    print(f"    task_id={ct.get('id')} status={ct.get('status')} new_notes={ct.get('new_notes')} progress={ct.get('progress')}")
    print(f"    errors={ct.get('errors')} start_time={ct.get('start_time')}")
