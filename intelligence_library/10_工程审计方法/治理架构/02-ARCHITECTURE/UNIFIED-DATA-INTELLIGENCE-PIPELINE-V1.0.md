# Unified Data Intelligence Pipeline V1.0

Status: ACTIVE SPECIFICATION · PLAN ONLY · NO PRODUCTION IMPLEMENTATION BY THIS DOCUMENT

## 1. Purpose

Unify the full product data chain without rewriting or weakening existing production capabilities:

External Data → Ingestion → Raw/Evidence → Parse → Validate → Normalize → Canonical Data → Function → Metric → Canonical Table → View Model → Visualization → UI/Report/Export/AI.

Core rule: business metrics are calculated once. Canonical Table is the numerical Truth Surface. Charts, UI, reports, exports and AI consume canonical outputs and must not independently recalculate business metrics.

## 2. Non-Destructive Migration Gate

This specification is additive and migration-first. Before changing any existing capability:

Inventory → Reference Scan → Dependency Scan → Runtime/Behavior Baseline → Classify → Preserve/Merge/Migrate → Implement → Regression Test → Evidence → Audit → Release.

Every existing asset must be classified as one of KEEP / MERGE / MIGRATE / LEGACY / ARCHIVE / DELETE.

DELETE is permitted only after reference/dependency/runtime verification, replacement coverage, regression verification and explicit audit evidence. LEGACY/ARCHIVE assets must not participate in active implementation.

No blind rewrite. No parallel duplicate business calculation. No removal of stable collection, subject filtering, risk rules, reports or runtime behavior merely for modernization.

## 3. Existing Capability Protection

The implementation must preserve current production truth and behavior, including collection, source adapters, authoritative subject filtering, business entities, KOS/KOL/KOC/UGC, events, risk, reports, APIs, runtime, health and recovery unless a measured replacement is demonstrably better and passes the migration gate.

New capability must first wrap/adapt existing behavior where possible. Proven code is reused before new code is written.

## 4. Data Source and Evidence Contract

Every external input must receive source_id, source_type, source_name, source_uri, collector_id, collector_version, collected_at, request_id, content_hash and schema_version where applicable.

Raw/Evidence is immutable. Parsing, normalization and derived data create versioned outputs rather than silently mutating raw evidence.

Required lineage:

Result → Metric → Function → Dataset/Table → Parsed/Canonical Data → Raw Evidence → Source/Run.

## 5. Data Quality Gate

Before Canonical Data, validate schema, types, required fields, nullability, ranges, uniqueness, referential integrity, freshness, completeness and business rules.

Never convert collection/calculation failure into numeric zero. Distinguish at least 0, NULL/UNKNOWN, NOT_AVAILABLE, STALE and ERROR.

## 6. Canonical Data

Core entities use stable IDs and versioned schemas. Existing business entities must be inventoried and reused. Do not create duplicate sources of truth.

Target domains include Content, Account, Brand, Category, KOS, KOL, KOC, UGC, Event, Campaign, Risk and Report.

## 7. Function Registry

Every business calculation becomes a versioned canonical Function with:

function_id, name, version, purpose, inputs, outputs, formula/logic, dependencies, dimensions, time window, unit, error policy, quality requirements, tests, evidence and status.

One business calculation must have one canonical implementation. Existing calculations must be located and classified before creating replacements.

## 8. Metric/Semantic Registry

Every business metric must have:

metric_id, name, definition, function_id, dataset, dimensions, unit, default time window, filters, version, owner, evidence, tests and status.

Identical metric IDs mean identical business semantics. Pages may change presentation/filtering but may not redefine the metric.

## 9. Canonical Tables

Canonical tables are the numerical Truth Surface. Recommended fact domains include content_metrics, kos_metrics, brand_metrics, event_metrics, campaign_metrics and risk_metrics, subject to inventory and dependency review.

A derived result should carry metric_id, function_version, dataset_version, time_window, generated_at, lineage_id and quality_status where applicable.

## 10. View Model

