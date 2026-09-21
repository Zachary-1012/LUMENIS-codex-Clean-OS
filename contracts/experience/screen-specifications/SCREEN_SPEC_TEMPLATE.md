# <SCREEN-ID> — <Screen name>

```yaml
screen_id: <SCREEN-ID>
status: DESIGN_EXPLORATION
revision: 1
owner_domain: UNKNOWN
binding_ids: []
product_owner_approval: PENDING
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: PENDING
reviewer: UNKNOWN
reviewed_at: UNKNOWN
approval_reference: UNKNOWN
```

## 0. Authority basis and artifact disposition

- Constitution sections applied:
- Product/workflow contract applied:
- Audit PDF/taskbook/sketch/screenshot/Figma references (non-authoritative):
- For each reference: `KEEP_AS_EXPLORATION` / `REJECT` / `RESTATED_IN_THIS_SPEC`:
- Anti-template check: explain why this is not a generic dashboard/card grid/shared renderer:
- Sol design decision: `DESIGN_EXPLORATION` / `DESIGN_READY` / `BLOCKED`:

## 1. User problem and product invariant

- Role and authorized context:
- User's real task and completion signal:
- Owning domain and invariant (CTH Subject-first / BMP Brand-Market-first / Shared origin lineage / SYSTEM infrastructure-only):
- Explicitly out of scope:

## 2. Route, entry, exit and return

- Entry routes and required context:
- Authorization-dependent destination behavior:
- Exit and deep-link paths:
- Trace target and source position to restore:
- Return state (selected Subject/Brand, filters, tab, selection, scroll, zoom, route):

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source/ViewModel field or callable | Definition / units / window | Freshness and missing-data behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | |

List exact route/method, request and response fields, pagination/cancellation behavior, idempotency and implementation file. Mark unresolved items `UNKNOWN`; do not invent a route or metric.

## 4. State and recovery matrix

| State | Trigger/evidence | User-visible meaning | Available actions | Recovery/return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | | | | | |
| Empty / no source data | | | | | |
| Not collected | | | | | |
| Fresh | | | | | |
| Stale | | | | | |
| Partial | | | | | |
| Offline | | | | | |
| Blocked / permission denied | | | | | |
| Error | | | | | |
| Success / persisted | | | | | |

## 5. Purpose-built desktop composition

- Primary question and visual hierarchy:
- Layout regions and information relationships:
- Primary interaction and precise result:
- Secondary interactions and keyboard operation:
- Density/resize behavior and comparison needs:
- What makes this composition specific to this screen:

## 5A. Web Workspace composition and desktop-only capability boundary

- Browser-first task, URL/deep-link and keyboard/pointer behavior:
- Shared Product Core/ViewModel/state semantics:
- Desktop-only capabilities and honest state (`DESKTOP_REQUIRED` / `UNAVAILABLE` / other):
- Authorized handoff/task tracking and Return behavior:

## 6. Purpose-built mobile composition

- Single active task and context that stays visible:
- Navigation and back/Return behavior:
- Touch interactions and target sizing:
- What is summarized, deferred or expanded:
- Offline and interruption recovery:
- What makes this composition specific to this screen:

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read/write/external effect | Idempotency / reversal | Evidence emitted | Confirmation and failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| | | | | | | |

## 8. Accessibility, motion and localization

- Keyboard, focus order, focus restoration and shortcut behavior:
- Screen-reader names, hierarchy and dynamic announcements:
- Chart/table non-visual equivalents:
- Reduced-motion behavior and interruptibility:
- Chinese/English copy and long-text behavior:

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State/error path | Platform/input | Test layer | Current evidence/reference |
| --- | --- | --- | --- | --- | --- |
| | | | | Widget / API / integration / runtime E2E | |

Acceptance must prove the real owner callable, server-side authorization, original product behavior, lineage, success/error recovery and Trace/Return. A fixture or screenshot alone is insufficient.

## 10. Review decision and open questions

- Decision: `DESIGN_EXPLORATION` / `DESIGN_READY` / `BLOCKED`
- Reviewer and date:
- Open questions with owners and next action:
- Changes required before implementation:
- Acceptance evidence required after implementation:
