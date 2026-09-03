# 序境-Core｜Module / Page / Workflow / Data Registry

> Canonical Product Baseline · 2026-09-04
> 依据：《序境｜双子库全量收敛与产品研发总执行指令》
> 说明：本 Registry 基于当前仓库真实源码盘点建立，映射到序境统一 IA。
> 状态：INVENTORY-DONE / CONTINUOUSLY-MAINTAINED

---

## 1. 信息架构（IA）

```
序境
├─ 观测  来源 / 采集 / 内容 / 舆情
├─ 洞察  趋势 / 事件 / 风险 / 机会
├─ 关系  品牌 / 创作者 / 内容 / 事件关系
├─ 行动  KOS / Campaign / 处置
├─ 研究  AI / 时尚 / 设计 / 高奢 / 重奢 / 创新品牌 / 技术
├─ 创作  Podcast / Report
├─ 智能  AI / Search / Assistant / Analysis
└─ 系统  Settings / Permission / Sources / Accounts / Runtime / Health
```

页面层级：`Product → Workspace → Module → Page → Section → Component → Action`

---

## 2. Module Registry（序境-Core）

> Module ID 规则：`MOD-<IA分组>-<序号>`。Owner 唯一；Consumer 经 Contract/API/Adapter。

| Module ID | IA 分组 | 模块名 | 核心源码 | 职责 | 状态 |
|---|---|---|---|---|---|
| MOD-OBS-01 | 观测·采集 | 小红书采集器 | collector.py / xhs_cdp_collector.py | XHS 话题/笔记采集（CDP 为主） | PASS |
| MOD-OBS-02 | 观测·采集 | 采集自动化 | collector_automation.py / collector_v2_integration.py | 自动/手动采集编排、时长与冷却控制 | PASS |
| MOD-OBS-03 | 观测·采集 | 自适应调节引擎 | adaptive_engine.py / platform_adapters/scheduling | 采集频率、退避、熔断、恢复策略 | PASS |
| MOD-OBS-04 | 观测·采集 | 采集守卫 | collector_guard/ | 采集安全门、失败隔离 | PASS |
| MOD-OBS-05 | 观测·采集 | CDP/Cookie 桥 | xhs_cookie_bridge.py / import_xhs_cookies.py | Cookie 导入、CDP 端口归属 | PASS |
| MOD-OBS-06 | 观测·来源 | Web 监测 | web_monitor.py / web_topic_discovery.py | 网页/话题发现监测 | PASS |
| MOD-OBS-07 | 观测·内容 | 监测流水线 | monitor_pipeline.py | 内容标准化、入库流水线 | PASS |
| MOD-INS-01 | 洞察·事件 | 事件图谱 | event_graph.py | 事件关系、三类四关系 | PASS |
| MOD-INS-02 | 洞察·风险 | 风险引擎 | risk_engine.py | 风险评分、日报风险口径 | PASS |
| MOD-INS-03 | 洞察·主体 | 主体规则 | subject_rules.py | SUBJECT_WORDS / 主体过滤（红线） | PASS |
| MOD-INS-04 | 洞察·趋势 | 话题快照 | topic_snapshot.py / topic_campaign.py | 话题数据快照、趋势 | PASS |
| MOD-INS-05 | 洞察·统计 | 重算/统计 | reprocess.py / brand_stats_recompute.py | 统计聚合、重算 | PASS |
| MOD-REL-01 | 关系·品牌 | 品牌知识库 | brand_knowledge_base.py | 品牌/竞品知识 | PASS |
| MOD-REL-02 | 关系·创作者 | KOL 分析 | kol_analysis.py | KOL 画像与关系 | PASS |
| MOD-ACT-01 | 行动·KOS | KOS 引擎 | kos_engine.py / kos_attribution.py | KOS 发现、归属、评分、分层 | PASS |
| MOD-ACT-02 | 行动·KOS | KOS 运营 | kos_execution.py / kos_ops.py / kos_paid.py | KOS 运营、留资、邀约、投流 | PARTIAL |
| MOD-ACT-03 | 行动·KOS | KOS 报告 | kos_report.py / kos_routes.py | KOS 报告与路由 | PASS |
| MOD-ACT-04 | 行动·处置 | 舆情处置 | review_workflow.py / pr_case_engine.py | 案例、处置工作流 | PASS |
| MOD-CRE-01 | 创作·报告 | 报告引擎 | report_engine.py / report_filter.py / export_report.py | 日报/周报/月报/专题 + 导出 | PASS |
| MOD-INT-01 | 智能·AI | 智谱 AI 网关 | intelligence.py / ark_llm.py | chat/search/vision 分级 + 预算 + 缓存 | PASS |
| MOD-INT-02 | 智能·AI | AI 资源包 | ai_resource_packs.py | 资源配额、用量、暂停 | PASS |
| MOD-INT-03 | 智能·AI | AI 分析 | ai_analyzer.py / ai_filter.py / ai_governance.py | AI 增强分析（非事实源） | PASS |
| MOD-INT-04 | 智能·学习 | AI 学习引擎 | ai_learning_engine.py / learning_collector.py | 学习采集、知识沉淀 | PASS |
| MOD-SYS-01 | 系统·Runtime | 生产运行时 | run_production.py / run_supervised.py / runtime_preflight.py | 启动、守护、预检 | PASS |
| MOD-SYS-02 | 系统·Health | 健康监控 | system_health_api.py / resident_health.py / stability_monitor.py | Health、heartbeat、恢复 | PASS |
| MOD-SYS-03 | 系统·安全 | 安全边界 | security_scanner.py / safety_boundary.py / compliance_gate.py | 敏感扫描、安全 Gate | PASS |
| MOD-SYS-04 | 系统·数据 | 数据层 | database.py / models.py / schema_registry.py | DB 访问、模型、Schema | PASS |
| MOD-SYS-05 | 系统·浏览器 | 内部浏览器 | internal_browser.py / browser_runtime_api.py | 系统内浏览/预览/Evidence | PARTIAL |
| MOD-SYS-06 | 系统·配置 | 设置中心 | settings_module.py / auth_recovery_center.py | 设置、权限、账户 | PASS |

