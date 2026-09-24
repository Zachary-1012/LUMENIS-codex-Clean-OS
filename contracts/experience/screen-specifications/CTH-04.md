# CTH-04 — 事件关系

```yaml
screen_id: CTH-04
status: BLOCKED
revision: 1
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-010
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: NON_AUTHORITATIVE_EXPLORATION_ONLY
reviewer: Codex delegated ROUND-10 bounded source review
reviewed_at: 2026-09-22
approval_reference: source baseline origin/main 5ba1aefc53a1babc293e990c23c62f841724c843; this is not per-screen acceptance
```

## 0. Authority basis and artifact disposition

- The governing experience row is the CTH-04 causal constellation paired with a time axis.
- The current source contract is `experience_screens._build_cth04()` and the shared `GET /api/experience/screen/CTH-04` envelope. The graph field is declared but the current builder returns curated events without verified relationship edges.
- Fixture/action JSON is a contract-gap record, not permission to invent graph edges or effectful actions. The implementation uses a timeline plus an explicit unavailable graph state until canonical edges exist.
- The composition is purpose-built: event timeline and relationship area remain synchronized in hierarchy; it is not a generic card list.
- Sol design decision: `BLOCKED`; no causal claim or Case navigation is accepted in this slice.

## 1. User problem and product invariant

- **User task:** understand the order of returned CTH events and inspect one event without mistaking chronology for causality.
- **Context:** use the same `settingsContext()` gate as CTH-03. `GLOBAL_ALL` is allowed only after a server `global_binding` (or current canonical equivalent) proves the global grant/scope, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage. `FOCUS` is allowed only after `focus_binding.applied` plus exact Subject, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage. Current backend responses without these fields are blocked.
- **Completion signal for this slice:** a returned event timeline can be selected and returned from locally; the relationship surface clearly says when graph edges are not returned.
- **Invariant:** an event row does not establish Evidence, a Case, causality, or actor authorization. `bound=true` is not authorization; unknown relationship and lineage data stays unknown.
- **Out of scope:** new event creation, linking a risk, navigation to a Case, opening Evidence, editing, notification, export and any other effect listed only in action metadata.

## 2. Route, entry, exit and return

- **Entry:** `Cth04Screen(client: ...)` from the existing CTH workspace; no new route/deep-link owner is added.
- **Read sequence:** `settingsContext()` → `screen('CTH-04')`. The current request is unparameterized. Focused data is rejected when the response does not prove an exact authorized focus binding; event rows additionally require explicit scope, read permission, verified Evidence lineage and a trace/evidence reference.
- **Verified response fields:** `events.items[title,date,time,desc,level,tags]`; the current `kpis` may report `cth04.graph` as `null/notcollected`. Internal event/evidence identifiers are dropped.
- **Exit / return:** selecting an event opens an inline inspection panel; `返回事件时间线` clears local selection and restores the timeline. No graph zoom, deep-link or Case position is persisted because no destination contract exists.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source/ViewModel field or callable | Definition / units / window | Freshness and missing-data behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Scope label | SYSTEM context read | `LumenisCoreClient.settingsContext()` | `GLOBAL_ALL` or applied focused CTH scope | Missing/mismatch blocks; IDs hidden | — | Current context contract |
| P1 | Event timeline | CTH read builder | `_build_cth04()` `events.items[title,date,time,desc,level,tags]` | Returned event fields; no total or causal score | Empty, not collected, offline and error remain distinct; rows without matching scope/lineage/trace are withheld | BACKEND-GAP-010 | Current source mapping; lineage pending |
| BLOCKED | Relationship constellation | CTH canonical event/Evidence relationship owner UNKNOWN | ViewModel `graph.nodes[]/edges[]`; current builder does not supply verified edges | No causal direction, case link or evidence anchor can be computed locally | Show graph unavailable; never derive edges from list order | BACKEND-GAP-010 | Current source says requested graph edges are not supplied |
| BLOCKED | Event → Evidence / Case trace | CTH/Evidence/Case owners unresolved | Action registry labels `to-case`, `link-risk`, but no verified App callback/request/result | UNKNOWN | No enabled action or raw identifier | BACKEND-GAP-010 | Permission/effect/Trace pending |

No new data owner is created. The App renders only the shared Core response, and no fixture is used as runtime fallback.

## 4. State and recovery matrix

| State | Trigger/evidence | User-visible meaning | Available actions | Recovery/return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Context/event request pending | 正在加载事件关系 | None | Announce; keep event details hidden | CTH04-W-001 |
| Empty / no events | `events.state=empty`, no items | 当前范围内暂无已返回事件 | Refresh | Keep graph unavailable separate from empty timeline | CTH04-W-002 |
| Not collected | Graph KPI/section is `notcollected` | 事件关系尚未返回 | None | Show timeline only; do not infer relations | CTH04-W-003 |
| Fresh / stale | No source timestamp/state contract | UNKNOWN | None | Do not label events live or stale | CTH04-W-004 |
| Partial | Timeline exists, graph missing | 事件时间线可用，关系信息暂缺 | Refresh | Selection/return remains local | CTH04-W-002 |
| Offline | Core/section `offline` | 暂时无法连接 | Retry | Never present the previous response as a new result | CTH04-W-005 |
| Blocked / permission denied | Invalid scope, `bound=false`, missing global grant/binding, or focused response without exact authorized binding; 401/403 | 经营主体信息暂不可用 | Retry after recovery | Do not fetch or reuse unscoped focused data; never display an untraceable event | CTH04-W-006 |
| Error | Malformed response or 5xx | 运营信息暂不可用 | Retry | Hide server details | CTH04-W-005 |
| Local inspect / return | User selects or clears an event | Inspecting one returned event | Return | Restore the same timeline; no server effect | CTH04-W-007 |

