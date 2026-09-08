# LUMENIS 能力注册表收敛核验 V1

状态：第 4 类“能力地图 / 能力归属”审计交付物  
审计对象：`Zachary-1012/Z-Brand-Core` 清洁基线  
审计提交：`78c469d81905568350338f9d01e2ce5baf3c6c67`  
结论性质：事实核验与目标归属方案，不声明所有能力已完成生产验证。

## 1. 判定原则

本文件只把真实仓库、运行时、数据库、测试和页面能够支持的内容记为事实。旧文档、文件名和注册表状态不能单独证明能力完成。

能力只有同时具备以下证据，才可标记为 `ACTIVE / VERIFIED`：

`Source → Call Graph → Data/API → Frontend/Consumer → Runtime → Tests → Production Evidence`

本轮没有删除源码、没有改写生产数据库、没有把旧实现直接判为可删除。

## 2. 真实注册表快照

来源：`00-GOVERNANCE/feature_registry.csv`，由当前清洁仓库直接读取。

| 项目 | 事实 |
|---|---:|
| 注册表记录 | 334 |
| Owner 值 | 334 条全部为 `Shard-D/Team1` |
| IMPLEMENTED | 88 |
| INTEGRATED | 192 |
| TESTED | 54 |
| AI Provider/Gateway 记录 | 134 |
| 主要业务域 | Product/Domain/Subject、Data Collection、Event、Case/Public Opinion、Risk、Report、KOS/KOL、Campaign/Topic |
| 主要系统域 | Runtime、Browser/CDP/Login、AI Gateway、Permission、Evidence、Evaluation、DB/Migration、Security/Audit |

这些状态是注册表字段，不等价于本次审计所要求的生产证据。当前注册表的 DB、API、Frontend、Permission 字段大量为空，因此它更像历史能力目录，不能直接作为生产能力真相。

## 3. 纯净产品线归属

目标归属严格采用新的 LUMENIS 产品方案：

### LUMENIS / 序境

生产核心与生产真相所有者，负责真实业务生产链和产品体验。

### CTH / 序境·商业运营

`Subject-first`。负责选定商业主体后的运营观察、事件、案例、风险、决策、行动和报告语义。CTH 不是交易产品，广州太古汇只是可配置 Subject Profile。

### BMP / 序境·品牌市场

`Brand-first`。负责品牌、竞品、传播主体、Campaign、Content、Audience、市场事件、品牌评估与品牌对标语义。

### Shared Capability / 序境·内容创作

跨 CTH 与 BMP 复用的 Evidence、Content Creation、Evaluation、Learning Asset、AI Enhancement 能力。

### SYSTEM

Collector、Runtime、AI Gateway、Database、Security、Settings、Browser 等系统能力。SYSTEM 不是产品线。

### Agent Groups

跨产品执行与协作层，不是第三个产品，也不得形成第四产品线。

## 4. 能力收敛表

下表给出当前实现候选与真实审计状态。候选表示“需要沿调用链验证的正式入口”，不是已经完成的断言。

| 能力 | 目标归属 | 当前主实现候选 | 已发现的其他实现/风险 | 当前判定 |
|---|---|---|---|---|
| Subject 识别与主体边界 | LUMENIS 生产边界，CTH/BMP 消费 | `subject_rules.py` | `subject_classifier.py`、`subject_context.py` 可能承担不同层职责；必须保持主体词、排除词和 `subject_hit()` 语义 | 需调用链回归 |
| Collection | SYSTEM / Collector | `collector.py` | `collector_v2`、`collector_automation.py`、平台采集器并存；不得按文件名直接删除 | 多实现，待收口 |
| Browser / CDP | SYSTEM | `browser_surface.py`、`browser_surface_api.py`、`browser_runtime/` | `internal_browser*`、`cdp_helper.py` 等存在边界重叠 | 需运行时验证 |
| Evidence | Shared Capability | `evidence_chain.py` | `evidence_store.py`、`app_evidence.py`、`evidence_api.py`；需明确事实证据与应用证据 | 候选待验证 |
| Canonical Data | LUMENIS 生产核心 | `canonical_data.py` | 另有 `canonical_metrics.py`、T4 registry；需确认唯一写入与 ID 血缘 | 需数据链验证 |
| Event | CTH/BMP 领域语义，共享基础设施 | `event_graph.py`、`reprocess.py` | `weekly_events.py`、`topic_snapshot.py` 等可能重复聚合 | 多实现，待收口 |
| Case | CTH/BMP 领域语义 | `case_deep_analysis.py`、`public_opinion_cases.py` | `pr_case_*`、`case_library.json` 等存在历史/专题分支 | 需定义 canonical case |
| Risk | CTH/BMP 领域语义，SYSTEM 执行基础设施 | `risk_engine.py` | 风险规则还可能在报告、主体和告警路径中重复调用 | 需规则与指标回溯 |
| Decision / Action | CTH/BMP 领域语义 | `review_workflow.py`、`p2_action_firewall.py` | Agent/action 路径必须经过 Permission、Firewall、Effect Fence、幂等 | 证据不足 |
| Report | CTH/BMP 消费，LUMENIS 生产核心生成 | `report_engine.py` | `daily_report.py`、`report_api.py`、`report_artifact.py`、`export_report.py` 并存 | 需确认唯一编排入口 |
| KOS/KOL/KOC | BMP 领域能力，CTH 可按主体调用 | `kos_engine.py`、`kos_attribution.py` | `kos_ops.py`、`kos_paid.py`、`kos_metrics.py`、`kol_analysis.py` 等是子能力或重复实现待判 | 领域能力存在，未完成收口 |
| Campaign / Content | BMP；Content Creation 为 Shared | `topic_campaign.py`、`content_generation.py` | `brand_propagation.py`、内容/案例模块边界需要按输出物重划 | 需产品归属验证 |
| AI Gateway | SYSTEM / Shared Enhancement | `ai_channel.py`、`provider_registry.py` | `local_ai_client.py`、`ark_llm.py`、`osai_engine` 侧能力；Provider 状态必须由真实调用证明 | 运行时待验证 |
| AI Analysis / Learning | Shared Capability | `ai_analyzer.py`、`ai_learning_engine.py` | `ai_filter.py`、`evaluation_system.py` 等需区分增强结果、事实和评估 | 必须保持事实不可覆盖 |
| Permission / Security | SYSTEM | `permission_gate.py`、`security_boundary.py`、`safety_boundary.py` | Agent 权限与应用权限存在跨仓边界，不能各自绕过 | 需端到端验证 |
| Evaluation | Shared Capability | `evaluation_system.py`、`ai_evaluation.py` | `evaluation_runner.py`、`evaluation_recorder.py` 可能是执行器/记录器，不应重复定义标准 | 需统一 Contract |
| Runtime | SYSTEM | `runtime_guardian.py`、`runtime_preflight.py` | `system_guardian.py`、`system_watchdog.py`、`resident_health.py` 并存 | 需确认唯一健康真相 |
| Database / Migration | SYSTEM | `database.py`、`database_migrations.py` | `alembic/`、`migrations/`、`models.py` 并存；必须区分生产/测试/实验 | 已发现迁移风险 |

