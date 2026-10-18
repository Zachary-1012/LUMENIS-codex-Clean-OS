# -*- coding: utf-8 -*-
"""SYSTEM-owned collection shared by exact CTH/BMP and unassigned GLOBAL work.

Manual calls require the current actor/scope and exact DATA_IMPORT approval.
Internal scheduled calls require an enabled, signed, freshly checked plan; they
do not enable future-user AUTO or grant platform credentials. XHS delegates to
the existing protected HK/international worker. Platform access stays read-only.
Source, Evidence, Canonical, native fields and metric history use the existing
transaction owner. No publishing or parallel data store is introduced.
"""
from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
import ipaddress

import threading
import time
import sys
import hashlib
import json
import os
import getpass
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .base import CollectionResult, CollectionStatus
from .config import PLATFORM_CAPABILITIES
from .registry import get_adapter
from .routing import RouteIdentityMismatch, bind_collection_route
from .safe_collection import CollectionHygienePolicy, RateGovernor


# Planned visibility is separate from the unchanged executable source set.
SECONDARY_COLLECTION_PLATFORMS = tuple(
    cap["canonical_id"] for cap in PLATFORM_CAPABILITIES.values()
    if cap["collection_entry_enabled"])
_COLLECTION_SURFACE_PLATFORMS = tuple(
    cap["canonical_id"] for cap in PLATFORM_CAPABILITIES.values()
    if cap["collection_surface_visible"])
PLATFORM_NAMES = {cap["canonical_id"]: cap["name"] for cap in PLATFORM_CAPABILITIES.values()}
MAX_RESULTS = 20
MAX_XHS_SCROLL = 20
MIN_INTERVAL_SECONDS = 3.0

_DEFAULT_GET_ADAPTER = get_adapter
_runtime_adapters: Dict[str, Any] = {}
_runtime_adapter_lock = threading.RLock()
_evidence_schema_paths: set[str] = set()
_evidence_schema_lock = threading.Lock()


def _get_runtime_adapter(platform: str):
    """Reuse the registered adapter instance so its existing breaker survives calls.

    Tests and embedding applications may replace ``get_adapter``; in that case
    retain the factory behavior instead of caching a test double.
    """
    if get_adapter is not _DEFAULT_GET_ADAPTER:
        return get_adapter(platform)
    with _runtime_adapter_lock:
        adapter = _runtime_adapters.get(platform)
        if adapter is None:
            adapter = get_adapter(platform)
            _runtime_adapters[platform] = adapter
        return adapter

_locks = {platform: threading.Lock() for platform in SECONDARY_COLLECTION_PLATFORMS}
_last_action = {platform: 0.0 for platform in SECONDARY_COLLECTION_PLATFORMS}
_last_action_lock = threading.Lock()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _canonical_status(result: CollectionResult | None) -> str:
    if result is None:
        return "UNAVAILABLE"
    value = result.status.value if isinstance(result.status, CollectionStatus) else str(result.status)
    return value.upper()


def _observed_raw_count(collection: CollectionResult | None, returned_count: int) -> int | None:
    """Keep an unobserved source count UNKNOWN; zero is valid only after a read."""
    if collection is None:
        return None
    raw = collection.raw_count
    raw_count = raw if type(raw) is int and raw >= 0 else None
    if raw_count is not None and raw_count > 0:
        return max(raw_count, returned_count)
    if collection.ok:
        return max(raw_count if raw_count is not None else 0, returned_count)
    if returned_count > 0:
        return returned_count
    return None


def _status_message(status: str, *, detail: str = "") -> str:
    messages = {
        "SUCCESS": "已完成只读采集并写入 CTH 证据链",
        "NO_NEW_DATA": "接口可用，本次没有新内容",
        "SESSION_EXPIRED": "登录态未通过，需要人工更新本地登录态",
        "RISK_WARNING": "出现平台风险信号，已停止扩大请求",
        "BLOCKED": "平台请求被阻断，已停止重试",
        "COOLING_DOWN": "平台处于冷却状态，暂不请求",
        "NOT_SUPPORTED": "此平台适配器未实现该能力",
        "NOT_CONFIGURED": "尚未配置该平台的授权运行方式",
        "PROVIDER_UNAVAILABLE": "采集提供方暂不可用，本次请求已隔离",
        "NEED_VERIFY": "授权或运行环境已配置，需由本次人工请求验证",
        "RATE_LIMITED": "已达到采集频率或每日上限，暂不请求",
        "POLICY_STATE_UNAVAILABLE": "无法读取采集限额状态，已阻止外部请求",
        "IMPORT_FAILED": "部分记录未能写入现有业务数据，结果未标记完成",
        "CANONICAL_SYNC_FAILED": "原始记录已保留，但 Canonical Data 同步未完成",
        "SCOPE_REVIEW_REQUIRED": "内容与所选主体的关联尚待核对，未归入该主体",
        "PARTIAL_SCOPE_REVIEW_REQUIRED": "已保存确认关联的内容，其余内容仍待核对",
        "EVIDENCE_WRITE_FAILED": "Evidence 未能持久化，本次采集不标记为完成",
        "COLLECT_ERROR": "采集引擎未完成本次请求",
        "UNAVAILABLE": "采集引擎未就绪",
    }
    # Adapter messages may contain remote response text.  Keep this product
    # contract fixed and never return raw payloads, cookie strings or
    # filesystem details to the UI.  Detailed diagnostics remain in the
    # local runtime log/evidence record.
    return messages.get(status, "采集状态已记录")


def _last_run(platform: str) -> Dict[str, Any] | None:
    """Read only the platform's recent web_runs summary from the active DB."""
    try:
        import database as db

        with db.get_db() as conn:
            row = conn.execute(
                """SELECT adapter, query, started_at, finished_at, fetched,
                          accepted, rejected, error
                     FROM web_runs WHERE adapter=?
                     ORDER BY id DESC LIMIT 1""",
                (platform,),
            ).fetchone()
        if not row:
            return None
        error_text = str(row[7] or "").strip().upper()
        if error_text:
            if "SESSION_EXPIRED" in error_text or "登录" in str(row[7] or ""):
                state = "SESSION_EXPIRED"
            elif "NOT_CONFIGURED" in error_text:
                state = "NOT_CONFIGURED"
            elif "PROVIDER_UNAVAILABLE" in error_text:
                state = "PROVIDER_UNAVAILABLE"
            elif "NEED_VERIFY" in error_text or "验证" in str(row[7] or ""):
                state = "NEED_VERIFY"
            elif "RATE_LIMITED" in error_text:
                state = "RATE_LIMITED"
            elif "CANONICAL_SYNC_FAILED" in error_text:
                state = "CANONICAL_SYNC_FAILED"
            elif "PARTIAL_SCOPE_REVIEW_REQUIRED" in error_text:
                state = "PARTIAL_SCOPE_REVIEW_REQUIRED"
            elif "SCOPE_REVIEW_REQUIRED" in error_text:
                state = "SCOPE_REVIEW_REQUIRED"
            elif "IMPORT_FAILED" in error_text:
                state = "IMPORT_FAILED"
            elif "RISK" in error_text or "风控" in str(row[7] or ""):
                state = "RISK_WARNING"
            elif "BLOCK" in error_text or "阻断" in str(row[7] or ""):
                state = "BLOCKED"
            elif "COOL" in error_text or "冷却" in str(row[7] or ""):
                state = "COOLING_DOWN"
            else:
                state = "COLLECT_ERROR"
        else:
            fetched_count = row[4] if type(row[4]) is int and row[4] >= 0 else None
            state = (
                "SUCCESS" if fetched_count is not None and fetched_count > 0 else
                "NO_NEW_DATA" if fetched_count == 0 else
                "UNKNOWN"
            )
        fetched = row[4] if type(row[4]) is int and row[4] >= 0 else None
        accepted = row[5] if type(row[5]) is int and row[5] >= 0 else None
        rejected = row[6] if type(row[6]) is int and row[6] >= 0 else None
        return {
            "platform": row[0],
            "query": row[1],
            "started_at": row[2],
            "finished_at": row[3],
            "fetched": fetched,
            "accepted": accepted,
            "rejected": rejected,
            "state": state,
            "error_recorded": bool(row[7]),
        }
    except Exception:
        return None


def _xhs_primary_runtime_status() -> Dict[str, Any]:
    """Project the already-loaded XHS orchestrator snapshot without probing credentials.

    The orchestrator is imported by the application entry point.  Looking it up
    in ``sys.modules`` avoids importing ``xhs_cookie_bridge`` from a screen read;
    that module has initialization-time statistics persistence.  This function
    never reads Cookie contents, starts a browser, or makes a network request.
    """
    base = {"status": "UNVERIFIED", "heartbeat_at": None, "observed": False}
    orchestrator = sys.modules.get("xhs_p0_orchestrator")
    get_status = getattr(orchestrator, "get_status", None)
    if not callable(get_status):
        return base
    try:
        snapshot = get_status()
        if not isinstance(snapshot, dict):
            return base
        base["observed"] = True
        paused = bool(snapshot.get("user_paused"))
        session_ok = snapshot.get("session_ok")
        heartbeat = snapshot.get("heartbeat_last")
        try:
            heartbeat = float(heartbeat) if heartbeat is not None else None
            interval = max(1.0, float(snapshot.get("heartbeat_interval") or 30.0))
        except (TypeError, ValueError):
            heartbeat = None
            interval = 30.0
        age = time.time() - heartbeat if heartbeat is not None else None
        heartbeat_fresh = age is not None and 0 <= age < interval * 2

        if paused:
            base["status"] = "USER_PAUSED"
        elif session_ok is False:
            base["status"] = "SESSION_EXPIRED"
        elif session_ok is True and heartbeat_fresh:
            base["status"] = "READY"
        elif str(snapshot.get("resident_mode") or "").upper() == "PROBING":
            base["status"] = "PROBING"
        if heartbeat is not None and heartbeat > 0:
            base["heartbeat_at"] = datetime.fromtimestamp(heartbeat).strftime("%Y-%m-%d %H:%M:%S")
        return base
    except Exception:
        return base


def _xhs_primary_last_run() -> Dict[str, Any] | None:
    """Read the last durable XHS collection-log summary, excluding error text."""
    try:
        import database as db

        with db.get_db() as conn:
            row = conn.execute(
                """SELECT status, notes_count, started_at, finished_at
                     FROM collection_logs ORDER BY id DESC LIMIT 1"""
            ).fetchone()
        if not row:
            return None
        count = int(row[1]) if row[1] is not None else None
        return {
            "state": str(row[0] or "UNKNOWN").upper(),
            "fetched": count,
            "accepted": None,
            "started_at": row[2],
            "finished_at": row[3],
            "source": "collection_logs",
        }
    except Exception:
        return None


def _adapter_health(platform: str, **source_kwargs: Any) -> Dict[str, Any]:
    try:
        adapter = _get_runtime_adapter(platform)
        result = adapter.health_check(**source_kwargs)
        status = _canonical_status(result)
        metadata = result.metadata if isinstance(result.metadata, dict) else {}
        # Only expose non-sensitive readiness and provenance facts. Cookie
        # values, paths, counts, endpoint URLs and response payloads stay local.
        safe_metadata = {
            key: metadata[key]
            for key in (
                "engine_ok", "cookie_required", "provider", "source",
                "healthcheck_scope", "session_state", "endpoint_configured",
                "requires_auth", "requires_authorization", "cookies_used",
                "availability", "worker_binding_registered", "login_and_collection_verified",
            )
            if key in metadata
        }
        return {
            "status": status,
            "ready": status == "SUCCESS",
            "can_attempt": status in {"SUCCESS", "NEED_VERIFY"},
            "message": _status_message(status),
            "metadata": safe_metadata,
        }
    except Exception as exc:  # pragma: no cover - defensive runtime boundary
        return {
            "status": "UNAVAILABLE",
            "ready": False,
            "can_attempt": False,
            "message": _status_message("UNAVAILABLE"),
            "metadata": {"error_type": type(exc).__name__},
        }


def get_collection_surface() -> Dict[str, Any]:
    """Return the product-facing CTH collection capability map.

    This is a local health/read-only call.  It does not start a browser or make
    an external request.
    """
    platforms: List[Dict[str, Any]] = []
    for platform in _COLLECTION_SURFACE_PLATFORMS:
        cap = PLATFORM_CAPABILITIES["xhs" if platform == "xiaohongshu" else platform]
        health = _adapter_health(platform)
        last_run = _last_run(platform)
        health_scope = (health.get("metadata") or {}).get("healthcheck_scope")
        display_status = (
            last_run["state"]
            if health["status"] == "SUCCESS" and last_run and last_run.get("state")
            else (
                "CONFIGURED"
                if health["status"] == "SUCCESS"
                and health_scope in {"configuration_only", "public_endpoint_configuration"}
                else ("READY" if health["status"] == "SUCCESS" else health["status"])
            )
        )
        platforms.append({
            "platform": platform,
            "name": PLATFORM_NAMES[platform],
            "implementation_state": cap["implementation_state"],
            "source_kind": cap["source_kind"],
            "product_owner": "CTH",
            "consumer_views": ["CTH", "BMP"],
            "manual_collection_enabled": bool(cap.get("manual_collection_enabled")),
            "scheduled_collection_enabled": bool(cap.get("enabled")),
            "collection_mode": "human_triggered_read_only",
            # Local readiness and the last real run are separate facts.  A
            # readable cookie file must not overwrite a verified session
            # failure or collection error in the product surface.
            "status": "PLANNED" if cap["implementation_state"] == "PLANNED" else display_status,
            "health": health,
            "last_run": last_run,
            "external_write": False,
            "publish_authority": "human_manual_only",
            "truth_path": "external_data -> evidence -> canonical_data -> CTH",
        })

    primary_runtime = _xhs_primary_runtime_status()
    primary_status = str(primary_runtime.get("status") or "UNVERIFIED").upper()
    primary_collection = {
        "platform": "xiaohongshu",
        "name": "小红书（香港账号）",
        "region": "hk_international",
        "product_owner": "CTH",
        "consumer_views": ["CTH", "BMP"],
        "implementation": "existing_primary_collector",
        "parallel_collector_added": False,
        "manual_collection_enabled": True,
        # The Experience V2 secondary form is intentionally not a second XHS
        # action surface. The existing primary route remains its sole owner.
        "form_selectable": False,
        "entry_label": "既有主采集链路 · 此表只读展示",
        "status": primary_status,
        "status_source": "existing_xhs_orchestrator_snapshot",
        "health": {
            "status": primary_status,
            "ready": primary_status == "READY",
            "can_attempt": primary_status == "READY",
            "healthcheck_scope": "in_process_status_snapshot",
        },
        "runtime": primary_runtime,
        "last_run": _xhs_primary_last_run(),
        "external_write": False,
        "publish_authority": "human_manual_only",
        "truth_path": "existing_xhs_primary_pipeline",
    }

    return {
        "ok": True,
        "product": "LUMENIS",
        "domain": "CTH",
        "surface": "平台情报 / 只读证据采集",
        "source_of_truth": "notes + canonical_data + collection_logs + web_runs + v4_audit_logs",
        "primary_collection": primary_collection,
        "platforms": platforms,
        "paused_platforms": ["xiaohongshu_cn"],
        "out_of_scope_platforms": [],
        "auxiliary_sources": [cap["canonical_id"] for cap in PLATFORM_CAPABILITIES.values()
                              if not cap["collection_surface_visible"]],
        "manual_only": True,
        "manual_only_scope": "secondary_platform_form",
        "read_only": True,
        "external_write": False,
        "product_will_not_publish": True,
        "generated_at": _now(),
    }


def _validate_request(platform: str, keyword: str, max_results: int) -> tuple[str, str, int]:
    canonical = str(platform or "").strip().lower()
    if canonical not in SECONDARY_COLLECTION_PLATFORMS:
        raise ValueError("当前采集入口不支持该平台；大陆小红书仍按现有区域门禁暂停")
    query = str(keyword or "").strip()
    # Public adapters receive a source URL, not a social search keyword. Keep
    # that URL intact so path/query identity, authorization and provenance agree.
    max_length = 4096 if canonical in {"public_http", "web_rss", "web_atom", "sitemap"} else 256
    if not query or len(query) > max_length:
        raise ValueError(f"keyword/source URL 必须为 1-{max_length} 个字符")
    try:
        limit = int(max_results)
    except (TypeError, ValueError):
        raise ValueError("max_results 必须为整数") from None
    if limit < 1 or limit > MAX_RESULTS:
        raise ValueError(f"max_results 必须在 1-{MAX_RESULTS} 之间")
    return canonical, query, limit


def _blocked_youtube_atom_feed(platform: str, source_url: str) -> bool:
    if platform != "web_atom":
        return False
    parts = urlsplit(source_url)
    host = (parts.hostname or "").lower()
    return (host == "youtube.com" or host.endswith(".youtube.com")) and parts.path == "/feeds/videos.xml"


def _native_record(item: Dict[str, Any], platform: str, keyword: str, captured_at: str) -> Dict[str, Any]:
    """Adapt the main normalized item to platform-native mapping keys.

    ``to_canonical_record`` intentionally reads native keys; this adapter adds
    those keys without changing the original normalized item or persisting raw
    payloads in the HTTP response.
    """
    raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
    if (platform == "xiaohongshu" and not raw
            and item.get("note_id") not in (None, "")):
        # The existing XHS adapter returns the collector's native note objects
        # directly (note_id/time/liked_count), unlike adapters that wrap them
        # under `raw`. Preserve the native observation through the established
        # credential filter and XHS field projection before the common importer.
        return prepare_xhs_observations(
            [item], keyword=keyword, captured_at=captured_at,
        )[0]
    record: Dict[str, Any] = dict(raw)
    record["source_raw"] = dict(raw)
    from .platform_naming import get_platform_fields, normalize_content_id
    spec = get_platform_fields(platform)
    native_id = raw.get(spec.content_id) if spec else None
    if native_id is None or native_id == "":
        native_id = item.get("platform_content_id")
    content_id = normalize_content_id(platform, native_id)
    publish_date = item.get("publish_datetime") or ""
    record.update({
        "platform": platform,
        "source_platform": platform,
        "content_id": content_id,
        "title": item.get("title") or "",
        "content": item.get("content") or "",
        "url": item.get("url") or "",
        "author_id": raw.get("author_id") if raw.get("author_id") not in (None, "") else item.get("author_id") or "",
        "author_nickname": item.get("author_nickname") or "",
        "captured_at": captured_at,
        "publish_datetime": publish_date,
        "source_keyword": keyword,
        "matched_keywords": keyword,
    })
    def fill_native(field, value):
        if record.get(field) in (None, "") and value is not None and value != "":
            record[field] = value
    if platform == "bilibili":
        source_bvid = raw.get("bvid") or content_id
        if source_bvid is not None and str(source_bvid).strip():
            record["bvid"] = str(source_bvid).strip()

        source_publication = publish_date or raw.get("pubdate_ts")
        if record.get("pubdate") in (None, "") and source_publication not in (None, ""):
            record["pubdate"] = source_publication

        for native_field, item_field in (
            ("mid", "author_id"),
            ("like", "likes"),
            ("reply", "comments"),
            ("favorite", "collects"),
            ("share", "shares"),
        ):
            value = item.get(item_field)
            if value is not None and value != "" and record.get(native_field) in (None, ""):
                record[native_field] = value
    elif platform == "douyin":
        fill_native("aweme_id", content_id)
        fill_native("desc", item.get("content") or item.get("title"))
        author_name = item.get("author_nickname")
        if (isinstance(author_name, str) and author_name.strip()
                and author_name.strip() != "抖音用户" and not record.get("nickname")):
            record["nickname"] = author_name.strip()
        if not item.get("author_id") and raw.get("author_id") is not None:
            record["author_id"] = raw["author_id"]
        for native_field, item_field in (("digg_count", "likes"),
                                         ("comment_count", "comments"),
                                         ("collect_count", "collects"),
                                         ("share_count", "shares")):
            value = item.get(item_field)
            fill_native(native_field, value)
    elif platform == "weibo":
        # Top-level idstr identifies the post. Author identity comes from
        # user.id in the adapter, never from the post's id/idstr.
        for native_field, value in (
            ("mid", content_id), ("user_id", item.get("author_id")),
            ("screen_name", item.get("author_nickname")),
            ("created_at", publish_date), ("attitudes_count", item.get("likes")),
            ("comments_count", item.get("comments")), ("reposts_count", item.get("shares")),
        ):
            if value is not None and value != "" and record.get(native_field) in (None, ""):
                record[native_field] = value
    elif platform == "x":
        fill_native("tweet_id", content_id)
        fill_native("created_at", publish_date)
        fill_native("screen_name", raw.get("handle"))
        for native_field, item_field in (("favorite_count", "likes"),
                                         ("reply_count", "comments"),
                                         ("retweet_count", "shares")):
            value = item.get(item_field)
            fill_native(native_field, value)
    elif platform == "zhihu":
        if raw.get("object_type") == "answer":
            fill_native("answer_id", content_id)
        fill_native("created_time", publish_date)
        for native_field, item_field in (("voteup_count", "likes"),
                                         ("comment_count", "comments"),
                                         ("share_count", "shares")):
            fill_native(native_field, item.get(item_field))
    elif platform == "instagram":
        if raw.get("shortcode") and not raw.get("media_id"):
            record["source_id_kind"] = "shortcode"
        fill_native("taken_at", publish_date)
        for native_field, item_field in (("like_count", "likes"),
                                         ("comment_count", "comments"),
                                         ("share_count", "shares")):
            fill_native(native_field, item.get(item_field))
    elif platform == "public_http":
        fill_native("published_at", publish_date)
    elif platform == "web_rss":
        fill_native("source_name", item.get("author_nickname"))
        fill_native("published_at", publish_date)
        for native_field, item_field in (("like_count", "likes"),
                                         ("comment_count", "comments"),
                                         ("collect_count", "collects"),
                                         ("share_count", "shares")):
            fill_native(native_field, item.get(item_field))
    elif platform == "web_atom":
        fill_native("author_name", item.get("author_nickname"))
        fill_native("published_at", publish_date)
        record["content_type"] = "video" if raw.get("video_id") else "article"
    return record


def _daily_action_count(platform: str, at: datetime) -> int | None:
    """Read today's attempts from the existing audit table; never create state."""
    try:
        import database as db

        with db.get_db() as conn:
            web_runs_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='web_runs'"
            ).fetchone()
        if not web_runs_exists:
            # Match the application's existing cold-start initializer for a
            # brand-new runtime DB; do not treat missing policy state as 0.
            db.init_db()

        day_start = at.strftime("%Y-%m-%d 00:00:00")
        next_day = at.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        with db.get_db() as conn:
            row = conn.execute(
                """SELECT COUNT(*) FROM web_runs
                     WHERE adapter=? AND started_at>=? AND started_at<?""",
                (platform, day_start, next_day.strftime("%Y-%m-%d 00:00:00")),
            ).fetchone()
        return int(row[0] or 0)
    except Exception:
        return None


def _mark_subject_and_sync(note_ids: Iterable[str], keyword: str) -> Dict[str, Any]:
    """Apply the existing CTH subject rule and sync only those rows to Canonical."""
    import database as db
    from subject_rules import subject_hit, subject_reason

    ids = [str(value).strip() for value in note_ids if str(value).strip()]
    matched = 0
    synced = 0
    subject_results: List[Dict[str, Any]] = []
    with db.get_db() as conn:
        rows = []
        for note_id in ids:
            row = conn.execute("SELECT * FROM notes WHERE note_id=?", (note_id,)).fetchone()
            if not row:
                continue
            note = dict(row)
            hit = bool(subject_hit(
                note.get("title", ""), note.get("body", ""), note.get("content", ""),
                note.get("source_keyword", "") or keyword, note.get("matched_keywords", "") or keyword,
            ))
            if hit:
                matched += 1
                conn.execute(
                    "UPDATE notes SET is_taikoo_verified=1, verify_reason=? WHERE note_id=?",
                    (subject_reason(note), note_id),
                )
            rows.append(note)
            subject_results.append({"note_id": note_id, "subject_match": hit})

    # Canonical writes use the same active DB path, and are deliberately after
    # the notes transaction so a missing canonical table cannot lose raw notes.
    try:
        from lumenis.shared.database import main_db_path
        from canonical_data import ensure_canonical_table, get_connection, note_to_canonical, persist_canonical

        db_path = main_db_path()
        ensure_canonical_table(db_path)
        con = get_connection(db_path)
        try:
            for note in rows:
                persist_canonical(con, note_to_canonical(note, product_id="CTH"))
                synced += 1
            con.commit()
        finally:
            con.close()
    except Exception:
        # Canonical synchronization is reported separately; notes remain the
        # raw/canonical import boundary and are not rolled back here.
        synced = 0

    return {"subject_matches": matched, "canonical_synced": synced, "subjects": subject_results}


def _write_run_log(platform: str, keyword: str, *, started: str, finished: str,
                   fetched: int | None, accepted: int | None, rejected: int | None,
                   error: str = "") -> None:
    import database as db

    db.log_web_run(platform, keyword, started, finished, fetched, accepted, rejected, error)
    db.log_web_source(
        platform, PLATFORM_NAMES.get(platform, platform), platform,
        success=not bool(error), error=error, item_count=fetched,
    )


def _ensure_evidence_schema() -> None:
    """Initialize the existing Evidence table for the currently bound runtime DB."""
    from lumenis.shared.database import main_db_path

    db_path = main_db_path()
    if db_path in _evidence_schema_paths:
        return
    with _evidence_schema_lock:
        if db_path in _evidence_schema_paths:
            return
        # Reuse the existing schema and additive evidence-chain migration. Both
        # resolve through the same ZBC_DB_PATH-bound runtime database.
        from lumenis.shared.evidence import store as evidence_store

        evidence_store.init_evidence_store(db_path)
        _evidence_schema_paths.add(db_path)




