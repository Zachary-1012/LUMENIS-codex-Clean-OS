# CTH-08 — 案例工作台与可复用知识

```yaml
screen_id: CTH-08
status: BLOCKED
revision: 1
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-014
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
artifact_disposition: BOUNDED_BLOCKED_STATE_IMPLEMENTATION_ONLY
reviewer: Codex bounded ROUND-11 Luna batch
reviewed_at: 2026-09-22
approval_reference: Product Owner approval of App / Experience Constitution §§30–36; this is not CTH-08 acceptance
```

## 1. User problem and product invariant

- **Role / context:** CTH operator in either `GLOBAL / ALL` or an authorized CTH Subject focus. Selection changes working context only; it never grants access or changes ownership.
- **User task:** inspect an authorized Case, follow its Case → Insight → Decision → Action → Outcome history, and distinguish reviewed reusable knowledge from the live Case.
- **Completion signal for this bounded slice:** render only a source-backed case payload that carries the exact scope and lineage binding below. Otherwise show a blocked, empty or not-collected state without fixture rows.
- **Invariant:** a Case is a working context, not a relabeled risk note or event row. Knowledge is a reviewed conclusion and never overwrites the original Case facts.
- **Current limitation:** `experience_screens._build_cth08()` returns high-risk notes and curated events, not canonical Case IDs, lifecycle state or actor-to-Subject lineage. The App must not promote those rows into Cases.

## 2. Route, entry and return

- **Entry:** nested CTH workflow from the CTH work surface. The bounded screen is directly instantiable while the shared shell route remains outside this batch.
- **Required read binding:** `GET /api/settings/context` must return `lumenis.context.v1`, `selection_only=true`, and either `GLOBAL_ALL` or `FOCUS` for domain `CTH`. The subsequent `GET /api/experience/screen/CTH-08` response must return `binding.actor_scope=verified`, `binding.context_mode` matching the selection, `binding.domain=CTH`, and `binding.evidence_lineage=verified`. Focused responses must echo the authorized `subject_id`.
- **Exit / Trace / Return:** selecting a case is local presentation state. Return restores the case board/list position and selected case. No context mutation, Case write, knowledge promotion or external action is implemented.

## 3. Verified data and callable bindings

| Priority | UI field / action | Source / callable | Definition and missing behavior | Binding |
| --- | --- | --- | --- | --- |
| P0 | Scope banner | `settingsContext()` plus the screen binding | Show `GLOBAL / ALL` or a safe focused display name; never use a Subject ID as an authorization claim | Required before any Case data is rendered |
| P0 | Case rows | Future CTH Case owner via `screen('CTH-08')` | Requires `cases[]` with `id`, `title`, `state`, `summary`, `timeline[]` and trusted `evidence[]`; high-risk notes/events are not accepted | `BACKEND-GAP-014`, currently missing |
| P1 | Case timeline | Same Case owner | Each step must identify a workflow stage and observed state; no fabricated completion | Unknown until canonical Case lifecycle exists |
| P1 | Knowledge shelf | CTH/Shared reviewed-learning owner | Requires reviewed item, source Case and trusted evidence reference; not the same list as active Cases | Unknown until owner and lineage exist |
| DRAFT | New Case | `CTH-08.new-case`, `case:write` | Opens no durable write in this batch | Disabled: no Permission, effect fence or result contract is bound |

Trusted CTH-08 reference IDs are allowlisted as `CASE-221` and `EV-7710` for this bounded renderer. Any other reference is omitted and shown as unavailable, never echoed as raw input.

## 4. State and recovery matrix

| State | Trigger | User-visible meaning | Available action | Acceptance |
| --- | --- | --- | --- | --- |
| Loading | Context or screen read pending | 正在读取案例工作台 | None | CTH08-W-001 |
| Empty | Bound response has `cases=[]` and a valid Case contract | 当前范围内暂无可查看案例。 | Refresh | CTH08-W-002 |
| Not collected | Bound response has no Case/knowledge section | 案例资料尚未接入，暂无可核验的生命周期记录。 | Refresh | CTH08-W-003 |
| Partial | Some rows lack trusted references or timeline fields | 部分案例资料未完成核验，未核验内容不显示。 | Refresh | CTH08-W-004 |
| Blocked | Missing actor/context/lineage binding, 401 or 403 | 当前范围暂不能查看案例资料。 | Retry; return | CTH08-W-005 |
| Offline / Error | Transport or malformed response | 暂时无法读取案例资料，请稍后重试。 | Retry | CTH08-W-006 |
| Ready | Bound Case payload | Display lifecycle board, selected timeline and separate knowledge shelf | Local selection only | CTH08-W-007 |

## 5. Purpose-built composition

- **Desktop/Web:** lifecycle board/list on the left, selected Case timeline and source trail inspector on the right, with a separate verified-knowledge shelf below. The board is not a generic table or renamed dashboard card set.
- **Mobile:** ranked Case inbox first, then the selected step-by-step timeline, source trail and knowledge shelf. Board columns collapse into explicit state labels.
- **Accessibility:** state is conveyed by text and icon plus color; case rows have one semantic label containing title, state and risk; Enter/Space selects; Escape returns to the inbox; loading/blocking states are live regions.

## 6. Actions, authorization and effects

| Action | Permission / effect | UI behavior | Evidence |
| --- | --- | --- | --- |
| Read Case | Server-side actor + CTH scope + lineage binding | Render only after all bindings pass | Trusted allowlist only |
| Select / Return | Local presentation state | Enabled and reversible | No write or new Evidence |
| New Case | `case:write` plus exact write result and Effect Fence | Disabled; no request is issued | None |
| Promote knowledge | No verified owner or approval contract | Not shown as an executable control | None |

HTTP 200, a static action registry row, fixture content or a plausible title is not business success.

## 7. Executable acceptance

| Acceptance ID | Action / expected result | State path | Platform/input | Test layer |
| --- | --- | --- | --- | --- |
| CTH08-W-001 | Pending repository keeps Case and knowledge rows hidden and announces loading | Loading | All widths | Widget |
| CTH08-W-002 | Bound response with no Cases is an empty state, not fixture fallback | Empty | Desktop/mobile | Widget + repository |
| CTH08-W-003 | Missing Case section is not-collected and does not relabel notes/events | Not collected | Desktop/mobile | Widget |
| CTH08-W-004 | Unknown Evidence IDs and hostile fields never render | Partial / hostile input | All widths | Widget |
| CTH08-W-005 | Missing scope or lineage binding blocks all Case data and disables New Case | Blocked | Desktop/mobile | Widget + repository |
| CTH08-W-006 | 401/403/offline/malformed response keeps internal server text hidden and offers retry | Error | Desktop/mobile | Widget |
| CTH08-W-007 | Desktop board, tablet list and mobile inbox/timeline recompose without overflow; Trace/Return restores selection | Ready | 1440 / 900 / 390 logical px | Widget |

## 8. Review decision and open dependencies

- **Decision:** BLOCKED for full CTH-08 acceptance. The bounded implementation is limited to a source-contract guard and purpose-built read-only composition.
- **Required before DESIGN_READY / ACCEPTED:** canonical Case owner, actor-to-Subject read decision, Case lifecycle payload, reviewed knowledge owner, trusted Evidence resolution, write Permission, Effect Fence admission, result contract and runtime/E2E evidence.
- **Current disposition:** no fixtures, high-risk note IDs or curated event IDs are presented as Cases.
