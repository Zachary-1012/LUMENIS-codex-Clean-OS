# CTH-03 — 实时监测

```yaml
screen_id: CTH-03
status: BLOCKED
revision: 3
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-009
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
presentation_design_decision: DESIGN_READY_BOUNDED_READABLE_SOURCE_TIME
artifact_disposition: NON_AUTHORITATIVE_EXPLORATION_ONLY
reviewer: Codex delegated ROUND-10 bounded source review
reviewed_at: 2026-09-30
approval_reference: published read-scope slice 3d6e0924dd883a23616ba2f63a01962e10b76e1e; bounded presentation review in section 11; Product Owner-approved D1–D5 SourceTarget direction 2026-10-06; this is not implementation, full-screen or round acceptance
```

## 0. Authority basis and artifact disposition

- The governing experience row is the CTH-03 real-time monitoring blueprint in `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`.
- The delivery overlay requires a real new event and honest separation of live, empty, not-collected and failed collection states before ROUND 10 can pass.
- The binding inputs are `contracts/experience/screen_meta.json`, `contracts/experience/viewmodels/VIEWMODEL_REGISTRY.json`, `contracts/experience/unknown-bindings.json`, `contracts/experience/screens/CTH-03/CTH-03.actions.json` and the current `experience_screens._build_cth03()` source. Fixture and sketch files are exploration evidence only.
- This specification is not a generic dashboard: the update rhythm is organized as pulse → source lanes → prioritized stream. A repeated KPI/card renderer would fail the CTH-03 blueprint.
- Sol design decision: `BLOCKED`; implementation may expose a source-backed read-only shell but cannot claim live Subject monitoring or `DESIGN_READY`.

## 1. User problem and product invariant

- **User task:** a CTH operator needs to see what has recently changed, which returned source lanes are available, and inspect one returned signal without losing the current range.
- **Context:** the screen accepts the Product Core context returned by `LumenisCoreClient.settingsContext()`: `GLOBAL_ALL`, or `FOCUS` with `domain_id=CTH` and a non-empty Subject. The global view means the returned global scope; it is not a license to show focused data.
- **Completion signal for this slice:** returned pulse metrics, source-lane status, and returned stream fields are visible with their returned state. A missing source-level freshness or Subject authorization remains visible as a limitation.
- **Invariant:** CTH remains Subject-first. The route, `bound=true` and a returned list do not prove actor-to-Subject authorization or Evidence lineage.
- **Out of scope for this bounded read slice:** starting/stopping a collector, pinning an event, exporting, classifying, creating a Case, controlled Evidence capture or any external write. Product Owner has approved user-gesture **Open Original** as the required source-trace target; it remains disabled until the shared SourceTarget, launcher and Return contracts are bound and tested.

## 2. Route, entry, exit and return

