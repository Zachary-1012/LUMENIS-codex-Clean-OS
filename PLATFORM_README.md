> **HISTORICAL / COMPATIBILITY REFERENCE - NOT CURRENT PRODUCT AUTHORITY.** Current execution starts at AGENTS.md; current product identity is LUMENIS, the sole blueprint is 00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md, and workspace context defaults to GLOBAL / ALL. Legacy names below are provenance/compatibility only.

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

Z-Brand-Core owns domain intelligence and production business capability, including brand/market intelligence, data collection and normalization, subject/content classification, sentiment and risk logic, event aggregation, reports, brand knowledge, AI-assisted domain analysis, domain learning, CTH-POMS production capability, and ZBMP controlled enhancement capability.

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

Reject or redesign an integration if it creates unnecessary coupling, dependencies, cross-repository edits, deployment steps, testing burden, runtime assumptions, hidden ownership, or duplicated state.

A shared component must have one clear owner and a stable interface.

## 6. Mandatory pre-change protocol

Before **every material optimization, feature change, refactor, integration, or release**, the engineering agent must:

1. Inspect the current state of **all three repositories**.
2. Read the current platform baselines and relevant source modules.
3. Identify ownership, dependencies, reusable capability, conflicts, and production impact.
4. Check current branch/commit/baseline and available verification evidence.
5. Compare the proposed change against the permanent principles and delivery contract.
6. Run applicable verification before changing code whenever the execution environment permits.
7. Produce a minimal-change plan.

If live execution is unavailable, state that limitation explicitly. Repository inspection is never represented as a runtime test.

## 7. Verification infrastructure

The platform may use the following controlled path:

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

DDC owns the engineering verification contract in `Development-Command-Console/docs/PLATFORM-VERIFICATION-RUNTIME.md`. Z-Brand-Core remains the owner of its domain tests and production validation; verification infrastructure must not become a runtime dependency of CTH-POMS.

GitHub Actions supplements controlled verification; it does not replace the evidence model.

Every release validation should identify repository, SHA, runtime/container, dependencies, test version, timestamp, result, and evidence.

## 8. Permanent delivery standard

A material change is not complete merely because code was written or an AI reports success.

```text
Requirement → Ownership/scope → Implementation → Compatibility → Tests → E2E where applicable → Fixed-SHA verification → Evidence → Risk/permission review → Acceptance → Release → Learning
```

Delivery states are:

`D0 Idea → D1 Planned → D2 Implemented → D3 Tested → D4 Verified → D5 Accepted → D6 Released → D7 Learned`

A lower state must never be reported as a higher state. Failed or incomplete verification remains visible.

## 9. AI dependency reduction

AI is an accelerator, not a single point of failure. When a task becomes deterministic and repeatedly verified, progressively move it from AI-dependent execution to rules, skills, automation, or native platform capability.

`Observe → AI-assisted → AI-led + verification → skill/rule automation → stable automation → native capability`

AI remains available for ambiguity, novel problems, high-value reasoning, and escalation.

## 10. Learning acceleration

```text
Task → Execution → Verification → Evidence → Human/rule evaluation → Learning → Skill/rule/automation → Re-verification
```

Repeated successful patterns become reusable capabilities. Repeated failures become diagnostic knowledge. Learning must be grounded in actual execution/evidence, not model confidence.

Z-Brand domain learning and DDC engineering learning remain separately owned and exchange information only through stable contracts.

## 11. Self-optimization protocol

After each material delivery, the engineering AI evaluates its own **process** against evidence:

- complexity removed/added
- capability reused or duplicated
- repeated failure/success patterns
- unnecessary AI context/quota consumption
- candidate deterministic tests, skills, rules, or automations
- next-cycle process improvements

Only evidence-backed process improvements may be added to the operating method. The AI may optimize its workflow; it may not silently weaken the immutable platform principles.

## 12. Risk and autonomy

Risk and capability maturity are separate dimensions.

- **Low risk + mature capability:** may run automatically.
- **Medium risk:** may escalate for confirmation.
- **High risk:** explicit authorization required.
- **Critical risk:** human gate retained.

Highest authorization never means unlimited or unaudited access.

## 13. Shadow-first

