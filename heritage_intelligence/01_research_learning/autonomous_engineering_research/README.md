# LUMENIS Autonomous Engineering Research Seed

Status: `RESEARCH_SEED / SHADOW_ONLY / NOT_PRODUCTION / NOT_IMPLEMENTED`

Purpose: preserve and operationalize external research patterns that can improve LUMENIS development speed, quality, and runtime efficiency without making external repositories a Production Runtime dependency.

## External research references

1. `karpathy/autoresearch`
   - Focus: autonomous research loop; agent changes one idea, runs an experiment, measures, keeps/rejects, repeats.
   - Intended LUMENIS use: Research Optimizer / isolated experiment loop.

2. `karpathy/nanochat`
   - Focus: Time-to-GPT-2 speedrun / fixed capability target under wall-clock optimization.
   - Intended LUMENIS use: Performance Race / fixed acceptance target, minimize time-to-pass while preserving quality.

3. `ScalingIntelligence/KernelBench`
   - Focus: benchmark + toolkit for execution/kernel efficiency.
   - Intended LUMENIS use: Execution Efficiency Lab; first CPU/DB/runtime hotspots, GPU only when relevant hardware exists.

## LUMENIS adaptation target

```text
Current Production Truth
→ Trigger
→ Fixed Budget
→ Hypothesis
→ Isolated Workspace / Branch
→ Single-variable Experiment
→ Benchmark
→ Quality / Speed / Resource Efficiency
→ Evidence
→ Promote Candidate / Reject
→ Regression
→ Human Approval
→ Production Promotion
```

## Hard boundaries

- External source reference is not a Production dependency.
- Research Seed is not an implemented capability.
- Do not copy third-party source into Production Core by default.
- Any source-level reuse requires version-pinned Source Trace, License Gate, dependency/license audit, security review, tests, Evidence, and explicit Production Promotion.
- Do not weaken Production Truth, Evidence, schema contracts, security, permissions, release gates, or regression requirements to win a benchmark.
- No autonomous merge to `main`.
- No autonomous production write/deploy/database migration.
- During current release convergence, use SHADOW mode only.

## Initial LUMENIS benchmark axes

- Quality: correctness, contract fidelity, Evidence completeness, Agent task success, regression safety.
- Speed: test duration, build duration, data processing latency, API latency, research/report task completion time.
- Resource Efficiency: CPU, RAM, disk I/O, DB query cost, browser/worker overhead.

## Current rollout

Phase 0 — Research seed: ACTIVE by this document only.
Phase 1 — Shadow integration: audit/benchmark/propose/isolated experiment; no Production mutation.
Phase 2 — Controlled candidate promotion: only after regression + human approval.
Phase 3 — Progressive replacement: replace external-inspired mechanisms with LUMENIS-native implementations when they reach or exceed benchmark parity.

Principle: `Use now for acceleration; progressively replace; never let research infrastructure become Production Truth.`
