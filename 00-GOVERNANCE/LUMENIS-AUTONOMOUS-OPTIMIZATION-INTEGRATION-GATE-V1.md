# LUMENIS Autonomous Optimization Integration Gate V1

Status: `GOVERNANCE / SHADOW INTEGRATION`

This gate governs temporary use of external open research implementations and patterns during LUMENIS release convergence.

## Objective

Accelerate current convergence without contaminating Production Core, while preserving a clear path to LUMENIS-native replacement.

## Rules

1. Research/benchmark infrastructure is R&D infrastructure, not Production Truth.
2. External projects must be version-pinned and source-traced before any source-level reuse.
3. License compatibility must be checked per repository version and for material transitive dependencies/assets; repository license alone is not sufficient for datasets, weights, model artifacts, or third-party bundled assets.
4. Prefer method adaptation or adapter isolation over source copying.
5. Any temporary reuse must have an explicit replacement owner/contract and removal path.
6. No external research dependency may become required for LUMENIS startup, data truth, core API, reporting, security, or release acceptance.
7. Shadow mode may observe, benchmark, propose, and experiment only in isolated workspaces/branches.
8. Promotion to current code requires normal tests, Evidence, diff review, regression, approval, and release gates.
9. Benchmark wins are invalid if they reduce correctness, Production Truth fidelity, Evidence completeness, security, permissions, recoverability, or test coverage.
10. Current release convergence has priority. If the research layer introduces instability, excessive resource use, or release delay, disable it without affecting Production Core.

## Temporary-to-native migration

```text
External Reference
→ License/Source Trace
→ Isolated Adapter
→ Shadow Benchmark
→ Evidence
→ LUMENIS-owned Contract
→ Native Implementation
→ Parity Benchmark
→ Dependency Removal
→ Regression Proof
```

## Allowed now

- research documentation and source references;
- benchmark design;
- read-only profiling;
- fixed-budget isolated experiments;
- candidate patches outside Production main;
- Evidence-backed keep/reject decisions.

## Forbidden now

- direct dependency from Production Runtime to external research repositories;
- automatic merge/push to main;
- autonomous deployment;
- autonomous DB migration;
- unbounded AI/CPU/GPU loops;
- copying code without attribution/license trace;
- claiming an external-inspired capability is LUMENIS-native before replacement is complete.

Principle: `Accelerate release now, preserve replacement freedom later.`
