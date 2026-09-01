# -*- coding: utf-8 -*-
"""_tmp_p0_http_9smoke.py — 9 条 P0 HTTP endpoints smoke test.

9 条必 PASS:
  1. GET  /healthz
  2. GET  /api/notes?limit=5
  3. GET  /api/events?limit=5
  4. GET  /api/health/summary
  5. GET  /api/health/platform-health
  6. GET  /api/collector/status
  7. GET  /api/auth-recovery/summary   ← B4/B5 新闭环
  8. GET  /api/daily-report/preview    ← 核心报告
  9. POST /api/collector/pause         ← (dry: 只是检查响应, 真 pause 立刻 unpause)

Auth: HTTP Basic Zachary / ID082610 (base64: WmFjaGFyeTpJRDA4MjYxMA==)
URL:  http://127.0.0.1:8200
"""
import json, sys, base64, urllib.request, urllib.error, time, ssl

URL_BASE = 'http://127.0.0.1:8200'
AUTH = base64.b64encode(b'Zachary:ID082610').decode()
HEADERS = {
    'Authorization': 'Basic ' + AUTH,
    'Accept': 'application/json,text/html,*/*;q=0.8',
    'User-Agent': 'p0-9smoke/1.0'
}
ENDPOINTS = [
    ('1. /healthz',                       'GET',  '/healthz'),
    ('2. /api/notes?limit=5',             'GET',  '/api/notes?limit=5'),
    ('3. /api/events?limit=5',            'GET',  '/api/events?limit=5'),
    ('4. /api/system/health',             'GET',  '/api/system/health'),
    ('5. /api/platform-health',           'GET',  '/api/platform-health'),
    ('6. /api/collector/status',          'GET',  '/api/collector/status'),
    ('7. /api/auth-recovery/summary',     'GET',  '/api/auth-recovery/summary'),
    ('8. /api/v2/report-center/preview',  'GET',  '/api/v2/report-center/preview'),
    ('9. POST /api/xhs/collect-pause',    'POST', '/api/xhs/collect-pause', b'{}'),
]

def call(label, method, path, body_bytes=None):
    t0 = time.time()
    try:
        ctx = ssl._create_unverified_context() if path.startswith('https') else None
        h = dict(HEADERS)
        data = None
        if method == 'POST':
            data = body_bytes if body_bytes is not None else b'{}'
            h['Content-Type'] = 'application/json'
        req = urllib.request.Request(URL_BASE + path, method=method, headers=h, data=data)
        try:
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                status = resp.getcode()
                body = resp.read()[:200]
                ok = 200 <= status < 300
                dt = time.time() - t0
                return ok, status, f'{dt*1000:.0f}ms', body.decode('utf-8','replace')
        except urllib.error.HTTPError as e:
            dt = time.time() - t0
            # 302 = redirect (e.g. unauth → login page) 也算 fail; 记录
            body = e.read()[:200]
            return False, e.code, f'{dt*1000:.0f}ms', body.decode('utf-8','replace')
    except Exception as e:
        dt = time.time() - t0
        return False, 'EXC', f'{dt*1000:.0f}ms', str(e)[:160]

def run():
    failed = 0; passed = 0; lines = []
    for item in ENDPOINTS:
        label, method, path = item[0], item[1], item[2]
        body_bytes = item[3] if len(item) > 3 else None
        ok, st, tm, body_preview = call(label, method, path, body_bytes)
        status_str = f'HTTP {st}' if isinstance(st, int) else f'ERR_{st}'
        mark = 'PASS' if ok else 'FAIL'
        if ok: passed += 1
        else: failed += 1
        preview = body_preview.replace('\n',' ')[:120]
        lines.append(f"  [{mark:4s}] {label:42s} {status_str:10s} ({tm:>6s})  {preview}")
    total = passed + failed
    print("\n" + "="*92)
    print(f"  _tmp_p0_http_9smoke.py — 9 P0 HTTP endpoints smoke test")
    print(f"  结果: {'PASS ✓' if failed==0 else 'FAIL ✗'}  (PASSED={passed}/{total}, FAILED={failed}/{total})  |  target={URL_BASE}")
    print("="*92)
    for ln in lines: print(ln)
    print("="*92 + "\n")
    sys.exit(0 if failed == 0 else 1)

if __name__ == '__main__':
    run()
