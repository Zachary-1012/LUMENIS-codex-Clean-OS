# ACC-02 — Subject and view-lens selection

```yaml
screen_id: ACC-02
status: DESIGN_READY
revision: 3
owner_domain: SYSTEM settings / CTH Subject Registry selection
binding_ids:
  - CODEX-ACC02-CONTEXT
  - CODEX-ACC02-SUBJECT-REGISTRY
product_owner_approval: APPROVED
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_READY
artifact_disposition: REVIEWED_BOUNDED_SELECTION_CONTINUATION
reviewer: Sol root integration review
reviewed_at: 2026-09-28
approval_reference: R14-ACC02-LAYERED-SELECTION bounded Task Card
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
- Narrow layouts: the searchable list is the browsing stage. Selecting a returned Subject opens a focused confirmation layer; the list, search and scroll position remain underneath for Return. Detail is not appended beneath a long list.
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

The existing list/detail ownership is reviewed as `DESIGN_READY` for bounded
selection continuation, with the interaction revision below. Continue opens the existing ACC-03 launch map only
when the selected domain and Subject match the server-confirmed focused
context, no confirmation is pending and no confirmation error remains.
Any in-flight selection disables duplicate confirmation and continuation,
including after selecting another row. Leaving the page cannot notify a
disposed view model. The shell displays the client's latest confirmed context
on continuation; no local permission or business effect is introduced.
Real authorized selection/return E2E and target-surface acceptance remain
unaccepted until independently recorded. GLOBAL/ALL remains the default;
this chooser is optional and is not a mandatory entry gate.

### Shared scope-picker recovery — 2026-09-27

Sol review: `DESIGN_READY` for the bounded recovery of the shell's existing
GLOBAL/FOCUS selector. This does not widen ACC-02's CTH directory or enable a
new business action. The shared selector retains its CTH/BMP focus support.

When a current-context read fails, the message remains unavailable or denied.
If the shell has a previously server-confirmed FOCUS envelope, offer the
existing clear action without displaying cached domain/Subject rows as newly
authorized. Call `LumenisCoreClient.clearContext()` (`DELETE
/api/settings/context`); only a validated GLOBAL_ALL response updates the
shell and closes the selector. A failed or denied clear retains the failure
state and must not claim GLOBAL. No previously confirmed focus means no
cache-derived recovery control. An in-flight clear disables conflicting
requests and duplicate submission. Selection/clear never invokes collection.

Verification: CTH and BMP expired-focus recovery, clear denial, no known focus,
and in-flight action controls in the existing shell tests. Real server-bound
recovery remains `LIVE_NOT_VERIFIED` until the safe Core environment is ready.

### Search/list recovery review — 2026-09-28

Sol review: `DESIGN_READY` for bounded repairs to the existing chooser. The
mobile list must scroll independently so every returned Subject can be
reached; the wide split composition remains. Search has a labelled clear action
that restores the returned list without changing focus or sending a mutation.
Blocked/unavailable/unknown list states do not display a numeric zero and disable
search. Partial read failure offers a retry through the existing repository,
with no duplicate retry during confirmation. Empty and no-search-match remain
separate states. State explanations, long names, retry and confirmation controls
must remain readable/reachable at 320 px and 200% text, including wide-window
enlarged text. Retry never grants permission or confirms a locally selected row.

This review does not widen the CTH-only directory API, add entity registration,
invent country/relationship fields or alter GLOBAL/FOCUS/Permission. Those
approved product requirements remain with their canonical contracts and future
bindings. Account/password design stays deferred until product closure reaches
100%; there is no new account wall. The public product default remains GLOBAL.

Research accessed 2026-09-28: official Flutter
[ListView](https://api.flutter.dev/flutter/widgets/ListView-class.html) and
[TextField](https://api.flutter.dev/flutter/material/TextField-class.html)
references, checked against the installed Flutter 3.47.5 SDK (BSD-3-Clause,
actively maintained upstream). ADAPT existing bounded scrolling and text controls;
no package upgrade, new design system or copied visual assets. The capability
locator found no separate historical research for `ACC-02`; the reviewed current
spec and existing implementation remain the applicable design inputs.

Acceptance: long-list last-row selection, clear-search restoration, actual retry,
unknown-count suppression and enlarged-text recovery; synthetic widget rows are
regression evidence only. Real authorized selection through the workspace and
native-surface acceptance remain separate required gates.

### Layered selection interaction — 2026-09-28

Sol review: `DESIGN_READY`, implementing the Product Owner's explicit instruction
to use meaningful hierarchy, direct manipulation and motion instead of treating
every mobile task as a vertical settings page. This is a revision of the same
Subject-selection job under Constitution §§32 and 36, not a new surface family.

- **Phone / compact window:** browse the actual searchable directory; tap a row
  to open the Subject confirmation sheet. Keep the originating list mounted.
  Within that sheet, horizontal paging compares the filtered returned Subjects,
  with explicit Previous/Next controls for keyboard and assistive users. A visible
  position label describes the candidate set, never collection coverage. Closing
  or Back returns to the same query/scroll position and performs no write.
- **Wide window:** retain the searchable directory beside the selected Subject
  inspector. Selecting a different row changes that inspector with a short
  directional transition. Outgoing content cannot receive input. The inspector
  remains usable for long names and enlarged text; no fixed-height overflow.
- **Action hierarchy:** browsing/paging changes only a local candidate. Confirm
  invokes the existing repository exactly once; Continue stays disabled until
  the live server context matches the shown candidate and no operation/error is
  pending. During confirmation, paging and duplicate confirmation/retry are
  disabled. A response for another candidate never enables Continue. Dismissal
  does not pretend to cancel a server write already sent.
- **Motion thesis:** list → candidate layer → confirmed context → Return. Use
  the existing shell's 180 ms / ease-out-cubic vocabulary for short disclosure
  and selection feedback. Respect `MediaQuery.disableAnimations`; reduced motion
  removes spatial travel while retaining immediate selection and status feedback.
  No idle pulse, decorative particle system, forced scroll or fabricated progress.
- **Reachability:** fixed visible Close/Return and action region, safe insets,
  content scrolling within the detail layer, 320 px / 200% text, accessible names
  in Chinese/English/Korean. Drag is an optional equivalent of labelled controls.

Interaction acceptance adds: open → swipe/Next → confirm exact candidate → server
response → Continue; cancel/Back preserves query and list position; denied writes
retain the candidate and retry; rapid actions cannot overlap; reduced-motion and
wide/phone transitions remain operable. Widget fixtures prove controls only.
Authorized real-registry selection and native OS acceptance remain required.

Research accessed 2026-09-28: official Flutter
[PageView](https://api.flutter.dev/flutter/widgets/PageView-class.html),
[modal sheet](https://api.flutter.dev/flutter/material/showModalBottomSheet.html)
and [reduced-motion query](https://api.flutter.dev/flutter/widgets/MediaQuery/disableAnimationsOf.html).
ADAPT Flutter 3.47.5 primitives already available in the app; BSD-3-Clause,
maintained by Flutter. No external UI assets, library or provider is introduced.
