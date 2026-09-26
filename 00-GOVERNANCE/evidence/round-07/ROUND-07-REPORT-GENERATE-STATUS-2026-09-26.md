# ROUND 07 — report generation result truth

Sol decision: `PASS FOR BOUNDED REPORT ROUTE BATCH / ROUND 07 REMAINS REWORK`, conditional on exact staged publication. The existing Shared Reporting generation endpoint now requires all five declared report types, a persisted row, verified artifact, and a structurally valid report before returning `ok=true`. An absent `total_notes` remains `null` in diagnostics; an explicitly measured zero remains valid.

## Exact source and verification

- Base: fetched `main` `34fd541b6bd264907d96960b62f00af4254f4189`. Only the report-generation route hunk in `lumenis/shared/reporting/routes.py` and new `tests/test_report_generate_status.py` are staged. The unrelated dirty scoped-report candidate in the same route file remains unstaged. Exact staged blob IDs: route `0605a97d275ecc682339bc4290bf6732e1a6f666`, test `92340a7079f271a18bbc7d837f11231377e6fc16`.
- The staged blobs were replayed byte-for-byte onto a clean archive of that `main`. `python -m pytest -q -c pytest.ini tests/test_report_generate_status.py tests/test_report_audit.py tests/test_g4_report_artifact_hash.py` passed 65/65, exit 0, with no daemon-thread leak. Tests used a fingerprint-matched disposable OS-temp seed and no provider call. Before the direct guard, the dirty worktree's older uncommitted artifact verifier made 1 of 3 new tests fail; the correction was rerun and passed. A sandbox-restricted temporary directory also produced `PermissionError` before test collection; that run is not counted as PASS.
- Protected `data/monitor.db` was not opened or migrated. SHA-256 before and after was `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`; no `-wal` or `-shm` sidecars were introduced.

## REAL DELIVERY CARD / 真实用户工作闭环验收

`REAL USER JOB`: request a complete, reopenable report rather than a success message for missing output. `ENTRY`: existing `/api/report/generate`. `REAL INPUT`: isolated complete, missing-count, empty and partial report bundles. `END-TO-END PATH`: existing Shared Reporting engine result → structural/artifact/row check → honest HTTP result. `USER-VISIBLE RESULT`: no real authorized user, actual Source/Evidence-backed report or App page was exercised. `FAILURE/RECOVERY`: incomplete bundles return `ok=false` and can be regenerated after the missing result is repaired; no zero is invented. `EVIDENCE`: exact staged clean replay and 65 focused/neighboring tests. `ACCEPTANCE ASSERTION`: bounded route truth only; ROUND 07 real user-work E2E and exit remain open.

`GLOBAL UNIVERSE / DATA MATURITY IMPACT`: no real entity was sampled or collected. Global Commercial Coverage=`NO`; Global Brand Coverage=`NO`; Guangzhou Taikoo Hui Reference Coverage=`PARTIAL / NOT REVERIFIED`; `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`.

`COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO`; actor-scope authorization, live source lineage, report reopen/export, operating recovery and release remain separate gates.

`CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION`: [JSON Schema object required-property guidance](https://json-schema.org/understanding-json-schema/reference/object#required), accessed 2026-09-26, confirms that property presence must be checked explicitly; the current missing→zero bug and existing Shared Reporting artifact verifier supplied the exact local behavior. Decision `ADAPT` within the existing owner, with no new dependency or truth source. The scoped route and tests are the rollback unit; a future real-report E2E is required before promotion of the Round.
