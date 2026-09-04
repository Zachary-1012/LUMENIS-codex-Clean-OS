# 序境

> **序境**  
> **한국어: 서경**  
> **English Canonical Brand: TBD**  
> **品牌哲学：芥子纳须弥· 微小之中本身就包含通向整体的结构。**

## Canonical Naming

| Layer | Canonical |
|---|---|
| 中文品牌 | **序境** |
| 韩文品牌 | **서경** |
| English Canonical Brand | **TBD** |
| 品牌哲学 | **芥子纳须弥· 微小之中本身就包含通向整体的结构。** |

历史英文名称 `Xujing` / `Xujing Core` / `Xujing Intelligence` 统一标记为 **LEGACY**，仅用于历史兼容、Git 历史、审计或必要技术追溯，不得作为新的 Canonical Brand。

英文 Canonical Brand 在完成命名、全球冲突、语言/文化、商标初筛、数字身份和架构适配审查并获得明确确认前，始终保持 `TBD`。

`Z-Brand-Core` 仅为 GitHub Repository identifier，不等同于中文产品品牌；`Core` 不作为中文正式产品名称。

## Twin Repository

```text
Zachary-OS-AI
Research & Intelligence
        │
        │ Evidence / Contract / Implementation Specification
        ↓
Z-Brand-Core
Production Truth
```

本仓库承担 Production Truth：生产代码、生产数据、采集、业务规则、风险、报告、Runtime、测试与发布。Research、Agent 或外部模型输出不得直接改变生产真相。

## Integration, Not Rewrite

本基线是对既有产品、架构、功能和规则的**融合升级**，不是推倒重做，不因新研究或新技术随意改版。

```text
Existing Production
      ↓
Inventory / Reference Scan / Dependency Scan
      ↓
Evaluate New Capability
      ↓
KEEP / MERGE / MIGRATE / LEGACY / ARCHIVE / DELETE
      ↓
Regression Test
      ↓
Evidence / Audit
      ↓
Release
```

处理原则：
- 已稳定且仍有效的能力 **KEEP**，不重复建设。
- 新能力只有在正确性、稳定性、性能、维护性、复用、安全或交互质量上有明确收益时才 **MERGE / MIGRATE**。
- 可融合的旧能力优先改造，不另起一套平行实现。
- 已被替代、冲突、重复且确认无运行依赖的规则或文件，完成引用/依赖扫描、迁移和回归验证后 **DELETE**。
- 有审计或证据价值的历史资产仅保留为 **LEGACY / ARCHIVE**，不得继续参与 active implementation。
- 不以“现代化”或“新技术”作为删除既有生产能力的理由。

## Research → Core Gate

```text
Research
→ Evidence
→ Contract
→ Implementation Specification
→ Core Implementation
→ Test
→ Evidence
→ Audit
→ Release
```

研究成果先验证，再决定是否进入生产；未通过 Gate 的研究成果不得标记为生产能力。

## Parent / Child Product Architecture

```text
ZBP = eventual parent system
CTH = child system/domain + current first development/validation environment
```

CTH-first development is intentional: implement and stabilize capabilities in CTH first, then absorb proven capabilities into ZBP through audited contracts/adapters/extraction. Final capability ownership is determined by dependency, reuse, data authority, runtime importance, business coverage, stability and measured benefit—not naming alone.

## Architecture Evolution Gate

Architecture may evolve only when evidence demonstrates a material improvement in correctness, stability, performance, maintainability, reuse, security or interaction quality. No rewrite-by-fashion. Stable collection and authoritative subject filtering must not be weakened merely for modernization.

## Data Intelligence Pipeline

所有外部数据和生产分析遵循统一链路：

```text
External Data
→ Ingestion
→ Raw / Evidence
→ Parse
→ Validate
→ Normalize
→ Canonical Data
→ Function
→ Metric
→ Canonical Table / Truth Surface
→ View Model
→ Visualization
→ UI / Report / Export / AI
```

