# 序境-Core · Unified Data Intelligence Pipeline V1.0 — Inventory & Audit

> 状态：P0-AUDIT-DONE（先审计、禁改码；本次未改任何生产代码）
> 依据：《全产品统一数据智能管线 V1.0》一次性研发指令（2026-09-04）
> 基线：`data/monitor.db` 真实生产库 + 根目录真实源码 + `序境/01-PRODUCT/MODULE_PAGE_WORKFLOW_DATA_REGISTRY.md`（复用）
> 原则：不推翻、不重建、不删旧；先 KEEP 复用，双真相登记待收敛，未经验证不 DELETE。

---

## 1. 数据层 Inventory

### 1.1 数据源与采集（External → Raw）

| 数据源 | Collector / Adapter | Raw 落点 | 状态 |
|---|---|---|---|
| 小红书（XHS）话题/笔记 | collector.py / xhs_cdp_collector.py / xhs_p0_orchestrator.py | `notes` 表 + `data/*.json` raw | PASS |
| 小红书评论 | xhs_cdp_collector.py | `comments` / `note_comments` 表 | PASS |
| Web 网页监测 | web_monitor.py / web_topic_discovery.py / web_monitor_v570.py | `web_topics` / `web_events` / `web_mentions` 表 | PASS |
| 事件图谱 | event_graph.py / event_graph_events | `event_graph_events` / `event_graph_relations` | PASS |
| Topic Campaign | topic_campaign.py（Node.js collector） | `topic_campaign_*` 表 | PASS |
| 案例库 / PR | pr_case_engine.py / case_library.json | `swire_events`(project_key='case_study') + JSON | PASS |
| 品牌行业监测 | brand_industry_monitor.py | `brand_industry_monitor` 表 | PASS |
| 微博 / B 站 | weibo_login_manager / bilibili_login_manager | cookies + 采集 | PARTIAL |
| 内部浏览器 | internal_browser.py / browser_runtime | Runtime 会话 | PASS |
| 播客 | podcast_store.py / podcast_routes.py | `podcast_*` 表 | NEW（空表，未采） |

### 1.2 数据库（Truth Surface）

生产库：`data/monitor.db`（10.7 MB，63 张表，sqlite）。已有备份：`data/backups/`（14+ 份阶段快照）。

核心 Canonical 表（当前事实源）：
- `notes`（1052 行 / 68 列）— 内容 Truth：ID/内容/作者/互动/情感/风险/主体/质量
- `events`（484 行 / 22 列）— 事件 Truth：风险/状态/多来源
- `kos_profiles`（375 行 / 59 列）— KOS 账号资产 Truth：归属/评分/分层/留资/合作
- `topic_campaign_notes`（481）`topic_campaign_topics`（7）`topic_campaign_snapshots`（406）— Campaign Truth
- `comments`（2）`note_comments`（141）— 评论 Truth
- `web_topics`（96）`web_events`（20）`web_mentions`（82）`web_runs`（31）`web_sources`（1）
- `swire_events`（32）— 案例/项目 Truth（含 case_study 22 条）
- `marketing_nodes`（10）— 营销节点
- `metric_snapshots`（250）— 指标快照（趋势数据）
- `daily_reports`（43）`weekly_events`（30）`daily_digest`（10）— 报告
- `kos_operations`（108）`kos_executions`（259）`kos_paid_plans`（38）`kos_rewards`（19）— KOS 运营/投流/奖励
- 运维：`collection_logs`（660）`collection_counters`（2）`collector_quality_log`（7）`auth_recovery_tasks`（122）`schedule_decisions`（10294）`v4_*` 系列

### 1.3 Data Contract（复用基础，已有）

`config/data-contracts/`：event.yaml / event_db.yaml / note.yaml / topic_snapshot.yaml（4 契约）
校验执行器：`data_quality_gate.py`（DataQualityGate，业务语义规则：必填/格式/范围/长度/枚举/日期）
Schema 反射：`schema_registry.py`（reflect/classify/build_markdown/generate）

## 2. 计算层 Inventory（业务计算）

### 2.1 已确认的 Canonical 业务计算（单一权威）

