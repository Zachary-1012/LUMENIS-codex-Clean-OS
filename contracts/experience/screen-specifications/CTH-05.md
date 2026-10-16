# CTH-05 — 舆情日历

```yaml
screen_id: CTH-05
status: BLOCKED
revision: 1
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-011
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: NON_AUTHORITATIVE_EXPLORATION_ONLY
reviewer: Codex delegated ROUND-10 bounded source review
reviewed_at: 2026-09-22
approval_reference: source baseline origin/main 5ba1aefc53a1babc293e990c23c62f841724c843; this is not per-screen acceptance
```

## 0. Authority basis and artifact disposition

- The governing experience row is the CTH-05 sentiment calendar: heatfield, scale, availability legend, selected-date detail and keyboard list mode.
- The current source is `experience_screens._build_cth05()` through `GET /api/experience/screen/CTH-05`. It returns chart arrays; missing days stay missing and real zeros stay zero. A complete trend definition and per-day source/error state are still required before drawing.
- Static calendar fixtures and the binding registry describe the intended shape only. They cannot promote a chart to real data.
- This is a date-density task surface with a linked day detail and list alternative, not a generic chart/card page.
- Sol design decision: `BLOCKED`; the implementation refuses to draw calendar values until the canonical definition and aligned arrays are present.

## 1. User problem and product invariant

- **User task:** find days with returned sentiment or event density, inspect one selected day, and switch to a precise list for keyboard use.
- **Context:** `GLOBAL_ALL` is the supported current source scope only when server `global_binding` (or the current canonical equivalent) proves global grant/scope, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage. A focused CTH scope additionally requires `focus_binding.applied == true`, exact Subject equality, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage; otherwise the repository blocks it.
- **Completion signal for this slice:** only a returned calendar with a complete numerator, denominator, time window, Subject, source and freshness definition is rendered. Otherwise the page says why the calendar is unavailable.
- **Invariant:** zero is a real returned value only when the source explicitly returns zero; a failed read or absent day must never become zero. `bound=true` alone never authorizes a global aggregate.
- **Out of scope:** date-range writes, source navigation, event/Cases, export and any inferred sentiment explanation.

## 2. Route, entry, exit and return

- **Entry:** `Cth05Screen(client: ...)` from the existing workspace; no new route.
- **Read sequence:** `settingsContext()` → `screen('CTH-05')`. The adapter first verifies the server scope/read/lineage binding, then reads `chart.labels`, `chart.series[name,data]` and `trend_metadata`/`truth.trend`; it accepts only aligned arrays and a scope-matching definition.
- **Calendar source:** current builder calls daily CTH data and returns chart arrays. It does not expose per-cell Evidence references or a reliable per-day failure state.
- **Exit / return:** selecting a day updates local detail; List/Calendar switches presentation mode; no server request or source deep-link is implied.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source/ViewModel field or callable | Definition / units / window | Freshness and missing-data behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Scope label | SYSTEM context read | `settingsContext()` context | `GLOBAL_ALL` or applied focused CTH scope | Invalid/missing scope blocks; internal IDs hidden | — | Current context contract |
| P1 | Date labels and density values | CTH daily read | `_build_cth05()` chart `labels`, series `negative`/`负面`, `high`/`高风险` | Values are returned counts over the returned time window | Adapter requires equal lengths and an authorized server binding; absent definition or ambiguous day state yields NOT_COLLECTED, not zero | BACKEND-GAP-011 | Current source arrays; zero-fill risk documented |
| P1 | Trend definition rail | CTH metric contract UNKNOWN | `trend_metadata` or `truth.trend`: numerator, denominator, time_window, subject, source, freshness | All six fields required; subject must match `GLOBAL/ALL` or focused Subject | Missing/unsafe source is incomplete; no chart | BACKEND-GAP-011 | Current server response lacks this metadata |
| P1 | Selected-day detail/list | CTH calendar/Evidence owner UNKNOWN | Local selection over aligned day values; per-day evidence is not returned | Shows returned counts only; no event list until a source binding exists | Detail says records are not connected; no guessed sources | BACKEND-GAP-011 | Per-cell lineage pending |

The page does not call `weekly_events`, `calendar`, a new trend API or a new data store. Current server array output is insufficient for full acceptance.

## 4. State and recovery matrix

| State | Trigger/evidence | User-visible meaning | Available actions | Recovery/return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Context/chart request pending | 正在加载情绪日历 | None | Announce loading; no calendar cells | CTH05-W-001 |
| Empty / no dates | Explicit empty chart state and no days | 当前范围内暂无日历记录 | Refresh | Do not synthesize zero-filled dates | CTH05-W-002 |
| Not collected / definition missing | Arrays or complete trend definition absent | 情绪日历暂不可用，口径尚未完整返回 | Refresh | Keep raw arrays hidden | CTH05-W-003 |
| Fresh / stale | No reliable source freshness state | UNKNOWN | None | Never use response time as data freshness | CTH05-W-004 |
| Partial | One series missing/misaligned or one day state unknown | 部分日历数据暂不可用 | Refresh | Do not render a misleading heatfield | CTH05-W-003 |
| Offline | Core or source failure | 暂时无法连接 | Retry | Failure is not zero or empty | CTH05-W-005 |
| Blocked / permission denied | Invalid scope, `bound=false`, missing global grant/binding, or focused response without exact authorized binding; 401/403 | 经营主体信息暂不可用 | Retry after recovery | No unscoped focused calendar; no aggregate is consumed without server lineage | CTH05-W-006 |
| Error | Malformed response/5xx | 运营信息暂不可用 | Retry | Hide raw details | CTH05-W-005 |
| Local selection/list | Choose day or List mode | 查看所选日期的已返回数值 | Calendar/List toggle | Restore selected day when switching modes | CTH05-W-007 |