核心规则：
- 外部输入先进入 Evidence / Data 层，不直接成为生产真相。
- 一个业务计算只允许一个 Canonical Function / Formula。
- 核心 Metric 统一口径、版本和时间窗口。
- Canonical Table 是数字 Truth Surface。
- Chart、UI、Report、Export、AI 消费 Canonical 输出，不自行重新计算业务指标。
- 核心数据必须具备来源、Evidence、Lineage、Freshness 与异常状态。
- `0`、`NULL/UNKNOWN`、`NOT_AVAILABLE`、`STALE`、`ERROR` 不得混用。

## Product / System Naming Standard

生产产品的中文 Canonical 名称为 **序境**，韩文标准表达为 **서경**，英文 Canonical Brand 暂为 **TBD**。

产品、子系统、模块、工作流与功能名称必须服从 Canonical Registry；不得自行创造第三套品牌命名。

## Core Responsibilities

- 生产代码与生产数据库
- 数据采集与来源适配
- 主体过滤与数据质量
- 舆情、事件、风险与分析
- KOS / Campaign 等生产能力
- 报告与数据导出
- API、Runtime、Health、Recovery
- 测试、证据与发布

## KOS / Production Intelligence

KOS 属于正式生产能力，沿用现有业务口径、数据表、指标和判定规则。新增研究或计算能力必须接入 Canonical Function / Metric / Table 链路，不得建立平行 KOS 真相。

## AI Boundary

AI 是生产能力增强层，不得绕过核心规则成为 Production Truth 的最终裁决者。重要 AI 结论必须能够追溯至证据，并记录必要的模型、提示词、输入、输出、置信度、最终结果及人工修正信息。

## UI / Interaction

```text
Shell → Workspace → Product / Domain → Module → Page → Section → Component → Window / Action
```

Window 和 route state 保留必要的 parent context、target、child context 与 return context。动态交互与可视化遵循同一层级。

统一 UI/UX 标准继续沿用既有 Design Language；新能力必须融入现有系统，而不是另建视觉或交互体系。

## File Governance

正式文件必须归属于明确模块：

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

资产状态统一使用：`KEEP / MERGE / MIGRATE / LEGACY / ARCHIVE / DELETE`。

任何 Rename / Migration / Delete 必须先做 Reference / Dependency / Runtime verification，再进行迁移、回归测试与 Audit。无用、冲突、重复、已被替代且无生产依赖的 active 规则和文件不得继续保留为当前规范。

## Protected Production Rules

以下既有生产能力为保护项，不得因融合升级而削弱：

```text
SUBJECT_WORDS
SUBJECT_EXCLUDE_WORDS
subject_hit()
```

采集遇到风控、验证码、平台安全限制或异常状态时，遵守现有安全边界，不以绕过平台安全机制换取采集结果。

## Release & Acceptance Gate

```text
Function
→ Data
→ Metric
→ UI / Table / Chart
→ Report / Export
→ AI
→ Stability / Recovery
→ Security
→ Regression
→ Evidence
→ Audit
→ Release
```

上线硬门槛：
- P0 核心流程 100% 通过
- 核心数据 Schema / Function / Metric 验证通过
- 核心 UI / Table / Chart / Report 数值一致
- 核心数据 Evidence / Lineage 可追溯
- Critical / Blocker = 0
- 核心故障可发现、可记录、可恢复或升级处理
- 发布前必须具备回滚路径

## Current Principle

- 序境是 Production Truth；序境-智能是 Research & Intelligence。
- 不建立第三核心库，不复制生产真相。
- 新能力采用融合、改造、迁移优先，不进行无依据的重写。
- 研究不直接写 Production Truth；AI 不替代确定性安全规则和人工决策 Gate。
- 不把未来概念写成当前已实现能力。
- 不让新模块脱离 Canonical Registry 独立生长。
- 不以英文品牌研究提前修改仓库名或生产架构。
- 英文 Canonical Brand 未确认前始终为 `TBD`。
- 每次更新都必须继承累计基线，先扫描既有依赖，再处理新增能力。
- 无用、冲突、重复、已被替代的 active 规则和文件，在安全迁移及回归验证后删除。

**Status: Active · Production Truth · Governed by Canonical Naming, Cumulative Architecture Baseline & Twin Repository Synchronization**
