# LUMENIS · CODEX START HERE
## Pre-Codex handoff snapshot · 2026-09-10

This folder is the current handoff package. It is evidence, not a declaration that the product is production-ready.

## Canonical online baseline at package creation

- Canonical production repository candidate: `Zachary-1012/LUMENIS-codex-Clean-OS`
- Online `main` verified before this package: `ab67612367c172ced2dff62b44e98de86469d1e6`
- Commit message: `docs: add Doubao to Codex pre-production handoff markdown`
- Parent: `b1cf9b3385c3e34bbbf932288dbdb12bbd465730`
- If HEAD moves, inspect only drift; do not redo whole-repository discovery.

## What has been done

1. P0-C implementation exists in `2a3be0ab2ef79cb0274c5b9a21114f3ce2e371af`.
2. P0-C focused verification recorded `69 passed`; full-suite evidence recorded `4074 passed / 49 failed / 14 skipped / 1 error`.
3. P0-D read-only handoff work inventoried DB isolation risks, runtime/route/frontend truth, capability gaps, P0-C carry-over, NO-GO gates, source evidence and Codex tickets.
4. Two workbook handoff summaries are included in this folder; they preserve the workbook structure, sheet ranges, major evidence and resume entrypoints in Git-readable text.
5. A five-repository truth lock is included so Production Truth is not confused with legacy, AI, command, growth/research or historical repositories.

## Current status

`PRODUCTION CONVERGENCE / NOT PRODUCTION READY`

Known open gates include DB path/isolation closure; real isolated server runtime verification; route/API/frontend reconciliation; P0-C FK/migration residuals; Evidence/Canonical/Metric ownership; remaining full-suite failures; Critical E2E; Security/Recovery; Production Acceptance; Release lineage/rollback.

## Read order

1. `01_FIVE_REPO_TRUTH_LOCK.md`
2. `02_CODEX_ZERO_DISCOVERY_MASTER.md`
3. `03_P0C_WORKBOOK_HANDOFF.md`
4. `04_P0D_WORKBOOK_HANDOFF.md`
5. Existing repository P0-C/P0-D evidence artifacts and current source

## Codex resume protocol

First run only:
- `git status`
- `git branch --show-current`
- `git rev-parse HEAD`
- verify current canonical GitHub HEAD

If baseline still matches relevant source facts, do not repeat full repository discovery. If drift exists, inspect only changed scope.

Then execute the first dependency-valid P0 ticket:
`Ticket -> Change -> Tests -> Isolated Runtime -> API/DB/UI truth -> Critical E2E where applicable -> Evidence -> Focused Commit`.

## Truth rules

- File existence != capability completion.
- Route declaration != runtime registration.
- HTTP 200 != correct data.
- README/Registry != runtime evidence.
- UNKNOWN remains UNKNOWN until proven.
- Never modify protected/production/history DBs to make tests pass.
- Never delete tests or legacy capability evidence to manufacture green status.
- Never merge five repositories blindly.
- Do not declare Production Ready until all six production gates pass.