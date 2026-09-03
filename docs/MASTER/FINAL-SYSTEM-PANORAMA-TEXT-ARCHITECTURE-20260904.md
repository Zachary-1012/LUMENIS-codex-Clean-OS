# FINAL SYSTEM PANORAMA — TEXT ARCHITECTURE & MULTI-PLATFORM DESIGN

Status: ACTIVE / PRE-VISUAL FINAL ARCHITECTURE BASELINE

## 0. Highest-order constraints

1. **Function Freeze**: existing confirmed functions are product assets. This document may reorganize architecture, hierarchy, routing, windows, interaction and presentation, but must not remove, redefine, weaken or silently alter an existing confirmed function.
2. **Code Preservation**: stable production code is not rewritten for visual reasons. Code changes require a classified reason: bug, security, stability, performance, architecture, compatibility, or explicitly approved function change. Visual redesign alone is not sufficient.
3. **Architecture Evolution**: architecture may change only when the replacement is measurably better and regression-verified.
4. **Platform Expansion**: Web, Desktop App, Mobile App and Mini Program are presentation/runtime surfaces over shared contracts; they are not separate business-logic systems.
5. **Data Truth**: canonical dataset/table is the numerical truth surface. Charts, UI, reports and exports derive from it.
6. **Research does not directly mutate Production Truth**: Zachary-OS-AI researches/proposes; Z-Brand-Core implements through an evidence/contract/test gate.
7. **Legacy removal**: obsolete/conflicting active rules/files are reference/dependency scanned, migrated, regression-tested and deleted. Historical evidence may remain only as explicit LEGACY/ARCHIVE.

## 1. Twin repositories

```text
Zachary-OS-AI
Research / Intelligence / Learning
        │
        │ Evidence → Proposal → Contract → Implementation Spec
        ▼
Z-Brand-Core
Production Truth / Runtime / Data / Product
```

The research repository can learn from open source, papers, models and external AI. It must not directly become the production truth without verification.

## 2. Product hierarchy

```text
ZBP
│  FINAL PARENT SYSTEM
│
├── Shared Platform / Capability Center
│   ├── User & Permission
│   ├── Organization / Workspace
│   ├── Data / Ingestion
│   ├── Metrics / Functions / Formula
│   ├── AI / Model / Knowledge
│   ├── Visualization
│   ├── Workflow
│   ├── Integration / API
│   ├── Files / Evidence
│   ├── Notification
│   ├── Audit / Governance
│   └── Coding / Agent Runtime
│
├── CTH
│   CHILD SYSTEM / CURRENT FIRST IMPLEMENTATION & VALIDATION
│   ├── Monitoring
│   ├── Notes
│   ├── Topics
│   ├── Events
│   ├── Risk
│   ├── Data Analysis
│   ├── Brand / Industry
│   ├── Case Library
│   ├── Reports
│   └── existing production capabilities
│
├── KOS / KOC / UGC
│   CONTENT / CREATOR / PROPAGATION CAPABILITY DOMAIN
│
└── Podcast
    COMPLETE ATTACHED BUSINESS SYSTEM
```

CTH is developed and stabilized first. Proven capabilities are later contractized/adapted and absorbed into ZBP. The parent/child relationship is architectural ownership, not permission to change CTH's confirmed functions.

## 3. Multi-platform surface architecture

```text
                    SHARED PRODUCT CONTRACTS
                           │
          ┌────────────────┼────────────────┐
          │                │                │
        Web              App          Mini Program
          │                │                │
    full workspace    full/compact    task-oriented
    analysis surface  operational     lightweight surface
          │                │                │
          └────────────────┼────────────────┘
                           │
                    Shared API / State
                           │
                 Shared Domain Services
                           │
                    Canonical Data
```

Desktop App may wrap or extend the Web workspace where needed, but must not create a second business-logic implementation.

### Surface responsibility