- **Entry:** `Cth03Screen(client: ...)` after the existing CTH shell selects the monitoring workflow; this batch adds no route or second navigation owner.
- **Read sequence:** `settingsContext()` is read first, then `screen('CTH-03')` through the existing scoped Core client. The published read slice accepts `lumenis.scope-read-binding.v1` for `commercial_realtime_stream`: `local-workspace-read-v1` or `actor-exact-scope-v1`, with exact CTH product/domain, applied/read-allowed/verified scope and exact GLOBAL or Subject match. A page read decision is not row Evidence. Every displayed row separately needs the verified v2 projection, stored Subject and Evidence integrity; metrics and source lanes need their own projections. Unknown policies, contracts or mismatched scope fail closed.
- **Current source:** `experience_screens._build_cth03()` reads `canonical_data.list_scoped_canonical()` with the selected Subject or GLOBAL. It returns scope-verified records, their publication time and source platform, while `coverage=NOT_VERIFIED` and `source_freshness=UNKNOWN` remain explicit. Recent-window and negative counts remain unavailable. The published 2026-09-29 read acceptance covered GLOBAL, Guangzhou Taikoo Hui and Shenzhen MixC Luohu, clear-to-GLOBAL, offline clearing and retry recovery. It did not accept live monitoring, source freshness, collector actions or a whole native surface.
- **Exit / return:** selecting a local source lane filters the mounted stream; clearing it returns to all returned records. The selection is presentation state only and preserves the context label. For an eligible row, `Trace → Open Original` opens the actual authorized page in product-internal SYS-06 by default; the user may separately choose an external browser. Return restores the same scope, lane filter, row selection and scroll position. No server mutation, collection or Evidence capture is implied.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source/ViewModel field or callable | Definition / units / window | Freshness and missing-data behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Current scope label | SYSTEM context read | `LumenisCoreClient.settingsContext()` → `context.mode`, `domain_id`, `subject_id`, `display_name` | `GLOBAL_ALL` or focused CTH context only | Missing or mismatched context blocks the screen; Subject IDs are never rendered | — | Current client and context contract |
| P1 | Recent and negative pulse | CTH read builder | `_build_cth03()` `kpis.items[id,value,state]` for `cth03.recent` and `cth03.negative` | Returned record counts; no inferred rate or trend | Current builder returns no verified numeric value; `empty`, `notcollected`, `offline` and unknown remain distinct | BACKEND-GAP-009 | Current source mapping; metric-level analysis/projection not verified |
| P1 | Source lanes | CTH read builder | `_build_cth03()` `platforms.items[platform,status,schedule/detail]` | Returned lane availability/status text | A missing lane is not “healthy”; no collector action is inferred | BACKEND-GAP-009 | Current source mapping |
| P1 | Prioritized stream | CTH read builder | `_build_cth03()` `table.rows[date,title,platform,sentiment,risk]` | Returned business fields only | A row is displayed only with explicit matching scope, read permission, verified Evidence lineage and a trace/evidence reference; otherwise it is withheld | BACKEND-GAP-009 | Published v2 row projection and writer-authenticated integrity check; sentiment/risk are not verified |
| P1 TARGET | SourceTarget / Open Original | CTH row + Shared Evidence contract; F/C6 consumer | `table.rows[].source_url` plus row `projection`; approved shape `lumenis.source-target/v1` | Open the actual same-row authorized page in product-internal SYS-06 by default; external browser only by separate explicit user choice | Missing/invalid/denied/unsupported/load/launch failure remain explicit; an internal launch is not acceptance until the actual page/session state is observed | BACKEND-GAP-009 | Historical implementation snapshot recorded with the 2026-10-06 SourceTarget review: backend field existed; current Flutter DTO drops SourceTarget; launcher/Return were unbound. This dated marker is not a claim about current source; retain current binding/acceptance status from fresh evidence |
| BLOCKED | Live pulse/freshness clock and collector health action | CTH/SYSTEM owners unresolved | ViewModel declares `realtime_series` and `collectors`; no verified endpoint or action contract | No verified source-level freshness, realtime series, health command or Permission | Do not label response generation time as source freshness; show unavailable copy where needed | BACKEND-GAP-009 | `collector_v2/realtime` and health action remain UNKNOWN |

The current App adapter uses only the shared `LumenisCoreClient`; it adds no API, database, Evidence, collector or localization owner. Pagination, cancellation, source-level freshness and collector actions remain unverified. Subject-scoped reads are accepted only by the exact current server/row contracts above. The adapter never invents local Permission or lineage defaults: a response without its valid server binding is blocked, and an untraceable row is withheld.

## 4. State and recovery matrix

| State | Trigger/evidence | User-visible meaning | Available actions | Recovery/return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Context or CTH-03 request pending | 正在读取实时监测 | None | Announce loading; do not reveal stale fixture data | CTH03-W-001 |
| Empty / no source data | `table.state=empty` and no rows | 当前范围内暂无实时记录 | Refresh | Keep pulse/lane states separate; never create zero rows | CTH03-W-002 |
| Not collected | A KPI or lane returns `notcollected` | 尚未采集 | None | Keep it distinct from an empty stream | CTH03-W-003 |
| Fresh / live | Source freshness contract | UNKNOWN in current binding | None | Do not claim “实时” beyond returned business copy | CTH03-W-004 |
| Stale | Source stale state | 暂不确定数据是否仍新鲜 | Refresh | Requires source state before a stale badge is accepted | CTH03-W-004 |
| Partial | Some lanes/metrics returned while another section is unavailable | 部分监测信息可用 | Refresh | Keep each section's state local | CTH03-W-002 |
| Offline | Core connectivity failure or section `offline` | 暂时无法连接 | Retry | Do not convert failure to zero or empty | CTH03-W-005 |
| Blocked / permission denied | Invalid context, `bound=false`, missing global grant/binding, or focused response without exact authorized binding; 401/403 | 经营主体信息暂不可用 | Retry after context/access recovery | Never reuse the global stream for a focused view; never display an untraceable row | CTH03-W-006 |
| Error | Malformed response or other server failure | 运营信息暂不可用 | Retry | Hide raw server details | CTH03-W-005 |

