# FINAL VISUAL SYSTEM — PRE-DESIGN MASTER
Date: 2026-09-04
Status: ACTIVE / DESIGN-FROZEN-FUNCTIONS / ARCHITECTURE-OPTIMIZABLE

## 0. HARD FREEZE — FUNCTIONALITY
This stage MUST NOT change the user's already-defined business functions, workflows, business rules, collection behavior, data contracts, APIs, or stable production code merely for UI/architecture optimization.

Priority:
1. Preserve existing functional behavior.
2. Preserve stable production code.
3. Preserve canonical business rules and outputs.
4. Optimize architecture only where it improves structure without changing function.
5. Optimize UI, interaction, visualization and composition around the existing capability.

Any proposed code change must be classified:
- UI-only
- architecture/refactor-only
- bug/security/stability fix
- required functional change

Functional change is BLOCKED in this phase unless explicitly approved because it is required for correctness, security or stability.

## 1. Final target
The deliverable before visual drawing is a complete system map covering:
- product hierarchy
- module hierarchy
- page hierarchy
- component hierarchy
- window/route hierarchy
- data lineage
- table/visualization lineage
- interaction transitions
- report/export paths
- CTH-first implementation boundary
- eventual ZBP capability absorption
- Podcast attached-system boundary
- KOS/KOC/UGC and monitoring relationships

## 2. Product topology

```text
ZBP — Parent System
│
├── Shared Platform
│   ├── Identity / Context
│   ├── Data / Evidence
│   ├── AI / Intelligence
│   ├── UI / Interaction
│   ├── Visualization
│   ├── Reports / Export
│   ├── Runtime / Health / Recovery
│   └── Notifications / Command
│
├── CTH — Child Business System
│   ├── Collection
│   ├── Notes
│   ├── Topics
│   ├── Events
│   ├── Sentiment
│   ├── Risk
│   ├── KOS
│   ├── KOC
│   ├── UGC
│   ├── Content Production
│   └── Reports / Export
│
└── Podcast — Attached Complete Business System
    ├── Idea Vault
    ├── Knowledge Base
    ├── Research
    ├── Topics
    ├── Guests
    ├── Episode Planning
    ├── Discussion Route
    ├── Script / Content
    ├── Recording / Review
    ├── Distribution
    ├── Analytics
    └── Reports
```

CTH is implemented first. Proven capabilities are later absorbed into ZBP through audited capability contracts. This does not alter CTH's existing function set.

## 3. Universal data truth

```text
ANY INPUT
collector / file / table / PPT / PDF / Word / text / image / video / audio / API / manual
        ↓
INGESTION
        ↓
RAW ASSET + EVIDENCE
        ↓
PARSE
        ↓
VALIDATE
        ↓
NORMALIZE
        ↓
FUNCTION / FORMULA
        ↓
CANONICAL DATASET / TABLE  ← numerical truth
        │
        ├── table-only business need
        │       ↓
        │    module / report / export
        │
        └── visualization required
                ↓
             VIEW MODEL
                ↓
        VISUALIZATION SPEC
                ↓
      dynamic table / chart / trend / timeline / graph
                ↓
              UI
                ↓
          report / export
```

Never calculate the same business metric separately in frontend, chart, report or export.

## 4. UI hierarchy

```text
APP SHELL
 ↓
WORKSPACE
 ↓
PRODUCT / DOMAIN
 ↓
MODULE
 ↓
PAGE
 ↓
SECTION
 ↓
COMPONENT
 ↓
WINDOW / ACTION
```

### Shell
Global navigation, global command/search, context, notifications, health, user/session state.

### Workspace
Current product/domain context and working scope.

### Module
A complete business capability; owns navigation grouping, not duplicated business calculations.

### Page
A functional composition of sections.

### Section
A coherent information/action region.

### Component
Reusable semantic rendering/interaction primitive.

### Window
Contextual surface: modal, drawer, detail, evidence, filter, comparison, command, confirmation or notification.

## 5. Window + route relationship

```text
Parent Page
   ↓ trigger
Action
   ↓
Window
   ├── Target
   ├── Context
   ├── Data
   ├── Evidence
   ├── Loading
   ├── Empty
   ├── Error
   └── Child Action
          ↓
     Return Context
```

Route/state must represent the same conceptual hierarchy. No hidden duplicate business state inside windows.

## 6. Core interaction transitions

```text
Dashboard / Page
   ↓ filter
Filtered State
   ↓ select
Table / Chart State
   ↓ drill-down
Detail Window
   ↓ evidence
Evidence Window
   ↓ related object
Related Detail
   ↓ back
Previous Context
```

```text
Chart ↔ Table ↔ Detail ↔ Evidence
          │
          ├── Compare
          ├── Filter
          ├── Timeline
          └── Export
```

Context such as time range, filters, selected dimensions and metric remains stable across transitions unless explicitly changed.

## 7. Data table visual grammar

```text
┌──────────────────────────────────────────────────────────────┐
│ TITLE / CONTEXT                         TIME / STATUS         │
├──────────────────────────────────────────────────────────────┤
│ FILTERS │ SEARCH │ SORT │ VIEW │ EXPORT                     │
├──────────────────────────────────────────────────────────────┤
│ □ │ ENTITY │ METRIC │ TREND │ STATUS │ IMPACT │ ACTION     │
├──────────────────────────────────────────────────────────────┤
│ □ │ ...    │ ...    │ ...   │ ...    │ ...    │ →          │
│ □ │ ...    │ ...    │ ...   │ ...    │ ...    │ →          │
├──────────────────────────────────────────────────────────────┤
│ SUMMARY / PAGINATION / DATA QUALITY / SOURCE                 │
└──────────────────────────────────────────────────────────────┘
```

