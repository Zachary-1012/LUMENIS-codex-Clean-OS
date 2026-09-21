# LUMENIS Subject Permission Audit — ROUND 05

> Task: `ROUND-05-B001 / LUNA-008-AUDIT`
> Baseline: `6a910598854dd0b7a7b4fd20aa4a6dc83fc652d8`
> Evidence date: 2026-09-21
> Status: **OWNER AND GAP AUDITED / IMPLEMENTATION NOT STARTED**

This audit maps the current actor, Subject context, registry, and Permission
owners. It is not implementation evidence and does not authorize a client,
request header, registry row, or content match to claim business read access.

## Current owner chain

- `lumenis.auth.service.get_current_user()` resolves the authenticated product
  actor from the existing account session. Core Basic transport authentication
  alone does not establish a product actor.
- `subject_context.py` builds request-local Product and Subject context and
  forces the protected CTH brand scope. Context selects and filters work; it is
  not an authorization decision.
- `subject_registry.py` owns Subject registration and selection metadata. Its
  GET route requires a product actor and filters visible CTH/BMP domains through
  `account.authorization.check_dual_domain_permission()`.
- `account/authorization.py` owns the persisted member authorization matrix.
  Its current decision uses actor, product, module, and action.
- `lumenis/system/security/permission.py` owns operation/risk/effect gates and
  coarse role/domain checks. It has no per-Subject read decision today.
- `experience_runtime.py` owns the current screen endpoints. CTH screen reads
  do not yet bind an authenticated actor to a canonical Subject read decision.

## Proven gaps

1. `v4_member_authorizations.data_scope` is stored but is not evaluated by
   `check_dual_domain_permission()`. The current result proves domain/module
   access only, not access to one Subject.
2. `SubjectContext.subject_id` is derived from a normalized brand key, while
   registry identities use their own `SUBJ-...` identifiers. No canonical,
   server-trusted mapping currently joins those identities.
3. Registry membership and `selection_only` visibility do not authorize the
   business data of a listed Subject.
4. Client-supplied `X-Domain-Id`, `X-Product-Id`, brand key, Subject ID, or UI
   state cannot establish actor authorization.
5. CTH GAP-005 through GAP-017 repeatedly lack actor-to-Subject read checks in
   addition to their separate data, Evidence, callable, or lifecycle gaps.
   Adding Permission alone must not mark those bindings complete.
6. Unknown actor, unknown Subject mapping, missing authorization state, and
   authorization-service failure must all fail closed.

## Frozen behavior

- Do not change `SUBJECT_WORDS`, `EXCLUDE`, or `subject_hit()` semantics.
  Content matching and query filtering remain separate from authorization.
- Do not turn media Cookie/session/browser state into a LUMENIS product actor.
- Do not restore a pre-beta global product-account wall.
- Do not create a second Subject Registry, Permission store, database owner, or
  screen-specific authorization authority.
- Do not create the absent GAP-016 Decision capability as a side effect of this
  permission slice.

## Test coverage truth

The taskbook suites exist:

- `tests/test_domain_context.py`;
- `tests/test_domain_context_switching.py`;
- `tests/test_api_domain_contract.py`;
- `tests/test_ai_permission_matrix.py`.

They cover context construction/switching, API contracts, and general
Permission behavior, but none proves per-Subject actor read authorization.
Relevant additional owner tests are `tests/test_subject_registry.py`,
`tests/test_permission_dual_domain.py`, `tests/test_request_domain_context.py`,
and `tests/test_subject_context_isolation.py`. New acceptance must cover no
actor, unknown mapping, no grant, cross-Subject denial, matching grant, owner
policy, and authorization-service failure.

## Next executable Batch

Implement one vertical server-side slice in the existing account authorization
owner:

1. define a canonical Subject scope representation and trusted mapping;
2. evaluate per-Subject `read` without weakening existing product/module
   decisions;
3. expose a typed fail-closed decision for CTH screen owners;
4. bind one existing CTH screen read path to that decision;
5. prove allowed, denied, unknown, cross-Subject, and unavailable outcomes with
   isolated tests before widening to GAP-005 through GAP-017.

The canonical checkout is currently serving port 8201 under an external
supervisor. Production-owner source must not be edited while an uncoordinated
restart could load an unvalidated intermediate state. The implementation Batch
therefore waits for an explicit safe execution window or an approved isolated
Git worktree; this audit itself made no runtime or database change.
