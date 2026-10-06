> **SUPERSEDED / HISTORICAL PRODUCT ARCHITECTURE — NOT CURRENT PRODUCT AUTHORITY.**
> Current sole product authority: `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`.
> Current execution: root `AGENTS.md`; current state: `00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md`.
> Retain the content below as provenance only; it must not override current owners, surfaces, scope or acceptance.

# 序境 / LUMENIS 最终产品架构

状态：SUPERSEDED / HISTORICAL SNAPSHOT

## 1. 产品定义

序境是面向真实业务生产的独立产品，是其数据、证据、分析、风险、决策、报告、运行和产品体验的 Production Truth Owner。

序境不是 AI 外壳，也不是普通 SaaS 菜单集合。它将业务事实转化为可以持续观察、理解、决策、创作、行动、评估和学习的生产生态。

```text
Observe → Understand → Decide → Create → Activate
→ Measure → Learn → Re-enter
```

AI 只能增强上述链路，不能拥有原始事实、业务规则、统计口径、数据所有权或最终决策权。

## 2. 唯一产品线

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
├── Shared Capability Layer
│   ├── Evidence
│   ├── Content & Creation
│   ├── Evaluation
│   ├── Learning Asset
│   └── AI Enhancement
│
└── SYSTEM
    ├── Collector / Browser / Auth
    ├── Runtime / Queue / Worker / Recovery
    ├── AI Gateway
    ├── Database / Migration
    ├── Security / Permission / Audit
    ├── Settings
    └── Observability
```

只有 CTH 与 BMP 是业务产品线。Shared Capability、SYSTEM、Agent Groups、AI、Research、OSAI、GGI、Command、Web/Desktop/Mobile/API 都不是第三或第四产品线。

## 3. CTH：序境·商业运营

CTH 以合法商业 Subject 为工作上下文，覆盖：

- Subject 与 Sub-Subject；
- 业务板块、品牌与业态；
- 外部内容、活动、传播和用户反馈；
- Evidence、Event、Case、Risk；
- Decision、Action、Outcome；
- 运营报告与复盘。

广州太古汇只是一个受保护 Subject Profile。CTH 不表示交易，不使用历史交易、商业情报或客户项目名作为正式产品语义。

选择 Subject 只改变当前上下文和视图，不改变 Evidence、Canonical Data、历史事件和已确认结果的原始归属。

## 4. BMP：序境·品牌市场

BMP 以 Brand 为主要工作焦点，覆盖：

- Brand / Competitor / Market；
- Campaign 与营销事件；
- Content 与内容资产；
- KOS / KOL / KOC / 普通用户 / 媒体 / 官方 / 机构；
- Audience、消费者需求与传播影响；
- 传播事件、舆情事件、风险；
- Evaluation、Benchmark、Action 和增长复盘。

选择 Brand 不改写事实归属。主体身份与内容属性必须分离，禁止把 UGC 等内容属性当作账号类型。

## 5. Shared Capability

共享能力由 CTH、BMP 按 Domain Context 调用：

| 能力 | 输入 | 输出 | 权威边界 |
|---|---|---|---|
| Evidence | Source/Raw Record | 可追溯证据 | 不由 AI 改写 |
| Content & Creation | Context/Brief/Evidence | 内容候选与资产 | 发布前需权限和审批 |
| Evaluation | Result/Outcome/Evidence | 评估、Badcase、Golden Case | 不回写原始事实 |
| Learning Asset | Evaluation/Human Feedback | 可复用知识候选 | 需验证、版本与采用门禁 |
| AI Enhancement | Task/Evidence/Rules | 分类、摘要、解释、建议 | 明确 Provider/Model/Confidence |

共享能力保持领域无关，但所有调用必须携带 `product_id/domain_id/context_id/subject_or_brand_id/permission/trace_id`。

## 6. SYSTEM

SYSTEM 只提供基础运行能力，不拥有业务事实：

```text
Source Adapter
→ Collector Guard
→ Auth / Browser Read-only Boundary
→ Normalize / Deduplicate / Quality
→ Evidence / Canonical Write
→ Worker / Queue / Lease / Checkpoint / DLQ
→ Health / Metrics / Trace / Audit
```

SYSTEM 健康必须按组件返回真实状态。`NO_RUN`、`NO_DATA`、`STALE`、`SESSION_EXPIRED`、`BLOCKED`、`UNKNOWN` 和 `ERROR` 不得映射为绿色健康。

## 7. Production Truth 架构

### 事实链

```text
External Data
→ Raw Evidence
→ Canonical Data
→ Deterministic Function
→ Metric
→ Truth Table
→ View Model
→ Visualization
→ UI / Report / Export
```

### 业务决策链

```text
Source → Evidence → Event → Case → Finding / Insight
→ Decision → Action → Outcome → Evaluation / Feedback
→ Learning Asset
```

每个节点必须有 canonical ID、owner、时间语义、版本、来源、状态和上游引用。AI 输出是派生节点，不能覆盖链中已有事实节点。

## 8. AI / Agent 架构

```text
User Intent
→ Orchestrator
→ Specialist Agent
→ Registered Tool / Skill
→ Evidence
→ Human Approval
→ Controlled Effect
→ Evaluation / Trace
```

生产写入唯一链：

```text
Task → Permission → Action Firewall → Effect Fence
→ Idempotency → Execute → Evidence → Evaluation → Trace
```

智谱、Ollama、ARK、千问或未来 Provider 都只能接入 AI Gateway。断网、无 Key 或模型不可用时，核心采集、过滤、去重、统计、风险和报告仍由确定性规则运行。

## 9. 产品体验架构

新设计不复刻旧页面和普通后台模板。统一认知结构是：

```text
Context
→ Current State / KPI
→ Change / Trend
→ Analysis
→ Evidence
→ Decision
→ Action
→ Outcome
```

CTH 的核心视觉对象是 Subject、Event、Risk 和 Action；BMP 的核心视觉对象是 Brand、Campaign、Content、Audience 和 Evaluation。两者共享设计语言，但不共享业务叙事。

动态只用于表达真实变化、因果、风险迁移、证据增长和行动反馈。禁止用装饰动画、虚构实时状态或 AI 文案制造“系统正在工作”的错觉。

## 10. 部署与仓库边界

- LUMENIS：Production Core 与 Production Truth Owner；
- OSAI：Shared Intelligence Core，可选、异步、非阻塞；
- GGI：独立产品；
- LUMENIS Command：私有研发 Sidecar，Observe → Control → Verify；
- 跨仓只允许版本化 Contract/Artifact；
- 不共享生产数据库、凭据、Session、内部 ORM 或必须同时部署的代码；
- 任一外部仓库停止不得阻断 LUMENIS 核心生产链。

## 11. 一套 Core、两种受控 Release

```text
LUMENIS Core Commit
├── CUSTOMER_RELEASE / CTH
└── LUMENIS_PLATFORM
    ├── CTH
    ├── BMP
    ├── Shared Capability
    └── SYSTEM
```

差异由不可变 Release Manifest、Profile、Capability/Route allowlist、权限和独立数据库控制，不复制两套长期 Core。

## 12. 完成标准

任何产品或能力只有同时具备以下证据才能标记 VERIFIED：

```text
Source + Call Graph + Data/API + Frontend/Consumer
+ Runtime + Tests + Production Evidence
```

架构已定义不等于实现完成。当前产品架构状态为 `DEFINED`，整体生产状态仍为 `NO-GO`。
