# BMP-02 — 品牌组合与竞品谱系

```yaml
screen_id: BMP-02
status: BLOCKED
revision: 1
owner_domain: BMP
binding_ids:
  - BACKEND-GAP-019
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
artifact_disposition: BOUNDED_IMPLEMENTATION_WITH_SCOPE_GUARD
reviewer: Codex bounded ROUND-12 Luna batch
reviewed_at: 2026-09-22
approval_reference: Product Owner approval of App / Experience Constitution §§30–36; this is not BMP-02 acceptance
```

## 0. Authority basis and artifact disposition

- Constitution basis: BMP is Brand/Market-first; responsive composition must recompose at the approved desktop, tablet and mobile widths.
- Product/workflow basis: BrandFocus → market position → competitor set → source-backed comparison. A CTH Subject is never a BrandFocus substitute.
- Exploration references: the current Experience Constitution blueprint only. No PDF, screenshot, Figma frame or historical UI is copied into this slice.
- Anti-template decision: the desktop view is a constellation of owned, sub-brand and competitor entities with one selected profile; it is not a KPI wall or swapped-title card grid.
- Sol design decision: `DESIGN_EXPLORATION`; implementation is a bounded scope-guard slice and remains blocked for full acceptance until the callable returns verified BrandFocus rows.

## 1. User problem and product invariant

- **Role / context:** A BMP operator compares one authorized BrandFocus with its owned brands, sub-brands and competitor entities.
- **User task / completion:** choose or confirm a BrandFocus, or inspect the default global product universe, understand the portfolio relationship, and inspect one source-backed entity profile. FOCUS completion requires exact `brand_focus_id`; GLOBAL_ALL completion requires explicit global scope, verified lineage and row read permission, plus source and item-level trace.
- **Invariant:** `subject_id` identifies the selected context only; `brand_focus_id` is a distinct BMP business scope. The screen must never infer brand ownership from a Subject, author, source or display name.
- **Global rule:** `GLOBAL / ALL` is the default full-universe view. It may show real global portfolio rows only when the response and every row carry explicit canonical global scope, verified lineage and `read_allowed`; a focused BrandFocus row without those markers is rejected, never promoted.
- **Out of scope:** changing context, creating a brand, editing competitor sets, CTH records, publishing, reports and any write or external effect.

## 2. Route, entry, exit and return

- **Entry:** the canonical App Shell may open BMP-02; this batch does not alter shell routing. The screen reads `GET /api/experience/screen/BMP-02` through `LumenisCoreClient.screen('BMP-02')`.
- **Required context:** either a server-returned `FOCUS` context for `domain_id=BMP`, `product_id=ZBMP`, a non-empty `subject_id`, a distinct `brand_focus_id`, `focus_binding.applied=true` and an allowed read decision, or `GLOBAL_ALL` with the explicit global grant, canonical scope, verified lineage and `read_allowed` contract above. The route cannot grant authorization.
- **Exit / return:** entity selection is local presentation state. Return restores the selected entity, search query and role filter when the host keeps the screen alive. No context mutation occurs.
- **Trace position:** the selected entity dossier retains its source and trace reference in the response-backed view model; a future trace route is not invented here.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source / callable | Definition / units / window | Freshness and missing behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Envelope and product identity | Experience API adapter + BMP | `GET /api/experience/screen/BMP-02`; `ok`, `screen`, `bound`, `source`, `truth.product_id`, `truth.domain_id` | Must be runtime-bound and exactly `ZBMP` / `zbmp` | Mismatch blocks all business rows | BACKEND-GAP-019 | `experience_runtime.py::screen_viewmodel`; `bmp02_snapshot.dart` |
| P0 | BrandFocus context and read decision | SYSTEM context / Permission + BMP scope | `focus_context` and `focus_binding` in the response | `FOCUS` requires distinct Subject/BrandFocus; `GLOBAL_ALL` requires `scope_verified=true`, `global_all_granted=true`, `evidence_lineage=verified`, canonical global scope and `read_allowed=true` | Unknown or denied blocks entity rows | BACKEND-GAP-019 | Current BMP-02 builder does not return a verified focus/global binding |
| P1 | Portfolio entities | BMP canonical owner | Future `sections[type=brands|portfolio].items[]` with `id`, optional `brand_focus_id`, `name`, `role`, `source`, `evidence_ref`, `read_allowed`, `scope_mode`, `canonical_scope`, `lineage` | FOCUS rows require exact BrandFocus; GLOBAL_ALL rows require explicit global scope, verified lineage and row read permission | Missing, focused-without-global-markers or cross-focus rows are omitted, never reassigned | BACKEND-GAP-019 | `_build_bmp02()` currently returns a curated directory without BrandFocus/global lineage |
| P1 | Selected entity profile | BMP canonical owner + Shared Evidence | Same entity row plus optional typed metrics, category, capture time and window | Each value remains source-backed and scope-matched | Null stays unavailable; no missing→0 conversion | BACKEND-GAP-019 | `Bmp02Brand` parser and dossier are bounded to verified rows |
| P2 | Search and role filter | App presentation state | `Bmp02ViewModel` local filters | No server mutation | Empty filter state keeps the focus banner and offers clear filter | BMP02-UI-LOCAL | `bmp02_view_model.dart` |

