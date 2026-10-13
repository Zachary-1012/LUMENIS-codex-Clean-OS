# -*- coding: utf-8 -*-
"""多平台数据导入接口（Shard C）。

接收标准化 JSON（平台原生字段或 canonical 字段均可），
依据 platform_naming 完成：平台归一化 → 字段映射 → ID 精度保护 → URL 构建，
最终通过 database.insert_note 入库。

设计原则（对齐 AGENTS.md）：
- 不新建表、不改 schema，复用 notes 表（note_id TEXT UNIQUE）；
- 非小红书平台的 content_id 直接作为 note_id 入库；
- source_platform 写入 canonical 名称（xiaohongshu/douyin/bilibili/weibo...）；
- 导入失败逐条记录，不静默丢弃（数据失败必须显式）；
- 导入层不做主体过滤/风险判断，保持纯净，下游核心模块负责；
- 抖音 19 位 aweme_id 全程字符串处理，禁止转 int 丢精度。
"""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math
import re
from typing import Any, Dict, List, Optional

from lumenis.system.collector.adapters.platform_naming import (
    normalize_platform_name,
    get_platform_fields,
    normalize_content_id,
    to_canonical_record,
    map_raw_to_normalized,
    build_content_url,
)


# Units are recorded only where the current source contract or adapter proves
# them. Other platforms' numeric fields remain UNKNOWN instead of guessing by
# magnitude or borrowing capture/update time.
_NATIVE_EPOCH_UNITS = {
    "xiaohongshu": "milliseconds",
    "douyin": "seconds",
    "bilibili": "seconds",
    "reddit": "seconds",
    "tiktok": "seconds",
}
_FLOAT_EPOCH_PLATFORMS = {"douyin", "reddit"}
_ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_ISO_DATETIME = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt ][0-9]{2}:[0-9]{2}"
    r"(?::[0-9]{2}(?:[.,][0-9]+)?)?(?:[Zz]|[+-][0-9]{2}(?::?[0-9]{2})?)$"
)
_NUMERIC_TEXT = re.compile(r"^[+-]?[0-9]+(?:\.[0-9]+)?$")
_RFC2822_DATE = re.compile(
    r"^(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s*)?"
    r"[0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4}\s+"
    r"[0-9]{2}:[0-9]{2}(?::[0-9]{2})?\s+(?:[A-Za-z]{1,5}|[+-][0-9]{4})$",
    re.IGNORECASE,
)


def _format_epoch_publication(value: int | float, platform: str) -> str:
    unit = _NATIVE_EPOCH_UNITS.get(platform)
    if unit is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return ""
    if isinstance(value, float) and (
        not math.isfinite(value) or platform not in _FLOAT_EPOCH_PLATFORMS
    ):
        return ""
    # Bilibili's native source uses zero as its missing-time sentinel.
    if platform == "bilibili" and value == 0:
        return ""
    try:
        timestamp = value / 1000 if unit == "milliseconds" else value
        published = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return ""
    timespec = "microseconds" if published.microsecond else "seconds"
    result = published.isoformat(timespec=timespec)
    return result.replace("+00:00", "Z") if platform == "douyin" else result