| 计算 | 权威位置 | 输出 | 状态 |
|---|---|---|---|
| 风险指数 risk_index（0-100，5 维） | `daily_report.py::calculate_risk_index` | 日报核心指标 | CANONICAL |
| 品牌健康度 brand_health_score（0-100） | `daily_report.py::calculate_brand_health_score` | 日报核心指标 | CANONICAL |
| KOS Score / 分层 / 生命周期 | `kos_engine.py::refresh_profiles` | kos_profiles | CANONICAL |
| KOS 归属门（主体归属） | `kos_engine.py::refresh_profiles` + `kos_attribution.py` | ownership_type/confidence | CANONICAL |
| KOS 漏斗/成本/分层基准 | `kos_metrics.py`（funnel/cost/tier_benchmark） | 运营指标 | CANONICAL |
| 投流 ROI | `kos_paid.py`（ROI=(conv*50-spend)/spend） | kos_paid_plans | CANONICAL |
| 数据质量校验 | `data_quality_gate.py::DataQualityGate.validate` | valid/errors | CANONICAL |
| 研发效率指标 | `engineering_metrics.py` | 工程度量 | CANONICAL |
| 话题情感/热度 | `topic_campaign.py` | snapshot | CANONICAL |

### 2.2 ⚠️ 双真相风险点（V1.0 治理对象，登记不删除）

| 指标 | 算法 A | 算法 B | 冲突说明 | 处置建议 |
|---|---|---|---|---|
| 笔记风险分 risk_score | `ai_analyzer.py::assess_risk`（high×25+med×10，写 notes.risk_score） | `daily_report.py`（risk_index 5 维综合） | 两个"风险"口径并存：notes.risk_score vs daily risk_index | 暂 KEEP；定义 FUNC-RISK-01 为 Canonical，A 作为 raw 信号字段保留，日报消费 B；下一阶段统一 |
| 品牌健康 | `daily_report` 单一口径 | 前端/其他计算需核验 | — | KEEP（已单一） |
| 情感 sentiment | `ai_analyzer` 写入 | `topic_campaign` 计算 | 需核验是否同源 | 登记待核 |

### 2.3 前端计算（低风险）

`static/js/*.js` 38 个文件，业务计算密度低（app.js 15 处、kos_dashboard 8 处，多为 format/render）；前端不做业务 Truth 计算，符合"页面不算"。登记为 VIS/UI 层，仅消费后端指标。

## 3. 产品层 Inventory

| 产品域 | 核心模块（MOD-xxx） | 状态 |
|---|---|---|
| 观测·采集 | MOD-OBS-01~07（采集器/自动化/自适应/守卫/CDP/Web/流水线） | PASS |
| 洞察 | 趋势/事件/风险/机会（daily_report、risk_engine、event_graph、web_topics） | PASS |
| 关系 | 品牌/创作者/内容/事件关系（brand_knowledge、subject_classifier） | PASS |
| 行动 | KOS/Campaign/处置（kos_engine、kos_ops、kos_paid、topic_campaign、pr_case） | PASS |
| 研究 | AI/时尚/高奢/重奢/创新品牌（case_deep_analysis、intelligence） | PASS |
| 创造 | Podcast/Report（podcast_*、report_engine、brand_report_generator） | PARTIAL |
| 智能 | AI/Search/Assistant（ai_analyzer、ark_llm、intelligence） | PASS |
| 系统 | Settings/Permission/Accounts/Runtime/Health（v4_*、system_health、resident_health） | PASS |

API 面：`app.py` 221 端点 + `kos_routes.py` 挂载 + `podcast_routes.py` + `architecture_api`/`collection_api`/`data_query_api`/`evidence_api` 等。

## 4. 可视化层 Inventory

