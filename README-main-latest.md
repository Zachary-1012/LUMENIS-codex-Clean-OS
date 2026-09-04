# 序境 / LUMENIS

> **中文品牌：序境**  
> **English Canonical Brand：LUMENIS**  
> **한국어：서경**  
> **品牌哲学：芥子纳须弥 · 微小之中本身就包含通向整体的结构。**

## 1. Product Identity

**序境智能平台 / LUMENIS Intelligence Platform**  
**序境智能操作系统 / LUMENIS Intelligence OS**

本仓库 `Z-Brand-Core` 仅为 GitHub Repository identifier，不是产品品牌。

## 2. Dual-Core Architecture

```text
LUMENIS Intelligence OS
│
├── Intelligence Core
│   └── Zachary-OS-AI
│       Research · Intelligence · Agent · Skill · Evaluation · Learning
│
├── Production Core
│   └── Z-Brand-Core
│       Production · Data · Collection · Domain · Risk · Report · Runtime
│
└── Shared Governance
    Contract · Evidence · Trace · Permission · Lifecycle · AI Gateway · Skill Interface
```

两个 Git Repository **保持物理分离**。逻辑上通过明确 Contract、Evidence、Trace、Permission、Lifecycle 与 Adapter 协作；不得复制第三核心，不得为了融合而重写生产核心。

## 3. Canonical Layering

```text
L0 Experience
L1 Intelligence
L2 Capability
L3 Domain
L4 Foundation
```

ZBC 主要承担 L3 Domain + L4 Foundation 中的生产能力；OSAI 主要承担 L1 Intelligence + L2 Capability 中的智能与研发能力；共享边界由 Contract 定义。

## 4. Production Truth

ZBC 是 Production Truth 的权威持有方，负责：

- 生产数据与数据库
- 数据采集与来源适配
- 主体过滤与数据质量
- 舆情、事件、风险与分析
- KOS / Campaign 等生产能力
- 报告与导出
- API / Runtime / Health / Recovery
- 生产测试、证据与发布

AI、Agent、Research 或外部模型输出不得直接成为生产真相。

## 5. Protected Production Rules

以下能力为融合升级保护项：

```text
SUBJECT_WORDS
SUBJECT_EXCLUDE_WORDS
subject_hit()
CollectorGuard
```

规则优先于 AI。AI 只能增强分析、分类、摘要、推理与建议，不得绕过主体过滤、安全边界或确定性业务规则。

采集遇到验证码、安全验证、IP 风险或平台限制时，只能按合法平台流程停止、记录、冷却和恢复；不得破解或绕过平台安全机制。

## 6. Data Truth Chain

```text
External Data
→ Evidence / Raw
→ Parse
→ Validate
→ Normalize
→ Canonical Data
→ Function
→ Metric
→ Canonical Table / Truth Surface
→ View Model
→ Visualization / Report / Export / AI
```

一个业务计算只允许一个 Canonical Function / Formula；UI、Chart、Report、Export 与 AI 不得自行重算核心业务指标。`0`、`NULL/UNKNOWN`、`NOT_AVAILABLE`、`STALE`、`ERROR` 必须区分。

## 7. Intelligence Boundary

Research → Evidence → Contract → Implementation Specification → Production Implementation → Test → Evidence → Audit → Release

禁止 `AI / Agent → 直接修改 Production Truth`。

重要 AI 结论应保留模型、提示词、输入、输出、置信度、最终结果及人工修正等必要追踪信息。

## 8. Engineering Governance

统一研发生命周期：

```text
DISCOVER → REQUIREMENT → RESEARCH → EVIDENCE → DECISION
→ ARCHITECTURE → IMPLEMENT → TEST → VERIFY → RELEASE
→ OPERATE → MONITOR → LEARN → IMPROVE → RETIRE
```

Agent 执行闭环：

```text
READ → AUDIT → ANALYZE → PLAN → PATCH PREVIEW
→ TEST → VERIFY → HUMAN APPROVAL → COMMIT → PUSH
```

内部工程循环必须有边界：

```text
INSPECT → PLAN → EXECUTE → VERIFY → REPAIR → VERIFY → EVIDENCE → EVALUATE
```

必须具备最大迭代次数、最大运行时间、checkpoint、failure / blocked / budget 状态。禁止无限循环、自动绕过审批、自动 Merge 或未经授权 Push。

## 9. Repository / Permission Governance

Repository 必须通过 Registry / Resolver 发现，不得依赖个人机器固定路径，例如 `D:\Taikoo-monitor-new`。

标准权限：

`READ / AUDIT / ANALYZE / RESEARCH / PLAN / PATCH_PREVIEW / TEST / VERIFY / HUMAN_APPROVAL / COMMIT / PUSH`

默认可分析和测试；生产写入、Commit、Push 必须经过明确人工批准。

## 10. Skill Governance

Skill 通过统一 Skill Contract / Registry / Router 管理。Skill 必须定义输入、输出、权限、副作用、Evidence、Evaluation 与 Lifecycle。

第一阶段优先建设真实可运行的基础 Skill，而不是制造大量空壳；目标能力规模可逐步扩展至完整 Skill Registry。

## 11. UI / UX

统一采用 LUMENIS Design Language：专业、克制、高信息密度、清晰层级、数据/证据优先。

```text
Intelligence
Production
Research
Operations
```

为主 Workspace 信息架构。UI 遵循 Design Token、Component Contract、真实 API / State Contract，不使用假数据证明功能完成。

视觉基线：Apple-inspired、微光银 Signature、克制 Liquid Glass；Glass-on-Glass 禁止；正式图标使用线性图标，不使用 Emoji；支持 Light / Dark、Reduce Motion / Transparency；数据动效仅响应真实数据变化。

## 12. File Governance

正式资产按职责归类：

```text
00-GOVERNANCE/
01-PRODUCT/
02-ARCHITECTURE/
03-DESIGN/
04-DATA/
05-RUNTIME/
06-REPORT/
07-RESEARCH/
08-AUDIT/
99-ARCHIVE/
```

资产状态：`KEEP / MERGE / MIGRATE / LEGACY / ARCHIVE / DELETE`。

任何 Rename / Migration / Delete 必须先完成 Reference / Dependency / Runtime verification、迁移与回归测试。旧规则、旧代码、旧 UI 或旧文档**不得因为新架构出现就直接删除**；只有完成替代、依赖迁移、验证和明确批准后才能 DELETE。

## 13. README / Governance Authority

本 README 是仓库入口说明，不替代详细治理规则。

最高治理文件：

`00-GOVERNANCE/LUMENIS-ENGINEERING-GOVERNANCE-V1.0.md`

若历史文档与当前 Governance 冲突，以最新实际源码 + 最新 Governance + Contract 为准；历史资产保留时必须明确 `LEGACY / ARCHIVE` 状态。

## 14. Current Status

当前属于 **LUMENIS Dual-Core Convergence** 阶段。文档、Contract、Skill、Frontend、Runtime 等状态必须以实际源码和测试证据为准；规划项不得写成已完成能力。

**Status: Active · Production Core · LUMENIS Dual-Core Architecture**
