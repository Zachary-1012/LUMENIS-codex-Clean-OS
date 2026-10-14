# -*- coding: utf-8 -*-
"""GAP-02b 日报/风险统计口径函数级黄金样例单测（不连库，直接断言生产统计口径）。

覆盖 Shared Reporting daily 中【生产统计口径】的纯计算函数——这些数字是报告/告警的事实来源，
AI 只允许增强（summarize/translate），绝不改写这些统计结果，因此必须用黄金样例锁死：

- calculate_risk_index：风险指数 0-100（负面占比/高风险/互动/事件时长/多来源加权）
- calculate_brand_health_score：品牌健康度 0-100（正面占比/风险反向/互动质量/官方声量）

每个用例只喂最小 dict，验证权重与边界：
- 空/未分类输入 → risk/health 为 None；完整测得的零值仍保留为 0.0
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
def test_risk_index_empty_or_unclassified_data_is_unknown():
    from lumenis.shared.reporting.daily import calculate_risk_index
    assert calculate_risk_index([], []) is None
    assert calculate_risk_index([], [{'status': 'active'}]) is None
    unknown = [_note('unknown', 'unknown')]
    assert calculate_risk_index(unknown, []) is None


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
def test_health_empty_or_unavailable_risk_is_unknown():
    from lumenis.shared.reporting.daily import calculate_brand_health_score
    assert calculate_brand_health_score([], 0) is None
    assert calculate_brand_health_score([_note('positive')], None) is None


def test_health_all_positive_high():
    from lumenis.shared.reporting.daily import calculate_brand_health_score
    notes = [_note('positive', 'low', likes=10, comments=1) for _ in range(10)]
    h = calculate_brand_health_score(notes, 0)
    assert h >= 70.0, f'全正面低风险应≥70，实际 {h}'


def test_health_all_negative_low():
    from lumenis.shared.reporting.daily import calculate_brand_health_score
    notes = [_note('negative', 'high', likes=1, comments=0) for _ in range(10)]
    h = calculate_brand_health_score(notes, 90)
    assert h < 40.0, f'全负面高风险应<40，实际 {h}'


def test_measured_zero_scores_remain_zero():
    from lumenis.shared.reporting.daily import calculate_risk_index, calculate_brand_health_score
    notes = [_note('positive', 'low', likes=0, comments=0)]
    risk = calculate_risk_index(notes, [])
    assert risk == 0.0
    assert calculate_brand_health_score(notes, risk) is None


def test_report_insights_and_actions_do_not_treat_missing_as_zero(monkeypatch):
    from lumenis.shared.reporting import daily

    monkeypatch.setattr(daily.db, 'get_hot_topics', lambda *_args: pytest.fail('unscoped reference topic query'))
    monkeypatch.setattr(daily.db, 'get_filter_stats', lambda: pytest.fail('unscoped reference status query'))
    notes = [_note('unknown', 'unknown', likes=None, comments=None)]
    summary = {
        'effective_count': 1,
        'positive_count': None,
        'negative_count': None,
        'risk_count': None,
        'sentiment_coverage': {'known': 0, 'total': 1, 'unknown': 1},
        'risk_coverage': {'known': 0, 'total': 1, 'missing': 1, 'other': 0},
    }

    insights = daily.generate_key_insights(notes, [], summary)
    actions = daily.generate_action_items(insights, [], summary)
    monkeypatch.setattr(daily, '_ai_allowed_for_report', lambda: False)
    executive = daily._ai_generate_executive_insight(summary, insights, [])

    assert any(item['type'] == 'data_gap' for item in insights)
    assert any(item['priority'] == '待核实' for item in actions)
    assert '整体平稳' not in ' '.join(item['action'] for item in actions)
    assert executive['priority'] == 'unknown'
    assert '—' in executive['executive_insight']
    assert '负面占比0%' not in executive['executive_insight']


def test_report_topics_and_pending_counts_come_only_from_scoped_rows(monkeypatch):
    from lumenis.shared.reporting import daily

    monkeypatch.setattr(daily.db, 'get_hot_topics', lambda *_args: pytest.fail('unscoped reference topic query'))
    monkeypatch.setattr(daily.db, 'get_filter_stats', lambda: pytest.fail('unscoped reference status query'))
    notes = [
        {'source_type': 'note', 'topics': '["topic-a", "topic-a"]',
         'sentiment': 'unknown', 'ai_filter_status': 'pending', 'likes': 0, 'comments': 0}
        for _ in range(101)
    ]
    notes.append({'source_type': 'note', 'topics': [], 'sentiment': 'unknown',
                  'ai_filter_status': None, 'likes': None, 'comments': None})
    summary = {'effective_count': 101, 'positive_count': None, 'negative_count': None,
               'risk_count': None,
               'sentiment_coverage': {'known': 0, 'total': 101, 'unknown': 101},
               'risk_coverage': {'known': 0, 'total': 101, 'missing': 101, 'other': 0}}

    insights = daily.generate_key_insights(notes, [], summary)
    actions = daily.generate_action_items(insights, [], summary, notes)

    assert any('topic-a' in item['insight'] and '101条' in item['insight'] for item in insights)
    assert any('101条记录待筛选复核' in item['insight'] for item in insights)
    assert any('101条待筛选记录' in item['action'] for item in actions)


def test_special_report_trigger_preserves_unknown_negative_count(monkeypatch):
    import risk_engine
    from lumenis.shared.reporting import daily

    scope = {'domain_id': 'cth', 'subject_id': None, 'brand_focus_id': None, 'global_scope': True}
    captured = []
    monkeypatch.setattr(daily, 'generate_today_summary', lambda *_args, **_kwargs: {})
    monkeypatch.setattr(daily.db, 'get_scoped_event_source_rows', lambda *_args, **_kwargs: {
        'sources': [], 'state': 'EMPTY', 'truncated': False, 'rejected_count': 0,
    })
    monkeypatch.setattr(risk_engine, 'check_special_report_trigger',
                        lambda event: (captured.append(event) or (False, [])))

    daily.format_daily_report_5sections(
        {'summary': {'effective_count': 0, 'negative_count': None, 'risk_count': 3},
         'top_events': [], 'action_items': []},
        date_str='2026-10-14', scope=scope,
    )

    assert captured and captured[0]['negative_count_24h'] is None
    assert captured[0]['sentiment'] is None


def test_report_insight_preserves_measured_zero():
    from lumenis.shared.reporting.daily import _measured_negative_percentage

    assert _measured_negative_percentage({
        'negative_count': 0,
        'sentiment_coverage': {'known': 3, 'total': 3, 'unknown': 0},
    }) == 0.0


def test_report_generator_propagation_keeps_invalid_engagement_unknown():
    from lumenis.shared.reporting.report_generator import ReportGenerator

    report = ReportGenerator()._generate_propagation_analysis(
        [{'likes': 'unavailable', 'comments': None}], []
    )
    assert report['engagement_level'] == 'unknown'
    assert report['total_engagement'] is None
    assert report['top_notes'][0]['engagement'] is None


@pytest.mark.parametrize(
    ("statuses", "expected_effective", "expected_known", "expected_unknown"),
    [
        (["relevant", "irrelevant", "rejected"], 1, 3, 0),
        (["relevant", None], None, 1, 1),
    ],
)
def test_daily_summary_uses_relevant_rows_only_and_keeps_incomplete_unknown(
        monkeypatch, statuses, expected_effective, expected_known, expected_unknown):
    from lumenis.shared.reporting import daily

    scope = {"domain_id": "cth", "product_id": "CTH", "subject_id": "SUBJECT-DAY",
             "brand_focus_id": None, "global_scope": False}
    notes = []
    for index, status in enumerate(statuses):
        notes.append({
            "source_type": "note", "source_id": f"note-{index}",
            "relevance_status": status,
            "sentiment": "positive" if index == 0 else "negative",
            "risk_level": "low" if index == 0 else "high",
            "likes": 0, "comments": 0,
        })
    monkeypatch.setattr(daily.db, "get_scoped_event_source_rows", lambda *args, **kwargs: {
        "sources": notes, "state": "AVAILABLE", "candidate_count": len(notes),
        "rejected_count": 0, "truncated": False,
    })
    monkeypatch.setattr(daily.db, "get_scoped_events", lambda *args, **kwargs: {
        "events": [], "candidate_count": 0, "rejected_count": 0, "truncated": False,
        "state": "EMPTY",
    })
    monkeypatch.setattr(daily, "_collection_health", lambda *_args: {"complete": None, "state": "NOT_RUN"})

    summary = daily.generate_today_summary("2026-10-14", scope=scope)

    assert summary["effective_count"] == expected_effective
    assert summary["relevance_coverage"] == {
        "known": expected_known, "total": len(notes), "unknown": expected_unknown, "observed": len(notes),
    }
    if expected_effective is None:
        assert summary["positive_count"] is None
        assert summary["negative_count"] is None
        assert summary["risk_count"] is None
        assert summary["risk_index"] is None
        assert summary["brand_health_score"] is None
        assert summary["sentiment_coverage"]["total"] is None
        assert summary["risk_coverage"]["total"] is None
    else:
        assert summary["positive_count"] == 1
        assert summary["negative_count"] == 0
        assert summary["risk_count"] == 0
        assert summary["risk_index"] == daily.calculate_risk_index([notes[0]], [])
        assert summary["sentiment_coverage"]["total"] == 1
        assert summary["risk_coverage"]["total"] == 1


def test_daily_digest_passes_only_effective_sources_to_analysis(monkeypatch):
    from lumenis.shared.reporting import daily

    scope = {"domain_id": "cth", "product_id": "CTH", "subject_id": "SUBJECT-DIGEST",
             "brand_focus_id": None, "global_scope": False}
    relevant = {"source_type": "note", "source_id": "effective-note", "relevance_status": "relevant",
                "sentiment": "positive", "risk_level": "low", "title": "Relevant"}
    irrelevant = {"source_type": "note", "source_id": "irrelevant-note", "relevance_status": "irrelevant",
                  "sentiment": "negative", "risk_level": "high", "title": "Irrelevant"}
    summary = {
        "total_found": 2, "effective_count": 1, "positive_count": 1, "neutral_count": 0,
        "negative_count": 0, "risk_count": 0, "risk_index": 0, "brand_health_score": 80,
        "relevance_coverage": {"known": 2, "total": 2, "unknown": 0, "observed": 2},
    }
    monkeypatch.setattr(daily, "generate_today_summary", lambda *_args, **_kwargs: summary)
    monkeypatch.setattr(daily.db, "get_scoped_event_source_rows", lambda *args, **kwargs: {
        "sources": [relevant, irrelevant], "candidate_count": 2, "rejected_count": 0,
        "truncated": False, "state": "AVAILABLE",
    })
    monkeypatch.setattr(daily.db, "get_scoped_events", lambda *args, **kwargs: {
        "events": [], "candidate_count": 0, "rejected_count": 0, "truncated": False,
        "state": "EMPTY",
    })
    analyzed = []
    monkeypatch.setattr(daily, "generate_key_insights",
                        lambda notes, *_args: (analyzed.extend(notes) or []))
    monkeypatch.setattr(daily, "generate_action_items", lambda *_args: [])
    monkeypatch.setattr(daily, "generate_executive_summary", lambda *_args: "measured summary")
    monkeypatch.setattr(daily, "_ai_allowed_for_report", lambda: False)
    monkeypatch.setattr(daily, "_ai_generate_executive_insight",
                        lambda *_args: {"executive_insight": "measured", "priority": "low"})
    monkeypatch.setattr(daily, "_generate_trend_alerts", lambda *_args: [])
    monkeypatch.setattr(daily, "_generate_risk_alerts", lambda *_args: [])

    digest = daily.generate_daily_digest("2026-10-14", scope=scope)

    assert digest["coverage"]["complete"] is True
    assert digest["effective_count"] == 1
    assert digest["relevance_coverage"] == summary["relevance_coverage"]
    assert analyzed == [relevant]


def test_daily_digest_hides_full_scope_analysis_when_relevance_is_unknown(monkeypatch):
    from lumenis.shared.reporting import daily

    scope = {"domain_id": "cth", "product_id": "CTH", "subject_id": "SUBJECT-DIGEST",
             "brand_focus_id": None, "global_scope": False}
    summary = {
        "total_found": 2, "effective_count": None, "positive_count": None, "neutral_count": None,
        "negative_count": None, "risk_count": None, "risk_index": None, "brand_health_score": None,
        "relevance_coverage": {"known": 1, "total": 2, "unknown": 1, "observed": 2},
    }
    monkeypatch.setattr(daily, "generate_today_summary", lambda *_args, **_kwargs: summary)
    monkeypatch.setattr(daily.db, "get_scoped_event_source_rows", lambda *args, **kwargs: {
        "sources": [
            {"source_type": "note", "source_id": "effective-note", "relevance_status": "relevant"},
            {"source_type": "note", "source_id": "unclassified-note", "relevance_status": None},
        ],
        "candidate_count": 2, "rejected_count": 0, "truncated": False, "state": "AVAILABLE",
    })
    monkeypatch.setattr(daily.db, "get_scoped_events", lambda *args, **kwargs: {
        "events": [], "candidate_count": 0, "rejected_count": 0, "truncated": False,
        "state": "EMPTY",
    })
    monkeypatch.setattr(daily, "generate_key_insights",
                        lambda *_args: pytest.fail("unknown relevance must suppress full-scope insights"))

    digest = daily.generate_daily_digest("2026-10-14", scope=scope)

    assert digest["coverage"]["complete"] is False
    assert digest["effective_count"] is None
    assert digest["relevance_coverage"]["unknown"] == 1
    assert "相关性" in digest["executive_summary"]


def test_health_risk_index_penalizes():
    from lumenis.shared.reporting.daily import calculate_brand_health_score
    notes = [_note('positive', 'low', likes=1, comments=0) for _ in range(10)]
    h_low_risk = calculate_brand_health_score(notes, 10)
    h_high_risk = calculate_brand_health_score(notes, 90)
    assert h_high_risk < h_low_risk, '高风险应拉低健康度'


def test_health_official_boost():
    from lumenis.shared.reporting.daily import calculate_brand_health_score
    notes = [_note('positive', 'low', likes=1, comments=0, is_official=1) for _ in range(5)]
    h_official = calculate_brand_health_score(notes, 0)
    notes2 = [_note('positive', 'low', likes=1, comments=0, is_official=0) for _ in range(5)]
    h_normal = calculate_brand_health_score(notes2, 0)
    assert h_official > h_normal, '官方声量应加分'


def test_health_bounds_0_100():
    from lumenis.shared.reporting.daily import calculate_brand_health_score
    notes = [_note('positive', 'low', likes=10, comments=1, is_official=1) for _ in range(20)]
    h = calculate_brand_health_score(notes, 0)
    assert 0.0 <= h <= 100.0
