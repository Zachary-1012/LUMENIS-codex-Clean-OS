# Learning Runtime — additive implementation

> Baseline: ZB-PROD-2026-08-31-04

## Audit finding

DCC already had `server/learning-store.js`, `server/shadow-learning.js`, their tests, and the five-times-daily inspection workflow. The missing link was that inspection results were not feeding a reviewable learning/Shadow bundle, so the architecture was ahead of the runtime loop.

## Runtime loop

```text
3 repositories
  ↓
5 deterministic inspections/day
  ↓
actual inspection evidence
  ↓
Learning Cycle
  ↓
case records + Shadow candidates
  ↓
REVIEW_REQUIRED
  ↓
Change Plan + Evidence + Gate
  ↓
manual promotion into data/learning/
```

GitHub documents that reusable workflows are appropriate for deterministic repeatable logic and that SHA references improve stability/security; contextual AI reasoning should remain separate from deterministic execution. citeturn0search0turn0search1

Actions artifacts are a staging/audit transport, not the permanent database. GitHub documents artifact retention is configurable; private repositories can retain artifacts for up to 400 days subject to organization limits. citeturn1search1

## Hard Shadow boundary

READ/ANALYZE/RECOMMEND are allowed. WRITE/COMMIT/MERGE/DEPLOY/EXEC and permission or production-rule changes remain denied. Shadow output is advisory and cannot become fact or a production rule without independent Evidence and human approval.
