# -*- coding: utf-8 -*-
"""只读验证 Auth Recovery 后端链路（不调 start，避免真开浏览器标签）。"""
import io, os, sys, json
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import requests
B = 'http://127.0.0.1:8201'
s = requests.Session()
r = s.post(B + '/v4/auth/login', json={'username': 'Zachary', 'password': 'Zachary01'}, timeout=10)
d = r.json()
print('登录:', d.get('success'))
tok = d.get('token', '')
H = {'Authorization': 'Bearer ' + tok} if tok else {}

def show(name, path, method='GET', body=None):
    rr = s.request(method, B + path, headers=H, json=body, timeout=20)
    try:
        j = rr.json()
    except Exception:
        print(f'{name}: HTTP {rr.status_code} 非JSON'); return None
    if name == '全局健康':
        hs = j.get('health', [])
        print(f'{name}: 平台数={len(hs)} 状态分布=', {})
        from collections import Counter
        print('   ', dict(Counter(x.get('state') for x in hs)))
        for x in hs[:12]:
            print('    -', x.get('platform'), x.get('display'), x.get('state'), 'fetched=', x.get('fetched'), 'needs_browser=', x.get('needs_browser'))
    elif name == '可恢复平台':
        ps = j.get('platforms', [])
        print(f'{name}: {len(ps)} 个 ->', [(p["platform"], p["display"], p["port"]) for p in ps])
    else:
        print(f'{name}:', json.dumps(j, ensure_ascii=False)[:300])
    return j

show('可恢复平台', '/v4/adapters/recovery/platforms')
show('全局健康', '/v4/adapters/health')
show('恢复任务状态', '/v4/adapters/recovery/status')
show('小红书只读登录态探测(launch=False,浏览器没开应UNKNOWN不报错)', '/v4/adapters/recovery/health/xiaohongshu')
show('风控快照', '/v4/adapters/risk')
print('AUTH_API_CHECK_DONE')
