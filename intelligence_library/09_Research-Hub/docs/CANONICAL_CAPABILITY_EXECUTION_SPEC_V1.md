# Canonical Capability Execution Specification V1

## Purpose

This specification upgrades implementation method without changing the established product definition, product architecture, functional boundaries, user roles, safety boundaries, or canonical business standards.

Core rule:

> Preserve product truth; progressively replace duplicated implementation with verified, reusable canonical capabilities.

## Dual-repository rule

Zachary-OS-AI is the research/evaluation/intelligence side. It may research, evaluate, compare, and propose improvements, but it must not establish a competing production metric truth. Production truth remains in Z-Brand-Core.

## Canonical path

Research/Evaluation -> Contract -> Production Capability -> Canonical Data -> Canonical Function -> Canonical Metric -> Truth Surface -> UI/Report/Export/AI.

For production data flows: External Source -> Collection Runtime -> Raw/Evidence -> Validate -> Normalize -> Canonical Data.

## Non-breaking principles

1. Do not redesign the established product architecture or product boundaries.
2. Reuse existing capabilities before creating new ones.
3. Replace only after dual-run/diff/regression/E2E/production verification.
4. AI is not a source of truth and must not create competing metric definitions.
5. Preserve rollback evidence and document KEEP/MERGE/REPLACE/LEGACY/DELETE decisions.

## Canonical Function contract

Every promoted capability must identify stable ID/name, input/output schemas, business meaning, dependencies, version, deterministic classification, error/empty semantics, tests, performance expectations, lineage, consumers, and lifecycle status.

## Anti-explosion controls

- One business fact -> one canonical source.
- One business calculation -> one canonical function.
- One business metric meaning -> one canonical metric.
- Consumer-specific duplicate functions are prohibited when semantics are identical.
- AI, UI, reports, and exports consume canonical truth rather than reimplementing it.
- New work begins with a capability-discovery/reference scan.

## Safe replacement protocol

OLD -> NEW -> dual run -> oracle/diff -> contract tests -> regression -> E2E -> production verification -> promote NEW -> LEGACY OLD -> delete only after clean impact/rollback checks.

## Optimal computation

Prefer canonical reads, reuse, incremental computation, caching where safe, parallel independent work, deterministic calculation over AI when sufficient, and AI only where reasoning adds value. Keep collection/runtime operations separate from pure canonical computation.

## AI governance

Permission/Policy -> Canonical Data/Metric/Evidence -> AI reasoning -> suggestion/explanation -> human approval where required. No silent metric redefinition, permission bypass, or production write outside established gates.

## Lineage/observability

Track capability version, source/evidence, execution run, outputs, downstream consumers, tests, errors, metrics, traces, and recovery events sufficiently to reconstruct why a result exists.

## Research-to-production gate

Research findings may enter production only through an explicit contract and validation path. No direct research-side metric becomes production truth by convention. If a research implementation is better, prove equivalence/benefit, migrate safely, and register the new canonical capability in production.

## Completion gate

A migration is complete only when duplicates are classified, canonical truth is explicit, old/new behavior is verified or intentional differences documented, regression/E2E/production checks pass, lineage/version/rollback are recorded, and no unintended product behavior changes.
