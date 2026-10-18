# ROUND 05 — core health readiness contract (bounded Batch)

Date: 2026-09-26. Base `main`: `29f378cb419515619ac7ae2b1bfbefdae848d099`. This record accompanies the exact source and tests in the containing commit; resolve that commit against fresh `origin/main` and live `refs/heads/main` after publication.

## Fault and repair

The committed `/healthz` returned `ok=true` without checking the canonical database. The supervisor accepted HTTP 200–499 as healthy, while the Windows launcher accepted any parseable successful response. This could report a broken Product Core as ready.

The existing Product Core route now opens the call-time canonical repository in read-only mode and requires its existing `notes` base table. It returns HTTP 503 with `ok=false`, `status=unavailable`, and `dependencies.database=unavailable` when the file, connection or base table is unavailable. It does not reveal a database error or create a missing database. The supervisor and launcher now accept only HTTP 200 with `ok=true`, `status=healthy`, and `dependencies.database=ok`. No new database, health owner, runtime or account route was introduced.

Scoped staged source blobs: `app.py` `f94edd436bd631092f668f105762fd3f2871fae6`, `run_supervised.py` `f3886b32954f8ff6d71794beb7f233694ac78528`, `scripts/start_production.ps1` `9141460c4d56ec9c7d48d88522d52d3c2c3343be`; test blobs `d140b1c4caf3039a2b439888c60f1e4ab93a860e` and `67523df426e3f1500fa3b7fc0f3f70464dfac327`. Isolated Luna patch SHA256 `4C206ABEB30B9D0FFD1D8DEE8ABC247BB721D194B075F857E3FB00941AAC8CB3` was Sol-reviewed and staged only by exact patch, preserving unrelated dirty changes.

## Verification at the exact staged snapshot

`git archive HEAD` plus the five staged blobs produced `C:\Users\private-user-121dcc385158\AppData\Local\Temp\lumenis-health-staged-20260926-b`; each replayed blob hash matched its staged hash. With a disposable empty SQLite seed and process-scoped cloud AI disabled, the five new endpoint/supervisor tests and three neighboring health/startup tests passed **8/8** (`pytest` exit 0). The mocked PowerShell launcher helper passed without executing the launcher; `verify_lumenis_single_product.py` and `verify_codex_takeover_governance.py` each exited 0. `git diff --cached --check` exited 0. An initial pytest selection used the wrong neighboring test name and collected nothing; the corrected run above is the current result. No real service, scheduled task, browser, model, collector, or production database was started/opened/migrated. Protected `data/monitor.db` SHA256 remained `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`; no WAL/SHM sidecar appeared.

## REAL DELIVERY CARD / COMMERCIAL OVERLAY IMPACT

Real user job: an operator starts or recovers the product and can trust its readiness signal. Entry: canonical Windows startup and `/healthz`. Real input: the configured canonical business database. User-visible result: a truthful healthy or unavailable core state. Failure/recovery: missing database, missing base schema and invalid responses fail closed; a real service recovery and return to the user's task have **not** been exercised. Evidence: isolated tests and source review only. Acceptance assertion: **not met** for ROUND 05 because there is no live 8201 boot, real operator recovery, or real user-work E2E. `ROUND 05=REWORK`; `COMMERCIAL_READY=NO`.

The health marker proves only the database file can be read and the base `notes` table exists. It does not prove the full schema, migrations, data maturity, collector/browser identity, external sources, or business workflows. The committed launcher would also start resident 9223/9224 browsers; `--no-scheduler` does not suppress every app startup background effect. A safe isolated full-Core loopback boot needs an explicit suppression gate before runtime E2E. Global Commercial Coverage, Global Brand Coverage, and Guangzhou Taikoo Hui Reference Coverage remain **NO NEW CLAIM**; no entity or business data was added.

## Continuous frontier research / capability evolution

SQLite's [URI filename documentation](https://www.sqlite.org/uri.html), accessed 2026-09-26, defines `mode=ro` as a read-only open rather than create-if-missing. Decision: **ADAPT** the repository's existing `DatabaseRepository.connection(read_only=True, wal=False)` for the health probe. Version boundary: the current committed SQLite connection API; no external dependency or license change. Promotion remains gated by live runtime, real user-work E2E, observability and rollback evidence.
