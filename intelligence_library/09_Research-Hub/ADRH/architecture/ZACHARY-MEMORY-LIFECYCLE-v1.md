# Zachary AI Memory Lifecycle v1

## Principle

Zachary does not treat every observed item as permanent memory. Memory is scoped, evidence-bearing, time-aware and lifecycle-managed.

## Memory classes

- `GLOBAL_CORE`: verified general knowledge/capabilities.
- `DOMAIN`: product/domain knowledge and experience.
- `SESSION`: current task state.
- `EVIDENCE`: provenance, outcomes, evaluations and validation history.
- `QUARANTINE`: uncertain, conflicting, stale or unverified material awaiting review.

## Lifecycle

```text
Ingest
 -> classify
 -> scope
 -> validate provenance
 -> store
 -> retrieve
 -> evaluate in context
 -> reinforce / correct / quarantine / retire
```

## Write gate

A new item must pass:

1. source/provenance check;
2. domain scope check;
3. privacy/authorization check;
4. temporal validity check;
5. duplication/conflict check;
6. evidence quality assessment.

Unverified information may be retained only as explicitly marked `QUARANTINE` or research material and must not silently become trusted core memory.

## Retrieval gate

Before retrieval is used for reasoning, Zachary must evaluate:

- current domain match;
- task relevance;
- temporal validity;
- confidence/evidence level;
- conflict with newer evidence;
- authorization scope.

## Reinforcement

Repeated, independently supported success may increase confidence, but frequency alone cannot promote a domain-bound fact to global capability.

## Correction

```text
new reliable evidence
 -> conflict detection
 -> identify affected memories/capabilities
 -> update applicability/confidence
 -> preserve prior provenance
 -> re-run affected benchmarks
```

## Retirement

Memory may be retired when it is obsolete, invalidated, superseded, unsafe, or repeatedly contradicted. Retirement preserves audit history and must not silently erase evidence.

## Forgetting / compaction

Low-value, stale, redundant or expired session material may be compacted or forgotten when it no longer contributes to future tasks. Core verified capabilities require stronger retention and rollback controls.

## Cross-domain protection

Domain memory never becomes global memory by retrieval frequency alone. Promotion requires explicit generalization evidence. Cross-domain leakage is treated as a regression even if the generated answer appears useful.

## Monitoring

Track:

- retrieval usefulness;
- stale-memory rate;
- contradiction rate;
- correction success;
- memory-induced regression;
- cross-domain leakage;
- unauthorized retrieval/access;
- provenance coverage.