| 视图类型 | 前端位置 | 数据源 | 状态 |
|---|---|---|---|
| Trend 趋势 | app.js renderTrend / renderDynamicTrendChart | /api/trends、metric_snapshots | PASS |
| Donut 分布 | app.js renderDonut/renderCategories | /api/overview | PASS |
| Ranking | renderRisk / renderTopics | /api/alerts、web_topics | PASS |
| Timeline | podcast.js / runtime | podcast/采集任务 | PARTIAL |
| KPI 指标卡 | metric-card（index.html 多处） | /api/* | PASS |
| 事件卡 | renderEvents / event-card | /api/events | PASS |
| KOS 面板 | kos_dashboard.js | /api/kos/* | PASS |
| Evidence | app_evidence.js / evidence_dashboard.js | evidence_api | PASS |
| Cross-filter | xujing-crossfilter.js | — | PASS |

## 5. 新旧关系分类（KEEP / MERGE / MIGRATE / LEGACY / ARCHIVE / DELETE）

> 判定依据：仍正确 / 仍被引用 / Runtime 依赖 / 业务价值 / 与新规范冲突 / 重复计算。
> 本次只登记，不执行任何删除。

| 资产 | 判定 | 依据 |
|---|---|---|
| data_quality_gate.py + config/data-contracts/* | KEEP（复用为 V1.0 Quality Gate 主体） | 已正确、被引用、有运行时依赖 |
| schema_registry.py | KEEP | 已有 Schema 反射与分类 |
| daily_report risk_index/brand_health | KEEP + 提升为 Canonical Metric | 单一权威、被报告消费 |
| ai_analyzer.assess_risk | KEEP（登记双真相，作为 raw 信号） | 仍写 notes.risk_score、被负评确认流使用；不删，待统一 |
| function_map.json（根目录旧版） | LEGACY（登记） | 内容为 API 描述非业务公式；被 /api/function-map 引用，暂不删 |
| 根目录 monitor.db（12KB 空壳） | ARCHIVE 候选 | 生产库在 data/monitor.db；空壳文件，登记待确认 |
| `你的数据库文件名.db`（0 字节） | ARCHIVE 候选 | 空文件占位 |
| topic_campaign.py + 前端 topic_campaign.* | KEEP | Campaign 生产能力 |
| 旧皮肤 CSS（zb-theme/zb-gpt/design-v9 等） | LEGACY（登记） | 已被 xujing-design-system 统一覆盖，仍被 index.html 引用，不可盲删；待 Reference Scan |
| templates/ 多页面版 | LEGACY（登记） | SPA 为系统主入口，templates 仍被 Flask 路由引用，低优先级待定 |

**删除守卫**：以上任何 ARCHIVE/DELETE 均未执行——须满足：Reference Scan + Dependency Scan + Runtime Scan + 新能力覆盖 + 一致性验证 + Regression + Rollback + Audit 后，才可删。

## 6. 既有可复用管线资产（V1.0 不得重建）

- `data_quality_gate.py`（Quality Gate 执行器）→ 复用为 P0-6 的 Data Quality Gate
- `config/data-contracts/*.yaml`（4 契约）→ 复用并扩展（KOS/Topic/Web 契约）
- `schema_registry.py`（Schema 反射/分类）→ 复用为 Schema Registry
- `metric_snapshots` 表 → 复用为指标快照/趋势 Truth
- `app_evidence.py` + `evidence_store.py` + `evidence_api.py` → 复用为 Evidence 层
- `engineering_metrics.py` → 复用为性能/健康指标

## 7. P0 后续（本报告之后执行，不在此次审计范围内）

- P0-5 Function Registry（FUNC-xxx 注册 Canonical Function）
- P0-6 Metric Registry（MET-xxx 唯一 Metric ID）
- P0-7 Canonical Table / Data Contract 扩展 / Lineage 骨架
- P1~P6：Content/Brand/KOS/… 接入 → UI 统一 → Visualization Registry → Report/Export → AI Semantic Access → 全产品一致性

---

## 附：审计证据

- 生产库：`data/monitor.db` 63 表真实盘点（行数/字段数见 §1.2）
- API 面：`app.py` 221 路由真实盘点（§3）
- 前端计算：38 个 static/js 文件扫描（§2.3）
- 双真相：daily_report vs ai_analyzer 两套风险算法源码对照（§2.2）
- 既有契约：config/data-contracts 4 yaml（§1.3）
