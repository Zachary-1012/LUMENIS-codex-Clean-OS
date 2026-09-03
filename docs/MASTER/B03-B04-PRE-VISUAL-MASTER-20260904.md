# B03-B04 PRE-VISUAL MASTER — 2026-09-04

Status: ACTIVE / PRE-VISUALIZATION IMPLEMENTATION BASELINE
Purpose: One-step consolidation before visual drawing/design implementation. This document supersedes fragmented B03/B04 planning where conflicts exist.

## 0. Cumulative baseline carried forward
- ZBP = eventual parent system.
- CTH = child system/domain and current first development/validation environment.
- Development order: CTH first -> real data -> stability -> regression/audit -> capability contract -> extract/adapt/merge -> ZBP absorption.
- Zachary-OS-AI = research/intelligence; Z-Brand-Core = production truth.
- Research cannot directly mutate production truth.
- Obsolete/conflicting rules/files must be reference/dependency scanned, migrated, tested, then deleted; historical material may remain only as explicit LEGACY/ARCHIVE.
- Stable collection, subject hard filtering and production truth must not be weakened for cosmetic modernization.

## 1. Architecture optimization decision
Architecture may change when evidence shows the replacement is measurably better in correctness, stability, performance, maintainability, reuse, security, or interaction quality. No rewrite-by-fashion.

The architecture is organized by capability and dependency, not by repository/file naming alone.

```text
ZBP Parent
├── shared platform capabilities
├── business domains
├── intelligence / knowledge
├── CTH child domain
└── Podcast attached business domain

CTH-first implementation
└── proven capabilities
    └── contractized absorption into ZBP
```

Capability weight is assessed by: foundationality, reuse, data authority, runtime criticality, business coverage, dependency fan-in, uniqueness, stability and replacement cost.

## 2. Source-to-experience chain

```text
External Source
  ├─ Collector
  ├─ File / Table
  ├─ PPT / PDF / Word
  ├─ Text
  ├─ Image / Video / Audio
  ├─ API
  └─ Manual Input
        ↓
Universal Ingestion
        ↓
Raw Asset / Evidence
        ↓
Parse
        ↓
Validate
        ↓
Normalize
        ↓
Function / Formula
        ↓
Canonical Dataset / Table
        ↓
Metric + Time Window + Filter State
        ↓
View Model
        ↓
Visualization Spec
        ↓
Dynamic Table / Chart / Timeline / Graph / UI
        ↓
Report / Export / Evidence
```

## 3. Data truth rules

### 3.1 Calculate once
A business metric has one authoritative calculation owner. Presentation and export layers never independently recompute it.

### 3.2 Table is the numerical truth surface
Where a task only requires structured computed data, stop at Canonical Dataset/Table. Do not force a chart/UI layer.

Where visualization is required:
`Canonical Table -> View Model -> Visualization Spec -> Dynamic presentation`.

### 3.3 Evidence is not invented data
Image/video/audio/document evidence can remain an Evidence object linked to entities/events. It must not be converted into fabricated numeric rows merely to make a chart.

### 3.4 Lineage
Every computed output must be traceable to source asset/record IDs, schema/version, transformation/function/formula versions, metric ID, time-window ID, quality status, calculation timestamp and evidence references.

## 4. Registry layer

Canonical registries are the authority for:
- Metric
- Formula
- Function
- Time Window
- Filter
- Dataset/View Model
- Route
- Window
- Visualization
- Report Template

Modules consume registries. They do not silently redefine an existing canonical metric or route/window contract.

## 5. UI hierarchy

```text
App Shell
└── Workspace
    └── Product / Domain
        └── Module
            └── Page
                └── Section
                    └── Component
                        └── Window / Action
```

### 5.1 Shell responsibilities
Global navigation, workspace/context, global search/command, system health, notifications and user/session context.

### 5.2 Page responsibilities
Page composes domain capabilities. It does not own duplicate business calculations.

