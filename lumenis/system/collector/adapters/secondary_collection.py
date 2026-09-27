# -*- coding: utf-8 -*-
"""CTH secondary platform collection surface.

This is the canonical runtime entry for manual, read-only platform collection.
XHS keeps its existing primary collector; this surface reuses the registered
adapters for Bilibili, Weibo, Douyin, Kuaishou and Web RSS, alongside the
already-integrated Zhihu and Instagram adapters.

The product boundary is deliberately narrow:

* CTH owns the collection action and the resulting Evidence/Canonical records.
* BMP may consume the resulting read-only market-intelligence view; it does not
  get a second collector or a second copy of the truth.
* Every action is human-triggered and read-only on the external platform.
* Raw platform records never leave the server response and credentials are never
  returned.  The existing ``notes`` and ``canonical_data`` tables remain the
  persistence boundary.
* Publishing is not a collection capability.  The product never publishes.

The scheduler flag remains disabled on purpose.  This surface enables a
controlled, explicit search collection action without silently turning on
background traffic for accounts that still need operating review.
"""
from __future__ import annotations

import threading
import time
import sys
import hashlib
import json
import getpass
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping
from urllib.parse import urlsplit

from .base import CollectionResult, CollectionStatus
from .config import PLATFORM_CAPABILITIES
from .registry import get_adapter
from .safe_collection import CollectionHygienePolicy, RateGovernor


SECONDARY_COLLECTION_PLATFORMS = (
    "bilibili", "weibo", "douyin", "kuaishou", "web_rss", "public_http", "web_atom", "sitemap", "zhihu", "instagram",
)
PLATFORM_NAMES = {
    "bilibili": "B站",
    "douyin": "抖音",
    "kuaishou": "快手",
    "weibo": "微博",
    "web_rss": "Web RSS",
    "public_http": "Public HTTP",
    "web_atom": "Web Atom",
    "sitemap": "Sitemap",
    "zhihu": "知乎",
    "instagram": "Instagram",
}
MAX_RESULTS = 20
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
            state = "SUCCESS" if int(row[4] or 0) > 0 else "NO_NEW_DATA"
        return {
            "platform": row[0],
            "query": row[1],
            "started_at": row[2],
            "finished_at": row[3],
            "fetched": int(row[4] or 0),
            "accepted": int(row[5] or 0),
            "rejected": int(row[6] or 0),
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
    for platform in SECONDARY_COLLECTION_PLATFORMS:
        cap = PLATFORM_CAPABILITIES.get(platform, {})
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
            "product_owner": "CTH",
            "consumer_views": ["CTH", "BMP"],
            "manual_collection_enabled": bool(cap.get("manual_collection_enabled")),
            "scheduled_collection_enabled": bool(cap.get("enabled")),
            "collection_mode": "human_triggered_read_only",
            # Local readiness and the last real run are separate facts.  A
            # readable cookie file must not overwrite a verified session
            # failure or collection error in the product surface.
            "status": display_status,
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
        "out_of_scope_platforms": [
            "tieba", "facebook", "x", "youtube",
            "tiktok", "reddit", "linkedin", "github", "channels",
        ],
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
    if not query or len(query) > 120:
        raise ValueError("keyword 必须为 1-120 个字符")
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
    record: Dict[str, Any] = dict(raw)
    content_id = str(item.get("platform_content_id") or "").strip()
    publish_date = item.get("publish_datetime") or ""
    record.update({
        "platform": platform,
        "source_platform": platform,
        "title": item.get("title") or "",
        "content": item.get("content") or "",
        "url": item.get("url") or "",
        "author_id": item.get("author_id") or "",
        "author_nickname": item.get("author_nickname") or "",
        "captured_at": captured_at,
        "source_keyword": keyword,
        "matched_keywords": keyword,
    })
    if platform == "douyin":
        record.update({"content_id": content_id, "aweme_id": content_id,
                       "desc": item.get("content") or item.get("title") or ""})
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
            if value is not None:
                record[native_field] = value
    elif platform == "weibo":
        record.update({"mid": content_id, "idstr": content_id, "created_at": publish_date})
        record.update({"attitudes_count": item.get("likes"), "comments_count": item.get("comments"),
                       "reposts_count": item.get("shares")})
    elif platform == "zhihu":
        record.update({"answer_id": content_id, "url_token": item.get("author_id") or "", "created_time": publish_date})
        record.update({"voteup_count": item.get("likes"), "comment_count": item.get("comments"),
                       "share_count": item.get("shares")})
    elif platform == "instagram":
        record.update({"media_id": content_id, "username": item.get("author_id") or "", "taken_at": publish_date})
        record.update({"like_count": item.get("likes"), "comment_count": item.get("comments"),
                       "share_count": item.get("shares")})
    elif platform == "public_http":
        record.update({"content_id": content_id, "published_at": publish_date})
    elif platform == "web_rss":
        record.update({
            "content_id": content_id,
            "source_id": item.get("author_id") or raw.get("source_name") or "",
            "source_name": item.get("author_nickname") or raw.get("source_name") or "",
            "published_at": publish_date,
            "like_count": item.get("likes"),
            "comment_count": item.get("comments"),
            "collect_count": item.get("collects"),
            "share_count": item.get("shares"),
        })
    elif platform == "web_atom":
        record.update({
            "content_id": content_id,
            "author_id": item.get("author_id") or "",
            "author_name": item.get("author_nickname") or "",
            "published_at": publish_date,
            "view_count": raw.get("view_count"),
            "content_type": "video" if raw.get("video_id") else "article",
        })
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
                   fetched: int, accepted: int, rejected: int, error: str = "") -> None:
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
                               *, maintenance_authorization=None) -> bool:
    try:
        from lumenis.system.security import OperationType, get_permission_gate, is_testing_bypass_enabled
        if is_testing_bypass_enabled():
            return False
        if maintenance_authorization is not None:
            return get_permission_gate().check_prelaunch_maintenance(
                maintenance_authorization, source_url=source, platform=platform,
                scope=dict(scope),
            ).allowed is True
        resource = _prelaunch_public_import_resource(scope, source, platform=platform)
        return get_permission_gate().check(
            OperationType.DATA_IMPORT, resource,
            caller=f"local_prelaunch_operator:{getpass.getuser()}",
            domain_id=scope["domain_id"], exact_approval_required=True,
        ).allowed is True
    except Exception:
        return False


