# Platform × Intelligence｜ZBC × OSAI × Local Source

**日期：2026-09-05**  
**性质：今日研发讨论整合 / 任务收口基线**  
**阶段：源码事实审计准备阶段**

## 1. 核心定位

当前主体仍然是**平台产品**，不是纯 AI 产品。

AI/Intelligence 是平台当前需要拉回来的核心智能与生产能力，用于加速研发、生产、研究与协作；未来 AI 仍应保留独立产品化、独立生产、独立研发和独立部署的出口。

因此当前策略是：**先整合能力，不永久耦合产品身份。**

```text
PLATFORM
├── Platform Core
├── Domain / Business
├── Data / Case / Workspace
├── User / Permission / Runtime
└── Integration Contract
        ↕
INTELLIGENCE
├── AI
├── Agent
├── Research
└── Evaluation
```

## 2. 本轮必须回答的三个问题

### Q1｜研发资产成熟度
过去一段时间实际沉淀了多少有价值、可复用、可产品化的资产？

检查范围：代码、数据库、案例库、语料库、规则、Prompt、AI 资产、Agent、Research、UI/UX、Design Token、Contract、测试、部署、配置、文档、历史能力。

每项至少判断：存在性、完整度、可运行性、可复用性、产品化程度、归属。

### Q2｜平台底座成熟度
ZBC + OSAI + Local Source 能否形成稳定、可上线的平台底座？

不是粗暴合仓，而是判断哪些直接可用、可复用、需改造、冲突、重复、缺失。

### Q3｜多人 + AI 协作成熟度
平台目前距离“多人在平台内部工作，同时 AI 作为生产角色参与”还有多远？

重点检查 User / Team / Role / Permission、Workspace / Project / Task、Assignee / Reviewer、Activity Log、Version、Concurrency、State Sync、Context、Artifact、Evidence、AI Session、Review / Approval / Lifecycle。

## 3. 三方事实来源

1. `Z-Brand-Core`
2. `Zachary-OS-AI`
3. Local Source Package（待提取完成）

Local Source 特别用于发现 GitHub 未包含的本地独有代码、数据库、案例库、语料库、历史数据、AI 分析记录、Prompt、配置、脚本、测试及其他研发资产。

**关联目录 ≠ 仓库合并 ≠ 代码合并。**

## 4. 能力归属模型

每项能力审计后增加归属标签：

- `PLATFORM`：平台核心
- `AI`：未来可独立出去的智能能力
- `SHARED`：平台与 AI 共同需要，通过 Contract 共享
- `BRIDGE`：平台与 AI 的连接层
- `LEGACY`：历史遗留，待判断

## 5. 源码事实审计链

```text
File
→ Module
→ Function
→ Contract
→ Requirement
→ Test
→ Commit
→ Lifecycle
```

最终形成 `Source Fact Baseline`，不以 README 或旧聊天记忆替代源码事实。

源码状态统一使用：

`EXIST / USED / PARTIAL / DOCUMENTED_ONLY / DEAD / ORPHANED / BROKEN / DUPLICATED / UNKNOWN`

遗留能力先分类，不直接删除：

`KEEP / MERGE / REFACTOR / DEPRECATE / DELETE / UNKNOWN`

## 6. Lifecycle

```text
DISCOVER
→ REQUIREMENT
→ RESEARCH
→ EVIDENCE
→ DECISION
→ ARCHITECTURE
→ IMPLEMENT
→ TEST
→ VERIFY
→ RELEASE
→ OPERATE
→ MONITOR
→ LEARN
→ IMPROVE
→ RETIRE
```

每项功能最终应可回查 Lifecycle。

## 7. Agent 治理

当前 13 人团队执行宪章已形成，角色包括：

1. `coding-analyze-codebase`
2. `coding-design-solution`
3. `coding-develop-backend-features`
4. `coding-develop-frontend-features`
5. `coding-develop-unit-tests`
6. `coding-diagnose-and-fix-bugs`
7. `coding-optimize-performance`
8. `data-analysis`
9. `app-builder`
10. `creative-design`
11. `lark-wiki`
12. `github-remote`
13. `coding-review-code`

统一原则：Agent 是受控执行角色，不能凌驾于产品 Lifecycle 和人工决策之上。

标准链路：

```text
ANALYZE
→ DESIGN
→ DEVELOP
→ TEST
→ DIAGNOSE
→ OPTIMIZE
→ REVIEW
→ DATA / CREATIVE / APP（按需）
→ KNOWLEDGE
→ VERSION CONTROL
```

任何未来变更应尽可能满足：

`READ → AUDIT → ANALYZE → PLAN → PATCH PREVIEW → TEST → VERIFY → HUMAN APPROVAL → COMMIT → PUSH`

## 8. UI / UX 当前基线

