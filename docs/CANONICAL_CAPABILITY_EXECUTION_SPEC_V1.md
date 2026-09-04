# Canonical Capability Execution Specification V1

## Purpose

This specification upgrades implementation method without changing the established product definition, product architecture, functional boundaries, user roles, safety boundaries, or canonical business standards.

Core rule:

> Preserve product truth; progressively replace duplicated implementation with verified, reusable canonical capabilities.

## Non-breaking principles

1. Product definition, existing modules, routes, APIs, user roles, business boundaries, naming standards, and safety gates remain authoritative unless an explicit product decision changes them.
2. New implementation is additive/compatible first. No destructive rewrite.
3. Existing behavior must be preserved by oracle/diff testing before promotion.
4. Reuse before creation; merge when equivalent; retain when independently justified; deprecate and delete only after verified replacement.
5. AI is not a source of truth and must not create a competing metric definition.

## Canonical path

External Source -> Collection Runtime -> Raw/Evidence -> Validate -> Normalize -> Canonical Data -> Canonical Function -> Canonical Metric -> Truth Surface/View Model -> UI/Report/Export/AI.

Runtime concerns remain separate: browser/session/cookie/rate-limit/retry/cooldown/heartbeat/recovery/security.

## Canonical Function contract

Every promoted canonical function must define:

- stable ID and name
- inputs and schema
- outputs and schema
- business meaning
- source/evidence dependencies
- version
- deterministic/non-deterministic classification
- error/empty semantics
- performance expectations
- tests and regression coverage
- downstream consumers
- lineage
- deprecation/replacement status

## Anti-explosion controls

- One business fact -> one canonical source.
- One business calculation -> one canonical function.
- One business metric meaning -> one canonical metric definition.
- UI/report/export must not reimplement business calculations.
- AI may read canonical metrics/evidence and reason, explain, compare, predict, or suggest; it may not silently redefine truth.
- No function proliferation by consumer (`*_for_ai`, `*_for_dashboard`, etc.) when the underlying business meaning is the same.
- New capability requires capability-discovery scan before implementation.

## Safe replacement protocol

OLD -> NEW -> dual run -> diff/oracle -> contract tests -> regression -> E2E -> production verification -> promote NEW -> mark OLD LEGACY -> remove OLD only when impact scan is clean and rollback evidence exists.

If old/new differ, do not guess. Classify: old-correct / new-correct / intentional business difference / data-quality issue / merge required.

## Optimal computation rules

1. Read canonical data before recollecting.
2. Reuse canonical functions before recalculating.
3. Reuse canonical metrics before redefining.
4. Prefer incremental computation over full recomputation when semantics permit.
5. Cache stable results where correctness permits.
6. Parallelize independent computations.
7. Use deterministic functions instead of AI when deterministic logic is sufficient.
8. Invoke AI only when interpretation/reasoning adds value.
9. Keep expensive runtime operations outside the pure canonical layer.
10. Measure correctness, latency, throughput, failure rate, and resource cost.

## UI/visualization rule

Canonical Function -> Metric -> View Model/State -> Visualization.

UI owns presentation, interaction, filtering, sorting, animation, and state expression; it does not become a second business calculation engine.

## AI rule

Permission/Policy -> Canonical Data/Metric/Evidence -> AI reasoning -> suggestion/explanation -> human gate where required.

AI must not bypass production permissions, safety gates, canonical metrics, or human approval boundaries.

## Lineage and observability

Every promoted capability should be traceable from output to function, inputs, source/evidence, execution run, version, tests, and consumers. Runtime observability should connect logs, metrics, traces, failures, and recovery events.

## Migration policy

Prefer WRAP -> VERIFY -> PROMOTE -> DEPRECATE -> DELETE. Do not perform broad rewrites merely to satisfy the architecture. A legacy implementation that is mathematically/business equivalent may remain KEEP when replacement adds no safety or maintainability value; document the reason.

## Acceptance gates

A migration is complete only when:

- canonical source/function/metric is identified
- duplicate implementations are classified
- old/new results are equivalent or an intentional difference is documented
- automated regression passes
- relevant production route/API verification passes
- no new hard-coded business truth is introduced
- lineage/ownership/version are recorded
- rollback path exists
- no product behavior or established business standard is changed unintentionally

## Scope for the current product

Apply progressively across data collection, KOS, campaign/event/risk/reporting, tables, dynamic visualization, exports, and AI surfaces. Existing product architecture remains the boundary; this specification governs implementation convergence, not product redesign.
