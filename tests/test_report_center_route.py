# -*- coding: utf-8 -*-
"""report_center 标准化报告只读旁路预览路由测试（GAP-10 边界：不抢既有报告 Owner）。"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_preview_returns_standard_sections(client, auth_headers):
    r = client.get('/api/v2/report-center/preview?period=daily&brand_mode=cth',
                   headers=auth_headers)
    assert r.status_code == 200
    j = r.get_json()
    assert j['ok'] is True and isinstance(j['report'], dict)
    # 标准化报告固定 18 节（空数据也产出框架，不抛异常）
    assert len(j['report']) == 18
    assert j['report']['period'] == 'daily'
    assert '不替代既有报告 Owner' in j['note']


def test_preview_zbmp_mode(client, auth_headers):
    r = client.get('/api/v2/report-center/preview?period=weekly&brand_mode=zbmp',
                   headers=auth_headers)
    assert r.status_code == 200
    rep = r.get_json()['report']
    assert rep['brand_mode'] == 'zbmp' and rep['period'] == 'weekly'


@pytest.mark.parametrize('qs', [
    'period=xxx',
    'brand_mode=xx',
    'start_date=2026-9-1',
    'end_date=bad',
])
def test_preview_rejects_invalid_params(client, auth_headers, qs):
    r = client.get('/api/v2/report-center/preview?' + qs, headers=auth_headers)
    assert r.status_code == 400 and r.get_json()['ok'] is False


def test_preview_requires_auth(client):
    r = client.get('/api/v2/report-center/preview?period=daily')
    assert r.status_code == 401