- **Web**: primary complete workspace, analysis, management, dashboards, dense tables, reports, configuration, research and coding workspace.
- **Desktop App**: deep operational workspace, long-running tasks, local runtime, coding/sandbox operations, monitoring and notifications.
- **Mobile App**: decision/monitoring/action surface; responsive cards, alerts, evidence, trend, approval, task and quick analysis.
- **Mini Program**: lightweight entry, quick status, selected monitoring, notification, approval, content/task interactions; no forced replication of the full desktop workspace.

All surfaces preserve the same domain identity, metric definitions, evidence IDs and permissions.

## 4. Global visual/layout principle

Use a **ChatGPT-like conversational workspace layout principle** as a structural reference: persistent left navigation, central work surface, contextual right/detail surface when useful, clean typography, generous spacing, restrained chrome and clear focus. Do not copy ChatGPT branding or implementation.

The visual language is not fixed by the current legacy UI. The new system should be calm, analytical, layered and information-dense without becoming crowded.

```text
┌──────────────────────────────────────────────────────────────────┐
│ Global Header: context / search / command / status / account     │
├──────────────┬───────────────────────────────────┬───────────────┤
│              │                                   │               │
│ Left Nav     │        Main Work Surface          │ Context       │
│              │                                   │ Panel         │
│ Product      │  Page                             │               │
│ Module       │  Section                          │ Detail        │
│ Views        │  Table / Chart / Timeline         │ Evidence      │
│              │  Actions                          │ Filters       │
│              │                                   │               │
├──────────────┴───────────────────────────────────┴───────────────┤
│ optional status / activity / task strip                          │
└──────────────────────────────────────────────────────────────────┘
```

The right panel is contextual, not permanently mandatory. On mobile it becomes a drawer/full-screen detail; on mini program it becomes a focused task page.

## 5. UI hierarchy

```text
Application Shell
  ↓
Workspace
  ↓
Product / Domain
  ↓
Module
  ↓
Page
  ↓
Section
  ↓
Component
  ↓
Window / Action
```

### Example

```text
CTH
└── 舆情监测
    └── 事件中心
        └── 事件详情页
            ├── 事件摘要
            ├── 传播趋势
            ├── 关联笔记
            ├── KOS/KOC/UGC
            ├── 风险
            └── Evidence
                 └── Detail Drawer / Modal
```

English labels in architecture diagrams are technical references only. Product-facing labels can use the project's canonical language/localization system.

## 6. Route / window / interaction

```text
Parent Page
 ↓
User Action
 ↓
Window State
 ↓
Target Object
 ↓
Child Context
 ↓
Detail / Evidence / Operation
 ↓
Return to exact Parent Context
```

Every window must declare parent context, target, state, data source, loading/empty/error state and return context.

### Window types

```text
Detail
Drawer
Modal
Filter
Search / Command
Comparison
Evidence
Confirmation
Notification
Task / Progress
```

No hidden route creation. No duplicated business state. Context must survive drill-down, filter, comparison, evidence inspection and return.

## 7. Universal data ingestion

All external inputs use one conceptual pipeline:

```text
Collector / File / Excel / Table / PPT / PDF / Word
Image / Video / Audio / API / Text / Manual Input
                         ↓
                  Universal Ingestion
                         ↓
                    Raw Asset
                         ↓
                  Evidence Registry
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
                Metric / Time Window
                         ↓
                     View Model
                         ↓
                Visualization Spec
                         ↓
      Dynamic Table / Chart / Timeline / Graph
                         ↓
                  UI / Report / Export
```

### Two valid output paths

```text
Path A: computed data → Canonical Table → business module

Path B: computed data → Canonical Table → View Model
       → Visualization Spec → dynamic visual UI
```

A table-only result is valid and must not be forced into a chart.

Images/video/audio are evidence objects unless a verified extraction pipeline produces structured fields. Do not fabricate numeric values from media merely to create charts.

## 8. Numerical accuracy contract

