# LUMENIS Shared Database Authority Audit — ROUND 03

> Task: `ROUND-03-B001 / LUNA-006A` through `ROUND-03-B003 / LUNA-006B`
> Baseline: `3f93c12858b1ac089e65ae0bf4bddcef036272ae`
> Evidence date: 2026-09-21
> Status: **AUTHORITY AND CLEAN MIGRATION TESTED / LEGACY SMOKE BLOCKED — NOT LIVE VERIFIED**

This evidence is subordinate to current executable source, runtime truth, the
Product Architecture, and the Source Owner Index. It does not claim that a test
fixture is Production Truth or that a static check proves live database health.

## B002 canonical business-schema continuation

`ROUND-03-B002` continued from live `origin/main` baseline
`755c06c68365b84e1899bdc73efef5f479ba61b9`. It moved the root compatibility
module's `SCHEMA`, four additive migration dictionaries, and idempotent apply
logic into `lumenis/shared/database/business_schema.py`. The root
`database.py` keeps the compatibility exports and delegates `init_db()` to the
canonical owner. Exact-value, insertion-order, and AST comparison against the
baseline root implementation passed, including the backfill and event-date SQL
text.

The canonical package now exports the compatibility symbols explicitly.
Regression tests lock the single owner, root/package identity compatibility,
thin delegation, schema-registry source, isolated backfills, the unique report
index, and event-date correction. The scoped B002 suite completed with
`37 passed`; Python compilation, the database-authority verifier, the Only-One
validator, and tracked/untracked whitespace checks all passed. The authority
verifier audited 553 production Python modules and retained only
`connection.py` and `migrations.py` as direct SQLite connection owners.

During Sol acceptance, the original isolation test exposed two protection
defects instead of being accepted as green: it imported `runtime_guardian`
before binding a temporary `ZBC_DB_PATH`, and the pytest seed bootstrap opened
the protected repository database through SQLite, which could create WAL/SHM
sidecars. The first run therefore changed the repository database before a
later assertion captured its baseline. The changed database and sidecars were
preserved outside the repository, and `data/monitor.db` was restored from a
byte-identical copy with the required SHA-256 before testing resumed.

The corrected tests bind an isolated database before any potentially
persistent import, verify call-time redirection with a second temporary path,
fingerprint the main database plus WAL/SHM sidecars, and copy the quiescent
repository seed without opening it through SQLite. A repository seed with any
WAL/SHM sidecar now fails closed rather than checkpointing, ignoring, or
mutating source state. The final scoped run preserved all protected artifacts:

- size: `53248` bytes;
- UTC modification time: `2026-09-20T00:52:49.6770349Z`;
- SHA-256: `F69208CFBA914E455B0BF34424E78E382940EE3C155F7F9C7CA4714E641E40DD`;
- `data/monitor.db-wal`: absent before and after;
- `data/monitor.db-shm`: absent before and after.

This is protected-file integrity and hermetic-test evidence. Production DB
contents and live runtime health remain **UNVERIFIED**.

## B003 clean-clone and migration truth

`ROUND-03-B003` started from the pushed B002 baseline
`f22d095d5c47c7fee44f94ae14afd7f18b870dad`. It makes
`lumenis.shared.database.migrations.migrate()` independently bootstrap a
genuinely empty v0 database through the canonical business-schema owner before
applying the historical migrations. The resulting numeric history is exactly
v1 through v13, and the migrated business tables retain the canonical column
and index contracts.

The v0 compatibility path remains explicit and fail closed. The existing
application startup order (`database.init_db()` followed by `migrate()`) still
passes when all three business tables match the canonical column contract. A
database with only some base tables, or with all three names but incomplete or
changed column contracts, is rejected without current-schema repair, data
rewrites, or a numeric version advance. Existing v9 records retain their data,
NULL values, and empty-string values through v13. A forced v12 migration
failure rolls back both the data mutation and version advance.

