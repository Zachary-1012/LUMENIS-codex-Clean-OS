# -*- coding: utf-8 -*-
"""
engineering_metrics.py — 工程度量聚合器（P0-E 工程度量落地）

职责（分工明确，不重复现有体系）：
- system_health_api.py 负责「组件健康红绿灯」——本模块直接复用 system_health_summary()，不重写
- collector_guard/metrics.py 负责「采集器性能窗口」——内存态，本模块不接管
- 本模块新增「任务级闭环度量」：从 staging/zell-trace.jsonl 计算
  Task Completion Rate / in-progress / 阶段分布 / 任务耗时 / 未闭合清单
  ——这是 P0 评价体系（Task Completion Rate / Recovery Rate）的核心落地，
    当前 ZBC 完全缺失。

数据源（Source → Evidence → Insight 原则，全部可下钻至原始行）：
- staging/zell-trace.jsonl：ZELL 闭环事件（begin / phase / done，task + ts + outcome）
- system_health_api.system_health_summary()：4 子灯健康摘要

用法：
- 作为模块：from engineering_metrics import full_snapshot
- 独立运行：python engineering_metrics.py  （打印统一快照 JSON）
- 仅计算闭环：python engineering_metrics.py --closed-loop
"""
from __future__ import annotations

import io
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    # 兼容 stdlib-only 运行（避免导入 app 体系）
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except Exception:
    pass

# 仓库根目录定位（本文件位于仓库根）
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TRACE_PATH = os.path.join(_REPO_ROOT, "staging", "zell-trace.jsonl")

# ZELL 闭环：begin=任务开启，done=任务闭合；phase 事件用业务阶段名（architecture/code/test/runtime/evaluation/research）
BEGIN_EVENT = "begin"
DONE_EVENT = "done"
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
        t = tasks.setdefault(task, {"begin": None, "done": None, "phases": [], "outcomes": []})
        ts = _parse_ts(r.get("ts"))
        if ev == BEGIN_EVENT and t["begin"] is None:
            t["begin"] = ts
        elif ev == DONE_EVENT and t["done"] is None:
            t["done"] = ts
        if ev in PHASE_EVENTS:
            t["phases"].append({"phase": ev, "ts": _parse_ts(r.get("ts"))})
        if r.get("outcome"):
            t["outcomes"].append(str(r["outcome"]))

    total = len(tasks)
    closed = sum(1 for t in tasks.values() if t["done"] is not None)
    in_progress = total - closed

    # 阶段分布：所有 phase 事件按阶段计数
    phase_counter = Counter(p["phase"] for t in tasks.values() for p in t["phases"])

    # 各任务耗时（begin→done，分钟）
    durations: List[Dict[str, Any]] = []
    for task, t in tasks.items():
        if t["begin"] and t["done"]:
            secs = (t["done"] - t["begin"]).total_seconds()
            durations.append({"task": task, "duration_min": round(secs / 60.0, 1)})

    # 未闭合任务清单（begin 无 done）——失败/挂起可见性
    open_tasks = [task for task, t in tasks.items() if t["done"] is None]

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
        "task_completion_rate": round(closed / total, 3) if total else 0.0,
        "in_progress_tasks": in_progress,
        "open_tasks": open_tasks[:20],  # 截断防爆
        "phase_distribution": dict(phase_counter),
        "task_durations_min": durations,
        "recent_closed": closed_tasks_sorted[:10],
        "avg_duration_min": round(
            sum(d["duration_min"] for d in durations) / len(durations), 1
        ) if durations else None,
        "source": "staging/zell-trace.jsonl",
    }


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
    """统一工程度量快照：任务闭环 + 系统健康 + 元信息。"""
    return {
        "engineered_metrics_version": 1,
        "generated_ts": datetime.now().isoformat(timespec="seconds"),
        "task_closed_loop": task_closed_loop_metrics(trace_path),
        "system_health": system_health_metrics(),
    }


def _main() -> None:
    args = set(sys.argv[1:])
    if "--closed-loop" in args:
        print(json.dumps(task_closed_loop_metrics(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(full_snapshot(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
