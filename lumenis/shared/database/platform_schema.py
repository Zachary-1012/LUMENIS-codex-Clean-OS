# -*- coding: utf-8 -*-
"""Platform data-center schema owned by the Shared Database migration engine.

This module provides schema declarations and a connection-scoped, additive
migration operation. The versioned migration runner is the only production
entry point; this module never selects or opens a database path.
"""
from __future__ import annotations

import json
import re
import sqlite3
from typing import Dict, List, Tuple

# ============================================================
# 1. Platform Raw 层 — 12平台原生表
# ============================================================

RAW_TABLES_SQL: List[str] = [
    # ---- 小红书 XHS ----
    """CREATE TABLE IF NOT EXISTS xhs_notes (
        note_id TEXT PRIMARY KEY,
        title TEXT,
        desc TEXT,
        type TEXT,
        user_id TEXT,
        nickname TEXT,
        avatar TEXT,
        liked_count INTEGER,
        collected_count INTEGER,
        comment_count INTEGER,
        share_count INTEGER,
        time INTEGER,
        url TEXT,
        tag_list TEXT,
        image_list TEXT,
        video TEXT,
        source_keyword TEXT,
        xsec_token TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS xhs_note_comments (
        comment_id TEXT PRIMARY KEY,
        note_id TEXT,
        user_id TEXT,
        nickname TEXT,
        content TEXT,
        like_count INTEGER,
        sub_comment_count INTEGER,
        time INTEGER,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS xhs_users (
        user_id TEXT PRIMARY KEY,
        nickname TEXT,
        avatar TEXT,
        desc TEXT,
        fans INTEGER,
        following INTEGER,
        interaction TEXT,
        gender INTEGER,
        collected_at TEXT
    )""",

    # ---- 抖音 Douyin ----
    """CREATE TABLE IF NOT EXISTS douyin_videos (
        aweme_id TEXT PRIMARY KEY,
        desc TEXT,
        author_id TEXT,
        author_uid TEXT,
        create_time INTEGER,
        digg_count INTEGER,
        comment_count INTEGER,
        share_count INTEGER,
        collect_count INTEGER,
        play_count INTEGER,
        download_count INTEGER,
        music_id TEXT,
        hashtag_list TEXT,
        location TEXT,
        duration INTEGER,
        url TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS douyin_comments (
        comment_id TEXT PRIMARY KEY,
        aweme_id TEXT,
        user_id TEXT,
        nickname TEXT,
        content TEXT,
        digg_count INTEGER,
        reply_count INTEGER,
        create_time INTEGER,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS douyin_users (
        sec_uid TEXT PRIMARY KEY,
        uid TEXT,
        nickname TEXT,
        avatar TEXT,
        signature TEXT,
        follower_count INTEGER,
        following_count INTEGER,
        total_favorited INTEGER,
        collected_at TEXT
    )""",

    # ---- B站 Bilibili ----
    """CREATE TABLE IF NOT EXISTS bilibili_videos (
        bvid TEXT PRIMARY KEY,
        aid INTEGER,
        title TEXT,
        owner_mid TEXT,
        owner_name TEXT,
        pubdate INTEGER,
        duration INTEGER,
        view INTEGER,
        like INTEGER,
        coin INTEGER,
        favorite INTEGER,
        share INTEGER,
        reply INTEGER,
        danmaku INTEGER,
        tid INTEGER,
        tname TEXT,
        url TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS bilibili_comments (
        rpid TEXT PRIMARY KEY,
        oid TEXT,
        mid TEXT,
        username TEXT,
        content TEXT,
        like INTEGER,
        rcount INTEGER,
        ctime INTEGER,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS bilibili_users (
        mid TEXT PRIMARY KEY,
        name TEXT,
        avatar TEXT,
        sign TEXT,
        level INTEGER,
        follower INTEGER,
        following INTEGER,
        collected_at TEXT
    )""",

    # ---- 视频号 Channels ----
    """CREATE TABLE IF NOT EXISTS channels_videos (
        object_id TEXT PRIMARY KEY,
        desc TEXT,
        author_id TEXT,
        author_name TEXT,
        create_time INTEGER,
        like_count INTEGER,
        comment_count TEXT,
        share_count TEXT,
        collect_count TEXT,
        view_count TEXT,
        duration INTEGER,
        url TEXT,
        location TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS channels_comments (
        comment_id TEXT PRIMARY KEY,
        object_id TEXT,
        author_id TEXT,
        author_name TEXT,
        content TEXT,
        like_count INTEGER,
        create_time INTEGER,
        collected_at TEXT
    )""",

    # ---- YouTube ----
    """CREATE TABLE IF NOT EXISTS youtube_videos (
        video_id TEXT PRIMARY KEY,
        channel_id TEXT,
        title TEXT,
        description TEXT,
        view_count INTEGER,
        like_count INTEGER,
        favorite_count INTEGER,
        comment_count INTEGER,
        duration TEXT,
        category_id TEXT,
        tags TEXT,
        live_broadcast_content TEXT,
        default_language TEXT,
        published_at TEXT,
        url TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS youtube_comments (
        comment_id TEXT PRIMARY KEY,
        video_id TEXT,
        author_channel_id TEXT,
        author_display_name TEXT,
        text_display TEXT,
        text_original TEXT,
        like_count INTEGER,
        reply_count INTEGER,
        published_at TEXT,
        updated_at TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS youtube_channels (
        channel_id TEXT PRIMARY KEY,
        title TEXT,
        description TEXT,
        custom_url TEXT,
        subscriber_count INTEGER,
        video_count INTEGER,
        view_count INTEGER,
        country TEXT,
        published_at TEXT,
        collected_at TEXT
    )""",

    # ---- TikTok ----
    """CREATE TABLE IF NOT EXISTS tiktok_videos (
        video_id TEXT PRIMARY KEY,
        author_username TEXT,
        author_id TEXT,
        desc TEXT,
        create_time INTEGER,
        digg_count INTEGER,
        comment_count INTEGER,
        share_count INTEGER,
        play_count INTEGER,
        collect_count INTEGER,
        music_id TEXT,
        hashtag_list TEXT,
        duration INTEGER,
        url TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS tiktok_comments (
        comment_id TEXT PRIMARY KEY,
        video_id TEXT,
        user_id TEXT,
        username TEXT,
        text TEXT,
        like_count INTEGER,
        reply_count INTEGER,
        create_time INTEGER,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS tiktok_users (
        user_id TEXT PRIMARY KEY,
        username TEXT,
        nickname TEXT,
        avatar TEXT,
        signature TEXT,
        follower_count INTEGER,
        following_count INTEGER,
        total_favorited INTEGER,
        collected_at TEXT
    )""",

    # ---- Instagram ----
    """CREATE TABLE IF NOT EXISTS instagram_media (
        media_id TEXT PRIMARY KEY,
        media_type TEXT,
        shortcode TEXT,
        permalink TEXT,
        caption TEXT,
        author_username TEXT,
        author_id TEXT,
        children TEXT,
        location TEXT,
        hashtags TEXT,
        mentions TEXT,
        collaboration TEXT,
        like_count INTEGER,
        comment_count INTEGER,
        taken_at INTEGER,
        url TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS instagram_comments (
        comment_id TEXT PRIMARY KEY,
        media_id TEXT,
        user_id TEXT,
        username TEXT,
        text TEXT,
        like_count INTEGER,
        parent_comment_id TEXT,
        created_at INTEGER,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS instagram_users (
        user_id TEXT PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        avatar TEXT,
        biography TEXT,
        is_business_account INTEGER,
        category TEXT,
        follower_count INTEGER,
        following_count INTEGER,
        media_count INTEGER,
        collected_at TEXT
    )""",

    # ---- X/Twitter ----
    """CREATE TABLE IF NOT EXISTS x_posts (
        tweet_id TEXT PRIMARY KEY,
        conversation_id TEXT,
        author_id TEXT,
        author_username TEXT,
        text TEXT,
        in_reply_to_user_id TEXT,
        retweet_count INTEGER,
        reply_count INTEGER,
        like_count INTEGER,
        quote_count INTEGER,
        bookmark_count INTEGER,
        impression_count INTEGER,
        context_annotations TEXT,
        referenced_tweets TEXT,
        hashtag_list TEXT,
        mention_list TEXT,
        created_at TEXT,
        url TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS x_users (
        user_id TEXT PRIMARY KEY,
        username TEXT,
        name TEXT,
        description TEXT,
        avatar TEXT,
        verified INTEGER,
        verified_type TEXT,
        follower_count INTEGER,
        following_count INTEGER,
        tweet_count INTEGER,
        listed_count INTEGER,
        location TEXT,
        created_at TEXT,
        collected_at TEXT
    )""",

    # ---- Reddit ----
    """CREATE TABLE IF NOT EXISTS reddit_posts (
        post_id TEXT PRIMARY KEY,
        subreddit TEXT,
        subreddit_id TEXT,
        author TEXT,
        author_fullname TEXT,
        title TEXT,
        selftext TEXT,
        url TEXT,
        permalink TEXT,
        score INTEGER,
        upvote_ratio REAL,
        num_comments INTEGER,
        num_crossposts INTEGER,
        link_flair_text TEXT,
        over_18 INTEGER,
        spoiler INTEGER,
        stickied INTEGER,
        created_utc REAL,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS reddit_comments (
        comment_id TEXT PRIMARY KEY,
        post_id TEXT,
        subreddit TEXT,
        author TEXT,
        body TEXT,
        score INTEGER,
        depth INTEGER,
        parent_comment_id TEXT,
        created_utc REAL,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS reddit_subreddits (
        subreddit_id TEXT PRIMARY KEY,
        name TEXT,
        display_name TEXT,
        description TEXT,
        subscriber_count INTEGER,
        active_user_count INTEGER,
        created_utc REAL,
        collected_at TEXT
    )""",

    # ---- LinkedIn ----
    """CREATE TABLE IF NOT EXISTS linkedin_posts (
        post_id TEXT PRIMARY KEY,
        author_id TEXT,
        author_name TEXT,
        commentary TEXT,
        article_url TEXT,
        image_url TEXT,
        like_count INTEGER,
        comment_count INTEGER,
        share_count INTEGER,
        impression_count INTEGER,
        created_at TEXT,
        url TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS linkedin_users (
        profile_id TEXT PRIMARY KEY,
        vanity_name TEXT,
        first_name TEXT,
        last_name TEXT,
        headline TEXT,
        summary TEXT,
        avatar TEXT,
        industry TEXT,
        company TEXT,
        job_title TEXT,
        follower_count INTEGER,
        connection_count INTEGER,
        location TEXT,
        collected_at TEXT
    )""",

    # ---- GitHub ----
    """CREATE TABLE IF NOT EXISTS github_repositories (
        repo_id INTEGER PRIMARY KEY,
        name TEXT,
        full_name TEXT,
        owner TEXT,
        owner_id INTEGER,
        description TEXT,
        language TEXT,
        stargazers_count INTEGER,
        forks_count INTEGER,
        watchers_count INTEGER,
        open_issues_count INTEGER,
        subscribers_count INTEGER,
        topics TEXT,
        license TEXT,
        default_branch TEXT,
        homepage TEXT,
        is_fork INTEGER,
        is_archived INTEGER,
        created_at TEXT,
        updated_at TEXT,
        pushed_at TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS github_issues (
        issue_id INTEGER PRIMARY KEY,
        issue_number INTEGER,
        repo_full_name TEXT,
        title TEXT,
        body TEXT,
        state TEXT,
        author TEXT,
        labels TEXT,
        assignees TEXT,
        comments_count INTEGER,
        is_pull_request INTEGER,
        created_at TEXT,
        updated_at TEXT,
        closed_at TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS github_pull_requests (
        pr_id INTEGER PRIMARY KEY,
        pr_number INTEGER,
        repo_full_name TEXT,
        title TEXT,
        body TEXT,
        state TEXT,
        author TEXT,
        head_branch TEXT,
        base_branch TEXT,
        commits_count INTEGER,
        additions INTEGER,
        deletions INTEGER,
        changed_files INTEGER,
        comments_count INTEGER,
        review_comments_count INTEGER,
        labels TEXT,
        created_at TEXT,
        updated_at TEXT,
        closed_at TEXT,
        merged_at TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS github_releases (
        release_id INTEGER PRIMARY KEY,
        tag_name TEXT,
        name TEXT,
        body TEXT,
        repo_full_name TEXT,
        author TEXT,
        is_draft INTEGER,
        is_prerelease INTEGER,
        assets_count INTEGER,
        download_count INTEGER,
        created_at TEXT,
        published_at TEXT,
        collected_at TEXT
    )""",

    # ---- 知乎 Zhihu ----
    """CREATE TABLE IF NOT EXISTS zhihu_answers (
        answer_id TEXT PRIMARY KEY,
        question_id TEXT,
        question_title TEXT,
        author_id TEXT,
        author_name TEXT,
        content TEXT,
        excerpt TEXT,
        voteup_count INTEGER,
        thanks_count INTEGER,
        favlists_count INTEGER,
        comment_count INTEGER,
        is_collapsed INTEGER,
        created_time INTEGER,
        updated_time INTEGER,
        url TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS zhihu_questions (
        question_id TEXT PRIMARY KEY,
        title TEXT,
        detail TEXT,
        author_id TEXT,
        answer_count INTEGER,
        follower_count INTEGER,
        comment_count INTEGER,
        topics TEXT,
        created_time INTEGER,
        updated_time INTEGER,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS zhihu_articles (
        article_id TEXT PRIMARY KEY,
        title TEXT,
        content TEXT,
        excerpt TEXT,
        author_id TEXT,
        author_name TEXT,
        voteup_count INTEGER,
        comment_count INTEGER,
        created_time INTEGER,
        updated_time INTEGER,
        url TEXT,
        collected_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS zhihu_comments (
        comment_id TEXT PRIMARY KEY,
        resource_id TEXT,
        resource_type TEXT,
        author_id TEXT,
        author_name TEXT,
        content TEXT,
        vote_count INTEGER,
        reply_count INTEGER,
        parent_comment_id TEXT,
        created_time INTEGER,
        collected_at TEXT
    )""",
]