---

## 3. Page Registry（序境-Core，生产侧）

> Page ID 规则：`PAGE-<ModuleID>-<序号>`。

| Page ID | Module | 页面名 | 静态入口 | 职责 |
|---|---|---|---|---|
| PAGE-OBS-01-01 | MOD-OBS-01 | 采集工作台 | static/collector*.html | 采集启停、状态、参数 |
| PAGE-INS-01-01 | MOD-INS-01 | 舆情驾驶舱 | static/*dashboard* | 风险/趋势/事件总览 |
| PAGE-ACT-01-01 | MOD-ACT-01 | KOS 工作台 | static/kos*.html | KOS 池、归属、分层 |
| PAGE-CRE-01-01 | MOD-CRE-01 | 报告中心 | static/report*.html | 报告查看/生成/导出 |
| PAGE-INT-01-01 | MOD-INT-01 | AI 资源面板 | static/*（topbar ⚡） | 资源用量、暂停、按次执行 |
| PAGE-SYS-01-01 | MOD-SYS-01 | 系统健康 | static/*health* | Runtime/Health/Recovery |
| PAGE-SYS-06-01 | MOD-SYS-06 | 设置中心 | static/settings*.html | 设置/权限/账户 |

---

## 4. Workflow Registry（关键生产工作流）

| Workflow ID | 名称 | 触发 | 步骤链 | 状态 |
|---|---|---|---|---|
| WF-COLLECT-01 | 小红书定时采集 | 自动 00:00 / 12:00（≤60min） | 调度→预热→采集→入库→关闭 | PASS |
| WF-COLLECT-02 | 小红书手动采集 | 手动（≤30min） | 手动触发→采集→入库 | PASS |
| WF-RISK-01 | 日报生成 | 每日 | 聚合事件→风险评分→主体过滤→日报 | PASS |
| WF-KOS-01 | KOS 闭环 | 手动/计划 | 采集→归属 Gate→评分→分层→运营→报告 | PARTIAL |
| WF-AI-01 | AI 增强分析 | 按需 | 分级→预算→缓存→调用→证据 | PASS |

---

## 5. Data Registry（核心数据对象）

| Data ID | 对象 | 主表 | 关键字段口径 | 时间模型 |
|---|---|---|---|---|
| DAT-NOTE | 笔记 | notes | 正文/互动/作者 | publish_datetime（发布）、captured_at（采集） |
| DAT-TOPIC | 话题快照 | topic_snapshots | 浏览量/讨论量/笔记数 | snapshot_date（快照时间） |
| DAT-EVENT | 事件 | events | 事件类型/关系 | event_date |
| DAT-KOS | KOS 账号资产 | kos_* | 归属/评分/分层/资产 | updated_at |
| DAT-EVIDENCE | 证据 | evidence_* | source/result/verification | created_at |

**数据铁律**：`publish_datetime` 优先于 `captured_at`；Event Date ≠ Publish Date ≠ Collection Date ≠ Update Date ≠ Snapshot Date；禁止 AI 生成数据冒充原始数据；数据必须有来源、有时间、有状态。

---

## 6. 维护规则

1. 新增模块必须先在 Module Registry 登记并判定 IA 归属，禁止直接新增一级入口。
2. 同一 Capability 只能有一个 Canonical Implementation（Owner 唯一）。
3. 跨库能力复用走 Contract / Adapter，禁止复制核心实现。
4. 状态使用统一标准：`PASS / PARTIAL / BLOCKED / NOT_VERIFIED / FAILED / LEGACY / DEPRECATED`。
5. 本 Registry 随真实代码变更持续更新。
