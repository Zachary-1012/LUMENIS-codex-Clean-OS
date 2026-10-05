# ROUND-03-B001C — Consistent backup and honest migration refusal

> **Historical completed Batch record:** The R03 B001C result and Sol/Luna roles below describe the dated accepted Batch only; they do not assign current models, activate ROUND 03, or authorize a new code/DB task. Current activation is controlled by the top of `AGENTS.md`.

Status in the recorded Batch: SOL-ACCEPTED FOR THIS BATCH ONLY. Luna produced and clean-replayed a bounded patch at base `f66a5ed8`; after one Sol-requested rework, Sol independently replayed and tested the exact staged blobs, then committed/pushed them as `98729908`. B001 and ROUND 03 were not thereby accepted.

| Field | Boundary |
| --- | --- |
| Base | Fetch `origin`, verify `main`, `HEAD`, `origin/main`, branch inventory and status. Preserve all current dirty files and production `data/monitor.db[-wal|-shm]`. |
| Job | From clean current `origin/main` source in an OS-temporary archive, produce a patch for `lumenis/shared/database/migrations.py` that uses call-time canonical path and SQLite Backup API for a consistent WAL-aware snapshot, validates it before atomic replace, refuses migration when backup fails, refuses schema downgrade, and makes `rollback()` honestly refuse an unimplemented downgrade. Keep `CURRENT_VERSION=13` and v14–v17 out of this patch. |
| Paired test | Add a new isolated `tests/test_shared_database_backup_contract.py` covering committed WAL content, changed `ZBC_DB_PATH`, backup failure with unchanged schema/version, lower target refusal and rollback refusal. Tests may open only disposable paths outside the repository and must set an explicit external `LUMENIS_TEST_SEED_DB` if the test harness requires it. |
| Forbidden | Do not edit or overwrite the dirty canonical workspace source; do not change `business_schema.py`, `canonical_data.py`, `scope.py`, Subject, Evidence, Permission, reporting, Collector, App or production DB; no checkout/reset/clean of the shared worktree. No commit/push or stage in the shared checkout. |
| Deliverable | Exact unified patch file in OS temp, base/final file hashes, isolated test command/results from clean archive, protected production file fingerprints, direct caller check and any compatibility risk. Sol alone will inspect the patch, stage only exact index hunks, replay tests and decide `PASS/REWORK/SPLIT/BLOCKED`. |

The task is source safety, not production backup authorization. Do not invoke `backup_database()` or `migrate()` against the protected real database.
