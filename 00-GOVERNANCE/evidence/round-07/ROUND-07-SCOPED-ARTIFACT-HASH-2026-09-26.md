# ROUND 07 — Scoped report artifact identity helpers (bounded Batch)

Date: 2026-09-26. Base `main`: `a3f18135f6c43055ebd8029572ee7ee6ec0bd625`. This evidence accompanies its exact source/test commit; resolve that commit against live `main` after publication.

## Fault and bounded repair

The protected local scoped-report candidate expected Shared Reporting artifact helpers that were absent from published `main`. Its draft content-hash helper globally replaced the generation timestamp in the full report body, which could hide the same timestamp in source findings. Sol accepted only a bounded rewrite inside the existing `artifact.py` owner: deterministic scope key, opaque return token, and a content hash that normalizes one identified Markdown generated-at header or the generated-time column of a canonical 12-column CSV. Unknown/malformed CSV, alternate quoting and line endings retain their raw hash. The helper never changes the report body. The existing `verify_report_dict` check still rejects a missing `total_notes`; an explicitly measured zero remains distinct from missing data.

Exact staged blobs: `lumenis/shared/reporting/artifact.py` `0913e0aba84e0953bc1ae33849b35339069635e3`; `tests/test_report_audit.py` `e2539e5bad22acb74b87d676d6e0f46ad1bef455`. The final isolated Luna patch SHA256 is `858DF2B60C11C68249D2A6C34CEE5BF21CA696E3B2B3EB403D281FE2D1DF1AC3`; Sol applied only these two paths to the index and verified the staged blobs in a fresh `HEAD` archive.

## Verification

The four new helper tests failed on unchanged clean `HEAD` because the helpers were absent. After the patch, Sol independently ran `tests/test_report_audit.py` and `tests/test_g4_report_artifact_hash.py` in the exact staged replay: **66/66 passed**, `pytest` exit 0, no reported thread leak. Tests prove the Markdown and CSV generated timestamp can vary without changing content identity, while the same timestamp inside a source finding remains hash-significant; altered CSV quoting and CRLF also remain significant. `git diff --cached --check` passed. A disposable `ZBC_DB_PATH` and test seed were used; cloud AI was disabled. Protected `data/monitor.db` SHA256 remained `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45` without WAL/SHM sidecars. No Product Core, public collection, report save/reopen route, model call or production DB migration ran.

## REAL DELIVERY CARD / COMMERCIAL OVERLAY IMPACT

**REAL USER JOB:** a researcher saves and later reopens an authorized source-backed report without losing its scope or source trace. **ENTRY:** the Shared Reporting route remains a separate dependency. **REAL INPUT:** exact actor scope and verified Evidence/Canonical rows. **END-TO-END PATH:** authorized read → report build → save → reopen → lineage recheck. **USER-VISIBLE RESULT:** a stable, traceable artifact. **FAILURE/RECOVERY:** malformed or altered artifact bytes must not normalize into a false identical content hash. **EVIDENCE:** exact staged source, focused test replay and protected-DB fingerprint. **ACCEPTANCE ASSERTION:** only artifact identity helpers passed; the route, Permission, Evidence scope/integrity, Canonical data, persistence and real user-work E2E are still open. `ROUND 07=REWORK`; `COMMERCIAL_READY=NO`.

**GLOBAL UNIVERSE / DATA MATURITY IMPACT:** no entity data, coverage or random-entity result was added. Global Commercial Coverage, Global Brand Coverage and Guangzhou Taikoo Hui Reference Coverage receive **NO NEW CLAIM**.

## Continuous frontier research / capability evolution

[Python 3.13.15 CSV documentation](https://docs.python.org/3.13/library/csv.html) (official; accessed 2026-09-26) documents reader/writer dialect and newline behavior. Decision: **ADAPT** the existing Shared Reporting artifact owner with an exact writer round-trip gate before normalizing a CSV metadata column. No external code was copied, no new package/license, external service, credential, effect or product surface was added. The helper remains inactive for a real report until the canonical scoped-report dependency chain and its user E2E pass.
