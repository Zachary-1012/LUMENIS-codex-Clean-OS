# ROUND 06 — prelaunch exact public import (2026-09-27)

Status: **TESTED source / isolated live Source→Raw→Evidence→Canonical**. ROUND 06 remains **REWORK**; Global Commercial/Brand Coverage and full-universe readiness remain **NO**, Guangzhou reference remains **PARTIAL**.

The existing SYSTEM Collector `public_http` entry now accepts an explicit, local prelaunch CTH Subject or BMP BrandFocus scope only when the source URL and entity have an exact `DATA_IMPORT` approval and the entity exists in the canonical Registry. Normal user collection remains manual. The existing Raw importer, signed Evidence writer and exact-scope persistence owner are reused. Known cross-scope raw identities are rejected before import; a missing/partial import or failed Evidence/scope write cannot report verified Canonical completion. No new Collector, Evidence or database owner was added.

Verification at the accepted source snapshot:

- Disposable v18 copy of the current product DB; synthetic signing key only in that copy. The product DB was not the test target.
- `tests/test_prelaunch_exact_scope_import.py`, `tests/test_secondary_collection_surface.py`, `tests/test_public_source_adapters.py`, `tests/test_p0_exact_raw_canonical_bind.py`: **34 passed**, including exact CTH/BMP binding, second manual run, permission denial, and cross-scope conflict. `git diff --check`: PASS.
- Constitution Gate: PASS.
- Real network source: [Nike official newsroom article, published 2026-09-09](https://about.nike.com/en/newsroom/releases/nike-nba-standard-issue-collection-reinvents-fan-wear). On a disposable DB copy, first run imported 1 Raw + 1 signed Evidence + 1 VERIFIED Canonical under Nike BMP; second run updated the same identity without duplicate Raw or Canonical. A later process reopened the disposable DB, collected again, and retained one Raw/Canonical identity. The source publication timestamp remained `2026-09-09T16:30:00-07:00`; it was not replaced with capture time. SQLite integrity `ok`, FK violations `0`.

Limits: this does not promote the Nike article or any candidate to the product DB, prove platform-wide source rights, prove GLOBAL coverage, establish continuous scheduled refresh, prove downstream CTH/BMP user results, or pass real-user E2E. Existing accounts/password work remains deferred. `HOSTED_CI` was not used while hosted execution is unavailable.
