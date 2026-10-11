# CTH-09 — 风险与决策工作台

```yaml
screen_id: CTH-09
status: BLOCKED
revision: 1
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-015
  - BACKEND-GAP-016
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
artifact_disposition: BOUNDED_BLOCKED_STATE_IMPLEMENTATION_ONLY
reviewer: Codex bounded ROUND-11 Luna batch
reviewed_at: 2026-09-22
approval_reference: Product Owner approval of App / Experience Constitution §§30–36; this is not CTH-09 acceptance
```

## 1. User problem and product invariant

- **Role / context:** CTH operator working in `GLOBAL / ALL` or an authorized focused CTH Subject.
- **User task:** inspect the basis of a risk, review a separate decision ledger, and understand whether an action is merely proposed, awaiting approval or actually executable.
- **Completion signal for this bounded slice:** show risk and decision rows only when the response proves actor/context scope and trusted references. No control may execute a decision in this batch.
- **Invariant:** risk, insight, decision and action remain distinct. Severity is never conveyed by color alone, and a static action declaration is not authorization.
- **Current limitation:** the current screen builder returns risk notes with `NOTE:<id>` references and has no Decision record, write callable or actor-to-Subject Permission decision.

## 2. Route, entry and return

- **Entry:** nested CTH decision workflow from a Case or the CTH work surface. The shared route is outside this bounded path.
- **Required read binding:** the context contract must be valid and the screen response must include `binding.actor_scope=verified`, matching `context_mode`, `domain=CTH`, and `evidence_lineage=verified`. Focus mode must echo `subject_id`.
- **Exit / Trace / Return:** selecting a risk or decision is local state. Return restores the risk feed and selected row; no context switch or external effect is made.

## 3. Verified data and callable bindings

| Priority | UI field / action | Source / callable | Definition and missing behavior | Binding |
| --- | --- | --- | --- | --- |
| P0 | Risk register | CTH risk owner | Requires `risks[]`, stable risk ID, level, score when actually returned, description and trusted `evidence[]` | `BACKEND-GAP-015`, currently not scope/lineage safe |
| P0 | Decision ledger | CTH Decision owner | Requires `decisions[]`, owner/status, requested action and explicit action contract state | `BACKEND-GAP-016`, currently ABSENT |
| P1 | Source trail | Canonical Evidence owner | Only allowlisted IDs are displayed; `NOTE:<id>` is not Evidence | Current response cannot satisfy this |
| EFFECT | Confirm action | Permission + approval + Effect Fence + real result contract | Disabled unless all exact gates and a callable are present; this UI has no mutation client | Not bound |

Trusted CTH-09 reference IDs are `EV-7710`, `EV-7699` and `EV-7712`. Unknown or `NOTE:` references are withheld.

## 4. State and recovery matrix

| State | Trigger | User-visible meaning | Available action | Acceptance |
| --- | --- | --- | --- | --- |
| Loading | Read pending | 正在读取风险与决策 | None | CTH09-W-001 |
| Empty | Bound response contains no risk or decision rows | 当前范围内暂无待处理风险或决策。 | Refresh | CTH09-W-002 |
| Not collected | Risk/decision section absent | 风险或决策资料尚未接入。 | Refresh | CTH09-W-003 |
| Partial | Risk is present but some basis/action lineage is missing | 部分资料尚未完成核验，未核验依据不显示。 | Inspect safe rows; retry | CTH09-W-004 |
| Blocked | Scope, lineage or decision owner missing; 401/403 | 当前范围暂不能查看风险与决策。 | Retry; return | CTH09-W-005 |
| Offline / Error | Transport or malformed response | 暂时无法读取风险与决策，请稍后重试。 | Retry | CTH09-W-006 |
| Ready | Bound risk/decision payload | Show matrix/feed, ledger and selected basis | Local selection only | CTH09-W-007 |

## 5. Purpose-built composition

- **Desktop/Web:** a ranked risk register with score tracks and text severity on the left; a separate decision ledger with owner/status/effect readiness on the right; a selected-basis inspector below or beside them. This is not the CTH-08 case board.
- **Mobile:** a ranked risk feed, selected risk basis, then decision ledger. Each disabled action states why it cannot be executed.
- **Accessibility:** level, score and status are included in semantics; critical/high/medium/low text is always present; selection uses keyboard and touch; blocking/error states are live regions.

## 6. Actions, authorization and effects

| Action | Required proof | UI behavior |
| --- | --- | --- |
| Inspect basis | Bound read response and trusted reference | Enabled as local selection only |
| Record decision | Exact CTH Decision write callable, Permission decision, approval when required, Effect Fence admission and result contract | Disabled; no request is issued |
| Execute proposed action | Matching actor/domain/Subject scope, `PermissionResult.verification_state=verified`, approval token where required, staged/idempotent effect and observable result | Disabled; no optimistic success |

HTTP 200, `VERIFIED_AVAILABLE` in a JSON registry, a risk score or a button label is not authorization or effect success.

## 7. Executable acceptance

| Acceptance ID | Action / expected result | State path | Platform/input | Test layer |
| --- | --- | --- | --- | --- |
| CTH09-W-001 | Pending read hides risk/decision rows and announces loading | Loading | All widths | Widget |
| CTH09-W-002 | Bound empty response stays empty and does not use the fixture | Empty | Desktop/mobile | Widget |
| CTH09-W-003 | Missing Decision section is not-collected and no action control appears enabled | Not collected | All widths | Widget |
| CTH09-W-004 | Unknown/NOTE evidence and hostile fields are omitted | Partial / hostile input | All widths | Widget |
| CTH09-W-005 | Missing binding blocks the screen; every write/action control is disabled | Blocked | Desktop/mobile | Widget + repository |
| CTH09-W-006 | 401/403/offline/malformed response hides server detail and offers retry | Error | Desktop/mobile | Widget |
| CTH09-W-007 | Matrix/ledger desktop, tablet and mobile feed compositions recompose without overflow; Trace/Return preserves selection | Ready | 1440 / 900 / 390 logical px | Widget |

## 8. Review decision and open dependencies

- **Decision:** BLOCKED for full CTH-09 acceptance. The bounded implementation is read-only and fail-closed.
- **Required before DESIGN_READY / ACCEPTED:** canonical Decision owner and API, actor-to-Subject read/write Permission, approval token flow, Effect Fence/effect result contract, item-level Evidence lineage and runtime/E2E evidence.
- **Current disposition:** current risk notes and static action declarations cannot be shown as an authorized decision loop.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 区分风险依据、决策状态、审批和实际动作。
- **屏幕专属呈现：** 风险、Decision ledger、Action receipt分区显示提案到执行状态
- **来源、范围与版本连续性：** 沿用已有Actor/scope/approval/effect ID，不为风险创建平行任务
- **四端差异：** Web/Desktop并列风险与账本；Mobile先状态再依据；官网不露内部审批
- **失败与恢复：** 未经批准无执行控制；effect UNKNOWN禁止重试并保留上下文
- **补充验收：** 服务端状态一致；真实Outcome/Evaluation才能称闭环完成。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。保留序境二维手绘水彩/版画色彩语言与有功能含义的线性控件；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，只借鉴手绘平面笔触与色彩，不复制参考人物、不用3D质感。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
