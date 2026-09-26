# ROUND 03 — Canonical Data caller-owned connection (bounded Batch)

Date: 2026-09-26. Base `main`: `4866289f2068918eadefde6157e7d645d106784a`. This record accompanies the exact source/test in its containing commit; verify that commit against fresh live main after publication.

## Fault and bounded repair

`canonical_data.ensure_canonical_table(db_path)` always opened, committed and closed another connection. When the versioned migrator called it while holding its own connection, Canonical schema changes could land outside the migrator's rollback boundary. The old broad `domain_id` backfill catch also hid a partial repair error.

The existing Canonical Data owner now accepts an exclusive keyword `connection=`. With a caller-supplied connection it opens no repository, does not commit or close, and propagates the legacy repair error for the caller to roll back. The standalone `db_path` behavior remains compatible. No new Canonical/DB owner or parallel database was created. Staged source blob: `canonical_data.py` `9a59254f458c35621752aacfa38f422cf884c4fe`; new test blob `7eea31bb64096e3877ec9901dbc2eae0274f3e91`. Isolated Luna patch SHA256 `E7F1409BE93EDB88DB602BB5D9FB2C8C70C6F21EA1ADCD23C68CA8E6F5A89BC2`; Sol applied only that patch to the index, preserving the unrelated dirty working file.

## Verification

The two staged blobs were replayed byte-for-byte onto a clean archive of `HEAD`, and both hashes matched. An isolated disposable SQLite seed and explicit process-scoped cloud AI disable were used. The new rollback/custom-path test plus the neighboring Canonical Data, shared migration and schema atomicity suites passed **31/31** (`pytest` exit 0). The test proves that caller rollback removes new schema/index changes, preserves an existing legacy row after a backfill error, leaves the connection usable, opens no second repository and leaves an unrelated database byte-identical. No app service or product database migration ran. The current working tree's single-product and takeover-governance static guards each exited 0; their attempt in the Git archive was unverified because the archive has no `.git`, not because of a product assertion. `git diff --cached --check` exited 0. Protected `data/monitor.db` SHA256 remained `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`, with no WAL/SHM sidecar.

## REAL DELIVERY CARD / COMMERCIAL OVERLAY IMPACT

Real user job: ingest a real source and retain its Canonical Data and Evidence in one consistent database. Entry: existing SYSTEM Collector/import through the Shared Database migration prerequisite. Real input: a real source record in an authorized Subject/BrandFocus scope. User-visible result: a traceable record that can be reopened. Failure/recovery: a failed migration must roll back without partial Canonical schema; the injected-connection test covers only this database seam. Real source, Permission, Evidence, API/UI return and recovery E2E remain **unverified**. `ROUND 03 B001=REWORK`, not PASS; `COMMERCIAL_READY=NO`.

This Batch enables the later migrator wiring but does not change it. The Evidence Chain counterpart, versioned migration transaction, isolated realistic migration and user-work E2E remain separate pending gates. Global Commercial Coverage, Global Brand Coverage and Guangzhou Taikoo Hui Reference Coverage remain **NO NEW CLAIM**; no business data or entity population was added.

## Continuous frontier research / capability evolution

[SQLite transaction documentation](https://www.sqlite.org/lang_transaction.html), accessed 2026-09-26, describes caller-controlled transactions and rollback. Decision: **ADAPT** the current Canonical Data owner to accept the migrator's connection and let that owner control commit/rollback. No new dependency, license boundary, external effect, model or product surface was introduced. Promotion still requires migration regression, real E2E, observability and rollback evidence.
