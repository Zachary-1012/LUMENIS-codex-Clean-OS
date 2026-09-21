# LUMENIS Shared Database Authority Audit — ROUND 03

> Task: `ROUND-03-B001 / LUNA-006A` + `ROUND-03-B001B / LUNA-006A-REWORK`
> Baseline: `3f93c12858b1ac089e65ae0bf4bddcef036272ae`
> Evidence date: 2026-09-21
> Status: **AUTHORITY TESTED / LEGACY SMOKE BLOCKED — NOT LIVE VERIFIED**

This evidence is subordinate to current executable source, runtime truth, the
Product Architecture, and the Source Owner Index. It does not claim that a test
fixture is Production Truth or that a static check proves live database health.

## Implemented and tested boundary

- Canonical database owner remains `lumenis/shared/database/`.
- Direct production `sqlite3.connect` calls are AST-audited, including module
  aliases, `from sqlite3 import connect` aliases, and assigned connect aliases.
- Only `connection.py` and `migrations.py` are permitted to open SQLite directly.
- Tests, operator/audit scripts, generated output, third-party trees, the Dart
  application, and historical/provenance trees are explicitly excluded from the
  production-runtime scan; they are not counted as compliant production callers.
- Root compatibility path/migration/registry modules are checked as forwarding
  surfaces and are not independent database owners.
- `lumenis.config.DB_PATH` remains a compatibility attribute but now derives
  only from canonical `main_db_path()`; `MONITOR_DB_PATH` is no longer a
  production database selector. The legacy smoke script now selects its
  disposable database through `ZBC_DB_PATH`.
- `tests/test_database.py` now creates a fresh OS-temporary schema and inserts one
  explicit `round03-db-fixture` record. It explicitly invokes the current
  transitional initializers for `kos_profiles`, `kos_paid_plans`,
  `kos_operations`, `podcast_entities`, `token_stat`, and
  `auth_recovery_tasks`, then verifies those six tables together with the four
  root-schema tables. It no longer requires local production notes or an
  existing production schema.

## Closed authority blocker

The rework removed the `MONITOR_DB_PATH` selection from `lumenis/config.py`.
The blocking authority verifier now exits `0` after AST-auditing 552 production
Python modules. No exception or compatibility allowlist was added.

## Out-of-scope legacy smoke blocker

`python tests/lumenis_smoke.py` had all declared imports available and was run.
It exits `1` on current source for three independent stale expectations:

- it expects exactly 8 registered acquisition adapters while current source
  registers 16;
- it expects retired template-backed V4 login/settings pages to render;
- its hand-written minimal `notes` schema omits `publish_datetime`, which the
  current publish-date cleaner queries.

The script reached 20 passing checks and 4 failing checks before the missing
column raised `sqlite3.OperationalError`. Fixing those product/test-history
expectations is outside this database-path rework and was not hidden, skipped,
or converted to PASS.

Sol disposition is **SPLIT**, with each failure routed to its actual owner:

- adapter-count/source expectations -> ROUND 06 Collector and Acquisition;
- retired login/settings template expectations -> ROUND 04 Identity and
  ROUND 08 Cross-Surface Experience, preserving the approved pre-beta access
  decision instead of restoring the removed templates;
- the hand-written `notes` schema -> ROUND 03 clean-clone/schema-contract work.

None of those follow-up items is counted as complete by this Batch.

## Production database protection evidence

Before this Batch, repository `data/monitor.db` had:

- size: `53248` bytes
- UTC modification time: `2026-09-20 00:52:49`
- SHA-256: `F69208CFBA914E455B0BF34424E78E382940EE3C155F7F9C7CA4714E641E40DD`

After all Batch validation, the same file remained `53248` bytes with UTC
modification time `2026-09-20 00:52:49` and the same SHA-256. This is
file-integrity evidence only; database contents and live runtime health remain
**UNVERIFIED**.

## Status semantics

- Authority guard: **TESTED / PASS** (552 production Python modules audited).
- Hermetic basic/isolation/owner/migration tests: **TESTED / PASS** (`29 passed`).
- Only-One governance regression and `git diff --check`: **TESTED / PASS**.
- Legacy `tests/lumenis_smoke.py`: **BLOCKED / exit 1** for the out-of-scope
  stale expectations recorded above.
- Local Alembic acceptance: **BLOCKED** because `alembic.config` is not
  installed in the active Python environment. No dependency was installed.
- Repository-registry supplemental suite: `35 passed, 2 failed`; both failures
  are environment collection/runtime failures caused by missing `python-dotenv`.
- Production DB runtime: **LIVE_UNVERIFIED**.
- Clean-clone CI declares development dependencies before executing the new
  hermetic DB acceptance step; current-head CI execution remains **UNVERIFIED**.
