# -*- coding: utf-8 -*-
"""
缺失值显式标记测试（P0 红线：禁止 0/"未知" 静默填充）
========================================================
验证：
1. MISSING 常量和 is_missing() 辅助函数存在且正确
2. note_to_canonical 中缺失的 likes/comments 等为 None，不是 0
3. web_mention_to_canonical 中互动字段为 None（web_mentions 无互动数据）
4. collected_note_to_canonical 中缺失互动为 None
5. 真实 0 值与缺失值可区分
6. display_missing 前端展示正确
7. engagement_total 缺测为 None；部分实测合计附覆盖语义，真实 0 保留
8. persist_canonical 能正确存储 None（DB 中为 NULL）

运行: .venv\\Scripts\\python.exe -m pytest tests/test_missing_values.py -v
"""
import os
import sys
import json
import sqlite3
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from canonical_data import (
    CanonicalRecord, note_to_canonical, web_mention_to_canonical,
    collected_note_to_canonical, persist_canonical, ensure_canonical_table,
    MISSING, is_missing, display_missing, _safe_int_or_none, _safe_float_or_none,
    CANONICAL_TABLE,
)


class TestMissingConstants:
    """验证 MISSING 常量和辅助函数。"""

    def test_missing_is_none(self):
        assert MISSING is None

    def test_is_missing_none(self):
        assert is_missing(None) is True

    def test_is_missing_empty_string(self):
        assert is_missing("") is True
        assert is_missing("   ") is True

    def test_is_missing_missing_string(self):
        assert is_missing("missing") is True
        assert is_missing("null") is True
        assert is_missing("None") is True

    def test_is_missing_real_zero(self):
        """真实 0 不是缺失值。"""
        assert is_missing(0) is False
        assert is_missing(0.0) is False

    def test_is_missing_real_value(self):
        assert is_missing(42) is False
        assert is_missing("hello") is False
        assert is_missing(False) is False  # False is not missing

    def test_display_missing_none(self):
        assert display_missing(None) == "--"

    def test_display_missing_real_zero(self):
        """真实 0 显示为 0，不是占位符。"""
        assert display_missing(0) == 0

    def test_display_missing_custom_placeholder(self):
        assert display_missing(None, placeholder="数据缺失") == "数据缺失"

    def test_display_missing_real_value(self):
        assert display_missing(100) == 100
        assert display_missing("hello") == "hello"


class TestSafeIntOrNone:
    """验证 _safe_int_or_none 保留缺失值。"""

    def test_none_returns_none(self):
        assert _safe_int_or_none(None) is None

    def test_empty_string_returns_none(self):
        assert _safe_int_or_none("") is None
        assert _safe_int_or_none("  ") is None

    def test_missing_string_returns_none(self):
        assert _safe_int_or_none("missing") is None

    def test_real_zero_returns_zero(self):
        assert _safe_int_or_none(0) == 0

    def test_valid_int(self):
        assert _safe_int_or_none(42) == 42
        assert _safe_int_or_none("42") == 42
        assert _safe_int_or_none("3.7") == 3

    def test_invalid_returns_none(self):
        assert _safe_int_or_none("abc") is None

    def test_safe_float_or_none(self):
        assert _safe_float_or_none(None) is None
        assert _safe_float_or_none("") is None
        assert _safe_float_or_none(0) == 0.0
        assert _safe_float_or_none("3.14") == 3.14
        assert _safe_float_or_none("abc") is None


class TestNoteToCanonicalMissing:
    """验证 note_to_canonical 中缺失互动值为 None。"""

    def test_missing_likes_is_none(self):
        note = {"note_id": "test1", "title": "test", "likes": None}
        rec = note_to_canonical(note)
        assert rec.engagement_likes is None, "缺失的 likes 应为 None，不是 0"

    def test_missing_all_engagement_is_none(self):
        note = {"note_id": "test2", "title": "test"}
        rec = note_to_canonical(note)
        assert rec.engagement_likes is None
        assert rec.engagement_comments is None
        assert rec.engagement_collects is None
        assert rec.engagement_shares is None

    def test_real_zero_preserved(self):
        """真实采集到的 0 赞应保留为 0，不是 None。"""
        note = {"note_id": "test3", "title": "test",
                "likes": 0, "comments": 0, "collects": 0, "shares": 0}
        rec = note_to_canonical(note)
        assert rec.engagement_likes == 0
        assert rec.engagement_comments == 0
        assert is_missing(rec.engagement_likes) is False

    def test_mixed_values(self):
        note = {"note_id": "test4", "title": "test",
                "likes": 100, "comments": None, "collects": 50, "shares": ""}
        rec = note_to_canonical(note)
        assert rec.engagement_likes == 100
        assert rec.engagement_comments is None
        assert rec.engagement_collects == 50
        assert rec.engagement_shares is None  # empty string -> None


class TestWebMentionToCanonicalMissing:
    """验证 web_mention_to_canonical 互动字段为 None（无互动数据）。"""

    def test_web_mention_engagement_is_none(self):
        web = {"source_id": "web1", "title": "news", "url": "http://example.com"}
        rec = web_mention_to_canonical(web)
        assert rec.engagement_likes is None
        assert rec.engagement_comments is None
        assert rec.engagement_collects is None
        assert rec.engagement_shares is None


