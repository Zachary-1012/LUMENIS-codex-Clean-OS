# MASTER ENGINEERING MATRIX · Zachary-OS-AI × Z-Brand-Core 双子库统一施工总单

- Version: UNIFIED-ENGINEERING-BASELINE-2026.09 / 对齐「OSAI #11 今夜统一工程施工总单」
- 生成时间：2026-09-03（源码级核对，非旧报告转述）
- 状态图例：✅已实现(直接复用) ｜ 🟡部分实现(需补齐/收敛) ｜ ⬜未实现(需施工)
- Owner：`ZBC`=生产事实源实现 ｜ `OSAI`=研究/契约/学习中枢 ｜ `Joint`=双库 Contract 协同
- 最高原则：功能零减配、数据零丢失、最小变更+可验证+可回滚、无真实数据不造假（只建能力边界）

## 一、A–N 完整性核对矩阵

| 域 | 项目 | 来源/源码证据 | 当前状态 | Owner | Dependency | Priority | 已实现 | 需施工 | Test | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| A | ZBC 生产事实源 | `D:\Taikoo-monitor-new` Flask+SQLite，382 回归全过 | ✅ | ZBC | — | P0 | 是 | 否 | pytest 382 | git b9f14bc |
| A | OSAI 研发智能中枢 | `D:\Zachary OS AI`（reconciliation 01–22/contracts/learning-feed/osai-ui） | ✅ | OSAI | — | P0 | 是 | 否 | pytest.ini | 22 份对账矩阵 |
| A | Capability/Owner/Contract/SoT | OSAI 10_ownership/11_contract/12_capability/13_duplicate + config/skills-registry + 2 CTR | ✅ 自动对账已建(scripts/reconcile_capabilities.py)：production 9/9 + research 10/10 + contracts 3/3 全 PASS | Joint | OSAI 矩阵 | P0-B | 是 | 否 | reconcile_capabilities.py | AUTO-RECONCILE-P0B-20260903.md |
| A | 跨仓库边界 | ZBC 不 import OSAI；Contract/Adapter 连接 | ✅ | Joint | — | P0 | 是 | 否 | — | twin contract V1 |
| B | ZELL 学习闭环 | learning-feed 3 轮标杆+contract-updates | 🟡 有沉淀，缺第一条端到端可复跑闭环 | OSAI | P0-A/B | P0-C | 部分 | 是：Issue→…→Knowledge Reuse 全链 | 待建 | learning-feed/*.md |
| B | 研发任务级 Trace ID | yyds-logger 有 request_id（请求级） | ✅ ZELL task_trace_id 规范已建(learning-feed/ZELL-LOOP-TEMPLATE)，ZBC unified_logger request_id 复用承载约定 | Joint | logger | P0-C | 是 | 否 | reconcile_capabilities.py | ZELL-LOOP-001 |
| C | Engineering Observatory | osai-ui 9 页（runtime/evidence/projects/research/knowledge…） | 🟡 第一条真实闭环已入 observatory-feed.json(zell_loops 时间轴)；双窗口/点击详情/增量更新待前端组件化 | OSAI | P0-C/E | P0-D | 部分 | 是：前端交互续接 | 待建 | ZELL-LOOP-001 |
| D | 研发效率指标长期记录 | collector_guard/metrics.py 仅为采集指标，非研发指标 | ✅ osai_engine/metrics/engineering-metrics.jsonl 建立(6类指标含 raw/normalized/baseline/sample_size/window/method)，首条 ZELL-001 | OSAI | P0-C/D | P0-E | 是 | 否 | — | ZELL-P0CDEF-20260904.md |
| E | Lean / Small Footprint | app.py 6013→5851、schema_registry、13_duplicate | 🟡 footprint 基线建立(2026-09-04: 659py/97811行/4.2MB/avg148.4)，app.py 6.6K 行为瘦身候选(稳定优先待专项) | Joint | — | P0-F | 部分 | 是：度量+瘦身 | test_schema_registry | ZELL-P0CDEF-20260904.md |
| F | Max Efficiency 四态 | ThreadPool 零散(job=1/web=6)、RiskEngine 六态+action、AdaptiveEngine | 🟡 缺统一 Resource Guard 消费 lifecycle_action 的 NORMAL/HIGH-EFFICIENCY/RESOURCE-GUARDED/RECOVERY 与统一 Queue/Backpressure | ZBC | P1-A | P0-G | 部分 | 是：统一调度 | test_risk_lifecycle | risk_engine.py |
| G | 小红书采集稳定+动态熔断 | collector_guard 全套、xhs_cookie_bridge、六态生命周期 | 🟡 较全，需 Scheduler 真正消费 lifecycle_action | ZBC | P0-G | P1-A | 部分 | 是：接线联动 | 382 回归 | risk_engine/guard |
| G | Topic 指标 Snapshot | metric_snapshots(note+topic 统一)、topic_campaign_snapshots、app_evidence | 🟡 能力刚建(b9f14bc)，topic 自动采集写入点待接 | ZBC | P1-A | P1-B | 部分 | 是：接采集写入 | test_metric_snapshots | metric_snapshots 表 |
| G | 五时间模型 | notes: publish_date/publish_datetime/captured_at/collected_at/last_seen_at/detail_fetched_at；events: event_date/first_seen/last_seen；snapshot_at | ✅ 字段基本齐，需固化口径文档 | ZBC | — | P1-B | 是 | 文档固化 | test_metric_snapshots | database.py |
| H | KOL/KOC/UGC 分层 | notes 有 author_id/nickname/is_official 数据基础，无分层模块 | ⬜ 缺 Account→Note→Interaction→Event→Evidence 分层 | ZBC | G | P1-C | 否 | 是：建分层能力 | 待建 | notes 作者字段 |
| I | 日/周/月/年/专报 | report_engine REPORT_TYPES=(daily,weekly,monthly,yearly)、daily_report 管理层洞察 | 🟡 周期报告已具备，缺专报 special + 独立日报弹窗 + Decision-First 强化 | ZBC | — | P1-D | 部分 | 是：专报+弹窗 | test_report_periods | report_engine.py |
| J | 跨端能力平价 | ZBC Web/static、App Evidence(shadow)、移动适配 | 🟡 无小程序、跨端 Contract 未统一 | Joint | I/K | P1-E | 部分 | 是：统一 Contract | — | app_evidence.py |
| K | UI/UX 动态可视化 | osai-ui + ZBC static 部分动态组件 | 🟡 缺动态时间轴/Evidence 展开/滑动历史/真实数据绑定系统组件 | Joint | C | P1-F | 部分 | 是：组件化 | — | osai-ui |
| L | AI 分层 | ai_governance(脱敏/额度/增强层标记)+intelligence(智谱唯一外接)+local_ai_client+Rule/SQL | 🟡 分层成型，需核对无 key 全链降级、付费零依赖 | Joint | — | P1-G | 部分 | 核对加固 | test_llm_gateway | ai_governance.py |
| M | 历史能力提取 | DCC 确认废弃并入 OSAI、16_migration_matrix、archive | 🟡 持续：只提取能力不恢复旧系统 | OSAI | 各阶段 | 伴随 | 部分 | 随阶段推进 | — | migration_matrix |
| N | Compliance Gate | safe_collection/safety_boundary/gate/ai_governance 脱敏/patch_redact | 🟡 组件多而分散，缺统一 Gate 编排+多法域矩阵(CN/HK/EU/UK/US) | Joint | L | P1-H | 部分 | 是：统一 Gate | test_safe_collection_contract 等 | safe_collection.py |

## 二、严格施工顺序（每阶段必过 8 道门：Test→Regression→Runtime→Performance→Data Completeness→Compliance→Evidence→Git）

| 阶段 | 目标 | 进入条件 | 完成判据（真实代码/测试/Runtime/Evidence/Git） |
|---|---|---|---|
| **P0-A** | 生产安全基线 Git→Runtime→Data→Test→Rollback→Evidence | 现状 | 一键基线脚本：工作区/远端同步、Runtime 可启、Data 备份+schema 完整、回归全绿、可回退 commit、Evidence 落盘 |
| **P0-B** | Capability/Contract/Ownership 收敛 | P0-A 过 | 一个 Capability 一个 Canonical；重复项收敛清单+自动对账；健康模块 7 个去重定性 |
| **P0-C** | ZELL 第一条真实闭环 | P0-B 过 | 真实任务跑通 Issue→Research→Architecture→Patch→Test→Runtime→Evidence→Evaluation→Learning，任务级 Trace 贯穿 |
| **P0-D** | Engineering Learning Observatory | P0-C 过 | ZBC+OSAI 双窗口、真实时间轴、点击节点详情、前后对比、增量更新，数据来自 P0-C 真实 Evidence |
| **P0-E** | 研发效率指标长期记录 | P0-D 过 | 6 类工程指标入库，每条含 raw/normalized/baseline/sample_size/window/method；第二次任务可对比第一次 |
| **P0-F** | Lean / Small Footprint | P0-E 过 | 体量/依赖/耦合/分位延迟/footprint 基线+一轮可验证瘦身，功能不减 |
| **P0-G** | Maximum Efficiency Mode | P0-F 过 | 统一 Resource Guard 四态，消费 lifecycle_action，Queue/Backpressure/Recovery 联动且不跑崩 |
| P1-A | 小红书稳定+动态熔断 | P0 全过 | Scheduler/Worker 真正按六态动作调度 |
| P1-B | Topic 数据能力 | P1-A | 浏览/讨论/笔记数 Snapshot 自动采集写入+趋势可读，五时间口径固化 |
| P1-C | KOL/KOC/UGC | P1-B | Account→Note→Interaction→Event→Evidence 分层可查 |
| P1-D | 报告全周期 | P1-C | +专报+独立日报弹窗，Decision-First |
| P1-E | 跨端 | P1-D | 统一 Contract，Web/App/Mobile/Mini 能力平价 |
| P1-F | UI/UX | P1-E | 动态时间轴/状态节点/Evidence 弹窗全绑真实数据 |
| P1-G | AI 分层 | P1-F | Rule/SQL→Cache→Local→Zachary→智谱，无 key 降级、付费零依赖核验 |
| P1-H | Compliance Gate | P1-G | 统一合规 Gate + 多法域矩阵，不确定即 BLOCK/HUMAN REVIEW |

## 三、今晚第一版闭环目标（不搞形式主义、优先打通而非铺量）
真实任务 → OSAI 研究 → 工程决策 → ZBC 实改 → 真实 Test → 真实 Runtime → 真实 Evidence → Evaluation → Learning → Knowledge Reuse → Observatory 可视化 → 第二次任务复用第一次经验 → 得到**可测量**的效率变化。约束：ZBC 生产功能不减、数据不丢、系统不卡、footprint 可控、全过程可追溯。

## 四、复用优先清单（已有即接，不重造）
- 契约/能力/属主：OSAI reconciliation 10/11/12/13 + skills-registry；契约模板 contracts/CTR-*.md
- 学习沉淀：learning-feed/；运行时 Trace：yyds-logger request_id
- 观测前端：osai-ui 9 页；周期报告：report_engine；AI 治理：ai_governance
- 采集韧性：collector_guard（含新六态 lifecycle）；指标快照：metric_snapshots；合规：safe_collection