The current backend builder is intentionally treated as unscoped. A successful HTTP response or a curated brand directory does not satisfy this table.

## 4. State and recovery matrix

| State | Trigger / evidence | User-visible meaning | Available actions | Recovery / return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Initial read or refresh | 正在读取品牌组合 | None; announce busy | Keep selected focus context; show no stale rows | BMP02-W-001 |
| Global / all blocked | `GLOBAL_ALL` lacks global grant/lineage/read contract, or only focused rows are returned | 当前全局范围暂不能显示未核验的品牌组合 | Retry; return to host context selector | Reject focused rows; do not relabel them global | BMP02-W-002 |
| Global / all ready | Authorized global binding plus at least one valid global row | 查看全球品牌产品宇宙与组合关系 | Search, role filter, local selection | Preserve global view; selection does not create BrandFocus | BMP02-W-003 |
| Empty | Bound focused or global payload has no valid entity rows and no rejected rows | 当前范围暂无品牌组合资料 | Refresh; clear filters | Keep scope visible | BMP02-W-004 |
| Not collected | `truth.data_state=NOT_COLLECTED` | 品牌组合资料尚未采集 | Refresh | Preserve unavailable metrics; never show zero | BMP02-W-005 |
| Stale / partial | Data state is stale or some rows lack lineage | 部分品牌资料仍待核验 | Refresh; inspect verified rows only | Hide invalid rows and keep source note | BMP02-W-006 |
| Offline | Transport unavailable | 暂时无法读取品牌组合，请稍后重试 | Retry | Do not substitute cached unscoped data | BMP02-W-007 |
| Blocked / denied | Missing focus, wrong owner, 401/403 or read denied | 当前范围暂不能查看品牌组合 | Retry; return | No business rows or internal diagnostics | BMP02-W-008 |
| Error | Malformed or unexpected response | 品牌组合暂不可用，请稍后重试 | Retry | Hide raw response text | BMP02-W-009 |
| Ready | Focus exact-match rows or authorized global rows pass all checks | Compare the selected focus or global portfolio and competitor set | Search, role filter, local selection | Restore local selection only | BMP02-W-010 |

## 5. Purpose-built desktop composition

- **Primary question:** Which entities belong to this BrandFocus, and how does the selected entity relate to the portfolio?
- **Composition:** a compact focus/context rail, a broad constellation field with owned/sub-brand/competitor grouping, and a selected entity dossier with source/time window. The constellation is a relationship view, not a repeated metric-card surface.
- **Interaction:** clicking or keyboard-selecting one entity updates only the dossier. Search and role chips filter the local list; they never change BrandFocus authorization.
- **Resize:** at wide desktop, constellation and dossier sit side by side; at tablet widths the dossier follows the selected list; no horizontal overflow or desktop shrink-to-mobile.

### 5A. Web Workspace composition and desktop-only boundary

- Web uses the same Product Core response and ViewModel semantics. Browser URL/deep-link restoration is host-owned and not invented in this batch.
- No desktop-only effect or export exists. Unavailable actions remain absent rather than appearing as disabled fake affordances.

## 6. Purpose-built mobile composition

- Keep the selected BrandFocus visible, followed by a searchable portfolio list. The selected profile expands below the list and competitor entities are represented as explicit chips/rows, not a miniature desktop constellation.
- Touch targets are at least 48 logical pixels. Back returns to the host shell; it does not switch Subject or BrandFocus.
- On interruption, retry the same read and preserve only local filter/selection state. Do not show stale rows from another focus.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read / write / external effect | Idempotency / reversal | Evidence emitted | Failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Read portfolio | BMP + SYSTEM context/Permission | Screen-specific read decision required | Read only | Safe repeat | Existing source/trace refs only | Block and offer retry |
| Search / role filter | App presentation state | None | Local only | Reversible | None | Show filtered empty state |
| Select entity | BMP presentation state | None beyond the already-authorized read | Local only | Reversible | None | Keep current focus; no context mutation |
| Edit portfolio / add competitor | No verified write owner in this slice | Unknown | Not shown | N/A | None | Omitted, never simulated |