The legacy smoke fixture now creates its disposable database through
`apply_business_schema()` and consumes the current `fixed_count` result key.
It completes without a traceback, SQLite error, or missing
`publish_datetime`: 25 checks pass and four stale product-history assertions
remain blocked (two exact-eight-adapter assertions and the retired login and
settings pages).

Sol independently reran the blocking four-file Shared Database suite with
`36 passed`. The isolation-only suite reported `7 passed`; Python compilation,
the database-authority verifier, the Only-One validator, and scoped whitespace
checks exited `0`. The authority verifier audited 553 production Python
modules and retained only `connection.py` and `migrations.py` as direct SQLite
connection owners. Local Alembic collection remains blocked with exit `2`
because the active interpreter cannot import `alembic.config`; no dependency
was installed and this blocker is not reported as PASS.

Two further production-file integrity incidents occurred while closing B003.
First, the pre-fix order-dependent isolation window allowed an import-time
`runtime_guardian.init_db()` to target the repository database; the changed
database was preserved as `lumenis-db-incident-b003-20260921-120123` in the
system temporary directory, and the exact F692 baseline was restored. After
that restoration, another concurrent worktree activity changed
the database again while also introducing unrelated AI Gateway edits. That
variant was separately preserved as
`lumenis-db-incident-b003-external-20260921-120234` before the same exact
baseline was restored.
The concurrent edit and database change were correlated in time but not
attributed as a proven single cause. No unrelated AI Gateway, application,
OpenCode, output, or temporary-tree changes were overwritten or staged.

The corrected isolation fixture keeps `ZBC_DB_PATH` bound to its temporary
database for the entire test lifecycle. Only the synchronous default-path
assertion briefly removes the variable inside a nested monkeypatch context and
restores it before imports or teardown can run. Every final B003 validation
compared the main database plus WAL/SHM presence, size, UTC mtime, and SHA-256
before and after. All remained identical to the protected baseline documented
above, with both sidecars absent. This remains file-integrity evidence, not a
claim of live production health.

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
The blocking authority verifier now exits `0` after AST-auditing 553 production
Python modules. No exception or compatibility allowlist was added.

## Out-of-scope legacy smoke blocker

`python tests/lumenis_smoke.py` had all declared imports available and was run.
After the B003 fixture correction, it exits `1` on current source for two
independent stale expectation groups:

- it expects exactly 8 registered acquisition adapters while current source
  registers 16;
- it expects retired template-backed V4 login/settings pages to render.

The script now completes with 25 passing checks and 4 failing checks. Fixing
those product/test-history expectations is outside this database migration
Batch and was not hidden, skipped, or converted to PASS.

Sol disposition is **SPLIT**, with each failure routed to its actual owner:

- adapter-count/source expectations -> ROUND 06 Collector and Acquisition;
- retired login/settings template expectations -> ROUND 04 Identity and
  ROUND 08 Cross-Surface Experience, preserving the approved pre-beta access
  decision instead of restoring the removed templates.

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

- Authority guard: **TESTED / PASS** (553 production Python modules audited).
- Hermetic basic/isolation/owner/migration tests: **TESTED / PASS** (`36 passed`).
- Only-One governance regression and `git diff --check`: **TESTED / PASS**.
- Legacy `tests/lumenis_smoke.py`: **BLOCKED / exit 1** (`25 passed`, `4 failed`)
  for the out-of-scope stale expectations recorded above.
- Local Alembic acceptance: **BLOCKED** because `alembic.config` is not
  installed in the active Python environment. No dependency was installed.
- Repository-registry supplemental suite: `35 passed, 2 failed`; both failures
  are environment collection/runtime failures caused by missing `python-dotenv`.
- Production DB runtime: **LIVE_UNVERIFIED**.
- Clean-clone CI declares development dependencies before executing the new
  hermetic DB acceptance step; current-head CI execution remains **UNVERIFIED**.