UI-facing View Models may filter, group, sort, paginate and apply permissions, but may not redefine or independently recalculate canonical business metrics.

## 11. Visualization Registry

Dynamic visualization is a reusable presentation layer. Recommended module classes include trend, ranking, distribution, timeline, heatmap, network, funnel, correlation, geo and comparison.

Visualization specifications consume canonical datasets/metrics. Renderer code must not contain hidden business formulas.

Required metadata: visualization_id, dataset_id, metric_id, dimensions, mapping/spec, interaction, renderer, empty/error states, responsive/accessibility rules, version and status.

## 12. Product-Wide Data Coverage

All numeric/data-bearing surfaces must be inventoried and connected: home/dashboard, monitoring, KOS/KOL/KOC/UGC, brands, categories, events, campaigns, risk, reports, exports, AI analysis and any future module.

For identical metric + dimensions + filters + time window + permissions, UI/table/chart/report/export/AI results must be consistent.

## 13. Reports

Daily, weekly, monthly, annual and special/event reports consume canonical metrics and evidence. Reports must not maintain independent business calculation logic.

Report generation is: Canonical Data + Metrics + Evidence + Interpretation + Decision context.

## 14. AI/Agent Boundary

AI/Agent may query, explain, compare, detect anomalies and propose changes. It may not bypass canonical metrics, data-quality gates, contracts, permissions or human/release gates to alter Production Truth.

Important AI outputs retain source/evidence, model, prompt/version, input, output, confidence and human correction where applicable.

## 15. Lineage, Observability and Versioning

Track source, collector, parser, dataset, function, metric, table, view, visualization and report versions. Record freshness, row counts, quality status, failures and last_success_at for critical pipelines.

Changes to a Function/Metric/Dataset must support impact analysis across dependent tables, views, charts, reports, exports and AI consumers.

## 16. Research-Informed Design Inputs

The implementation may learn from OpenLineage for lineage/provenance, OpenTelemetry for semantic conventions/observability, dbt/MetricFlow for metrics/semantic modeling, Great Expectations for executable data quality, Vega-Lite for declarative visualization and Apache ECharts for interactive dataset/renderer separation. These are references, not dependencies or copied architecture.

External research, open-source code and models are inputs only. License, security, compatibility and fitness must be reviewed before adoption.

## 17. Execution Phases

P0: inventory existing calculations, data-bearing surfaces, schemas, APIs, tables, reports and visualizations; establish baseline and registries.

P1: introduce contracts, quality gates, lineage IDs and canonical function/metric definitions without changing business results.

P2: connect existing Content/Brand/KOS/KOL/KOC/Event/Risk/Campaign calculations to canonical functions/tables.

P3: migrate visualizations to registry/spec-driven consumption.

P4: migrate reports/exports to canonical metrics.

P5: expose governed semantic/metric access to AI/Agent.

P6: run product-wide duplicate-calculation, consistency, lineage, quality and regression audit.

## 18. Acceptance Criteria

A. Every critical result can trace back to evidence/source.
B. Same canonical metric under identical parameters is numerically consistent across all surfaces.
C. Each business calculation has one canonical Function.
D. Tables are the numerical Truth Surface.
E. Visualizations do not independently calculate business metrics.
F. Data failure states are not disguised as zero.
G. Version and impact relationships are auditable.
H. Existing production capabilities remain behaviorally equivalent unless an audited improvement is approved.
I. No third core repository is created.
J. No research artifact becomes production truth without Contract → Implementation → Test → Evidence → Audit → Release.

## 19. Rollback

Every migration must be reversible until release acceptance is complete. Existing path remains available during migration when technically safe. Feature flags/adapters may be used to switch between old and new paths while comparing outputs.

## 20. Definition of Done

Do not mark this initiative complete because files compile. Completion requires implementation evidence, test evidence, cross-surface consistency evidence, data-quality evidence, lineage evidence, regression evidence, audit result and release decision.

This document is the governing implementation specification for the unified data pipeline initiative. It does not itself authorize deletion or rewrite of existing production assets.
