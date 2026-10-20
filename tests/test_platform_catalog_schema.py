# -*- coding: utf-8 -*-
"""LUMENIS SYSTEM Collector catalog and data-center schema tests.

覆盖：
1. 6个新增平台命名归一化（channels/youtube/tiktok/reddit/linkedin/github）
2. 12平台字段映射（map_raw_to_normalized）
3. Adapter骨架可导入+可注册
4. Shared Database migration creates 44 tables (43 platform data tables + platform_registry)
5. platform_registry is seeded from the SYSTEM Collector catalog
6. 互动量统一计算
7. 生产红线：SUBJECT_WORDS未修改、无Secret泄漏
"""
import os
import sys
import json
import sqlite3
from pathlib import Path

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lumenis.system.collector.adapters.platform_naming import (
    normalize_platform,
    platform_display_name,
    PLATFORM_NATIVE_FIELDS,
    PLATFORM_FIELD_MAPPING,
    PLATFORM_CONNECTION,
    V1_PLATFORMS,
    map_raw_to_normalized,
    calculate_engagement,
    calculate_engagement_rate,
    get_ui_visible_platforms,
    get_connection_status,
    get_raw_table,
    get_platform_registry_catalog,
)


@pytest.fixture
def platform_db(tmp_path, monkeypatch):
    """Upgrade an isolated v12 SQLite database through the canonical v13 migration."""
    from lumenis.shared.database import migrations

    db_path = str(tmp_path / "platform-schema.db")
    conn = sqlite3.connect(db_path)
    migrations.init_version_table(conn)
    conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, event_date TEXT)")
    for table_name in (
        "notes", "note_comments", "daily_reports", "collection_logs",
        "metric_snapshots", "event_mentions", "note_review_history",
    ):
        conn.execute(f'CREATE TABLE "{table_name}" (id INTEGER PRIMARY KEY)')
    conn.execute("INSERT INTO notes (id) VALUES (1)")
    migrations.set_version(conn, 12, "hermetic v12 fixture")
    conn.close()

    monkeypatch.setattr(migrations, "get_connection", lambda: sqlite3.connect(db_path))
    monkeypatch.setenv("ZBC_DB_PATH", db_path)
    assert migrations.migrate(target_version=13) is True

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def _existing_tables(conn):
    return {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def _data_center_client(monkeypatch, db_path):
    import data_center_api

    class TemporaryRepository:
        def connect(self):
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn

    monkeypatch.setattr(data_center_api, "get_repository", lambda: TemporaryRepository())
    app = Flask(__name__)
    app.register_blueprint(data_center_api.data_center_bp)
    return app.test_client()


# ============================================================
# 1. 新增平台命名归一化测试
# ============================================================
class TestNewPlatformNaming:
    def test_channels_aliases(self):
        assert normalize_platform("channels") == "channels"
        assert normalize_platform("wechat_channels") == "channels"
        assert normalize_platform("shipinhao") == "channels"
        assert normalize_platform("视频号") == "channels"

    def test_youtube_aliases(self):
        assert normalize_platform("youtube") == "youtube"
        assert normalize_platform("yt") == "youtube"
        assert normalize_platform("YOUTUBE") == "youtube"

    def test_tiktok_aliases(self):
        assert normalize_platform("tiktok") == "tiktok"
        assert normalize_platform("tt") == "tiktok"
        assert normalize_platform("douyin_intl") == "tiktok"

    def test_reddit_aliases(self):
        assert normalize_platform("reddit") == "reddit"
        assert normalize_platform("rd") == "reddit"

    def test_linkedin_aliases(self):
        assert normalize_platform("linkedin") == "linkedin"
        assert normalize_platform("ln") == "linkedin"

    def test_github_aliases(self):
        assert normalize_platform("github") == "github"
        assert normalize_platform("gh") == "github"

    def test_new_platforms_display_names(self):
        assert platform_display_name("channels") == "视频号"
        assert platform_display_name("youtube") == "YouTube"
        assert platform_display_name("tiktok") == "TikTok"
        assert platform_display_name("reddit") == "Reddit"
        assert platform_display_name("linkedin") == "LinkedIn"
        assert platform_display_name("github") == "GitHub"

    def test_unknown_returns_none(self):
        assert normalize_platform("ghost_platform_xyz") is None
        assert normalize_platform("") is None
        assert normalize_platform(None) is None


# ============================================================
# 2. 12平台字段映射测试
# ============================================================
class TestFieldMapping:
    def test_catalog_platform_count(self):
        assert len(V1_PLATFORMS) == 12

    def test_all_v1_platforms_have_native_fields(self):
        for p in V1_PLATFORMS:
            assert p in PLATFORM_NATIVE_FIELDS, f"{p} missing native fields"

    def test_all_v1_platforms_have_field_mapping(self):
        for p in V1_PLATFORMS:
            assert p in PLATFORM_FIELD_MAPPING, f"{p} missing field mapping"

    def test_all_v1_platforms_have_connection_status(self):
        for p in V1_PLATFORMS:
            assert p in PLATFORM_CONNECTION, f"{p} missing connection status"

    def test_xhs_mapping_preserves_native_names(self):
        raw = {"note_id": "n1", "liked_count": 100, "collected_count": 50, "comment_count": 20, "share_count": 5, "time": 1700000000}
        norm = map_raw_to_normalized(raw, "xhs")
        assert norm["platform"] == "xiaohongshu"
        assert norm["platform_content_id"] == "n1"
        assert norm["like_count"] == 100  # liked_count -> like_count
        assert norm["collect_count"] == 50  # collected_count -> collect_count
        assert norm["raw_data"] is raw

    def test_douyin_mapping_digg_to_like(self):
        raw = {"aweme_id": "7342000000000000000", "digg_count": 999, "play_count": 5000}
        norm = map_raw_to_normalized(raw, "douyin")
        assert norm["like_count"] == 999  # digg_count -> like_count
        assert norm["view_count"] == 5000  # play_count -> view_count

    def test_bilibili_mapping(self):
        raw = {"bvid": "BV1xx", "like": 100, "favorite": 50, "view": 1000, "reply": 30}
        norm = map_raw_to_normalized(raw, "bilibili")
        assert norm["platform_content_id"] == "BV1xx"
        assert norm["like_count"] == 100
        assert norm["collect_count"] == 50
        assert norm["view_count"] == 1000
        assert norm["comment_count"] == 30

    def test_youtube_mapping(self):
        raw = {"video_id": "abc123", "channel_id": "ch1", "view_count": 10000, "like_count": 500}
        norm = map_raw_to_normalized(raw, "youtube")
        assert norm["platform_content_id"] == "abc123"
        assert norm["author_id"] == "ch1"
        assert norm["view_count"] == 10000

    def test_x_mapping_retweet_to_share(self):
        raw = {"tweet_id": "123", "retweet_count": 50, "reply_count": 20, "impression_count": 1000}
        norm = map_raw_to_normalized(raw, "x")
        assert norm["share_count"] == 50  # retweet_count -> share_count
        assert norm["comment_count"] == 20  # reply_count -> comment_count
        assert norm["view_count"] == 1000  # impression_count -> view_count

    def test_reddit_mapping_score_to_like(self):
        raw = {"post_id": "abc", "score": 500, "num_comments": 100, "num_crossposts": 5}
        norm = map_raw_to_normalized(raw, "reddit")
        assert norm["like_count"] == 500  # score -> like_count
        assert norm["comment_count"] == 100
        assert norm["share_count"] == 5

    def test_zhihu_mapping_voteup_to_like(self):
        raw = {"answer_id": "a1", "voteup_count": 200, "favlists_count": 80, "comment_count": 30}
        norm = map_raw_to_normalized(raw, "zhihu")
        assert norm["like_count"] == 200  # voteup_count -> like_count
        assert norm["collect_count"] == 80  # favlists_count -> collect_count

    def test_github_mapping_stargazers_to_like(self):
        raw = {"repo_id": 123, "stargazers_count": 1000, "forks_count": 200, "watchers_count": 500}
        norm = map_raw_to_normalized(raw, "github")
        assert norm["like_count"] == 1000  # stargazers_count -> like_count
        assert norm["share_count"] == 200  # forks_count -> share_count
        assert norm["view_count"] == 500  # watchers_count -> view_count

    def test_missing_fields_are_none_not_zero(self):
        raw = {"video_id": "test"}
        norm = map_raw_to_normalized(raw, "youtube")
        assert norm["like_count"] is None
        assert norm["comment_count"] is None
        assert norm["view_count"] is None

    def test_raw_data_preserved(self):
        raw = {"video_id": "test", "custom_field": "value"}
        norm = map_raw_to_normalized(raw, "youtube")
        assert norm["raw_data"]["custom_field"] == "value"


# ============================================================
# 3. Adapter骨架测试
# ============================================================
class TestAdapters:
    def test_all_new_adapters_importable(self):
        import lumenis.system.collector.adapters.channels
        import lumenis.system.collector.adapters.youtube
        import lumenis.system.collector.adapters.tiktok
        import lumenis.system.collector.adapters.reddit
        import lumenis.system.collector.adapters.linkedin
        import lumenis.system.collector.adapters.github
        assert True

    def test_all_adapters_registered(self):
        from lumenis.system.collector.adapters.registry import list_adapters
        registered = list_adapters()
        for expected in ["channels", "youtube", "tiktok", "reddit", "linkedin", "github",
                          "xhs", "douyin", "bilibili", "instagram", "x", "zhihu", "weibo"]:
            assert expected in registered, f"{expected} not registered"

    def test_new_adapters_disabled_by_default(self):
        from lumenis.system.collector.adapters.channels import ChannelsAdapter
        from lumenis.system.collector.adapters.youtube import YouTubeAdapter
        from lumenis.system.collector.adapters.tiktok import TikTokAdapter
        from lumenis.system.collector.adapters.reddit import RedditAdapter
        from lumenis.system.collector.adapters.linkedin import LinkedInAdapter
        from lumenis.system.collector.adapters.github import GitHubAdapter
        for cls in [ChannelsAdapter, YouTubeAdapter, TikTokAdapter, RedditAdapter, LinkedInAdapter, GitHubAdapter]:
            assert cls.enabled is False, f"{cls.__name__} should be disabled"

    def test_adapter_search_returns_not_implemented(self):
        from lumenis.system.collector.adapters.channels import ChannelsAdapter
        from lumenis.system.collector.adapters.base import CollectionStatus
        adapter = ChannelsAdapter()
        result = adapter.search("test")
        assert result.status == CollectionStatus.NOT_SUPPORTED
        assert "not implemented" in result.message.lower() or "待接入" in result.message

    def test_adapter_normalize_method_exists(self):
        from lumenis.system.collector.adapters.youtube import YouTubeAdapter
        adapter = YouTubeAdapter()
        raw = {"video_id": "v1", "view_count": 100}
        norm = adapter.normalize_to_platform_contents(raw)
        assert norm["platform_content_id"] == "v1"
        assert norm["platform"] == "youtube"


# ============================================================
# 4. 数据库表结构验证测试
# ============================================================
class TestDatabaseTables:
    def test_raw_tables_exist(self, platform_db):
        expected_raw = [
            "xhs_notes", "xhs_note_comments", "xhs_users",
            "douyin_videos", "douyin_comments", "douyin_users",
            "bilibili_videos", "bilibili_comments", "bilibili_users",
            "channels_videos", "channels_comments",
            "youtube_videos", "youtube_comments", "youtube_channels",
            "tiktok_videos", "tiktok_comments", "tiktok_users",
            "instagram_media", "instagram_comments", "instagram_users",
            "x_posts", "x_users",
            "reddit_posts", "reddit_comments", "reddit_subreddits",
            "linkedin_posts", "linkedin_users",
            "github_repositories", "github_issues", "github_pull_requests", "github_releases",
            "zhihu_answers", "zhihu_questions", "zhihu_articles", "zhihu_comments",
        ]
        missing = [table for table in expected_raw if table not in _existing_tables(platform_db)]
        assert len(expected_raw) == 35
        assert not missing, f"Missing raw tables: {missing}"

    def test_normalized_tables_exist(self, platform_db):
        for table in ["platform_accounts", "platform_contents", "platform_comments"]:
            assert table in _existing_tables(platform_db), f"Missing normalized table: {table}"

    def test_evidence_tables_exist(self, platform_db):
        for table in ["collection_runs", "platform_evidence"]:
            assert table in _existing_tables(platform_db), f"Missing evidence table: {table}"

    def test_business_tables_exist(self, platform_db):
        for table in ["brands", "content_analysis", "creators", "platform_registry"]:
            assert table in _existing_tables(platform_db), f"Missing business/registry table: {table}"

    def test_existing_tables_and_rows_are_preserved(self, platform_db):
        """The v13 schema addition retains core application data."""
        for table in ["notes", "note_comments", "events", "daily_reports", "collection_logs",
                      "metric_snapshots", "event_mentions", "note_review_history"]:
            assert table in _existing_tables(platform_db), f"Existing table missing: {table}"
        assert platform_db.execute("SELECT id FROM notes WHERE id=1").fetchone()[0] == 1

    def test_events_extended_columns(self, platform_db):
        cols = {row[1] for row in platform_db.execute("PRAGMA table_info(events)").fetchall()}
        for col in ["event_type", "severity", "growth_rate", "confidence"]:
            assert col in cols, f"events missing column: {col}"

    def test_platform_contents_has_unique_constraint(self, platform_db):
        sql = platform_db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='platform_contents'"
        ).fetchone()[0]
        assert "UNIQUE" in sql.upper()
        assert "platform_content_id" in sql

    def test_xhs_notes_has_liked_count_not_likes(self, platform_db):
        cols = {row[1] for row in platform_db.execute("PRAGMA table_info(xhs_notes)").fetchall()}
        assert "liked_count" in cols
        assert "likes" not in cols

    def test_douyin_videos_has_digg_count(self, platform_db):
        cols = {row[1] for row in platform_db.execute("PRAGMA table_info(douyin_videos)").fetchall()}
        assert "digg_count" in cols
        assert "like_count" not in cols

    def test_bilibili_videos_has_view_not_play_count(self, platform_db):
        cols = {row[1] for row in platform_db.execute("PRAGMA table_info(bilibili_videos)").fetchall()}
        assert "view" in cols
        assert "play_count" not in cols


