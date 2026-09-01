# -*- coding: utf-8 -*-
"""阶段4c：Global BIL research-stage 只读加载器与路由测试（不建表/不写库/不联网）。"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_loader_overview_lists_real_seeds():
    from v4_upgrade.global_bil import overview, load_resource, _FILES
    ov = overview()
    assert set(ov) == set(_FILES)
    for name, info in ov.items():
        assert info['available'] is True and info['count'] and info['count'] > 0
    d = load_resource('benchmarks')
    assert isinstance(d, dict) and isinstance(d.get('benchmarks'), list)


def test_loader_rejects_unknown_resource():
    from v4_upgrade.global_bil import load_resource
    with pytest.raises(KeyError):
        load_resource('secret_etc')


def test_route_overview_and_resource(client, auth_headers):
    r = client.get('/api/v2/global-bil/overview', headers=auth_headers)
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] and j['stage'] == 'research'
    assert j['overview']['cases']['available'] is True

    r2 = client.get('/api/v2/global-bil/cases', headers=auth_headers)
    assert r2.status_code == 200 and r2.get_json()['data'].get('cases')


def test_route_rejects_unknown_and_requires_auth(client, auth_headers):
    r = client.get('/api/v2/global-bil/nope', headers=auth_headers)
    assert r.status_code == 400
    assert client.get('/api/v2/global-bil/overview').status_code == 401
