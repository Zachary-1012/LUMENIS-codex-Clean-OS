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

from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
import ipaddress

import threading
import time
import sys
import hashlib
import json
import os
import getpass
import logging
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .config import PLATFORM_CAPABILITIES
from .registry import get_adapter
from .routing import RouteIdentityMismatch, bind_collection_route, normalize_provider_selection
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
logger = logging.getLogger(__name__)
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
        "SUCCESS": "已取得并保存资料",
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
        "PUBLICATION_TIME_REVIEW_REQUIRED": "部分内容缺少可核实的原生发布时间，未纳入本次时间范围结果",
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
                "network_attempted", "authorization_verification",
                "provider_mode", "public_transport",
            )
            if key in metadata
        }
        configuration_only = (
            metadata.get('healthcheck_scope') in {'configuration_only', 'public_endpoint_configuration'}
            or metadata.get('network_attempted') is False
            or metadata.get('authorization_verification') == 'NOT_VERIFIED'
        )
        return {
            "status": status,
            "ready": status == "SUCCESS" and not configuration_only,
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


def _platform_capability_states(platform, capability):
    names = ('search','detail','comments','author','author_posts')
    try:
        implementation = type(_get_runtime_adapter(platform))
    except Exception:
        return {name:'PROVIDER_UNAVAILABLE' if capability.get('creator' if name=='author' else name)
                else 'NOT_IMPLEMENTED' for name in names}
    states = {}
    for name in names:
        method = 'creator' if name == 'author' else name
        states[name] = ('IMPLEMENTED' if capability.get(method) is True
            and capability.get('implementation_state') != 'PLANNED'
            and callable(getattr(implementation,method,None))
            and getattr(implementation,method,None) is not getattr(BasePlatformAdapter,method,None)
            else 'NOT_IMPLEMENTED')
    return states


def get_collection_surface() -> Dict[str, Any]:
    """Return the SYSTEM collection capability map for its existing consumers.

    This is a local health/read-only call.  It does not start a browser or make
    an external request.
    """
    platforms: List[Dict[str, Any]] = []
    for platform in _COLLECTION_SURFACE_PLATFORMS:
        cap = PLATFORM_CAPABILITIES["xhs" if platform == "xiaohongshu" else platform]
        health = _adapter_health(platform)
        last_run = _last_run(platform)
        metadata = health.get("metadata") or {}
        health_scope = metadata.get("healthcheck_scope")
        last_run_state = (str(last_run.get("state") or "").upper()
                          if isinstance(last_run, dict) else "")
        last_run_failed = bool(last_run_state and last_run_state not in {
            "SUCCESS", "NO_NEW_DATA", "UNKNOWN",
        })
        display_status = ("CONFIGURED" if health["status"] == "SUCCESS"
            and (health_scope in {"configuration_only", "public_endpoint_configuration"}
                 or metadata.get("network_attempted") is False
                 or metadata.get("authorization_verification") == "NOT_VERIFIED")
            else ("READY" if health["status"] == "SUCCESS" else health["status"]))
        platforms.append({
            "platform": platform,
            "name": PLATFORM_NAMES[platform],
            "implementation_state": cap["implementation_state"],
            "source_kind": cap["source_kind"],
            "product_owner": "SYSTEM",
            "consumer_views": ["CTH", "BMP"],
            "manual_collection_enabled": bool(cap.get("manual_collection_enabled")),
            "scheduled_collection_enabled": bool(cap.get("enabled")),
            "collection_mode": "human_triggered_read_only",
            'capabilities':_platform_capability_states(platform,cap),
            'provider_modes':list((cap.get('provider_modes') or {}).keys()),
            'public_transports':list(cap.get('public_transports') or []),
            'default_provider_mode':cap.get('default_provider_mode'),
            'default_public_transport':cap.get('default_public_transport'),
            # Local readiness and the last real run are separate facts.  A
            # readable cookie file must not overwrite a verified session
            # failure or collection error in the product surface.
            "status": (last_run_state if last_run_failed else
                       "PLANNED" if cap["implementation_state"] == "PLANNED" else display_status),
            "health": health,
            "last_run": last_run,
            "external_write": False,
            "publish_authority": "human_manual_only",
            "truth_path": "external_data -> evidence -> canonical_data -> authorized consumers",
        })

    primary_runtime = _xhs_primary_runtime_status()
    primary_health = next((row['health'] for row in platforms if row['platform'] == 'xiaohongshu'),
                          {'status': 'UNVERIFIED', 'ready': False, 'can_attempt': False})
    primary_status = str(primary_health.get('status') or 'UNVERIFIED').upper()
    primary_collection = {
        "platform": "xiaohongshu",
        "name": "小红书（香港账号）",
        "region": "hk_international",
        "product_owner": "SYSTEM",
        "consumer_views": ["CTH", "BMP"],
        "implementation": "existing_primary_collector",
        "parallel_collector_added": False,
        "manual_collection_enabled": True,
        "form_selectable": True,
        "entry_label": "搜索、读取原帖与已取得的评论",
        "capabilities": _platform_capability_states('xiaohongshu', PLATFORM_CAPABILITIES['xhs']),
        "status": primary_status,
        "status_source": "registered_adapter_health",
        "health": primary_health,
        "runtime": primary_runtime,
        "last_run": _xhs_primary_last_run(),
        "external_write": False,
        "publish_authority": "human_manual_only",
        "truth_path": "external_data -> evidence -> canonical_data -> CTH/BMP",
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
        "request_limits": {"max_page_items": MAX_RESULTS, "default_page_items": MAX_RESULTS},
    }


def _validate_request(platform: str, keyword: str, max_results: int, *, capability='search') -> tuple[str, str, int]:
    canonical = str(platform or "").strip().lower()
    if canonical not in SECONDARY_COLLECTION_PLATFORMS:
        raise ValueError("当前采集入口不支持该平台；大陆小红书仍按现有区域门禁暂停")
    query = str(keyword or "").strip()
    # Public adapters receive a source URL, not a social search keyword. Keep
    # that URL intact so path/query identity, authorization and provenance agree.
    max_length = 4096 if capability == 'detail' or canonical in {"public_http", "web_rss", "web_atom", "sitemap"} else 256
    if not query or len(query) > max_length:
        raise ValueError(f"keyword/source URL 必须为 1-{max_length} 个字符")
    try:
        limit = int(max_results)
    except (TypeError, ValueError):
        raise ValueError("max_results 必须为整数") from None
    if limit < 1 or limit > MAX_RESULTS:
        raise ValueError(f"max_results 必须在 1-{MAX_RESULTS} 之间")
    return canonical, query, limit


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
    if item.get('cover') is not None:
        record['cover'] = item['cover']
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
        if "play_count" not in record:
            views = item.get("views")
            if views is not None and views != "":
                record["play_count"] = views
    elif platform == "facebook":
        for native_field, item_field in (("reactions", "likes"),
                                         ("comments", "comments"),
                                         ("shares", "shares")):
            if native_field not in record and item_field in item:
                record[native_field] = item[item_field]
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
        kind = raw.get('object_type')
        if kind in {'answer','article','question'}:
            fill_native(kind+'_id', raw.get('id') or content_id)
            if kind != 'answer' and content_id:
                record['content_id'] = f'zhihu:{kind}:{record[kind+"_id"]}'
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
    elif platform in {'naver','daum'}:
        fill_native(spec.content_id,content_id)
        for field in ('likes','comments','collects','shares','views'):
            fill_native(field,item.get(field))
            record.setdefault(field,None)
        if not publish_date:
            record['publish_datetime'] = None
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
        if result.get('discovery_observations'):
            inputs['discovery_observation_records'] = result['discovery_observations']
        if result.get('native_pagination') is not None:
            inputs['native_pagination'] = result['native_pagination']
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


def _source_item_views(connection, records, source_ids, platform, evidence_id, scope):
    """Product source selection uses persisted native identities, never typed IDs."""
    from .platform_naming import to_canonical_record, map_raw_to_normalized
    stored = {str(row['source_id']): dict(row) for row in connection.execute(
        "SELECT canonical_id,source_id,scope_status FROM canonical_data WHERE source_table='notes' "
        'AND product_id=? AND source_id IN (' + ','.join('?' for _ in source_ids) + ')',
        ['CTH' if scope['domain_id'] == 'cth' else 'ZBMP', *source_ids])} if source_ids else {}
    values = []
    for record in records:
        native = to_canonical_record(record, platform)
        normalized = map_raw_to_normalized(record,platform)
        source_id = str(native.get('content_id') or '')
        if source_id not in source_ids:
            continue
        row = stored.get(source_id)
        body = record.get('content') if isinstance(record.get('content'), str) else None
        metrics = {name: normalized.get(key) for name, key in [('likes','like_count'),('comments','comment_count'),
            ('collects','collect_count'),('shares','share_count'),('views','view_count')]}
        media = []
        for value in normalized.get('media_list') or []:
            clue = {'url':value} if isinstance(value,str) else value if isinstance(value,dict) else {}
            url = clue.get('url')
            if isinstance(url,str) and url.startswith('//'):
                url = 'https:'+url
            observed_url = (url if isinstance(url,str) and urlsplit(url).scheme=='https'
                            and _credential_free_observations(url)==url else None)
            if clue:
                media.append({'kind':clue.get('media_type') or clue.get('type'),'url':observed_url,
                    'platform_media_id':str(clue.get('media_id',clue.get('id')))
                        if type(clue.get('media_id',clue.get('id'))) in (str,int) else None,
                    'url_state':'OBSERVED' if observed_url else 'NATIVE_MEDIA_HINT_WITHOUT_USABLE_URL',
                    'original_bytes_state':'NOT_ACQUIRED'})
        for key in ('cover', 'pic', 'thumbnail', 'cover_url'):
            url = record.get(key) or (record.get('source_raw') or {}).get(key)
            if isinstance(url, str) and url:
                if url.startswith('//'):
                    url = 'https:' + url
                safe = _credential_free_observations(url)
                if safe == url and urlsplit(url).scheme == 'https' and url not in [m['url'] for m in media]:
                    media.append({'kind':'cover', 'url':url, 'original_bytes_state':'NOT_ACQUIRED'})
        body_state = ('FEED_OR_INDEX_EXCERPT' if platform in {'web_rss','web_atom','sitemap'} else
                      record.get('body_state') or 'SOURCE_OBSERVED_TEXT')
        values.append({'source_id':source_id, 'platform':platform,
            'canonical_ref':row['canonical_id'] if row else None,
            'state':'CANONICAL_SAVED' if row else 'SOURCE_SAVED_CANONICAL_PENDING',
            'scope_status':row['scope_status'] if row else None,
            'title':record.get('title') or None, 'body_preview':body[:1000] if body else None,
            'body_character_count':len(body) if body is not None else None,
            'url':_credential_free_observations(record.get('url')),
            'author_id':native.get('author_id') or None,
            'author_name':native.get('author_nickname') or record.get('author_nickname') or native.get('author_name') or None,
            'published_at':native.get('published_at') or None, 'captured_at':record.get('captured_at') or None,
            'body_state':body_state,
            'original_body_available':False if body_state in {'FEED_OR_INDEX_EXCERPT','SEARCH_EXCERPT','TRUNCATED_PLATFORM_TEXT','EMPTY'}
                else True if body_state in {'PLATFORM_BODY','NATIVE_LONG_TEXT'} else None,
            'metrics':metrics, 'metric_states':{name:'OBSERVED' if value is not None else 'NOT_REPORTED'
                for name,value in metrics.items()}, 'media':media,
            'evidence_ref':f'app_evidence_records:{evidence_id}', 'rights_state':'CHECK_SOURCE_USE_PER_ACTION'})
    return values


def _current_inspectable_source_rows(connection, source_ids, *, actor, scope):
    """Inspect admitted GLOBAL sources without promoting unassigned business scope."""
    from canonical_data import CanonicalRecord, _validate_canonical_scope
    from lumenis.shared.evidence.store import classify_evidence_integrity
    from .platform_naming import to_canonical_record
    domain = 'bmp' if scope.get('domain_id') == 'zbmp' else scope.get('domain_id')
    stored_domain, product = ('cth','CTH') if domain=='cth' else ('zbmp','ZBMP')
    rows = connection.execute('SELECT * FROM canonical_data WHERE product_id=? AND domain_id=? '
        'AND source_id IN (' + ','.join('?' for _ in source_ids) + ')',
        (product,stored_domain,*source_ids)).fetchall() if source_ids else []
    visible = []
    for raw in rows:
        row = dict(raw)
        actual = {'domain_id':domain,'subject_id':row.get('subject_id') or None,
                  'brand_focus_id':row.get('brand_focus_id') or None,
                  'global_scope':not bool(row.get('subject_id') or row.get('brand_focus_id'))}
        if not scope.get('global_scope') and (actual['subject_id'] != scope.get('subject_id')
                or actual['brand_focus_id'] != scope.get('brand_focus_id')):
            continue
        _business_batch_binding(actor,{domain:actual},'human',None)
        if row['scope_status'] == 'VERIFIED':
            record = CanonicalRecord()
            for key in ('product_id','domain_id','subject_id','brand_focus_id','scope_status','scope_evidence_ref','source_id'):
                setattr(record,key,row.get(key))
            try:
                _validate_canonical_scope(connection,record)
            except (ValueError, RuntimeError):
                continue
        elif row['scope_status'] != 'UNASSIGNED' or not actual['global_scope']:
            continue
        # GLOBAL admission deliberately has no asserted Subject/BrandFocus
        # scope proof. Its signed source observation remains evidence_ref.
        # A focused source still passes its independent scope proof above.
        observation_ref = row.get('evidence_ref') or row.get('scope_evidence_ref')
        parent = connection.execute('SELECT * FROM app_evidence_records WHERE id=?',(observation_ref,)).fetchone()
        evidence = dict(parent) if parent else {}
        inputs = json.loads(evidence.get('inputs_json') or '{}')
        expected = {'domain_id':stored_domain,'product_id':product,'global':actual['global_scope']}
        if actual['subject_id']:
            expected['subject_id'] = actual['subject_id']
        if actual['brand_focus_id']:
            expected['brand_focus_id'] = actual['brand_focus_id']
        if (classify_evidence_integrity(evidence).get('assurance') != 'writer-authenticated'
                or evidence.get('source') != 'collector' or evidence.get('result') != 'PASS'
                or evidence.get('product_id') != product or evidence.get('domain_id') != stored_domain
                or inputs.get('_lumenis_scope') != expected
                or row['source_id'] not in inputs.get('source_ids',[])):
            continue
        if row['source_table'] == 'platform_accounts':
            matching = [item for item in inputs.get('author_observation_records') or []
                if 'platform-author:'+item['platform']+':'+item['platform_author_id'] == row['source_id']]
            correct = len(matching)==1 and (row['title'],row['content'],row['url']) == (
                matching[0].get('display_name') or matching[0].get('username') or '',
                matching[0].get('bio') or '',matching[0].get('profile_url') or '')
        elif row['source_table'] == 'notes':
            matching = [item for item in inputs.get('source_observation_records') or []
                if str(to_canonical_record(item,row['source_platform']).get('content_id') or '') == row['source_id']]
            correct = len(matching)==1 and (row['title'],row['content'],row['url']) == (
                matching[0].get('title') or '',matching[0].get('content') or '',matching[0].get('url') or '')
            source = connection.execute('SELECT title,content,url FROM notes WHERE note_id=?',
                                        (row['source_id'],)).fetchone()
            correct = correct and source is not None and tuple(source) == (row['title'],row['content'],row['url'])
        else:
            correct = False
        if correct:
            visible.append(row)
    return visible


def _publication_review_candidate_views(evidence_ref, evidence, inputs, source_scope, *, selected_source_id=None):
    """Project time-rejected originals separately from admitted Source rows.

    Review rows are joined only when the signed native ID/URL and the preserved
    observation resolve uniquely. Ambiguous or missing joins stay unprojected;
    they are never promoted to Canonical or assigned a guessed date.
    """
    unassigned = inputs.get('unassigned_review_candidates') or []
    if not isinstance(unassigned, list):
        return [], 'UNAVAILABLE', None, None
    try:
        collection_metadata = json.loads(evidence.get('collection_metadata') or '{}')
    except (TypeError, ValueError):
        return [], 'UNAVAILABLE', len(unassigned), None
    if not isinstance(collection_metadata, dict):
        return [], 'UNAVAILABLE', len(unassigned), None
    publication_window = collection_metadata.get('requested_publication_window')
    if publication_window is None:
        return [], 'NOT_REQUESTED' if not unassigned else 'PARTIAL', len(unassigned), None
    if not isinstance(publication_window, dict):
        return [], 'UNAVAILABLE', len(unassigned), None
    reviews = publication_window.get('reviews')
    observations = inputs.get('source_observation_records') or []
    platform = inputs.get('platform')
    if not isinstance(reviews, list) or not isinstance(observations, list) or not isinstance(platform, str):
        return [], 'UNAVAILABLE', len(unassigned), publication_window

    from .platform_naming import to_canonical_record
    unassigned_count = len(unassigned)
    candidate_records = unassigned
    if not candidate_records:
        # Older Evidence receipts kept a rejected original in the signed
        # observation list and the matching time review in collection metadata,
        # but did not populate unassigned_review_candidates. Reconstruct only
        # those review-backed, non-admitted observations; never treat the whole
        # observation list as a pending result.
        source_ids = {str(value) for value in (inputs.get('source_ids') or [])}
        review_entries = []
        review_keys = set()
        for review in reviews:
            if not isinstance(review, dict) or not str(review.get('status') or '').startswith('REVIEW_REQUIRED_'):
                continue
            review_id = review.get('platform_content_id')
            review_id = str(review_id) if review_id not in (None, '') else None
            review_url = review.get('source_url')
            review_url = (_credential_free_observations(review_url)
                          if isinstance(review_url, str) else None)
            if review_id is not None and review_id in source_ids:
                continue
            key = ('id', review_id) if review_id is not None else ('url', review_url)
            if key[1] is not None and key not in review_keys:
                review_keys.add(key)
                review_entries.append((review_id, review_url))
        unassigned_count = len(review_entries)
        candidate_records = []
        for record in observations:
            if not isinstance(record, dict):
                continue
            try:
                record_id = to_canonical_record(record, platform).get('content_id')
            except (TypeError, ValueError):
                record_id = None
            record_id = str(record_id) if record_id not in (None, '') else None
            if record_id is not None and record_id in source_ids:
                continue
            record_url = record.get('url')
            record_url = (_credential_free_observations(record_url)
                          if isinstance(record_url, str) else None)
            if any((review_id is not None and record_id == review_id
                    and (review_url is None or record_url == review_url))
                   or (review_id is None and review_url is not None and record_url == review_url)
                   for review_id, review_url in review_entries):
                candidate_records.append(record)
    indexed_candidates = []
    for candidate in candidate_records:
        if not isinstance(candidate, dict):
            continue
        try:
            canonical_id = to_canonical_record(candidate, platform).get('content_id')
        except (TypeError, ValueError):
            canonical_id = None
        candidate_id = str(canonical_id) if canonical_id not in (None, '') else None
        candidate_url = candidate.get('url')
        candidate_url = _credential_free_observations(candidate_url) if isinstance(candidate_url, str) else None
        positions = [index for index, observation in enumerate(observations)
                     if isinstance(observation, dict) and observation == candidate]
        if len(positions) != 1:
            continue
        indexed_candidates.append((candidate, candidate_id, candidate_url, positions[0]))

    projected = []
    used_positions = set()
    for review in reviews:
        if not isinstance(review, dict) or not str(review.get('status') or '').startswith('REVIEW_REQUIRED_'):
            continue
        review_id = review.get('platform_content_id')
        review_id = str(review_id) if review_id not in (None, '') else None
        review_url = review.get('source_url')
        review_url = _credential_free_observations(review_url) if isinstance(review_url, str) else None
        matches = [entry for entry in indexed_candidates
                   if ((review_id is not None and entry[1] == review_id)
                       or (review_id is None and review_url is not None and entry[2] == review_url))
                   and (review_url is None or entry[2] == review_url)]
        if len(matches) != 1:
            continue
        record, candidate_id, source_url, observation_index = matches[0]
        if observation_index in used_positions:
            continue
        used_positions.add(observation_index)
        body = record.get('content') if isinstance(record.get('content'), str) else None
        status = review.get('status')
        body_state = ('FEED_OR_INDEX_EXCERPT' if platform in {'web_rss', 'web_atom', 'sitemap'}
                      else record.get('body_state') or 'SOURCE_OBSERVED_TEXT')
        candidate = {
            'candidate_id': candidate_id,
            'platform_content_id': candidate_id,
            'platform': platform,
            'review_kind': 'PUBLICATION_TIME',
            'review_status': status,
            'review_reason': review.get('reason'),
            'title': record.get('title') or None,
            'body_preview': body[:1000] if body else None,
            'body_character_count': len(body) if body is not None else None,
            'body_state': body_state,
            'original_body_available': False if body_state in {
                'FEED_OR_INDEX_EXCERPT', 'SEARCH_EXCERPT', 'TRUNCATED_PLATFORM_TEXT', 'EMPTY'}
                else True if body_state in {'PLATFORM_BODY', 'NATIVE_LONG_TEXT'} else None,
            'source_url': source_url,
            'captured_at': record.get('captured_at'),
            'native_publication_literal': review.get('native_publication_literal'),
            'native_publication_normalized': review.get('native_publication_normalized'),
            'publication_time_state': ('UNKNOWN' if status == 'REVIEW_REQUIRED_NATIVE_PUBLICATION_TIME_UNKNOWN'
                                       else 'UNVERIFIED'),
            'within_publication_window': None,
            'publication_since': review.get('publication_since'),
            'publication_until': review.get('publication_until'),
            'source_scope': dict(source_scope),
            'canonical_admission': 'NOT_ADMITTED',
            'evidence_ref': evidence_ref,
            'source_observation_ref': (
                f'{evidence_ref}:inputs.source_observation_records[{observation_index}]'),
            'detail_available': candidate_id is not None and body is not None,
            'rights_state': 'CHECK_SOURCE_USE_PER_ACTION',
        }
        if candidate_id == selected_source_id and body is not None:
            candidate['body'] = body
        projected.append(candidate)

    state = 'COMPLETE' if len(projected) == unassigned_count else 'PARTIAL'
    return projected, state, unassigned_count, publication_window


def read_collected_items(evidence_ref, *, actor, scope, source_id=None):
    """Reopen saved native results through current scope and Canonical proofs."""
    import database as db
    from lumenis.shared.evidence.store import classify_evidence_integrity
    domain = 'bmp' if scope.get('domain_id') == 'zbmp' else scope.get('domain_id')
    _business_batch_binding(actor, {domain: scope}, 'human', None)
    if not isinstance(evidence_ref, str) or re.fullmatch(r'app_evidence_records:[1-9]\d*', evidence_ref) is None:
        raise ValueError('COLLECTION_RESULT_REFERENCE_INVALID')
    with db.get_db() as connection:
        row = connection.execute('SELECT * FROM app_evidence_records WHERE id=?', (int(evidence_ref.split(':')[1]),)).fetchone()
        evidence = dict(row) if row else None
        if (evidence is None or evidence.get('source') != 'collector'
                or classify_evidence_integrity(evidence).get('assurance') != 'writer-authenticated'):
            raise PermissionError('COLLECTION_RESULT_NOT_VERIFIED')
        if evidence.get('feature_id') == 'COLLECTOR_NATIVE_AUTHORS':
            return read_collected_authors(evidence_ref,actor=actor,scope=scope)
        inputs = json.loads(evidence['inputs_json'])
        try:
            collection_metadata = json.loads(evidence.get('collection_metadata') or '{}')
        except (TypeError, ValueError):
            collection_metadata = {}
        collection_metadata = collection_metadata if isinstance(collection_metadata, dict) else {}
        from .public_source import safe_public_source_failure_fields
        public_failure_fields = safe_public_source_failure_fields(collection_metadata)
        limit_validation = collection_metadata.get('result_limit_validation')
        limit_validation = limit_validation if isinstance(limit_validation, dict) else {}
        signed_scope = inputs.get('_lumenis_scope') or {}
        source_domain = 'bmp' if signed_scope.get('domain_id') == 'zbmp' else signed_scope.get('domain_id')
        source_scope = {'domain_id':source_domain, 'global_scope':signed_scope.get('global'),
                        'subject_id':signed_scope.get('subject_id'), 'brand_focus_id':signed_scope.get('brand_focus_id')}
        if (source_domain != domain or type(source_scope['global_scope']) is not bool
                or not scope.get('global_scope') and (
                    source_scope['subject_id'] != scope.get('subject_id')
                    or source_scope['brand_focus_id'] != scope.get('brand_focus_id'))):
            raise PermissionError('COLLECTION_RESULT_SCOPE_CHANGED')
        _business_batch_binding(actor, {domain: source_scope}, 'human', None)
        ids = inputs.get('source_ids') or []
        current_rows = _current_inspectable_source_rows(connection,ids,actor=actor,scope=scope)
        visible = {str(item['source_id']) for item in current_rows}
        if set(map(str, ids)) != visible:
            raise PermissionError('COLLECTION_RESULT_SCOPE_CHANGED')
        observations = inputs.get('source_observation_records') or []
        items = _source_item_views(connection, observations, ids, inputs['platform'], evidence['id'], {'domain_id':domain})
        review_candidates, review_candidates_state, unassigned_count, publication_window = (
            _publication_review_candidate_views(evidence_ref, evidence, inputs, source_scope,
                                                selected_source_id=source_id))
        from .platform_naming import to_canonical_record
        originals = {str(to_canonical_record(value, inputs['platform']).get('content_id') or ''): value
                     for value in observations}
        current_by_id = {str(row['source_id']): row for row in current_rows}
        for item in items:
            current = current_by_id[item['source_id']]
            item['source_version_state'] = ('CURRENT_SOURCE_VERSION' if
                str(current.get('evidence_ref')) == str(evidence['id'])
                else 'RECORDED_SOURCE_VERSION')
        if source_id is not None:
            if not isinstance(source_id, str):
                raise ValueError('COLLECTION_SOURCE_REFERENCE_INVALID')
            if source_id in visible:
                items = [item for item in items if item['source_id'] == source_id]
                review_candidates = []
                review_candidates_state = 'NOT_SELECTED'
                for item in items:
                    original = originals[source_id]
                    item['body'] = original.get('content') if isinstance(original.get('content'), str) else None
            else:
                selected = [item for item in review_candidates if item.get('candidate_id') == source_id]
                if len(selected) != 1:
                    raise ValueError('COLLECTION_SOURCE_REFERENCE_INVALID')
                items = []
                review_candidates = selected
                review_candidates_state = 'SELECTED'
        return {'ok':evidence.get('result') == 'PASS', 'status':evidence.get('actual'),
            'evidence_ref':evidence_ref, 'network_attempted':False,
            'error_type':collection_metadata.get('error_type'),
            **public_failure_fields,
            'requested_result_limit': (limit_validation.get('requested_limit')
                if type(limit_validation.get('requested_limit')) is int else None),
            'provider_returned_count': (limit_validation.get('provider_returned_count')
                if type(limit_validation.get('provider_returned_count')) is int else None),
            'items':items,
            'review_candidates':review_candidates,
            'review_candidates_state':review_candidates_state,
            'unassigned_review_candidate_count':unassigned_count,
            'requested_publication_window':publication_window,
            'scope':source_scope,
            'discovery_observations':inputs.get('discovery_observation_records') or [],
            'native_pagination':inputs.get('native_pagination'), 'result_freshness':'SAVED_SOURCE_RESULT'}


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
        # These are current, scope-admitted observations backed by the Evidence
        # above, not a partial file-import patch. Missing current counters must
        # remain unknown across notes/Canonical/native, never reuse an old value.
        # Keep source timestamps, analysis and the original scope proof intact.
        for observed in accepted:
            current = to_canonical_record(observed, platform=canonical_platform)
            connection.execute(
                "UPDATE notes SET likes=?,comments=?,collects=?,shares=? WHERE note_id=?",
                (current.get("like_count"), current.get("comment_count"),
                 current.get("collect_count"), current.get("share_count"), observed["content_id"]),
            )
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
    scope, platform, keyword, max_results, receipt, *, max_scroll=None, capability="search",
    provider_mode=None, public_transport=None, publication_since=None, publication_until=None,
):
    """Bind approval to the server identity and the exact bounded source request."""
    binding = {
        "module": "collector", "action": "write", "platform": platform,
        "capability": capability, "keyword": keyword, "max_results": max_results,
        "domain_id": scope["domain_id"], "global_scope": scope["global_scope"],
        "subject_id": scope["subject_id"], "brand_focus_id": scope["brand_focus_id"],
        "actor_id": receipt.actor_id, "principal_kind": receipt.principal_kind,
        "principal_ref": receipt.principal_ref,
    }
    if max_scroll is not None:
        binding["max_scroll"] = max_scroll
    if provider_mode is not None:
        binding['provider_mode'] = provider_mode
    if public_transport is not None:
        binding['public_transport'] = public_transport
    if publication_since is not None:
        binding['publication_since'] = publication_since
    if publication_until is not None:
        binding['publication_until'] = publication_until
    encoded = json.dumps(binding, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "collector-source-import:v2:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


_SUBJECT_DIRECTORY_DENIALS = {
    "SUBJECT_DIRECTORY_UNAVAILABLE",
    "SUBJECT_NOT_IN_DIRECTORY",
    "SUBJECT_REMOVED_FROM_DIRECTORY",
    "SUBJECT_CN_OPERATION_NOT_CONFIRMED",
    "SUBJECT_SCOPE_IDENTITY_MISMATCH",
}


def _subject_directory_decision(actor, scope):
    """Resolve one exact Subject/BrandFocus against its actor's current CN set.

    The registry and its Evidence-backed projection remain authoritative; the
    SavedWork preference only records removals. A GLOBAL request without an
    exact entity identity is left as unassigned discovery and is not guessed
    from its keyword.
    """
    if not isinstance(scope, Mapping):
        return {"allowed": False, "status": "SUBJECT_SCOPE_IDENTITY_MISMATCH"}
    domain = str(scope.get("domain_id") or "").strip().lower()
    if domain == "zbmp":
        domain = "bmp"
    if domain not in {"cth", "bmp"}:
        return {"allowed": False, "status": "SUBJECT_SCOPE_IDENTITY_MISMATCH"}
    subject_id = scope.get("subject_id")
    brand_focus_id = scope.get("brand_focus_id")
    if subject_id is None and brand_focus_id is None:
        return {"allowed": True, "status": "UNASSIGNED_DISCOVERY"}
    if (subject_id is not None and (not isinstance(subject_id, str) or not subject_id.strip())
            or brand_focus_id is not None and (not isinstance(brand_focus_id, str) or not brand_focus_id.strip())):
        return {"allowed": False, "status": "SUBJECT_SCOPE_IDENTITY_MISMATCH"}

    try:
        import subject_registry as registry

        domain_name = domain.upper()
        rows = registry.list_subjects(domain_name)
        matches = [row for row in rows
            if (subject_id is None or row.get("subject_id") == subject_id)
            and (brand_focus_id is None or row.get("brand_focus_id") == brand_focus_id)]
        if len(matches) != 1:
            # Separate selectors must resolve to the same single canonical row.
            by_subject = [row for row in rows if row.get("subject_id") == subject_id] if subject_id else []
            by_focus = [row for row in rows if row.get("brand_focus_id") == brand_focus_id] if brand_focus_id else []
            if subject_id and brand_focus_id and by_subject and by_focus and by_subject[0] is not by_focus[0]:
                return {"allowed": False, "status": "SUBJECT_SCOPE_IDENTITY_MISMATCH"}
            return {"allowed": False, "status": "SUBJECT_NOT_IN_DIRECTORY"}
        row = matches[0]
        if row.get("status") not in {"configured", "active"}:
            return {"allowed": False, "status": "SUBJECT_NOT_IN_DIRECTORY"}

        projection = registry._country_subject_projection(domain_name, "CN", "OPERATES_IN")
        evaluated_at = datetime.now().astimezone()
        operations = {
            item["subject_id"]: registry._china_operation_for_subject(
                projection, item["subject_id"], evaluated_at=evaluated_at,
            )
            for item in rows
        }
        working_set = registry._subject_working_set_view(
            domain_name, actor, rows, china_operations=operations,
        )
        if (working_set.get("state") != "READY"
                or not isinstance(working_set.get("subject_ids"), list)):
            return {"allowed": False, "status": "SUBJECT_DIRECTORY_UNAVAILABLE"}
        canonical_id = row["subject_id"]
        if canonical_id in working_set["subject_ids"]:
            return {"allowed": True, "status": "IN_WORKING_SET", "subject_id": canonical_id}
        if canonical_id in working_set.get("removed_subject_ids", []):
            return {"allowed": False, "status": "SUBJECT_REMOVED_FROM_DIRECTORY",
                    "subject_id": canonical_id}
        return {"allowed": False, "status": "SUBJECT_CN_OPERATION_NOT_CONFIRMED",
                "subject_id": canonical_id}
    except Exception:
        logger.exception("Collector subject directory admission unavailable")
        return {"allowed": False, "status": "SUBJECT_DIRECTORY_UNAVAILABLE"}


def _subject_directory_denial_result(decision, *, platform=None, keyword=None):
    status = decision.get("status") or "SUBJECT_DIRECTORY_UNAVAILABLE"
    recovery = {
        "SUBJECT_DIRECTORY_UNAVAILABLE": "RETRY_AFTER_DIRECTORY_READBACK",
        "SUBJECT_NOT_IN_DIRECTORY": "REVIEW_SUBJECT_DIRECTORY",
        "SUBJECT_REMOVED_FROM_DIRECTORY": "ADD_SUBJECT_TO_DIRECTORY",
        "SUBJECT_CN_OPERATION_NOT_CONFIRMED": "REVIEW_CN_OPERATION_EVIDENCE",
        "SUBJECT_SCOPE_IDENTITY_MISMATCH": "RESELECT_SUBJECT",
    }.get(status, "REVIEW_SUBJECT_DIRECTORY")
    return {
        "ok": False, "status": status, "reason_code": status,
        "error_kind": status, "recovery_action": recovery,
        "platform": platform, "keyword": keyword, "read_only": True,
        "external_write": False, "network_attempted": False,
        "persistence_attempted": False,
    }


def _manual_collection_admission(actor, scope, platform, keyword, max_results, *,
                                 max_scroll=None, capability="search",provider_mode=None,public_transport=None,
                                 publication_since=None, publication_until=None,
                                 enforce_subject_directory=True):
    """Resolve current source admission without authorizing an acquisition."""
    from lumenis.system.security import (
        LocalWorkspacePrincipal, check_actor_scope_permission,
        check_local_workspace_scope_permission, get_permission_gate,
        is_testing_bypass_enabled,
    )

    def denied(status, **extra):
        return None, {
            "ok": False, "status": status, "platform": platform, "keyword": keyword,
            "read_only": True, "external_write": False, **extra,
        }

    if capability not in {"search", "detail", "comments", "author", "author_posts", "media"}:
        return denied("NOT_SUPPORTED", network_attempted=False, persistence_attempted=False)
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
        if not gate.fail_closed:
            return denied("PERMISSION_UNAVAILABLE")
        check = (check_local_workspace_scope_permission
                 if type(actor) is LocalWorkspacePrincipal else check_actor_scope_permission)
        receipt = check(actor, module="collector", action="write", gate=gate, **exact)
        if receipt.verification_state != "verified":
            return denied("PERMISSION_UNAVAILABLE")
        if receipt.allowed is not True:
            return denied("SCOPE_UNAUTHORIZED")
        if enforce_subject_directory:
            directory = _subject_directory_decision(actor, exact)
            if directory.get("allowed") is not True:
                return None, _subject_directory_denial_result(
                    directory, platform=platform, keyword=keyword,
                )
        selection = ({} if capability=='media' else normalize_provider_selection(platform,
            provider_mode=provider_mode,public_transport=public_transport))
        resource = _manual_collection_approval_resource(
            exact, platform, keyword, max_results, receipt,
            max_scroll=max_scroll, capability=capability,**selection,
            publication_since=publication_since, publication_until=publication_until,
        )
        return {"scope": exact, "approval_resource": resource,
                "permission_keyword": keyword,
                "provider_selection":selection,
                "caller": (f"account:{receipt.actor_id}" if receipt.actor_id is not None
                           else receipt.principal_ref)}, None
    except Exception:
        return denied("PERMISSION_UNAVAILABLE")


def _manual_collection_guard(actor, scope, platform, keyword, max_results, *,
                             max_scroll=None, capability="search",provider_mode=None,public_transport=None,
                             publication_since=None, publication_until=None,
                             enforce_subject_directory=True):
    """Check live Collector admission and separate import approval; never grant it."""
    from lumenis.system.security import OperationType, get_permission_gate
    admission, denial = _manual_collection_admission(actor, scope, platform, keyword, max_results,
        max_scroll=max_scroll, capability=capability,provider_mode=provider_mode,public_transport=public_transport,
        publication_since=publication_since, publication_until=publication_until,
        enforce_subject_directory=enforce_subject_directory)
    if denial is not None:
        return None, denial
    try:
        exact = admission["scope"]
        approval = get_permission_gate().check(
            OperationType.DATA_IMPORT, admission["approval_resource"], caller=admission["caller"],
            domain_id="zbmp" if exact["domain_id"] == "bmp" else "cth", exact_approval_required=True,
        )
        if approval.allowed is not True:
            return None, {"ok": False,
                "status": "APPROVAL_REQUIRED" if approval.requires_approval else "SCOPE_UNAUTHORIZED",
                "platform": platform, "keyword": keyword, "read_only": True, "external_write": False,
                "approval_resource": admission["approval_resource"]}
        return exact, None
    except Exception:
        return None, {"ok": False, "status": "PERMISSION_UNAVAILABLE", "platform": platform,
                      "keyword": keyword, "read_only": True, "external_write": False}


def _manual_collection_request(*, actor, scope, capability="search", platform=None, keyword=None,
                               content_id=None, source_id=None, max_results=MAX_RESULTS,
                               include_replies=False, author_id=None, source_evidence_ref=None,
                               source_fingerprint=None,provider_mode=None,public_transport=None,
                               publication_since=None, publication_until=None):
    """Use the same source normalization for the preview, confirmation and run."""
    if publication_since is not None or publication_until is not None:
        if capability != "search":
            raise ValueError("PUBLICATION_WINDOW_REQUIRES_SEARCH")
        from ..acquisition_plan import _validate_publication_period
        _validate_publication_period(publication_since, publication_until)
    if capability == 'media':
        from lumenis.shared.reporting.media_brief import prepare_collected_media
        if (platform is not None or keyword is not None or content_id is not None or author_id is not None or include_replies
                or provider_mode is not None or public_transport is not None):
            raise ValueError('MEDIA_REQUIRES_A_SAVED_SOURCE')
        prepared = prepare_collected_media(source_id, actor=actor, scope=scope,
            source_evidence_ref=source_evidence_ref, source_fingerprint=source_fingerprint)
        import database as db
        with db.get_db() as connection:
            parent = _comment_parent(connection, source_id, actor, scope)
        platform, scope, max_results = parent['platform'], parent['scope'], 1
        request = {'capability': 'media', 'platform': platform, 'source_id': source_id,
            'source_evidence_ref': prepared['source_evidence_ref'],
            'source_fingerprint': prepared['source_fingerprint'], 'max_results': 1}
        keyword = json.dumps(request, sort_keys=True, ensure_ascii=False)
    elif source_evidence_ref is not None or source_fingerprint is not None:
        raise ValueError('MEDIA_FIELDS_REQUIRE_MEDIA_CAPABILITY')
    elif capability in {'author','author_posts'}:
        if keyword is not None or content_id is not None or source_id is not None or include_replies is not False:
            raise ValueError('AUTHOR_REQUEST_REQUIRES_AN_EXACT_PROFILE')
        platform = 'xiaohongshu' if platform == 'xhs' else platform
        platform, _, max_results = _validate_request(platform, str(author_id or ''), max_results)
        keyword = _normalize_author_target(platform, author_id)
        if capability == 'author':
            max_results = 1
        request = {'capability':capability,'platform':platform,'author_id':keyword,'max_results':max_results}
    elif capability == "comments":
        if author_id is not None:
            raise ValueError('AUTHOR_FIELDS_REQUIRE_AUTHOR_CAPABILITY')
        import database as db
        if platform is not None or keyword is not None or content_id is not None:
            raise ValueError("Comments require an admitted source")
        if type(include_replies) is not bool or type(max_results) is not int or not 1 <= max_results <= MAX_RESULTS:
            raise ValueError("COMMENT_REQUEST_INVALID")
        with db.get_db() as connection:
            parent = _comment_parent(connection, source_id, actor, scope)
        platform = parent["platform"]
        scope = parent["scope"]
        keyword = json.dumps({"capability": "comments", "source_id": source_id,
            "source_url": parent["source_url"], "include_replies": include_replies},
            sort_keys=True, ensure_ascii=False)
        request = {"capability": capability, "source_id": source_id, "platform": platform,
                   "source_url": parent["source_url"], "max_results": max_results,
                   "include_replies": include_replies}
    else:
        if source_id is not None or include_replies is not False or author_id is not None:
            raise ValueError("Comment fields require comments capability")
        if capability == "detail":
            if keyword is not None:
                raise ValueError("Detail accepts a content_id")
            if platform in {"xhs", "xiaohongshu"}:
                from .xhs import validate_xhs_detail_target
                content_id = validate_xhs_detail_target(content_id)
            keyword, max_results = _credential_free_observations(content_id), 1
        elif capability != "search" or content_id is not None:
            raise ValueError("Invalid collection capability")
        if platform == "xhs":
            platform = "xiaohongshu"
        platform, keyword, max_results = _validate_request(platform, keyword, max_results, capability=capability)
        request = {"capability": capability, "platform": platform,
                   "content_id" if capability == "detail" else "keyword": keyword,
                   "max_results": max_results}
    if publication_since is not None:
        request["publication_since"] = publication_since
    if publication_until is not None:
        request["publication_until"] = publication_until
    selection = ({} if capability=='media' else normalize_provider_selection(platform,
        provider_mode=provider_mode,public_transport=public_transport))
    request.update(selection)
    admission, denial = _manual_collection_admission(actor, scope, platform, keyword, max_results,
        capability=capability,**selection, publication_since=publication_since,
        publication_until=publication_until)
    return admission, denial, request


def prepare_collection_request(*, actor, scope, **request):
    """Prepare an inert read-only review; this never grants or acquires anything."""
    admission, denial, normalized = _manual_collection_request(actor=actor, scope=scope, **request)
    if denial is not None:
        return {**denial, "network_attempted": False, "persistence_attempted": False}
    return {"ok": True, "status": "CONFIRMATION_REQUIRED", "request": normalized,
            "scope": admission["scope"], "approval_resource": admission["approval_resource"],
            "read_only": True, "external_write": False, "network_attempted": False,
            "persistence_attempted": False}


def confirm_collection_request(*, actor, scope, confirmed_resource, confirmed, **request):
    """Confirm the freshly resolved exact request in the canonical approval store."""
    from lumenis.system.security import OperationType, PermissionLevel, get_permission_gate, is_testing_bypass_enabled
    admission, denial, normalized = _manual_collection_request(actor=actor, scope=scope, **request)
    if denial is not None:
        return {**denial, "network_attempted": False, "persistence_attempted": False}
    if (confirmed is not True or not isinstance(confirmed_resource, str)
            or confirmed_resource != admission["approval_resource"]):
        raise PermissionError("COLLECTION_CONFIRMATION_CHANGED")
    gate = get_permission_gate()
    if (is_testing_bypass_enabled() or not gate.fail_closed
            or not gate.has_permission(PermissionLevel.HUMAN_APPROVAL)
            or not gate.has_permission(PermissionLevel.COMMIT)):
        raise PermissionError("COLLECTION_CONFIRMATION_NOT_ALLOWED")
    # The resource includes current server-issued actor, exact scope and source.
    # No client token, claimed actor or approval flag is admitted as authority.
    gate.grant_approval(OperationType.DATA_IMPORT.value, duration_minutes=5,
                        resource=admission["approval_resource"], granted_by=admission["caller"])
    if normalized['capability'] == 'media':
        from lumenis.shared.reporting.media_brief import prepare_collected_media, confirm_collected_media
        media_args = {key: normalized[key] for key in ('source_evidence_ref', 'source_fingerprint')}
        prepared = prepare_collected_media(normalized['source_id'], actor=actor, scope=scope, **media_args)
        confirm_collected_media(normalized['source_id'], actor=actor, scope=scope, **media_args,
            confirmed_resources=[entry['resource'] for entry in prepared['approval_resources']], confirmed=confirmed)
    exact, denial = _manual_collection_guard(actor, admission["scope"], normalized["platform"],
        admission['permission_keyword'], normalized["max_results"],
        capability=normalized["capability"],**admission['provider_selection'],
        publication_since=normalized.get('publication_since'),
        publication_until=normalized.get('publication_until'))
    if denial is not None:
        return {**denial, "network_attempted": False, "persistence_attempted": False}
    return {"ok": True, "status": "READY", "request": normalized, "scope": exact,
            "approval_resource": admission["approval_resource"], "approved": True,
            "expires_in_seconds": 300, "read_only": True, "external_write": False,
            "network_attempted": False, "persistence_attempted": False}


def _manual_task_status(row):
    progress = row['payload'].get('progress') or {}
    if row['payload'].get('cancel_requested') is True:
        return 'CANCELLED'
    result = progress.get('result') or {}
    publication_window = result.get('publication_window') if isinstance(result, dict) else None
    if (isinstance(result, dict)
            and result.get('status') == 'PUBLICATION_TIME_REVIEW_REQUIRED'
            and result.get('error_type') == 'PUBLICATION_TIME_REVIEW_REQUIRED'
            and result.get('evidence_ref')
            and isinstance(publication_window, dict)
            and publication_window.get('state') == 'REVIEW_REQUIRED'
            and type(publication_window.get('review_required_count')) is int
            and publication_window['review_required_count'] > 0):
        # Older durable requests recorded this review outcome as a queue failure.
        # Keep that stored failure receipt intact while projecting the recoverable
        # Evidence-backed review to the caller; reads never resume collection.
        return 'REVIEW_REQUIRED'
    if row['status'] == 'done':
        if (isinstance(publication_window, dict)
                and publication_window.get('state') == 'REVIEW_REQUIRED'):
            return 'REVIEW_REQUIRED'
        # A durable source receipt can legitimately end the queue attempt
        # while its acquisition outcome is explicitly partial or failed. The
        # task projection must preserve that outcome instead of deriving
        # success from the queue's terminal bookkeeping state.
        if isinstance(result, dict) and result.get('ok') is False:
            return 'FAILED'
        return 'COMPLETED'
    if row['status'] == 'failed':
        return 'FAILED'
    if progress.get('waiting_user'):
        return 'WAITING_USER'
    return row['status'].upper()


def _manual_collection_actor_identity(actor):
    """Resolve only the authenticated owner identity for a control-only action."""
    from lumenis.system.security.permission import LocalWorkspacePrincipal
    if type(actor) is LocalWorkspacePrincipal:
        return {'principal_ref': actor.principal_ref}
    if isinstance(actor, dict) and type(actor.get('id')) is int and actor['id'] > 0:
        return {'actor_id': actor['id']}
    raise PermissionError('AUTH_REQUIRED')


def _manual_collection_safe_status(row, *, cancel_applied=False):
    """Return durable queue control state without inspecting saved result data."""
    payload = row.get('payload') if isinstance(row, dict) else None
    payload = payload if isinstance(payload, dict) else {}
    cancel_requested = payload.get('cancel_requested') is True
    queue_status = str(row.get('status') or '').lower()
    status = ('CANCELLED' if cancel_requested else
              'PENDING' if queue_status == 'pending' else
              'RUNNING' if queue_status == 'running' else 'TERMINAL')
    return {'ok': True, 'status': status, 'task_id': row.get('id'),
        'queue_status': queue_status.upper() if queue_status else 'UNKNOWN',
        'cancel_requested': cancel_requested, 'cancel_applied': bool(cancel_applied),
        'result_available': False, 'read_only': True, 'external_write': False,
        'network_attempted': False, 'result_freshness': 'TASK_CONTROL_STATUS_ONLY'}


def list_collection_requests(*, actor, scope, before=None, limit=20):
    from ..guard.task_queue import TaskQueue
    domain = 'bmp' if scope.get('domain_id') == 'zbmp' else scope.get('domain_id')
    binding = _business_batch_binding(actor, {domain: scope}, 'human', None)
    exact = {key: scope.get(key) for key in ('domain_id', 'global_scope', 'subject_id', 'brand_focus_id')}
    exact['domain_id'] = domain
    queue = TaskQueue()
    try:
        rows, next_cursor = queue.list_manual_requests(binding['identity'], exact, before=before, limit=limit)
        return {'ok': True, 'network_attempted': False, 'next_cursor': next_cursor,
            'tasks': [{'task_id': row['id'], 'status': _manual_task_status(row),
                'request': row['payload']['binding']['request'], 'created_at': row['created_at'],
                'continuation_required': (row['payload'].get('progress') or {}).get('continuation_required', False),
                'result_status': (((row['payload'].get('progress') or {}).get('result') or {}).get('source_status')
                    or ((row['payload'].get('progress') or {}).get('result') or {}).get('status'))}
                for row in rows]}
    finally:
        queue.close()


def cancel_subject_collection_requests(*, actor, scope):
    """Stop this actor's exact-subject manual tasks after a directory removal.

    The operational queue is queried by its original actor and exact scope.
    Global/discovery tasks and actorless schedules are deliberately outside this
    helper. Existing completed results and task history are never deleted.
    """
    from ..guard.task_queue import TaskQueue

    if not isinstance(scope, Mapping):
        return {"state": "UNAVAILABLE", "matched": 0, "cancelled": 0,
                "cancellation_pending": 0, "already_terminal": 0, "failed": 1}
    domain = str(scope.get("domain_id") or "").strip().lower()
    if domain == "zbmp":
        domain = "bmp"
    subject_id = scope.get("subject_id")
    brand_focus_id = scope.get("brand_focus_id")
    if (domain not in {"cth", "bmp"} or scope.get("global_scope") is not False
            or subject_id is None and brand_focus_id is None):
        return {"state": "UNAVAILABLE", "matched": 0, "cancelled": 0,
                "cancellation_pending": 0, "already_terminal": 0, "failed": 1}

    try:
        identity = _manual_collection_actor_identity(actor)
        exact = {"domain_id": domain, "global_scope": False,
                 "subject_id": subject_id, "brand_focus_id": brand_focus_id}
        variants = [exact]
        # Older BMP callers may bind only BrandFocus, while newer directory
        # entries retain both registry Subject and BrandFocus identifiers.
        if domain == "bmp" and subject_id is not None and brand_focus_id is not None:
            variants.append({"domain_id": domain, "global_scope": False,
                             "subject_id": None, "brand_focus_id": brand_focus_id})

        queue = TaskQueue()
    except Exception:
        return {"state": "UNAVAILABLE", "matched": 0, "cancelled": 0,
                "cancellation_pending": 0, "already_terminal": 0, "failed": 1}

    rows_by_id = {}
    failed = 0
    try:
        for exact_scope in variants:
            before = None
            while True:
                try:
                    rows, next_before = queue.list_manual_requests(
                        identity, exact_scope, before=before, limit=100,
                    )
                except Exception:
                    failed += 1
                    break
                rows_by_id.update((row["id"], row) for row in rows)
                if next_before is None or next_before == before:
                    break
                before = next_before

        cancelled = cancellation_pending = already_terminal = 0
        for task_id, row in rows_by_id.items():
            status = str(row.get("status") or "").lower()
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            request_key = payload.get("request_key")
            if status not in {"pending", "running", "cancel_requested"}:
                already_terminal += 1
                continue
            if not isinstance(request_key, str) or not request_key:
                failed += 1
                continue
            try:
                result = queue.request_cancel(
                    task_id, task_type="collector_manual_request", request_key=request_key,
                    reason="SUBJECT_REMOVED_FROM_DIRECTORY",
                )
            except Exception:
                result = None
            if not isinstance(result, dict):
                failed += 1
            elif result.get("status") == "cancelled":
                cancelled += 1
            elif result.get("status") == "cancel_requested":
                cancellation_pending += 1
            elif result.get("status") in {"done", "failed"}:
                already_terminal += 1
            else:
                failed += 1

        if failed:
            state = "PARTIAL"
        elif cancellation_pending:
            state = "CANCELLATION_PENDING"
        elif cancelled:
            state = "CANCELLED"
        else:
            state = "NO_ACTIVE_TASKS"
        return {"state": state, "matched": len(rows_by_id), "cancelled": cancelled,
                "cancellation_pending": cancellation_pending,
                "already_terminal": already_terminal, "failed": failed,
                "network_attempted": False}
    finally:
        queue.close()


def operate_collection_request(action, *, actor, scope, request_id=None, task_id=None,
                               page_before=None, safe_status_only=False, **source_request):
    """Manual request consumer of the original queue, live scope and source writer.

    A step executes in the real user's current request. The queue retains only
    execution state and source references, never source bodies or approval.
    """
    import uuid
    from ..guard.task_queue import TaskQueue
    if action not in {'start', 'status', 'step', 'cancel', 'resume','recover'}:
        raise ValueError('COLLECTION_TASK_ACTION_INVALID')
    if type(safe_status_only) is not bool or (safe_status_only and action not in {'status', 'cancel'}):
        raise ValueError('COLLECTION_TASK_CONTROL_MODE_INVALID')
    if page_before is not None and (action != 'status' or type(page_before) is not int or page_before <= 0):
        raise ValueError('COLLECTION_RESULT_PAGE_INVALID')
    if not isinstance(scope, Mapping):
        raise PermissionError('SCOPE_UNAUTHORIZED')
    domain = 'bmp' if scope.get('domain_id') == 'zbmp' else scope.get('domain_id')
    current_identity = (_manual_collection_actor_identity(actor) if safe_status_only else
        _business_batch_binding(actor, {domain: scope}, 'human', None)['identity'])
    queue = TaskQueue()
    try:
        if action == 'start':
            if (task_id is not None or not isinstance(request_id, str)
                    or re.fullmatch(r'[A-Za-z0-9_-]{8,128}', request_id) is None):
                raise ValueError('COLLECTION_REQUEST_ID_REQUIRED')
            admission, denial, normalized = _manual_collection_request(actor=actor, scope=scope, **source_request)
            if denial is not None:
                return denial
            _, denial = _manual_collection_guard(actor, admission['scope'], normalized['platform'],
                admission['permission_keyword'], normalized['max_results'], capability=normalized['capability'],
                **admission['provider_selection'],
                publication_since=normalized.get('publication_since'),
                publication_until=normalized.get('publication_until'))
            if denial is not None:
                return denial
            identity = _task_commit_binding('manual-request', actor, admission['scope'], 'human', None,
                normalized['platform'], admission['permission_keyword'], normalized['max_results'], None)['identity']
            requested_scope = {key: scope.get(key) for key in ('domain_id', 'global_scope', 'subject_id', 'brand_focus_id')}
            requested_scope['domain_id'] = 'bmp' if requested_scope['domain_id'] == 'zbmp' else requested_scope['domain_id']
            binding = {'identity': identity, 'scope': requested_scope, 'source_scope': admission['scope'],
                       'request': normalized, 'request_id': request_id}
            request_key = hashlib.sha256(json.dumps(binding, ensure_ascii=False, sort_keys=True,
                separators=(',', ':')).encode()).hexdigest()
            task_id = queue.enqueue_once('collector_manual_request', {'binding': binding,
                'operation_id': uuid.uuid4().hex, 'progress': {'round': 0}}, request_key)
        else:
            if source_request or request_id is not None or type(task_id) is not int or task_id <= 0:
                raise ValueError('COLLECTION_TASK_REFERENCE_REQUIRED')
        row = queue.get(task_id)
        if row is None or row['task_type'] != 'collector_manual_request':
            raise LookupError('COLLECTION_TASK_NOT_FOUND')
        payload, binding = row['payload'], row['payload']['binding']
        normalized = binding['request']
        request_fields = {key: normalized[key] for key in
            ('capability', 'platform', 'keyword', 'content_id', 'source_id', 'max_results', 'include_replies', 'author_id',
             'source_evidence_ref', 'source_fingerprint','provider_mode','public_transport',
             'publication_since','publication_until')
            if key in normalized}
        if normalized['capability'] in {'comments', 'media'}:
            request_fields.pop('platform', None)
        current_scope = {key: scope.get(key) for key in ('domain_id', 'global_scope', 'subject_id', 'brand_focus_id')}
        current_scope['domain_id'] = 'bmp' if current_scope['domain_id'] == 'zbmp' else current_scope['domain_id']
        if binding['identity'] != current_identity or binding['scope'] != current_scope:
            raise PermissionError('COLLECTION_TASK_CONTEXT_CHANGED')

        if safe_status_only:
            if action == 'cancel':
                applied = queue.set_manual_request_cancelled(task_id, payload['request_key'], cancelled=True)
                return _manual_collection_safe_status(queue.get(task_id), cancel_applied=applied)
            return _manual_collection_safe_status(row)

        def read_task():
            current = queue.get(task_id)
            progress = current['payload'].get('progress') or {}
            cancelled = current['payload'].get('cancel_requested') is True
            result = dict(progress.get('result') or {})
            if normalized['capability'] == 'media' and result.get('media'):
                from lumenis.shared.reporting.media_brief import read_collected_media
                result['saved_media'] = [read_collected_media(item['evidence_ref'], actor=actor, scope=scope,
                    source_id=normalized['source_id'], source_evidence_ref=normalized['source_evidence_ref'],
                    source_fingerprint=normalized['source_fingerprint'])
                    for item in result['media'] if item.get('evidence_ref')]
            elif result.get('page_ref'):
                result['saved_page'] = read_collected_comments(normalized['source_id'], actor=actor,
                    scope=scope, page_ref=result['page_ref'])
            elif result.get('author_evidence_ref'):
                result['saved_authors'] = read_collected_authors(result['author_evidence_ref'], actor=actor, scope=scope)
            elif result.get('evidence_ref'):
                result['saved_sources'] = read_collected_items('app_evidence_records:' + str(result['evidence_ref']),
                                                              actor=actor, scope=scope)
            pages = progress.get('result_pages') or []
            available = [page for page in pages if page_before is None or page['sequence'] < page_before]
            selected = available[-20:]
            return {'ok': True, 'status': _manual_task_status(current),
                'task_id': task_id, 'request': normalized, 'queue_status': current['status'],
                'result': result, 'continuation_required': progress.get('continuation_required', False),
                'last_attempt': progress.get('last_attempt'),
                'result_pages': selected, 'result_page_count': len(pages),
                'next_page_before': selected[0]['sequence'] if len(available) > len(selected) else None,
                'cancel_requested': cancelled, 'read_only': True, 'external_write': False,
                'network_attempted': False, 'result_freshness': 'SAVED_TASK_RESULT',
                'retry_after_seconds': max(0, current['scheduled_at'] - time.time())
                    if current['status'] == 'pending' else None}

        if action in {'start', 'status'}:
            if action == 'start':
                directory = _subject_directory_decision(actor, binding['source_scope'])
                if directory.get('allowed') is not True:
                    cancelled = queue.request_cancel(
                        task_id, task_type='collector_manual_request',
                        request_key=payload['request_key'],
                        reason=directory.get('status') or 'SUBJECT_DIRECTORY_UNAVAILABLE',
                    )
                    answer = read_task()
                    answer.update(subject_directory_state=directory.get('status'),
                        task_cancellation_state=(cancelled or {}).get('status', 'UNAVAILABLE'),
                        recovery_action=_subject_directory_denial_result(directory).get('recovery_action'))
                    return answer
            return read_task()
        if action == 'cancel':
            queue.set_manual_request_cancelled(task_id, payload['request_key'], cancelled=True)
            return read_task()
        admission, denial, current_request = _manual_collection_request(actor=actor, scope=scope, **request_fields)
        if denial is not None:
            if denial.get('status') in _SUBJECT_DIRECTORY_DENIALS:
                cancelled = queue.request_cancel(
                    task_id, task_type='collector_manual_request',
                    request_key=payload['request_key'], reason=denial['status'],
                )
                answer = read_task()
                answer.update(last_attempt={key: denial[key] for key in
                    ('ok', 'status', 'reason_code', 'error_kind', 'recovery_action') if key in denial},
                    task_cancellation_state=(cancelled or {}).get('status', 'UNAVAILABLE'))
                return answer
            return {**denial, 'task_id': task_id, 'network_attempted': False}
        if binding['source_scope'] != admission['scope'] or current_request != normalized:
            raise PermissionError('COLLECTION_TASK_CONTEXT_CHANGED')
        _, denial = _manual_collection_guard(actor, admission['scope'], normalized['platform'],
            admission['permission_keyword'], normalized['max_results'], capability=normalized['capability'],
            **admission['provider_selection'],
            publication_since=normalized.get('publication_since'),
            publication_until=normalized.get('publication_until'))
        if denial is not None:
            return {**denial, 'task_id': task_id, 'network_attempted': False}
        if action == 'resume':
            queue.set_manual_request_cancelled(task_id, payload['request_key'], cancelled=False)
            return read_task()
        if action == 'recover':
            if row['status']=='done' or payload.get('cancel_requested') is True:
                return read_task()
            from lumenis.adapters.auth_recovery import check_recovery
            recovery = check_recovery(normalized['platform'],resume_pending=False)
            return {**read_task(),'session_recovery':recovery,'source_acquisition_attempted':False,
                    'next_action':'step' if recovery.get('recovered') is True else 'recover'}
        if row['status'] == 'done' or payload.get('cancel_requested') is True:
            return read_task()
        queue.reap_stale(120, task_id=task_id)
        worker = 'manual-source-' + uuid.uuid4().hex
        claimed = queue.dequeue(worker_id=worker, lease_owner=worker, task_id=task_id)
        if claimed is None:
            return read_task()
        receipt = {key: claimed[key] for key in ('run_id', 'worker_id', 'lease_owner')}
        progress = dict(claimed['payload'].get('progress') or {'round': 0})
        stop = threading.Event()
        def renew():
            owner = TaskQueue()
            try:
                while not stop.wait(15):
                    if not owner.heartbeat(task_id, worker, run_id=receipt['run_id'], lease_owner=worker):
                        return
            finally:
                owner.close()
        heartbeat = threading.Thread(target=renew, daemon=True, name='collector-manual-lease')
        heartbeat.start()
        try:
            @contextmanager
            def guard():
                directory = _subject_directory_decision(actor, admission['scope'])
                if directory.get('allowed') is not True:
                    queue.request_cancel(task_id, task_type='collector_manual_request',
                        request_key=payload['request_key'],
                        reason=directory.get('status') or 'SUBJECT_DIRECTORY_UNAVAILABLE')
                with queue.attempt_guard(task_id, **receipt) as active:
                    yield active
                current = queue.get(task_id)
                if current and current.get('status') == 'cancel_requested':
                    queue.finish_cancelled(task_id, task_type='collector_manual_request',
                        request_key=payload['request_key'],
                        reason=current.get('last_error') or 'SUBJECT_REMOVED_FROM_DIRECTORY',
                        **receipt)
            operation = 'manual:' + payload['operation_id']
            round_key = operation + ':' + str(progress.get('round', 0))
            selection = {key:normalized[key] for key in ('provider_mode','public_transport') if key in normalized}
            if normalized['capability'] == 'media':
                from lumenis.shared.reporting.media_brief import process_collected_media
                def media_guard():
                    with guard() as active:
                        if active is not True:
                            raise PermissionError('COLLECTION_ATTEMPT_NO_LONGER_ACTIVE')
                result = process_collected_media(normalized['source_id'], actor=actor, scope=scope,
                    source_evidence_ref=normalized['source_evidence_ref'],
                    source_fingerprint=normalized['source_fingerprint'], job_id=operation,
                    check_continue=media_guard, attempt_guard=guard)
            elif normalized['capability'] == 'author':
                result = collect_author(normalized['platform'], normalized['author_id'], actor=actor, scope=scope,
                                        attempt_guard=guard, operation_key=round_key,**selection)
            elif normalized['capability'] == 'author_posts':
                result = collect_author_posts(normalized['platform'], normalized['author_id'], actor=actor, scope=scope,
                    max_results=normalized['max_results'], attempt_guard=guard, operation_key=round_key,
                    native_task_key=operation, _native_cursor=progress.get('native_cursor'),**selection)
            elif normalized['capability'] == 'comments':
                result = collect_comments(normalized['source_id'], actor=actor, scope=scope,
                    request_id=payload['operation_id'], max_results=normalized['max_results'],
                    include_replies=normalized['include_replies'], continuation=progress.get('continuation'),
                    attempt_guard=guard,**selection)
            elif normalized['capability'] == 'detail':
                result = collect_detail(normalized['platform'], normalized['content_id'], actor=actor,
                    scope=scope, attempt_guard=guard, operation_key=round_key, native_task_key=operation,**selection)
            else:
                result = collect_search(normalized['platform'], normalized['keyword'], actor=actor,
                    scope=scope, max_results=normalized['max_results'], attempt_guard=guard,
                    operation_key=round_key, native_task_key=operation, _native_cursor=progress.get('native_cursor'),
                    publication_since=normalized.get('publication_since'),
                    publication_until=normalized.get('publication_until'),**selection)
            keys = {'ok', 'status', 'source_status', 'error_type', 'error', 'platform', 'source_id', 'evidence_ref', 'page_ref',
                'task_commit_evidence_ref', 'commit_reconciled', 'network_attempted', 'raw_count',
                'returned_count', 'observed_count', 'imported', 'updated', 'canonical_synced',
                'native_fields_synced', 'coverage_state', 'partial_reason', 'source_use', 'public_original_refs',
                'original_source', 'refresh_verified', 'scope_status', 'new_collection_required', 'recovery_required',
                'retry_safe', 'recovery_action', 'review_pending_count', 'filtered_count',
                'requested_reply_scope', 'reply_coverage_state', 'replies_complete',
                'requested_result_limit', 'provider_returned_count',
                'native_pagination', 'publication_window', 'retry_after_seconds',
                'network_attempted', 'reason_code', 'error_kind'}
            keys |= {'author_evidence_ref','author_count','canonical_refs'}
            if normalized['capability'] == 'media':
                keys |= {'source_evidence_ref', 'source_fingerprint', 'processing_version',
                    'observed_media_count', 'saved_media_count', 'media_original_coverage',
                    'full_post_media_coverage', 'semantic_understanding', 'owned_inference',
                    'auto_continue', 'continuation_reason', 'pending_positions', 'failed_positions',
                    'intervention_required', 'step_processed_count', 'step_transferred_bytes',
                    'pending_media_count', 'failed_media_count'}
            saved_result = {key: result[key] for key in keys if key in result}
            if normalized['capability'] == 'media':
                saved_result['media'] = [{key: item[key] for key in
                    ('evidence_ref', 'artifact_ref', 'manifest_sha256', 'status', 'reason', 'recoverable',
                     'position', 'native_locator', 'original_bytes_saved', 'failure_evidence_ref',
                     'failure_stage', 'failure_class', 'retry_policy') if key in item}
                    for item in result.get('media') or []]
            pages = list(progress.get('result_pages') or [])
            if not pages and progress.get('result'):
                previous = progress['result']
                if previous.get('page_ref') or previous.get('evidence_ref') or previous.get('author_evidence_ref'):
                    pages.append({'sequence': 1, **previous})
            source_ref = result.get('page_ref') or result.get('author_evidence_ref') or result.get('evidence_ref')
            if source_ref is not None and not any(
                    (page.get('page_ref') or page.get('author_evidence_ref') or page.get('evidence_ref')) == source_ref
                    for page in pages):
                pages.append({'sequence': len(pages) + 1, **saved_result})
            progress['result_pages'] = pages
            progress['last_attempt'] = saved_result
            if source_ref is not None or normalized['capability'] == 'media' or not progress.get('result'):
                progress['result'] = saved_result
            comment_next = (result.get('continuation', progress.get('continuation'))
                            if normalized['capability'] == 'comments' else None)
            native_next = result.get('native_continuation_verified') is True and not result.get('new_collection_required')
            source_page = result.get('native_pagination') or {}
            page_next = (normalized['capability'] in {'search','author_posts'} and source_page.get('request_cursor') == progress.get('native_cursor')
                         and source_page.get('next_cursor') is not None and source_page.get('exhausted') is not True)
            waiting = result.get('status') in {'AUTH_REQUIRED', 'SESSION_EXPIRED', 'NEED_VERIFY', 'BLOCKED',
                'COOLING_DOWN', 'RATE_LIMITED', 'BUSY', 'APPROVAL_REQUIRED', 'PROVIDER_UNAVAILABLE'}
            media_pending = normalized['capability'] == 'media' and result.get('continuation_required') is True
            progress.update(continuation=comment_next, continuation_required=bool(comment_next or native_next or page_next or waiting or media_pending),
                waiting_user=waiting, round=progress.get('round', 0) + (1 if native_next or page_next else 0))
            if page_next:
                progress['native_cursor'] = source_page['next_cursor']
            if not queue.save_progress(task_id, progress, **receipt):
                current = queue.get(task_id)
                if current and current.get('status') == 'cancel_requested':
                    queue.finish_cancelled(task_id, task_type='collector_manual_request',
                        request_key=payload['request_key'],
                        reason=current.get('last_error') or 'SUBJECT_REMOVED_FROM_DIRECTORY',
                        **receipt)
                return read_task()
            if progress['continuation_required']:
                delay = max(float(result.get('wait_seconds') or 0), float(result.get('retry_after_seconds') or 0))
                queue.yield_pending(task_id, **receipt, delay=delay)
            elif result.get('ok') is True or result.get('page_ref') or result.get('task_commit_evidence_ref'):
                queue.ack(task_id, **receipt)
            else:
                queue.fail(task_id, str(result.get('status') or 'COLLECTION_FAILED'), **receipt, retryable=False)
            answer = read_task()
            answer.update(network_attempted=result.get('network_attempted') is not False,
                          result_freshness='HISTORICAL_COMMIT_RECONCILED' if result.get('commit_reconciled')
                              else 'CURRENT_TASK_EXECUTION')
            return answer
        except PermissionError as exc:
            current = queue.get(task_id)
            if current and current['payload'].get('cancel_requested') is True:
                if current.get('status') == 'cancel_requested':
                    queue.finish_cancelled(task_id, task_type='collector_manual_request',
                        request_key=payload['request_key'],
                        reason=current.get('last_error') or 'SUBJECT_REMOVED_FROM_DIRECTORY',
                        **receipt)
                return read_task()
            if str(exc) in {
                    'COLLECTED_MEDIA_USE_APPROVAL_REQUIRED',
                    'COLLECTED_MEDIA_COMMIT_USE_REVOKED',
                    'COLLECTED_MEDIA_COMMIT_APPROVAL_BUSY'}:
                progress.update(waiting_user=True, continuation_required=True,
                    last_attempt={'ok': False, 'status': 'APPROVAL_REQUIRED',
                        'code': str(exc), 'auto_continue': False,
                        'intervention_required': True,
                        'continuation_reason': 'MEDIA_USE_APPROVAL_REQUIRED'})
                if queue.save_progress(task_id, progress, **receipt):
                    queue.yield_pending(task_id, **receipt)
                answer = read_task()
                answer.update(ok=False, code=str(exc), recovery_required=True,
                    next_action='confirm', auto_continue=False,
                    network_attempted=getattr(exc, 'network_attempted', None),
                    result_freshness='SAVED_TASK_RESULT')
                return answer
            queue.fail(task_id, str(exc), **receipt, retryable=False)
            raise
        except Exception as exc:
            # The stable round replays a committed Source receipt after an
            # operational-checkpoint failure; no blind external refetch.
            queue.fail(task_id, type(exc).__name__, **receipt, retryable=True)
            raise
        finally:
            stop.set()
            heartbeat.join(timeout=2)
    finally:
        queue.close()


class _CollectionWriteRejected(Exception):
    """Abort the scoped transaction without publishing partial write success."""

    def __init__(self, result):
        self.result = result
        super().__init__(str(result.get("status") or "COLLECTION_WRITE_FAILED"))


def _verified_native_resume(platform, keyword, fingerprint, metadata):
    """A resumable native pointer is progress, never an acquisition permission."""
    if platform != "xiaohongshu" or not isinstance(fingerprint, str):
        return False
    continuation = metadata.get("continuation")
    if (metadata.get("continuation_persisted") is not True
            or metadata.get("checkpoint_identity_verified") is not True
            or not isinstance(continuation, dict)
            or continuation.get("identity_verified") is not True
            or continuation.get("continuation_required") is not True
            or continuation.get("keyword") != keyword
            or continuation.get("source_host") != "www.rednote.com"):
        return False
    from ..guard.checkpoint import Checkpoint
    saved = Checkpoint("xhs").get_operational_resume(keyword, fingerprint)
    return bool(isinstance(saved, dict) and saved.get("task_binding") == fingerprint
        and saved.get("keyword") == keyword and saved.get("source_host") == "www.rednote.com"
        and saved.get("continuation_required") is True and saved.get("complete") is False
        and saved.get("terminal_error") is False
        and isinstance(saved.get("run_id"), str) and bool(saved["run_id"])
        and saved["run_id"] == continuation.get("checkpoint_run_id"))


def _task_commit_binding(operation_key, actor, scope, operator, authorization,
                         platform, keyword, max_results, business_query, *,
                         publication_since=None, publication_until=None):
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
    if publication_since is not None:
        material["publication_since"] = publication_since
    if publication_until is not None:
        material["publication_until"] = publication_until
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
        resumable = (result.get("status") == "PARTIAL_ACQUISITION_PENDING"
                     and result.get("native_continuation_verified") is True)
        result.update(source_status=result.get("status"), status="PARTIAL_COMMITTED",
                      retry_safe=resumable, new_collection_required=not resumable,
                      recovery_action="RESUME_VERIFIED_NATIVE_CHECKPOINT" if resumable else
                      "REVIEW_COMMITTED_SOURCES_THEN_CREATE_NEW_REQUEST")
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
                   attempt_guard=None, operation_key=None,
                    capability: str = 'search', _source_url=None, native_task_key=None,
                    _native_cursor=None,provider_mode=None,public_transport=None,
                    publication_since=None, publication_until=None) -> Dict[str, Any]:
    """Run one explicit, read-only platform search and persist its evidence."""
    if capability not in {'search', 'detail', 'author_posts'}:
        raise ValueError('unsupported collection capability')
    if publication_since is not None or publication_until is not None:
        if capability != 'search':
            raise ValueError('PUBLICATION_WINDOW_REQUIRES_SEARCH')
        from ..acquisition_plan import _validate_publication_period
        _validate_publication_period(publication_since, publication_until)
    if _native_cursor is not None and (capability not in {'search','author_posts'} or not native_task_key
            or _credential_free_observations(_native_cursor) != _native_cursor):
        raise ValueError('server-authored search continuation required')
    if _source_url is not None and (capability != 'detail' or _credential_free_observations(_source_url) != keyword):
        raise ValueError('detail source locator does not match its source identity')
    if capability == 'detail' and (prelaunch_local_import or raw_capture is not None
            or native_capture is not None or business_query is not None or max_scroll is not None):
        raise ValueError('independent detail requires the exact manual source request')
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
    platform, keyword, max_results = _validate_request(platform, keyword, max_results, capability=capability)
    if (prelaunch_local_import or native_capture is not None or raw_capture is not None):
        if provider_mode is not None or public_transport is not None:
            raise ValueError('COLLECTION_CAPTURE_HAS_FIXED_PROVIDER')
        provider_selection = {}
    else:
        provider_selection = normalize_provider_selection(platform,provider_mode=provider_mode,public_transport=public_transport)
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
            max_scroll=max_scroll, capability=capability,**provider_selection,
            publication_since=publication_since, publication_until=publication_until,
        )
        if denial is not None:
            return denial
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
            operator, prelaunch_authorization, platform, keyword, max_results, business_query,
            publication_since=publication_since, publication_until=publication_until)
        if provider_selection:
            task_binding['provider_selection'] = provider_selection
        if capability != 'search':
            task_binding['capability'] = capability
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
            _adapter_health(platform, url=keyword,**provider_selection)
            if platform in {"public_http", "web_atom", "sitemap", "instagram", "wechat"} else _adapter_health(platform,**provider_selection)
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
            search_kwargs = {"max_results": max_results,**provider_selection}
            if (platform in {"public_http", "web_atom", "sitemap"}
                    and (capability == "search"
                         or platform == "public_http" and capability == "detail")):
                def check_public_fetch_attempt():
                    if attempt_guard is not None:
                        with attempt_guard() as attempt_active:
                            if attempt_active is not True:
                                raise InterruptedError("COLLECTION_ATTEMPT_NO_LONGER_ACTIVE")

                def recheck_public_fetch_admission():
                    # The public-document limiter may wait after the request's
                    # initial admission. Recheck the exact live authority only
                    # after that wait and before the anonymous transport starts.
                    check_public_fetch_attempt()
                    if manual_scope is not None:
                        _, current_denial = _manual_collection_guard(
                            actor, manual_scope, platform, permission_keyword, max_results,
                            max_scroll=max_scroll, capability=capability, **provider_selection,
                            publication_since=publication_since, publication_until=publication_until,
                        )
                        if current_denial is not None:
                            raise PermissionError("COLLECTION_SOURCE_PERMISSION_REVOKED")
                    elif prelaunch_scope is not None:
                        if not _authorize_prelaunch_public(
                                prelaunch_scope, keyword, platform,
                                maintenance_authorization=prelaunch_authorization,
                                business_query=business_query, max_results=max_results):
                            raise PermissionError("COLLECTION_SOURCE_PERMISSION_REVOKED")
                        _validate_prelaunch_registry(prelaunch_scope)

                search_kwargs["before_fetch"] = recheck_public_fetch_admission
                if attempt_guard is not None:
                    search_kwargs["check_continue"] = check_public_fetch_attempt
            if _native_cursor is not None:
                search_kwargs['cursor'] = _native_cursor
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
            elif platform == 'xiaohongshu' and (capability == 'detail' or native_task_key is not None):
                binding = _task_commit_binding(native_task_key or operation_key or 'manual-independent-detail',
                    actor, manual_scope, operator, None, platform, keyword, max_results, None)
                binding['capability'] = capability
                acquisition_fingerprint = hashlib.sha256(json.dumps(binding,
                    ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                search_kwargs['acquisition_fingerprint'] = acquisition_fingerprint
            collection = (_native_capture_collection(native_capture) if native_capture is not None else
                          _public_raw_collection(raw_capture) if raw_capture is not None
                          else getattr(_get_runtime_adapter(platform), capability)(_source_url or keyword, **search_kwargs))
            if not isinstance(collection, CollectionResult):
                raise TypeError("adapter returned a non-CollectionResult value")
            if native_capture is None and raw_capture is None:
                bind_collection_route(
                    collection, platform=platform, capability=capability, request_value=keyword,
                    **provider_selection,
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
        except PermissionError:
            # A public-source permission change after limiter wait is still an
            # authorization denial, not a retryable provider failure.
            raise
        except InterruptedError as exc:
            if str(exc) != "COLLECTION_ATTEMPT_NO_LONGER_ACTIVE":
                raise
            network_attempted = getattr(exc, "network_attempted", False) is True
            collection = CollectionResult(
                status=CollectionStatus.BLOCKED,
                platform=platform,
                message=("本次采集任务已停止，公开来源读取已中断" if network_attempted
                         else "本次采集任务已停止，尚未开始公开来源请求"),
                metadata={"provider": platform, "error_type": str(exc),
                          "network_attempted": network_attempted},
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
        provider_items = collection.items if isinstance(collection.items, list) else []
        provider_returned_count = len(provider_items)
        provider_limit_exceeded = provider_returned_count > max_results
        if provider_limit_exceeded:
            # max_results is part of the exact approved request. A provider
            # returning more records cannot widen that request, and truncating
            # the page would make its native cursor skip unseen records. Keep
            # only count/pagination diagnostics; do not admit any returned body.
            metadata = dict(collection.metadata) if isinstance(collection.metadata, dict) else {}
            rejected_pagination = {
                key: _credential_free_observations(metadata[key])
                for key in ('pagination', 'continuation') if key in metadata
            }
            metadata['error_type'] = 'PROVIDER_RESULT_LIMIT_EXCEEDED'
            metadata['result_limit_validation'] = {
                'requested_limit': max_results,
                'provider_returned_count': provider_returned_count,
                'rejected_pagination': rejected_pagination,
            }
            # A cursor from this rejected response must not become a task
            # continuation, because its exact page was not admitted.
            metadata.pop('pagination', None)
            metadata.pop('continuation', None)
            collection.metadata = metadata
            collection.status = CollectionStatus.COLLECT_ERROR
            collection.message = 'provider returned more records than the approved request limit'
            collection.items = []
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
        identity_review_pending = any(review['status'] != 'CANDIDATE_TASK_RELEVANT'
                                      for review in business_reviews)
        publication_reviews = (_requested_publication_window_reviews(
            records, platform=platform, publication_since=publication_since,
            publication_until=publication_until,
        ) if publication_since is not None or publication_until is not None else [])
        publication_review_pending = [review for review in publication_reviews
            if review['status'].startswith('REVIEW_REQUIRED_')]
        if manual_scope is not None:
            _, denial = _manual_collection_guard(
                actor, manual_scope, platform, permission_keyword, max_results,
                max_scroll=max_scroll, capability=capability,**provider_selection,
                publication_since=publication_since, publication_until=publication_until,
            )
            if denial is not None:
                return denial
        source_item_count = len(items)
        entity_mentions = []
        review_pending = []
        review_candidates = []
        accepted_indices = set(range(len(records)))
        if business_reviews:
            business_accepted = {index for index, review in enumerate(business_reviews)
                                 if review['status'] == 'CANDIDATE_TASK_RELEVANT'}
            accepted_indices.intersection_update(business_accepted)
            review_pending = [review for review in business_reviews if review['status'] != 'CANDIDATE_TASK_RELEVANT']
        if publication_reviews:
            time_accepted = {review['observation_index'] for review in publication_reviews
                             if review['status'] == 'CANDIDATE_IN_REQUESTED_PUBLICATION_WINDOW'}
            accepted_indices.intersection_update(time_accepted)
            review_pending.extend(review for review in publication_reviews
                                  if review['status'].startswith('REVIEW_REQUIRED_'))
        review_candidates = [record for index, record in enumerate(records) if index not in accepted_indices]
        records = [record for index, record in enumerate(records) if index in accepted_indices]
        items = [item for index, item in enumerate(items) if index in accepted_indices]
        if (prelaunch_scope is not None and collection.ok and records
                and (manual_scope is not None or business_query is not None or platform in {"douyin", "x"})):
            entity_mentions = _prelaunch_entity_mentions(records, prelaunch_scope)
            entity_review_pending = [item for item in entity_mentions if item["status"] != "EXACT_NAME_MENTION"]
            identity_review_pending = identity_review_pending or bool(entity_review_pending)
            review_pending += entity_review_pending
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
        public_failure_fields = {}
        if status not in {"SUCCESS", "NO_NEW_DATA"}:
            from .public_source import safe_public_source_failure_fields
            public_failure_fields = safe_public_source_failure_fields(metadata)
            provenance.update(public_failure_fields)
        if metadata.get('result_limit_validation'):
            provenance['result_limit_validation'] = _credential_free_observations(
                metadata['result_limit_validation'])
        observed_failure = {key:metadata.get(key) for key in
            ('failure_class','http_status','provider_code','retry_after_seconds','identity_failure_stage')
            if metadata.get(key) is not None}
        if observed_failure:
            provenance['provider_observation'] = _credential_free_observations(observed_failure)
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
        if publication_since is not None or publication_until is not None:
            provenance['requested_publication_window'] = {
                'publication_since': publication_since,
                'publication_until': publication_until,
                'transport_filter_state': 'NOT_APPLIED_BY_REGISTERED_ADAPTER',
                'candidate_review_state': 'APPLIED_POST_FETCH_NATIVE_TIME',
                'reviews': publication_reviews,
            }
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
                    final_status = ("PUBLICATION_TIME_REVIEW_REQUIRED"
                                    if publication_review_pending and not identity_review_pending
                                    else "SCOPE_REVIEW_REQUIRED")
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
                result.update(public_failure_fields)
                if metadata.get("network_attempted") is False:
                    result["network_attempted"] = False
                retry_after = metadata.get("retry_after_seconds")
                if type(retry_after) is int and retry_after >= 0:
                    result["retry_after_seconds"] = retry_after
                if provider_limit_exceeded:
                    result.update(
                        error_type='PROVIDER_RESULT_LIMIT_EXCEEDED',
                        error='PROVIDER_RESULT_LIMIT_EXCEEDED: provider exceeded the exact request limit',
                        provider_returned_count=provider_returned_count,
                        requested_result_limit=max_results,
                        returned_count=provider_returned_count,
                        filtered_count=None,
                    )
                if publication_since is not None or publication_until is not None:
                    result['publication_window'] = _publication_window_summary(
                        publication_reviews, publication_since=publication_since,
                        publication_until=publication_until)
                discovered = metadata.get('discovery_candidates')
                if isinstance(discovered, list):
                    result['discovery_observations'] = [_credential_free_observations({key: candidate.get(key)
                        for key in ('source_url','source_title','index_excerpt','index_date_literal',
                                    'index_date_not_article_publication','native_publication')})
                        for candidate in discovered if isinstance(candidate, dict)]
                    result['discovery_state'] = 'INDEX_ONLY_ORIGINAL_BODY_REQUIRED'
                    result['original_outcomes'] = _credential_free_observations(metadata.get('original_outcomes') or [])
                native_page = metadata.get('pagination')
                if isinstance(native_page, dict):
                    native_page = _credential_free_observations(native_page)
                    if native_page.get('request_cursor') != _native_cursor:
                        result.update(ok=False, status='NATIVE_CURSOR_NOT_CONSUMED',
                                      error_type='NATIVE_CURSOR_NOT_CONSUMED', refresh_verified=False)
                    if native_page.get('next_cursor') is not None and native_page.get('next_cursor') == _native_cursor:
                        native_page = {**native_page, 'next_cursor':None, 'exhausted':False,
                                       'partial_reason':'NATIVE_CURSOR_NON_PROGRESSING'}
                    result['native_pagination'] = native_page
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
                if (platform in PUBLIC_ORIGINAL_PLATFORMS and manual_scope is not None and raw_capture is None
                        and native_capture is None and note_ids and result.get('ok')):
                    conn.execute('SAVEPOINT collected_public_original')
                    source_path_start = len(staged_source_paths)
                    try:
                        from lumenis.shared.reporting.saved_work import authorize
                        source_context = authorize(actor, manual_scope, action='write', connection=conn)
                        if len(note_ids) != 1 or len(records) != 1:
                            raise ValueError('PUBLIC_SOURCE_OBSERVATION_AMBIGUOUS')
                        original = _persist_public_http_original(conn, response=collection.original_response,
                            record=records[0], source_id=note_ids[0], collection_evidence_id=evidence_id,
                            context=source_context, staged_paths=staged_source_paths, actor=actor,
                            scope=manual_scope, keyword=permission_keyword, max_results=max_results,
                            capability=capability, platform=platform)
                        _bind_native_source_original(conn, note_ids[0], source_context, original)
                        conn.execute('RELEASE SAVEPOINT collected_public_original')
                        result['public_original_refs'] = {'source_id': note_ids[0], **original}
                    except Exception as exc:
                        conn.execute('ROLLBACK TO SAVEPOINT collected_public_original')
                        conn.execute('RELEASE SAVEPOINT collected_public_original')
                        cleanup_ok = _cleanup_collected_source_paths(staged_source_paths[source_path_start:])
                        del staged_source_paths[source_path_start:]
                        result['public_original_refs'] = {'source_id': note_ids[0], 'status': 'UNAVAILABLE',
                            'source_artifact_ref': None, 'reason': str(exc) if isinstance(exc, ValueError)
                                else 'PUBLIC_SOURCE_ORIGINAL_PRESERVATION_UNAVAILABLE',
                            'cleanup_status': 'COMPLETE' if cleanup_ok else 'FAILED', 'source_use': 'NOT_GRANTED'}
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
                        max_scroll=max_scroll, capability=capability,**provider_selection,
                        publication_since=publication_since, publication_until=publication_until,
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
                        result["native_continuation_verified"] = _verified_native_resume(
                            platform, keyword, acquisition_fingerprint, metadata)
                # The signed success above covers only admitted source_ids. Keep the
                # overall request partial when other returned items still need review.
                if review_pending and result["ok"]:
                    time_only_review = publication_review_pending and not identity_review_pending
                    result.update({
                        "ok": False,
                        "status": ("PUBLICATION_TIME_REVIEW_REQUIRED" if time_only_review and not records
                                   else "PARTIAL_SCOPE_REVIEW_REQUIRED"),
                        "error_type": ("PUBLICATION_TIME_REVIEW_REQUIRED" if time_only_review
                                       else "SOURCE_ENTITY_IDENTITY_UNCONFIRMED"),
                        "error": (_status_message("PUBLICATION_TIME_REVIEW_REQUIRED") if time_only_review
                                  else _status_message("PARTIAL_SCOPE_REVIEW_REQUIRED")),
                        "scope_status": "PARTIAL", "refresh_verified": False,
                    })
                if (publication_reviews and not publication_review_pending and not records
                        and all(review['status'] == 'OUTSIDE_REQUESTED_PUBLICATION_PERIOD'
                                for review in publication_reviews)
                        and result['ok']):
                    result['publication_window']['state'] = 'NO_MATCHING_OBSERVATIONS'
                    result['status'] = 'NO_NEW_DATA'
                    result['error_type'] = 'NO_MATCHING_OBSERVATIONS'
                    result['error'] = _status_message('NO_MATCHING_OBSERVATIONS')
                if note_ids:
                    result['items'] = _source_item_views(conn, records, note_ids, platform, evidence_id,
                                                       manual_scope or prelaunch_scope)
                has_source_effect = any(int(result.get(field, 0) or 0) > 0 for field in
                    ("imported", "updated", "canonical_synced", "native_fields_synced")) or any(
                    item.get("status") == "SAVED" for item in
                    result.get("live_original_refs", []) + result.get("pending_original_refs", []))
                # A transient error's diagnostic Evidence is not a completed
                # source effect. Permit retry; committed partial sources remain fenced.
                discovery_saved = bool(result.get('discovery_observations') and result.get('evidence_recorded'))
                publication_review_saved = (
                    result.get('status') == 'PUBLICATION_TIME_REVIEW_REQUIRED'
                    and result.get('evidence_recorded') is True
                    and isinstance(result.get('evidence_ref'), str)
                    and isinstance(result.get('publication_window'), dict)
                    and result['publication_window'].get('state') == 'REVIEW_REQUIRED'
                    and result['publication_window'].get('review_required_count', 0) > 0
                )
                if task_binding is not None and (result.get("ok") is True or has_source_effect
                                                 or discovery_saved or publication_review_saved):
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


def _normalize_author_target(platform, value):
    if not isinstance(value,str) or not value.strip() or value != value.strip():
        raise ValueError('AUTHOR_PROFILE_REQUIRED')
    text = value
    if platform in {'naver','daum'} and not text.startswith(('http://','https://')):
        text = text.removeprefix('blog:' if platform=='naver' else 'tistory:')
    if text.startswith(('http://','https://')):
        parts = urlsplit(text)
        if platform in {'naver','daum'}:
            if parts.scheme!='https' or parts.username or parts.password or parts.port not in (None,443):
                raise ValueError('AUTHOR_PROFILE_PLATFORM_MISMATCH')
            if platform=='naver' and parts.hostname in {'blog.naver.com','m.blog.naver.com'}:
                text = parts.path.strip('/')
                if parts.path in {'/PostList.naver','/PostList.nhn'}:
                    text = dict(parse_qsl(parts.query)).get('blogId','')
            elif (platform=='daum' and str(parts.hostname or '').endswith('.tistory.com')
                    and parts.path in {'','/'}):
                text = parts.hostname[:-len('.tistory.com')]
            else:
                raise ValueError('AUTHOR_PROFILE_PLATFORM_MISMATCH')
            if re.fullmatch(r'[A-Za-z0-9_-]{1,100}',text) is None:
                raise ValueError('AUTHOR_ID_INVALID')
            return text
        hosts = {'bilibili':{'space.bilibili.com'}, 'xiaohongshu':{'www.rednote.com','rednote.com'},
            'douyin':{'www.douyin.com','douyin.com'}, 'instagram':{'www.instagram.com','instagram.com'},
            'facebook':{'www.facebook.com','facebook.com'}, 'x':{'x.com','www.x.com','twitter.com','www.twitter.com'},
            'weibo':{'weibo.com','www.weibo.com','m.weibo.cn'}, 'zhihu':{'www.zhihu.com','zhihu.com'},
            'kuaishou':{'www.kuaishou.com','kuaishou.com'}, 'youtube':{'www.youtube.com','youtube.com'},
            'reddit':{'www.reddit.com','reddit.com'}, 'linkedin':{'www.linkedin.com','linkedin.com'},
            'tiktok':{'www.tiktok.com','tiktok.com'}, 'tieba':{'tieba.baidu.com'},
            'github':{'github.com','www.github.com'},'channels':{'weixin.qq.com','channels.weixin.qq.com'}}
        if (parts.scheme != 'https' or parts.hostname not in hosts.get(platform,set())
                or parts.username or parts.password or parts.port not in (None,443)):
            raise ValueError('AUTHOR_PROFILE_PLATFORM_MISMATCH')
        segments = parts.path.strip('/').split('/')
        if platform=='channels':
            if (_credential_free_observations(text)!=text or any(part in {'login','auth','cgi-bin'} for part in segments)):
                raise ValueError('AUTHOR_PROFILE_FORMAT_INVALID')
            return text
        if platform=='youtube' and len(segments)==1 and segments[0].startswith('@'):
            return segments[0]
        if platform=='linkedin' and len(segments)==2 and segments[0] in {'in','company'}:
            if re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',segments[1]) is None:
                raise ValueError('AUTHOR_ID_INVALID')
            return segments[0]+':'+segments[1]
        prefixes = {'xiaohongshu':['user','profile'], 'douyin':['user'], 'zhihu':['people'],
                    'kuaishou':['profile'], 'youtube':['channel'], 'reddit':['user'], 'linkedin':['in']}
        prefix = prefixes.get(platform,[])
        if platform == 'weibo' and segments[:1] == ['u']:
            prefix = ['u']
        if segments[:len(prefix)] != prefix or len(segments) != len(prefix)+1:
            raise ValueError('AUTHOR_PROFILE_FORMAT_INVALID')
        text = segments[-1]
    if re.fullmatch(r'[A-Za-z0-9_.@:-]{1,160}',text) is None:
        raise ValueError('AUTHOR_ID_INVALID')
    if platform == 'bilibili' and re.fullmatch(r'[1-9]\d{0,19}',text) is None:
        raise ValueError('AUTHOR_ID_INVALID')
    if platform == 'xiaohongshu' and re.fullmatch(r'[0-9a-fA-F]{24}',text) is None:
        raise ValueError('AUTHOR_ID_INVALID')
    return text


def _author_observation(platform, item, requested, captured_at):
    from .platform_naming import get_platform_fields
    raw = item.get('raw') or {}
    spec = get_platform_fields(platform)
    identity = next((raw.get(key) for key in (spec.author_id if spec else '', 'username','uid','mid')
                     if raw.get(key) is not None and raw.get(key) != ''), item.get('author_id'))
    if identity is None or identity == '':
        raise ValueError('AUTHOR_NATIVE_ID_NOT_OBSERVED')
    identity = str(identity)
    compare = str.lower if platform in {'x','instagram','facebook'} else str
    aliases = raw.get('native_author_aliases') or item.get('native_author_aliases') or []
    if not isinstance(aliases, list):
        raise ValueError('AUTHOR_NATIVE_ALIASES_INVALID')
    observed = {compare(identity.lstrip('@'))}
    observed.update(compare(str(value).lstrip('@')) for value in aliases
                    if isinstance(value, (str, int)) and not isinstance(value, bool)
                    and re.fullmatch(r'[A-Za-z0-9_.@:-]{1,160}', str(value)))
    if platform in {'linkedin','channels'}:
        profile_url = raw.get('profile_url') or item.get('url')
        if isinstance(profile_url,str):
            try:
                observed.add(compare(_normalize_author_target(platform,profile_url).lstrip('@')))
            except ValueError:
                pass
    if compare(requested.lstrip('@')) not in observed:
        raise ValueError('AUTHOR_NATIVE_ID_MISMATCH')
    def count(names, display_name):
        value = next((raw[key] for key in names if raw.get(key) is not None), None)
        display = raw.get(display_name)
        if display and re.fullmatch(r'[0-9,\s]+',str(display)) is None:
            return None
        if type(value) is int and value >= 0:
            return value
        if isinstance(value,str) and value.isascii() and value.isdigit():
            return int(value)
        return None
    value = {'platform':platform, 'platform_author_id':identity,
        'native_author_aliases': sorted(observed),
        'username':raw.get('username') or None,
        'display_name':raw.get('display_name') or item.get('author_nickname') or item.get('title') or None,
        'bio':raw.get('bio') or item.get('content') or None,
        'avatar_url':raw.get('avatar_url') or raw.get('face') or item.get('cover') or None,
        'profile_url':raw.get('profile_url') or item.get('url') or None,
        'verified':raw.get('verified') if type(raw.get('verified')) is bool else None,
        'verification_type':raw.get('verification_type'), 'account_type':raw.get('creator_type'),
        'follower_count':count(('follower_count','followers','followers_count'),'followers_str'),
        'following_count':count(('following_count','following','follow_count'),'following_str'),
        'content_count':count(('content_count','posts','statuses_count'),'posts_str'),
        'count_displays':{key:raw.get(key) or None for key in ('followers_str','following_str','posts_str')},
        'location':raw.get('location'), 'country':raw.get('country'), 'language':raw.get('language'),
        'website':raw.get('website'), 'captured_at':captured_at, 'published_at':None,
        'raw':raw, 'claim_type':'PLATFORM_REPORTED_PROFILE',
        'entity_relationship_established':False}
    return _credential_free_observations(value)


def collect_author(platform, author_id, *, actor, scope, attempt_guard=None, operation_key=None,
                   provider_mode=None,public_transport=None):
    """Read a native author through the same session, approval and data owners."""
    import database as db
    from lumenis.shared.evidence.store import record_evidence
    from lumenis.shared.database.platform_content import persist_platform_author_records
    platform = 'xiaohongshu' if platform == 'xhs' else platform
    platform, _, _ = _validate_request(platform, str(author_id or ''), 1)
    selection = normalize_provider_selection(platform,provider_mode=provider_mode,public_transport=public_transport)
    target = _normalize_author_target(platform, author_id)
    exact, denial = _manual_collection_guard(actor, scope, platform, target, 1, capability='author',**selection)
    if denial is not None:
        return denial
    binding = _task_commit_binding(operation_key, actor, exact, 'human', None, platform,target,1,None) if operation_key else None
    if binding and selection:
        binding['provider_selection'] = selection
    if binding:
        with db.get_db() as connection:
            saved = _task_commit_receipt(connection,binding)
            if saved:
                return saved
    lock = _locks[platform]
    if not lock.acquire(blocking=False):
        return {'ok':False,'status':'BUSY','platform':platform,'network_attempted':False}
    try:
        with _last_action_lock:
            elapsed = time.monotonic() - _last_action[platform]
            if elapsed < MIN_INTERVAL_SECONDS:
                return {'ok':False,'status':'RATE_LIMITED','platform':platform,
                        'wait_seconds':MIN_INTERVAL_SECONDS-elapsed,'network_attempted':False}
            _last_action[platform] = time.monotonic()
        try:
            result = _get_runtime_adapter(platform).author(target,**selection)
            if not isinstance(result, CollectionResult):
                raise TypeError('AUTHOR_PROVIDER_RESULT_INVALID')
            bind_collection_route(result,platform=platform,capability='creator',request_value=target,**selection)
        except Exception as exc:
            result = CollectionResult(CollectionStatus.PROVIDER_UNAVAILABLE,platform,
                metadata={'error_type':type(exc).__name__},message='AUTHOR_PROVIDER_UNAVAILABLE')
        captured = datetime.now().astimezone().isoformat(timespec='seconds')
        native_items = [item for item in result.items or [] if isinstance(item,dict)]
        observations, rejected = [], []
        if result.ok:
            try:
                observations = [_author_observation(platform,item,target,captured) for item in native_items]
                if len(observations) > 1:
                    raise ValueError('AUTHOR_PROFILE_AMBIGUOUS')
            except ValueError as exc:
                rejected = _credential_free_observations(native_items)
                observations = []
                result.status = CollectionStatus.PROVIDER_UNAVAILABLE
                result.metadata['error_type'] = str(exc)
        elif native_items:
            rejected = _credential_free_observations(native_items)
        status = _canonical_status(result)
        if result.ok and not observations:
            status = 'NO_NEW_DATA'
        response = {'ok':result.ok,'status':status, 'platform':platform,
            'author_count':len(observations) if result.ok else None, 'authors':observations,
            'raw_count':_observed_raw_count(result,len(native_items)),
            'error_type':(result.metadata or {}).get('error_type'),
            'provenance':_credential_free_observations(result.provenance or {}),
            'read_only':True,'external_write':False,'network_attempted':True,
            'source_use':'INSPECTION_ONLY_CHECK_EACH_RESEARCH_QUOTE_EXPORT_TRAIN_USE'}
        with (attempt_guard() if attempt_guard else nullcontext(True)) as active, db.get_db() as connection:
            if active is not True:
                raise PermissionError('COLLECTION_ATTEMPT_SUPERSEDED')
            connection.execute('BEGIN IMMEDIATE')
            _, denial = _manual_collection_guard(actor,exact,platform,target,1,capability='author',**selection)
            if denial is not None:
                raise PermissionError('AUTHOR_APPROVAL_REVOKED')
            source_ids = ['platform-author:'+platform+':'+item['platform_author_id'] for item in observations]
            evidence_id = record_evidence(connection=connection, source='collector',feature_id='COLLECTOR_NATIVE_AUTHORS',
                version='collector-native-author/1',asset_id=target,capture_mode='native_author_read',
                inputs={'platform':platform,'provider_selection':selection,'source_ids':source_ids,'author_observation_records':observations,
                    'unverified_author_observation_records':rejected},
                outputs={'status':response['status'],'author_count':response['author_count'],
                    'raw_count':response['raw_count'],'error_type':response['error_type']},
                result='PASS' if response['ok'] else 'FAIL',provider=(result.metadata or {}).get('provider') or platform,
                collection_metadata=response['provenance'],
                product='CTH' if exact['domain_id']=='cth' else 'ZBMP',
                domain_id='cth' if exact['domain_id']=='cth' else 'zbmp',subject_id=exact['subject_id'],
                brand_focus_id=exact['brand_focus_id'],global_scope=exact['global_scope'],captured_at=captured)
            response.update(evidence_ref=str(evidence_id),author_evidence_ref=f'app_evidence_records:{evidence_id}')
            if observations:
                response['canonical_refs'] = persist_platform_author_records(observations,platform=platform,
                    evidence_id=evidence_id,scope=exact,connection=connection)
            if binding:
                _task_commit_receipt(connection,binding,response)
        try:
            _write_run_log(platform,target,started=captured,finished=_now(),fetched=response['raw_count'],
                accepted=len(observations) if response['ok'] else None,
                rejected=len(rejected) if response['raw_count'] is not None else None,error=response['error_type'])
            response['run_log_recorded'] = True
        except Exception:
            response['run_log_recorded'] = False
        return response
    finally:
        lock.release()


def read_collected_authors(evidence_ref, *, actor, scope):
    import database as db
    from lumenis.shared.evidence.store import classify_evidence_integrity
    domain = 'bmp' if scope.get('domain_id') == 'zbmp' else scope.get('domain_id')
    _business_batch_binding(actor,{domain:scope},'human',None)
    if not isinstance(evidence_ref,str) or re.fullmatch(r'app_evidence_records:[1-9]\d*',evidence_ref) is None:
        raise ValueError('AUTHOR_EVIDENCE_REFERENCE_REQUIRED')
    with db.get_db() as connection:
        row = connection.execute('SELECT * FROM app_evidence_records WHERE id=?',(int(evidence_ref.split(':')[1]),)).fetchone()
        evidence = dict(row) if row else {}
        inputs = json.loads(evidence.get('inputs_json') or '{}')
        signed = inputs.get('_lumenis_scope') or {}
        expected = {'domain_id':'cth' if domain=='cth' else 'zbmp','product_id':'CTH' if domain=='cth' else 'ZBMP',
                    'global':scope.get('global_scope') is True}
        if scope.get('subject_id'):
            expected['subject_id'] = scope['subject_id']
        if scope.get('brand_focus_id'):
            expected['brand_focus_id'] = scope['brand_focus_id']
        if (evidence.get('feature_id')!='COLLECTOR_NATIVE_AUTHORS' or signed != expected
                or classify_evidence_integrity(evidence).get('assurance')!='writer-authenticated'):
            raise PermissionError('AUTHOR_SOURCE_NOT_AUTHORIZED')
        ids = inputs.get('source_ids') or []
        if ids:
            visible = _current_inspectable_source_rows(connection,ids,actor=actor,scope=scope)
            if {row['source_id'] for row in visible} != set(ids):
                raise PermissionError('AUTHOR_SOURCE_REMOVED_OR_SCOPE_CHANGED')
            for item in inputs.get('author_observation_records') or []:
                if connection.execute('SELECT 1 FROM platform_accounts WHERE platform=? AND platform_account_id=?',
                        (item['platform'],item['platform_author_id'])).fetchone() is None:
                    raise PermissionError('AUTHOR_SOURCE_REMOVED_OR_SCOPE_CHANGED')
        outputs = json.loads(evidence.get('outputs_json') or '{}')
        return {'ok':evidence.get('result')=='PASS','status':outputs.get('status'),
                'evidence_ref':evidence_ref,'authors':inputs.get('author_observation_records') or [],
                'author_count':outputs.get('author_count'), 'raw_count':outputs.get('raw_count'),
                'error_type':outputs.get('error_type'), 'network_attempted':False,
                'result_freshness':'SAVED_SOURCE_OBSERVATION'}


def collect_author_posts(platform, author_id, *, actor, scope, **kwargs):
    platform = 'xiaohongshu' if platform == 'xhs' else platform
    target = _normalize_author_target(platform,author_id)
    return collect_search(platform,target,actor=actor,scope=scope,capability='author_posts',**kwargs)


def collect_detail(platform: str, content_id: str, *, operator='human', scope=None,
                   actor=None, attempt_guard=None, operation_key=None, native_task_key=None,
                   provider_mode=None,public_transport=None):
    """Exact source read through the existing Permission/Evidence transaction.

    The caller must supply the same actor and Source scope as search. This is
    manual by default; a URL or a resume pointer never supplies permission.
    """
    if platform in {'xhs', 'xiaohongshu'}:
        # This validator reads no configuration or session material.
        from .xhs import validate_xhs_detail_target
        content_id = validate_xhs_detail_target(content_id)
    reference = _credential_free_observations(content_id)
    return collect_search(platform, reference, max_results=1, operator=operator,
        scope=scope, actor=actor, attempt_guard=attempt_guard, operation_key=operation_key,
        capability='detail', _source_url=content_id, native_task_key=native_task_key,
        provider_mode=provider_mode,public_transport=public_transport)


def _comment_parent(connection, source_id, actor, scope):
    """Resolve the existing Canonical post after fresh server scope checks."""
    from canonical_data import list_scoped_canonical
    from lumenis.system.security import (LocalWorkspacePrincipal, get_permission_gate,
        check_actor_scope_permission, check_local_workspace_scope_permission)
    from .platform_naming import normalize_platform
    if not isinstance(source_id, str) or not source_id or not isinstance(scope, Mapping):
        raise ValueError('COMMENT_SOURCE_REQUIRED')
    domain = str(scope.get('domain_id') or '').lower()
    if domain == 'zbmp':
        domain = 'bmp'
    exact = {'domain_id': domain, 'subject_id': scope.get('subject_id'),
             'brand_focus_id': scope.get('brand_focus_id'), 'global_scope': scope.get('global_scope')}
    check = check_local_workspace_scope_permission if type(actor) is LocalWorkspacePrincipal else check_actor_scope_permission
    def authorize(value):
        permission = check(actor, module='collector', action='read', gate=get_permission_gate(),
                           connection=connection, **value)
        if permission.allowed is not True or permission.verification_state != 'verified':
            raise PermissionError('COMMENT_SOURCE_NOT_AUTHORIZED')
    authorize(exact)
    rows = list_scoped_canonical(connection,product_id='CTH' if domain=='cth' else 'ZBMP',
        subject_id=exact['subject_id'],brand_focus_id=exact['brand_focus_id'],source_ids=[source_id],limit=1)['records']
    if not rows and exact['global_scope'] is True:
        rows = [item for item in _current_inspectable_source_rows(connection,[source_id],actor=actor,scope=exact)
                if item['scope_status']=='UNASSIGNED']
    if len(rows) != 1 or rows[0].get('source_table') != 'notes':
        raise LookupError('COMMENT_PARENT_NOT_FOUND')
    row = rows[0]
    actual_scope = {'domain_id': domain, 'subject_id': row.get('subject_id') or None,
                    'brand_focus_id': row.get('brand_focus_id') or None,
                    'global_scope': not bool(row.get('subject_id') or row.get('brand_focus_id'))}
    # A GLOBAL view does not erase the source's own focused permission.
    authorize(actual_scope)
    platform = normalize_platform(row.get('source_platform'))
    if platform not in SECONDARY_COLLECTION_PLATFORMS:
        raise ValueError('COMMENT_PLATFORM_NOT_SUPPORTED')
    parent = {'source_id': source_id, 'canonical_id': row['canonical_id'], 'platform': platform,
              'source_url': _credential_free_observations(row.get('url') or ''),
              'scope_evidence_ref': str(row.get('scope_evidence_ref') or ''), 'scope': actual_scope,
              'body_sha256': hashlib.sha256((row.get('content') or '').encode()).hexdigest()}
    if actual_scope['global_scope']:
        parent['source_observation_evidence_ref'] = str(row.get('evidence_ref') or '')
    parent['fingerprint'] = hashlib.sha256(json.dumps(parent, sort_keys=True,
        separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    return parent


def _comment_page_record(connection, reference, parent, binding):
    from lumenis.shared.evidence.store import classify_evidence_integrity
    if not isinstance(reference, str) or re.fullmatch(r'app_evidence_records:[1-9]\d*', reference) is None:
        raise ValueError('COMMENT_PAGE_RECEIPT_INVALID')
    row = connection.execute('SELECT * FROM app_evidence_records WHERE id=?', (int(reference.split(':')[1]),)).fetchone()
    if row is None or classify_evidence_integrity(dict(row)).get('assurance') != 'writer-authenticated':
        raise PermissionError('COMMENT_PAGE_RECEIPT_UNVERIFIED')
    row = dict(row)
    inputs, outputs = json.loads(row['inputs_json']), json.loads(row['outputs_json'])
    if (row['feature_id'] != 'COLLECTOR_NATIVE_COMMENTS' or inputs.get('parent') != parent
            or inputs.get('binding') != binding):
        raise PermissionError('COMMENT_PAGE_CONTEXT_CHANGED')
    return outputs


def _comment_parent_version(recorded, current):
    """Historical bodies remain readable only under the same current source scope."""
    identity = ('source_id', 'canonical_id', 'platform', 'scope')
    if not isinstance(recorded, dict) or any(recorded.get(key) != current.get(key) for key in identity):
        raise PermissionError('COMMENT_PAGE_CONTEXT_CHANGED')
    return 'CURRENT_SOURCE_VERSION' if recorded == current else 'RECORDED_SOURCE_VERSION'


def _normalized_comment_observations(values, parent, *, include_replies):
    """Keep native IDs/relations; unidentified observations remain explicit."""
    observed, by_id = [], {}
    captured_at = datetime.now().astimezone().isoformat()
    def identity(value):
        return str(value).strip() if type(value) in (str, int) and str(value).strip() else None
    for source in values:
        if not isinstance(source, dict):
            raise ValueError('COMMENT_PROVIDER_SHAPE_INVALID')
        native_parent = identity(source.get('parent_content_id'))
        if native_parent and native_parent != parent['source_id']:
            raise ValueError('COMMENT_PARENT_IDENTITY_MISMATCH')
        native_id = identity(source.get('platform_comment_id', source.get('comment_id', source.get('id'))))
        parent_id = identity(source.get('parent_comment_id', source.get('parent_id')))
        if parent_id in ('0', ''):
            parent_id = None
        likes = source.get('likes')
        likes = likes if type(likes) is int and likes >= 0 else None
        record = {'platform_comment_id': native_id, 'parent_comment_id': parent_id,
            'reply_to_comment_id': identity(source.get('reply_to_comment_id')),
            'parent_content_id': parent['source_id'], 'platform': parent['platform'],
            'content': source.get('content') if isinstance(source.get('content'), str) else '',
            'author_id': identity(source.get('author_id')),
            'author_nickname': source.get('author_nickname', source.get('author', source.get('user'))),
            'publish_datetime': source.get('publish_datetime', source.get('publish_time')),
            'likes': likes, 'url': _credential_free_observations(source.get('url') or ''),
            'captured_at': captured_at,
            'identity_state': 'NATIVE_ID_OBSERVED' if native_id else 'NATIVE_ID_NOT_OBSERVED',
            'raw': _credential_free_observations(source.get('raw', source))}
        if native_id and native_id in by_id:
            if by_id[native_id] != record:
                raise ValueError('COMMENT_PAGE_NATIVE_ID_CONFLICT')
            continue
        if native_id:
            by_id[native_id] = record
        observed.append(record)
    return observed


def _comment_page_body(observations):
    parts, segments, offset = [], [], 0
    for index, observation in enumerate(observations):
        content = observation['content']
        if index:
            parts.append('\n\n')
            offset += 2
        segments.append({'comment_index': index, 'start': offset, 'end': offset + len(content),
            'platform_comment_id': observation['platform_comment_id'],
            'parent_comment_id': observation['parent_comment_id'],
            'author_id': observation['author_id']})
        parts.append(content)
        offset += len(content)
    return ''.join(parts), segments


def _comment_page_original_document(parent, observations, pagination, context, binding):
    body, segments = _comment_page_body(observations)
    return {'schema': 'collector-native-comment-page/1', 'parent': parent,
        'parent_source_id': parent['source_id'], 'platform': parent['platform'],
        'observations': observations, 'body': body,
        'body_sha256': hashlib.sha256(body.encode('utf-8')).hexdigest(), 'body_segments': segments,
        'representation': 'COLLECTOR_PARSED_OBSERVATIONS_NOT_FULL_PROVIDER_RESPONSE',
        'pagination': _credential_free_observations(pagination),
        'rights': {'status': 'UNREVIEWED', 'allowed_uses': [], 'third_party_rights_granted': False},
        'claim_type': 'PLATFORM_USER_STATEMENTS_NOT_INDEPENDENTLY_VERIFIED',
        'context': context, 'request_binding': binding}


def _preserve_comment_page_original(connection, *, actor, parent, observations, pagination, binding, staged_paths):
    """Preserve this exact observed page in the existing Artifact owner.

    It is the Collector's parsed observation, not a complete provider response.
    Source preservation does not grant any use of another author's expression.
    A non-critical original-file failure remains explicit beside primary intake.
    """
    from lumenis.shared.reporting.saved_work import authorize, _stage_bytes, staging_write
    start = len(staged_paths)
    prepared = {}
    connection.execute('SAVEPOINT comment_original_source')
    try:
        context = authorize(actor, parent['scope'], action='write', connection=connection)
        document = _comment_page_original_document(parent, observations, pagination, context, binding)
        raw = json.dumps(document, sort_keys=True, ensure_ascii=False,
                         separators=(',', ':'), allow_nan=False).encode('utf-8')
        digest = hashlib.sha256(raw).hexdigest()
        prepared = {'source_fingerprint': digest, 'body_sha256': document['body_sha256'],
            'size_bytes': len(raw), 'context': context, 'source_kind': 'collected_comment_page',
            'representation': document['representation'], 'rights': document['rights'],
            'pagination': document['pagination']}
        with staging_write('collector-comment-page:' + digest):
            artifact, path = _stage_bytes(connection, raw=raw, context=context, kind='collected_source',
                source_execution_id='comment-page-pending:' + digest, extension='.json', media_type='application/json')
        staged_paths.append(path)
        connection.execute('RELEASE SAVEPOINT comment_original_source')
        return {**prepared, 'status': 'PRESERVED', 'source_artifact_ref': artifact['artifact_id']}
    except Exception:
        connection.execute('ROLLBACK TO SAVEPOINT comment_original_source')
        connection.execute('RELEASE SAVEPOINT comment_original_source')
        cleaned = _cleanup_collected_source_paths(staged_paths[start:])
        del staged_paths[start:]
        return {**prepared, 'status': 'UNAVAILABLE', 'source_artifact_ref': None,
                'reason': 'COMMENT_ORIGINAL_ARTIFACT_PRESERVATION_UNAVAILABLE',
                'cleanup_status': 'COMPLETE' if cleaned else 'FAILED',
                'source_use': 'NOT_GRANTED'}


def validate_comment_page_original(evidence, raw, artifact):
    """Pure Producer validation for the original Shared SourceUse reader."""
    from lumenis.shared.evidence.store import classify_evidence_integrity
    if (not isinstance(evidence, Mapping) or not isinstance(artifact, Mapping) or not isinstance(raw, bytes)
            or not 0 < len(raw) <= 8 * 1024 * 1024
            or classify_evidence_integrity(dict(evidence)).get('assurance') != 'writer-authenticated'
            or evidence.get('source') != 'collector' or evidence.get('feature_id') != 'COLLECTOR_NATIVE_COMMENTS'
            or evidence.get('version') != 'collector-native-comments/2'):
        raise ValueError('COMMENT_ORIGINAL_PRODUCER_INVALID')
    try:
        inputs = json.loads(evidence['inputs_json'])
        outputs = json.loads(evidence['outputs_json'])
        metadata = json.loads(evidence['collection_metadata'])
        document = json.loads(raw)
    except (KeyError, ValueError, TypeError, UnicodeError) as exc:
        raise ValueError('COMMENT_ORIGINAL_PRODUCER_INVALID') from exc
    if (not all(isinstance(value, dict) for value in (inputs, outputs, metadata, document))
            or not isinstance(outputs.get('result'), dict) or not isinstance(inputs.get('parent'), dict)
            or not isinstance(document.get('observations'), list)):
        raise ValueError('COMMENT_ORIGINAL_PRODUCER_INVALID')
    original = outputs['result'].get('original_source') or {}
    identity = 'comment-page:' + str(evidence['id'])
    digest = hashlib.sha256(raw).hexdigest()
    preserved = (original.get('status') == 'PRESERVED'
        and metadata.get('source_artifact_ref') == original.get('source_artifact_ref') == artifact.get('artifact_id'))
    recovered = (original.get('status') == 'UNAVAILABLE'
        and original.get('reason') == 'COMMENT_ORIGINAL_ARTIFACT_PRESERVATION_UNAVAILABLE'
        and original.get('source_artifact_ref') is None and metadata.get('source_artifact_ref') is None)
    if (metadata.get('source_kind') != 'collected_comment_page' or not (preserved or recovered)
            or artifact.get('kind') != 'collected_source' or artifact.get('source_execution_id') != identity
            or artifact.get('evidence_id') != str(evidence['id']) or artifact.get('note_id') != evidence['asset_id']
            or artifact.get('sha256') != digest or metadata.get('source_fingerprint') != digest
            or original.get('source_fingerprint') != digest or artifact.get('size_bytes') != len(raw)
            or artifact.get('product_id') != evidence.get('product_id') or artifact.get('domain_id') != evidence.get('domain_id')
            or document.get('schema') != 'collector-native-comment-page/1'
            or document.get('parent') != inputs.get('parent')
            or document.get('parent_source_id') != evidence.get('asset_id')
            or document.get('platform') != inputs['parent']['platform']
            or document.get('request_binding') != inputs.get('binding')
            or document.get('observations') != outputs['result'].get('comments')
            or document.get('context') != metadata.get('context')
            or document.get('rights') != {'status': 'UNREVIEWED', 'allowed_uses': [], 'third_party_rights_granted': False}
            or document.get('representation') != 'COLLECTOR_PARSED_OBSERVATIONS_NOT_FULL_PROVIDER_RESPONSE'):
        raise ValueError('COMMENT_ORIGINAL_BINDING_INVALID')
    body, segments = _comment_page_body(document['observations'])
    if (document.get('body') != body or document.get('body_segments') != segments
            or document.get('body_sha256') != hashlib.sha256(body.encode('utf-8')).hexdigest()
            or original.get('body_sha256') != document['body_sha256']):
        raise ValueError('COMMENT_ORIGINAL_BODY_CHANGED')
    return document


def read_comment_page_original(page_ref, *, actor, scope, connection=None):
    """Reopen exact bytes after current parent-scope checks; grants no SourceUse."""
    import database as db
    import shared_artifacts
    from lumenis.shared.evidence.store import classify_evidence_integrity
    if not isinstance(page_ref, str) or re.fullmatch(r'app_evidence_records:[1-9]\d*', page_ref) is None:
        raise ValueError('COMMENT_PAGE_RECEIPT_INVALID')
    with (nullcontext(connection) if connection is not None else db.get_db()) as con:
        row = con.execute('SELECT * FROM app_evidence_records WHERE id=?', (int(page_ref.split(':')[1]),)).fetchone()
        if row is None or classify_evidence_integrity(dict(row)).get('assurance') != 'writer-authenticated':
            raise PermissionError('COMMENT_PAGE_RECEIPT_UNVERIFIED')
        evidence = dict(row)
        if (evidence.get('source') != 'collector' or evidence.get('feature_id') != 'COLLECTOR_NATIVE_COMMENTS'
                or evidence.get('version') != 'collector-native-comments/2'):
            raise ValueError('COMMENT_ORIGINAL_PRODUCER_INVALID')
        inputs = json.loads(evidence['inputs_json'])
        parent = _comment_parent(con, evidence['asset_id'], actor, scope)
        version_state = _comment_parent_version(inputs.get('parent'), parent)
        metadata = json.loads(evidence['collection_metadata'])
        if metadata.get('source_artifact_ref'):
            artifact_rows = con.execute('SELECT * FROM lumenis_shared_artifacts WHERE artifact_id=?',
                                       (metadata['source_artifact_ref'],)).fetchall()
        else:
            artifact_rows = con.execute('SELECT * FROM lumenis_shared_artifacts WHERE kind=? AND evidence_id=? '
                'AND source_execution_id=? AND note_id=? AND sha256=?', ('collected_source', str(evidence['id']),
                'comment-page:' + str(evidence['id']), evidence['asset_id'], metadata.get('source_fingerprint'))).fetchall()
        if not artifact_rows:
            raise LookupError('COMMENT_ORIGINAL_ARTIFACT_UNAVAILABLE')
        if len(artifact_rows) != 1:
            raise ValueError('COMMENT_ORIGINAL_ARTIFACT_AMBIGUOUS')
        artifact = dict(artifact_rows[0])
        root = shared_artifacts.artifact_root().resolve()
        path = (root / artifact['relative_path']).resolve()
        if not path.is_relative_to(root) or not path.is_file() or not 0 < artifact['size_bytes'] <= 8 * 1024 * 1024:
            raise ValueError('COMMENT_ORIGINAL_ARTIFACT_INVALID')
        with path.open('rb') as handle:
            raw = handle.read(8 * 1024 * 1024 + 1)
        document = validate_comment_page_original(evidence, raw, artifact)
        return {'source_id': 'comment-page:' + str(evidence['id']), 'parent_source_id': evidence['asset_id'],
                'evidence_ref': page_ref, 'evidence': evidence, 'source_artifact': artifact,
                'raw': raw, 'sha256': artifact['sha256'], 'document': document,
                'source_fingerprint': artifact['sha256'], 'body_sha256': document['body_sha256'],
                'source_version': evidence['version'], 'rights': document['rights'],
                'source_version_state': version_state, 'source_use': 'CHECK_CURRENT_COMMENT_PAGE_USE'}


def recover_comment_page_original(page_ref, *, actor, scope):
    """Explicit storage-only recovery from signed observations, without refetch.

    A committed failed original-file write keeps its historical Evidence. Only
    the exact already-signed fingerprint can be registered in the Artifact owner.
    Current Collector import approval, source scope and staging fences still apply.
    """
    import database as db
    from lumenis.shared.evidence.store import classify_evidence_integrity
    from lumenis.shared.reporting.saved_work import authorize, _stage_bytes, staging_write
    paths = []
    try:
        with db.get_db() as con:
            con.execute('BEGIN IMMEDIATE')
            try:
                current = read_comment_page_original(page_ref, actor=actor, scope=scope, connection=con)
            except LookupError:
                current = None
            if current is not None:
                return {**current, 'replayed': True, 'network_attempted': False, 'evidence_rewritten': False}
            row = con.execute('SELECT * FROM app_evidence_records WHERE id=?', (int(page_ref.split(':')[1]),)).fetchone()
            if row is None or classify_evidence_integrity(dict(row)).get('assurance') != 'writer-authenticated':
                raise PermissionError('COMMENT_PAGE_RECEIPT_UNVERIFIED')
            evidence = dict(row)
            inputs, outputs = json.loads(row['inputs_json']), json.loads(row['outputs_json'])
            original = outputs['result'].get('original_source') or {}
            if (evidence['version'] != 'collector-native-comments/2' or evidence['feature_id'] != 'COLLECTOR_NATIVE_COMMENTS'
                    or original.get('status') != 'UNAVAILABLE' or not original.get('source_fingerprint')
                    or not isinstance(original.get('context'), dict) or not isinstance(original.get('pagination'), dict)):
                raise ValueError('COMMENT_ORIGINAL_NOT_RECOVERABLE')
            parent = _comment_parent(con, evidence['asset_id'], actor, scope)
            _comment_parent_version(inputs.get('parent'), parent)
            binding = inputs['binding']
            exact, denial = _manual_collection_guard(actor, parent['scope'], parent['platform'],
                binding['keyword'], binding['max_results'], capability='comments',**binding.get('provider_selection',{}))
            if denial is not None:
                raise PermissionError('COMMENT_ORIGINAL_RECOVERY_APPROVAL_REQUIRED')
            authorized = _task_commit_binding(binding['operation_key'], actor, exact, 'human', None,
                parent['platform'], binding['keyword'], binding['max_results'], None)
            if authorized['identity'] != binding['identity']:
                raise PermissionError('COMMENT_ORIGINAL_RECOVERY_ACTOR_CHANGED')
            authorize(actor, parent['scope'], action='write', connection=con)
            document = _comment_page_original_document(inputs['parent'], outputs['result']['comments'],
                original['pagination'], original['context'], binding)
            raw = json.dumps(document, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':'), allow_nan=False).encode('utf-8')
            if hashlib.sha256(raw).hexdigest() != original['source_fingerprint']:
                raise ValueError('COMMENT_ORIGINAL_RECOVERY_BYTES_CHANGED')
            identity = 'comment-page:' + str(evidence['id'])
            with staging_write('collector-comment-original-recovery:' + original['source_fingerprint']):
                artifact, path = _stage_bytes(con, raw=raw, context=original['context'], kind='collected_source',
                    source_execution_id=identity, evidence_id=str(evidence['id']), extension='.json', media_type='application/json')
            paths.append(path)
            con.execute('UPDATE lumenis_shared_artifacts SET note_id=? WHERE artifact_id=?',
                        (evidence['asset_id'], artifact['artifact_id']))
            result = read_comment_page_original(page_ref, actor=actor, scope=scope, connection=con)
        return {**result, 'replayed': False, 'network_attempted': False, 'evidence_rewritten': False}
    except BaseException:
        _cleanup_collected_source_paths(paths)
        raise


def collect_comments(source_id: str, *, actor, scope, request_id: str, max_results=20,
                     include_replies=False, continuation=None, attempt_guard=None,
                     provider_mode=None,public_transport=None):
    """One explicit page through existing adapters, Evidence and note_comments.

    Clients echo a signed page reference, never a platform cursor or actor/scope
    grant. Each next page rechecks the source and exact import approval. The
    signed transaction receipt recovers a committed page without refetching.
    """
    import database as db
    from lumenis.shared.evidence.store import record_evidence
    if (type(max_results) is not int or not 1 <= max_results <= MAX_RESULTS
            or type(include_replies) is not bool or not isinstance(request_id, str)
            or re.fullmatch(r'[A-Za-z0-9_-]{8,128}', request_id) is None):
        raise ValueError('COMMENT_REQUEST_INVALID')
    if continuation is not None and (not isinstance(continuation, dict) or set(continuation) != {'page_ref'}):
        raise ValueError('COMMENT_PAGE_RECEIPT_REQUIRED')
    with db.get_db() as connection:
        parent = _comment_parent(connection, source_id, actor, scope)
    platform = parent['platform']
    selection = normalize_provider_selection(platform,provider_mode=provider_mode,public_transport=public_transport)
    keyword = json.dumps({'capability': 'comments', 'source_id': source_id,
        'source_url': parent['source_url'], 'include_replies': include_replies}, sort_keys=True, ensure_ascii=False)
    exact, denial = _manual_collection_guard(actor, parent['scope'], platform, keyword, max_results, capability='comments',**selection)
    if denial is not None:
        return denial
    binding = _task_commit_binding('comments:' + request_id, actor, exact, 'human', None,
                                   platform, keyword, max_results, None)
    binding.update(capability='comments', parent_fingerprint=parent['fingerprint'], include_replies=include_replies)
    if selection:
        binding['provider_selection'] = selection
    previous = continuation['page_ref'] if continuation else None
    cursor, chain = None, []
    with db.get_db() as connection:
        if previous:
            prior = _comment_page_record(connection, previous, parent, binding)
            if not prior.get('retry_current_cursor') and (prior.get('exhausted') is True or prior.get('next_cursor') is None):
                return {**prior['result'], 'cached': True, 'network_attempted': False,
                        'page_ref': previous, 'evidence_ref': int(previous.split(':')[1]),
                        'continuation': None, 'coverage_state': prior['result']['coverage_state']}
            cursor, chain = prior['next_cursor'], list(prior.get('cursor_chain') or [])
        page_binding = {**binding, 'previous_page_ref': previous, 'request_cursor': cursor}
        cached = _task_commit_receipt(connection, page_binding)
        if cached is not None:
            return cached
    cursor_hash = hashlib.sha256(json.dumps(cursor, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if cursor_hash in chain:
        return {'ok': False, 'status': 'NATIVE_CURSOR_LOOP', 'network_attempted': False,
                'source_id': source_id, 'continuation': None, 'coverage_state': 'PARTIAL'}
    if not _locks[platform].acquire(blocking=False):
        return {'ok': False, 'status': 'BUSY', 'network_attempted': False, 'source_id': source_id}
    staged_paths = []
    try:
        with _last_action_lock:
            elapsed = time.monotonic() - _last_action[platform]
            if _last_action[platform] and elapsed < MIN_INTERVAL_SECONDS:
                return {'ok': False, 'status': 'RATE_LIMITED', 'network_attempted': False,
                        'retry_after_seconds': MIN_INTERVAL_SECONDS - elapsed, 'source_id': source_id}
            _last_action[platform] = time.monotonic()
        health = _adapter_health(platform,**selection)
        if health.get('can_attempt', health.get('ready')) is not True:
            return {'ok': False, 'status': health.get('status', 'UNAVAILABLE'),
                    'network_attempted': False, 'source_id': source_id}
        options = {'max_comments': max_results, 'include_replies': include_replies,
                   'source_url': parent['source_url'],**selection}
        if cursor is not None:
            options['cursor'] = cursor
        target = parent['source_url'] if platform == 'xiaohongshu' else source_id
        try:
            collection = _get_runtime_adapter(platform).comments(target, **options)
        except Exception as exc:
            collection = CollectionResult(CollectionStatus.PROVIDER_UNAVAILABLE, platform,
                message='comment provider request failed', metadata={'error_type': type(exc).__name__})
        if not isinstance(collection, CollectionResult):
            raise ValueError('COMMENT_PROVIDER_SHAPE_INVALID')
        bind_collection_route(collection, platform=platform, capability='comments', request_value=target,**selection)
        provider_comments = collection.comments if isinstance(collection.comments, list) else []
        provider_returned_count = len(provider_comments)
        provider_limit_exceeded = provider_returned_count > max_results
        if provider_limit_exceeded:
            metadata = dict(collection.metadata) if isinstance(collection.metadata, dict) else {}
            rejected_pagination = metadata.get('pagination')
            rejected_pagination = (_credential_free_observations(rejected_pagination)
                                   if isinstance(rejected_pagination, dict) else {})
            request_cursor = rejected_pagination.get('request_cursor')
            metadata['error_type'] = 'PROVIDER_RESULT_LIMIT_EXCEEDED'
            metadata['result_limit_validation'] = {
                'requested_limit': max_results,
                'provider_returned_count': provider_returned_count,
                'rejected_pagination': rejected_pagination,
            }
            # Retain only the cursor-consumption fact needed for this call.
            # The rejected response's next cursor is diagnostic and cannot
            # resume a page whose observations were not admitted.
            metadata['pagination'] = {
                'request_cursor': request_cursor,
                'next_cursor': None,
                'exhausted': None,
                'page_complete': False,
                'replies_complete': None,
                'partial_reason': 'PROVIDER_RESULT_LIMIT_EXCEEDED',
            }
            collection.metadata = metadata
            collection.status = CollectionStatus.COLLECT_ERROR
            collection.message = 'provider returned more comments than the approved request limit'
            collection.comments = []
        observations = _normalized_comment_observations(collection.comments, parent, include_replies=include_replies)
        metadata = collection.metadata if isinstance(collection.metadata, dict) else {}
        pagination = metadata.get('pagination') if isinstance(metadata.get('pagination'), dict) else {}
        observed_cursor = pagination.get('request_cursor')
        if cursor is not None and observed_cursor != cursor:
            raise ValueError('COMMENT_PROVIDER_CURSOR_NOT_CONSUMED')
        exhausted = pagination.get('exhausted') if type(pagination.get('exhausted')) is bool else None
        next_cursor = pagination.get('next_cursor')
        if next_cursor is not None and type(next_cursor) not in (str, int, dict):
            raise ValueError('COMMENT_PROVIDER_CURSOR_INVALID')
        if len(json.dumps(next_cursor, allow_nan=False).encode()) > 16384:
            raise ValueError('COMMENT_PROVIDER_CURSOR_INVALID')
        retry_current = (not provider_limit_exceeded
                         and (not collection.ok or pagination.get('page_complete') is False))
        chain = chain if retry_current else [*chain, cursor_hash]
        if retry_current:
            next_cursor = cursor
        if not retry_current and next_cursor is not None and hashlib.sha256(json.dumps(next_cursor, sort_keys=True,
                separators=(',', ':')).encode()).hexdigest() in chain:
            next_cursor, exhausted = None, False
            pagination = {**pagination, 'partial_reason': 'NATIVE_CURSOR_LOOP'}
        status = _canonical_status(collection)
        replies_complete = pagination.get('replies_complete')
        collection_metadata = collection.metadata if isinstance(collection.metadata, dict) else {}
        declared_reply_scope = pagination.get('reply_scope') or collection_metadata.get('reply_scope')
        # Some adapters declare their reply scope at the provider level while
        # keeping pagination in a separate field. Promote only explicit scopes
        # whose own adapter contract says the complete provider-visible tree
        # was traversed; visible-DOM scopes remain unknown.
        if (include_replies and type(replies_complete) is not bool and exhausted is True
                and (declared_reply_scope == 'ALL_API_VISIBLE_REPLIES'
                     or (declared_reply_scope == 'NESTED'
                         and collection_metadata.get('comment_coverage') == 'API_VISIBLE_TREE_ONLY'))):
            replies_complete = True
        reply_coverage_state = ('NOT_REQUESTED' if not include_replies else
            'COMPLETE_FOR_PROVIDER_SCOPE' if replies_complete is True else
            'INCOMPLETE' if replies_complete is False else 'UNKNOWN')
        complete = (collection.ok and exhausted is True and pagination.get('page_complete') is not False
                    and (not include_replies or replies_complete is True))
        partial_reason = pagination.get('partial_reason')
        if (collection.ok and pagination.get('page_complete') is False and not partial_reason):
            partial_reason = 'PAGE_COMPLETION_NOT_ESTABLISHED'
        elif (collection.ok and exhausted is True and include_replies and replies_complete is not True
                and not partial_reason):
            partial_reason = ('REPLY_PAGES_PENDING' if replies_complete is False
                              else 'REPLY_COVERAGE_NOT_ESTABLISHED')
        result = {'ok': bool(collection.ok), 'status': 'SUCCESS' if complete else
                    'COMMENTS_PARTIAL' if collection.ok else status,
            'provider_status': status, 'source_id': source_id, 'platform': platform,
            'comments': observations, 'observed_count': (provider_returned_count if provider_limit_exceeded
                else len(observations) if collection.ok or observations else None),
            'native_identity_count': (sum(bool(item['platform_comment_id']) for item in observations)
                                      if collection.ok or observations else None),
            'coverage_state': 'COMPLETE_FOR_DECLARED_SCOPE' if complete else 'PARTIAL',
            'coverage_scope': pagination.get('coverage_scope', 'PROVIDER_RETURNED_OBSERVATIONS_ONLY'),
            'requested_reply_scope': 'INCLUDE_REPLIES' if include_replies else 'TOP_LEVEL_ONLY',
            'reply_coverage_state': reply_coverage_state,
            'replies_complete': replies_complete if include_replies else None,
            'partial_reason': partial_reason or (None if complete else 'COVERAGE_NOT_ESTABLISHED'),
            'read_only': True, 'external_write': False, 'network_attempted': True,
            'continuation': None, 'pagination_exhausted': exhausted,
            'recovery_required': retry_current,
            'refresh_verified': bool(collection.ok), 'cached': False}
        if provider_limit_exceeded:
            result.update(error_type='PROVIDER_RESULT_LIMIT_EXCEEDED',
                requested_result_limit=max_results, provider_returned_count=provider_returned_count,
                new_collection_required=True, retry_safe=False, recovery_required=False)
            result['partial_reason'] = 'PROVIDER_RESULT_LIMIT_EXCEEDED'
        result['source_use'] = {'purpose': 'COLLECTION_INSPECTION', 'source_scope_checked': True,
            'source_rights_promoted': False, 'analysis_export_training': 'CHECK_EXISTING_SOURCE_USE_PER_ACTION'}
        # Observed bodies are retained even on an interrupted provider page;
        # only a successful page receives the terminal replay receipt.
        with (attempt_guard() if attempt_guard is not None else nullcontext(True)) as active, db.get_db() as connection:
            if active is not True:
                raise PermissionError('COMMENT_ATTEMPT_SUPERSEDED')
            connection.execute('BEGIN IMMEDIATE')
            if _comment_parent(connection, source_id, actor, scope) != parent:
                raise PermissionError('COMMENT_PARENT_CHANGED')
            _, denial = _manual_collection_guard(actor, exact, platform, keyword, max_results, capability='comments',**selection)
            if denial is not None:
                raise PermissionError('COMMENT_APPROVAL_REVOKED')
            repeated = _task_commit_receipt(connection, page_binding)
            if repeated is not None:
                return repeated
            original = (_preserve_comment_page_original(connection, actor=actor, parent=parent,
                observations=observations, pagination=pagination, binding=binding, staged_paths=staged_paths)
                if collection.ok or observations else {'status': 'UNAVAILABLE', 'source_artifact_ref': None,
                    'reason': 'NO_SOURCE_OBSERVATIONS', 'source_use': 'NOT_GRANTED'})
            result['original_source'] = original
            page_ref = record_evidence(connection=connection, source='collector', feature_id='COLLECTOR_NATIVE_COMMENTS',
                version='collector-native-comments/2', asset_id=source_id, status='verified' if collection.ok else 'failed',
                result='PASS' if collection.ok else 'FAIL', capture_mode='native_comments',
                product='CTH' if exact['domain_id'] == 'cth' else 'ZBMP',
                domain_id='cth' if exact['domain_id'] == 'cth' else 'zbmp', subject_id=exact['subject_id'],
                brand_focus_id=exact['brand_focus_id'], global_scope=exact['global_scope'],
                inputs={'binding': binding, 'parent': parent, 'previous_page_ref': previous, 'request_cursor': cursor},
                outputs={'result': result, 'next_cursor': next_cursor, 'exhausted': exhausted,
                         'retry_current_cursor': retry_current, 'cursor_chain': chain},
                collection_metadata={'capability': 'comments', 'source_platform': platform,
                                     'source_url': parent['source_url'], 'includes_replies': include_replies,
                                     **{key: original[key] for key in ('source_artifact_ref', 'source_fingerprint',
                                        'body_sha256', 'context', 'source_kind') if key in original}})
            if original.get('status') == 'PRESERVED':
                connection.execute('UPDATE lumenis_shared_artifacts SET evidence_id=?,source_execution_id=?,note_id=? WHERE artifact_id=?',
                    (str(page_ref), 'comment-page:' + str(page_ref), source_id, original['source_artifact_ref']))
            stored = []
            for observation in observations:
                native_id = observation['platform_comment_id']
                if not native_id:
                    continue
                key = 'comment:' + hashlib.sha256(json.dumps([platform, source_id, native_id],
                    separators=(',', ':')).encode()).hexdigest()
                legacy = connection.execute('SELECT note_id FROM note_comments WHERE comment_id=?', (native_id,)).fetchone()
                if legacy is not None and legacy[0] == source_id:
                    key = native_id
                stored.append({**observation, 'comment_id': key, 'raw_data': {**observation,
                    'collection_evidence_ref': 'app_evidence_records:' + str(page_ref)}})
            result['persistence'] = db.upsert_note_comments(source_id, stored, connection=connection)
            result['persistence']['unidentified'] = len(observations) - len(stored)
            result['evidence_ref'] = page_ref
            result['page_ref'] = 'app_evidence_records:' + str(page_ref)
            if retry_current or (next_cursor is not None and not exhausted):
                result['continuation'] = {'page_ref': result['page_ref']}
            if collection.ok:
                _task_commit_receipt(connection, page_binding, result)
            return result
    except BaseException:
        _cleanup_collected_source_paths(staged_paths)
        raise
    finally:
        _locks[platform].release()


def read_collected_comments(source_id: str, *, actor, scope, limit=20, before=None, page_ref=None):
    """Read the existing latest projection or one immutable native page."""
    import database as db
    from lumenis.shared.evidence.store import classify_evidence_integrity
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('COMMENT_READ_LIMIT_INVALID')
    if page_ref is not None and before is not None:
        raise ValueError('COMMENT_READ_CURSOR_INVALID')
    with db.get_db() as connection:
        parent = _comment_parent(connection, source_id, actor, scope)
        if page_ref is not None:
            if not isinstance(page_ref, str) or re.fullmatch(r'app_evidence_records:[1-9]\d*', page_ref) is None:
                raise ValueError('COMMENT_PAGE_RECEIPT_INVALID')
            row = connection.execute('SELECT * FROM app_evidence_records WHERE id=?', (int(page_ref.split(':')[1]),)).fetchone()
            if row is None or classify_evidence_integrity(dict(row)).get('assurance') != 'writer-authenticated':
                raise PermissionError('COMMENT_PAGE_RECEIPT_UNVERIFIED')
            inputs, outputs = json.loads(row['inputs_json']), json.loads(row['outputs_json'])
            if row['feature_id'] != 'COLLECTOR_NATIVE_COMMENTS' or row['asset_id'] != source_id:
                raise PermissionError('COMMENT_PAGE_CONTEXT_CHANGED')
            version_state = _comment_parent_version(inputs.get('parent'), parent)
            page_result = outputs['result']
            return {'source_id': source_id, 'comments': page_result['comments'], 'page_ref': page_ref,
                    'coverage_state': page_result['coverage_state'], 'immutable': True,
                    'status': page_result.get('status'), 'error_type': page_result.get('error_type'),
                    'observed_count': page_result.get('observed_count'),
                    'requested_result_limit': page_result.get('requested_result_limit'),
                    'provider_returned_count': page_result.get('provider_returned_count'),
                    'requested_reply_scope': page_result.get('requested_reply_scope'),
                    'reply_coverage_state': page_result.get('reply_coverage_state'),
                    'replies_complete': page_result.get('replies_complete'),
                    'partial_reason': page_result.get('partial_reason'),
                    'source_version_state': version_state, 'source_use': outputs['result'].get('source_use')}
        params = [source_id]
        predicate = 'note_id=?'
        if before is not None:
            if not isinstance(before, str) or not connection.execute('SELECT 1 FROM note_comments WHERE note_id=? AND comment_id=?',
                    (source_id, before)).fetchone():
                raise ValueError('COMMENT_READ_CURSOR_INVALID')
            predicate += ' AND comment_id<?'
            params.append(before)
        rows = connection.execute('SELECT comment_id,raw_json FROM note_comments WHERE ' + predicate
                                  + ' ORDER BY comment_id DESC LIMIT ?', (*params, limit + 1)).fetchall()
        comments = []
        for row in rows[:limit]:
            try:
                observation = json.loads(row['raw_json'])
            except (ValueError, TypeError):
                observation = {}
            if not isinstance(observation, dict):
                observation = {}
            reference = observation.get('collection_evidence_ref')
            if not reference:
                comments.append({'comment_ref': row['comment_id'], 'state': 'LEGACY_COMMENT_NOT_VERIFIED'})
                continue
            if not isinstance(reference, str) or re.fullmatch(r'app_evidence_records:[1-9]\d*', reference) is None:
                raise PermissionError('COMMENT_OBSERVATION_UNVERIFIED')
            evidence = connection.execute('SELECT * FROM app_evidence_records WHERE id=?', (int(reference.split(':')[1]),)).fetchone()
            if (evidence is None or evidence['feature_id'] != 'COLLECTOR_NATIVE_COMMENTS'
                    or evidence['asset_id'] != source_id
                    or classify_evidence_integrity(dict(evidence)).get('assurance') != 'writer-authenticated'):
                raise PermissionError('COMMENT_OBSERVATION_UNVERIFIED')
            original = json.loads(evidence['outputs_json'])['result']['comments']
            public = {key: value for key, value in observation.items() if key != 'collection_evidence_ref'}
            version_state = _comment_parent_version(json.loads(evidence['inputs_json']).get('parent'), parent)
            if public not in original:
                raise PermissionError('COMMENT_OBSERVATION_CHANGED')
            comments.append({**public, 'comment_ref': row['comment_id'], 'evidence_ref': reference,
                             'source_version_state': version_state})
        return {'source_id': source_id, 'platform': parent['platform'], 'comments': comments,
                'next_cursor': rows[limit - 1]['comment_id'] if len(rows) > limit else None,
                'coverage_state': 'SAVED_OBSERVATIONS_NOT_PLATFORM_TOTAL', 'immutable': False}


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


def _requested_publication_window_reviews(records, *, platform,
                                          publication_since=None, publication_until=None):
    """Apply a durable source request's explicit window to native publication time.

    Current registered search adapters do not share a native date-filter
    contract. Keep the exact request bound in permission and task receipts, then
    review fetched observations before Canonical import. Missing or imprecise
    native time stays review-only; capture time never substitutes for it.
    """
    from datetime import date, datetime
    from ..acquisition_plan import (
        _outside_publication_period, _validate_publication_period,
    )
    from .multi_platform_import import _normalize_source_publication
    from .platform_naming import get_platform_fields, normalize_content_id, normalize_platform

    start, end = _validate_publication_period(publication_since, publication_until)
    canonical = normalize_platform(platform)
    spec = get_platform_fields(canonical)
    reviews = []
    for index, record in enumerate(records):
        native = record.get(spec.published_at) if spec else None
        if native in (None, ''):
            native = record.get('publish_datetime')
        literal = native if isinstance(native, (str, int, float)) and not isinstance(native, bool) else None
        if isinstance(literal, str):
            literal = literal[:160]
        normalized = _normalize_source_publication(native, canonical)
        publication = None
        if normalized:
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}', normalized):
                try:
                    publication = date.fromisoformat(normalized)
                except ValueError:
                    publication = None
            else:
                try:
                    parsed = datetime.fromisoformat(normalized.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        from email.utils import parsedate_to_datetime
                        parsed = parsedate_to_datetime(normalized)
                    except (TypeError, ValueError, OverflowError):
                        parsed = None
                if (isinstance(parsed, datetime) and parsed.tzinfo is not None
                        and parsed.utcoffset() is not None):
                    publication = parsed

        source_id = (normalize_content_id(canonical, record.get(spec.content_id) if spec else None)
                     or normalize_content_id(canonical, record.get('content_id')))
        base = {
            'observation_index': index,
            'platform_content_id': str(source_id) if source_id else None,
            'source_url': _credential_free_observations(record.get('url')),
            'native_publication_literal': literal,
            'native_publication_normalized': normalized or None,
            'publication_since': publication_since,
            'publication_until': publication_until,
            'derivative': True,
        }
        if publication is None:
            reviews.append({**base, 'within_publication_window': None,
                            'status': 'REVIEW_REQUIRED_NATIVE_PUBLICATION_TIME_UNKNOWN',
                            'reason': 'NATIVE_PUBLICATION_TIME_OR_OFFSET_UNVERIFIED'})
            continue
        if isinstance(publication, date) and not isinstance(publication, datetime):
            if any(isinstance(boundary, datetime) for boundary in (start, end) if boundary is not None):
                reviews.append({**base, 'within_publication_window': None,
                                'status': 'REVIEW_REQUIRED_PUBLICATION_PRECISION',
                                'reason': 'DATE_ONLY_SOURCE_CANNOT_PROVE_INSTANT_BOUNDARY'})
                continue
            outside = ((start is not None and publication < start)
                       or (end is not None and publication > end))
        else:
            outside = _outside_publication_period(publication, start, end)
        if outside:
            reviews.append({**base, 'within_publication_window': False,
                            'status': 'OUTSIDE_REQUESTED_PUBLICATION_PERIOD',
                            'reason': 'NATIVE_PUBLICATION_OUTSIDE_EXPLICIT_REQUEST_WINDOW'})
            continue

        captured_raw = record.get('captured_at')
        if isinstance(captured_raw, str) and isinstance(publication, datetime):
            try:
                captured = datetime.fromisoformat(captured_raw.replace('Z', '+00:00'))
            except ValueError:
                captured = None
            if (captured is not None and captured.tzinfo is not None
                    and captured.utcoffset() is not None and publication > captured):
                reviews.append({**base, 'within_publication_window': None,
                                'status': 'REVIEW_REQUIRED_PUBLICATION_AFTER_CAPTURE',
                                'reason': 'NATIVE_PUBLICATION_AFTER_ACTUAL_CAPTURE'})
                continue
        reviews.append({**base, 'within_publication_window': True,
                        'status': 'CANDIDATE_IN_REQUESTED_PUBLICATION_WINDOW',
                        'reason': None})
    return reviews


def _publication_window_summary(reviews, *, publication_since, publication_until):
    """Expose the time-bound decision without implying the transport searched the range."""
    review_required = sum(review.get('status', '').startswith('REVIEW_REQUIRED_') for review in reviews)
    outside = sum(review.get('status') == 'OUTSIDE_REQUESTED_PUBLICATION_PERIOD' for review in reviews)
    within = sum(review.get('status') == 'CANDIDATE_IN_REQUESTED_PUBLICATION_WINDOW' for review in reviews)
    if review_required:
        state = 'REVIEW_REQUIRED'
    elif reviews and outside == len(reviews):
        state = 'NO_MATCHING_OBSERVATIONS'
    elif not reviews:
        state = 'NO_OBSERVATIONS'
    else:
        state = 'APPLIED'
    return {
        'publication_since': publication_since,
        'publication_until': publication_until,
        'state': state,
        'source_time_basis': 'NATIVE_PUBLICATION_ONLY',
        'transport_filter_state': 'NOT_APPLIED_BY_REGISTERED_ADAPTER',
        'candidate_review_state': 'APPLIED_POST_FETCH_NATIVE_PUBLICATION',
        'observed_count': len(reviews),
        'within_window_count': within,
        'outside_window_count': outside,
        'review_required_count': review_required,
        'reviews': reviews,
    }


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
            pages = progress.get('pages') or {}
            cached = pages.get('receipt:' + checkpoint['receipt']) or pages.get(page_key)
            resumable = bool(cached and cached.get('native_continuation_required') is True
                and cached.get('checkpoint', {}).get('receipt') == checkpoint['receipt'])
            if cached is not None and not resumable:
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
                    query_scope = (query.scope if isinstance(source_scope, Mapping)
                                   and source_scope.get('global_scope') is True else source_scope)
                    # This read-stage check retains exact Permission. Working-set
                    # eligibility is checked per query at execution so one removed
                    # entity does not hide history or block independent queries.
                    _, error = _manual_collection_guard(actor, query_scope, platform, query.keyword,
                        max_results, enforce_subject_directory=False)
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
        if task['payload'].get('cancel_requested') is True:
            return {'ok': False, 'status': 'CANCELLED', 'runs': [], 'task_id': task_id,
                    'network_attempted': False, 'resume_required': True,
                    'checkpoint': checkpoint, 'continuation_required': True}
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
        def save_native_round(key, native_round):
            progress.setdefault('native_rounds', {})[key] = native_round
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
                native_rounds=dict(progress.get('native_rounds') or {}),
                native_progress_callback=save_native_round,
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
            result['new_collection_requires_new_request_id'] = result.get('native_continuation_required') is not True
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
            if result.get('ok') is True or result.get('native_continuation_required') is True:
                progress.setdefault('pages', {})[page_key] = result
                if checkpoint is not None:
                    progress['pages']['receipt:' + checkpoint['receipt']] = result
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
                             attempt_guard=None, operation_prefix=None,
                             native_rounds=None, native_progress_callback=None):
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
    native_rounds = dict(native_rounds or {})
    if any(not isinstance(key, str) or type(value) is not int or value < 0
           for key, value in native_rounds.items()):
        raise AcquisitionPlanError('invalid server native continuation progress')
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
                query_scope = query.scope if scope.get('global_scope') is True else scope
                directory = ({'allowed': True} if operator == 'prelaunch_maintenance'
                    else _subject_directory_decision(actor, query_scope))
                if directory.get('allowed') is not True:
                    result = _subject_directory_denial_result(
                        directory, platform=platform, keyword=query.keyword,
                    )
                else:
                    def query_attempt_guard():
                        @contextmanager
                        def guarded_attempt():
                            current_directory = ({'allowed': True}
                                if operator == 'prelaunch_maintenance'
                                else _subject_directory_decision(actor, query_scope))
                            underlying = (attempt_guard() if attempt_guard is not None
                                          else nullcontext(True))
                            with underlying as active:
                                yield active is True and current_directory.get('allowed') is True
                        return guarded_attempt()

                    try:
                        result = collect_search(platform, query.keyword, max_results=max_results,
                            actor=actor, operator=operator, scope=query_scope, business_query=query,
                            prelaunch_local_import=operator == 'prelaunch_maintenance',
                            prelaunch_authorization=prelaunch_authorization,
                            attempt_guard=query_attempt_guard,
                            operation_key=((operation_prefix + ":" + key
                                + (":native:" + str(native_rounds[key]) if native_rounds.get(key) else ""))
                                if operation_prefix else None))
                    except (ValueError, PermissionError) as exc:
                        result = {'ok': False, 'status': 'COLLECTION_REQUEST_REJECTED',
                                  'platform': platform, 'error_type': type(exc).__name__}
            runs.append({'query_key': key, 'planned_query': query.to_dict(), 'result': result})
            if (result.get('native_continuation_verified') is True
                    and result.get('task_commit_evidence_ref')
                    and result.get('source_status') == 'PARTIAL_ACQUISITION_PENDING'
                    and result.get('new_collection_required') is False):
                native_rounds[key] = native_rounds.get(key, 0) + 1
                if native_progress_callback is not None:
                    native_progress_callback(key, native_rounds[key])
            if result.get('ok') is True and result.get('status') in {'SUCCESS', 'NO_NEW_DATA'}:
                completed.add(key)
                if progress_callback is not None:
                    progress_callback(sorted(completed))
            elif result.get('status') in _SUBJECT_DIRECTORY_DENIALS:
                # One removed/unverified entity blocks only its own query.
                # Other selected entities and source platforms remain usable.
                deferred.append({'query_key': key, 'query': query.to_dict(),
                                 'reason': result.get('status')})
            else:
                blocked[platform] = result.get('status') or 'UNAVAILABLE'
                deferred.append({'query_key': key, 'query': query.to_dict(), 'reason': blocked[platform]})
    native_pending = any(run['result'].get('native_continuation_verified') is True
        and run['result'].get('new_collection_required') is False for run in runs)
    return {'ok': not deferred, 'status': 'PARTIAL' if deferred else 'BATCH_COMPLETED',
            'query_plan': plan.to_dict(), 'runs': runs, 'deferred_queries': deferred,
            'checkpoint': {'input_fingerprint': plan.input_fingerprint,
                           'completed_query_keys': sorted(completed)},
            'next_cursor': continuation if native_pending else plan.next_cursor,
            'continuation_required': bool(deferred or plan.next_cursor),
            'native_continuation_required': native_pending,
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
    from .public_http import PublicHttpAdapter,has_observed_media_source
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
    if not item.get("content", "").strip() and not has_observed_media_source(item):
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

PUBLIC_ORIGINAL_PLATFORMS = frozenset({'public_http', 'naver', 'daum'})


def _parse_public_original(platform, response, media_schema):
    if platform == 'public_http':
        from .public_http import PublicHttpAdapter
        return PublicHttpAdapter._item(response, media_schema=media_schema)
    if platform == 'naver':
        from .naver import NaverAdapter
        return NaverAdapter.parse_original(response)
    if platform == 'daum':
        from .daum import DaumAdapter
        return DaumAdapter.parse_original(response)
    raise ValueError('PUBLIC_SOURCE_PLATFORM_UNSUPPORTED')


def validate_public_source_original(content, sha256):
    """Pure public Source producer check; no fetch, DNS or session read."""
    import base64
    from .public_source import PublicResponse
    if (type(content) is not bytes or not 0 < len(content) <= 4 * 1024 * 1024
            or hashlib.sha256(content).hexdigest() != sha256):
        raise ValueError('PUBLIC_SOURCE_ORIGINAL_BYTES_CHANGED')
    value = json.loads(content)
    if not isinstance(value, dict) or value.get('platform') not in PUBLIC_ORIGINAL_PLATFORMS:
        raise ValueError('PUBLIC_SOURCE_ORIGINAL_INVALID')
    platform = value['platform']
    response = value.get('source_response')
    if (not isinstance(response, dict) or set(response) != {
            'body_base64', 'sha256', 'url', 'requested_url', 'content_type', 'status_code'}
            or type(response['status_code']) is not int or not 200 <= response['status_code'] < 300):
        raise ValueError('PUBLIC_SOURCE_RESPONSE_INVALID')
    raw = base64.b64decode(response['body_base64'], validate=True)
    if (not 0 < len(raw) <= 2 * 1024 * 1024
            or hashlib.sha256(raw).hexdigest() != response['sha256']):
        raise ValueError('PUBLIC_SOURCE_RESPONSE_BYTES_CHANGED')
    for target in (response['url'], response['requested_url']):
        parts = urlsplit(target)
        host = (parts.hostname or '').lower()
        if (parts.scheme not in {'http', 'https'} or not host or parts.username or parts.password
                or host == 'localhost' or host.endswith(('.localhost', '.local'))
                or _credential_free_observations(target) != target):
            raise ValueError('PUBLIC_SOURCE_URL_INVALID')
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError('PUBLIC_SOURCE_URL_INVALID')
    observed = value.get('native_record')
    source_raw = (observed.get('source_raw') or {}) if isinstance(observed, dict) else {}
    media_observation = source_raw.get('media_observation')
    media_schema = (media_observation.get('schema') if isinstance(media_observation, dict)
                    else 'public-http-dom-media/v1')
    if media_schema not in {'public-http-dom-media/v1', 'public-http-dom-media/v2'}:
        raise ValueError('PUBLIC_SOURCE_MEDIA_SCHEMA_UNSUPPORTED')
    item = _parse_public_original(platform, PublicResponse(url=response['url'], content=raw,
        content_type=response['content_type'], status_code=response['status_code'],
        requested_url=response['requested_url']), media_schema)
    observation = (observed.get('source_raw') or {}).get('content_observation') if isinstance(observed, dict) else None
    if (not isinstance(observed, dict) or not isinstance(observation, dict)
            or value.get('native_id') != item['platform_content_id']
            or value.get('stable_source_key') != platform + ':' + item['platform_content_id']
            or observed.get('content_id') != item['platform_content_id']
            or value.get('source_url') != response['url'] or observed.get('url') != item['url']
            or value.get('body') != item['content'] or observed.get('content') != item['content']
            or observed.get('title') != item['title']
            or value.get('body_sha256') != hashlib.sha256(item['content'].encode()).hexdigest()
            or observation.get('document_sha256') != response['sha256']
            or observation.get('document_byte_length') != len(raw)
            or observation != item['raw']['content_observation']):
        raise ValueError('PUBLIC_SOURCE_BODY_BINDING_CHANGED')
    if media_observation is not None:
        if (not isinstance(media_observation, dict)
                or media_observation.get('schema') != media_schema
                or any(source_raw.get(key) != item['raw'].get(key)
                       or observed.get(key) != item['raw'].get(key)
                       for key in ('media_list', 'media_hints', 'media_observation'))):
            raise ValueError('PUBLIC_SOURCE_MEDIA_BINDING_CHANGED')
    datetime.fromisoformat(value['capture_observation_native'].replace('Z', '+00:00'))
    if value['capture_observation_native'] != observed.get('captured_at'):
        raise ValueError('PUBLIC_SOURCE_CAPTURE_TIME_CHANGED')
    publication = value.get('publication') or {}
    if publication.get('native_time') != (item['publish_datetime'] or None):
        raise ValueError('PUBLIC_SOURCE_PUBLICATION_CHANGED')
    lineage = value.get('source_lineage')
    if (not isinstance(lineage, list) or len(lineage) != 2
            or lineage[0].get('sha256') != response['sha256']
            or lineage[0].get('kind') != 'ORIGINAL_HTTP_RESPONSE_BODY'
            or lineage[0].get('locator') != response['url']
            or lineage[0].get('transport_original') is not True
            or lineage[1].get('sha256') != hashlib.sha256(json.dumps(observed, ensure_ascii=False,
                sort_keys=True, separators=(',', ':')).encode()).hexdigest()):
        raise ValueError('PUBLIC_SOURCE_LINEAGE_CHANGED')
    return value


def _persist_public_http_original(connection, *, response, record, source_id, collection_evidence_id,
                                  context, staged_paths, actor, scope, keyword, max_results, capability,
                                  platform='public_http'):
    import base64
    from .public_source import PublicResponse
    from lumenis.shared.evidence.store import classify_evidence_integrity
    if platform not in PUBLIC_ORIGINAL_PLATFORMS:
        raise ValueError('PUBLIC_SOURCE_PLATFORM_UNSUPPORTED')
    exact, denial = _manual_collection_guard(actor, scope, platform, keyword, max_results,
                                             capability=capability)
    if denial is not None:
        raise ValueError('PUBLIC_SOURCE_IMPORT_NOT_AUTHORIZED')
    if type(response) is not PublicResponse:
        raise ValueError('PUBLIC_SOURCE_ORIGINAL_RESPONSE_UNAVAILABLE')
    parent = connection.execute('SELECT * FROM app_evidence_records WHERE id=?', (collection_evidence_id,)).fetchone()
    parent = dict(parent) if parent else {}
    integrity = classify_evidence_integrity(parent)
    observations = json.loads(parent.get('inputs_json') or '{}').get('source_observation_records')
    if (integrity.get('assurance') != 'writer-authenticated' or parent.get('result') != 'PASS'
            or not isinstance(observations, list) or observations.count(record) != 1):
        raise ValueError('PUBLIC_SOURCE_PARENT_UNVERIFIED')
    position = observations.index(record)
    source_id = str(source_id)
    if source_id != record.get('content_id'):
        raise ValueError('PUBLIC_SOURCE_ID_CHANGED')
    canonical = connection.execute('SELECT content,publish_datetime FROM canonical_data WHERE source_table=\'notes\' '
        'AND source_id=? AND product_id=? AND domain_id=? AND NULLIF(subject_id,\'\') IS ? '
        'AND NULLIF(brand_focus_id,\'\') IS ?', (source_id, 'CTH' if exact['domain_id'] == 'cth' else 'ZBMP',
        context['domain_id'], exact['subject_id'], exact['brand_focus_id'])).fetchall()
    if len(canonical) != 1 or canonical[0]['content'] != record.get('content'):
        raise ValueError('PUBLIC_SOURCE_CANONICAL_BODY_CHANGED')
    value = {'platform': platform, 'native_id': source_id, 'stable_source_key': platform + ':' + source_id,
        'source_url': response.url, 'body': record['content'],
        'body_sha256': hashlib.sha256(record['content'].encode()).hexdigest(),
        'body_state': record['source_raw']['content_observation']['completeness'], 'native_record': record,
        'capture_observation_native': record['captured_at'],
        'publication': {'published_at_utc': canonical[0]['publish_datetime'] or None,
                        'native_time': record.get('publish_datetime') or None,
                        'normalization_owner': 'Canonical publication owner', 'timezone_inferred': None},
        'claim_type': 'PUBLIC_WEB_SOURCE_STATEMENT',
        'rights': {'status': 'UNREVIEWED', 'allowed_uses': [], 'third_party_rights_granted': False,
                   'intake_purpose': 'SOURCE_PRESERVATION'},
        'source_response': {'body_base64': base64.b64encode(response.content).decode('ascii'),
                            'sha256': hashlib.sha256(response.content).hexdigest(), 'url': response.url,
                            'requested_url': response.requested_url or keyword,
                            'content_type': response.content_type, 'status_code': response.status_code},
        'source_lineage': [{'sha256': hashlib.sha256(response.content).hexdigest(), 'locator': response.url,
                            'kind': 'ORIGINAL_HTTP_RESPONSE_BODY', 'transport_original': True},
                           {'sha256': hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                separators=(',', ':')).encode()).hexdigest(),
                            'locator': f'app_evidence_records:{collection_evidence_id}:inputs.source_observation_records[{position}]',
                            'kind': 'SIGNED_SOURCE_OBSERVATION_JSON', 'transport_original': False}]}
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    fingerprint = hashlib.sha256(raw).hexdigest()
    validate_public_source_original(raw, fingerprint)
    return _persist_collected_source_original(connection, value=value, source_bytes=raw,
        source_fingerprint=fingerprint, source_id=source_id, collection_evidence_id=collection_evidence_id,
        context=context, staged_paths=staged_paths, capture_mode='live_public_response_intake',
        source_version='collected-public-source:live-v1',
        authorization_resource='collector-public-source-preservation:' + fingerprint,
        source_locator_unit='public-document-body')


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
    if platform == "facebook":
        detail_native_id = normalize_content_id("facebook", detail.get("native_post_id"))
        if detail_native_id != native_id:
            raise ValueError("LIVE_NATIVE_DETAIL_ID_MISMATCH")
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
                                          max_results, reason, recovery_binding=None):
    """Preserve an authorized native observation pending business-entity assignment."""
    if recovery_binding is None:
        if not _authorize_prelaunch_public(
                scope, keyword, platform, maintenance_authorization=authorization,
                business_query=business_query, max_results=max_results):
            raise ValueError("COLLECTED_SOURCE_IMPORT_PERMISSION_DENIED")
    elif (not isinstance(recovery_binding, Mapping)
          or getattr(authorization, "recovery_only", False) is not True):
        raise ValueError("PENDING_SOURCE_RECOVERY_BINDING_INVALID")
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
    if recovery_binding is not None and not _authorize_prelaunch_pending_source_recovery(
            scope, authorization=authorization,
            parent_evidence_ref=recovery_binding["parent_evidence_ref"],
            parent_integrity_digest=recovery_binding["parent_integrity_digest"],
            observation_sha256=recovery_binding["observation_sha256"],
            native_id=native_id, source_fingerprint=fingerprint,
            source_url=keyword, platform=platform, business_query=business_query,
            max_results=max_results, connection=connection):
        raise ValueError("PENDING_SOURCE_RECOVERY_PERMISSION_DENIED")
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
                                      capture_mode, source_version, authorization_resource,
                                      source_locator_unit='native-post-body'):
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
    locator = {"unit": source_locator_unit, "json_path": "$.body", "start": 0,
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
                                       max_results, reviews, saved_ids, covers=None,
                                       recovery_bindings=None):
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
                max_results=max_results, reason="SOURCE_ENTITY_IDENTITY_UNCONFIRMED",
                recovery_binding=(recovery_bindings or {}).get(str(source_id)))
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
    eligible_pending = sum(row.get("status") != "EXCLUDED" for row in originals)
    summary = {"observed_records": len(records), "formal_saved_records_skipped": len(saved_ids),
               "unassigned_originals_saved": saved,
               "unassigned_originals_unavailable": sum(row["status"] == "UNAVAILABLE" for row in originals),
               "excluded_observations": sum(row["status"] == "EXCLUDED" for row in originals),
               "eligible_pending_records": eligible_pending,
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
                result="PASS" if saved == eligible_pending else "FAIL",
                actual=("NO_ELIGIBLE_PENDING_ORIGINALS" if eligible_pending == 0
                        else "PENDING_ORIGINALS_PRESERVED" if saved == eligible_pending
                        else "PARTIAL_PENDING_SOURCE_PRESERVATION"),
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
    import sqlite3

    from lumenis.importer.documents import _source_bytes
    from lumenis.shared.database import get_repository
    from lumenis.shared.evidence import store

    from .scheduling.prelaunch_baseline import (
        PURPOSE_POLICY,
        BaselineConfigError,
        _purpose_query,
        load_prelaunch_baseline_config,
        maintenance_authorization,
    )
    if type(limit) is not int or not 1 <= limit <= 40:
        raise ValueError("PENDING_SOURCE_RECOVERY_LIMIT_INVALID")
    config_error = None
    try:
        loaded = load_prelaunch_baseline_config(
            os.environ.get("LUMENIS_PRELAUNCH_BASELINE_CONFIG") or None)
    except BaselineConfigError as exc:
        loaded = {"plans": [], "recovery_plans": []}
        config_error = exc.code
    if loaded.get("status") == "DISABLED":
        config_error = "PRELAUNCH_SERVICE_DISABLED"
    plans = {p.plan_id: p for p in loaded.get("plans", []) if p.policy_id == PURPOSE_POLICY}
    for plan in loaded.get("recovery_plans", []):
        if plan.policy_id == PURPOSE_POLICY:
            plans.setdefault(plan.plan_id, plan)
    con = get_repository().connect(timeout=10)
    outcomes, scanned, deferred, invalid_parents = [], 0, 0, 0
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
            parent_ref = "app_evidence_records:" + str(parent.get("id"))
            try:
                metadata = json.loads(parent["collection_metadata"] or "{}")
                plan = plans.get(metadata.get("maintenance_plan_id"))
                inputs = json.loads(parent["inputs_json"] or "{}")
                observations = inputs.get("source_observation_records")
                integrity = store.classify_evidence_integrity(parent)
                if (not isinstance(observations, list) or integrity.get("verified") is not True
                        or integrity.get("assurance") != "writer-authenticated"
                        or parent.get("status") != "verified"
                        or parent.get("result") not in {"PASS", "FAIL"}):
                    invalid_parents += 1
                    continue
                if plan is None:
                    platform = inputs.get("platform") if isinstance(inputs, dict) else None
                    if platform:
                        from .platform_naming import normalize_platform
                        platform = normalize_platform(platform)
                    needs_recovery = False
                    for observation in observations[:40]:
                        try:
                            native_id, _ = _verified_live_native_observation(platform, observation)
                        except (TypeError, ValueError):
                            deferred += 1
                            continue
                        scanned += 1
                        if (parent_ref, native_id) not in preserved:
                            needs_recovery = True
                    if needs_recovery:
                        outcomes.append({
                            "collection_evidence_ref": parent_ref, "status": "PENDING",
                            "reason": config_error or "RECOVERY_AUTHORIZATION_UNAVAILABLE",
                            "network_collection": False, "canonical_ref": None,
                        })
                    continue
                query = _purpose_query(plan.purpose_query)
                scope = {"domain_id": plan.domain_id, "subject_id": plan.subject_id,
                         "brand_focus_id": plan.brand_focus_id}
                context = {**scope, "domain_id": "zbmp" if plan.domain_id == "bmp" else "cth",
                           "global_scope": False, "collector_plan_id": plan.plan_id,
                           "collector_authorization_ref": plan.authorization_ref}
                authorization = maintenance_authorization(plan, recovery_only=True)
                eligible = []
                recovery_bindings = {}
                for observation in observations[:plan.max_results]:
                    scanned += 1
                    try:
                        native_id, _ = _verified_live_native_observation(plan.platform, observation)
                    except (TypeError, ValueError):
                        deferred += 1
                        continue
                    if (parent_ref, native_id) not in preserved:
                        eligible.append(observation)
                        encoded_observation = json.dumps(
                            observation, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":"),
                        ).encode("utf-8")
                        recovery_bindings[native_id] = {
                            "parent_evidence_ref": parent_ref,
                            "parent_integrity_digest": str(parent.get("integrity_digest") or ""),
                            "observation_sha256": hashlib.sha256(encoded_observation).hexdigest(),
                        }
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
                from .platform_naming import normalize_platform
                recovery_platform = normalize_platform(plan.platform)
                if recovery_platform is None:
                    raise ValueError("PENDING_SOURCE_RECOVERY_PLATFORM_INVALID")
                con.execute("BEGIN IMMEDIATE")
                result = _persist_pending_live_observations(
                    con, platform=recovery_platform, records=eligible,
                    collection_evidence_id=parent["id"], context=context, staged_paths=paths,
                    scope=scope, keyword=plan.source_url, authorization=authorization,
                    business_query=query, max_results=plan.max_results, reviews=reviews,
                    saved_ids=set(), recovery_bindings=recovery_bindings)
                for item in result.get("original_refs", []):
                    if item.get("status") != "SAVED":
                        continue
                    native_id = str(item.get("source_id") or "")
                    binding = recovery_bindings.get(native_id)
                    if (binding is None or not _authorize_prelaunch_pending_source_recovery(
                            scope, authorization=authorization,
                            parent_evidence_ref=binding["parent_evidence_ref"],
                            parent_integrity_digest=binding["parent_integrity_digest"],
                            observation_sha256=binding["observation_sha256"],
                            native_id=native_id,
                            source_fingerprint=item.get("source_fingerprint"),
                            source_url=plan.source_url, platform=plan.platform,
                            business_query=query, max_results=plan.max_results,
                            connection=con)):
                        raise ValueError("PENDING_SOURCE_RECOVERY_PERMISSION_REVOKED")
                con.commit()
                committed = True
                for item in result["original_refs"]:
                    outcomes.append({"collection_evidence_ref": parent_ref,
                                     "outcome_ref": result["outcome_ref"], **item})
                    if item.get("status") == "SAVED":
                        preserved.add((parent_ref, str(item["source_id"])))
            except (ImportError, KeyError, OSError, PermissionError, RuntimeError,
                    TypeError, ValueError, sqlite3.Error) as exc:
                con.rollback()
                outcomes.append({"collection_evidence_ref": parent_ref, "status": "UNAVAILABLE",
                    "reason": str(exc) if isinstance(exc, ValueError)
                        and re.fullmatch(r"[A-Z][A-Z0-9_]{0,100}", str(exc))
                        else "PENDING_SOURCE_RECOVERY_UNAVAILABLE",
                    "network_collection": False})
            finally:
                if not committed:
                    _cleanup_collected_source_paths(paths)
        saved = sum(r.get("status") == "SAVED" for r in outcomes)
        pending = sum(r.get("status") == "PENDING" for r in outcomes)
        return {"status": "PARTIAL" if any(r.get("status") in {"UNAVAILABLE", "PENDING"}
                                                for r in outcomes)
                else "COMPLETED", "processed": len(outcomes), "saved": saved,
                "observations_scanned": scanned, "native_detail_unavailable": deferred,
                "pending_authorization": pending, "invalid_parent_count": invalid_parents,
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


def _authorize_prelaunch_pending_source_recovery(
    scope: Mapping[str, Any], *, authorization, parent_evidence_ref: str,
    parent_integrity_digest: str, observation_sha256: str, native_id: str,
    source_fingerprint: str, source_url: str, platform: str, business_query,
    max_results: int, connection,
) -> bool:
    """Recheck a current signed recovery grant for one stored parent item."""
    try:
        from lumenis.system.security import (
            get_permission_gate,
            is_testing_bypass_enabled,
        )
        if is_testing_bypass_enabled():
            return False
        decision = get_permission_gate().check_prelaunch_pending_source_recovery(
            authorization, parent_evidence_ref=parent_evidence_ref,
            parent_integrity_digest=parent_integrity_digest,
            observation_sha256=observation_sha256, native_id=native_id,
            source_fingerprint=source_fingerprint, source_url=source_url,
            platform=platform, business_query=business_query,
            max_results=max_results, scope=dict(scope), connection=connection,
        )
        return decision.allowed is True and bool(decision.audit_id)
    except (ImportError, OSError, RuntimeError, TypeError, ValueError):
        return False
