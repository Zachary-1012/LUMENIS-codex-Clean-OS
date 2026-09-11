# 序境 / LUMENIS

> **Production Core · Production Truth Owner**
>
> 当前阶段：**PRODUCTION CONVERGENCE + DESIGN ECOSYSTEM OPTIMIZATION**。本仓库负责序境 / LUMENIS 的真实生产代码、数据、Evidence、API、DB、Runtime、Permission、Metric、Report、UI binding、测试与 Production Acceptance。

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

当前 `READY_FOR_CODEX_EXECUTION` 判定暂缓，先完成豆包主导的 **Design Ecosystem Optimization** 并将其作为 Experience V2 的增量正式资产同步；该暂停不授权重新定义 Production Truth，也不允许重做已完成的前端前期。

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

## 5. Design Ecosystem Optimization / 设计生态系统优化

本阶段由 **豆包作为设计生态优化执行者**，基于已正式入仓的 Experience V2、Design Language v2.4、页面 source、contracts、registries、frontend engineering assets、research 与 legacy evidence 做 **增量优化**。

目标不是再做一套设计，而是把现有设计资产收敛成一个跨模块、跨页面、跨状态、跨设备可持续扩展的 **LUMENIS Design Ecosystem**。

### 豆包可以优化

- 全产品视觉与交互一致性
- 四域共享但不混淆的设计语义
- AI / CTH / BMP / Shared Capability / SYSTEM 页面之间的生态关系
- Layout、Grid、Spacing、Typography、Icon、Surface、Divider、State、Motion、Responsive 的统一规则
- 页面层级与 2–4 层动态信息架构的视觉承载
- Evidence / Trace / Decision / Action / Outcome 的统一呈现语义
- AI Conversation、Dashboard、Detail、Workspace、Report、Settings 等页面族的系统化模式
- Component / Pattern / Token / Motion / Interaction 的复用与变体治理
- Desktop / Tablet / Mobile 的响应式连续性
- Empty / Loading / Error / Stale / Unknown / Permission / Approval / Risk 等状态体系
- Accessibility、可读性、信息密度、动效性能与工程可实现性

### 豆包不得做

- 从零重建第二套 Design System
- 推翻 Experience V2 的正式边界
- 将 Legacy UI 重新提升为 Current Truth
- 发明不存在的 API / DB / Permission / Evidence / Metric / Runtime 能力
- 为追求视觉效果改变 Production Truth
- 把内部生产链或 Runtime 链做成业务页面装饰性流程图
- 将产品改成 generic SaaS / card wall / purple AI template

### 设计生态最终应形成

```text
LUMENIS Design Ecosystem
├─ Foundations
│  ├─ Color / Material / Typography / Grid / Spacing
│  ├─ Iconography / Illustration / AI Orb
│  └─ Motion / Accessibility / Responsive
├─ Tokens
│  ├─ Primitive Tokens
│  ├─ Semantic Tokens
│  └─ Domain / State Tokens
├─ Components
│  ├─ Core Components
│  ├─ Data / Evidence Components
│  ├─ AI Components
│  └─ Control / Permission Components
├─ Patterns
│  ├─ Context / Fact / Relationship
│  ├─ Evidence / Finding / Risk
│  ├─ Decision / Action / Outcome
│  └─ Approval / Provenance / Trace
├─ Page Families
│  ├─ AI Workspace
│  ├─ CTH
│  ├─ BMP
│  ├─ Shared Capability
│  └─ SYSTEM
└─ Governance
   ├─ Reuse / Variant Rules
   ├─ Responsive Rules
   ├─ Motion Rules
   ├─ Accessibility Rules
   └─ Engineering Acceptance
```

豆包交付后的设计生态资产属于 **Experience V2 增量正式输入**。Codex 接手后只做读取、真实性核验、工程实现、真实数据与后端绑定、必要修复和 E2E，不再重复设计生态前期工作。

---

## 6. Legacy

Legacy 永久定义为：

```text
READ ONLY
EVIDENCE
CAPABILITY REFERENCE
```

Legacy 可以用于能力追踪、历史语义、回归、迁移依据，但不能覆盖 Current Production Truth，也不能要求 Codex 把旧 UI 当作最终 UI 来源。

---

## 7. Codex 接手顺序

```text
README
→ AGENTS
→ CODEX TAKEOVER
→ Experience V2 + Design Ecosystem formal source
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

## 8. AI Conversation 安全边界

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

## 9. ChatGPT / MCP 公共边界

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

## 10. Production Acceptance

最终 Production Ready 必须真实通过：

1. `P0 Blocking = 0`
2. `Repository Integrity = PASS`
3. `Production Truth = PASS`
4. `Runtime + Critical E2E = PASS`
5. `Security + Recovery = PASS`
6. `Release Lineage + Rollback = VERIFIED`

任何一项未通过，不得声明 Production Ready。

---

## 11. 当前状态声明

**序境 / LUMENIS · Independent Production Core · Production Truth Owner · AI-Enhanced, Not AI-Dependent · Production Convergence + Design Ecosystem Optimization**
