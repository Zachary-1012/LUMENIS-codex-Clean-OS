# LUMENIS Single-Mainline Branch Consolidation V1

> Status: Canonical repository-convergence rule.
> Goal: `main` is the only long-lived development and production-candidate line.
> This document records branch disposition by content, not by branch name.

## 1. Rule

`main` is the only long-lived development line.

Short-lived task branches are allowed only to isolate a coherent change. Before a branch is retired, one of the following must be proven:

1. `ahead_by = 0` against current `main`; or
2. all unique valid implementation/tests/evidence have been merged or salvaged into `main`; or
3. the branch contains historical/superseded evidence only, and its commit history has been preserved without re-promoting its old tree into current Production Truth.

Never delete/overwrite unique implementation merely to obtain a clean branch list.

## 2. Current audit snapshot

Audit basis: GitHub compare against `main` at `571d15d31ab4012887f7863f9217005c000de9d2`, followed by the active convergence PR branch.

### A. Already absorbed — no unique commits

These branches were verified with `ahead_by = 0` and therefore are not development authorities:

- `codex/ci-truth-convergence-20260913`
- `codex/human-engineering-convergence-20260913`
- `codex/production-experience-wiring`
- `handoff/codex-frontend-gpt-ready-20260911`
- the branch group pointing at `f548669d82974ea065afb310776ec63935896d7d`
- `handoff/frontend-gpt-v24-20260911-codex-ready` (`faddac4c60e49dd2dbf730d91af4f03c8c10a477`)
- `handoff/pre-codex-20260910` (`ab67612367c172ced2dff62b44e98de86469d1e6`)

Disposition: RETIRED / ALREADY IN MAIN.

### B. Unique production implementation — must converge by code, not by history-only merge

#### `codex/production-convergence`

Observed: diverged, `ahead_by = 6`.

Unique work includes production-facing DB isolation/path ownership, Experience runtime builder loading, Permission/action-chain work, candidate E2E tests and related convergence evidence. Examples observed in diff include:

- `db_paths.py`
- DB-path changes across active modules
- `experience_runtime.py`
- `experience_screens.py`
- `experience_v2/06_CONTRACTS/actions/ACTION_REGISTRY.json`
- `tests/test_db_isolation_contract.py`
- `tests/test_ai_intent_permission.py`
- `tests/test_experience_builder_loading.py`
- `tests/test_experience_e2e_candidate.py`

Disposition: **DO NOT RETIRE UNTIL VALID UNIQUE IMPLEMENTATION IS IN MAIN AND RETESTED.**

#### `integration/local-open-source-ai-runtime-v3`

Observed: diverged, `ahead_by = 1`.

Contains a local AI runtime/config/adapter implementation and related tests/evidence. It must be evaluated against the current AI Gateway/adapter ownership before any production adoption; do not blindly reintroduce old provider/runtime behavior.

Disposition: UNIQUE IMPLEMENTATION — dependency-trace and selectively converge.

#### `integration/p0b-runtime-identity-v1`

Observed: diverged, `ahead_by = 2`.

Contains runtime identity/release-manifest/preflight implementation layered on the local-AI integration work.

Disposition: UNIQUE IMPLEMENTATION — dependency-trace and selectively converge.

#### `integration/p0c-test-migration-isolation-v1`

Observed: diverged, `ahead_by = 3`.

Contains DB/test/migration-isolation work plus the prior integration chain, including `database_isolation.py`, migration/test fixture changes and P0C verification assets.

Disposition: UNIQUE IMPLEMENTATION — highest integration branch in that chain; evaluate this branch before separately re-applying its ancestors.

### C. Unique historical / handoff / research evidence

These branches have unique commits, but their observed unique value is primarily point-in-time handoff, research, design-delivery or audit evidence rather than current runtime authority:

- `handoff/codex-zero-discovery-ready-20260910` — large zero-discovery handoff package; observed `ahead_by = 136` from old baseline.
- `handoff/pre-codex-20260910-v2` — five pre-Codex handoff documents; observed `ahead_by = 5`.
- `handoff/frontend-gpt-v24-20260911-final` / `handoff-import-v25` group — old Experience V2 delivery/handoff assets; observed unique commit history against current main.
- `research/autonomous-optimization-shadow` — autonomous-optimization/open-source integration research/governance; observed `ahead_by = 4`.

Disposition: preserve history/evidence without replacing current main tree or reactivating stale runtime assumptions. If a concrete artifact remains useful, place it under the appropriate current governance/archive path and link it; do not make the historical branch an execution authority.

## 3. Active convergence branch

`codex/ci-layering-engineering-20260913` is a short-lived task branch only. Its purpose is to repair CI truthfulness/test-tier semantics, human engineering entrypoints, single-mainline governance and current blocker diagnostics.

It must converge into `main`; it must not become a second permanent line.

## 4. Consolidation order

Use this order to minimize regression risk:

```text
1. Merge current CI/human-engineering convergence into main when its scoped changes are acceptable
2. Rebase/compare current main truth
3. Converge codex/production-convergence valid code + tests
4. Evaluate integration/p0c-test-migration-isolation-v1 as the tip of the older integration chain
5. Salvage only still-valid local-AI/runtime-identity pieces not already superseded by current main
6. Preserve historical/handoff/research branch history without restoring stale runtime trees
7. Run hermetic CI + affected integration/E2E
8. Run Production/Live gates where environment is available
9. Retire/align stale branch refs after unique work is safely represented in main
```

## 5. Non-negotiable safety

- Never merge a branch solely because its name sounds important.
- Never resolve a conflict by blindly preferring the older branch tree.
- Never replace current README/AGENTS/CI/governance with stale branch copies.
- Never drop unique production implementation without explicit classification.
- Never use a history-only merge for branches that still contain unabsorbed production code.
- Never mark branch convergence complete until current `main` tests/runtime prove the integrated result.

## 6. Completion definition

Branch convergence is complete when:

```text
main = only long-lived development truth
AND
all unique valid implementation is represented in main
AND
historical-only branch value is preserved as history/evidence without becoming runtime authority
AND
no active feature/runtime implementation exists only on a side branch
AND
current CI/runtime/E2E validates the converged main tree
```

Branch count alone is not the acceptance criterion; absence of parallel implementation truth is.
