# <SCREEN-ID> — <Screen name>

```yaml
screen_id: <SCREEN-ID>
status: DESIGN_EXPLORATION
revision: 1
owner_domain: UNKNOWN
binding_ids: []
product_owner_approval: PENDING
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: PENDING
reviewer: UNKNOWN
reviewed_at: UNKNOWN
approval_reference: UNKNOWN
```

Latest PO direct-build rule: reuse current screen records and implement from real contracts without a separate design draft/Figma or M DESIGN_READY prerequisite. Design review fields above record facts, not a coding gate. Website/Web first; native Windows/macOS and iOS later. Unknown business/auth contracts still block dependent actions; acceptance requires actual operation.

## 0. Authority basis and artifact disposition

- Constitution sections applied:
- Product/workflow contract applied:
- Audit PDF/taskbook/sketch/screenshot/Figma references (non-authoritative):
- For each reference: `KEEP_AS_EXPLORATION` / `REJECT` / `RESTATED_IN_THIS_SPEC`:
- Anti-template check: explain why this is not a generic dashboard/card grid/shared renderer:
- M review decision under the current manually selected model: `DESIGN_EXPLORATION` / `DESIGN_READY` / `BLOCKED`:

## 1. User problem and product invariant

- Role and authorized context:
- User's real task and completion signal:
- Owning domain and invariant (CTH Subject-first / BMP Brand-Market-first / Shared origin lineage / SYSTEM infrastructure-only):
- Explicitly out of scope:

## 2. Route, entry, exit and return

- Entry routes and required context:
- Authorization-dependent destination behavior:
- Exit and deep-link paths:
- Trace target and source position to restore:
- Return state (selected Subject/Brand, filters, tab, selection, scroll, zoom, route):

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source/ViewModel field or callable | Definition / units / window | Freshness and missing-data behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | |

List exact route/method, request and response fields, pagination/cancellation behavior, idempotency and implementation file. Mark unresolved items `UNKNOWN`; do not invent a route or metric.

## 4. State and recovery matrix

| State | Trigger/evidence | User-visible meaning | Available actions | Recovery/return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | | | | | |
| Empty / no source data | | | | | |
| Not collected | | | | | |
| Fresh | | | | | |
| Stale | | | | | |
| Partial | | | | | |
| Offline | | | | | |
| Blocked / permission denied | | | | | |
| Error | | | | | |
| Success / persisted | | | | | |

## 5. Purpose-built desktop composition

- Primary question and visual hierarchy:
- Layout regions and information relationships:
- Primary interaction and precise result:
- Secondary interactions and keyboard operation:
- Density/resize behavior and comparison needs:
- What makes this composition specific to this screen:

## 5A. Web Workspace composition and desktop-only capability boundary

- Browser-first task, URL/deep-link and keyboard/pointer behavior:
- Shared Product Core/ViewModel/state semantics:
- Desktop-only capabilities and honest state (`DESKTOP_REQUIRED` / `UNAVAILABLE` / other):
- Authorized handoff/task tracking and Return behavior:

## 6. Purpose-built mobile composition

- Single active task and context that stays visible:
- Navigation and back/Return behavior:
- Touch interactions and target sizing:
- What is summarized, deferred or expanded:
- Offline and interruption recovery:
- What makes this composition specific to this screen:

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read/write/external effect | Idempotency / reversal | Evidence emitted | Confirmation and failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| | | | | | | |

## 8. Accessibility, motion and localization

- Keyboard, focus order, focus restoration and shortcut behavior:
- Screen-reader names, hierarchy and dynamic announcements:
- Chart/table non-visual equivalents:
- Reduced-motion behavior and interruptibility:
- Chinese/English copy and long-text behavior:

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State/error path | Platform/input | Test layer | Current evidence/reference |
| --- | --- | --- | --- | --- | --- |
| | | | | Widget / API / integration / runtime E2E | |

Acceptance must prove the real owner callable, server-side authorization, original product behavior, lineage, success/error recovery and Trace/Return. A fixture or screenshot alone is insufficient.

## 10. Review decision and open questions

- Decision: `DESIGN_EXPLORATION` / `DESIGN_READY` / `BLOCKED`
- Reviewer and date:
- Open questions with owners and next action:
- Actual contract blockers and changes required before dependent behavior/acceptance (not a separate design-draft gate):
- Acceptance evidence required after implementation:


## Intelligent UI 逐屏采用项（设计增补，不自动改变状态）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

每屏依照其实际任务、Owner、字段、Action和失败状态单独填写；不能复制统一布局模板，不能新增未绑定 callable，也不能将此节当成 DESIGN_READY。

- **真实任务与完成信号：** 用户本屏完成什么，何种真实回执表示完成。
- **屏幕专属呈现：** 为什么选文字、图表、原生Reader、表格、时间轴、编辑器等组合；列出现有字段与Action边界。
- **来源、范围与版本连续性：** Task/Brief/Actor/Scope/时间窗/Budget/Source/Evidence/Artifact如何按既有Owner传递，何时需用户采用新版本。
- **四端差异：** 分别说明Web Workspace、Desktop App、Mobile Companion、Public Website的职责；官网不适合操作时，只呈现已验证公开能力/明确标记示例。保留足够交互、二维手绘水彩/版画视觉和可访问性。
- **失败与恢复：** stale/partial/unknown/denied/offline/error/取消/效果未知的呈现，原任务与未提交工作的恢复方式，禁止重试/效果的条件。
- **补充验收：** 覆盖真实成功、权限/数据失败、跨屏上下文继承及四端职责，并引用验收ID和真实证据要求。

Intelligent UI 可改变结果呈现，不能改变 Product Core、Truth、Source/Evidence、Permission、Owner、范围或Effect语义。缺失绑定继续UNKNOWN/BLOCKED；研究到创作不得要求重复输入Brief或重选同一资料。

### 可编辑设计到源码映射（2026-10-08 审计采用）

F 在 Product Owner 明确恢复后，在本屏现有规范中补齐同一条链；本轮只更新规则，不创建或修改 Figma 工程：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。

### 2026-10-08 有用分段与直接操作补充

应用唯一Experience §38“智能UI的逐步交付与组件选择合同”：本屏明确首个有用块、后续补充/更正、Task/run/输入与结果版本、可用组件及动作、保存回执和恢复。采用原组件保持稳定布局/焦点/选区，旧响应不覆盖用户编辑；事实和引用一致、缺值维度保留、纯文本可用。普通确定性操作不等待模型；按本屏任务决定是否需要动态UI，不能为了统一而套通用卡片。状态仍为原实现/设计状态，新增设计待本屏审阅，未派工。
