# ACC-02 — Subject and view-lens selection

```yaml
screen_id: ACC-02
status: BLOCKED
revision: 4
owner_domain: SYSTEM settings / CTH Subject Registry / BMP BrandFocus
binding_ids:
  - CODEX-ACC02-CONTEXT
  - CODEX-ACC02-SUBJECT-REGISTRY
product_owner_approval: APPROVED
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
selection_design_decision: DESIGN_READY_BOUNDED_SELECTION_CONTINUATION
registration_design_decision: DESIGN_READY_BOUNDED_REGISTRATION
artifact_disposition: REVIEWED_BOUNDED_SELECTION_AND_REGISTRATION
reviewer: Sol root integration review
reviewed_at: 2026-09-30
approval_reference: existing R14-ACC02-LAYERED-SELECTION review; primary controller approved bounded registration in section 11 on 2026-09-30
```

## 0. Authority and invariant

- ACC-02 is a Subject-first selection surface. A selection changes the current view lens only; it never grants permission, changes ownership or rewrites Canonical Truth.
- The server remains the owner of context and Subject authorization. A local list or cached selection cannot substitute for server confirmation.
- The desktop split list/detail and mobile two-stage flow are specific to selecting and confirming a Subject, not a generic settings card grid.

## 1. Routes and callable contract

- Read current view: `GET /api/settings/context` via `settingsContext()`.
- Read CTH directory: `GET /api/settings/subjects?domain_id=CTH` via `settingsSubjects(domainId: 'CTH')`.
- Confirm focus: `PUT /api/settings/context` with `{mode: FOCUS, domain_id, subject_id}` via `selectContext()`; the server rechecks access and returns the context envelope.
- Exit returns to the host shell with the server-confirmed selection. No local grant or direct business-data fetch is performed.

## 2. Verified fields and allowlist

| UI field | Source | Rule |
| --- | --- | --- |
| Context mode | `context.mode` | `GLOBAL_ALL` / `FOCUS`; otherwise unavailable |
| Current view label | `context.display_name.zh/en` | safe bounded text only |
| Subject id | `subject_id` / `id` | `[A-Za-z0-9._:-]+`, bounded length |
| Subject name/type/domain | Subject row | safe text; domain only CTH/BMP; invalid rows hidden |
| List state | response `ok`, list presence, error class | empty, unavailable and blocked remain distinct |

Paths, tokens, provider/model strings, raw errors and arbitrary domains are never rendered.

## 3. State and recovery matrix

| State | Meaning | Action |
| --- | --- | --- |
| Loading | Context and directory reads are pending | Wait |
| Ready | Server returned safe Subject rows | Search, select, confirm |
| Empty | Server confirmed an empty directory | Show empty, not access failure |
| Blocked | 401/403 or permission denial | Retry or return; do not show a local Subject |
| Unavailable | timeout, malformed rows or partial dependency failure | Refresh the affected read |
| Confirming | `PUT` is in flight | Disable duplicate confirmation and show progress |
| Confirmation error | server rejected or failed the selection | Keep the previous server state and show recovery copy |

## 4. Desktop and mobile composition

- Desktop at ≥1000px: bounded list and confirmation detail side by side, with the context banner above both.
- Narrow layouts: the searchable list is the browsing stage. Selecting a returned Subject opens a focused confirmation layer; the list, search and scroll position remain underneath for Return. Detail is not appended beneath a long list.
- Keyboard order is context banner → search → returned rows → selected Subject → confirm → continue. Rows are reachable by keyboard and have visible selected state.

## 5. Authorization, effects, and accessibility

- In the existing selection slice, `PUT` confirms focus and the recovery `DELETE` clears focus; both remain Core/SYSTEM-owned and server-authorized. Registration is separately bounded by section 11 and its pending exact-write contract.
- Selection is not permission. Denied or pending responses do not update the UI to the requested Subject.
- Announce list count, selected row and confirmation result; do not rely on color. Search and controls remain usable at enlarged text sizes.

## 6. Localization integration key list

Existing shared keys: `screen.ACC-02`, `common.search`, `common.refresh`.

