# -*- coding: utf-8 -*-
"""版本中心后端接口只读集成测试：登录 -> status/history/config。不触发 save/push/pull/rollback。"""
import io, os, sys, json, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = 'http://127.0.0.1:8201'

def call(path, method='GET', token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE+path, data=data, method=method)
    req.add_header('Content-Type', 'application/json')
    if token: req.add_header('Authorization', 'Bearer '+token)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return None, {'err': str(e)}

st, login = call('/v4/auth/login', 'POST', body={'username':'Zachary','password':'ID082610'})
token = login.get('token') or (login.get('data') or {}).get('token')
print('登录=', bool(token), 'status', st)
if not token:
    print('登录返回:', json.dumps(login, ensure_ascii=False)[:300]); sys.exit(1)

for p in ['/v4/version-center/api/status', '/v4/version-center/api/history?limit=5', '/v4/version-center/api/config']:
    st, r = call(p, token=token)
    print('\n====', p, 'HTTP', st, '====')
    if 'status' in p and p.endswith('status'):
        s = r.get('status', {})
        for k in ('version','branch','head_short','sync_state','ahead','behind','changed_count','remote_url'):
            print('  ', k, '=', s.get(k))
        lc = s.get('last_commit') or {}
        print('   last_commit=', lc.get('time'), (lc.get('subject') or '')[:40])
    elif 'history' in p:
        print('  success=', r.get('success'), '历史条数=', len(r.get('items', [])))
        for it in (r.get('items') or [])[:5]:
            print('   ', it.get('short'), it.get('subject','')[:44])
    else:
        print('  ', json.dumps(r, ensure_ascii=False)[:240])
