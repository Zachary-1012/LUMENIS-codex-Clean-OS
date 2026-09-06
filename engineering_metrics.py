# -*- coding: utf-8 -*-
"""
engineering_metrics.py — 序境工程度量能力（P0-E，可观测性标准 Capability）

职责（分工明确，不重复现有体系）：
- system_health_api.py 负责「组件健康红绿灯」——本模块直接复用 system_health_summary()，不重写
- collector_guard/metrics.py 负责「采集器性能窗口」——内存态，本模块不接管
- 本模块新增「任务级闭环度量」：从 staging/zell-trace.jsonl 计算
  Task Completion Rate / in-progress / 阶段分布 / 任务耗时 / 未闭合清单
  ——这是 P0 评价体系（Task Completion Rate / Recovery Rate）的核心落地。

终端适配（零号序列：Web/App/Mini 共用同一业务逻辑/数据，仅做终端适配）：
- 本模块输出**纯结构化 JSON**（不绑任何 HTML/终端），Web 表格/Chart、App Card、
  Mini 简化视图消费同一数据源；各终端只做展示层适配，不复制口径。
- API 端点：GET /api/engineering-metrics  →  {ok, data: full_snapshot()}

证据下钻（零号序列：任何指标必须可下钻至来源/原始数据/Evidence）：
- 每条 task 名即 ZELL trace 的证据 key（task 字段）；done_ts/open_tasks 可直接
  回查 staging/zell-trace.jsonl 原始行；system_health 带 source 函数名。

数据源（Source → Evidence → Insight 原则）：
- staging/zell-trace.jsonl：ZELL 闭环事件（begin / phase / done，task + ts + outcome）
- system_health_api.system_health_summary()：4 子灯健康摘要

用法：
- 作为模块：from engineering_metrics import full_snapshot
- 独立运行：python engineering_metrics.py  （打印统一快照 JSON）
- 仅计算闭环：python engineering_metrics.py --closed-loop
"""

from __future__ import annotations

# ---- API 契约（schema v3，Web/App/Mini 通用）----
# GET /api/engineering-metrics
# {
#   "ok": true,
#   "data": {
#     "engineered_metrics_version": 4,   # v4 新增 alert 健康告警分级
#     "generated_ts": "<ISO8601>",
#     "task_closed_loop": {
#       "total_tasks": int,            # 已 begin 的唯一任务数
#       "closed_tasks": int,           # 已 done 的任务数
#       "failed_tasks": int,           # v3：显式 fail 且未 done 的任务数
#       "task_completion_rate": float, # 0.0-1.0，closed/total
#       "recovery_rate": float|null,   # v3：closed/(closed+failed)，成功恢复率
#       "in_progress_tasks": int,      # total-closed-failed
#       "open_tasks": [str],           # 挂起任务（begin 无 done 无 fail）
#       "failed_task_list": [{task,reason}],  # v3：失败明细（可下钻）
#       "phase_distribution": {str:int},# 阶段事件计数（architecture/code/test/runtime/evaluation/research）
#       "task_durations_min": [{task,duration_min}],  # 已闭合任务耗时（可下钻）
#       "recent_closed": [{task,done_ts}],            # 最近闭合（可下钻）
#       "avg_duration_min": float|null,               # 已闭合平均耗时
#       "source": str                 # 证据源：staging/zell-trace.jsonl
#     },
#     "collector_performance": {       # v2：采集性能趋势（GuardMetrics 落盘）
#       "samples": int,                # 已落盘快照数
#       "latest": {total/success/failure/success_rate/avg_latency/p95/last_error/ts},
#       "window_success_rate": float,  # 近 N 条快照成功率均值（默认 20）
#       "window_avg_latency": float,   # 近 N 条快照平均延迟均值
#       "source": str                  # data/metrics/collector-metrics.jsonl
#     },
#     "scheduling_health": {           # v3：调度健康（PlatformSchedulePlanner）
#       "platforms": {platform: state},# 各平台调度状态（可下钻）
#       "degraded": bool|null,         # planner 不可用时为 true
#       "source": str
#     },
#     "system_health": {
#       "engineered": "system_health",
#       "health": { status/子灯... },  # 复用 system_health_summary
#       "source": str
#     },
#     "alert": {                       # v4：健康告警分级（只读，无副作用）
#       "level": "OK|WARN|CRIT",       # 按最严重 check 取级
#       "checks": [{
#         "name": "recovery_rate|collector_success_rate|scheduling|system_health",
#         "level": "OK|WARN|CRIT",
#         "value": number|null,
#         "warn_threshold": number|null,
#         "crit_threshold": number|null,
#         "message": str
#       }],
#       "generated_ts": str
#     }
#   }
# }
# 契约版本：v1（2026-09-04）→ v2（+collector_performance）→ v3（+scheduling_health/failed/recovery）
#   → v4（+alert 健康告警分级）。任何口径变更须 bump engineered_metrics_version 并同步 OSAI 契约文档。
API_CONTRACT_VERSION = 4

