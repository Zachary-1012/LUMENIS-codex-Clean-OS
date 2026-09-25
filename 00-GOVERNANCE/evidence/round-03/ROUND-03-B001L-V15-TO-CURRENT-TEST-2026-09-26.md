# ROUND 03 — BrandFocus v15-to-current migration test contract

Sol decision: `PASS FOR BOUNDED TEST BATCH / ROUND 03 REMAINS REWORK`. The v14→v15 BrandFocus migration test no longer asserts that the repository's current schema version is permanently 15. It tests the v15 transition explicitly, then continues to the current migration version and verifies BrandFocus identities and registry rows remain stable on a repeated run.

## Exact source and verification

- Candidate base: fetched main `742e48e1197d4a5cb6608b8f7e749657e9818a63`. Only `tests/test_round03_b001l_brand_focus_migration.py` changes. The migration implementation, registry owner and production database are unchanged.
- Negative control on the isolated base: `test_v14_upgrade_is_deterministic_compatible_and_reusable` failed at its old `CURRENT_VERSION == 15` assertion because current source declares v17; pytest exit 1 before the migration executed.
- Candidate: `migrate(target_version=15)` verifies the historical v15 behavior; `migrate()` then reaches `CURRENT_VERSION`, checks the same registry rows/BrandFocus IDs and succeeds idempotently on another call. The focused test passed, exit 0. The exact staged test blob `4860374e6be957f2bce4604456dd8b5b826148e2` was replayed on a clean archive of `e50540d02e8d0dee27de3e5c10a5ce776676b232`; `python -m pytest -q -c pytest.ini tests/test_round03_b001l_brand_focus_migration.py tests/test_shared_database_migrations.py` passed 9/9, exit 0, using disposable SQLite fixtures. An initial sandboxed run could not create its temporary fixture DB and exited 4 before test collection; the identical clean archive passed when temporary fixture storage was writable. No source adjustment or test skip was used to resolve that environment error.
- No protected `data/monitor.db` connection or migration was made. Its SHA-256 at resume was `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`.

## REAL DELIVERY CARD / 真实用户工作闭环验收

`REAL USER JOB`: retain the correct BrandFocus identity when an existing BMP dataset is upgraded. `ENTRY`: existing Shared Database migration owner. `REAL INPUT`: isolated v14 registry fixture with legacy BMP and CTH subjects. `END-TO-END PATH`: v14 fixture → v15 migration/ID backfill → later migrations through current version → repeated migration → registry identity check. `USER-VISIBLE RESULT`: no App workflow or real production dataset was exercised. `FAILURE/RECOVERY`: the test fails on an actual migration or identity regression; production backup/rollback and user recovery remain separate gates. `EVIDENCE`: negative control, 9 passing isolated migration/neighbor tests and unchanged production DB fingerprint. `ACCEPTANCE ASSERTION`: test contract Batch passes after publication; ROUND 03 real-user work E2E and migration acceptance remain open.

`GLOBAL UNIVERSE / DATA MATURITY IMPACT`: no entity was collected. Global Commercial Coverage=`NO`; Global Brand Coverage=`NO`; Guangzhou Taikoo Hui Reference Coverage=`PARTIAL / NOT REVERIFIED`; `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`. Random entity acceptance was not exercised by this test-only Batch.

`COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO`; isolated fixture migration does not prove live dataset safety or user workflow.

`CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION`: current [SQLite CREATE TABLE documentation](https://www.sqlite.org/lang_createtable.html), accessed 2026-09-26, and the repository's current migration/version owner were checked. Decision `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE`: this is a stale test expectation, so no new dependency, schema, owner or product surface is justified. The negative control and disposable upgrade regression validate it; reverting the single test patch is the rollback path.

`NEXT DEPENDENCY`: keep the v17 migration and Evidence/Permission integration under their existing Round 03/04 gates, with a real user-work E2E before any Round 03 PASS.
