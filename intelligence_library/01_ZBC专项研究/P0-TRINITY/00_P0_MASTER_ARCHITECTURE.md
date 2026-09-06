# Zachary OSAI P0｜AI + CTH-POMS + ZBMP 三位一体持续进化研究与反哺系统

> **状态：ACTIVE**｜确立日期：2026-09-02｜顶层研究工程，统领 OSAI 全部研究线

---

## 0. 定位

本工程是 Zachary OSAI 的 **P0 总研究工程**。

不是"研究完给一份报告"，而是建立一个**持续运行的产品进化闭环**：OSAI 从 AI 前沿、自家产品（CTH-POMS / ZBMP）、外部市场三条线持续吸收情报，经过综合研究判断，形成机会与缺口，再走 Product Decision → Architecture → Contract → Z Brand Core 施工 → Evidence → 再学习。

---

## 1. 三位一体总架构

```
                 Zachary OSAI
                       │
       ┌───────────────┼────────────────┐
       ↓               ↓                ↓
  AI Frontier     Product Intel     Market Intel
       │               │                │
       │          ┌────┴────┐           │
       │          ↓         ↓           │
       │        CTH-POMS   ZBMP         │
       │          │         │           │
       └──────────┴────┬────┴───────────┘
                       ↓
                综合研究 / 判断
                       ↓
              Opportunity / Gap
                       ↓
              Product Decision
                       ↓
                 Architecture
                       ↓
                  Contract
                       ↓
                Z Brand Core
                       ↓
             Code / Test / E2E
                       ↓
                    Evidence
                       ↓
                OSAI 再学习
                       ↺
```

---

## 2. 三条主研究线

### ① AI Frontier Research

研究最新：Agent、Long-running Agent、Memory、Experience Learning、Proactive AI、Browser / Computer Use、Coding Agent、Multi-Agent、AI Research Agent、Evaluation、Agent Safety、AI Operating System。

**目标回答**：Zachary OSAI 下一阶段应该进化成什么。

产出归位：`ai-os-research/`、`P0-resident-xhs-runtime/`

### ② Product Intelligence

**CTH-POMS**（广州太古汇垂直舆情/品牌传播情报系统）：
现在这个系统下一步应该怎么变得更强、更有客户价值。研究功能、用户、客户需求、报告、数据、交互、商业价值、行业趋势、竞品以及应该删掉什么。

**ZBMP**（母平台）：
母平台应该怎样承载可复用的品牌情报能力，同时不把 CTH 做成失去垂直优势的"大杂烩"。

重点回答：哪些能力应该平台化、哪些必须留在 CTH、哪些能力可以跨客户复用、哪些能力形成平台核心、哪些功能不应该进入 ZBMP。

### ③ Market / Competitive / Customer Intelligence

持续跟踪：市场、行业、竞品、客户、用户、技术、开源、论文、商业模式、产品趋势、监管变化。

**不是简单收集新闻**。OSAI 必须判断"这件事情跟 CTH、ZBMP、OSAI 到底有没有关系"，然后形成：

`IGNORE / MONITOR / RESEARCH / ADAPT / ADOPT / P0 / P1 / P2`

---

## 3. 最高规则：研究不能停在报告

研究成果必须尽可能经过完整链路：

```
Research → Evidence → Insight → Opportunity → Product Decision
→ Architecture → Contract → Z Brand Core → Implementation → Test
→ Evidence → Learning
```

这样 OSAI 才真正成为研发大脑，Z Brand Core 才真正成为生产施工现场。

---

## 4. 边界（保持双子星基线）

- OSAI：学习、研究、判断、形成 Contract
- Z Brand Core：开发、测试、执行、验证
- 不恢复四库架构
- 不建立第三核心库
- 不写生产代码、不保存任何 Cookie/Token/Session 到仓库
- 研究结论不能自动变成生产规则

---

## 5. 最终大问题

本工程最终必须回答：

> **三年以后，CTH-POMS、ZBMP 和 Zachary OSAI 分别应该是什么，以及三者为什么必须存在？**

这个问题一旦研究透，后面的产品路线、代码架构和功能优先级都会清楚很多。

---

## 6. 产出目录

| 目录 | 内容 | 状态 |
|---|---|---|
| `P0-TRINITY/` | 顶层架构、P0 状态、三位一体工程主文档 | ACTIVE |
| `P0-resident-xhs-runtime/` | 小红书 Resident AI Browser Runtime 研究（AI Frontier 线） | ACTIVE |
| `ai-os-research/` | AI 前沿能力雷达 / AI Operating System 研究 | 研究中 |
| `osai-ui/` | OSAI UI 交互体系 | 构建中 |
