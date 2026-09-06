# -*- coding: utf-8 -*-
"""
评论/详情失败不静默丢弃测试（P0 红线）
========================================
验证：
1. CanonicalRecord 有 comments_status/detail_status 字段
2. 失败状态可记录（failed/partial/timeout）
3. 失败原因可记录
4. 评论/详情失败不丢弃主内容记录
5. 失败记录可查询

运行: .venv\\Scripts\\python.exe -m pytest tests/test_comment_detail_failure.py -v
"""
import os
import sys
import sqlite3
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from canonical_data import (
    CanonicalRecord, persist_canonical, ensure_canonical_table,
    get_canonical_by_id, CANONICAL_TABLE,
)


class TestStatusFieldsExist:
    """验证状态字段存在。"""

    def test_comments_status_field(self):
        rec = CanonicalRecord(title="test")
        assert hasattr(rec, 'comments_status')
        assert rec.comments_status == "pending"

    def test_detail_status_field(self):
        rec = CanonicalRecord(title="test")
        assert hasattr(rec, 'detail_status')
        assert rec.detail_status == "pending"

    def test_comments_error_field(self):
        rec = CanonicalRecord(title="test")
        assert hasattr(rec, 'comments_error')
        assert rec.comments_error == ""

    def test_detail_error_field(self):
        rec = CanonicalRecord(title="test")
        assert hasattr(rec, 'detail_error')
        assert rec.detail_error == ""


class TestFailureRecording:
    """验证失败状态记录。"""

    def test_comments_failed_status(self):
        rec = CanonicalRecord(title="test")
        rec.comments_status = "failed"
        rec.comments_error = "timeout after 30s"
        assert rec.comments_status == "failed"
        assert "timeout" in rec.comments_error

    def test_detail_partial_status(self):
        rec = CanonicalRecord(title="test")
        rec.detail_status = "partial"
        rec.detail_error = "部分字段缺失: author_avatar"
        assert rec.detail_status == "partial"

    def test_timeout_status(self):
        rec = CanonicalRecord(title="test")
        rec.comments_status = "timeout"
        rec.detail_status = "timeout"
        assert rec.comments_status == "timeout"
        assert rec.detail_status == "timeout"

    def test_success_status(self):
        rec = CanonicalRecord(title="test")
        rec.comments_status = "success"
        rec.detail_status = "success"
        assert rec.comments_status == "success"
        assert rec.detail_status == "success"


class TestFailureNotDroppingContent:
    """验证评论/详情失败不丢弃主内容记录。"""

    @pytest.fixture
    def tmp_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        ensure_canonical_table(path)
        yield path
        os.unlink(path)

    def test_failed_comments_keeps_main_record(self, tmp_db):
        rec = CanonicalRecord(
            canonical_id="fail_test_001",
            title="重要内容",
            content="这是一条重要的舆情内容",
            source_platform="xiaohongshu",
            url="http://example.com/1",
        )
        rec.comments_status = "failed"
        rec.comments_error = "ConnectionError: timeout"
        rec.detail_status = "success"
        rec.compute_hash()

        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        try:
            persist_canonical(con, rec)
            con.commit()
            # 主记录仍然存在
            stored = get_canonical_by_id(con, "fail_test_001")
            assert stored is not None
            assert stored["title"] == "重要内容"
            assert stored["comments_status"] == "failed"
            assert "timeout" in stored["comments_error"]
        finally:
            con.close()

    def test_failed_detail_keeps_main_record(self, tmp_db):
        rec = CanonicalRecord(
            canonical_id="fail_test_002",
            title="另一条内容",
            content="详情页抓取失败但主内容已保存",
            source_platform="weibo",
            url="http://example.com/2",
        )
        rec.detail_status = "failed"
        rec.detail_error = "404 Not Found"
        rec.comments_status = "success"
        rec.compute_hash()

        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        try:
            persist_canonical(con, rec)
            con.commit()
            stored = get_canonical_by_id(con, "fail_test_002")
            assert stored is not None
            assert stored["detail_status"] == "failed"
            assert stored["content"] == "详情页抓取失败但主内容已保存"
        finally:
            con.close()

    def test_both_failed_keeps_record(self, tmp_db):
        rec = CanonicalRecord(
            canonical_id="fail_test_003",
            title="双重失败",
            content="评论和详情都失败了",
            source_platform="douyin",
        )
        rec.comments_status = "timeout"
        rec.comments_error = "ReadTimeout"
        rec.detail_status = "failed"
        rec.detail_error = "LoginRequired"
        rec.compute_hash()

        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        try:
            persist_canonical(con, rec)
            con.commit()
            stored = get_canonical_by_id(con, "fail_test_003")
            assert stored is not None
            assert stored["comments_status"] == "timeout"
            assert stored["detail_status"] == "failed"
        finally:
            con.close()

    def test_failed_records_queryable(self, tmp_db):
        """失败记录可通过状态查询。"""
        for i in range(3):
            rec = CanonicalRecord(
                canonical_id=f"query_test_{i:03d}",
                title=f"内容{i}", content=f"测试内容{i}",
                source_platform="xhs",
            )
            if i == 0:
                rec.comments_status = "failed"
                rec.comments_error = "error1"
            elif i == 1:
                rec.detail_status = "timeout"
                rec.detail_error = "timeout1"
            rec.compute_hash()
            con = sqlite3.connect(tmp_db)
            persist_canonical(con, rec)
            con.commit()
            con.close()

        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        try:
            failed_comments = con.execute(
                f"SELECT COUNT(*) FROM {CANONICAL_TABLE} WHERE comments_status='failed'"
            ).fetchone()[0]
            timeout_detail = con.execute(
                f"SELECT COUNT(*) FROM {CANONICAL_TABLE} WHERE detail_status='timeout'"
            ).fetchone()[0]
            assert failed_comments >= 1
            assert timeout_detail >= 1
        finally:
            con.close()
