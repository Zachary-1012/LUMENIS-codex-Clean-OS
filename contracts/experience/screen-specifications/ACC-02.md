# ACC-02 — Subject and view-lens selection

```yaml
screen_id: ACC-02
status: DESIGN_READY
revision: 2
owner_domain: SYSTEM settings / CTH Subject Registry selection
binding_ids:
  - CODEX-ACC02-CONTEXT
  - CODEX-ACC02-SUBJECT-REGISTRY
product_owner_approval: APPROVED
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_READY
artifact_disposition: REVIEWED_BOUNDED_SELECTION_CONTINUATION
reviewer: Sol root integration review
reviewed_at: 2026-09-26
approval_reference: ROUND-14A bounded implementation Task Card
```

## 0. Authority and invariant

- ACC-02 is a Subject-first selection surface. A selection changes the current view lens only; it never grants permission, changes ownership or rewrites Canonical Truth.
- The server remains the owner of context and Subject authorization. A local list or cached selection cannot substitute for server confirmation.
- The desktop split list/detail and mobile two-stage flow are specific to selecting and confirming a Subject, not a generic settings card grid.

## 1. Routes and callable contract

- Read current view: `GET /api/settings/context` via `settingsContext()`.
- Read CTH directory: `GET /api/settings/subjects?domain_id=CTH` via `settingsSubjects(domainId: 'CTH')`.
- Confirm focus: `PUT /api/settings/context` with `{mode: FOCUS, domain_id, subject_id}` via `selectContext()`; the server rechecks access and returns the context envelope.
- Exit returns to the host shell with the server-confirmed selection. No local grant or direct business-data fetch is performed.

## 2. Verified fields and allowlist

| UI field | Source | Rule |
| --- | --- | --- |
| Context mode | `context.mode` | `GLOBAL_ALL` / `FOCUS`; otherwise unavailable |
| Current view label | `context.display_name.zh/en` | safe bounded text only |
| Subject id | `subject_id` / `id` | `[A-Za-z0-9._:-]+`, bounded length |
| Subject name/type/domain | Subject row | safe text; domain only CTH/BMP; invalid rows hidden |
| List state | response `ok`, list presence, error class | empty, unavailable and blocked remain distinct |

Paths, tokens, provider/model strings, raw errors and arbitrary domains are never rendered.

## 3. State and recovery matrix

| State | Meaning | Action |
| --- | --- | --- |
| Loading | Context and directory reads are pending | Wait |
| Ready | Server returned safe Subject rows | Search, select, confirm |
| Empty | Server confirmed an empty directory | Show empty, not access failure |
| Blocked | 401/403 or permission denial | Retry or return; do not show a local Subject |
| Unavailable | timeout, malformed rows or partial dependency failure | Refresh the affected read |
| Confirming | `PUT` is in flight | Disable duplicate confirmation and show progress |
| Confirmation error | server rejected or failed the selection | Keep the previous server state and show recovery copy |

## 4. Desktop and mobile composition

- Desktop at ≥1000px: bounded list and confirmation detail side by side, with the context banner above both.
- Narrow layouts: searchable Subject list has a bounded 300px viewport, followed by confirmation detail in one scroll flow; no unbounded flex list is used.
- Keyboard order is context banner → search → returned rows → selected Subject → confirm → continue. Rows are reachable by keyboard and have visible selected state.

## 5. Authorization, effects, and accessibility

- The `PUT` is the only effect and is Core/SYSTEM-owned. It must pass existing auth and server reauthorization.
- Selection is not permission. Denied or pending responses do not update the UI to the requested Subject.
- Announce list count, selected row and confirmation result; do not rely on color. Search and controls remain usable at enlarged text sizes.

## 6. Localization integration key list

Existing shared keys: `screen.ACC-02`, `common.search`, `common.refresh`.

Feature integration keys: `acc02.availableSubjects`, `acc02.confirmLens`, `acc02.globalView`, `acc02.focusedView`, `acc02.subjectListEmpty`, `acc02.subjectListBlocked`, `acc02.subjectListUnavailable`, `acc02.serverConfirmation`, `acc02.confirmSelection` for `zh-CN`, `en`, and `ko`. Current code keeps local fallback copy pending shared-l10n integration.

## 7. Executable acceptance

| ID | Acceptance | Current evidence |
| --- | --- | --- |
| ACC02-PARSE-01 | Keep only safe CTH/BMP Subject rows and retain empty vs blocked | `acc02_feature_test.dart` |
| ACC02-SELECT-01 | Confirm selection through the repository and reload server state | `acc02_feature_test.dart` view-model test |
| ACC02-RESP-01 | No overflow at phone width; desktop uses the two-region composition | static responsive implementation; widget/E2E still required |
| ACC02-REAL-01 | Select a real non-reference Subject, confirm, return to the real workspace and verify downstream context | Not run in this bounded batch |

## 8. REAL USER WORK E2E / data card

- `REAL USER JOB`: an authorized operator chooses a real Subject from the server registry and confirms the view lens before using CTH work.
- `REAL INPUT`: live context envelope, live Subject Registry rows, selected non-reference Subject.
- `END-TO-END PATH`: shell → ACC-02 → context/directory reads → server-confirmed PUT → return → CTH consumer read.
- `USER-VISIBLE RESULT`: selected Subject is visibly server-confirmed; denial remains denial.
- `FAILURE/RECOVERY`: preserve previous state on 401/403/offline/server error; never fabricate a Subject.
- `EVIDENCE`: request/response, permission decision, return state and downstream Subject header.
- `ACCEPTANCE ASSERTION`: `BLOCKED_PENDING_LIVE_RUNTIME_E2E`.
- `RANDOM ENTITY DATA ACCEPTANCE`: sample count 0 here; future acceptance must rotate non-reference commercial/brand/cross-region registry rows.
- `GLOBAL UNIVERSE / DATA MATURITY IMPACT`: selection supports GLOBAL/ALL and focus-only semantics but does not assert collection maturity; report coverage separately.
- `COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO` until real selection/return is proven on promised surfaces.

## 9. Continuous frontier research / capability evolution

- `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE` on 2026-09-22 after inspecting the current Core client, Subject Registry contract and local Flutter 3.47.5 responsive patterns. No new state-management or directory dependency is justified.
- Decision: `ADAPT` existing context/Subject owners; no parallel registry, client permission cache or navigation contract.
- Any later multi-select, creation or access-request action requires canonical owner and permission/effect review; this slice remains selection-only.

## 10. Review decision

The existing list/detail composition is reviewed as `DESIGN_READY` for bounded
selection continuation. Continue opens the existing ACC-03 launch map only
when the selected domain and Subject match the server-confirmed focused
context, no confirmation is pending and no confirmation error remains.
Any in-flight selection disables duplicate confirmation and continuation,
including after selecting another row. Leaving the page cannot notify a
disposed view model. The shell displays the client's latest confirmed context
on continuation; no local permission or business effect is introduced.
Real authorized selection/return E2E and target-surface acceptance remain
unaccepted until independently recorded. GLOBAL/ALL remains the default;
this chooser is optional and is not a mandatory entry gate.