### 5.3 Component responsibilities
Components render state and emit actions. Business truth remains outside presentation components.

## 6. Window and navigation model

Every window declares:
- parent context
- trigger action
- target object
- window type
- child state
- route/state mutation
- data/evidence source
- loading state
- empty state
- error state
- return context

```text
Parent Context
  ↓
Action
  ↓
Window State
  ↓
Target
  ↓
Child Context
  ↓
Detail / Evidence / Action
  ↓
Return Context
```

Window types: modal, drawer, detail, command/search, filter, comparison, evidence, confirmation, notification.

No hidden route creation and no duplicated business state inside modal code.

## 7. Dynamic interaction model

Interaction is stateful and context-preserving:
- filter
- sort
- select
- drill-down
- compare
- timeline navigation
- evidence inspection
- row action
- chart-to-table transition
- table-to-detail transition
- detail-to-evidence transition
- report/export

The same metric/filter/time-window context must survive transitions unless the user explicitly changes it.

## 8. B03 semantic component system

Required primitives:
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
- Command/Search
- Notification Center
- Health Indicator
- ComparisonView
- ExportAction

The visual system should use semantic tokens and composable primitives. Existing components should be reused/adapted before new ones are invented.

## 9. B04 Visualization system

### VisualizationSpec
```text
VisualizationSpec
├── dataset_id
├── metric_ids
├── dimensions
├── time_window_id
├── filters
├── aggregation
├── formatter
├── interaction
└── evidence_action
```

### Presentation families
- Dense table
- Metric cards
- Line/area trend
- Bar/stacked bar
- Distribution
- Timeline
- Event relationship graph
- Heatmap
- Funnel/lifecycle
- Comparison matrix

Every visual must answer a defined analytical question and expose its source/context where appropriate.

## 10. Data table behavior

Table is not a static HTML surface. It is a reusable stateful data surface with:
- column definitions
- sorting
- filtering
- pagination
- row selection
- column visibility
- row actions
- density/format rules
- virtualization when scale requires it
- empty/loading/error states
- evidence/detail transition
- export context

Adopt the architectural principle of feature-based/headless table behavior rather than forcing every business table into one monolithic component. Current open-source patterns show this separation in shadcn/TanStack Table; however, dependency/version compatibility must be verified before adoption. TanStack Table v9 changed APIs substantially, so version must be pinned and tested rather than inferred from latest examples.

## 11. Visual design direction

Do not copy the current legacy visual style. Build a new system from:
- information hierarchy
- semantic density
- clear state transitions
- strong whitespace rhythm
- restrained but expressive typography
- analytical readability
- evidence visibility
- responsive behavior
- accessibility
- motion only where it communicates state/change

Visual references are inputs, not authority. The product's own information architecture determines the final visual language.

## 12. Domain modules carried forward

### CTH
Collection, notes, topics, sentiment, events, risk, KOS, KOC, UGC, content production, reports, export, runtime, health, recovery and related mature capabilities.

### ZBP
Eventual parent orchestration, shared platform capabilities, business domains and mature capability absorption from CTH.

### Podcast
Complete attached business system under ZBP. Includes Idea Vault (Daily/Weekly/Monthly), knowledge base, research, topics, guests, episode planning, discussion route, scripts, recording/review, distribution, analytics and report surfaces. It reuses shared data/evidence/AI/UI/report infrastructure but retains its own domain logic.

## 13. KOS / KOC / UGC

All three use the same canonical data and UI contracts. Their domain model must support identity, content, influence, engagement, relevance, quality, risk, potential, attribution, lifecycle, outreach/reward where applicable, and evidence.

## 14. Monitoring objects

Notes, topics, events and risks are linked rather than isolated dashboards:

```text
Note
 ↓
Topic
 ↓
Event
 ↓
Sentiment / Risk
 ↓
Impact
 ↓
KOS / KOC / UGC relationship
 ↓
Decision
```

