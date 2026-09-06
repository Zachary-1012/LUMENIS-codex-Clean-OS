# -*- coding: utf-8 -*-
"""P1-D 报告 special 专报测试：类型校验 + 周期 + 生成冒烟（monkeypatch AI 不真实调用）。"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import report_engine  # noqa: E402


def test_special_in_report_types():
    assert "special" in report_engine.REPORT_TYPES


def test_special_period_defaults():
    now = datetime(2026, 9, 3)
    start, end = report_engine.period_for("special", now)
    assert end == "2026-09-03"
    assert start == (now - timedelta(days=30)).strftime("%Y-%m-%d")


def test_invalid_type_still_rejected():
    with pytest.raises(ValueError):
        report_engine.period_for("bad")


def test_generate_special_smoke(monkeypatch):
    captured = {}

    class FakeAnalyzer:
        def generate_period_report(self, notes, stats, rtype, start, end):
            captured.update(notes=notes, stats=stats, rtype=rtype, start=start, end=end)
            return {"ai_summary": "专报摘要"}

    class FakeDb:
        @staticmethod
        def get_notes_by_date_range(a, b):
            return []
        @staticmethod
        def get_stats_by_date_range(a, b):
            return {"total": 5, "positive": 2, "neutral": 2, "negative": 1,
                    "high_risk": 0, "medium_risk": 1, "low_risk": 4,
                    "total_likes": 100, "total_comments": 10, "total_engagements": 110}
        @staticmethod
        def save_daily_report(r):
            captured["saved"] = r
            return 1  # 模拟真实 save_daily_report 返回行 id

    monkeypatch.setattr(report_engine, "ai_analyzer", FakeAnalyzer())
    monkeypatch.setattr(report_engine, "db", FakeDb())
    monkeypatch.setattr(report_engine.ai_filter, "run_filter_batch", lambda limit=500: None)
    monkeypatch.setattr(report_engine.daily_report, "generate_daily_digest", lambda d: None)

    report, digest = report_engine.generate_report("special", "2026-08-01", "2026-08-31")
    assert captured["rtype"] == "special"
    assert report["report_type"] == "special"
    assert report["period_start"] == "2026-08-01"
    assert report["period_end"] == "2026-08-31"
    assert report["total_notes"] == 5  # 统计口径强制写回
