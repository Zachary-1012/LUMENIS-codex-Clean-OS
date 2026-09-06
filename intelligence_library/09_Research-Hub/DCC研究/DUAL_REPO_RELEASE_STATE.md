# Dual-Repository Release State

Baseline ID: ZB-PROD-2026-08-31-04
Status: ACTIVE / HARD PRODUCTION GATE

> This is a coordination snapshot, not a substitute for live GitHub state. Before every write or promotion, read the live `main` HEAD and the live Core submodule pointer again.

## Snapshot

| Field | Snapshot value |
|---|---|
| Core repository | Zachary-1012/Z-Brand-Core |
| Core visibility | Private |
| Core HEAD observed before this state-document commit | b3ddcd36680203243af06e7adc0919961451e27b |
| Core version | v5.9.8 development line |
| DCC repository | Zachary-1012/Development-Command-Console |
| DCC visibility | Private |
| DCC HEAD observed before this state-document commit | e7e8cd0144e8f0c9a676906f70d1166d8112506c |
| DCC version | v0.3.x development line |
| Core pinned DCC SHA observed | 51d6a7353af4d244faa09e59fdc92a3d6a03dfd1 |
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

The observed Core pin is `51d6a7353af4d244faa09e59fdc92a3d6a03dfd1`. The DCC HEAD can be newer without authorization for promotion. A future promotion must be a separate, explicit Core submodule update after DCC testing, security/audit evidence, Core compatibility/regression verification, and approval.