# ============================================================
# 2. Platform Normalized 层 — 跨平台统一表
# ============================================================

NORMALIZED_TABLES_SQL: List[str] = [
    """CREATE TABLE IF NOT EXISTS platform_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        platform_account_id TEXT NOT NULL,
        username TEXT,
        display_name TEXT,
        avatar_url TEXT,
        bio TEXT,
        verified INTEGER,
        verification_type TEXT,
        account_type TEXT,
        follower_count INTEGER,
        following_count INTEGER,
        content_count INTEGER,
        location TEXT,
        country TEXT,
        language TEXT,
        website TEXT,
        profile_url TEXT,
        first_seen_at TEXT,
        last_seen_at TEXT,
        raw_data TEXT,
        UNIQUE(platform, platform_account_id)
    )""",
    """CREATE TABLE IF NOT EXISTS platform_contents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        platform_content_id TEXT NOT NULL,
        content_type TEXT,
        author_id TEXT,
        author_name TEXT,
        title TEXT,
        content TEXT,
        published_at TEXT,
        url TEXT,
        like_count INTEGER,
        comment_count INTEGER,
        share_count INTEGER,
        collect_count INTEGER,
        view_count INTEGER,
        topic_list TEXT,
        hashtag_list TEXT,
        mention_list TEXT,
        media_list TEXT,
        language TEXT,
        location TEXT,
        raw_data TEXT,
        first_collected_at TEXT,
        last_collected_at TEXT,
        collected_at TEXT,
        UNIQUE(platform, platform_content_id)
    )""",
    """CREATE TABLE IF NOT EXISTS platform_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        comment_id TEXT NOT NULL,
        content_id TEXT,
        parent_comment_id TEXT,
        author_id TEXT,
        author_name TEXT,
        content TEXT,
        like_count INTEGER,
        reply_count INTEGER,
        created_at TEXT,
        updated_at TEXT,
        location TEXT,
        raw_data TEXT,
        collected_at TEXT,
        UNIQUE(platform, comment_id)
    )""",
]

