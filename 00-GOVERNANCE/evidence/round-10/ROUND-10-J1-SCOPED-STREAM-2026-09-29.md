# J1 / ROUND 10 — Canonical records reach the scoped monitoring stream

Status: **LOCAL API VERIFIED; FRONTEND ACCEPTANCE IN PROGRESS; J1 PARTIAL**.
Base: `5653ee173dea8961112e5b7d1d2a5c8bb384d7dd`. This is a bounded read path,
not acceptance of ROUND 10 or the whole J1 data package.

## Existing owners and change

Canonical's existing signed scope validator now returns a safe provenance proof.
`list_scoped_canonical` reuses it for exact CTH/BMP reads through the shared
database connection. Bound parameters, strict domain/focus inputs and a 100-row
maximum keep a bounded query; candidate/scanned/rejected/returned counts and
truncation are explicit. Missing or tampered scope Evidence is withheld. Storage
and verifier failures propagate rather than returning a fabricated empty list.
The proof contains no headers, cookies, signing key or raw Evidence payload.

CTH03 authorizes each request through the existing local read or Actor scope
policy, then reads Canonical using a read-only connection. Its top-level
`lumenis.scope-read-binding.v1` describes the read decision; it is not an Evidence
proof copied from one arbitrary record. Every returned row retains its own
version-2 projection, source identity, stored exact Subject and HMAC verification.
The existing platform surface is retained; its status alone is not proof of
scoped metrics or collected coverage.

No risk or sentiment is presented as verified solely because a source's scope
verifies. Publication time stays separate from capture time. Window aggregates
remain unknown because this bounded stream does not prove a complete time window.

## Real local readback and failure/recovery

The actual product database returned:

| View | Candidates | Returned with verified scope | Withheld |
| --- | ---: | ---: | ---: |
| CTH GLOBAL | 94 | 91 | 3 |
| Guangzhou Taikoo Hui | 27 | 27 | 0 |
| Shenzhen MixC Luohu | 4 | 4 | 0 |

All focused rows matched their requested Subject. The three unassigned Shenzhen
Bay records remain withheld. Coverage is NOT_VERIFIED and freshness UNKNOWN;
partial date/quality data is displayed as partial rather than made complete.

Actual invalid-domain (400), missing-Subject (404), foreign-Origin (401), and
forwarded-request (401) probes returned no stream rows. A valid request immediately
after those failures returned the same 91 rows. The existing loopback supervisor
was restarted and reopened the same database. No collection, account provisioning,
Raw/Canonical/Evidence rewrite, migration, or business mutation was invoked.

## Automated verification

- Canonical read, signed scope persistence and injected-connection regression:
  20 tests passed, exit 0, against explicit disposable databases and the real
  Evidence signing/verification path. Includes tampering, cross-domain exclusion,
  strict scope inputs, limited scans, and verifier/storage failure.
- Full `tests/test_experience_runtime.py` regression: exit 0. Its isolated setup
  now explicitly opens the local viewing
  policy and creates the Canonical table; no assertion or gate was removed.
- `tests/test_cth03_scope_viewmodel.py`: 11 passed, exit 0. Covers actual Flask
  routing, denied reads before database access, local no-account initialization,
  per-row projection, unknown date/analysis/aggregates, failure sanitization and
  successful retry. Its projection inputs are isolated unit-test samples; actual
  signed production-source readback is recorded separately above.
- Frontend acceptance remains in progress. Test-only data does not count as
  product coverage or user E2E.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

Job: choose an actual commercial Subject, see its collected records with honest
missing state, switch to another Subject and return to GLOBAL without cross-scope
residue. Entry: CTH03 in the existing Flutter workspace. Real inputs: the product's
signed Canonical rows above. Result: scoped, traceable record projection, not a
completed decision/operating report. Evidence: actual API readback and each row's
stored scope proof; user-visible acceptance is being executed by the frontend
owner. Failure/recovery must include denied/offline reads, stale-view removal,
retry and return. Real source interaction/action/evaluation remain later Job work.

## GLOBAL UNIVERSE / DATA MATURITY IMPACT

No inventory or relation-review status advances. Global Commercial Coverage = NO /
NOT VERIFIED; Global Brand Coverage = NO / NOT VERIFIED; Guangzhou Taikoo Hui
Reference Coverage = PARTIAL. FULL_UNIVERSE_READY, RELEASED, OPERATING and
COMMERCIAL_READY remain NO. Bounded representative data may support J2/J3 before
all country inventory work completes, as authorized by the Product Owner.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

REUSE the existing Canonical/Evidence/Permission owners instead of restoring the
old broad anonymous projection candidate. The preserved old candidate remains
historical input. No dependency or truth store added. COMMERCIAL OVERLAY IMPACT:
source provenance and a visible record are not an independent truth judgement,
data license, marketing result, or commercial readiness claim.