## 15. Content production system

```text
Data
 ↓
Insight
 ↓
Topic
 ↓
Content Strategy
 ↓
Title / Copy / Cover / Script
 ↓
Comment / Reply
 ↓
Publish
 ↓
Monitor
 ↓
Review
 ↓
Learning Asset
```

AI may assist generation and recommendations but cannot bypass human decision gates or alter canonical facts silently.

## 16. Report system

Report templates consume canonical outputs:

```text
Canonical Data
 ↓
Report Adapter
 ↓
Template
 ↓
Rendered Report
 ↓
Export
```

Core report families: daily, weekly, monthly, quarterly, yearly, special/event, sentiment, risk, KOS/KOC/UGC, propagation, content and Podcast.

Standard skeleton:
`Executive Summary -> Key Findings -> Event/Issue -> Impact -> Risk -> Evidence -> Trend -> Recommendation -> Appendix/Data`.

## 17. CSS / JS and legacy cleanup

Before visual implementation:
1. inventory all style/script systems;
2. map consumers;
3. identify duplicate/conflicting selectors and logic;
4. select canonical token/component owner;
5. migrate consumers;
6. regression test;
7. delete obsolete/conflicting files/rules;
8. verify no inactive rule remains loaded in production.

No permanent parallel design systems.

## 18. Research adoption

External/open-source research follows:

```text
Research
 ↓
Evidence
 ↓
Candidate
 ↓
Compatibility
 ↓
Benefit / Risk
 ↓
Contract
 ↓
Implementation
 ↓
Test
 ↓
Audit
 ↓
Release
```

Examples studied for this baseline include shadcn/ui's composable data-table approach and feature-oriented TanStack Table integration. shadcn explicitly recommends composing existing components rather than inventing monoliths; its current docs also demonstrate feature-based table behavior. These principles are adopted conceptually, not as an automatic dependency decision.

## 19. Pre-visualization acceptance gate

Do not start final visual drawing until:
- architecture ownership is mapped;
- CTH-first implementation boundary is explicit;
- ZBP absorption boundary is explicit;
- data lineage is explicit;
- canonical metric/function/formula ownership is explicit;
- table-only vs table+visualization paths are explicit;
- route/window/context model is explicit;
- component inventory is explicit;
- domain modules are mapped;
- report/content templates are mapped;
- legacy removal candidates are identified;
- adoption decisions are evidence-backed.

## 20. Hard stop conditions

Stop and fix before visual implementation if any of these occurs:
- UI calculates a business metric;
- chart and table use different metric definitions;
- report/export recalculates data independently;
- window loses parent/return context;
- a new component duplicates an existing canonical component without justification;
- an obsolete rule remains active;
- a legacy CSS/JS system remains silently loaded;
- CTH stability is compromised for redesign;
- research output is written directly into Production Truth;
- a proposed architecture change has no measurable benefit evidence.

## 21. Final implementation sequence

```text
Cumulative Baseline
 ↓
Source / Dependency Mapping
 ↓
Architecture Reorganization
 ↓
CTH-first capability stabilization
 ↓
UI / Window / Route contracts
 ↓
Canonical Data / Metric / Function contracts
 ↓
View Model
 ↓
VisualizationSpec
 ↓
Component System
 ↓
Dynamic Table
 ↓
Dynamic Visualization / Trend
 ↓
Domain UI
 ↓
Report / Export
 ↓
Regression
 ↓
Legacy Removal
 ↓
Audit
 ↓
ONLY THEN: Final Visual Drawing / Design Pass
```

## 22. Supersession rule

This document is the single pre-visualization implementation baseline for B03/B04. Older fragmented B03/B04 rules that conflict with it are superseded. They must not remain active. After reference/dependency verification, conflicting files/rules are to be deleted or explicitly moved to LEGACY/ARCHIVE according to the repository deletion gate.