def _normalize_source_publication(value: Any, platform: Optional[str]) -> str:
    """Return a source-backed absolute publication value, or empty if unknown.

    Text is retained verbatim only when it is an explicit valid calendar date,
    timezone-aware ISO datetime, RFC 2822 date, or the Weibo full-year display
    format. Numeric epochs use only the platform units listed above.
    """
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)):
        return _format_epoch_publication(value, platform or "")
    if not isinstance(value, str):
        return ""

    text = value.strip()
    if not text:
        return ""
    if _NUMERIC_TEXT.fullmatch(text):
        unit = _NATIVE_EPOCH_UNITS.get(platform or "")
        if unit is None:
            return ""
        try:
            if "." in text:
                if platform not in _FLOAT_EPOCH_PLATFORMS:
                    return ""
                numeric_value: int | float = float(text)
            else:
                numeric_value = int(text)
        except (OverflowError, ValueError):
            return ""
        return _format_epoch_publication(numeric_value, platform or "")

    if _ISO_DATE.fullmatch(text):
        try:
            datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            return ""
        return value

    if _ISO_DATETIME.fullmatch(text):
        normalized = text.replace("z", "+00:00").replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return ""
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return ""
        return value

    if _RFC2822_DATE.fullmatch(text):
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError, OverflowError):
            return ""
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return ""
        return value

    if platform == "weibo":
        try:
            parsed = datetime.strptime(text, "%a %b %d %H:%M:%S %z %Y")
        except ValueError:
            return ""
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return ""
        if parsed.strftime("%a").casefold() != text[:3].casefold():
            return ""
        return value

    return ""


def _normalize_douyin_publish_datetime(value: Any) -> str:
    """Compatibility helper for Douyin's native Unix-seconds timestamp."""
    normalized = _normalize_source_publication(value, "douyin")
    if normalized:
        return normalized
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("invalid Douyin create_time value")
        raise ValueError("Douyin create_time is outside the supported timestamp range")
    raise ValueError("invalid Douyin create_time type")


def _to_note_payload(canonical: Dict[str, Any], raw: Dict[str, Any]) -> Dict[str, Any]:
    """把 canonical 记录 + 原始 raw 转为 database.insert_note 期望的 note_data 结构。

    notes 表列映射：
      content_id   → note_id          (UNIQUE TEXT)
      platform     → source_platform  (canonical)
      author_id    → author_id
      published_at → publish_datetime / publish_date
      like_count   → likes
      comment_count→ comments
      collect_count→ collects
      share_count  → shares
      content_type → note_type
      title/url    → 同名
      content/body → content / body
    """
    plat = canonical.get("platform")
    spec = get_platform_fields(plat) if plat else None

    # Prefer the original native field so a canonical adapter cannot erase the
    # source timezone or type. Canonical and legacy explicit publication fields
    # remain fallbacks; capture/update fields never enter this chain.
    native_publish_field = spec.published_at if spec else None
    if native_publish_field and native_publish_field in raw:
        published_source = raw[native_publish_field]
    else:
        published_source = None
    if published_source is None or (
        isinstance(published_source, str) and not published_source.strip()
    ):
        if "published_at" in raw:
            published_source = raw["published_at"]
        else:
            published_source = canonical.get("published_at")
    if published_source is None or (
        isinstance(published_source, str) and not published_source.strip()
    ):
        published_source = raw.get("publish_datetime")
    if published_source is None or (
        isinstance(published_source, str) and not published_source.strip()
    ):
        published_source = raw.get("publish_date")
    published_at = _normalize_source_publication(published_source, plat)

    author_id = canonical.get("author_id")
    if plat == "douyin" and not author_id:
        # Search responses can expose uid without sec_uid. Retain the known uid
        # in the generic author field; never relabel it as native sec_uid.
        native_author_id = raw.get("author_id")
        if isinstance(native_author_id, str):
            author_id = native_author_id

    content = (
        raw.get("content")
        or raw.get("body")
        or raw.get("desc")
        or raw.get("text")
        or raw.get("description")
        or ""
    )
    if not content:
        content = map_raw_to_normalized(raw, plat).get("content") or ""

    payload: Dict[str, Any] = {
        "note_id": canonical.get("content_id"),
        "source_platform": plat or "unknown",
        "title": canonical.get("title") or raw.get("title") or "",
        "content": content,
        "url": canonical.get("url") or raw.get("url") or "",
        "cover": raw.get("cover") or raw.get("image") or raw.get("thumbnail") or raw.get("cover_url") or "",
        "author_id": author_id or "",
        "author_nickname": (
            raw.get("author_nickname")
            or raw.get("nickname")
            or raw.get("name")
            or raw.get("screen_name")
            or raw.get("username")
            or ""
        ),
        "author_avatar": raw.get("author_avatar") or raw.get("avatar") or raw.get("avatar_url") or "",
        "likes": canonical.get("like_count"),
        "comments": canonical.get("comment_count"),
        "collects": canonical.get("collect_count"),
        "shares": canonical.get("share_count"),
        "type": canonical.get("content_type") or raw.get("type") or "normal",
        "publish_datetime": published_at or "",
        "captured_at": (
            canonical.get("captured_at")
            or raw.get("captured_at")
            or raw.get("collected_at")
            or ""
        ),
        # Provenance fields are transport metadata, not a subject decision.
        # Keeping them on the canonical notes row lets CTH apply its existing
        # subject rules without losing the human query that produced a record.
        "source_keyword": raw.get("source_keyword") or raw.get("keyword") or "",
        "matched_keywords": raw.get("matched_keywords") or raw.get("keyword") or "",
    }

    # 小红书 xsec_token 透传（signature_token 字段名因平台而异）
    if spec and spec.signature_token and spec.signature_token in raw:
        payload["xsec_token"] = raw[spec.signature_token]

    # URL 兜底：raw 未给 url 时用平台规则构建
    if not payload["url"] and plat and payload["note_id"]:
        try:
            token = raw.get(spec.signature_token) if spec and spec.signature_token else None
            built = build_content_url(plat, payload["note_id"], author_id=payload["author_id"], token=token)
            if built:
                payload["url"] = built
        except Exception:
            pass  # URL 构建失败不阻断入库

    return payload