```text
SOURCE
 ↓
TRANSFORMATION
 ↓
FUNCTION
 ↓
FORMULA
 ↓
CANONICAL TABLE
 ↓
VIEW MODEL
 ↓
VISUALIZATION
 ↓
REPORT / EXPORT
```

One metric = one authoritative calculation owner.

The UI, chart, report and export layers must not independently recalculate the same business metric.

Every computed result should retain lineage: source/evidence ID, schema version, function/formula version, metric ID, time window, filter state, quality status and calculation timestamp.

## 9. Visualization system

Visualization is a semantic layer, not hand-drawn numbers.

```text
VisualizationSpec
├── dataset_id
├── metric_ids
├── dimensions
├── time_window
├── filters
├── aggregation
├── formatter
├── interaction
└── evidence_action
```

Supported families:

```text
Metric Card
Dense Data Table
Line / Area Trend
Bar / Stacked Bar
Distribution
Timeline
Heatmap
Relationship Graph
Funnel / Lifecycle
Comparison Matrix
```

Every visual must answer an analytical question and support drill-down where the domain requires it.

## 10. Core domain relationship

```text
Note
 ↓
Topic
 ↓
Event
 ↓
Sentiment / Risk
 ↓
Impact / Propagation
 ↓
KOS / KOC / UGC
 ↓
Decision
```

These are related objects, not seven isolated dashboards.

## 11. KOS / KOC / UGC architecture

```text
Creator / Account
 ↓
Content
 ↓
Topic / Event
 ↓
Engagement / Influence
 ↓
Quality / Relevance
 ↓
Risk
 ↓
Potential / Attribution
 ↓
Lifecycle
 ↓
Content / Outreach / Reward / Learning
```

The existing confirmed KOS/KOC/UGC functions remain intact. Architecture only provides common capability contracts and shared data/visual infrastructure.

## 12. Podcast architecture

Podcast is a complete attached domain, not a single feature:

```text
Podcast
├── Idea Vault
│   ├── Daily
│   ├── Weekly
│   └── Monthly
├── Knowledge Base
├── Research
├── Topics
├── Guests
├── Episode Planning
├── Discussion Route
├── Script / Content
├── Recording / Review
├── Publishing / Distribution
├── Analytics
└── Reports
```

It reuses shared data, evidence, AI, UI and report infrastructure but retains domain-specific business logic.

## 13. Content production

```text
Data
 ↓
Insight
 ↓
Topic
 ↓
Strategy
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

Templates are canonical assets. AI assists but does not silently alter confirmed facts or bypass approval gates.

## 14. Report architecture

```text
Canonical Data
 ↓
Report Adapter
 ↓
Report Template
 ↓
Rendered Report
 ↓
Export
```

Report families include daily, weekly, monthly, quarterly, yearly, special/event, sentiment, risk, KOS/KOC/UGC, propagation, content and Podcast.

Standard structure:

```text
Executive Summary
 → Key Findings
 → Event / Issue
 → Impact
 → Risk
 → Evidence
 → Trend
 → Recommendation
 → Appendix / Data
```

## 15. Internal Coding + multi-AI

```text
                 Internal Coding Workspace
                           │
                   Task + Repository Context
                           │
                    AI Orchestrator
             ┌─────────────┼─────────────┐
             ↓             ↓             ↓
        Local AI        Zhipu        Doubao / Other
             └─────────────┼─────────────┘
                           ↓
                    Candidate Solution
                           ↓
                    Local Sandbox
                           ↓
                    Test / Lint / CI
                           ↓
                         Diff
                           ↓
                     AI Review / Audit
                           ↓
                     Human Approval Gate
                           ↓
                       Git Commit
                           ↓
                     Learning Asset
                           ↺
```

External AI providers are collaborators/validators. The long-term goal is for the internal/local AI to assume increasing control as capability is proven.

Doubao can be reduced from primary executor to backup/second opinion/benchmark, and eventually removed only after the internal agent can reliably perform the same role under the same gates.

## 16. Coding function freeze

The internal Coding Agent must classify every proposed code change:

```text
Bug / Stability / Security / Performance / Architecture / Compatibility
                      ↓
                 MAY PROCEED

