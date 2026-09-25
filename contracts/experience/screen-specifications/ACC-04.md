# ACC-04 — Guard and recovery

```yaml
screen_id: ACC-04
status: DESIGN_READY
revision: 2
owner_domain: SYSTEM Permission / recovery boundary
binding_ids:
  - CODEX-ACC04-GUARD
product_owner_approval: APPROVED
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_READY
artifact_disposition: REVIEWED_RETURN_ONLY_BOUNDARY
reviewer: Sol root integration review
reviewed_at: 2026-09-26
approval_reference: ROUND-14A bounded implementation Task Card
```

## 0. User task and invariant

- User job: understand why a protected workspace action is unavailable and choose an honest recovery path.
- ACC-04 never issues credentials, grants access, retries a write, resets a session or invents a successful permission decision.
- Product-account deferral remains visible and distinct from Core transport auth and business Permission.

## 1. Route and fields

- Read route: `GET /api/experience/screen/ACC-04` via `CoreAcc04Repository`.
- Current runtime reports this target as unbound; the page must show unavailable rather than use AI-01, CTH or another screen as a permission bypass.
- Allowlist: `bound`, `source`, `guard.recovery_paths`, `guard.reason` and `generated_at`, all bounded and sanitized.

## 2. Recovery matrix

| State | Meaning | Permitted action |
| --- | --- | --- |
| Loading | guard read pending | Wait |
| Available | real guard contract returned | Use only returned host recovery callbacks |
| Unavailable / unbound | no screen contract | Recheck or return; no local grant |
| Blocked | server denied the guard read | Show denial and return/switch context if host supplies it |
| Offline / malformed | no trustworthy guard | Retry read; do not infer permission |

`retry`, `switch_context`, `request_access`, and `return` are labels only until a host callback and canonical Permission owner are provided.

## 3. Desktop/mobile and accessibility

- Desktop: guard explanation is primary, recovery paths are a clear secondary rail.
- Mobile: explanation first, recovery actions stack in server-returned order with 44px+ targets.
- Focus order, announcements and text labels distinguish unavailable, blocked and product-account-deferred; reduced motion is immediate.

## 4. Localization integration key list

Existing shared key: `screen.ACC-04`, `common.refresh`.

Feature keys: `acc04.guardUnavailable`, `acc04.guardBlocked`, `acc04.productAccountDeferred`, `acc04.recheck`, `acc04.switchContext`, `acc04.requestAccess`, `acc04.returnToWorkspace` for `zh-CN`, `en`, and `ko`. Local fallback copy is used in this bounded slice.

## 5. Executable acceptance

| ID | Acceptance | Current evidence |
| --- | --- | --- |
| ACC04-GUARD-01 | Preserve unbound guard as unavailable and sanitize reason | `acc04_feature_test.dart` |
| ACC04-EFFECT-01 | No recovery action creates a local grant or fake success | source review; host callbacks are optional and side-effect-free here |
| ACC04-REAL-01 | Hit a real denial, choose a real host recovery path and verify the protected route remains protected | Not run; requires live Permission/E2E |

## 6. REAL USER WORK / global / commercial overlay

- `REAL USER JOB`: a user encounters a real protected boundary, understands it and recovers through an authorized context or return path.
- `REAL INPUT`: live Permission/guard response and actual host recovery callbacks.
- `END-TO-END PATH`: protected route → ACC-04 → real denial/recovery → server recheck → return.
- `USER-VISIBLE RESULT`: honest blocked/unavailable/recovered state; never a fake grant.
- `FAILURE/RECOVERY`: preserve denial across retries and distinguish transport/auth from product Permission.
- `EVIDENCE`: guard response, permission audit and protected-route recheck.
- `ACCEPTANCE ASSERTION`: `BLOCKED_PENDING_LIVE_RUNTIME_E2E`.
- `RANDOM ENTITY DATA ACCEPTANCE`: sample count 0; no access decisions fabricated.
- `GLOBAL UNIVERSE / DATA MATURITY IMPACT`: none; this page reports authorization state only.
- `COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO` until denied and recovered real flows pass.

## 7. Continuous frontier research / review decision

- `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE` on 2026-09-22. Existing guard/Permission owners and explicit callback boundaries are sufficient; no new auth or recovery dependency is justified.
- On 2026-09-26, root reviewed the existing explanation/recovery composition as
  `DESIGN_READY` for return-only host navigation. The shell supplies Return to
  ACC-03 without changing the guard state, making a permission grant, retrying
  a write or exposing access-request/context-switch actions. Recheck remains
  the same guard GET. The guard binding and real authorized recovery flow stay
  `BLOCKED_PENDING_LIVE_RUNTIME_E2E`; returning to the map is not recovery proof.
