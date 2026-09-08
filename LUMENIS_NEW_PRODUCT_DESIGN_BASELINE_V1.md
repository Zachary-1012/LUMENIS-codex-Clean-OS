# 序境 / LUMENIS 新产品设计基线 V1

状态：用户方案确认后的新设计基线

用途：作为十二大类连续执行的产品设计权威，不复刻原线上仓库的旧产品结构。

## 1. 设计权威顺序

设计与实现采用以下顺序：

1. 用户确认的完整中文版 LUMENIS 方案；
2. 当前源码、数据库、Runtime、测试和真实页面证据；
3. 原线上仓库的最终收敛文档，仅用于识别已存在能力、兼容约束和历史血缘；
4. 研究结果与工程参考，仅用于提出可验证的实现方式。

原线上架构不得直接作为新产品设计模板。任何历史命名、菜单、模块、API、表和 Agent 结构都必须重新映射。

## 2. 最终产品线

LUMENIS 是一个面向真实业务生产的独立产品，负责数据、证据、分析、风险、决策、报告、运行和产品体验。

```text
序境 / LUMENIS
│
├── CTH｜序境·商业运营
│   └── Subject-first
│       Subject → Evidence → Event → Case → Risk
│       → Decision → Action → Outcome
│
├── BMP｜序境·品牌市场
│   └── Brand-first / Primary Focus
│       Brand → Campaign → Content → Audience
│       → Event → Evaluation → Action
│
├── Shared Capability｜共享能力层
│   ├── Evidence
│   ├── Content Creation
│   ├── Evaluation
│   ├── Learning Asset
│   └── AI Enhancement
│
└── SYSTEM｜系统层
    ├── Collector
    ├── Runtime
    ├── AI Gateway
    ├── Database
    ├── Security
    ├── Settings
    └── Observability
```

只允许两条业务产品线：CTH 与 BMP。Shared Capability、SYSTEM、Agent Groups、AI、Research、Command 都不是第四产品线。

## 3. 未来产品形态

LUMENIS 不设计成普通 SaaS 管理后台，而设计成一个可以持续传播、营销、运营、广告和创作的业务生态系统。

核心闭环不是“功能菜单”，而是：

```text
Observe → Understand → Decide → Create → Activate
→ Measure → Learn → Re-enter the next decision
```

其中：

- Observe：采集外部数据、业务事件和用户反馈；
- Understand：从 Evidence 形成 Canonical Data、Event、Case、Risk 和 Insight；
- Decide：把事实转化为可追溯的 Decision；
- Create：调用共享内容与创作能力，生成传播、营销、广告或运营资产；
- Activate：经权限和人工审批后进入行动；
- Measure：记录行动结果与传播反馈；
- Learn：形成 Evaluation 和 Learning Asset，但不能覆盖原始事实。

## 4. 领域边界

### CTH：商业运营

CTH 以合法商业 Subject 为入口。广州太古汇只是一个 Subject Profile，不是产品名称，也不固化为永久边界。

CTH 负责主体下的业务板块、品牌、业态、内容、活动、传播、用户反馈、舆情、事件、风险、分析、决策信息和报告。

### BMP：品牌市场

BMP 以 Brand 为主要工作焦点，但保留多品牌、竞品、市场、传播主体、内容、事件、风险、消费者需求、对标和多平台监测能力。

选择 Brand 只改变当前工作重点，不改变 Canonical Data 的事实归属。

### Shared Capability：共享能力

共享能力由 CTH、BMP 及未来 LUMENIS 产品调用。共享能力必须通过明确 Contract、Permission、Evidence 和 Evaluation 工作，不得暗中改变业务归属。

### SYSTEM：系统层

系统层只提供运行、存储、采集、安全、模型接入、配置和可观测能力，不拥有 CTH 或 BMP 的业务事实。

## 5. 产品体验设计

用户体验以“上下文和决策”组织，而不是以旧菜单组织：

