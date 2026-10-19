# CTH-08 — 案例工作台与可复用知识

```yaml
screen_id: CTH-08
status: BLOCKED
revision: 1
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-014
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
artifact_disposition: BOUNDED_BLOCKED_STATE_IMPLEMENTATION_ONLY
reviewer: Codex bounded ROUND-11 Luna batch
reviewed_at: 2026-09-22
approval_reference: Product Owner approval of App / Experience Constitution §§30–36; this is not CTH-08 acceptance
```

## 1. User problem and product invariant

- **Role / context:** CTH operator in either `GLOBAL / ALL` or an authorized CTH Subject focus. Selection changes working context only; it never grants access or changes ownership.
- **User task:** inspect an authorized Case, follow its Case → Insight → Decision → Action → Outcome history, and distinguish reviewed reusable knowledge from the live Case.
- **Completion signal for this bounded slice:** render only a source-backed case payload that carries the exact scope and lineage binding below. Otherwise show a blocked, empty or not-collected state without fixture rows.
- **Invariant:** a Case is a working context, not a relabeled risk note or event row. Knowledge is a reviewed conclusion and never overwrites the original Case facts.
- **Current limitation:** `experience_screens._build_cth08(binding)` projects scoped risk notes/events; these are not canonical Case IDs or a Case lifecycle payload. The existing `api_dual_domain` Case Owner is real, but this screen read-model has not bound its canonical Case payload and Case-specific lineage/action contract. Do not deny the existing backend Owner or promote observation rows into Cases.

## 2. Route, entry and return

- **Entry:** nested CTH workflow from the CTH work surface. The bounded screen is directly instantiable while the shared shell route remains outside this batch.
- **Required read binding:** `GET /api/settings/context` must return `lumenis.context.v1`, `selection_only=true`, and either `GLOBAL_ALL` or `FOCUS` for domain `CTH`. The subsequent `GET /api/experience/screen/CTH-08` response must return `binding.actor_scope=verified`, `binding.context_mode` matching the selection, `binding.domain=CTH`, and `binding.evidence_lineage=verified`. Focused responses must echo the authorized `subject_id`.
- **Exit / Trace / Return:** selecting a case is local presentation state. Return restores the case board/list position and selected case. No context mutation, Case write, knowledge promotion or external action is implemented.

## 3. Verified data and callable bindings

| Priority | UI field / action | Source / callable | Definition and missing behavior | Binding |
| --- | --- | --- | --- | --- |
| P0 | Scope banner | `settingsContext()` plus the screen binding | Show `GLOBAL / ALL` or a safe focused display name; never use a Subject ID as an authorization claim | Required before any Case data is rendered |
| P0 | Case rows | Existing CTH Case owner, pending binding via `screen('CTH-08')` | Requires `cases[]` with `id`, `title`, `state`, `summary`, `timeline[]` and trusted `evidence[]`; high-risk notes/events are not accepted | `BACKEND-GAP-014`, currently missing |
| P1 | Case timeline | Same Case owner | Each step must identify a workflow stage and observed state; no fabricated completion | Unverified until this screen binds the existing canonical Case lifecycle |
| P1 | Knowledge shelf | CTH/Shared reviewed-learning owner | Requires reviewed item, source Case and trusted evidence reference; not the same list as active Cases | Unknown until owner and lineage exist |
| DRAFT | New Case | `CTH-08.new-case`, `case:write` | Opens no durable write in this batch | Disabled: no Permission, effect fence or result contract is bound |

Trusted CTH-08 fixture IDs are `CASE-221` and `EV-7710` for this bounded renderer only (not a single-subject scope). Any other reference is omitted and shown as unavailable, never echoed as raw input.

## 4. State and recovery matrix

