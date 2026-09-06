# -*- coding: utf-8 -*-
"""
时间口径分离测试（P0 红线：publish_datetime vs captured_at）
============================================================
验证：
1. normalize_relative_time 正确解析相对时间
2. 归一化失败返回 None，不猜测
3. publish_datetime 与 captured_at 严格分离
4. 相对时间不直接存入 publish_datetime

运行: .venv\\Scripts\\python.exe -m pytest tests/test_time_normalization.py -v
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from canonical_data import (
    CanonicalRecord, normalize_relative_time, verify_time_separation,
    note_to_canonical,
)


class TestNormalizeRelativeTime:
    """验证相对时间归一化。"""

    def test_just_now(self):
        result = normalize_relative_time("刚刚")
        assert result is not None
        # 应该是最近的时间
        parsed = datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
        assert abs((datetime.now() - parsed).total_seconds()) < 5

    def test_minutes_ago(self):
        result = normalize_relative_time("3分钟前")
        assert result is not None
        parsed = datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
        diff = (datetime.now() - parsed).total_seconds() / 60
        assert 2.5 <= diff <= 3.5

    def test_hours_ago(self):
        result = normalize_relative_time("2小时前")
        assert result is not None
        parsed = datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
        diff = (datetime.now() - parsed).total_seconds() / 3600
        assert 1.5 <= diff <= 2.5

    def test_yesterday(self):
        result = normalize_relative_time("昨天")
        assert result is not None
        parsed = datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
        assert parsed.date() == (datetime.now() - timedelta(days=1)).date()

    def test_yesterday_with_time(self):
        result = normalize_relative_time("昨天 14:30")
        assert result is not None
        parsed = datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
        assert parsed.hour == 14
        assert parsed.minute == 30

    def test_days_ago(self):
        result = normalize_relative_time("5天前")
        assert result is not None
        parsed = datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
        assert (datetime.now() - parsed).days == 5

    def test_weeks_ago(self):
        result = normalize_relative_time("2周前")
        assert result is not None
        parsed = datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
        assert 13 <= (datetime.now() - parsed).days <= 15

    def test_months_ago(self):
        result = normalize_relative_time("3个月前")
        assert result is not None
        parsed = datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
        # 近似每月30天
        assert 85 <= (datetime.now() - parsed).days <= 95

    def test_absolute_datetime(self):
        result = normalize_relative_time("2026-09-01 14:30:00")
        assert result == "2026-09-01 14:30:00"

    def test_absolute_date(self):
        result = normalize_relative_time("2026-09-01")
        assert result == "2026-09-01 00:00:00"

    def test_absolute_slash_format(self):
        result = normalize_relative_time("2026/09/01 14:30")
        assert result == "2026-09-01 14:30:00"

    def test_chinese_date_format(self):
        result = normalize_relative_time("2026年09月01日 14:30")
        assert result == "2026-09-01 14:30:00"

    def test_none_returns_none(self):
        assert normalize_relative_time(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_relative_time("") is None
        assert normalize_relative_time("   ") is None

    def test_missing_string_returns_none(self):
        assert normalize_relative_time("missing") is None

    def test_unparseable_returns_none(self):
        """无法解析的时间返回 None，不得猜测或用当前时间填充。"""
        result = normalize_relative_time("some random text")
        assert result is None

    def test_datetime_input(self):
        dt = datetime(2026, 9, 1, 14, 30, 0)
        result = normalize_relative_time(dt)
        assert result == "2026-09-01 14:30:00"

    def test_with_reference_time(self):
        ref = datetime(2026, 9, 6, 12, 0, 0)
        result = normalize_relative_time("3小时前", reference_time=ref)
        assert result == "2026-09-06 09:00:00"


class TestTimeSeparation:
    """验证 publish_datetime 与 captured_at 严格分离。"""

    def test_separate_values_valid(self):
        rec = CanonicalRecord(
            title="test",
            publish_datetime="2026-09-01 10:00:00",
            captured_at="2026-09-06 12:00:00",
        )
        result = verify_time_separation(rec)
        assert result['valid'] is True

    def test_same_values_invalid(self):
        rec = CanonicalRecord(
            title="test",
            publish_datetime="2026-09-06 12:00:00",
            captured_at="2026-09-06 12:00:00",
        )
        result = verify_time_separation(rec)
        assert result['valid'] is False
        assert '相同' in result['issue']

    def test_empty_publish_valid(self):
        rec = CanonicalRecord(title="test", captured_at="2026-09-06 12:00:00")
        rec.publish_datetime = ""
        result = verify_time_separation(rec)
        assert result['valid'] is True

    def test_note_to_canonical_separates_times(self):
        note = {
            "note_id": "time_test_001",
            "title": "test",
            "publish_datetime": "2026-09-01 10:00:00",
            "captured_at": "2026-09-06 12:00:00",
        }
        rec = note_to_canonical(note)
        assert rec.publish_datetime == "2026-09-01 10:00:00"
        assert rec.captured_at == "2026-09-06 12:00:00"
        assert rec.publish_datetime != rec.captured_at

    def test_note_to_canonical_publish_date_fallback(self):
        note = {
            "note_id": "time_test_002",
            "title": "test",
            "publish_date": "2026-09-01",
            "collected_at": "2026-09-06 12:00:00",
        }
        rec = note_to_canonical(note)
        assert rec.publish_datetime == "2026-09-01"
        assert rec.captured_at == "2026-09-06 12:00:00"
