# -*- coding: utf-8 -*-
"""数据中心 API — 平台注册表查询 + 各平台Raw表数据动态查询。

只返回 ui_visible=true 的平台给前端导航；系统管理接口返回全部平台。
所有查询使用参数化SQL，禁止拼接。缺失值显式返回null，不伪造。
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request
from lumenis.shared.database import get_repository

data_center_bp = Blueprint("data_center", __name__, url_prefix="/api/data-center")

# 允许查询的表白名单（防止SQL注入）
ALLOWED_TABLES = {
    # 小红书
    "xhs_notes", "xhs_note_comments", "xhs_users",
    # 抖音
    "douyin_videos", "douyin_comments", "douyin_users",
    # B站
    "bilibili_videos", "bilibili_comments", "bilibili_users",
    # 视频号
    "channels_videos", "channels_comments",
    # YouTube
    "youtube_videos", "youtube_comments", "youtube_channels",
    # TikTok
    "tiktok_videos", "tiktok_comments", "tiktok_users",
    # Instagram
    "instagram_media", "instagram_comments", "instagram_users",
    # X
    "x_posts", "x_users",
    # Reddit
    "reddit_posts", "reddit_comments", "reddit_subreddits",
    # LinkedIn
    "linkedin_posts", "linkedin_users",
    # GitHub
    "github_repositories", "github_issues", "github_pull_requests", "github_releases",
    # 知乎
    "zhihu_answers", "zhihu_questions", "zhihu_articles", "zhihu_comments",
    # Normalized层
    "platform_accounts", "platform_contents", "platform_comments",
    # 采集Evidence
    "collection_runs", "platform_evidence",
    # 业务层
    "brands", "content_analysis", "creators",
    # 现有兼容
    "notes", "note_comments", "events", "event_mentions", "metric_snapshots",
}

# 平台品牌色（用于前端点缀）
PLATFORM_COLORS: Dict[str, str] = {
    "xiaohongshu": "#FF2442",
    "douyin": "#000000",
    "bilibili": "#00A1D6",
    "channels": "#07C160",
    "youtube": "#FF0000",
    "tiktok": "#000000",
    "instagram": "#E4405F",
    "x": "#000000",
    "reddit": "#FF4500",
    "linkedin": "#0A66C2",
    "github": "#24292e",
    "zhihu": "#0084FF",
}


def _get_db() -> sqlite3.Connection:
    return get_repository().connect()


def _parse_date_bound(value: str) -> tuple[datetime, bool]:
    """Parse an ISO date/time bound and reject invalid calendar values."""
    date_only = re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed, date_only


def _out_of_range_bound(parsed: datetime, *, end: bool):
    """A valid ISO bound whose UTC instant leaves Python's year range.

    An end bound past year 9999 or a start bound before year 1 excludes
    nothing (no bound). The opposite cases cannot be represented, so they are
    rejected as a controlled validation error instead of a 500.
    """
    beyond_max = parsed.year == 9999
    if end == beyond_max:
        return None, None
    raise ValueError("date bound outside representable range")


def _text_date_filter(value: str, *, end: bool) -> tuple[str, str]:
    """Validate an ISO bound and return a UTC literal for julianday() comparison."""
    parsed, date_only = _parse_date_bound(value)
    try:
        utc = parsed.astimezone(timezone.utc)
    except OverflowError:
        return _out_of_range_bound(parsed, end=end)
    if date_only and end:
        try:
            return "<", (utc + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        except OverflowError:
            # 9999-12-31 has no next day and SQLite's julianday() returns NULL
            # for fractional instants at that boundary: no upper bound exists.
            return None, None
    if (end and utc >= datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
            and utc.microsecond >= 999500):
        # SQLite rounds to milliseconds; this rounds past 9999-12-31 and
        # julianday() becomes NULL. Nothing representable is later, so the
        # bound excludes nothing. Second-precision bounds stay active.
        return None, None
    return ("<=" if end else ">="), utc.strftime("%Y-%m-%d %H:%M:%S.%f")


def _unix_date_filter(
    value: str, *, end: bool, timestamp_multiplier: float = 1,
) -> tuple[str, float]:
    """Convert an ISO bound to a source-native Unix timestamp comparison."""
    parsed, date_only = _parse_date_bound(value)
    try:
        if date_only and end:
            # Include the whole requested end date, including fractional seconds.
            return "<", (parsed + timedelta(days=1)).timestamp() * timestamp_multiplier
        return ("<=" if end else ">="), parsed.timestamp() * timestamp_multiplier
    except (OverflowError, ValueError):
        return _out_of_range_bound(parsed, end=end)


@data_center_bp.route("/platforms", methods=["GET"])
def list_platforms():
    """获取前端可见的平台列表（ui_visible=true）。"""
    include_all = request.args.get("all", "0") == "1"
    conn = _get_db()
    try:
        if include_all:
            rows = conn.execute(
                "SELECT * FROM platform_registry ORDER BY status, platform_id"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM platform_registry WHERE ui_visible=1 ORDER BY status, platform_id"
            ).fetchall()
        platforms = []
        for r in rows:
            p = dict(r)
            p["color"] = PLATFORM_COLORS.get(p["platform_id"], "#666666")
            # 解析JSON字段
            for key in ("raw_tables", "normalized_mapping"):
                if p.get(key):
                    try:
                        p[key] = json.loads(p[key])
                    except (json.JSONDecodeError, TypeError):
                        pass
            platforms.append(p)
        return jsonify({"ok": True, "count": len(platforms), "platforms": platforms})
    finally:
        conn.close()


@data_center_bp.route("/platform/<platform_id>", methods=["GET"])
def get_platform_detail(platform_id: str):
    """获取单个平台详情 + 各Raw表数据量统计。"""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT * FROM platform_registry WHERE platform_id=?", (platform_id,)
        ).fetchone()
        if not row:
            return jsonify({"ok": False, "error": f"Platform not found: {platform_id}"}), 404
        p = dict(row)
        p["color"] = PLATFORM_COLORS.get(platform_id, "#666666")
        for key in ("raw_tables", "normalized_mapping"):
            if p.get(key):
                try:
                    p[key] = json.loads(p[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        # 统计各Raw表数据量
        table_stats = []
        raw_tables = p.get("raw_tables", [])
        if isinstance(raw_tables, list):
            for t in raw_tables:
                if t in ALLOWED_TABLES:
                    try:
                        cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                        table_stats.append({"table": t, "count": cnt})
                    except sqlite3.Error:
                        # Preserve the existing error field without presenting an
                        # unavailable count as a real empty table.
                        table_stats.append({"table": t, "count": None, "error": "query_failed"})
        p["table_stats"] = table_stats
        return jsonify({"ok": True, "platform": p})
    finally:
        conn.close()


@data_center_bp.route("/table/<table_name>", methods=["GET"])
def query_table(table_name: str):
    """动态查询任意白名单表，支持搜索/筛选/排序/分页/时间范围。

    Query params:
      q: 搜索关键词（在文本字段中模糊匹配）
      platform: 平台筛选（仅对有platform字段的表生效）
      author: 作者筛选
      content_type: 内容类型筛选
      sentiment: 情绪筛选
      risk_level: 风险筛选
      start_date / end_date: 来源发布时间范围（publish_date/published_at及平台原生发布时间字段）
      sort_by: 排序字段
      sort_order: asc/desc
      page: 页码（默认1）
      per_page: 每页数量（默认20，最大100）
    """
    if table_name not in ALLOWED_TABLES:
        return jsonify({"ok": False, "error": f"Table not allowed: {table_name}"}), 400

    conn = _get_db()
    try:
        # 获取表结构
        cols_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        columns = [c["name"] for c in cols_info]

        # 构建查询
        where_clauses = []
        params: List[Any] = []

        q = request.args.get("q", "").strip()
        if q:
            # 在文本字段中搜索
            text_cols = [c["name"] for c in cols_info if c["type"].upper() in ("TEXT", "VARCHAR", "")]
            if text_cols:
                or_clauses = [f"{col} LIKE ?" for col in text_cols]
                where_clauses.append("(" + " OR ".join(or_clauses) + ")")
                params.extend([f"%{q}%"] * len(text_cols))

        # 平台筛选
        if "platform" in columns:
            platform = request.args.get("platform", "").strip()
            if platform:
                where_clauses.append("platform = ?")
                params.append(platform)

        # 作者筛选
        author_col = None
        for ac in ("author_id", "author_name", "user_id", "nickname", "owner_mid", "author"):
            if ac in columns:
                author_col = ac
                break
        author = request.args.get("author", "").strip()
        if author and author_col:
            where_clauses.append(f"{author_col} LIKE ?")
            params.append(f"%{author}%")

        # 内容类型筛选
        if "content_type" in columns:
            content_type = request.args.get("content_type", "").strip()
            if content_type:
                where_clauses.append("content_type = ?")
                params.append(content_type)

        # 情感与风险筛选只在对应数据字段真实存在时执行，不能静默忽略。
        for filter_name in ("sentiment", "risk_level"):
            filter_value = request.args.get(filter_name, "").strip()
            if filter_value:
                if filter_name not in columns:
                    return jsonify({
                        "ok": False,
                        "error": f"{filter_name} filter unavailable for table {table_name}",
                    }), 400
                where_clauses.append(f"{filter_name} = ?")
                params.append(filter_value)

        # 仅用来源发布字段筛选。publish_date 优先于通用原生字段；绝不把
        # collected_at/captured_at 等采集时间作为发布时间。
        time_col = next((
            candidate for candidate in (
                "publish_date", "publish_datetime", "published_at", "time",
                "create_time", "pubdate", "created_utc", "taken_at",
                "created_time", "created_at",
            )
            if candidate in columns
        ), None)
        time_expr = time_col
        time_col_type = next(
            (str(c["type"] or "").upper() for c in cols_info if c["name"] == time_col),
            "",
        )
        if time_col == "publish_date" and "publish_datetime" in columns:
            # Some imported rows have only the more precise source datetime.
            # Use it only when this row has no date value; do not substitute
            # capture/collection time or override a declared publish_date.
            time_expr = (
                "COALESCE(NULLIF(TRIM(publish_date), ''), "
                "NULLIF(TRIM(publish_datetime), ''))"
            )
            time_col_type = ""
        numeric_time_col = any(kind in time_col_type for kind in ("INT", "REAL", "NUM", "FLOAT", "DOUBLE"))
        timestamp_multiplier = (
            1000 if time_col == "time" and table_name in {"xhs_notes", "xhs_note_comments"}
            else 1
        )
        start_date = request.args.get("start_date", "").strip()
        end_date = request.args.get("end_date", "").strip()
        if (start_date or end_date) and time_col is None:
            return jsonify({
                "ok": False,
                "error": f"publication date filter unavailable for table {table_name}",
            }), 400
        if time_col:
            if start_date:
                try:
                    if numeric_time_col:
                        operator, value = _unix_date_filter(
                            start_date, end=False,
                            timestamp_multiplier=timestamp_multiplier,
                        )
                    else:
                        operator, value = _text_date_filter(start_date, end=False)
                except ValueError:
                    return jsonify({"ok": False, "error": "invalid start_date"}), 400
                if operator is None:
                    pass  # earliest representable date: nothing is earlier
                elif not numeric_time_col:
                    # Compare instants, not strings: julianday() applies
                    # declared offsets (Z/+08:00) and accepts 'T' or space.
                    where_clauses.append(f"julianday({time_expr}) {operator} julianday(?)")
                else:
                    where_clauses.append(f"{time_expr} {operator} ?")
                if operator is not None:
                    params.append(value)
            if end_date:
                try:
                    if numeric_time_col:
                        operator, value = _unix_date_filter(
                            end_date, end=True,
                            timestamp_multiplier=timestamp_multiplier,
                        )
                    else:
                        operator, value = _text_date_filter(end_date, end=True)
                except ValueError:
                    return jsonify({"ok": False, "error": "invalid end_date"}), 400
                if operator is None:
                    pass  # maximum date: every stored instant is on or before it
                elif not numeric_time_col:
                    # Compare instants, not strings: julianday() applies
                    # declared offsets (Z/+08:00) and accepts 'T' or space.
                    where_clauses.append(f"julianday({time_expr}) {operator} julianday(?)")
                else:
                    where_clauses.append(f"{time_expr} {operator} ?")
                if operator is not None:
                    params.append(value)

        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # 总数
        total = conn.execute(f"SELECT COUNT(*) FROM {table_name}{where_sql}", params).fetchone()[0]

        # 排序
        sort_by = request.args.get("sort_by", "").strip()
        sort_order = request.args.get("sort_order", "desc").strip().lower()
        if sort_by and sort_by in columns:
            order_sql = f" ORDER BY {sort_by} {'ASC' if sort_order == 'asc' else 'DESC'}"
        elif time_col:
            order_sql = f" ORDER BY {time_expr} DESC"
        else:
            order_sql = ""

        # 分页
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
        offset = (page - 1) * per_page

        rows = conn.execute(
            f"SELECT * FROM {table_name}{where_sql}{order_sql} LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()

        data = [dict(r) for r in rows]

        return jsonify({
            "ok": True,
            "table": table_name,
            "columns": columns,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
            "data": data,
        })
    finally:
        conn.close()


@data_center_bp.route("/table/<table_name>/schema", methods=["GET"])
def get_table_schema(table_name: str):
    """获取表结构（字段名+类型）。"""
    if table_name not in ALLOWED_TABLES:
        return jsonify({"ok": False, "error": f"Table not allowed: {table_name}"}), 400
    conn = _get_db()
    try:
        cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        schema = [{"name": c["name"], "type": c["type"], "notnull": c["notnull"], "pk": c["pk"]} for c in cols]
        return jsonify({"ok": True, "table": table_name, "schema": schema})
    finally:
        conn.close()


@data_center_bp.route("/stats/overview", methods=["GET"])
def get_overview_stats():
    """数据中心总览统计：各平台数据量、表数量。"""
    conn = _get_db()
    try:
        platforms = conn.execute(
            "SELECT platform_id, display_name, status, ui_visible, raw_tables FROM platform_registry ORDER BY status"
        ).fetchall()
        stats = []
        total_records = 0
        errors = []
        for p in platforms:
            raw_tables = []
            if p["raw_tables"]:
                try:
                    raw_tables = json.loads(p["raw_tables"])
                except (json.JSONDecodeError, TypeError):
                    raw_tables = None
            table_counts = {}
            table_errors = {}
            platform_total = 0
            countable_tables = [
                table for table in raw_tables if isinstance(table, str) and table in ALLOWED_TABLES
            ] if isinstance(raw_tables, list) else []
            catalog_available = (
                isinstance(raw_tables, list)
                and bool(raw_tables)
                and len(countable_tables) == len(raw_tables)
            )
            if not catalog_available:
                table_errors["_catalog"] = "raw_tables_unavailable"
                errors.append({
                    "platform_id": p["platform_id"],
                    "table": None,
                    "error": "raw_tables_unavailable",
                })
            for t in countable_tables:
                try:
                    row = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
                    if row is None or row[0] is None:
                        raise sqlite3.DatabaseError("COUNT query returned no value")
                    cnt = row[0]
                    table_counts[t] = cnt
                    platform_total += cnt
                except sqlite3.Error:
                    table_counts[t] = None
                    table_errors[t] = "query_failed"
                    errors.append({
                        "platform_id": p["platform_id"],
                        "table": t,
                        "error": "query_failed",
                    })
            total_records_available = catalog_available and not table_errors
            if total_records_available:
                total_records += platform_total
            stats.append({
                "platform_id": p["platform_id"],
                "display_name": p["display_name"],
                "status": p["status"],
                "ui_visible": bool(p["ui_visible"]),
                "color": PLATFORM_COLORS.get(p["platform_id"], "#666"),
                "table_counts": table_counts,
                "table_errors": table_errors,
                "total_records": platform_total if total_records_available else None,
            })
        return jsonify({
            "ok": not errors,
            "total_platforms": len(stats),
            "ui_visible_count": sum(1 for s in stats if s["ui_visible"]),
            "total_records": total_records if not errors else None,
            "errors": errors,
            "platforms": stats,
        })
    finally:
        conn.close()
