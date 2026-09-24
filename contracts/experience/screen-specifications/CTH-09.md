# CTH-09 — 风险与决策工作台

```yaml
screen_id: CTH-09
status: BLOCKED
revision: 1
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-015
  - BACKEND-GAP-016
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
artifact_disposition: BOUNDED_BLOCKED_STATE_IMPLEMENTATION_ONLY
reviewer: Codex bounded ROUND-11 Luna batch
reviewed_at: 2026-09-22
approval_reference: Product Owner approval of App / Experience Constitution §§30–36; this is not CTH-09 acceptance
```

## 1. User problem and product invariant

- **Role / context:** CTH operator working in `GLOBAL / ALL` or an authorized focused CTH Subject.
- **User task:** inspect the basis of a risk, review a separate decision ledger, and understand whether an action is merely proposed, awaiting approval or actually executable.
- **Completion signal for this bounded slice:** show risk and decision rows only when the response proves actor/context scope and trusted references. No control may execute a decision in this batch.
- **Invariant:** risk, insight, decision and action remain distinct. Severity is never conveyed by color alone, and a static action declaration is not authorization.
- **Current limitation:** the current screen builder returns risk notes with `NOTE:<id>` references and has no Decision record, write callable or actor-to-Subject Permission decision.

## 2. Route, entry and return

- **Entry:** nested CTH decision workflow from a Case or the CTH work surface. The shared route is outside this bounded path.
- **Required read binding:** the context contract must be valid and the screen response must include `binding.actor_scope=verified`, matching `context_mode`, `domain=CTH`, and `evidence_lineage=verified`. Focus mode must echo `subject_id`.
- **Exit / Trace / Return:** selecting a risk or decision is local state. Return restores the risk feed and selected row; no context switch or external effect is made.

## 3. Verified data and callable bindings

| Priority | UI field / action | Source / callable | Definition and missing behavior | Binding |
| --- | --- | --- | --- | --- |
| P0 | Risk register | CTH risk owner | Requires `risks[]`, stable risk ID, level, score when actually returned, description and trusted `evidence[]` | `BACKEND-GAP-015`, currently not scope/lineage safe |
| P0 | Decision ledger | CTH Decision owner | Requires `decisions[]`, owner/status, requested action and explicit action contract state | `BACKEND-GAP-016`, currently ABSENT |
| P1 | Source trail | Canonical Evidence owner | Only allowlisted IDs are displayed; `NOTE:<id>` is not Evidence | Current response cannot satisfy this |
| EFFECT | Confirm action | Permission + approval + Effect Fence + real result contract | Disabled unless all exact gates and a callable are present; this UI has no mutation client | Not bound |

Trusted CTH-09 reference IDs are `EV-7710`, `EV-7699` and `EV-7712`. Unknown or `NOTE:` references are withheld.

## 4. State and recovery matrix

| State | Trigger | User-visible meaning | Available action | Acceptance |
| --- | --- | --- | --- | --- |
| Loading | Read pending | 正在读取风险与决策 | None | CTH09-W-001 |
| Empty | Bound response contains no risk or decision rows | 当前范围内暂无待处理风险或决策。 | Refresh | CTH09-W-002 |
| Not collected | Risk/decision section absent | 风险或决策资料尚未接入。 | Refresh | CTH09-W-003 |
| Partial | Risk is present but some basis/action lineage is missing | 部分资料尚未完成核验，未核验依据不显示。 | Inspect safe rows; retry | CTH09-W-004 |
| Blocked | Scope, lineage or decision owner missing; 401/403 | 当前范围暂不能查看风险与决策。 | Retry; return | CTH09-W-005 |
| Offline / Error | Transport or malformed response | 暂时无法读取风险与决策，请稍后重试。 | Retry | CTH09-W-006 |
| Ready | Bound risk/decision payload | Show matrix/feed, ledger and selected basis | Local selection only | CTH09-W-007 |

## 5. Purpose-built composition

- **Desktop/Web:** a ranked risk register with score tracks and text severity on the left; a separate decision ledger with owner/status/effect readiness on the right; a selected-basis inspector below or beside them. This is not the CTH-08 case board.
- **Mobile:** a ranked risk feed, selected risk basis, then decision ledger. Each disabled action states why it cannot be executed.
- **Accessibility:** level, score and status are included in semantics; critical/high/medium/low text is always present; selection uses keyboard and touch; blocking/error states are live regions.

## 6. Actions, authorization and effects

| Action | Required proof | UI behavior |
| --- | --- | --- |
| Inspect basis | Bound read response and trusted reference | Enabled as local selection only |
| Record decision | Exact CTH Decision write callable, Permission decision, approval when required, Effect Fence admission and result contract | Disabled; no request is issued |
| Execute proposed action | Matching actor/domain/Subject scope, `PermissionResult.verification_state=verified`, approval token where required, staged/idempotent effect and observable result | Disabled; no optimistic success |

HTTP 200, `VERIFIED_AVAILABLE` in a JSON registry, a risk score or a button label is not authorization or effect success.

## 7. Executable acceptance

| Acceptance ID | Action / expected result | State path | Platform/input | Test layer |
| --- | --- | --- | --- | --- |
| CTH09-W-001 | Pending read hides risk/decision rows and announces loading | Loading | All widths | Widget |
| CTH09-W-002 | Bound empty response stays empty and does not use the fixture | Empty | Desktop/mobile | Widget |
| CTH09-W-003 | Missing Decision section is not-collected and no action control appears enabled | Not collected | All widths | Widget |
| CTH09-W-004 | Unknown/NOTE evidence and hostile fields are omitted | Partial / hostile input | All widths | Widget |
| CTH09-W-005 | Missing binding blocks the screen; every write/action control is disabled | Blocked | Desktop/mobile | Widget + repository |
| CTH09-W-006 | 401/403/offline/malformed response hides server detail and offers retry | Error | Desktop/mobile | Widget |
| CTH09-W-007 | Matrix/ledger desktop, tablet and mobile feed compositions recompose without overflow; Trace/Return preserves selection | Ready | 1440 / 900 / 390 logical px | Widget |

## 8. Review decision and open dependencies

- **Decision:** BLOCKED for full CTH-09 acceptance. The bounded implementation is read-only and fail-closed.
- **Required before DESIGN_READY / ACCEPTED:** canonical Decision owner and API, actor-to-Subject read/write Permission, approval token flow, Effect Fence/effect result contract, item-level Evidence lineage and runtime/E2E evidence.
- **Current disposition:** current risk notes and static action declarations cannot be shown as an authorized decision loop.
