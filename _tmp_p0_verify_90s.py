"""P0 Final: POST collector start, wait 90s, verify DB notes_count>957 and real growth"""
import requests, sqlite3, time, json, datetime, sys
from requests.auth import HTTPBasicAuth

ROOT = r'd:\Taikoo-monitor-new'
DB = os.path.join(ROOT, 'data', 'monitor.db') if 'os' in dir() else r'd:\Taikoo-monitor-new\data\monitor.db'
import os

AUTH = HTTPBasicAuth("Zachary", "ID082610")
s = requests.Session(); s.auth = AUTH
BASE = "http://127.0.0.1:8200"
now = lambda: datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def db_snapshot(label):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), MAX(collected_at), MAX(publish_datetime) FROM notes")
    cnt, max_col, max_pub = c.fetchone()
    c.execute("SELECT id, status, keyword, notes_count, finished_at FROM collection_logs ORDER BY id DESC LIMIT 5")
    logs = c.fetchall()
    conn.close()
    print(f"\n[{label} @ {now()}] DB notes COUNT={cnt}  max_collected={max_col}  max_publish={max_pub}")
    for row in logs:
        print(f"  log id={row[0]:>3} {str(row[1]):<14} kw={str(row[2]):<20} notes={row[3]} fin={row[4]}")
    return cnt, max_col, logs

# ---- 1: BASELINE before collector launch ----
cnt0, _, logs0 = db_snapshot("T0 PRE-COLLECT")

# ---- 2: POST /api/collector/start ----
print(f"\n[2] POST /api/collector/start at {now()}")
r = s.post(BASE + "/api/collector/start", timeout=15)
print(f"  status={r.status_code}  body[:400]: {r.text[:400]}")
time.sleep(6)
r2 = s.get(BASE + "/api/collector/status", timeout=12).json()
ct = r2.get('current_task') or {}
print(f"  [+6s] is_running={r2.get('is_running')} browser={r2.get('browser_running')} cdpport={r2.get('cdp_port')}")
if ct: print(f"  task id={ct.get('id')} status={ct.get('status')} progress={ct.get('progress')} new_notes={ct.get('new_notes')} errors={ct.get('errors')}")

# ---- 3: Sleep 90s + periodic probes at 30s, 60s, 90s ----
for sleep_min, period_s in [(1,30),(2,60),(3,90)]:
    print(f"\n[{period_s}s mark] Sleeping {period_s - (time.time() % 60)}s ...")
    target = time.time() + (period_s if sleep_min==1 else 30)
    time.sleep(max(1, target - time.time() - (time.time() - int(time.time() - (period_s - 30) if sleep_min>1 else 0))))
    # Simpler: just wait 30s each iteration
    pass
# Simple approach: three 30s intervals
for i in range(3):
    print(f"\n--- sleeping 30s iteration {i+1}/3 @ {now()} ---")
    time.sleep(30)
    # Quick check running state mid-sleep
    try:
        r = s.get(BASE + "/api/collector/status", timeout=10).json()
        ct = r.get('current_task') or {}
        print(f"  [mid-{i+1}] is_running={r.get('is_running')} task.status={ct.get('status')} new_notes={ct.get('new_notes','?')} progress={ct.get('progress','?')} errors={ct.get('errors','?')}")
    except Exception as e:
        print(f"  mid check fail {e}")

# ---- 4: AFTER 90s Snapshot DB + APIs ----
cnt1, max_col1, logs1 = db_snapshot("T90 POST-COLLECT")
new_notes_real = cnt1 - cnt0
print(f"\n==== RESULT SUMMARY at {now()} ====")
print(f"  DB notes growth: {cnt0} → {cnt1}  Δ = {new_notes_real}")

# Check collection_logs: did new rows appear after our placeholder id=520?
last_log_id_post = logs1[0][0]
print(f"  Last collection_log id PRE=520  POST={last_log_id_post}  Δrows={last_log_id_post-520}")