## 5. Purpose-built desktop composition

- **Primary question:** what has changed in the current CTH scope, and which returned lane needs attention?
- **Hierarchy:** scope and read time → pulse band → source lanes → prioritized stream. The stream remains the dominant surface; lanes explain availability rather than becoming a control dashboard.
- **Wide desktop:** `cth03/desktop-layout` places a pulse band above independent channel lanes and the stream. A local lane selection filters only the visible list and has a visible selected state.
- **Keyboard:** lanes are focusable controls; Enter/Space applies the local filter; Escape clears it. Stream rows expose title, date, channel, sentiment and risk in text and do not expose internal IDs.
- **Screen identity:** freshness/connection state and lane-to-stream relationship define the composition. It is not a generic four-card grid.

## 5A. Web Workspace composition and desktop-only capability boundary

- Web Workspace and desktop use the same Core client, ViewModel states and read-only scope semantics. No browser-only collector action is introduced.
- Pointer and keyboard filtering must leave the current scope visible. The approved source destination/lineage contract is `contracts/experience/source-target-contract-v1.json`; until the typed DTO, public-HTTPS validator, platform launcher and Return state are bound, the control remains disabled and the lane/stream remains readable.
- There is no desktop-only completion claim. Runtime/browser E2E is required before accepting the page.

## 6. Purpose-built mobile composition

- **Active task:** keep the scope label, pulse state and one filtered stream readable on a single vertical surface.
- **Layout:** at narrow widths, pulse → lane selector → stream. The selected lane can be cleared without navigation and the stream's empty state remains adjacent to the filter.
- **Touch:** lane chips and retry controls are at least 48 logical pixels high; risk and sentiment use text, not color alone.
- **Interruption:** no local business cache or pending action is represented. Retry re-reads context and the screen.
- **Screen identity:** the mobile surface preserves the lane-to-stream monitoring rhythm instead of collapsing into repeated cards.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read/write/external effect | Idempotency / reversal | Evidence emitted | Confirmation and failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Load context and stream | SYSTEM context + CTH read builder; exact server scope binding from §2 | Existing local-workspace or actor-exact-scope READ policy | Read only | N/A | Returned Canonical row projection/Evidence; no new Evidence write | Render verified rows or honest blocked/error state; no account wall |
| Filter/clear source lane | Flutter local presentation state | None | No server effect | Reversible immediately | None | Local selection is enabled |
| Refresh | Existing Core read | Same as load | Read only | Repeatable | New response only | Retry; no optimistic values |
| Open Original | CTH row read + Shared SourceTarget; exact current row scope/Evidence; F/C6 launcher | Reuse current row READ; no write/effect permission | By default open and show the actual public HTTPS page inside product SYS-06; external browser only after a separate explicit user choice; no collection/capture/login/write | Repeatable; Return restores route/context/filter/selection/scroll | No new Evidence; retain existing source/canonical/Evidence refs and opening state | Disabled until `lumenis.source-target/v1` and platform launcher are bound; preserve honest URL, page-load and launch-failure states |
| Pause/resume, pin, health action, controlled capture | Collector/SYSTEM/SYS-06 owner/callable/Permission/effect/Trace UNKNOWN | UNKNOWN | UNKNOWN or consequential | UNKNOWN | UNKNOWN | No enabled control |

## 8. Accessibility, motion and localization

