# ROUND 03 — existing-v0 migration atomicity (2026-09-26)

## Batch and current truth

- Owner: `lumenis/shared/database/migrations.py`; no schema owner, DB path, or migration number added.
- Base: `781a833858fad7aebf1755c66b7a79317144b9af` on the sole `main` branch. The final delivery SHA must be read from Git after publication; this evidence is co-published with the source and tests.
- State: accepted **bounded implementation Batch**, while ROUND 03 remains `REWORK`. This is not a release, live migration, or real-user E2E acceptance.
- Worktree isolation: the canonical shared worktree contained an unrelated, older dirty `migrations.py` candidate and dirty tests. The exact mainline source was edited and tested in a clean `git archive HEAD` under `%TEMP%`, then only the reviewed source/test blobs and this evidence were selected for publication. The dirty files were not reset or overwritten.

## Defect and change

For a v0 database with all three valid historical base tables already present, `_ensure_migration_prerequisites` wrote and **committed** the v1 marker before Canonical/Evidence owner initialization or the first versioned migration. A later failure could leave `schema_version=1` while owner schema work rolled back. After validating the existing base schema, the migration now opens a transaction and writes v1 without committing. Existing base rows, owner DDL, the v1 marker, and the first versioned step share the same rollback boundary. Empty-v0 behavior and partial-v0 fail-closed behavior remain covered by existing tests.

## Verification at the exact candidate snapshot

- Clean archive import was checked to resolve from the archive, not the shared dirty checkout. An initial test invocation accidentally resolved imports from the shared checkout because PowerShell started in the canonical workdir; its four failures are **not** candidate results. The process was rerun with explicit `Set-Location` and `PYTHONPATH` to the archive.
- Disposable DB only: `ZBC_DB_PATH` and `LUMENIS_TEST_SEED_DB` pointed under `%TEMP%`; cloud AI was disabled. No real `data/monitor.db` migration was executed.
- `python -m pytest -q tests/test_shared_database_schema_atomicity.py tests/test_shared_database_migrations.py tests/test_shared_database_backup_contract.py tests/test_shared_database_owner.py`: **37 passed, exit 0**, no daemon-thread leak. New cases cover owner failure and first-step failure on existing-v0 rows, with no persisted v1 marker or partial DDL.
- Protected `data/monitor.db` before publication: SHA-256 `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`, 1,458,176 bytes; no `monitor.db-wal` or `monitor.db-shm` appeared. Recheck after publication.
- Constitution/static validators and staged diff check: run on the exact staged candidate before commit, then on the final HEAD after commit; record actual results rather than inferring from tests.

## REAL DELIVERY CARD / 真实用户工作闭环验收

- REAL USER JOB: authorized operator safely upgrades an existing business database while retaining its source records.
- ENTRY / REAL INPUT: an isolated v0 database with three valid historical base tables and an existing note. This is a test input, not a production or real-user database.
- END-TO-END PATH: backup → validation → v1 marker → Canonical/Evidence owner prerequisite → first versioned step → rollback on failure.
- USER-VISIBLE RESULT: none at this Batch boundary. A real authorized upgrade, reopen, UI/result, failure recovery, and user verification are still required for Round 03.
- FAILURE / RECOVERY: the two injected failures preserve the existing note, leave no integer version marker, and remove DDL from the failed transaction; pre-migration backup remains available.
- ACCEPTANCE ASSERTION: the bounded migration failure contract is `TESTED`; `REAL USER WORK E2E ACCEPTANCE` is **not passed**. ROUND 03 = `REWORK`.

## GLOBAL UNIVERSE / DATA MATURITY and commercial impact

No entity population or coverage was changed. Random entity sample count is 0 for this Batch; Global Commercial Coverage = `NO`, Global Brand Coverage = `NO`, Guangzhou Taikoo Hui Reference Coverage = `PARTIAL` from earlier isolated reference evidence, `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`. The Batch adds no authorization to use customer data, no production migration, and no commercial readiness claim. Source rights, retention, real backup/restore, runtime and human acceptance remain open.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

The current Round 03 charter cites SQLite's maintained transaction, WAL, ALTER TABLE and Backup API documentation, accessed on 2026-09-23, and records SQLite public-domain license. This Batch **ADAPTS** its transaction principle inside the existing Shared Database owner. It adds no dependency, provider, model, or alternate data store. Exact links remain in the current Round 03 charter. No unrelated capability promotion is claimed.

## Online closure

After commit, fetch and verify local HEAD, `origin/main`, live `refs/heads/main`, this evidence path, and the co-published CURRENT status file. If CI does not execute, record `EXECUTION-LAYER UNVERIFIED`. The shared dirty candidates remain `LOCAL_ONLY` until separately classified and accepted.