| State | Trigger | User-visible meaning | Available action | Acceptance |
| --- | --- | --- | --- | --- |
| Loading | Context or screen read pending | 正在读取案例工作台 | None | CTH08-W-001 |
| Empty | Bound response has `cases=[]` and a valid Case contract | 当前范围内暂无可查看案例。 | Refresh | CTH08-W-002 |
| Not collected | Bound response has no Case/knowledge section | 案例资料尚未接入，暂无可核验的生命周期记录。 | Refresh | CTH08-W-003 |
| Partial | Some rows lack trusted references or timeline fields | 部分案例资料未完成核验，未核验内容不显示。 | Refresh | CTH08-W-004 |
| Blocked | Missing actor/context/lineage binding, 401 or 403 | 当前范围暂不能查看案例资料。 | Retry; return | CTH08-W-005 |
| Offline / Error | Transport or malformed response | 暂时无法读取案例资料，请稍后重试。 | Retry | CTH08-W-006 |
| Ready | Bound Case payload | Display lifecycle board, selected timeline and separate knowledge shelf | Local selection only | CTH08-W-007 |

## 5. Purpose-built composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-08)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- **Desktop/Web:** lifecycle board/list on the left, selected Case timeline and source trail inspector on the right, with a separate verified-knowledge shelf below. The board is not a generic table or renamed dashboard card set.
- **Mobile:** ranked Case inbox first, then the selected step-by-step timeline, source trail and knowledge shelf. Board columns collapse into explicit state labels.
- **Accessibility:** state is conveyed by text and icon plus color; case rows have one semantic label containing title, state and risk; Enter/Space selects; Escape returns to the inbox; loading/blocking states are live regions.

## 6. Actions, authorization and effects

| Action | Permission / effect | UI behavior | Evidence |
| --- | --- | --- | --- |
| Read Case | Server-side actor + CTH scope + lineage binding | Render only after all bindings pass | Trusted allowlist only |
| Select / Return | Local presentation state | Enabled and reversible | No write or new Evidence |
| New Case | `case:write` plus exact write result and Effect Fence | Disabled; no request is issued | None |
| Promote knowledge | No verified owner or approval contract | Not shown as an executable control | None |

HTTP 200, a static action registry row, fixture content or a plausible title is not business success.

## 7. Executable acceptance

| Acceptance ID | Action / expected result | State path | Platform/input | Test layer |
| --- | --- | --- | --- | --- |
| CTH08-W-001 | Pending repository keeps Case and knowledge rows hidden and announces loading | Loading | All widths | Widget |
| CTH08-W-002 | Bound response with no Cases is an empty state, not fixture fallback | Empty | Desktop/mobile | Widget + repository |
| CTH08-W-003 | Missing Case section is not-collected and does not relabel notes/events | Not collected | Desktop/mobile | Widget |
| CTH08-W-004 | Unknown Evidence IDs and hostile fields never render | Partial / hostile input | All widths | Widget |
| CTH08-W-005 | Missing scope or lineage binding blocks all Case data and disables New Case | Blocked | Desktop/mobile | Widget + repository |
| CTH08-W-006 | 401/403/offline/malformed response keeps internal server text hidden and offers retry | Error | Desktop/mobile | Widget |
| CTH08-W-007 | Desktop board, tablet list and mobile inbox/timeline recompose without overflow; Trace/Return restores selection | Ready | 1440 / 900 / 390 logical px | Widget |

## 8. Review decision and open dependencies

- **Decision:** BLOCKED for full CTH-08 acceptance. The bounded implementation is limited to a source-contract guard and purpose-built read-only composition.
- **Required before DESIGN_READY / ACCEPTED:** bind the existing canonical Case owner and its Case-specific actor/scope read decision to this screen, return its Case lifecycle payload, reviewed knowledge owner, trusted Evidence resolution, write Permission, Effect Fence admission, result contract and runtime/E2E evidence.
- **Current disposition:** no fixtures, high-risk note IDs or curated event IDs are presented as Cases.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 追踪真实Case到Outcome并区分复用知识。
- **屏幕专属呈现：** Case→Insight→Decision→Action→Outcome泳道；知识独立显示审阅状态
- **来源、范围与版本连续性：** 所有节点绑定同一canonical Case/scope/来源和版本；知识不覆盖事实
- **四端差异：** Web/Desktop全链和知识并看；Mobile逐阶段返回；官网不露私有Case
- **失败与恢复：** 没有canonical Case不以note替代；receipt未知留待核
- **补充验收：** 父子阶段可追踪，未发生步骤不显示完成，知识有审阅依据。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
