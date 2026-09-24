# CTH-06 — 负面监测与反馈

```yaml
screen_id: CTH-06
status: BLOCKED
revision: 1
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-012
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: NON_AUTHORITATIVE_EXPLORATION_ONLY
reviewer: Codex delegated ROUND-10 bounded source review
reviewed_at: 2026-09-22
approval_reference: source baseline origin/main 5ba1aefc53a1babc293e990c23c62f841724c843; this is not per-screen acceptance
```

## 0. Authority basis and artifact disposition

- The governing experience row is the CTH-06 triage queue that distinguishes public opinion, customer feedback and confirmed incidents, with a source-first reader.
- The current source is `experience_screens._build_cth06()` through `GET /api/experience/screen/CTH-06`. It supplies the current negative/high-risk note table, but the declared feedback API, category semantics and per-item lineage are not fully bound.
- Fixture rows, `note_id` values and action JSON are non-authoritative evidence. A row identifier is not a Case or Evidence link.
- This composition is queue → reading pane → source availability, not a generic table and detail card.
- Sol design decision: `BLOCKED`; the slice is read-only and does not classify, link or mutate records.

## 1. User problem and product invariant

- **User task:** triage returned negative feedback, understand whether it is public opinion, customer feedback, a confirmed incident or not yet classified, and read the returned wording without losing queue context.
- **Context:** `GLOBAL_ALL` uses the returned global list only after a server `global_binding` (or current canonical equivalent) proves global grant/scope, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage. A focused CTH context additionally requires an applied focus binding, exact Subject equality, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage; otherwise it is blocked.
- **Completion signal for this slice:** returned rows are grouped by category when the response supplies a category; missing category stays `待分类反馈`, and the reading pane shows returned business fields only.
- **Invariant:** category labels do not create an incident or Case. Original source wording and lineage must remain distinguishable from derived classification. `bound=true` alone never authorizes a global list.
- **Out of scope:** classifying a row on the server, linking a Case, opening an original source, editing wording, resolving an incident, exporting and external notification.

## 2. Route, entry, exit and return

- **Entry:** `Cth06Screen(client: ...)` from the existing CTH workspace; no route or secondary repository is introduced.
- **Read sequence:** `settingsContext()` → `screen('CTH-06')`; current response fields are `table.state` and rows `time/date`, `title/summary`, `platform/channel`, `sentiment`, `risk`, and optional `category/cluster/kind`.
- **Scope gate:** `bound == true` is only route wiring. The adapter requires the authorized server global/focus binding first; each displayed row also requires explicit matching scope, read permission, verified Evidence lineage and a trace/evidence reference. No local Permission or lineage default is created.
- **Exit / return:** category filter and selected reading item are local. Clearing selection returns to the queue; no source deep-link or write action is attempted.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source/ViewModel field or callable | Definition / units / window | Freshness and missing-data behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Scope label | SYSTEM context read | `LumenisCoreClient.settingsContext()` | `GLOBAL_ALL` or applied CTH focus | Invalid/missing scope blocks; IDs hidden | — | Current context contract |
| P1 | Feedback queue | CTH note read builder | `_build_cth06()` `table.rows[time/date,title/summary,platform/channel,sentiment,risk]` | Returned negative/high-risk records; no total claim | Explicit empty stays empty; rows without matching scope/lineage/trace are withheld; source read failure is not empty | BACKEND-GAP-012 | Current source mapping; lineage pending |
| P1 | Triage category | CTH classification owner UNKNOWN | Optional row `category`, `cluster` or `kind` parsed to public opinion/customer feedback/confirmed incident/unclassified | Missing category is `待分类反馈`; it is not an incident | No category mutation; no inferred category from risk alone | BACKEND-GAP-012 | Current row shape only partially matches declared ViewModel |
| P1 | Reading pane | CTH source/Evidence owner UNKNOWN | Selected returned business fields from the same row | Preserve returned wording; no source claim without a bound origin | Show source unavailable copy; hide note IDs and internal fields | BACKEND-GAP-012 | Per-item lineage and source reader pending |

The adapter does not rename notes into Cases, does not call a negative-comments API directly and does not create a parallel feedback store.

## 4. State and recovery matrix

| State | Trigger/evidence | User-visible meaning | Available actions | Recovery/return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Context/table request pending | 正在加载负面反馈 | None | Announce; hide queue details | CTH06-W-001 |
| Empty / no feedback | `table.state=empty`, no rows | 当前范围内暂无负面反馈 | Refresh | Do not show a blank reading pane as success | CTH06-W-002 |
| Not collected | Table/source says not collected | 负面反馈尚未采集 | None | Keep distinct from empty | CTH06-W-003 |
| Fresh / stale | No source freshness contract | UNKNOWN | None | Do not label feedback live/latest | CTH06-W-004 |
| Partial | Rows exist but category/source detail is absent | 反馈可查看，分类或出处暂缺 | Refresh | Keep returned wording and name missing fields | CTH06-W-005 |
| Offline | Core/source failure | 暂时无法连接 | Retry | No stale success or invented row | CTH06-W-006 |
| Blocked / permission denied | Invalid scope, `bound=false`, missing global grant/binding, or focused response without exact authorized binding; 401/403 | 经营主体信息暂不可用 | Retry after recovery | No global fallback for a focused scope; no untraceable row is shown | CTH06-W-007 |
| Error | Malformed response/5xx | 运营信息暂不可用 | Retry | Hide raw details | CTH06-W-006 |
| Local reading/return | Select or clear a row/category filter | 阅读当前返回的反馈 | Return/clear filter | Restore queue and selected category locally | CTH06-W-008 |

