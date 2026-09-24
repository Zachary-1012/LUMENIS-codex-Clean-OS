# SYS-02 — Collector status

```yaml
screen_id: SYS-02
status: DESIGN_EXPLORATION
revision: 1
owner_domain: SYSTEM Collector
binding_ids:
  - BACKEND-GAP-037
product_owner_approval: PENDING
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
reviewer: Sol review required
reviewed_at: UNKNOWN
approval_reference: UNKNOWN
```

## 0. Authority basis and artifact disposition

- Constitution basis: SYSTEM collector blueprint, truthful state semantics, responsive recomposition, accessibility and §36 executable acceptance.
- Product contract: `SYSTEM Collector → Source/Evidence → Canonical Data`; this screen reports operational collection state only.
- External sketches, screenshots and taskbooks: `KEEP_AS_EXPLORATION`; none authorize layout or capability.
- Anti-template check: the primary composition is a platform-lane inspection with an ingestion-boundary explanation, not a generic KPI dashboard.
- Sol design decision: `DESIGN_EXPLORATION`; the implementation is a bounded candidate until reviewed.

## 1. User problem and product invariant

- Authorized context: SYSTEM operator permitted to read the current screen envelope.
- Real task: determine which collection lanes are verified, partial, missing or blocked, and whether a record may cross into Evidence/Canonical Data.
- Completion signal: the returned platform states and counts are visible with their source state; missing values stay unavailable.
- Out of scope: cookie/session inspection, collection control, retry/stop/compensation actions, and business truth.

## 2. Route, entry, exit and return

- Entry: App shell route for SYS-02; shell authentication remains the caller boundary.
- Read binding: `GET /api/experience/screen/SYS-02` → `experience_screens._build_sys02()` → `collector_status_api.get_all_status()`.
- Exit: return to the originating SYSTEM route; no drilldown route is verified.
- Return state: preserve shell origin and scroll position only; no Subject/Brand selection is changed.

## 3. Verified data and callable bindings

| Priority | UI field | Owner / source | Missing-data behavior | Binding / evidence |
| --- | --- | --- | --- | --- |
| P0 | Active/partial/missing/blocked counts | `truth.summary`; KPI ids `sys02.active`, `sys02.partial`, `sys02.missing`, `sys02.blocked` | Numeric value only when KPI state is `ready`; otherwise unavailable | BACKEND-GAP-037; `experience_screens.py::_build_sys02`; `sys02_snapshot.dart` |
| P0 | Platform lane | `sections[type=table].rows` fields `平台/状态/解析记录/说明` | Unknown status and unavailable record count remain explicit | BACKEND-GAP-037 |
| P1 | Ingestion boundary note | `sections[type=note]` | If absent, show binding-unavailable copy; do not infer Evidence acceptance | Collector closed-loop contract |

No pagination, write action, idempotency key, Evidence emission or cancellation contract is verified.

## 4. State and recovery matrix

| State | Meaning and UI | Action / recovery |
| --- | --- | --- |
| Loading | Reading current collector state; no placeholder counts | Wait or leave |
| Empty / not collected | No platform lane or metric returned | Read boundary explanation; do not show zero |
| Partial | Some lanes/counts returned, others unavailable | Refresh read route |
| Offline / error | Connection, malformed envelope or server failure | Retry only when the failure is retryable; clear stale snapshot |
| Blocked / permission denied | 401/403 access state | Return to authentication/access flow; no collector operation |
| Ready | Current returned states are shown | Read only; `ACTIVE` is not inferred from registration |

## 5. Purpose-built desktop and web composition

- Desktop: header and summary strip first; platform lanes occupy the primary inspection plane; ingestion boundary is a separate explanatory panel.
- Web Workspace: same Core/ViewModel semantics and keyboard navigation; no desktop-only capability is claimed.
- At tablet width, stack lanes and boundary; at phone width, keep one platform lane per row and preserve state/detail pairing.
- No charts are rendered because the endpoint supplies no time series.

## 6. Purpose-built mobile composition

- One active question: “what is the current collection state, and can it enter the truth chain?”
- Order: summary → platform lanes → ingestion boundary.
- Touch targets are provided by the shell/refresh affordance; no destructive action exists.
- Offline/error recovery returns to the same page and clears old values.

## 7. Actions, authorization and effects

| Action | Permission/effect | Evidence and failure |
| --- | --- | --- |
| Load current state | Existing screen GET; read only | No persisted Evidence; distinguish 401, 403, offline and malformed response |
| Retry read | Same GET only when retryable | No collector mutation and no fake success |

## 8. Accessibility, motion and localization

- Keyboard order follows summary, platform lane, state/detail and boundary explanation.
- Status uses text, icon and color; live failure/loading regions have semantic labels.
- No chart alternative is required; every metric has a textual unavailable state.
- zh-CN/en/ko copy must wrap at narrow widths; reduced motion suppresses non-essential transitions.

## 9. Executable acceptance

| ID | Acceptance | Test/evidence |
| --- | --- | --- |
| SYS02-STATE-01 | Ready zero is rendered as zero; offline/null is not zero | Flutter snapshot/widget tests |
| SYS02-BOUNDARY-01 | Registration/status does not become Evidence or Canonical acceptance | source binding review + widget test |
| SYS02-RESP-01 | Desktop, tablet and phone use distinct lane composition | Flutter widget tests |
| SYS02-RECOVERY-01 | 401/403/offline/malformed response show safe bounded states | ViewModel/widget tests; live HTTP still pending |
| SYS02-REAL-USER-01 | Operator opens SYS-02, reads one real returned lane, and can distinguish not-collected from zero | Requires authenticated runtime E2E at current commit |

## 10. Cross-cutting gates and review

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; this page does not select a business entity or report Global/Brand/Guangzhou coverage.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable; entity sample count is zero and no entity value is fabricated.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: research complete for this slice; no justified upgrade beyond the existing Collector closed-loop contract. Any future retry/effect must be versioned behind Permission, Evidence, observability and rollback.
- Decision: `DESIGN_EXPLORATION`; Sol must review the spec, verify the screen route and complete authenticated runtime acceptance.
