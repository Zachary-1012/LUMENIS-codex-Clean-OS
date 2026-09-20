# SYS-01 — Runtime health / RuntimeGuardian slice

```yaml
screen_id: SYS-01
status: APPROVED
revision: 1
owner_domain: SYSTEM / RuntimeGuardian
binding_ids:
  - BACKEND-GAP-036
product_owner_approval: APPROVED
reviewer: Codex source review under Product Owner direction
reviewed_at: 2026-09-20
approval_reference: Product Owner instruction to implement the approved App / UX plan and Experience Constitution §§30–36
```

This specification approves the **read-only RuntimeGuardian health slice**. It does not claim the complete dependency topology or latency series in the SYS-01 blueprint is implemented.

## 1. User problem and product invariant

- Role and authorized context: SYSTEM operator, after the App's current authentication boundary permits the GET request. This page reports infrastructure state only; it does not select a CTH Subject or BMP Brand/Market context.
- User task: understand the RuntimeGuardian overall state, Worker and dead-letter queue counts, reaper/circuit-breaker indicators, and when the health snapshot was sampled.
- Completion signal: current health values and sample timestamp are displayed with their real availability state. This read-only slice has no operation action or state transition.
- Owner/invariant: SYSTEM owns runtime infrastructure. Runtime health is operational state and must never be presented as CTH/BMP business truth.
- Explicitly out of scope: restarting/reloading workers, retrying DLQ items, changing breaker state, latency charts, App→API→database→adapter health claims, and persisted Evidence artifacts.

## 2. Route, entry, exit and return

- Entry: App shell route to SYS-01. Shell/authentication remains the caller boundary.
- Read route: `GET /api/experience/screen/SYS-01`. `experience_runtime.screen_viewmodel()` resolves the propagated builder in `experience_screens.SCREEN_BUILDERS` and returns its JSON envelope.
- Source chain: `experience_screens._build_sys01()` → `runtime_guardian.legacy_health_check()` → `RuntimeGuardian.get_instance("legacy").health_check()`.
- Exit: return to the originating SYSTEM navigation state. There are no drilldown routes verified by this slice.
- Trace/Return: show `runtime_guardian.timestamp`, guardian name and runtime source. The current endpoint has no historical sample/detail route, so it cannot open a prior snapshot. Preserve only the shell's origin route and scroll/focus state.

## 3. Verified data and callable bindings

| Priority | UI field | Current owner | Exact source/ViewModel field or callable | Definition / units / window | Freshness and missing-data behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Overall status | SYSTEM RuntimeGuardian | `truth.overall`; runtime item `总体状态.state/detail` | RuntimeGuardian health classification (`healthy`, `degraded`, etc.) | `truth.overall == null` or status `offline` means unavailable; never map it to healthy | BACKEND-GAP-036 | `runtime_guardian.py::RuntimeGuardian.health_check`; `experience_screens.py::_build_sys01` |
| P0 | Registered Worker count | SYSTEM RuntimeGuardian | KPI id `sys01.workers_total`, from `health_check().workers.total` | Count of workers currently returned by `list_workers()` | Display integer only when state is `ready`; display 0 only when the source returned numeric 0 and state is ready; otherwise unavailable | BACKEND-GAP-036 | `experience_screens.py::_build_sys01`; `tests/test_experience_runtime.py::test_sys01_unavailable_health_counts_are_not_reported_as_zero` |
| P0 | Failed Worker count | SYSTEM RuntimeGuardian | KPI id `sys01.workers_failed`, from `health_check().workers.failed` | Count with `WorkerStatus.FAILED`; not the sum of failed and dead | Same null/ready distinction as above | BACKEND-GAP-036 | Same as above |
| P0 | DLQ count | SYSTEM RuntimeGuardian | KPI id `sys01.dlq`, from `health_check().dlq.total` | RuntimeGuardian DLQ aggregate total | Same null/ready distinction as above | BACKEND-GAP-036 | `_build_sys01`; `runtime_guardian.py::RuntimeGuardian.health_check` |
| P1 | Reaper | SYSTEM RuntimeGuardian | Runtime item `name=reaper`, `state`, `detail`; source `health_check().reaper_running` | Whether this guardian's reaper loop is running | Use only when the health snapshot is complete; if the endpoint normalized missing data to a default, show unavailable rather than false | BACKEND-GAP-036 | `_build_sys01`; `RuntimeGuardian.health_check` |
| P1 | Circuit breaker OPEN / registered counts | SYSTEM RuntimeGuardian | Runtime item `name=熔断器`, `detail=open=N · registered=N`; source `health_check().circuit_breakers` | `open` counts entries whose state is `open`; `registered` is the number of breaker entries returned. | Hide if snapshot is incomplete or the runtime item is offline. | BACKEND-GAP-036 | Current `_build_sys01` filters breaker entries by `state == "open"` and separately returns `len(breakers)` |
| P1 | Guardian identity | SYSTEM RuntimeGuardian | Runtime item `name=guardian`, `detail`; source `health_check().guardian_name` | RuntimeGuardian instance name | `—` or absent is unavailable | BACKEND-GAP-036 | Same source chain |
| P0 | Sample timestamp | SYSTEM RuntimeGuardian | Runtime item `name=时间戳`, `detail`; source `health_check().timestamp` | ISO timestamp returned by the health check, distinct from the screen envelope's `generated_at` | Missing/`—` means sample time unavailable; do not substitute client time | BACKEND-GAP-036 | `RuntimeGuardian.health_check`; `_build_sys01` |

