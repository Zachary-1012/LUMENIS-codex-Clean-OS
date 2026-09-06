# Zachary AI — Internal Learning Contract v1

## Purpose

This contract defines how Zachary may learn from products while remaining a separate general-purpose AI core. It prevents domain knowledge, product architecture, permissions, workflows, and implementation details from leaking across products or silently becoming global capability.

## 1. Learning is scoped

Every learning event must have:

- product_id
- domain_id
- task/session_id
- source/provenance
- evidence level
- capability class
- temporal validity
- authorization scope
- outcome/evaluation state

No unscoped learning event may enter durable Zachary memory.

## 2. Four memory partitions

### GLOBAL-CORE
Verified, domain-independent capabilities and knowledge.

### DOMAIN
Product/domain knowledge, experience, workflows, rules, terminology, and local outcomes.

### SESSION
Current task state and temporary working context.

### EVIDENCE
Provenance, observations, evaluations, benchmark results, contradictions, promotion decisions, and rollback history.

Default rule: DOMAIN and SESSION data cannot silently write to GLOBAL-CORE.

## 3. Three capability classes

### CORE-GENERAL
A reusable reasoning or orchestration capability demonstrated across sufficiently independent contexts.

### DOMAIN-BOUND
A capability whose validity depends on a specific product, business, platform, dataset, workflow, policy, or domain.

### ADAPTER
A controlled interface allowing CORE-GENERAL reasoning to operate on DOMAIN-BOUND capabilities without importing the domain implementation into the core.

## 4. Promotion protocol

```text
Product experience
 -> observation
 -> candidate learning
 -> classify
 -> domain validation
 -> cross-domain validation (if generalization is proposed)
 -> benchmark
 -> shadow
 -> evidence review
 -> promote / retain-domain / reject
```

One successful outcome never proves a general capability.

## 5. Context firewall

Before retrieval, reasoning, tool use, or memory write, resolve:

```text
Current product
Current domain
Current task
Authorized tools
Authorized data
Applicable rules
Memory scope
Capability scope
Temporal validity
Provenance
```

If scope is ambiguous, Zachary must abstain from cross-domain reuse and request/obtain the required context.

## 6. Anti-contamination rules

1. Product architecture is never learned as a core capability.
2. Product function names are never assumed to be universal capabilities.
3. Product UI, routes, schemas, database structures, permissions, deployment details, and business rules remain domain-bound unless explicitly generalized as an abstract pattern and independently validated.
4. Domain permissions never transfer automatically.
5. Domain memory never becomes global memory by retrieval frequency or repeated use.
6. A product-specific failure does not automatically change global behavior.
7. A product-specific success does not automatically change global behavior.
8. Similar terminology across products does not establish semantic equivalence.
9. Shared concepts must be normalized through an adapter/contract layer.
10. Every promoted capability retains provenance and affected-domain history.

## 7. Conflict handling

When memories or rules conflict:

```text
Detect conflict
 -> compare domain scope
 -> compare temporal validity
 -> compare authority/provenance
 -> determine whether conflict is local or general
 -> preserve both when context differs
 -> supersede only when evidence supports it
```

The system must not collapse contextual differences into one false universal rule.

## 8. Transfer test

A capability may be proposed for CORE-GENERAL only when:

- it can be expressed independently of product implementation;
- it has evidence from multiple sufficiently independent domains/tasks;
- it improves performance over a suitable baseline;
- it does not create unacceptable negative transfer;
- it survives contradiction, temporal-change, and isolation tests;
- its provenance and limitations are recorded.

## 9. Learning quality metrics

Track separately:

- Learning Gain
- Transfer Gain
- Repair Gain
- Regression Rate
- Negative Transfer Rate
- Memory Retrieval Precision
- Conflict Resolution Accuracy
- Scope Isolation Accuracy
- Provenance Coverage
- Abstention/Uncertainty Quality

Do not use a single aggregate score as the sole promotion criterion.

## 10. Write governance

Durable memory writes are higher risk than ordinary responses because a bad write can repeatedly influence future decisions. Therefore:

- unverified observations should remain provisional;
- uncertain or conflicting memories should be quarantinable;
- provenance must survive summarization;
- stale information must retain temporal validity or expiration metadata;
- deletion/revocation must be testable;
- user/product-specific claims must not be generalized without evidence.

## 11. Evaluation protocol

For important learning changes, use controlled comparisons:

```text
Baseline / no learned change
vs.
Candidate / learned change
```

Measure both improvement and regressions. Where possible, replay the same tasks under identical conditions and include cross-domain isolation tests.

## 12. Product independence

Products consume Zachary through explicit interfaces. Products may expose domain tools and data to Zachary, but they must not modify Zachary Core directly.

Zachary may improve a product through verified capability reuse, but product code must remain responsible for its own architecture, state, permissions, and business logic.

## 13. Standalone readiness

This contract remains internal until the owner explicitly authorizes Zachary extraction. Before extraction, the system must demonstrate stable general capabilities, domain isolation, reproducible benchmarks, memory governance, safe tool use, correction/repair, cross-domain transfer, and regression resistance.

The goal is not to make Zachary resemble any single product. The goal is to let every product make Zachary more capable while keeping Zachary structurally independent from all of them.
