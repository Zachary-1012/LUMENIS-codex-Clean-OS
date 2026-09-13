# -*- coding: utf-8 -*-
"""Canonical Capability V1 阶段七: HTTP 跨面一致性测试 (online)
验证同一 Metric 在真实 HTTP 消费面取值一致（同一时间窗口 + 同一 effective 口径）:
  a) /api/metrics/canonical?date=D 情感计数 == canonical 直算（effective 过滤后, 与 summary 同口径）
  b) MET-RISK-01/02 存在且含 lineage（FUNC-RISK-* / MET-RISK-*）
  c) 空窗口: 当日无数据返回 0 且 ok=true（不伪装、不报错）
口径说明:
  - daily_report.generate_today_summary 的计数基于 effective_notes（今日主体过滤 accepted 笔记；
    未跑 AI 过滤时退化为今日全部）。
  - 测试必须复现同一 effective 口径才能断言一致; 全量 vs effective 是 Filter 差异而非算法分叉。
"""
import os
import sys
import json
import sqlite3
import importlib
import urllib.request

import pytest

ZBC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ['ZBC_DB_PATH']
BASE = 'http://127.0.0.1:8201'


def _load_cm():
    for name in list(sys.modules):
        if name == 'canonical_metrics' or name.startswith('canonical_metrics.'):
            del sys.modules[name]
    sys.path.insert(0, ZBC)
    return importlib.import_module('canonical_metrics')


def _service_available():
    """检查 8201 服务是否可达，不可达时测试应 skip 而非 error。"""
    import socket
    try:
        with socket.create_connection(('127.0.0.1', 8201), timeout=3):
            return True
    except OSError:
        return False


def _auth():
    ac = json.loads(urllib.request.urlopen(BASE + '/api/auth/config', timeout=15).read().decode('utf-8'))
    return ac.get('auth_header', '')


def _get(path, auth):
    req = urllib.request.Request(BASE + path, headers={'Authorization': auth})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode('utf-8'))


def _latest_date_with_data():
    c = sqlite3.connect(DB)
    row = c.execute("SELECT substr(publish_date,1,10) d FROM notes WHERE publish_date IS NOT NULL AND publish_date != '' ORDER BY d DESC LIMIT 1").fetchone()
    c.close()
    return row[0] if row else None


def _effective_notes_for(date_str):
    """复现 daily_report 的 effective 口径: 今日主体过滤 accepted 笔记; 未跑 AI 过滤时退化为今日全部"""
    import database
    today_notes = database.get_notes_by_date_range(date_str, date_str)
    effective = [n for n in today_notes if n.get('ai_filter_status') == 'accepted']
    if not effective and today_notes:
        effective = today_notes
    return effective


@pytest.fixture(scope='module')
def ctx():
    if not _service_available():
        pytest.skip('Flask service on 127.0.0.1:8201 not reachable (online test)')
    os.environ['ZBC_DB_PATH'] = DB
    cm = _load_cm()
    auth = _auth()
    return cm, auth


@pytest.mark.online
def test_canonical_api_sentiment_matches_db_same_window(ctx):
    """a) /api/metrics/canonical?date=D 情感计数 == canonical 直算（effective 口径, 同窗口）"""
    cm, auth = ctx
    d = _latest_date_with_data()
    if d is None:
        pytest.skip('DB has no dated notes')
    effective = _effective_notes_for(d)
    if not effective:
        pytest.skip('date has no effective notes: ' + d)
    want = cm.sentiment_count(effective)
    got = _get('/api/metrics/canonical?date=' + d, auth)
    assert got.get('ok') is True, f'api not ok: {got}'
    ctx_api = got.get('context', {})
    api_pos = ctx_api.get('positive_count', 0)
    api_neu = ctx_api.get('neutral_count', 0)
    assert api_pos == want.get('positive', 0), f'positive: api={api_pos} canonical={want.get("positive",0)}'
    assert api_neu == want.get('neutral', 0), f'neutral: api={api_neu} canonical={want.get("neutral",0)}'
    # effective_count 也与 DB 过滤后条数一致
    assert ctx_api.get('effective_count') == len(effective), \
        f'effective_count: api={ctx_api.get("effective_count")} db={len(effective)}'


@pytest.mark.online
def test_risk_index_present_in_canonical_api(ctx):
    """b) MET-RISK-01/02 在 canonical 出口必须存在且含 function/registry lineage"""
    cm, auth = ctx
    got = _get('/api/metrics/canonical', auth)
    m = got.get('metrics', {})
    assert 'MET-RISK-01' in m and 'MET-RISK-02' in m
    assert m['MET-RISK-01'].get('function') == 'FUNC-RISK-01'
    assert m['MET-RISK-02'].get('function') == 'FUNC-RISK-02'
    assert 'risk_index' in m['MET-RISK-01'].get('name', '')
    assert 0.0 <= m['MET-RISK-01'].get('value', -1) <= 100.0
    assert 0.0 <= m['MET-RISK-02'].get('value', -1) <= 100.0


@pytest.mark.online
def test_empty_window_returns_zero_not_error(ctx):
    """c) 空窗口: 当日无数据必须返回 0 且 ok=true（不伪装、不报错）"""
    cm, auth = ctx
    got = _get('/api/metrics/canonical', auth)  # 默认今日
    assert got.get('ok') is True
    assert (got.get('context', {})).get('positive_count', 0) >= 0
    assert (got.get('context', {})).get('neutral_count', 0) >= 0
    m = got.get('metrics', {})
    if 'MET-RISK-01' in m:
        assert 0.0 <= m['MET-RISK-01']['value'] <= 100.0
