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
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List

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


def _adapter_health(platform: str) -> Dict[str, Any]:
    try:
        adapter = _get_runtime_adapter(platform)
        result = adapter.health_check()
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
        record.update({"aweme_id": content_id, "sec_uid": item.get("author_id") or "", "create_time": publish_date})
        record.update({"digg_count": item.get("likes"), "comment_count": item.get("comments"),
                       "collect_count": item.get("collects"), "share_count": item.get("shares")})
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
        record.update({
            "content_id": content_id,
            "published_at": publish_date,
        })
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
                   operator: str = "human") -> Dict[str, Any]:
    """Run one explicit, read-only platform search and persist its evidence."""
    if str(operator or "").strip().lower() not in {"human", "human_ui"}:
        raise PermissionError("该采集入口只接受人工触发")
    platform, keyword, max_results = _validate_request(platform, keyword, max_results)
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

    now_local = datetime.now()
    used_today = _daily_action_count(platform, now_local)
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

        health = _adapter_health(platform)
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
        metadata = collection.metadata if isinstance(collection.metadata, dict) else {}
        provenance = {
            "provider": str(metadata.get("provider") or metadata.get("engine") or "platform_adapter")[:100],
            "source": str(metadata.get("source") or f"platform:{platform}")[:180],
            "collected_at": str(metadata.get("collected_at") or captured_at)[:40],
        }
        if metadata.get("error_type"):
            provenance["error_type"] = str(metadata["error_type"])[:80]

        import_result: Dict[str, Any] = {"imported": 0, "updated": 0, "failed": 0, "details": []}
        subject = {"subject_matches": 0, "canonical_synced": 0, "subjects": []}
        note_ids: List[str] = []
        if items and collection.ok:
            from .multi_platform_import import import_multi_platform_records

            import_result = import_multi_platform_records(records)
            note_ids = [
                str(detail.get("note_id"))
                for detail in import_result.get("details", [])
                if detail.get("note_id") and detail.get("status") in {"imported", "updated"}
            ]
            subject = _mark_subject_and_sync(note_ids, keyword)

        canonical_failed = bool(note_ids) and int(subject.get("canonical_synced", 0) or 0) != len(note_ids)
        final_status = "CANONICAL_SYNC_FAILED" if canonical_failed else status
        if not canonical_failed and collection.ok and import_result.get("failed"):
            final_status = "IMPORT_FAILED"
        finished = _now()
        error = "" if final_status in {"SUCCESS", "NO_NEW_DATA"} else f"{final_status}: {_status_message(final_status)}"
        result = {
            "ok": bool(collection.ok and not import_result.get("failed") and not canonical_failed),
            "status": final_status,
            "platform": platform,
            "keyword": keyword,
            "raw_count": int(collection.raw_count or len(items) or 0),
            "returned_count": len(items),
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
            "product_owner": "CTH",
            "consumer_views": ["CTH", "BMP"],
            "provenance": provenance,
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
        _write_run_log(
            platform, keyword, started=started_at, finished=finished,
            fetched=int(collection.raw_count or len(items) or 0),
            accepted=int(subject.get("subject_matches", 0) or 0),
            rejected=max(0, len(items) - int(subject.get("subject_matches", 0) or 0)),
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
