# Construction Methodology & Final System Panorama — 2026-09-04

Status: ACTIVE / MASTER CONSTRUCTION STANDARD / PRE-VISUAL → VISUAL EXECUTION

## 0. Non-negotiable product-function freeze

**Existing approved business functions are frozen.** This document does NOT authorize changing, removing, renaming, weakening, or silently altering an approved function.

Architecture may be reorganized only if externally observable behavior, business semantics, data meaning and expected outputs remain compatible.

Code is not to be rewritten for visual modernization. Existing stable code is reused first. Code changes are allowed only for verified bug/security/stability defects, explicit architectural adapters, or unavoidable integration boundaries, and must preserve the approved function contract.

### Change classification
- UI/visual reorganization: ALLOWED
- interaction/window/route organization: ALLOWED if behavior is preserved
- architecture refactor: ALLOWED with compatibility evidence
- shared capability extraction: ALLOWED after validation
- deterministic metric/function change: BLOCKED unless explicitly approved as a functional correction
- business-function addition/removal/change: BLOCKED by this baseline
- stable code rewrite only for style: BLOCKED

## 1. Reusable construction methodology

```text
DISCOVER → FREEZE APPROVED FUNCTION CONTRACTS → MAP SOURCE
→ RESEARCH BETTER PATTERNS → KEEP / CHANGE / ADD / REMOVE
→ REORGANIZE ARCHITECTURE WITHOUT CHANGING FUNCTION
→ DATA TRUTH + LINEAGE → ROUTE / WINDOW / INTERACTION CONTRACTS
→ SEMANTIC COMPONENTS → DYNAMIC TABLE / VISUALIZATION
→ DOMAIN MODULES → REGRESSION → REMOVE OBSOLETE ACTIVE RULES/FILES
→ AUDIT → FINAL VISUAL DESIGN
```

This methodology is the construction baseline for future systems, modules and domains.

## 2. Cumulative knowledge rule

Every future research pass MUST start from and carry forward the cumulative baseline. New research may supersede an old decision only with evidence and an explicit supersession record. Research is reference material, not production authority.

## 3. Parent / child product model

```text
                         ZBP
                  FINAL PARENT SYSTEM
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
       CTH            Shared Capabilities   Podcast
    CHILD DOMAIN          ↑ absorbed         ATTACHED
        │                  │                  │
        └── FIRST IMPLEMENTATION / VALIDATION ┘
                    │
                    ↓
            proven capability
                    ↓
            Capability Contract
                    ↓
               ZBP absorbs
```

CTH is developed first because it is the current implementation/validation environment. This does not change the final parent-child relationship.

## 4. Final system panorama

```text
┌───────────────────────────────────────────────────────────────────────┐
│                         ZBP / PLATFORM SHELL                           │
│ Navigation · Workspace · Search/Command · Health · Notification       │
├───────────────────────────────────────────────────────────────────────┤
│                         BUSINESS DOMAINS                               │
│                                                                       │
│  CTH                          Shared Intelligence        Podcast       │
│  ├─ Collection                ├─ AI/Knowledge           ├─ Research  │
│  ├─ Notes                     ├─ Evidence               ├─ Idea Vault │
│  ├─ Topics                    ├─ Metrics                ├─ Topics     │
│  ├─ Events                    ├─ Reports                ├─ Guests     │
│  ├─ Sentiment                 └─ Learning               ├─ Episodes   │
│  ├─ Risk                                                ├─ Scripts    │
│  ├─ KOS/KOC/UGC                                          ├─ Review    │
│  ├─ Content Production                                   ├─ Publish   │
│  └─ Reports/Export                                       └─ Analytics │
├───────────────────────────────────────────────────────────────────────┤
│                    SHARED DATA / EXPERIENCE CORE                      │
│ Ingestion · Evidence · Canonical Table · Metric · Function · Formula │
│ View Model · VisualizationSpec · Route · Window · Component · Export │
├───────────────────────────────────────────────────────────────────────┤
│                     RUNTIME / GOVERNANCE                              │
│ Health · Recovery · Audit · Permissions · Git · Tests · Release      │
└───────────────────────────────────────────────────────────────────────┘
```

## 5. Universal data construction

```text
Collector / File / Table / PPT / PDF / Word / Image / Video / Audio
API / Text / Manual Input
              ↓
       Universal Ingestion
              ↓
         Raw / Evidence
              ↓
     Parse → Validate → Normalize
              ↓
       Function / Formula
              ↓
     Canonical Dataset / Table
              │
              ├───────────────→ table-only business path
              │
              ↓
     Metric + Time Window + Filters
              ↓
           View Model
              ↓
       VisualizationSpec
              ↓
 Dynamic Table / Chart / Trend / Timeline / Graph / UI
              ↓
        Report / Export
```

**Truth rule: calculate once; present many times.** The table is the numerical truth surface. UI, charts, reports and exports consume canonical outputs and must not independently recalculate business metrics.

## 6. Evidence and lineage

Every computed output should retain source asset/record IDs, schema/version, transformation/function/formula versions, metric ID, time-window/filter state, quality status, calculation timestamp and evidence references. Evidence-only material must remain evidence and must never be fabricated into numeric facts.

## 7. UI / information architecture

```text
APP SHELL → WORKSPACE → PRODUCT / DOMAIN → MODULE → PAGE
→ SECTION → COMPONENT → WINDOW / ACTION
```

Function names are references for hierarchy only. They are not permission to change existing business functionality.

## 8. Window / route / interaction model

```text
Current Page → User Action → Window State → Target Object
→ Detail / Evidence / Related Action → Return Context
```

