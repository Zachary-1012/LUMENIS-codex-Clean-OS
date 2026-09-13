# LUMENIS Single-Mainline Branch Consolidation V1

> Status: Canonical repository-convergence rule and current convergence evidence.
> Goal: `main` is the only long-lived development and production-candidate line.
> Branch disposition is determined by content and ancestry, not by branch name.

## 1. Rule

`main` is the only long-lived development line.

Short-lived task branches are allowed only to isolate a coherent change. Before a branch is retired, one of the following must be proven:

1. `ahead_by = 0` against the current convergence/main line; or
2. all unique valid implementation/tests/evidence have been merged or selectively salvaged; or
3. historical/superseded commit history has been preserved without restoring its stale tree as current Production Truth.

Never delete or overwrite unique implementation merely to obtain a clean branch list.

## 2. Convergence already completed on the active consolidation line

### `codex/production-convergence`

The branch previously had six unique production commits. Its valid production implementation was selectively absorbed while the branch tip was retained as a merge parent.

Absorbed production areas include:

- canonical DB path resolver (`db_paths.py`);
- DB isolation/path changes across active writers;
- PermissionGate enforcement for Experience AI intent writes;
- Experience screen-builder deterministic loading;
- Experience candidate E2E / DB isolation / Permission regression tests;
- semantic asset-admission implementation/tests where present in the source branch.

Explicitly **not** restored from the old tree:

- obsolete CI workflow state;
- obsolete launcher/local-path assumptions;
- old README/AGENTS/governance copies.

Verified after convergence: comparing the active convergence line to `codex/production-convergence` returns `ahead_by = 0`. The side branch no longer contains unique commit ancestry.

### Older integration chain

The following chain is represented by its highest tip `integration/p0c-test-migration-isolation-v1`:

```text
integration/local-open-source-ai-runtime-v3
→ integration/p0b-runtime-identity-v1
→ integration/p0c-test-migration-isolation-v1
```

The P0C tip was folded into the active convergence history without restoring its stale tree over current Production Truth. This preserves the local-AI, Runtime Identity and migration/isolation implementation history for reuse while preventing old provider/API/config behavior from silently replacing the current application.

Verified after convergence: comparing the active convergence line to `integration/p0c-test-migration-isolation-v1` returns `ahead_by = 0`.

Important implementation decision:

- `runtime_identity.py` / release-manifest work remains valid reusable historical implementation evidence but is **not declared active merely because its history is merged**; it must be adapted to current `app.py`, current preflight and current DB ownership and then retested before activation.
- old `database_isolation.py` is not promoted as a second canonical DB-path resolver because current `db_paths.py` owns path resolution. Useful read-only copy/integrity primitives may be selectively reused behind the current DB contract.
- old local-AI/provider code is not automatically reactivated; current AI Gateway/provider truth wins.

## 3. Historical / handoff / research ancestry preserved

The following unique historical tips have also been folded into the convergence ancestry while retaining the current file tree:

- `handoff/codex-zero-discovery-ready-20260910`
- `handoff/pre-codex-20260910-v2`
- `handoff/frontend-gpt-v24-20260911-final` / `handoff-import-v25` shared historical line
- `research/autonomous-optimization-shadow`

Their history/evidence remains retrievable, but those branches are not runtime or product authorities.

Branches already verified with no unique commits before this convergence included:

- `codex/ci-truth-convergence-20260913`
- `codex/human-engineering-convergence-20260913`
- `codex/production-experience-wiring`
- `handoff/codex-frontend-gpt-ready-20260911`
- the repeated frontend handoff branch group pointing at `f548669d82974ea065afb310776ec63935896d7d`
- `handoff/frontend-gpt-v24-20260911-codex-ready`
- `handoff/pre-codex-20260910`

These are retired development authorities.

## 4. Current active convergence branch

`codex/ci-layering-engineering-20260913` is a temporary consolidation branch only.

It currently owns the in-flight convergence work for:

- truthful hermetic CI versus Production/Live test tiers;
- bilingual human-engineering README;
- compact model-neutral AGENTS router;
- third-party / OSS register and replaceability boundary;
- portable production launcher root resolution;
- security data-boundary false-positive repair;
- branch-history convergence;
- selective recovery of valid production implementation.

It must merge to `main` and then cease to be a separate development authority.

## 5. Known current-source follow-up discovered during convergence

Branch convergence exposed a remaining DB-isolation ownership gap:

- `account/models.py` still captures `DB_PATH` at module import time;
- `skill_execution_chain` uses `account.models.get_db()` for execution traces;
- therefore module reload / environment-path changes can read execution samples from the wrong database identity;
- this can contaminate Experience AI traceability metrics and tests.

This is a real DBISO follow-up. Do not hide it by weakening the traceability assertion or classifying it as an environment-only test.

The canonical repair direction is to make account persistence resolve the current canonical DB path at connection time, without creating another DB truth.

## 6. Remaining consolidation order

```text
1. Complete the current hermetic CI run and retain deterministic failures as real blockers
2. Merge the active consolidation PR into main
3. Confirm every historical/implementation branch is ahead_by = 0 against main
4. Align stale branch refs to final main where repository permissions allow
5. Close temporary convergence PRs
6. Continue deterministic blocker repair from current main only
7. Run Production/Live acceptance on the real local runtime
```

## 7. Non-negotiable safety

- Never merge a branch solely because its name sounds important.
- Never resolve conflicts by blindly preferring an older branch tree.
- Never replace current README/AGENTS/CI/governance with stale branch copies.
- Never drop unique production implementation without classification.
- Never reactivate historical local-AI/provider/runtime behavior merely because its history is now an ancestor.
- Never create a second DB/API/Evidence/Permission/Runtime truth while salvaging old work.
- Never mark repository convergence as Production Ready until current main runtime/tests/E2E prove it.

## 8. Completion definition

Repository branch convergence is complete when:

```text
main = only long-lived development truth
AND
all side-branch tips are ancestors of main / ahead_by = 0
AND
all unique valid current implementation is represented in the active main tree
AND
historical-only value is preserved as history/evidence, not active runtime authority
AND
no active feature/runtime implementation exists only on a side branch
```

This is distinct from product Production Readiness. A single-mainline repository may still have truthful product/test blockers that Codex must repair next.
