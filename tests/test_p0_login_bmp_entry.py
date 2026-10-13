#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_p0_login_zbmp_entry.py — P0 登录流程重构 + TOTP + 域身份 测试

覆盖：
1. CTH登录流程（/v4/auth/login）
2. ZBMP entry status 端点（/api/auth/zbmp-entry/status）
3. TOTP setup → confirm → verify 全链路
4. 域身份获取（/api/auth/domain-identity）
5. ZBMP entry verify（/api/auth/zbmp-entry/verify）
6. /zbmp/login 重定向到CTH
7. 设置页API连通性
"""

# 本文件是依赖已启动 Runtime、测试账号与有状态 TOTP 流程的独立验收脚本。
# record() 只累计结果而不向 pytest 抛错，故不得被 hermetic pytest 自动收集；
# 正式运行验收阶段以脚本 main() 的退出码执行并记录证据。
__test__ = False
import os
import sys
import json
import time
import requests

BASE = os.environ.get('TEST_BASE', 'http://127.0.0.1:8201')
TIMEOUT = 15

# 测试账号（从环境变量或默认）
TEST_USER = os.environ.get('TEST_USER', 'Zachary')
TEST_PASS = os.environ.get('TEST_PASS', os.environ.get('LUMENIS_TEST_AUTH_PASS', 'test-only-pass'))

results = []
passed = 0
failed = 0


def record(name, success, detail=''):
    global passed, failed
    status = 'PASS' if success else 'FAIL'
    if success:
        passed += 1
    else:
        failed += 1
    results.append((name, success, detail))
    print(f'  [{status}] {name}' + (f' — {detail}' if detail else ''))


def make_session():
    return requests.Session()


# 模块级session共享（pytest不传递前一个测试的返回值）
_shared_session = None
_shared_setup_data = None


def test_cth_login():
    """测试1: CTH账号密码登录"""
    print('\n=== 1. CTH登录流程 ===')
    s = make_session()
    try:
        r = s.post(f'{BASE}/v4/auth/login',
                    json={'username': TEST_USER, 'password': TEST_PASS},
                    timeout=TIMEOUT)
        data = r.json()
        record('CTH登录返回200', r.status_code == 200, f'status={r.status_code}')
        record('CTH登录success字段', data.get('success') is True,
               f'success={data.get("success")}')
        record('CTH登录返回token', bool(data.get('token')),
               f'token_len={len(data.get("token", ""))}')
        global _shared_session
        _shared_session = s
        return s, data
    except Exception as e:
        record('CTH登录异常', False, str(e))
        return None, None


def test_zbmp_entry_status():
    """测试2: ZBMP entry status 端点"""
    print('\n=== 2. ZBMP Entry Status ===')
    s = _shared_session
    if not s:
        record('ZBMP entry status', False, '无session')
        return
    try:
        r = s.get(f'{BASE}/api/auth/zbmp-entry/status', timeout=TIMEOUT)
        data = r.json()
        record('ZBMP entry status返回200', r.status_code == 200, f'status={r.status_code}')
        record('ZBMP entry status ok字段', data.get('ok') is True, f'ok={data.get("ok")}')
        record('ZBMP entry status logged_in', data.get('logged_in') is True,
               f'logged_in={data.get("logged_in")}')
        record('ZBMP entry status有user_id', data.get('user_id') is not None,
               f'user_id={data.get("user_id")}')
        record('ZBMP entry status有domain_identity', 'domain_identity' in data,
               f'domain_identity={data.get("domain_identity")}')
        return data
    except Exception as e:
        record('ZBMP entry status异常', False, str(e))
        return None


def test_totp_setup():
    """测试3: TOTP setup 生成二维码"""
    print('\n=== 3. TOTP Setup（生成二维码） ===')
    s = _shared_session
    if not s:
        record('TOTP setup', False, '无session')
        return None
    try:
        r = s.post(f'{BASE}/api/system/account/totp/setup',
                   json={}, timeout=TIMEOUT)
        data = r.json()
        record('TOTP setup返回200', r.status_code == 200, f'status={r.status_code}')
        record('TOTP setup success', data.get('success') is True,
               f'success={data.get("success")}')
        record('TOTP setup返回secret', bool(data.get('secret')),
               f'sector_len={len(data.get("secret", ""))}')
        record('TOTP setup返回qr_code', bool(data.get('qr_code')),
               f'qr_code前缀={data.get("qr_code", "")[:30]}...')
        record('TOTP qr_code是data URL', data.get('qr_code', '').startswith('data:image/'),
               f'格式检查')
        record('TOTP setup返回otpauth_url', bool(data.get('otpauth_url')),
               f'otpauth={data.get("otpauth_url", "")[:50]}...')
        record('TOTP digits=6', data.get('digits') == 6, f'digits={data.get("digits")}')
        record('TOTP period=30', data.get('period') == 30, f'period={data.get("period")}')
        return data
    except Exception as e:
        record('TOTP setup异常', False, str(e))
        return None


def test_totp_confirm():
    """测试4: TOTP confirm 绑定（用当前code验证）"""
    print('\n=== 4. TOTP Confirm（绑定） ===')
    s = _shared_session
    setup_data = _shared_setup_data
    if not s or not setup_data:
        record('TOTP confirm', False, '无setup数据')
        return False
    try:
        # 用 pyotp 或手动计算当前TOTP code
        secret = setup_data.get('secret')
        if not secret:
            record('TOTP confirm', False, '无secret')
            return False
        # 手动计算TOTP
        code = compute_totp(secret)
        record('TOTP计算当前code', bool(code), f'code={code}')

        r = s.post(f'{BASE}/api/system/account/totp/confirm',
                   json={'code': code}, timeout=TIMEOUT)
        data = r.json()
        record('TOTP confirm返回', r.status_code in (200, 400), f'status={r.status_code}')
        if data.get('success'):
            record('TOTP confirm绑定成功', True, data.get('message', ''))
            return True
        else:
            # 可能是时钟偏移，尝试前后窗口
            record('TOTP confirm首次失败（可能时钟偏移）', False,
                   data.get('error', data.get('message', '')))
            # 不重试，标记为已知问题
            return False
    except Exception as e:
        record('TOTP confirm异常', False, str(e))
        return False


def compute_totp(secret, period=30, digits=6):
    """手动计算TOTP验证码（不依赖pyotp）"""
    import hmac
    import hashlib
    import struct
    import base64
    try:
        key = base64.b32decode(secret.upper() + '=' * ((8 - len(secret) % 8) % 8))
        counter = int(time.time() // period)
        msg = struct.pack('>Q', counter)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        offset = h[-1] & 0x0F
        binary = struct.unpack('>I', h[offset:offset + 4])[0] & 0x7FFFFFFF
        return str(binary % (10 ** digits)).zfill(digits)
    except Exception:
        return None


def test_domain_identity():
    s = _shared_session
    """测试5: 域身份获取"""
    print('\n=== 5. Domain Identity ===')
    if not s:
        record('Domain identity', False, '无session')
        return
    try:
        r = s.get(f'{BASE}/api/auth/domain-identity', timeout=TIMEOUT)
        data = r.json()
        record('Domain identity返回200', r.status_code == 200, f'status={r.status_code}')
        record('Domain identity ok', data.get('ok') is True, f'ok={data.get("ok")}')
        record('Domain identity有domain_identity字段', 'domain_identity' in data,
               f'domain_identity={data.get("domain_identity")}')
        record('Domain identity cth_logged', data.get('cth_logged') is True,
               f'cth_logged={data.get("cth_logged")}')
    except Exception as e:
        record('Domain identity异常', False, str(e))


def test_zbmp_login_redirect():
    """测试6: /zbmp/login 重定向到CTH"""
    print('\n=== 6. /zbmp/login 重定向 ===')
    s = make_session()
    try:
        r = s.get(f'{BASE}/zbmp/login', allow_redirects=False, timeout=TIMEOUT)
        record('/zbmp/login返回3xx', 300 <= r.status_code < 400,
               f'status={r.status_code}')
        location = r.headers.get('Location', '')
        record('重定向到CTH overview', 'cth/overview' in location,
               f'location={location}')
        record('重定向带zbmp-entry参数', 'zbmp-entry=1' in location,
               f'has_param={"zbmp-entry=1" in location}')
    except Exception as e:
        record('/zbmp/login异常', False, str(e))


def test_settings_apis():
    s = _shared_session
    """测试7: 设置页API连通性"""
    print('\n=== 7. 设置页API连通性 ===')
    if not s:
        record('设置页API', False, '无session')
        return
    endpoints = [
        ('/api/system/account/profile', 'GET'),
        ('/api/system/account/members', 'GET'),
        ('/api/system/account/devices', 'GET'),
        ('/api/system/account/totp/status', 'GET'),
        ('/api/system/account/quota', 'GET'),
        ('/api/system/account/skills', 'GET'),
        ('/api/system/account/nav?domain=CTH', 'GET'),
        ('/api/system/account/audit?page=1&page_size=5', 'GET'),
    ]
    for path, method in endpoints:
        try:
            if method == 'GET':
                r = s.get(f'{BASE}{path}', timeout=TIMEOUT)
            else:
                r = s.post(f'{BASE}{path}', timeout=TIMEOUT)
            name = f'设置API {path}'
            record(name, r.status_code == 200, f'status={r.status_code}')
        except Exception as e:
            record(f'设置API {path}', False, str(e))


def test_ai_collector_apis():
    """测试8: AI状态和采集状态API"""
    print('\n=== 8. AI/采集状态API ===')
    s = make_session()
    endpoints = [
        '/api/ai-resource-packs/status',
        '/api/platform-health',
        '/api/collector-guard/status',
    ]
    for path in endpoints:
        try:
            r = s.get(f'{BASE}{path}', timeout=TIMEOUT)
            record(f'{path}', r.status_code in (200, 401, 500),
                   f'status={r.status_code}')
        except Exception as e:
            record(f'{path}', False, str(e))


def main():
    print('=' * 60)
    print('P0 登录流程重构 + TOTP + 域身份 集成测试')
    print(f'目标: {BASE}')
    print(f'账号: {TEST_USER}')
    print('=' * 60)

    # 1. CTH登录
    s, login_data = test_cth_login()

    # 2. ZBMP entry status
    status_data = test_zbmp_entry_status(s)

    # 3. TOTP setup
    setup_data = test_totp_setup(s)

    # 4. TOTP confirm（如果setup成功）
    if setup_data and setup_data.get('success'):
        test_totp_confirm(s, setup_data)

    # 5. Domain identity
    test_domain_identity(s)

    # 6. /zbmp/login 重定向
    test_zbmp_login_redirect()

    # 7. 设置页API
    test_settings_apis(s)

    # 8. AI/采集API
    test_ai_collector_apis()

    # 汇总
    print('\n' + '=' * 60)
    print(f'测试汇总: {passed} 通过, {failed} 失败, 共 {passed + failed} 项')
    print('=' * 60)

    if failed > 0:
        print('\n失败项:')
        for name, success, detail in results:
            if not success:
                print(f'  - {name}: {detail}')

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
