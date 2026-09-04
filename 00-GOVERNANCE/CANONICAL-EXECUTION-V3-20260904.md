# 双库 AI 统一执行总指令 V3

> 状态：ACTIVE · 当前唯一 AI 通用执行入口
> 生效：2026-09-04
> 适用范围：ZBC × OSAI · Canonical Execution / Lifecycle / UI / UX / Data / Runtime
> 适用范围对象：ZBC / OSAI / Web / App / UI / UX / Runtime / Data / AI / Research / Lifecycle / Testing / CI/CD / Bug Fix / Refactor / Feature Development / Deployment

---

## 0. 唯一权威原则

从本版本开始：不要再建立新的"最高优先级执行规则"。

所有 AI 执行统一从 **CANONICAL EXECUTION V3** 开始。

其他文件只能属于：ACTIVE / DOMAIN / RECORD / SUPERSEDED

- ACTIVE → 当前通用规则
- DOMAIN → 特定领域规则
- RECORD → 历史记录 / 证据
- SUPERSEDED → 历史规则，不参与当前执行

如果两个规则冲突：

`V3 > Domain Contract > Task Requirement > Historical Record`

但 Safety / Legal / Security 等更高层约束始终优先。

---

## 1. 第一动作：读取，不得直接开发

任何任务开始：

`READ → AUDIT → TRACE → UNDERSTAND → PLAN → IMPLEMENT`

不得：收到需求 → 直接写代码

---

## 2. 必须先检查的内容

按顺序检查：

01 Canonical Execution V3
02 Governance Authority Map
03 README
04 AGENTS / Repository Instructions
05 Relevant Domain Contracts
06 Existing Architecture
07 Existing Code
08 Existing UI / UX
09 Existing Runtime
10 Existing Data
11 Existing Tests
12 Previous Research
13 Previous Decisions
14 Previous Evidence
15 Git History

---

## 3. 历史规则处理

发现旧规则时不得直接删除。必须判断：

- 是否仍有效？
- 是否重复？
- 是否冲突？
- 是否已经被替代？
- 是否仍被代码引用？
- 是否仍被 README / AGENTS 引用？
- 是否具有历史证据价值？

然后归类：ACTIVE / DOMAIN / RECORD / SUPERSEDED

只有真正没有价值且没有依赖的内容才能删除。

---

## 4. 需求生命周期

所有需求必须拥有 Requirement-ID。

完整生命周期：

```text
DISCOVERED → RESEARCHED → DECIDED → SPECIFIED → IMPLEMENTED → LOADED → RUNNING → TESTED → VERIFIED → DELIVERED → MONITORED → IMPROVED
```

---

## 5. 执行生命周期

需求生命周期与系统执行生命周期分开。

执行状态：

```text
REGISTERED → SYNCED → LOADED → READY → RUNNING → UPDATED → VERIFIED
```

不得混成一个字段。至少保持：`lifecycle_stage` / `execution_status` / `verification_status`

---

## 6. 每次任务必须建立追溯链

```text
Research-ID → Decision-ID → Requirement-ID → Task-ID → File → Function → Component → Runtime → Test → Evidence → Commit-SHA
```

任何一环不存在必须明确：UNKNOWN。不得猜测。

---

## 7. 需求必须先转 Contract

自然语言不能直接进入代码。必须转换为：

- Product Intent
- User Goal
- Information Hierarchy
- UX Behavior
- Visual Intent
- Data Requirement
- Runtime Requirement
- Render Requirement
- Interaction
- Dependencies
- Change Boundary
- Acceptance Criteria

---

## 8. 设计语言必须工程化

任何"简约 / 高级 / 通透 / 克制 / 自然 / 有呼吸感 / 层叠 / 动态 / 苹果感"都必须转换为可执行定义：

- Design Token
- Layout Rule
- Component Rule
- Interaction Rule
- Motion Rule
- Rendering Rule
- Accessibility Rule

禁止 AI 自由发挥。

---

## 9. Web / App 总布局

默认：

```text
LEFT NAVIGATION
        +
CENTRAL WORKSPACE
```

不设置永久右侧 Context，除非具体功能有明确必要。

---

## 10. 页面信息层级

统一：

```text
CORE → PRIMARY → SECONDARY → DETAIL → DEEP DETAIL
```

首页只显示：当前最重要 / 当前变化 / 需要注意 / AI 当前状态 / 下一步动作

次级内容进入功能页。深层信息通过：Child Page / Sheet / Dialog / Popover / Focused Workspace / Bounded Local Scroll 解决。

