> **HISTORICAL / SUPPORTING FUNCTION INVENTORY — NOT CURRENT PRODUCT/CAPABILITY AUTHORITY.**
> Current product scope comes from the sole Product Architecture; current owners/gaps come from the Source Owner Index and fresh source/runtime evidence. The inventory below is provenance and may contain stale candidate/status labels.

# LUMENIS 现有功能地图

状态：Canonical Function Inventory Entry

## 1. 说明

本文把现有源码能力映射到最终产品线，不依据文件名直接判定功能。完整模块/函数候选继续由 `audit/module_inventory.json`、`audit/module_inventory.md`、`function_map.json` 和 API inventory 承载；这些旧扫描状态必须经过当前调用链和 Runtime 复核。

状态含义：

- `ACTIVE CANDIDATE`：存在真实调用或消费者，但尚未满足七类证据；
- `MULTIPLE`：存在多个可能产生同类输出的实现；
- `PARTIAL`：部分链路有源码/测试，生产闭环缺失；
- `BLOCKED`：当前 Runtime、数据或契约阻断；
- `UNKNOWN`：证据不足；
- `LEGACY CANDIDATE`：历史兼容候选，禁止直接删除。

## 2. CTH 功能

| 功能 | 当前实现候选 | 下游 | 状态 |
|---|---|---|---|
| Subject Authority | `subject_rules.py`、`subject_context.py` | Collector、Risk、Report、CTH 页面 | ACTIVE CANDIDATE；语义保护项 |
| Subject Profile | Brand/Profile 配置与 Context | CTH 数据域与页面 | PARTIAL |
| 商业运营总览 | CTH route/template、overview API | CTH UI | BLOCKED：UI Truth 冲突 |
| 实时监测 | Collector/API/CTH realtime | UI、Event、Risk | BLOCKED：当前 NO_RUN |
| 话题与活动 | `topic_campaign.py` 等 | Event/Report | MULTIPLE / PARTIAL |
| Event | `events`、`event_graph_events`、`event_graph.py` | Risk、Case、Report | MULTIPLE |
| Case | `case_deep_analysis.py`、`public_opinion_cases.py`、PR Case | Decision/Report | MULTIPLE |
| Risk | `risk_engine.py`、alert/report 风险路径 | CTH UI、Report、Action | PARTIAL |
| 品牌与业态 | swire/brand/profile 数据 | CTH UI | PARTIAL；KPI 来源需溯源 |
| Evidence 与案例回溯 | Evidence API/Store/Chain | UI、Report、Audit | MULTIPLE |
| Decision / Action | review workflow、action firewall | Outcome/Evaluation | PARTIAL |
| 运营报告 | report engine/daily report/export | UI/文件 | MULTIPLE / HIGH RISK |

## 3. BMP 功能

| 功能 | 当前实现候选 | 下游 | 状态 |
|---|---|---|---|
| Brand Focus | Brand Profile / domain context | BMP 页面与查询 | BLOCKED：正式 BMP 页面未验证 |
| 多品牌/竞品 | Brand profile、comparison 模块 | Analysis/Report | PARTIAL |
| Campaign | topic/campaign/propagation | Content/Event/Evaluation | MULTIPLE |
| Content Library | 内容生成、内容库、案例库 | Shared Creation/BMP | PARTIAL |
| KOS/KOL/KOC | `kos_engine.py`、attribution、ops、metrics、KOL analysis | Audience/Evaluation | MULTIPLE |
| Audience | 主体画像与互动数据 | Influence/Evaluation | PARTIAL |
| 传播事件 | Event Graph / propagation | Analysis/Risk | PARTIAL |
| 舆情事件 | Event/Risk/Public Opinion | Report/Decision | PARTIAL |
| 消费者需求 | AI/规则/主题分析候选 | BMP Insight | UNKNOWN / AI boundary required |
| 品牌对标 | Benchmark/competition 候选 | Evaluation | PARTIAL |
| 品牌评估 | evaluation/metrics/report | BMP UI/Report | MULTIPLE |
| BMP 页面体验 | ZBMP legacy routes/templates | Browser | BLOCKED：canonical route 404 |

## 4. Shared Capability 功能