# ============================================================
# 3. 采集与 Evidence 层
# ============================================================

EVIDENCE_TABLES_SQL: List[str] = [
    """CREATE TABLE IF NOT EXISTS collection_runs (
        collection_run_id TEXT PRIMARY KEY,
        platform TEXT,
        collector TEXT,
        collector_version TEXT,
        task_id TEXT,
        keyword TEXT,
        started_at TEXT,
        finished_at TEXT,
        status TEXT,
        requested_count INTEGER,
        collected_count INTEGER,
        new_count INTEGER,
        duplicate_count INTEGER,
        filtered_count INTEGER,
        error_count INTEGER,
        error_code TEXT,
        error_message TEXT,
        duration_ms INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS platform_evidence (
        evidence_id TEXT PRIMARY KEY,
        platform TEXT,
        content_id TEXT,
        source_url TEXT,
        source_type TEXT,
        captured_at TEXT,
        capture_method TEXT,
        raw_payload TEXT,
        screenshot TEXT,
        content_hash TEXT,
        collector_version TEXT,
        confidence REAL
    )""",
]

# ============================================================
# 4. 业务层 — 新建表（events已存在，只扩展字段）
# ============================================================

BUSINESS_TABLES_SQL: List[str] = [
    """CREATE TABLE IF NOT EXISTS brands (
        brand_id TEXT PRIMARY KEY,
        brand_name TEXT,
        brand_alias TEXT,
        category TEXT,
        industry TEXT,
        parent_brand_id TEXT,
        status TEXT,
        created_at TEXT,
        updated_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS content_analysis (
        analysis_id TEXT PRIMARY KEY,
        platform TEXT,
        content_id TEXT,
        sentiment TEXT,
        sentiment_score REAL,
        emotion TEXT,
        risk_level TEXT,
        risk_score REAL,
        topic TEXT,
        intent TEXT,
        brand_relevance REAL,
        event_relevance REAL,
        ai_model TEXT,
        prompt_version TEXT,
        confidence REAL,
        analyzed_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS creators (
        creator_id TEXT PRIMARY KEY,
        platform TEXT,
        platform_account_id TEXT,
        creator_type TEXT,
        display_name TEXT,
        followers INTEGER,
        engagement_rate REAL,
        content_count INTEGER,
        average_interaction REAL,
        influence_score REAL,
        brand_relevance REAL,
        category TEXT,
        location TEXT,
        verified INTEGER,
        first_seen_at TEXT,
        last_seen_at TEXT
    )""",
]

