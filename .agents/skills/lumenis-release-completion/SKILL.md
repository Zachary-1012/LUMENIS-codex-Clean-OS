---
name: lumenis-release-completion
description: Must use before saying a LUMENIS implementation, screen, workflow, round, release, or production capability is complete, passed, ready, live, released, or operating.
---
# Completion Gate
Use exact repository acceptance requirements and REAL USER WORK E2E where applicable. C1–C6 retain engineering source responsibilities; product outcomes close against the five Architecture rounds and the mapped R01–R15/J1–J8 requirements. A mapping is not a PASS. A Codex Cloud candidate is not product deployment or local runtime proof. The Product Owner performs repeated core-job acceptance only after engineering is fully operable; development-window E2E does not mark `USER_VERIFIED`, `RELEASED` or `OPERATING`.

IMPLEMENTED=code exists; TESTED=isolated automated verification at its recorded scope, not real user closure; VERIFIED=runtime/E2E proves behavior; RELEASED=production/security/recovery/rollback gates pass; OPERATING=real operation has live/scheduled evidence. Never upgrade one state into another. Inspect diff, run proportional verification, capture evidence, and distinguish local-only from pushed/CI-verified truth.
