# ROUND 03 — Evidence-backed entity relations, v18 (bounded Batch)

Status: **TESTED SOURCE; ROUND 03 remains REWORK**. This is one additive Shared Database Batch, not Global coverage or real-user E2E acceptance.

## Source and scope

- Shared Database v17→v18 adds `lumenis_entity_relation_assertions` and its connection-scoped repository. It preserves the existing Subject Registry, notes, Evidence, Permission and Canonical owners.
- Country roles remain distinct: origin, headquarters, legal jurisdiction, operating market, venue location and market activity. `OTHER` is a query bucket, never a stored country. Venue tenant assertions retain source language and original store name. Every new assertion starts `UNREVIEWED`.
- Writers require a registered exact CTH Subject or BMP BrandFocus, signed writer-authenticated Evidence, the Evidence's exact scope and source-note ID, and the matching scoped note. Tenant writes also require literal shop name/floor in the verified source note and the exact listing URL. No existing record is guessed into a new relation.

## Verification on 2026-09-27

- `pytest --noconftest -q tests/test_shared_database_entity_relations.py tests/test_shared_database_migrations.py tests/test_shared_database_schema_atomicity.py tests/test_shared_database_owner.py`: **33 passed** in the current checkout. `--noconftest` avoids the protected real-DB sidecar safety gate; the tests use explicit disposable connections. The current dirty `business_schema.py` candidate initially regressed caller transaction atomicity, and a test pinned v17. Both were repaired locally before this PASS; the broader dirty candidate is not accepted by this Batch.
- `python scripts/audit_tools/verify_ai_native_constitution.py`: **PASS**.
- Disposable snapshot of the actual v17 DB migrated to v18; the migration backup reopened as v17, data counts matched, `integrity_check=ok`, foreign-key violations 0. A disposable run wrote and read back 5 exact country assertions and 24 bilingual tenant assertions.
- Actual local product DB was separately backed up, then migrated v17→v18. The local import wrote and reread 5 country assertions (CTH Guangzhou/Shenzhen location; BMP Nike HQ/China operation and Le Labo Shanghai market activity) and 214 official Guangzhou Taikoo Hui directory assertions (110 Chinese, 104 English). All 214 tenant readbacks reported signed Evidence `VERIFIED`, remained `UNREVIEWED`; `integrity_check=ok`, foreign-key violations 0. The 214 language-specific assertions are **not** 214 deduplicated stores or accepted BrandFocus identities. Product DB contents are local, ignored by Git, and are not published by this source Batch.

## REAL DELIVERY CARD / limits

Real user job: from GLOBAL, choose a country and CTH Subject or BMP BrandFocus, inspect evidence-backed market/tenant relationships, perform a useful business task, then clear focus. This complete user path **has not run**. No user-visible country selector, four-surface result, source-rights clearance, continuous refresh, 14-country × 50-per-domain coverage or release is claimed. Global Commercial Coverage = `NO / NOT VERIFIED`; Global Brand Coverage = `NO / NOT VERIFIED`; Guangzhou reference = `PARTIAL`; `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`.

COMMERCIAL OVERLAY IMPACT: explicit source rights, permissioned user reads, freshness, evaluation and operating evidence remain open. Failure and recovery: migration backups are retained and reopened successfully; an actual rollback/restart drill is not accepted. This Batch changes `IMPLEMENTED → TESTED` for the relation repository only, while ROUND 03 stays `REWORK`.