### Exact callable and effect

- `GET /api/experience/screen/SYS-01` has no request body, pagination, cancellation, idempotency key or write effect. The aggregate envelope includes `ok`, `screen`, `source`, `bound`, `sections`, `truth`, `binding` and `generated_at`.
- The current builder returns one `kpis` section containing the three count metrics and one `runtime` section containing overall, reaper, circuit-breaker, guardian and timestamp items.
- `app.py::_basic_auth` may require Basic/session authentication when auth is enabled. The GET route is not in the explicit CTH read-only GET allowlist. The route has no separate SYS-01 action permission check because the page defines no action.
- No Evidence record is emitted by this GET. RuntimeGuardian's timestamp and source name are operational provenance, not a persisted Shared Evidence artifact.
- `viewmodel.latency: number[]` and the fixture's dependency uptime / response chart are not backed by this RuntimeGuardian callable. They are excluded and remain unimplemented.

## 4. State and recovery matrix

| State | Trigger/evidence | User-visible meaning | Available actions | Recovery/return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | GET pending | Reading RuntimeGuardian snapshot | Wait or leave page | No placeholders or zero counts | SYS01-READ-01 |
| Empty / no source data | Bound response with known zero Worker/DLQ count | The returned source count is exactly zero | Read details | Render zero only for a numeric value whose KPI state is `ready` | SYS01-READ-02 |
| Not collected | Metric is null/notcollected or field missing | This health value was not supplied | Read other available fields | Keep unavailable distinct from zero | SYS01-READ-03 |
| Fresh | Runtime source timestamp is present | Show the timestamp returned by RuntimeGuardian | Read current snapshot | Do not claim a freshness SLA that is not in the contract | SYS01-READ-04 |
| Stale | No stale threshold is defined | Staleness cannot be classified | Reload only through the normal screen refresh mechanism | Do not infer stale from device clock | SYS01-READ-05 |
| Partial | Some KPI values are ready while others are null/offline, or sample timestamp/overall is absent | Show valid counts and mark affected runtime indicators unavailable | Return or retry GET | Do not interpret normalized `false`, `open=0`, `—` defaults as source facts when the sample is incomplete | SYS01-READ-06 |
| Offline | Network/Socket failure | Runtime state cannot currently be read | Retry GET | Clear old snapshot; never keep stale values under a live label | SYS01-READ-07 |
| Blocked / permission denied | HTTP 401 or 403 | Authentication is required or this account cannot read the endpoint | Return to shell authentication/access route; no operation action is offered | Keep 401 and 403 distinct | SYS01-AUTH-01 |
| Error | Non-2xx other than 401/403, malformed JSON, wrong screen id or runtime error | Runtime health could not be read | Retry GET | Show a bounded error state, no zero values | SYS01-READ-08 |
| Success / persisted | Not applicable: endpoint is read-only | Nothing is persisted by this screen | None | Do not show a success toast or imply a runtime mutation | SYS01-EFFECT-01 |

## 5. Purpose-built desktop composition

- Primary question: is RuntimeGuardian healthy, and which runtime counts or guardrails explain that state?
- At ≥1100 logical px of feature content after Shell navigation, use a vertical operational spine: overall state and source sample at the top; Worker/DLQ counts in the central inspection plane; reaper and circuit-breaker entry count in a narrow guardrail rail. Keep timestamp and guardian identity in the source rail.
- At 768–1099 logical px of feature content, keep the overall state pinned above the count surface; move guardrail details into a reversible inspector so the primary status remains visible.
- Use status text plus shape/label; never rely on color alone. A number is not colored as healthy unless its source state is ready.
- This composition follows operational dependency and failure inspection. It does not use the product KPI dashboard or prototype line chart.

## 6. Purpose-built mobile composition