def _prelaunch_douyin_manual_import_resource(
    scope: Mapping[str, Any], keyword: str, *, platform: str,
) -> str:
    """Bind human-only Douyin import approval to platform, query, and exact entity."""
    exact = _prelaunch_scope(scope)
    if platform != "douyin" or not isinstance(keyword, str) or not 1 <= len(keyword) <= 120:
        raise ValueError("exact Douyin manual source required")
    entity_id = exact["subject_id"] or exact["brand_focus_id"]
    digest = hashlib.sha256(keyword.encode("utf-8")).hexdigest()
    return f"prelaunch-manual:{platform}:{exact['domain_id']}:{entity_id}:{digest}"


def _authorize_prelaunch_douyin_manual(
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
        resource = _prelaunch_douyin_manual_import_resource(
            exact, keyword, platform=platform,
        )
        return get_permission_gate().check(
            OperationType.DATA_IMPORT, resource,
            caller=f"local_prelaunch_operator:{getpass.getuser()}",
            domain_id=exact["domain_id"], exact_approval_required=True,
        ).allowed is True
    except Exception:
        return False


def _validate_prelaunch_registry(scope: Mapping[str, Any]) -> None:
    from lumenis.shared.database import get_repository
    from lumenis.shared.database.scope import resolve_scope
    conn = get_repository().connect(timeout=10)
    try:
        resolve_scope(conn, product_id="CTH" if scope["domain_id"] == "cth" else "ZBMP",
                      subject_id=scope.get("subject_id"), brand_focus_id=scope.get("brand_focus_id"),
                      requested_status="UNVERIFIED")
    finally:
        conn.close()


def _prelaunch_entity_mentions(records: List[Dict[str, Any]], scope: Mapping[str, Any]) -> List[dict]:
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
    with get_repository().transaction() as conn:
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


def _existing_prelaunch_evidence(note_ids: List[str], scope: Mapping[str, Any]) -> int | None:
    if not note_ids:
        return None
    import database as db
    domain = "cth" if scope["domain_id"] == "cth" else "zbmp"
    key = scope.get("subject_id") or scope.get("brand_focus_id")
    with db.get_db() as conn:
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


def _prelaunch_scope_conflict(records: List[Dict[str, Any]], scope: Mapping[str, Any]) -> bool:
    """Reject known cross-scope raw identities before the existing importer writes."""
    ids = [record.get("content_id") for record in records]
    if any(not isinstance(note_id, str) or not note_id for note_id in ids):
        return True
    if len(set(ids)) != len(ids):
        return True
    import database as db
    expected_domain = "zbmp" if scope["domain_id"] == "bmp" else "cth"
    expected_subject = scope.get("subject_id")
    expected_brand = scope.get("brand_focus_id")
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT domain_id, subject_id, brand_focus_id FROM notes WHERE note_id IN ("
            + ",".join("?" for _ in ids) + ")", ids,
        ).fetchall() if ids else []
    return any(
        (row[0] not in (None, "", expected_domain))
        or (row[1] not in (None, "", expected_subject))
        or (row[2] not in (None, "", expected_brand))
        for row in rows
    )


def _write_prelaunch_evidence(platform: str, keyword: str, result: Dict[str, Any], *,
                              started: str, scope: Mapping[str, Any], source_ids: List[str],
                              review_candidates: List[Dict[str, Any]] | None = None) -> int | None:
    try:
        _ensure_evidence_schema()
        from lumenis.shared.evidence.store import record_evidence
        bmp = scope["domain_id"] == "bmp"
        evidence_id = record_evidence(
            source="collector", project="LUMENIS", product="ZBMP" if bmp else "CTH",
            feature_id=f"PRELAUNCH_{platform.upper()}_COLLECT", level="L8",
            test_name=f"prelaunch_collection_{platform}",
            result="PASS" if result.get("ok") else "FAIL", started_at=started,
            inputs={"platform": platform, "source_url": keyword,
                    "source_ids": source_ids, "keywords": [keyword],
                    "unassigned_review_candidates": review_candidates or []},
            outputs={"notes_collected": result.get("raw_count", 0),
                     "notes_inserted": result.get("imported", 0),
                     "notes_updated": result.get("updated", 0),
                     "entity_mentions": result.get("entity_mentions")},
            actual=result.get("status", "COLLECT_ERROR"), account=f"PRELAUNCH_{platform.upper()}",
            provider=(result.get("provenance") or {}).get("provider", "platform_adapter"),
            collection_metadata=result.get("provenance"),
            domain_id="zbmp" if bmp else "cth", subject_id=scope.get("subject_id"),
            brand_focus_id=scope.get("brand_focus_id"),
        )
        return evidence_id if type(evidence_id) is int and evidence_id > 0 else None
    except Exception:
        return None


def _persist_prelaunch_scope(note_ids: List[str], scope: Mapping[str, Any], evidence_id: int) -> int:
    import database as db
    from lumenis.adapters.persist import persist_existing_note_scope
    bmp = scope["domain_id"] == "bmp"
    with db.get_db() as conn:
        return persist_existing_note_scope(
            conn, note_ids, product_id="ZBMP" if bmp else "CTH",
            domain_id="zbmp" if bmp else "cth", subject_id=scope.get("subject_id"),
            brand_focus_id=scope.get("brand_focus_id"), scope_evidence_ref=evidence_id,
        )


def _prelaunch_scope_note_ids_needing_verification(
    note_ids: List[str], scope: Mapping[str, Any],
) -> List[str]:
    """Return only rows that still need their first exact-scope Evidence link."""
    import database as db

    product = "ZBMP" if scope["domain_id"] == "bmp" else "CTH"
    domain = "zbmp" if scope["domain_id"] == "bmp" else "cth"
    with db.get_db() as conn:
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
    note_ids: List[str], scope: Mapping[str, Any],
) -> int:
    """Refresh source fields through the existing Canonical Data owner."""
    import database as db
    from canonical_data import (
        ensure_canonical_table, get_connection, note_to_canonical, persist_canonical,
    )
    from lumenis.shared.database import main_db_path

    product = "ZBMP" if scope["domain_id"] == "bmp" else "CTH"
    expected = (
        product, "zbmp" if product == "ZBMP" else "cth",
        scope.get("subject_id"), scope.get("brand_focus_id"), "VERIFIED",
    )
    notes = []
    with db.get_db() as conn:
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
            if actual != expected or not note.get("scope_evidence_ref"):
                raise ValueError(f"imported note has no matching signed scope: {note_id}")
            notes.append(note)

    db_path = main_db_path()
    ensure_canonical_table(db_path)
    conn = get_connection(db_path)
    try:
        for note in notes:
            persist_canonical(conn, note_to_canonical(note, product_id=product))
        conn.commit()
    finally:
        conn.close()
    return len(notes)


