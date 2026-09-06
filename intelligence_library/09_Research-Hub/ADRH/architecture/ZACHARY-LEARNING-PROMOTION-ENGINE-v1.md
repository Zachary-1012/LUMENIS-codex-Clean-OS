# Zachary AI Learning Promotion Engine v1

## Purpose

Control how observed product experience can, or cannot, become a reusable Zachary capability. Promotion is a governed decision, never an automatic side effect of success.

## Decision pipeline

```text
Experience
 -> Scope Check
 -> Evidence Check
 -> Pattern Extraction
 -> Counterexample Check
 -> Candidate
 -> Domain Benchmark
 -> Shadow Replay
 -> Transfer Test (if generalization is proposed)
 -> Risk / Isolation Check
 -> Review
 -> Promote / Keep Domain / Reject / Repair
```

## Promotion classes

| Status | Meaning |
|---|---|
| OBSERVED | Seen in a real task; no learning claim. |
| CANDIDATE | A potentially reusable pattern has been proposed. |
| DOMAIN-VERIFIED | Reproducibly useful within its originating domain. |
| TRANSFER-CANDIDATE | Evidence suggests the pattern may generalize. |
| CORE-VERIFIED | Independently validated as a general capability. |
| REJECTED | Evidence, safety, reliability or isolation is insufficient. |
| REPAIRED | A previous capability was corrected and revalidated. |
| RETIRED | No longer valid or intentionally withdrawn. |

## Required promotion evidence

A candidate must have, where applicable:

- clear provenance;
- explicit domain scope;
- reproducible task definition;
- measurable outcome;
- baseline comparison;
- post-learning comparison;
- counterexample analysis;
- failure analysis;
- privacy/authorization review;
- regression check;
- isolation check.

A single successful interaction is never enough for `CORE-VERIFIED`.

## Generalization gate

To promote a domain-derived pattern to `CORE-VERIFIED`, the engine must establish that:

1. the candidate is abstracted from domain implementation details;
2. it has evidence in its originating domain;
3. it is tested in an independent domain;
4. it improves or preserves outcomes in the independent domain;
5. negative transfer remains within the accepted threshold;
6. it does not import domain rules, data, permissions, schemas, UI or workflows;
7. the capability remains explainable through provenance.

If any condition fails, the candidate remains domain-bound or is rejected.

## Promotion scoring

Do not use one opaque score as the sole gate. Evaluate separate dimensions:

```text
Evidence Quality
Outcome Gain
Reproducibility
Transfer Evidence
Isolation Safety
Regression Risk
Provenance Completeness
Operational Risk
```

The final decision is a governed policy decision over these dimensions.

## Learning gain

```text
Learning Gain = Post-Learning Performance - Baseline Performance
```

Where appropriate, report confidence intervals or repeated-trial variance rather than a single run.

## Negative transfer

A capability that improves Domain A but degrades Domain B must not be promoted as global. Record the degradation and investigate whether the candidate should remain domain-bound or be split into a conditional capability.

## Repair path

```text
Known capability
 -> contradictory reliable evidence
 -> identify affected scope
 -> quarantine affected behavior if necessary
 -> repair candidate
 -> replay benchmark
 -> transfer/isolation regression test
 -> promote repaired version or retire
```

Repairs must preserve the original provenance and change history.

## Rollback

Every promoted capability must be versioned and reversible. A regression in a dependent product must not require rewriting unrelated capabilities. Roll back the affected capability version, preserve evidence, and open a repair candidate.

## Product boundary

The engine may receive outcome evidence from products, but it must not modify product architecture or business logic. Product-specific improvements remain in the product unless separately promoted through this engine.

## Standalone maturity

The engine also supplies evidence for the future Zachary standalone-release decision. Standalone extraction requires a portfolio of verified capabilities across multiple independent domains, with acceptable safety, isolation, regression, transfer and operational performance.
