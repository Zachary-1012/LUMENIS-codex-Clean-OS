# -*- coding: utf-8 -*-
"""
采集编排服务（Collection Orchestrator）
======================================
把“注册表 → 适配器采集 → 统一入库 → 健康状态”串成一条可被 Web 调用的后台流水线。

设计原则（对应生产级要求）：
1. 后台任务化：真人浏览器单平台就要 7~12s，HTTP 请求不阻塞等待，返回 task_id 轮询；
2. 分组调度：免登网页平台线程池并行；真人浏览器平台（同一 CDP Profile）全局加锁串行，
   杜绝多标签并发操作同一浏览器而触发风控/封号；
3. 六态如实：每平台 SUCCESS/EMPTY/AUTH_REQUIRED/CAPTCHA/BLOCKED/NETWORK_ERROR/FAIL，
   风控绝不显示成“0条”；
4. 结果经现有 secondary_collection 单一 owner 写入 Source/Evidence/Canonical；
   TaskQueue 保存运营进度，健康投影沿用 web_runs/web_sources，不另造来源事实。
"""
import threading
import uuid
import time
import datetime
from contextlib import ExitStack, contextmanager
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional

from .registry import registry, register_default_adapters
from . import persist
from .risk_controller import risk_controller

# 需要真人浏览器（CDP）的平台：统一串行，降低风控风险
BROWSER_PLATFORMS = {"douyin", "instagram", "google", "xhs", "xiaohongshu", "weibo", "bilibili",
                    "facebook", "x"}

# 后台任务线程池（一次只跑一个采集任务，避免叠加触发风控）
_job_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="collect-job")
# 免登网页平台并行池
_web_pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="collect-web")
# 真人浏览器平台全局串行锁
_browser_lock = threading.Lock()

# 内存任务表：task_id -> 任务状态
_TASKS: Dict[str, dict] = {}
_TASKS_LOCK = threading.Lock()
_ACTIVE_JOBS: set[str] = set()
_HUMAN_BROWSER_LEASE: Optional[tuple[str, str]] = None


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def browser_worker_idle() -> bool:
    """Return whether the shared browser collector lock is currently free."""
    with _TASKS_LOCK:
        return not _browser_lock.locked() and _HUMAN_BROWSER_LEASE is None


@contextmanager
def platform_activity_lock(platform: str):
    """Reuse the scheduler's cross-process attempt lock for this platform.

    The lock covers scheduled baseline acquisition and Collector browser runs;
    it is an operational mutex only and contains no task, session, or business data.
    """
    from lumenis.shared.database import main_db_path
    from lumenis.system.collector.adapters.platform_naming import normalize_platform
    from lumenis.system.collector.adapters.scheduling.store import ScheduleDecisionStore

    exact_platform = str(platform or "").strip().casefold()
    canonical = normalize_platform(exact_platform) or exact_platform
    if not canonical:
        raise RuntimeError("COLLECTOR_PLATFORM_LOCK_ID_UNAVAILABLE")
    lock_ids = {canonical}
    # Existing purpose-baseline plans use the historical `xhs` key.
    if canonical == "xiaohongshu":
        lock_ids.add("xhs")
    store = ScheduleDecisionStore(main_db_path())
    with ExitStack() as stack:
        for lock_id in sorted(lock_ids):
            acquired = stack.enter_context(store.platform_attempt_lock(lock_id))
            if acquired is not True:
                yield False
                return
        yield True


def human_browser_lease_owned(task_id: str, platform: str) -> bool:
    """Verify the same live Collector task owns the exclusive human-browser lane."""
    task_id = str(task_id or "").strip()
    platform = str(platform or "").strip().casefold()
    with _TASKS_LOCK:
        return (_HUMAN_BROWSER_LEASE == (task_id, platform)
                and _browser_lock.locked()
                and _verification_task_locked(task_id, platform) is not None)


