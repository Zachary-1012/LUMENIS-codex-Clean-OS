# CTH-03 — 实时监测

```yaml
screen_id: CTH-03
status: BLOCKED
revision: 1
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-009
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: NON_AUTHORITATIVE_EXPLORATION_ONLY
reviewer: Codex delegated ROUND-10 bounded source review
reviewed_at: 2026-09-22
approval_reference: source baseline origin/main 5ba1aefc53a1babc293e990c23c62f841724c843; this is not per-screen acceptance
```

## 0. Authority basis and artifact disposition

- The governing experience row is the CTH-03 real-time monitoring blueprint in `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`.
- The delivery overlay requires a real new event and honest separation of live, empty, not-collected and failed collection states before ROUND 10 can pass.
- The binding inputs are `contracts/experience/screen_meta.json`, `contracts/experience/viewmodels/VIEWMODEL_REGISTRY.json`, `contracts/experience/unknown-bindings.json`, `contracts/experience/actions/CTH-03.actions.json` and the current `experience_screens._build_cth03()` source. Fixture and sketch files are exploration evidence only.
- This specification is not a generic dashboard: the update rhythm is organized as pulse → source lanes → prioritized stream. A repeated KPI/card renderer would fail the CTH-03 blueprint.
- Sol design decision: `BLOCKED`; implementation may expose a source-backed read-only shell but cannot claim live Subject monitoring or `DESIGN_READY`.

## 1. User problem and product invariant

- **User task:** a CTH operator needs to see what has recently changed, which returned source lanes are available, and inspect one returned signal without losing the current range.
- **Context:** the screen accepts the Product Core context returned by `LumenisCoreClient.settingsContext()`: `GLOBAL_ALL`, or `FOCUS` with `domain_id=CTH` and a non-empty Subject. The global view means the returned global scope; it is not a license to show focused data.
- **Completion signal for this slice:** returned pulse metrics, source-lane status, and returned stream fields are visible with their returned state. A missing source-level freshness or Subject authorization remains visible as a limitation.
- **Invariant:** CTH remains Subject-first. The route, `bound=true` and a returned list do not prove actor-to-Subject authorization or Evidence lineage.
- **Out of scope:** starting/stopping a collector, pinning an event, opening source evidence, exporting, classifying, creating a Case, or any external effect. No button is shown for an action without a verified callable, Permission result, effect fence and Trace.

## 2. Route, entry, exit and return

- **Entry:** `Cth03Screen(client: ...)` after the existing CTH shell selects the monitoring workflow; this batch adds no route or second navigation owner.
- **Read sequence:** `settingsContext()` is read first, then `screen('CTH-03')`. The screen request has no verified focus parameter. For `GLOBAL_ALL`, the repository requires a server `global_binding` (or the current canonical equivalent) with `applied`, explicit global grant/scope, CTH product/domain, `scope_verified`, `read_allowed` and verified Evidence lineage. For `FOCUS`, it additionally requires `focus_binding.applied`, exact Subject equality, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage; otherwise it blocks rather than reusing a global aggregate.
- **Current source:** `experience_screens._build_cth03()` currently reads verified notes/negative comments and returns `kpis`, `platforms` and `table` sections. The current runtime focus allowlist covers CTH-01 and BMP-01, not CTH-03, so focused acceptance is blocked.
- **Exit / return:** selecting a local source lane filters the mounted stream; clearing it returns to all returned records. The selection is presentation state only and preserves the context label. No deep-link or server mutation is introduced.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source/ViewModel field or callable | Definition / units / window | Freshness and missing-data behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Current scope label | SYSTEM context read | `LumenisCoreClient.settingsContext()` → `context.mode`, `domain_id`, `subject_id`, `display_name` | `GLOBAL_ALL` or focused CTH context only | Missing or mismatched context blocks the screen; Subject IDs are never rendered | — | Current client and context contract |
| P1 | Recent and negative pulse | CTH read builder | `_build_cth03()` `kpis.items[id,value,state]` for `cth03.recent` and `cth03.negative` | Returned record counts; no inferred rate or trend | `ready` with a numeric value only; `empty`, `notcollected`, `offline` and unknown remain distinct | BACKEND-GAP-009 | Current source mapping; actor scope and lineage pending |
| P1 | Source lanes | CTH read builder | `_build_cth03()` `platforms.items[platform,status,schedule/detail]` | Returned lane availability/status text | A missing lane is not “healthy”; no collector action is inferred | BACKEND-GAP-009 | Current source mapping |
| P1 | Prioritized stream | CTH read builder | `_build_cth03()` `table.rows[date,title,platform,sentiment,risk]` | Returned business fields only | A row is displayed only with explicit matching scope, read permission, verified Evidence lineage and a trace/evidence reference; otherwise it is withheld | BACKEND-GAP-009 | Current source mapping; source lineage pending |
| BLOCKED | Live pulse/freshness clock and collector health action | CTH/SYSTEM owners unresolved | ViewModel declares `realtime_series` and `collectors`; no verified endpoint or action contract | No verified source-level freshness, realtime series, health command or Permission | Do not label response generation time as source freshness; show unavailable copy where needed | BACKEND-GAP-009 | `collector_v2/realtime` and health action remain UNKNOWN |

