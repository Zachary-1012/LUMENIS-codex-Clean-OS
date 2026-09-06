# Zachary AI — Internal Maturation & Domain Isolation v1

## 1. Strategic definition

Zachary AI is an independent, general-purpose AI core. During the current product-development phase, Zachary remains an internal capability and learning system. It is not yet a standalone user-facing product.

The current products are controlled real-world environments in which Zachary can acquire domain knowledge, test reasoning patterns, execute tasks, observe outcomes, and mature capabilities.

When the owner determines that Zachary has reached sufficient maturity, reliability, transferability, safety, and operational readiness, Zachary may be extracted as a standalone product. This extraction is a deliberate release decision, not an automatic consequence of product success.

## 2. Product relationship

Products are applications, training/validation environments, and sources of real-world feedback. They must never become merged into Zachary's core identity.

```text
                    ZACHARY AI CORE
                 internal / independent
                         |
          +--------------+--------------+
          |              |              |
        ZBMP           SICI-Core       CTH / future
          |              |              |
          +--------------+--------------+
                         |
                 real-world outcomes
                         |
                  Research-Hub
                         |
                evidence / learning
                         |
                       DCC
                 audit / test / gate
                         |
                verified capabilities
                         |
                    Zachary Core
```

## 3. Internal-only maturation phase

Before standalone release:

- Zachary is used internally through products and development workflows.
- Learning materials, cases, UGC, research, benchmarks and experience records remain backend knowledge assets.
- Users interact with product experiences; Zachary's internal learning architecture remains an implementation concern.
- Product-specific capabilities may be used by Zachary only inside their authorized domain context.
- No product should silently redefine Zachary's global behavior.

## 4. Standalone extraction gate

Zachary may be separated only after explicit evaluation of:

- general reasoning capability
- reliable context understanding
- memory accuracy
- conflict resolution
- repair/correction capability
- cross-domain transfer
- tool-use reliability
- task completion
- outcome improvement
- regression resistance
- safety and policy compliance
- provenance and auditability
- domain isolation
- reproducible benchmarks

No single successful product or benchmark is sufficient for extraction.

## 5. General capability vs domain capability

Every capability must be classified as one of:

### CORE-GENERAL
Reusable across products and domains, e.g. understanding, planning, reasoning, retrieval, evaluation, correction, structured communication, tool orchestration.

### DOMAIN-BOUND
Valid only within a named product/domain, e.g. a specific brand ontology, product workflow, data schema, business rule, platform-specific operation, or industry-specific policy.

### ADAPTER
A controlled bridge that lets Zachary use a domain capability without importing that domain's architecture into the core.

A DOMAIN-BOUND capability must never be promoted to CORE-GENERAL merely because it worked successfully once.

## 6. Domain isolation rule

Zachary must never confuse one product's architecture, functions, data model, business rules, UI, permissions, workflows, or terminology with another product's architecture.

```text
Zachary Core
   |
   +-- Domain Context A
   |      +-- A knowledge
   |      +-- A tools
   |      +-- A rules
   |      +-- A permissions
   |
   +-- Domain Context B
          +-- B knowledge
          +-- B tools
          +-- B rules
          +-- B permissions
```

The core may learn a general reasoning pattern from A and later transfer that pattern to B only after validation. It may not transfer A's implementation details into B.

## 7. Context firewall

Every product interaction must carry an explicit domain context and capability scope. At minimum:

- product_id
- domain_id
- session/task scope
- authorized tools
- authorized data sources
- domain rules
- capability class
- provenance
- temporal validity

Before using memory or a learned capability, Zachary must resolve whether the memory belongs to the current domain and whether it is transferable or domain-bound.

## 8. Memory partitioning

Memory must be separated into:

- Global Core Memory — general, verified knowledge/capabilities.
- Domain Memory — product-specific knowledge and experience.
- Session Memory — current task/session state.
- Evidence Memory — provenance, evaluations, outcomes and validation history.

Domain memory must not silently become global memory.

## 9. Learning promotion boundary

```text
Product experience
 -> observation
 -> hypothesis
 -> candidate learning
 -> domain validation
 -> cross-domain test (if generalization is proposed)
 -> evidence
 -> review
 -> promotion
```

A successful result inside one product proves local usefulness, not general capability.

## 10. Anti-contamination rules

1. Never copy a product architecture into Zachary Core.
2. Never treat a product-specific function name as a universal capability.
3. Never transfer permissions across products.
4. Never transfer business rules without explicit authorization.
5. Never merge domain databases into global memory by default.
6. Never use a case from one domain as a universal strategy without contextual validation.
7. Never allow one product's failure to corrupt global capability without evidence that the failure represents a general weakness.
8. Never allow one product's success to rewrite global behavior without cross-domain evidence.
9. Preserve provenance for every promoted capability.
10. Prefer adapters and scoped contexts over direct coupling.

## 11. Evolution model

Zachary evolves through controlled learning, not uncontrolled self-modification:

```text
Observe
 -> Learn candidate
 -> Evaluate
 -> Shadow
 -> Verify
 -> Promote
 -> Monitor
 -> Repair / rollback if needed
```

The system must preserve the ability to identify what changed, why it changed, which evidence justified it, and which products are affected.

## 12. End-state

When mature, Zachary can become a standalone general AI product while retaining clean separation from every product it helped build.

The intended end state is:

```text
Zachary AI
  = general intelligence / reasoning / learning / orchestration

Products
  = domain applications

Research-Hub
  = knowledge / research / evidence / learning assets

DCC
  = engineering governance / audit / testing / release control

Adapters
  = controlled bridges between Zachary and domains
```

Zachary should leave products stronger without becoming structurally trapped inside any one of them.