class TestPlatformRegistry:
    def test_registry_has_full_current_catalog(self, platform_db):
        count = platform_db.execute("SELECT COUNT(*) FROM platform_registry").fetchone()[0]
        assert count == len(get_platform_registry_catalog())

    def test_ui_visibility_and_catalog_status_match_system_owner(self, platform_db):
        rows = platform_db.execute(
            "SELECT platform_id, status, ui_visible FROM platform_registry"
        ).fetchall()
        assert {row[0] for row in rows if row[2]} == set(get_ui_visible_platforms())
        for platform_id, status, _ui_visible in rows:
            assert status == PLATFORM_CONNECTION[platform_id].status

    def test_xiaohongshu_catalog_is_active_but_health_is_unknown(self, platform_db):
        row = platform_db.execute(
            "SELECT status, has_real_data FROM platform_registry WHERE platform_id='xiaohongshu'"
        ).fetchone()
        assert row[0] == PLATFORM_CONNECTION["xiaohongshu"].status == "ACTIVE"
        assert row[1] is None

    def test_planned_platforms_visible_without_collector(self, platform_db):
        rows = platform_db.execute(
            "SELECT platform_id, ui_visible FROM platform_registry WHERE status='PLANNED'"
        ).fetchall()
        for platform_id, visible in rows:
            assert visible == int(PLATFORM_CONNECTION[platform_id].ui_visible)
            assert PLATFORM_CONNECTION[platform_id].has_collector is False

    def test_registry_has_required_columns(self, platform_db):
        cols = {row[1] for row in platform_db.execute("PRAGMA table_info(platform_registry)").fetchall()}
        required = ["platform_id", "platform_name", "display_name", "status", "ui_visible",
                    "adapter_module", "raw_tables", "normalized_mapping", "has_collector",
                    "has_api_routes", "has_real_data", "last_sync_at", "data_quality_score"]
        for col in required:
            assert col in cols, f"platform_registry missing column: {col}"

    def test_registry_static_metadata_uses_current_system_modules(self, platform_db):
        rows = platform_db.execute(
            "SELECT platform_id, adapter_module, raw_tables, normalized_mapping, notes FROM platform_registry"
        ).fetchall()
        for platform_id, module, raw_tables, normalized_mapping, notes in rows:
            catalog = next(item for item in get_platform_registry_catalog() if item["platform_id"] == platform_id)
            assert module == catalog["adapter_module"]
            assert module is None or module.startswith("lumenis.system.collector.adapters.")
            assert json.loads(raw_tables) == catalog["raw_tables"]
            assert json.loads(normalized_mapping) == catalog["normalized_mapping"]
            assert notes == catalog["notes"]

    def test_get_ui_visible_matches_database(self, platform_db):
        rows = platform_db.execute(
            "SELECT platform_id FROM platform_registry WHERE ui_visible=1"
        ).fetchall()
        assert {row[0] for row in rows} == set(get_ui_visible_platforms())

    def test_migration_refreshes_static_metadata_only(self, platform_db):
        from lumenis.shared.database import migrations

        platform_db.execute("""UPDATE platform_registry SET
            platform_name='legacy', display_name='legacy', status='COOLDOWN', ui_visible=0,
            adapter_module='platform_adapters.xhs', raw_tables='[]', normalized_mapping='{}',
            last_sync_at='2026-01-02T03:04:05', data_quality_score=0.37,
            has_collector=0, has_api_routes=0, has_real_data=1, notes='legacy metadata'
            WHERE platform_id='xiaohongshu'""")
        platform_db.execute(
            "INSERT INTO xhs_notes (note_id, title, liked_count) VALUES ('keep-note', 'kept', 11)"
        )
        platform_db.execute("""INSERT INTO platform_registry
            (platform_id, platform_name, status, ui_visible, has_real_data, notes)
            VALUES ('future_platform', 'future_platform', 'VERIFYING', 0, NULL, 'keep')""")
        platform_db.commit()

        migrations.migration_12_to_13(platform_db)
        platform_db.commit()
        migrations.migration_12_to_13(platform_db)
        platform_db.commit()

        row = platform_db.execute(
            """SELECT platform_name, display_name, status, ui_visible, adapter_module,
                raw_tables, normalized_mapping, last_sync_at, data_quality_score,
                has_collector, has_api_routes, has_real_data, notes
                FROM platform_registry WHERE platform_id='xiaohongshu'"""
        ).fetchone()
        catalog = next(item for item in get_platform_registry_catalog() if item["platform_id"] == "xiaohongshu")
        assert row[0] == catalog["platform_name"]
        assert row[1] == catalog["display_name"]
        assert row[2:4] == ("COOLDOWN", 0)
        assert row[4] == catalog["adapter_module"]
        assert json.loads(row[5]) == catalog["raw_tables"]
        assert json.loads(row[6]) == catalog["normalized_mapping"]
        assert row[7:10] == ("2026-01-02T03:04:05", 0.37, catalog["has_collector"])
        assert row[10:] == (catalog["has_api_routes"], 1, catalog["notes"])
        assert platform_db.execute("SELECT title FROM xhs_notes WHERE note_id='keep-note'").fetchone()[0] == "kept"
        assert tuple(platform_db.execute(
            "SELECT status, has_real_data, notes FROM platform_registry WHERE platform_id='future_platform'"
        ).fetchone()) == ("VERIFYING", None, "keep")

    def test_conflicting_existing_schema_fails_closed_without_data_loss(self, tmp_path, monkeypatch):
        from lumenis.shared.database import migrations, platform_schema

        db_path = str(tmp_path / "conflicting-v12.db")
        conn = sqlite3.connect(db_path)
        migrations.init_version_table(conn)
        conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, event_date TEXT)")
        bad_platform_contents_sql = platform_schema.NORMALIZED_TABLES_SQL[1].replace(
            "        collected_at TEXT,\n        UNIQUE(platform, platform_content_id)\n",
            "        collected_at TEXT\n",
        )
        conn.execute(bad_platform_contents_sql)
        conn.execute(
            "INSERT INTO platform_contents (platform, platform_content_id, title) VALUES ('xhs', 'keep-id', 'kept')"
        )
        migrations.set_version(conn, 12, "hermetic conflict fixture")
        conn.close()

        monkeypatch.setattr(migrations, "get_connection", lambda: sqlite3.connect(db_path))
        monkeypatch.setattr(migrations, "backup_database", lambda *_args, **_kwargs: "test-backup-skipped")
        assert migrations.migrate() is False

        verify = sqlite3.connect(db_path)
        try:
            assert migrations.get_current_version(verify) == 12
            tables = _existing_tables(verify)
            assert "xhs_notes" not in tables
            kept = verify.execute(
                "SELECT title FROM platform_contents WHERE platform_content_id='keep-id'"
            ).fetchone()
            assert kept == ("kept",)
        finally:
            verify.close()