def human_browser_return_lease_owned(task_id: str, platform: str) -> bool:
    """Verify an existing human lease for safe return after task-state changes.

    This is deliberately return-only: opening a human session still requires the
    completed NEED_VERIFY task contract in ``_verification_task_locked``.
    """
    task_id = str(task_id or "").strip()
    platform = str(platform or "").strip().casefold()
    with _TASKS_LOCK:
        task = _TASKS.get(task_id)
        state = task.get("human_browser") if isinstance(task, dict) else None
        return (
            _HUMAN_BROWSER_LEASE == (task_id, platform)
            and _browser_lock.locked()
            and isinstance(task, dict)
            and task.get("manual") is True
            and isinstance(state, dict)
            and state.get("platform") == platform
            and state.get("status") in {"ACTIVE", "BLOCKED", "RETURNING_BACKGROUND"}
        )


def _verification_task_locked(task_id: str, platform: str) -> dict | None:
    task = _TASKS.get(str(task_id or "").strip())
    result = (task.get("per_platform") or {}).get(platform) if isinstance(task, dict) else None
    if (not isinstance(task, dict) or task.get("manual") is not True
            or task.get("status") != "finished" or not isinstance(result, dict)
            or str(result.get("state") or "").upper()
            not in {"AUTH_REQUIRED", "CAPTCHA", "NEED_VERIFY"}):
        return None
    return task


def _same_platform(left: str, right: str) -> bool:
    try:
        from lumenis.system.collector.adapters.config import resolve_platform_config_key
        return resolve_platform_config_key(left) == resolve_platform_config_key(right)
    except (KeyError, TypeError, ValueError):
        return str(left or "").casefold() == str(right or "").casefold()


def begin_human_browser(task_id: str, platform: str) -> bool:
    """Reserve the existing Collector browser lane for one authorized human step."""
    global _HUMAN_BROWSER_LEASE
    task_id = str(task_id or "").strip()
    platform = str(platform or "").strip().casefold()
    with _TASKS_LOCK:
        task = _verification_task_locked(task_id, platform)
        if task is None or _HUMAN_BROWSER_LEASE is not None:
            return False
        for other_id, other in _TASKS.items():
            if other_id == task_id or other.get("status") != "running":
                continue
            if any(_same_platform(str(item), platform)
                   for item in other.get("platforms", [])):
                return False
        if not _browser_lock.acquire(blocking=False):
            return False
        state = task.get("human_browser")
        if isinstance(state, dict) and state.get("status") not in {
                "RETURNED_BACKGROUND", "BLOCKED"}:
            _browser_lock.release()
            return False
        _HUMAN_BROWSER_LEASE = (task_id, platform)
        task["human_browser"] = {"platform": platform, "status": "OPENING"}
        return True


def begin_background_browser_return(task_id: str, platform: str) -> bool:
    """Keep the same task's exclusive browser lane while restoring BACKGROUND."""
    task_id = str(task_id or "").strip()
    platform = str(platform or "").strip().casefold()
    with _TASKS_LOCK:
        task = _TASKS.get(task_id)
        state = task.get("human_browser") if isinstance(task, dict) else None
        if (_HUMAN_BROWSER_LEASE != (task_id, platform) or _browser_lock.locked() is not True
                or task is None or task.get("manual") is not True
                or not isinstance(state, dict)
                or state.get("platform") != platform
                or state.get("status") not in {"ACTIVE", "BLOCKED"}):
            return False
        state["status"] = "RETURNING_BACKGROUND"
        return True


def update_human_browser_state(task_id: str, platform: str, status: str,
                               *, release_lease: bool = False) -> bool:
    """Update the same task's human-browser state without creating another queue."""
    global _HUMAN_BROWSER_LEASE
    task_id = str(task_id or "").strip()
    platform = str(platform or "").strip().casefold()
    allowed = {"ACTIVE", "RETURNED_BACKGROUND", "BLOCKED"}
    if status not in allowed:
        return False
    with _TASKS_LOCK:
        task = (_verification_task_locked(task_id, platform) if status == "ACTIVE"
                else _TASKS.get(task_id))
        if (not isinstance(task, dict) or task.get("manual") is not True
                or _HUMAN_BROWSER_LEASE != (task_id, platform)
                or not _browser_lock.locked()):
            return False
        state = task.get("human_browser")
        if not isinstance(state, dict) or state.get("platform") != platform:
            return False
        if (status == "RETURNED_BACKGROUND"
                and state.get("status") != "RETURNING_BACKGROUND"):
            return False
        if (status == "BLOCKED" and release_lease
                and state.get("status") not in {"OPENING", "ACTIVE"}):
            return False
        state["status"] = status
        if status == "RETURNED_BACKGROUND":
            state["session_state"] = "NEED_VERIFY"
        if release_lease:
            _HUMAN_BROWSER_LEASE = None
            _browser_lock.release()
        return True