The table is the authoritative numerical reading surface. Dynamic behavior may include sort, filter, selection, column visibility, density, pagination/virtualization, drill-down and evidence actions.

## 8. Dashboard visual grammar

```text
┌──────────────────────────────────────────────────────────────┐
│ PAGE CONTEXT                         TIME RANGE / REFRESH    │
├────────────┬────────────┬────────────┬──────────────────────┤
│ KPI / 01    │ KPI / 02   │ KPI / 03   │ KPI / 04             │
├────────────┴────────────┴────────────┴──────────────────────┤
│ PRIMARY TREND / DECISION VISUAL                              │
├──────────────────────────────┬───────────────────────────────┤
│ EVENT / RISK / DISTRIBUTION  │ TOP CHANGES / ALERTS          │
├──────────────────────────────┴───────────────────────────────┤
│ DETAIL TABLE / EVIDENCE / NEXT ACTION                        │
└──────────────────────────────────────────────────────────────┘
```

The dashboard is not a decorative wall of charts. Visual hierarchy follows decision priority.

## 9. CTH monitoring relationship

```text
Note
 ↓
Topic
 ↓
Event
 ├── Sentiment
 ├── Risk
 └── Impact
      ↓
KOS / KOC / UGC
      ↓
Content / Propagation
      ↓
Decision / Recommendation
```

## 10. KOS / KOC / UGC experience

Shared framework; domain-specific views.

```text
Identity → Content → Relevance → Engagement → Influence
   ↓          ↓          ↓            ↓           ↓
Quality → Risk → Lifecycle → Attribution → Recommendation
```

Do not create three disconnected data/visualization engines when shared capabilities can be reused.

## 11. Content production experience

```text
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

Templates are domain configurations over canonical data, not isolated hard-coded pages.

## 12. Podcast experience

Podcast is complete but attached to the platform:

```text
Podcast Home
 ↓
Idea Vault
 ├── Daily
 ├── Weekly
 └── Monthly
 ↓
Research / Knowledge
 ↓
Topic / Guest
 ↓
Episode
 ├── Outline
 ├── Discussion Route
 ├── Script
 └── Recording / Review
 ↓
Distribution
 ↓
Analytics
 ↓
Learning / Knowledge Base
```

It shares platform infrastructure but keeps Podcast-specific business logic.

## 13. Report / export experience

```text
Canonical Dataset
 ↓
Report Adapter
 ↓
Template
 ↓
Rendered Report
 ↓
Export
```

Core families: daily / weekly / monthly / quarterly / yearly / special event / sentiment / risk / KOS / KOC / UGC / propagation / content / Podcast.

## 14. Dynamic + realtime principles

- Every dynamic element has a defined state source.
- Realtime refresh must update canonical/view state rather than mutate individual UI numbers.
- Trend charts use the same metric/time-window contract as tables.
- Loading, stale, partial, empty and error states are explicit.
- Motion communicates state/change; it does not decorate noise.
- User interaction can move between multiple representations without losing analytical context.

## 15. Visual design direction

The visual language is intentionally not locked to the current legacy appearance. Final visual direction is derived from the information architecture and the user's accumulated design references, emphasizing:
- strong hierarchy
- analytical clarity
- sophisticated density
- deliberate whitespace
- typography-led hierarchy
- restrained visual noise
- evidence visibility
- dynamic state communication
- responsive composition
- accessibility

No visual decision may alter functional behavior.

## 16. Function / code freeze

The following are protected during visual-system construction:
- existing defined functions
- business workflows
- collection behavior
- authoritative filtering
- API contracts
- data semantics
- stable production logic
- established report/content functions

Architecture refactoring is permitted only when behavior is demonstrably preserved. Prefer adapter, facade, composition, extraction and routing-layer changes over rewriting stable domain logic.

## 17. Architecture optimization without functional change

```text
KEEP existing capability
        ↓
Map dependency
        ↓
Extract shared boundary
        ↓
Introduce adapter / interface
        ↓
Preserve existing implementation
        ↓
Regression
        ↓
Only then simplify / consolidate
```

## 18. Final visual drawing gate

The visual drawing stage may begin only when the following are represented in one coherent system map:
- parent/child architecture
- module ownership
- page hierarchy
- window hierarchy
- route/context transitions
- universal data chain
- table-only path
- table-to-visual path
- dynamic/realtime behavior
- CTH/KOS/KOC/UGC/Podcast domains
- report/export chain
- legacy cleanup boundaries
- function/code freeze

## 19. Non-negotiable invariants

1. Function does not change because architecture changes.
2. Stable code is not rewritten for visual reasons.
3. Canonical data is calculated once.
4. Table remains numerical truth.
5. Visualizations derive from canonical data.
6. Route/window/context remain coherent.
7. CTH is first implementation/validation; ZBP is eventual parent.
8. Podcast remains a complete attached system.
9. KOS/KOC/UGC share platform primitives while preserving domain semantics.
10. Obsolete active rules/files are removed after safe migration and regression.
11. Research informs decisions but does not directly mutate production truth.
12. Final visual design cannot introduce hidden functional changes.

## 20. Status

This is the master pre-design system-wide blueprint. It is the direct source for the next visual system map / final UI design. Fragmented B03/B04 pre-visual instructions are superseded where conflicting.