- Tab order is scope → pulse text → lane controls → stream records → retry. Focus remains visible and filter selection is announced.
- Loading, blocked, empty and error states use live-region semantics. Sentiment/risk are written as labels and are never color-only.
- The stream is the non-visual equivalent of any future pulse chart. No canvas is drawn for the unresolved realtime series.
- No authored motion is required; reduced motion produces the same immediate state changes.
- The current UI reuses `screen.CTH-03`, context, common, state and `cth01.*` keys. §11 replaces misleading generic mappings with scoped `cth03.*` copy in the existing zh-CN/en/ko deltas and generated `LumenisLocalizations`; it creates no second localization owner.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State/error path | Platform/input | Test layer | Current evidence/reference |
| --- | --- | --- | --- | --- | --- |
| CTH03-W-001 | Start the screen with a pending read; loading is announced and returned stream text is hidden until completion | Loading | Widget; desktop/mobile | Widget: `app/test/features/cth/cth03/cth03_screen_test.dart` | Published 3d6e read-slice tests; each later source snapshot needs its own regression |
| CTH03-W-002 | Render source-backed pulse, lanes and stream with internal IDs absent | Ready/partial/empty | Widget; desktop 1440 and mobile 390 | Widget + browser | 3d6e read-slice acceptance: 91 GLOBAL rows, 27 Guangzhou Taikoo Hui, 4 Shenzhen MixC Luohu; partial state retained; metric/health completion not claimed |
| CTH03-W-003 | Return not-collected values | Not collected | Widget | Widget test required before promotion | Current parser preserves state |
| CTH03-W-004 | Verify live/stale claims are not inferred from `generated_at` | Fresh/stale unknown | Widget/API | Contract + widget | Source freshness remains UNKNOWN; §11 fixes the ambiguous read-time and historical-record copy before separate presentation acceptance |
| CTH03-W-005 | Return offline, malformed and 5xx failure | Offline/error | Widget + browser | Widget + actual tab-network failure/retry | 3d6e acceptance verified old rows clear while offline and return only after explicit successful retry |
| CTH03-W-006 | Return focused CTH context without `focus_binding.applied` | Blocked focus | Widget/repository | Widget + repository test | Invalid binding remains blocked; valid current FOCUS binding separately verified under §2 |
| CTH03-W-007 | Resize 1440 → 1024 → 390 and operate lane filter with keyboard/touch | Responsive/accessibility | Widget; pointer, keyboard, touch | Widget + browser | Actual 1440/390 scope-read interaction recorded for 3d6e; full breakpoint/filter and native surface acceptance remain separate |
| CTH03-W-008 | Return `bound=true` with records but no server global grant/lineage; the repository blocks and shows no aggregate or record | Global authorization/lineage block | Repository/widget | Repository test | Implemented hostile fixture |
| CTH03-W-009 | Return authorized `GLOBAL_ALL` and exact Guangzhou Taikoo Hui `FOCUS`; only the matching scope is decoded | Authorized global/focus read | Repository + browser | Repository test + actual scoped read | 3d6e verified GLOBAL → Guangzhou Taikoo Hui → Shenzhen MixC Luohu → clear-to-GLOBAL; no production write or coverage claim |

| CTH03-W-010 | From one authorized LUMENIS-composed row, open the actual page in product-internal SYS-06 by default, observe its real state, then Return to the same scope/lane/selection/scroll; external browser is a separate explicit choice | URL missing/invalid/denied/unsupported/page-load/launch failure/Return recovery | Web Workspace, Windows/macOS Desktop, iOS Mobile; browser coverage on other OS is separate | Contract + widget + platform integration + runtime E2E | Current native targets; historical marker: current Flutter DTO drops SourceTarget (2026-10-06 SourceTarget snapshot, not a current-source assertion); current binding/page/Return acceptance remains governed by fresh evidence |

## 10. Review decision and open questions

- **Decision:** the full live-monitoring design, J1 and ROUND-10 remain `BLOCKED`. The published read/scope/recovery slice and the bounded presentation review below do not close those gates.
- **Open owners:** C1/Collector must define and demonstrate realtime/health/freshness and native continuation; C3 must establish recent-window/business-analysis contracts; C5/F/C6 must bind SourceTarget mode selection, internal SYS-06 / explicit external handoff and Return. Per-Subject read scope and row lineage now use the published contracts in §2; their existence does not prove the wider business task or original-page availability.
- **Required before full acceptance:** a real new event through Source → Event → Evidence → monitoring UI; live/freshness semantics; negative/offline/not-collected separation; and applicable Web/Desktop/Mobile E2E. Preserve the historical acceptance rows above as the original gate record; §11 records the newer narrow review and evidence scope.

