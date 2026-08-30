# Dual-Repository Release State

Baseline ID: ZB-PROD-2026-08-31-04
Status: ACTIVE / HARD PRODUCTION GATE

> This file records the current cross-repository facts. GitHub HEAD and current source are authoritative if this document becomes stale.

## Current State

| Field | Value |
|---|---|
| Core repository | Zachary-1012/Z-Brand-Core |
| Core visibility | Private |
| Core HEAD | 9b9dfde60acbcaaa2a2011b4e57aa96a7a4a24d0 |
| Core version | v5.9.8 development line |
| DCC repository | Zachary-1012/Development-Command-Console |
| DCC visibility | Private |
| DCC HEAD | 28041521c349c5fa6f6e11197255cf44e7080750 |
| DCC version | v0.3.x development line |
| Core pinned DCC SHA | 51d6a7353af4d244faa09e59fdc92a3d6a03dfd1 |
| DCC HEAD vs pinned | AHEAD / normal |
| DCC Release Candidate | NOT DECLARED |
| Promotion to Core | NOT APPROVED |

## Integration Contract

- Core remains the production/business source of truth.
- DCC remains the development/audit source of truth.
- DCC HEAD may advance without changing Core's pin.
- Core pin changes require an explicit DCC Release Candidate and Core compatibility/regression verification.
- No automatic DCC-to-Core promotion.
- No DCC source copy is permitted inside Core.
- Both repositories remain Private.

## Current Security Boundary

DCC WRITE / COMMIT / MERGE / DEPLOY / EXEC remain DENY unless a future approved baseline explicitly changes them. No token, secret, cookie, credential, or private key belongs in repository source or documentation.

## Change Protocol

Before writing to either repository: re-read remote HEAD and this state. If remote HEAD moved, stop and re-plan. Never force-push or silently resolve concurrent changes. After every write, re-read GitHub and verify the resulting commit and changed-file scope.

## Promotion Record

Current DCC pinned commit: `51d6a7353af4d244faa09e59fdc92a3d6a03dfd1`.

The current DCC HEAD is newer because the dual-repository policy was added after the pinned commit. This is expected; the new policy does not itself authorize promotion. A future promotion must be a separate, explicit Core submodule update after testing and approval.
