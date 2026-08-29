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
4. 结果统一入库（persist.py），并以 web_runs/web_sources 作为全局健康状态中心数据源，
   进程重启后健康灯仍可从数据库还原。
"""
import threading
import uuid
import time
import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional

from .registry import registry, register_default_adapters
from . import persist
from .risk_controller import risk_controller

# 需要真人浏览器（CDP）的平台：统一串行，降低风控风险
BROWSER_PLATFORMS = {"douyin", "instagram", "google", "xiaohongshu", "weibo", "bilibili"}

# 后台任务线程池（一次只跑一个采集任务，避免叠加触发风控）
_job_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="collect-job")
# 免登网页平台并行池
_web_pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="collect-web")
# 真人浏览器平台全局串行锁
_browser_lock = threading.Lock()

# 内存任务表：task_id -> 任务状态
_TASKS: Dict[str, dict] = {}
_TASKS_LOCK = threading.Lock()


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _run_one(platform: str, keyword: str, max_results: int, manual: bool = False) -> dict:
    """采集并入库单个平台。浏览器平台持锁串行；采集前经动态风控放行判断。"""
    adapter = registry.get(platform)
    if adapter is None:
        return {"platform": platform, "state": persist.STATE_FAIL, "success": False,
                "fetched": 0, "inserted": 0, "updated": 0, "error": "适配器未注册", "duration": 0}

    # 动态风控：自动任务严格遵循间隔/熔断；手动仅在需验证/熔断时硬拦截以保护账号
    allowed, reason = risk_controller.allow(platform, manual=manual)
    if not allowed:
        lv = risk_controller._of(platform).level
        state = "NEED_VERIFY" if lv == "NEED_VERIFY" else ("IP_RISK" if lv == "IP_RISK" else "COOLDOWN")
        return {"platform": platform, "display": getattr(adapter, "platform_display", platform),
                "state": state, "success": False, "skipped": True, "fetched": 0,
                "inserted": 0, "updated": 0, "error": reason, "duration": 0, "risk_level": lv}

    locked = platform in BROWSER_PLATFORMS
    try:
        if locked:
            _browser_lock.acquire()
        t0 = time.time()
        result = adapter.collect(keyword, max_results)
        result.duration_seconds = result.duration_seconds or (time.time() - t0)
        stats = persist.persist_result(platform, adapter.platform_display, result, keyword)
        # 六态驱动动态风控状态机
        risk_controller.report(platform, stats["state"], stats.get("error", ""))
        stats["risk_level"] = risk_controller._of(platform).level
        return stats
    except Exception as e:
        risk_controller.report(platform, persist.STATE_FAIL, str(e))
        return {"platform": platform, "display": getattr(adapter, "platform_display", platform),
                "state": persist.STATE_FAIL, "success": False, "fetched": 0,
                "inserted": 0, "updated": 0, "error": str(e), "duration": 0,
                "risk_level": risk_controller._of(platform).level}
    finally:
        if locked and _browser_lock.locked():
            _browser_lock.release()


def _job(task_id: str, keyword: str, platforms: List[str], max_results: int, manual: bool = True):
    """后台采集任务主体：网页组并行 + 浏览器组串行。"""
    task = _TASKS[task_id]
    web_targets = [p for p in platforms if p not in BROWSER_PLATFORMS]
    browser_targets = [p for p in platforms if p in BROWSER_PLATFORMS]

    def _mark(stats: dict):
        with _TASKS_LOCK:
            task["per_platform"][stats["platform"]] = stats
            task["done"] += 1

    # 免登网页平台并行
    if web_targets:
        futs = {_web_pool.submit(_run_one, p, keyword, max_results, manual): p for p in web_targets}
        for fut in futs:
            try:
                _mark(fut.result())
            except Exception as e:
                _mark({"platform": futs[fut], "state": persist.STATE_FAIL, "success": False,
                       "fetched": 0, "inserted": 0, "updated": 0, "error": str(e), "duration": 0})

    # 真人浏览器平台串行（持锁，逐个跑，最稳）
    for p in browser_targets:
        _mark(_run_one(p, keyword, max_results, manual))

    with _TASKS_LOCK:
        per = list(task["per_platform"].values())
        task["status"] = "finished"
        task["finished_at"] = _now()
        task["total_fetched"] = sum(s.get("fetched", 0) for s in per)
        task["total_inserted"] = sum(s.get("inserted", 0) for s in per)
        task["total_updated"] = sum(s.get("updated", 0) for s in per)


def start_collect(keyword: str, platforms: Optional[List[str]] = None,
                  max_results: int = 20, manual: bool = True) -> str:
    """启动一次后台采集，返回 task_id。manual=True 为用户手动触发。"""
    if not registry.list_platforms():
        register_default_adapters()
    targets = platforms or registry.list_platforms()
    task_id = uuid.uuid4().hex[:12]
    with _TASKS_LOCK:
        _TASKS[task_id] = {
            "task_id": task_id, "keyword": keyword, "status": "running",
            "total": len(targets), "done": 0,
            "per_platform": {}, "started_at": _now(), "finished_at": "",
            "total_fetched": 0, "total_inserted": 0, "total_updated": 0,
        }
    _job_pool.submit(_job, task_id, keyword, targets, max_results, manual)
    return task_id


def get_task(task_id: str) -> Optional[dict]:
    """查询任务进度（返回副本）。"""
    with _TASKS_LOCK:
        t = _TASKS.get(task_id)
        return dict(t) if t else None


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
