# Podcast Module — Shared System Rules

This module is a first-class ZBC module and MUST inherit all applicable system engineering rules. It does not create a parallel engineering standard.

## Non-negotiable rules

1. Reuse before rebuild: inspect existing ZBC/Zachary OS AI capabilities and mature OSS before implementing new infrastructure.
2. Adapt before fork: use adapters/contracts when an existing capability does not fit the Podcast domain.
3. No silent execution: every job has a runtime ID, heartbeat, result, evidence, return status and failure state.
4. No silent failure or completion: `no_return` is an explicit runtime state.
5. Contract-first: domain, runtime and integration contracts are versioned and tested before cross-module wiring.
6. Evidence-first: external facts require source/evidence metadata; AI suggestions cannot silently become facts.
7. AI boundary: models assist extraction, classification, ranking and generation; deterministic rules and human verification govern promotion of claims/rules.
8. Module isolation: Podcast business logic stays in the Podcast domain. Shared capabilities are consumed through stable interfaces.
9. UI consistency: all Podcast views inherit the ZBC design system and interaction rules. Business-specific tables define their own columns without inventing a separate visual language.
10. Progressive disclosure: first surface shows the primary decision; secondary detail opens through drill-down/drawers.
11. State completeness: loading, empty, partial, error, retry, recovering and success states are designed, not incidental.
12. Observability: production-relevant actions expose runtime/evidence context for diagnosis and audit.
13. No fake data: benchmark cases may contain placeholders, but unverified values must remain explicitly marked and must never be presented as observed facts.
14. Regression safety: changes must preserve existing module contracts and must be evaluated before promotion.
15. Bidirectional learning: validated Podcast outcomes may become learning assets, but only through evidence-backed promotion rules.

## Reuse boundary

- Z-Brand-Core: Podcast domain, research, case library, topic/episode/person intelligence, content yield and product UI.
- Zachary OS AI: shared AI/model/runtime/evaluation/orchestration capabilities.
- Cross-repo communication: versioned contract + adapter + evidence/runtime identifiers.

## Required lifecycle

Research -> Ingest -> Normalize -> Analyze -> Verify -> Produce -> Distribute -> Observe -> Evaluate -> Learn.

Every stage must expose runtime state and preserve traceability to its inputs and outputs.