# ============================================================
# 5. 索引
# ============================================================

INDEX_SQL: List[str] = [
    "CREATE INDEX IF NOT EXISTS idx_platform_contents_platform ON platform_contents(platform)",
    "CREATE INDEX IF NOT EXISTS idx_platform_contents_published_at ON platform_contents(published_at)",
    "CREATE INDEX IF NOT EXISTS idx_platform_contents_author ON platform_contents(author_id)",
    "CREATE INDEX IF NOT EXISTS idx_platform_comments_content ON platform_comments(content_id)",
    "CREATE INDEX IF NOT EXISTS idx_platform_accounts_platform ON platform_accounts(platform)",
    "CREATE INDEX IF NOT EXISTS idx_collection_runs_platform ON collection_runs(platform)",
    "CREATE INDEX IF NOT EXISTS idx_collection_runs_status ON collection_runs(status)",
    "CREATE INDEX IF NOT EXISTS idx_platform_evidence_content ON platform_evidence(content_id)",
    "CREATE INDEX IF NOT EXISTS idx_content_analysis_platform ON content_analysis(platform, content_id)",
    "CREATE INDEX IF NOT EXISTS idx_creators_platform ON creators(platform)",
    "CREATE INDEX IF NOT EXISTS idx_xhs_notes_time ON xhs_notes(time)",
    "CREATE INDEX IF NOT EXISTS idx_douyin_videos_create_time ON douyin_videos(create_time)",
    "CREATE INDEX IF NOT EXISTS idx_bilibili_videos_pubdate ON bilibili_videos(pubdate)",
]

