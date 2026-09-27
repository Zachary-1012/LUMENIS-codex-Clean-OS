# ROUND 06 — remove legacy Collector daily quotas (2026-09-27)

Status: **TESTED source**, ROUND 06 **REWORK**. Product Owner cancelled the old Collector daily/manual collection count limits during P0 Global data work.

The existing SYSTEM Collector policy now defaults to **no product-wide daily count cap**. An explicitly configured source-specific cap remains possible when required by that source. The active secondary collection path no longer reads the old daily count as a prerequisite or returns `DAILY_COLLECTION_CAP` by default. The legacy scheduler no longer blocks after 12 total or 3 manual runs, and its status/API projection reports `null` limits rather than falsely advertising remaining quota. Historical counts remain observability data.

The per-request result batch bound, short local spacing/cooldown, source response limits, risk stop, exact Permission, source authorization and SSRF/DNS protections remain active. This Batch changes only the artificial day/manual quotas; it does not grant automatic collection or any Cookie/session access. Final-user AUTO remains opt-in and the prelaunch public baseline stays within its approved source scope.

Disposable v18-seed regression: `test_safe_collection_contract.py`, `test_secondary_collection_surface.py`, `test_prelaunch_exact_scope_import.py`, `test_public_source_adapters.py` **41 passed**. The exact-scope integration test makes old daily-count lookup raise if touched, and the legacy scheduler test proves counts above the former limits no longer block manual collection. Python syntax, Constitution Gate, diff check and current takeover governance gate were run for this Batch. No hosted CI result or real-user E2E is claimed.
