# -*- coding: utf-8 -*-
"""GAP-21 Cookie 导入 API 回归测试（隔离临时库 + Basic Auth，不接触生产库/真实凭证）

覆盖：
  - 无凭证访问 401
  - GET /api/cookies/import/status 200 + 平台结构
  - POST /api/cookies/import 200 + 三平台结果 + 无 Cookie 明文泄漏
  - 非法方法 405
"""
import os
import sys
import tempfile
import base64

import pytest

TEST_USER = 'Zachary'
TEST_PASS = os.environ.get('LUMENIS_TEST_AUTH_PASS', 'test-only-pass')


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    # 数据目录隔离：临时 data/ 避免 raw 导入测试污染生产 data/
    tmp_data = tempfile.mkdtemp(prefix='zbip_test_data_')
    # Keep the whole app request in an isolated, function-scoped environment.
    # A module-scoped fixture used to conflict with the suite's per-test
    # environment guard and leak temporary runtime paths into later tests.
    env_patch = pytest.MonkeyPatch()
    env_patch.setenv('ZBC_DATA_DIR', tmp_data)
    env_patch.setenv('ZBC_DB_PATH', path)
    env_patch.setenv('TAIKOO_AUTH_USER', TEST_USER)
    env_patch.setenv('TAIKOO_AUTH_PASSWORD', TEST_PASS)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app import app
    app.config['TESTING'] = True
    c = app.test_client()
    try:
        yield c
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
        try:
            import shutil
            shutil.rmtree(tmp_data, ignore_errors=True)
        except Exception:
            pass
        env_patch.undo()


def _headers():
    auth = base64.b64encode(f"{TEST_USER}:{TEST_PASS}".encode()).decode()
    return {'Authorization': f'Basic {auth}'}


def test_no_auth_401(client):
    assert client.get('/api/cookies/import/status').status_code == 401


def test_status_200_and_structure(client):
    r = client.get('/api/cookies/import/status', headers=_headers())
    assert r.status_code == 200
    d = r.get_json()
    assert d.get('ok') is True
    for k in ('weibo', 'bilibili', 'xhs', 'xhs_source_exists'):
        assert k in d.get('status', {})


def test_import_200_no_leak(client):
    r = client.post('/api/cookies/import', headers=_headers(), json={})
    assert r.status_code == 200
    d = r.get_json()
    assert d.get('ok') is True
    for k in ('weibo', 'bilibili', 'xhs'):
        assert k in d.get('results', {})
    raw = r.data.decode()
    assert 'web_session=' not in raw  # 不泄漏 Cookie 明文


def test_import_method_not_allowed(client):
    assert client.get('/api/cookies/import', headers=_headers()).status_code == 405

def test_raw_import_ok(client):
    r = client.post('/api/cookies/import/raw', headers=_headers(), json={
        'platform': 'xhs',
        'cookies': [{'name': 'a1', 'value': 'ab12cd34ef56', 'domain': '.xiaohongshu.com'},
                    {'name': 'web_session', 'value': 'sessionreal123456789', 'domain': '.xiaohongshu.com'}]
    })
    assert r.status_code == 200
    d = r.get_json()
    assert d.get('ok') is True
    assert d.get('cookie_count') == 2
    raw = r.data.decode()
    assert 'web_session' not in raw  # 不泄漏 Cookie 名值


def test_raw_import_no_auth_401(client):
    assert client.post('/api/cookies/import/raw', json={'platform': 'xhs', 'cookies': [{'name': 'a', 'value': 'b'}]}).status_code == 401


def test_raw_import_bad_platform_400(client):
    assert client.post('/api/cookies/import/raw', headers=_headers(), json={'platform': 'bad', 'cookies': [{'name': 'a', 'value': 'b'}]}).status_code == 400


def test_raw_import_empty_cookies_400(client):
    assert client.post('/api/cookies/import/raw', headers=_headers(), json={'platform': 'xhs', 'cookies': []}).status_code == 400

def test_raw_import_reject_fake_websession(client):
    # 测试占位 web_session 必须被拒绝，防止污染生产
    r = client.post('/api/cookies/import/raw', headers=_headers(), json={
        'platform': 'xhs',
        'cookies': [{'name': 'a1', 'value': 's', 'domain': '.xiaohongshu.com'},
                    {'name': 'web_session', 'value': 'x', 'domain': '.xiaohongshu.com'}]
    })
    assert r.status_code == 400
    assert '拒绝' in (r.get_json().get('error') or '')


def test_raw_import_missing_websession_400(client):
    r = client.post('/api/cookies/import/raw', headers=_headers(), json={
        'platform': 'xhs',
        'cookies': [{'name': 'a1', 'value': 'realvalue', 'domain': '.xiaohongshu.com'}]
    })
    assert r.status_code == 400


def test_raw_import_real_default_not_applied(client):
    # 真实 web_session + 默认 apply=false：写 source 但不覆盖生产 xhs_cookies.json
    r = client.post('/api/cookies/import/raw', headers=_headers(), json={
        'platform': 'xhs',
        'cookies': [{'name': 'web_session', 'value': 'abcdefg123456789', 'domain': '.xiaohongshu.com'}]
    })
    assert r.status_code == 200
    d = r.get_json()
    assert d.get('applied') is False


def test_raw_import_real_apply_true(client):
    r = client.post('/api/cookies/import/raw', headers=_headers(), json={
        'platform': 'xhs',
        'apply': True,
        'cookies': [{'name': 'web_session', 'value': 'abcdefg123456789', 'domain': '.xiaohongshu.com'}]
    })
    assert r.status_code == 200
    assert r.get_json().get('applied') is True
