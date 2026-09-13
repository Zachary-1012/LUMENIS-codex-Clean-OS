# LUMENIS — Current Codex Blockers (2026-09-13)

> Point-in-time handoff only. Re-verify current `origin/main`, local working tree and runtime before acting.
> Current source/runtime/tests outrank this file. Do not turn this handoff into a mandatory full-read step for unrelated tasks.

## What has already been separated

Clean-checkout CI is being split from tests that require protected production data, real cookies/sessions, resident browsers, a running local service, live providers, or manual top-level smoke execution.

Canonical CI interpretation:

- `tests/CI_TEST_TIERS.md`
- `tests/ci_environment_tests.txt`
- `tests/ci_quarantined_nodeids.txt`
- `tests/select_ci_tests.py`

`excluded from clean CI != PASS`. Environment/live suites remain required Production Acceptance evidence.

## Latest completed high-signal hermetic run

The latest completed clean-checkout run after environment/manual-script separation selected **243 hermetic test files** and reached 100% execution. Infrastructure gates passed; the remaining deterministic failures were concentrated in the following owners/contracts.

### P0 — Repository / security truth

1. `tests/test_runtime_preflight.py`
   - tracked-credential/data-boundary check reports `fail`;
   - preflight reports one blocker.
   - Resolve the exact tracked boundary path first. Do not weaken the preflight assertion.

### P0 — Production truth / Experience

2. `tests/test_experience_runtime.py::test_ai01_traceability_not_fabricated`
   - current result exposes `100.0` where the contract expects `None` when traceability is not evidenced.
   - Preserve `missing/unknown != 0/100`; fix the owner, not the assertion, unless current canonical contract proves the test stale.

### P1 — AI/provider contracts

3. `tests/test_ai_channel_flag.py`
   - model override / `has_thinking` contract mismatches.

4. `tests/test_ai_channel_multiprovider.py`
   - auth-error fallback semantics mismatch (`ark` fallback attempted where test expects no fallback).

5. `tests/test_ad_intelligence.py`
   - imports `ad_intelligence.models.*`, but the current `ad_intelligence/` package has no `models/` package.
   - Determine from current product ownership whether implementation is missing or the test is obsolete. Do not create a parallel model stack just to satisfy imports.

### P1 — API permission/auth contract

6. `tests/test_ic_contracts_p1.py`
   - three smoke requests return `401` where tests expect `200`.
   - Resolve against current authentication/permission truth; do not disable auth to obtain green tests.

### P1 — Collector state semantics

7. `tests/test_secondary_platforms_main.py`
   - Bilibili detail and Weibo comments paths return `SESSION_EXPIRED` where tests expect `COLLECT_ERROR` for not-implemented behavior.
   - Resolve the six-state semantics at the adapter owner.

## Recommended execution order

```text
Security/preflight boundary
→ AI-01 truthfulness
→ AI/provider contract cluster
→ ad_intelligence ownership decision
→ IC permission/auth contract
→ secondary-platform state contract
→ hermetic CI rerun
→ environment/live Production Acceptance on the real local runtime
→ canonical DB/config + final full regression
→ production startup / health / core runtime
→ critical/domain E2E
→ G0→G16 continuation
```

## Rules for the next executor

- Do not reclassify deterministic failures as environment tests just to make CI green.
- Do not rerun full repository discovery before working.
- Read only the owner/source/tests needed for the active blocker.
- Prefer `reuse → adapt → bind → verify`.
- Do not claim `PRODUCTION_READY` from clean GitHub CI alone.
- After deterministic CI is green, return to the real local production/runtime gates rather than continuing CI cleanup indefinitely.