Every window declares parent context, trigger, target, child state, data/evidence source, loading/empty/error state, return context and route/state mutation if any. Transitions preserve active filter, metric and time-window context unless the user changes them.

## 9. Component methodology

Use semantic, composable primitives instead of a single universal monolith: MetricCard, DataTable, ChartFrame, FilterBar, TimeRange, StatusBadge, EvidenceLink, DetailDrawer, DetailModal, ConfirmDialog, Timeline, ComparisonView, Command/Search, Notification, Health, ExportAction, Loading/Empty/Error. Components cannot redefine business truth.

## 10. Table system

```text
Canonical Dataset → Table Definition → State
  ├ filter ├ sort ├ pagination ├ selection ├ visibility ├ density └ row action
→ Detail / Evidence / Export
```

A table can terminate the pipeline when no visualization is needed.

## 11. Visualization system

```text
Canonical Table → VisualizationSpec
  ├ dataset ├ metric ├ dimension ├ time window ├ filter
  ├ aggregation ├ formatter └ interaction
→ Trend / Bar / Distribution / Timeline / Event Graph
  / Heatmap / Funnel-Lifecycle / Comparison Matrix
```

No visual is created merely for decoration. Each visual must answer an analytical or operational question.

## 12. CTH capability preservation

The approved CTH capability set remains intact: collection, notes, topics, sentiment, events, risk, KOS, KOC, UGC, content production, reports, export, runtime, health, recovery and associated existing functions. This baseline reorganizes architecture and presentation only; it does not redefine what these functions do.

## 13. Podcast system

Podcast is a complete attached business system inside the final parent platform, not a decorative page:

```text
Podcast → Idea Vault(Daily/Weekly/Monthly) → Knowledge Base → Research
→ Topic / Hot Topic → Guest → Episode Planning → Discussion Route
→ Script / Content → Recording / Review → Distribution → Analytics → Reports / Learning
```

It uses shared platform infrastructure while retaining podcast-specific business logic.

## 14. KOS / KOC / UGC / content

```text
Canonical Data → Note / Topic / Event → KOS/KOC/UGC relationship
→ Insight → Content Strategy → Title / Copy / Cover / Script
→ Comment / Reply → Publish → Monitor → Review / Learning
```

Templates are execution specifications; they do not change underlying data truth.

## 15. Reports

```text
Canonical Data → Report Adapter → Template → Rendered Report → Export
```

Report families include daily, weekly, monthly, quarterly, yearly, special/event, sentiment, risk, KOS/KOC/UGC, propagation, content and Podcast reports.

## 16. Internal coding / development capability — new direction

The existing coding capability should evolve toward **internal code authoring**, while external model platforms are model/execution providers rather than the location of source truth.

```text
User / Agent Task → Internal Coding Workspace → Repository Context / Code Map
→ Planning / Patch Proposal → Sandboxed Execution → Tests / Lint / Build
→ Diff Review → Human Approval Gate → Git Commit / PR → Learning Asset
```

### Source-of-truth rule
Code MUST be written and stored in the user's own repository/workspace. An external model platform may provide inference, suggestions or execution assistance, but it must not become the canonical location of source code.

### Learning loop
Accepted coding tasks should retain task intent, relevant repository context, proposed patch, tests, human corrections, final accepted diff, failure/retry information, model/provider/version and reusable engineering lessons, subject to privacy/security policy.

### Safety boundary
The internal coding agent must use sandboxed execution and explicit repository permissions. It must not silently deploy, rewrite protected functionality, expose secrets, or bypass human approval for high-impact changes.

### Research reference
Open-source coding-agent systems such as OpenHands provide SDK/CLI/local GUI patterns for repository inspection, code modification and command execution; Aider demonstrates repository mapping, Git integration and model-provider flexibility. These are architectural references only, not automatic dependencies. citeturn0search0turn0search16

## 17. Learning without changing functionality

```text
Repository + Architecture Baseline + Function Contracts + Tests
+ Accepted Diffs + Human Decisions + Research Evidence
→ Engineering Knowledge → Better Future Suggestions
```

The learning system must not silently mutate production behavior.

## 18. Obsolete rule/file disposal

```text
Candidate obsolete → Reference Scan → Dependency Scan
→ Consumer Migration → Regression → DELETE → Repository Verification
```

Historical evidence may remain only as `LEGACY` or `ARCHIVE`, and must not be active.

## 19. Final visual design gate

Only after architecture, data lineage, function preservation, route/window contracts, component inventory, visualization contracts, domain mapping and legacy cleanup are accepted should the final visual system be drawn.

The visual design must express information hierarchy, functional ownership, data lineage, interaction state, window relationships, dynamic changes, evidence visibility, operational priority, trend/comparison and responsive behavior.

## 20. Construction acceptance criteria

1. Every approved function remains available and behavior-compatible.
2. No UI component owns duplicate business truth.
3. Table/chart/report/export values agree.
4. Route/window transitions preserve context.
5. Data lineage is inspectable.
6. CTH remains stable.
7. CTH-first development remains intact.
8. ZBP absorption boundaries are explicit.
9. Podcast remains a complete attached domain.
10. KOS/KOC/UGC and content/report templates use shared contracts.
11. Obsolete active rules/files are removed after safe migration.
12. Internal coding can write to the repository without making an external model platform the source of truth.
13. High-impact code changes retain human approval and Git traceability.

## 21. Master rule

**Architecture can evolve. Function cannot silently change. Code is preserved by default. Research improves the construction method. The repository remains the source of truth. Data is calculated once and presented many ways. Every visual and window is subordinate to the information architecture. Proven CTH capabilities are developed first and later absorbed into ZBP only through evidence-backed contracts.**
