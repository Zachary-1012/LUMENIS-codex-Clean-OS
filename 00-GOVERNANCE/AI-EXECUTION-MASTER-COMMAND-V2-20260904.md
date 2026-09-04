# 双库 AI 开工执行口令 V2

> 状态：ACTIVE（开工口令）
> 生效：2026-09-04
> 适用范围：ZBC × OSAI 双库 AI 执行开工流程
> 权威关系：本口令为"开工执行流程"，唯一通用 AI 执行入口见 `CANONICAL-EXECUTION-V3-20260904.md`（V3）

---

你现在开始执行任务。

第一原则：

不要自行创造新的最高优先级规则。

先读取并遵守：

00-GOVERNANCE/AI-EXECUTION-MASTER-COMMAND-V2-20260904.md

然后读取当前仓库的：

1. Governance Authority Map
2. Canonical AI Execution Baseline
3. README
4. AGENTS / Repo Instructions
5. 当前任务相关 Domain Contract
6. 当前功能已有源码
7. 历史 Decision / Research / Evidence
8. 当前测试与 Runtime 状态

---

## 一、先审计，不准直接写代码

先回答：

- 当前基线是什么？
- 这个需求以前是否做过？
- 已有代码在哪里？
- 已有组件能否复用？
- 是否存在旧实现？
- 哪些规则已经失效？
- 哪些规则仍然有效？
- 有没有冲突？
- 修改边界是什么？
- 会影响哪些现有能力？

没有完成以上审计，不进入实现。

---

## 二、先建立任务生命周期

为本任务建立：

- Research-ID
- Decision-ID
- Requirement-ID
- Task-ID

并建立：

`Requirement → Contract → Implementation → Test → Evidence → Commit`

---

## 三、不得把自然语言直接翻译成代码

必须先把需求转换成：

- Product Intent
- User Goal
- Information Hierarchy
- UX Behavior
- Visual Intent
- Data Requirement
- Runtime Requirement
- Render Requirement
- Interaction
- Lifecycle
- Dependencies
- Change Boundary
- Acceptance Criteria

任何"高级、简约、通透、克制、好用、动态、自然"等设计语言，都必须转换成具体：

- Token
- Layout Rule
- Component Rule
- Interaction Rule
- Motion Rule
- Rendering Rule

不得自行猜测。

---

## 四、UI / UX 执行标准

默认：

```text
LEFT NAVIGATION
        +
CENTRAL WORKSPACE
```

默认不使用永久右侧 Context。

网页默认：

```text
FIXED VIEWPORT
```

禁止无限向下滚动。

信息超过当前层级时：

- Child Page
- Focused Workspace
- Sheet
- Dialog
- Popover
- Bounded Local Scroll

选择最合理的一种。不得为了塞内容而拥挤页面。

---

## 五、首页

首页不是功能仓库。

首页只展示：

- What matters now
- What changed
- What needs attention
- What AI is doing
- What should I do next

卡片数量不设固定目标。有价值才显示。

次级信息进入功能页。深层数据进入下一层。

不要为了视觉丰富强行增加卡片。

---

## 六、视觉

必须：

- Minimal
- Functional
- Clear
- Precise
- Information-first

禁止：

- 可爱化
- 大面积装饰
- 过度玻璃
- 无意义动效
- 无意义特效
- 大组件堆叠

Glass 只用于：

- Navigation
- Control
- Focus
- State
- Layer
- Interaction

Motion 必须解释状态、关系、导航或反馈。

---

## 七、Rendering

任何区域必须明确：

- State Owner
- Data Owner
- Layout Owner
- Renderer Owner
- DOM Owner
- Event Owner

一个 UI 区域只能存在一个 Render Authority。

禁止多个 Renderer 同时修改同一 DOM。

发现覆盖、显示不全、闪烁、错位：不得只改 CSS。必须追：

- Viewport
- Sizing
- Overflow
- Visibility
- Opacity
- Position
- Transform
- Stacking Context
- Mount
- Unmount
- Async Render
- State
- Ownership
- Duplicate Render

然后：

