# Dual-Repository Release Policy

## Baseline Lock

Baseline ID: ZB-PROD-2026-08-31-04

This policy is a hard repository boundary. Facts from GitHub and current source take precedence over chat history or AI-generated reports.

## Repository Roles

- Z-Brand-Core is the business source of truth for CTH-POMS, ZBMP, collectors, analysis, evidence, reporting, and production logic.
- Development-Command-Console (DCC) is the development/audit source of truth for command contracts, tests, evidence, security gates, and the Local AI Bridge.
- Both repositories remain Private.
- DCC remains an independent repository and is referenced by Core only as a Git submodule.

## Submodule Rule

- Core stores a pinned DCC commit SHA.
- DCC HEAD may advance independently.
- DCC HEAD != Core pinned SHA is normal and is not itself a defect.
- A new DCC HEAD MUST NOT automatically change Core's pinned SHA.
- Core may advance the pinned SHA only after the DCC commit is explicitly classified as a Release Candidate and passes Core compatibility/regression checks.

## Hard Change Boundaries

1. No DCC source-code copy may be recreated inside Core.
2. No Core business code may be modified as a side effect of DCC development.
3. No CTH-POMS/ZBMP production logic may be weakened, bypassed, or silently replaced.
4. No token, secret, cookie, credential, or private key may be committed.
5. No force-push is permitted for baseline synchronization.
6. No automatic conflict resolution is permitted when remote HEAD has moved.
7. Production deployment is DENY unless separately and explicitly authorized.
8. WRITE/MERGE/DEPLOY/EXEC permissions remain denied in the DCC security boundary unless a future baseline explicitly changes them.

## Write Protocol

Before every write to either repository:

1. Read the current GitHub HEAD.
2. Read the current baseline/release-state documents.
3. Verify the expected HEAD still matches.
4. If remote HEAD changed: STOP, re-read, rebuild the patch, and only then continue.
5. Make the smallest possible change.
6. Never include unrelated working-tree changes.
7. Push only the intended commit.
8. Re-read GitHub after push and verify the resulting HEAD and changed files.

## Release Promotion

DCC development -> tests -> security scan -> audit -> Release Candidate SHA -> Core compatibility/regression -> explicit approval -> Core submodule pin update.

Core development does not require DCC to follow every Core commit. DCC integration is performed only at an approved compatibility point.

## Concurrent-Agent Rule

If another agent/user pushes during an operation, the operation is considered stale. Do not overwrite or merge blindly. Re-read the remote state and re-plan from the new HEAD.

## Verification Requirement

A change is not considered complete until GitHub confirms:
- intended files exist with expected content;
- repository visibility remains Private;
- no unrelated business files changed;
- submodule URL and pinned SHA are correct where applicable;
- security boundaries remain intact;
- commit SHA exists on the remote.

## Stop Conditions

STOP and report BLOCKED if any of the following occurs:
- remote HEAD moved unexpectedly;
- unrelated files would be included;
- a private repository cannot be accessed safely;
- a token/secret is detected;
- submodule state is ambiguous;
- tests/security evidence cannot be verified;
- a requested change would cross a hard boundary without explicit approval.
