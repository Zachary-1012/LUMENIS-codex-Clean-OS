# BMP-04 — 品牌传播路径

```yaml
screen_id: BMP-04
status: BLOCKED
revision: 1
owner_domain: BMP
binding_ids:
  - BACKEND-GAP-021
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
artifact_disposition: BOUNDED_IMPLEMENTATION_WITH_SCOPE_GUARD
reviewer: Codex bounded ROUND-12 Luna batch
reviewed_at: 2026-09-22
approval_reference: Product Owner approval of App / Experience Constitution §§30–36; this is not BMP-04 acceptance
```

## 0. Authority basis and artifact disposition

- Constitution basis: BMP propagation is a brand/market workflow and must preserve source-backed metric definitions, comparable windows and honest missing states.
- Product/workflow basis: channel → content → exposure → response / conversion. A raw dashboard total is not a propagation path.
- Exploration references: current Experience Constitution blueprint only; generic funnel screenshots and legacy dashboards are rejected.
- Anti-template decision: the screen uses a propagation river and channel matrix with a selected channel, not a generic KPI wall.
- Sol design decision: `DESIGN_EXPLORATION`; full acceptance is blocked because current propagation builders are not BrandFocus-bound.

## 1. User problem and product invariant

- **Role / context:** A BMP operator traces how a selected BrandFocus moves through channels toward response or conversion.
- **User task / completion:** compare channels over a declared window, inspect the path stages and understand which measures are observed versus unavailable. Completion requires a per-channel source, trace, unit, definition and comparable window.
- **Invariant:** BrandFocus is a distinct BMP scope. The screen must not use a Subject ID, global dashboard or missing value as a brand attribution.
- **Global rule:** `GLOBAL / ALL` is the default global universe for propagation when the response and every channel row carry explicit canonical global scope, verified lineage and `read_allowed`. Focused BrandFocus rows without those markers are rejected, never promoted.
- **Out of scope:** publishing, campaign edits, attribution claims beyond returned fields, audience identity, external effects and fabricated reach.

## 2. Route, entry, exit and return

- **Entry:** host shell opens BMP-04; read is `GET /api/experience/screen/BMP-04` through `LumenisCoreClient.screen('BMP-04')`.
- **Required context:** verified BMP/ZBMP `FOCUS`, distinct Subject and BrandFocus IDs, applied binding and allowed read, or `GLOBAL_ALL` with explicit global grant, canonical scope, verified lineage and `read_allowed`.
- **Exit / return:** channel selection is local presentation state. Back returns from channel detail to the river and restores the selected channel/window filter when possible.
- **Trace:** stage metrics preserve source, evidence trace, definition and window. No write, attribution recalculation or new Evidence is created.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source / callable | Definition / units / window | Freshness and missing behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Runtime envelope and owner | Experience API adapter + BMP | `GET /api/experience/screen/BMP-04`; envelope and `truth` | Runtime-bound ZBMP/zbmp response | Mismatch blocks all flow rows | BACKEND-GAP-021 | `experience_runtime.py::screen_viewmodel`; `bmp04_snapshot.dart` |
| P0 | Focus/global read binding | SYSTEM context / Permission | `focus_context` + `focus_binding` | FOCUS exact Subject/BrandFocus; GLOBAL_ALL explicit global grant/canonical scope/verified lineage/read permission | Unknown blocks channel data | BACKEND-GAP-021 | Current builder does not return verified Focus/global binding |
| P1 | Propagation channel | BMP propagation owner | Future `sections[type=channels|propagation].items[]` with channel, optional BrandFocus, stage metrics, source, trace, row scope/read/lineage fields | FOCUS exact BrandFocus; GLOBAL_ALL requires explicit global scope, verified lineage and row read permission; every metric includes value, unit, definition and comparable window | Missing metric remains unavailable; direct untyped numbers are rejected | BACKEND-GAP-021 | Current `brand_propagation` output is unscoped and lacks the required contract |
| P1 | Stage relation | BMP canonical content/metric owner | channel/content/exposure/response/conversion stage fields | Path order must be explicit; no unsupported reach/conversion derivation | Partial paths show only observed stages | BACKEND-GAP-021 | `Bmp04Channel` parser is strict by design |
| P2 | Channel selector | App presentation state | `Bmp04ViewModel` local selection | No server mutation | Empty selection shows all verified channels | BMP04-UI-LOCAL | `bmp04_view_model.dart` |