---

## 11. 禁止无限页面滚动

页面默认 Fixed Viewport。禁止无限纵向页面 / 不断增加页面高度 / 通过堆内容解决信息架构问题。

允许数据表、日志等使用 Bounded Local Scroll，并必须定义：Scroll Owner / Scroll Boundary。

---

## 12. 首页卡片

不设置固定卡片数量。原则：

- 有价值 → 显示
- 高频 → 显示
- 核心 → 显示
- 次级 → 可展开
- 低频 → 功能页
- 无价值 → 删除

不为了视觉丰富强行增加卡片。

---

## 13. 视觉原则

统一：

`Information > Function > Hierarchy > Interaction > Feedback > Motion > Decoration`

禁止：过度可爱化 / 过度装饰 / 大面积玻璃 / 无意义动画 / 无意义特效 / 巨大组件 / 信息拥挤

---

## 14. Glass

Glass 只能作为：Navigation / Control / Focus / State / Layer / Interaction

禁止：Glass everywhere / Glass-on-Glass / 用玻璃遮盖层级问题

---

## 15. Motion

动效必须表达：Navigation / State Change / Focus / Feedback / Relationship

如果无法解释动效为什么存在：REMOVE

---

## 16. Renderer Ownership

每个 UI 区域必须明确：State Owner / Data Owner / View Model Owner / Renderer Owner / DOM Owner / Event Owner

一个区域只能存在一个 Renderer Authority。

禁止：Renderer A + Renderer B → 同时修改同一 DOM

---

## 17. UI 覆盖 Bug

遇到覆盖 / 错位 / 闪烁 / 显示不全 / 元素消失 / 重复渲染，禁止直接使用 `z-index: 9999 !important` / `overflow hidden` / `absolute` 作为最终解决方案。

必须追：

```text
Viewport → Sizing → Layout → Overflow → Visibility → Position → Transform → Stacking Context → Mount → Unmount → Async Render → State → Ownership → Duplicate Render
```

然后：`ROOT CAUSE → EVIDENCE → PATCH → TEST → REGRESSION`

---

## 18. 数据唯一真相

数据链：

```text
SOURCE → VALIDATE → NORMALIZE → CANONICAL DATA → DOMAIN FUNCTION → METRIC → VIEW MODEL → RENDER → UI
```

- UI 不得制造业务真相。
- 不得不同页面重复计算同一个核心指标。
- 不得用 Mock 冒充真实数据。

---

## 19. 实时更新

任何 Code / Data / Research / Model / Configuration / Capability 进入仓库后，不代表已经运行。

必须：

```text
REGISTERED → SYNCED → LOADED → READY → RUNNING → UPDATED → VERIFIED
```

如果只同步但没有加载：`SYNCED / NOT LOADED`，不得显示 LIVE / READY。

---

## 20. Runtime

至少追踪：

```text
created_at / updated_at / loaded_at / started_at / last_success_at / last_error_at
execution_status / sync_status / verification_status
```

---

## 21. Lifecycle Center

Lifecycle 必须最终成为真实系统能力，而不是单纯 Markdown。

入口：`LEFT NAVIGATION → LIFECYCLE → LIFECYCLE CENTER`

页面结构：Overview / Requirements / Research / Decisions / Tasks / Runtime / Evidence / History；右侧展示 Current Lifecycle（DISCOVERED → RESEARCHED → IMPLEMENTED → VERIFIED）。

第一阶段必须独立开发。不得直接重构整个首页。

---

## 22. Lifecycle Detail

每个对象必须能够查看：Requirement / Research / Decision / Implementation / Runtime / UI / UX / Tests / Evidence / Commit History / Next Action

---

## 23. 双向 Trace

必须支持：

```text
Requirement → Code → Function → Runtime → UI → Test → Evidence → Commit
```

同时：

```text
Commit → File → Function → Requirement
```

无法关联：TRACE INCOMPLETE

---

## 24. Lifecycle History

禁止覆盖历史状态。必须记录：Previous State / New State / Timestamp / Actor / Reason / Evidence

---

## 25. Research

Research 必须进入生命周期：

```text
Research → Evidence → Finding → Relevance → Decision → Adaptation → Implementation → Verification
```

外部研究只允许：ADOPT / ADAPT / DEFER / REJECT。不得直接复制外部代码或产品。

---

## 26. Change Boundary

每次修改之前必须声明：

- Allowed Files
- Allowed Components
- Allowed Routes
- Allowed State
- Allowed Runtime
- Forbidden Areas