class TestDataCenterAPI:
    def test_platform_list_and_detail_query_registry_and_raw_counts(self, platform_db, monkeypatch):
        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)
        platform_db.execute(
            "INSERT INTO xhs_notes (note_id, title, liked_count) VALUES ('api-note', 'API fixture', 7)"
        )
        platform_db.commit()

        all_response = client.get("/api/data-center/platforms?all=1")
        assert all_response.status_code == 200
        all_payload = all_response.get_json()
        assert all_payload["count"] == len(get_platform_registry_catalog())
        visible_response = client.get("/api/data-center/platforms")
        assert visible_response.status_code == 200
        assert {item["platform_id"] for item in visible_response.get_json()["platforms"]} == set(get_ui_visible_platforms())

        detail = client.get("/api/data-center/platform/xiaohongshu")
        assert detail.status_code == 200
        payload = detail.get_json()["platform"]
        assert payload["status"] == "ACTIVE"
        stats = {item["table"]: item["count"] for item in payload["table_stats"]}
        assert stats["xhs_notes"] == 1

    def test_all_43_queryable_platform_data_tables(self, platform_db, monkeypatch):
        from lumenis.shared.database import platform_schema
        import data_center_api

        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)
        table_sql = (
            platform_schema.RAW_TABLES_SQL + platform_schema.NORMALIZED_TABLES_SQL
            + platform_schema.EVIDENCE_TABLES_SQL + platform_schema.BUSINESS_TABLES_SQL
        )
        expected = {platform_schema._table_name(sql) for sql in table_sql}
        assert len(expected) == 43
        assert expected <= data_center_api.ALLOWED_TABLES
        for table_name in sorted(expected):
            response = client.get(f"/api/data-center/table/{table_name}/schema")
            assert response.status_code == 200, f"{table_name}: {response.get_json()}"
            assert response.get_json()["schema"], f"{table_name} has no queryable columns"

    def test_raw_table_query_preserves_native_fields_and_data(self, platform_db, monkeypatch):
        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)
        platform_db.execute(
            "INSERT INTO xhs_notes (note_id, title, liked_count, time) VALUES (?, ?, ?, ?)",
            ("api-note", "catalog fixture", 17, 1700000000),
        )
        platform_db.commit()

        schema = client.get("/api/data-center/table/xhs_notes/schema")
        assert schema.status_code == 200
        names = {column["name"] for column in schema.get_json()["schema"]}
        assert "liked_count" in names and "likes" not in names
        query = client.get("/api/data-center/table/xhs_notes?q=catalog&page=1&per_page=10")
        assert query.status_code == 200
        result = query.get_json()
        assert result["total"] == 1
        assert result["data"][0]["liked_count"] == 17

    def test_fix032_filters_sentiment_risk_and_source_publish_date(self, platform_db, monkeypatch):
        """FIX-032: filter by source sentiment/risk/publication, never collection time."""
        columns = {row["name"] for row in platform_db.execute("PRAGMA table_info(notes)")}
        for name, data_type in (
            ("sentiment", "TEXT"),
            ("risk_level", "TEXT"),
            ("publish_date", "TEXT"),
            ("collected_at", "TEXT"),
        ):
            if name not in columns:
                platform_db.execute(f"ALTER TABLE notes ADD COLUMN {name} {data_type}")
        platform_db.execute("DELETE FROM notes")
        platform_db.executemany(
            "INSERT INTO notes (id, sentiment, risk_level, publish_date, collected_at) VALUES (?, ?, ?, ?, ?)",
            [
                (11, "negative", "high", "2026-10-10", "2026-11-10"),
                (12, "negative", "high", "2026-11-01", "2026-10-10"),
                (13, "positive", "high", "2026-10-12", "2026-10-12"),
                (14, "negative", "low", "2026-10-13", "2026-10-13"),
            ],
        )
        platform_db.commit()
        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)

        response = client.get(
            "/api/data-center/table/notes?sentiment=negative&risk_level=high"
            "&start_date=2026-10-01&end_date=2026-10-31"
        )
        assert response.status_code == 200
        result = response.get_json()
        assert result["total"] == 1
        assert [item["id"] for item in result["data"]] == [11]
        assert result["data"][0]["publish_date"] == "2026-10-10"

        empty = client.get(
            "/api/data-center/table/notes?sentiment=neutral&risk_level=high"
            "&start_date=2026-10-01&end_date=2026-10-31"
        )
        assert empty.status_code == 200
        assert empty.get_json()["total"] == 0
        assert empty.get_json()["data"] == []

    def test_fix032_filters_unix_timestamp_publication_fields(self, platform_db, monkeypatch):
        """Numeric native publication times are compared as Unix seconds, not ISO text."""
        from datetime import datetime, timezone

        inside = datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc).timestamp()
        outside = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp()
        platform_db.execute("DELETE FROM zhihu_answers")
        platform_db.executemany(
            "INSERT INTO zhihu_answers (answer_id, created_time) VALUES (?, ?)",
            [("fix032-inside", int(inside)), ("fix032-outside", int(outside))],
        )
        platform_db.commit()
        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)

        response = client.get(
            "/api/data-center/table/zhihu_answers?start_date=2026-10-01&end_date=2026-10-31"
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["total"] == 1
        assert [row["answer_id"] for row in payload["data"]] == ["fix032-inside"]

    @pytest.mark.parametrize(("table_name", "id_column", "inside_id", "outside_id"), [
        ("xhs_notes", "note_id", "fix096-xhs-note-in", "fix096-xhs-note-out"),
        ("xhs_note_comments", "comment_id", "fix096-xhs-comment-in", "fix096-xhs-comment-out"),
    ])
    def test_fix096_xhs_millisecond_publication_bounds(
        self, platform_db, monkeypatch, table_name, id_column, inside_id, outside_id,
    ):
        """FIX-096: XHS native time is epoch milliseconds, not seconds."""
        from datetime import datetime, timezone

        inside = int(datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc).timestamp() * 1000)
        outside = int(datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
        platform_db.execute(f"DELETE FROM {table_name}")
        platform_db.executemany(
            f"INSERT INTO {table_name} ({id_column}, time) VALUES (?, ?)",
            [(inside_id, inside), (outside_id, outside)],
        )
        platform_db.commit()
        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)

        response = client.get(
            f"/api/data-center/table/{table_name}?start_date=2026-10-31&end_date=2026-10-31"
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["total"] == 1
        assert [row[id_column] for row in payload["data"]] == [inside_id]

    def test_fix096_empty_publish_date_falls_back_per_row_to_publish_datetime(
        self, platform_db, monkeypatch,
    ):
        """FIX-096: each row falls back only when publish_date is null or blank."""
        columns = {row["name"] for row in platform_db.execute("PRAGMA table_info(notes)")}
        if "publish_date" not in columns:
            platform_db.execute("ALTER TABLE notes ADD COLUMN publish_date TEXT")
        if "publish_datetime" not in columns:
            platform_db.execute("ALTER TABLE notes ADD COLUMN publish_datetime TEXT")
        platform_db.execute("DELETE FROM notes")
        platform_db.executemany(
            "INSERT INTO notes (id, publish_date, publish_datetime) VALUES (?, ?, ?)",
            [
                (9601, "", "2026-10-15T10:00:00Z"),
                (9602, None, "2026-10-16T10:00:00Z"),
                (9603, "2026-10-17", "2026-11-15T10:00:00Z"),
                (9604, "2026-11-01", "2026-10-18T10:00:00Z"),
                (9605, None, "2026-11-01T00:00:00Z"),
            ],
        )
        platform_db.commit()
        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)

        response = client.get(
            "/api/data-center/table/notes?start_date=2026-10-01&end_date=2026-10-31"
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["total"] == 3
        assert {row["id"] for row in payload["data"]} == {9601, 9602, 9603}

    def test_text_publication_bounds_compare_instants_not_strings(
        self, platform_db, monkeypatch,
    ):
        """Offset-bearing text timestamps are compared as UTC instants."""
        columns = {row["name"] for row in platform_db.execute("PRAGMA table_info(notes)")}
        if "publish_date" not in columns:
            platform_db.execute("ALTER TABLE notes ADD COLUMN publish_date TEXT")
        platform_db.execute("DELETE FROM notes")
        platform_db.executemany(
            "INSERT INTO notes (id, publish_date) VALUES (?, ?)",
            [
                (9701, "2026-10-31T05:00:00Z"),        # == 13:00+08:00, inside
                (9702, "2026-10-31 03:00:00"),         # == 11:00+08:00, before
                (9703, "2026-10-31T12:30:00+08:00"),   # inside
            ],
        )
        platform_db.commit()
        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)
        from urllib.parse import quote
        response = client.get(
            "/api/data-center/table/notes?start_date="
            + quote("2026-10-31T12:00:00+08:00") + "&end_date=2026-10-31"
        )
        assert response.status_code == 200
        assert {row["id"] for row in response.get_json()["data"]} == {9701, 9703}

    def test_text_publication_max_end_date_is_inclusive_not_an_error(self, platform_db, monkeypatch):
        columns = {row["name"] for row in platform_db.execute("PRAGMA table_info(notes)")}
        if "publish_date" not in columns:
            platform_db.execute("ALTER TABLE notes ADD COLUMN publish_date TEXT")
        platform_db.execute("DELETE FROM notes")
        platform_db.execute("INSERT INTO notes (id, publish_date) VALUES (9801, '9999-12-31T12:00:00Z')")
        platform_db.execute("INSERT INTO notes (id, publish_date) VALUES (9802, '9999-12-31T23:59:59.999999Z')")
        platform_db.commit()
        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)
        response = client.get("/api/data-center/table/notes?end_date=9999-12-31")
        assert response.status_code == 200
        assert sorted(row["id"] for row in response.get_json()["data"]) == [9801, 9802]
        response = client.get("/api/data-center/table/notes?end_date=9999-12-31T23:59:59.999999Z")
        assert response.status_code == 200
        assert sorted(row["id"] for row in response.get_json()["data"]) == [9801, 9802]
        # Offset-adjusted extremes leave Python's UTC range: no 500.
        response = client.get("/api/data-center/table/notes?end_date=9999-12-31T23:59:59-05:00")
        assert response.status_code == 200
        assert sorted(row["id"] for row in response.get_json()["data"]) == [9801, 9802]
        response = client.get("/api/data-center/table/notes?start_date=0001-01-01T00:00:00%2B05:00")
        assert response.status_code == 200
        assert sorted(row["id"] for row in response.get_json()["data"]) == [9801, 9802]
        platform_db.execute("INSERT INTO notes (id, publish_date) VALUES (9803, '9999-12-31T23:59:59.500000Z')")
        platform_db.commit()
        response = client.get("/api/data-center/table/notes?end_date=9999-12-31T23:59:59Z")
        assert response.status_code == 200
        assert sorted(row["id"] for row in response.get_json()["data"]) == [9801]
        response = client.get("/api/data-center/table/notes?end_date=9999-12-31T23:59:59.999999Z")
        assert sorted(row["id"] for row in response.get_json()["data"]) == [9801, 9802, 9803]
        response = client.get("/api/data-center/table/notes?start_date=9999-12-31T23:59:59-05:00")
        assert response.status_code == 400
        assert response.get_json() == {"ok": False, "error": "invalid start_date"}

    @pytest.mark.parametrize(("parameter", "invalid_date"), [
        ("start_date", "2026-02-30"),
        ("end_date", "2026-13-01"),
    ])
    def test_fix096_rejects_invalid_calendar_dates_for_text_columns(
        self, platform_db, monkeypatch, parameter, invalid_date,
    ):
        """FIX-096: calendar validation applies before text-column filtering too."""
        columns = {row["name"] for row in platform_db.execute("PRAGMA table_info(notes)")}
        if "publish_date" not in columns:
            platform_db.execute("ALTER TABLE notes ADD COLUMN publish_date TEXT")
        platform_db.commit()
        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)

        response = client.get(
            f"/api/data-center/table/notes?{parameter}={invalid_date}"
        )

        assert response.status_code == 400
        assert response.get_json() == {"ok": False, "error": f"invalid {parameter}"}


    def test_fix032_rejects_filters_without_source_fields(self, platform_db, monkeypatch):
        """FIX-032: unsupported filters fail instead of silently returning unfiltered rows."""
        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)

        sentiment = client.get("/api/data-center/table/xhs_users?sentiment=positive")
        assert sentiment.status_code == 400
        assert sentiment.get_json() == {
            "ok": False,
            "error": "sentiment filter unavailable for table xhs_users",
        }

        date_range = client.get("/api/data-center/table/xhs_users?start_date=2026-10-01")
        assert date_range.status_code == 400
        assert date_range.get_json() == {
            "ok": False,
            "error": "publication date filter unavailable for table xhs_users",
        }

    def test_fix032_database_query_error_does_not_return_success(self, platform_db, monkeypatch):
        """FIX-032: a database query failure remains an HTTP error."""
        import data_center_api

        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)

        class FailingNotesConnection:
            def __init__(self, wrapped):
                self.wrapped = wrapped

            def execute(self, sql, parameters=()):
                if sql.startswith("SELECT COUNT(*) FROM notes"):
                    raise sqlite3.OperationalError("synthetic FIX-032 query failure")
                return self.wrapped.execute(sql, parameters)

            def close(self):
                self.wrapped.close()

        def connect_with_one_synthetic_failure():
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            return FailingNotesConnection(conn)

        monkeypatch.setattr(data_center_api, "_get_db", connect_with_one_synthetic_failure)
        response = client.get("/api/data-center/table/notes")
        assert response.status_code == 500

    def test_overview_endpoint_reads_migrated_registry(self, platform_db, monkeypatch):
        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)
        response = client.get("/api/data-center/stats/overview")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["total_platforms"] == len(get_platform_registry_catalog())
        assert payload["ui_visible_count"] == len(get_ui_visible_platforms())
        empty_catalog_ids = []
        for row in platform_db.execute("SELECT platform_id, raw_tables FROM platform_registry"):
            try:
                raw_tables = json.loads(row["raw_tables"]) if row["raw_tables"] else []
            except (json.JSONDecodeError, TypeError):
                raw_tables = None
            if not isinstance(raw_tables, list) or not raw_tables:
                empty_catalog_ids.append(row["platform_id"])
        assert payload["ok"] is (not empty_catalog_ids)
        assert {entry["platform_id"] for entry in payload["errors"]} == set(empty_catalog_ids)
        assert (payload["total_records"] is None) is bool(empty_catalog_ids)

    def test_fix033_successful_count_and_real_empty_table_keep_zero(self, platform_db, monkeypatch):
        """FIX-033: a real COUNT(*) result of zero remains a known zero."""
        platform_db.execute(
            "UPDATE platform_registry SET raw_tables=? WHERE platform_id='xiaohongshu'",
            (json.dumps(["xhs_notes"]),),
        )
        platform_db.execute(
            "INSERT INTO xhs_notes (note_id, title) VALUES ('fix033-note', 'counted')"
        )
        platform_db.commit()
        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)

        populated = client.get("/api/data-center/stats/overview").get_json()
        xhs = next(item for item in populated["platforms"] if item["platform_id"] == "xiaohongshu")
        assert populated["ok"] is False
        assert not any(error["platform_id"] == "xiaohongshu" for error in populated["errors"])
        assert all(error["error"] == "raw_tables_unavailable" for error in populated["errors"])
        assert xhs["table_counts"]["xhs_notes"] == 1
        assert xhs["total_records"] == 1

        platform_db.execute("DELETE FROM xhs_notes WHERE note_id='fix033-note'")
        platform_db.commit()
        empty = client.get("/api/data-center/stats/overview").get_json()
        xhs = next(item for item in empty["platforms"] if item["platform_id"] == "xiaohongshu")
        assert empty["ok"] is False
        assert not any(error["platform_id"] == "xiaohongshu" for error in empty["errors"])
        assert all(error["error"] == "raw_tables_unavailable" for error in empty["errors"])
        assert xhs["table_counts"]["xhs_notes"] == 0
        assert xhs["total_records"] == 0

    def test_fix033_query_failure_is_unavailable_and_preserves_error_field(self, platform_db, monkeypatch):
        """FIX-033: a failed count cannot masquerade as zero or erase its error."""
        import data_center_api

        platform_db.execute(
            "UPDATE platform_registry SET raw_tables=? WHERE platform_id='xiaohongshu'",
            (json.dumps(["xhs_notes"]),),
        )
        platform_db.commit()
        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)

        class FailingCountConnection:
            def __init__(self, wrapped):
                self.wrapped = wrapped

            def execute(self, sql, parameters=()):
                if sql == "SELECT COUNT(*) FROM xhs_notes":
                    raise sqlite3.OperationalError("synthetic FIX-033 query failure")
                return self.wrapped.execute(sql, parameters)

            def close(self):
                self.wrapped.close()

        def connect_with_one_synthetic_failure():
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            return FailingCountConnection(conn)

        monkeypatch.setattr(data_center_api, "_get_db", connect_with_one_synthetic_failure)
        overview = client.get("/api/data-center/stats/overview")
        assert overview.status_code == 200
        payload = overview.get_json()
        xhs = next(item for item in payload["platforms"] if item["platform_id"] == "xiaohongshu")
        assert payload["ok"] is False
        assert payload["total_records"] is None
        assert {error["platform_id"] for error in payload["errors"] if error["error"] == "raw_tables_unavailable"}
        assert {error["platform_id"] for error in payload["errors"] if error["error"] == "query_failed"} == {"xiaohongshu"}
        assert next(error for error in payload["errors"] if error["platform_id"] == "xiaohongshu") == {
            "platform_id": "xiaohongshu", "table": "xhs_notes", "error": "query_failed"
        }
        assert xhs["table_counts"]["xhs_notes"] is None
        assert xhs["table_errors"]["xhs_notes"] == "query_failed"
        assert xhs["total_records"] is None

        detail = client.get("/api/data-center/platform/xiaohongshu")
        assert detail.status_code == 200
        table_stats = detail.get_json()["platform"]["table_stats"]
        assert table_stats == [{"table": "xhs_notes", "count": None, "error": "query_failed"}]

    @pytest.mark.parametrize("raw_tables", ["[]", '["not_in_allowlist"]'])
    def test_fix033_uncountable_raw_table_catalog_is_unavailable_not_zero(
            self, platform_db, monkeypatch, raw_tables):
        platform_db.execute(
            "UPDATE platform_registry SET raw_tables=? WHERE platform_id='xiaohongshu'",
            (raw_tables,),
        )
        platform_db.commit()
        path = platform_db.execute("PRAGMA database_list").fetchone()[2]
        client = _data_center_client(monkeypatch, path)

        response = client.get("/api/data-center/stats/overview")
        payload = response.get_json()
        xhs = next(item for item in payload["platforms"] if item["platform_id"] == "xiaohongshu")

        assert response.status_code == 200
        assert payload["ok"] is False
        assert payload["total_records"] is None
        xhs_error = next(error for error in payload["errors"] if error["platform_id"] == "xiaohongshu")
        assert xhs_error == {
            "platform_id": "xiaohongshu", "table": None,
            "error": "raw_tables_unavailable",
        }
        assert xhs["table_counts"] == {}
        assert xhs["table_errors"]["_catalog"] == "raw_tables_unavailable"
        assert xhs["total_records"] is None


