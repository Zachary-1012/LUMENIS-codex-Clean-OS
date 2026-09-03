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
import sqlite3
import tempfile
import base64

import pytest

TEST_USER = 'Zachary'
TEST_PASS = 'Zachary01'


@pytest.fixture(scope='module')
def client():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    os.environ['ZBC_DB_PATH'] = path
    os.environ['TAIKOO_AUTH_USER'] = TEST_USER
    os.environ['TAIKOO_AUTH_PASSWORD'] = TEST_PASS
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # 临时库补证据表（app.init_db 会建基础表）
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS app_evidence_records (id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT, product TEXT, feature_id TEXT, env TEXT, level TEXT, test_name TEXT, result TEXT, outputs TEXT, actual TEXT, created_at TEXT)")
        conn.commit()
    except Exception:
        pass
    conn.close()
    from app import app
    app.config['TESTING'] = True
    c = app.test_client()
    yield c
    try:
        os.unlink(path)
    except OSError:
        pass


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
        'cookies': [{'name': 'a1', 'value': 's', 'domain': '.xiaohongshu.com'},
                    {'name': 'web_session', 'value': 'x', 'domain': '.xiaohongshu.com'}]
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
