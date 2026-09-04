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

ZBC = r'D:\Taikoo-monitor-new'
DB = os.path.join(ZBC, 'data', 'monitor.db')
BASE = 'http://127.0.0.1:8201'


def _canonical_brand_counts():
    """用 canonical 口径计算 brand_industry_monitor 的 negative/positive 品牌数（实体 id 计数）"""
    conn = sqlite3.connect(DB)
    neg = conn.execute("SELECT COUNT(*) FROM brand_industry_monitor WHERE negative_count > 0").fetchone()[0]
    pos = conn.execute("SELECT COUNT(*) FROM brand_industry_monitor WHERE positive_count > 0").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM brand_industry_monitor").fetchone()[0]
    conn.close()
    return {'total': total, 'negative': neg, 'positive': pos}


def _http_get(path, auth_header):
    req = urllib.request.Request(BASE + path, headers={'Authorization': auth_header})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


@pytest.mark.online
def test_brand_industry_stats_matches_canonical():
    """HTTP /api/brand-industry/stats == canonical 实体口径"""
    auth = _http_get('/api/auth/config', '')['auth_header']
    bi = _http_get('/api/brand-industry/stats', auth)
    canon = _canonical_brand_counts()
    assert bi['total'] == canon['total'], f"total: api={bi['total']} canon={canon['total']}"
    assert bi['negative_brands'] == canon['negative'], \
        f"negative_brands: api={bi['negative_brands']} canon={canon['negative']}"
    assert bi['positive_brands'] == canon['positive'], \
        f"positive_brands: api={bi['positive_brands']} canon={canon['positive']}"


@pytest.mark.online
def test_brand_industry_stats_consistent_across_views():
    """/api/brand-industry/stats 内一致：total==total_brands、categories==industry 数"""
    auth = _http_get('/api/auth/config', '')['auth_header']
    bi = _http_get('/api/brand-industry/stats', auth)
    assert bi['total'] == bi['total_brands']
    assert bi['negative'] == bi['negative_brands']
    assert bi['positive'] == bi['positive_brands']
    assert len(bi['industries']) == bi['categories']
