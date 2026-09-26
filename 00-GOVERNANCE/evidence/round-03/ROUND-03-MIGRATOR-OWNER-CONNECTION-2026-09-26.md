# ROUND 03 — Migrator-owned prerequisite transaction (bounded Batch)

Date: 2026-09-26. Base `main`: `c2dbff064b5815f93c055b08b8abd66fa968b2b5`. This record accompanies the exact source and tests in its containing commit; verify that commit against live `main` after publication.

## Fault and bounded repair

The versioned Shared Database migrator invoked the existing Canonical Data and Evidence Chain schema owners by path. Each owner could open a separate connection, so a prerequisite failure could leave schema outside the migrator's rollback. The migrator now passes its own connection to both published owner APIs. It begins an explicit transaction when either owner schema is needed and rolls back on prerequisite failure. No second database or schema owner was added. The v0 base-business-schema commit and per-version commits retain their existing behavior; whole-upgrade atomicity is not claimed.

Exact staged blobs: `lumenis/shared/database/migrations.py` `cc707fc7dffc6dfb704ec519c1d57665cc86d212`; new `tests/test_shared_database_migration_connection_owner.py` `b32784f2fde33f27536b4263bc94ff49041be2d3`; adjacent v16 test correction `tests/test_content_evidence_v16_migration.py` `7d7cbab36603a1985a7fcd26c864263d8d9df0e7`. The Luna patch SHA256 was `3EC9A03AAA836193B3AA8EA36DBD1E27BBF9E0FCD2BAE34D1C4E4868ED0ED231`; Sol reviewed and staged only its two requested paths, then independently removed two obsolete v16-current-version assumptions from the clean adjacent test. The Luna-reported migration blob differed from the actual staged blob; the staged blob above is the publication authority.

## Verification

Sol reconstructed `HEAD` plus the three exact staged blobs in a disposable archive and matched each Git blob hash. On Python 3.13.15 / SQLite 3.50.4 with an external disposable SQLite seed and cloud AI disabled, migration, Canonical, Evidence, v16 and v17 neighbor tests passed **18/18** (`pytest` exit 0). The added tests prove that the supplied connection keeps owner DDL in one transaction and ignores a stale database path; an injected failure after real Evidence owner initialization rolls back both owner schemas and leaves the version at 10. The adjacent v16 test had first failed on unchanged `HEAD` because it asserted `CURRENT_VERSION == 16` after v17 was published; the staged correction removed only that obsolete global-version assertion and the obsolete no-v17-migration assertion. Baseline failure and corrected suite were both observed, not counted as a source regression.

`git diff --cached --check` passed. Current-worktree single-product, Codex takeover and database-authority static guards passed with exit 0 before this publication cycle; rerun after the evidence/status edit for the final snapshot. Protected `data/monitor.db` SHA256 remained `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`, with no WAL/SHM sidecar at the observed checks. No production migration, full Product Core, scheduler, browser or model call ran.

## REAL DELIVERY CARD / COMMERCIAL OVERLAY IMPACT

**REAL USER JOB:** retain a real acquired source as trustworthy Evidence and Canonical Data for an operator's later decision. **ENTRY:** existing SYSTEM Collector/import and Shared Database migration. **REAL INPUT:** an authorized public or internal source. **END-TO-END PATH:** Source → Evidence → Canonical → scoped result. **USER-VISIBLE RESULT:** a traceable record and reopenable result. **FAILURE/RECOVERY:** prerequisite failure must leave no partial owner schema; the isolated test proves this storage seam only. **EVIDENCE:** staged source/test blobs and disposable rollback test above. **ACCEPTANCE ASSERTION:** the full job is still unproven because authorized real source, actor Permission, reporting and UI return path have not passed current-main E2E. Therefore `ROUND 03 B001=REWORK`, not a Round PASS, and `COMMERCIAL_READY=NO`.

**GLOBAL UNIVERSE / DATA MATURITY IMPACT:** no entity data was added. Global Commercial Coverage, Global Brand Coverage and Guangzhou Taikoo Hui Reference Coverage receive **NO NEW CLAIM**. Random-entity acceptance and source-rights review remain open.

## Continuous frontier research / capability evolution

[SQLite transaction documentation](https://www.sqlite.org/lang_transaction.html) (official; updated 2026-02-18; accessed 2026-09-26) confirms explicit `BEGIN` persists until `COMMIT` or `ROLLBACK` and nested `BEGIN` fails. [Python 3.13.15 sqlite3 documentation](https://docs.python.org/3.13/library/sqlite3.html) (official; accessed 2026-09-26) describes connection transaction control. Decision: **ADAPT** the existing migrator/owner connection contract, with `conn.in_transaction` guarding `BEGIN`; no library or code was copied, no new dependency/license, commercial service, credential or external effect was introduced. The capability remains versioned by the existing v0–v17 migrator; real E2E, observability and rollback checks remain required before a Round exit.