class CollectorAdmissionError(PermissionError):
    def __init__(self, result):
        self.result = result
        super().__init__(result.get("status", "COLLECTOR_ADMISSION_DENIED"))


def _queue():
    from lumenis.system.collector.guard.task_queue import TaskQueue
    return TaskQueue()


def _queue_id(task_id):
    value = str(task_id or "")
    return int(value[3:]) if value.startswith("cq-") and value[3:].isdigit() else None


def _admit(actor, scope, platforms, keyword, max_results):
    from lumenis.system.collector.adapters.secondary_collection import (
        _manual_collection_guard, _validate_request,
    )
    if not isinstance(actor, dict) or type(actor.get("id")) is not int:
        raise CollectorAdmissionError({"ok": False, "status": "AUTH_REQUIRED"})
    if not isinstance(platforms, list) or not platforms or len(platforms) > 32:
        raise ValueError("An explicit bounded platform list is required")
    canonical = []
    for platform in platforms:
        platform = "xiaohongshu" if platform == "xhs" else platform
        platform, keyword, max_results = _validate_request(platform, keyword, max_results)
        if platform in canonical:
            continue
        _, error = _manual_collection_guard(actor, scope, platform, keyword, max_results)
        if error is not None:
            raise CollectorAdmissionError(error)
        canonical.append(platform)
    return canonical, keyword, max_results


def _run_one(platform, keyword, max_results, manual=True, *, actor=None, scope=None, attempt_guard=None, operation_key=None):
    """Compatibility caller of the single permission/Evidence/Canonical owner."""
    from lumenis.system.collector.adapters.secondary_collection import collect_search
    from contextlib import nullcontext
    browser_platform = platform in BROWSER_PLATFORMS
    with (_browser_lock if browser_platform else nullcontext()):
        with (platform_activity_lock(platform) if browser_platform else nullcontext(True)) as acquired:
            if acquired is not True:
                return {"platform": platform, "state": "BUSY", "success": False}
            result = collect_search(platform, keyword, max_results=max_results,
                                    operator="human", actor=actor, scope=scope,
                                    attempt_guard=attempt_guard, operation_key=operation_key)
    # Keep operational references and counts, never a second raw content store.
    keys = ("ok", "status", "error_type", "approval_resource", "evidence_ref",
            "evidence_recorded", "canonical_synced", "native_fields_synced",
            "refresh_verified", "scope_status", "returned_count", "imported", "updated",
            "read_only", "external_write", "next_cursor", "continuation_required",
            "task_commit_evidence_ref", "commit_reconciled", "network_attempted", "historical_commit_verified",
            "new_collection_required", "retry_safe", "recovery_action", "source_status", "wait_seconds")
    stats = {key: result[key] for key in keys if key in result}
    transport_error = (result.get("provenance") or {}).get("error_type")
    stats["retryable_transport_failure"] = (result.get("status") == "PROVIDER_UNAVAILABLE"
        and transport_error in {"ConnectionError", "Timeout", "ConnectTimeout", "ReadTimeout", "TimeoutError"})
    stats.update(platform=platform, state=result.get("status", "FAIL"),
                 success=result.get("ok") is True,
                 fetched=result.get("returned_count", 0),
                 inserted=result.get("imported", 0), updated=result.get("updated", 0))
    return stats