# ============================================================
# 6. events表现有字段扩展（向后兼容，只加字段）
# ============================================================

EVENTS_EXTENSION_COLUMNS = [
    ("event_type", "TEXT"),
    ("severity", "TEXT"),
    ("growth_rate", "REAL"),
    ("confidence", "REAL"),
]


PLATFORM_REGISTRY_SQL = """
CREATE TABLE IF NOT EXISTS platform_registry (
    platform_id TEXT PRIMARY KEY,
    platform_name TEXT NOT NULL,
    display_name TEXT,
    status TEXT NOT NULL DEFAULT 'PLANNED',
    ui_visible INTEGER NOT NULL DEFAULT 0,
    collector_endpoint TEXT,
    adapter_module TEXT,
    raw_tables TEXT,
    normalized_mapping TEXT,
    last_sync_at TEXT,
    data_quality_score REAL,
    has_collector INTEGER DEFAULT 0,
    has_api_routes INTEGER DEFAULT 0,
    has_real_data INTEGER,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
)
"""


def _table_name(sql: str) -> str:
    match = re.search(r"CREATE TABLE IF NOT EXISTS\s+(\w+)", sql, re.IGNORECASE)
    if not match:
        raise ValueError(f"Unsupported platform schema statement: {sql[:80]}")
    return match.group(1)