def _existing_prelaunch_observation_evidence(
    note_ids: List[str], platform: str,
) -> int | None:
    """Reuse the latest matching observation Evidence on an unchanged public page."""
    if not note_ids:
        return None
    from lumenis.shared.database import get_repository

    evidence_ids = set()
    with get_repository().transaction() as conn:
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
    return next(iter(evidence_ids)) if len(evidence_ids) == 1 else None


def _write_evidence(platform: str, keyword: str, result: Dict[str, Any], *, started: str) -> int | None:
    try:
        _ensure_evidence_schema()
        from lumenis.shared.evidence.store import record_collection_evidence

        status = result.get("status") or "COLLECT_ERROR"
        provenance = result.get("provenance") if isinstance(result.get("provenance"), dict) else {}
        evidence_id = record_collection_evidence(
            account=f"CTH_{platform.upper()}_RUNTIME",
            platform=platform,
            notes_collected=int(result.get("raw_count", 0) or 0),
            notes_filtered=int(result.get("filtered_count", 0) or 0),
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
            provider=provenance.get("provider") or "platform_adapter",
            source=provenance.get("source") or f"platform:{platform}",
            collected_at=provenance.get("collected_at") or "",
            collection_metadata=provenance,
        )
        return evidence_id if isinstance(evidence_id, int) and not isinstance(evidence_id, bool) and evidence_id > 0 else None
    except Exception:
        return None


