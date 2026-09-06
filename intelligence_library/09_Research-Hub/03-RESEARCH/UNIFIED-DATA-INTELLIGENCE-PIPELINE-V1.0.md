# Unified Data Intelligence Pipeline V1.0 — Research & Implementation Contract Basis

Status: ACTIVE RESEARCH/IMPLEMENTATION SPECIFICATION · SYNCHRONIZED WITH PRODUCTION PLAN

## Objective

Research and formalize a reusable product-wide data architecture:

External Data → Ingestion → Raw/Evidence → Parse → Validate → Normalize → Canonical Data → Function → Metric → Canonical Table → View Model → Visualization → UI/Report/Export/AI.

The objective is not to rewrite the production system. It is to improve reuse, correctness, traceability, dynamic visualization, data quality and governed AI access while preserving existing production truth.

## Research Principles

Learn from established/open approaches including OpenLineage (lineage/provenance), OpenTelemetry (semantic conventions and observability), dbt/MetricFlow (metric/semantic modeling), Great Expectations (executable data quality), Vega-Lite (declarative visualization) and Apache ECharts (interactive dataset/renderer separation). Do not copy architecture or introduce dependencies without license, security, compatibility, performance and fitness review.

## Twin-Repository Boundary

Research produces Evidence, Knowledge, Contract and Implementation Specification. Production remains the authoritative Production Truth. No research result directly changes production truth.

Required gate:

Research → Evidence → Contract → Implementation Specification → Production Implementation → Test → Evidence → Audit → Release.

## Non-Destructive Evolution

Before recommending replacement or deletion, perform:

Inventory → Reference Scan → Dependency Scan → Runtime/Behavior Baseline → Classification → Migration/Adaptation Plan → Test → Evidence → Audit.

Every legacy asset is classified KEEP / MERGE / MIGRATE / LEGACY / ARCHIVE / DELETE. DELETE requires replacement coverage and verified absence of active dependencies. When an old capability is still correct, prefer reuse/adaptation. When the new approach is materially better, migrate behind a reversible gate and preserve rollback until acceptance.

## Canonical Data Truth

Raw/Evidence is immutable. Canonical data is validated and normalized. Business calculations are implemented once as versioned Functions. Metrics have stable semantic definitions. Canonical Tables are the numerical Truth Surface. View Models, charts, UI, reports, exports and AI consume canonical outputs and must not independently recalculate business metrics.

## Function Contract

Each Function records ID, name, version, purpose, inputs, outputs, logic/formula, dependencies, dimensions, time window, unit, error policy, quality requirements, tests, evidence and status.

## Metric/Semantic Contract

Each Metric records ID, definition, Function, Dataset, dimensions, unit, time window, filters, version, owner, evidence, tests and status. Identical metric IDs represent identical business semantics.

## Visualization Contract

Visualization is a presentation/interaction layer. It consumes canonical datasets/metrics via a declarative or structured specification. Renderer code must not hide business calculations. Dynamic interaction changes query/view state rather than duplicating calculation logic.

## Data Quality Contract

At minimum validate schema, types, required fields, nullability, range, uniqueness, referential integrity, freshness, completeness and business rules. Explicitly distinguish verified zero from NULL/UNKNOWN, NOT_AVAILABLE, STALE and ERROR.

## Lineage Contract

Every critical result must be traceable through Metric → Function → Dataset/Table → Canonical/Parsed Data → Raw/Evidence → Source/Run. Version changes must support dependency and impact analysis.

## AI/Agent Contract

AI may query and reason over governed metrics and evidence, but cannot bypass permissions, quality gates, contracts or release gates to modify production truth. Important AI outputs remain traceable to source/evidence and model/prompt/version metadata.

## Research Deliverables Before Production Adoption

For each proposed capability provide:

1. Problem and current-state evidence.
2. Relevant primary/official sources and open-source references.
3. Compatibility with the current twin-repository architecture.
4. Data Contract.
5. Function Contract.
6. Metric/Semantic Contract.
7. Visualization Contract where relevant.
8. Migration/rollback plan.
9. Test/Evaluation plan.
10. Security/license/privacy considerations.
11. Expected benefit and measurable acceptance criteria.

## Current Recommendation

Treat this specification as the cumulative research baseline for product-wide data unification. Do not create a third core repository. Do not replace stable production collection or authoritative subject filtering merely for modernization. Prefer adapters, wrappers and incremental migration. Research findings must be incorporated only through the formal gate.