跨边界修改必须：`IMPACT ANALYSIS → DECISION → IMPLEMENT`

---

## 27. Regression

修改任何内容都必须检查：Feature / Page / Component / Global Shell / Navigation / Runtime / Data / Dependent Features

---

## 28. 测试

测试必须覆盖：Function / UI / UX / Data / Runtime / Lifecycle / Renderer / Regression

重要问题至少验证：Empty State / Invalid Data / Async State / Loading / Error / Success / Resize Viewport / Duplicate Render / State Transition

---

## 29. 完成状态

严格区分：

- IMPLEMENTED：代码已经存在
- TESTED：测试已经运行
- VERIFIED：测试与证据通过
- DELIVERED：符合交付标准

不得混用。

---

## 30. 禁止假完成

- 代码完成但未测试：IMPLEMENTED / UNVERIFIED
- 测试失败：FAIL
- 依赖缺失：BLOCKED

禁止用 DONE / COMPLETE / READY / DELIVERED 掩盖事实。

---

## 31. Requirement Coverage

每次任务结束：

```text
REQ-001 ✓
REQ-002 ✓
REQ-003 ✗
REQ-004 UNKNOWN
```

任何 ✗ / UNKNOWN / BLOCKED 都不得宣布整体完成。

---

## 32. 规则治理

发现规则重复：MERGE
发现冲突：REASSESS
发现过期：SUPERSEDE
发现历史价值：RECORD
发现无价值且无依赖：DELETE

禁止继续堆规则解决规则混乱。

---

## 33. 双库职责

- OSAI：Research / Evidence / Evaluation / Intelligence / Specification
- ZBC：Production Truth / Runtime / Canonical Data / Implementation / Release

标准链：

```text
OSAI → Research → Evidence → Decision → Contract → ZBC → Implementation → Runtime → Production
```

---

## 34. Commit 前强制回查

Commit 前：

```text
Requirement → Contract → Code → Function → Runtime → View Model → Renderer → UI → Interaction → Test → Evidence
```

反向：

```text
Commit → File → Function → Requirement
```

两条链必须检查。

---

## 35. Commit 后

Push 后必须重新读取远程状态：

```text
Remote Commit → File Exists → Content Exists → Branch Correct → Commit SHA Correct
```

不能只说"已经 Push"，必须有证据。

---

## 36. 最终报告

每次重要任务：

OBJECTIVE / BASELINE / RESEARCH / DECISION / REQUIREMENTS / FILES / FUNCTIONS / UI / UX / DATA / RUNTIME / TEST / REGRESSION / LIFECYCLE TRACEABILITY / EVIDENCE / COMMIT / REMOTE VERIFY / REQUIREMENT COVERAGE / REMAINING / RISKS / STATUS

---

## 37. 最终状态机

统一：

```text
DISCOVERED → RESEARCHED → DECIDED → SPECIFIED → IMPLEMENTED → LOADED → RUNNING → TESTED → VERIFIED → DELIVERED → MONITORED → IMPROVED → (loop)
```

任何阶段都必须可追溯。

---

## 38. 最终工程原则

不要追求：更多规则 / 更多命令 / 更多文档 / 更多 UI / 更多卡片 / 更多效果

而追求：

```text
ONE AUTHORITY
+ CLEAR CONTRACTS
+ EXPLICIT OWNERSHIP
+ CANONICAL DATA
+ DETERMINISTIC RENDERING
+ REAL-TIME STATE
+ LIFECYCLE TRACE
+ MACHINE VERIFICATION
+ AUDITABLE EVIDENCE
```

---

## 39. 开始执行

收到任何新任务：

```text
READ → AUDIT → TRACE → RESEARCH → DECIDE → SPECIFY → IMPLEMENT → TEST → VERIFY → REGRESSION → LIFECYCLE TRACE → EVIDENCE → COMMIT → REMOTE VERIFY → REPORT
```

不得跳步。不得自行增加平行最高规则。不得删除历史证据。不得用猜测代替事实。不得把代码存在当成完成。不得把 GitHub 已同步当成 Runtime 已执行。不得把 UI 显示出来当成 UI 正确。

如果无法证明：NOT VERIFIED

---

## Status

- Status: ACTIVE（当前唯一 AI 通用执行入口）
- 前置开工口令：`AI-EXECUTION-MASTER-COMMAND-V2-20260904.md`（V2）
- 权威顺序：V3 > Domain Contract > Task Requirement > Historical Record
- Safety / Legal / Security 更高层约束始终优先