Confirmed Function Change
                      ↓
                    BLOCK
                      ↓
               Human Approval
```

No AI agent may redefine a confirmed function merely because it believes an alternative is cleaner.

## 17. Platform-specific adaptation

Do not duplicate pages one-to-one across platforms.

```text
Shared capability
      ↓
Shared domain contract
      ↓
Surface-specific presentation

Web       = complete workspace
Desktop   = deep/local/long-running workspace
Mobile    = monitor/decide/act
Mini      = quick task/entry/approval
```

The same event, metric, evidence and permission object must remain semantically identical across surfaces.

## 18. Visual simplification rule

The system must avoid architectural overloading.

Use:

```text
One capability
→ one canonical owner
→ many composed surfaces
```

Avoid:

```text
one page = one new system
one chart = one calculation
one platform = one backend
one window = one duplicated state
```

The visual goal is not maximum information density; it is **maximum decision clarity per unit of attention**.

## 19. Architecture audit findings to carry forward

- Current `ARCHITECTURE.md` is still strongly CTH-specific and identifies an older v5.7.0 snapshot. It should be treated as historical/current-implementation evidence, not the final ZBP architecture authority. This is a documentation conflict, not a reason to rewrite the production functions.
- The repository contains both broad governance baselines and implementation-era documents. The canonical master must be clearly designated so agents do not choose conflicting historical instructions.
- The current tree also contains an empty `.gitmodules`; this should be verified against actual submodule intent before any repository cleanup. Do not infer a migration from documentation alone.
- The research repository already contains cumulative architecture/research governance assets; future research must feed the master baseline rather than create parallel architectural truths.

## 20. KEEP / ADAPT / REMOVE policy

```text
Existing function
   ↓
KEEP

Existing implementation
   ↓
Stable? → KEEP
   ↓
Needs structural improvement? → ADAPT / REFACTOR under regression

Existing rule/file
   ↓
Compatible? → KEEP / MERGE
   ↓
Partially useful? → ADAPT
   ↓
Obsolete / conflicting / duplicate? → MIGRATE → TEST → DELETE
```

No deletion based on filename alone. Dependency/reference/runtime verification is mandatory.

## 21. Final text panorama

```text
                           ZBP — PARENT
                                │
      ┌─────────────────────────┼──────────────────────────┐
      │                         │                          │
 Shared Platform              Domains                 Attached Systems
      │                         │                          │
 ┌────┼────┬────┬────┐    ┌────┼────┐                ┌────┴────┐
 │    │    │    │    │    CTH  KOS/KOC/UGC            Podcast  │
Data AI  Viz Workflow API      │                            Research
 │    │    │    │               │
 └────┴────┴────┴───────┬───────┘
                         │
                  Canonical Contracts
                         │
       ┌─────────────────┼──────────────────┐
       │                 │                  │
      Web             Desktop             Mobile
       │                 │                  │
       └─────────────────┼──────────────────┘
                         │
                    Mini Program
                         │
                         ↓
                 SAME DATA / METRICS
                 SAME PERMISSIONS
                 SAME EVIDENCE
                 DIFFERENT PRESENTATION
```

## 22. Final design principle

```text
FUNCTION = FROZEN ASSET
ARCHITECTURE = OPTIMIZABLE
DATA = SINGLE SOURCE OF TRUTH
TABLE = NUMERICAL TRUTH
VISUAL = DERIVED EXPERIENCE
WINDOW = CONTEXTUAL STATE
PLATFORM = PRESENTATION SURFACE
AI = COLLABORATOR → VALIDATOR → EVENTUAL LOCAL AUTONOMY
RESEARCH = EVIDENCE / PROPOSAL
CORE = PRODUCTION TRUTH
```

**This document is the final text architecture baseline before detailed visual drawing.**
