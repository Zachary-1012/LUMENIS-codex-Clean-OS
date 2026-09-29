# ROUND 04 — exact local workspace source confirmation

Base: `826916869370e5bd6e47d2542dbde50cd8cddb24`.
Status: bounded Permission implementation/test; no J or Round acceptance.

## REAL DELIVERY CARD / 真实用户工作闭环验收

The product's open local workspace can confirm one media import without an
account record. The existing Permission owner binds server-issued principal,
exact business scope, filename, observed size and SHA256. Client JSON cannot
create a principal. Mixed account/workspace identities are rejected; existing
integer-account resource hashes are preserved.

Prepare does not import media. Confirm creates only an exact short-lived grant;
cancel/expiry/revocation/closed workspace invalidates it without enabling generic
COMMIT or DB writes. A root review identified mutation of the grant dictionary
during lookup. Snapshot iteration and a two-grant regression now preserve the
unaffected grant when the other loses its registered scope.

## Current-snapshot verification

Frozen Git blobs checked by root:

- `permission.py`: `48db29ba0b297b64aa2d43103e9749a83cd2e424`
- `test_local_content_source_confirmation.py`: `330c352532b87bca09e3f61d32aecc565dd0fa94`

Worker's actual seven-file pytest invocation exited **0** (`functions.exec`
cell 113/completed wait, `PYTEST_EXIT_CODE=0`), with no background thread leak.
The output suppressed the numeric pytest summary. A separate collection found
271 tests; that count is not substituted for a printed passed-test summary.
Files: local workspace principal/read, exact resource scope, scope approval
binding, Permission gate, account content-source import and new local content
confirmation. Eight new cases cover lifecycle, old hash, forgery/mixed identity,
cross-scope, isolated cancel, closure/replay, expiry and grant iteration.

Root's dependent source/import/export/inspection group separately returned
**35 passed in 25.33s, exit 0** against these exact Permission bytes, using an
isolated DB with its account table removed and actual media encoding. These API
consumers are still local candidates in this Permission commit. AST, exact diff
and blocking Constitution are required before publication.

## Scope and remaining acceptance

GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; global coverage remains unverified.
COMMERCIAL OVERLAY IMPACT: no publishing, rights or commercial-readiness claim.
CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: reuse the already accepted
typed import/Permission owner; no new dependency or account-system design.
Recovery is verified at this owner's boundary; production App E2E and cumulative
restart/release acceptance remain pending. No production DB was changed.
