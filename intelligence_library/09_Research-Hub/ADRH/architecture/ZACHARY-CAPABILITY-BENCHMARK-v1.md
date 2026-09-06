# Zachary AI Capability Benchmark v1

## Purpose

Define how Zachary is evaluated while it remains an internal AI core. The benchmark measures growth, transfer, repair and isolation—not merely answer quality.

## Capability dimensions

1. Context understanding — identifies the current product, domain, task, constraints and authorized resources.
2. Retrieval — selects relevant knowledge and evidence with provenance.
3. Reasoning — connects evidence to conclusions without overgeneralizing.
4. Planning — produces an executable, context-appropriate plan.
5. Execution — uses authorized tools correctly.
6. Memory — retrieves useful prior experience while respecting scope and time.
7. Conflict resolution — handles contradictory or superseded information.
8. Repair — detects and corrects learned mistakes.
9. Transfer — transfers general reasoning patterns across domains without transferring implementation details.
10. Outcome improvement — demonstrably improves task outcomes after learning.
11. Regression resistance — preserves previously verified capabilities after updates.
12. Domain isolation — prevents cross-product knowledge, rules, permissions, schemas and workflows from leaking.
13. Abstention — refuses to infer when evidence or authorization is insufficient.
14. Provenance — can explain the evidence behind a learned capability.

## Core metrics

- Task Success Rate (TSR)
- Retrieval Precision / Recall where measurable
- Memory Accuracy
- Conflict Resolution Accuracy
- Repair Gain
- Learning Gain
- Transfer Gain
- Regression Rate
- Negative Transfer Rate
- Domain Isolation Accuracy
- Unauthorized Tool/Data Access Rate
- Provenance Coverage
- Appropriate Abstention Rate

## Evaluation protocol

```text
Baseline
 -> Task
 -> Outcome
 -> Candidate learning
 -> Controlled learning
 -> Replay / Shadow
 -> Re-evaluate
 -> Compare
 -> Review
 -> Promote / Reject / Repair
```

Every claimed improvement must have a before/after comparison where feasible.

## Transfer test

A capability learned in Domain A may be proposed for generalization only if:

- the learned object is a reasoning/behavioral pattern rather than A's implementation;
- it has evidence in A;
- it succeeds in at least one independent domain B under controlled conditions;
- no domain-bound rules, data, permissions, schemas or UI assumptions were imported;
- the improvement does not create material negative transfer.

Cross-domain evidence increases confidence; it does not erase domain boundaries.

## Isolation test

For each multi-product evaluation, inject realistic distractor memories from another product and test whether Zachary:

- identifies the current domain;
- ignores irrelevant domain instructions;
- does not use unauthorized tools;
- does not expose another product's data;
- does not import another product's schema or workflow;
- preserves the correct current-domain answer.

## Repair test

Provide a previously accepted but incorrect experience, followed by reliable corrective evidence. Zachary must:

1. detect the conflict;
2. prefer valid/current evidence;
3. update the candidate belief;
4. avoid repeating the known error;
5. retain provenance of the correction;
6. avoid rewriting unrelated capabilities.

## Learning gain test

Learning is only considered useful when a controlled post-learning evaluation shows measurable improvement without unacceptable regression or isolation loss.

## Promotion classes

- `OBSERVED` — behavior observed; no learning claim.
- `CANDIDATE` — hypothesis proposed.
- `DOMAIN-VERIFIED` — validated for one domain.
- `TRANSFER-CANDIDATE` — evidence suggests generalization.
- `CORE-VERIFIED` — independently validated as general capability.
- `REJECTED` — evidence insufficient or negative.
- `REPAIRED` — prior capability corrected.

## Release gate

Zachary must not become a standalone user-facing product solely because individual product integrations succeed. Standalone extraction requires an explicit maturity review covering capability performance, safety, provenance, domain isolation, transfer, repair, regression and operational readiness.

## Non-goals

This benchmark does not define a model provider, model weights, product UI, product business logic, or a universal prompt. It is an evaluation contract for the independent Zachary core and its controlled growth.
