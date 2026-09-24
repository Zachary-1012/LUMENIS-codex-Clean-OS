# BMP-03 — 市场情报与机会雷达

```yaml
screen_id: BMP-03
status: BLOCKED
revision: 1
owner_domain: BMP
binding_ids:
  - BACKEND-GAP-020
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
artifact_disposition: BOUNDED_IMPLEMENTATION_WITH_SCOPE_GUARD
reviewer: Codex bounded ROUND-12 Luna batch
reviewed_at: 2026-09-22
approval_reference: Product Owner approval of App / Experience Constitution §§30–36; this is not BMP-03 acceptance
```

## 0. Authority basis and artifact disposition

- Constitution basis: BMP market intelligence must be BrandFocus-first, source-aware and responsive across the approved surfaces.
- Product/workflow basis: BrandFocus → market signal → opportunity interpretation → source brief. `GLOBAL / ALL` is also a first-class global product universe, but a global signal must carry explicit canonical global scope, verified lineage and `read_allowed`.
- Exploration references: current Experience Constitution blueprint only; historical dashboards and screenshots are rejected as implementation inputs.
- Anti-template decision: the page is a momentum/confidence radar paired with a ranked signal feed and source brief, not a generic KPI wall.
- Sol design decision: `DESIGN_EXPLORATION`; full acceptance is blocked because the current builder is global/unscoped.

## 1. User problem and product invariant

- **Role / context:** A BMP operator needs to identify market opportunities for one authorized BrandFocus and understand why each opportunity is present.
- **User task / completion:** inspect a ranked signal, compare momentum with confidence, and read its source-backed brief. Completion requires a same-focus signal with a valid source, time window and trace.
- **Invariant:** Subject context is not brand scope. `brand_focus_id` must match the selected focus on every visible signal.
- **Global rule:** `GLOBAL / ALL` may render real global market signals when the response and each row pass the global scope/lineage/read contract. Focused BrandFocus signals without those markers are rejected, never promoted.
- **Out of scope:** automatic recommendations, action execution, reports, provider selection, hidden source identifiers and invented scores.

## 2. Route, entry, exit and return

- **Entry:** host shell opens BMP-03 and the screen reads `GET /api/experience/screen/BMP-03` through `LumenisCoreClient.screen('BMP-03')`.
- **Required context:** verified BMP/ZBMP `FOCUS` with distinct Subject and BrandFocus IDs, applied binding and allowed read, or `GLOBAL_ALL` with explicit global grant, canonical scope, verified lineage and `read_allowed`. The route cannot grant access.
- **Exit / return:** signal selection is local. Return restores selected signal and kind filter if the host preserves the screen; no context change or workflow write occurs.
- **Trace:** the source brief keeps the signal's source, capture time/window and item-level trace as the return anchor. A future evidence-reader route remains unbound.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source / callable | Definition / units / window | Freshness and missing behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Runtime envelope and owner | Experience API adapter + BMP | `GET /api/experience/screen/BMP-03`; envelope and `truth` fields | Runtime-bound, exactly ZBMP/zbmp | Any mismatch blocks signals | BACKEND-GAP-020 | `experience_runtime.py::screen_viewmodel`; `bmp03_snapshot.dart` |
| P0 | BrandFocus/global read binding | SYSTEM context / Permission | `focus_context` + `focus_binding` | FOCUS requires exact Subject/BrandFocus; GLOBAL_ALL requires global grant, canonical scope, verified lineage and `read_allowed` | Unknown blocks the feed | BACKEND-GAP-020 | Current `_build_bmp03()` has no verified BrandFocus/global binding |
| P1 | Market signal | BMP intelligence owner | Future `sections[type=signals|intel|opportunities].items[]`: id, optional BrandFocus, title, kind, confidence, momentum, source, evidence ref, row scope/read/lineage fields | FOCUS rows exact-match BrandFocus; GLOBAL_ALL rows require explicit global scope, verified lineage and row read permission | Missing score remains unavailable; no zero fallback | BACKEND-GAP-020 | Current builder reads global intelligence assets without the required contract |
| P1 | Source brief | BMP + Shared Evidence | signal summary, source, captured time, time window, trace | Source position must explain the signal | Invalid lineage hides the signal | BACKEND-GAP-020 | `Bmp03Signal` parser preserves source fields only when safe |
| P2 | Kind filter | App presentation state | `Bmp03ViewModel` | Local filter only | Empty filter state keeps focus and source context | BMP03-UI-LOCAL | `bmp03_view_model.dart` |

