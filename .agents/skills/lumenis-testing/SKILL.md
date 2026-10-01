---
name: lumenis-testing
description: Must use after LUMENIS code changes or when choosing verification depth, diagnosing failures, assessing CI, or deciding whether a task may be called complete.
---
# Proportional Testing
Progress fast/static -> targeted unit -> affected integration -> neighbor regression -> representative/domain E2E -> full regression at convergence/release. Widen for persistence, Permission, Evidence, Canonical contracts, shared primitives, and runtime infrastructure. Never delete, skip, swallow, or weaken a legitimate blocking test to get green. Keep hermetic and live acceptance evidence distinct.

For a concrete bug, reproduce once, resolve the exact owner and research current official documentation and maintained GitHub implementations before repeated trials. Fix the selected cause, run affected checks and required gates once per coherent outcome Batch, then return to the real job. Repeat only when source, hypothesis or an unresolved risk changes; do not use unrelated scans or repeated tests as progress.
