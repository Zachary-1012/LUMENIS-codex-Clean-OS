# NEXT STAGE — B03/B04 Execution Plan
Date: 2026-09-04
Status: ACTIVE EXECUTION

## 0. Cumulative baseline
This plan carries forward the active architecture baseline. ZBP is the eventual parent system; CTH is the current child system and the first implementation/validation environment. Mature CTH capabilities may later be absorbed into ZBP through audited contracts/adapters/extraction.

## 1. B03 — Architecture + UI Foundation

### 1.1 Architecture mapping
For every existing page/module/function, map:
`route -> page -> section -> component -> window -> API -> service -> function -> dataset -> metric -> evidence`.
Record canonical owner, dependency, reuse decision, migration status, and replacement.

### 1.2 UI hierarchy
`Shell -> Workspace -> Product/Domain -> Module -> Page -> Section -> Component -> Window/Action`.
Window state must include parent context, child target, action, route/context state and return context.

### 1.3 UI cleanup
Inventory all active CSS/JS systems. Keep only the canonical token/component layer for new work. Isolate historical systems, migrate consumers, regression-test, then DELETE obsolete/conflicting files. Do not leave inactive rules loaded into production.

### 1.4 Required semantic components
MetricCard, DataTable, ChartFrame, FilterBar, TimeRange, StatusBadge, EvidenceLink, DetailDrawer, DetailModal, ConfirmDialog, EmptyState, LoadingState, ErrorState, Toast, Timeline, Command/Search, Notification Center, Health Indicator.

## 2. B04 — Data-to-Visualization Foundation

### 2.1 Universal ingestion
All external inputs — collector, file, Excel/table, PPT, PDF, Word, image, video, audio, API, text/manual input — enter through the ingestion contract.

`asset -> parser -> validation -> normalization -> function -> formula -> canonical dataset/table`.

Evidence-only assets remain evidence and must not be fabricated into numeric records.

### 2.2 Canonical data rule
A business metric is calculated once. UI, tables, charts, reports and exports consume the canonical output. No second calculation in presentation/export layers.

### 2.3 Visualization contract
`VisualizationSpec = dataset_id + metric_ids + dimensions + time_window_id + filters + aggregation + formatter + interaction + evidence_action`.

Presentation families: dense table, metric cards, line/area trend, bar/stacked bar, distribution, timeline, event graph, heatmap, lifecycle/funnel, comparison matrix.

### 2.4 Table-first rule
Where the output only requires a calculated table, stop at canonical table and enter the relevant business module. Where visualization is required, the same canonical table feeds dynamic table/chart/UI. Tables are the numerical truth surface; visualizations are derived views.

## 3. Domain execution

Implement and validate in CTH first: notes, topics, sentiment, events, risk, KOS, KOC, UGC, content production, reports, exports and related stable production capabilities. Do not destabilize collection or subject hard filtering.

Podcast remains a complete attached business system under the eventual ZBP parent and reuses shared data/evidence/AI/UI/report infrastructure.

## 4. Acceptance gates

A change is accepted only when:
- source-to-output lineage is traceable;
- canonical dataset/table is identified;
- metric/formula/function owner is identified;
- table/chart/report/export agree;
- time window and filters are reproducible;
- window/route context is reproducible;
- loading/empty/error states exist;
- evidence is traceable;
- regression/golden-data tests pass;
- obsolete conflicting implementation is removed or explicitly archived.

## 5. Mandatory deletion
Old rules/files that are no longer applicable MUST NOT remain active. Before deletion: reference scan -> migrate consumers -> tests -> delete -> verify. Historical audit material may remain only as LEGACY/ARCHIVE and cannot participate in active implementation.

## 6. Execution order

B03.1 architecture inventory
B03.2 route/window map
B03.3 UI component map
B03.4 CSS/JS consolidation
B03.5 canonical shell/window implementation
B04.1 ingestion contract
B04.2 canonical table contract
B04.3 metric/formula registry integration
B04.4 visualization spec
B04.5 dynamic table
B04.6 dynamic chart/trend
B04.7 report/export adapters
B04.8 regression and deletion audit
