# CTR-OBSERVABILITY-P0-01 · 序境可观测性能力契约（工程度量 / 健康 / 任务闭环）

> 状态：ACTIVE ｜ 版本：v4（2026-09-04，+alert 健康告警分级）｜ Owner：ZBC（生产实施）+ OSAI（口径治理）
> 目的：Observability 是序境**标准 Capability**——Web / App / Mini Program 共用同一业务逻辑、数据、权限和状态机，仅做终端适配（零号序列）。

## 1. 能力定位与分工（不重复）

| 能力 | 职责 | 生产实现 | 状态 |
|---|---|---|---|
| 组件健康红绿灯 | 数据库/采集器/登录态/调度等组件 up/down | `system_health_api.py` `system_health_summary()` | ✅ 已有 |
| 采集器性能窗口 | 采集成功率/延迟（内存滑动窗） | `collector_guard/metrics.py` `GuardMetrics` | ✅ 已有 |
| **任务级闭环度量** | Task Completion Rate / 进行中 / 阶段分布 / 耗时 / 未闭合清单（失败可见性） | `engineering_metrics.py` `task_closed_loop_metrics()` | ✅ 已落地（ZBC e822960） |
| **采集性能趋势** | 采集成功率/延迟持久化趋势（GuardMetrics 限频落盘 `data/metrics/collector-metrics.jsonl`，不阻塞 record 热路径） | `collector_guard/metrics.py` `persist()` + `collector_guard/guard.py` `status()` | ✅ 已落地（ZBC 384f722） |
| **调度健康** | 各平台调度状态聚合（PlatformSchedulePlanner snapshot） | `engineering_metrics.py` `scheduling_health()` | ✅ 已落地（ZBC 264688b） |
| **失败可见性/恢复率** | ZELL 显式 `fail` 事件 → `failed_tasks` / `recovery_rate`（closed/(closed+failed)） | `scripts/zell_trace.py` `fail()` + `engineering_metrics.py` | ✅ 已落地（ZBC 264688b） |
| **健康告警分级** | OK/WARN/CRIT 分级（recovery<0.5/0.3、collector<0.8/0.5、scheduling degraded→WARN、系统健康非ok→WARN；无数据保守 WARN；阈值可覆盖）只读无副作用 | `engineering_metrics.py` `health_alert()` | ✅ 已落地（ZBC a4ec25b） |
| **统一度量聚合 API** | 上述聚合为单一结构化快照（任务闭环含失败/采集性能/调度/健康/告警），供全终端消费 | `engineering_metrics.py` `full_snapshot()` + `GET /api/engineering-metrics` | ✅ 已落地 |

分工红线：本能力**不重写** system_health / GuardMetrics，只聚合复用；任何终端不得复制口径逻辑，只做展示适配。

## 2. 数据源与证据下钻（Source → Evidence → Insight）

- 任务闭环数据源：`staging/zell-trace.jsonl`（ZELL 闭环事件，begin/phase/done）
- 证据 key：**task 名**即 ZELL trace 的 `task` 字段 → 任一指标（完成率/耗时/未闭合）均可回查原始行
- 系统健康数据源：`system_health_api.system_health_summary()`（带 source 函数名）
- 采集性能数据源：`data/metrics/collector-metrics.jsonl`（GuardMetrics `persist()` 限频落盘，60s/次，不阻塞采集热路径）
- 下钻规则：任何指标必须能下钻至 聚合 → 原始记录 → Evidence；禁止只给结论不给来源

## 3. API 契约（schema v4，全终端通用）

`GET /api/engineering-metrics` → `{ "ok": true, "data": {...} }`

```
data = {
  "engineered_metrics_version": 1,     # 契约版本，口径变更必须 bump
  "generated_ts": "<ISO8601>",
  "task_closed_loop": {
    "total_tasks": int,                # 已 begin 唯一任务数
    "closed_tasks": int,               # 已 done 任务数
    "task_completion_rate": float,     # 0.0-1.0
    "in_progress_tasks": int,
    "open_tasks": [str],               # 未闭合（失败/挂起可见性）
    "phase_distribution": {str:int},   # architecture/code/test/runtime/evaluation/research
    "task_durations_min": [{task, duration_min}],   # 已闭合耗时（可下钻）
    "recent_closed": [{task, done_ts}],             # 最近闭合（可下钻）
    "avg_duration_min": float|null,
    "source": str                      # 证据源
  },
  "collector_performance": {            # v2 新增
    "samples": int,                    # 已落盘快照数
    "latest": {total/success/failure/success_rate/avg_latency/p95/last_error/ts},
    "window_success_rate": float|null, # 近 N 条快照成功率均值（默认 20）
    "window_avg_latency": float|null,  # 近 N 条快照平均延迟均值
    "source": str                      # data/metrics/collector-metrics.jsonl
  },
  "system_health": {
    "engineered": "system_health",
    "health": { status/子灯... },      # 复用 system_health_summary
    "source": str
  }
}
```

## 4. 终端适配（同一数据，不同展示）

| 终端 | 展示建议 | 数据来源 |
|---|---|---|
| Web | 表格 + Chart + Drill-down（下钻到任务清单 → ZELL 原始行） | 同一 `/api/engineering-metrics` |
| App | Card 概览（完成率大数字 + 红绿灯 + 进行中列表） | 同一 API |
| Mini Program | 精简摘要（完成率 + 健康状态） | 同一 API |

禁止：各终端自造口径 / 独立采集 / 复制度量逻辑。仅做 UI 层渲染适配（遵守统一 Design System：细线 Icon、数据优先表格/Card/Chart）。

## 5. 版本与演进规则

- 口径变更：bump `engineered_metrics_version` + 更新本文档 + 同步 ZBC `engineering_metrics.py` 契约注释
- **禁止静默改字段**（删除/改名/改类型必须走版本迁移）
- 新指标建议：先入 OSAI 研究（P0-E 评价体系）→ 评估 → 最小实现 → 测试 → 纳入契约 v2
- 失败可见性：✅ 已落地（v3）——ZELL 显式 `fail` 事件 → `failed_tasks` / `recovery_rate`
- 下一步演进：告警接入通知渠道（IM/邮件）；采集性能趋势接入 Dashboard；恢复率阈值按运营基线调参

## 6. 关联资产

- ZBC：`engineering_metrics.py` / `tests/test_engineering_metrics.py`（6 单测）/ `app.py` 端点 / `staging/zell-trace.jsonl`
- OSAI：`research-inbox/ZELL-P0CDEF-20260904.md`（P0-E 落地 Evidence）/ P0-AGENT-ORG（评价体系研究）
- 验收：`python -m unittest tests.test_engineering_metrics` 全绿（15 项，含 HealthAlertTest 7 项）；快照字段与本文档一致（v4：任务闭环含 failed/recovery + 采集性能 + 调度健康 + 系统健康 + alert）；`collector_guard` persist 落盘验证通过；ZELL `fail` 冒烟通过且不污染真实 trace
