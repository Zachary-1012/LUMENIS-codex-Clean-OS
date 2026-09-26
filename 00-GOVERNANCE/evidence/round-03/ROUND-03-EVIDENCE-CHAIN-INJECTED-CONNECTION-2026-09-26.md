# ROUND 03 — Evidence Chain caller-owned connection (bounded Batch)

Date: 2026-09-26. Base `main`: `db5b3a2c55c1e4865babad9032dcdefc75f262a5`. This record accompanies the exact source/test in its containing commit; verify that commit against fresh live main after publication.

## Fault and bounded repair

`lumenis.shared.evidence.chain.init_db(db_path)` always opened another connection and ran `executescript`, which implicitly commits a pending transaction. When called from the versioned migrator, Evidence schema changes could escape the migrator's rollback boundary. Its legacy ALTER helper also swallowed errors.

The existing Evidence Chain owner now accepts an exclusive keyword `connection=`. With a caller-supplied connection it executes the existing schema statements individually, opens no second connection, does not commit or close, and propagates legacy table-info/ALTER errors so the caller can roll back. The standalone `db_path` path keeps its existing behavior. No new Evidence, database or migration owner was introduced. Staged source blob: `lumenis/shared/evidence/chain.py` `a308b360483c4b27accd24a074adfcbd90233887`; new test blob `0639a6fa066f615dbf2d059e912d264483e33a6c`. The corrected isolated Luna patch SHA256 is `F695E07D4FBF1084C14671DCFF5BA849B154FC49546EBB4531E10EF716367E3D`; Sol applied only that patch to the index. Its first artifact had a malformed new-file header and was not applied; the corrected artifact passed `git apply --cached --check`.

## Verification

Both staged blobs were replayed byte-for-byte onto a clean archive of `HEAD`, with matching Git blob hashes. Using a disposable SQLite seed and process-scoped cloud AI disable, the new rollback/legacy/custom-path tests plus neighboring Evidence Chain, shared migration, schema atomicity and Canonical connection tests passed **58/58** (`pytest` exit 0). The tests prove that a pending caller write and new Evidence schema roll back together, a denied legacy ALTER propagates, the supplied connection stays usable, and an explicit standalone custom path works. No app service or product database migration ran. `git diff --cached --check` exited 0. Protected `data/monitor.db` SHA256 remained `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`, with no WAL/SHM sidecar.

## REAL DELIVERY CARD / COMMERCIAL OVERLAY IMPACT

Real user job: ingest a real source and retain Source, Evidence and Canonical Data consistently for later review. Entry: existing SYSTEM Collector/import through the Shared Database migration prerequisite. Real input: an authorized real source record. User-visible result: traceable Evidence and a Canonical record that can be reopened. Failure/recovery: an Evidence schema failure must roll back with the caller's transaction; the isolated test covers only this database seam. Real source, Permission, API/UI return, migration wiring and real user-work E2E remain **unverified**. `ROUND 03 B001=REWORK`, not PASS; `COMMERCIAL_READY=NO`.

The Canonical and Evidence injected APIs now exist, but the versioned migrator still needs to pass its own connection and prove realistic migration/rollback on an isolated database. Global Commercial Coverage, Global Brand Coverage and Guangzhou Taikoo Hui Reference Coverage remain **NO NEW CLAIM**; no entity or business data was added.

## Continuous frontier research / capability evolution

[Python's sqlite3 documentation](https://docs.python.org/3.13/library/sqlite3.html), accessed 2026-09-26, states that `executescript()` implicitly commits a pending transaction. Decision: **ADAPT** the current Evidence Chain owner so its caller-owned path executes the existing schema on the caller connection without that implicit commit. No new dependency, license boundary, external effect, model or product surface was introduced. Promotion still requires versioned migration regression, real E2E, observability and rollback evidence.
