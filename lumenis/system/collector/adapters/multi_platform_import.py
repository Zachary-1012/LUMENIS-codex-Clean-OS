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

from typing import Any, Dict, List, Optional

from lumenis.system.collector.adapters.platform_naming import (
    normalize_platform_name,
    get_platform_fields,
    normalize_content_id,
    to_canonical_record,
    build_content_url,
)


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

    payload: Dict[str, Any] = {
        "note_id": canonical.get("content_id"),
        "source_platform": plat or "unknown",
        "title": canonical.get("title") or raw.get("title") or "",
        "content": (
            raw.get("content")
            or raw.get("body")
            or raw.get("desc")
            or raw.get("text")
            or raw.get("description")
            or ""
        ),
        "url": canonical.get("url") or raw.get("url") or "",
        "cover": raw.get("cover") or raw.get("image") or raw.get("thumbnail") or raw.get("cover_url") or "",
        "author_id": canonical.get("author_id") or "",
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
        "publish_datetime": (
            canonical.get("published_at")
            or raw.get("publish_datetime")
            or raw.get("publish_date")
            or ""
        ),
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


def import_multi_platform_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
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
            row_id, is_new = db.insert_note(payload)

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