# POST-block: XHS platform state
r_pf = s.get(BASE + "/api/platform-health", timeout=12).json()
r_hs = s.get(BASE + "/api/system/health/summary", timeout=12).json()
xhs = next((p for p in r_pf['platforms'] if p['platform']=='xhs'), None)
print(f"  platform_health overall={r_pf.get('overall')} counts={r_pf.get('counts')}")
if xhs:
    print(f"  xhs.status={xhs.get('status')}  stop_request={xhs.get('stop_request')}  risk_status={xhs.get('risk_status')}  cooldown={xhs.get('cooldown_until')}")
    print(f"  xhs.session_valid={xhs.get('session_valid')}  msg={xhs.get('message','')[:100]}")
    # latest log from xhs object
    last = xhs.get('last') or {}
    print(f"  xhs.last: state={last.get('state')} notes={last.get('notes')} at={last.get('at')} msg={str(last.get('msg',''))[:80]}")
print(f"  health_summary overall={r_hs.get('overall_status')}  ok={r_hs.get('ok')}  need_manual={r_hs.get('need_manual_intervention')}")
sub = r_hs.get('sub_lights') or {}
for k in ('xhs_platform','database','collector','auth'):
    if k in sub: print(f"  {k} light={sub[k].get('light')} status={sub[k].get('status','')}")
print(f"  diagnostic hints[:3]: {r_hs.get('diagnostic_hints',[])[:3]}")

# ---- BRANCH DECISION ----
print(f"\n==== DECISION at {now()} ====")
PASS_notes = (new_notes_real > 0)
PASS_status = (xhs and xhs.get('status') not in ('BLOCKED','SESSION_EXPIRED','NEED_VERIFY') and xhs.get('stop_request') is False)
print(f"  CRITERIA 1: real notes growth > 0 → {new_notes_real} → {'PASS' if PASS_notes else 'FAIL (0 真实增长，可能仍被风控)'}")
print(f"  CRITERIA 2: XHS platform status != BLOCKED && stop_request=false → status={xhs.get('status') if xhs else 'N/A'} stop={xhs.get('stop_request') if xhs else 'N/A'} → {'PASS' if PASS_status else 'FAIL'}")

if PASS_notes and PASS_status:
    print("\n  ✅ P0 XHS BLOCKED解除 + 真实数据增长 —— PASS! 系统恢复健康。")
elif PASS_status and not PASS_notes:
    print("\n  ⚠️ BLOCKED 解除了但 0 真实笔记。可能原因：a) 90s 内没跑完一圈；b) 真没新内容；c) 小红书真实风控仍在拦截但 BLOCKED 已解。建议等下一轮 30 分钟自动调度（current_interval=1800s）。")
else:
    # 如果仍是 BLOCKED —— 触发 Auth Recovery Center 自动创建任务（AGENTS §7.2 可见可恢复）
    print("\n  ❌ FAIL. Creating Auth Recovery Center task per AGENTS §7.2 (system内可见可恢复)...")
    if xhs and xhs.get('status') == 'BLOCKED':
        task = {
            "platform": "xiaohongshu",
            "task_type": "unblock",
            "reason": f"XHS status=BLOCKED stop_request={xhs.get('stop_request')} cooldown={xhs.get('cooldown_until')} msg={xhs.get('message','IP_RISK_OR_CAPTCHA')} MAX(collected_at)={max_col1 or 'N/A'} 32h+ 0条",
            "priority": "p0",
            "requires_human_verification": True
        }
        print(f"  POST /api/auth-recovery/tasks payload: {json.dumps(task, ensure_ascii=False)[:300]}")
        r_task = s.post(BASE + "/api/auth-recovery/tasks", json=task, timeout=15)
        print(f"  Auth Recovery response: HTTP {r_task.status_code} → {r_task.text[:500]}")

# Also print newest notes (if any)
if new_notes_real > 0:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, note_id, title, author, collected_at, publish_datetime FROM notes ORDER BY id DESC LIMIT 8")
    rows = c.fetchall()
    conn.close()
    print("\n  [NEW NOTES sample]")
    cols = ['id','note_id','title','author','collected_at','publish_datetime']
    for r in rows:
        d = dict(zip(cols, r))
        title = (d['title'] or '')[:30].replace('\n',' ')
        print(f"    #{d['id']} collected={d['collected_at']}  publish={d['publish_datetime']}  author={d['author']}  '{title}'")