def _prelaunch_scope(scope: Mapping[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(scope, Mapping):
        raise ValueError("scope required")
    domain = str(scope.get("domain_id") or "").strip().lower()
    if domain == "zbmp":
        domain = "bmp"
    subject, brand = scope.get("subject_id"), scope.get("brand_focus_id")
    key = subject if domain == "cth" else brand
    other = brand if domain == "cth" else subject
    if domain not in {"cth", "bmp"} or scope.get("global_scope") is True:
        raise ValueError("exact CTH/BMP scope required")
    if not isinstance(key, str) or not key or key.strip() != key or other not in (None, ""):
        raise ValueError("one exact registry identity required")
    return {"domain_id": domain, "subject_id": subject if domain == "cth" else None,
            "brand_focus_id": brand if domain == "bmp" else None}


def _prelaunch_public_import_resource(
    scope: Mapping[str, Any], source_url: str, *, platform: str = "public_http",
) -> str:
    """Bind one local import approval to a registered entity and public URL."""
    exact = _prelaunch_scope(scope)
    parts = urlsplit(source_url)
    host = (parts.hostname or "").lower()
    if (
        platform not in {"public_http", "web_atom"}
        or parts.scheme != "https"
        or not host
        or host == "youtube.com"
        or host.endswith(".youtube.com")
        or host == "youtu.be"
        or host.endswith(".youtu.be")
    ):
        raise ValueError("public HTTPS source required")
    entity_id = exact["subject_id"] or exact["brand_focus_id"]
    digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    return f"prelaunch-{platform}:{exact['domain_id']}:{entity_id}:{digest}"


def _authorize_prelaunch_public(scope: Mapping[str, Any], source: str, platform: str,
                               *, maintenance_authorization=None, raw_capture=None,
                               business_query=None, max_results=None) -> bool:
    try:
        from lumenis.system.security import OperationType, get_permission_gate, is_testing_bypass_enabled
        if is_testing_bypass_enabled():
            return False
        if maintenance_authorization is not None:
            return get_permission_gate().check_prelaunch_maintenance(
                maintenance_authorization, source_url=source, platform=platform,
                scope=dict(scope), business_query=business_query, max_results=max_results,
            ).allowed is True
        if raw_capture is not None:
            if platform != "public_http" or raw_capture.source_url != source:
                return False
            resource = approved_public_raw_resource(scope, raw_capture)
        else:
            resource = _prelaunch_public_import_resource(scope, source, platform=platform)
        allowed = get_permission_gate().check(
            OperationType.DATA_IMPORT, resource,
            caller=f"local_prelaunch_operator:{getpass.getuser()}",
            domain_id=scope["domain_id"], exact_approval_required=True,
        ).allowed is True
        if allowed and raw_capture is not None:
            from lumenis.system.security.permission import _registered_resource_scope_exists
            return _registered_resource_scope_exists(
                scope["domain_id"],
                subject_id=scope.get("subject_id"), brand_focus_id=scope.get("brand_focus_id"),
            )
        return allowed
    except Exception:
        return False


def _prelaunch_manual_import_resource(
    scope: Mapping[str, Any], keyword: str, *, platform: str,
) -> str:
    """Bind human-only social import approval to platform, query, and exact entity."""
    exact = _prelaunch_scope(scope)
    if platform not in {"douyin", "x", "xhs"} or not isinstance(keyword, str) or not 1 <= len(keyword) <= 120:
        raise ValueError("exact social manual source required")
    entity_id = exact["subject_id"] or exact["brand_focus_id"]
    digest = hashlib.sha256(keyword.encode("utf-8")).hexdigest()
    return f"prelaunch-manual:{platform}:{exact['domain_id']}:{entity_id}:{digest}"


def _prelaunch_douyin_manual_import_resource(
    scope: Mapping[str, Any], keyword: str, *, platform: str,
) -> str:
    """Compatibility alias for existing Douyin approval callers."""
    if platform != "douyin":
        raise ValueError("exact Douyin manual source required")
    return _prelaunch_manual_import_resource(scope, keyword, platform=platform)


def _authorize_prelaunch_manual(
    scope: Mapping[str, Any], keyword: str, *, platform: str,
) -> bool:
    """Require the existing exact-resource human DATA_IMPORT approval."""
    try:
        from lumenis.system.security import (
            OperationType, get_permission_gate, is_testing_bypass_enabled,
        )
        if is_testing_bypass_enabled():
            return False
        exact = _prelaunch_scope(scope)
        resource = _prelaunch_manual_import_resource(
            exact, keyword, platform=platform,
        )
        return get_permission_gate().check(
            OperationType.DATA_IMPORT, resource,
            caller=f"local_prelaunch_operator:{getpass.getuser()}",
            domain_id=exact["domain_id"], exact_approval_required=True,
        ).allowed is True
    except Exception:
        return False


def _authorize_prelaunch_douyin_manual(
    scope: Mapping[str, Any], keyword: str, *, platform: str,
) -> bool:
    """Compatibility alias for existing Douyin approval callers."""
    return platform == "douyin" and _authorize_prelaunch_manual(
        scope, keyword, platform=platform,
    )


def _validate_prelaunch_registry(scope: Mapping[str, Any], *, connection=None) -> None:
    from lumenis.shared.database import get_repository
    from lumenis.shared.database.scope import resolve_scope
    conn = connection if connection is not None else get_repository().connect(timeout=10)
    try:
        resolve_scope(conn, product_id="CTH" if scope["domain_id"] == "cth" else "ZBMP",
                      subject_id=scope.get("subject_id"), brand_focus_id=scope.get("brand_focus_id"),
                      requested_status="UNVERIFIED")
    finally:
        if connection is None:
            conn.close()


def _prelaunch_entity_mentions(records: List[Dict[str, Any]], scope: Mapping[str, Any], *, connection=None) -> List[dict]:
    """Check source text, never the query, before a social result gets exact scope.

    A unique registered-name mention is bounded association evidence, not a
    claim that every statement concerns that entity or that the source is true.
    Unnamed or ambiguous results need review; location, author and query text
    cannot silently supply a missing content-level identity.
    """
    from lumenis.shared.database import get_repository

    def normalized(value):
        return " ".join(unicodedata.normalize("NFKC", str(value or "")).casefold().split())

    expected = scope.get("subject_id") or scope.get("brand_focus_id")
    domain = "CTH" if scope["domain_id"] == "cth" else "BMP"
    with (get_repository().transaction() if connection is None else nullcontext(connection)) as conn:
        rows = conn.execute(
            "SELECT subject_id, brand_focus_id, name_zh, name_en "
            "FROM lumenis_subject_registry WHERE domain_id=? "
            "AND status NOT IN ('archived','disabled','deleted')", (domain,),
        ).fetchall()
    names: dict[str, set[str]] = {}
    for subject, brand, chinese, english in rows:
        for name in (chinese, english):
            key = normalized(name)
            if len(key) >= 2:
                names.setdefault(key, set()).add(brand if domain == "BMP" else subject)
    target_names = {name: ids for name, ids in names.items() if expected in ids}
    decisions = []
    for record in records:
        text = normalized(" ".join(str(record.get(key) or "") for key in ("title", "content")))
        mentions = []
        for name, ids in target_names.items():
            # Latin names must not match a substring of another word. Chinese
            # names keep their full registry spelling (深圳湾 != 深圳).
            pattern = re.escape(name)
            if name[0].isascii() and name[0].isalnum():
                pattern = r"(?<![a-z0-9])" + pattern
            if name[-1].isascii() and name[-1].isalnum():
                pattern += r"(?![a-z0-9])"
            if re.search(pattern, text):
                mentions.append((name, ids))
        unique = [name for name, ids in mentions if ids == {expected}]
        decisions.append({
            "source_id": record.get("content_id"),
            "status": "EXACT_NAME_MENTION" if unique else "REVIEW_REQUIRED",
            "matched_names": sorted(unique),
            "reason": "source_name_mention" if unique else (
                "ambiguous_registered_name" if mentions else "no_exact_source_name"),
            "source_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    return decisions


def _existing_prelaunch_evidence(note_ids: List[str], scope: Mapping[str, Any], *, connection=None) -> int | None:
    if not note_ids:
        return None
    import database as db
    domain = "cth" if scope["domain_id"] == "cth" else "zbmp"
    key = scope.get("subject_id") or scope.get("brand_focus_id")
    with (db.get_db() if connection is None else nullcontext(connection)) as conn:
        rows = [conn.execute(
            "SELECT domain_id, subject_id, brand_focus_id, scope_status, scope_evidence_ref "
            "FROM notes WHERE note_id=?", (note_id,)
        ).fetchone() for note_id in note_ids]
    refs = set()
    for row in rows:
        if row is None:
            return None
        if row[0] == domain and row[3] == "VERIFIED" and (row[1] or row[2]) == key and row[4]:
            refs.add(int(row[4]))
    return refs.pop() if len(refs) == 1 else None


def _prelaunch_scope_conflict(records: List[Dict[str, Any]], scope: Mapping[str, Any], *, connection=None) -> bool:
    """Reject known cross-scope raw identities before the existing importer writes."""
    ids = [record.get("content_id") for record in records]
    if any(not isinstance(note_id, str) or not note_id for note_id in ids):
        return True
    if len(set(ids)) != len(ids):
        return True
    import database as db
    from .platform_naming import normalize_platform
    expected_platform = normalize_platform(records[0].get("platform") or records[0].get("source_platform"))
    if expected_platform is None or any(
        normalize_platform(record.get("platform") or record.get("source_platform")) != expected_platform
        for record in records
    ):
        return True
    expected_domain = "zbmp" if scope["domain_id"] == "bmp" else "cth"
    expected_product = "ZBMP" if scope["domain_id"] == "bmp" else "CTH"
    expected_subject = scope.get("subject_id")
    expected_brand = scope.get("brand_focus_id")
    rows = []
    with (db.get_db() if connection is None else nullcontext(connection)) as conn:
        identities = {}
        for table, id_column in (("notes", "note_id"), ("canonical_data", "source_id")):
            found = conn.execute(
                "SELECT " + id_column + ",domain_id,subject_id,brand_focus_id,"
                "source_platform,scope_status,scope_evidence_ref,product_id FROM " + table
                + " WHERE " + id_column + " IN (" + ",".join("?" for _ in ids) + ")", ids,
            ).fetchall() if ids else []
            rows.extend(row[1:] for row in found)
            for row in found:
                identities.setdefault(row[0], []).append(tuple(row[1:]))
        # A verified source must agree in both owners. Partial promotion or a
        # mismatched proof requires recovery before refreshing that identity.
        for prior in identities.values():
            if any(str(row[4] or "").upper() == "VERIFIED" for row in prior):
                proofs = {(row[0], row[1] or None, row[2] or None,
                           normalize_platform(row[3]), row[4], str(row[5] or ""), row[6]) for row in prior}
                if len(prior) != 2 or len(proofs) != 1:
                    return True
    return any(
        (row[0] not in (None, "", expected_domain))
        or (row[6] not in (None, "", expected_product))
        or (row[1] not in (None, "", expected_subject))
        or (row[2] not in (None, "", expected_brand))
        or normalize_platform(row[3]) != expected_platform
        or (scope.get("global_scope") is True and str(row[4] or "").upper() == "VERIFIED")
        or (str(row[4] or "").upper() == "VERIFIED" and not row[5])
        for row in rows
    )


def _write_prelaunch_evidence(platform: str, keyword: str, result: Dict[str, Any], *,
                              started: str, scope: Mapping[str, Any], source_ids: List[str],
                              review_candidates: List[Dict[str, Any]] | None = None,
                              manual: bool = False,
                              observations: List[Dict[str, Any]] | None = None,
                              connection=None) -> int | None:
    try:
        if connection is None:
            _ensure_evidence_schema()
        from lumenis.shared.evidence.store import record_evidence
        bmp = scope["domain_id"] == "bmp"
        inputs = {"platform": platform, "source_url": _credential_free_observations(keyword),
                  "source_ids": source_ids, "keywords": [_credential_free_observations(keyword)],
                  "unassigned_review_candidates": _credential_free_observations(review_candidates or [])}
        if observations:
            from lumenis.shared.database.platform_content import _stable_observation
            # Preserve the observed native material even when a later access
            # failure prevents Canonical admission. Hash-only continuity cannot
            # recover an accepted detail body that never reached the importer.
            inputs["source_observation_records"] = _credential_free_observations(observations)
            inputs["source_observations"] = [{
                "source_id": record.get("content_id"),
                "platform": platform,
                "source_url": _credential_free_observations(record.get("url")),
                "observation_sha256": hashlib.sha256(json.dumps(
                    _stable_observation(_credential_free_observations(record)),
                    ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")).hexdigest(),
            } for record in observations]
        prefix = "SYSTEM" if manual else "PRELAUNCH"
        evidence_id = record_evidence(
            source="collector", project="LUMENIS", product="ZBMP" if bmp else "CTH",
            feature_id=f"{prefix}_{platform.upper()}_COLLECT", level="L8",
            version=("approved-public-raw-source-v1" if
                     (result.get("provenance") or {}).get("provider") == "approved_original_public_raw"
                     else "collector-native-observation:v2"),
            test_name=f"{prefix.lower()}_collection_{platform}",
            result="PASS" if result.get("ok") else "FAIL", started_at=started,
            inputs=inputs,
            outputs={"notes_collected": result.get("raw_count"),
                     "notes_inserted": result.get("imported", 0),
                     "notes_updated": result.get("updated", 0),
                     "entity_mentions": result.get("entity_mentions")},
            actual=result.get("status", "COLLECT_ERROR"), account=f"{prefix}_{platform.upper()}",
            provider=(result.get("provenance") or {}).get("provider", "unreported"),
            collection_metadata=result.get("provenance"),
            domain_id="zbmp" if bmp else "cth", subject_id=scope.get("subject_id"),
            brand_focus_id=scope.get("brand_focus_id"),
            global_scope=scope.get("global_scope", False),
            connection=connection,
        )
        return evidence_id if type(evidence_id) is int and evidence_id > 0 else None
    except Exception:
        if connection is not None:
            raise
        return None


def _credential_free_observations(value):
    """Retain native source fields without copying transport credentials.

    Public author IDs and Zhihu url_token are source fields, so a broad
    substring match on auth/token would corrupt the observation.
    """
    if isinstance(value, dict):
        return {
            key: _credential_free_observations(item)
            for key, item in value.items()
            if not (
                str(key).lower() in {
                    "cookie", "cookies", "authorization", "password", "passwd",
                    "secret", "api_key", "apikey", "session", "session_id",
                    "headers", "request_headers", "xsec_token",
                }
                or (str(key).lower().endswith("_token") and str(key).lower() != "url_token")
            )
        }
    if isinstance(value, list):
        return [_credential_free_observations(item) for item in value]
    if isinstance(value, str) and value.lower().startswith(("http://", "https://")):
        parts = urlsplit(value)
        secret_names = {"key", "api_key", "apikey", "access_key", "appkey",
                        "token", "auth", "authorization", "cookie", "session",
                        "session_id", "password", "signature", "sign", "sig"}
        query = [(key, item) for key, item in parse_qsl(parts.query, keep_blank_values=True)
                 if key.lower() not in secret_names and not key.lower().endswith("_token")]
        # Source identity can keep its public query fields; credentials embedded
        # in URL user-info, query or fragments must not enter signed Evidence.
        netloc = parts.netloc.rsplit("@", 1)[-1]
        return urlunsplit((parts.scheme, netloc, parts.path, urlencode(query), ""))
    return value


def _sync_unassigned_collection(note_ids, scope, evidence_id, *, connection=None,
                               new_note_ids=(), source_unchanged=False):
    """Keep GLOBAL observations unassigned through the existing Canonical writer."""
    import database as db
    product = "ZBMP" if scope["domain_id"] == "bmp" else "CTH"
    domain = "zbmp" if scope["domain_id"] == "bmp" else "cth"
    new_ids = set(new_note_ids)
    if not new_ids.issubset(note_ids):
        raise ValueError("new source identities must belong to this transaction")
    with (db.get_db() if connection is None else nullcontext(connection)) as conn:
        conn.execute("SAVEPOINT manual_global_collection")
        try:
            for note_id in note_ids:
                row = conn.execute("SELECT * FROM notes WHERE note_id=?", (note_id,)).fetchone()
                if row is None:
                    raise ValueError("Raw source is missing")
                note = dict(row)
                if (note.get("subject_id") or note.get("brand_focus_id")
                        or str(note.get("scope_status") or "").upper() == "VERIFIED"
                        or (note.get("domain_id") not in (None, "", domain) and note_id not in new_ids)):
                    raise ValueError("GLOBAL cannot rewrite an assigned source")
                conn.execute(
                    "UPDATE notes SET product_id=?,domain_id=?,scope_status='UNASSIGNED' WHERE note_id=?",
                    (product, domain, note_id),
                )
            _sync_prelaunch_canonical_source_fields(
                note_ids, scope, evidence_id=evidence_id,
                source_unchanged=source_unchanged, connection=conn,
            )
            conn.execute("RELEASE SAVEPOINT manual_global_collection")
        except Exception:
            conn.execute("ROLLBACK TO SAVEPOINT manual_global_collection")
            conn.execute("RELEASE SAVEPOINT manual_global_collection")
            raise
    return len(note_ids)


def _persist_prelaunch_scope(note_ids: List[str], scope: Mapping[str, Any], evidence_id: int, *, connection=None) -> int:
    import database as db
    from lumenis.adapters.persist import persist_existing_note_scope
    bmp = scope["domain_id"] == "bmp"
    with (db.get_db() if connection is None else nullcontext(connection)) as conn:
        return persist_existing_note_scope(
            conn, note_ids, product_id="ZBMP" if bmp else "CTH",
            domain_id="zbmp" if bmp else "cth", subject_id=scope.get("subject_id"),
            brand_focus_id=scope.get("brand_focus_id"), scope_evidence_ref=evidence_id,
        )


def prepare_xhs_observations(notes, *, keyword, captured_at=None):
    """Project the current RedNote capture fields without querying a profile."""
    if not isinstance(notes, (list, tuple)) or not notes or len(notes) > 100:
        raise ValueError("a bounded captured RedNote batch is required")
    captured = captured_at or _now()
    records = []
    for note in notes:
        if not isinstance(note, dict):
            raise ValueError("a captured RedNote note must be a mapping")
        raw = _credential_free_observations(note)
        record = dict(raw)
        record["source_raw"] = raw
        def known(*keys):
            for key in keys:
                if key in raw and raw[key] is not None and raw[key] != "":
                    return raw[key]
            return None
        publication = known("time", "source_published_at", "detail_source_published_at",
                            "pub_time", "publish_datetime", "detail_publish_time",
                            "publish_time", "publish_date")
        record.update({
            "platform": "xiaohongshu", "source_platform": "xiaohongshu",
            "content_id": raw.get("note_id"), "note_id": raw.get("note_id"),
            "title": raw.get("title") or "", "content": raw.get("content") or raw.get("desc") or "",
            "desc": raw.get("desc") or raw.get("content") or "",
            "url": known("url", "note_url") or "",
            "user_id": known("user_id", "author_id"),
            "nickname": known("nickname", "author_nickname"),
            "time": publication,
            "liked_count": known("liked_count", "likes"),
            # The JS capture contract separates its dedicated post total from
            # comment_count/comments_collected, which count loaded DOM rows.
            "comment_count": known("total_comment_count", "comments"),
            "collected_count": known("collected_count", "collects"),
            "share_count": known("share_count", "shares"),
            "captured_at": captured, "source_keyword": keyword,
            "matched_keywords": keyword,
        })
        records.append(record)
    return records


def bind_collected_social_scope(note_ids, *, scope, platform, keyword, provider,
                                observations=None, connection=None):
    """Bind stored observations after the caller's collection permission gate.

    The requested query is context, never identity evidence. Reuse the signed
    Collector Evidence and exact Raw/Canonical writer; preserve unmatched data
    for review. A source mention does not establish a tenant/location relation.
    """
    import database as db

    if connection is None:
        _ensure_evidence_schema()
        try:
            with db.get_db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                return bind_collected_social_scope(
                    note_ids, scope=scope, platform=platform, keyword=keyword,
                    provider=provider, observations=observations, connection=conn,
                )
        except _CollectionWriteRejected as rejected:
            return rejected.result
    if not connection.in_transaction:
        raise ValueError("the caller must own an active collection transaction")
    exact = _prelaunch_scope(scope)
    _validate_prelaunch_registry(exact, connection=connection)
    ids = list(dict.fromkeys(str(value) for value in note_ids if value))
    if platform not in {"xhs", "douyin", "x"} or not ids or len(ids) > 100:
        raise ValueError("a bounded social observation batch is required")
    with nullcontext(connection) as conn:
        records = []
        for source_id in ids:
            row = conn.execute(
                "SELECT note_id content_id,title,content,source_platform "
                "FROM notes WHERE note_id=?", (source_id,),
            ).fetchone()
            from .platform_naming import normalize_platform
            if row is None or normalize_platform(row["source_platform"]) != normalize_platform(platform):
                raise ValueError("stored observation/platform mismatch")
            records.append(dict(row))
    if observations is not None:
        return _bind_collected_social_observations(
            records, observations, scope=exact, platform=platform, keyword=keyword,
            provider=provider, connection=connection,
        )
    if _prelaunch_scope_conflict(records, exact, connection=connection):
        return {"ok": False, "status": "SCOPE_CONFLICT", "verified": 0}
    mentions = _prelaunch_entity_mentions(records, exact, connection=connection)
    accepted = [item["source_id"] for item in mentions
                if item["status"] == "EXACT_NAME_MENTION"]
    review = [item for item in mentions if item["status"] != "EXACT_NAME_MENTION"]
    evidence_id = _existing_prelaunch_evidence(accepted, exact, connection=connection) if accepted else None
    if not accepted:
        from lumenis.shared.evidence.store import classify_evidence_integrity
        with nullcontext(connection) as conn:
            prior_reviews = conn.execute(
                "SELECT * FROM app_evidence_records WHERE feature_id=? ORDER BY id DESC LIMIT 30",
                (f'PRELAUNCH_{platform.upper()}_COLLECT',),
            ).fetchall()
        for prior_row in prior_reviews:
            prior_row = dict(prior_row)
            inputs = json.loads(prior_row.get('inputs_json') or '{}')
            marker = inputs.get('_lumenis_scope') or {}
            outputs = json.loads(prior_row.get('outputs_json') or '{}')
            if (classify_evidence_integrity(prior_row).get('verified')
                    and marker.get('subject_id') == exact.get('subject_id')
                    and marker.get('brand_focus_id') == exact.get('brand_focus_id')
                    and outputs.get('entity_mentions') == mentions):
                evidence_id = prior_row['id']
                break
    if evidence_id is not None:
        with nullcontext(connection) as conn:
            row = conn.execute("SELECT outputs_json FROM app_evidence_records WHERE id=?",
                               (evidence_id,)).fetchone()
        prior = json.loads(row[0] or '{}').get('entity_mentions') or []
        hashes = {item.get('source_id'): item.get('source_text_sha256') for item in prior}
        if any(hashes.get(item['source_id']) != item['source_text_sha256']
               for item in mentions if item['source_id'] in accepted):
            return {'ok': False, 'status': 'SOURCE_OBSERVATION_CHANGED', 'verified': 0}
    if evidence_id is None:
        evidence_id = _write_prelaunch_evidence(
            platform, keyword,
            {"ok": True, "status": "SOURCE_SCOPE_REVIEW", "raw_count": len(ids),
             "entity_mentions": mentions,
             "provenance": {"provider": provider, "scope_basis": "source_name_mention",
                            "tenant_location_asserted": False}},
            started=datetime.now().isoformat(), scope=exact, source_ids=accepted,
            review_candidates=review,
            connection=connection,
        )
    if evidence_id is None:
        raise _CollectionWriteRejected({"ok": False, "status": "SCOPE_EVIDENCE_UNAVAILABLE", "verified": 0})
    if accepted:
        _persist_prelaunch_scope(accepted, exact, evidence_id, connection=connection)
    return {"ok": True, "status": "PARTIAL" if review else "VERIFIED",
            "verified": len(accepted), "unassigned": len(review),
            "evidence_ref": evidence_id, "review_candidates": review,
            "tenant_location_asserted": False}


def _bind_collected_social_observations(stored, observations, *, scope, platform,
                                         keyword, provider, connection):
    """Keep original scope proof and current source observations distinct."""
    from .platform_naming import normalize_platform, to_canonical_record
    from .multi_platform_import import _to_note_payload
    from lumenis.shared.database.platform_content import (
        platform_records_changed, persist_verified_platform_records,
    )

    canonical_platform = normalize_platform(platform)
    if not isinstance(observations, (list, tuple)) or len(observations) != len(stored):
        raise ValueError("one captured observation is required per stored source")
    records = []
    for note, observed in zip(stored, observations):
        if not isinstance(observed, dict):
            raise ValueError("a native source observation must be a mapping")
        record = _credential_free_observations(observed)
        canonical = to_canonical_record(record, platform=canonical_platform)
        payload = _to_note_payload(canonical, record)
        if (payload.get("note_id") != note["content_id"]
                or payload.get("title", "") != (note["title"] or "")
                or payload.get("content", "") != (note["content"] or "")):
            raise ValueError("captured observation does not match the stored source")
        record.update(platform=canonical_platform, source_platform=canonical_platform,
                      content_id=note["content_id"], title=payload.get("title") or "",
                      content=payload.get("content") or "")
        records.append(record)
    if _prelaunch_scope_conflict(records, scope, connection=connection):
        raise _CollectionWriteRejected({"ok": False, "status": "SCOPE_CONFLICT", "verified": 0})
    mentions = _prelaunch_entity_mentions(records, scope, connection=connection)
    accepted = [record for record, mention in zip(records, mentions)
                if mention["status"] == "EXACT_NAME_MENTION"]
    review = [record for record, mention in zip(records, mentions)
              if mention["status"] != "EXACT_NAME_MENTION"]
    accepted_ids = [record["content_id"] for record in accepted]
    if review:
        for record in review:
            row = connection.execute("SELECT scope_status FROM notes WHERE note_id=?",
                                     (record["content_id"],)).fetchone()
            if str(row[0] or "").upper() == "VERIFIED":
                raise _CollectionWriteRejected({"ok": False, "status": "SOURCE_SCOPE_REVIEW_REQUIRED", "verified": 0})
    changed = bool(accepted) and platform_records_changed(
        accepted, platform=canonical_platform, connection=connection,
    )
    evidence_id = (_existing_prelaunch_observation_evidence(
        accepted_ids, canonical_platform, connection=connection,
    ) if accepted and not changed and not review else None)
    if evidence_id is None:
        try:
            evidence_id = _write_prelaunch_evidence(
                platform, keyword, {"ok": bool(accepted), "status": "SOURCE_SCOPE_REVIEW",
                    "raw_count": len(records), "entity_mentions": mentions,
                    "provenance": {"provider": provider, "scope_basis": "source_name_mention",
                                   "tenant_location_asserted": False}},
                started=_now(), scope=scope, source_ids=accepted_ids,
                review_candidates=review, observations=records, connection=connection,
            )
        except Exception as exc:
            raise _CollectionWriteRejected({"ok": False, "status": "EVIDENCE_WRITE_FAILED", "verified": 0}) from exc
    if evidence_id is None:
        raise _CollectionWriteRejected({"ok": False, "status": "SCOPE_EVIDENCE_UNAVAILABLE", "verified": 0})
    if accepted:
        pending = _prelaunch_scope_note_ids_needing_verification(
            accepted_ids, scope, connection=connection,
        )
        if pending:
            _persist_prelaunch_scope(pending, scope, evidence_id, connection=connection)
        _sync_prelaunch_canonical_source_fields(
            accepted_ids, scope, evidence_id=evidence_id,
            source_unchanged=not changed, connection=connection,
        )
        persist_verified_platform_records(
            accepted, platform=canonical_platform, note_ids=accepted_ids,
            evidence_id=evidence_id, scope=scope, connection=connection,
            require_observation_proof=True,
        )
    return {"ok": True, "status": "PARTIAL" if review else "VERIFIED",
            "verified": len(accepted), "unassigned": len(review),
            "evidence_ref": evidence_id, "observation_changed": changed,
            "native_fields_synced": len(accepted), "review_candidates": review,
            "tenant_location_asserted": False}


def _prelaunch_scope_note_ids_needing_verification(
    note_ids: List[str], scope: Mapping[str, Any],
    *, connection=None,
) -> List[str]:
    """Return only rows that still need their first exact-scope Evidence link."""
    import database as db

    product = "ZBMP" if scope["domain_id"] == "bmp" else "CTH"
    domain = "zbmp" if scope["domain_id"] == "bmp" else "cth"
    with (db.get_db() if connection is None else nullcontext(connection)) as conn:
        pending = []
        for note_id in note_ids:
            note = conn.execute(
                "SELECT product_id, domain_id, subject_id, brand_focus_id, "
                "scope_status, scope_evidence_ref FROM notes WHERE note_id=?",
                (note_id,),
            ).fetchone()
            canonical = conn.execute(
                "SELECT product_id, domain_id, subject_id, brand_focus_id, "
                "scope_status, scope_evidence_ref FROM canonical_data "
                "WHERE source_id=? AND product_id=? LIMIT 1", (note_id, product),
            ).fetchone()
            expected = (product, domain, scope.get("subject_id"),
                        scope.get("brand_focus_id"), "VERIFIED")
            if (note is None or canonical is None
                    or (note[0], note[1], note[2] or None, note[3] or None, note[4]) != expected
                    or (canonical[0], canonical[1], canonical[2] or None,
                        canonical[3] or None, canonical[4]) != expected
                    or not note[5] or str(note[5]) != str(canonical[5])):
                pending.append(note_id)
        return pending


def _sync_prelaunch_canonical_source_fields(
    note_ids: List[str], scope: Mapping[str, Any], *, evidence_id: int,
    source_unchanged: bool = False, connection=None,
) -> int:
    """Refresh source fields through the existing Canonical Data owner."""
    if isinstance(evidence_id, bool) or not isinstance(evidence_id, int) or evidence_id <= 0:
        raise ValueError("current observation Evidence reference must be a positive record ID")
    from dataclasses import fields

    import database as db
    from canonical_data import (
        CanonicalRecord, ensure_canonical_table, get_connection, note_to_canonical,
        persist_canonical,
    )
    from lumenis.shared.database import main_db_path

    product = "ZBMP" if scope["domain_id"] == "bmp" else "CTH"
    expected = (
        product, "zbmp" if product == "ZBMP" else "cth",
        scope.get("subject_id"), scope.get("brand_focus_id"),
        "UNASSIGNED" if scope.get("global_scope") is True else "VERIFIED",
    )
    notes = []
    existing_canonical = {}
    with (db.get_db() if connection is None else nullcontext(connection)) as conn:
        for note_id in note_ids:
            cursor = conn.execute("SELECT * FROM notes WHERE note_id=?", (note_id,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"imported note is missing: {note_id}")
            note = dict(zip((column[0] for column in cursor.description), row))
            actual = (
                note.get("product_id"), note.get("domain_id"),
                note.get("subject_id") or None, note.get("brand_focus_id") or None,
                note.get("scope_status"),
            )
            if actual != expected or (expected[-1] == "VERIFIED" and not note.get("scope_evidence_ref")):
                raise ValueError(f"imported note has no matching signed scope: {note_id}")
            notes.append(note)
            if source_unchanged:
                canonical_cursor = conn.execute(
                    "SELECT * FROM canonical_data WHERE source_id=? AND product_id=? LIMIT 1",
                    (note_id, product),
                )
                canonical_row = canonical_cursor.fetchone()
                if canonical_row is not None:
                    canonical_values = dict(zip(
                        (column[0] for column in canonical_cursor.description), canonical_row,
                    ))
                    existing_canonical[note_id] = CanonicalRecord(**{
                        field.name: canonical_values[field.name]
                        for field in fields(CanonicalRecord)
                        if field.name in canonical_values
                    })

    if connection is not None:
        for note in notes:
            canonical = note_to_canonical(note, product_id=product)
            if source_unchanged and note["note_id"] in existing_canonical:
                current_metrics = canonical
                canonical = existing_canonical[note["note_id"]]
                canonical.engagement_likes = current_metrics.engagement_likes
                canonical.engagement_comments = current_metrics.engagement_comments
                canonical.engagement_collects = current_metrics.engagement_collects
                canonical.engagement_shares = current_metrics.engagement_shares
            canonical.evidence_ref = str(evidence_id)
            persist_canonical(connection, canonical)
    else:
        db_path = main_db_path()
        ensure_canonical_table(db_path)
        conn = get_connection(db_path)
        try:
            for note in notes:
                canonical = note_to_canonical(note, product_id=product)
                if source_unchanged and note["note_id"] in existing_canonical:
                    current_metrics = canonical
                    canonical = existing_canonical[note["note_id"]]
                    canonical.engagement_likes = current_metrics.engagement_likes
                    canonical.engagement_comments = current_metrics.engagement_comments
                    canonical.engagement_collects = current_metrics.engagement_collects
                    canonical.engagement_shares = current_metrics.engagement_shares
                canonical.evidence_ref = str(evidence_id)
                persist_canonical(conn, canonical)
            conn.commit()
        finally:
            conn.close()
    return len(notes)


def _existing_prelaunch_observation_evidence(
    note_ids: List[str], platform: str,
    *, connection=None,
) -> int | None:
    """Reuse the latest matching observation Evidence on an unchanged public page."""
    if not note_ids:
        return None
    from lumenis.shared.database import get_repository

    evidence_ids = set()
    with (get_repository().transaction() if connection is None else nullcontext(connection)) as conn:
        for note_id in note_ids:
            row = conn.execute(
                "SELECT raw_data FROM platform_contents "
                "WHERE platform=? AND platform_content_id=?",
                (platform, note_id),
            ).fetchone()
            if row is None:
                return None
            try:
                observation = json.loads(row[0] or "{}")
            except (TypeError, ValueError):
                return None
            evidence_id = observation.get("_lumenis_evidence_id")
            if type(evidence_id) is not int or evidence_id <= 0:
                return None
            evidence_ids.add(evidence_id)
        if len(evidence_ids) != 1:
            return None
        evidence_id = next(iter(evidence_ids))
        cursor = conn.execute("SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        from lumenis.shared.evidence.store import classify_evidence_integrity
        evidence = dict(zip((column[0] for column in cursor.description), row))
        try:
            inputs = json.loads(evidence.get("inputs_json") or "{}")
        except (TypeError, ValueError):
            return None
        if (not classify_evidence_integrity(evidence).get("verified")
                or str(evidence.get("result") or "").upper() != "PASS"
                or str(evidence.get("status") or "").lower() != "verified"
                or set(inputs.get("source_ids") or ()) != set(note_ids)):
            return None
        return evidence_id


def _write_evidence(platform: str, keyword: str, result: Dict[str, Any], *, started: str) -> int | None:
    try:
        _ensure_evidence_schema()
        from lumenis.shared.evidence.store import record_collection_evidence

        status = result.get("status") or "COLLECT_ERROR"
        provenance = result.get("provenance") if isinstance(result.get("provenance"), dict) else {}
        evidence_id = record_collection_evidence(
            account=f"CTH_{platform.upper()}_RUNTIME",
            platform=platform,
            notes_collected=result.get("raw_count"),
            notes_filtered=result.get("filtered_count"),
            notes_inserted=int(result.get("imported", 0) or 0),
            notes_updated=int(result.get("updated", 0) or 0),
            duration_ms=int(result.get("duration_ms", 0) or 0),
            result="PASS" if status in {"SUCCESS", "NO_NEW_DATA"} else "FAIL",
            error_type=result.get("error_type", ""),
            error_message=result.get("error", ""),
            session_state=result.get("health_status", ""),
            keywords=[keyword],
            started_at=started,
            version="secondary-collection-v1",
            feature_id=f"CTH_{platform.upper()}_COLLECT",
            provider=provenance.get("provider") or "unreported",
            source=provenance.get("source") or f"platform:{platform}",
            collected_at=provenance.get("collected_at") or "",
            collection_metadata=provenance,
        )
        return evidence_id if isinstance(evidence_id, int) and not isinstance(evidence_id, bool) and evidence_id > 0 else None
    except Exception:
        return None


def _manual_collection_approval_resource(
    scope, platform, keyword, max_results, receipt, *, max_scroll=None,
):
    """Bind approval to the server identity and the exact bounded source request."""
    binding = {
        "module": "collector", "action": "write", "platform": platform,
        "keyword": keyword, "max_results": max_results,
        "domain_id": scope["domain_id"], "global_scope": scope["global_scope"],
        "subject_id": scope["subject_id"], "brand_focus_id": scope["brand_focus_id"],
        "actor_id": receipt.actor_id, "principal_kind": receipt.principal_kind,
        "principal_ref": receipt.principal_ref,
    }
    if max_scroll is not None:
        binding["max_scroll"] = max_scroll
    encoded = json.dumps(binding, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "collector-source-import:v1:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _manual_collection_guard(actor, scope, platform, keyword, max_results, *, max_scroll=None):
    """Check live Collector admission and separate import approval; never grant it."""
    from lumenis.system.security import (
        LocalWorkspacePrincipal, OperationType, check_actor_scope_permission,
        check_local_workspace_scope_permission, get_permission_gate,
        is_testing_bypass_enabled,
    )

    def denied(status, **extra):
        return None, {
            "ok": False, "status": status, "platform": platform, "keyword": keyword,
            "read_only": True, "external_write": False, **extra,
        }

    if max_scroll is not None:
        canonical_platform = str(platform or "").strip().lower()
        if canonical_platform == "xhs":
            canonical_platform = "xiaohongshu"
        if canonical_platform != "xiaohongshu":
            return denied("NOT_SUPPORTED", network_attempted=False,
                          persistence_attempted=False)
        if (type(max_scroll) is not int
                or not 1 <= max_scroll <= MAX_XHS_SCROLL):
            return denied("INVALID_SCROLL_LIMIT", network_attempted=False,
                          persistence_attempted=False)

    if actor is None:
        return denied("AUTH_REQUIRED")
    if not isinstance(scope, Mapping) or type(scope.get("global_scope")) is not bool:
        return denied("SCOPE_UNAUTHORIZED")
    domain = scope.get("domain_id")
    if not isinstance(domain, str):
        return denied("SCOPE_UNAUTHORIZED")
    domain = domain.strip().lower()
    if domain == "zbmp":
        domain = "bmp"
    if domain not in {"cth", "bmp"}:
        return denied("SCOPE_UNAUTHORIZED")
    exact = {
        "domain_id": domain, "global_scope": scope["global_scope"],
        "subject_id": scope.get("subject_id"), "brand_focus_id": scope.get("brand_focus_id"),
    }
    try:
        if is_testing_bypass_enabled():
            return denied("PERMISSION_UNAVAILABLE")
        gate = get_permission_gate()
        check = (check_local_workspace_scope_permission
                 if type(actor) is LocalWorkspacePrincipal else check_actor_scope_permission)
        receipt = check(actor, module="collector", action="write", gate=gate, **exact)
        if receipt.verification_state != "verified":
            return denied("PERMISSION_UNAVAILABLE")
        if receipt.allowed is not True:
            return denied("SCOPE_UNAUTHORIZED")
        resource = _manual_collection_approval_resource(
            exact, platform, keyword, max_results, receipt,
            max_scroll=max_scroll,
        )
        approval = gate.check(
            OperationType.DATA_IMPORT, resource,
            caller=(f"account:{receipt.actor_id}" if receipt.actor_id is not None
                    else receipt.principal_ref),
            domain_id="zbmp" if domain == "bmp" else "cth",
            exact_approval_required=True,
        )
        if approval.allowed is not True:
            return denied(
                "APPROVAL_REQUIRED" if approval.requires_approval else "SCOPE_UNAUTHORIZED",
                approval_resource=resource,
            )
        return exact, None
    except Exception:
        return denied("PERMISSION_UNAVAILABLE")


class _CollectionWriteRejected(Exception):
    """Abort the scoped transaction without publishing partial write success."""

    def __init__(self, result):
        self.result = result
        super().__init__(str(result.get("status") or "COLLECTION_WRITE_FAILED"))


def _task_commit_binding(operation_key, actor, scope, operator, authorization,
                         platform, keyword, max_results, business_query):
    """Server-only task instance plus exact authorized operation, never an HTTP field."""
    if not isinstance(operation_key, str) or not operation_key:
        raise ValueError("invalid server collection operation")
    from lumenis.system.security.permission import LocalWorkspacePrincipal
    if type(actor) is LocalWorkspacePrincipal:
        identity = {"principal_ref": actor.principal_ref}
    elif isinstance(actor, dict) and type(actor.get("id")) is int:
        identity = {"actor_id": actor["id"]}
    elif operator == "prelaunch_maintenance" and authorization is not None:
        identity = {"maintenance_plan": authorization.plan_id}
    else:
        raise PermissionError("server collection identity required")
    material = {"operation_key": operation_key, "identity": identity,
        "scope": dict(scope), "operator": operator, "platform": platform,
        "keyword": keyword, "max_results": max_results,
        "query": business_query.to_dict() if business_query is not None else None}
    return json.loads(json.dumps(material, sort_keys=True, ensure_ascii=False))


def _task_commit_receipt(connection, binding, result=None):
    """Existing signed Evidence transaction receipt, not collected source truth.

    Caller holds BEGIN IMMEDIATE when writing. The serialized lookup+insert is
    the uniqueness fence for this feature/asset key; no parallel task store.
    """
    from lumenis.shared.evidence.store import classify_evidence_integrity, record_evidence
    key = "collector-task:" + hashlib.sha256(json.dumps(binding, sort_keys=True,
        ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='app_evidence_records'").fetchone():
        if result is None:
            return None
        raise ValueError("source Evidence schema unavailable")
    rows = connection.execute("SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=?",
        ("COLLECTOR_TASK_COMMIT", key)).fetchall()
    if rows:
        row = dict(rows[0])
        if (len(rows) != 1 or row.get("version") != "collector-task-commit:v1"
                or row.get("result") != "PASS"
                or classify_evidence_integrity(row).get("assurance") != "writer-authenticated"
                or json.loads(row["inputs_json"]).get("binding") != binding):
            raise ValueError("COLLECTION_COMMIT_RECEIPT_UNVERIFIED")
        saved = json.loads(row["outputs_json"])["result"]
        source_ref = json.loads(row["inputs_json"]).get("source_evidence_ref")
        if not isinstance(source_ref, str) or not source_ref.startswith("app_evidence_records:"):
            raise ValueError("COLLECTION_SOURCE_RECEIPT_UNVERIFIED")
        source_row = connection.execute("SELECT * FROM app_evidence_records WHERE id=?",
            (int(source_ref.split(":", 1)[1]),)).fetchone()
        if source_row is None or classify_evidence_integrity(dict(source_row)).get("assurance") != "writer-authenticated":
            raise ValueError("COLLECTION_SOURCE_RECEIPT_UNVERIFIED")
        if result is not None:
            raise ValueError("COLLECTION_COMMIT_ALREADY_EXISTS")
        return {**saved, "task_commit_evidence_ref": "app_evidence_records:" + str(row["id"]),
                "commit_reconciled": True, "network_attempted": False,
                "historical_commit_verified": True, "refresh_verified": False}
    if result is None:
        return None
    if result.get("ok") is not True:
        result.update(source_status=result.get("status"), status="PARTIAL_COMMITTED",
                      retry_safe=False, new_collection_required=True,
                      recovery_action="REVIEW_COMMITTED_SOURCES_THEN_CREATE_NEW_REQUEST")
    scope = binding["scope"]
    evidence_id = record_evidence(source="collector", feature_id="COLLECTOR_TASK_COMMIT",
        asset_id=key, version="collector-task-commit:v1", capture_mode="derived_task_commit",
        inputs={"binding": binding, "source_evidence_ref": "app_evidence_records:" + str(result.get("evidence_ref"))},
        collection_metadata={"kind": "DERIVATIVE_EXECUTION_OUTCOME", "grants_source_use": False},
        outputs={"result": result}, result="PASS",
        actual="SOURCE_TRANSACTION_COMMITTED", provider="collector_task_transaction",
        product="CTH" if scope["domain_id"] == "cth" else "ZBMP",
        domain_id="cth" if scope["domain_id"] == "cth" else "zbmp",
        subject_id=scope.get("subject_id"), brand_focus_id=scope.get("brand_focus_id"),
        global_scope=scope.get("global_scope", False), connection=connection)
    if type(evidence_id) is not int or evidence_id <= 0:
        raise ValueError("COLLECTION_COMMIT_RECEIPT_UNAVAILABLE")
    result["task_commit_evidence_ref"] = "app_evidence_records:" + str(evidence_id)
    return result


def collect_search(platform: str, keyword: str, *, max_results: int = MAX_RESULTS,
                   operator: str = "human", scope: Mapping[str, Any] | None = None,
                   actor: Any = None,
                   max_scroll: int | None = None,
                   prelaunch_local_import: bool = False,
                   prelaunch_authorization: Any = None,
                   raw_capture: PublicRawCapture | None = None,
                   business_query: Any = None,
                   native_capture: NativePublicCapture | None = None,
                   attempt_guard=None, operation_key=None) -> Dict[str, Any]:
    """Run one explicit, read-only platform search and persist its evidence."""
    operator = str(operator or "").strip().lower()
    maintenance_operator = operator == "prelaunch_maintenance"
    if operator not in {"human", "human_ui", "prelaunch_maintenance"}:
        raise PermissionError("该采集入口只接受人工触发或签名预发布维护计划")
    if maintenance_operator and not prelaunch_local_import:
        return {"ok": False, "status": "SCOPE_UNAUTHORIZED", "platform": platform,
                "keyword": keyword, "read_only": True, "external_write": False}
    if max_scroll is not None:
        requested_platform = str(platform or "").strip().lower()
        if requested_platform == "xhs":
            requested_platform = "xiaohongshu"
        if requested_platform != "xiaohongshu":
            return {"ok": False, "status": "NOT_SUPPORTED", "platform": requested_platform,
                    "keyword": keyword, "read_only": True, "external_write": False,
                    "network_attempted": False, "persistence_attempted": False}
        if type(max_scroll) is not int or not 1 <= max_scroll <= MAX_XHS_SCROLL:
            return {"ok": False, "status": "INVALID_SCROLL_LIMIT", "platform": requested_platform,
                    "keyword": keyword, "read_only": True, "external_write": False,
                    "network_attempted": False, "persistence_attempted": False}
        # Scroll depth is an exact manual XHS acquisition boundary. Other
        # import modes use their own signed request contract and cannot accept it.
        if prelaunch_local_import or raw_capture is not None or native_capture is not None:
            return {"ok": False, "status": "NOT_SUPPORTED", "platform": requested_platform,
                    "keyword": keyword, "read_only": True, "external_write": False,
                    "network_attempted": False, "persistence_attempted": False}
    if platform == "xhs":
        platform = "xiaohongshu"
    platform, keyword, max_results = _validate_request(platform, keyword, max_results)
    permission_keyword = keyword
    if native_capture is not None:
        try:
            if raw_capture is not None or prelaunch_local_import or operator not in {"human", "human_ui"}:
                raise ValueError("frozen native import requires the real manual caller")
            native_value = _native_capture_record(native_capture)
            if native_capture.platform != platform or native_value["source_url"] != keyword:
                raise ValueError("native capture platform/source mismatch")
            permission_keyword = native_capture_permission_keyword(native_capture)
        except NativeCaptureError as exc:
            return {"ok":False,"status":exc.code,"platform":platform,
                    "network_attempted":False,"persistence_attempted":False}
        except (TypeError, ValueError, AttributeError):
            return {"ok":False,"status":"INVALID_NATIVE_CAPTURE","platform":platform,
                    "network_attempted":False,"persistence_attempted":False}
    if business_query is not None:
        from ..acquisition_plan import AcquisitionQuery
        from .platform_naming import normalize_platform
        if (type(business_query) is not AcquisitionQuery
                or not business_query.business_context
                or business_query.keyword != keyword
                or normalize_platform(business_query.business_context.get('platform')) != platform):
            raise ValueError('business query must match the exact planned platform and keyword')
        query_domain = 'cth' if business_query.domain_id == 'CTH' else 'bmp'
        scope_domain = (scope or {}).get('domain_id') if isinstance(scope, Mapping) else None
        if scope_domain == 'zbmp':
            scope_domain = 'bmp'
        if scope_domain != query_domain:
            raise ValueError('business query domain must match the authorized source scope')
    if raw_capture is not None:
        try:
            if (not prelaunch_local_import or operator != "human" or actor is not None
                    or platform != "public_http" or raw_capture.source_url != keyword):
                raise ValueError("explicit approved public Raw intake required")
            _public_raw_material(raw_capture)
        except (AttributeError, TypeError, ValueError):
            return {"ok": False, "status": "INVALID_ORIGINAL_CAPTURE", "platform": platform,
                    "keyword": keyword, "read_only": True, "external_write": False}
    manual_scope = None
    if not prelaunch_local_import:
        manual_scope, denial = _manual_collection_guard(
            actor, scope, platform, permission_keyword, max_results,
            max_scroll=max_scroll,
        )
        if denial is not None:
            return denial
    if _blocked_youtube_atom_feed(platform, keyword):
        return {
            "ok": False, "status": "BLOCKED", "platform": platform,
            "keyword": keyword, "read_only": True, "external_write": False,
            "error_type": "SOURCE_POLICY",
        }
    prelaunch_scope = (
        manual_scope if manual_scope and not manual_scope["global_scope"] else None
    )
    if prelaunch_local_import:
        from .scheduling.prelaunch_baseline import PURPOSE_POLICY
        purpose_maintenance = (maintenance_operator and
                               getattr(prelaunch_authorization, "policy_id", None) == PURPOSE_POLICY)
        permitted_platforms = ({"xiaohongshu", "douyin", "x", "instagram", "facebook", "wechat"}
                               if purpose_maintenance else {"public_http", "web_atom"}
                               if maintenance_operator else {"public_http", "web_atom", "douyin", "x"})
        if (actor is not None
                or platform not in permitted_platforms
                or (operator != "human" and not maintenance_operator)):
            return {"ok": False, "status": "SCOPE_UNAUTHORIZED", "platform": platform,
                    "keyword": keyword, "read_only": True, "external_write": False}
        try:
            prelaunch_scope = _prelaunch_scope(scope)
            if maintenance_operator:
                from .scheduling.prelaunch_baseline import PrelaunchMaintenanceAuthorization
                if (not isinstance(prelaunch_authorization, PrelaunchMaintenanceAuthorization)
                        or not prelaunch_authorization.matches_request(
                            source_url=keyword, platform=platform, scope=prelaunch_scope)):
                    raise PermissionError("signed exact baseline plan required")
            if maintenance_operator:
                authorized = _authorize_prelaunch_public(
                    prelaunch_scope, keyword, platform,
                    maintenance_authorization=prelaunch_authorization,
                    business_query=business_query, max_results=max_results,
                )
            elif platform in {"douyin", "x"}:
                authorized = _authorize_prelaunch_manual(
                    prelaunch_scope, keyword, platform=platform,
                )
            else:
                authorized = _authorize_prelaunch_public(prelaunch_scope, keyword, platform, raw_capture=raw_capture)
            if not authorized:
                raise PermissionError("exact import approval unavailable")
            _validate_prelaunch_registry(prelaunch_scope)
        except Exception:
            return {"ok": False, "status": "SCOPE_UNAUTHORIZED", "platform": platform,
                    "keyword": keyword, "read_only": True, "external_write": False}
    task_binding = None
    if operation_key is not None:
        task_binding = _task_commit_binding(operation_key, actor, manual_scope or prelaunch_scope,
            operator, prelaunch_authorization, platform, keyword, max_results, business_query)
        import database as db
        try:
            with db.get_db() as receipt_conn:
                committed = _task_commit_receipt(receipt_conn, task_binding)
            if committed is not None:
                return committed
        except Exception:
            return {"ok": False, "status": "COLLECTION_COMMIT_UNVERIFIED",
                    "network_attempted": False, "persistence_attempted": False,
                    "platform": platform, "keyword": keyword}
    policy = CollectionHygienePolicy(
        platform=platform,
        read_only=True,
        public_data_only=True,
        single_local_account=True,
        allow_account_pool=False,
        allow_proxy_pool=False,
        min_interval_seconds=MIN_INTERVAL_SECONDS,
        max_batch=MAX_RESULTS,
        write_enabled=False,
        human_confirmation_required_for_write=True,
        deployment_target="internal",
    )
    policy_errors = policy.validate()
    if policy_errors:
        raise RuntimeError("采集安全策略未通过: " + ",".join(policy_errors))
    governor = RateGovernor(policy)
    if not governor.within_batch(max_results):
        return {
            "ok": False, "status": "RATE_LIMITED", "platform": platform,
            "keyword": keyword, "read_only": True, "external_write": False,
            "error_type": "BATCH_LIMIT",
        }

    if policy.daily_cap is not None:
        used_today = _daily_action_count(platform, datetime.now())
        if used_today is None:
            return {
                "ok": False, "status": "POLICY_STATE_UNAVAILABLE", "platform": platform,
                "keyword": keyword, "read_only": True, "external_write": False,
                "error_type": "COLLECTION_LIMIT_STATE_UNAVAILABLE",
            }
        if not governor.within_daily_cap(used_today):
            return {
                "ok": False, "status": "RATE_LIMITED", "platform": platform,
                "keyword": keyword, "read_only": True, "external_write": False,
                "error_type": "DAILY_COLLECTION_CAP",
            }

    lock = _locks[platform]
    if not lock.acquire(blocking=False):
        return {
            "ok": False, "status": "BUSY", "platform": platform, "keyword": keyword,
            "read_only": True, "external_write": False, "error_type": "COLLECTION_BUSY",
        }
    started_at = _now()
    started_monotonic = time.monotonic()
    worker_recovery = None
    try:
        with _last_action_lock:
            previous = _last_action[platform] or None
            allowed, wait = governor.permit(time.monotonic(), previous)
            if not allowed:
                wait = round(wait, 2)
                return {
                    "ok": False, "status": "RATE_LIMITED", "platform": platform,
                    "keyword": keyword, "wait_seconds": wait, "read_only": True,
                    "external_write": False, "error_type": "LOCAL_RATE_LIMIT",
                }
            _last_action[platform] = time.monotonic()

        if (maintenance_operator and raw_capture is None and native_capture is None
                and prelaunch_scope is not None
                and platform in {"douyin", "x", "instagram", "facebook"}):
            if not _authorize_prelaunch_public(
                    prelaunch_scope, keyword, platform,
                    maintenance_authorization=prelaunch_authorization,
                    business_query=business_query, max_results=max_results):
                return {"ok": False, "status": "SCOPE_UNAUTHORIZED", "platform": platform,
                        "keyword": keyword, "read_only": True, "external_write": False}
            from lumenis.adapters.human_browser import recover_registered_readonly_worker
            worker_recovery = recover_registered_readonly_worker(platform, mode="BACKGROUND")

        health = ({"status": "LOCAL_CAPTURE_INPUT", "can_attempt": True,
                   "healthcheck_scope": "local_original_capture_only"} if raw_capture is not None or native_capture is not None else (
            _adapter_health(platform, url=keyword)
            if platform in {"public_http", "web_atom", "sitemap", "instagram", "wechat"} else _adapter_health(platform)
        ))


        health_status = health.get("status", "UNAVAILABLE")
        if not health.get("can_attempt", health.get("ready", False)):
            finished = _now()
            error = f"{health_status}: {_status_message(health_status)}"
            result = {
                "ok": False, "status": health_status, "platform": platform,
                "keyword": keyword, "raw_count": None, "returned_count": None,
                "imported": 0, "updated": 0, "filtered_count": None,
                "health_status": health_status, "error": error,
                "error_type": "PREFLIGHT_NOT_READY", "read_only": True,
                "external_write": False, "publish_authority": "human_manual_only",
                "duration_ms": int((time.monotonic() - started_monotonic) * 1000),
            }
            result["provenance"] = _credential_free_observations(health.get("metadata") or {})
            if worker_recovery is not None:
                result["provenance"]["worker_recovery"] = worker_recovery
            if maintenance_operator:
                result["provenance"].update(
                    maintenance_plan_id=prelaunch_authorization.plan_id,
                    authorization_ref=prelaunch_authorization.authorization_ref,
                    source_version=prelaunch_authorization.source_version,
                    scope_version=prelaunch_authorization.scope_version,
                )
            if prelaunch_scope is not None:
                evidence_id = _write_prelaunch_evidence(
                    platform, keyword, result, started=started_at,
                    scope=prelaunch_scope, source_ids=[], manual=manual_scope is not None,
                )
            else:
                evidence_id = _write_evidence(platform, keyword, result, started=started_at)
            result["evidence_recorded"] = evidence_id is not None
            result["evidence_id"] = evidence_id
            if evidence_id is None:
                result.update({
                    "ok": False,
                    "status": "EVIDENCE_WRITE_FAILED",
                    "error_type": "EVIDENCE_WRITE_FAILED",
                    "error": f"EVIDENCE_WRITE_FAILED: {_status_message('EVIDENCE_WRITE_FAILED')}",
                })
            _write_run_log(platform, keyword, started=started_at, finished=finished,
                           fetched=None, accepted=None, rejected=None, error=result["error"])
            return result

        collection = None
        acquisition_fingerprint = None
        try:
            search_kwargs = {"max_results": max_results}
            if max_scroll is not None:
                search_kwargs["max_scroll"] = max_scroll
            if platform == "instagram" and business_query is not None:
                native_topic_reference = business_query.business_context.get("user_seed_topic_ref")
                if isinstance(native_topic_reference, dict):
                    # The platform adapter revalidates the original reviewed
                    # native tag; a free-text query never becomes a hashtag.
                    search_kwargs["native_topic_reference"] = dict(native_topic_reference)
            if (platform == "xiaohongshu" and maintenance_operator
                    and prelaunch_scope is not None and business_query is not None):
                search_kwargs["detail_media_mode"] = "cover_only"
            if platform in {"xiaohongshu", "x"} and business_query is not None:
                # This operational binding distinguishes task-selected source
                # checkpoints; it grants neither identity nor collection scope.
                binding = {"query": business_query.to_dict(),
                           "scope": prelaunch_scope or manual_scope,
                           "plan_id": getattr(prelaunch_authorization, "plan_id", None)}
                acquisition_fingerprint = hashlib.sha256(
                    json.dumps(binding, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":")).encode("utf-8")).hexdigest()
                search_kwargs["acquisition_fingerprint"] = acquisition_fingerprint
            collection = (_native_capture_collection(native_capture) if native_capture is not None else
                          _public_raw_collection(raw_capture) if raw_capture is not None
                          else _get_runtime_adapter(platform).search(keyword, **search_kwargs))
            if not isinstance(collection, CollectionResult):
                raise TypeError("adapter returned a non-CollectionResult value")
            if native_capture is None and raw_capture is None:
                bind_collection_route(
                    collection, platform=platform, capability="search", request_value=keyword,
                )
        except RouteIdentityMismatch as exc:
            source_result = collection if isinstance(collection, CollectionResult) else None
            source_metadata = (
                source_result.metadata if source_result is not None
                and isinstance(source_result.metadata, dict) else {}
            )
            source_provenance = {
                "route_state": "IDENTITY_MISMATCH",
                "requested_platform": platform,
                "source_platform": source_result.platform if source_result is not None else None,
                "actual_access_state": "ATTEMPTED_ONLY",
                "error_type": type(exc).__name__,
            }
            actual_provider = source_metadata.get("provider") or source_metadata.get("engine")
            if actual_provider:
                source_provenance["provider"] = str(actual_provider)[:100]
            collection = CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=platform,
                message="adapter result identity did not match the requested platform",
                metadata={"error_type": type(exc).__name__},
                provenance=source_provenance,
            )
        except Exception as exc:
            if raw_capture is not None:
                return {"ok": False, "status": "INVALID_ORIGINAL_CAPTURE", "platform": platform,
                        "keyword": keyword, "error_type": type(exc).__name__,
                        "read_only": True, "external_write": False}
            collection = CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=platform,
                message="provider request failed",
                metadata={"error_type": type(exc).__name__},
            )
        status = _canonical_status(collection)
        items = [item for item in (collection.items or []) if isinstance(item, dict)]
        captured_at = (native_value["capture_observation_native"] if native_capture is not None else
                       raw_capture.captured_at if raw_capture is not None else
                       datetime.now().astimezone().isoformat(timespec="seconds"))
        records = [_native_record(item, platform, keyword, captured_at) for item in items]
        # Keep the observed originals independently of lexical/identity review.
        # These records are still subject to current import authorization and
        # source validation; they never establish an entity binding by themselves.
        original_observation_records = list(records)
        business_reviews = []
        business_observed_at = None
        if business_query is not None:
            from datetime import timezone
            business_observed_at = (raw_capture.captured_at if raw_capture is not None
                                    else datetime.now(timezone.utc).isoformat())
            business_reviews = _business_source_reviews(records, business_query, business_observed_at)
        if manual_scope is not None:
            _, denial = _manual_collection_guard(
                actor, manual_scope, platform, permission_keyword, max_results,
                max_scroll=max_scroll,
            )
            if denial is not None:
                return denial
        source_item_count = len(items)
        entity_mentions = []
        review_pending = []
        review_candidates = []
        if business_reviews:
            accepted_indices = [index for index, review in enumerate(business_reviews)
                                if review['status'] == 'CANDIDATE_TASK_RELEVANT']
            review_candidates = [record for index, record in enumerate(records) if index not in accepted_indices]
            review_pending = [review for review in business_reviews if review['status'] != 'CANDIDATE_TASK_RELEVANT']
            records = [records[index] for index in accepted_indices]
            items = [items[index] for index in accepted_indices]
        if (prelaunch_scope is not None and collection.ok and records
                and (manual_scope is not None or business_query is not None or platform in {"douyin", "x"})):
            entity_mentions = _prelaunch_entity_mentions(records, prelaunch_scope)
            review_pending += [item for item in entity_mentions if item["status"] != "EXACT_NAME_MENTION"]
            accepted_indices = [i for i, item in enumerate(entity_mentions) if item["status"] == "EXACT_NAME_MENTION"]
            review_candidates += [record for i, record in enumerate(records) if i not in accepted_indices]
            records = [records[i] for i in accepted_indices]
            items = [items[i] for i in accepted_indices]
        if (maintenance_operator and prelaunch_scope is not None
                and not _authorize_prelaunch_public(
                    prelaunch_scope, keyword, platform,
                    maintenance_authorization=prelaunch_authorization,
                    business_query=business_query, max_results=max_results,
                )):
            return {
                "ok": False, "status": "SCOPE_UNAUTHORIZED",
                "platform": platform, "keyword": keyword,
                "read_only": True, "external_write": False,
                "publish_authority": "human_manual_only",
            }
        if (prelaunch_local_import and platform in {"douyin", "x"} and prelaunch_scope is not None
                and not maintenance_operator
                and not _authorize_prelaunch_manual(
                    prelaunch_scope, keyword, platform=platform,
                )):
            return {
                "ok": False, "status": "SCOPE_UNAUTHORIZED",
                "platform": platform, "keyword": keyword,
                "read_only": True, "external_write": False,
                "publish_authority": "human_manual_only",
            }
        metadata = collection.metadata if isinstance(collection.metadata, dict) else {}
        provenance = dict(collection.provenance) if isinstance(collection.provenance, dict) else {}
        if worker_recovery is not None:
            provenance["worker_recovery"] = worker_recovery
        actual_provider = metadata.get("provider") or metadata.get("engine")
        if actual_provider:
            provenance.setdefault("provider", str(actual_provider)[:100])
        provenance.setdefault("source", str(metadata.get("source") or f"platform:{platform}")[:180])
        provenance.setdefault("collected_at", str(metadata.get("collected_at") or captured_at)[:40])
        if max_scroll is not None:
            provenance["max_scroll"] = max_scroll
        if native_capture is not None:
            provenance["native_capture_sha256"] = native_capture.sha256
            provenance["source_version"] = native_capture.sha256
            provenance["intake_mode"] = "FROZEN_NATIVE_ORIGINAL_NO_NETWORK"
            provenance["source_lineage"] = native_value["source_lineage"]
            provenance["rights"] = native_value.get("rights")
            provenance["native_publication_state"] = native_value.get("publication_since_2026")
        if metadata.get("error_type"):
            provenance["error_type"] = str(metadata["error_type"])[:80]
        if isinstance(metadata.get("detail"), dict):
            # Preserve the adapter's observed per-post work separately from
            # source-scope admission and the query's final result.
            provenance["native_detail_observation"] = _credential_free_observations(metadata["detail"])
        if isinstance(metadata.get("continuation"), dict):
            provenance["native_acquisition_continuation"] = _credential_free_observations(metadata["continuation"])
        if business_query is not None:
            provenance['planned_business_query'] = business_query.to_dict()
            provenance['business_source_reviews'] = business_reviews
            provenance['actual_response_observation_utc'] = business_observed_at
            provenance['query_scope_role'] = 'PLANNED_TARGET_NOT_SOURCE_ENTITY_BINDING'
        if maintenance_operator:
            provenance["maintenance_plan_id"] = prelaunch_authorization.plan_id
            provenance["authorization_ref"] = prelaunch_authorization.authorization_ref
            provenance["source_version"] = prelaunch_authorization.source_version
            provenance["scope_version"] = prelaunch_authorization.scope_version

        import database as db
        # Fetch one observed cover for each eligible original observation,
        # including posts that remain pending entity assignment. Network work
        # stays outside the DB writer and under the exact current authorization.
        live_covers = {}
        if (maintenance_operator and prelaunch_scope is not None
                and original_observation_records and collection.ok is True
                and status in {"SUCCESS", "NO_NEW_DATA"} and platform in {
                    "xiaohongshu", "douyin", "x", "instagram", "facebook", "wechat"}):
            if _authorize_prelaunch_public(
                    prelaunch_scope, keyword, platform,
                    maintenance_authorization=prelaunch_authorization,
                    business_query=business_query, max_results=max_results):
                from concurrent.futures import ThreadPoolExecutor
                from .public_source import fetch_observed_post_cover
                from .platform_naming import normalize_content_id
                excluded_statuses = {
                    "EXCLUDED_TASK_BOUNDARY", "OUTSIDE_REQUESTED_PUBLICATION_PERIOD"}
                excluded_native_ids = set()
                for review in business_reviews:
                    if not isinstance(review, dict) or review.get("status") not in excluded_statuses:
                        continue
                    review_id = normalize_content_id(platform, review.get("platform_content_id"))
                    if review_id:
                        excluded_native_ids.add(str(review_id))
                cover_candidates = []
                seen_native_ids = set()
                for record in original_observation_records[:max_results]:
                    try:
                        native_id, _ = _verified_live_native_observation(platform, record)
                    except (TypeError, ValueError):
                        continue
                    if native_id in excluded_native_ids or native_id in seen_native_ids:
                        continue
                    seen_native_ids.add(native_id)
                    cover_candidates.append((native_id, record))
                    if len(cover_candidates) >= max_results:
                        break

                def fetch_cover(candidate):
                    native_id, record = candidate
                    try:
                        cover = fetch_observed_post_cover(platform, record)
                    except Exception:
                        cover = {"status": "NULL", "reason": "COVER_FETCH_UNAVAILABLE"}
                    return native_id, cover

                # Each helper call owns its public session. Keep the existing
                # two-worker cap and map every receipt to its verified native ID.
                try:
                    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="collector-cover") as executor:
                        for native_id, cover in executor.map(fetch_cover, cover_candidates):
                            live_covers[native_id] = cover
                except Exception:
                    for native_id, _ in cover_candidates:
                        live_covers.setdefault(
                            native_id, {"status": "NULL", "reason": "COVER_FETCH_UNAVAILABLE"})
        staged_source_paths = []
        source_files_committed = False
        result = None
        try:
            # Reserve the writer before checking either source owner. Every
            # scoped write below uses this connection and commits only after
            # the final permission check, including Evidence and native fields.
            # Server-owned queue fence spans only this existing transaction,
            # after acquisition. Reapers cannot supersede the active lease
            # between the identity check and the business commit.
            from contextlib import nullcontext
            with (attempt_guard() if attempt_guard is not None else nullcontext(True)) as attempt_active, db.get_db() as conn:
                if attempt_active is not True:
                    raise _CollectionWriteRejected({"ok": False, "status": "STALE_ATTEMPT",
                        "platform": platform, "read_only": True, "external_write": False})
                conn.execute("BEGIN IMMEDIATE")
                if raw_capture is not None and not _authorize_prelaunch_public(
                    prelaunch_scope, keyword, platform, raw_capture=raw_capture,
                ):
                    raise _CollectionWriteRejected({"ok": False, "status": "SCOPE_UNAUTHORIZED",
                        "platform": platform, "keyword": keyword,
                        "read_only": True, "external_write": False})
                if raw_capture is not None:
                    _validate_prelaunch_registry(prelaunch_scope, connection=conn)
                prelaunch_observation_changed = False
                if (prelaunch_scope is not None or manual_scope is not None) and records:
                    from lumenis.shared.database.platform_content import platform_records_changed

                    prelaunch_observation_changed = platform_records_changed(records, platform=platform, connection=conn)
                prelaunch_scope_conflict = bool(
                    (prelaunch_scope is not None or manual_scope is not None) and items
                    and _prelaunch_scope_conflict(records, prelaunch_scope or manual_scope, connection=conn)
                )
                import_result: Dict[str, Any] = {"imported": 0, "updated": 0, "failed": 0, "details": []}
                subject = {"subject_matches": 0, "canonical_synced": 0, "subjects": []}
                note_ids: List[str] = []
                if items and collection.ok and not prelaunch_scope_conflict:
                    from .multi_platform_import import import_multi_platform_records

                    import_result = import_multi_platform_records(records, connection=conn)
                    note_ids = [
                        str(detail.get("note_id"))
                        for detail in import_result.get("details", [])
                        if detail.get("note_id") and detail.get("status") in {"imported", "updated"}
                    ]

                prelaunch_import_incomplete = (
                    (prelaunch_scope is not None or manual_scope is not None) and bool(items)
                    and (len(note_ids) != len(records) or len(set(note_ids)) != len(note_ids))
                )
                canonical_failed = False
                final_status = ("SCOPE_CONFLICT" if prelaunch_scope_conflict else
                                "CANONICAL_SYNC_FAILED" if canonical_failed else status)
                if review_pending and not records and collection.ok:
                    final_status = "SCOPE_REVIEW_REQUIRED"
                if (not prelaunch_scope_conflict and not canonical_failed and collection.ok
                        and (import_result.get("failed") or prelaunch_import_incomplete)):
                    final_status = "IMPORT_FAILED"
                finished = _now()
                error = "" if final_status in {"SUCCESS", "NO_NEW_DATA"} else f"{final_status}: {_status_message(final_status)}"
                observed_raw_count = _observed_raw_count(collection, source_item_count)
                result = {
                    "ok": bool(collection.ok and not prelaunch_scope_conflict and not import_result.get("failed")
                               and not prelaunch_import_incomplete and not canonical_failed),
                    "status": final_status,
                    "platform": platform,
                    "keyword": keyword,
                    "raw_count": observed_raw_count,
                    "returned_count": (
                        source_item_count
                        if collection.ok or source_item_count > 0 or observed_raw_count is not None
                        else None
                    ),
                    "filtered_count": (
                        max(0, source_item_count - len(items))
                        if collection.ok or source_item_count > 0 else None
                    ),
                    "imported": int(import_result.get("imported", 0) or 0),
                    "updated": int(import_result.get("updated", 0) or 0),
                    "failed": int(import_result.get("failed", 0) or 0),
                    "subject_matches": int(subject.get("subject_matches", 0) or 0),
                    "canonical_synced": int(subject.get("canonical_synced", 0) or 0),
                    "health_status": health_status,
                    "error": error,
                    "error_type": "" if final_status in {"SUCCESS", "NO_NEW_DATA"} else final_status,
                    "duration_ms": int((time.monotonic() - started_monotonic) * 1000),
                    "read_only": True,
                    "external_write": False,
                    "publish_authority": "human_manual_only",
                    "product_owner": (
                        "BMP" if (prelaunch_scope or manual_scope or {}).get("domain_id") == "bmp"
                        else "CTH"
                    ),
                    "consumer_views": ["CTH", "BMP"],
                    "provenance": provenance,
                    "entity_mentions": entity_mentions,
                    "review_pending_count": len(review_pending),
                }
                if final_status == "SCOPE_REVIEW_REQUIRED":
                    result["ok"] = False
                    result["error_type"] = "SOURCE_ENTITY_IDENTITY_UNCONFIRMED"
                if prelaunch_scope is not None or manual_scope is not None:
                    result["refresh_verified"] = False
                try:
                    if prelaunch_scope is not None:
                        if prelaunch_observation_changed or review_candidates:
                            evidence_id = None
                        else:
                            evidence_id = _existing_prelaunch_observation_evidence(note_ids, platform, connection=conn)
                        if evidence_id is None:
                            evidence_id = _write_prelaunch_evidence(
                                platform, keyword, result, started=started_at,
                                scope=prelaunch_scope, source_ids=note_ids,
                                review_candidates=review_candidates,
                                manual=manual_scope is not None, observations=records + review_candidates, connection=conn,
                            )
                    elif manual_scope is not None:
                        evidence_id = (None if prelaunch_observation_changed else
                            _existing_prelaunch_observation_evidence(note_ids, platform, connection=conn))
                        if evidence_id is None:
                            evidence_id = _write_prelaunch_evidence(
                                platform, keyword, result, started=started_at, scope=manual_scope,
                                source_ids=note_ids, manual=True, observations=records + review_candidates, connection=conn,
                            )
                    else:
                        evidence_id = _write_evidence(platform, keyword, result, started=started_at)
                except Exception as exc:
                    raise _CollectionWriteRejected({
                        **result, "ok": False, "status": "EVIDENCE_WRITE_FAILED",
                        "error_type": "EVIDENCE_WRITE_FAILED",
                        "error": _status_message("EVIDENCE_WRITE_FAILED"),
                    }) from exc
                result["evidence_recorded"] = isinstance(evidence_id, int) and evidence_id > 0
                if result["evidence_recorded"]:
                    result["evidence_ref"] = str(evidence_id)
                if not isinstance(evidence_id, int) or evidence_id <= 0:
                    result.update({
                        "ok": False,
                        "status": "EVIDENCE_WRITE_FAILED",
                        "error_type": "EVIDENCE_WRITE_FAILED",
                        "error": f"EVIDENCE_WRITE_FAILED: {_status_message('EVIDENCE_WRITE_FAILED')}",
                    })
                elif prelaunch_scope is not None and note_ids and result["ok"]:
                    try:
                        pending_scope_ids = _prelaunch_scope_note_ids_needing_verification(
                            note_ids, prelaunch_scope, connection=conn,
                        )
                        if pending_scope_ids:
                            _persist_prelaunch_scope(pending_scope_ids, prelaunch_scope, evidence_id, connection=conn)
                        canonical_synced = _sync_prelaunch_canonical_source_fields(
                            note_ids, prelaunch_scope, evidence_id=evidence_id,
                            source_unchanged=not prelaunch_observation_changed,
                            connection=conn,
                        )
                        result["canonical_synced"] = canonical_synced
                        result["scope_status"] = "VERIFIED"
                        if prelaunch_scope is not None:
                            from lumenis.shared.database.platform_content import persist_verified_platform_records

                            result["native_fields_synced"] = persist_verified_platform_records(
                                records, platform=platform, note_ids=note_ids,
                                evidence_id=evidence_id, scope=prelaunch_scope, connection=conn,
                                require_observation_proof=True,
                            )
                        if prelaunch_scope is not None:
                            refresh_verified = (
                                bool(records)
                                and len(note_ids) == len(records)
                                and canonical_synced == len(records)
                                and result.get("native_fields_synced") == len(records)
                                and result.get("evidence_recorded") is True
                            )
                            result["refresh_verified"] = refresh_verified
                            if not refresh_verified:
                                result.update({
                                    "ok": False,
                                    "status": "CANONICAL_SYNC_FAILED",
                                    "error_type": "CANONICAL_SYNC_FAILED",
                                    "error": _status_message("CANONICAL_SYNC_FAILED"),
                                })
                    except Exception:
                        result.update({"ok": False, "status": "CANONICAL_SYNC_FAILED",
                                       "error_type": "CANONICAL_SYNC_FAILED",
                                       "error": _status_message("CANONICAL_SYNC_FAILED")})
                elif manual_scope is not None and note_ids and result["ok"]:
                    try:
                        result["canonical_synced"] = _sync_unassigned_collection(
                            note_ids, manual_scope, evidence_id, connection=conn,
                            new_note_ids=[detail["note_id"] for detail in import_result["details"]
                                          if detail.get("status") == "imported"],
                            source_unchanged=not prelaunch_observation_changed,
                        )
                        from lumenis.shared.database.platform_content import persist_unassigned_platform_records
                        result["native_fields_synced"] = persist_unassigned_platform_records(
                            records, platform=platform, note_ids=note_ids,
                            evidence_id=evidence_id, scope=manual_scope, connection=conn,
                        )
                        result["scope_status"] = "UNASSIGNED"
                        result["refresh_verified"] = (
                            len(records) == len(note_ids)
                            and result["canonical_synced"] == len(records)
                            and result["native_fields_synced"] == len(records)
                        )
                    except Exception:
                        result.update({"ok": False, "status": "CANONICAL_SYNC_FAILED",
                                       "error_type": "CANONICAL_SYNC_FAILED",
                                       "error": _status_message("CANONICAL_SYNC_FAILED")})
                if not result["evidence_recorded"] or (collection.ok and records and not result["ok"]):
                    raise _CollectionWriteRejected(result)
                if raw_capture is not None and result["ok"]:
                    canonical_rows = conn.execute(
                        "SELECT canonical_id,source_id,version,product_id,domain_id,subject_id,brand_focus_id,"
                        "scope_status,scope_evidence_ref,publish_datetime,captured_at FROM canonical_data "
                        "WHERE source_type='note' AND source_table='notes' AND source_id=?",
                        (note_ids[0],),
                    ).fetchall()
                    evidence = conn.execute("SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)).fetchone()
                    from lumenis.shared.evidence.store import classify_evidence_integrity
                    integrity = classify_evidence_integrity(dict(evidence)) if evidence else {}
                    if len(canonical_rows) != 1 or not integrity.get("verified"):
                        raise _CollectionWriteRejected({**result, "ok": False, "status": "EVIDENCE_WRITE_FAILED"})
                    try:
                        admission_id = _record_public_raw_admission(
                            conn, raw_capture, prelaunch_scope, note_ids, evidence_id, started=started_at,
                        )
                    except Exception as exc:
                        raise _CollectionWriteRejected({**result, "ok": False,
                            "status": "EVIDENCE_WRITE_FAILED", "error_type": "EVIDENCE_WRITE_FAILED"}) from exc
                    admission = conn.execute("SELECT * FROM app_evidence_records WHERE id=?", (admission_id,)).fetchone()
                    if not admission or not classify_evidence_integrity(dict(admission)).get("verified"):
                        raise _CollectionWriteRejected({**result, "ok": False, "status": "EVIDENCE_WRITE_FAILED"})
                    result["approved_raw_refs"] = {
                        "source_id": note_ids[0], "source_table": "notes",
                        "canonical": dict(canonical_rows[0]),
                        "evidence_ref": f"app_evidence_records:{evidence_id}",
                        "evidence_version": evidence["version"],
                        "signature_verified": True,
                        "admission_evidence_ref": f"app_evidence_records:{admission_id}",
                        "admission_evidence_version": admission["version"],
                        "admission_signature_verified": True,
                        "original_capture": _public_raw_material(raw_capture),
                        "approval_resource": approved_public_raw_resource(prelaunch_scope, raw_capture),
                        "domain_adapter": {"prelaunch": prelaunch_scope["domain_id"],
                                           "consumer": "cth" if prelaunch_scope["domain_id"] == "cth" else "zbmp"},
                    }
                if native_capture is not None and note_ids and result.get("ok"):
                    rows = conn.execute("SELECT canonical_id,source_id,version,product_id,domain_id,subject_id,brand_focus_id,scope_status,scope_evidence_ref,publish_datetime,captured_at FROM canonical_data WHERE source_table='notes' AND source_id=?", (note_ids[0],)).fetchall()
                    evidence = conn.execute("SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)).fetchone()
                    from lumenis.shared.evidence.store import classify_evidence_integrity
                    if len(rows) != 1 or not evidence or not classify_evidence_integrity(dict(evidence)).get("verified"):
                        raise _CollectionWriteRejected({**result,"ok":False,"status":"EVIDENCE_WRITE_FAILED"})
                    result["native_original_refs"] = {"source_id":note_ids[0],"canonical":dict(rows[0]),
                        "evidence_ref":"app_evidence_records:"+str(evidence_id),"evidence_version":evidence["version"],
                        "observation_sha256":native_capture.sha256,"original_capture_time":captured_at,
                        "body_sha256":native_value["body_sha256"],"source_lineage":native_value["source_lineage"],
                        "approval_resource_keyword":permission_keyword,"signature_verified":True,
                        "per_use_admission":{"DATA_IMPORT":"CURRENT_CALLER_APPROVED","READ_ANALYZE_SAVE_EXPORT":"CHECK_EACH_CURRENT_USE","MODEL_TRAIN":"NOT_GRANTED"}}
                    # Original preservation is a source-specific side write, not
                    # another Canonical import. Its own failure stays visible
                    # without erasing the already admitted primary observation.
                    conn.execute("SAVEPOINT collected_native_original")
                    source_path_start = len(staged_source_paths)
                    try:
                        from lumenis.shared.reporting.saved_work import authorize
                        source_context = authorize(actor, manual_scope, action="write", connection=conn)
                        original = _persist_native_source_original(
                            conn, capture=native_capture, source_id=note_ids[0],
                            collection_evidence_id=evidence_id, context=source_context,
                            staged_paths=staged_source_paths,
                        )
                        _bind_native_source_original(conn, note_ids[0], source_context, original)
                        conn.execute("RELEASE SAVEPOINT collected_native_original")
                        result["native_original_refs"]["original_source"] = original
                    except Exception as exc:
                        conn.execute("ROLLBACK TO SAVEPOINT collected_native_original")
                        conn.execute("RELEASE SAVEPOINT collected_native_original")
                        cleanup_ok = _cleanup_collected_source_paths(staged_source_paths[source_path_start:])
                        del staged_source_paths[source_path_start:]
                        result["native_original_refs"]["original_source"] = {
                            "status": "UNAVAILABLE", "source_artifact_ref": None,
                            "source_evidence_ref": None, "source_evidence_version": None,
                            "source_signature_verified": False,
                            "reason": str(exc) if isinstance(exc, (ValueError, NativeCaptureError))
                                      else "COLLECTED_SOURCE_WRITE_FAILED",
                            "cleanup_status": "COMPLETE" if cleanup_ok else "FAILED",
                            "media_original_status": "NOT_VERIFIED", "media_asset_refs": None,
                        }
                if manual_scope is not None:
                    _, denial = _manual_collection_guard(
                        actor, manual_scope, platform, permission_keyword, max_results,
                        max_scroll=max_scroll,
                    )
                    if denial is not None:
                        raise _CollectionWriteRejected(denial)
                elif prelaunch_scope is not None:
                    authorized = (_authorize_prelaunch_public(
                        prelaunch_scope, keyword, platform,
                        maintenance_authorization=prelaunch_authorization,
                        raw_capture=raw_capture,
                        business_query=business_query, max_results=max_results,
                    ) if maintenance_operator or platform in {"public_http", "web_atom"} else _authorize_prelaunch_manual(
                        prelaunch_scope, keyword, platform=platform,
                    ))
                    if not authorized:
                        raise _CollectionWriteRejected({"ok": False, "status": "SCOPE_UNAUTHORIZED",
                            "platform": platform, "keyword": keyword,
                            "read_only": True, "external_write": False})
                if (maintenance_operator and prelaunch_scope is not None and note_ids
                        and result.get("ok") and platform in {
                            "xiaohongshu", "douyin", "x", "instagram", "facebook", "wechat"}):
                    source_context = {
                        **prelaunch_scope,
                        "domain_id": "zbmp" if prelaunch_scope["domain_id"] == "bmp" else "cth",
                        "global_scope": False,
                        "collector_plan_id": prelaunch_authorization.plan_id,
                        "collector_authorization_ref": prelaunch_authorization.authorization_ref,
                    }
                    originals = []
                    from .platform_naming import get_platform_fields, normalize_content_id
                    spec = get_platform_fields(platform)
                    records_by_id = {
                        (normalize_content_id(platform, record.get(spec.content_id) if spec else None)
                         or normalize_content_id(platform, record.get("content_id"))): record
                        for record in records
                    }
                    for source_id in note_ids:
                        conn.execute("SAVEPOINT collected_live_original")
                        source_path_start = len(staged_source_paths)
                        try:
                            record = records_by_id.get(str(source_id))
                            if record is None:
                                raise ValueError("COLLECTED_SOURCE_NATIVE_ID_MISMATCH")
                            original = _persist_live_source_original(
                                conn, platform=platform, record=record, source_id=source_id,
                                collection_evidence_id=evidence_id, context=source_context,
                                staged_paths=staged_source_paths, scope=prelaunch_scope,
                                keyword=keyword, authorization=prelaunch_authorization,
                                business_query=business_query, max_results=max_results,
                            )
                            cover = live_covers.get(str(source_id))
                            cover_refs = {"status": "NULL", "reason": "NO_OBSERVED_COVER",
                                          "media_asset_refs": None}
                            if isinstance(cover, dict):
                                cover_refs["reason"] = cover.get("reason")
                                if cover.get("status") == "AVAILABLE":
                                    conn.execute("SAVEPOINT collected_post_cover")
                                    cover_path_start = len(staged_source_paths)
                                    try:
                                        cover_refs = _persist_live_post_cover(
                                            conn, cover=cover, platform=platform, source_id=source_id,
                                            context=source_context, body_original=original,
                                            staged_paths=staged_source_paths,
                                            authorization_resource="collector-cover:" + prelaunch_authorization.plan_id,
                                        )
                                        conn.execute("RELEASE SAVEPOINT collected_post_cover")
                                    except Exception:
                                        conn.execute("ROLLBACK TO SAVEPOINT collected_post_cover")
                                        conn.execute("RELEASE SAVEPOINT collected_post_cover")
                                        cleanup_ok = _cleanup_collected_source_paths(staged_source_paths[cover_path_start:])
                                        del staged_source_paths[cover_path_start:]
                                        cover_refs = {"status": "NULL", "reason": "COVER_INTAKE_FAILED",
                                                      "media_asset_refs": None,
                                                      "cleanup_status": "COMPLETE" if cleanup_ok else "FAILED"}
                            original["cover"] = cover_refs
                            # One saved cover is partial media intake. It does
                            # not establish video acquisition or understanding.
                            original["media_original_status"] = (
                                "PARTIAL_COVER_ONLY" if cover_refs["status"] == "SAVED"
                                else "NOT_VERIFIED")
                            original["media_asset_refs"] = cover_refs.get("media_asset_refs")
                            original["media_understanding"] = {
                                "required": True, "state": "NOT_RUN",
                                "reason": "POST_INTAKE_MEDIA_JOB_BINDING_NOT_IMPLEMENTED",
                                "native_media_locator": {
                                    "source_artifact_ref": original["source_artifact_ref"],
                                    "source_evidence_ref": original["source_evidence_ref"],
                                    "source_fingerprint": original["source_fingerprint"],
                                    "json_path": "$.native_record",
                                    "representation": "OBSERVED_NATIVE_METADATA"},
                                "image_input_refs": cover_refs.get("media_asset_refs"),
                                "image_analysis_ref": None, "video_analysis_ref": None,
                                "speech_transcript_ref": None,
                                "full_post_media_coverage": "UNKNOWN",
                                "job_enqueued": False,
                                "per_use_admission": "CHECK_CURRENT_MEDIA_ANALYSIS_USE",
                            }
                            _bind_native_source_original(conn, source_id, source_context, original)
                            conn.execute("RELEASE SAVEPOINT collected_live_original")
                            originals.append({"source_id": source_id, **original})
                        except Exception as exc:
                            conn.execute("ROLLBACK TO SAVEPOINT collected_live_original")
                            conn.execute("RELEASE SAVEPOINT collected_live_original")
                            cleanup_ok = _cleanup_collected_source_paths(staged_source_paths[source_path_start:])
                            del staged_source_paths[source_path_start:]
                            originals.append({"source_id": source_id, "status": "UNAVAILABLE",
                                "source_artifact_ref": None, "source_evidence_ref": None,
                                "source_evidence_version": None, "source_signature_verified": False,
                                "reason": str(exc) if isinstance(exc, (ValueError, NativeCaptureError))
                                          and re.fullmatch(r"[A-Z][A-Z0-9_]{0,100}", str(exc))
                                          else "COLLECTED_SOURCE_WRITE_FAILED",
                                "cleanup_status": "COMPLETE" if cleanup_ok else "FAILED"})
                    result["live_original_refs"] = originals
                    # Commit originals before processing. The existing resident
                    # Source backlog performs current use checks and derivative
                    # writes on its next pass; no second queue is introduced.
                    analyses = []
                    for original in originals:
                        if original.get("status") != "SAVED":
                            continue
                        analyses.append({
                            "source_id": original["source_id"], "status": "PENDING",
                            "keyword_evidence_ref": None, "keyword_artifact_ref": None,
                            "reason": "PERSISTED_SOURCE_BACKLOG_PENDING",
                            "source_evidence_ref": original["source_evidence_ref"],
                            "source_artifact_ref": original["source_artifact_ref"],
                            "source_fingerprint": original["source_fingerprint"],
                            "processing_owner": "process_prelaunch_keyword_backlog",
                            "job_enqueued": False,
                        })
                    result["post_intake_keyword_refs"] = analyses
                    source_saved = sum(row.get("status") == "SAVED" for row in originals)
                    analyses_saved = sum(row.get("status") == "SAVED" for row in analyses)
                    result["source_intake"] = {
                        "admitted_posts": len(note_ids), "originals_saved": source_saved,
                        "originals_pending": len(note_ids) - source_saved,
                        "covers_saved": sum(row.get("cover", {}).get("status") == "SAVED"
                                            for row in originals),
                        "max_cover_images_per_post": 1,
                        "keyword_analysis": "SAVED" if analyses_saved == source_saved and source_saved
                                            else "PENDING",
                        "keyword_analyses_saved": analyses_saved,
                        "keyword_analyses_pending": source_saved - analyses_saved,
                        "owned_inference": "NOT_RUN",
                        "keyword_analysis_blocks_collection": False,
                        "keyword_processing_mode": "POST_COMMIT_SOURCE_BACKLOG",
                        "extra_images_processed": False, "video_processing": False,
                        "media_understanding_required": True,
                        "media_understanding_state": "NOT_RUN",
                        "media_understanding_reason": "POST_INTAKE_MEDIA_JOB_BINDING_NOT_IMPLEMENTED",
                    }
                    if source_saved != len(note_ids):
                        result.update(ok=False, status="PARTIAL_SOURCE_INTAKE_PENDING",
                                      error_type="SOURCE_ORIGINAL_INCOMPLETE", refresh_verified=False)
                    from lumenis.shared.evidence import store as source_outcome_store
                    # Persist per-item outcomes after intake, rather than losing
                    # failed Source/cover refs in a scheduler summary. This is
                    # derivative execution evidence, never new source content.
                    conn.execute("SAVEPOINT collected_intake_outcome")
                    try:
                        source_outcome_id = source_outcome_store.record_evidence(
                            connection=conn, source="collector", project="LUMENIS",
                            product="CTH" if source_context["domain_id"] == "cth" else "ZBMP",
                            feature_id="COLLECTOR_SOURCE_INTAKE_OUTCOME",
                            asset_id=prelaunch_authorization.plan_id, version="collector-source-intake:v3",
                            capture_mode="live_native_intake_outcome", captured_at=_now(),
                            inputs={"source_ids": note_ids,
                                    "collection_evidence_ref": "app_evidence_records:" + str(evidence_id),
                                    "authorization_ref": prelaunch_authorization.authorization_ref},
                            outputs={"source_intake": result["source_intake"], "original_refs": originals,
                                     "post_intake_keyword_refs": analyses},
                            collection_metadata={"kind": "DERIVATIVE_EXECUTION_OUTCOME",
                                                 "native_platform_signature_provided": False},
                            result="PASS" if source_saved == len(note_ids) else "FAIL",
                            actual="SOURCE_ORIGINALS_SAVED" if source_saved == len(note_ids)
                                   else "PARTIAL_SOURCE_INTAKE_PENDING",
                            provider="collector-source-intake",
                            domain_id=source_context["domain_id"], subject_id=source_context["subject_id"],
                            brand_focus_id=source_context["brand_focus_id"], global_scope=False,
                        )
                        conn.execute("RELEASE SAVEPOINT collected_intake_outcome")
                        result["source_intake_outcome_ref"] = "app_evidence_records:" + str(source_outcome_id)
                    except Exception:
                        conn.execute("ROLLBACK TO SAVEPOINT collected_intake_outcome")
                        conn.execute("RELEASE SAVEPOINT collected_intake_outcome")
                        result["source_intake_outcome_ref"] = None
                        result["source_intake_outcome_state"] = "OUTCOME_EVIDENCE_WRITE_FAILED"
                    if not _authorize_prelaunch_public(
                            prelaunch_scope, keyword, platform,
                            maintenance_authorization=prelaunch_authorization,
                            business_query=business_query, max_results=max_results):
                        raise _CollectionWriteRejected({"ok": False, "status": "SCOPE_UNAUTHORIZED",
                            "platform": platform, "keyword": keyword,
                            "read_only": True, "external_write": False})
                if (maintenance_operator and prelaunch_scope is not None
                        and original_observation_records and result.get("evidence_recorded")
                        and not prelaunch_scope_conflict and platform in {
                            "xiaohongshu", "douyin", "x", "instagram", "facebook", "wechat"}):
                    source_context = {
                        **prelaunch_scope,
                        "domain_id": "zbmp" if prelaunch_scope["domain_id"] == "bmp" else "cth",
                        "global_scope": False,
                        "collector_plan_id": prelaunch_authorization.plan_id,
                        "collector_authorization_ref": prelaunch_authorization.authorization_ref,
                    }
                    pending_intake = _persist_pending_live_observations(
                        conn, platform=platform, records=original_observation_records,
                        collection_evidence_id=evidence_id, context=source_context,
                        staged_paths=staged_source_paths, scope=prelaunch_scope,
                        keyword=keyword, authorization=prelaunch_authorization,
                        business_query=business_query, max_results=max_results,
                        reviews=business_reviews, covers=live_covers,
                        saved_ids={str(row["source_id"]) for row in result.get("live_original_refs", [])
                                   if row.get("status") == "SAVED"},
                    )
                    result["pending_original_refs"] = pending_intake["original_refs"]
                    result["pending_source_intake"] = pending_intake["summary"]
                    result["pending_source_intake_outcome_ref"] = pending_intake["outcome_ref"]
                    if not _authorize_prelaunch_public(
                            prelaunch_scope, keyword, platform,
                            maintenance_authorization=prelaunch_authorization,
                            business_query=business_query, max_results=max_results):
                        raise _CollectionWriteRejected({"ok": False, "status": "SCOPE_UNAUTHORIZED",
                            "platform": platform, "keyword": keyword,
                            "read_only": True, "external_write": False})
                continuation = metadata.get("continuation")
                if isinstance(continuation, dict):
                    result["acquisition_continuation"] = _credential_free_observations(continuation)
                    if continuation.get("continuation_required") is True and result.get("ok"):
                        # Commit useful admitted observations, but never close a
                        # task whose native detail checkpoint still has work.
                        result.update(ok=False, status="PARTIAL_ACQUISITION_PENDING",
                                      error_type="NATIVE_ACQUISITION_CONTINUATION_REQUIRED",
                                      refresh_verified=False)
                # The signed success above covers only admitted source_ids. Keep the
                # overall request partial when other returned items still need review.
                if review_pending and result["ok"]:
                    result.update({
                        "ok": False, "status": "PARTIAL_SCOPE_REVIEW_REQUIRED",
                        "error_type": "SOURCE_ENTITY_IDENTITY_UNCONFIRMED",
                        "error": _status_message("PARTIAL_SCOPE_REVIEW_REQUIRED"),
                        "scope_status": "PARTIAL", "refresh_verified": False,
                    })
                has_source_effect = any(int(result.get(field, 0) or 0) > 0 for field in
                    ("imported", "updated", "canonical_synced", "native_fields_synced")) or any(
                    item.get("status") == "SAVED" for item in
                    result.get("live_original_refs", []) + result.get("pending_original_refs", []))
                # A transient error's diagnostic Evidence is not a completed
                # source effect. Permit retry; committed partial sources remain fenced.
                if task_binding is not None and (result.get("ok") is True or has_source_effect):
                    _task_commit_receipt(conn, task_binding, result)
            source_files_committed = True
            # The operational checkpoint follows the actual Source transaction.
            # Observed/skipped cards and rejected IDs cannot count as committed.
            if platform == "x" and acquisition_fingerprint:
                checkpoint_key = "scope:" + acquisition_fingerprint
                continuation = metadata.get("continuation")
                source_ids_saved = [str(row["source_id"]) for row in
                                    result.get("live_original_refs", []) + result.get("pending_original_refs", [])
                                    if row.get("status") == "SAVED"]
                if (isinstance(continuation, dict)
                        and continuation.get("seen_checkpoint_key") == checkpoint_key and source_ids_saved):
                    try:
                        from lumenis.system.collector.guard.checkpoint import Checkpoint
                        saved = Checkpoint("x").mark_seen(checkpoint_key, source_ids_saved)
                        result["committed_post_checkpoint"] = {
                            "status": "SAVED" if saved is True else "UNAVAILABLE",
                            "acquisition_fingerprint": acquisition_fingerprint,
                            "committed_id_count": len(source_ids_saved) if saved is True else None,
                            "native_cursor": None, "pagination_exhausted": None,
                            "coverage_complete": False,
                        }
                    except Exception:
                        result["committed_post_checkpoint"] = {
                            "status": "UNAVAILABLE", "committed_id_count": None,
                            "native_cursor": None, "pagination_exhausted": None,
                            "coverage_complete": False}
        except _CollectionWriteRejected as rejected:
            rejected_result = dict(rejected.result)
            result = dict(rejected_result)
            result.update(imported=0, updated=0, canonical_synced=0,
                          native_fields_synced=0, evidence_recorded=False, refresh_verified=False)
            for stale_key in (
                "evidence_ref", "approved_raw_refs", "native_original_refs",
                "live_original_refs", "pending_original_refs", "source_intake",
                "source_intake_outcome_ref", "source_intake_outcome_state",
                "post_intake_keyword_refs", "pending_source_intake",
                "pending_source_intake_outcome_ref", "original_preservation",
                "source_recovery_outcome_ref", "source_recovery_refs",
            ):
                result.pop(stale_key, None)
            for stale_key in (
                "source_saved_count", "source_originals_saved", "source_originals_pending",
                "keyword_analyses_saved", "keyword_analyses_pending", "covers_saved",
            ):
                result.pop(stale_key, None)
            result.pop("scope_status", None)
            if (maintenance_operator and prelaunch_scope is not None
                    and prelaunch_authorization is not None
                    and business_query is not None
                    and collection.ok is True and status in {"SUCCESS", "NO_NEW_DATA"}
                    and original_observation_records
                    and result.get("status") in {
                        "CANONICAL_SYNC_FAILED", "IMPORT_FAILED", "EVIDENCE_WRITE_FAILED"}):
                result["original_preservation"] = _preserve_prelaunch_originals_after_rollback(
                    platform=platform, keyword=keyword, scope=prelaunch_scope,
                    authorization=prelaunch_authorization, business_query=business_query,
                    max_results=max_results, observations=original_observation_records,
                    reviews=business_reviews, original_result=rejected_result,
                    started=started_at, acquisition_ok=collection.ok,
                    acquisition_status=status, covers=live_covers,
                )
            if result.get("status") not in {"AUTH_REQUIRED", "APPROVAL_REQUIRED",
                    "SCOPE_UNAUTHORIZED", "PERMISSION_UNAVAILABLE"}:
                try:
                    _write_run_log(platform, keyword, started=started_at, finished=_now(),
                        fetched=_observed_raw_count(collection, source_item_count), accepted=0,
                        rejected=(source_item_count if collection.ok or source_item_count > 0 else None),
                        error=result.get("error") or str(result.get("status")))
                    result["run_log_recorded"] = True
                except Exception:
                    result["run_log_recorded"] = False
            return result
        except Exception:
            result = {"ok": False, "status": "COLLECTION_WRITE_FAILED",
                    "error_type": "COLLECTION_WRITE_FAILED", "platform": platform,
                    "keyword": keyword, "imported": 0, "updated": 0,
                    "canonical_synced": 0, "native_fields_synced": 0,
                    "evidence_recorded": False, "refresh_verified": False,
                    "read_only": True, "external_write": False}
            return result
        finally:
            if not source_files_committed and not _cleanup_collected_source_paths(staged_source_paths):
                if isinstance(result, dict):
                    result["original_source_cleanup_status"] = "FAILED"
        accepted_count = int(result.get("canonical_synced", 0) or 0)
        fetched_count = _observed_raw_count(collection, source_item_count)
        read_completed = collection.ok or source_item_count > 0
        try:
            _write_run_log(
                platform, keyword, started=started_at, finished=finished,
                fetched=fetched_count,
                accepted=accepted_count if read_completed else None,
                rejected=max(0, source_item_count - accepted_count) if read_completed else None,
                error=result["error"],
            )
            result["run_log_recorded"] = True
        except Exception:
            result["run_log_recorded"] = False
        return result
    finally:
        lock.release()


def _business_source_reviews(records, query, observed_at):
    """Review live native time and task scope without altering source observations."""
    from ..acquisition_plan import assess_query_relevance
    from .platform_naming import get_platform_fields, normalize_platform
    from .multi_platform_import import _normalize_source_publication
    spec = get_platform_fields(query.business_context['platform'])
    reviewed = []
    for record in records:
        native = record.get(spec.published_at) if spec else None
        if native in (None, ''):
            native = record.get('publish_datetime')
        # Reuse the native-platform unit authority: XHS milliseconds are not
        # seconds, and capture/update time never repairs unknown publication.
        native = _normalize_source_publication(
            native, normalize_platform(query.business_context['platform'])) or None
        observation = {'native_id': record.get('content_id'), 'source_url': record.get('url'),
                       'title': record.get('title'), 'content': record.get('content'),
                       'published_at': native, 'capture_observation_utc': observed_at}
        reviewed.append({**assess_query_relevance(observation, query),
                         'platform_content_id': record.get('content_id'),
                         'source_url': record.get('url'), 'native_publication_literal': native})
    return reviewed


def _business_batch_binding(actor, scopes, operator, prelaunch_authorization):
    """Verify current actor authority before reading any durable task result."""
    from lumenis.system.security.permission import (
        LocalWorkspacePrincipal, check_actor_scope_permission,
        check_local_workspace_scope_permission,
    )
    if operator == "prelaunch_maintenance":
        if prelaunch_authorization is None:
            raise PermissionError("SIGNED_MAINTENANCE_REQUIRED")
        identity = {"maintenance_plan": prelaunch_authorization.plan_id}
    else:
        if type(actor) is LocalWorkspacePrincipal:
            identity = {"principal_ref": actor.principal_ref}
            checker = check_local_workspace_scope_permission
        elif isinstance(actor, dict) and type(actor.get("id")) is int:
            identity = {"actor_id": actor["id"]}
            checker = check_actor_scope_permission
        else:
            raise PermissionError("AUTH_REQUIRED")
        if not isinstance(scopes, Mapping) or not scopes:
            raise PermissionError("SCOPE_UNAUTHORIZED")
        for scope_key, scope in scopes.items():
            if not isinstance(scope, Mapping):
                raise PermissionError("SCOPE_UNAUTHORIZED")
            normalized_domain = 'bmp' if scope.get('domain_id') == 'zbmp' else scope.get('domain_id')
            if scope_key not in {'cth', 'bmp'} or normalized_domain != scope_key:
                raise PermissionError("QUERY_CALLER_SCOPE_MISMATCH")
            decision = checker(actor, module="collector", action="write", **scope)
            if decision.allowed is not True or decision.verification_state != "verified":
                raise PermissionError("SCOPE_UNAUTHORIZED")
    return {"identity": identity, "scopes": scopes, "operator": operator}


def _historical_business_result(result):
    """Cached task truth is explicitly historical, never a new source refresh."""
    cached = json.loads(json.dumps(result))
    cached.update(cached=True, execution_attempted=False, refresh_performed=False,
                  result_freshness="HISTORICAL_TASK_RESULT")
    for run in cached.get("runs", []):
        outcome = run.get("result") or {}
        outcome["refresh_verified"] = False
        outcome["historical_task_result"] = True
    return cached


def collect_business_queries(business_requests, *, actor=None, scopes=None,
                             operator='human', continuation=None, checkpoint=None,
                             max_queries=32, max_results=MAX_RESULTS,
                             prelaunch_authorization=None, request_id=None):
    """Resume only server-issued, actor/scope/plan-bound operational receipts.

    Client completed keys are an inspectable echo, never task truth or approval.
    Native pagination stays in the existing acquisition plan's separate cursor.
    """
    import uuid
    from ..acquisition_plan import build_acquisition_plan, AcquisitionPlanError
    from ..guard.task_queue import TaskQueue
    if operator in {'human', 'human_ui'} and actor is None:
        return {'ok': False, 'status': 'AUTH_REQUIRED', 'runs': [], 'network_attempted': False}
    plan = build_acquisition_plan(business_requests=business_requests,
                                 continuation=continuation, max_queries=max_queries)
    if checkpoint is not None and (not isinstance(checkpoint, Mapping)
            or set(checkpoint) != {'input_fingerprint', 'completed_query_keys', 'task_id', 'receipt'}):
        raise AcquisitionPlanError('server-issued collection checkpoint required')
    binding = _business_batch_binding(actor, scopes, operator, prelaunch_authorization)
    if operator == 'prelaunch_maintenance':
        for query in plan.queries:
            domain = 'cth' if query.domain_id == 'CTH' else 'bmp'
            source_scope = (scopes or {}).get(domain)
            if not _authorize_prelaunch_public(source_scope, query.keyword,
                    query.business_context['platform'], maintenance_authorization=prelaunch_authorization,
                    business_query=query, max_results=max_results):
                raise PermissionError('SCOPE_UNAUTHORIZED')
    binding = json.loads(json.dumps({**binding, 'input_fingerprint': plan.input_fingerprint,
                                    'max_queries': max_queries, 'max_results': max_results}, sort_keys=True))
    if request_id is not None and (not isinstance(request_id, str) or not 1 <= len(request_id) <= 128):
        raise AcquisitionPlanError('invalid collection request_id')
    binding['request_id'] = request_id
    page_key = json.dumps(continuation, sort_keys=True, separators=(',', ':'))
    queue = TaskQueue()
    try:
        if checkpoint is not None:
            task_id = checkpoint.get('task_id')
            if type(task_id) is not int or type(checkpoint.get('receipt')) is not str:
                raise AcquisitionPlanError('invalid server collection receipt')
            task = queue.get(task_id)
            if (task is None or task['task_type'] != 'collector_business_batch'
                    or task['payload'].get('binding') != binding):
                raise AcquisitionPlanError('collection checkpoint actor, scope or plan mismatch')
            progress = task['payload'].get('progress') or {}
            issued = (progress.get('receipts') or {}).get(checkpoint['receipt'])
            if (issued is None or checkpoint['completed_query_keys'] != issued['completed_query_keys']
                    or checkpoint['input_fingerprint'] != plan.input_fingerprint
                    or page_key not in {issued['page_key'], json.dumps(issued['next_cursor'], sort_keys=True, separators=(',', ':'))}):
                raise AcquisitionPlanError('collection checkpoint was not issued for this continuation')
            cached = (progress.get('pages') or {}).get(page_key)
            if cached is not None:
                return _historical_business_result(cached)
            # A saved receipt is never a live permission/import grant.
            for query in plan.queries:
                domain = 'cth' if query.domain_id == 'CTH' else 'bmp'
                source_scope = (scopes or {}).get(domain)
                platform = query.business_context['platform']
                if operator == 'prelaunch_maintenance':
                    if not _authorize_prelaunch_public(source_scope, query.keyword, platform,
                            maintenance_authorization=prelaunch_authorization,
                            business_query=query, max_results=max_results):
                        raise PermissionError('SCOPE_UNAUTHORIZED')
                elif platform in SECONDARY_COLLECTION_PLATFORMS:
                    _, error = _manual_collection_guard(actor, source_scope, platform, query.keyword, max_results)
                    if error is not None:
                        return {**error, 'runs': [], 'network_attempted': False}
            queue.reap_stale(120, task_id=task_id)
        else:
            if continuation is not None:
                raise AcquisitionPlanError('continuation requires a server checkpoint')
            request_key = hashlib.sha256(json.dumps(binding, sort_keys=True,
                ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()
            task_id = queue.enqueue_once('collector_business_batch', {'binding': binding, 'operation_id': uuid.uuid4().hex}, request_key)
            task = queue.get(task_id)
            progress = task['payload'].get('progress') or {}
            cached = (progress.get('pages') or {}).get(page_key)
            if cached is not None:
                return _historical_business_result(cached)
            queue.reap_stale(120, task_id=task_id)
        if not task['payload'].get('operation_id'):
            return {'ok': False, 'status': 'LEGACY_COLLECTION_COMMIT_UNKNOWN', 'runs': [],
                    'task_id': task_id, 'network_attempted': False,
                    'new_collection_requires_new_request_id': True}
        worker = 'business-batch-' + uuid.uuid4().hex
        claimed = queue.dequeue(worker_id=worker, lease_owner=worker, task_id=task_id)
        if claimed is None:
            current = queue.get(task_id)
            queue_state = current['status'] if current else 'missing'
            state = 'FAILED' if queue_state == 'failed' else 'PENDING' if queue_state == 'pending' else 'BUSY'
            return {'ok': False, 'status': state, 'runs': [], 'network_attempted': False,
                    'task_id': task_id, 'attempts': current['attempts'] if current else None,
                    'retry_after_seconds': max(0, current['scheduled_at'] - time.time()) if queue_state == 'pending' else None,
                    'new_collection_requires_new_request_id': queue_state == 'failed'}
        receipt = {key: claimed[key] for key in ('run_id', 'worker_id', 'lease_owner')}
        progress = claimed['payload'].get('progress') or progress
        stop_heartbeat = threading.Event()
        def renew_batch():
            heartbeat_queue = TaskQueue()
            try:
                while not stop_heartbeat.wait(15):
                    if not heartbeat_queue.heartbeat(task_id, worker,
                            run_id=receipt['run_id'], lease_owner=worker):
                        return
            finally:
                heartbeat_queue.close()
        heartbeat_thread = threading.Thread(target=renew_batch, daemon=True)
        heartbeat_thread.start()
        def save_completed(completed):
            progress['completed_query_keys'] = completed
            if not queue.save_progress(task_id, progress, **receipt):
                raise RuntimeError('COLLECTION_ATTEMPT_SUPERSEDED')
        try:
            result = _execute_business_queries(business_requests, actor=actor, scopes=scopes,
                operator=operator, continuation=continuation,
                checkpoint={'input_fingerprint': plan.input_fingerprint,
                            'completed_query_keys': progress.get('completed_query_keys', [])},
                max_queries=max_queries, max_results=max_results,
                prelaunch_authorization=prelaunch_authorization,
                progress_callback=save_completed,
                operation_prefix=claimed['payload'].get('operation_id'),
                attempt_guard=lambda: queue.attempt_guard(task_id, **receipt))
            result = json.loads(json.dumps(result, ensure_ascii=False))
            outcomes = [run.get('result') or {} for run in result.get('runs', [])]
            reconciled_only = bool(outcomes) and all(outcome.get('commit_reconciled') is True for outcome in outcomes)
            refreshed = any(outcome.get('ok') is True and outcome.get('commit_reconciled') is not True
                            and outcome.get('network_attempted') is not False for outcome in outcomes)
            result.update(cached=False, execution_attempted=True, refresh_performed=refreshed,
                result_freshness='HISTORICAL_COMMIT_RECONCILED' if reconciled_only else 'CURRENT_TASK_EXECUTION')
            if any(outcome.get('new_collection_required') is True for outcome in outcomes):
                result.update(new_collection_required=True, continuation_required=False,
                    recovery_action='REVIEW_COMMITTED_SOURCES_THEN_CREATE_NEW_REQUEST')
            result['new_collection_requires_new_request_id'] = True
            result['task_created_at'] = claimed['created_at']
            result['request_identity_mode'] = 'explicit' if request_id is not None else 'default_idempotent'
            # Store terminal operation receipts, not a second Source/Evidence store.
            token = uuid.uuid4().hex
            completed = result.get('checkpoint', {}).get('completed_query_keys', [])
            result['checkpoint'] = {'input_fingerprint': plan.input_fingerprint,
                'completed_query_keys': completed, 'task_id': task_id, 'receipt': token}
            progress.setdefault('receipts', {})[token] = {
                'completed_query_keys': completed, 'page_key': page_key,
                'next_cursor': result.get('next_cursor')}
            if result.get('ok') is True:
                progress.setdefault('pages', {})[page_key] = result
            progress['completed_query_keys'] = completed
            if not queue.save_progress(task_id, progress, **receipt):
                raise RuntimeError('COLLECTION_ATTEMPT_SUPERSEDED')
            if result.get('ok') is True and result.get('continuation_required') is not True:
                queue.ack(task_id, **receipt)
            else:
                queue.defer(task_id, **receipt)
            return result
        except Exception:
            queue.fail(task_id, 'COLLECTION_BATCH_INTERRUPTED', **receipt)
            raise
        finally:
            stop_heartbeat.set()
            heartbeat_thread.join(timeout=2)
    finally:
        queue.close()


def _execute_business_queries(business_requests, *, actor=None, scopes=None,
                             operator='human', continuation=None, checkpoint=None,
                             max_queries=32, max_results=MAX_RESULTS,
                             prelaunch_authorization=None, progress_callback=None,
                             attempt_guard=None, operation_prefix=None):
    """Execute a task-selected batch through the existing guarded collection entry.

    Existing task owners persist the returned checkpoint. Source scopes come
    from the authenticated caller, never from a name in the plan. One platform's
    failure defers its remaining queries and permits the other platforms to run.
    Native pagination and formal admission remain separately explicit.
    """
    from collections import deque
    from ..acquisition_plan import build_acquisition_plan, AcquisitionPlanError
    from .platform_naming import normalize_platform

    if operator not in {'human', 'human_ui', 'prelaunch_maintenance'}:
        raise PermissionError('normal collector caller or signed schedule owner required')
    if operator in {'human', 'human_ui'} and actor is None:
        return {'ok': False, 'status': 'AUTH_REQUIRED', 'runs': [], 'network_attempted': False}
    plan = build_acquisition_plan(business_requests=business_requests,
                                  continuation=continuation, max_queries=max_queries)
    if not plan.is_runnable:
        return {'ok': False, 'status': 'ACQUISITION_PLAN_BLOCKED', 'query_plan': plan.to_dict(), 'runs': []}
    if checkpoint is not None and (not isinstance(checkpoint, Mapping)
            or checkpoint.get('input_fingerprint') != plan.input_fingerprint
            or not isinstance(checkpoint.get('completed_query_keys'), list)
            or any(not isinstance(key, str) or not re.fullmatch(r'[0-9a-f]{64}', key)
                   for key in checkpoint['completed_query_keys'])):
        raise AcquisitionPlanError('checkpoint does not match this task-selected query plan')
    completed = set((checkpoint or {}).get('completed_query_keys', []))
    groups = {}
    keys = {}
    for query in plan.queries:
        key = hashlib.sha256(json.dumps(query.to_dict(), sort_keys=True, ensure_ascii=False,
                                        separators=(',', ':')).encode('utf-8')).hexdigest()
        keys[key] = query
        platform = normalize_platform(query.business_context['platform'])
        groups.setdefault(platform, deque()).append((key, query))
    blocked = {}
    runs = []
    deferred = []
    while any(groups.values()):
        for platform, queries in groups.items():
            if not queries:
                continue
            key, query = queries.popleft()
            if key in completed:
                continue
            if platform in blocked:
                deferred.append({'query_key': key, 'query': query.to_dict(), 'reason': blocked[platform]})
                continue
            domain = 'cth' if query.domain_id == 'CTH' else 'bmp'
            scope = (scopes or {}).get(domain)
            if platform not in SECONDARY_COLLECTION_PLATFORMS:
                result = {'ok': False, 'status': 'NOT_SUPPORTED', 'platform': platform,
                          'network_attempted': False, 'error_type': 'EXISTING_PLATFORM_ROUTE_REQUIRED'}
            elif not isinstance(scope, Mapping):
                result = {'ok': False, 'status': 'SCOPE_UNAUTHORIZED', 'platform': platform,
                          'network_attempted': False}
            elif not scope.get('global_scope') and (
                    scope.get('subject_id') != query.subject_id or
                    scope.get('brand_focus_id') != query.brand_focus_id):
                result = {'ok': False, 'status': 'SCOPE_UNAUTHORIZED', 'platform': platform,
                          'network_attempted': False, 'error_type': 'QUERY_CALLER_SCOPE_MISMATCH'}
            else:
                try:
                    result = collect_search(platform, query.keyword, max_results=max_results,
                        actor=actor, operator=operator, scope=scope, business_query=query,
                        prelaunch_local_import=operator == 'prelaunch_maintenance',
                        prelaunch_authorization=prelaunch_authorization,
                        attempt_guard=attempt_guard,
                        operation_key=(operation_prefix + ":" + key) if operation_prefix else None)
                except (ValueError, PermissionError) as exc:
                    result = {'ok': False, 'status': 'COLLECTION_REQUEST_REJECTED',
                              'platform': platform, 'error_type': type(exc).__name__}
            runs.append({'query_key': key, 'planned_query': query.to_dict(), 'result': result})
            if result.get('ok') is True and result.get('status') in {'SUCCESS', 'NO_NEW_DATA'}:
                completed.add(key)
                if progress_callback is not None:
                    progress_callback(sorted(completed))
            else:
                blocked[platform] = result.get('status') or 'UNAVAILABLE'
                deferred.append({'query_key': key, 'query': query.to_dict(), 'reason': blocked[platform]})
    return {'ok': not deferred, 'status': 'PARTIAL' if deferred else 'BATCH_COMPLETED',
            'query_plan': plan.to_dict(), 'runs': runs, 'deferred_queries': deferred,
            'checkpoint': {'input_fingerprint': plan.input_fingerprint,
                           'completed_query_keys': sorted(completed)},
            'next_cursor': plan.next_cursor, 'continuation_required': bool(deferred or plan.next_cursor),
            'coverage_complete': False, 'source_scopes_promoted_from_plan': False,
            'product_schedule_operation_proven': False}


__all__ = [
    "SECONDARY_COLLECTION_PLATFORMS",
    "collect_search",
    "collect_business_queries",
    "NativePublicCapture",
    "native_capture_permission_keyword",
    "get_collection_surface",
]


@dataclass(frozen=True)
class PublicRawCapture:
    """Immutable observed bytes and native metadata; this object grants nothing."""
    content: bytes
    sha256: str
    source_url: str
    final_url: str
    content_type: str
    captured_at: str
    published_at: str | None
    rights_json: str
    native_scope_json: str
    purpose: str = "INTERNAL_SOURCE_REVIEW_AND_ORIGINAL_BUSINESS_BRIEF"
    claim_type: str = "BRAND_AUTHORED_SOURCE_CLAIM"

def _public_raw_collection(capture: PublicRawCapture) -> CollectionResult:
    """Normal local Source intake of observed bytes; no fetcher substitution."""
    from .public_source import PublicResponse
    from .public_http import PublicHttpAdapter
    material = _public_raw_material(capture)
    if capture.content_type == "text/html":
        item = PublicHttpAdapter._item(PublicResponse(
            url=capture.final_url, content=capture.content,
            content_type=capture.content_type, status_code=0,
        ))
        if (item["publish_datetime"] or None) != capture.published_at:
            raise ValueError("publication does not match declared original HTML")
    else:
        if capture.published_at is not None:
            raise ValueError("plain directory text has no independent publication signal")
        body = capture.content.decode("utf-8").strip()
        item = {"platform_content_id": "public-http:" + hashlib.sha256(capture.final_url.encode()).hexdigest()[:32],
                "title": body.splitlines()[0] if body else "", "content": body,
                "url": capture.final_url, "publish_datetime": "", "author_id": None,
                "author_nickname": None, "likes": None, "comments": None, "collects": None,
                "shares": None, "raw": {"body_source": "captured_utf8_text",
                    "publication_date_source": "unknown", "publication_date_state": "unknown",
                    "full_body_text": body, "full_body_sha256": hashlib.sha256(body.encode()).hexdigest()}}
    if not item.get("content", "").strip():
        raise ValueError("original Raw contains no source body")
    item["captured_at"] = capture.captured_at
    # Capture time belongs to the signed admission observation, not the stable
    # source identity. The original time remains in the record's captured_at.
    stable_material = {key: value for key, value in material.items() if key != "captured_at"}
    item["raw"].update({"approved_original_capture": stable_material,
                         "original_raw_utf8": capture.content.decode("utf-8")})
    return CollectionResult(status=CollectionStatus.SUCCESS, platform="public_http",
                            items=[PublicHttpAdapter().normalize_item(item)],
                            raw_count=1, new_count=1,
                            metadata={"provider": "approved_original_public_raw", "source": capture.source_url,
                                      "collected_at": capture.captured_at,
                                      "healthcheck_scope": "local_original_capture_only"})

def _public_raw_material(capture: PublicRawCapture) -> dict:
    if (type(capture) is not PublicRawCapture or type(capture.content) is not bytes
            or not 0 < len(capture.content) <= 2 * 1024 * 1024
            or hashlib.sha256(capture.content).hexdigest() != capture.sha256):
        raise ValueError("original Raw bytes/hash required")
    for url in (capture.source_url, capture.final_url):
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if (parts.scheme != "https" or not host or parts.username or parts.password
                or parts.fragment or host == "localhost" or host.endswith((".localhost", ".local"))):
            raise ValueError("public HTTPS capture URL required")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError("private source URL forbidden")
        if _credential_free_observations(url) != url:
            raise ValueError("capture URL contains credential material")
    if capture.content_type not in {"text/html", "text/plain"}:
        raise ValueError("unsupported original Raw representation")
    if not isinstance(capture.captured_at, str) or not any(mark in capture.captured_at for mark in ("T", " ")):
        raise ValueError("actual native capture timestamp required")
    datetime.fromisoformat(capture.captured_at.replace("Z", "+00:00"))
    if capture.published_at is not None:
        datetime.fromisoformat(capture.published_at.replace("Z", "+00:00"))
    rights = json.loads(capture.rights_json)
    native_scope = json.loads(capture.native_scope_json)
    if not isinstance(rights, dict) or not isinstance(native_scope, dict):
        raise ValueError("original rights and native scope required")
    if (_credential_free_observations(rights) != rights
            or _credential_free_observations(native_scope) != native_scope):
        raise ValueError("private capture metadata forbidden")
    if capture.purpose != "INTERNAL_SOURCE_REVIEW_AND_ORIGINAL_BUSINESS_BRIEF":
        raise ValueError("this intake does not grant publication or model training")
    if capture.claim_type not in {"BRAND_AUTHORED_SOURCE_CLAIM", "OFFICIAL_SINGLE_STORE_DIRECTORY"}:
        raise ValueError("explicit supported source claim required")
    capture.content.decode("utf-8", errors="strict")
    return {"version": "approved-public-raw-v1", "raw_sha256": capture.sha256,
            "raw_bytes": len(capture.content), "source_url": capture.source_url,
            "final_url": capture.final_url, "content_type": capture.content_type,
            "captured_at": capture.captured_at, "published_at": capture.published_at,
            "rights": rights, "native_scope": native_scope, "purpose": capture.purpose,
            "claim_type": capture.claim_type}

def _record_public_raw_admission(connection, capture: PublicRawCapture, scope: Mapping[str, Any],
                                 source_ids: List[str], source_evidence_id: int, *, started: str) -> int:
    """Sign the exact capture through the existing Evidence owner and transaction."""
    from lumenis.shared.evidence.store import classify_evidence_integrity, record_evidence
    resource = approved_public_raw_resource(scope, capture)
    inputs = {"original_capture": _public_raw_material(capture), "approval_resource": resource,
              "source_ids": source_ids, "source_evidence_ref": f"app_evidence_records:{source_evidence_id}"}
    rows = connection.execute(
        "SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=?",
        ("SYSTEM_APPROVED_PUBLIC_RAW_ADMISSION", resource),
    ).fetchall()
    if rows:
        if len(rows) != 1:
            raise ValueError("ambiguous original capture admission")
        prior = dict(rows[0])
        prior_inputs = json.loads(prior["inputs_json"])
        if (any(prior_inputs.get(key) != value for key, value in inputs.items())
                or not classify_evidence_integrity(prior).get("verified")):
            raise ValueError("original capture admission cannot be verified")
        return prior["id"]
    bmp = scope["domain_id"] == "bmp"
    evidence_id = record_evidence(
        source="collector", project="LUMENIS", product="ZBMP" if bmp else "CTH",
        feature_id="SYSTEM_APPROVED_PUBLIC_RAW_ADMISSION", asset_id=resource,
        version="approved-public-raw-v1", level="L8", capture_mode="manual",
        captured_at=capture.captured_at, started_at=started,
        inputs=inputs, outputs={"source_ids": source_ids}, result="PASS",
        test_name="approved_original_public_raw_admission", actual="ADMITTED_ORIGINAL_CAPTURE",
        provider="approved_original_public_raw", domain_id="zbmp" if bmp else "cth",
        subject_id=scope.get("subject_id"), brand_focus_id=scope.get("brand_focus_id"),
        global_scope=False, connection=connection,
    )
    if type(evidence_id) is not int or evidence_id <= 0:
        raise ValueError("signed original capture admission unavailable")
    return evidence_id

def approved_public_raw_resource(scope: Mapping[str, Any], capture: PublicRawCapture) -> str:
    """Exact approval binds original Raw identity, times, use and selected focus."""
    exact = _prelaunch_scope(scope)
    material = {"capture": _public_raw_material(capture), "scope": exact}
    digest = hashlib.sha256(json.dumps(material, ensure_ascii=False, sort_keys=True,
                                       separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    return f"prelaunch-public_http:{exact['domain_id']}:{exact['subject_id'] or exact['brand_focus_id']}:{digest}"


class NativeCaptureError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class NativePublicCapture:
    """Frozen public post observation; the DTO grants no scope or permitted use."""
    platform: str
    content: bytes
    sha256: str

def _native_capture_record(capture):
    if type(capture) is not NativePublicCapture or capture.platform not in {
            "xiaohongshu", "douyin", "x", "instagram", "facebook", "wechat"}:
        raise ValueError("explicit supported native observation required")
    return _validate_native_source_bytes(capture.platform, capture.content, capture.sha256)


def _validate_native_source_bytes(platform, content, sha256):
    """Pure source reader shared by frozen input and live observation intake."""
    if platform not in {"xiaohongshu", "douyin", "x", "instagram", "facebook", "wechat"}:
        raise ValueError("explicit supported native observation required")
    if type(content) is not bytes or not 1 <= len(content) <= 2 * 1024 * 1024:
        raise ValueError("bounded native observation bytes required")
    if hashlib.sha256(content).hexdigest() != sha256:
        raise ValueError("native observation bytes changed")
    value = json.loads(content)
    if (not isinstance(value, dict) or value.get("platform") != platform
            or not isinstance(value.get("native_id"), str)
            or value.get("stable_source_key") != platform + ":" + value["native_id"]
            or not isinstance(value.get("body"), str) or not value["body"].strip()
            or hashlib.sha256(value["body"].encode("utf-8")).hexdigest() != value.get("body_sha256")
            or not isinstance(value.get("source_lineage"), list) or not value["source_lineage"]
            or not isinstance(value.get("native_record"), dict)):
        raise ValueError("native post identity/body/lineage required")
    if value.get("body_state") in {"OG_PREVIEW_ONLY_NOT_NATIVE_FULL_POST", "NATIVE_BODY_UNAVAILABLE"}:
        raise NativeCaptureError("NATIVE_BODY_UNAVAILABLE")
    for parent in value["source_lineage"]:
        if (not isinstance(parent, dict) or not re.fullmatch(r"[0-9a-f]{64}", str(parent.get("sha256") or ""))
                or not isinstance(parent.get("locator"), str) or not parent["locator"]):
            raise ValueError("source byte hash and original locator required")
    stamp = value.get("capture_observation_native")
    if not isinstance(stamp, str) or not stamp:
        raise NativeCaptureError("SOURCE_CAPTURE_TIME_UNAVAILABLE")
    # Preserve naive literals rather than silently assigning their timezone.
    datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    parts = urlsplit(value.get("source_url") or "")
    allowed = {
        "xiaohongshu": {"www.rednote.com", "rednote.com"},
        "douyin": {"www.douyin.com", "douyin.com"},
        "x": {"x.com", "www.x.com", "twitter.com", "www.twitter.com"},
        "instagram": {"www.instagram.com", "instagram.com"},
        "facebook": {"www.facebook.com", "facebook.com"},
        "wechat": {"mp.weixin.qq.com"},
    }
    if parts.scheme != "https" or parts.hostname not in allowed[platform] or parts.username or parts.password:
        raise ValueError("approved public platform source URL required")
    from .platform_naming import get_platform_fields
    spec = get_platform_fields(platform)
    native_id = value["native_record"].get(spec.content_id) if spec else None
    if native_id is not None and str(native_id) != value["native_id"]:
        raise ValueError("post identity differs from original native record")
    return value

def native_capture_permission_keyword(capture):
    """Existing manual DATA_IMPORT approval includes the complete observed bytes."""
    _native_capture_record(capture)
    return "native-original:" + capture.platform + ":" + capture.sha256


def _cleanup_collected_source_paths(paths):
    """Remove only immutable files returned by this attempt's Artifact writer."""
    cleaned = True
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            cleaned = False
    return cleaned


def _persist_native_source_original(connection, *, capture, source_id,
                                    collection_evidence_id, context, staged_paths):
    """Retain exact approved native bytes under the existing Source/Artifact owner.

    The Collector caller owns the surrounding savepoint, final authorization,
    commit and file rollback. This JSON source is not an image/video asset and
    its declared rights never grant read, quote, export or training admission.
    """
    value = _native_capture_record(capture)
    return _persist_collected_source_original(
        connection, value=value, source_bytes=capture.content,
        source_fingerprint=capture.sha256, source_id=source_id,
        collection_evidence_id=collection_evidence_id, context=context,
        staged_paths=staged_paths, capture_mode="frozen_native_original_intake",
        source_version="collected-native-source:v1",
        authorization_resource=native_capture_permission_keyword(capture),
    )


def _verified_live_native_observation(platform, observed):
    """Return only an exactly identified native detail body from one observation."""
    if not isinstance(observed, dict):
        raise ValueError("COLLECTED_SOURCE_OBSERVATION_INVALID")
    body = observed.get("content")
    raw = observed.get("source_raw")
    raw = raw if isinstance(raw, dict) else observed
    detail = raw.get("detail_observation")
    detail = detail if isinstance(detail, dict) else {}
    if platform == "xiaohongshu":
        native_detail = (observed.get("detail_fetched") is True
                         and observed.get("detail_identity_verified") is True)
    else:
        native_detail = (detail.get("status") in {"SUCCESS", "REUSED_SAME_NATIVE_ID"}
                         and detail.get("body_kind") in {"NATIVE_POST_BODY", "NATIVE_CAPTION",
                                                         "native_post_text", "caption", "native_caption"}
                         and detail.get("body") == body)
    if not native_detail or not isinstance(body, str) or not body.strip():
        raise ValueError("LIVE_NATIVE_BODY_NOT_VERIFIED")
    from .platform_naming import get_platform_fields, normalize_content_id
    spec = get_platform_fields(platform)
    native_id = normalize_content_id(platform, observed.get(spec.content_id) if spec else None)
    native_id = native_id or normalize_content_id(platform, observed.get("content_id"))
    if not native_id:
        raise ValueError("COLLECTED_SOURCE_NATIVE_ID_MISSING")
    return str(native_id), body


def _persist_live_source_original(connection, *, platform, record, source_id,
                                  collection_evidence_id, context, staged_paths,
                                  scope, keyword, authorization, business_query,
                                  max_results):
    """Preserve an admitted live observation under its actual DATA_IMPORT caller.

    This is Source intake, not SavedWork creation or a frozen manual capture.
    Every other use remains subject to its own rights and Permission checks.
    """
    if not _authorize_prelaunch_public(
            scope, keyword, platform, maintenance_authorization=authorization,
            business_query=business_query, max_results=max_results):
        raise ValueError("COLLECTED_SOURCE_IMPORT_PERMISSION_DENIED")
    from lumenis.shared.evidence import store
    parent = connection.execute("SELECT * FROM app_evidence_records WHERE id=?",
                                (collection_evidence_id,)).fetchone()
    parent = dict(parent) if parent else {}
    integrity = store.classify_evidence_integrity(parent)
    if (integrity.get("verified") is not True or integrity.get("assurance") != "writer-authenticated"
            or parent.get("result") != "PASS" or parent.get("status") != "verified"):
        raise ValueError("COLLECTED_SOURCE_PARENT_INVALID")
    parent_inputs = json.loads(parent.get("inputs_json") or "{}")
    source_id = str(source_id)
    if source_id not in [str(value) for value in parent_inputs.get("source_ids", [])]:
        raise ValueError("COLLECTED_SOURCE_PARENT_INVALID")
    observed = _credential_free_observations(record)
    source_observations = parent_inputs.get("source_observation_records")
    if not isinstance(source_observations, list):
        raise ValueError("COLLECTED_SOURCE_OBSERVATION_MISSING")
    matched = [i for i, value in enumerate(source_observations) if value == observed]
    if len(matched) != 1:
        raise ValueError("COLLECTED_SOURCE_OBSERVATION_AMBIGUOUS")
    native_id, body = _verified_live_native_observation(platform, observed)
    if source_id != native_id:
        # The existing notes importer stores the normalized native ID directly.
        # Never bind an observation to a different source merely by list order.
        raise ValueError("COLLECTED_SOURCE_NATIVE_ID_MISMATCH")
    canonical = connection.execute(
        "SELECT content,publish_datetime,captured_at FROM canonical_data WHERE source_table='notes' "
        "AND source_id=? AND product_id=? AND domain_id=? "
        "AND NULLIF(subject_id,'') IS ? AND NULLIF(brand_focus_id,'') IS ?",
        (source_id, "CTH" if context["domain_id"] == "cth" else "ZBMP", context["domain_id"],
         context["subject_id"], context["brand_focus_id"])).fetchall()
    if len(canonical) != 1 or canonical[0]["content"] != body:
        raise ValueError("COLLECTED_SOURCE_CANONICAL_BODY_MISMATCH")
    captured_at = observed.get("captured_at")
    if not isinstance(captured_at, str) or not captured_at:
        raise ValueError("COLLECTED_SOURCE_CAPTURE_TIME_MISSING")
    observation_bytes = json.dumps(observed, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":")).encode("utf-8")
    parent_ref = "app_evidence_records:" + str(collection_evidence_id)
    value = {
        "platform": platform, "native_id": native_id,
        "stable_source_key": platform + ":" + native_id,
        "source_url": observed.get("url"), "body": body,
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "body_state": "NATIVE_DETAIL_OBSERVED_COMPLETENESS_UNKNOWN",
        "native_record": observed,
        "capture_observation_native": captured_at,
        "publication": {"published_at_utc": canonical[0]["publish_datetime"] or None,
                        "native_time": observed.get("publish_datetime") or None,
                        "normalization_owner": "Canonical publication owner",
                        "timezone_inferred": None},
        "claim_type": "ISSUER_OR_PLATFORM_USER_STATEMENT",
        "rights": {"status": "UNREVIEWED", "allowed_uses": [],
                   "intake_authorization_ref": authorization.authorization_ref,
                   "intake_purpose": "SOURCE_PRESERVATION",
                   "third_party_rights_granted": False},
        "source_lineage": [{"sha256": hashlib.sha256(observation_bytes).hexdigest(),
                            "locator": parent_ref + ":inputs.source_observation_records[" + str(matched[0]) + "]",
                            "kind": "SIGNED_NATIVE_OBSERVATION_JSON",
                            "transport_original": False}],
    }
    # The immutable bytes are explicitly a native observation JSON envelope;
    # they are not raw HTML, media bytes or an unmodified HTTP response.
    source_bytes = json.dumps(value, ensure_ascii=False, sort_keys=True,
                              separators=(",", ":")).encode("utf-8")
    fingerprint = hashlib.sha256(source_bytes).hexdigest()
    _validate_native_source_bytes(platform, source_bytes, fingerprint)
    return _persist_collected_source_original(
        connection, value=value, source_bytes=source_bytes, source_fingerprint=fingerprint,
        source_id=source_id, collection_evidence_id=collection_evidence_id,
        context=context, staged_paths=staged_paths, capture_mode="live_native_observation_intake",
        source_version="collected-native-source:live-v1",
        authorization_resource="collector-source-preservation:" + authorization.plan_id + ":" + fingerprint,
    )


def _persist_pending_live_source_original(connection, *, platform, record, source_id,
                                          collection_evidence_id, context, staged_paths,
                                          scope, keyword, authorization, business_query,
                                          max_results, reason):
    """Preserve an authorized native observation pending business-entity assignment."""
    if not _authorize_prelaunch_public(
            scope, keyword, platform, maintenance_authorization=authorization,
            business_query=business_query, max_results=max_results):
        raise ValueError("COLLECTED_SOURCE_IMPORT_PERMISSION_DENIED")
    if not isinstance(reason, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,100}", reason):
        raise ValueError("PENDING_SOURCE_REASON_INVALID")
    if not isinstance(context, Mapping):
        raise ValueError("PENDING_SOURCE_SCOPE_INVALID")
    from lumenis.shared.evidence import store
    parent = connection.execute("SELECT * FROM app_evidence_records WHERE id=?",
                                (collection_evidence_id,)).fetchone()
    parent = dict(parent) if parent else {}
    integrity = store.classify_evidence_integrity(parent)
    if (integrity.get("verified") is not True
            or integrity.get("assurance") != "writer-authenticated"
            or parent.get("source") != "collector"
            or parent.get("status") != "verified"
            or parent.get("result") not in {"PASS", "FAIL"}
            or parent.get("version") != "collector-native-observation:v2"
            or parent.get("feature_id") != "PRELAUNCH_" + str(platform).upper() + "_COLLECT"):
        raise ValueError("PENDING_SOURCE_PARENT_INVALID")
    try:
        parent_inputs = json.loads(parent.get("inputs_json") or "{}")
        parent_metadata = json.loads(parent.get("collection_metadata") or "{}")
    except (TypeError, ValueError) as exc:
        raise ValueError("PENDING_SOURCE_PARENT_INVALID") from exc
    if not isinstance(parent_inputs, dict) or not isinstance(parent_metadata, dict):
        raise ValueError("PENDING_SOURCE_PARENT_INVALID")
    plan_id = getattr(authorization, "plan_id", None)
    if (not isinstance(plan_id, str) or not plan_id
            or parent_metadata.get("maintenance_plan_id") != plan_id
            or context.get("collector_plan_id") != plan_id):
        raise ValueError("PENDING_SOURCE_PARENT_PLAN_MISMATCH")
    try:
        expected_scope = store._normalize_record_evidence_scope(
            product="CTH" if context.get("domain_id") == "cth" else "ZBMP",
            domain_id=context.get("domain_id"),
            subject_id=context.get("subject_id"),
            brand_focus_id=context.get("brand_focus_id"),
            global_scope=context.get("global_scope"),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("PENDING_SOURCE_SCOPE_INVALID") from exc
    if (expected_scope is None
            or parent_inputs.get("_lumenis_scope") != expected_scope):
        raise ValueError("PENDING_SOURCE_SCOPE_MISMATCH")

    observed = _credential_free_observations(record)
    source_observations = parent_inputs.get("source_observation_records")
    if not isinstance(observed, dict) or not isinstance(source_observations, list):
        raise ValueError("COLLECTED_SOURCE_OBSERVATION_MISSING")
    matched = [i for i, value in enumerate(source_observations) if value == observed]
    if len(matched) != 1:
        raise ValueError("COLLECTED_SOURCE_OBSERVATION_AMBIGUOUS")
    native_id, body = _verified_live_native_observation(platform, observed)
    source_id = str(source_id)
    if source_id != native_id:
        raise ValueError("COLLECTED_SOURCE_NATIVE_ID_MISMATCH")
    captured_at = observed.get("captured_at")
    if not isinstance(captured_at, str) or "T" not in captured_at:
        raise ValueError("COLLECTED_SOURCE_CAPTURE_TIME_MISSING")
    try:
        datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("COLLECTED_SOURCE_CAPTURE_TIME_INVALID") from exc

    observation_bytes = json.dumps(observed, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":")).encode("utf-8")
    parent_ref = "app_evidence_records:" + str(collection_evidence_id)
    body_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
    value = {
        "platform": platform, "native_id": native_id,
        "stable_source_key": platform + ":" + native_id,
        "source_url": observed.get("url"), "body": body,
        "body_sha256": body_sha256,
        "body_state": "NATIVE_DETAIL_OBSERVED_COMPLETENESS_UNKNOWN",
        "native_record": observed,
        "capture_observation_native": captured_at,
        "publication": {"published_at_utc": None,
                        "native_time": observed.get("publish_datetime") or None,
                        "normalization_owner": None,
                        "timezone_inferred": None},
        "claim_type": "ISSUER_OR_PLATFORM_USER_STATEMENT",
        "rights": {"status": "UNREVIEWED", "allowed_uses": [],
                   "intake_authorization_ref": authorization.authorization_ref,
                   "intake_purpose": "SOURCE_PRESERVATION",
                   "third_party_rights_granted": False},
        "source_lineage": [{"sha256": hashlib.sha256(observation_bytes).hexdigest(),
                            "locator": parent_ref + ":inputs.source_observation_records[" + str(matched[0]) + "]",
                            "kind": "SIGNED_NATIVE_OBSERVATION_JSON",
                            "transport_original": False}],
        "entity_assignment": {
            "state": "PENDING", "subject_id": None, "brand_focus_id": None,
            "canonical_ref": None, "context_role": "ACQUISITION_PERMISSION_CONTEXT_ONLY",
            "reason": reason,
        },
    }
    source_bytes = json.dumps(value, ensure_ascii=False, sort_keys=True,
                              separators=(",", ":")).encode("utf-8")
    fingerprint = hashlib.sha256(source_bytes).hexdigest()
    _validate_native_source_bytes(platform, source_bytes, fingerprint)
    return _persist_collected_source_original(
        connection, value=value, source_bytes=source_bytes,
        source_fingerprint=fingerprint, source_id=source_id,
        collection_evidence_id=collection_evidence_id, context=context,
        staged_paths=staged_paths, capture_mode="live_pending_observation_intake",
        source_version="collected-native-source:pending-v1",
        authorization_resource="collector-source-preservation:" + plan_id + ":" + fingerprint,
    )


def _persist_collected_source_original(connection, *, value, source_bytes,
                                       source_fingerprint, source_id,
                                       collection_evidence_id, context, staged_paths,
                                      capture_mode, source_version, authorization_resource):
    """Shared immutable Source writer; callers provide their actual admission."""
    from lumenis.shared.evidence import store
    from lumenis.shared.reporting.saved_work import _stage_bytes, staging_write
    from lumenis.importer.documents import _source_bytes, source_boundaries
    # The retained public source cannot carry transport credentials. Never
    # sanitize approved original bytes and then claim the same source hash.
    if _credential_free_observations(value) != value:
        raise ValueError("COLLECTED_SOURCE_TRANSPORT_CREDENTIALS_FORBIDDEN")
    source_id = str(source_id)
    parent_ref = "app_evidence_records:" + str(collection_evidence_id)
    owner = {key: val for key, val in context.items()
             if key not in {"domain_id", "subject_id", "brand_focus_id", "global_scope"}}
    binding = {"platform": value["platform"], "native_id": value["native_id"],
               "stable_source_key": value["stable_source_key"], "source_id": source_id,
               "body_sha256": value["body_sha256"], "collection_evidence_ref": parent_ref}
    locator = {"unit": "native-post-body", "json_path": "$.body", "start": 0,
               "end": len(value["body"]), "offset_unit": "unicode-codepoint"}
    entity_assignment = value.get("entity_assignment")
    if entity_assignment is not None and not isinstance(entity_assignment, dict):
        raise ValueError("COLLECTED_SOURCE_ENTITY_ASSIGNMENT_INVALID")

    def refs(evidence, metadata, artifact, *, replayed):
        result = {"status": "SAVED", "source_artifact_ref": artifact["artifact_id"],
                  "source_evidence_ref": "app_evidence_records:" + str(evidence["id"]),
                  "source_evidence_version": evidence["version"],
                  "source_signature_verified": False,
                  "source_signature_state": "NATIVE_SIGNATURE_NOT_PROVIDED",
                  "evidence_integrity_verified": True,
                  "evidence_assurance": "writer-authenticated", "replayed": replayed,
                  "source_fingerprint": source_fingerprint, "source_size_bytes": len(source_bytes),
                  "source_kind": "collected_source", "locators": metadata["locators"],
                  "rights": metadata["provenance"]["rights"],
                  "per_use_admission": {"DATA_IMPORT": "CURRENT_CALLER_APPROVED",
                      "READ_ANALYZE_SAVE_EXPORT": "CHECK_EACH_CURRENT_USE", "MODEL_TRAIN": "NOT_GRANTED"},
                  "media_original_status": "NOT_VERIFIED", "media_asset_refs": None}
        if isinstance(metadata.get("entity_assignment"), dict):
            result.update(entity_assignment=metadata["entity_assignment"],
                          scope_status="UNASSIGNED", canonical_ref=None)
        return result

    for row in connection.execute(
            "SELECT * FROM app_evidence_records WHERE source='collector' AND feature_id='COLLECTED_SOURCE' "
            "AND asset_id=? AND content_hash=? ORDER BY id DESC", (source_id, value["body_sha256"])):
        evidence = dict(row)
        try:
            metadata = json.loads(evidence["collection_metadata"])
        except (TypeError, ValueError):
            continue
        if (not isinstance(metadata, dict) or metadata.get("source_fingerprint") != source_fingerprint
                or metadata.get("context") != context or metadata.get("native_source_binding") != binding
                or metadata.get("entity_assignment") != entity_assignment):
            continue
        integrity = store.classify_evidence_integrity(evidence)
        if (integrity.get("verified") is not True or integrity.get("assurance") != "writer-authenticated"
                or evidence.get("status") != "verified" or evidence.get("result") != "PASS"):
            raise ValueError("COLLECTED_SOURCE_INTEGRITY_FAILED")
        raw, artifact = _source_bytes(connection, {**evidence, "provenance": metadata})
        if raw != source_bytes:
            raise ValueError("COLLECTED_SOURCE_REPLAY_CONFLICT")
        return refs(evidence, metadata, artifact, replayed=True)

    publication = value.get("publication") or {}
    provenance = {"source_url": value["source_url"],
                  "published_at": publication.get("published_at_utc"),
                  "captured_at": value["capture_observation_native"],
                  "rights": value.get("rights"), "intended_use": "source_preservation",
                  "title": value["native_record"].get("title"),
                  "content_origin": {"kind": "publisher-material", "claim_type": "source_statement"}}
    metadata = {"context": dict(context), "owner": owner, "provenance": provenance,
                "source_url": value["source_url"], "source_fingerprint": source_fingerprint,
                "parsed_text": value["body"], "source_kind": "collected_source",
                "native_source_binding": binding, "locators": [locator],
                "native_claim_type": value.get("claim_type"),
                "native_publication": publication, "source_lineage": value["source_lineage"],
                "capture_mode": capture_mode,
                "autonomous_collection": False if capture_mode == "frozen_native_original_intake" else None,
                "autonomous_execution_verification": "SCHEDULER_RECEIPT_REQUIRED",
                **source_boundaries(provenance)}
    if entity_assignment is not None:
        metadata["entity_assignment"] = entity_assignment
    child_inputs = {"source_ids": [source_id], "collection_evidence_ref": parent_ref,
                    "source_intake_resource": authorization_resource}
    if entity_assignment is not None:
        child_inputs["entity_assignment"] = entity_assignment
    with staging_write(authorization_resource):
        artifact, path = _stage_bytes(
            connection, raw=source_bytes, context=context, kind="collected_source",
            source_execution_id=source_id, extension=".json", media_type="application/json")
        staged_paths.append(path)
        metadata["source_artifact_ref"] = artifact["artifact_id"]
        evidence_id = store.record_evidence(
            connection=connection, source="collector", project="LUMENIS",
            product="CTH" if context["domain_id"] == "cth" else "ZBMP",
            feature_id="COLLECTED_SOURCE", asset_id=source_id, version=source_version,
            capture_mode=capture_mode, captured_at=value["capture_observation_native"],
            inputs=child_inputs,
            outputs={"source_artifact_ref": artifact["artifact_id"],
                     "native_body_sha256": value["body_sha256"], "source_fingerprint": source_fingerprint},
            raw_content=value["body"], collection_metadata=metadata,
            publish_datetime=publication.get("published_at_utc") or "", provider="collector-native-original",
            domain_id=context["domain_id"], subject_id=context["subject_id"],
            brand_focus_id=context["brand_focus_id"], global_scope=context["global_scope"])
        connection.execute("UPDATE lumenis_shared_artifacts SET note_id=?,evidence_id=? WHERE artifact_id=?",
                           (source_id, str(evidence_id), artifact["artifact_id"]))
        evidence = dict(connection.execute("SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)).fetchone())
        integrity = store.classify_evidence_integrity(evidence)
        if integrity.get("verified") is not True or integrity.get("assurance") != "writer-authenticated":
            raise ValueError("COLLECTED_SOURCE_INTEGRITY_FAILED")
        raw, artifact = _source_bytes(connection, {**evidence, "provenance": metadata})
        if raw != source_bytes:
            raise ValueError("COLLECTED_SOURCE_ORIGINAL_INVALID")
        return refs(evidence, metadata, artifact, replayed=False)


def _persist_pending_live_observations(connection, *, platform, records,
                                       collection_evidence_id, context, staged_paths,
                                       scope, keyword, authorization, business_query,
                                       max_results, reviews, saved_ids, covers=None):
    """Preserve reviewed/unbound native originals without assigning entity facts."""
    from .platform_naming import get_platform_fields, normalize_content_id
    from lumenis.shared.evidence import store
    spec = get_platform_fields(platform)
    review_by_id = {}
    for review in reviews:
        if isinstance(review, dict):
            review_by_id.setdefault(str(review.get("platform_content_id")), []).append(review)
    originals = []
    for record in records[:max_results]:
        source_id = (normalize_content_id(platform, record.get(spec.content_id) if spec else None)
                     or normalize_content_id(platform, record.get("content_id")))
        if source_id and str(source_id) in saved_ids:
            continue
        reviews_for_source = review_by_id.get(str(source_id), [])
        excluded = next((review for review in reviews_for_source if review.get("status") in {
            "EXCLUDED_TASK_BOUNDARY", "OUTSIDE_REQUESTED_PUBLICATION_PERIOD"}), None)
        if excluded is not None:
            originals.append({"source_id": source_id, "status": "EXCLUDED",
                "reason": excluded["status"], "source_evidence_ref": None,
                "source_artifact_ref": None, "canonical_ref": None,
                "original_observation_ref": "app_evidence_records:" + str(collection_evidence_id),
                "entity_assignment": "NOT_ADMITTED"})
            continue
        source_path_start = len(staged_paths)
        connection.execute("SAVEPOINT pending_live_original")
        try:
            original = _persist_pending_live_source_original(
                connection, platform=platform, record=record, source_id=source_id,
                collection_evidence_id=collection_evidence_id, context=context,
                staged_paths=staged_paths, scope=scope, keyword=keyword,
                authorization=authorization, business_query=business_query,
                max_results=max_results, reason="SOURCE_ENTITY_IDENTITY_UNCONFIRMED")
            if isinstance(covers, Mapping):
                cover_refs = {"status": "NULL", "reason": "NO_OBSERVED_COVER",
                              "media_asset_refs": None}
                cover_path_start = len(staged_paths)
                cover_savepoint_open = False
                try:
                    cover = covers.get(str(source_id))
                    if isinstance(cover, dict):
                        cover_status = cover.get("status")
                        if cover_status == "AVAILABLE":
                            connection.execute("SAVEPOINT pending_live_cover")
                            cover_savepoint_open = True
                            cover_refs = _persist_live_post_cover(
                                connection, cover=cover, platform=platform, source_id=source_id,
                                context=context, body_original=original, staged_paths=staged_paths,
                                authorization_resource="collector-cover:" + authorization.plan_id,
                            )
                            connection.execute("RELEASE SAVEPOINT pending_live_cover")
                            cover_savepoint_open = False
                        else:
                            reason = cover.get("reason")
                            cover_refs = {"status": "NULL",
                                          "reason": reason if isinstance(reason, str)
                                                    and re.fullmatch(r"[A-Z][A-Z0-9_]{0,100}", reason) else
                                                    "COVER_FETCH_UNAVAILABLE",
                                          "media_asset_refs": None}
                except Exception as cover_error:
                    if cover_savepoint_open:
                        connection.execute("ROLLBACK TO SAVEPOINT pending_live_cover")
                        connection.execute("RELEASE SAVEPOINT pending_live_cover")
                    cleaned = _cleanup_collected_source_paths(staged_paths[cover_path_start:])
                    del staged_paths[cover_path_start:]
                    reason = (str(cover_error) if isinstance(cover_error, ValueError)
                              and re.fullmatch(r"[A-Z][A-Z0-9_]{0,100}", str(cover_error))
                              else "COVER_INTAKE_FAILED")
                    cover_refs = {"status": "NULL", "reason": reason,
                                  "media_asset_refs": None,
                                  "cleanup_status": "COMPLETE" if cleaned else "FAILED"}
                original["cover"] = cover_refs
                original["media_original_status"] = (
                    "PARTIAL_COVER_ONLY" if cover_refs.get("status") == "SAVED"
                    else "NOT_VERIFIED")
                original["media_asset_refs"] = cover_refs.get("media_asset_refs")
                original["media_understanding"] = {
                    "required": True, "state": "NOT_RUN",
                    "reason": "POST_INTAKE_MEDIA_JOB_BINDING_NOT_IMPLEMENTED",
                    "native_media_locator": {
                        "source_artifact_ref": original["source_artifact_ref"],
                        "source_evidence_ref": original["source_evidence_ref"],
                        "source_fingerprint": original["source_fingerprint"],
                        "json_path": "$.native_record",
                        "representation": "OBSERVED_NATIVE_METADATA"},
                    "image_input_refs": cover_refs.get("media_asset_refs"),
                    "image_analysis_ref": None, "video_analysis_ref": None,
                    "speech_transcript_ref": None,
                    "full_post_media_coverage": "UNKNOWN",
                    "job_enqueued": False,
                    "per_use_admission": "CHECK_CURRENT_MEDIA_ANALYSIS_USE",
                }
            connection.execute("RELEASE SAVEPOINT pending_live_original")
            originals.append({"source_id": source_id, **original,
                              "keyword_analysis_state": "PENDING",
                              "media_understanding_state": "NOT_RUN", "job_enqueued": False})
        except Exception as exc:
            connection.execute("ROLLBACK TO SAVEPOINT pending_live_original")
            connection.execute("RELEASE SAVEPOINT pending_live_original")
            cleaned = _cleanup_collected_source_paths(staged_paths[source_path_start:])
            del staged_paths[source_path_start:]
            originals.append({"source_id": source_id, "status": "UNAVAILABLE",
                "reason": str(exc) if isinstance(exc, ValueError)
                    and re.fullmatch(r"[A-Z][A-Z0-9_]{0,100}", str(exc))
                    else "PENDING_SOURCE_PRESERVATION_UNAVAILABLE",
                "source_evidence_ref": None, "source_artifact_ref": None,
                "canonical_ref": None, "scope_status": "UNASSIGNED",
                "cleanup_status": "COMPLETE" if cleaned else "FAILED"})
    saved = sum(row["status"] == "SAVED" for row in originals)
    summary = {"observed_records": len(records), "formal_saved_records_skipped": len(saved_ids),
               "unassigned_originals_saved": saved,
               "unassigned_originals_unavailable": sum(row["status"] == "UNAVAILABLE" for row in originals),
               "excluded_observations": sum(row["status"] == "EXCLUDED" for row in originals),
               "observations_beyond_authorized_batch": max(0, len(records) - max_results),
               "canonical_rows_created": 0, "entity_assignment": "PENDING",
               "keyword_processing_mode": "POST_COMMIT_SOURCE_BACKLOG",
               "media_understanding_state": "NOT_RUN", "job_enqueued": False}
    if isinstance(covers, Mapping):
        summary["covers_saved"] = sum(
            row.get("cover", {}).get("status") == "SAVED" for row in originals)
        summary["covers_null"] = sum(
            row.get("cover", {}).get("status") == "NULL" for row in originals)
        summary["max_cover_images_per_post"] = 1
    outcome_ref = None
    if originals:
        connection.execute("SAVEPOINT pending_source_outcome")
        try:
            outcome_id = store.record_evidence(
                connection=connection, source="collector", project="LUMENIS",
                product="CTH" if context["domain_id"] == "cth" else "ZBMP",
                feature_id="COLLECTOR_PENDING_SOURCE_INTAKE_OUTCOME",
                asset_id=authorization.plan_id, version="collector-pending-source-intake:v1",
                capture_mode="live_pending_source_intake_outcome", captured_at=_now(),
                inputs={"collection_evidence_ref": "app_evidence_records:" + str(collection_evidence_id),
                        "authorization_ref": authorization.authorization_ref},
                outputs={"summary": summary, "original_refs": originals},
                collection_metadata={"kind": "DERIVATIVE_EXECUTION_OUTCOME",
                                     "context_role": "ACQUISITION_PERMISSION_CONTEXT_ONLY"},
                result="PASS" if saved == len(originals) else "FAIL",
                actual="PENDING_ORIGINALS_PRESERVED" if saved == len(originals)
                       else "PARTIAL_PENDING_SOURCE_PRESERVATION",
                provider="collector-source-intake", domain_id=context["domain_id"],
                subject_id=context["subject_id"], brand_focus_id=context["brand_focus_id"],
                global_scope=False)
            connection.execute("RELEASE SAVEPOINT pending_source_outcome")
            outcome_ref = "app_evidence_records:" + str(outcome_id)
        except Exception:
            connection.execute("ROLLBACK TO SAVEPOINT pending_source_outcome")
            connection.execute("RELEASE SAVEPOINT pending_source_outcome")
    return {"original_refs": originals, "summary": summary, "outcome_ref": outcome_ref}


def _preserve_prelaunch_originals_after_rollback(*, platform, keyword, scope,
                                                 authorization, business_query,
                                                 max_results, observations, reviews,
                                                 original_result, started,
                                                 acquisition_ok, acquisition_status,
                                                 covers=None):
    """Save only verified native originals in a new authorized transaction.

    This recovery preserves permitted observations after an allowlisted primary
    write failure. It never retries the failed Canonical import or marks the
    original collection result successful.
    """
    allowed_platforms = {"xiaohongshu", "douyin", "x", "instagram", "facebook", "wechat"}
    allowed_failures = {"CANONICAL_SYNC_FAILED", "IMPORT_FAILED", "EVIDENCE_WRITE_FAILED"}
    failure_status = original_result.get("status") if isinstance(original_result, dict) else None
    staged_paths = []
    parent_ref = None
    pending = None
    committed = False

    def unavailable(reason, *, refs=None, cleanup_status=None):
        safe_refs = refs if isinstance(refs, list) else []
        if not safe_refs:
            for observed in observations if isinstance(observations, list) else []:
                try:
                    source_id, _ = _verified_live_native_observation(platform, observed)
                except (TypeError, ValueError):
                    source_id = None
                safe_refs.append({
                    "source_id": source_id, "status": "UNAVAILABLE",
                    "source_evidence_ref": None, "source_artifact_ref": None,
                    "canonical_ref": None, "reason": reason,
                })
        else:
            safe_refs = [{
                "source_id": row.get("source_id"), "status": "UNAVAILABLE",
                "source_evidence_ref": None, "source_artifact_ref": None,
                "canonical_ref": None, "reason": reason,
            } for row in safe_refs if isinstance(row, dict)]
        return {
            "status": "UNAVAILABLE", "error_type": reason,
            "parent_evidence_ref": None,
            "pending_source_intake_outcome_ref": None,
            "original_refs": safe_refs,
            "source_originals_saved": 0,
            "source_originals_unavailable": len(safe_refs),
            "canonical_rows_created": 0,
            "cleanup_status": cleanup_status,
        }

    if (platform not in allowed_platforms or failure_status not in allowed_failures
            or acquisition_ok is not True or acquisition_status not in {"SUCCESS", "NO_NEW_DATA"}
            or not isinstance(observations, list) or not observations):
        return unavailable("ORIGINAL_PRESERVATION_NOT_ELIGIBLE")
    try:
        from ..acquisition_plan import AcquisitionQuery
        from .platform_naming import normalize_platform
        from .scheduling.prelaunch_baseline import (
            PURPOSE_POLICY, PrelaunchMaintenanceAuthorization,
        )
        if (not isinstance(authorization, PrelaunchMaintenanceAuthorization)
                or authorization.signature_verified is not True
                or authorization.policy_id != PURPOSE_POLICY
                or type(business_query) is not AcquisitionQuery
                or business_query.keyword != keyword
                or not isinstance(business_query.business_context, Mapping)
                or normalize_platform(business_query.business_context.get("platform")) != platform
                or type(max_results) is not int or not 1 <= max_results <= MAX_RESULTS):
            return unavailable("ORIGINAL_PRESERVATION_AUTHORIZATION_UNAVAILABLE")
        exact_scope = _prelaunch_scope(scope)
        if not authorization.matches_request(
                source_url=keyword, platform=platform, scope=exact_scope):
            return unavailable("ORIGINAL_PRESERVATION_SCOPE_MISMATCH")
        provenance = original_result.get("provenance") if isinstance(original_result, dict) else None
        provenance = _credential_free_observations(provenance) if isinstance(provenance, dict) else {}
        if (provenance.get("maintenance_plan_id") != authorization.plan_id
                or provenance.get("authorization_ref") != authorization.authorization_ref
                or provenance.get("source_version") != authorization.source_version
                or provenance.get("scope_version") != authorization.scope_version
                or provenance.get("planned_business_query") != business_query.to_dict()):
            return unavailable("ORIGINAL_PRESERVATION_PROVENANCE_MISMATCH")
        if not _authorize_prelaunch_public(
                exact_scope, keyword, platform,
                maintenance_authorization=authorization,
                business_query=business_query, max_results=max_results):
            return unavailable("ORIGINAL_PRESERVATION_PERMISSION_UNAVAILABLE")

        import database as db
        from .platform_naming import normalize_platform as _normalize_platform

        source_context = {
            **exact_scope,
            "domain_id": "zbmp" if exact_scope["domain_id"] == "bmp" else "cth",
            "global_scope": False,
            "collector_plan_id": authorization.plan_id,
            "collector_authorization_ref": authorization.authorization_ref,
        }
        clean_observations = _credential_free_observations(observations)
        if (not isinstance(clean_observations, list)
                or _credential_free_observations(clean_observations) != clean_observations):
            return unavailable("ORIGINAL_PRESERVATION_OBSERVATION_INVALID")
        if _normalize_platform(authorization.platform) != platform:
            return unavailable("ORIGINAL_PRESERVATION_PLATFORM_MISMATCH")
        failure_error_type = original_result.get("error_type")
        if failure_error_type not in allowed_failures:
            failure_error_type = failure_status

        failed_parent_result = {
            "ok": False, "status": failure_status, "raw_count": original_result.get("raw_count"),
            "imported": 0, "updated": 0, "failed": 0,
            "canonical_synced": 0, "native_fields_synced": 0,
            "entity_mentions": [],
            "provenance": {
                **provenance,
                "original_write_failure": {
                    "status": failure_status,
                    "error_type": failure_error_type,
                    "duration_ms": (original_result.get("duration_ms")
                                    if type(original_result.get("duration_ms")) is int
                                    and original_result.get("duration_ms") >= 0 else None),
                    "native_observed_count": len(clean_observations),
                },
                "preservation_mode": "ORIGINALS_ONLY_NO_CANONICAL",
                "source_acquisition_status": acquisition_status,
            },
        }
        with db.get_db() as connection:
            connection.execute("BEGIN IMMEDIATE")
            _validate_prelaunch_registry(exact_scope, connection=connection)
            if not _authorize_prelaunch_public(
                    exact_scope, keyword, platform,
                    maintenance_authorization=authorization,
                    business_query=business_query, max_results=max_results):
                raise PermissionError("ORIGINAL_PRESERVATION_PERMISSION_UNAVAILABLE")
            parent_id = _write_prelaunch_evidence(
                platform, keyword, failed_parent_result, started=started,
                scope=exact_scope, source_ids=[], review_candidates=clean_observations,
                manual=False, observations=clean_observations, connection=connection,
            )
            if type(parent_id) is not int or parent_id <= 0:
                raise ValueError("ORIGINAL_PRESERVATION_PARENT_EVIDENCE_FAILED")
            parent_ref = "app_evidence_records:" + str(parent_id)
            clean_reviews = _credential_free_observations(reviews if isinstance(reviews, list) else [])
            pending = _persist_pending_live_observations(
                connection, platform=platform, records=clean_observations,
                collection_evidence_id=parent_id, context=source_context,
                staged_paths=staged_paths, scope=exact_scope, keyword=keyword,
                authorization=authorization, business_query=business_query,
                max_results=max_results, reviews=clean_reviews, saved_ids=set(),
                covers=covers,
            )
            if not _authorize_prelaunch_public(
                    exact_scope, keyword, platform,
                    maintenance_authorization=authorization,
                    business_query=business_query, max_results=max_results):
                raise PermissionError("ORIGINAL_PRESERVATION_PERMISSION_UNAVAILABLE")

        committed = True
        refs = pending.get("original_refs", []) if isinstance(pending, dict) else []
        refs = [row for row in refs if isinstance(row, dict)]
        eligible_refs = [row for row in refs if row.get("status") != "EXCLUDED"]
        saved_count = sum(row.get("status") == "SAVED" for row in eligible_refs)
        unavailable_count = sum(row.get("status") == "UNAVAILABLE" for row in eligible_refs)
        recovery_status = (
            "UNAVAILABLE" if saved_count == 0 else
            "SAVED" if saved_count == len(eligible_refs) and eligible_refs else "PARTIAL"
        )
        return {
            "status": recovery_status,
            "error_type": None if recovery_status == "SAVED" else
                          "ORIGINAL_PRESERVATION_PARTIAL" if recovery_status == "PARTIAL" else
                          "NO_SOURCE_ORIGINAL_SAVED",
            "parent_evidence_ref": parent_ref,
            "pending_source_intake_outcome_ref": pending.get("outcome_ref"),
            "original_refs": refs,
            "source_originals_saved": saved_count,
            "source_originals_unavailable": unavailable_count,
            "source_originals_excluded": sum(row.get("status") == "EXCLUDED" for row in refs),
            "canonical_rows_created": 0,
            "summary": pending.get("summary"),
        }
    except Exception:
        if committed:
            # A response-construction failure cannot revoke committed Source
            # artifacts or claim that their transaction was rolled back.
            return {
                "status": "READBACK_REQUIRED", "parent_evidence_ref": parent_ref,
                "error_type": "ORIGINAL_PRESERVATION_RECEIPT_UNAVAILABLE",
                "pending_source_intake_outcome_ref": None, "original_refs": [],
                "source_originals_saved": None, "canonical_rows_created": 0,
                "source_commit_state": "COMMITTED", "cleanup_status": "NOT_APPLICABLE",
            }
        cleanup_ok = _cleanup_collected_source_paths(staged_paths)
        return unavailable(
            "ORIGINAL_PRESERVATION_TRANSACTION_FAILED",
            refs=(pending.get("original_refs", []) if isinstance(pending, dict) else None),
            cleanup_status="COMPLETE" if cleanup_ok else "FAILED",
        )


def recover_prelaunch_pending_sources(*, limit=40):
    """Recover permitted originals from retained observations, never recollect."""
    from lumenis.shared.database import get_repository
    from lumenis.shared.evidence import store
    from lumenis.importer.documents import _source_bytes
    from .scheduling.prelaunch_baseline import (
        PURPOSE_POLICY, _purpose_query, load_prelaunch_baseline_config, maintenance_authorization,
    )
    if type(limit) is not int or not 1 <= limit <= 40:
        raise ValueError("PENDING_SOURCE_RECOVERY_LIMIT_INVALID")
    loaded = load_prelaunch_baseline_config(os.environ.get("LUMENIS_PRELAUNCH_BASELINE_CONFIG") or None)
    plans = {p.plan_id: p for p in loaded.get("plans", []) if p.policy_id == PURPOSE_POLICY}
    con = get_repository().connect(timeout=10)
    outcomes, scanned, deferred = [], 0, 0
    try:
        preserved = set()
        for row in con.execute("SELECT * FROM app_evidence_records WHERE feature_id='COLLECTED_SOURCE' "
                               "AND source='collector' AND result='PASS' AND status='verified'"):
            source = dict(row)
            try:
                meta = json.loads(source["collection_metadata"])
                if store.classify_evidence_integrity(source).get("assurance") != "writer-authenticated":
                    continue
                _source_bytes(con, {**source, "provenance": meta})
                binding = meta["native_source_binding"]
                preserved.add((binding["collection_evidence_ref"], binding["native_id"]))
            except Exception:
                continue
        parents = con.execute(
            "SELECT * FROM app_evidence_records WHERE source='collector' "
            "AND version='collector-native-observation:v2' ORDER BY id").fetchall()
        for row in parents:
            if len(outcomes) >= limit:
                break
            parent = dict(row)
            try:
                metadata = json.loads(parent["collection_metadata"] or "{}")
                plan = plans.get(metadata.get("maintenance_plan_id"))
                if plan is None:
                    continue
                inputs = json.loads(parent["inputs_json"] or "{}")
                observations = inputs.get("source_observation_records")
                integrity = store.classify_evidence_integrity(parent)
                if (not isinstance(observations, list) or integrity.get("verified") is not True
                        or integrity.get("assurance") != "writer-authenticated"):
                    continue
                query = _purpose_query(plan.purpose_query)
                scope = {"domain_id": plan.domain_id, "subject_id": plan.subject_id,
                         "brand_focus_id": plan.brand_focus_id}
                context = {**scope, "domain_id": "zbmp" if plan.domain_id == "bmp" else "cth",
                           "global_scope": False, "collector_plan_id": plan.plan_id,
                           "collector_authorization_ref": plan.authorization_ref}
                authorization = maintenance_authorization(plan)
                parent_ref = "app_evidence_records:" + str(parent["id"])
                eligible = []
                for observation in observations[:plan.max_results]:
                    scanned += 1
                    try:
                        native_id, _ = _verified_live_native_observation(plan.platform, observation)
                    except (TypeError, ValueError):
                        deferred += 1
                        continue
                    if (parent_ref, native_id) not in preserved:
                        eligible.append(observation)
                if not eligible:
                    continue
                # Use the actual observation cutoff in the retained parent.
                # No current capture timestamp supplies a missing publication year.
                reviews = _business_source_reviews(
                    eligible, query, metadata.get("actual_response_observation_utc"))
                permitted = [(observation, review) for observation, review in zip(eligible, reviews)
                             if review.get("status") not in {
                                 "EXCLUDED_TASK_BOUNDARY", "OUTSIDE_REQUESTED_PUBLICATION_PERIOD"}]
                permitted = permitted[:limit - len(outcomes)]
                eligible = [item[0] for item in permitted]
                reviews = [item[1] for item in permitted]
                if not eligible:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            paths, committed = [], False
            try:
                con.execute("BEGIN IMMEDIATE")
                result = _persist_pending_live_observations(
                    con, platform=plan.platform, records=eligible,
                    collection_evidence_id=parent["id"], context=context, staged_paths=paths,
                    scope=scope, keyword=plan.source_url, authorization=authorization,
                    business_query=query, max_results=plan.max_results, reviews=reviews, saved_ids=set())
                if not _authorize_prelaunch_public(
                        scope, plan.source_url, plan.platform, maintenance_authorization=authorization,
                        business_query=query, max_results=plan.max_results):
                    raise ValueError("COLLECTED_SOURCE_IMPORT_PERMISSION_DENIED")
                con.commit()
                committed = True
                for item in result["original_refs"]:
                    outcomes.append({"collection_evidence_ref": parent_ref,
                                     "outcome_ref": result["outcome_ref"], **item})
                    if item.get("status") == "SAVED":
                        preserved.add((parent_ref, str(item["source_id"])))
            except Exception:
                con.rollback()
                outcomes.append({"collection_evidence_ref": parent_ref, "status": "UNAVAILABLE",
                                 "reason": "PENDING_SOURCE_RECOVERY_UNAVAILABLE"})
            finally:
                if not committed:
                    _cleanup_collected_source_paths(paths)
        saved = sum(r.get("status") == "SAVED" for r in outcomes)
        return {"status": "PARTIAL" if any(r.get("status") == "UNAVAILABLE" for r in outcomes)
                else "COMPLETED", "processed": len(outcomes), "saved": saved,
                "observations_scanned": scanned, "native_detail_unavailable": deferred,
                "canonical_rows_created": 0, "network_collection": False,
                "scope_status": "UNASSIGNED", "results": outcomes}
    finally:
        con.close()


def process_prelaunch_keyword_backlog(*, limit=40):
    """Resume post-intake work from persisted Sources, without recollection.

    The existing resident maintenance entry calls this on every tick. Its
    backlog is the Source/Evidence already in the sole production database;
    there is no second queue or keyword store. Per-source failure is isolated.
    """
    from lumenis.shared.database import get_repository
    from lumenis.shared.evidence import store
    from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import (
        PURPOSE_POLICY, POST_INTAKE_KEYWORD_POLICY,
        load_prelaunch_baseline_config, maintenance_authorization,
    )
    if type(limit) is not int or not 1 <= limit <= 40:
        raise ValueError("POST_INTAKE_BACKLOG_LIMIT_INVALID")
    loaded = load_prelaunch_baseline_config(os.environ.get("LUMENIS_PRELAUNCH_BASELINE_CONFIG") or None)
    plans = {plan.plan_id: plan for plan in loaded.get("plans", [])
             if plan.policy_id == PURPOSE_POLICY and plan.post_intake_policy}
    if not plans:
        return {"status": "DISABLED", "processed": 0, "saved": 0, "pending": 0}
    repository = get_repository()
    connection = repository.connect(timeout=10)
    outcomes = []
    try:
        # Metadata is a navigation index only. Actual content/use/lineage is
        # checked afresh by Permission and the Source reader in each operation.
        completed = set()
        for row in connection.execute(
                "SELECT * FROM app_evidence_records WHERE feature_id='COLLECTED_KEYWORD_CANDIDATES' "
                "AND version=? AND result='PASS' AND status='verified' ORDER BY id DESC",
                (POST_INTAKE_KEYWORD_POLICY["processing_version"],)):
            evidence = dict(row)
            try:
                metadata = json.loads(evidence.get("collection_metadata") or "{}")
                source_inputs = metadata.get("source_inputs") or {}
                if (source_inputs.get("plan_id") in plans
                        and source_inputs.get("policy") == plans[source_inputs["plan_id"]].post_intake_policy
                        and source_inputs.get("extraction_context") == _post_intake_extraction_context(
                            plans[source_inputs["plan_id"]])
                        and store.classify_evidence_integrity(evidence).get("verified") is True):
                    _keyword_candidate_bytes(connection, evidence)
                    canonical = connection.execute("SELECT raw_ref FROM canonical_data WHERE canonical_id=?",
                                                   (source_inputs.get("canonical_ref"),)).fetchone()
                    refs = json.loads(canonical["raw_ref"] or "{}") if canonical else {}
                    if (refs.get("content_evidence_ref") != source_inputs.get("source_evidence_ref")
                            or (refs.get("keyword_candidates") or {}).get("keyword_evidence_ref") ==
                            "app_evidence_records:" + str(evidence["id"])):
                        completed.add(source_inputs.get("source_evidence_ref"))
            except Exception:
                continue
        source_rows = connection.execute(
            "SELECT * FROM app_evidence_records WHERE source='collector' AND feature_id='COLLECTED_SOURCE' "
            "AND version IN ('collected-native-source:live-v1','collected-native-source:pending-v1') "
            "AND result='PASS' AND status='verified' "
            "ORDER BY id").fetchall()
        for row in source_rows:
            if len(outcomes) >= limit:
                break
            evidence = dict(row)
            source_ref = "app_evidence_records:" + str(evidence["id"])
            if source_ref in completed:
                continue
            try:
                metadata = json.loads(evidence.get("collection_metadata") or "{}")
                context = metadata.get("context") or {}
                plan = plans.get(context.get("collector_plan_id"))
                if plan is None:
                    continue
                authorization = maintenance_authorization(plan)
                scope = {"domain_id": plan.domain_id, "subject_id": plan.subject_id,
                         "brand_focus_id": plan.brand_focus_id}
                original = {"source_evidence_ref": source_ref,
                            "source_fingerprint": metadata.get("source_fingerprint"),
                            "source_evidence_version": evidence["version"]}
            except Exception:
                continue
            paths = []
            committed = False
            try:
                connection.execute("BEGIN IMMEDIATE")
                result = _persist_post_intake_keyword_candidates(
                    connection, original=original, context=context, scope=scope,
                    authorization=authorization, staged_paths=paths)
                connection.commit()
                committed = True
                outcomes.append({"source_evidence_ref": source_ref, **result})
            except Exception as exc:
                connection.rollback()
                outcomes.append({"source_evidence_ref": source_ref, "status": "PENDING",
                    "keyword_evidence_ref": None, "keyword_artifact_ref": None,
                    "reason": str(exc) if isinstance(exc, ValueError)
                        and re.fullmatch(r"[A-Z][A-Z0-9_]{0,100}", str(exc))
                        else "POST_INTAKE_PROCESSING_UNAVAILABLE"})
            finally:
                if not committed and not _cleanup_collected_source_paths(paths):
                    outcomes[-1]["cleanup_status"] = "FAILED"
        saved = sum(row.get("status") == "SAVED" for row in outcomes)
        return {"status": "COMPLETED" if saved == len(outcomes) else "PARTIAL",
                "processed": len(outcomes), "saved": saved, "pending": len(outcomes) - saved,
                "owned_inference": "NOT_RUN", "results": outcomes}
    finally:
        connection.close()


def _keyword_candidate_bytes(connection, evidence):
    """Read back a derivative through the existing Artifact/Evidence owners."""
    import shared_artifacts
    from lumenis.shared.evidence import store
    metadata = json.loads(evidence.get("collection_metadata") or "{}")
    integrity = store.classify_evidence_integrity(evidence)
    row = connection.execute(
        "SELECT * FROM lumenis_shared_artifacts WHERE artifact_id=? AND kind=?",
        (metadata.get("keyword_artifact_ref"), "collected_keyword_candidates")).fetchone()
    if (row is None or evidence.get("feature_id") != "COLLECTED_KEYWORD_CANDIDATES"
            or evidence.get("status") != "verified" or evidence.get("result") != "PASS"
            or integrity.get("verified") is not True
            or integrity.get("assurance") != "writer-authenticated"):
        raise ValueError("POST_INTAKE_DERIVATIVE_INTEGRITY_FAILED")
    artifact = dict(row)
    root = shared_artifacts.artifact_root().resolve()
    path = (root / artifact["relative_path"]).resolve()
    if (not path.is_relative_to(root) or not path.is_file()
            or not 0 < artifact["size_bytes"] <= 8 * 1024 * 1024
            or artifact["source_execution_id"] != evidence["asset_id"]
            or artifact["evidence_id"] != str(evidence["id"])
            or artifact["domain_id"] != evidence["domain_id"]):
        raise ValueError("POST_INTAKE_DERIVATIVE_ARTIFACT_INVALID")
    with path.open("rb") as handle:
        raw = handle.read(8 * 1024 * 1024 + 1)
    if (len(raw) != artifact["size_bytes"]
            or hashlib.sha256(raw).hexdigest() != artifact["sha256"]
            or artifact["sha256"] != metadata.get("derivative_sha256")):
        raise ValueError("POST_INTAKE_DERIVATIVE_ARTIFACT_INVALID")
    return raw, artifact


def _persist_post_intake_keyword_candidates(connection, *, original, context, scope,
                                             authorization, staged_paths):
    """Append deterministic candidates after separately authorized Source use.

    No model, source-rights promotion, native-topic assertion or automatic query
    adoption occurs here. The surrounding caller owns transaction and cleanup.
    """
    from lumenis.importer.analyzer import extract_source_keyword_candidates
    from lumenis.importer.documents import _source_bytes
    from lumenis.system.security import get_permission_gate
    from lumenis.system.collector.acquisition_plan import build_observed_topic_catalog
    from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import (
        POST_INTAKE_KEYWORD_POLICY, load_prelaunch_baseline_config,
    )
    from lumenis.shared.evidence import store
    from lumenis.shared.reporting.saved_work import _stage_bytes, staging_write
    policy = authorization.post_intake_policy
    if not policy:
        raise ValueError("POST_INTAKE_POLICY_REVOKED_OR_MISSING")
    source_ref = original.get("source_evidence_ref")
    if not isinstance(source_ref, str) or not re.fullmatch(r"app_evidence_records:[1-9][0-9]*", source_ref):
        raise ValueError("POST_INTAKE_SOURCE_REFERENCE_INVALID")
    row = connection.execute("SELECT * FROM app_evidence_records WHERE id=?",
                             (int(source_ref.split(":")[1]),)).fetchone()
    if row is None:
        raise ValueError("POST_INTAKE_SOURCE_UNAVAILABLE")
    evidence = dict(row)
    source_metadata = json.loads(evidence.get("collection_metadata") or "{}")
    binding = source_metadata.get("native_source_binding") or {}
    processing_version = POST_INTAKE_KEYWORD_POLICY["processing_version"]
    use_binding = {
        "source_evidence_ref": source_ref,
        "source_fingerprint": original.get("source_fingerprint"),
        "source_version": original.get("source_evidence_version"),
        "body_sha256": binding.get("body_sha256"),
        "processing_version": processing_version, "scope": scope,
    }
    gate = get_permission_gate()
    use_receipts = {}

    def admit(action):
        decision = gate.check_prelaunch_post_intake(
            authorization, action=action, connection=connection, **use_binding)
        if not decision.allowed or not decision.audit_id:
            raise ValueError(decision.reason)
        use_receipts[action] = decision.to_dict()
        return decision

    admit("READ")
    raw, source_artifact = _source_bytes(connection, {**evidence, "provenance": source_metadata})
    source = json.loads(raw)
    pending_source = evidence["version"] == "collected-native-source:pending-v1"
    canonical_ref = None
    if not pending_source:
        canonical_rows = connection.execute(
            "SELECT canonical_id FROM canonical_data WHERE source_table='notes' AND source_id=? "
            "AND domain_id=? AND NULLIF(subject_id,'') IS ? AND NULLIF(brand_focus_id,'') IS ?",
            (str(evidence["asset_id"]), context["domain_id"], scope["subject_id"], scope["brand_focus_id"])).fetchall()
        if len(canonical_rows) != 1:
            raise ValueError("POST_INTAKE_CANONICAL_SOURCE_UNAVAILABLE")
        canonical_ref = canonical_rows[0]["canonical_id"]
    current = load_prelaunch_baseline_config(os.environ.get("LUMENIS_PRELAUNCH_BASELINE_CONFIG") or None)
    plans = [plan for plan in current.get("plans", []) if authorization.matches(
        plan, source_url=authorization.source_url, platform=authorization.platform, scope=scope)]
    if len(plans) != 1:
        raise ValueError("POST_INTAKE_POLICY_REVOKED_OR_MISSING")
    extraction_context = _post_intake_extraction_context(plans[0])
    source_inputs = {
        **use_binding, "source_artifact_ref": source_artifact["artifact_id"],
        "canonical_ref": canonical_ref, "plan_id": authorization.plan_id,
        "policy": policy, "source_rights": source["rights"],
        "extraction_context": extraction_context,
    }
    if pending_source:
        source_inputs["entity_assignment"] = source["entity_assignment"]
    derivation_id = hashlib.sha256(json.dumps(
        source_inputs, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    admit("ANALYZE")
    saved = connection.execute(
        "SELECT * FROM app_evidence_records WHERE source='collector' AND feature_id=? "
        "AND asset_id=? AND version=? ORDER BY id DESC",
        ("COLLECTED_KEYWORD_CANDIDATES", derivation_id, processing_version)).fetchone()
    if saved is not None:
        prior = dict(saved)
        prior_raw, artifact = _keyword_candidate_bytes(connection, prior)
        payload = json.loads(prior_raw)
        if payload.get("source_inputs") != source_inputs:
            raise ValueError("POST_INTAKE_DERIVATIVE_REPLAY_CONFLICT")
        admit("DERIVED_SAVE")
        use_evidence_ref = _persist_internal_source_use_receipts(
            connection, source_inputs=source_inputs, receipts=use_receipts, context=context)
        binding_state = "UNASSIGNED_SOURCE_ONLY" if pending_source else _bind_keyword_candidate_ref(
            connection, canonical_ref=canonical_ref, source_ref=source_ref,
            keyword_ref="app_evidence_records:" + str(prior["id"]),
            keyword_artifact_ref=artifact["artifact_id"], processing_version=processing_version)
        return {"status": "SAVED", "replayed": True, "keyword_artifact_ref": artifact["artifact_id"],
                "keyword_evidence_ref": "app_evidence_records:" + str(prior["id"]),
                "processing_version": processing_version, "derivative_sha256": artifact["sha256"],
                "candidate_count": len(payload["candidates"]), "owned_inference": "NOT_RUN",
                "admitted": False, "automatic_adoption": False, "current_use_receipts": use_receipts,
                "current_use_evidence_ref": use_evidence_ref, "canonical_binding": binding_state}
    candidates = extract_source_keyword_candidates(
        source["body"], context_keywords=extraction_context["entity_aliases"])
    publication = source.get("publication") or {}
    query = authorization.source_url
    observation = {
        "platform": source["platform"], "platform_content_id": source["native_id"],
        "source_url": source["source_url"],
        "native_publication": publication.get("published_at_utc"),
        "capture_observation_utc": source["capture_observation_native"],
        "native_raw_ref": {"path": source_artifact["artifact_id"],
                           "sha256": original["source_fingerprint"]},
        "source_body": source["body"], "body_sha256": source["body_sha256"],
        "derived_topics": candidates, "rights": source["rights"], "planned_task": query,
        "formal_refs": {"source_evidence_ref": source_ref,
                        "source_artifact_ref": source_artifact["artifact_id"],
                        "source_evidence_version": evidence["version"], "canonical_ref": canonical_ref,
                        "read_audit_ref": use_receipts["READ"]["audit_id"],
                        "analyze_audit_ref": use_receipts["ANALYZE"]["audit_id"]},
    }
    query_context = (plans[0].purpose_query or {}).get("business_context") or {}
    # The task period is already checked on Source admission. Preserve native
    # time again in the catalog; capture time never supplies a missing year.
    catalog = build_observed_topic_catalog(
        [observation], candidate_origin="DERIVED_SOURCE_BODY",
        publication_since=query_context.get("publication_since"),
        publication_until=query_context.get("publication_until"))
    write_decision = admit("DERIVED_SAVE")
    use_evidence_ref = _persist_internal_source_use_receipts(
        connection, source_inputs=source_inputs, receipts=use_receipts, context=context)
    for node in catalog["terms"]:
        for source_observation in node["observations"]:
            refs = source_observation.get("source_evidence_canonical_use_refs") or {}
            refs["read_audit_ref"] = use_evidence_ref + ":outputs.permission_receipts.READ"
            refs["analyze_audit_ref"] = use_evidence_ref + ":outputs.permission_receipts.ANALYZE"
            refs["derived_save_audit_ref"] = use_evidence_ref + ":outputs.permission_receipts.DERIVED_SAVE"
            source_observation["source_use_refs"] = dict(refs)
            node["source_use_ref"] = use_evidence_ref
    payload = {
        "version": "collector.post-intake-keyword-candidates.v1",
        "source_inputs": source_inputs, "candidates": candidates, "topic_catalog": catalog,
        "processing_version": processing_version, "purpose": policy["purpose"],
        "use_receipts": use_receipts, "use_evidence_ref": use_evidence_ref, "owned_inference": "NOT_RUN",
        "admitted": False, "automatic_adoption": False,
        "platform_heat": None, "representative_demand": None,
        "source_rights_unchanged": True, "commercial_reporting_authorized": False,
    }
    derivative = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(derivative).hexdigest()
    with staging_write(write_decision.resource):
        artifact, path = _stage_bytes(
            connection, raw=derivative, context=context, kind="collected_keyword_candidates",
            source_execution_id=derivation_id, extension=".json", media_type="application/json")
        staged_paths.append(path)
        metadata = {
            "kind": "DERIVED_SOURCE_KEYWORD_CANDIDATES", "context": dict(context),
            "source_inputs": source_inputs, "use_receipts": use_receipts,
            "use_evidence_ref": use_evidence_ref,
            "keyword_artifact_ref": artifact["artifact_id"], "derivative_sha256": digest,
            "processing_version": processing_version, "owned_inference": "NOT_RUN",
            "native_platform_signature_provided": False, "admitted": False,
        }
        evidence_id = store.record_evidence(
            connection=connection, source="collector", project="LUMENIS",
            product="CTH" if context["domain_id"] == "cth" else "ZBMP",
            feature_id="COLLECTED_KEYWORD_CANDIDATES", asset_id=derivation_id,
            version=processing_version, capture_mode="deterministic_post_intake",
            captured_at=datetime.now().astimezone().isoformat(),
            inputs=source_inputs, outputs={"keyword_artifact_ref": artifact["artifact_id"],
                "candidate_count": len(candidates), "admitted": False},
            raw_content=derivative.decode("utf-8"), collection_metadata=metadata,
            provider="collector-deterministic-keywords", result="PASS",
            actual="INTERNAL_CANDIDATES_SAVED", domain_id=context["domain_id"],
            subject_id=context["subject_id"], brand_focus_id=context["brand_focus_id"], global_scope=False)
        connection.execute("UPDATE lumenis_shared_artifacts SET note_id=?,evidence_id=? WHERE artifact_id=?",
                           (str(evidence["asset_id"]), str(evidence_id), artifact["artifact_id"]))
        saved_evidence = dict(connection.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)).fetchone())
        reopened, artifact = _keyword_candidate_bytes(connection, saved_evidence)
        if reopened != derivative:
            raise ValueError("POST_INTAKE_DERIVATIVE_READBACK_MISMATCH")
        # Revocation/scope/source changes stop this write before its savepoint
        # returns to the Collector's commit boundary.
        admit("DERIVED_SAVE")
        binding_state = "UNASSIGNED_SOURCE_ONLY" if pending_source else _bind_keyword_candidate_ref(
            connection, canonical_ref=canonical_ref, source_ref=source_ref,
            keyword_ref="app_evidence_records:" + str(evidence_id),
            keyword_artifact_ref=artifact["artifact_id"], processing_version=processing_version)
    return {"status": "SAVED", "replayed": False, "keyword_artifact_ref": artifact["artifact_id"],
            "keyword_evidence_ref": "app_evidence_records:" + str(evidence_id),
            "processing_version": processing_version, "derivative_sha256": digest,
            "candidate_count": len(candidates), "owned_inference": "NOT_RUN",
            "admitted": False, "automatic_adoption": False, "current_use_receipts": use_receipts,
            "current_use_evidence_ref": use_evidence_ref, "canonical_binding": binding_state}


def _post_intake_extraction_context(plan):
    """Freeze actual signed Registry aliases as processing inputs, not output."""
    context = (plan.purpose_query or {}).get("business_context") or {}
    aliases = context.get("entity_aliases") or []
    return {"version": "signed-registry-alias-context:v1",
            "entity_aliases": list(dict.fromkeys(alias for alias in aliases
                                                  if isinstance(alias, str) and alias.strip()))}


def _bind_keyword_candidate_ref(connection, *, canonical_ref, source_ref, keyword_ref,
                                keyword_artifact_ref, processing_version):
    """Link a current Source's derivative without changing any factual field."""
    from dataclasses import fields
    from canonical_data import CanonicalRecord, persist_canonical
    row = connection.execute("SELECT * FROM canonical_data WHERE canonical_id=?",
                             (canonical_ref,)).fetchone()
    if row is None:
        raise ValueError("POST_INTAKE_CANONICAL_SOURCE_UNAVAILABLE")
    row = dict(row)
    raw_ref = json.loads(row.get("raw_ref") or "{}")
    if raw_ref.get("content_evidence_ref") != source_ref:
        return "HISTORICAL_SOURCE_VERSION_ONLY"
    raw_ref["keyword_candidates"] = {
        "source_evidence_ref": source_ref, "keyword_evidence_ref": keyword_ref,
        "keyword_artifact_ref": keyword_artifact_ref, "processing_version": processing_version,
        "admitted": False, "automatic_adoption": False,
    }
    record = CanonicalRecord(**{item.name: row[item.name] for item in fields(CanonicalRecord)
                                if item.name in row})
    record.raw_ref = json.dumps(raw_ref, ensure_ascii=False, sort_keys=True)
    persist_canonical(connection, record)
    return "CURRENT_SOURCE_LINKED"


def _persist_internal_source_use_receipts(connection, *, source_inputs, receipts, context):
    """Persist the actual Permission decisions as writer-authenticated Evidence.

    This is an audit of separately granted internal actions, not source rights,
    an approval issuer or a new Permission store. The caller holds the actual
    DERIVED_SAVE grant and its transaction; failures roll back that derivative.
    """
    from lumenis.shared.evidence import store
    if set(receipts) != {"READ", "ANALYZE", "DERIVED_SAVE"} or any(
            value.get("allowed") is not True or not value.get("audit_id")
            or value.get("caller") != "prelaunch_baseline_maintenance"
            for value in receipts.values()):
        raise ValueError("POST_INTAKE_USE_RECEIPTS_INVALID")
    evidence_id = store.record_evidence(
        connection=connection, source="collector", project="LUMENIS",
        product="CTH" if context["domain_id"] == "cth" else "ZBMP",
        feature_id="COLLECTOR_INTERNAL_SOURCE_USE", asset_id=source_inputs["source_evidence_ref"],
        version="collector-internal-source-use:v1", capture_mode="internal_source_use_audit",
        captured_at=datetime.now().astimezone().isoformat(), inputs=source_inputs,
        outputs={"permission_receipts": receipts},
        raw_content=json.dumps(receipts, ensure_ascii=False, sort_keys=True),
        collection_metadata={"kind": "PERMISSION_ACTION_RECEIPTS", "source_rights_unchanged": True,
                             "native_platform_signature_provided": False},
        provider="system-permission-audit", result="PASS", actual="INTERNAL_USE_GRANTED",
        domain_id=context["domain_id"], subject_id=context["subject_id"],
        brand_focus_id=context["brand_focus_id"], global_scope=False)
    evidence = dict(connection.execute("SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)).fetchone())
    integrity = store.classify_evidence_integrity(evidence)
    if integrity.get("verified") is not True or integrity.get("assurance") != "writer-authenticated":
        raise ValueError("POST_INTAKE_USE_RECEIPT_INTEGRITY_FAILED")
    return "app_evidence_records:" + str(evidence_id)


def _persist_live_post_cover(connection, *, cover, platform, source_id, context,
                             body_original, staged_paths, authorization_resource):
    """Preserve one cover in the existing Artifact/Evidence owners, without decoding."""
    from lumenis.shared.reporting.saved_work import _stage_bytes, staging_write
    from lumenis.shared.evidence import store
    raw = cover.get("raw_bytes")
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= 2 * 1024 * 1024
            or len(raw) != cover.get("size_bytes")
            or hashlib.sha256(raw).hexdigest() != cover.get("sha256")):
        raise ValueError("COLLECTED_COVER_BYTES_INVALID")
    metadata = {key: val for key, val in cover.items() if key != "raw_bytes"}
    metadata.update(context=dict(context), source_kind="collected_post_cover",
                    native_id=str(source_id), platform=platform,
                    parent_body_evidence_ref=body_original["source_evidence_ref"],
                    rights=body_original["rights"], processing="ORIGINAL_BYTES_ONLY",
                    source_signature_state="NATIVE_SIGNATURE_NOT_PROVIDED")
    entity_assignment = body_original.get("entity_assignment")
    if entity_assignment is not None:
        if not isinstance(entity_assignment, dict):
            raise ValueError("COLLECTED_COVER_ENTITY_ASSIGNMENT_INVALID")
        metadata["entity_assignment"] = entity_assignment
    with staging_write(authorization_resource + ":" + str(source_id) + ":" + cover["sha256"]):
        artifact, path = _stage_bytes(
            connection, raw=raw, context=context, kind="collected_post_cover",
            source_execution_id=str(source_id), extension=cover["extension"],
            media_type=cover["content_type"])
        staged_paths.append(path)
        metadata["source_artifact_ref"] = artifact["artifact_id"]
        child_inputs = {"source_ids": [str(source_id)],
                        "body_evidence_ref": body_original["source_evidence_ref"],
                        "source_intake_resource": authorization_resource}
        if entity_assignment is not None:
            child_inputs["entity_assignment"] = entity_assignment
        evidence_id = store.record_evidence(
            connection=connection, source="collector", project="LUMENIS",
            product="CTH" if context["domain_id"] == "cth" else "ZBMP",
            feature_id="COLLECTED_POST_COVER", asset_id=str(source_id), version="collected-post-cover:v1",
            capture_mode="live_native_cover_intake", captured_at=cover["captured_at"],
            inputs=child_inputs,
            outputs={"source_artifact_ref": artifact["artifact_id"],
                     "cover_sha256": cover["sha256"], "cover_size_bytes": len(raw)},
            raw_content=json.dumps({"sha256": cover["sha256"], "size_bytes": len(raw)}, sort_keys=True),
            collection_metadata=metadata, provider="collector-native-cover",
            domain_id=context["domain_id"], subject_id=context["subject_id"],
            brand_focus_id=context["brand_focus_id"], global_scope=False)
        connection.execute("UPDATE lumenis_shared_artifacts SET note_id=?,evidence_id=? WHERE artifact_id=?",
                           (str(source_id), str(evidence_id), artifact["artifact_id"]))
        evidence = dict(connection.execute("SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)).fetchone())
        if store.classify_evidence_integrity(evidence).get("verified") is not True:
            raise ValueError("COLLECTED_COVER_INTEGRITY_FAILED")
        stored = path.read_bytes()
        if stored != raw or hashlib.sha256(stored).hexdigest() != cover["sha256"]:
            raise ValueError("COLLECTED_COVER_READBACK_FAILED")
    return {"status": "SAVED", "reason": None,
            "media_asset_refs": [{"artifact_ref": artifact["artifact_id"],
                "evidence_ref": "app_evidence_records:" + str(evidence_id),
                "evidence_version": "collected-post-cover:v1", "sha256": cover["sha256"],
                "size_bytes": len(raw), "native_locator": cover["native_locator"],
                "captured_at": cover["captured_at"], "rights": body_original["rights"]}],
            "other_images_processed": False, "image_ocr": False, "video_processing": False}


def _bind_native_source_original(connection, source_id, context, original):
    """Add an explicit body reference without treating scope proof as content."""
    from dataclasses import fields
    from canonical_data import CanonicalRecord, persist_canonical

    product = "CTH" if context["domain_id"] == "cth" else "ZBMP"
    rows = connection.execute(
        "SELECT * FROM canonical_data WHERE source_table='notes' AND source_id=? AND product_id=?",
        (str(source_id), product)).fetchall()
    if len(rows) != 1:
        raise ValueError("COLLECTED_SOURCE_CANONICAL_BINDING_INVALID")
    row = dict(rows[0])
    if (row.get("domain_id") != context["domain_id"]
            or (row.get("subject_id") or None) != context["subject_id"]
            or (row.get("brand_focus_id") or None) != context["brand_focus_id"]):
        raise ValueError("COLLECTED_SOURCE_CANONICAL_BINDING_INVALID")
    raw_ref = json.loads(row.get("raw_ref") or "{}")
    if not isinstance(raw_ref, dict):
        raise ValueError("COLLECTED_SOURCE_CANONICAL_REFERENCE_INVALID")
    raw_ref["content_evidence_ref"] = original["source_evidence_ref"]
    if "cover" in original:
        raw_ref["cover_original"] = original["cover"]
    if "media_understanding" in original:
        raw_ref["media_understanding"] = original["media_understanding"]
    record = CanonicalRecord(**{field.name: row[field.name] for field in fields(CanonicalRecord)
                                if field.name in row})
    record.raw_ref = json.dumps(raw_ref, ensure_ascii=False, sort_keys=True)
    persist_canonical(connection, record)

def _native_capture_collection(capture):
    value = _native_capture_record(capture)
    native = value["native_record"]
    platform = capture.platform
    raw = dict(native)
    publication = value.get("publication") or {}
    metrics = {}
    author_id = None
    author_name = None
    if platform == "douyin":
        observed = (value.get("additional") or {}).get("metric_observations") or []
        matched = [m for m in observed if m.get("captured_at") == value["capture_observation_native"]]
        stats = matched[-1]["native"] if matched else native.get("statistics") or {}
        raw.update({key: stats.get(key) for key in ("digg_count","comment_count","collect_count","share_count","play_count")})
        metrics = {"likes":raw.get("digg_count"),"comments":raw.get("comment_count"),
                   "collects":raw.get("collect_count"),"shares":raw.get("share_count"),"views":raw.get("play_count")}
        author = native.get("author") or {}
        author_id, author_name = author.get("sec_uid") or author.get("uid"), author.get("nickname")
    elif platform == "x":
        observed = native.get("metrics_observed") or {}
        for key in ("favorite_count","reply_count","retweet_count","bookmark_count","view_count"):
            raw[key] = (observed.get(key) or {}).get("value")
        metrics = {"likes":raw.get("favorite_count"),"comments":raw.get("reply_count"),
                   "shares":raw.get("retweet_count"),"collects":None,"views":raw.get("view_count")}
        author_id = native.get("author_numeric_id")
        author_name = native.get("screen_name")
        raw["repost_native_metric_name"] = "retweet_count"
        raw["bookmark_native_metric_name"] = "bookmark_count"
    elif platform == "instagram":
        metrics = {"likes":native.get("like_count"),"comments":native.get("comment_count"),
                   "collects":None,"shares":native.get("share_count"),"views":native.get("play_count")}
        author_id = native.get("author_id")
        author_name = (native.get("author") or {}).get("username")
    elif platform == "xiaohongshu":
        raw.update(note_id=value["native_id"], user_id=native.get("author_id"),
                   liked_count=native.get("likes"), comment_count=native.get("comments"),
                   collected_count=native.get("collects"), share_count=native.get("shares"))
        metrics = {"likes":native.get("likes"),"comments":native.get("comments"),
                   "collects":native.get("collects"),"shares":native.get("shares"),"views":None}
        author_id, author_name = native.get("author_id"), native.get("author_nickname")
    else:
        metrics = {"likes":None,"comments":None,"collects":None,"shares":None,"views":None}
        author_id, author_name = native.get("author_id"), native.get("account_display")
    for metric in metrics.values():
        if metric is not None and (type(metric) is not int or metric < 0):
            raise ValueError("native metrics must be exact nonnegative integers or NULL")
    raw["_native_original"] = {
        "source_sha256": capture.sha256, "body_sha256":value["body_sha256"],
        "source_lineage": value["source_lineage"], "original_capture_time":value["capture_observation_native"],
        "body_state":value["body_state"], "publication_since_2026":value.get("publication_since_2026"),
        "claim_type":value.get("claim_type"),"rights":value.get("rights"),
    }
    item = {"platform_content_id":value["native_id"],"url":value["source_url"],
            "title":native.get("title"),"content":value["body"],
            "publish_datetime":publication.get("published_at_utc"),
            "author_id":author_id,"author_nickname":author_name,"raw":raw,**metrics}
    return CollectionResult(CollectionStatus.SUCCESS, platform, items=[item], raw_count=1,
        metadata={"provider":"frozen_public_native_observation","source_version":capture.sha256,
                  "source":"platform:"+platform,"collected_at":value["capture_observation_native"],
                  "original_body_available":True,"native_capture_sha256":capture.sha256,
                  "source_native_time_unknown":publication.get("published_at_utc") is None})


# Browser snapshots are a distinct producer under the existing Collector owner.
# They never impersonate native originals or an uploaded document.
def _browser_source_request(*, actor, scope, request_id, capture_id, rights, intended_use, rights_statement):
    from lumenis.shared.reporting.saved_work import authorize, SavedWorkError, _digest
    if (not isinstance(request_id, str) or re.fullmatch(r'[A-Za-z0-9_-]{8,128}', request_id) is None
            or not isinstance(capture_id, str) or re.fullmatch(r'cap_[a-f0-9]{32}', capture_id) is None
            or rights not in ('public-reference-only', 'owner-approved')
            or intended_use not in ('research_reference', 'report_quote', 'internal_draft')
            or (rights == 'public-reference-only' and intended_use == 'internal_draft')
            or not isinstance(rights_statement, str) or not 0 < len(rights_statement) <= 2000):
        raise SavedWorkError('BROWSER_SOURCE_ADMISSION_INVALID')
    context = authorize(actor, scope, action='write')
    request = dict(context=context, request_id=request_id, capture_id=capture_id,
                   rights=rights, intended_use=intended_use, rights_statement=rights_statement)
    source_id = 'browser_' + _digest({'context': context, 'request_id': request_id})
    return context, request, source_id


def _browser_import_admitted(actor, scope, resource, *, connection=None):
    from lumenis.shared.reporting.saved_work import authorize, SavedWorkError
    from lumenis.system.security import permission
    context = authorize(actor, scope, action='write', connection=connection)
    if permission.is_testing_bypass_enabled():
        raise SavedWorkError('WORK_PERMISSION_UNVERIFIED')
    caller = context.get('principal_ref') or f"actor:{context['actor_id']}"
    result = permission.get_permission_gate().check(permission.OperationType.DATA_IMPORT,
        resource=resource, caller=caller, domain_id=context['domain_id'], exact_approval_required=True)
    if not result.allowed:
        raise SavedWorkError('BROWSER_SOURCE_IMPORT_APPROVAL_REQUIRED')
    return context


def _browser_source_existing(con, source_id, request):
    from lumenis.shared.reporting.saved_work import SavedWorkError
    from lumenis.importer.documents import _source_bytes
    from lumenis.shared.evidence import store
    row = con.execute("SELECT * FROM app_evidence_records WHERE source='collector' AND "
        "feature_id='COLLECTED_SOURCE' AND asset_id=? AND version='collected-browser-snapshot:v1'",
        (source_id,)).fetchone()
    if row is None:
        return None
    evidence = dict(row)
    metadata = json.loads(evidence['collection_metadata'])
    if metadata.get('browser_admission_request') != request:
        raise SavedWorkError('BROWSER_SOURCE_REQUEST_CONFLICT')
    integrity = store.classify_evidence_integrity(evidence)
    if integrity.get('verified') is not True or integrity.get('assurance') != 'writer-authenticated':
        raise SavedWorkError('BROWSER_SOURCE_INTEGRITY_FAILED')
    _source_bytes(con, {**evidence, 'provenance': metadata})
    return evidence, metadata


def _browser_source_result(evidence, metadata, *, replayed):
    return {'ok': True, 'source_id': evidence['asset_id'], 'evidence_id': evidence['id'],
        'source_evidence_ref': 'app_evidence_records:' + str(evidence['id']),
        'source_artifact_ref': metadata['source_artifact_ref'], 'source_version': evidence['version'],
        'snapshot_sha256': metadata['source_fingerprint'],
        'body_sha256': metadata['browser_snapshot_binding']['body_sha256'],
        'source_capture': 'SANITIZED_SNAPSHOT_RETAINED', 'source_use': 'NOT_ADMITTED',
        'fact_verification': 'NOT_VERIFIED', 'original_resource_sha256': None,
        'canonical_ref': None, 'replayed': replayed}


def admit_browser_snapshot(session, *, actor, scope, request_id, capture_id, rights,
                           intended_use, rights_statement, prepare=False):
    """Explicit server-bound snapshot admission; no network or automatic grants."""
    from lumenis.shared.reporting.saved_work import SavedWorkError, _digest, _stage_bytes, staging_write
    from lumenis.shared.database import get_repository
    from lumenis.shared.evidence import store
    from lumenis.importer.documents import _source_bytes, source_boundaries
    from lumenis.system.collector.runtime.browser_extract import (
        snapshot_bytes, validate_source_snapshot, BROWSER_SOURCE_VERSION)
    context, request, source_id = _browser_source_request(actor=actor, scope=scope,
        request_id=request_id, capture_id=capture_id, rights=rights, intended_use=intended_use,
        rights_statement=rights_statement)
    # Bind the authenticated API actor to the owned browser session again at the service seam.
    expected_actor = context.get('actor_id')
    expected_principal = context.get('principal_ref')
    if (session.owner_actor_id != expected_actor or session.owner_principal_ref != expected_principal
            or (expected_actor is not None and session.owner_account_session_id != actor.get('session_id'))):
        raise SavedWorkError('BROWSER_SOURCE_OWNER_MISMATCH')
    repo = get_repository()
    with repo.connection() as con:
        old = _browser_source_existing(con, source_id, request)
    if old:
        resource = old[1]['source_intake_resource']
        if prepare:
            return {'ok': True, 'state': 'APPROVAL_REQUIRED', 'operation': 'data_import', 'resource': resource}
        _browser_import_admitted(actor, scope, resource)
        return _browser_source_result(*old, replayed=True)
    snapshot = validate_source_snapshot(session.snapshot_for_source(capture_id))
    binding = snapshot['binding']
    rows = session.evidence_store.query(session_id=session.session_id, action='extract', limit=1000)
    receipt = next((row for row in rows if row['id'] == binding['browser_evidence_id']), None)
    if (receipt is None or receipt.get('after_state_hash') != binding['capture_sha256']
            or receipt.get('result') not in ('PASS', 'PARTIAL')
            or json.loads(receipt.get('verification') or '{}').get('operation_id') != binding['operation_id']):
        raise SavedWorkError('BROWSER_SOURCE_CAPTURE_RECEIPT_INVALID')
    raw = snapshot_bytes(snapshot)
    fingerprint = hashlib.sha256(raw).hexdigest()
    resource = 'browser-snapshot-import:v1:' + _digest({**request, 'snapshot_sha256': fingerprint})
    if prepare:
        return {'ok': True, 'state': 'APPROVAL_REQUIRED', 'operation': 'data_import', 'resource': resource,
                'snapshot_sha256': fingerprint, 'original_resource_sha256': None}
    _browser_import_admitted(actor, scope, resource)
    paths = []
    committed = False
    commit_attempted = False
    try:
        with repo.transaction() as con:
            con.execute('BEGIN IMMEDIATE')
            _browser_import_admitted(actor, scope, resource, connection=con)
            old = _browser_source_existing(con, source_id, request)
            if old:
                if old[1]['source_fingerprint'] != fingerprint:
                    raise SavedWorkError('BROWSER_SOURCE_REQUEST_CONFLICT')
                return _browser_source_result(*old, replayed=True)
            provenance = {'source_url': snapshot['metadata']['url'], 'title': snapshot['metadata']['title'],
                'captured_at': snapshot['metadata']['captured_at'], 'published_at': None,
                'rights': rights, 'intended_use': intended_use, 'rights_statement': rights_statement,
                'content_origin': {'kind': 'publisher-material', 'claim_type': 'source_statement'}}
            owner = {k:v for k,v in context.items() if k not in ('domain_id','subject_id','brand_focus_id','global_scope')}
            parent_metadata = {'context': context, 'owner': owner, 'browser_admission_request': request,
                'source_intake_resource': resource, 'snapshot_sha256': fingerprint,
                'browser_snapshot_binding': {**binding, 'snapshot_sha256': fingerprint}}
            with staging_write(resource):
                parent_id = store.record_evidence(connection=con, source='collector', product='CTH' if context['domain_id']=='cth' else 'ZBMP',
                    feature_id='BROWSER_SNAPSHOT_ADMISSION', asset_id=source_id, version='browser-snapshot-admission:v1',
                    provider='collector-browser-snapshot', capture_mode='sanitized_browser_snapshot',
                    captured_at=provenance['captured_at'], raw_content=snapshot['body'],
                    inputs={'source_intake_resource': resource}, outputs={'snapshot_sha256': fingerprint},
                    collection_metadata=parent_metadata, domain_id=context['domain_id'],
                    subject_id=context['subject_id'], brand_focus_id=context['brand_focus_id'], global_scope=context['global_scope'])
                artifact, path = _stage_bytes(con, raw=raw, context=context, kind='collected_source',
                    source_execution_id=source_id, extension='.json', media_type='application/json')
                paths.append(path)
                metadata = {**parent_metadata, 'source_kind': 'collected_source', 'provenance': provenance,
                    'source_url': provenance['source_url'], 'source_fingerprint': fingerprint,
                    'parsed_text': snapshot['body'], 'locators': snapshot['block_map'],
                    'capture_mode': 'sanitized_browser_snapshot', 'original_resource_sha256': None,
                    'source_artifact_ref': artifact['artifact_id'],
                    'collection_evidence_ref': 'app_evidence_records:'+str(parent_id),
                    **source_boundaries(provenance)}
                evidence_id = store.record_evidence(connection=con, source='collector', product='CTH' if context['domain_id']=='cth' else 'ZBMP',
                    feature_id='COLLECTED_SOURCE', asset_id=source_id, version=BROWSER_SOURCE_VERSION,
                    provider='collector-browser-snapshot', capture_mode='sanitized_browser_snapshot',
                    captured_at=provenance['captured_at'], raw_content=snapshot['body'],
                    inputs={'source_ids':[source_id], 'source_intake_resource':resource,
                            'collection_evidence_ref':metadata['collection_evidence_ref']},
                    outputs={'source_artifact_ref':artifact['artifact_id'], 'snapshot_sha256':fingerprint},
                    collection_metadata=metadata, domain_id=context['domain_id'], subject_id=context['subject_id'],
                    brand_focus_id=context['brand_focus_id'], global_scope=context['global_scope'])
                con.execute('UPDATE lumenis_shared_artifacts SET note_id=?,evidence_id=? WHERE artifact_id=?',
                    (source_id, str(evidence_id), artifact['artifact_id']))
                evidence = dict(con.execute('SELECT * FROM app_evidence_records WHERE id=?',(evidence_id,)).fetchone())
                _source_bytes(con, {**evidence, 'provenance': metadata})
                _browser_import_admitted(actor, scope, resource, connection=con)
                commit_attempted = True
                con.commit()
                committed = True
                return _browser_source_result(evidence, metadata, replayed=False)
    except Exception:
        if commit_attempted and not committed:
            # A failed commit acknowledgement is not proof of rollback. Keep
            # possibly committed bytes; replay resolves the durable request.
            from lumenis.system.collector.runtime.browser_extract import BrowserExtractionError
            raise BrowserExtractionError('BROWSER_SOURCE_COMMIT_UNKNOWN',
                source_id=source_id, request_id=request_id, retry_safe=False,
                recovery='REPLAY_SAME_SOURCE_IMPORT_REQUEST') from None
        raise
    finally:
        if not committed and not commit_attempted:
            for path in paths:
                path.unlink(missing_ok=True)