## 8. Accessibility, motion and localization

- Keyboard order is focus context → search → role filters → entity list → dossier. Enter/Space selects an entity; focus remains visible after filtering.
- Each entity exposes one semantic label containing its name, relationship role and selection state. Constellation visuals have a list equivalent.
- No decorative animation is required; reduced motion removes any selection transition. Color is never the only role signal.
- The shared localization owner receives semantic keys, not feature-local dictionaries. Required integration keys are declared for `zh-CN`, `en` and `ko`: `bmp02.title`, `bmp02.focus_label`, `bmp02.role.owned`, `bmp02.role.sub_brand`, `bmp02.role.competitor`, `bmp02.state.not_collected`, `bmp02.state.blocked`, `bmp02.source_label`, `bmp02.trace_label`.
- Machine IDs, source paths and internal diagnostics are not user copy.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State / error path | Platform / input | Test layer | Current evidence / reference |
| --- | --- | --- | --- | --- | --- |
| BMP02-W-001 | Parse a focused response and render only rows whose `brand_focus_id` equals the selected BrandFocus | Cross-focus / compatibility rows rejected | All widths | Snapshot + widget | `app/test/features/bmp02/bmp02_screen_test.dart` |
| BMP02-W-002 | Return `GLOBAL_ALL` with focused rows or missing global binding; show blocked scope state and render no rows | Global / blocked | Desktop and mobile | Snapshot + widget | `bmp02_snapshot.dart` |
| BMP02-W-003 | Return authorized global binding plus explicitly global, lineage-verified rows; render the same portfolio workspace | Global / ready | Desktop and mobile | Snapshot + widget | `bmp02_snapshot.dart`; `bmp02_screen_test.dart` |
| BMP02-W-004 | Return `NOT_COLLECTED`, `UNKNOWN` or null metrics; preserve explicit unavailable state and never render zero | Not collected / unknown | All widths | Snapshot | `bmp02_snapshot.dart` |
| BMP02-W-005 | Select an entity; dossier keeps source, window and trace-backed fields and reveals no internal vocabulary | Ready | Desktop / keyboard | Widget | Purpose-built dossier test |
| BMP02-W-006 | Narrow to mobile width; list, search, filters and dossier recompose without overflow | Responsive / accessibility | 1440 / 768 / 390 logical px | Widget | `bmp02_screen_test.dart` |
| BMP02-W-007 | Transport or malformed response offers retry without echoing raw server text | Offline / error | Desktop and mobile | Repository + widget | Core client contract; runtime binding still blocked |

The real Product Core/API/Permission/Evidence acceptance is blocked until the backend returns verified BrandFocus rows. Fixtures prove parser and rendering isolation only; they do not prove production completion.

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for full acceptance; the bounded renderer is `DESIGN_EXPLORATION` with a fail-closed implementation.
- **Open owners:** BMP must define the canonical portfolio/competitor response and metric lineage; SYSTEM must return the actor/read decision; Shared Evidence must validate item traces; App Shell must later bind the host BrandFocus selector.
- **Changes required before DESIGN_READY / ACCEPTED:** a current callable with per-record BrandFocus, Permission and Evidence proof; live runtime/E2E on desktop/web/mobile; and Sol review of this screen-specific composition.

## 11. Real delivery and data-maturity overlay

- **REAL USER JOB:** understand the selected brand's portfolio position and competitor set well enough to choose the next market-intelligence drill-in.
- **REAL DELIVERY CARD:** real BrandFocus input → scoped portfolio read → visible entity relationship and source-backed profile → local selection return. Current callable fails the scoped-read entry gate, so commercial completion is blocked.
- **GLOBAL UNIVERSE / DATA MATURITY IMPACT:** `GLOBAL / ALL` is the default global product universe when the explicit global contract is present; focused rows are never promoted. Current endpoint lacks that contract, so global coverage remains blocked. Random entity acceptance is `NOT RUN / current canonical scoped population unavailable`.
- **CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION:** `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE` for this bounded slice. The Experience Constitution and current Product Core are sufficient references; no third-party dependency or alternate data owner is introduced.