## 5. Purpose-built desktop composition

- **Primary question:** which returned negative voices need reading, and what is known versus still unclassified?
- **Hierarchy:** scope → triage filters → dense queue → source-first reading pane. Category chips explain returned classification state; they do not submit classification.
- **Wide desktop:** `cth06/desktop-layout` keeps the queue mounted beside the reading pane. Selecting a row opens its returned date, channel, sentiment, risk and summary without showing internal IDs.
- **Keyboard:** category controls and queue rows are focusable; Enter/Space applies/selects; Escape or Return clears the reading item. Category meaning is textual.
- **Screen identity:** triage queue plus source-availability reading pane distinguishes this from CTH-03 monitoring and CTH-04 events.

## 5A. Web Workspace composition and desktop-only capability boundary

- Web and desktop share the same read-only queue model and local selection. No browser-only source automation is introduced.
- Source opening, classification, Case linking and export remain unavailable until their canonical owners provide scope, Permission, effect and Trace contracts.
- Runtime acceptance must verify a real row and keyboard reading flow; widget fixtures alone are insufficient.

## 6. Purpose-built mobile composition

- **Active task:** filter the returned feedback, open one item, read its wording and return to the queue.
- **Layout:** filters → stacked queue items → full-width reading pane. The category state remains visible when the reading pane is open.
- **Touch:** filter chips, rows and Return have at least 48 logical pixels. Risk and sentiment are not color-only.
- **Interruption:** retry restarts the context and table read; no local mutation or offline cache is represented.
- **Screen identity:** the mobile page keeps queue-to-reading flow instead of turning each item into a generic dashboard card.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read/write/external effect | Idempotency / reversal | Evidence emitted | Confirmation and failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Load context/feedback | SYSTEM + CTH read builder; actor/Subject binding UNKNOWN | Optional global auth; screen READ UNKNOWN | Read only | Repeatable | Returned row only | Safe state copy |
| Filter/select/return | Flutter local state | None | No server effect | Reversible | None | Enabled |
| Classify / link Case / open original source | CTH classification, Case and Evidence owners UNKNOWN | UNKNOWN | Potential write/navigation | UNKNOWN | UNKNOWN | No enabled controls |

## 8. Accessibility, motion and localization

- Queue rows announce summary, date, channel, sentiment, risk and category; internal IDs are not in the accessible tree.
- A source-first reader must have a linear text equivalent. The current source gap is announced as a message, not represented by an empty link.
- Loading, empty, unavailable and error statuses use live regions; category and risk have text labels.
- No authored motion is required; reduced motion keeps the same queue/reader relationship.
- The bounded UI uses existing `screen.CTH-06`, context, common, state and `cth01.*` keys; no hardcoded screen copy remains. Canonical l10n must add `cth06.category_filter`, `cth06.unclassified`, `cth06.source_unavailable`, `cth06.reading_return`, `cth06.action_unavailable` and state copy in zh-CN/en/ko before acceptance, then replace the temporary generic mappings. No second l10n owner.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State/error path | Platform/input | Test layer | Current evidence/reference |
| --- | --- | --- | --- | --- | --- |
| CTH06-W-001 | Pending response keeps feedback hidden and announces loading | Loading | Widget | `app/test/features/cth/cth06/cth06_screen_test.dart` | Local evidence |
| CTH06-W-002 | Empty table does not create a reading item | Empty | Widget | Widget test | Local evidence |
| CTH06-W-003 | Not-collected table remains distinct | Not collected | Widget/repository | Contract test required | Parser preserves state |
| CTH06-W-004 | No latest/live claim is inferred without source freshness | Unknown freshness | API/widget | Contract test required | Current source gap |
| CTH06-W-005 | Missing category/source detail stays visibly incomplete and no action button appears | Partial | Widget | Widget test | Local evidence |
| CTH06-W-006 | Offline/error hides raw server detail and offers retry | Offline/error | Widget | Widget test required | Safe copy implemented |
| CTH06-W-007 | Focused unbound context is blocked | Focus scope | Repository/widget | Repository test required | Current focus gap |
| CTH06-W-008 | Filter and read one item, then return without write/effect | Local Trace/Return | Widget; keyboard/touch | Widget test | Local evidence |
| CTH06-W-009 | A real new negative record preserves source wording and lineage into the reader | Real user work | Runtime/E2E | Required before ROUND-10 PASS | Not yet run |
| CTH06-W-010 | Return `bound=true` with rows but no global grant/lineage; the repository blocks before exposing feedback | Global authorization/lineage block | Repository/widget | Repository test | Implemented hostile fixture |
| CTH06-W-011 | Return an authorized `GLOBAL_ALL` fixture; only rows with explicit global scope and trace are decoded | Authorized global read | Repository | Repository test | Implemented legal fixture; live source binding pending |

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for source-first lineage, classification actions and ROUND-10 acceptance. The bounded implementation provides a read-only triage queue with explicit gaps.
- **Open owners:** Evidence/source owner must bind original records; CTH/Case owner must define classification/link operations; SYSTEM must bind Subject authorization; canonical l10n must add three locales.
- **Required before acceptance:** real new negative feedback, preserved source wording and lineage, category semantics, focused binding, action Permission/effect/Trace, and desktop/mobile E2E.