def collect_search(platform: str, keyword: str, *, max_results: int = MAX_RESULTS,
                   operator: str = "human", scope: Mapping[str, Any] | None = None,
                   actor: Mapping[str, Any] | None = None,
                   prelaunch_local_import: bool = False,
                   prelaunch_authorization: Any = None) -> Dict[str, Any]:
    """Run one explicit, read-only platform search and persist its evidence."""
    operator = str(operator or "").strip().lower()
    maintenance_operator = operator == "prelaunch_maintenance"
    if operator not in {"human", "human_ui", "prelaunch_maintenance"}:
        raise PermissionError("该采集入口只接受人工触发或签名预发布维护计划")
    if maintenance_operator and not prelaunch_local_import:
        return {"ok": False, "status": "SCOPE_UNAUTHORIZED", "platform": platform,
                "keyword": keyword, "read_only": True, "external_write": False}
    platform, keyword, max_results = _validate_request(platform, keyword, max_results)
    if _blocked_youtube_atom_feed(platform, keyword):
        return {
            "ok": False, "status": "BLOCKED", "platform": platform,
            "keyword": keyword, "read_only": True, "external_write": False,
            "error_type": "SOURCE_POLICY",
        }
    prelaunch_scope = None
    if prelaunch_local_import:
        if (actor is not None
                or platform not in {"public_http", "web_atom", "douyin"}
                or (maintenance_operator and platform not in {"public_http", "web_atom"})
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
                )
            elif platform == "douyin":
                authorized = _authorize_prelaunch_douyin_manual(
                    prelaunch_scope, keyword, platform=platform,
                )
            else:
                authorized = _authorize_prelaunch_public(prelaunch_scope, keyword, platform)
            if not authorized:
                raise PermissionError("exact import approval unavailable")
            _validate_prelaunch_registry(prelaunch_scope)
        except Exception:
            return {"ok": False, "status": "SCOPE_UNAUTHORIZED", "platform": platform,
                    "keyword": keyword, "read_only": True, "external_write": False}
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

        health = (
            _adapter_health(platform, url=keyword)
            if platform in {"public_http", "web_atom"} else _adapter_health(platform)
        )


        health_status = health.get("status", "UNAVAILABLE")
        if not health.get("can_attempt", health.get("ready", False)):
            finished = _now()
            error = f"{health_status}: {_status_message(health_status)}"
            result = {
                "ok": False, "status": health_status, "platform": platform,
                "keyword": keyword, "raw_count": 0, "returned_count": 0,
                "imported": 0, "updated": 0, "filtered_count": 0,
                "health_status": health_status, "error": error,
                "error_type": "PREFLIGHT_NOT_READY", "read_only": True,
                "external_write": False, "publish_authority": "human_manual_only",
                "duration_ms": int((time.monotonic() - started_monotonic) * 1000),
            }
            evidence_id = _write_evidence(platform, keyword, result, started=started_at)
            result["evidence_recorded"] = evidence_id is not None
            if evidence_id is None:
                result.update({
                    "ok": False,
                    "status": "EVIDENCE_WRITE_FAILED",
                    "error_type": "EVIDENCE_WRITE_FAILED",
                    "error": f"EVIDENCE_WRITE_FAILED: {_status_message('EVIDENCE_WRITE_FAILED')}",
                })
            _write_run_log(platform, keyword, started=started_at, finished=finished,
                           fetched=0, accepted=0, rejected=0, error=result["error"])
            return result

        adapter = _get_runtime_adapter(platform)
        try:
            collection = adapter.search(keyword, max_results=max_results)
            if not isinstance(collection, CollectionResult):
                raise TypeError("adapter returned a non-CollectionResult value")
        except Exception as exc:
            collection = CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=platform,
                message="provider request failed",
                metadata={"provider": "platform_adapter", "error_type": type(exc).__name__},
            )
        status = _canonical_status(collection)
        items = [item for item in (collection.items or []) if isinstance(item, dict)]
        captured_at = _now()
        records = [_native_record(item, platform, keyword, captured_at) for item in items]
        source_item_count = len(items)
        entity_mentions = []
        review_pending = []
        review_candidates = []
        if platform == "douyin" and prelaunch_scope is not None and collection.ok and records:
            entity_mentions = _prelaunch_entity_mentions(records, prelaunch_scope)
            review_pending = [item for item in entity_mentions if item["status"] != "EXACT_NAME_MENTION"]
            accepted_indices = [i for i, item in enumerate(entity_mentions) if item["status"] == "EXACT_NAME_MENTION"]
            review_candidates = [record for i, record in enumerate(records) if i not in accepted_indices]
            records = [records[i] for i in accepted_indices]
            items = [items[i] for i in accepted_indices]
            if not records:
                result = {
                    "ok": False, "status": "SCOPE_REVIEW_REQUIRED",
                    "error_type": "SOURCE_ENTITY_IDENTITY_UNCONFIRMED",
                    "platform": platform, "keyword": keyword,
                    "raw_count": source_item_count, "returned_count": source_item_count,
                    "imported": 0, "updated": 0, "canonical_synced": 0,
                    "read_only": True, "external_write": False,
                    "entity_mentions": entity_mentions,
                    "review_pending_count": len(review_pending),
                    "error": _status_message("SCOPE_REVIEW_REQUIRED"),
                }
                evidence_id = _write_prelaunch_evidence(
                    platform, keyword, result, started=started_at,
                    scope=prelaunch_scope, source_ids=[], review_candidates=review_candidates,
                )
                result["evidence_recorded"] = evidence_id is not None
                if evidence_id is None:
                    result["status"] = "EVIDENCE_WRITE_FAILED"
                _write_run_log(platform, keyword, started=started_at, finished=_now(),
                               fetched=source_item_count, accepted=0, rejected=source_item_count,
                               error=result["status"])
                return result
        if (maintenance_operator and prelaunch_scope is not None
                and not _authorize_prelaunch_public(
                    prelaunch_scope, keyword, platform,
                    maintenance_authorization=prelaunch_authorization,
                )):
            return {
                "ok": False, "status": "SCOPE_UNAUTHORIZED",
                "platform": platform, "keyword": keyword,
                "read_only": True, "external_write": False,
                "publish_authority": "human_manual_only",
            }
        if (platform == "douyin" and prelaunch_scope is not None
                and not maintenance_operator
                and not _authorize_prelaunch_douyin_manual(
                    prelaunch_scope, keyword, platform=platform,
                )):
            return {
                "ok": False, "status": "SCOPE_UNAUTHORIZED",
                "platform": platform, "keyword": keyword,
                "read_only": True, "external_write": False,
                "publish_authority": "human_manual_only",
            }
        prelaunch_observation_changed = False
        if prelaunch_scope is not None and platform in {"web_atom", "public_http", "douyin"} and records:
            from lumenis.shared.database.platform_content import platform_records_changed

            prelaunch_observation_changed = platform_records_changed(records, platform=platform)
        prelaunch_scope_conflict = bool(
            prelaunch_scope is not None and items
            and _prelaunch_scope_conflict(records, prelaunch_scope)
        )
        metadata = collection.metadata if isinstance(collection.metadata, dict) else {}
        provenance = {
            "provider": str(metadata.get("provider") or metadata.get("engine") or "platform_adapter")[:100],
            "source": str(metadata.get("source") or f"platform:{platform}")[:180],
            "collected_at": str(metadata.get("collected_at") or captured_at)[:40],
        }
        if metadata.get("error_type"):
            provenance["error_type"] = str(metadata["error_type"])[:80]
        if maintenance_operator:
            provenance["maintenance_plan_id"] = prelaunch_authorization.plan_id
            provenance["authorization_ref"] = prelaunch_authorization.authorization_ref
            provenance["source_version"] = prelaunch_authorization.source_version
            provenance["scope_version"] = prelaunch_authorization.scope_version

        import_result: Dict[str, Any] = {"imported": 0, "updated": 0, "failed": 0, "details": []}
        subject = {"subject_matches": 0, "canonical_synced": 0, "subjects": []}
        note_ids: List[str] = []
        if items and collection.ok and not prelaunch_scope_conflict:
            from .multi_platform_import import import_multi_platform_records

            import_result = import_multi_platform_records(records)
            note_ids = [
                str(detail.get("note_id"))
                for detail in import_result.get("details", [])
                if detail.get("note_id") and detail.get("status") in {"imported", "updated"}
            ]
            if prelaunch_scope is None:
                subject = _mark_subject_and_sync(note_ids, keyword)

        prelaunch_import_incomplete = (
            prelaunch_scope is not None and bool(items)
            and (len(note_ids) != len(records) or len(set(note_ids)) != len(note_ids))
        )
        canonical_failed = (prelaunch_scope is None and bool(note_ids)
                           and int(subject.get("canonical_synced", 0) or 0) != len(note_ids))
        final_status = ("SCOPE_CONFLICT" if prelaunch_scope_conflict else
                        "CANONICAL_SYNC_FAILED" if canonical_failed else status)
        if (not prelaunch_scope_conflict and not canonical_failed and collection.ok
                and (import_result.get("failed") or prelaunch_import_incomplete)):
            final_status = "IMPORT_FAILED"
        finished = _now()
        error = "" if final_status in {"SUCCESS", "NO_NEW_DATA"} else f"{final_status}: {_status_message(final_status)}"
        result = {
            "ok": bool(collection.ok and not prelaunch_scope_conflict and not import_result.get("failed")
                       and not prelaunch_import_incomplete and not canonical_failed),
            "status": final_status,
            "platform": platform,
            "keyword": keyword,
            "raw_count": int(collection.raw_count or len(items) or 0),
            "returned_count": source_item_count,
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
                "BMP" if prelaunch_scope and prelaunch_scope.get("domain_id") == "bmp"
                else "CTH"
            ),
            "consumer_views": ["CTH", "BMP"],
            "provenance": provenance,
            "entity_mentions": entity_mentions,
            "review_pending_count": len(review_pending),
        }
        if prelaunch_scope is not None and platform in {"public_http", "web_atom", "douyin"}:
            result["refresh_verified"] = False
        if prelaunch_scope is not None:
            if prelaunch_observation_changed or review_candidates:
                evidence_id = None
            elif platform in {"public_http", "web_atom", "douyin"}:
                evidence_id = _existing_prelaunch_observation_evidence(note_ids, platform)
            else:
                evidence_id = _existing_prelaunch_evidence(note_ids, prelaunch_scope)
            if evidence_id is None:
                evidence_id = _write_prelaunch_evidence(
                    platform, keyword, result, started=started_at,
                    scope=prelaunch_scope, source_ids=note_ids,
                    review_candidates=review_candidates,
                )
        else:
            evidence_id = _write_evidence(platform, keyword, result, started=started_at)
        result["evidence_recorded"] = isinstance(evidence_id, int) and evidence_id > 0
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
                    note_ids, prelaunch_scope,
                )
                if pending_scope_ids:
                    _persist_prelaunch_scope(pending_scope_ids, prelaunch_scope, evidence_id)
                canonical_synced = len(pending_scope_ids)
                if prelaunch_observation_changed:
                    canonical_synced = _sync_prelaunch_canonical_source_fields(
                        note_ids, prelaunch_scope,
                    )
                elif not prelaunch_observation_changed:
                    canonical_synced = len(note_ids)
                result["canonical_synced"] = canonical_synced
                result["scope_status"] = "VERIFIED"
                if platform in {"web_atom", "public_http", "douyin"}:
                    from lumenis.shared.database.platform_content import persist_verified_platform_records

                    result["native_fields_synced"] = persist_verified_platform_records(
                        records, platform=platform, note_ids=note_ids,
                        evidence_id=evidence_id, scope=prelaunch_scope,
                    )
                if platform in {"public_http", "web_atom", "douyin"}:
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
        # The signed success above covers only admitted source_ids. Keep the
        # overall request partial when other returned items still need review.
        if review_pending and result["ok"]:
            result.update({
                "ok": False, "status": "PARTIAL_SCOPE_REVIEW_REQUIRED",
                "error_type": "SOURCE_ENTITY_IDENTITY_UNCONFIRMED",
                "error": _status_message("PARTIAL_SCOPE_REVIEW_REQUIRED"),
                "scope_status": "PARTIAL", "refresh_verified": False,
            })
        accepted_count = int(result.get("canonical_synced", 0) or 0)
        _write_run_log(
            platform, keyword, started=started_at, finished=finished,
            fetched=int(collection.raw_count or len(items) or 0),
            accepted=accepted_count,
            rejected=max(0, source_item_count - accepted_count),
            error=result["error"],
        )
        return result
    finally:
        lock.release()


__all__ = [
    "SECONDARY_COLLECTION_PLATFORMS",
    "collect_search",
    "get_collection_surface",
]
