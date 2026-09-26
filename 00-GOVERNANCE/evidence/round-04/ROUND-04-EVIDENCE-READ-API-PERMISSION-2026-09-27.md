# ROUND 04 — authenticated exact-scope Evidence read API (2026-09-27)

## Bounded Batch and source truth

- Base: published `origin/main` `79f46a7ab8aa49a7de2d733528a8e920be8d9696`. Sol reviewed the four isolated source/test files against that exact base; the intervening Product Owner collection-mode governance commit did not alter these paths. The shared dirty worktree was not used as source input and its unaccepted changes remain protected.
- Owner: existing Shared Evidence API/store and canonical SYSTEM actor-scope Permission. GET `/api/evidence/stats`, `/list`, `/<id>` and `/timeline` now require a server-authenticated actor, explicit CTH/BMP data-route context and verified exact `evidence/read` Permission before reading. BMP Subject IDs resolve through the canonical registry to BrandFocus IDs. Cross-scope detail returns 404; unavailable authorization/read returns 503. Replay POST authorization and effects are unchanged.
- The storage reader gains an internal stable keyset cursor so scoped pagination and exact-scope aggregation can read beyond 200 records without using the legacy unscoped query. Existing list equality filters apply after scope filtering. SQL NULL result/level/source counts are exposed separately in `null_counts`, never silently treated as zero or dropped.
- `GLOBAL_ALL` on these Evidence data routes requires a CTH or BMP domain and returns only explicitly global-marked Evidence in that domain. Its response says `EXPLICIT_GLOBAL_MARKED_EVIDENCE_ONLY`. This is **not** the authorized full Global Universe, its coverage, or an identity-free `GLOBAL / ALL` business ViewModel. The selection-only `/api/settings/context` contract is distinct.

## Verification on the exact candidate

- Clean `79f46a7` archive with only the reviewed Evidence API/store, two neighboring tests and this evidence/status update; process-scoped disposable `ZBC_DB_PATH` and `LUMENIS_TEST_SEED_DB`, cloud AI disabled. No production database, XHS session, browser profile, collector or running Core was used.
- `python -m py_compile` of the four changed Python files: exit 0.
- `python -m pytest -q -rA tests/test_permission_exact_resource_scope.py -k evidence_api`: **3 passed, exit 0**. The third case was Sol's independent global-grant/global-marker/no-silent-focus regression.
- `python -m pytest -q -rA tests/test_permission_exact_resource_scope.py tests/test_batch2_intel_security.py tests/test_evidence_scoped_write.py tests/test_evidence_replay_api.py`: exit 0, progress 100%, no failing cases, no background-thread leak. The suite includes 207 scoped rows across a cursor page, exact stats, CTH/BMP scope, global grant, denied/hidden detail, honest SQL NULL counts, read failure and replay preservation. The repository reporter did not print a total count for this combined run; do not infer one from the progress display. Expected injected failure logs are test evidence, not runtime failure.
- Constitution/static owner checks and staged whitespace/diff check must pass on the final candidate before commit. Push/fetch/live-remote verification is required before describing this Batch as online.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

- **REAL USER JOB / ENTRY / REAL INPUT:** an authorized worker opens Evidence for the selected Subject/BrandFocus or permitted domain-global scope. This Batch uses isolated fixture records and a test actor; no real user source was supplied.
- **END-TO-END PATH:** fixture scoped write → persisted Evidence → server-side actor-scope Permission → exact API read is tested. Running Core → real authenticated user → page/ViewModel → visible business result → recovery/return is **not verified**.
- **USER-VISIBLE RESULT:** no running product page was accepted. The published `ui_view_model.py` has an old unscoped `?range=` link, but no production caller was found; if activated, it fails closed and must be rebound under the current Context/Permission contract.
- **FAILURE/RECOVERY:** missing actor, missing/malformed scope, denied grant, hidden detail, failed authorization audit and store failure return distinct non-success states. Operational recovery in a running service is unverified.
- **ACCEPTANCE ASSERTION:** bounded security/API source Batch = `TESTED SOURCE`; `REAL USER WORK E2E=NO`; ROUND 04 remains `REWORK`. Do not promote this as Global data coverage or release completion.

## GLOBAL UNIVERSE / DATA MATURITY and commercial impact

No new source acquisition, baseline registry, freshness or mature entity coverage is established. Rotating real-entity sample count = 0 for this isolated security Batch. `Global Commercial Coverage=NO / NOT VERIFIED`, `Global Brand Coverage=NO / NOT VERIFIED`, `Guangzhou Taikoo Hui Reference Coverage=PARTIAL / NOT REVERIFIED`, `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`, `COMMERCIAL_READY=NO`. Default manual collection and opt-in automatic mode remain separate SYSTEM Collector work under the current Global contract.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

The current gap was a direct conflict between published broad GET routes and the already published exact Evidence storage reader/actor-scope Permission contract. Decision: **ADAPT** those existing owners; `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE` for an external library, duplicate Evidence store or new Permission owner. A future full authorized Global ViewModel needs per-record scope, coverage and real user E2E; it must not be inferred from this exact-global reader. Promotion requires the current canonical tests, live actor/page acceptance, observability and a reversible mainline rollback.
