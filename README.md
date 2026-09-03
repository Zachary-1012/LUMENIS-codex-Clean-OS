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

不得因为品牌候选出现而进行未经依赖分析的全局替换。旧名称如因 Git 历史、不可变标识、兼容性或审计需要保留，必须明确标记为 `LEGACY`。

## Product / System Naming Standard

生产产品的中文 Canonical 名称为 **序境**，韩文标准表达为 **서경**，英文 Canonical Brand 暂为 **TBD**。

不要使用 `Core` 作为中文正式产品名称。`Z-Brand-Core` 仅为现有 GitHub Repository identifier，不等同于中文产品品牌。

涉及产品、子系统、模块、页面、功能、数据、API、Runtime、文件、类和函数的命名，应映射到 Canonical Registry；技术标识与品牌名称必须分层管理。

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

## Philosophy & Life-Level Research

```text
Life → Worldview → Philosophy → Brand → Methodology
→ Ecosystem → Architecture → Product → Experience
→ Feedback → Evolution ↺
```

`Living System`、`Living Intelligence`、`Embedded Wholeness`、`Relational Becoming` 属于研究语义/概念层，不自动构成当前生产功能或 Canonical 产品名称。

## Data & Reporting

```text
Source → Collection → Raw → Normalize → Analyze → Evidence → Insight → Report
```

标准报告骨架：

```text
Executive Summary
→ Key Findings
→ Event / Issue
→ Impact
→ Risk
→ Evidence
→ Trend
→ Recommendation
→ Appendix / Data
```

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

删除或迁移前必须完成 Reference / Dependency / Runtime 验证。历史资产若具有证据或审计价值，应归档而不是直接删除。

## Current Principle

- 架构保持稳定
- 不建立第三核心库
- 不重复建设已有 Core 能力
- Research 不直接写入 Production Truth
- AI 不替代确定性安全规则
- 不把未来生命层构想写成当前已实现能力
- 不因英文品牌研究提前修改仓库或生产架构
- 所有 Canonical 命名变更遵循治理 Gate

**Status: Active · Production Truth · Governed by Canonical Naming & Twin Repository Synchronization**
