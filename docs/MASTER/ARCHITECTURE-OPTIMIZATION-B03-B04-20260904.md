# Architecture Optimization + B03/B04 Foundation

Date: 2026-09-04
Status: EXECUTION BASELINE

## 1. Decision

The production architecture may change only when the replacement is demonstrably better, preserves production truth, preserves stable collection/subject rules, and passes regression gates. No rewrite-by-fashion.

The target architecture is a layered system with explicit ownership:

```text
External / Collector / File / Text / Media / API
                    |
             Universal Ingestion
                    |
          Raw Asset + Evidence
                    |
             Parse / Validate
                    |
          Normalize / Canonicalize
                    |
       Function + Formula Registry
                    |
          Canonical Dataset Layer
                    |
       Metric / Time Window Registry
                    |
       Domain Services / Business Logic
                    |
        API / View-model Adapters
                    |
        UI Shell / Window System
                    |
   Table | Chart | Timeline | Graph | Report
                    |
              Export / Evidence
```

## 2. Architecture changes approved

### 2.1 Introduce a Canonical Data Plane

Business metrics must be calculated once from canonical datasets. UI, charts, reports and exports consume adapters, not independent calculations.

Required concepts:
- dataset_id
- dataset_version
- schema_version
- source_asset_id
- source_record_ids
- transformation_version
- calculation_version
- formula_version
- quality_status
- calculated_at
- evidence_refs

### 2.2 Introduce registries

Create logical registries for:
- Metric
- Formula
- Function
- Time Window
- Route
- Window
- Visualization

A registry is the authoritative definition; modules may consume it but may not silently redefine the same metric.

### 2.3 Split Application responsibilities

`app.py` remains a compatibility entry point during migration. New work should move toward:

```text
routes -> services -> domain/functions -> repositories -> database
                     |
                canonical data
```

No big-bang rewrite. Existing routes are migrated one bounded domain at a time.

### 2.4 UI becomes a semantic system

UI is organized as:

```text
App Shell
  -> Workspace
    -> Module
      -> Page
        -> Section
          -> Component
            -> Window / Action
```

Window state and route state must be explicit. A modal/drawer/detail view must know its parent context and return context.

## 3. B03 UI Foundation

### Shell
- global navigation
- workspace switch/context
- top status bar
- global command/search
- system health indicator
- notification center

### Semantic primitives
- MetricCard
- DataTable
- ChartFrame
- FilterBar
- TimeRange
- StatusBadge
- EvidenceLink
- DetailDrawer
- DetailModal
- ConfirmDialog
- EmptyState
- LoadingState
- ErrorState
- Toast
- Timeline

### Design rules
- one canonical token layer
- no broad `[class*=...]` overrides for new code
- no component-level business calculations
- no duplicate route logic
- no hidden modal navigation
- accessibility and keyboard behavior are part of the component contract

Historical CSS may remain during migration but must be isolated and progressively retired. New components use semantic namespaces/tokens.

## 4. B04 visualization contract

Every visualization receives a canonical dataset plus a visualization specification:

```text
VisualizationSpec
- dataset_id
- metric_ids
- dimensions
- time_window_id
- filters
- aggregation
- formatter
- interaction
- evidence_action
```

Table, chart and report must derive from the same dataset and metric IDs.

Supported presentation families:
- dense data table
- metric cards
- line / area trend
- bar / stacked bar
- distribution
- timeline
- event relationship graph
- heatmap
- funnel / lifecycle
- comparison matrix

Do not add a chart merely for decoration. Every visual must answer a defined analytical question.

## 5. Data-to-UI path

```text
source
 -> ingestion_job
 -> parser
 -> validation
 -> normalization
 -> canonical_dataset
 -> metric/formula
 -> view_model
 -> visualization adapter
 -> component
```

For evidence-only assets:

```text
asset -> evidence -> linked entity
```

They must not be forced into fabricated numeric rows.

## 6. Domain ownership

```text
Collection      -> ingestion / collector services
Notes           -> note domain
Events          -> event domain
Risk            -> risk domain
KOS/KOC/UGC     -> influence/content domain
Reports         -> report domain
Podcast         -> podcast domain
AI              -> intelligence boundary
Evidence        -> evidence domain
```

Cross-domain references use IDs/contracts, not duplicated truth tables.

## 7. Migration strategy

1. Inventory existing implementation.
2. Identify canonical owner.
3. Wrap stable code where possible.
4. Move duplicated calculation into registry/service.
5. Point UI/report/export to canonical outputs.
6. Add regression/golden dataset.
7. Deprecate old path.
8. Remove only after usage and tests prove safe.

## 8. B04 acceptance gates

A module passes only when:
- source is traceable
- canonical dataset is identified
- metric/formula is identified
- table and chart agree
- report/export agree
- time window is identical
- filters are reproducible
- empty/loading/error states exist
- evidence is traceable
- regression tests pass

## 9. Non-negotiables

- Do not weaken `subject_rules` / hard filtering.
- Do not bypass human decision gates.
- Do not put secrets in frontend source.
- Do not create a second calculation for an existing metric.
- Do not let research directly mutate Production Truth.
- Do not rewrite stable production collection merely to modernize the stack.
