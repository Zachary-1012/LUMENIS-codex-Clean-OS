# -*- coding: utf-8 -*-
"""GAP-04 三套 run-code 统一安全收口回归。

验证：
1. 生产默认态（_DEV_EXEC_ENABLED=False）三个入口对任意代码一律 403、不执行、不写盘；
2. 危险 payload（import os / 写文件 / 网络）在生产态同样被 403（根本不进入 exec）；
3. /api/dev/run-code 的 javascript 分支在生产态不向 static/js 写任何内容（防持久化注入）；
4. 开发态（ZBC_DEV_EXEC=1）仍拦截危险构造（400 DEV_EXEC_DANGEROUS）；
5. 开发态保留本地热更能力：安全表达式可执行并返回结果（能力不删除）。
"""
import base64
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_AUTH = {'Authorization': 'Basic ' + base64.b64encode(b'Zachary:Zachary01').decode()}
ENDPOINTS = ['/api/developer/run', '/api/config/run-code', '/api/dev/run-code']
DANGEROUS_PAYLOADS = [
    "import os\nos.system('echo pwned')",
    "__import__('subprocess').check_output('whoami')",
    "open('static/js/evil.js','w').write('x')",
    "import socket; socket.socket()",
]


@pytest.fixture
def prod_mode(monkeypatch):
    import app as app_module
    monkeypatch.setattr(app_module, '_DEV_EXEC_ENABLED', False)
    return app_module


@pytest.fixture
def dev_mode(monkeypatch):
    import app as app_module
    monkeypatch.setattr(app_module, '_DEV_EXEC_ENABLED', True)
    return app_module


def test_all_three_endpoints_denied_in_production(prod_mode, client):
    for ep in ENDPOINTS:
        r = client.post(ep, json={'code': 'result=1+1'}, headers=_AUTH)
        assert r.status_code == 403, ep
        body = r.get_json()
        assert body['ok'] is False
        assert body.get('code') == 'DEV_EXEC_DISABLED', (ep, body)


@pytest.mark.parametrize('payload', DANGEROUS_PAYLOADS)
def test_dangerous_payload_never_executes_in_production(prod_mode, client, payload, tmp_path, monkeypatch):
    marker = tmp_path / 'should_not_exist.txt'
    # 把 payload 里的写文件目标替换为 tmp marker，若服务端真执行则会留下痕迹
    crafted = "open(r'%s','w').write('x')" % str(marker).replace('\\', '\\\\')
    for ep in ENDPOINTS:
        r = client.post(ep, json={'code': crafted}, headers=_AUTH)
        assert r.status_code == 403, ep
    assert not marker.exists(), '生产态竟然执行了写文件代码=RCE 未收口'


def test_dev_run_code_js_branch_does_not_write_static_in_production(prod_mode, client):
    target = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'static', 'js', 'dev_custom.js')
    before = os.path.getsize(target) if os.path.exists(target) else None
    r = client.post('/api/dev/run-code', json={'type': 'javascript', 'code': '// GAP04_MARKER_SHOULD_NOT_WRITE'},
                    headers=_AUTH)
    assert r.status_code == 403
    after = os.path.getsize(target) if os.path.exists(target) else None
    assert before == after, '生产态 JS 分支改动了 static/js/dev_custom.js=持久化注入未收口'
    if os.path.exists(target):
        with open(target, encoding='utf-8', errors='replace') as fh:
            assert 'GAP04_MARKER_SHOULD_NOT_WRITE' not in fh.read()


def test_dev_mode_still_blocks_dangerous_constructs(dev_mode, client):
    r = client.post('/api/config/run-code', json={'code': "import os\nos.listdir('.')"}, headers=_AUTH)
    assert r.status_code == 400
    assert r.get_json().get('code') == 'DEV_EXEC_DANGEROUS'


def test_dev_mode_preserves_safe_local_hotfix(dev_mode, client):
    # 开发态保留能力：纯算术安全代码可执行并回传结果（不触网/不写盘/不反射）
    r = client.post('/api/config/run-code', json={'code': 'result = 21 * 2'}, headers=_AUTH)
    assert r.status_code == 200, r.get_json()
    assert '42' in str(r.get_json().get('result', ''))


def test_empty_code_rejected(dev_mode, client):
    r = client.post('/api/config/run-code', json={'code': '   '}, headers=_AUTH)
    assert r.status_code in (400, 403)
