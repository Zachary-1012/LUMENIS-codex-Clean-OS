# 序境

> **序境**  
> **한국어: 서경**  
> **English Canonical Brand: TBD**  
> **品牌哲学：芥子纳须弥**  
> **哲学定义：微小之中本身就包含通向整体的结构。**

## Canonical Naming

| Layer | Canonical |
|---|---|
| 中文品牌 | **序境** |
| 韩文品牌 | **서경** |
| English Canonical Brand | **TBD** |
| 品牌哲学 | **芥子纳须弥** |

历史英文名称 `Xujing` / `Xujing Core` / `Xujing Intelligence` 统一标记为 **LEGACY**，仅用于历史兼容、Git 历史、审计或必要技术追溯，不得作为新的 Canonical Brand。

英文 Canonical Brand 在完成命名、全球冲突、语言/文化、商标初筛、数字身份和架构适配审查并获得明确确认前，始终保持 `TBD`。

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

本仓库承担 Production Truth。Research、Agent 或外部模型输出不得直接改变生产真相。

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

## Parent / Child Product Architecture

```text
ZBP = eventual parent system
CTH = child system/domain + current first development/validation environment
```

CTH-first development is intentional: implement and stabilize capabilities in CTH first, then absorb proven capabilities into ZBP through audited contracts/adapters/extraction. Final capability ownership is determined by dependency, reuse, data authority, runtime importance, business coverage, stability and measured benefit—not naming alone.

## Architecture Evolution Gate

Architecture is allowed to change when the replacement is demonstrably better in correctness, stability, performance, maintainability, reuse, security or interaction quality. No rewrite-by-fashion. Stable collection and authoritative subject filtering must not be weakened merely for modernization.

## Rename / Migration Gate

任何 Canonical Rename / Migration 必须按以下顺序执行：

```text
Inventory
→ Reference Scan
→ Dependency Scan
→ Canonical Registry Update
→ Documentation Update
→ Code / Config Migration Plan
→ Test
→ Evidence
→ Audit
→ Release
→ Legacy Mapping
```

## Product / System Naming Standard

生产产品的中文 Canonical 名称为 **序境**，韩文标准表达为 **서경**，英文 Canonical Brand 暂为 **TBD**。

不要使用 `Core` 作为中文正式产品名称。`Z-Brand-Core` 仅为现有 GitHub Repository identifier，不等同于中文产品品牌。

## Core Responsibilities

- 生产代码与生产数据库
- 数据采集与来源适配
- 主体过滤与数据质量
- 舆情、事件、风险与分析
- KOS / Campaign 等生产能力
- 报告与数据导出
- API、Runtime、Health、Recovery
- 测试、证据与发布

## AI Boundary

AI 是生产能力增强层，不得绕过核心规则成为 Production Truth 的最终裁决者。重要 AI 结论必须能够追溯至证据，并记录必要的模型、提示词、输入、输出、置信度、最终结果及人工修正信息。

## Data Truth

```text
External Input
→ Ingestion
→ Raw / Evidence
→ Parse
→ Validate
→ Normalize
→ Function / Formula
→ Canonical Dataset / Table
→ Metric / Time Window
→ View Model
→ Visualization
→ UI / Report / Export
```

Business metrics are calculated once. Table is the numerical truth surface; charts, UI, reports and exports consume canonical outputs and must not independently recalculate business metrics.

## UI / Interaction

```text
Shell → Workspace → Product / Domain → Module → Page → Section → Component → Window / Action
```

Window and route state preserve parent context, target, child context and return context. Dynamic interaction and visualization follow the same hierarchy.

## File Governance

正式文件必须归属于明确模块。建议结构：

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

**Obsolete, conflicting, superseded or duplicated active rules/files MUST be removed after Reference / Dependency / Runtime verification, migration and regression tests.** Historical assets with audit/evidence value may remain only as explicitly marked `LEGACY` or `ARCHIVE` and must not participate in active implementation.

## Philosophy & Life-Level Research

```text
Life → Worldview → Philosophy → Brand → Methodology
→ Ecosystem → Architecture → Product → Experience
→ Feedback → Evolution ↺
```

`Living System`、`Living Intelligence`、`Embedded Wholeness`、`Relational Becoming` 属于研究语义/概念层，不自动构成当前生产功能或 Canonical 产品名称。

## Current Principle

- ZBP is the eventual parent; CTH is the child and current first implementation/validation environment.
- CTH capabilities are developed, stabilized and audited first; proven capabilities may later be absorbed into ZBP.
- Architecture may improve when evidence proves the replacement is better.
- No third core repository.
- No duplicate construction of proven core capabilities.
- Research does not directly write Production Truth.
- AI does not replace deterministic safety rules or human decision gates.
- No future concept is presented as an implemented production capability.
- Canonical naming changes follow governance gates.
- Every new research update carries forward the cumulative baseline.
- Obsolete/conflicting active rules and files are deleted after safe migration and regression verification.

**Status: Active · Production Truth · Governed by Canonical Naming, Cumulative Architecture Baseline & Twin Repository Synchronization**