```text
Context → KPI → Trend → Analysis → Evidence
→ Decision → Action → Outcome
```

每一个页面、模块和组件都必须能够回答：

1. 当前主体/品牌/范围是什么；
2. 当前看到的事实来自哪条 Evidence 链；
3. 变化是什么，可信度和新鲜度如何；
4. 需要做什么决策；
5. 行动之后如何反馈和评估。

LUMENIS 可以有 Web、Desktop、Mobile、API 和 Command 入口，但入口不是新的产品线；所有入口必须共享同一 State Contract 和 Evidence 语义。

## 6. AI 与 Agent 设计

```text
User Intent
    ↓
Orchestrator
    ↓
Specialist Agents
    ↓
Tools / Skills
    ↓
Evidence
    ↓
Human Approval
```

AI 与 Agent 只能增强发现、分类、摘要、解释、推理、建议、创作和工程辅助；不得拥有 Production Truth、数据所有权、最终业务规则或最终业务边界。

生产写入必须经过：

```text
Task → Permission → Action Firewall → Effect Fence
→ Idempotency → Execute → Evidence → Evaluation → Trace
```

智谱、Ollama、OpenCode 等是受控执行工具或 Provider，不是产品线；Provider 不可用时，核心生产链必须由规则和数据继续运行。

## 7. 数据与产品的唯一事实链

```text
External Data → Evidence → Canonical Data → Function → Metric
→ Truth Table → View Model → Visualization → UI / Report / Export
```

业务情报链：

```text
Source → Evidence → Event → Case → Finding / Insight
→ Decision → Action → Outcome → Evaluation / Feedback
→ Learning Asset
```

AI 输出永远是带有 Provider、Model、Prompt/Task、Confidence、Evidence Reference 和人工修正状态的派生结果，不得覆盖原始 Evidence 或 Canonical Data。

## 8. 旧实现处理原则

原线上已收敛的代码分类只作为资产清单。每项实际实现必须重新进入：

```text
Inventory → Dependency Trace → Runtime Verification
→ KEEP / MERGE / MIGRATE / REFACTOR / LEGACY / ARCHIVE / DELETE
```

没有调用链、数据影响、Runtime、测试和生产证据，不得声明 ACTIVE，也不得直接删除。

## 9. 十二大类执行映射

十二大类作为一条连续工程链执行：

1. 事实基线与干净工程基线；
2. 源码、数据库与 Runtime 全量审计；
3. 本设计基线下的最终产品线与领域重映射；
4. Capability Registry 与唯一实现收敛；
5. Evidence 到 UI/Report 的数据真相链；
6. 前端产品体验与信息架构重构；
7. 决策驱动的动态化；
8. AI / Agent / Orchestrator 执行链；
9. API、数据库、迁移、安全、依赖和性能质量；
10. 兼容、旁路、灰度和 Release 血缘；
11. 真实运行、真实页面和跨仓 Contract 验证；
12. 完整研发路线、上线准备和持续闭环。

每一项都必须完成 Source、Call Graph、Data/API、Frontend/Consumer、Runtime、Tests、Production Evidence 七类证据，未齐全时只能标记为 PARTIAL 或 BLOCKED。

## 10. 明确禁止

- 不把原线上 UI、菜单或双核文案直接当作新设计；
- 不增加第四产品线；
- 不把 AI、Agent、Content、Research 或 Command 包装成新业务产品；
- 不让 AI 覆盖生产事实；
- 不用假数据、静态页面、通过测试或配置存在冒充上线；
- 不把旧系统清理等同于产品重构；
- 不为追求“纯净”删除未完成溯源的代码、表、API、Provider 或数据。

## 11. 完成标准

只有当新设计在真实源码、调用链、数据库、API、前端、Runtime、测试和生产证据中均得到验证，LUMENIS 才能进入 RELEASED / OPERATING。
