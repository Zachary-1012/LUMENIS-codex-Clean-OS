# -*- coding: utf-8 -*-
"""Release Gate · API Smoke：在 conftest 隔离数据库中创建一次性测试 owner/session，
验证核心端点与认证边界；测试结束清理测试身份，不依赖 seed 中存在真实 owner。

GAP-01：由顶层脚本（import 即 sys.exit，会打断 pytest 收集）改造为规范 pytest 用例，
同时保留 `python tests/test_api_smoke.py` 直接运行的能力。
"""
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_api_smoke_release_gate(monkeypatch):
    from app import app
    from lumenis.auth.security import generate_token
    from lumenis.auth.models import get_db, init_auth_db
    from lumenis.system.collector.adapters import health_center
    import collection_api

    init_auth_db()
    conn = get_db()
    # The smoke suite must be self-contained on an ownerless CI seed. This
    # identity exists only in pytest's disposable database and is never used
    # for password login.
    test_username = 'api-smoke-test-owner'
    conn.execute(
        "DELETE FROM v4_sessions WHERE user_id IN (SELECT id FROM v4_users WHERE username=?)",
        (test_username,))
    conn.execute("DELETE FROM v4_users WHERE username=?", (test_username,))
    conn.execute(
        "INSERT INTO v4_users(username,password_hash,role,display_name,status) VALUES(?,?,?,?,?)",
        (test_username, 'test-only-unused-password-hash', 'owner', 'API smoke test', 'active'))
    u = conn.execute(
        "SELECT id,username,role FROM v4_users WHERE username=?", (test_username,)
    ).fetchone()
    assert u, '测试身份创建失败'
    token = generate_token(u['id'])
    exp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + 3600))
    conn.execute(
        "INSERT INTO v4_sessions(user_id,token,ip,user_agent,expires_at) VALUES(?,?,?,?,?)",
        (u['id'], token, '127.0.0.1', 'api-smoke', exp))
    conn.commit(); conn.close()
    H = {'Authorization': 'Bearer ' + token}
    fail = []
    try:
        # Exercise the real health aggregation and API/auth route without
        # reading this workstation's local XHS account state.
        monkeypatch.setattr(health_center, '_xhs_runtime', lambda: {
            'circuit': {}, 'last': None, 'session_valid': None, 'session_msg': ''})
        # The legacy collection health endpoint reads only local circuit/DB
        # state. Stub the circuit reader so this smoke never touches a real
        # account or its runtime files.
        monkeypatch.setattr(collection_api.xhs_cookie_bridge, 'get_circuit_state', lambda: {})
        print('测试会话用户 =', u['username'], u['role'])
        c = app.test_client()
        gets = ['/healthz', '/api/platform-health', '/api/xhs/collect-health',
                '/v4/console/', '/v4/collect/', '/v4/settings/', '/v4/version-center/',
                '/v4/version-center/api/status', '/v4/adapters/health', '/v4/adapters/recovery/platforms']
        for path in gets:
            response = c.get(path, headers=H)
            code = response.status_code
            print(f'{code:4} {"OK " if code == 200 else "FAIL"} {path}')
            if code != 200:
                fail.append((path, code))
            if path in {'/v4/console/', '/v4/collect/', '/v4/settings/', '/v4/version-center/'}:
                if not response.is_json or response.get_json().get('ui_reset') is not True:
                    fail.append((path, 'expected ui_reset JSON shell'))
                if response.mimetype == 'text/html':
                    fail.append((path, 'unexpected HTML response'))

        anon = app.test_client()
        for path in ['/api/platform-health', '/api/xhs/collect-health']:
            code = anon.get(path).status_code
            print(f'{code:4} {"OK " if code == 401 else "FAIL"} 匿名 {path}（期望401）')
            if code != 401:
                fail.append(('anon:' + path, code))
        assert anon.get('/healthz').status_code == 200

        d = c.get('/api/platform-health', headers=H).get_json()
        assert len(d.get('platforms', [])) >= 7, '健康平台槽位不足 7'
        xhs = [p for p in d['platforms'] if p['platform'] == 'xhs'][0]
        print('overall =', d.get('overall'), '| xhs =', xhs.get('status'), xhs.get('triage'))
        # GAP-01：以断言替代 sys.exit，纳入 pytest 结果体系
        assert not fail, f'API smoke 未通过端点: {fail}'
    finally:
        # 自清理：只在 conftest 的 disposable DB 副本中删除测试身份和会话。
        try:
            cc = get_db()
            cc.execute("DELETE FROM v4_sessions WHERE token=? AND user_agent='api-smoke'", (token,))
            cc.execute("DELETE FROM v4_users WHERE username=?", (test_username,))
            cc.commit(); cc.close()
            print('测试会话已清理')
        except Exception as _e:
            print('测试会话清理失败:', _e)
        print('\nAPI_SMOKE RESULT:', 'ALL_PASS' if not fail else f'FAIL {fail}')


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
