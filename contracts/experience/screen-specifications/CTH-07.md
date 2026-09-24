# CTH-07 — 趋势分析

```yaml
screen_id: CTH-07
status: BLOCKED
revision: 1
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-013
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: NON_AUTHORITATIVE_EXPLORATION_ONLY
reviewer: Codex delegated ROUND-10 bounded source review
reviewed_at: 2026-09-22
approval_reference: source baseline origin/main 5ba1aefc53a1babc293e990c23c62f841724c843; this is not per-screen acceptance
```

## 0. Authority basis and artifact disposition

- The governing experience row is the CTH-07 aligned time-series canvas with metric-definition rail, compatible comparisons and a decomposition panel.
- The current source is `experience_screens._build_cth07()` through `GET /api/experience/screen/CTH-07`. It uses daily aggregate arrays, while the declared trend/canonical-metric callable is not verified. The current response lacks a complete metric definition and safe contribution decomposition.
- Static trend fixtures and action metadata are non-authoritative. A chart array alone does not prove numerator, denominator, Subject, source, freshness or an explanation for change.
- The implementation is purpose-built as definition → aligned chart → arithmetic change explanation. It does not guess causal contributions.
- Sol design decision: `BLOCKED`; a trend is rendered only when its definition and aligned values are source-backed.

## 1. User problem and product invariant

- **User task:** understand how a returned CTH metric changed over one stated window, what its numerator/denominator mean, and which returned series is selected.
- **Context:** global data requires `GLOBAL_ALL` plus a server `global_binding` (or current canonical equivalent) proving global grant/scope, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage; the definition subject must also be global. Focused data additionally requires an applied CTH focus binding, exact Subject equality, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage. Missing fields block the chart.
- **Completion signal for this slice:** a user can select a returned series and read its labels, values, definition and simple first-to-last delta. The UI does not claim why the delta happened when contribution data is absent.
- **Invariant:** arithmetic change is not causal analysis. No missing series, source error or undefined denominator becomes zero. `bound=true` alone never authorizes a global aggregate.
- **Out of scope:** adding metrics/cohorts through a server call, exporting, editing a metric, causal explanation, Evidence navigation and any external effect.

## 2. Route, entry, exit and return

- **Entry:** `Cth07Screen(client: ...)` from the existing workspace; no new route.
- **Read sequence:** `settingsContext()` → `screen('CTH-07')`. The adapter verifies the server scope/read/lineage binding, then reads `chart.labels`, `chart.series[name,data]` and `trend_metadata`/`truth.trend`; every series must align to all labels.
- **Scope gate:** global definitions must be `GLOBAL/ALL`, `global_all` or `global` and carry the authorized global binding; focused definitions must match the returned Subject ID and authorized focus binding. Missing or mismatched scope blocks the chart.
- **Exit / return:** series chips and detail selection are local; there is no server-side metric/cohort mutation and no deep-link to a contribution source.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source/ViewModel field or callable | Definition / units / window | Freshness and missing-data behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Scope label | SYSTEM context read | `LumenisCoreClient.settingsContext()` | `GLOBAL_ALL` or applied CTH focus | Invalid/missing scope blocks; internal IDs hidden | — | Current context contract |
| P1 | Aligned series | CTH aggregate read | `_build_cth07()` chart `labels`, `series[name,data]` | Same time labels for every series; numeric values only | Unaligned/missing data or missing server authorization/lineage produces NOT_COLLECTED; no zero-fill | BACKEND-GAP-013 | Current aggregate source; canonical metric callable not bound |
| P1 | Definition rail | Metric owner UNKNOWN | `trend_metadata` or `truth.trend`: numerator, denominator, time_window, subject, source, freshness | All six fields required; units/window shown as returned | Missing/unsafe source means no chart | BACKEND-GAP-013 | Current server response lacks metadata |
| P1 | Change explanation | Metric/decomposition owner UNKNOWN | Local first-to-last difference only; contribution data is not returned | Numeric delta over the displayed window; not a cause | Show “贡献拆解暂未返回” when absent | BACKEND-GAP-013 | Current backend has no verified decomposition |
| BLOCKED | Add/remove metric or cohort | CTH trend/action owner UNKNOWN | ViewModel/action declaration only; no verified request/result | UNKNOWN | No controls or optimistic overlay | BACKEND-GAP-013 | `trend_api/canonical_metrics` UNKNOWN |

## 4. State and recovery matrix

| State | Trigger/evidence | User-visible meaning | Available actions | Recovery/return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Context/chart request pending | 正在加载趋势分析 | None | Announce; no line or table values | CTH07-W-001 |
| Empty / no series | Explicit empty chart state | 当前范围内暂无趋势记录 | Refresh | Do not build an empty/zero line | CTH07-W-002 |
| Not collected / definition missing | Chart arrays or definition absent | 趋势暂不可用，口径尚未完整返回 | Refresh | Keep raw arrays hidden | CTH07-W-003 |
| Fresh / stale | Source freshness field absent/returned | Only show returned freshness | None | Never infer “latest” from response time | CTH07-W-004 |
| Partial | One series misaligned or contribution missing | 趋势可读，但解释项暂缺 | Refresh | Render only complete aligned series; arithmetic delta may remain | CTH07-W-003 |
| Offline | Core/source failure | 暂时无法连接 | Retry | Failure is not zero | CTH07-W-005 |
| Blocked / permission denied | Invalid scope, `bound=false`, missing global grant/binding, or focused response without exact authorized binding; 401/403 | 经营主体信息暂不可用 | Retry after recovery | Do not reuse global trend for focus; do not render an unauthorized aggregate | CTH07-W-006 |
| Error | Malformed response/5xx | 运营信息暂不可用 | Retry | Hide raw details | CTH07-W-005 |
| Local series selection | Choose a compatible returned series | 查看所选指标 | Switch series | Preserve definition/window; no server effect | CTH07-W-007 |

