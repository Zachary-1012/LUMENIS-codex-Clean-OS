# Round 06 — exact existing Raw to Canonical binding (2026-09-27)

Status: `TESTED SOURCE / ROUND 06 REWORK`. This is one bounded SYSTEM Collector
persistence path, not P0 Global Universe or real-user Job acceptance.

## Changed owner and behavior

- `lumenis/adapters/persist.py`: `persist_existing_note_scope` validates a
  registered exact CTH Subject or BMP BrandFocus and a writer-authenticated,
  matching Evidence row before binding existing Raw notes and Canonical data.
- The caller supplies a bounded set of raw note identities and owns the SQLite
  transaction. The writer uses a savepoint, rejects domain or Evidence mismatch,
  and preserves a prior VERIFIED binding instead of silently reassigning it.
- Raw and Canonical identity remain on the existing product DB and owners.

## Verification and limits

`tests/test_p0_exact_raw_canonical_bind.py` covers CTH and BMP, idempotent
repeat, close/reopen, unknown publication time, tampered Evidence, cross-domain
Evidence, and rollback after a missing raw member. Tests use a disposable DB
and a disposable signing key. The exact staged-source test result and
Constitution Gate are recorded in the delivery command log; no production DB
write was made by this Batch.

The writer does not register sources or entities, acquire a page, approve
commercial reuse, schedule refresh, or itself close Global coverage. New
official-source data still has to pass Collector, Evidence, exact binding,
downstream consumption, and real-user acceptance.

Real user work E2E: `NOT VERIFIED`. Global Commercial Coverage:
`NO / NOT VERIFIED`. Global Brand Coverage: `NO / NOT VERIFIED`.
Guangzhou reference: `PARTIAL`. Full Universe, RELEASED, OPERATING:
`NO`.
