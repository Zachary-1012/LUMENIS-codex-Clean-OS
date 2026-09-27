# ROUND 06 — Exact prelaunch Atom import and refresh

## Accepted source slice

The existing SYSTEM Collector can take a manually approved HTTPS Atom source for one registered CTH Subject or BMP BrandFocus. It routes the source through Raw, signed exact-scope Evidence, Canonical Data and the existing Shared Database platform-content owner. Native Atom fields remain source-specific; absent engagement values remain unknown. Repeated unchanged reads keep Raw/Canonical identity and their original Evidence reference. Changed observations receive new signed Evidence, retain the original Raw/Canonical provenance, update the current native observation and append a metric snapshot only when the actual view count changes. A mixed feed with an old and a new item binds each item's first scope separately.

The Evidence schema owner now adds nullable `domain_id` and `product_id` before the v18 relation migration needs them. Existing Evidence rows are not rewritten. The accepted public-source transport rejects YouTube `/feeds/videos.xml` before DNS/HTTP and after redirect selection; the [official robots file](https://www.youtube.com/robots.txt), checked 2026-09-28, disallows that path. Earlier feed reads are historical observations, not authorization for future refresh.

## Verification at the accepted source snapshot

- Base: `ca85e1647abf6e3ebac340a5d919de0309cef769`; isolated archive and exact staged patch, no product-DB test seed.
- `python -m pytest -q tests/test_prelaunch_local_atom_import.py tests/test_evidence_schema_owner.py tests/test_shared_database_v17_evidence_migration.py tests/test_shared_database_entity_relations.py`: **11 passed, exit 0** in the isolated current-source archive, independently rerun by Sol. The cases include fresh v0→v18, v17/v18 regressions, first/unchanged/changed/missing observations and mixed old/new feed entries.
- `python scripts/audit_tools/verify_ai_native_constitution.py`: **PASS** in the isolated archive and shared checkout. `git apply --cached --check` and staged diff whitespace check passed.
- No approved live Atom source was collected into the product DB by this Batch. The older 30 YouTube-derived platform records remain historical data pending source-rights disposition; they are not evidence of sustainable authorized refresh.

## REAL DELIVERY CARD

`REAL USER JOB`: a CTH/BMP operator reads a real authorized content source and uses its native observations inside an exact selected Subject or BrandFocus. `ENTRY`: GLOBAL / ALL, then an explicit focus and manual collection request. `REAL INPUT`: an approved feed URL and a registered exact entity. `END-TO-END PATH`: the isolated fixture proves Collector → Raw → signed Evidence → Canonical → native observation and append-only metric history; an authorized live product source and real user result remain unverified. `USER-VISIBLE RESULT`: not yet accepted. `FAILURE/RECOVERY`: unapproved YouTube feed fails before network access; missing data is not zero; unchanged and changed reruns preserve lineage. `ACCEPTANCE ASSERTION`: ROUND 06 remains `REWORK`.

`COMMERCIAL OVERLAY IMPACT`: source rights and commercial use remain source-specific and unverified for a live Atom provider. `GLOBAL UNIVERSE / DATA MATURITY IMPACT`: Global Commercial Coverage and Global Brand Coverage remain `NO / NOT VERIFIED`; Guangzhou Taikoo Hui reference remains `PARTIAL`; `LUMENIS_INTERNAL_FULL_UNIVERSE_READY`, `RELEASED`, `OPERATING` and `COMMERCIAL_READY` remain `NO`. This code slice adds no country, brand, commercial entity or platform coverage count.

`CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION`: the official YouTube robots rule was rechecked on 2026-09-28 and mapped to the existing SYSTEM public-source policy guard. Generic authorized Atom feeds reuse the existing adapter; no second Collector, Evidence or database owner was introduced. Live source selection, permission, actual platform fields, schedule and user-job acceptance remain later gates within ROUND 06 and dependent rounds.