## 4. State and recovery matrix

| State | Trigger / evidence | User-visible meaning | Available actions | Recovery / return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Initial read or refresh | 正在读取品牌传播路径 | None; announce busy | Do not flash prior-focus metrics | BMP04-W-001 |
| Global / all blocked | Global grant/lineage/read contract is absent, or only focused rows are returned | 当前全局范围暂不能查看未核验传播路径 | Retry; return to context selector | Reject focused rows; do not relabel them global | BMP04-W-002 |
| Global / all ready | Authorized global binding plus valid global channels | 查看全球传播路径与可比窗口 | Select channel | Preserve global view | BMP04-W-003 |
| Empty | Valid focus or global scope but no verified channel | 当前范围暂无传播路径资料 | Refresh | Keep stage labels but no invented totals | BMP04-W-004 |
| Not collected / unknown | No channel collection or unknown state | 传播资料尚未采集完成 | Refresh | No zero or blank-as-zero display | BMP04-W-005 |
| Stale / partial | Stale window or missing stages | 部分传播阶段仍待核验 | Refresh; inspect observed stages | Mark unavailable stages explicitly | BMP04-W-006 |
| Offline | Transport unavailable | 暂时无法读取传播路径，请稍后重试 | Retry | No unscoped cached dashboard | BMP04-W-007 |
| Blocked / denied | Missing focus/read/lineage or 401/403 | 当前范围暂不能查看传播路径 | Retry; return | Hide all business metrics | BMP04-W-008 |
| Error | Malformed response or unsafe metric | 传播路径暂不可用，请稍后重试 | Retry | Hide raw payload | BMP04-W-009 |
| Ready | Exact-match focused channels or authorized global channels | Compare channel propagation over the same window | Select channel | Restore local channel selection | BMP04-W-010 |

## 5. Purpose-built desktop composition

- **Primary question:** Where does the selected brand's propagation path strengthen or stop, and what is actually observed?
- **Composition:** a focus/window header, a left-to-right propagation river for channel → content → exposure → response/conversion, and a channel matrix with definitions/windows. A selected channel detail panel explains unavailable stages rather than collapsing them to zero.
- **Interaction:** selecting a channel highlights its path and matrix row; no channel edit or attribution action is enabled.
- **Resize:** desktop shows river plus matrix; tablet stacks matrix below the selected flow; layout recomposes rather than shrinking the river into unreadable cards.

### 5A. Web Workspace composition and desktop-only boundary

- Web shares the same read contract and presentation semantics. No browser-only export, campaign action or attribution operation is added.
- Host routing owns URL restoration; local selection is the only bounded state.

## 6. Purpose-built mobile composition

- Recompose into a vertical funnel/river with a channel selector. The selected channel shows stage-by-stage rows with unit, definition and window before any summary.
- Keep BrandFocus and comparison window in view. Back returns to the channel selector.
- Each stage row is touch-safe and announces when a stage is observed, unavailable, stale or not collected. No cached unscoped metrics survive an interruption.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read / write / external effect | Idempotency / reversal | Evidence emitted | Failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Read propagation | BMP + SYSTEM context/Permission | Screen-specific read decision | Read only | Safe repeat | Existing source/trace refs | Block and retry |
| Select channel | App presentation state | None beyond read | Local only | Reversible | None | Keep focus and window |
| Change attribution / publish | No verified owner or effect contract | Unknown | Not shown | N/A | None | Omitted |

