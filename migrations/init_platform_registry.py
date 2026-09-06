# -*- coding: utf-8 -*-
"""platform_registry 表创建与12平台初始化数据。

platform_registry 是平台接入状态的单一真值源，控制前端显示与采集调度。
"""
from __future__ import annotations

import json
import os
import sqlite3
from typing import Dict, List

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "monitor.db")

CREATE_TABLE_SQL = """
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
    has_real_data INTEGER DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
)
"""

# 12平台初始注册数据（与 platform_naming.PLATFORM_CONNECTION 一致）
PLATFORM_INITIAL_DATA: List[Dict] = [
    {
        "platform_id": "xiaohongshu", "platform_name": "xiaohongshu", "display_name": "小红书",
        "status": "ACTIVE", "ui_visible": 1,
        "adapter_module": "platform_adapters.xhs",
        "raw_tables": json.dumps(["xhs_notes", "xhs_note_comments", "xhs_users"]),
        "normalized_mapping": json.dumps({"content_id": "note_id", "like_count": "liked_count", "collect_count": "collected_count"}),
        "has_collector": 1, "has_api_routes": 1, "has_real_data": 1,
        "notes": "主力采集平台，Playwright/CDP完整链路，963+条真实数据",
    },
    {
        "platform_id": "douyin", "platform_name": "douyin", "display_name": "抖音",
        "status": "PARTIAL", "ui_visible": 1,
        "adapter_module": "platform_adapters.douyin",
        "raw_tables": json.dumps(["douyin_videos", "douyin_comments", "douyin_users"]),
        "normalized_mapping": json.dumps({"content_id": "aweme_id", "like_count": "digg_count", "view_count": "play_count"}),
        "has_collector": 0, "has_api_routes": 0, "has_real_data": 0,
        "notes": "有Adapter骨架引用v4引擎，enabled=False，无运行中采集管道",
    },
    {
        "platform_id": "bilibili", "platform_name": "bilibili", "display_name": "B站",
        "status": "PARTIAL", "ui_visible": 1,
        "adapter_module": "platform_adapters.bilibili",
        "raw_tables": json.dumps(["bilibili_videos", "bilibili_comments", "bilibili_users"]),
        "normalized_mapping": json.dumps({"content_id": "bvid", "like_count": "like", "collect_count": "favorite", "view_count": "view"}),
        "has_collector": 0, "has_api_routes": 1, "has_real_data": 0,
        "notes": "有登录管理+搜索API，但搜索结果未入库，无完整采集管道",
    },
    {
        "platform_id": "channels", "platform_name": "channels", "display_name": "视频号",
        "status": "PLANNED", "ui_visible": 0,
        "adapter_module": "platform_adapters.channels",
        "raw_tables": json.dumps(["channels_videos", "channels_comments"]),
        "normalized_mapping": json.dumps({"content_id": "object_id"}),
        "has_collector": 0, "has_api_routes": 0, "has_real_data": 0,
        "notes": "视频号无公开API，需微信生态特殊入口，部分字段unavailable",
    },
    {
        "platform_id": "youtube", "platform_name": "youtube", "display_name": "YouTube",
        "status": "PLANNED", "ui_visible": 0,
        "adapter_module": "platform_adapters.youtube",
        "raw_tables": json.dumps(["youtube_videos", "youtube_comments", "youtube_channels"]),
        "normalized_mapping": json.dumps({"content_id": "video_id", "author_id": "channel_id", "view_count": "view_count"}),
        "has_collector": 0, "has_api_routes": 0, "has_real_data": 0,
        "notes": "有Data API v3可接入，待配置API Key",
    },
    {
        "platform_id": "tiktok", "platform_name": "tiktok", "display_name": "TikTok",
        "status": "PLANNED", "ui_visible": 0,
        "adapter_module": "platform_adapters.tiktok",
        "raw_tables": json.dumps(["tiktok_videos", "tiktok_comments", "tiktok_users"]),
        "normalized_mapping": json.dumps({"content_id": "video_id", "like_count": "digg_count", "view_count": "play_count"}),
        "has_collector": 0, "has_api_routes": 0, "has_real_data": 0,
        "notes": "待接入采集端口",
    },
    {
        "platform_id": "instagram", "platform_name": "instagram", "display_name": "Instagram",
        "status": "PLANNED", "ui_visible": 0,
        "adapter_module": "platform_adapters.instagram",
        "raw_tables": json.dumps(["instagram_media", "instagram_comments", "instagram_users"]),
        "normalized_mapping": json.dumps({"content_id": "media_id", "content_type": "media_type"}),
        "has_collector": 0, "has_api_routes": 0, "has_real_data": 0,
        "notes": "有较完整Adapter骨架(235行)，但无运行中采集",
    },
    {
        "platform_id": "x", "platform_name": "x", "display_name": "X/Twitter",
        "status": "PLANNED", "ui_visible": 0,
        "adapter_module": "platform_adapters.x_platform",
        "raw_tables": json.dumps(["x_posts", "x_users"]),
        "normalized_mapping": json.dumps({"content_id": "tweet_id", "share_count": "retweet_count", "comment_count": "reply_count", "view_count": "impression_count"}),
        "has_collector": 0, "has_api_routes": 0, "has_real_data": 0,
        "notes": "有Adapter骨架(95行)，待接入API",
    },
    {
        "platform_id": "reddit", "platform_name": "reddit", "display_name": "Reddit",
        "status": "PLANNED", "ui_visible": 0,
        "adapter_module": "platform_adapters.reddit",
        "raw_tables": json.dumps(["reddit_posts", "reddit_comments", "reddit_subreddits"]),
        "normalized_mapping": json.dumps({"content_id": "post_id", "like_count": "score", "comment_count": "num_comments", "share_count": "num_crossposts"}),
        "has_collector": 0, "has_api_routes": 0, "has_real_data": 0,
        "notes": "有公开API，待接入",
    },
    {
        "platform_id": "linkedin", "platform_name": "linkedin", "display_name": "LinkedIn",
        "status": "PLANNED", "ui_visible": 0,
        "adapter_module": "platform_adapters.linkedin",
        "raw_tables": json.dumps(["linkedin_posts", "linkedin_users"]),
        "normalized_mapping": json.dumps({"content_id": "post_id", "view_count": "impression_count"}),
        "has_collector": 0, "has_api_routes": 0, "has_real_data": 0,
        "notes": "需官方API权限，待接入",
    },
    {
        "platform_id": "github", "platform_name": "github", "display_name": "GitHub",
        "status": "PLANNED", "ui_visible": 0,
        "adapter_module": "platform_adapters.github",
        "raw_tables": json.dumps(["github_repositories", "github_issues", "github_pull_requests", "github_releases"]),
        "normalized_mapping": json.dumps({"content_id": "repo_id", "like_count": "stargazers_count", "share_count": "forks_count", "view_count": "watchers_count"}),
        "has_collector": 0, "has_api_routes": 0, "has_real_data": 0,
        "notes": "有REST API v3可接入，按原生对象模型分4表",
    },
    {
        "platform_id": "zhihu", "platform_name": "zhihu", "display_name": "知乎",
        "status": "PLANNED", "ui_visible": 0,
        "adapter_module": "platform_adapters.zhihu",
        "raw_tables": json.dumps(["zhihu_answers", "zhihu_questions", "zhihu_articles", "zhihu_comments"]),
        "normalized_mapping": json.dumps({"content_id": "answer_id", "like_count": "voteup_count", "collect_count": "favlists_count"}),
        "has_collector": 0, "has_api_routes": 0, "has_real_data": 0,
        "notes": "有Adapter骨架(124行)，待接入",
    },
]


