# 序境 / LUMENIS

> **Production Core · Production Truth Owner**
>
> 面向真实业务生产的独立产品：数据、采集、分析、风险、决策信息、报告、运行与产品体验由本仓库负责。

## 品牌哲学 / Brand Philosophy

> **品牌哲学｜芥子纳须弥**
>
> **微小之中本身就包含通向整体的结构。**
>
> 序境从真实、具体、可验证的微小事实出发，建立证据、关系与上下文，由局部理解整体；又让每一个整体判断，都能够重新回到最初的证据。

序境相信，真正有价值的整体判断，并不是从宏大的结论开始，而是从一个个真实、具体、可验证的微小事实开始。

一条内容、一次互动、一个数据变化、一项用户反馈、一个事件、一份证据，都是一粒“芥子”。序境不让这些微小信号停留在孤立的数据里，而是沿着真实关系不断建立证据、事件、案例、洞察与行动，使局部逐渐显现它所处的整体环境。

因此，“芥子纳须弥”在序境中不是一句抽象的品牌修辞，而是一种贯穿产品、数据与生产的工作方式：

```text
微小真实 → Evidence → Canonical Data → Relationship / Event / Case
→ Finding / Insight → Decision → Action → Outcome
→ Evaluation / Feedback → 新的微小真实
```

**由微见著，由局部理解整体；又让每一个整体判断，都能够重新回到最初的证据。**

这是一条双向生产循环，而不是单向抽象：**芥子 → 须弥 → 芥子**。能力可以被抽象、复用与增强，但 Production Truth、Evidence、所有权、安全、权限与合规边界不能因此模糊。AI 可以增强发现、理解与推理，但不能替代真实事实与生产真相。

## 0. 当前执行阶段 / Current Execution Phase

**CURRENT PHASE: PRODUCTION CONVERGENCE**

本仓库已经进入最终生产收敛阶段。当前优先级不是继续横向扩张，而是：

```text
Capability Closure
→ Runtime Verification
→ Production Acceptance
→ Release Candidate
→ Production / Operating
```

每次 Codex / Agent / 人工研发执行前后都必须执行真实审计循环：

```text
READ CURRENT REPO → AUDIT CURRENT TRUTH → CLASSIFY GAPS
→ IMPLEMENT / FIX → TEST → VERIFY → EVIDENCE
→ UPDATE STATUS → RE-AUDIT
```

强制读取：

- 当前 `README.md`
- 当前 `AGENTS.md`
- `00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md`
- 当前 Governance / Architecture / Audit / Runtime / Test / Evidence

除明确 P0 / P1 或最终收敛所需能力外，新功能默认进入 Backlog，不得打断收敛。

最终六大 Gate：

1. `P0 Blocking = 0`
2. `Repository Integrity = PASS`
3. `Production Truth = PASS`
4. `Runtime + Critical E2E = PASS`
5. `Security + Recovery = PASS`
6. `Release Lineage + Rollback = VERIFIED`

任意一项未通过，不得声明 Production Ready。

### 四仓 Canonical Registry

| 仓库 | 当前角色 | 真相所有权 | 对其他仓运行时依赖 |
|---|---|---|---|
| `Zachary-1012/LUMENIS-codex-Clean-OS` | 序境 / LUMENIS Production Core | Production Truth | 无 |
| `Zachary-1012/Zachary-OS-AI` | LUMENIS Intelligence / OSAI | Shared Intelligence Capability | 无 |
| `Zachary-1012/global-growth-intelligence` | Global Growth Intelligence | Research / Growth Truth | 无 |
| `Zachary-1012/lumenis-command` | 序枢 / LUMENIS Command | R&D Control / Engineering Evidence | 不得成为产品 Runtime 依赖 |

`Zachary-1012/Z-Brand-Core` 视为历史 / Legacy 工程资产，不是当前四仓 Canonical Production Registry 中的主生产仓；任何恢复、对照或迁移必须先做依赖追踪与当前等价能力审计。

跨仓共享只能通过**版本化、可追溯、可验证的 Contract / Artifact / Evidence**，不得共享生产数据库、生产凭据、隐藏运行时耦合或未经验证的事实。

## 1. 产品定位

序境不是“AI 产品外壳”。**AI 是序境中的增强能力，不是生产真相本身。**

序境必须在 AI 不可用时仍能完成核心生产流程；AI 可用于发现、分类、摘要、解释、推理、建议与工程辅助，但不能替代确定性业务规则、原始事实、Evidence、最终业务边界或生产数据所有权。

