# -*- coding: utf-8 -*-
"""GAP-02b 日报/风险统计口径函数级黄金样例单测（不连库，直接断言生产统计口径）。

覆盖 Shared Reporting daily 中【生产统计口径】的纯计算函数——这些数字是报告/告警的事实来源，
AI 只允许增强（summarize/translate），绝不改写这些统计结果，因此必须用黄金样例锁死：

- calculate_risk_index：风险指数 0-100（负面占比/高风险/互动/事件时长/多来源加权）
- calculate_brand_health_score：品牌健康度 0-100（正面占比/风险反向/互动质量/官方声量）

每个用例只喂最小 dict，验证权重与边界：
- 空输入（notes=[] → risk 0.0 / health 50.0 中性）
- 全负面 → 高风险指数
- 全正面 → 高健康度、低风险
- 高互动 → 传播规模加分
- 多来源/多事件 → 多来源加分
- 数值边界：0-100 收敛
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.redline


def _note(sentiment='neutral', risk_level='low', likes=0, comments=0, is_official=0):
    """构造最小笔记 dict。"""
    return {'sentiment': sentiment, 'risk_level': risk_level,
            'likes': likes, 'comments': comments, 'is_official': is_official}


# ---------- calculate_risk_index ----------
def test_risk_index_empty_notes_zero():
    from lumenis.shared.reporting.daily import calculate_risk_index
    assert calculate_risk_index([], []) == 0.0
    assert calculate_risk_index([], [{'status': 'active'}]) == 0.0


def test_risk_index_all_negative_high():
    from lumenis.shared.reporting.daily import calculate_risk_index
    # 全部负面 + 全部高风险 + 高互动 → 应显著偏高
    notes = [_note('negative', 'high', likes=200, comments=50) for _ in range(10)]
    idx = calculate_risk_index(notes, [])
    assert idx >= 50.0, f'全负面高风险应≥50，实际 {idx}'


def test_risk_index_all_positive_low():
    from lumenis.shared.reporting.daily import calculate_risk_index
    notes = [_note('positive', 'low', likes=1, comments=0) for _ in range(10)]
    idx = calculate_risk_index(notes, [])
    # 无负面、无高风险、低互动 → 基础得分应很低（事件/多来源也空）
    assert idx < 10.0, f'全正面低互动应<10，实际 {idx}'


def test_risk_index_negative_engagement_weight():
    from lumenis.shared.reporting.daily import calculate_risk_index
    # 负面互动规模（likes+comments*2）应推高传播得分
    low_eng = [_note('negative', 'low', likes=10, comments=1) for _ in range(5)]
    high_eng = [_note('negative', 'low', likes=5000, comments=200) for _ in range(5)]
    idx_low = calculate_risk_index(low_eng, [])
    idx_high = calculate_risk_index(high_eng, [])
    assert idx_high > idx_low, f'高互动应推高风险指数 {idx_high} vs {idx_low}'


def test_risk_index_bounds_0_100():
    from lumenis.shared.reporting.daily import calculate_risk_index
    # 极端高负面+高互动+多事件 → 上限 100
    notes = [_note('negative', 'high', likes=9999, comments=999) for _ in range(50)]
    events = [{'status': 'active', 'first_seen': '2026-09-01', 'last_seen': '2026-09-03',
               'source_count': 3} for _ in range(5)]
    idx = calculate_risk_index(notes, events)
    assert 0.0 <= idx <= 100.0


def test_risk_index_event_duration_and_source():
    from lumenis.shared.reporting.daily import calculate_risk_index
    notes = [_note('negative', 'medium', likes=10, comments=1) for _ in range(5)]
    # 带持续时长 + 多来源 → 应比无事件高
    base = calculate_risk_index(notes, [])
    events = [{'status': 'active', 'first_seen': '2026-09-01', 'last_seen': '2026-09-05',
               'source_count': 3}]
    with_ev = calculate_risk_index(notes, events)
    assert with_ev > base, f'事件时长/多来源应加分 {with_ev} vs {base}'


def test_risk_index_medium_risk_partial():
    from lumenis.shared.reporting.daily import calculate_risk_index
    # medium 风险贡献系数 1.5，低于 high 的 5
    notes = [_note('neutral', 'medium') for _ in range(4)]
    idx = calculate_risk_index(notes, [])
    # 4*1.5=6 → 高分区 6 分（+负面0+互动0）
    assert 5.0 <= idx <= 10.0, f'medium 4条风险分应在5-10，实际 {idx}'


# ---------- calculate_brand_health_score ----------
def test_health_empty_neutral_50():
    from lumenis.shared.reporting.daily import calculate_brand_health_score
    assert calculate_brand_health_score([], 0) == 50.0
    assert calculate_brand_health_score([], 100) == 50.0


def test_health_all_positive_high():
    from lumenis.shared.reporting.daily import calculate_brand_health_score
    notes = [_note('positive', 'low', likes=10, comments=1) for _ in range(10)]
    h = calculate_brand_health_score(notes, 0)
    assert h >= 70.0, f'全正面低风险应≥70，实际 {h}'


def test_health_all_negative_low():
    from lumenis.shared.reporting.daily import calculate_brand_health_score
    notes = [_note('negative', 'high', likes=0, comments=0) for _ in range(10)]
    h = calculate_brand_health_score(notes, 90)
    assert h < 40.0, f'全负面高风险应<40，实际 {h}'


def test_health_risk_index_penalizes():
    from lumenis.shared.reporting.daily import calculate_brand_health_score
    notes = [_note('positive', 'low', likes=1, comments=0) for _ in range(10)]
    h_low_risk = calculate_brand_health_score(notes, 10)
    h_high_risk = calculate_brand_health_score(notes, 90)
    assert h_high_risk < h_low_risk, '高风险应拉低健康度'


def test_health_official_boost():
    from lumenis.shared.reporting.daily import calculate_brand_health_score
    notes = [_note('positive', 'low', is_official=1) for _ in range(5)]
    h_official = calculate_brand_health_score(notes, 0)
    notes2 = [_note('positive', 'low', is_official=0) for _ in range(5)]
    h_normal = calculate_brand_health_score(notes2, 0)
    assert h_official > h_normal, '官方声量应加分'


def test_health_bounds_0_100():
    from lumenis.shared.reporting.daily import calculate_brand_health_score
    notes = [_note('positive', 'low', likes=10, comments=1, is_official=1) for _ in range(20)]
    h = calculate_brand_health_score(notes, 0)
    assert 0.0 <= h <= 100.0