## 5. Purpose-built desktop composition

- **Primary question:** what events were returned, in what order, and what relationship information is actually available?
- **Hierarchy:** scope → relationship availability → constellation area → synchronized event timeline. The relationship area is not allowed to visually imply edges when none are returned.
- **Wide desktop:** `cth04/desktop-layout` gives the constellation a stable region and the timeline a full-height companion region. The selected event inspector replaces only the local detail region and leaves the timeline visible.
- **Keyboard:** timeline rows are focusable; Enter/Space selects; Escape or Return clears selection. Graph unavailable status is announced and text-readable.
- **Screen identity:** a time axis plus explicit relationship gap differentiates this page from a generic event table.

## 5A. Web Workspace composition and desktop-only capability boundary

- Web and desktop share the same read contract, local selection state and blocked relationship semantics. No browser-only graph library or second data source is introduced.
- Case navigation, Evidence opening and graph zoom are unavailable until canonical destination and lineage contracts are bound.
- A production claim requires runtime acceptance at desktop and browser widths; widget tests do not promote this spec.

## 6. Purpose-built mobile composition

- **Active task:** scan the vertical event path, open one returned event, then return to the path.
- **Layout:** timeline first, relationship availability second, selected detail inline. The mobile order follows time rather than shrinking the desktop constellation into cards.
- **Touch:** event rows and Return are at least 48 logical pixels; event severity and tags are textual.
- **Interruption:** no pending write or local business cache is represented. Retry restarts the read gate.
- **Screen identity:** the event path is primary and causal edges are visibly withheld when unbound.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read/write/external effect | Idempotency / reversal | Evidence emitted | Confirmation and failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Load context/events | SYSTEM context + CTH event read | Optional global auth; screen-level Subject read UNKNOWN | Read only | Repeatable | Returned event fields only | Safe ready/empty/blocked/error copy |
| Select/return event | Flutter local state | None | No server effect | Immediately reversible | None | Enabled; preserve timeline |
| New event / to Case / link risk / open source | Action registry labels only; callable owner and destination UNKNOWN | UNKNOWN | Potential write/navigation/external effect | UNKNOWN | UNKNOWN | No controls or requests |

## 8. Accessibility, motion and localization

- Focus order is scope → relationship state → timeline items → selected details → Return. The selected row and Return target are announced.
- A graph, when later bound, must have a synchronized table/list equivalent; the current page uses text explaining unavailable edges and never relies on edge color alone.
- Loading, empty, blocked and error states are live regions. Severity and tags have spoken text.
- No authored motion is required; reduced motion has identical semantics.
- The bounded UI uses existing `screen.CTH-04`, context, common, state and `cth01.*` keys; no hardcoded screen copy remains. Canonical l10n must add `cth04.relationship_unavailable`, `cth04.event_detail`, `cth04.return_timeline`, `cth04.action_unavailable` and state copy in zh-CN/en/ko before acceptance, then replace the temporary generic mappings. No second localization owner is permitted.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State/error path | Platform/input | Test layer | Current evidence/reference |
| --- | --- | --- | --- | --- | --- |
| CTH04-W-001 | Pending request shows loading and no event fields | Loading | Widget | `app/test/features/cth/cth04/cth04_screen_test.dart` | Local evidence |
| CTH04-W-002 | Empty events remain empty; graph absence is separately explained | Empty/partial | Widget | Widget test | Current builder-shaped response |
| CTH04-W-003 | Graph `notcollected` never becomes a causal edge | Not collected | Widget | Widget test | Current graph gap |
| CTH04-W-004 | No freshness/cause claim is inferred from response generation time or list order | Unknown freshness | API/widget | Contract test required | Current source lacks fields |
| CTH04-W-005 | 5xx/malformed/offline state hides raw details and supports retry | Error/offline | Widget | Widget test | Safe copy implemented |
| CTH04-W-006 | Focused context without applied binding is blocked | Focus scope | Repository/widget | Repository test | Current runtime focus gap |
| CTH04-W-007 | Select and Return preserves event timeline and does not call a write action | Local Trace/Return | Widget; keyboard/touch | Widget test | Local implementation evidence |
| CTH04-W-008 | Resize 1440 → 390 without overflow and with spoken event labels | Responsive/accessibility | Widget + runtime E2E | Widget now; runtime pending | Desktop/mobile composition implemented |
| CTH04-W-009 | Return `bound=true` without global grant/lineage; the repository blocks instead of decoding the global event list | Global authorization/lineage block | Repository/widget | Repository test | Implemented hostile fixture |
| CTH04-W-010 | Return authorized `GLOBAL_ALL` and exact focused Subject fixtures; only authorized events are decoded | Authorized global/focus read | Repository | Repository test | Implemented legal global fixture; live backend binding pending |

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for causal graph, source/Evidence trace, Case navigation and ROUND-10 acceptance. The bounded implementation is a read-only timeline with an honest graph gap.
- **Open owners:** CTH must define canonical relationship edges; Evidence must provide lineage; Case/action owners must define request, Permission, effect, confirmation and Trace/Return; SYSTEM must bind Subject scope; l10n must add the three locales.
- **Required before acceptance:** at least one real new event with lineage, verified relation edges or an explicit accepted no-edge state, focus binding, and real desktop/mobile E2E.
