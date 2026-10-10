# LUMENIS Verification and Historical Test Inventory

## Current formal Product Owner policy — 2026-10-10

Authority: AGENTS.md, Governance Machine v1.3.0 and
`00-GOVERNANCE/evidence/approvals/PO-20261010-BRANCHES-AND-TESTING.json`.
Unit and integration tests are authorized for isolated defect reproduction and regression verification. Relevant regressions accompany scoped changes and run before merge. Inspect historical tests for live collection, credentials, network and training effects before selecting them; do not blindly execute all scripts. Preserve historical assertions and failed receipts. Unit/integration results never substitute for real user E2E.

## Retained blocking checks

- Product Gate: tracked Python compilation, current governance/authority checks,
  static configuration, security/data-boundary checks at their existing severity,
  runtime dependency installation, actual disposable product schema initialization
  and FFmpeg/ffprobe availability. This is not product E2E acceptance.
- App Gate: pinned toolchain, locked dependency resolution, static Flutter analysis,
  current Experience/authority checks and an actual release Web build.
- Owner Closure and Release: genuine running-product user operation with permitted
  real inputs, useful persistent results, save/revise/reopen/recovery, required
  Permission/Evidence/Evaluation and same-version runtime/release/PO acceptance.
  The mapped R01-R15/J1-J8/U01-U25 obligations remain complete.

Missing live evidence remains LIVE_NOT_VERIFIED/OPEN/BLOCKED. A build, static check,
HTTP 200, mock/fixture or CI badge alone cannot establish JOB_CLOSED or RELEASED.
Only actually retained and executed checks may report PASS.

## Preserved historical inventories

Existing `tests/`, `app/test/`, `tests/select_ci_tests.py`,
`tests/ci_environment_tests.txt` and `tests/ci_quarantined_nodeids.txt` are retained
with their historical fixtures, assertions and evidence. Their former Tier A/B/C
and exact-node selections are historical classifications, not current execution
requirements. Do not delete or alter them to manufacture a green result.
Historical FAILED remains FAILED. Removing a suite from the current gate does
not repair an observed product defect; reproduce and repair the actual user
failure through the existing owner and real product operation.

Use explicit reviewed regression selections. Do not expand quarantine or weaken assertions to obtain green; no artificial coverage quota is required. The prior policy is preserved in Git history, including b90fce808959de09e889ed178973a49f0fa8148d.

Renaming module suites does not make them real user E2E.