New AI decision capabilities should, where practical, operate in shadow mode against existing rules/human decisions before becoming authoritative. Promotion requires measurable evidence.

## 14. Production protection

Existing production behavior, subject/data calibration, security controls, and customer delivery paths must be preserved. Experimental AI, new adapters, Runtime work, and cross-repository integration must be isolated or feature-gated when necessary.

## 15. External research

GitHub and industry projects are used to learn architecture, testing, security, runtime isolation, agent evaluation, and engineering practice. External code is not copied indiscriminately. License and provenance must be audited before reuse.

## 16. Three-repository target architecture

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

## 17. Mutual verification and feedback loop — IMMUTABLE

The three repositories must **verify and strengthen one another without collapsing their boundaries**.

```text
Z-Brand-Core
  │  domain requirements / production truth
  ↓
DDC
  │  engineering contracts / verification / evidence
  ↓
SICI-Core
  │  mobile interaction / real workflow feedback
  ↓
DDC
  │  execution + test evidence
  ↓
Z-Brand-Core
  │  domain validation / production applicability
  └──────────────→ Learning → all three
```

This is a **mutual feedback contract**, not mutual ownership:

1. **Z-Brand-Core validates business meaning and production applicability.**
2. **DDC validates engineering execution, risk, permissions, tests, evidence, rollback, and delivery state.**
3. **SICI validates mobile usability, interaction flow, device-side constraints, and user-facing execution feedback.**
4. Findings from one repository become inputs to the other repositories only through explicit contracts, Evidence, tests, or reviewed learning records.
5. A repository may challenge another repository's assumptions, but may not silently rewrite another repository's owned internals.
6. Reusable improvements are adapted and re-verified at their destination; successful behavior in one repository is never assumed to be valid everywhere.
7. A failed verification is a platform learning signal and must remain visible until resolved or explicitly accepted.
8. The loop must continuously reduce duplicated work, failure recurrence, AI dependency, and integration complexity while increasing verified capability.

### Permanent principle

> **三方反哺、互相验证、边界不破、能力共享、责任分明。**
>
> **Z-Brand-Core 提供业务/生产真相；DDC 提供工程控制与验证真相；SICI-Core 提供移动交互与真实使用反馈。三方通过 Contract + Evidence + Test + Learning 形成闭环，任何一方都不能成为另外两方的无边界上级。**

This section is immutable. It may only be clarified, strengthened, or expanded. It may not be deleted, weakened, bypassed, or reinterpreted to permit uncontrolled coupling or one-way dependency.

## 18. Implementation roadmap

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

## 19. Five-times-daily engineering inspection

GitHub Actions is the execution layer for the platform's recurring engineering inspection. DDC owns the inspection contract; Z-Brand-Core remains the domain/production owner.

The DDC workflow `.github/workflows/platform-five-inspections.yml` schedules five deterministic inspections per UTC day across all three repositories. Each run checks out the target repository at a recent history window and executes the read-only `tools/platform_inspection.py` evidence collector.

The inspection is intentionally **read-only**: it records repository SHA, working-tree state, structure markers, tracked-file counts, and inspection-tool provenance. It does not silently modify source code, release production code, or declare unexecuted tests successful.

For private repositories, the workflow requires an explicitly configured read-only `ZACHARY_PLATFORM_TOKEN`; it never bypasses GitHub authentication.

The five daily inspections are the engineering heartbeat. Actual optimization remains gated by the permanent pre-change protocol and delivery standard:

```text
Inspection → Three-repository understanding → Research → Candidate → Minimal change → Real verification → Evidence → Acceptance → Push/Release → Learning
```

This design deliberately separates **ChatGPT/AI research and reminder assistance** from **GitHub Actions deterministic engineering inspection**. AI may propose improvements; Actions supplies repeatable repository evidence. Neither may bypass the delivery gates.

## 20. Non-negotiable rule

**The platform can only grow stronger.** New frameworks, models, providers, runtimes, protocols, or product requirements enter only when compatible with this baseline and improve capability without damaging safety, stability, boundaries, verification, rollback, or complexity control.

For Z-Brand-Core specifically: **never sacrifice production stability to accelerate platform experimentation.**