## 4. State and recovery matrix

| State | Trigger / evidence | User-visible meaning | Available actions | Recovery / return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Initial read or refresh | 正在读取市场情报 | None; announce busy | No previous-focus rows flash | BMP03-W-001 |
| Global / all blocked | Global grant/lineage/read contract is absent, or only focused rows are returned | 当前全局范围暂不能查看未核验市场情报 | Retry; return to context selector | Reject focused rows; do not relabel them global | BMP03-W-002 |
| Global / all ready | Authorized global binding plus valid global signals | 查看全球市场机会与来源说明 | Kind filter; select signal | Preserve global view | BMP03-W-003 |
| Empty | Valid focused or global response with no valid signals and no rejected rows | 当前范围暂无市场机会信号 | Refresh | Keep explicit empty state | BMP03-W-004 |
| Not collected / unknown | Data state says not collected or unknown | 市场情报尚未形成可核验记录 | Refresh | Do not translate unknown to zero | BMP03-W-005 |
| Stale / partial | stale data or dropped rows | 部分市场情报仍待核验 | Refresh; read verified rows | Show data freshness wording without claiming live | BMP03-W-006 |
| Offline | Transport unavailable | 暂时无法读取市场情报，请稍后重试 | Retry | No stale unscoped feed | BMP03-W-007 |
| Blocked / denied | Missing focus/Permission/lineage, 401/403 | 当前范围暂不能查看市场情报 | Retry; return | Hide all business records | BMP03-W-008 |
| Error | Contract failure or malformed values | 市场情报暂不可用，请稍后重试 | Retry | Hide raw payload/error | BMP03-W-009 |
| Ready | Exact-match focused signals or authorized global signals | Review ranked opportunities and their source brief | Kind filter; select signal | Restore local selection | BMP03-W-010 |

## 5. Purpose-built desktop composition

- **Primary question:** Which market signal deserves attention, and what source-backed evidence explains its confidence and momentum?
- **Composition:** a focus header, a compact radial opportunity field using confidence/momentum axes, a ranked signal feed and a right-side source brief. The radar has a list/table equivalent and is not a decorative chart.
- **Interaction:** selecting a signal updates the source brief; kind filters affect the local feed only. No signal is promoted into a decision or action.
- **Resize:** desktop uses radar + ranked feed + brief; tablet stacks the brief under the selected feed; the page never reduces to a generic three-column card grid.

### 5A. Web Workspace composition and desktop-only boundary

- Web shares the same screen response, parser and ViewModel. URL restoration of a selected signal is host-owned and not added here.
- No browser-only effect, export or report action is exposed.

## 6. Purpose-built mobile composition

- Recompose to a ranked signal feed first, with momentum/confidence labels in each row and a source-reader drill-in below the selected row.
- Keep BrandFocus and time window visible. Back returns from the source brief to the feed; it never changes context.
- Use 48 px touch targets, announce filter changes, and preserve no stale signal after an interrupted read.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read / write / external effect | Idempotency / reversal | Evidence emitted | Failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Read signals | BMP + SYSTEM scope/Permission | Screen-specific read decision | Read only | Safe repeat | Existing trace refs | Block and retry |
| Filter / select | App presentation state | None beyond read | Local only | Reversible | None | Keep source context |
| Create recommendation / decision | No verified owner in this slice | Unknown | Not shown | N/A | None | Omitted |

