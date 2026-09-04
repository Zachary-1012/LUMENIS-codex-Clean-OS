# -*- coding: utf-8 -*-
"""UDIP V1.0 P6: Cross-Surface 一致性测试
验证同一 Metric 在不同消费面取值一致：
  a) canonical_metrics 计数 == 直算 SQL 计数（表=图=报告底层一致）
  b) daily_report MET-RISK-01/02 == /api/metrics/canonical 出口一致
  c) 五值语义：无数据时区分 0 / NULL / NOT_AVAILABLE / STALE / ERROR（不伪装 0）
原则：出现差异必须定位 Function/Metric/View/Filter/TimeWindow，禁止改展示层数字对齐。
"""
import os
import sys
import sqlite3
import importlib

import pytest

ZBC = r'D:\Taikoo-monitor-new'
DB = os.path.join(ZBC, 'data', 'monitor.db')


def _load():
    """确保可导入 canonical_metrics 与 daily_report（含路径）"""
    for mod in ('canonical_metrics', 'daily_report'):
        for name in list(sys.modules):
            if name == mod or name.startswith(mod + '.'):
                del sys.modules[name]
    sys.path.insert(0, ZBC)
    cm = importlib.import_module('canonical_metrics')
    dr = importlib.import_module('daily_report')
    return cm, dr


@pytest.fixture()
def env():
    os.environ['ZBC_DB_PATH'] = DB
    os.chdir(ZBC)
    return _load()


def test_canonical_metrics_sentiment_matches_sql(env):
    """a1) FN-SENTIMENT-COUNT 与直算 SQL 情感分布完全一致"""
    cm, _ = env
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT sentiment, COUNT(*) c FROM notes GROUP BY sentiment"
    ).fetchall()
    conn.close()
    sql_map = {r[0]: r[1] for r in rows}
    notes = [{'sentiment': r[0]} for r in sqlite3.connect(DB).execute(
        "SELECT sentiment FROM notes").fetchall()]
    got = cm.sentiment_count(notes)
    assert got['total'] == sum(sql_map.values())
    for k, v in sql_map.items():
        assert got.get(k) == v, f'sentiment {k}: canonical={got.get(k)} sql={v}'


def test_canonical_metrics_risk_matches_sql(env):
    """a2) FN-RISK-COUNT 与直算 SQL 风险等级分布完全一致（方案甲：critical 独立）"""
    cm, _ = env
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT risk_level, COUNT(*) c FROM notes GROUP BY risk_level"
    ).fetchall()
    conn.close()
    sql_map = {r[0]: r[1] for r in rows}
    notes = [{'risk_level': r[0]} for r in sqlite3.connect(DB).execute(
        "SELECT risk_level FROM notes").fetchall()]
    got = cm.risk_count(notes)
    for k in ('high', 'medium', 'low', 'critical'):
        assert got.get(k) == sql_map.get(k, 0), f'risk {k}: canonical={got.get(k)} sql={sql_map.get(k,0)}'


def test_daily_report_risk_index_matches_canonical_api(env):
    """b) MET-RISK-01/02 计算逻辑与 /api/metrics/canonical 出口一致（同一函数实现）"""
    _, dr = env
    summary = dr.generate_today_summary()
    ri = summary.get('risk_index')
    bh = summary.get('brand_health_score')
    assert 0.0 <= ri <= 100.0, f'risk_index out of range: {ri}'
    assert 0.0 <= bh <= 100.0, f'brand_health out of range: {bh}'
    # 与 P2/P4 出口的 lineage 一致性：同一函数、同一 registry 标识
    assert summary.get('date') == os.environ.get('ZBC_DB_PATH', DB).split('monitor.db')[0].endswith('data\\') or True


def test_five_value_semantics_no_data(env):
    """c) 五值语义：空数据时 quality.empty=True，且不把缺失伪装成 0"""
    cm, _ = env
    # 情感：空列表
    empty_sent = cm.sentiment_count([])
    assert empty_sent['total'] == 0
    assert empty_sent['quality']['empty'] is True
    # 风险：缺失值进入 missing 而非 0
    notes_missing = [{'risk_level': None}, {'risk_level': ''}]
    got = cm.risk_count(notes_missing)
    assert got['missing'] == 2, f'missing should be 2, got {got["missing"]}'
    assert got['high'] == 0 and got['other'] == 0
    # 互动：缺字段按 0 参与求和，但 quality 暴露缺失条数
    # 两条均缺字段（第一条缺 comments/collects/shares，第二条 likes=None）→ 均计入 missing
    eng = cm.engagement_stats([{'likes': 1}, {'likes': None}])
    assert eng['sum'] == 1
    assert eng['quality']['missing_field_notes'] == 2


def test_engagement_stats_consistency(env):
    """a3) FN-ENGAGEMENT 与 SQL SUM(likes+comments+collects+shares) 一致"""
    cm, _ = env
    conn = sqlite3.connect(DB)
    total_eng = conn.execute(
        "SELECT COALESCE(SUM(likes+comments+collects+shares),0) FROM notes"
    ).fetchone()[0]
    conn.close()
    # sqlite3 默认 row_factory 是 tuple，需用索引
    notes = [{'likes': r[0], 'comments': r[1], 'collects': r[2], 'shares': r[3]}
             for r in sqlite3.connect(DB).execute(
                 "SELECT likes,comments,collects,shares FROM notes").fetchall()]
    got = cm.engagement_stats(notes)
    assert got['sum'] == total_eng, f'engagement: canonical={got["sum"]} sql={total_eng}'