def _job(task_id, *_legacy_args):
    """Consume this durable task; retries preserve completed platform checkpoints."""
    queue = _queue()
    identity = _queue_id(task_id)
    with _TASKS_LOCK:
        _ACTIVE_JOBS.add(task_id)
    worker = "collector-" + uuid.uuid4().hex
    try:
        while True:
            row = queue.get(identity)
            if row is None or row["status"] in {"done", "failed"}:
                return
            if row["status"] == "running":
                # Another live process owns it. Never steal its attempt.
                return
            delay = max(0, row["scheduled_at"] - time.time())
            if delay:
                time.sleep(min(delay, 4))
                continue
            task = queue.dequeue(worker_id=worker, lease_owner=worker, task_id=identity)
            if task is None:
                return
            receipt = {key: task[key] for key in ("run_id", "worker_id", "lease_owner")}
            get_task(task_id)  # Keep the existing human-browser lane's live task cache current.
            payload = task["payload"]
            if time.time() >= float(payload.get("deadline_at", task["created_at"] + _manual_window_seconds(payload["platforms"]))):
                existing_per = dict((payload.get("progress") or {}).get("per_platform") or {})
                deadline_progress = {"per_platform": {platform: existing_per[platform]
                    if existing_per.get(platform, {}).get("success") is True else {
                    **existing_per.get(platform, {}), "platform": platform,
                    "state": "TASK_DEADLINE_EXCEEDED", "success": False,
                    "network_attempted": False} for platform in payload["platforms"]}, "waiting_user": False}
                queue.save_progress(identity, deadline_progress, **receipt)
                queue.fail(identity, "TASK_DEADLINE_EXCEEDED", retryable=False, **receipt)
                return
            progress = payload.get("progress") or {}
            per = dict(progress.get("per_platform") or {})
            stop = threading.Event()
            def renew():
                heartbeat_queue = _queue()
                try:
                    while not stop.wait(15):
                        if not heartbeat_queue.heartbeat(identity, worker,
                                run_id=receipt["run_id"], lease_owner=worker):
                            return
                finally:
                    heartbeat_queue.close()
            heartbeat = threading.Thread(target=renew, daemon=True)
            heartbeat.start()
            try:
                for platform in payload["platforms"]:
                    if per.get(platform, {}).get("success") is True:
                        continue
                    if not queue.heartbeat(identity, worker, run_id=receipt["run_id"], lease_owner=worker):
                        return
                    try:
                        if not payload.get("operation_id"):
                            raise RuntimeError("LEGACY_COLLECTION_COMMIT_UNKNOWN")
                        stats = _run_one(platform, payload["keyword"], payload["max_results"],
                                         actor={"id": payload["actor_id"]}, scope=payload["scope"],
                                         operation_key=(payload["operation_id"] + ":" + platform) if payload.get("operation_id") else None,
                                         attempt_guard=lambda: queue.attempt_guard(identity, **receipt))
                    except Exception as exc:
                        stats = {"platform": platform, "state": "FAIL", "success": False,
                                 "error_type": type(exc).__name__}
                        if str(exc) == "LEGACY_COLLECTION_COMMIT_UNKNOWN":
                            stats.update(state="LEGACY_COLLECTION_COMMIT_UNKNOWN",
                                error_type="LEGACY_COLLECTION_COMMIT_UNKNOWN", retry_safe=False,
                                new_collection_required=True,
                                recovery_action="REVIEW_EXISTING_SOURCES_THEN_CREATE_NEW_REQUEST")
                    if stats.get("success") is not True and time.time() >= float(payload.get("deadline_at", task["created_at"] + _manual_window_seconds(payload["platforms"]))):
                        stats.update(state="TASK_DEADLINE_EXCEEDED", retry_safe=False)
                    per[platform] = stats
                    progress = {"per_platform": per, "updated_at": _now(), "waiting_user": False}
                    if not queue.save_progress(identity, progress, **receipt):
                        return
                if all(per.get(platform, {}).get("success") is True for platform in payload["platforms"]):
                    queue.ack(identity, **receipt)
                    return
                incomplete = [value for value in per.values() if value.get("success") is not True]
                if any(value.get("state") == "TASK_DEADLINE_EXCEEDED" for value in incomplete):
                    queue.fail(identity, "TASK_DEADLINE_EXCEEDED", retryable=False, **receipt)
                    return
                if incomplete and all(value.get("state") == "RATE_LIMITED"
                        and value.get("error_type") == "LOCAL_RATE_LIMIT" for value in incomplete):
                    delay = max(0.1, min(60.0, max(float(value.get("wait_seconds", 1)) for value in incomplete)))
                    if not queue.defer(identity, delay_seconds=delay, **receipt):
                        return
                    continue
                # Permission/challenge states must await an explicit user action,
                # never trigger repeated network acquisition automatically.
                retryable = {"NETWORK_ERROR", "RATE_LIMITED", "BUSY"}
                waiting_user = any(value.get("success") is not True and value.get("state") not in retryable
                                   and value.get("retryable_transport_failure") is not True
                                   for value in per.values())
                progress["waiting_user"] = waiting_user
                queue.save_progress(identity, progress, **receipt)
                queue.fail(identity, "COLLECTION_NOT_COMPLETED", **receipt)
                if waiting_user:
                    return
            finally:
                stop.set()
                heartbeat.join(timeout=2)
    finally:
        queue.close()
        with _TASKS_LOCK:
            _ACTIVE_JOBS.discard(task_id)