## 11. Bounded read-presentation review — 2026-09-30

### 11.1 Current task and boundary

The operator opens the already-bound monitoring read view, selects a source or
Subject and needs to understand where a returned record came from and when it
was published. The current UI exposes `public_http`, `douyin` and raw date/time
strings, and reuses a "latest changes" heading for records that may be historical.
These are presentation defects within the existing read task. This review keeps
the current route, scope selection, pulse/source/stream anatomy and recovery
actions. It introduces no new action, data, freshness assertion, owner or design
system. It creates no account, login or permission-management UI.

### 11.2 Source-backed fields and copy

| Existing field | Presentation decision | Semantic boundary |
| --- | --- | --- |
| `table.rows[].platform` / channel `name` | Resolve known `public_http` and `douyin` identifiers to localized human-readable source names. Filtering continues to use the original identity. | Unknown technical identifiers have an honest unknown-source label; never rename one source to another. |
| `table.rows[].date` | Label as source publication time: `_build_cth03()` maps it from Canonical `publish_datetime`. Show readable dates without inventing missing precision or a timezone. | A date-only value remains date-only. An explicit offset is preserved or explicitly displayed; no implicit local conversion. Invalid or absent values are unavailable, never now/zero/fresh. |
| Response `generated_at` | Label as page read time. | This is neither source publication/capture time nor source freshness. Absence does not by itself prove stale source data. |
| Stream and header copy | Use neutral collected/returned-record language and explain the current scope. | Old source records must not be described as newly occurring events or current complete coverage. |
| State and metric values | Keep PARTIAL, unavailable and not-collected labels and existing values unchanged. | Scope-read acceptance does not establish monitoring-window, sentiment, risk or collector-health truth. |

Copy belongs to the existing three locale deltas and generated
`LumenisLocalizations` output. The `copy-registry.json` counts must match the
actual final deltas; it is a derived count update, not a second copy source.

