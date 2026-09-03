# 序境 · UI / UX 视觉与交互架构规范（Pure Design Architecture）

> 状态：CANONICAL BASELINE · 用户 2026-09-04 交付纯净版
> 定位：序境-Core / 序境-Intelligence 统一 UI/UX 设计基线；一切新页面、数据呈现、交互改造必须对齐本节；**数据呈现品质优先（先解决"丑数据"）**。
> 本节为产品/UI 设计基线，非开发讨论。修改须经产品 Owner 确认（Zero Sequence 保护）。

---

## 01. 核心目标

系统 UI 的核心不是装饰，而是：**让用户快速理解信息、判断状态、查看证据，并完成下一步操作。**

统一遵循：

```
信息 → 判断 → 证据 → 行动 → 反馈
```

## 02. 系统整体层级

```
序境
│
├── Intelligence
│   ├── Research / AI / Knowledge / Benchmark / Evaluation
│
├── Production
│   ├── Brand Intelligence：KOS / 舆情 / Campaign
│   └── Content Intelligence：Podcast
│
└── Operations
    ├── Runtime / Monitoring / Audit / Tasks / Deployment / System Health
```

## 03. 页面层级

统一采用：

```
Shell → Workspace → Domain → Module → Page → Section → Component → Detail / Action
```

禁止不同模块自行创造完全不同的层级体系。

## 04. Shell

全局固定层。包含：当前 Workspace、全局搜索、Runtime 状态、通知、用户状态、全局任务、全局 Command。**业务功能不直接堆入 Shell。**

```
┌─────────────────────────────────────────────┐
│ 序境   Workspace ▾   Search   Runtime ●   User │
└─────────────────────────────────────────────┘
```

## 05. Workspace

表示用户当前工作空间：Intelligence / Production / Operations。用户首先理解"我现在正在做什么"，再进入具体业务模块。

## 06–08. 三大 Workspace 结构

- **Intelligence**：Research / AI / Knowledge / Benchmark / Evaluation
- **Production**：Brand Intelligence（KOS / 舆情 / Campaign）+ Content Intelligence（Podcast）
- **Operations**：Runtime / Monitoring / Audit / Tasks / Deployment / System Health（不与业务模块混杂）

## 09. 页面统一结构

```
Context → Decision → Data / Trend → Evidence → Detail → Action
```

## 10. Dashboard

不做成卡片堆积。首屏只突出：当前状态 / 核心变化 / 核心判断 / 重要异常 / 下一步行动。

## 11. 数据可视化

图表必须回答具体问题，禁止为视觉效果无意义增加图表。

| 视图 | 主要作用 |
|---|---|
| Trend | 看变化 |
| Timeline | 看过程 |
| Runtime | 看时间结构 |
| Table | 看精确数据 |
| Graph | 看关系 |
| Distribution | 看结构 |
| Heatmap | 看集中程度 |
| Ranking | 看优先级 |

## 12. Table

表格是系统重要基础视图。统一支持 Sort / Filter / Search / Group / Compare / Drill-down / Export。同一数据可切换 Table ↔ Chart ↔ Timeline ↔ Graph ↔ Detail，数据对象保持一致。

## 13. Runtime

表达"事情发生在什么时候"，统一时间轴（Podcast / 采集任务 / AI 任务 / Campaign / 舆情事件 / Runtime 监控）。

## 14. Timeline

```
Signal → Event → Analysis → Risk → Decision → Action
```

可点击任意节点进入对应详情。

## 15. Evidence

统一证据层，任何重要判断可追溯：`判断 → Evidence → Source → Time → Original Data`。Evidence 优先 Drawer / Side Panel 展示，避免离开当前页面。

## 16. AI 结果

AI 不作为孤立聊天窗口。统一：Input → AI Analysis → Confidence → Reason → Evidence → Human Decision → Final Result。必须清晰区分：原始数据 / AI 判断 / AI 置信度 / 证据 / 人工判断 / 最终结果。

