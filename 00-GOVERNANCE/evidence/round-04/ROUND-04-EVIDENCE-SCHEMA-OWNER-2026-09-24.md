# ROUND 04 — Shared Evidence integrity schema owner

Sol decision: `PASS FOR BOUNDED OWNER BATCH / ROUND 04 EXIT NOT ACCEPTED`. The Shared Evidence owner now exposes a caller-transaction-safe helper for four nullable integrity fields and their indexes. This is a prerequisite for a separately reviewed Shared Database v17 migration; it is not that migration, a writer-integrity rollout or real Evidence acceptance.

## Exact source and verification

- Base: fetched `main` `58464c73a4b596e1c3d96b134606046cc151f413`, also live `refs/heads/main` before staging. Luna's isolated patch SHA-256: `8A527F2A724BACC68ED96649E5875CC1A279BEC724328E2BB7657498F5C7C76A`. Accepted source paths: `lumenis/shared/evidence/store.py` and `tests/test_evidence_schema_owner.py`. The protected dirty store has a broader unaccepted integrity candidate and was not replaced by the clean-index patch.
- `ensure_evidence_schema(conn)` adds `integrity_version`, `integrity_algorithm`, `integrity_key_id` and `integrity_digest` as nullable columns, creates owner indexes after columns, and leaves transaction control and legacy row values with its caller. It does not backfill an integrity claim.
- Sol independently replayed the exact patch against a clean `HEAD` archive with a disposable SQLite seed. `python -m pytest -q -c pytest.ini tests/test_evidence_schema_owner.py tests/test_evidence_chain.py tests/test_evidence_store.py` passed 58/58, exit 0, with no background-thread leak. The new tests cover legacy-row preservation, explicit transaction rollback and fresh-schema idempotence. `py_compile` and staged `git diff --check` exited 0. Current dirty backend sources compiled; the broader dirty Evidence candidate remains unaccepted and not a test PASS for this Batch.
- The protected `data/monitor.db` remains 1,458,176 bytes with SHA-256 `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`; no WAL/SHM at prepublication inspection. No production database was opened through SQLite or changed.

## REAL DELIVERY CARD / 真实用户工作闭环验收

`REAL USER JOB`: preserve a real source record's lineage and verifiable storage while an operator investigates it. `ENTRY`: existing Shared Evidence storage owner. `REAL INPUT`: in-memory seeded legacy Evidence row; no live source. `END-TO-END PATH`: caller transaction → additive schema → unchanged legacy row → rollback/idempotence verification. `USER-VISIBLE RESULT`: none verified. `FAILURE/RECOVERY`: an explicit caller rollback removes the added schema without changing the seeded row. `EVIDENCE`: 58 clean staged tests and current static compile. `ACCEPTANCE ASSERTION`: this owner API passes as a bounded Batch only; no real user-work E2E, so ROUND 04 and ROUND 03 remain open.

`GLOBAL UNIVERSE / DATA MATURITY IMPACT`: no new entity coverage; Global Commercial Coverage=`NO`; Global Brand Coverage=`NO`; Guangzhou Taikoo Hui Reference Coverage=`PARTIAL / NOT REVERIFIED`; `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`. Random real-entity sample count is zero for this schema-only Batch.

`COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO`. v17 migration, writer-authenticated integrity, authorized live source, user-visible review and recovery evidence remain open.

`CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION`: [SQLite ALTER TABLE](https://www.sqlite.org/lang_altertable.html) and [SQLite transaction documentation](https://www.sqlite.org/lang_transaction.html), accessed 2026-09-24, support additive, transaction-scoped DDL; decision `ADAPT` within the existing Shared Evidence owner. [OpenLineage](https://github.com/OpenLineage/OpenLineage), accessed 2026-09-24, Apache-2.0 maintained OSS, is `DEFER`: no new lineage runtime is justified for this schema prerequisite. No new dependency or external effect was added. Reversal is through mainline source history and caller transaction rollback.

`NEXT DEPENDENCY`: independently accept a v17 Shared Database migration that calls this helper without altering v13–v16 behavior, then verify real Evidence writer and user-work E2E.