**Research / ADAPT:** [Dart 3.13.4 DateTime.parse documentation](https://api.dart.dev/dart-core/DateTime/parse.html),
accessed 2026-09-30, matches the installed SDK. The documented parser normalizes
overflowing components and converts explicit offsets to UTC. Therefore successful
parsing alone must not authorize a displayed publication date: validate the
original calendar/time components and preserve original precision and offset.
Use the existing SDK and localization owner; no new dependency or source-data
normalizer is introduced. Documentation is CC BY 4.0 and sample code BSD-3-Clause;
this change adopts the documented behavior, without vendoring sample code.

### 11.3 Surfaces, accessibility and effects

| Surface | Bounded behavior | Required proof / limit |
| --- | --- | --- |
| Public Website | No website change or monitoring availability claim. | Not an editing or monitoring entry in this slice. |
| Web Workspace | Keep existing source lanes and record stream; readable source and distinct time labels in visible text and semantics. | Actual scope/read/retry at the rebuilt snapshot. Source filtering is live-verifiable only when verified lane projections are returned. |
| Desktop App | Same existing read composition and Core contracts; longer localized labels wrap. | Current Windows build; native interaction remains a separate claim until inspected. |
| Mobile Companion | Keep the existing source selector and readable record stream, with wrapping metadata and unchanged touch actions. | 390 logical pixels and 200% text; actual browser mobile-layout interaction is not native Android/iOS proof. |

There is no new animation or external effect. Existing keyboard/touch filtering
must use the original source key and preserve current context. Accessible labels
use the same localized platform and time meaning as visible labels. No shortened
date may silently remove an explicit offset or add hours to a date-only source.

### 11.4 Executable acceptance and decision

- **CTH03-PRESENT-01:** `public_http`/`douyin` are human-readable in rows, source
  selection and semantic labels; filtering still selects the exact source key.
- **CTH03-PRESENT-02:** historical, date-only, offset-bearing, invalid and missing
  publication values retain their actual meaning. `generated_at` is labelled
  only as page read time and never creates a live/fresh/stale-source assertion.
- **CTH03-PRESENT-03:** Chinese, English and Korean preserve these distinctions;
  a narrow viewport with 200% text has no clipped record metadata or overflow.
- **CTH03-PRESENT-04:** current CTH03, localization, launch and Shell regression,
  the three Experience audits and constitution gate must pass after final edits.
  Inspect the actual rebuilt UI with real returned records and scope changes.
  The 2026-09-30 live response has no verified lane projections; preserve that
  unavailable state and report live source filtering as `LIVE_NOT_VERIFIED`.
  Widget filtering assertions verify identity preservation, not live lane health.
  Keep current source/time unknowns visible.
- **Review decision:** the primary controller approved this exact bounded
  presentation contract on 2026-09-30 under the existing source-backed UX Batch.
  `DESIGN_READY_BOUNDED_READABLE_SOURCE_TIME` authorizes only §11's changes.
  The whole-screen decision above remains `BLOCKED`, regardless of this smaller
  maintenance acceptance.

## 12. Approved SourceTarget / Open Original integration — 2026-10-06

Product Owner approval fixes the product meaning without promoting implementation status:

```text
platform-native row → Source/Evidence/Canonical
→ LUMENIS monitoring composition
→ Trace → Open Original → actual page in product-internal SYS-06 by default (explicit external-browser choice)
→ Return to exact CTH-03 context
```

The source control consumes `lumenis.source-target/v1`; it never renders a copied platform feed, reads cookies, silently authenticates, launches collection or invokes SYS-06 capture. Backend `source_url` presence is only one field. The default internal path must display the actual authorized page and its real SYS-06 page/session/action state; user-gesture external opening is a separate optional mode. Full acceptance requires same-row projection/Evidence, allowed HTTPS validation, typed Flutter DTO, internal-page observation, per-platform behavior, honest load/failure states, three-language/accessibility behavior, Return restoration and runtime E2E. An external `HANDOFF_ACCEPTED` means only that the explicitly chosen browser accepted the handoff; it is not default acceptance or proof of page load. Until then the action remains `CODEX_BINDING_REQUIRED` and the whole screen remains `BLOCKED` for live-monitoring acceptance.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 查看监测变化、平台lane并阅读一条信号。
- **屏幕专属呈现：** 时间窗脉冲+Collector lane+单条reader；平台热度与自有样本分开
- **来源、范围与版本连续性：** 原始platform ID、发布时间、采集时间、scope、Evidence进入Research
- **四端差异：** Web/Desktop流与lane检视；Mobile先变化后单条；官网只讲已验证采集
- **失败与恢复：** 验证码/登录墙/限流仅阻断对应lane；保持原帖定位
- **补充验收：** 允许时打开原文并返回同信号；无授权不得起采集/导出。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。保留序境二维手绘水彩/版画色彩语言与有功能含义的线性控件；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，只借鉴手绘平面笔触与色彩，不复制参考人物、不用3D质感。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。

## Topic/time and truthful missing dimensions — 2026-10-08

Follow Global §10 and Experience §38's latest correction. Collection is subject/topic/task driven with no universal start date; explicit task dates still apply. Distinguish publication/event/capture time, group unknown dates honestly, and preserve precision/timezone. Required dimension definitions remain visible even without values: display “—” with accessible reason/state/last verified time, never zero-fill, hide required columns or invent chart continuity. Real zero remains zero. A source limitation requires actual collection-chain evidence; missing code, skipped execution, parsing failure or expired authorization stays an owner defect/blocker. No requirement for every data value to be obtainable, no automatic acceptance of collector capability. C1/C6 still need to migrate the pinned old date literal; this specification does not activate them or promote design/runtime acceptance.


### 2026-10-08 SourceTarget mode correction

The current approved source-opening target is the actual authorized page inside SYS-06 by default on operational surfaces, with a separate explicit external-browser choice. SourceTarget v1 owns the required mode resolution; old external-only call sites must migrate, never silently fall back or infer consent from a stored mode. Earlier handoff-only acceptance covers the explicitly chosen external option only. Internal reading requires the authorized session and fresh matching page observation; neither launch acceptance nor a screen file proves page readability. Preserve the exact same-row lineage, READ scope, no collection/capture/write side effects and Return context. These are required targets, not a promotion of this screen's existing implementation/design/runtime state.