Feature integration keys: `acc02.availableSubjects`, `acc02.confirmLens`, `acc02.globalView`, `acc02.focusedView`, `acc02.subjectListEmpty`, `acc02.subjectListBlocked`, `acc02.subjectListUnavailable`, `acc02.serverConfirmation`, `acc02.confirmSelection` for `zh-CN`, `en`, and `ko`. Current code keeps local fallback copy pending shared-l10n integration.

## 7. Executable acceptance

| ID | Acceptance | Current evidence |
| --- | --- | --- |
| ACC02-PARSE-01 | Keep only safe CTH/BMP Subject rows and retain empty vs blocked | `acc02_feature_test.dart` |
| ACC02-SELECT-01 | Confirm selection through the repository and reload server state | `acc02_feature_test.dart` view-model test |
| ACC02-RESP-01 | No overflow at phone width; desktop uses the two-region composition | static responsive implementation; widget/E2E still required |
| ACC02-REAL-01 | Select a real non-reference Subject, confirm, return to the real workspace and verify downstream context | Not run in this bounded batch |

## 8. REAL USER WORK E2E / data card

- `REAL USER JOB`: an authorized operator chooses a real Subject from the server registry and confirms the view lens before using CTH work.
- `REAL INPUT`: live context envelope, live Subject Registry rows, selected non-reference Subject.
- `END-TO-END PATH`: shell → ACC-02 → context/directory reads → server-confirmed PUT → return → CTH consumer read.
- `USER-VISIBLE RESULT`: selected Subject is visibly server-confirmed; denial remains denial.
- `FAILURE/RECOVERY`: preserve previous state on 401/403/offline/server error; never fabricate a Subject.
- `EVIDENCE`: request/response, permission decision, return state and downstream Subject header.
- `ACCEPTANCE ASSERTION`: `BLOCKED_PENDING_LIVE_RUNTIME_E2E`.
- `RANDOM ENTITY DATA ACCEPTANCE`: sample count 0 here; future acceptance must rotate non-reference commercial/brand/cross-region registry rows.
- `GLOBAL UNIVERSE / DATA MATURITY IMPACT`: selection supports GLOBAL/ALL and focus-only semantics but does not assert collection maturity; report coverage separately.
- `COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO` until real selection/return is proven on promised surfaces.

## 9. Continuous frontier research / capability evolution

- `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE` on 2026-09-22 after inspecting the current Core client, Subject Registry contract and local Flutter 3.47.5 responsive patterns. No new state-management or directory dependency is justified.
- Decision: `ADAPT` existing context/Subject owners; no parallel registry, client permission cache or navigation contract.
- Any later multi-select, creation or access-request action requires canonical owner and permission/effect review; this slice remains selection-only.

## 10. Review decision

The existing list/detail ownership is reviewed as `DESIGN_READY` for bounded
selection continuation, with the interaction revision below. Continue opens the existing ACC-03 launch map only
when the selected domain and Subject match the server-confirmed focused
context, no confirmation is pending and no confirmation error remains.
Any in-flight selection disables duplicate confirmation and continuation,
including after selecting another row. Leaving the page cannot notify a
disposed view model. The shell displays the client's latest confirmed context
on continuation; no local permission or business effect is introduced.
Real authorized selection/return E2E and target-surface acceptance remain
unaccepted until independently recorded. GLOBAL/ALL remains the default;
this chooser is optional and is not a mandatory entry gate.

### Shared scope-picker recovery — 2026-09-27

Sol review: `DESIGN_READY` for the bounded recovery of the shell's existing
GLOBAL/FOCUS selector. This does not widen ACC-02's CTH directory or enable a
new business action. The shared selector retains its CTH/BMP focus support.

When a current-context read fails, the message remains unavailable or denied.
If the shell has a previously server-confirmed FOCUS envelope, offer the
existing clear action without displaying cached domain/Subject rows as newly
authorized. Call `LumenisCoreClient.clearContext()` (`DELETE
/api/settings/context`); only a validated GLOBAL_ALL response updates the
shell and closes the selector. A failed or denied clear retains the failure
state and must not claim GLOBAL. No previously confirmed focus means no
cache-derived recovery control. An in-flight clear disables conflicting
requests and duplicate submission. Selection/clear never invokes collection.

Verification: CTH and BMP expired-focus recovery, clear denial, no known focus,
and in-flight action controls in the existing shell tests. Real server-bound
recovery remains `LIVE_NOT_VERIFIED` until the safe Core environment is ready.

