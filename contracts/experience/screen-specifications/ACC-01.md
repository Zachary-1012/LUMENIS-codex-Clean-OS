# ACC-01 — Workspace entry and account boundary

```yaml
screen_id: ACC-01
status: BLOCKED
revision: 1
owner_domain: SYSTEM / Experience entry
binding_ids:
  - CODEX-ACC01-RUNTIME-IDENTITY
product_owner_approval: APPROVED
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: NON_AUTHORITATIVE_UNTIL_SCREEN_REVIEW
reviewer: Sol acceptance required
reviewed_at: 2026-09-22
approval_reference: ROUND-14A bounded implementation Task Card
```

## 0. Authority and invariant

- The screen follows the Experience Constitution's quiet identity / entry surface. It is not a product-account sign-in page and does not create a new auth owner.
- Product account onboarding is deferred until after internal beta. Core transport authorization, product account identity and media-session authorization remain separate.
- The composition is purpose-built: one calm entry/status surface plus a separate boundary explanation, not a generic dashboard or repeated card template.
- Historical mockups and screenshots are non-authoritative and are not copied into the implementation.

## 1. User problem and route

- User job: confirm that the internal-beta workspace entry is available and continue through the host-provided route.
- Read route: `GET /api/experience/runtime/identity`, via `LumenisCoreClient.runtimeIdentity()`.
- No account creation, password, credential reset or external effect is exposed here.
- Continue is a host callback only. If the host does not supply a route, the button remains visibly unavailable; the page never claims navigation succeeded.

## 2. Verified fields and allowlist

| UI field | Source | Allowlist / missing state |
| --- | --- | --- |
| Entry status | `ok`, `runtime_guardian.overall` | `connected`/`healthy`, `degraded`, `unavailable`, `unknown`; `ok=true` alone never means connected |
| Current view label | `focus_context.display_name` | safe display text only; path, secret and provider-like values are discarded |
| Generated time | `generated_at` | bounded safe text; omitted when absent |
| Product account boundary | product policy | fixed statement that account is deferred; not inferred from Core auth |

The client never displays API paths, database names, server paths, tokens, cookies, provider/model identifiers or raw errors.

## 3. State and recovery matrix

| State | Meaning | Action |
| --- | --- | --- |
| Loading | Runtime entry is being read | Wait |
| Healthy / degraded | Runtime guardian explicitly reports the state | Continue only through host callback; refresh is host-owned |
| Unknown | Identity envelope is valid but the guardian does not explicitly report connectivity | Show unconfirmed state; do not infer a ready entry |
| Unavailable | Runtime did not confirm the entry | Retry the read; do not create a local account |
| 401 / 403 | Transport or screen access is not confirmed | Show the access-specific recovery copy; do not turn it into a product-account wall |
| Offline / error | Read failed or response was malformed | Retry; preserve no fabricated workspace state |

## 4. Desktop and mobile composition

- Desktop: bounded two-region surface, entry status first and the account boundary beside it; maximum width 1180px.
- Mobile: one vertical entry surface followed by the boundary explanation; controls remain full width and touch-sized.
- Keyboard order is heading → status → host continue → boundary statement. Focus is not moved into a nonexistent login form.

## 5. Authorization, effects, and accessibility

- Read authorization remains Core-owned. The screen does not interpret transport success as customer identity or business permission.
- `Enter` activates Continue only when the host callback exists; Escape / hardware Back returns to the host shell.
- Screen readers receive status labels and the account-boundary statement as text, not color alone. Long labels wrap at enlarged text sizes.
- Reduced motion uses immediate state changes.

## 6. Localization integration key list

Existing shared keys: `screen.ACC-01`, `common.refresh`.

Feature integration keys to register with the canonical l10n owner: `acc01.betaEntry`, `acc01.entryStatus`, `acc01.currentView`, `acc01.productAccountBoundary`, `acc01.enterWorkspace`, `acc01.hostReturnPath`, `acc01.accountAfterBeta` for `zh-CN`, `en`, and `ko`. The current bounded slice uses an explicit three-locale fallback map because shared l10n files are outside scope.

## 7. Executable acceptance

| ID | Acceptance | Current evidence |
| --- | --- | --- |
| ACC01-READ-01 | Parse only the runtime identity allowlist and preserve unknown/unavailable states; `identity.ok` alone cannot connect the runtime | `acc01_feature_test.dart` |
| ACC01-BETA-01 | Render the internal-beta entry without a global product-account wall | `acc01_feature_test.dart` widget test |
| ACC01-SAFE-01 | Hostile display metadata never reaches visible text | `acc01_feature_test.dart` |
| ACC01-REAL-01 | From a real App entry, read the live identity, continue through the host route, and observe the returned shell state | Not run in this bounded batch; runtime/E2E required |

## 8. REAL USER WORK E2E ACCEPTANCE / delivery card

- `REAL USER JOB`: internal-beta user opens the App, confirms the actual entry state, and enters the already authorized workspace without creating a product account.
- `REAL INPUT`: live Core identity response and the host's real continuation callback.
- `END-TO-END PATH`: App Shell → ACC-01 → runtime identity → host continuation → originating workspace.
- `USER-VISIBLE RESULT`: real status, explicit account boundary, and a real returned workspace or an honest unavailable state.
- `FAILURE/RECOVERY`: distinguish 401, 403, offline, malformed response and missing host route.
- `EVIDENCE`: current commit, live response, callback return, and no product-account side effect.
- `ACCEPTANCE ASSERTION`: `BLOCKED_PENDING_LIVE_RUNTIME_E2E`; widget/parser evidence is not commercial acceptance.
- `RANDOM ENTITY DATA ACCEPTANCE`: sample count 0 in this UI-only batch; no registry data fabricated.
- `GLOBAL UNIVERSE / DATA MATURITY IMPACT`: entry surface does not claim global data maturity; all data coverage fields remain not applicable.
- `COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO` until live entry/return and all target surfaces are verified.

## 9. Continuous frontier research / capability evolution

- `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE` for this bounded slice. Local Flutter 3.47.5 and the repository's existing responsive/accessibility patterns were inspected on 2026-09-22; no dependency or alternate auth surface is justified.
- Decision: `ADAPT` the existing Core client, `LayoutBuilder`, Material semantics and three-locale fallback; do not add a second account or runtime owner.
- Any future account capability must be versioned by the canonical identity/Permission owner and pass a new screen review, effect fence, E2E and rollback gate.

## 10. Review decision

Implementation is present but this specification remains `BLOCKED` until the screen-specific design gate, live runtime entry/return and target-surface acceptance are independently recorded. No product-account wall is authorized by this document.
