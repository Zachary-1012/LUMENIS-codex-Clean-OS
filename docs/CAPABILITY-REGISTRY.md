# ZBC Capability Registry（P0-B｜Capability / Contract / Ownership）

> 生成：2026-09-03（Zachary AI 施工，智谱辅助分析，ai-budget 已记账）
> 原则：一个 Capability 一个 Canonical Implementation；功能零减配；删除需 Evidence。
> 口径：✅ 已落地 Canonical ｜🟡 部分/待接线 ｜⬜ 待施工（能力边界，不伪造数据）

## 1. 健康 / 监控 Capability（智谱分析结论，2026-09-03）

| Capability | Canonical Owner | 文件 | Status | 证据 |
|---|---|---|---|---|
| 系统健康监控 | ZBC | `system_health_api.py` | ✅ | 统一监控面板/状态文件/API，无重复实现 |
| 驻场浏览器健康（L1端口/L2 CDP/L3登录态） | ZBC | `resident_health.py` | ✅ | 三层探测/状态分级/自动恢复 |
| 采集指标采集 | ZBC | `collector_guard/metrics.py` | ✅ | 采集侧性能指标（P0-E 消费源） |

收敛结论：以上为独立 Capability，职责清晰无重叠，**无删除项**（功能零减配）。

## 2. 采集稳定性 Capability（熔断生命周期）

| Capability | Owner | 文件 | Status | 证据 |
|---|---|---|---|---|
| 采集风险引擎（风险分档→采集动作映射） | ZBC | `collector_guard/risk_engine.py` + `collector_guard/state.py` | ✅ | 风险分 0-100 五档 `NORMAL→WATCH→THROTTLED→COOLDOWN→CIRCUIT_OPEN`（阈值可由 `config/collector_guard.yaml` 覆盖）；映射 `CollectState` 七态 `HEALTHY/WARNING/COOLDOWN/PAUSED/AUTH_REQUIRED/NEED_VERIFY/NETWORK_ERROR`；熔断=CIRCUIT_OPEN（停止任务走恢复检测，不无限重试）。⚠️ 2026-09-03 智谱交叉验证修正：原"六态生命周期(NORMAL→ADAPTIVE→FROZEN…)"口径与源码不符，已改为源码真实口径（七态+五档） |
| 指标快照时序 | ZBC | `database.py` + `data_query_api.py` | ✅ | `metric_snapshots` 表 + `/api/metric-trend`，五时间模型 |
| 采集执行 Guard | ZBC | `collector_guard/` | ✅ | retry/backoff/heartbeat/last_success_at |

## 3. Contract 收口（25 项，P1-1）

| 分组 | 数量 | Owner | Status | 证据 |
|---|---|---|---|---|
| Safe Collection | 8/8 | ZBC（同名落地） | ✅ | `platform_adapters/safe_collection.py` + `tests/test_safe_collection_contract.py` |
| 其余 Contract | 17 | OSAI（研发中枢维护） | 🟡 | `D:\Zachary OS AI\baseline\CONTRACT-25-RECONCILIATION-20260903.md` |

## 4. 待施工（能力边界，不伪造数据）

| Capability | Owner | 需要 | Status |
|---|---|---|---|
| KOL/KOC/UGC 分层 | ZBC | Account→Note→Interaction→Event→Evidence 分层模块 | ⬜（P1-C） |
| 研发效率指标长期记录 | OSAI | 平均研发时长/回归Bug/重复代码/无效AI调用/测试覆盖 | ⬜（P0-E，AI Budget 已建） |
| 统一 Resource Guard 四态消费 | ZBC | 消费 `lifecycle_action` 联动调度/队列/Worker | 🟡（P0-G） |
| 专报 + 独立日报弹窗 | ZBC | report_engine 扩展 | ⬜（P1-D） |
| 统一 Compliance Gate | OSAI | 多法域矩阵 + BLOCK/HUMAN REVIEW | ⬜（P1-H） |