## 8. Accessibility, motion and localization

- Keyboard order is focus header → kind filter → ranked feed → source brief. Enter/Space selects a signal; Escape returns from brief.
- Radar has a semantic ranked-list equivalent. Each signal announces title, kind, confidence, momentum, freshness and source in plain language.
- No decorative animation; reduced motion removes chart transitions. Confidence and momentum use text as well as position/color.
- Shared localization integration keys for `zh-CN`, `en` and `ko`: `bmp03.title`, `bmp03.focus_label`, `bmp03.kind.opportunity`, `bmp03.kind.risk`, `bmp03.kind.trend`, `bmp03.confidence_label`, `bmp03.momentum_label`, `bmp03.source_brief`, `bmp03.state.not_collected`, `bmp03.state.blocked`, `bmp03.trace_label`.
- Internal terms, raw source URLs and untrusted identifiers remain hidden from user copy.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State / error path | Platform / input | Test layer | Current evidence / reference |
| --- | --- | --- | --- | --- | --- |
| BMP03-W-001 | Only signals matching the selected BrandFocus appear; Subject-shaped and other-focus rows are rejected | Cross-focus / compatibility isolation | All widths | Snapshot + widget | `app/test/features/bmp03/bmp03_screen_test.dart` |
| BMP03-W-002 | Return `GLOBAL_ALL` with focused rows or missing global binding; show blocked scope state and render no signals | Global / blocked | Desktop/mobile | Snapshot + widget | `bmp03_snapshot.dart` |
| BMP03-W-003 | Return authorized global binding plus explicitly global, lineage-verified signals; render the market workspace | Global / ready | Desktop/mobile | Snapshot + widget | `bmp03_snapshot.dart`; `bmp03_screen_test.dart` |
| BMP03-W-004 | Unknown, not collected and missing numeric values remain explicit states, never zero | Unknown / not collected | All widths | Snapshot | `bmp03_snapshot.dart` |
| BMP03-W-005 | Desktop radar selection opens a source brief without internal implementation vocabulary | Ready / trace | Keyboard + pointer | Widget | `bmp03_screen_test.dart` |
| BMP03-W-006 | Mobile ranked feed and source brief recompose without overflow; hostile text is dropped | Responsive / hostile input | 1440 / 768 / 390 logical px | Widget | `bmp03_screen_test.dart` |
| BMP03-W-007 | Offline/schema failure offers retry and hides raw response | Offline / error | Desktop/mobile | Repository + widget | Core client contract; runtime remains blocked |

Real API/Permission/Evidence and runtime/E2E acceptance remain blocked because the current builder has neither the Focus nor the explicit global contract. Widget fixtures prove both-scope isolation, not production readiness.

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for full acceptance; `DESIGN_EXPLORATION` bounded slice only.
- **Open owners:** BMP must provide Focus-scoped signal fields and definitions; SYSTEM must return actor/read binding; Shared Evidence must validate signal traces; Sol must review the screen composition before DESIGN_READY.
- **Required before acceptance:** live BrandFocus run, source-reader trace resolution, responsive/a11y runtime checks and random entity data acceptance.

## 11. Real delivery and data-maturity overlay

- **REAL USER JOB:** understand which market opportunity matters for a selected brand and why.
- **REAL DELIVERY CARD:** real BrandFocus → scoped signal retrieval → ranked signal → source brief. Current entry lacks scoped signal retrieval, so commercial readiness is `NO`.
- **GLOBAL UNIVERSE / DATA MATURITY IMPACT:** `GLOBAL / ALL` may expose the global market universe only through explicit global scope/lineage/read markers; focused signals cannot be relabeled. Current endpoint lacks that contract, so global and brand coverage remain blocked. Random sample acceptance is `NOT RUN / scoped population unavailable`.
- **CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION:** `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE`; current Experience Constitution and Product Core are reused, with no alternate intelligence provider or owner.