def import_multi_platform_records(records: List[Dict[str, Any]], *, connection=None) -> Dict[str, Any]:
    """批量导入多平台记录。

    Args:
        records: 原始记录列表，每条必须含 platform 或 source_platform 字段，
                 以及对应平台的内容 ID 字段（如 note_id / aweme_id / bvid / mid）。

    Returns:
        {
            "total": int, "imported": int, "updated": int,
            "skipped": int, "failed": int,
            "details": [{"index", "status", "platform", "note_id", "reason"/"error"}, ...]
        }
    """
    import database as db  # 延迟导入，避免模块加载时触发 DB 初始化

    results: List[Dict[str, Any]] = []
    imported = 0
    updated = 0
    skipped = 0
    failed = 0

    for idx, raw in enumerate(records):
        try:
            # 1. 归一化平台（允许别名：xhs/xiaohongshu/xiaohongshu-cdp 等）
            plat = normalize_platform_name(raw.get("platform") or raw.get("source_platform"))
            if not plat:
                skipped += 1
                results.append({
                    "index": idx, "status": "skipped", "reason": "unknown_platform",
                    "raw_platform": raw.get("platform") or raw.get("source_platform"),
                })
                continue

            # 2. 原生字段 → canonical 记录
            canonical = to_canonical_record(raw, plat)

            # 3. 标准化内容 ID（抖音 19 位 aweme_id 强制字符串保精度）
            content_id = normalize_content_id(plat, canonical.get("content_id"))
            if not content_id:
                skipped += 1
                results.append({
                    "index": idx, "status": "skipped", "reason": "missing_content_id",
                    "platform": plat,
                })
                continue
            canonical["content_id"] = content_id

            # 4. 转 note payload 并入库（insert_note 内部处理 INSERT/UPDATE）
            payload = _to_note_payload(canonical, raw)
            if connection is None:
                row_id, is_new = db.insert_note(payload)
            else:
                row_id, is_new = db.insert_note(payload, connection=connection)

            if is_new:
                imported += 1
                status = "imported"
            else:
                updated += 1
                status = "updated"
            results.append({
                "index": idx, "status": status, "platform": plat,
                "note_id": content_id, "row_id": row_id,
            })

        except Exception as e:
            failed += 1
            results.append({"index": idx, "status": "failed", "error": str(e)})

    return {
        "total": len(records),
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "details": results,
    }
