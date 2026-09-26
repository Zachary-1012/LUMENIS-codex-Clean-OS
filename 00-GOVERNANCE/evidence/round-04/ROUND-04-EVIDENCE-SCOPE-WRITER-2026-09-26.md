# ROUND 04 — Evidence exact-scope write contract

Status: **SOURCE + ISOLATED TESTED / REAL USER E2E NOT VERIFIED / ROUND 04 REWORK**
Date: 2026-09-26
Base: `origin/main` `2dc3abac3df94a9a40983d8e130a740a1f289146`; baseline Shared Evidence store blob `02870ab88103b9283cc04fcf8d393af60100ef0a`.

## Task, owner, and change

An authorized CTH or BMP caller needs Evidence to retain its exact Subject, BrandFocus, or explicit global scope. The existing `lumenis/shared/evidence/store.py` writer accepted no such arguments, and its compatibility filter silently dropped columns absent from an older table. This bounded change keeps the sole Shared Evidence owner. `record_evidence` now validates an explicit scope and persists the normalized domain/product columns and reserved `_lumenis_scope` JSON in the **same record**. Invalid, conflicting, non-JSON, or incomplete storage returns an error or the existing `-1` write-failure sentinel; it cannot report a scoped success with lost scope. Legacy unscoped inputs and records stay unassigned and are not backfilled.

The existing failure queue now checks scoped metadata before replay. When an older schema lacks a required scope column, replay leaves the item pending instead of filtering those fields and inserting an unscoped record. It succeeds after the same canonical Evidence table receives the missing column. No new table, store, permission grant, report path, or UI is introduced.

## Verification and protection

- Exact staged `store.py` and new `tests/test_evidence_scoped_write.py` bytes were replayed into a clean `origin/main` archive. `pytest -q` for the new test plus `test_evidence_store.py`, `test_evidence_store_schema.py`, and `test_evidence_write_failed_health.py`: **40 passed, exit 0**. This covers CTH/BMP/Global scopes, legacy inputs, mismatches, missing columns, and failed-write replay after storage repair.
- `verify_ai_native_constitution.py`: **PASS on the exact staged clean snapshot**; `verify_database_authority.py`: **PASS**, 555 production Python modules AST-audited. `git diff --cached --check`: **PASS**. The takeover validator passed in the actual repository, where it can inspect Git HEAD.
- The same constitution command in the **shared dirty worktree** returned exit 1 because unrelated, unaccepted `tests/test_report_audit.py` edits lack two required regression-test names. Those edits were not staged; the exact staged snapshot contains both tests and passes the blocking Gate. This distinction must remain visible until the dirty candidate is reconciled.
- Tests used an explicit disposable external SQLite seed, process-scoped `ZBC_DB_PATH` and `LUMENIS_TEST_SEED_DB`, cloud AI disabled, and no browser or collector. The protected `data/monitor.db` remained 1,458,176 bytes with SHA-256 `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`; no `monitor.db-wal`/`-shm` sidecar appeared.

## REAL DELIVERY CARD / 真实用户工作闭环验收

- **REAL USER JOB:** a brand analyst or commerce operator uses an authorized source to support a scoped decision and later reopens its report.
- **ENTRY / REAL INPUT:** an approved CTH Subject or BMP BrandFocus and a real source. This Batch supplies only the Evidence writer contract; no live source was submitted through the end-to-end product flow.
- **END-TO-END PATH / USER-VISIBLE RESULT:** Source → Evidence → Canonical → decision/report → return path remains **LIVE_NOT_VERIFIED**. A test record and API success alone do not satisfy this job.
- **FAILURE / RECOVERY:** malformed scope is rejected; an incomplete Evidence schema returns `-1`; queued scoped writes do not replay without full scope storage. Real user recovery remains unverified.
- **EVIDENCE / ACCEPTANCE ASSERTION:** isolated storage and replay tests pass. **ROUND 04 stays REWORK**, with exact-scope query, actor Permission, live source lineage, user-visible outcome and return path open.

## COMMERCIAL OVERLAY IMPACT / GLOBAL UNIVERSE / DATA MATURITY IMPACT

`COMMERCIAL_READY=NO`. `Global Commercial Coverage=NO`, `Global Brand Coverage=NO`, and `Guangzhou Taikoo Hui Reference Coverage=NO` for this Batch: a storage contract adds no population or mature source coverage. `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`. Random entity acceptance was not run because this Batch did not expose an entity result; it remains required in the owning user-visible rounds.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

The reviewed gap is deterministic storage semantics in the existing owner. No external model or library upgrade is justified for this Batch (`RESEARCH COMPLETE / NO JUSTIFIED UPGRADE`). The official [SQLite ALTER TABLE documentation](https://www.sqlite.org/lang_altertable.html), accessed 2026-09-26, supports the existing additive-column direction; the repository's migration owner still controls any schema change. Future CTH/BMP interpretation or model-based classification may consume only source-linked Evidence and must pass its own evaluation and Permission gates.