## 17. 交互原则

Select / Filter / Drill-down / Cross-highlight / Context Preserve / Drawer / Timeline Seek / Compare。

## 18. Detail 页面

Detail 不应该是新的孤立页面。统一：Object → Overview / Status / Data / Relationships / Evidence / History / Actions。

## 19. Podcast 专属结构

Overview + Intelligence（Research/Cases/Topics/People）+ Production（Episodes/Interview/Transcript/Assets）+ Performance（Runtime/Platforms/Breakout/Audience）+ Learning（Patterns/Validation/Knowledge）。

## 20. KOS 专属结构

Overview + Intelligence（People/Content/Topics/Research）+ Operations（Monitoring/Comments/Recommendations/Automation）+ Performance（Growth/Engagement/Conversion）+ Learning。

## 21. 舆情专属结构

Overview + Intelligence（Signals/Topics/Brands/Cases）+ Monitoring（Sources/Collection/Runtime）+ Analysis（Sentiment/Risk/Trend）+ Reports。

## 22. 统一视觉语言

克制 → 留白 → 层级 → 信息 → 重点。**而非**：颜色 → 卡片 → 渐变 → 动画 → 装饰。整体保持：高信息可读性、克制、清晰、低装饰、高层级感、数据优先、内容优先。

## 23. Typography

文字分级：System → Workspace → Page → Section → Primary Information → Secondary Information → Metadata。标题、数据、说明、状态不能混成同一种视觉重量。

## 24. Color

颜色主要承担：状态 / 风险 / 重点 / 反馈，不承担纯装饰。**任何状态不能只依赖颜色表达**，必须同时有图形、文本、状态符号、层级。

## 25. Motion

动效只用于 State / Cause / Continuity（状态变化、因果反馈、页面连续性）。禁止无意义动画。

## 26. 跨模块统一

KOS、舆情、Campaign、Podcast 共享：Shell / Workspace / Navigation / Typography / Spacing / Component / Table / Chart / Timeline / Drawer / Evidence / Status / AI Result / Action。不同模块只改变数据、业务逻辑、专属视图，不重新创造 UI 语言。

## 27. 数据关系

```
DATA → SIGNAL → CONTEXT → EVENT → ANALYSIS → RISK/IMPACT → EVIDENCE → DECISION → ACTION → FEEDBACK → LEARNING
```

## 28. 最终视觉关系

```
Context → Decision → (Data / Trend / Runtime) → Evidence → Detail → Action
```

## 29. 设计验收标准

| 检查项 | 要求 |
|---|---|
| 层级 | 是否清晰 |
| 信息 | 是否能快速理解 |
| 数据 | 是否有明确含义 |
| 图表 | 是否解决问题 |
| Evidence | 是否可追溯 |
| AI | 是否区分判断与事实 |
| Action | 是否明确下一步 |
| Context | 是否保持连续 |
| Interaction | 是否有反馈 |
| Visual | 是否统一 |
| Accessibility | 是否不依赖单一颜色 |
| Performance | 是否避免无意义动效 |

## 30. 最终总原则

**不是"把功能放进网页"，而是"把功能组织成任务 → 把任务组织成判断 → 把判断连接到证据 → 把证据连接到行动 → 把行动形成反馈 → 把反馈沉淀成学习"。**

序境不是 Dashboard 集合，而是一套以信息理解、证据验证、人机协作和决策行动为核心的统一交互系统。

---

## 落地优先级（本节执行依据）

1. **数据呈现品质**（先解决"丑数据"）：Table/Timeline/Evidence/Chart 统一、层级清晰、克制低装饰。
2. 页面结构统一（Context → Decision → Data → Evidence → Detail → Action）。
3. Evidence Drawer / Side Panel 统一。
4. AI 结果区分判断与事实。
5. 跨模块共享 Shell/Workspace/Component。
