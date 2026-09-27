# ROUND 06 — US CTH internal source snapshot, 2026-09-27

State: **LOCAL PRODUCT DB VERIFIED / SOURCE IMPLEMENTATION NOT PUBLISHED / ROUND 06 REWORK**.
This records a real prelaunch data increment, not acceptance of Global
Commercial Coverage, commercial source rights, scheduled maintenance or user E2E.

The actual local `data/monitor.db` is schema v18. Fifty distinct Regency Centers
venue pages were read through the existing public HTTP collector and bound to
exact CTH Subjects. For each page the local operator verified the official
venue name/address, signed `app_evidence_records`, Raw→Canonical scope lineage,
and a source-linked `VENUE_LOCATION=US` assertion. The assertions remain
`UNREVIEWED`. The [50-row metadata snapshot](ROUND-06-CTH-US-INTERNAL-SOURCE-SNAPSHOT-2026-09-27.jsonl)
contains source URLs, identities, content hashes and Evidence/relation references;
it contains no copied page body. SHA-256 of that JSONL:
`e2b0d31de6437b659338095446c12083a9932a70ce1bf04d8113136dd933a61a`.

| Local product DB readback | Before this cohort | After |
| --- | ---: | ---: |
| Registry (BMP / CTH) | 107 (101 / 6) | 157 (101 / 56) |
| Raw / Canonical | 169 / 169 | 219 / 219 |
| Signed Evidence / web runs | 142 / 142 | 192 / 192 |
| Entity relations | 219 | 269 |
| Distinct US CTH `VENUE_LOCATION` Subjects | 0 | 50 |
| Raw quality `missing` / `ok` | 135 / 34 | 185 / 34 |
| Orphan VERIFIED scope Evidence | 0 | 0 |
| `PRAGMA integrity_check` / FK violations | `ok` / 0 | `ok` / 0 |

These 50 properties are one operator and one venue family across 13 US state
abbreviations. They do not establish the approved/versioned global inclusion
inventory or representative commercial coverage. The [official Regency site
terms](https://www.regencycenters.com/terms-of-service) allow personal/internal
business use on one computer while restricting redistribution/resale. The local
operator therefore marked every record `INTERNAL_ONLY_PENDING_REVIEW`; this
cohort is **not** approved for user-facing commercial distribution or automatic
scheduled collection.

Execution: a pre-write SQLite backup was made at
`C:\Users\28049\AppData\Local\Temp\lumenis-prelaunch-db-backup-9cz_j8w0\monitor-before.db`.
The exact 50-source apply returned 50 verified and 0 blocked. A separate
read-only reopen returned 50/50 verified with 50 relation IDs. Immediate Run 2
returned 50/50 `ALREADY_VERIFIED` and no new Subject/Raw/Canonical/Evidence/
relation rows. `python -m py_compile scripts/prelaunch_cth_us_venues.py` passed;
`python -m pytest --noconftest -q tests/test_prelaunch_local_public_import.py`
passed 2 tests. A broader local command that also included
`tests/test_scope_schema_migration.py` had 3 failures: its isolated v13/v14
fixtures lack the v18 relation prerequisite `notes` columns. That command is
**not** a PASS and the fixture/migration test gap remains open under the Shared
Database owner.

The local import script and its intertwined Collector/Registry/Scope/Persist
dependencies remain uncommitted and are not a remotely reproducible product
capability. The product DB is ignored by Git and was not pushed. This online
metadata snapshot reports local truth only. Global Commercial Coverage and
Global Brand Coverage remain `NO / NOT VERIFIED`; Guangzhou reference remains
`PARTIAL`; `FULL_UNIVERSE_READY`, `RELEASED`, `OPERATING` and
`COMMERCIAL_READY` remain `NO`.