class TestEngagement:
    def test_engagement_sum(self):
        assert calculate_engagement(10, 5, 3, 2) == 20

    def test_engagement_partial_none(self):
        assert calculate_engagement(10, None, 3, None) == 13

    def test_engagement_all_none_returns_none(self):
        assert calculate_engagement(None, None, None, None) is None

    def test_engagement_not_zero_filled(self):
        """缺失值不返回0。"""
        assert calculate_engagement(None, None, None, 5) == 5

    def test_engagement_rate(self):
        assert calculate_engagement_rate(100, 1000) == 0.1

    def test_engagement_rate_zero_followers(self):
        assert calculate_engagement_rate(100, 0) is None
        assert calculate_engagement_rate(100, None) is None

    def test_engagement_from_normalized(self):
        from lumenis.system.collector.adapters.platform_naming import engagement_from_normalized
        record = {"like_count": 10, "collect_count": 5, "comment_count": 3, "share_count": 2}
        assert engagement_from_normalized(record) == 20


# ============================================================
# 7. 生产红线测试
# ============================================================
class TestProductionRedLines:
    def test_subject_words_not_modified(self):
        """SUBJECT_WORDS必须仍然存在且非空。"""
        from subject_rules import SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS, subject_hit
        assert SUBJECT_WORDS is not None
        assert len(SUBJECT_WORDS) > 0
        assert SUBJECT_EXCLUDE_WORDS is not None
        assert callable(subject_hit)

    def test_no_api_keys_in_source(self):
        """检查关键源码文件不含硬编码API Key。"""
        import re
        key_pattern = re.compile(r'(sk-|api_key\s*=\s*["\'][A-Za-z0-9]{20,})', re.IGNORECASE)
        files_to_check = [
            "lumenis/system/collector/adapters/platform_naming.py",
            "lumenis/system/collector/adapters/channels.py",
            "lumenis/system/collector/adapters/youtube.py",
            "lumenis/system/collector/adapters/github.py",
            "data_center_api.py",
        ]
        for f in files_to_check:
            filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), f)
            if os.path.exists(filepath):
                content = open(filepath, encoding="utf-8").read()
                assert not key_pattern.search(content), f"API key found in {f}"

    def test_fixture_uses_temporary_database(self, platform_db, tmp_path):
        db_path = Path(platform_db.execute("PRAGMA database_list").fetchone()[2]).resolve()
        assert db_path.parent == tmp_path.resolve()
        assert db_path.name == "platform-schema.db"

    def test_raw_table_field_naming_compliance(self, platform_db):
        """Verify raw tables preserve the native platform field names."""
        xhs_cols = {r[1] for r in platform_db.execute("PRAGMA table_info(xhs_notes)").fetchall()}
        assert "liked_count" in xhs_cols
        dy_cols = {r[1] for r in platform_db.execute("PRAGMA table_info(douyin_videos)").fetchall()}
        assert "digg_count" in dy_cols
        bl_cols = {r[1] for r in platform_db.execute("PRAGMA table_info(bilibili_videos)").fetchall()}
        assert "view" in bl_cols
        assert "favorite" in bl_cols

    def test_get_raw_table_returns_correct_names(self):
        assert get_raw_table("xiaohongshu", "content") == "xhs_notes"
        assert get_raw_table("douyin", "content") == "douyin_videos"
        assert get_raw_table("bilibili", "comment") == "bilibili_comments"
        assert get_raw_table("youtube", "user") == "youtube_channels"
        assert get_raw_table("github", "content") == "github_repositories"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))


