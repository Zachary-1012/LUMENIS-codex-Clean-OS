---
name: lumenis-testing
description: Must use after LUMENIS code changes or when choosing verification depth, diagnosing failures, assessing CI, or deciding whether a task may be called complete.
---
# Real Product Verification
Follow AGENTS.md and the machine contract's current verification_policy. The PO
formally forbids creating/running unit and integration suites, including renamed
module-level contract/functional/scenario tests. Preserve their historical files,
assertions and failures. Do not pursue coverage or gate user work on those suites.

Verify actual useful outcomes: real task -> existing-source repair -> build/run ->
actual user operation -> real result -> save/revise/reopen -> recovery -> acceptance.
Retain applicable compilation, static quality/security, Permission/Evidence/
Canonical/Effect Fence and data consistency. Real E2E uses the running product
and permitted real input; mocks, fixtures, isolated calls or HTTP 200 cannot pass.
Repair known real defects. Reuse unchanged evidence, and run only retained checks
needed for the coherent outcome; never claim historical failed runs passed.