## 5. 注册表问题

1. 所有记录共享同一 Owner，无法表达 CTH、BMP、Shared Capability 与 SYSTEM 的真实归属。
2. 334 条记录混合能力、实现、平台适配器、运行脚本、Provider 和实验资产，粒度不一致。
3. `IMPLEMENTED / INTEGRATED / TESTED` 的定义未绑定本次七段证据链，不能直接推出 `VERIFIED` 或 `OPERATING`。
4. AI Provider/Gateway 占 134 条，存在“配置很多但真实调用链未证明”的误判风险。
5. DB、API、Frontend、Permission 字段大量缺失，无法完成从能力到消费者的闭环追踪。
6. 已发现若干相同文件/函数在注册表重复出现，包括 `canonical_data.py`、`wechat_notifier.py`、`agent_identity.py` 等；这是重复登记证据，不等于可以删除实现。
7. 旧注册表没有把 Evidence、Metric、Truth Table、View Model、Visualization、Report 串成可审计的数据真相链。

## 6. 归属与状态规则

后续收口必须把每条能力拆成：

`Capability → Canonical Implementation → Contract → DB → API → Frontend → Permission → Test → Runtime Evidence`

状态使用：

- `ACTIVE`：唯一生产入口已确认，且七段证据完整。
- `DUPLICATE`：与另一实现产生同一业务输出，待保留一个 canonical 入口。
- `LEGACY`：历史兼容实现，仍可能被依赖，禁止直接删除。
- `DEPRECATED`：已有替代物且有迁移路径，但尚未清理。
- `DEAD`：依赖追踪、运行验证和测试均证明无消费者。
- `UNKNOWN`：证据不足，必须继续审计。

在完成依赖追踪与回归前，当前多数“多实现”只能标记为 `UNKNOWN / LEGACY CANDIDATE`，不能直接标记 `DEAD`。

## 7. 本轮七项验收

| 验收项 | 结果 | 证据 |
|---|---|---|
| Source | PASS | 当前清洁仓库、`feature_registry.csv`、各候选模块均已读取 |
| Call Graph | PARTIAL | 注册表能列出入口，但不能替代完整运行调用链；多实现仍待验证 |
| Data / API | PARTIAL | 注册表大量接口/数据库字段为空，需逐能力补齐 |
| Frontend / Consumer | PARTIAL | 已确认前端存在领域页面，但注册表未完成能力到页面映射 |
| Runtime | PARTIAL | 运行时模块存在；注册表没有把每项能力绑定健康、任务、队列与实际运行证据 |
| Tests | PASS（注册表结构层） | 当前仓库测试资产可发现；本轮未把“注册表状态”冒充全链路生产通过 |
| Production Evidence | FAIL（能力收口层） | 尚未为 334 条记录逐条建立生产证据 |

### 本轮结论

第 4 类“能力地图 / 能力注册表事实审计”完成；“所有能力已经完成 canonical 收口”未完成，正式状态为 `PARTIAL / UNKNOWN`。这不是失败隐藏，而是按红线保留真实边界。

下一项应以本文件为基线，继续执行第 5 类“数据真相链审计”，优先核验：

`External Data → Evidence → Canonical Data → Function → Metric → Truth Table → View Model → Visualization → Report`

重点先处理 Evidence、Canonical Data、Metric、Report 的唯一来源与数据库血缘，不得在证据不足时删除任何旧实现。

## 8. 研究依据

- Backstage Software Catalog：以实体、所有权和关系图维护软件目录的官方文档，用作“能力必须具备 Owner、关系和可追踪元数据”的研究参考：<https://backstage.io/docs/features/software-catalog/>。
- Backstage Catalog Graph：用关系图表达组件依赖与所有权关系的官方文档：<https://backstage.io/docs/features/software-catalog/creating-the-catalog-graph/>。
- LUMENIS 新产品设计基线：`LUMENIS_NEW_PRODUCT_DESIGN_BASELINE_V1.md`，仅作为本仓库本轮目标归属方案，不沿用旧页面设计。

