# ROUND 03 — exact CTH/BMP Canonical scope (2026-09-27)

Status: `TESTED / SOURCE ONLY`; Round 03 remains `REWORK`.

Shared Database identity resolution now reads the existing Subject Registry and
returns an exact CTH Subject or BMP BrandFocus as `UNVERIFIED`. It does not
manufacture permission, source Evidence or a verified status. The existing
Canonical writer now carries v14 scope columns through `CanonicalRecord` and
Raw-note mapping, rejects CTH/BMP identity mixing and domain mismatch, and
requires writer-authenticated Evidence with exact scope and source ID before
accepting `VERIFIED`. A previously verified Canonical row cannot silently be
downgraded or rebound to another Evidence identity.

On the exact staged snapshot, 54 focused and affected Canonical/BMP/time
regressions passed with the Constitution Gate. A separate read-only check of
one existing VERIFIED CTH row and one VERIFIED BMP row in the actual local v18
product DB confirmed that the revised note mapper preserves each exact focus
and scope Evidence reference and agrees with stored Canonical lineage.

No product database write, migration or historical backfill is part of this
source Batch. It does not by itself ingest a new venue/brand or close the full
Collector→Raw→Evidence→Canonical chain. Those are separate Round 06 gates.
Real user E2E, Global coverage, release and operating remain unverified.