class TestCurrentManifestDiscovery:
    def test_fresh_process_discovers_adapters_without_network_or_db(self):
        import subprocess
        code = """
import socket, sqlite3
from unittest.mock import patch
with patch.object(socket.socket, 'connect', side_effect=AssertionError('network at startup')), patch.object(sqlite3, 'connect', side_effect=AssertionError('database at startup')):
    from lumenis.system.collector.adapters.registry import get_adapter, list_adapters
    from lumenis.system.collector.adapters.config import PLATFORM_CAPABILITIES
    assert {k for k,c in PLATFORM_CAPABILITIES.items() if c['adapter_module']} <= set(list_adapters())
    for key in ('channels','youtube','tiktok','reddit','linkedin'):
        adapter = get_adapter(key)
        assert adapter.enabled is False
        assert adapter.healthcheck().status.value == 'NOT_CONFIGURED'
        assert adapter.healthcheck().ok is False
        for method in ('search','detail','comments','author','author_posts'):
            result = getattr(adapter, method)('isolated')
            assert result.status.value == 'NOT_SUPPORTED', (key, method, result)
            assert result.ok is False and not result.items
            assert adapter.capability_map()[method] == 'not_supported'
    assert get_adapter('yt').platform == 'youtube'
    assert get_adapter('wechat_channels').platform == 'channels'
    assert get_adapter('微信公众号').platform == 'wechat'
"""
        result = subprocess.run([sys.executable, '-B', '-c', code],
                                cwd=Path(__file__).resolve().parents[1],
                                text=True, capture_output=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr

    def test_full_catalog_projects_manifest_and_aliases(self):
        from lumenis.system.collector.adapters.config import PLATFORM_CAPABILITIES, get_platform_capabilities
        from lumenis.system.collector.adapters.registry import capability_matrix
        catalog = {item['platform_id']: item for item in get_platform_registry_catalog()}
        assert set(catalog) == {c['canonical_id'] for c in PLATFORM_CAPABILITIES.values()}
        planned = {'channels','youtube','tiktok','reddit','linkedin'}
        for key, cap in PLATFORM_CAPABILITIES.items():
            row = catalog[cap['canonical_id']]
            assert row['adapter_module'] == cap['adapter_module']
            assert row['status'] == cap['catalog_status']
            assert row['has_real_data'] is None
            if key in planned:
                assert row['status'] == 'PLANNED'
                assert row['has_collector'] == row['has_api_routes'] == 0
                assert cap['enabled'] is cap['manual_collection_enabled'] is False
        assert get_platform_capabilities('yt')['canonical_id'] == 'youtube'
        original = list(PLATFORM_CAPABILITIES['youtube']['raw_tables'])
        capability_matrix()['youtube']['raw_tables'].append('not-real')
        get_platform_capabilities('yt')['raw_tables'].append('not-real-either')
        assert PLATFORM_CAPABILITIES['youtube']['raw_tables'] == original
