# LUMENIS Single-Mainline Branch Consolidation V1

> Status: **COMPLETE for repository branch convergence**.
> Product Production Readiness is a separate gate and is not implied by this document.
> `main` is the only long-lived development line and the only remote production-candidate truth.

## 1. Canonical rule

`main` is the only long-lived development line.

Short-lived task branches may be used only to isolate one coherent engineering change. Valid implementation, tests, governance and evidence must converge back into `main`. No long-lived production, integration, handoff, research or feature branch may become a second source of product truth.

Before retiring or aligning a branch, prove one of the following:

1. it has no unique commits relative to the convergence line; or
2. all unique valid implementation/tests/evidence have been merged or selectively salvaged; or
3. historical/superseded commit history has been preserved without restoring the stale tree as current Production Truth.

Never delete or overwrite unique implementation merely to obtain a clean branch list.

## 2. Final convergence result — 2026-09-13

PR #4 was merged into `main` as the single-mainline engineering baseline.

The convergence absorbed or preserved, as appropriate:

- truthful blocking compile + hermetic pytest CI;
- explicit Environment / Production-Live test tiers (`excluded != PASS`);
- bilingual Chinese/English README;
- compact model-neutral `AGENTS.md` execution router;
- human maintainability / feature-closure / E2E / release governance;
- third-party / open-source inventory and replaceability boundaries;
- portable production launcher root resolution;
- narrow credential-path false-positive repair without weakening real credential protection;
- valid DB isolation / Permission / Experience runtime work from `codex/production-convergence`;
- older local-AI / runtime-identity / migration-isolation ancestry for historical reuse without restoring stale runtime ownership;
- historical handoff / Experience delivery / research ancestry without promoting those branches back into Production Truth.

Repository branch inspection after convergence verified that every listed remote branch ref can fast-forward to the final `main` without force. All listed refs were then aligned to the same `main` commit. No side branch retained a unique tip or independent development authority.

Because the available GitHub connector does not expose branch-ref deletion, historical branch names may remain visible in GitHub. Their presence is cosmetic only: after alignment they point to the same commit as `main` and are explicitly retired. They must not be used as development entrypoints.

## 3. Previously unique production branch

### `codex/production-convergence`

This branch previously contained six unique production commits. Valid implementation was selectively absorbed while preserving current governance/CI/startup truth.

Absorbed areas include:

- `db_paths.py` canonical call-time DB path resolver;
- DB-path changes across active persistence writers;
- PermissionGate enforcement for Experience AI intent writes;
- deterministic Experience screen-builder loading;
- Experience candidate E2E / DB isolation / Permission regression tests;
- semantic asset-admission implementation/tests where applicable.

Explicitly not restored from its old tree:

- obsolete CI state;
- obsolete local launcher/path assumptions;
- stale README/AGENTS/governance copies.

The branch no longer contains unique commit ancestry.

## 4. Older integration chain

Historical chain:

```text
integration/local-open-source-ai-runtime-v3
→ integration/p0b-runtime-identity-v1
→ integration/p0c-test-migration-isolation-v1
```

The highest tip was folded into the convergence ancestry without restoring its stale tree over current Production Truth.

Important ownership decisions remain:

- historical `runtime_identity.py` / release-manifest work is reusable implementation evidence only until adapted to the current app/preflight/DB owners and retested;
- historical `database_isolation.py` does not become a second DB resolver; current `db_paths.py` owns path resolution;
- historical local-AI/provider code is not automatically reactivated; current AI Gateway/provider contracts win.

All three integration branch refs are retired and aligned with `main`.

## 5. Historical handoff / research branches

Historical handoff, Experience delivery/import and research branches are preserved in Git ancestry for evidence and auditability. They do not own runtime or product truth.

This includes the historical `handoff/*`, `handoff-import-v25`, and `research/autonomous-optimization-shadow` lines that were previously present in the repository.

All visible historical branch refs are retired and aligned with `main`.

## 6. Current product blocker handoff

Repository convergence is complete; product convergence is not.

Do not perform branch archaeology again. Continue only from current `main` and current executable truth.

Canonical point-in-time blocker handoff:

`00-GOVERNANCE/handoff/CODEX-CURRENT-BLOCKERS-20260913.md`

Current highest dependency order begins with:

```text
canonical call-time DB identity / import-time persistence consumers
→ DBISO + Experience + subject/topic/AI-task focused regression
→ Python reload/type identity contract
→ semantic memory / asset admission
→ AI/provider contract
→ ad_intelligence ownership decision
→ IC auth/permission
→ secondary-platform state semantics
→ full hermetic CI
→ Production/Live local acceptance
→ startup / health / runtime
→ critical/domain closed-loop E2E
→ G0→G16 release convergence
```

## 7. Non-negotiable safety

- Never create a second DB/API/Evidence/Permission/Runtime/Subject Context truth.
- Never use an old branch name or old HEAD as current implementation authority.
- Never restore an older branch tree over current source merely because historical code once worked.
- Never reclassify deterministic product failures as Environment/Live solely to get green CI.
- Never mark Product Production Ready from branch convergence or clean GitHub CI alone.
- Never force-push `main`.

## 8. Completion semantics

Repository branch convergence is complete when:

```text
main = only long-lived development truth
AND
all unique valid implementation is represented in main
AND
all historical-only value is preserved as ancestry/evidence
AND
no active feature/runtime implementation exists only on a side branch
AND
all visible remote branch refs are equal to or safely retired behind current main
```

Current repository branch convergence satisfies this definition.

This does **not** mean:

```text
Hermetic CI = PASS
Production/Live = PASS
Critical E2E = PASS
RELEASED = YES
OPERATING = YES
PRODUCTION_READY = YES
```

Those states require the remaining product/runtime gates to be completed from current `main`.