"""Scan recent logs for the collector error (task collect_20260902_041349)"""
import os, glob, datetime, re
LOG_DIRS = [r'd:\Taikoo-monitor-new', r'd:\Taikoo-monitor-new\data\logs']
CUTOFF = datetime.datetime.now().timestamp() - 7200  # last 2h
candidates = []
for d in LOG_DIRS:
    for p in glob.glob(os.path.join(d, '*.log*')):
        try:
            st = os.stat(p)
            if st.st_mtime >= CUTOFF and st.st_size > 0:
                candidates.append((st.st_mtime, st.st_size, p))
        except: pass
candidates.sort(reverse=True)
print(f"Found {len(candidates)} recently touched log files:")
for t, sz, p in candidates[:15]:
    print(f"  {datetime.datetime.fromtimestamp(t):%Y-%m-%d %H:%M:%S}  {sz:>8}B  {os.path.relpath(p, r'd:\Taikoo-monitor-new').replace(chr(92),'/')}")

# Search for failure patterns in tail of each candidate file
needles = ['collect_20260902_041349', '执行采集失败', '采集失败', 'Traceback', 'Exception', 
           'xhs_cookie_bridge', 'IP_RISK_OR_CAPTCHA', 'CDP', '浏览器', 'cookie', '风控', 'cooldown']
print(f"\n====== FAILURE SEARCH (tail 400 lines of each top-8 candidate) ======")
for t, sz, p in candidates[:8]:
    rel = os.path.relpath(p, r'd:\Taikoo-monitor-new').replace(chr(92),'/')
    print(f"\n--- FILE: {rel}  size={sz}B  @ {datetime.datetime.fromtimestamp(t)} ---")
    try:
        with open(p, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        tail = lines[-400:]
        hits = False
        for i, ln in enumerate(tail, max(1, len(lines)-399)):
            if any(n.lower() in ln.lower() for n in needles):
                if not hits:
                    hits = True
                    print("  (showing matching lines)")
                clean = ln.rstrip()
                if len(clean) > 300: clean = clean[:299]+"…"
                print(f"  L{i:>4}: {clean}")
        if not hits:
            # print last 5 lines to confirm its content / datetime
            last5 = [ln.rstrip() for ln in tail[-5:] if ln.strip()]
            print(f"  (no hits; last 5 lines of file):")
            for ln in last5[-3:]:
                print(f"    {ln[:200]}")
    except Exception as e:
        print(f"  [read fail {e}]")
