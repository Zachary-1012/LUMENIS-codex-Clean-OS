# -*- coding: utf-8 -*-
"""Release Gate · API Smoke：进程内为 owner 签发一次性测试会话（不使用/打印密码），
验证核心端点真实可用，并验证匿名仍被拦截。测试结束自动删除测试会话，不污染生产库。"""
import io, os, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app
from v4_upgrade.auth.security import generate_token
from v4_upgrade.auth.models import get_db, init_auth_db

init_auth_db()
conn = get_db()
u = conn.execute("SELECT id,username,role FROM v4_users WHERE role='owner' AND status='active' ORDER BY id LIMIT 1").fetchone()
assert u, '无 owner 账号'
token = generate_token(u['id'])
exp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()+3600))
conn.execute("INSERT INTO v4_sessions(user_id,token,ip,user_agent,expires_at) VALUES(?,?,?,?,?)",
             (u['id'], token, '127.0.0.1', 'api-smoke', exp)); conn.commit(); conn.close()
H = {'Authorization': 'Bearer ' + token}
fail = []
try:
    print('测试会话用户 =', u['username'], u['role'])
    c = app.test_client()
    gets = ['/healthz','/api/platform-health','/api/xhs/collect-health',
            '/v4/console/','/v4/collect/','/v4/settings/','/v4/version-center/',
            '/v4/version-center/api/status','/v4/adapters/health','/v4/adapters/recovery/platforms']
    for path in gets:
        code = c.get(path, headers=H).status_code
        print(f'{code:4} {"OK " if code==200 else "FAIL"} {path}')
        if code != 200: fail.append((path, code))

    anon = app.test_client()
    for path in ['/api/platform-health','/api/xhs/collect-health']:
        code = anon.get(path).status_code
        print(f'{code:4} {"OK " if code==401 else "FAIL"} 匿名 {path}（期望401）')
        if code != 401: fail.append(('anon:'+path, code))
    assert anon.get('/healthz').status_code == 200

    d = c.get('/api/platform-health', headers=H).get_json()
    assert len(d.get('platforms', [])) >= 7, '健康平台槽位不足 7'
    xhs = [p for p in d['platforms'] if p['platform'] == 'xhs'][0]
    print('overall =', d.get('overall'), '| xhs =', xhs.get('status'), xhs.get('triage'))
finally:
    # 自清理：删除一次性测试会话，保证生产库不留测试 token
    try:
        cc = get_db(); cc.execute("DELETE FROM v4_sessions WHERE token=? AND user_agent='api-smoke'", (token,)); cc.commit(); cc.close()
        print('测试会话已清理')
    except Exception as _e:
        print('测试会话清理失败:', _e)

print('\nAPI_SMOKE RESULT:', 'ALL_PASS' if not fail else f'FAIL {fail}')
sys.exit(1 if fail else 0)