## 5. Purpose-built desktop composition

- **Primary question:** what changed over the stated window, and what exactly does the metric measure?
- **Hierarchy:** scope/window → metric-definition rail → aligned chart and table → change/decomposition panel. Units/window remain adjacent to axes and values.
- **Wide desktop:** `cth07/desktop-layout` gives the definition a stable rail, the time-series canvas the main width and the decomposition panel a separate explanation region.
- **Keyboard:** series chips are focusable; Enter/Space selects; chart has an accessible label and synchronized data table; no chart-only meaning.
- **Screen identity:** definition-first trend analysis and explicit non-causal decomposition differentiate this from a generic line chart.

## 5A. Web Workspace composition and desktop-only capability boundary

- Web and desktop share the same series/definition model, table alternative and no-guessing rules. No client-side trend API or metric store is added.
- Metric/cohort controls, Evidence contribution links and export are unavailable until contracts bind.
- Runtime E2E must verify resize, keyboard series selection and truthful missing-definition state.

## 6. Purpose-built mobile composition

- **Active task:** choose one returned metric and understand its aligned values and window.
- **Layout:** chart/table first, metric switcher second, definition rail third, change explanation fourth; the selected metric remains visible.
- **Touch:** metric chips and retry meet 48 logical pixels; chart has a spoken label and the data table remains available.
- **Interruption:** no cached trend or pending metric change is represented. Retry repeats the read.
- **Screen identity:** one primary trend plus definition and delta explanation remains the organizing task, not a shrunken desktop grid.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read/write/external effect | Idempotency / reversal | Evidence emitted | Confirmation and failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Load context/trend | SYSTEM + CTH aggregate; actor/Subject binding UNKNOWN | Optional global auth; screen READ UNKNOWN | Read only | Repeatable | Returned series/definition only | Safe ready/not-collected/error state |
| Select returned series | Flutter local state | None | No server effect | Reversible | None | Enabled |
| Add/remove metric/cohort, inspect contribution, export | CTH metric/action/Evidence owners UNKNOWN | UNKNOWN | Potential write/read/export | UNKNOWN | UNKNOWN | No enabled controls |

## 8. Accessibility, motion and localization

- Every series chip exposes its label and selected state. The chart has a non-visual label and a synchronized data table with date/value text.
- Axis units/window and definition fields are plain text; color is not the only series distinction. Missing contribution state is announced.
- Loading, unavailable, empty and error states are live regions. No authored motion is required.
- The bounded UI uses existing `screen.CTH-07`, context, common, state and `cth01.*` keys; no hardcoded screen copy remains. Canonical l10n must add `cth07.definition_rail`, `cth07.series_switcher`, `cth07.chart_label`, `cth07.decomposition_missing`, `cth07.action_unavailable` and state copy in zh-CN/en/ko before acceptance, then replace the temporary generic mappings. No second l10n owner.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State/error path | Platform/input | Test layer | Current evidence/reference |
| --- | --- | --- | --- | --- | --- |
| CTH07-W-001 | Pending response announces loading and hides trend values | Loading | Widget | `app/test/features/cth/cth07/cth07_screen_test.dart` | Local evidence |
| CTH07-W-002 | Explicit empty trend does not create zero values | Empty | Widget | Widget test | Local evidence |
| CTH07-W-003 | Raw arrays without complete definition or alignment stay unavailable | Not collected/partial | Widget/repository | Widget + contract test | Current backend metadata gap |
| CTH07-W-004 | Definition shows numerator, denominator, window, Subject, source and freshness when returned; no inferred freshness | Definition/freshness | Widget/API | Contract test required | Adapter contract implemented |
| CTH07-W-005 | Offline/5xx/malformed response is safe and retryable | Offline/error | Widget | Widget test required | Safe copy implemented |
| CTH07-W-006 | Focused unbound or mismatched scope is blocked | Focus scope | Repository/widget | Repository test required | Current runtime focus gap |
| CTH07-W-007 | Select a series and retain chart/table/definition alignment without an effect | Local interaction | Widget; keyboard/touch | Widget test | Desktop/mobile evidence |
| CTH07-W-008 | A real new event feeds a source-backed trend with an honest definition and lineage | Real user work | Runtime/E2E | Required before ROUND-10 PASS | Not yet run |
| CTH07-W-009 | Return `bound=true` with chart arrays but no global grant/lineage; the repository blocks before decoding the trend | Global authorization/lineage block | Repository/widget | Repository test | Implemented hostile fixture |
| CTH07-W-010 | Return authorized `GLOBAL_ALL` and exact Guangzhou Taikoo Hui `FOCUS` definitions; only matching scope is rendered | Authorized global/focus read | Repository | Repository test | Implemented legal fixtures; contribution lineage still pending |

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for canonical trend analysis and ROUND-10 acceptance. The bounded implementation only draws a complete, scope-matching, definition-backed trend and labels missing decomposition honestly.
- **Open owners:** CTH metric owner must define the callable and units; Evidence must bind contribution/source lineage; SYSTEM must bind Subject read authorization; action owner must define metric/cohort requests; l10n must add three locales.
- **Required before acceptance:** real new data, complete trend definition, source freshness, Subject binding, non-zero/failure distinction, contribution lineage and desktop/mobile E2E.