## 8. Accessibility, motion and localization

- Keyboard order is focus/window context → channel selector → river stages → matrix/detail. Selection is available by Enter/Space; focus remains visible.
- The river has a sequential table/list equivalent. Each stage announces metric value only when its unit, definition and window are present; otherwise announces unavailable/not collected.
- No decorative flow animation is required; reduced motion disables transitions. Stage meaning is not encoded by color alone.
- Shared localization integration keys for `zh-CN`, `en` and `ko`: `bmp04.title`, `bmp04.focus_label`, `bmp04.stage.channel`, `bmp04.stage.content`, `bmp04.stage.exposure`, `bmp04.stage.response`, `bmp04.stage.conversion`, `bmp04.window_label`, `bmp04.definition_label`, `bmp04.state.not_collected`, `bmp04.state.blocked`.
- Internal owner/path/provider/database vocabulary and raw errors never enter visible copy.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State / error path | Platform / input | Test layer | Current evidence / reference |
| --- | --- | --- | --- | --- | --- |
| BMP04-W-001 | Only channels matching the selected BrandFocus are available; foreign/Subject rows are rejected | Cross-focus isolation | All widths | Snapshot + widget | `app/test/features/bmp04/bmp04_screen_test.dart` |
| BMP04-W-002 | Return `GLOBAL_ALL` with focused rows or missing global binding; show blocked scope state and render no propagation metrics | Global / blocked | Desktop/mobile | Snapshot + widget | `bmp04_snapshot.dart` |
| BMP04-W-003 | Return authorized global binding plus explicitly global, lineage-verified channels; render the propagation workspace | Global / ready | Desktop/mobile | Snapshot + widget | `bmp04_snapshot.dart`; `bmp04_screen_test.dart` |
| BMP04-W-004 | Direct numbers without metric definitions/windows are rejected; missing stages stay unavailable | Partial / missing | All widths | Snapshot | `bmp04_snapshot.dart` |
| BMP04-W-005 | Desktop river and channel matrix expose comparable windows and source-backed detail | Ready / trace | Pointer + keyboard | Widget | `bmp04_screen_test.dart` |
| BMP04-W-006 | Mobile vertical funnel and selector remain usable without overflow and distinguish exposure from response | Responsive / accessibility | 1440 / 768 / 390 logical px | Widget | `bmp04_screen_test.dart` |
| BMP04-W-007 | Offline/schema failure offers retry without raw response or zero fallback | Offline / error | Desktop/mobile | Repository + widget | Core client contract; runtime remains blocked |

The real propagation API/Permission/Evidence and runtime/E2E gate is not passed by these widget fixtures; current builders provide neither the required Focus contract nor the explicit global contract.

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for full acceptance; bounded implementation remains `DESIGN_EXPLORATION`.
- **Open owners:** BMP must define stage and metric semantics; SYSTEM must return verified context/read; Shared Evidence must validate channel traces; Sol must review the river/table composition.
- **Required before acceptance:** live comparable-window data, random entity checks, runtime responsive/a11y proof and explicit rollback/observability for any future attribution capability.

## 11. Real delivery and data-maturity overlay

- **REAL USER JOB:** understand how a selected brand's content propagates through channels and where observed response begins or remains unknown.
- **REAL DELIVERY CARD:** real BrandFocus/window → scoped channel read → stage-by-stage propagation result → source-backed detail. Current source fails the scoped entry gate; commercial readiness is `NO`.
- **GLOBAL UNIVERSE / DATA MATURITY IMPACT:** `GLOBAL / ALL` may show the global propagation universe only through explicit global scope/lineage/read markers; focused rows cannot become global propagation. Current endpoint lacks that contract, so coverage remains blocked; random sample acceptance is `NOT RUN / canonical scoped channels unavailable`.
- **CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION:** `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE`; the bounded slice reuses current contracts and adds no parallel attribution engine or provider.