## 5. Purpose-built desktop composition

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-05)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- **Primary question:** which dates have returned sentiment density, and what can be said about one selected date without overstating its source?
- **Hierarchy:** scope and definition → calendar heatfield with explicit scale/legend → selected-day detail. List mode is a first-class keyboard alternative, not a hidden fallback.
- **Wide desktop:** `cth05/desktop-layout` places the calendar panel and day detail side by side. The selected cell has text, focus and semantic state; color only supplements the numeric values.
- **Keyboard:** every date is reachable in List mode; Enter/Space selects; List/Calendar is keyboard-operable; focus returns to the selected date after mode change where possible.
- **Screen identity:** date grid + density scale + selected-day evidence gap define this screen.

## 5A. Web Workspace composition and desktop-only capability boundary

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-05)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- Web and desktop share the same aligned-day model and do not add client-side calendar calculations beyond rendering returned values.
- Evidence strip, event list, source opening and range writes remain unavailable until their owners/callables are bound.
- Runtime E2E must verify keyboard list mode and resize; widget evidence alone is not production acceptance.

## 6. Purpose-built mobile composition

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-05)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- **Active task:** choose a day from a compact calendar/list, then read its returned counts and availability state.
- **Layout:** calendar/list selector first, compact day density marks second, selected-day detail third. The detail never claims source records when none are returned.
- **Touch:** days and mode toggles meet 48 logical pixels; selected day is announced with date and counts.
- **Interruption:** no offline calendar cache or pending range change is shown. Retry repeats the read.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read/write/external effect | Idempotency / reversal | Evidence emitted | Confirmation and failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Load context/calendar | SYSTEM + CTH daily read; actor/Subject binding UNKNOWN | Optional global auth; screen READ UNKNOWN | Read only | Repeatable | Returned daily values only | Honest ready/not-collected/error state |
| Select day / switch List | Flutter local state | None | No server effect | Reversible | None | Enabled |
| Inspect source/event/range/export | CTH/Evidence/action owners UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | No enabled controls |

## 8. Accessibility, motion and localization

- Calendar cells expose date, negative count, high-risk count and selected state. List mode provides a linear equivalent and is required for keyboard precision.
- Heat colors are paired with labels and numbers; loading, unavailable, empty and error states are live regions.
- No authored motion is required; reduced motion preserves selected state and focus.
- The bounded UI uses existing `screen.CTH-05`, context, common, state and `cth01.*` keys; no hardcoded screen copy remains. Canonical l10n must add `cth05.calendar_legend`, `cth05.definition_missing`, `cth05.day_detail`, `cth05.list_mode`, `cth05.source_unavailable` and related state copy in zh-CN/en/ko before acceptance, then replace the temporary generic mappings. No second l10n owner.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State/error path | Platform/input | Test layer | Current evidence/reference |
| --- | --- | --- | --- | --- | --- |
| CTH05-W-001 | Pending request announces loading and hides dates | Loading | Widget | `app/test/features/cth/cth05/cth05_screen_test.dart` | Local evidence |
| CTH05-W-002 | Explicit empty result shows no cells or invented zero values | Empty | Widget | Widget test | Local test |
| CTH05-W-003 | Raw arrays without definition, misalignment or unknown day state stay unavailable | Not collected/partial | Widget/repository | Widget + contract test | Current server metadata gap |
| CTH05-W-004 | Missing source freshness is not described as latest/live | Freshness unknown | API/widget | Contract test required | Current server gap |
| CTH05-W-005 | Offline/5xx/malformed response is recoverable and safe | Offline/error | Widget | Widget test required | Safe copy implemented |
| CTH05-W-006 | Focused context without applied binding is blocked | Focus scope | Repository/widget | Repository test required | Current runtime focus gap |
| CTH05-W-007 | Select day and switch Calendar/List while preserving selection and semantics | Local return | Widget; keyboard/touch | Widget test | Desktop/mobile implementation evidence |
| CTH05-W-008 | A real new event/date flows Source → Event → Evidence → day detail | Real user work | Runtime/E2E | Required before ROUND-10 PASS | Not yet run |
| CTH05-W-009 | Return `bound=true` with chart arrays but no global grant/lineage; the repository blocks before decoding the aggregate | Global authorization/lineage block | Repository/widget | Repository test | Implemented hostile fixture |
| CTH05-W-010 | Return authorized `GLOBAL_ALL` and exact Guangzhou Taikoo Hui `FOCUS` definitions; only matching scope is rendered | Authorized global/focus read | Repository | Repository test | Implemented legal fixtures; per-day lineage still pending |

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for a real sentiment calendar and ROUND-10 acceptance. The bounded implementation is intentionally conservative: it renders a calendar only when the complete definition and aligned values are returned.
- **Open owners:** CTH daily source must preserve zero vs failure; metric owner must return definition/freshness; Evidence must bind per-day records; SYSTEM must bind Subject scope; l10n must add the three locales.
- **Required before acceptance:** real new data, per-day state/error semantics, complete definition, Subject-scoped read authorization, source-linked day detail and desktop/mobile E2E.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 寻找真实变化日期并查看当日样本。
- **屏幕专属呈现：** 真实日密度与当日列表关联，标记分子/分母/窗口
- **来源、范围与版本连续性：** 保留scope、日期、时区、metric定义和source
- **四端差异：** Web/Desktop日历+列表；Mobile日期摘要后列表；官网不显示内部日历
- **失败与恢复：** 零/无数据/未采集/失败区分，缺分母不画热度
- **补充验收：** 点日准确过滤当日样本；缺失日期不自动为0。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
