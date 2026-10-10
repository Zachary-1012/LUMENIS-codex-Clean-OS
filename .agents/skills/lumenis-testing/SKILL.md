---
name: lumenis-testing
description: Must use after LUMENIS code changes or when choosing verification depth, diagnosing failures, assessing CI, or deciding whether a task may be called complete.
---
# Real Product Verification
Follow AGENTS.md and the current machine verification_policy. The 2026-10-10 PO instruction restores targeted unit/integration regressions. Inspect side effects, use isolated data and bounded commands, and preserve legitimate assertions and historical failures. Classify evidence honestly: unit/integration, build/static/security, running-product E2E and actual user outcome are distinct.
Verify the complete approved user task through existing owners, useful results, save/revise/reopen and recovery. A fixture, empty result, HTTP 200 or CI badge cannot establish product closure. Tests do not authorize live collection, external inference, GPU training, deployment or spending.