class TestCollectedNoteToCanonicalMissing:
    """验证 collected_note_to_canonical 缺失互动为 None。"""

    def test_missing_engagement(self):
        from dataclasses import dataclass

        @dataclass
        class FakeCollected:
            title: str = "test"
            content: str = ""
            url: str = ""
            author: str = ""
            author_id: str = ""
            publish_date: str = ""
            likes: int = None
            comments: int = None
            collects: int = None
            shares: int = None
            cover: str = ""
            source_platform: str = "xiaohongshu"
            raw_data: dict = None

        note = FakeCollected(title="test", raw_data={})
        rec = collected_note_to_canonical(note, source_platform="xiaohongshu")
        assert rec.engagement_likes is None
        assert rec.engagement_comments is None
        assert rec.engagement_collects is None
        assert rec.engagement_shares is None

    def test_real_zero_collected(self):
        from dataclasses import dataclass

        @dataclass
        class FakeCollected:
            title: str = "test"
            content: str = ""
            url: str = ""
            author: str = ""
            author_id: str = ""
            publish_date: str = ""
            likes: int = 0
            comments: int = 0
            collects: int = 0
            shares: int = 0
            cover: str = ""
            source_platform: str = "xiaohongshu"
            raw_data: dict = None

        note = FakeCollected(title="test", raw_data={})
        rec = collected_note_to_canonical(note, source_platform="xiaohongshu")
        assert rec.engagement_likes == 0
        assert is_missing(rec.engagement_likes) is False


class TestEngagementTotalWithNone:
    """验证 engagement_total 正确处理 None。"""

    def test_all_none_returns_unknown(self):
        rec = CanonicalRecord(title="test")
        rec.engagement_likes = None
        rec.engagement_comments = None
        rec.engagement_collects = None
        rec.engagement_shares = None
        assert rec.engagement_total() is None
        observation = rec.engagement_observation()
        assert observation["observed_sum"] is None
        assert observation["quality"]["state"] == "UNKNOWN"
        assert observation["quality"]["known_field_count"] == 0

    def test_mixed_none_and_values(self):
        rec = CanonicalRecord(title="test")
        rec.engagement_likes = 100
        rec.engagement_comments = None
        rec.engagement_collects = 50
        rec.engagement_shares = None
        assert rec.engagement_total() is None
        observation = rec.engagement_observation()
        assert observation["observed_sum"] == 150
        assert observation["quality"]["state"] == "PARTIAL"
        assert observation["quality"]["known_field_count"] == 2
        assert observation["quality"]["expected_field_count"] == 4

    def test_all_real_values(self):
        rec = CanonicalRecord(title="test")
        rec.engagement_likes = 10
        rec.engagement_comments = 5
        rec.engagement_collects = 3
        rec.engagement_shares = 2
        assert rec.engagement_total() == 20


class TestPersistNoneToDb:
    """验证 persist_canonical 能正确存储 None（DB 中为 NULL）。"""

    @pytest.fixture
    def tmp_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        ensure_canonical_table(path)
        yield path
        os.unlink(path)

    def test_none_stored_as_null(self, tmp_db):
        rec = CanonicalRecord(
            canonical_id="test_null_001",
            title="test missing values",
            source_platform="xiaohongshu",
        )
        rec.engagement_likes = None
        rec.engagement_comments = None
        rec.engagement_collects = None
        rec.engagement_shares = None
        rec.compute_hash()

        con = sqlite3.connect(tmp_db)
        try:
            persist_canonical(con, rec)
            con.commit()
            row = con.execute(
                f"SELECT engagement_likes, engagement_comments, engagement_collects, engagement_shares "
                f"FROM {CANONICAL_TABLE} WHERE canonical_id=?",
                ("test_null_001",)
            ).fetchone()
            assert row[0] is None, "DB 中 likes 应为 NULL"
            assert row[1] is None, "DB 中 comments 应为 NULL"
            assert row[2] is None, "DB 中 collects 应为 NULL"
            assert row[3] is None, "DB 中 shares 应为 NULL"
        finally:
            con.close()

    def test_real_zero_stored_as_zero(self, tmp_db):
        rec = CanonicalRecord(
            canonical_id="test_zero_001",
            title="test real zero",
            source_platform="xiaohongshu",
        )
        rec.engagement_likes = 0
        rec.engagement_comments = 0
        rec.engagement_collects = 0
        rec.engagement_shares = 0
        rec.compute_hash()

        con = sqlite3.connect(tmp_db)
        try:
            persist_canonical(con, rec)
            con.commit()
            row = con.execute(
                f"SELECT engagement_likes FROM {CANONICAL_TABLE} WHERE canonical_id=?",
                ("test_zero_001",)
            ).fetchone()
            assert row[0] == 0, "真实 0 应存储为 0，不是 NULL"
        finally:
            con.close()

    def test_null_vs_zero_distinguishable_in_db(self, tmp_db):
        """DB 中 NULL 和 0 可区分查询。"""
        # Insert one with None and one with 0
        rec1 = CanonicalRecord(canonical_id="null_rec", title="null", source_platform="xhs")
        rec1.engagement_likes = None
        rec1.compute_hash()
        rec2 = CanonicalRecord(canonical_id="zero_rec", title="zero", source_platform="xhs")
        rec2.engagement_likes = 0
        rec2.compute_hash()

        con = sqlite3.connect(tmp_db)
        try:
            persist_canonical(con, rec1)
            persist_canonical(con, rec2)
            con.commit()
            # Count NULL
            null_count = con.execute(
                f"SELECT COUNT(*) FROM {CANONICAL_TABLE} WHERE engagement_likes IS NULL"
            ).fetchone()[0]
            # Count zero
            zero_count = con.execute(
                f"SELECT COUNT(*) FROM {CANONICAL_TABLE} WHERE engagement_likes = 0"
            ).fetchone()[0]
            assert null_count >= 1, "应有 NULL 记录"
            assert zero_count >= 1, "应有 0 记录"
            assert null_count != zero_count or null_count >= 1, "NULL 和 0 应可区分"
        finally:
            con.close()
