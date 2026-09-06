# 序境 / LUMENIS Intelligence Core

> **中文品牌：序境**  
> **English Canonical Brand：LUMENIS**  
> **한국어：서경**  
> **正式产品：序境智能平台 / LUMENIS Intelligence Platform**  
> **整体系统：序境智能操作系统 / LUMENIS Intelligence OS**

`Zachary-OS-AI` 仅为 GitHub Repository identifier，不是产品品牌。

## 1. Dual-Core Architecture

```text
LUMENIS Intelligence OS
│
├── Intelligence Core
│   └── Zachary-OS-AI
│       AI · Agent · Research · Knowledge · Skill · Evaluation · Learning
│
├── Production Core
│   └── Z-Brand-Core
│       Production · Data · Collection · Domain · Risk · Report · Runtime
│
└── Shared Governance
    Contract · Evidence · Trace · Permission · Lifecycle · AI Gateway
```

两个 Git Repository **保持物理分离**。OSAI 是 Intelligence Core，不是生产数据库，也不拥有 Production Truth。

## 2. Intelligence Core Responsibility

OSAI 负责：

- Agent / Orchestration
- Research / Knowledge / Evidence
- Skill Registry / Skill Router
- Evaluation / Benchmark
- Learning
- Architecture Research
- Contract / Implementation Specification
- Engineering Loop
- AI Gateway / Model Routing
- 研发建议与可验证工程能力

生产数据、生产业务规则、主体过滤、风险与报告真相仍由 ZBC 负责。

## 3. Canonical Naming

| 对象 | 中文 | English | 한국어 |
|---|---|---|---|
| 品牌 | **序境** | **LUMENIS** | **서경** |
| 智能核心 | **序境智能中枢** | **LUMENIS Intelligence Core** | **서경 Intelligence** |
| 生产核心 | **序境生产中枢** | **LUMENIS Production Core** | **서경 Production** |
| 整体系统 | **序境智能操作系统** | **LUMENIS Intelligence OS** | — |

历史 `Xujing` / `Xujing Intelligence` 仅作为 Legacy 追溯，不作为新的 Canonical Brand。

## 4. Layering

```text
L0 Experience
L1 Intelligence
L2 Capability
L3 Domain
L4 Foundation
```

OSAI 主要承担 L1 Intelligence 与 L2 Capability；通过 Contract 向 ZBC 提供可验证能力，不建立第三核心。

## 5. Intelligence → Production Gate

```text
Research
→ Evidence
→ Contract
→ Implementation Specification
→ Production Implementation
→ Test
→ Evidence
→ Audit
→ Release
```

禁止 `AI / Agent → 直接修改 Production Truth`。涉及生产写入必须经过正式 Permission / Contract / Release Gate。

## 6. Engineering Loop

```text
READ → AUDIT → ANALYZE → PLAN → PATCH PREVIEW
→ TEST → VERIFY → HUMAN APPROVAL → COMMIT → PUSH
```

内部循环：

```text
INSPECT → PLAN → EXECUTE → VERIFY → REPAIR → VERIFY → EVIDENCE → EVALUATE
```

必须受最大迭代次数、最大运行时间、checkpoint、budget、failed、blocked 状态约束。禁止无限循环、绕过人工批准、自动 Merge 或未经批准 Push。

## 7. Skill Governance

Skill 通过统一 Registry / Contract / Router 管理。每个 Skill 必须明确：

- Input
- Output
- Permission
- Side Effects
- Evidence
- Evaluation
- Lifecycle

第一阶段优先建设真实可运行的基础能力，不制造大量空壳 Skill。

## 8. AI Gateway

AI Gateway 保持 Provider-Agnostic，可承载 Local 与 Cloud Provider。现有 Zhipu 能力不得因新模型接入被无依据删除；Ollama / gpt-oss 可作为 Local Provider。

API Key / Secret 不得进入源码、前端、日志、测试样例或 Git。

## 9. Evidence / Trace / Lifecycle

重要任务必须形成：

`Task → Repository → File → Module → Function → Change → Test → Result → Evidence → Lifecycle → SHA`

统一生命周期：

`DISCOVER → REQUIREMENT → RESEARCH → EVIDENCE → DECISION → ARCHITECTURE → IMPLEMENT → TEST → VERIFY → RELEASE → OPERATE → MONITOR → LEARN → IMPROVE → RETIRE`

文档声明不能替代源码、测试与运行证据。

## 10. Research Governance

研究资产必须可检索、可引用、可追溯并具有证据等级与状态。外部论文、开源模型、代码、案例和产品只能作为研究输入；采用前必须进行适配、许可证/权利边界、Evaluation 与治理审查。

推荐状态：`FACT / VERIFIED / PENDING / CONCEPT / RECOMMENDATION / LEGAL REVIEW / LEGACY / REJECT`。

## 11. UI / UX Boundary

OSAI 与 ZBC 使用统一 LUMENIS Design Language，但 UI 不改变后端业务边界。页面必须消费真实 API / State Contract，不使用假数据证明完成；正式图标不得使用 Emoji；支持 Light / Dark 与可访问性状态。

## 12. File Governance

```text
00-GOVERNANCE/
01-PRODUCT/
02-ARCHITECTURE/
03-RESEARCH/
04-KNOWLEDGE/
05-MODELS/
06-EVALUATION/
07-CONTRACTS/
08-AUDIT/
99-ARCHIVE/
```

资产状态统一：`KEEP / MERGE / MIGRATE / LEGACY / ARCHIVE / DELETE`。

旧文件、旧规则、旧实现不得因新架构出现就直接删除。DELETE 必须经过引用/依赖扫描、替代或迁移、回归验证和明确批准。

## 13. Governance Authority

详细工程治理规则位于：

`00-GOVERNANCE/LUMENIS-ENGINEERING-GOVERNANCE-V1.0.md`

若历史文档与当前源码、Contract 或治理规则冲突，不得把历史文档当作当前实现事实。

## 14. Current Status

当前为 **LUMENIS Dual-Core Convergence**。任何能力是否“完成”必须由源码、测试、运行与 Evidence 共同证明；规划不得伪装为已实现。

**Status: Active · Intelligence Core · LUMENIS Dual-Core Architecture**
