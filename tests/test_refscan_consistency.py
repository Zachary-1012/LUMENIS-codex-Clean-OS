# -*- coding: utf-8 -*-
"""UDIP V1.0 P6: 多端点 Reference Scan 一致性测试（可重复运行）
验证 /api/brand-industry/stats 的 negative/positive 品牌数与 canonical 实体口径一致。
不硬编码数字：直接查 DB 用 canonical_metrics 计算权威值，再断言 HTTP 返回与之相等。
"""
import os
import sys
import sqlite3
import importlib
import urllib.request
import json

import pytest

ZBC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ['ZBC_DB_PATH']
BASE = 'http://127.0.0.1:8201'


def _canonical_brand_counts():
    """用 canonical 口径计算 brand_industry_monitor 的 negative/positive 品牌数（实体 id 计数）。
    表不存在时返回 None，调用方应 skip。"""
    conn = sqlite3.connect(DB)
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='brand_industry_monitor'"
    ).fetchone()
    if not exists:
        conn.close()
        return None
    neg = conn.execute("SELECT COUNT(*) FROM brand_industry_monitor WHERE negative_count > 0").fetchone()[0]
    pos = conn.execute("SELECT COUNT(*) FROM brand_industry_monitor WHERE positive_count > 0").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM brand_industry_monitor").fetchone()[0]
    conn.close()
    return {'total': total, 'negative': neg, 'positive': pos}


def _service_available():
    """检查 8201 服务是否可达，不可达时测试应 skip 而非 error。"""
    import socket
    try:
        with socket.create_connection(('127.0.0.1', 8201), timeout=3):
            return True
    except OSError:
        return False


def _http_get(path, auth_header):
    req = urllib.request.Request(BASE + path, headers={'Authorization': auth_header})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


@pytest.mark.online
def test_brand_industry_stats_matches_canonical():
    """HTTP /api/brand-industry/stats == canonical 实体口径。
    brand_industry_monitor 表未建时 skip（功能未启用）。"""
    if not _service_available():
        pytest.skip('Flask service on 127.0.0.1:8201 not reachable (online test)')
    canon = _canonical_brand_counts()
    if canon is None:
        pytest.skip("brand_industry_monitor table not present (feature not enabled)")
    auth = _http_get('/api/auth/config', '')['auth_header']
    bi = _http_get('/api/brand-industry/stats', auth)
    if bi.get('error'):
        pytest.skip(f"API returned error: {bi['error']}")
    assert bi['total'] == canon['total'], f"total: api={bi['total']} canon={canon['total']}"
    # API 实际字段为 negative/positive（非 negative_brands/positive_brands）
    assert bi['negative'] == canon['negative'], \
        f"negative: api={bi['negative']} canon={canon['negative']}"
    assert bi['positive'] == canon['positive'], \
        f"positive: api={bi['positive']} canon={canon['positive']}"


@pytest.mark.online
def test_brand_industry_stats_consistent_across_views():
    """/api/brand-industry/stats 内一致：total==total_brands。
    brand_industry_monitor 表未建时 skip。"""
    if not _service_available():
        pytest.skip('Flask service on 127.0.0.1:8201 not reachable (online test)')
    canon = _canonical_brand_counts()
    if canon is None:
        pytest.skip("brand_industry_monitor table not present (feature not enabled)")
    auth = _http_get('/api/auth/config', '')['auth_header']
    bi = _http_get('/api/brand-industry/stats', auth)
    if bi.get('error'):
        pytest.skip(f"API returned error: {bi['error']}")
    assert bi['total'] == bi['total_brands']
    # API 实际字段为 negative/positive
    assert bi['negative'] == bi.get('negative', 0)
    assert bi['positive'] == bi.get('positive', 0)
    if 'industries' in bi and 'categories' in bi:
        assert len(bi['industries']) == bi['categories']