def _unique_column_groups(
    conn: sqlite3.Connection, table_name: str, schema: str = "main"
) -> set[Tuple[str, ...]]:
    groups: set[Tuple[str, ...]] = set()
    for index in conn.execute(f'PRAGMA {schema}.index_list("{table_name}")').fetchall():
        if not int(index[2]):
            continue
        columns = tuple(
            row[2] for row in conn.execute(
                f'PRAGMA {schema}.index_info("{index[1]}")'
            ).fetchall()
        )
        if columns and all(columns):
            groups.add(columns)
    return groups


def _expected_table_contracts(conn: sqlite3.Connection) -> Dict[str, dict]:
    """Compile declared DDL in temp schema for conflict validation."""
    table_sql = RAW_TABLES_SQL + NORMALIZED_TABLES_SQL + EVIDENCE_TABLES_SQL + BUSINESS_TABLES_SQL + [PLATFORM_REGISTRY_SQL]
    savepoint = "lumenis_platform_schema_contract_probe"
    conn.execute(f"SAVEPOINT {savepoint}")
    try:
        probe_names = {}
        contracts = {}
        for sql in table_sql:
            name = _table_name(sql)
            probe_name = f"__lumenis_schema_contract_{name}"
            temp_sql = re.sub(
                r"CREATE TABLE IF NOT EXISTS\s+\w+",
                f'CREATE TEMP TABLE IF NOT EXISTS "{probe_name}"',
                sql,
                count=1,
                flags=re.IGNORECASE,
            )
            conn.execute(temp_sql)
            probe_names[name] = probe_name
        for name, probe_name in probe_names.items():
            columns = {
                row[1]: (str(row[2] or "").upper(), int(row[3]), int(row[5]))
                for row in conn.execute(f'PRAGMA temp.table_info("{probe_name}")').fetchall()
            }
            contracts[name] = {
                "columns": columns,
                "unique_groups": _unique_column_groups(conn, probe_name, schema="temp"),
            }
        return contracts
    finally:
        conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
        conn.execute(f"RELEASE SAVEPOINT {savepoint}")


def _validate_table_contract(conn: sqlite3.Connection, table_name: str, expected: dict) -> None:
    actual_rows = conn.execute(f'PRAGMA main.table_info("{table_name}")').fetchall()
    actual = {
        row[1]: (str(row[2] or "").upper(), int(row[3]), int(row[5]))
        for row in actual_rows
    }
    missing = sorted(set(expected["columns"]) - set(actual))
    incompatible = sorted(
        name for name, spec in expected["columns"].items()
        if name in actual and actual[name] != spec
    )
    actual_unique = _unique_column_groups(conn, table_name, schema="main")
    missing_unique = sorted(expected["unique_groups"] - actual_unique)
    if missing or incompatible or missing_unique:
        raise sqlite3.DatabaseError(
            f"Conflicting existing table schema for {table_name}: "
            f"missing_columns={missing}, incompatible_columns={incompatible}, "
            f"missing_unique_constraints={missing_unique}"
        )