核心生产链：

```text
External Data → Evidence → Canonical Data → Function → Metric
→ Truth Table → View Model → Dynamic Visualization → UI / Report / Export
```

业务情报链：

```text
Source → Evidence → Event → Case → Finding / Insight
→ Decision → Action → Outcome → Evaluation / Feedback → Learning Asset
```

## 2. 产品定位与领域产品

序境拥有自己的 Product Truth、Subject Truth、Production Data、Collection Runtime、Event / Case / Risk、Metrics / Reports、Production UX、Production Permissions 与 Production Runtime。

### 正式产品名称

| 层级 | 中文正式名 | English 正式名 | 한국어 | 内部标识 |
|---|---|---|---|---|
| 母产品 | **序境** | **LUMENIS** | **서경** | ZBC repository identifier / legacy compatibility |
| CTH 产品 | **序境·商业运营** | **LUMENIS Commerce Operations** | **서경·커머스 운영** | CTH |
| BMP 产品 | **序境·品牌市场** | **LUMENIS Brand & Market** | **서경·브랜드 & 마켓** | BMP |
| 共享能力 | **序境·内容创作** | **LUMENIS Content & Creation** | **서경·콘텐츠 & 크리에이션** | Shared Capability |

> **命名原则：名称小、领域大；产品名保持克制，领域负责解释范围，功能负责解释能力。**

`CTH` 与 `BMP` 是稳定的内部技术标识；正式产品名称不得再扩展为历史名称。`ZBC` 仅作为历史 / engineering compatibility identifier 使用，不作为对外产品品牌，也不覆盖当前 Canonical Repository Registry。

### 统一主体上下文 / Global Subject Context

CTH 与 BMP **都支持主体可选择**。两者不得分别建立互不兼容的主体选择体系，而应共享同一套 `Subject Context` / 主体上下文语义。

统一原则：

```text
Selected Subject
→ Domain Lens
→ Scope / Permission
→ Query / Function / Metric
→ View Model
→ UI / Report / Export
```

主体决定当前工作上下文；领域决定分析方法、指标体系、对象关系、功能组合与行动链。

建议的目标 Contract 至少覆盖：

```text
SubjectContext
├── subject_id
├── subject_type
├── domain
├── scope
├── permissions
├── time_window
├── locale
└── context_version
```

该结构是当前 Production Convergence 的目标契约方向；真实实施必须先审计当前 Source / Route / API / Service / DB / Cache / Permission / Frontend，再做兼容映射，不得凭文档直接重写现有生产链。

### CTH / 序境·商业运营

**Commerce Operations Domain / 商业运营领域 / 커머스 운영 영역**。

CTH 是 **Selected Subject + Commerce Operations Lens**：用户选择合法商业 Subject 后，以商业运营视角组织、观察、分析与行动其业务板块、品牌、业态、内容、活动、传播、用户反馈、舆情、风险及相关业务对象。

CTH **不表示交易能力**，不再使用 Commerce & Trading Hub、Trading、商业交易、商业情报、Taikoo Hui Intelligence、太古汇智能等作为正式产品语义。

广州太古汇是当前已有业务规则与生产保护最成熟的一个可选择 `Subject Profile`，不是 CTH 产品本身，也不是永久产品边界。

### BMP / 序境·品牌市场

**Brand & Market Domain / 品牌市场领域 / 브랜드 & 마켓 영역**。

BMP 同样支持 **Selected Subject**，并以 **Brand & Market Lens** 处理当前主体：围绕品牌、竞品、市场、内容、传播主体、KOS / KOL / KOC / UGC、消费者需求、趋势、Campaign、Event / Case / Risk、Benchmark、Report / Evaluation 等能力形成品牌与市场工作链。

BMP 不再以“只有品牌才能作为固定主语”作为产品边界；品牌仍是其最重要、最常见的 `subject_type` 之一，但主体上下文必须允许当前源码与业务契约支持的其他合法主体类型。

BMP 的正式产品名称不再使用 Z-Brand Monitoring Platform、Brand Intelligence、品牌智能等历史产品命名；`BMP` 作为兼容性内部 identifier 保留。

### 共享能力 / Content & Creation

内容创作不是 BMP 专属能力，也不是 CTH 专属能力。**Content & Creation / 内容与创作能力**属于 Shared Capability Layer，可由 CTH、BMP 及未来 LUMENIS 产品调用。

