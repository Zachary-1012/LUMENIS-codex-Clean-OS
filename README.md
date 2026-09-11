# 序境 / LUMENIS

> **Production Core · Production Truth Owner**
>
> 当前阶段：**PRODUCTION CONVERGENCE**。本仓库负责序境 / LUMENIS 的真实生产代码、数据、Evidence、API、DB、Runtime、Permission、Metric、Report、UI binding、测试与 Production Acceptance。

## 0. Codex 唯一入口 / Canonical Codex Entrypoint

当前唯一 Codex 接手入口：

```text
Repository: Zachary-1012/LUMENIS-codex-Clean-OS
Branch: handoff/frontend-gpt-v24-20260911-final
Base: main
```

当前前端 / Experience 最终交付硬基线：

```text
TOTAL_SOURCE_RECORDS = 1604
NON_MEDIA_EXPECTED   = 682
PACKAGE_A_REQUIRED   = 642
PACKAGE_B_REQUIRED   = 40
MEDIA_EXCLUDED       = 922
WOFF2_REQUIRED       = 56
```

历史 `CANONICAL_IMPORT_MANIFEST.json / file_count=111` 只代表早期过度裁剪版本，**已废止，不得再作为完整 Codex handoff 标准**。

Package B 与 Package A 的 Legacy Delivery Evidence 可以发生 Git Blob 去重，但 **Package B 独立 provenance 必须永久保留**。

`READY_FOR_CODEX_EXECUTION` 只表示仓库已达到 Codex 可直接接手状态，**不等于 `PRODUCTION_READY`**。

---

## 1. Product Truth / 产品定义

序境不是 AI 外壳。AI 是增强能力，不是 Production Truth 本身。

### 内部主生产链

```text
External Data
→ Evidence
→ Canonical Data
→ Function
→ Metric
→ Truth Table
→ View Model
→ Visualization
→ UI / Report / Export
```

这条链属于 **backend / contracts / production logic / runtime truth**，不是普通页面视觉流程。

### 业务链

```text
Source
→ Evidence
→ Event
→ Case
→ Insight
→ Decision
→ Action
→ Outcome
→ Evaluation
→ Learning Asset
```

正常业务页面不得把以上内部链条做成长期可见的 decorative flow diagram / stepper / card chain / permanent process bar。

业务页面应展示：

`Context / Facts / Relationships / State / Evidence / Finding / Risk / Decision / Action / Outcome / Controls`

---

## 2. 四域 / Four Domains

### CTH｜序境·商业运营 / LUMENIS Commerce Operations

Subject-first。以 Selected Subject + Commerce Operations Lens 组织运营、事件、案例、风险、决策与行动。

### BMP｜序境·品牌市场 / LUMENIS Brand & Market

Brand / Market-first。支持品牌、竞品、KOS/KOL/KOC/UGC、Campaign、市场、传播、风险、Benchmark、Report / Evaluation。

### Shared Capability

共享能力，包括 Content & Creation、Evidence、Evaluation、Learning Asset、AI Enhancement。

### SYSTEM

Collector、Runtime、AI Gateway、Database、Security、Permission、Settings、Recovery、Observability。

CTH 与 BMP 共享统一 Subject Context 语义，但领域模型、Metric Pack、Relationship、Action Chain 不合并。

---

## 3. Authority Priority / 权威优先级

发生冲突时，必须按以下顺序：

```text
Current Production Source
>
Runtime Reality
>
Current DB / API / Permission / Evidence Contracts
>
Tests / Production Acceptance
>
Experience V2
>
Current Production UI capability evidence
>
Legacy Evidence
```

不得用旧聊天、旧 README、旧 commit message、Legacy UI、研究稿或前端静态稿覆盖当前真实 Source / Runtime / Data / Permission / Evidence / Test。

---

## 4. Experience V2 正式边界

Experience V2 负责：

- IA
- Experience
- Interaction
- Screen Contracts
- Visual Language
- Design Tokens
- Motion semantics
- Responsive behavior

Experience V2 **不能伪造或替代**：

- Backend
- API
- DB
- Permission
- Runtime
- Evidence
- Metrics
- Production status

前端前期工作已经完成并作为正式 handoff 资产入仓。Codex **不得重新从零研究 UI 趋势、重新定义 IA、重新搭第二套 Design System、重新做所有前端稿、重新定义 Experience V2**。

Codex 对前端的责任是：阅读、核验、必要修复、AI-01 + CTH-01 校准、真实 backend binding、E2E、验证后传播。

### Design Language v2.4

保持：

- black-silver / white-silver
- metallic monochrome
- editorial serif display
- restrained sans
- Lumen Axis / 序轴
- Strata / 境层
- de-boxed hierarchy
- whitespace
- hairlines
- Icy Cyan only for state / data semantics
- LUMENIS original AI orb
- Evidence / Trace-first
- semantic motion

失败标准：

- generic SaaS
- generic dashboard
- card wall
- purple / indigo AI template
- component-library demo
- 换 Logo 后仍像任何普通 AI SaaS

---

## 5. Legacy

Legacy 永久定义为：

```text
READ ONLY
EVIDENCE
CAPABILITY REFERENCE
```

Legacy 可以用于能力追踪、历史语义、回归、迁移依据，但不能覆盖 Current Production Truth，也不能要求 Codex 把旧 UI 当作最终 UI 来源。

---

## 6. Codex 接手顺序

```text
README
→ AGENTS
→ CODEX TAKEOVER
→ Experience V2 formal source
→ Contracts / Registries
→ Current backend / API / DB / Permission / Evidence / Runtime
→ Current Tests / Production Acceptance
→ AI-01 + CTH-01 calibration
→ real backend binding
→ Critical E2E
→ validated propagation
→ remaining module integration
→ GPT / MCP public adapter
→ Security / Regression / Recovery
→ Production Acceptance
```

第一阶段不是：

```text
Research → Re-design → New design system → New frontend architecture
```

第一阶段必须是：

```text
Read → Verify → AI-01 + CTH-01 calibration → Backend binding → E2E → Propagate
```

---

## 7. AI Conversation 安全边界

AI 页面允许展示：

- retrieval status
- evidence citation
- source
- tool status
- action status
- permission
- approval
- artifact
- provenance
- confidence
- limitation

禁止展示：

- private chain-of-thought
- system prompt
- developer prompt
- credentials
- cookie
- token
- browser session
- CDP
- security internals

---

## 8. ChatGPT / MCP 公共边界

正式链路：

```text
ChatGPT
→ MCP / App Adapter
→ Allowlisted Schema
→ Auth
→ Subject Context
→ Domain
→ Permission
→ Provenance / Policy
→ Versioned Internal Contract
→ LUMENIS Production Truth
```

公共 ChatGPT 不得直接访问：Collector、Cookie、Browser Session、CDP、raw DB、privileged hidden tools。

---

## 9. Production Acceptance

最终 Production Ready 必须真实通过：

1. `P0 Blocking = 0`
2. `Repository Integrity = PASS`
3. `Production Truth = PASS`
4. `Runtime + Critical E2E = PASS`
5. `Security + Recovery = PASS`
6. `Release Lineage + Rollback = VERIFIED`

任何一项未通过，不得声明 Production Ready。

---

## 10. 当前状态声明

**序境 / LUMENIS · Independent Production Core · Production Truth Owner · AI-Enhanced, Not AI-Dependent · Production Convergence**
