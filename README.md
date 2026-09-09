# 序境 / LUMENIS

> **Production Core · Production Truth Owner**
>
> 面向真实业务生产的独立产品：数据、采集、分析、风险、决策信息、报告、运行与产品体验由本仓库负责。

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
| 母产品 | **序境** | **LUMENIS** | **서경** | ZBC repository |
| CTH 产品 | **序境·商业运营** | **LUMENIS Commerce Operations** | **서경·커머스 운영** | CTH |
| BMP 产品 | **序境·品牌市场** | **LUMENIS Brand & Market** | **서경·브랜드 & 마켓** | BMP |
| 共享能力 | **序境·内容创作** | **LUMENIS Content & Creation** | **서경·콘텐츠 & 크리에이션** | Shared Capability |

> **命名原则：名称小、领域大；产品名保持克制，领域负责解释范围，功能负责解释能力。**

`CTH` 与 `BMP` 是稳定的内部技术标识；正式产品名称不得再扩展为历史名称。`ZBC` 继续作为 repository / engineering identifier 使用，不作为对外产品品牌。

### CTH / 序境·商业运营

**Commerce Operations Domain / 商业运营领域 / 커머스 운영 영역**。

CTH 是以 **Subject-first** 为核心的商业运营领域产品：用户先选择合法商业 Subject，再在该 Subject 上组织、观察、分析与行动其品牌、业态、内容、活动、传播、用户反馈、舆情、风险及相关业务对象。

CTH **不表示交易能力**，不再使用 Commerce & Trading Hub、Trading、商业交易、商业情报、Taikoo Hui Intelligence、太古汇智能等作为正式产品语义。

广州太古汇只是一个可选择的 `Subject Profile`，不是 CTH 产品本身，也不是永久产品边界。

### BMP / 序境·品牌市场

**Brand & Market Domain / 品牌市场领域 / 브랜드 & 마켓 영역**。

BMP 保持 **Brand-first / Primary Focus**：选择某一品牌代表当前主要监测主体与工作焦点，但不限制平台继续监测其他品牌、竞品、市场、内容、传播、用户反馈、趋势、事件与风险。

BMP 的正式产品名称不再使用 Z-Brand Monitoring Platform、Brand Intelligence、品牌智能等历史产品命名；`BMP` 作为兼容性内部 identifier 保留。

### 共享能力 / Content & Creation

内容创作不是 BMP 专属能力，也不是 CTH 专属能力。**Content & Creation / 内容与创作能力**属于 Shared Capability Layer，可由 CTH、BMP 及未来 LUMENIS 产品调用。

### Agent Groups

Agent Groups 不是第三个产品，而是 **Cross-Product Execution & Collaboration / 跨产品执行与协作层**，可以调用 CTH、BMP、共享内容能力、AI 与其他受控能力，但不得成为新的产品线。

### 产品领域关系

```text
LUMENIS / 序境
│
├── Commerce Operations Domain
│   └── 序境·商业运营 / LUMENIS Commerce Operations / CTH
│       └── Subject-first
│
├── Brand & Market Domain
│   └── 序境·品牌市场 / LUMENIS Brand & Market / BMP
│       └── Brand-first / Primary Focus
│
├── Shared Capability Layer
│   └── 序境·内容创作 / LUMENIS Content & Creation
│
└── Cross-Product Execution & Collaboration
    └── Agent Groups
```

### CTH / BMP 功能边界

- **CTH**：商业 Subject 驱动；能力随 `subject_id / scope` 绑定，覆盖主体下业务板块、品牌、业态、内容、活动、传播、用户、舆情、风险、分析、决策信息与报告等既有能力。
- **BMP**：Brand-first；保持原有多品牌、品牌/竞品、传播主体、内容、事件、风险、消费者需求、品牌对标、多平台监测等能力。
- **Shared Content**：内容创作跨 CTH / BMP 共享，不改变已有功能归属或运行链。
- **Agent Groups**：跨产品调用与执行层，不改变产品边界。

**CTH 与 BMP 的既有功能划分不因本次命名调整而重划。**

`SUBJECT_WORDS`、`SUBJECT_EXCLUDE_WORDS`、`subject_hit()` 等主体规则属于生产保护项；重构必须保持语义兼容并提供回归证据。

### 主体模型原则

```text
Product
  └─ Domain (CTH / BMP)
       └─ Selected Subject / Primary Focus
            ├─ Sub-Subject / Business Unit
            ├─ Industry / Category
            ├─ Content
            ├─ Event / Case
            ├─ Risk
            └─ Report / Decision
```

**选择主体 ≠ 改写生产事实。** 选择器只改变当前工作上下文、重点监测范围和下游视图；Canonical Data、Evidence、历史事件与已确认结果必须保持原始归属。

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

当前处于**产品级全量收口与持续产品化**阶段，覆盖前端、后端、API、数据库、采集、AI、Skill、Agent、Runtime、Security、Evidence、Evaluation、Report、Import/Export、KOS/KOL/KOC、Research、Learning 与历史实现。

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

本 README 是当前产品总入口。产品名称、领域归属与跨仓协议以当前 Canonical Registry 及三仓协议为准；旧版本 README 叙述、过期架构、失效状态不再作为当前事实来源；历史细节只保留在具有明确版本意义的审计、变更与证据文档中。

## 12. 状态声明

**序境 / LUMENIS · Independent Production Core · Production Truth Owner · AI-Enhanced, Not AI-Dependent**

本地优先 AI 的隔离集成说明：[`docs/ai_runtime/LUMENIS-OPEN-SOURCE-RUNTIME-AND-RESEARCH-INTEGRATION-V1.md`](docs/ai_runtime/LUMENIS-OPEN-SOURCE-RUNTIME-AND-RESEARCH-INTEGRATION-V1.md)。当前状态只允许以该文档及真实验收 Evidence 中的 `SHADOW_READY / READY_FOR_AUDIT` 表述，不代表生产批准。