### Agent Groups

Agent Groups 不是第三个产品，而是 **Cross-Product Execution & Collaboration / 跨产品执行与协作层**，可以调用 CTH、BMP、共享内容能力、AI 与其他受控能力，但不得成为新的产品线。

### 产品领域关系

```text
LUMENIS / 序境
│
├── Global Subject Context
│   └── Selected Subject
│
├── Commerce Operations Domain
│   └── 序境·商业运营 / LUMENIS Commerce Operations / CTH
│       └── Selected Subject + Commerce Operations Lens
│
├── Brand & Market Domain
│   └── 序境·品牌市场 / LUMENIS Brand & Market / BMP
│       └── Selected Subject + Brand & Market Lens
│
├── Shared Capability Layer
│   └── 序境·内容创作 / LUMENIS Content & Creation
│
└── Cross-Product Execution & Collaboration
    └── Agent Groups
```

### CTH / BMP 功能边界

- **CTH**：主体可选择；以商业运营视角处理主体下业务板块、品牌组合、业态、内容、活动、传播、用户反馈、舆情、风险、分析、决策信息、行动与报告等既有能力。
- **BMP**：主体可选择；以品牌与市场视角处理品牌/竞品、传播主体、内容、Campaign、消费者需求、市场趋势、事件、风险、品牌对标、决策、行动与评估等既有能力。
- **Shared Subject Context**：CTH / BMP 共享主体上下文契约，不复制两套主体选择基础设施；Domain 与 Subject 必须可以独立切换和验证。
- **Shared Content**：内容创作跨 CTH / BMP 共享，不改变已有功能归属或运行链。
- **Agent Groups**：跨产品调用与执行层，不改变产品边界。

**CTH 与 BMP 的既有功能划分不因统一 Subject Context 而重划。统一的是主体上下文与隔离规则，不是把两个领域合并成一个。**

`SUBJECT_WORDS`、`SUBJECT_EXCLUDE_WORDS`、`subject_hit()` 等主体规则属于生产保护项；重构必须保持语义兼容并提供回归证据。

### 主体模型原则

```text
Product
  └─ Selected Subject
       └─ Domain Lens (CTH / BMP)
            ├─ Scope / Permission
            ├─ Sub-Subject / Business Unit
            ├─ Industry / Category
            ├─ Content
            ├─ Event / Case
            ├─ Risk
            └─ Report / Decision / Action
```

**选择主体 ≠ 改写生产事实。** 选择器只改变当前工作上下文、重点监测范围和下游视图；Canonical Data、Evidence、历史事件与已确认结果必须保持原始归属。

Subject Context 必须贯穿并隔离：

```text
Subject Selector
→ URL / Router Context
→ API Context
→ Permission Validation
→ Query / Function Scope
→ Cache Key
→ Evidence / Trace
→ Report / Export Snapshot
```

不得仅依赖前端传入 `subject_id` 作为授权依据；后端必须重新验证 Subject access。缓存、查询、指标、报告与导出不得发生跨 Subject 污染。

## 3. 四仓边界

```text
                         ┌────────────────────────────┐
                         │ OSAI / LUMENIS Intelligence│
                         │ Shared Intelligence Core   │
                         └─────────────┬──────────────┘
                                       │
                          Versioned Contract / Artifact
                                       │
                 ┌─────────────────────┴─────────────────────┐
                 │                                           │
       ┌─────────▼──────────┐                      ┌─────────▼──────────┐
       │ 序境 / LUMENIS     │                      │ Global Growth      │
       │ Production Core    │                      │ Intelligence        │
       │ Production Truth   │                      │ Independent Product │
       └────────────────────┘                      └─────────────────────┘

       LUMENIS Command / 序枢
       = Private R&D Sidecar
       = Observe → Control → Verify
       = Never a product runtime dependency
```

硬边界：

1. 序境不调用 GGI 生产代码或生产数据库。
2. OSAI 不是序境启动、采集、分析、报告或核心业务的运行时前置条件。
3. 不共享生产数据库、生产凭据或未经验证的产品事实。
4. 跨仓共享只能通过版本化、可追溯的 Contract / Artifact。
5. 序枢停止、删除或故障，不得导致序境生产不可运行。
6. 四仓每次发生边界、命名、Contract、Release 或 Runtime 变更时，必须先审计当前真实状态并检查四仓兼容性。