- At ≤767 px, use a single fault-priority column: overall health first, then failed Worker and DLQ counts, then total workers, then reaper/breaker details and sample time.
- Unknown/offline indicators remain beside each metric, not collapsed into a generic empty page.
- Keep SYSTEM identity visible while scrolling. No destructive or recovery control is shown.
- Use touch-sized refresh/back controls only when supplied by the existing shell. Return to the same originating navigation location.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read/write/external effect | Idempotency / reversal | Evidence emitted | Confirmation and failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Load SYS-01 health | SYSTEM RuntimeGuardian; request governed by existing app authentication | GET; no SYS-01 operation permission is invoked | Read only | Safe to reload | None; timestamp is runtime telemetry provenance | 401 authentication, 403 access denial, offline and server errors have distinct states |
| Restart/reload/retry | Not implemented in this slice | UNKNOWN/not used | Would mutate runtime/DLQ state | No route or reversal contract verified | UNKNOWN | No corresponding control is rendered |

## 8. Accessibility, motion and localization

- Keyboard focus proceeds from overall state to counts, guardrails, guardian identity and timestamp; all text remains selectable.
- Announce overall state and read failure through semantic labels/live region. Each unavailable count includes “未提供/离线”, not just a dash or color.
- Counts and breaker-entry count are textual; no chart is needed for this slice.
- Motion is limited to state transitions and can be disabled for reduced-motion preference.
- Chinese/English labels wrap at narrow widths and 200% text size. Do not claim Korean localization until verified.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State/error path | Platform/input | Test layer | Current evidence/reference |
| --- | --- | --- | --- | --- | --- |
| SYS01-READ-01 | Read real SYS-01 envelope and map typed fields only | Loading / ready | All supported widths | Widget + source binding | `experience_runtime.screen_viewmodel`; `_build_sys01` |
| SYS01-READ-02 | A real integer zero remains visible as zero when its state is ready | Empty / zero | All widths | Widget | `tests/test_experience_runtime.py::test_sys01_status_is_not_a_numeric_kpi` |
| SYS01-READ-03 | Null/offline metrics render unavailable and never zero | Not collected / partial | All widths | Widget + API | `test_sys01_unavailable_health_counts_are_not_reported_as_zero` |
| SYS01-READ-04 | Show RuntimeGuardian source sample timestamp without substituting client time | Fresh / time absent | Desktop and phone | Widget | `RuntimeGuardian.health_check().timestamp` |
| SYS01-READ-05 | Do not add latency values or a chart without an owner callable | Unsupported latency | All widths | Snapshot/widget | ViewModel's latency declaration has no verified source |
| SYS01-READ-06 | Incomplete health response masks normalized fallback status/counts | Partial response | All widths | Snapshot/widget | `_build_sys01` normalizes missing data; frontend must fail closed |
| SYS01-READ-07 | Network error clears snapshot and exposes retry | Offline | Phone/desktop | ViewModel/widget | LumenisCoreClient socket exception contract |
| SYS01-AUTH-01 | 401 and 403 show different access states | Authentication / permission denied | All widths | ViewModel/widget | `app.py::_basic_auth` response contract |
| SYS01-READ-08 | Bad shape, wrong screen, and server error do not render health values | Error | All widths | Snapshot/widget | screen envelope validation |
| SYS01-RESP-01 | Desktop shows topology + inspector; mobile orders by failure priority | 1440/1024/390 logical px | Pointer/keyboard/touch | Widget + visual review | Constitution §§20, 31 and SYS-01 §36 |

## 10. Review decision and open questions

- Decision: `APPROVED` for this read-only RuntimeGuardian slice. The full SYS-01 dependency topology and latency series remain unimplemented and must not be represented by this page as complete.
- Product owner approval: inherited from the explicit approval of the overall App / UX plan and Experience Constitution §§30–36 on 2026-09-20; this implementation adds no product or recovery action.
- Confirmed binding: BACKEND-GAP-036 maps to `runtime_guardian.legacy_health_check()` through the current SYS-01 screen builder. The old `UNKNOWN`/`CODEX_VERIFY` statements are stale for this read aggregate.
- Remaining source limitations: `latency` has no verified callable; when health is missing, the builder normalizes some guardrail fields to strings such as `running=unknown` and `状态不可用`, without presence flags. The client must mark that group unavailable when the overall sample/timestamp is absent. The breaker detail format is `open=N · registered=N`; the two counts must remain distinct.
- No user approval is needed for read-only display. Do not add restart, retry, DLQ mutation, or breaker controls without an existing owner route and server-side permission contract.
- Acceptance required after implementation: local Flutter widget tests plus the existing isolated SYS-01 backend tests; runtime HTTP verification remains dependent on the current Core session/auth setup.