import json
import os
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# 仓库根目录定位（本文件位于仓库根）
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TRACE_PATH = os.path.join(_REPO_ROOT, "staging", "zell-trace.jsonl")

# ZELL 闭环：begin=任务开启，done=任务闭合，fail=显式失败（P0-E 失败可见性）；phase 事件用业务阶段名
BEGIN_EVENT = "begin"
DONE_EVENT = "done"
FAIL_EVENT = "fail"
PHASE_EVENTS = {"architecture", "code", "test", "runtime", "evaluation", "research"}


def _load_trace(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """读取 ZELL trace，容错：文件不存在/空/坏行均不抛异常。"""
    p = path or DEFAULT_TRACE_PATH
    recs: List[Dict[str, Any]] = []
    if not os.path.exists(p):
        return recs
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    recs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # 坏行跳过，不致命
    except OSError:
        return recs
    return recs


def _parse_ts(ts: str) -> Optional[datetime]:
    """解析 ISO 时间戳，兼容无时区 / 带 Z / 带微秒。"""
    if not ts:
        return None
    s = str(ts).strip()
    try:
        s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def task_closed_loop_metrics(trace_path: Optional[str] = None) -> Dict[str, Any]:
    """从 ZELL trace 计算任务闭环度量（本模块核心新增能力）。

    返回字段全部可下钻：每项带 counts + 原始 task 清单。
    """
    recs = _load_trace(trace_path)
    # 按 task 聚合
    tasks: Dict[str, Dict[str, Any]] = {}
    for r in recs:
        task = (r.get("task") or "unknown").strip()
        ev = (r.get("event") or "").strip()
        t = tasks.setdefault(task, {"begin": None, "done": None, "failed": None,
                                    "fail_reason": "", "phases": [], "outcomes": []})
        ts = _parse_ts(r.get("ts"))
        if ev == BEGIN_EVENT and t["begin"] is None:
            t["begin"] = ts
        elif ev == DONE_EVENT and t["done"] is None:
            t["done"] = ts
        elif ev == FAIL_EVENT and t["failed"] is None:
            t["failed"] = ts
            t["fail_reason"] = str(r.get("reason") or r.get("outcome") or "")[:160]
        if ev in PHASE_EVENTS:
            t["phases"].append({"phase": ev, "ts": _parse_ts(r.get("ts"))})
        if r.get("outcome"):
            t["outcomes"].append(str(r["outcome"]))

    total = len(tasks)
    closed = sum(1 for t in tasks.values() if t["done"] is not None)
    failed = sum(1 for t in tasks.values() if t["failed"] is not None and t["done"] is None)
    in_progress = total - closed - failed

    # 阶段分布：所有 phase 事件按阶段计数
    phase_counter = Counter(p["phase"] for t in tasks.values() for p in t["phases"])

    # 各任务耗时（begin→done，分钟）
    durations: List[Dict[str, Any]] = []
    for task, t in tasks.items():
        if t["begin"] and t["done"]:
            secs = (t["done"] - t["begin"]).total_seconds()
            durations.append({"task": task, "duration_min": round(secs / 60.0, 1)})

    # 未闭合任务清单（begin 无 done 且无 fail）——挂起可见性
    open_tasks = [task for task, t in tasks.items()
                  if t["done"] is None and t["failed"] is None]

    # 显式失败任务清单（fail 事件且未 done）——失败可见性
    failed_tasks = [{"task": task, "reason": t["fail_reason"]} for task, t in tasks.items()
                    if t["failed"] is not None and t["done"] is None]

    # 最近闭合
    closed_tasks_sorted = sorted(
        ({"task": task, "done_ts": t["done"].isoformat() if t["done"] else None}
         for task, t in tasks.items() if t["done"]),
        key=lambda x: x["done_ts"] or "",
        reverse=True,
    )

    return {
        "engineered": "task_closed_loop",
        "total_tasks": total,
        "closed_tasks": closed,
        "failed_tasks": failed,
        "task_completion_rate": round(closed / total, 3) if total else 0.0,
        "recovery_rate": round(closed / (closed + failed), 3) if (closed + failed) else None,
        "in_progress_tasks": in_progress,
        "open_tasks": open_tasks[:20],  # 截断防爆
        "failed_task_list": failed_tasks[:20],  # 失败明细（可下钻至 reason）
        "phase_distribution": dict(phase_counter),
        "task_durations_min": durations,
        "recent_closed": closed_tasks_sorted[:10],
        "avg_duration_min": round(
            sum(d["duration_min"] for d in durations) / len(durations), 1
        ) if durations else None,
        "source": "staging/zell-trace.jsonl",
    }


DEFAULT_COLLECTOR_METRICS_PATH = os.path.join(_REPO_ROOT, "data", "metrics", "collector-metrics.jsonl")


def collector_performance_metrics(metrics_path: Optional[str] = None, window: int = 20) -> Dict[str, Any]:
    """采集性能趋势（v2 新增）：读 GuardMetrics 落盘 jsonl 聚合。

    - latest：最近一次快照（total/success/failure/success_rate/avg_latency/p95/last_error/ts）
    - window_success_rate / window_avg_latency：近 N 条快照均值（默认 20）
    - 证据下钻：每条快照带 ts，可回查原始 jsonl 行
    """
    p = metrics_path or DEFAULT_COLLECTOR_METRICS_PATH
    rows: List[Dict[str, Any]] = []
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
    if not rows:
        return {"engineered": "collector_performance", "samples": 0, "latest": None,
                "window_success_rate": None, "window_avg_latency": None,
                "source": "data/metrics/collector-metrics.jsonl"}
    recent = rows[-window:]
    rates = [r["success_rate"] for r in recent if isinstance(r.get("success_rate"), (int, float))]
    lats = [r["avg_latency"] for r in recent if isinstance(r.get("avg_latency"), (int, float))]
    return {
        "engineered": "collector_performance",
        "samples": len(rows),
        "latest": rows[-1],
        "window_success_rate": round(sum(rates) / len(rates), 4) if rates else None,
        "window_avg_latency": round(sum(lats) / len(lats), 3) if lats else None,
        "source": "data/metrics/collector-metrics.jsonl",
    }


def scheduling_health() -> Dict[str, Any]:
    """调度健康（v3 新增）：聚合 PlatformSchedulePlanner 各平台调度状态。

    仅做只读聚合；Planner 不可用/未初始化时给 degraded 占位，不抛异常。
    证据下钻：platform 名即状态 key，可回查 platform_adapters/scheduling/planner.py。
    """
    try:
        from platform_adapters.scheduling.planner import PlatformSchedulePlanner

        # 无参数实例化（默认 policies/state_file），若需要参数则退化
        planner = PlatformSchedulePlanner()
        snap = planner.snapshot() if hasattr(planner, "snapshot") else {}
        if isinstance(snap, dict):
            return {"engineered": "scheduling", "platforms": snap,
                    "source": "platform_adapters.scheduling.planner.PlatformSchedulePlanner.snapshot()"}
        return {"engineered": "scheduling", "platforms": {}, "source": "planner.snapshot"}
    except Exception as e:  # noqa: BLE001 — 兜底
        return {"engineered": "scheduling", "platforms": {}, "degraded": True,
                "error": str(e)[:120], "source": "platform_adapters.scheduling.planner (fallback)"}


def system_health_metrics() -> Dict[str, Any]:
    """复用 system_health_api 红绿灯摘要（不重写）；失败时给 degraded 占位而非抛异常。"""
    try:
        from system_health_api import system_health_summary

        summary = system_health_summary()
        if isinstance(summary, dict):
            # 抽取红绿灯相关字段
            keys = [k for k in ("status", "lights", "database_light", "collector_light",
                                "auth_light", "xhs_platform_light", "summary") if k in summary]
            return {"engineered": "system_health", "health": {k: summary[k] for k in keys},
                    "source": "system_health_api.system_health_summary()"}
    except Exception as e:  # noqa: BLE001 — 兜底
        return {"engineered": "system_health", "health": {"status": "degraded",
                "error": str(e)[:120]}, "source": "system_health_api (fallback)"}
    return {"engineered": "system_health", "health": {"status": "unknown"},
            "source": "system_health_api"}


def full_snapshot(trace_path: Optional[str] = None) -> Dict[str, Any]:
    """统一工程度量快照：任务闭环 + 采集性能 + 调度健康 + 系统健康 + 告警 + 元信息（API 契约 schema v4）。"""
    data = {
        "engineered_metrics_version": API_CONTRACT_VERSION,
        "generated_ts": datetime.now().isoformat(timespec="seconds"),
        "task_closed_loop": task_closed_loop_metrics(trace_path),
        "collector_performance": collector_performance_metrics(),
        "scheduling_health": scheduling_health(),
        "system_health": system_health_metrics(),
    }
    data["alert"] = health_alert(snapshot=data)
    return data


# ---- 告警阈值（v4 新增：健康分级 OK/WARN/CRIT）----
DEFAULT_ALERT_THRESHOLDS: Dict[str, float] = {
    "recovery_warn": 0.5,      # 恢复率低于 WARN
    "recovery_crit": 0.3,      # 恢复率低于 CRIT
    "collector_warn": 0.8,     # 采集窗口成功率低于 WARN
    "collector_crit": 0.5,     # 采集窗口成功率低于 CRIT
}


def health_alert(snapshot: Optional[Dict[str, Any]] = None,
                 thresholds: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """健康告警分级（v4 新增）：基于快照关键指标计算 OK/WARN/CRIT。

    - recovery_rate：成功恢复率低于阈值告警（失败堆积信号）
    - collector_success_rate：采集窗口成功率低于阈值告警（采集链路劣化）
    - scheduling：planner degraded 或无平台 → WARN（调度不可观测）
    - system_health：非 ok → WARN
    - 阈值可传入 thresholds 覆盖默认；只读，不触发任何副作用
    - 证据下钻：每条 check 带 name/value/warn/crit，可回查对应聚合源
    """
    snap = snapshot or full_snapshot()
    th = {**DEFAULT_ALERT_THRESHOLDS, **(thresholds or {})}
    checks: List[Dict[str, Any]] = []
    levels = {"OK": 0, "WARN": 1, "CRIT": 2}

    def _check(name, value, warn, crit, msg):
        if value is None:
            level = "WARN"  # 无数据不可判，保守 WARN
        elif value < crit:
            level = "CRIT"
        elif value < warn:
            level = "WARN"
        else:
            level = "OK"
        checks.append({"name": name, "level": level, "value": value,
                       "warn_threshold": warn, "crit_threshold": crit, "message": msg})
        return level

    _check("recovery_rate", snap["task_closed_loop"].get("recovery_rate"),
           th["recovery_warn"], th["recovery_crit"], "成功恢复率 closed/(closed+failed)")
    _check("collector_success_rate", snap["collector_performance"].get("window_success_rate"),
           th["collector_warn"], th["collector_crit"], "采集窗口成功率均值")

    sched = snap["scheduling_health"]
    sched_ok = bool(sched.get("platforms")) and not sched.get("degraded")
    checks.append({"name": "scheduling", "level": "OK" if sched_ok else "WARN",
                   "value": len(sched.get("platforms") or {}), "warn_threshold": None,
                   "crit_threshold": None,
                   "message": "调度健康" if sched_ok else "调度 degraded 或无平台可观测"})

    sysh = snap["system_health"].get("health", {}).get("status")
    checks.append({"name": "system_health", "level": "OK" if sysh == "ok" else "WARN",
                   "value": sysh, "warn_threshold": None, "crit_threshold": None,
                   "message": f"系统健康状态={sysh}"})

    rank = max(levels[c["level"]] for c in checks)
    level = {0: "OK", 1: "WARN", 2: "CRIT"}[rank]
    return {"engineered": "health_alert", "level": level, "checks": checks,
            "generated_ts": datetime.now().isoformat(timespec="seconds")}


def _main() -> None:
    args = set(sys.argv[1:])
    if "--closed-loop" in args:
        print(json.dumps(task_closed_loop_metrics(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(full_snapshot(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