def _manual_window_seconds(platforms):
    """Use the existing deterministic server scheduling policy, never client budget."""
    from lumenis.system.collector.adapters.scheduling.policy import DEFAULT_POLICIES, PlatformSchedulePolicy
    windows = []
    for platform in platforms:
        key = "xhs" if platform == "xiaohongshu" else platform
        policy = DEFAULT_POLICIES.get(key) or PlatformSchedulePolicy(platform=key)
        windows.append(max(1, min(int(policy.run_duration_manual), policy.MAX_MANUAL_DURATION)))
    return min(windows) if windows else PlatformSchedulePolicy(platform="manual").run_duration_manual


def start_collect(keyword: str, platforms: Optional[List[str]] = None,
                  max_results: int = 20, manual: bool = True,
                  actor_ref: Optional[str] = None, *, actor=None, scope=None) -> str:
    """Admit exact actor/scope requests before durable enqueue; no implicit platforms."""
    if manual is not True:
        raise ValueError("Automatic collection requires the signed scheduler owner")
    targets, keyword, max_results = _admit(actor, scope, platforms, keyword, max_results)
    queue = _queue()
    try:
        identity = queue.enqueue("collector_source", {
            "keyword": keyword, "platforms": targets, "max_results": max_results,
            "actor_id": actor["id"], "scope": dict(scope), "manual": True,
            "operation_id": uuid.uuid4().hex, "deadline_at": time.time() + _manual_window_seconds(targets),
        })
    finally:
        queue.close()
    task_id = "cq-" + str(identity)
    _job_pool.submit(_job, task_id)
    return task_id


def get_task(task_id: str) -> Optional[dict]:
    """Read durable progress after restart; polling never executes acquisition."""
    identity = _queue_id(task_id)
    if identity is None:
        with _TASKS_LOCK:
            t = _TASKS.get(task_id)
            return {key: value for key, value in t.items() if not key.startswith("_")} if t else None
    queue = _queue()
    try:
        row = queue.get(identity)
    finally:
        queue.close()
    if row is None or row["task_type"] != "collector_source":
        return None
    payload = row["payload"]
    per = (payload.get("progress") or {}).get("per_platform") or {}
    new_required = any(item.get("new_collection_required") is True for item in per.values())
    expired = row["status"] == "failed" and row["last_error"] == "TASK_DEADLINE_EXCEEDED"
    terminal = row["status"] in {"done", "failed"}
    waiting = row["status"] == "pending" and (payload.get("progress") or {}).get("waiting_user") is True
    with _TASKS_LOCK:
        active = task_id in _ACTIVE_JOBS
    task = {
        "task_id": task_id, "keyword": payload["keyword"], "manual": True,
        "platforms": payload["platforms"], "scope": payload["scope"],
        "status": "finished" if terminal or waiting else row["status"],
        "queue_status": row["status"], "success": row["status"] == "done",
        "total": len(payload["platforms"]), "done": len(per), "per_platform": per,
        "started_at": row["created_at"], "finished_at": row["last_success_at"] or "",
        "attempts": row["attempts"], "resume_required": (row["status"] == "pending" or expired) and not active and not new_required,
        "deadline_expired": expired,
        "new_collection_required": new_required,
        "waiting_user": waiting,
        "total_fetched": sum(item.get("fetched", 0) or 0 for item in per.values()),
        "total_inserted": sum(item.get("inserted", 0) or 0 for item in per.values()),
        "total_updated": sum(item.get("updated", 0) or 0 for item in per.values()),
    }
    with _TASKS_LOCK:
        prior = _TASKS.get(task_id) or {}
        _TASKS[task_id] = {**task, "_actor_ref": "actor:" + str(payload["actor_id"])}
        if "human_browser" in prior:
            _TASKS[task_id]["human_browser"] = prior["human_browser"]
    return task


