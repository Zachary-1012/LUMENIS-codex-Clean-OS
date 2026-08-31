# Zachary AI Platform — Z-Brand-Core Integration Baseline

> **IMMUTABLE PLATFORM BASELINE**
>
> This document is additive: principles may be clarified, strengthened, and expanded, but never deleted, weakened, bypassed, or reinterpreted to reduce their force.

## 1. Platform objective

Zachary AI is one platform implemented through three deliberately separated repositories:

- **Z-Brand-Core** — domain/business intelligence.
- **Development-Command-Console (DDC)** — engineering control plane.
- **SICI-Core** — mobile-first creation surface.

The purpose of integration is to reduce duplicated development, engineering difficulty, operational risk, and dependence on any single AI provider. Integration is successful only when it makes the whole system simpler to build, test, operate, and evolve.

## 2. Permanent priority

1. Eternal platform principles
2. Production safety
3. System stability
4. Clear repository boundaries
5. Complexity reduction
6. Reuse of proven capability
7. Adaptation and enhancement
8. New capability development
9. Industry/GitHub learning
10. Performance, UX, and expansion

Lower priorities may never override higher priorities.

## 3. Z-Brand-Core responsibility

Z-Brand-Core owns domain intelligence and production business capability, including:

- brand / market intelligence
- data collection and normalization
- subject/content classification
- sentiment and risk logic
- event aggregation and relationships
- reports and decision outputs
- brand knowledge
- AI-assisted domain analysis
- domain learning and evaluation
- CTH-POMS production capability
- ZBMP controlled enhancement capability

**CTH-POMS remains the production priority.** ZBMP remains an enhancement layer inside Core and must not become a second independently maintained Core.

DDC remains an independent engineering control plane and is not a production runtime dependency of CTH-POMS.

## 4. What integration means

Unify stable contracts, not repository internals.

Shared platform contracts may include:

`Task` · `Risk` · `Permission` · `Execution` · `Evidence` · `Test` · `Rollback` · `Session` · `Learning` · `Delivery`

Existing capability must be reused through:

**understand → abstract → adapt → test → enhance**

Copy/paste duplication is not considered reuse.

## 5. Complexity guard

Reject or redesign an integration if it creates unnecessary:

- coupling
- dependencies
- cross-repository edits
- deployment steps
- testing burden
- runtime assumptions
- hidden ownership
- duplicated state

A shared component must have one clear owner and a stable interface.

## 6. Verification infrastructure

The platform may use the following controlled verification path:

```text
GitHub
  ↓
Fixed commit SHA
  ↓
Dev Container / isolated runtime
  ↓
Python + SQLite + required PDF/runtime dependencies
  ↓
Unit + integration + E2E tests
  ↓
Automatic failure localization
  ↓
Evidence
  ↓
GitHub Actions
  ↓
Release decision
```

GitHub Actions supplements controlled verification; it does not replace the evidence model.

Every release validation should identify repository, SHA, runtime/container, dependencies, test version, timestamp, result, and evidence.

## 7. Permanent delivery standard

A material change is not considered complete merely because code was written or an AI reports success.

```text
Requirement
 ↓
Ownership / scope
 ↓
Implementation
 ↓
Compatibility check
 ↓
Tests
 ↓
E2E where applicable
 ↓
Fixed-SHA verification
 ↓
Evidence
 ↓
Risk / permission review
 ↓
Acceptance
 ↓
Release
 ↓
Learning
```

Delivery states are:

`D0 Idea → D1 Planned → D2 Implemented → D3 Tested → D4 Verified → D5 Accepted → D6 Released → D7 Learned`

The system must never represent a lower state as a higher state. Failed or incomplete verification remains explicitly visible.

## 8. AI dependency reduction

AI is an accelerator, not a single point of failure.

When a task becomes deterministic and repeatedly verified, progressively move it from AI-dependent execution to rules, skills, automation, or native platform capability.

This is **capability maturation**, not weakening AI:

`Observe → AI-assisted → AI-led + verification → skill/rule automation → stable automation → native capability`

AI remains available for ambiguity, novel problems, high-value reasoning, and escalation.

## 9. Learning acceleration

The permanent learning loop is:

```text
Task
 ↓
Execution
 ↓
Verification
 ↓
Evidence
 ↓
Human/rule evaluation
 ↓
Learning
 ↓
Skill / rule / automation
 ↓
Re-verification
```

Repeated successful patterns become reusable capabilities. Repeated failures become diagnostic knowledge. Learning must be grounded in actual execution/evidence, not self-reported model confidence.

Z-Brand domain learning and DDC engineering learning remain separately owned and can exchange information only through stable contracts.

## 10. Risk and autonomy

Risk and capability maturity are separate dimensions.

- **Low risk + mature capability:** may run automatically.
- **Medium risk:** automatic handling may escalate for confirmation.
- **High risk:** explicit authorization required.
- **Critical risk:** human gate retained.

Highest authorization never means unlimited or unaudited access.

## 11. Shadow-first

New AI decision capabilities should, where practical, operate in shadow mode against existing rules/human decisions before becoming authoritative. Promotion requires measurable evidence.

## 12. Production protection

Existing production behavior, subject/data calibration, security controls, and customer delivery paths must be preserved. Experimental AI, new adapters, Runtime work, and cross-repository integration must be isolated or feature-gated when necessary.

## 13. External research

GitHub and industry projects are used to learn architecture, testing, security, runtime isolation, agent evaluation, and engineering practice. External code is not copied indiscriminately. License and provenance must be audited before reuse.

## 14. Three-repository target architecture

```text
                    Zachary AI
                        │
          ┌─────────────┴─────────────┐
          ↓                           ↓
     Z-Brand-Core                    DDC
   Domain Intelligence        Engineering Control
          │                           │
          └─────────────┬─────────────┘
                        ↓
                    SICI-Core
                 Mobile Surface
                        ↓
                 Permission Gate
                        ↓
                Agent Runtime
                        ↓
              Verification Layer
                        ↓
             Evidence / Learning
                        ↓
                   Zachary AI
```

## 15. Implementation roadmap

### P0 — Baseline
- preserve existing production behavior
- map every major module in all three repositories
- identify duplicate capabilities
- establish ownership and contracts

### P1 — Shared contracts
- Task
- Risk
- Permission
- Execution
- Evidence
- Test
- Rollback
- Session
- Learning
- Delivery

### P2 — Mobile-first SICI
- keep SICI lightweight
- expose platform capabilities through adapters
- avoid putting server/runtime responsibilities into the browser UI

### P3 — DDC controlled Runtime bridge
- task contract
- policy/risk evaluation
- permission gate
- isolated execution
- evidence collection

### P4 — Verification infrastructure
- fixed SHA
- reproducible Dev Container/runtime
- unit/integration/E2E
- automatic failure localization
- GitHub Actions
- release gate

### P5 — Learning acceleration
- collect execution/evidence records
- cluster repeated failures/successes
- promote verified patterns to skills/rules
- measure AI dependency reduction
- keep novel/high-risk reasoning with AI/human review

### P6 — Progressive autonomy
- combine Risk × Capability Maturity
- automate only after repeated verification
- retain human gates for high/critical risk

## 16. Non-negotiable rule

**The platform can only grow stronger.** New frameworks, models, providers, runtimes, protocols, or product requirements enter only when they are compatible with this baseline and improve capability without damaging safety, stability, boundaries, verification, rollback, or complexity control.

For Z-Brand-Core specifically: **never sacrifice production stability to accelerate platform experimentation.**
