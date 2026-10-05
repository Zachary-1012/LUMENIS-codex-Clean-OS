# -*- coding: utf-8 -*-
"""
T4 Canonical Data Layer 测试
==============================
验证 Raw→Canonical 断点修复、时间口径分离、幂等写入、schema_version 接入。

运行: D:\Taikoo-monitor-new\.venv\Scripts\python.exe -m pytest tests/test_canonical_data_t4.py -v
"""
import os
import sys
import json
import sqlite3
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from canonical_data import (
    CanonicalRecord, note_to_canonical, web_mention_to_canonical,
    collected_note_to_canonical, persist_canonical, sync_all_to_canonical,
    ensure_canonical_table, ensure_schema_version_table, register_schema_version,
    get_schema_versions, self_check, count_canonical, get_canonical_by_id,
    list_canonical, CANONICAL_TABLE, SCHEMA_VERSION, SENTIMENT_POSITIVE,
    SENTIMENT_UNKNOWN, RISK_HIGH, RISK_UNKNOWN, SOURCE_TYPE_NOTE,
    SOURCE_TYPE_WEB_MENTION, PRODUCT_CTH,
)


@pytest.fixture
def tmp_db():
    """创建临时数据库，避免污染生产库。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    ensure_canonical_table(path)
    ensure_schema_version_table(path)
    # 创建 notes 和 web_mentions 表用于同步测试
    con = sqlite3.connect(path)
    con.execute("""
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id TEXT, title TEXT, content TEXT, url TEXT,
            author_id TEXT, author_nickname TEXT,
            likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0,
            collects INTEGER DEFAULT 0, shares INTEGER DEFAULT 0,
            publish_date TEXT, publish_datetime TEXT,
            collected_at TEXT, captured_at TEXT,
            sentiment TEXT DEFAULT 'neutral', sentiment_score REAL DEFAULT 0,
            risk_level TEXT DEFAULT 'low', risk_score INTEGER DEFAULT 0,
            source_platform TEXT DEFAULT 'xhs', source_keyword TEXT DEFAULT '',
            subject_type TEXT DEFAULT '', content_type TEXT DEFAULT '',
            data_quality_status TEXT DEFAULT 'unknown', data_quality_score REAL DEFAULT 0,
            verification_confidence REAL DEFAULT 0,
            relevance_status TEXT DEFAULT 'relevant', verification_status TEXT DEFAULT 'review',
            ai_provider TEXT DEFAULT 'rule', ai_model TEXT DEFAULT '',
            topics TEXT DEFAULT '[]', event_hint TEXT DEFAULT '', body TEXT DEFAULT ''
        )
    """)
    con.execute("""
        CREATE TABLE web_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT, source_platform TEXT, source_type TEXT,
            title TEXT, content TEXT, url TEXT, domain TEXT,
            published_at TEXT, fetched_at TEXT, source_adapter TEXT,
            query TEXT, canonical_url TEXT,
            relevance TEXT DEFAULT 'pending', verification TEXT DEFAULT 'review',
            ai_provider TEXT DEFAULT 'rule'
        )
    """)
    con.commit()
    con.close()
    yield path
    os.unlink(path)


class TestCanonicalRecord:
    """CanonicalRecord 数据模型测试。"""

    def test_default_values(self):
        rec = CanonicalRecord()
        assert rec.canonical_id.startswith("can_")
        assert rec.product_id == PRODUCT_CTH
        assert rec.sentiment == SENTIMENT_UNKNOWN
        assert rec.sentiment_score is None
        assert rec.risk_level == RISK_UNKNOWN
        assert rec.risk_score is None
        assert rec.publish_datetime == ""
        assert rec.captured_at == ""

    def test_time_separation(self):
        """P0红线：publish_datetime 与 captured_at 必须独立设置，不互相覆盖。"""
        rec = CanonicalRecord(
            publish_datetime="2026-08-31 10:00:00",
            captured_at="2026-09-04 22:51:31",
        )
        assert rec.publish_datetime == "2026-08-31 10:00:00"
        assert rec.captured_at == "2026-09-04 22:51:31"
        assert rec.publish_datetime != rec.captured_at

    def test_engagement_total(self):
        rec = CanonicalRecord(
            engagement_likes=10, engagement_comments=5,
            engagement_collects=3, engagement_shares=2,
        )
        assert rec.engagement_total() == 20

    def test_compute_hash(self):
        rec = CanonicalRecord(title="test", content="content", url="http://x.com/1")
        h = rec.compute_hash()
        assert len(h) == 16
        assert rec.content_hash == h
        # 相同内容哈希一致
        rec2 = CanonicalRecord(title="test", content="content", url="http://x.com/1")
        assert rec2.compute_hash() == h

    def test_to_dict(self):
        rec = CanonicalRecord(title="test")
        d = rec.to_dict()
        assert isinstance(d, dict)
        assert d["title"] == "test"
        assert "canonical_id" in d
        assert "publish_datetime" in d
        assert "captured_at" in d


class TestNoteToCanonical:
    """notes 表 → CanonicalRecord 转化测试。"""

    def test_missing_sentiment_and_risk_remain_unknown_not_neutral_or_zero(self):
        rec = note_to_canonical({"note_id": "unknown-analysis"})

        assert rec.sentiment == SENTIMENT_UNKNOWN
        assert rec.sentiment_score is None
        assert rec.risk_level == RISK_UNKNOWN
        assert rec.risk_score is None

    def test_basic_conversion(self):
        note = {
            "id": 1, "note_id": "test_001", "title": "测试笔记",
            "content": "测试内容", "url": "https://x.com/1",
            "author_id": "author1", "author_nickname": "测试用户",
            "likes": 10, "comments": 5, "collects": 3, "shares": 2,
            "publish_date": "2026-08-31", "publish_datetime": "2026-08-31 10:00:00",
            "collected_at": "2026-09-04 22:51:31", "captured_at": "2026-09-04 22:51:31",
            "sentiment": "positive", "sentiment_score": 0.8,
            "risk_level": "low", "risk_score": 0,
            "source_platform": "xhs", "source_keyword": "太古汇",
            "subject_type": "normal_user", "content_type": "ugc",
            "data_quality_status": "ok", "data_quality_score": 100.0,
            "verification_confidence": 0.9,
            "relevance_status": "relevant", "verification_status": "review",
            "ai_provider": "rule", "ai_model": "",
            "topics": '["美食","购物"]', "event_hint": "",
        }
        rec = note_to_canonical(note)
        assert rec.canonical_id == "can_note_test_001"
        assert rec.source_type == SOURCE_TYPE_NOTE
        assert rec.source_table == "notes"
        assert rec.source_platform == "xhs"
        assert rec.title == "测试笔记"
        assert rec.content == "测试内容"
        assert rec.sentiment == "positive"
        assert rec.risk_level == "low"
        assert rec.engagement_likes == 10
        assert rec.engagement_comments == 5
        assert rec.subject_type == "normal_user"
        assert rec.content_type == "ugc"
        # P0红线：时间分离
        assert rec.publish_datetime == "2026-08-31 10:00:00"
        assert rec.captured_at == "2026-09-04 22:51:31"
        assert rec.publish_datetime != rec.captured_at

    def test_fallback_publish_date(self):
        """当 publish_datetime 为空时，回退到 publish_date。"""
        note = {"note_id": "t2", "publish_date": "2026-08-31",
                "publish_datetime": "", "captured_at": "2026-09-04 22:51:31"}
        rec = note_to_canonical(note)
        assert rec.publish_datetime == "2026-08-31"

    def test_fallback_collected_at(self):
        """当 captured_at 为空时，回退到 collected_at。"""
        note = {"note_id": "t3", "publish_datetime": "2026-08-31",
                "captured_at": "", "collected_at": "2026-09-04 22:51:31"}
        rec = note_to_canonical(note)
        assert rec.captured_at == "2026-09-04 22:51:31"


class TestWebMentionToCanonical:
    """web_mentions 表 → CanonicalRecord 转化测试。"""

    def test_basic_conversion(self):
        web = {
            "id": 1, "source_id": "bing_abc123",
            "source_platform": "bing_search", "source_type": "web",
            "title": "广州太古汇新闻", "content": "新闻内容",
            "url": "https://news.example.com/1", "domain": "example.com",
            "published_at": "2026-08-30 14:00:00",
            "fetched_at": "2026-09-04 22:51:31",
            "source_adapter": "bing_search", "query": "太古汇",
            "canonical_url": "https://news.example.com/1",
            "relevance": "pending", "verification": "review",
            "ai_provider": "rule",
        }
        rec = web_mention_to_canonical(web)
        assert rec.canonical_id == "can_web_bing_abc123"
        assert rec.source_type == SOURCE_TYPE_WEB_MENTION
        assert rec.source_table == "web_mentions"
        assert rec.source_platform == "bing_search"
        assert rec.title == "广州太古汇新闻"
        assert rec.subject_type == "media"
        assert rec.content_type == "news"
        # P0红线：published_at → publish_datetime, fetched_at → captured_at
        assert rec.publish_datetime == "2026-08-30 14:00:00"
        assert rec.captured_at == "2026-09-04 22:51:31"
        assert rec.publish_datetime != rec.captured_at


class TestCollectedNoteToCanonical:
    """CollectedNote → CanonicalRecord 转化测试。"""

    def test_basic_conversion(self):
        from lumenis.adapters.base import CollectedNote
        cn = CollectedNote(
            title="采集测试", content="采集内容", url="https://xhs.com/123",
            author="测试用户", author_id="u123", publish_date="2026-09-01",
            likes=100, comments=20, collects=10, shares=5,
            source_platform="xiaohongshu",
            raw_data={"note_id": "note123"},
        )
        rec = collected_note_to_canonical(cn, source_platform="xiaohongshu", keyword="太古汇")
        assert rec.source_type == "collected_note"
        assert rec.source_platform == "xiaohongshu"
        assert rec.title == "采集测试"
        assert rec.external_id == "note123"
        assert rec.engagement_likes == 100
        assert rec.engagement_comments == 20
        # P0红线：publish_date → publish_datetime, 当前时刻 → captured_at
        assert rec.publish_datetime == "2026-09-01"
        assert rec.captured_at != ""  # 当前时刻
        assert rec.publish_datetime != rec.captured_at


class TestPersistCanonical:
    """幂等写入测试。"""

    def test_insert_new(self, tmp_db):
        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        rec = CanonicalRecord(
            canonical_id="can_test_001", title="测试", content="内容",
            publish_datetime="2026-08-31", captured_at="2026-09-04",
        )
        flag = persist_canonical(con, rec)
        assert flag == "inserted"
        row = con.execute(f"SELECT * FROM {CANONICAL_TABLE} WHERE canonical_id=?",
                          ("can_test_001",)).fetchone()
        assert row is not None
        assert row["title"] == "测试"
        con.close()

    def test_update_existing(self, tmp_db):
        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        rec1 = CanonicalRecord(
            canonical_id="can_test_002", title="原始标题", content="内容",
            engagement_likes=10,
        )
        persist_canonical(con, rec1)
        # 再次写入，更新互动量
        rec2 = CanonicalRecord(
            canonical_id="can_test_002", title="原始标题", content="内容",
            engagement_likes=20,
        )
        flag = persist_canonical(con, rec2)
        assert flag == "updated"
        row = con.execute(f"SELECT engagement_likes FROM {CANONICAL_TABLE} WHERE canonical_id=?",
                          ("can_test_002",)).fetchone()
        assert row["engagement_likes"] == 20
        con.close()

    def test_protected_fields_not_overwritten(self, tmp_db):
        """已有人工标注字段（verification_status等）不应被新写入覆盖。"""
        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        rec1 = CanonicalRecord(
            canonical_id="can_test_003", title="测试",
            verification_status="confirmed", relevance_status="relevant",
            subject_type="KOL", content_type="商业",
            sentiment="positive", risk_level="high",
        )
        persist_canonical(con, rec1)
        # 再次写入默认值，受保护字段应保留
        rec2 = CanonicalRecord(
            canonical_id="can_test_003", title="测试",
            verification_status="review", relevance_status="unverified",
            subject_type="", content_type="",
            sentiment="neutral", risk_level="low",
        )
        persist_canonical(con, rec2)
        row = con.execute(
            f"SELECT verification_status, subject_type, sentiment, risk_level FROM {CANONICAL_TABLE} WHERE canonical_id=?",
            ("can_test_003",)).fetchone()
        # 受保护字段保留旧值
        assert row["verification_status"] == "confirmed"
        assert row["subject_type"] == "KOL"
        con.close()


class TestSyncAllToCanonical:
    """批量同步测试。"""

    def test_sync_notes_and_web(self, tmp_db):
        con = sqlite3.connect(tmp_db)
        # 插入测试 notes
        con.execute("""
            INSERT INTO notes (note_id, title, content, url, publish_datetime, captured_at,
                              source_platform, sentiment, risk_level, subject_type, content_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("n1", "笔记1", "内容1", "http://x.com/1", "2026-08-31", "2026-09-04",
              "xhs", "positive", "low", "normal_user", "ugc"))
        con.execute("""
            INSERT INTO notes (note_id, title, content, url, publish_datetime, captured_at,
                              source_platform, sentiment, risk_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("n2", "笔记2", "内容2", "http://x.com/2", "2026-09-01", "2026-09-04",
              "weibo", "neutral", "medium"))
        # 插入测试 web_mentions
        con.execute("""
            INSERT INTO web_mentions (source_id, source_platform, title, content, url,
                                      published_at, fetched_at, source_adapter, query, canonical_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("w1", "bing", "网页1", "内容1", "http://news.com/1",
              "2026-08-30", "2026-09-04", "bing_search", "太古汇", "http://news.com/1"))
        con.commit()
        con.close()

        stats = sync_all_to_canonical(tmp_db)
        assert stats["notes_total"] == 2
        assert stats["notes_inserted"] == 2
        assert stats["web_total"] == 1
        assert stats["web_inserted"] == 1
        assert len(stats["errors"]) == 0

        # 验证 canonical_data 表
        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        count = con.execute(f"SELECT COUNT(*) as c FROM {CANONICAL_TABLE}").fetchone()["c"]
        assert count == 3
        # 验证时间分离
        rows = con.execute(f"SELECT publish_datetime, captured_at FROM {CANONICAL_TABLE}").fetchall()
        for r in rows:
            assert r["publish_datetime"] != r["captured_at"] or r["publish_datetime"] == ""
        con.close()

    def test_sync_idempotent(self, tmp_db):
        """重复同步不应产生重复记录。"""
        con = sqlite3.connect(tmp_db)
        con.execute("INSERT INTO notes (note_id, title, publish_datetime, captured_at) VALUES (?, ?, ?, ?)",
                    ("n1", "笔记1", "2026-08-31", "2026-09-04"))
        con.commit()
        con.close()

        stats1 = sync_all_to_canonical(tmp_db)
        stats2 = sync_all_to_canonical(tmp_db)
        assert stats1["notes_inserted"] == 1
        assert stats2["notes_inserted"] == 0
        assert stats2["notes_updated"] == 1

        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        count = con.execute(f"SELECT COUNT(*) as c FROM {CANONICAL_TABLE}").fetchone()["c"]
        assert count == 1
        con.close()


class TestSchemaVersion:
    """schema_version 表接入测试。"""

    def test_register_and_get(self, tmp_db):
        register_schema_version(tmp_db, "1.0.0", "canonical_data 表初始化", "t4-test")
        versions = get_schema_versions(tmp_db)
        assert len(versions) == 1
        assert versions[0]["version"] == "1.0.0"
        assert versions[0]["description"] == "canonical_data 表初始化"
        assert versions[0]["applied_by"] == "t4-test"
        assert versions[0]["applied_at"] != ""

    def test_multiple_versions(self, tmp_db):
        register_schema_version(tmp_db, "1.0.0", "v1")
        register_schema_version(tmp_db, "1.1.0", "v2")
        versions = get_schema_versions(tmp_db)
        assert len(versions) == 2
        assert versions[0]["version"] == "1.0.0"
        assert versions[1]["version"] == "1.1.0"


class TestSelfCheck:
    """自检测试。"""

    def test_self_check_pass(self, tmp_db):
        con = sqlite3.connect(tmp_db)
        con.execute("INSERT INTO notes (note_id, title, publish_datetime, captured_at) VALUES (?, ?, ?, ?)",
                    ("n1", "笔记1", "2026-08-31 10:00:00", "2026-09-04 22:51:31"))
        con.commit()
        con.close()
        sync_all_to_canonical(tmp_db)

        check = self_check(tmp_db)
        assert check["canonical_table_exists"] is True
        assert check["schema_version_table_exists"] is True
        assert check["canonical_count"] == 1
        assert check["time_separation_violations"] == 0
        assert check["status"] == "PASS"

    def test_self_check_empty(self, tmp_db):
        check = self_check(tmp_db)
        assert check["canonical_table_exists"] is True
        assert check["canonical_count"] == 0
        assert any("canonical_data 表为空" in issue for issue in check["issues"])


class TestQuery:
    """查询函数测试。"""

    def test_get_by_id(self, tmp_db):
        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        rec = CanonicalRecord(canonical_id="can_q1", title="查询测试")
        persist_canonical(con, rec)
        result = get_canonical_by_id(con, "can_q1")
        assert result is not None
        assert result["title"] == "查询测试"
        assert get_canonical_by_id(con, "nonexistent") is None
        con.close()

    def test_list_and_count(self, tmp_db):
        con = sqlite3.connect(tmp_db)
        con.row_factory = sqlite3.Row
        for i in range(5):
            rec = CanonicalRecord(
                canonical_id=f"can_l{i}", title=f"标题{i}",
                source_type="note" if i < 3 else "web_mention",
                source_platform="xhs" if i < 3 else "weibo",
            )
            persist_canonical(con, rec)
        con.commit()

        all_records = list_canonical(con, limit=10)
        assert len(all_records) == 5
        notes_only = list_canonical(con, source_type="note")
        assert len(notes_only) == 3
        xhs_only = list_canonical(con, platform="xhs")
        assert len(xhs_only) == 3

        stats = count_canonical(con)
        assert stats["total"] == 5
        assert stats["note"] == 3
        assert stats["web_mention"] == 2
        con.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
