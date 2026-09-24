# ACC-03 — Workspace launch map

```yaml
screen_id: ACC-03
status: BLOCKED
revision: 1
owner_domain: SYSTEM shell / CTH / BMP / Shared AI entry map
binding_ids:
  - CODEX-ACC03-RUNTIME
  - CODEX-ACC03-CONTEXT
product_owner_approval: APPROVED
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: NON_AUTHORITATIVE_UNTIL_SCREEN_REVIEW
reviewer: Sol acceptance required
reviewed_at: 2026-09-22
approval_reference: ROUND-14A bounded implementation Task Card
```

## 0. User task and ownership

- User job: see the three approved workspace destinations, confirm the current view lens and choose an entry supplied by the host shell.
- CTH remains Subject-first, BMP remains Brand/Market-first and Shared AI remains derivative. ACC-03 owns spatial entry only; it owns no business data or duplicate navigation truth.
- The composition is a launch map with a current-view rail and startup checks, not a dashboard of invented health metrics.

## 1. Routes and fields

- `GET /api/experience/runtime/identity` → runtime entry state.
- `GET /api/settings/context` → current server-returned view label/mode.
- Launch destinations are static approved host entry descriptors (`CTH`, `BMP`, `AI`) until the shell supplies verified routes. A card tap calls `onOpen`; it does not claim navigation without a callback.
- Safe fields: `runtime_guardian.overall`, context mode and safe display name. Raw route, path, provider, token, error and implementation values are excluded.
- `identity.ok` alone does not prove a connected runtime. Missing guardian evidence remains `UNKNOWN`; a context payload is connected only when its `lumenis.context.v1` envelope is valid and marked selection-only. An invalid envelope is `UNAVAILABLE`, never connected.

## 2. States and recovery

| State | Meaning | Action |
| --- | --- | --- |
| Loading | runtime/context reads pending | Wait |
| Connected | runtime guardian or valid selection-only context explicitly confirms availability | Open only host-supplied destination |
| Degraded / unavailable | actual response reports it | Show per-check status; retry via host |
| Unknown | the guardian or context evidence is missing | Keep the unknown state visible; do not infer readiness |
| 401 / 403 | access is not confirmed | Return or go to ACC-02/ACC-04 through the host; no bypass |
| Missing callback | destination descriptor exists but host route is absent | Keep entry visibly unavailable |

## 3. Desktop/mobile and accessibility

- Desktop: launch map occupies the primary region; startup checks stay in a narrow secondary region.
- Mobile: destinations stack as a map-like sequence with current view above; each tile has a distinct domain label and 44px+ target.
- Keyboard order follows current view → CTH → BMP → AI → checks. Screen readers receive destination names and state text, not color-only dots.
- Reduced motion collapses directly to the selected host result.

## 4. Localization integration key list

Existing shared key: `screen.ACC-03`.

Feature keys: `acc03.commerce`, `acc03.brandMarket`, `acc03.aiTasks`, `acc03.currentView`, `acc03.startupChecks`, `acc03.openDestination`, `acc03.hostRouteUnavailable` for `zh-CN`, `en`, and `ko`. The bounded code uses a local fallback map pending canonical l10n integration.

## 5. Executable acceptance

| ID | Acceptance | Current evidence |
| --- | --- | --- |
| ACC03-MAP-01 | Build distinct CTH/BMP/AI destination descriptors from safe state | `acc03_feature_test.dart` |
| ACC03-SAFE-01 | Suppress hostile context labels and keep missing/invalid health evidence out of the connected state | `acc03_feature_test.dart` |
| ACC03-REAL-01 | Open a real destination, complete its return path and retain the selected view | Not run; requires host shell runtime E2E |

## 6. REAL USER WORK E2E / global impact

- `REAL USER JOB`: operator starts from the launch map, opens a real CTH/BMP/AI workflow and returns with the current view preserved.
- `REAL INPUT`: live runtime identity, live context, actual host route.
- `END-TO-END PATH`: shell → ACC-03 → host destination → target screen → return.
- `USER-VISIBLE RESULT`: actual target opens or an honest route-unavailable state appears.
- `FAILURE/RECOVERY`: no success claim without callback; 401/403/offline remain distinct.
- `EVIDENCE`: route/return trace, current view, permission result and downstream screen.
- `ACCEPTANCE ASSERTION`: `BLOCKED_PENDING_LIVE_RUNTIME_E2E`.
- `RANDOM ENTITY DATA ACCEPTANCE`: sample count 0; this map does not fabricate entity data.
- `GLOBAL UNIVERSE / DATA MATURITY IMPACT`: routing preserves the selected global/focus context but does not measure coverage.
- `COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO` pending target-surface route/return proof.

## 7. Continuous frontier research / review decision

- `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE` on 2026-09-22. Existing shell callbacks, LayoutBuilder and shared route owners satisfy the bounded gap; adding a router or route registry here would duplicate truth.
- Decision: `ADAPT` host navigation and current context owners. This specification remains `BLOCKED` until the screen-specific design gate and real route/return E2E pass.
