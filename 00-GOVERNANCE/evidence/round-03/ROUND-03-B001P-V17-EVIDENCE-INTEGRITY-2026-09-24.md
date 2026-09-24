# ROUND 03 B001P — Shared Database v17 Evidence integrity storage

Sol decision: `PASS FOR BOUNDED BATCH / ROUND 03 REWORK`. This Batch connects the existing Shared Database migrator to the already published Shared Evidence schema owner. It does not calculate or attest an integrity digest, migrate the protected production database, or pass real user-work E2E.

## Exact source and verification

- Base: fetched local and remote `main` `76c341f9e34a331eb3f613106e51b7d99b33bf47` before staging. Exact candidate patch SHA-256: `0085E8059C78E6254C954EBF6F8EC25CAF0AD825BFAA0275E97B72671F7DCD74`. Staged paths are `lumenis/shared/database/migrations.py`, `tests/test_shared_database_migrations.py`, `tests/test_shared_database_owner.py`, and `tests/test_shared_database_v17_evidence_migration.py`; protected broader dirty work remains unstaged.
- v17 invokes `ensure_evidence_schema(conn)` inside the caller's transaction. Four integrity columns remain nullable; historical Evidence rows retain their values and unknown integrity, without a fabricated backfill. v13–v16 migration bodies are unchanged.
- Sol independently replayed the exact corrected patch on clean `main` with a disposable SQLite database: migration, owner, and Evidence tests passed 28/28, exit 0. The focused tests include legacy-row preservation, runner backup/version, caller transaction rollback, and forced post-helper failure rollback. Current staged diff and static checks are recorded in the delivery run; no production migration was executed.
- Protected `data/monitor.db` file fingerprint before staging: 1,458,176 bytes, SHA-256 `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`. No SQLite connection to that file was made.

## REAL DELIVERY CARD / 真实用户工作闭环验收

`REAL USER JOB`: retain verifiable source lineage across a schema upgrade so an operator can later investigate a source record. `ENTRY`: existing Shared Database migration path. `REAL INPUT`: isolated v16 legacy Evidence row, not a live user source. `END-TO-END PATH`: v16 backup → additive v17 migration → row/index inspection → reopen or injected failure rollback. `USER-VISIBLE RESULT`: none verified. `FAILURE/RECOVERY`: failed migration leaves schema version and legacy row at v16; the caller can retry after correction. `EVIDENCE`: 28 clean replay tests and staged diff. `ACCEPTANCE ASSERTION`: this storage Batch passes, but ROUND 03 remains `REWORK` until a genuine authorized user-work E2E is shown.

`GLOBAL UNIVERSE / DATA MATURITY IMPACT`: no entity coverage added. Global Commercial Coverage=`NO`; Global Brand Coverage=`NO`; Guangzhou Taikoo Hui Reference Coverage=`PARTIAL / NOT REVERIFIED`; `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`. Random real-entity sample count is zero for this storage-only Batch.

`COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO`. A real source, caller-side digest creation/verification, user-visible review, and recovery evidence remain open.

`CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION`: [SQLite ALTER TABLE](https://www.sqlite.org/lang_altertable.html) and [transaction documentation](https://www.sqlite.org/lang_transaction.html), accessed 2026-09-24, support additive transactional DDL (`ADAPT` to the existing Shared Database and Evidence owners). [OpenLineage](https://github.com/OpenLineage/OpenLineage), Apache-2.0 and maintained at access on 2026-09-24, remains `DEFER` because this storage change needs no new runtime or truth owner. Rollback is the migration runner's transaction on failure; no downgrade of accepted data is implied.
