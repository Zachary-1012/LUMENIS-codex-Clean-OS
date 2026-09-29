# ROUND 07 — open local workspace media inspection

Base dependencies: principal `5f81f35e`, Artifact `b81b8726`.
State: TESTED API integration; live App import/edit/export remains unaccepted.

## REAL DELIVERY CARD / 真实用户工作闭环验收

Job: inspect a supplied media file in an explicitly selected CTH/BMP context
without a product account. Existing Experience runtime now exposes
`POST /api/experience/shared-skills/shared.content_project/inspect` with
`action_type=READ` and one existing-owner asset input. The server resolves exact
domain/product/Focus or GLOBAL and asks canonical Permission before opening media.
Open local requests use the sealed workspace principal; authenticated requests
retain their account path. No account ID, scope grant or file fact comes from AI.

Real ffprobe reads return fingerprint/media properties and honest unknown rights.
This endpoint neither fetches remote URLs nor imports/registers an Artifact.
Existing imported-source refs route through their scoped Artifact reader; that
reader's local-principal adaptation is still a dependent Batch.

## Verification

Final targeted suite: **15 passed in 2.34s, exit 0**, no background thread leak.
Tests use an explicit disposable DB seed, real generated WAV bytes/ffprobe,
strict Permission and real Flask request contexts. Cases cover CTH/BMP local
reads with account resolution deliberately forbidden; closed/remote/forwarded/
credential-bearing requests; mismatched domain/product/context; registered
BrandFocus revalidation; forbidden remote assets; missing files; restoration and
successful retry. Original bytes remain unchanged and Artifact rows remain empty.

Source: `experience_runtime.py` (151 added lines) and
`tests/test_content_media_inspection.py`. Current AST/diff and Constitution gates
passed. Runtime restart/App invocation has not yet been performed for this new
endpoint; test-client integration is not claimed as live user E2E.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: no records or coverage claims change.
COMMERCIAL OVERLAY IMPACT: no publishing, rights grant or release acceptance.
CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: adapt the frozen Content
candidate through current Permission and media owners, no new library or service.

Failure/recovery is checked within this API slice. J8 still owes cross-system
restart/recovery. Reverting this route/helper slice has no production-data effect.