def get_task_owner(task_id: str) -> Optional[str]:
    identity = _queue_id(task_id)
    if identity is not None:
        queue = _queue()
        try:
            row = queue.get(identity)
            if row and row["task_type"] == "collector_source":
                return "actor:" + str(row["payload"]["actor_id"])
        finally:
            queue.close()
        return None
    with _TASKS_LOCK:
        task = _TASKS.get(str(task_id or "").strip())
        return task.get("_actor_ref") if isinstance(task, dict) else None


def resume_collect(task_id, *, actor, scope):
    """Explicit resume preserves input identity and rechecks current approval."""
    task = get_task(task_id)
    if (task is None or get_task_owner(task_id) != "actor:" + str(actor.get("id"))
            or task.get("scope") != scope):
        raise CollectorAdmissionError({"ok": False, "status": "SCOPE_UNAUTHORIZED"})
    if (task["queue_status"] == "done" or (task["queue_status"] == "failed" and not task.get("deadline_expired"))
            or task.get("new_collection_required") is True):
        return task
    queue = _queue()
    try:
        row = queue.get(_queue_id(task_id))
        payload = row["payload"]
        _admit(actor, scope, payload["platforms"], payload["keyword"], payload["max_results"])
        if task.get("deadline_expired"):
            if not queue.resume_expired(_queue_id(task_id), time.time() + _manual_window_seconds(payload["platforms"])):
                raise CollectorAdmissionError({"ok": False, "status": "COLLECTION_RESUME_CONFLICT"})
        else:
            queue.reap_stale(120, task_id=_queue_id(task_id))
    finally:
        queue.close()
    _job_pool.submit(_job, task_id)
    return get_task(task_id)


def _state_from_row(fetched: int, error: str) -> str:
    if not error:
        return persist.STATE_SUCCESS if fetched > 0 else persist.STATE_EMPTY
    low = error.lower()
    if any(h in low for h in persist._AUTH_HINTS):
        return persist.STATE_AUTH_REQUIRED
    if any(h in low for h in persist._CAPTCHA_HINTS):
        return persist.STATE_CAPTCHA
    if any(h in low for h in persist._BLOCK_HINTS):
        return persist.STATE_BLOCKED
    if any(h in low for h in persist._NET_HINTS):
        return persist.STATE_NETWORK_ERROR
    return persist.STATE_FAIL


def get_health() -> List[dict]:
    """全局采集健康：以注册表平台为基准，结合 web_sources/web_runs 还原每平台最近六态。"""
    if not registry.list_platforms():
        register_default_adapters()
    con = persist.get_conn()
    health = []
    risk_map = {x["platform"]: x for x in risk_controller.snapshot()}
    try:
        for name in registry.list_platforms():
            adapter = registry.get(name)
            row = con.execute(
                "SELECT last_run_at,last_success_at,last_error,item_count FROM web_sources WHERE source_key=?",
                (name,)).fetchone()
            last = con.execute(
                """SELECT fetched,error,finished_at FROM web_runs WHERE adapter=?
                   ORDER BY id DESC LIMIT 1""", (name,)).fetchone()
            if last:
                state = _state_from_row(last["fetched"] or 0, last["error"] or "")
                fetched, finished = last["fetched"], last["finished_at"]
            elif row:
                state = _state_from_row(row["item_count"] or 0, row["last_error"] or "")
                fetched, finished = row["item_count"], row["last_run_at"]
            else:
                state, fetched, finished = "IDLE", 0, ""
            health.append({
                "platform": name,
                "display": getattr(adapter, "platform_display", name),
                "needs_browser": name in BROWSER_PLATFORMS,
                "state": state,
                "fetched": fetched or 0,
                "last_run": finished or (row["last_run_at"] if row else ""),
                "last_error": (row["last_error"] if row else "") or "",
                "breaker": getattr(getattr(adapter, "breaker", None), "state", "closed"),
                "risk": risk_map.get(name),
            })
    finally:
        con.close()
    return health