| 功能 | 当前实现候选 | 消费者 | 状态 |
|---|---|---|---|
| Evidence | `evidence_chain.py`、`evidence_store.py`、`app_evidence.py` | CTH/BMP/System/AI | MULTIPLE |
| Canonical Data | `canonical_data.py`、`zbc_canonical_data` | Metric/Report/UI | MULTIPLE / P0 |
| Content Creation | `content_generation.py`、内容工作台 | CTH/BMP | PARTIAL |
| Podcast | podcast routes/entities/AI runs | CTH/BMP | PARTIAL；标题仍绑定 ZBMP |
| Evaluation | `evaluation_system.py`、AI evaluation/runner/recorder | 所有能力 | MULTIPLE |
| Learning Asset | AI learning、Heritage、OSAI contract | CTH/BMP/Engineering | PARTIAL |
| AI Enhancement | analyzer/filter/gateway/providers | CTH/BMP/Shared | PARTIAL；不得持有 Truth |
| Report Artifact | report artifact/export | CTH/BMP | MULTIPLE |

## 5. SYSTEM 功能

| 功能 | 当前实现候选 | 状态 |
|---|---|---|
| Collector | `collector.py`、`collector_v2`、automation、platform adapters | MULTIPLE |
| Xiaohongshu | Playwright/CDP/session/guard | PARTIAL；当前 SESSION_EXPIRED |
| 多平台 Adapter | XHS/Weibo/Bilibili/Douyin/其他槽位 | PARTIAL；多数未启用 |
| Browser/CDP | browser surface/runtime/internal browser/CDP helper | MULTIPLE |
| Auth Recovery | cookie/session/global recovery API | PARTIAL |
| Runtime Guardian | runtime guardian/watchdog/resident health | MULTIPLE；当前 UNKNOWN |
| Queue/Lease/Checkpoint/DLQ | guardian/collector guard | IMPLEMENTED CANDIDATE；当前无 worker 运行 |
| Database | `database.py` | ACTIVE CANDIDATE；数据库基线分裂 |
| Migration | migrations/Alembic/database migrations | MULTIPLE；clean bootstrap 失败过 |
| API | app + 22+ blueprints + legacy routes | MULTIPLE；Canonical Contract 未完成 |
| View Model/Viz | UI View Model、viz provider/API | PARTIAL；页面未全量接入 |
| Permission/Security | permission/security/agent boundary/firewall | MULTIPLE |
| AI Gateway | `ai_channel.py`、provider registry、本地/云 Provider | PARTIAL；8202 未启用 |
| Settings | system settings/config/env | PARTIAL；配置存在不等于有效 |
| Observability | health/log/metrics/trace/evidence | PARTIAL；缺统一 Runtime identity |
| Release | Docker/compose/scripts/portable assets | BLOCKED；无不可变血缘 |

## 6. Cross-Product Execution

| 功能 | 当前实现候选 | 状态 |
|---|---|---|
| Orchestrator | AI task engine/parser、OSAI orchestrator 候选 | MULTIPLE / 未证明唯一入口 |
| Specialist Agents | Agent registries / domain agents | PARTIAL |
| Skill Registry | LUMENIS 与 OSAI registries | MULTIPLE / 跨仓耦合 |
| Tool Registry | Tool/Capability registries | PARTIAL |
| Permission → Effect | Permission、Firewall、Fence、Approval | PARTIAL；未覆盖全部写入口 |
| Trace/Evaluation | 多 Evidence/Trace/Evaluation store | MULTIPLE |
| Cross-Repo Artifact | ZBC exporter、GGI outbox、OSAI contract | PARTIAL / Schema 不互操作 |

## 7. 当前不能删除的实现族

以下实现族均存在重叠，但在完成 Inventory → Dependency Trace → Runtime Verification → Regression 前不得删除：

- Collector / Collector V2 / Platform Adapter；
- Evidence Chain / Evidence Store / App Evidence；
- Canonical Data 双表与相关转换器；
- Event / Event Graph / Topic Snapshot；
- Report Engine / Daily Report / Export / V4 Report；
- Permission / Security Boundary / Agent Boundary / Action Firewall；
- Runtime Guardian / Watchdog / Resident Health；
- AI Gateway / Analyzer / Filter / Provider clients；
- legacy API、ZBMP 路由、v4_upgrade 与兼容层。

## 8. 总判定

功能资产丰富，但“一个能力一个 Canonical Implementation”尚未实现。当前功能地图状态为 `INVENTORIED / OWNERSHIP MAPPED / CANONICALIZATION PARTIAL`，不能把候选数量或旧 VERIFIED 标签视为生产完成率。