def _catalog_rows() -> List[dict]:
    """Load static platform metadata from the SYSTEM Collector catalog owner."""
    from lumenis.system.collector.adapters.platform_naming import get_platform_registry_catalog

    rows = get_platform_registry_catalog()
    if len({row["platform_id"] for row in rows}) != len(rows):
        raise ValueError("SYSTEM Collector catalog contains duplicate platform IDs")
    for row in rows:
        if not row.get("platform_id") or not row.get("platform_name"):
            raise ValueError("SYSTEM Collector catalog has an empty platform identity")
        if row.get("has_real_data") is not None:
            raise ValueError("SYSTEM Collector catalog must not assert runtime data presence")
        row["raw_tables"] = json.dumps(row.get("raw_tables") or [], ensure_ascii=False, separators=(",", ":"))
        row["normalized_mapping"] = json.dumps(
            row.get("normalized_mapping") or {}, ensure_ascii=False, separators=(",", ":")
        )
    return rows


def apply_platform_schema(conn: sqlite3.Connection) -> dict:
    """Create/validate platform data-center schema and synchronize static catalog metadata.

    Existing table data and runtime-owned registry fields are preserved. Any
    conflicting table structure aborts the savepoint so partial DDL cannot be
    committed by the versioned migration runner.
    """
    result = {
        "raw_tables": len(RAW_TABLES_SQL),
        "normalized_tables": len(NORMALIZED_TABLES_SQL),
        "evidence_tables": len(EVIDENCE_TABLES_SQL),
        "business_tables": len(BUSINESS_TABLES_SQL),
        "registry_table": 1,
        "indexes": len(INDEX_SQL),
        "events_columns_added": 0,
        "catalog_inserted": 0,
        "catalog_updated": 0,
    }
    contracts = _expected_table_contracts(conn)
    statements = RAW_TABLES_SQL + NORMALIZED_TABLES_SQL + EVIDENCE_TABLES_SQL + BUSINESS_TABLES_SQL + [PLATFORM_REGISTRY_SQL]
    savepoint = "lumenis_platform_schema_v13"
    conn.execute(f"SAVEPOINT {savepoint}")
    try:
        events = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='events'"
        ).fetchone()
        if events is None:
            raise sqlite3.DatabaseError("Schema v13 requires the existing Shared Database events table")

        for sql in statements:
            conn.execute(sql)
        for sql in INDEX_SQL:
            conn.execute(sql)

        event_columns = {
            row[1]: str(row[2] or "").upper()
            for row in conn.execute("PRAGMA table_info(events)").fetchall()
        }
        for name, type_name in EVENTS_EXTENSION_COLUMNS:
            existing_type = event_columns.get(name)
            if existing_type is None:
                conn.execute(f"ALTER TABLE events ADD COLUMN {name} {type_name}")
                result["events_columns_added"] += 1
            elif existing_type != type_name.upper():
                raise sqlite3.DatabaseError(
                    f"Conflicting existing events.{name} type: {existing_type}, expected {type_name.upper()}"
                )

        for table_name, contract in contracts.items():
            _validate_table_contract(conn, table_name, contract)

        catalog = _catalog_rows()
        static_columns = (
            "platform_name", "display_name", "adapter_module", "raw_tables",
            "normalized_mapping", "has_collector", "has_api_routes", "notes",
        )
        for row in catalog:
            existing = conn.execute(
                "SELECT 1 FROM platform_registry WHERE platform_id=?", (row["platform_id"],)
            ).fetchone()
            if existing:
                assignments = ", ".join(f"{column}=?" for column in static_columns)
                conn.execute(
                    f"UPDATE platform_registry SET {assignments}, updated_at=datetime('now') WHERE platform_id=?",
                    tuple(row[column] for column in static_columns) + (row["platform_id"],),
                )
                result["catalog_updated"] += 1
            else:
                conn.execute(
                    """INSERT INTO platform_registry
                    (platform_id, platform_name, display_name, status, ui_visible,
                     adapter_module, raw_tables, normalized_mapping, has_collector,
                     has_api_routes, has_real_data, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)""",
                    (
                        row["platform_id"], row["platform_name"], row["display_name"],
                        row["status"], row["ui_visible"], row["adapter_module"],
                        row["raw_tables"], row["normalized_mapping"], row["has_collector"],
                        row["has_api_routes"], row["notes"],
                    ),
                )
                result["catalog_inserted"] += 1

        conn.execute(f"RELEASE SAVEPOINT {savepoint}")
        return result
    except Exception:
        conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
        conn.execute(f"RELEASE SAVEPOINT {savepoint}")
        raise