### Search/list recovery review — 2026-09-28

Sol review: `DESIGN_READY` for bounded repairs to the existing chooser. The
mobile list must scroll independently so every returned Subject can be
reached; the wide split composition remains. Search has a labelled clear action
that restores the returned list without changing focus or sending a mutation.
Blocked/unavailable/unknown list states do not display a numeric zero and disable
search. Partial read failure offers a retry through the existing repository,
with no duplicate retry during confirmation. Empty and no-search-match remain
separate states. State explanations, long names, retry and confirmation controls
must remain readable/reachable at 320 px and 200% text, including wide-window
enlarged text. Retry never grants permission or confirms a locally selected row.

This review does not widen the CTH-only directory API, add entity registration,
invent country/relationship fields or alter GLOBAL/FOCUS/Permission. Those
approved product requirements remain with their canonical contracts and future
bindings. Optional product account/login/settings are in the approved engineering
closure; there is no account wall. The public product default remains GLOBAL.

Research accessed 2026-09-28: official Flutter
[ListView](https://api.flutter.dev/flutter/widgets/ListView-class.html) and
[TextField](https://api.flutter.dev/flutter/material/TextField-class.html)
references, checked against the installed Flutter 3.47.5 SDK (BSD-3-Clause,
actively maintained upstream). ADAPT existing bounded scrolling and text controls;
no package upgrade, new design system or copied visual assets. The capability
locator found no separate historical research for `ACC-02`; the reviewed current
spec and existing implementation remain the applicable design inputs.

Acceptance: long-list last-row selection, clear-search restoration, actual retry,
unknown-count suppression and enlarged-text recovery; synthetic widget rows are
regression evidence only. Real authorized selection through the workspace and
native-surface acceptance remain separate required gates.

### Layered selection interaction — 2026-09-28

Sol review: `DESIGN_READY`, implementing the Product Owner's explicit instruction
to use meaningful hierarchy, direct manipulation and motion instead of treating
every mobile task as a vertical settings page. This is a revision of the same
Subject-selection job under Constitution §§32 and 36, not a new surface family.

- **Phone / compact window:** browse the actual searchable directory; tap a row
  to open the Subject confirmation sheet. Keep the originating list mounted.
  Within that sheet, horizontal paging compares the filtered returned Subjects,
  with explicit Previous/Next controls for keyboard and assistive users. A visible
  position label describes the candidate set, never collection coverage. Closing
  or Back returns to the same query/scroll position and performs no write.
- **Wide window:** retain the searchable directory beside the selected Subject
  inspector. Selecting a different row changes that inspector with a short
  directional transition. Outgoing content cannot receive input. The inspector
  remains usable for long names and enlarged text; no fixed-height overflow.
- **Action hierarchy:** browsing/paging changes only a local candidate. Confirm
  invokes the existing repository exactly once; Continue stays disabled until
  the live server context matches the shown candidate and no operation/error is
  pending. During confirmation, paging and duplicate confirmation/retry are
  disabled. A response for another candidate never enables Continue. Dismissal
  does not pretend to cancel a server write already sent.
- **Motion thesis:** list → candidate layer → confirmed context → Return. Use
  the existing shell's 180 ms / ease-out-cubic vocabulary for short disclosure
  and selection feedback. Respect `MediaQuery.disableAnimations`; reduced motion
  removes spatial travel while retaining immediate selection and status feedback.
  No idle pulse, decorative particle system, forced scroll or fabricated progress.
- **Reachability:** fixed visible Close/Return and action region, safe insets,
  content scrolling within the detail layer, 320 px / 200% text, accessible names
  in Chinese/English/Korean. Drag is an optional equivalent of labelled controls.

Interaction acceptance adds: open → swipe/Next → confirm exact candidate → server
response → Continue; cancel/Back preserves query and list position; denied writes
retain the candidate and retry; rapid actions cannot overlap; reduced-motion and
wide/phone transitions remain operable. Widget fixtures prove controls only.
Authorized real-registry selection and native OS acceptance remain required.

Research accessed 2026-09-28: official Flutter
[PageView](https://api.flutter.dev/flutter/widgets/PageView-class.html),
[modal sheet](https://api.flutter.dev/flutter/material/showModalBottomSheet.html)
and [reduced-motion query](https://api.flutter.dev/flutter/widgets/MediaQuery/disableAnimationsOf.html).
ADAPT Flutter 3.47.5 primitives already available in the app; BSD-3-Clause,
maintained by Flutter. No external UI assets, library or provider is introduced.

## 11. Bounded Subject / BrandFocus registration — 2026-09-30

### 11.1 Decision, owner and entry gate

The primary controller reviewed this interaction as
`DESIGN_READY_BOUNDED_REGISTRATION` in the active 序境12 coordination thread.
The existing selection review remains valid. Overall ACC-02 delivery is
`BLOCKED` until the new write binding and real user flow are verified; this
document does not revoke working selection or accept the wider screen/round.

Reuse the current shell scope picker, `LumenisCoreClient`, SYSTEM settings and
`subject_registry.py`. Add no page, registry, identity service, account screen
or automatic collection path. Product access remains open without a login or
account design; server Permission and exact effect confirmation remain enforced.

Implementation of the write call waits for the primary controller's current
server contract. Do not guess a confirmation endpoint, header, token, principal
or approval response. Existing `POST /api/settings/subjects` is the sole intended
registry mutation; a confirmation step is a gate on that operation, not another
registry owner. A specification approval alone cannot make this call usable.

### 11.2 Task and interaction

- **Job:** a commercial operator or brand practitioner adds a real object absent
  from the directory, then chooses whether to view it or continue browsing.
- **Entry:** inside the existing CTH/BMP scope picker, beside search, show
  “添加主体” / “添加品牌” for the selected business domain. The current domain is
  visible throughout. This entry supports arbitrary valid registry identities,
  not a fixed list of reference projects or four samples.
- **Form:** keep the browsing query, returned rows and scroll position underneath
  one focused form layer. Show type and Chinese/English names first; optional
  industry and keywords can expand in place. Back returns to browsing. Dismissing
  a changed form requires an explicit keep-editing/discard choice.
- **Review:** after field validation, show the exact business domain, type,
  names and optional supplied details before the final confirmed write. Editing
  a field invalidates any prior confirmation for a different payload. Raw
  identifiers, tokens, hashes and Permission jargon stay out of the main flow.
- **Result:** only a validated server response produces “已添加” or “已在目录中”.
  Show the returned object's real name with “查看该对象” and “继续浏览”. Creation
  leaves GLOBAL/FOCUS unchanged. Viewing invokes existing `selectContext()` and
  waits for the exact returned context before the shell changes its view.
- **Copy:** the chooser explains “选择只切换查看范围，不会启动采集”. Registration
  explains that adding to the directory does not establish data coverage.
  It never triggers acquisition, AUTO, external publication or a model call.

### 11.3 Existing payload and identity contract

| Field / result | Current source contract | UI handling |
| --- | --- | --- |
| `domain_id` | `CTH` or `BMP` | Explicit current business use; never silently substitute BMP. |
| `subject_type` | `brand` or `company` | Label with the existing business type names. |
| `name_zh`, `name_en` | Both required, each at most 160 characters | Trim and validate; do not generate an identity or translate a name silently. |
| `industry` | Optional, at most 120 characters | Preserve supplied text. |
| `keywords` | Optional list or comma-separated text; at most 50 normalized unique entries, each at most 80 characters | Client convenience validation only; server remains authoritative. |
| New object | HTTP 201, `ok: true`, `created: true`, `selection_only: true`, `subject` | Validate domain/type/identity and safe text before presenting success. |
| Existing identity | HTTP 200, `ok: true`, `created: false`, `duplicate: true`, `selection_only: true`, `subject` | Reuse the returned object without overwriting it or claiming a new record. |
| Stable identity | Server derives `subject_id`; BMP additionally has `brand_focus_id` | Never derive either identifier in the frontend. |

The server's normalized bilingual-name/type/domain identity controls idempotence.
A user retry cannot create a client-local replacement record. Distinct names are
not merged merely because a similar display label already appears in the list.
Country/relationship assertions and collected-data maturity are not form fields
without their own existing source contract.

### 11.4 States, recovery and accessibility

| State | Required behavior |
| --- | --- |
| Invalid field | Explain beside the affected field; keep every other value and focus the first issue. No request. |
| Confirmation pending | Show the named operation and retain input; duplicate submit, payload changes and conflicting scope actions are disabled. |
| Declined / expired confirmation | No success claim; return to the same values, obtain a fresh exact confirmation when supported. |
| Denied / unavailable | Show a business-level failure with retry/return; preserve values and prior focus. No login or access-request diversion. |
| Timeout / connection loss after submit | Say the result is not yet confirmed; refresh the existing directory to reconcile the stable returned identity. No automatic second mutation. Explicit retry follows server idempotence and confirmation rules. |
| Created / duplicate | Show the matching returned object. Refresh the directory through its existing read owner; failed refresh must not erase an already confirmed result. |
| Focus fails after creation | Retain the confirmed object and previous view; allow retrying selection or returning to browsing. Never report that creation itself failed. |

Wide Web/Desktop retain one bounded picker with a focused form/result region.
Mobile uses one active layer with persistent Return and action controls, safe
keyboard insets and scrollable fields. Search state survives return; no desktop
form appended beneath a long list. Verify 320/390 px and 200% text in Chinese,
English and Korean, 48 px touch targets, keyboard order, focus return and
reduced motion. Public Website acquires no form or new runtime.

### 11.5 REAL USER WORK E2E and delivery card

- `REAL INPUT`: user-authorized real Subject/BrandFocus details; no fixture
  promoted to production registry. Persistence tests use an explicit isolated DB.
- `END-TO-END PATH`: existing picker → form → exact write confirmation → existing
  registry POST → server result → optional confirmed focus → downstream CTH/BMP
  read → clear focus and return to GLOBAL.
- `USER-VISIBLE RESULT`: the real object can be found again; duplicate submission
  returns the same identity. Uncollected content remains explicitly uncollected.
- `FAILURE/RECOVERY`: invalid fields, cancellation, expired confirmation, denial,
  offline, unknown write completion and failed post-create focus as above.
- `EVIDENCE`: exact reviewed source/contract, current-snapshot tests, server
  confirmation/result, registry reread, selected-context read and no-collection
  assertion. Desktop build and browser screenshots alone do not prove native
  operation or a production write.
- `ACCEPTANCE ASSERTION`: `BLOCKED_PENDING_EXACT_WRITE_CONTRACT_AND_REAL_E2E`.
- `GLOBAL UNIVERSE / DATA MATURITY IMPACT`: extends the existing directory while
  retaining GLOBAL by default. No change to Global Commercial Coverage, Global
  Brand Coverage or Guangzhou Taikoo Hui Reference Coverage is asserted. The
  named reference is a retained acceptance dimension, never a selected-subject
  default, account selector or limit on the global directory.
- `RANDOM ENTITY DATA ACCEPTANCE`: no registration sample run in this design
  step; sample count 0. Later tests must include real non-reference CTH and BMP
  objects without treating registration as collected coverage.
- `COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO`; no release acceptance.

### 11.6 CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

Accessed 2026-09-30: official Flutter
[Form](https://api.flutter.dev/flutter/widgets/Form-class.html) and
[TextFormField](https://api.flutter.dev/flutter/material/TextFormField-class.html)
documentation, mapped to the installed Flutter 3.47.5 SDK. The APIs support
grouped field validation and explicit controller lifetime in scrollable forms.
**ADAPT** these existing BSD-3-Clause, upstream-maintained primitives; no new
dependency, copied layout, external service, data transmission or design system.
The exact capability locator found no separate historical research for this
registration slice. Current registry validation and the Experience Constitution
remain the implementation inputs. Actual write confirmation and native return
behavior still require their owner/runtime evidence.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 查看当前GLOBAL_ALL或明确选择一个可访问Subject视角。
- **屏幕专属呈现：** 列表、当前视角和确认预览并置；说明选择不授予业务读取权限
- **来源、范围与版本连续性：** 只有服务端确认的scope envelope传递给下游，切换后回原工作
- **四端差异：** Web/Desktop提供目录与预览；Mobile逐项选择；官网不展示私有目录
- **失败与恢复：** 拒绝/目录错误保留原scope与草稿，不本地切换
- **补充验收：** 无选择为GLOBAL_ALL；合法FOCUS服务器确认；拒绝无业务读取。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