- 先结构后视觉、先 IA 后组件、先 Contract 后代码
- 20 条母规则为验收红线
- 防覆盖 Contract：z-index / overflow / min-max height / Layer / Container / Viewport / State Sync / Realtime Update
- 真数据变化才产生动效；禁止假数据、假状态、写死循环、双真相
- 正式 Icon 禁用 emoji
- 每次交付必须经过 Visual QA + Functional QA
- Design-ID → Page-ID → Component-ID → File → Test → Commit → Lifecycle-ID 可追溯
- ZBC / OSAI 形态融合、物理不合并，共享 Token 与组件，但不共享产品 IA
- 不静默删除能力；旧 UI/能力必须经过审计→映射→迁移→验证→显式退役

### 当前 Design DNA

`Complexity → Simplicity / AI First / Information First / Function First / Real-time / Minimal / Professional / Spatial Layer / Light Motion / No Infinite Scroll / No Permanent Right Context / No Cute UI / No Visual Overload / One Design Language`

### Token / 视觉方向

- ZBIP Apple 色系为骨
- 融入 XUJING 微光银作为品牌签名
- 状态色统一 Apple 系
- 圆角方向：`8 / 12 / 16 / 20 / 9999`
- 字体方向：`SF Pro + PingFang SC`，400 / 600 / 700
- Liquid Glass 仅用于导航悬浮等空间层，不做全屏玻璃化
- 禁 glass-on-glass；目标对比度 ≥ 4.5:1；尊重 reduce-transparency / reduce-motion
- Light 优先，Dark 同步定义、后续实现
- 移动端采用响应式 Web 适配

最终实际 Token 仍以源码中最终 Design Token 文件核验为准。

## 9. 产品 IA 方向

页面层级：

`L0 Product → L1 Module → L2 Function → L3 Workspace / Detail → L4 Drawer / Modal`

首页采用左导航 + 中央工作区，不做永久右侧 Context、不做无限滚动、不把所有功能堆在首页。

Case Library 作为统一信息资产入口，但**统一入口不等于强制合并底层数据表**。

## 10. 当前阶段边界

在 Local Source 三方事实基线完成前：

- 不重写 Core
- 不重写业务逻辑
- 不重新建设完整 UI
- 不删除未知遗留能力
- 不因发现问题就立即重构
- 不用旧聊天记忆替代当前源码事实

当前主要工作：源码审计、事实确认、能力盘点、重复检查、Contract 分析、Test 分析、Lifecycle 回查、Agent 责任分析。

## 11. 当前本地项目协作状态

豆包当前项目为 `序境1.0`，已关联：

```text
序境1.0
├── Taikoo-monitor-new   ← 主要工作目录
└── Zachary OS AI
```

其意义是让 Agent 在同一项目上下文中横向读取两个目录；这不等于代码已经合并。

Local Source Package 完成后，再作为第三份事实来源纳入审计。

## 12. 当前 P0 / P1 任务

### P0

- Local Source Package 完整提取
- 三方源码事实审计
- 本地数据库 / 案例库 / 语料库资产盘点
- AI / Agent / Research 资产盘点
- Platform / AI / Shared / Bridge / Legacy 归属判断
- Capability Matrix
- Duplication Matrix
- Dependency Matrix
- Contract Matrix
- Lifecycle Matrix
- Test / Verification 状态
- 当前真实可运行能力确认

### P1

- 平台底座成熟度评估
- AI 能力成熟度评估
- 数据 / 案例 / 语料资产价值评估
- Agent 体系成熟度评估
- 多人协作成熟度评估
- AI 协作成熟度评估
- Realtime / State Sync
- 权限体系
- Workspace / Task / Artifact / Evidence 链
- AI 未来独立拆分可行性

## 13. 最终目标模型

```text
PRODUCT
→ PRODUCT PHILOSOPHY
→ DESIGN LANGUAGE
→ INFORMATION ARCH
→ MODULE
→ FUNCTION
→ CONTRACT
→ REQUIREMENT
→ CODE
→ TEST
→ VERIFICATION
→ COMMIT
→ LIFECYCLE
→ LEARNING
→ IMPROVEMENT
```

Agent 处于受控位置；Human 负责关键判断、批准与最终验收。

## 14. 本轮收口结论

当前不是重新做一个 AI，也不是把 ZBC / OSAI 粗暴揉成一个 Core。

本轮目标是把过去研发产生的平台、AI、数据、案例、语料、Agent、Research、UI/UX、Contract 和工程资产全部重新找回来，以 ZBC、OSAI、Local Source 三方实际材料为事实依据，确认：

**什么真正存在、什么真正可用、什么属于平台、什么属于 AI、什么应该共享、什么只是历史遗留，以及当前底座能否支撑平台内部多人 + AI 协作，同时为未来 AI 独立出去保留架构出口。**

> 本文件是今日讨论的研发任务收口记录，不替代后续三方源码事实审计结果。后续事实以实际源码、数据、文件、测试和最新 Git 状态为准。