## 4. AI / Skill / Agent

目标 AI 架构：

```text
Zhipu + Local AI
       │
       ├── deterministic rules / functions
       └── advisory / analysis

Legacy Provider
       ↓
仅在真实依赖链仍存在且经验证时保留
```

Provider 的 ACTIVE 状态必须由真实调用链、健康验证和测试证据证明；历史配置不等于正在使用。无效或无调用链的旧 Provider，在完成依赖追踪后清理。

Skill Registry、Skill Execution Contract、Agent、Permission、Effect Fence、Evidence、Evaluation、Trace 必须形成真实运行链，而不是仅存在文件或接口。

生产写入：

```text
Task → Permission → Action Firewall → Effect Fence / Idempotency
→ Execute → Evidence → Evaluation → Trace
```

AI / Agent 不得绕过生产权限直接修改 Production Truth。

## 5. Runtime / Security / Reliability

生产运行覆盖：Process / Worker Heartbeat、DB / Queue / Lease、Checkpoint / Resume、Retry / DLQ、Collector、Browser / CDP、Provider、Auth / Session、Security Boundary、Audit / Trace / Evidence。

安全采用 Edge → Application → Permission / Agent Tool Firewall → Data → Runtime → Supply Chain 的分层边界。安全声明必须以可重复测试与运行证据为依据。

## 6. 前端 / API / 数据真实性

前端是生产数据的真实 View，不是独立静态展示层。

- 所有状态来自真实 API / State Contract。
- 禁止伪造完成、指标、运行、测试、部署状态。
- 数据展示必须可追溯到 Evidence / Event / Case / Metric。
- 动态时间视图保留真实时间语义、freshness、confidence 与变化量。
- UI/UX 使用序境自己的视觉与交互体系，不复制外部模板。
- 页面、API、数据模型、Runtime 状态同步演进。

## 7. 数据库与历史实现

每张表必须明确：所有权、事实含义、读写者、生命周期、canonical ID、保留与迁移策略。

旧表、旧字段、旧 API、旧脚本、旧 UI 不得凭“看起来没用了”直接删除，必须经过：

```text
Inventory → Dependency Trace → Runtime Verification
→ KEEP / MERGE / MIGRATE / LEGACY / ARCHIVE / DELETE
→ Regression → Evidence
```

## 8. 工程生命周期

```text
DISCOVER → REQUIREMENT → RESEARCH → EVIDENCE → DECISION → ARCHITECTURE
→ IMPLEMENT → TEST → VERIFY → RELEASE → OPERATE → MONITOR
→ LEARN → IMPROVE → RETIRE
```

工程权限闭环：

```text
READ → AUDIT → ANALYZE → PLAN → PATCH PREVIEW
→ TEST → VERIFY → HUMAN APPROVAL → COMMIT → PUSH
```

原则：**先审计、再修改；先兼容、再重构；先旁路、再切换；先验证、再删除。**

## 9. 当前状态

当前处于 **Production Convergence / 最终生产收敛** 阶段，覆盖前端、后端、API、数据库、采集、AI、Skill、Agent、Runtime、Security、Evidence、Evaluation、Report、Import/Export、KOS/KOL/KOC、Research、Learning 与历史实现。

状态严格区分：`PLANNED / IMPLEMENTED / TESTED / VERIFIED / RELEASED / OPERATING`。

文件存在 ≠ 功能完成；测试通过 ≠ 生产运行完成；页面可打开 ≠ 数据链路完成。

## 10. 完成标准

只有同时具备以下证据，才能声明能力完成：

```text
Source + Call Graph + Data / API + Frontend / Consumer
+ Runtime + Tests + Production Evidence
```

## 11. 文档治理

工程规范：[`00-GOVERNANCE/LUMENIS-ENGINEERING-GOVERNANCE-V1.0.md`](00-GOVERNANCE/LUMENIS-ENGINEERING-GOVERNANCE-V1.0.md)

最终收敛母清单：[`00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md`](00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md)

本 README 是当前产品总入口。产品名称、领域归属与跨仓协议以当前 Canonical Registry 及**四仓协议**为准；旧版本 README 叙述、过期架构、失效状态不再作为当前事实来源；历史细节只保留在具有明确版本意义的审计、变更与证据文档中。

## 12. 状态声明

**序境 / LUMENIS · Independent Production Core · Production Truth Owner · AI-Enhanced, Not AI-Dependent · Production Convergence**