def init_platform_registry(db_path: str = DB_PATH) -> dict:
    """创建 platform_registry 表并初始化12平台数据。"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    result = {"table_created": False, "inserted": 0, "updated": 0, "skipped": 0, "errors": []}

    try:
        cursor.execute(CREATE_TABLE_SQL)
        result["table_created"] = True

        for p in PLATFORM_INITIAL_DATA:
            try:
                # 检查是否已存在
                existing = cursor.execute(
                    "SELECT platform_id FROM platform_registry WHERE platform_id = ?",
                    (p["platform_id"],)
                ).fetchone()
                if existing:
                    # 更新状态字段（保留last_sync_at等运行时字段）
                    cursor.execute("""
                        UPDATE platform_registry SET
                            status=?, ui_visible=?, adapter_module=?, raw_tables=?,
                            normalized_mapping=?, has_collector=?, has_api_routes=?,
                            has_real_data=?, notes=?, updated_at=datetime('now')
                        WHERE platform_id=?
                    """, (
                        p["status"], p["ui_visible"], p["adapter_module"], p["raw_tables"],
                        p["normalized_mapping"], p["has_collector"], p["has_api_routes"],
                        p["has_real_data"], p["notes"], p["platform_id"]
                    ))
                    result["updated"] += 1
                else:
                    cursor.execute("""
                        INSERT INTO platform_registry
                        (platform_id, platform_name, display_name, status, ui_visible,
                         adapter_module, raw_tables, normalized_mapping,
                         has_collector, has_api_routes, has_real_data, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p["platform_id"], p["platform_name"], p["display_name"],
                        p["status"], p["ui_visible"], p["adapter_module"],
                        p["raw_tables"], p["normalized_mapping"],
                        p["has_collector"], p["has_api_routes"], p["has_real_data"], p["notes"]
                    ))
                    result["inserted"] += 1
            except Exception as e:
                result["errors"].append(f"{p['platform_id']}: {str(e)[:100]}")

        conn.commit()

        # 验证
        total = cursor.execute("SELECT COUNT(*) FROM platform_registry").fetchone()[0]
        ui_visible = cursor.execute("SELECT COUNT(*) FROM platform_registry WHERE ui_visible=1").fetchone()[0]
        active = cursor.execute("SELECT COUNT(*) FROM platform_registry WHERE status='ACTIVE'").fetchone()[0]
        partial = cursor.execute("SELECT COUNT(*) FROM platform_registry WHERE status='PARTIAL'").fetchone()[0]
        planned = cursor.execute("SELECT COUNT(*) FROM platform_registry WHERE status='PLANNED'").fetchone()[0]
        result["total"] = total
        result["ui_visible_count"] = ui_visible
        result["active_count"] = active
        result["partial_count"] = partial
        result["planned_count"] = planned

    finally:
        conn.close()

    return result


if __name__ == "__main__":
    print("=" * 60)
    print("platform_registry 初始化")
    print("=" * 60)
    result = init_platform_registry()
    print(f"表创建: {result['table_created']}")
    print(f"新增: {result['inserted']}, 更新: {result['updated']}")
    print(f"总平台数: {result['total']}")
    print(f"  ACTIVE: {result['active_count']}")
    print(f"  PARTIAL: {result['partial_count']}")
    print(f"  PLANNED: {result['planned_count']}")
    print(f"  UI可见: {result['ui_visible_count']}")
    if result["errors"]:
        print(f"错误 ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"  - {e}")
    else:
        print("错误: 无")
    print("=" * 60)