`ROOT CAUSE → EVIDENCE → PATCH → TEST → REGRESSION`

---

## 八、数据

UI 不得自行制造业务真相。

必须：

`Source → Validate → Normalize → Canonical Data → Domain Function → Metric → View Model → UI`

不得使用静态 Mock 冒充实时数据。

---

## 九、实时更新

任何进入 GitHub 的 Code / Data / Research / Model / Capability / Configuration，都不能直接宣称已经生效。

必须追：

`REGISTERED → SYNCED → LOADED → READY → RUNNING → UPDATED → VERIFIED`

状态不完整就明确报告实际状态。

---

## 十、研究

需要研究时：

`Research → Evidence → Finding → Relevance → Decision → Adaptation → Implementation → Verification`

Apple、开源项目、AI/ML、Rendering、UX、Motion、Accessibility 等只用于：

- ADOPT
- ADAPT
- DEFER
- REJECT

必须说明为什么。不得直接复制。

---

## 十一、修改边界

实施前先列：

- Allowed Files
- Allowed Components
- Allowed Routes
- Allowed State
- Allowed Runtime
- Forbidden Areas

跨边界必须先做影响分析。不得为了一个局部功能修改整个系统。

---

## 十二、生命周期回查

完成实现以后，必须从头反查：

`Requirement → Contract → Code → Function → Runtime → State → View Model → Renderer → UI → Interaction → Evidence`

然后反向：

`User Action → Event → State Mutation → Runtime → View Model → Renderer → UI Update`

两条链必须闭合。

---

## 十三、回归测试

任何修改必须检查：

- Current Feature
- Current Page
- Current Component
- Global Shell
- Navigation
- Runtime
- Data
- Dependent Features

禁止：修 A → 破坏 B → 宣布 A 完成。

---

## 十四、完成条件

以下全部通过才允许：

Requirement ✓ Product ✓ Design ✓ UX ✓ Data ✓ Runtime ✓ Renderer ✓ Interaction ✓ Visual ✓ Accuracy ✓ Regression ✓ Lifecycle ✓ Evidence ✓

否则只能：

- PASS
- FAIL
- PARTIAL
- BLOCKED

不得使用 DONE / COMPLETE / READY / DELIVERED 来掩盖未验证状态。

---

## 十五、规则治理

如果发现旧规则：重复 / 冲突 / 失效 / 过期 / 无实际执行价值，不要继续叠加新规则。

先判断：

- ACTIVE
- DOMAIN
- RECORD
- SUPERSEDED

真正重复的删除或标记替代。真正有价值的领域规则保留。历史证据不得删除。

---

## 十六、最终报告

每次重要任务完成必须报告：

OBJECTIVE / BASELINE / RESEARCH / DECISION / REQUIREMENTS / FILES / FUNCTIONS / RUNTIME / DATA / UI / UX / TEST / VISUAL VERIFICATION / REGRESSION / LIFECYCLE TRACE / EVIDENCE / COMMIT / REQUIREMENT COVERAGE / REMAINING / RISKS / STATUS

最后明确：PASS / FAIL / PARTIAL / BLOCKED

---

## 最重要的一句话

不要通过增加规则来解决规则混乱。

真正目标是：

```text
ONE AUTHORITY
+ FEW CLEAR CONTRACTS
+ EXPLICIT OWNERSHIP
+ BOUNDED CHANGES
+ CANONICAL DATA
+ DETERMINISTIC RENDER
+ LIFECYCLE TRACE
+ MACHINE VERIFICATION
```

如果发现任何未知项：UNKNOWN
如果发现任何冲突：CONFLICT
如果发现任何无法验证的完成状态：UNVERIFIED

不要猜。不要跳步。不要自行解释成"差不多"。

---

## Status

- 本文件为开工执行口令（V2）。
- 唯一通用 AI 执行入口：`CANONICAL-EXECUTION-V3-20260904.md`（V3）。
- 冲突时：V3 > Domain Contract > Task Requirement > Historical Record；Safety/Legal/Security 更高层约束始终优先。
- Status: ACTIVE
