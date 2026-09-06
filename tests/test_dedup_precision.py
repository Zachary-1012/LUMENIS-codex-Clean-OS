# -*- coding: utf-8 -*-
"""
去重精准测试（P0 红线：content_hash + platform_id 组合键）
============================================================
验证：
1. dedup_key 生成 content_hash + platform_id 组合
2. 同平台同内容判定重复
3. 不同平台同内容不判定重复
4. 相似标题不同内容不判定重复
5. 去重决策可追溯

运行: .venv\\Scripts\\python.exe -m pytest tests/test_dedup_precision.py -v
"""
import os
import sys
import sqlite3
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from canonical_data import (
    CanonicalRecord, dedup_key, find_duplicates, is_duplicate,
    persist_canonical, ensure_canonical_table, CANONICAL_TABLE,
)


class TestDedupKey:
    """验证去重键生成。"""

    def test_dedup_key_format(self):
        key = dedup_key("abc123", "xiaohongshu")
        assert key == "xiaohongshu:abc123"

    def test_dedup_key_none_hash(self):
        assert dedup_key(None, "xiaohongshu") is None

    def test_dedup_key_none_platform(self):
        assert dedup_key("abc123", None) is None

    def test_dedup_key_empty(self):
        assert dedup_key("", "xhs") is None
        assert dedup_key("abc", "") is None


class TestDedupPrecision:
    """验证去重精准性。"""

    @pytest.fixture
    def tmp_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        ensure_canonical_table(path)
        yield path
        os.unlink(path)

    def _insert_record(self, con, canonical_id, title, content, url, platform):
        rec = CanonicalRecord(
            canonical_id=canonical_id,
            title=title, content=content, url=url,
            source_platform=platform,
        )
        rec.compute_hash()
        persist_canonical(con, rec)
        con.commit()
        return rec.content_hash

    def test_same_platform_same_content_is_duplicate(self, tmp_db):
        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        try:
            h = self._insert_record(con, "dup1", "标题A", "内容A", "http://a.com", "xiaohongshu")
            assert is_duplicate(con, h, "xiaohongshu", canonical_id="dup2") is True
        finally:
            con.close()

    def test_different_platform_same_content_not_duplicate(self, tmp_db):
        """不同平台相同内容不视为重复（跨平台转载是正常现象）。"""
        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        try:
            h = self._insert_record(con, "dup1", "标题A", "内容A", "http://a.com", "xiaohongshu")
            # 同内容但不同平台
            assert is_duplicate(con, h, "weibo", canonical_id="dup2") is False
        finally:
            con.close()

    def test_same_platform_different_content_not_duplicate(self, tmp_db):
        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        try:
            self._insert_record(con, "dup1", "标题A", "内容A", "http://a.com", "xiaohongshu")
            rec2 = CanonicalRecord(
                canonical_id="dup2", title="标题B", content="内容B",
                url="http://b.com", source_platform="xiaohongshu",
            )
            rec2.compute_hash()
            assert is_duplicate(con, rec2.content_hash, "xiaohongshu") is False
        finally:
            con.close()

    def test_similar_title_different_content_not_duplicate(self, tmp_db):
        """标题相似但内容不同不应误删。"""
        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        try:
            self._insert_record(con, "dup1", "太古汇探店", "今天去了太古汇，感觉很好", "http://a.com", "xhs")
            rec2 = CanonicalRecord(
                canonical_id="dup2", title="太古汇探店", content="太古汇探店体验分享，完全不同的内容",
                url="http://b.com", source_platform="xhs",
            )
            rec2.compute_hash()
            assert is_duplicate(con, rec2.content_hash, "xhs") is False
        finally:
            con.close()

    def test_find_duplicates_returns_ids(self, tmp_db):
        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        try:
            h = self._insert_record(con, "dup1", "标题A", "内容A", "http://a.com", "xhs")
            dups = find_duplicates(con, h, "xhs")
            assert "dup1" in dups
        finally:
            con.close()

    def test_find_duplicates_excludes_self(self, tmp_db):
        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        try:
            h = self._insert_record(con, "dup1", "标题A", "内容A", "http://a.com", "xhs")
            dups = find_duplicates(con, h, "xhs", canonical_id="dup1")
            assert "dup1" not in dups
            assert len(dups) == 0
        finally:
            con.close()

    def test_content_hash_based_not_title_based(self, tmp_db):
        """验证去重基于 content_hash 而非 title。"""
        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        try:
            # 同标题不同内容
            self._insert_record(con, "dup1", "相同标题", "内容版本一", "http://a.com", "xhs")
            rec2 = CanonicalRecord(
                canonical_id="dup2", title="相同标题", content="内容版本二完全不同",
                url="http://b.com", source_platform="xhs",
            )
            rec2.compute_hash()
            # content_hash 不同，不应判定重复
            assert is_duplicate(con, rec2.content_hash, "xhs") is False
        finally:
            con.close()
