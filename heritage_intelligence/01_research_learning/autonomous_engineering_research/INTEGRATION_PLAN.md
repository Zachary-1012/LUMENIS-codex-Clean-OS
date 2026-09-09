# LUMENIS Autonomous Optimization Shadow Integration Plan

Status: `READY_FOR_IMPLEMENTATION / SHADOW_ONLY`

## Goal

Use three open research directions to accelerate LUMENIS convergence now, while preserving current Product Architecture and enabling later LUMENIS-native replacement.

## Integration policy

- Do not install external repositories into LUMENIS Production Runtime.
- Integrate the mechanisms behind them into an isolated R&D layer.
- Prefer wrappers/adapters and reproducible benchmarks over source copying.
- Any temporary third-party code reuse must be pinned, attributed, licensed, isolated, and replaceable.

## Component mapping

### 1. Research Optimizer
Reference: `karpathy/autoresearch`.

Responsibilities:
- accept a bounded optimization target;
- create hypothesis candidates;
- execute isolated experiments;
- enforce one attributable variable per experiment where practical;
- measure against immutable baseline;
- retain only evidence-backed candidates;
- stop on budget exhaustion.

Initial targets during convergence:
- failing/hanging tests;
- slow test groups;
- API/runtime hotspots;
- DB query inefficiency;
- Agent task latency/cost;
- Evidence generation overhead.

### 2. Performance Race
Reference: `karpathy/nanochat` speedrun methodology.

Responsibilities:
- define a fixed acceptance target first;
- optimize wall-clock time to reach the same target;
- reject any candidate that trades away correctness, Evidence, security, or regression coverage.

Initial metrics:
- time-to-green for selected test suites;
- time-to-valid-report;
- time-to-complete controlled Agent task;
- API P50/P95 under fixed dataset;
- data pipeline throughput under fixed correctness checksum.

### 3. Execution Efficiency Lab
Reference: `ScalingIntelligence/KernelBench` benchmark philosophy.

Responsibilities:
- identify execution hotspots;
- compare implementations with deterministic correctness checks;
- measure CPU/RAM/disk/DB/browser/worker cost;
- GPU/kernel work remains `NOT_REQUIRED` until suitable hardware/workload exists.

## Required architecture

```text
Trigger
→ Experiment Contract
→ Budget Guard
→ Baseline Snapshot
→ Isolated Workspace
→ Candidate Change
→ Fixed Benchmark
→ Correctness Gate
→ Resource Measurement
→ Evidence Record
→ Keep / Reject
→ Regression
→ Human Approval
```

## Budget Guard

Every research task must declare:
- max iterations;
- max wall-clock duration;
- max Codex/AI calls where observable;
- max CPU/RAM/disk budget;
- allowed files/modules;
- forbidden effects.

No unbounded autonomous loop.

## Promotion Gate

A candidate may be promoted only if all are true:
1. baseline and candidate are reproducible;
2. correctness/contract results are equal or better;
3. no Evidence/security/permission regression;
4. benchmark gain is measurable and attributable;
5. regression suite passes;
6. diff is reviewable;
7. human approval exists;
8. Production release gates remain unchanged.

## Progressive replacement

Temporary external-inspired adapters must expose a stable LUMENIS-owned contract so implementation can later change without callers changing.

Lifecycle:
`REFERENCE → ADAPTER → LUMENIS-NATIVE PARITY → REPLACE → REMOVE TEMP DEPENDENCY → REGRESSION PROOF`

## First implementation task

During current Production Convergence, implement only the minimum viable SHADOW engine:
- benchmark contract;
- baseline record;
- budget guard;
- experiment result/evidence schema;
- keep/reject decision;
- no automatic Production mutation.

Then run it against one existing convergence problem before widening scope.

## First recommended proving case

Use an existing reproducible engineering bottleneck (for example a hanging/slow test or deterministic runtime hotspot) and prove:
- baseline exists;
- experiment is isolated;
- budget is enforced;
- candidate is objectively compared;
- rejected candidates leave no residue;
- accepted candidate still requires normal review/approval.

## Release protection

This integration must not become a blocker or dependency for the current LUMENIS release. If Shadow Research is unavailable, Production Core and Production Acceptance must continue normally.