The current App adapter uses only the shared `LumenisCoreClient`; it adds no API, database, Evidence, collector or localization owner. Pagination, cancellation, source-level freshness and per-Subject authorization are not part of the verified current callable. The adapter never invents local Permission or lineage defaults: a global aggregate without the server binding is blocked, and an untraceable row is withheld.

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
- Pointer and keyboard filtering must leave the current scope visible. A future source/evidence open action requires an approved destination and lineage contract; until then the lane/stream remains read-only.
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
| Load context and stream | SYSTEM context + CTH read builder; actor/Subject binding UNKNOWN | Optional global auth only; no verified screen READ decision | Read only | N/A | Returned response only; no lineage claim | Render safe fields or honest blocked/error state |
| Filter/clear source lane | Flutter local presentation state | None | No server effect | Reversible immediately | None | Local selection is enabled |
| Refresh | Existing Core read | Same as load | Read only | Repeatable | New response only | Retry; no optimistic values |
| Pause/resume, pin, open source evidence, health action | Owner/callable/Permission/effect/Trace UNKNOWN | UNKNOWN | UNKNOWN or consequential | UNKNOWN | UNKNOWN | No enabled control |

## 8. Accessibility, motion and localization

- Tab order is scope → pulse text → lane controls → stream records → retry. Focus remains visible and filter selection is announced.
- Loading, blocked, empty and error states use live-region semantics. Sentiment/risk are written as labels and are never color-only.
- The stream is the non-visual equivalent of any future pulse chart. No canvas is drawn for the unresolved realtime series.
- No authored motion is required; reduced motion produces the same immediate state changes.
- The bounded UI uses existing `screen.CTH-03`, context, common, state and `cth01.*` keys; it does not add a local copy owner. Before acceptance, the canonical `LumenisLocalizations` owner must add and review the pending `cth03.pulse`, `cth03.channel_status`, `cth03.stream_state`, `cth03.scope_gap` and `cth03.action_unavailable` copy in zh-CN/en/ko, then replace the temporary generic mappings. This spec creates no second l10n owner.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State/error path | Platform/input | Test layer | Current evidence/reference |
| --- | --- | --- | --- | --- | --- |
| CTH03-W-001 | Start the screen with a pending read; loading is announced and returned stream text is hidden until completion | Loading | Widget; desktop/mobile | Widget: `app/test/features/cth/cth03/cth03_screen_test.dart` | Local implementation evidence; runtime pending |
| CTH03-W-002 | Render source-backed pulse, lanes and stream with internal IDs absent | Ready/partial/empty | Widget; desktop 1440 and mobile 390 | Widget test | Current builder-shaped response; lineage pending |
| CTH03-W-003 | Return not-collected values | Not collected | Widget | Widget test required before promotion | Current parser preserves state |
| CTH03-W-004 | Verify live/stale claims are not inferred from `generated_at` | Fresh/stale unknown | Widget/API | Contract test required | Current backend lacks source freshness |
| CTH03-W-005 | Return offline, malformed and 5xx failure | Offline/error | Widget | Widget test required | Safe copy implemented |
| CTH03-W-006 | Return focused CTH context without `focus_binding.applied` | Blocked focus | Widget/repository | Widget + repository test | Current runtime does not bind CTH-03 focus |
| CTH03-W-007 | Resize 1440 → 1024 → 390 and operate lane filter with keyboard/touch | Responsive/accessibility | Widget; pointer, keyboard, touch | Widget test | Desktop/mobile anatomy implemented; runtime E2E pending |
| CTH03-W-008 | Return `bound=true` with records but no server global grant/lineage; the repository blocks and shows no aggregate or record | Global authorization/lineage block | Repository/widget | Repository test | Implemented hostile fixture |
| CTH03-W-009 | Return authorized `GLOBAL_ALL` and exact Guangzhou Taikoo Hui `FOCUS`; only the matching scope is decoded | Authorized global/focus read | Repository | Repository test | Implemented legal fixtures; live backend binding pending |

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for `DESIGN_READY`, Subject-scoped monitoring and ROUND-10 completion. The bounded implementation is read-only and source-honest for the current global response shape.
- **Open owners:** SYSTEM/Permission must bind actor-to-Subject read authorization; CTH/Evidence must return source lineage; Collector must define realtime/health/freshness contracts; canonical l10n must add the three locales; Sol must review the screen spec.
- **Required before acceptance:** a real new event through Source → Event → Evidence → monitoring UI; live/freshness semantics; focused binding; negative/offline/not-collected separation; and Web/Desktop/Mobile E2E.
