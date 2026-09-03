# FINAL SYSTEM PANORAMA — VISUAL SPEC / 2026-09-04

Status: READY FOR VISUAL DESIGN

## 1. Non-negotiable governance
- Existing confirmed functions are FROZEN. Do not remove, rename semantically, weaken, or change their business behavior.
- Existing stable production code is not to be rewritten for visual reasons.
- Architecture, information hierarchy, routing/context organization, component composition and presentation may be optimized only when behavior and data semantics remain equivalent and the change is demonstrably better.
- Any suspected functional change is BLOCKED pending human confirmation.
- Feature labels may be English internally for implementation reference; user-facing language follows the product language system.

## 2. System map

```text
                                   ZBP
                              PARENT SYSTEM
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
         CTH                 Shared Platform               Podcast
     CHILD SYSTEM              Capabilities             ATTACHED SYSTEM
          │                         │                         │
          │                         ├─ Data Truth             ├─ Idea Vault
          │                         ├─ AI / Knowledge         ├─ Research
          │                         ├─ Coding Agent           ├─ Guests
          │                         ├─ UI / Design            ├─ Episodes
          │                         ├─ Reports                ├─ Production
          │                         └─ Export                 ├─ Distribution
          │                                                   └─ Analytics
          │
          ├─ Collection
          ├─ Notes / Topics
          ├─ Events / Risk
          ├─ Sentiment
          ├─ KOS / KOC / UGC
          ├─ Content Production
          ├─ Reports / Export
          └─ Runtime / Health / Recovery
```

## 3. Universal data pipeline

```text
Collector / File / Table / PPT / PDF / Image / Video / Audio / API / Text / Manual
                                      │
                                      ▼
                               Universal Ingestion
                                      │
                                      ▼
                                Raw / Evidence
                                      │
                              Parse / Validate
                                      │
                                   Normalize
                                      │
                              Function / Formula
                                      │
                                      ▼
                         CANONICAL DATASET / TABLE
                                      │
                           Metric / Time Window
                                      │
                                  View Model
                                      │
                            Visualization Spec
                                      │
                ┌─────────────────────┼─────────────────────┐
                ▼                     ▼                     ▼
             Dynamic Table          Charts              Timeline/Graph
                │                     │                     │
                └─────────────────────┼─────────────────────┘
                                      ▼
                                  UI / Windows
                                      │
                              Report / Export
```

## 4. Data authority rule
Canonical Dataset/Table is the numerical truth surface. A table-only workflow stops at the table. A visualization workflow derives from that same canonical output. UI, chart, report and export never independently recalculate a business metric.

## 5. UI panorama

```text
SHELL
│
├─ Global navigation
├─ Workspace / context
├─ Search / command
├─ Notifications
└─ System health
    │
    ▼
PRODUCT / DOMAIN
    │
    ▼
MODULE
    │
    ▼
PAGE
    │
    ├─ Section
    │   ├─ Metric / status
    │   ├─ Filter / time
    │   ├─ Table / visualization
    │   └─ Insight / action
    │
    └─ Component
         │
         ▼
     WINDOW / ACTION
```

## 6. Window graph

```text
Page
 ↓ trigger
Action
 ↓
Window State
 ↓
Target
 ↓
Detail / Evidence / Related Object
 ↓
Child Context
 ↓
Return to Parent Context
```

Window classes: Modal, Drawer, Detail, Filter, Comparison, Evidence, Confirmation, Command/Search, Notification.

Every window must retain parent context, target identity, active filters/time window where applicable, and return context.

## 7. Dynamic interaction model

`Filter → Recompute canonical query/view → Update table → Update linked visuals → Preserve context`

`Chart point/row → Detail window → Evidence → Related event/note/person/content → Return`

`Select → Compare → Comparison window → Evidence → Export`

No interaction may silently fork business truth.

## 8. KOS / KOC / UGC / event relationship

```text
NOTE
 ↓
TOPIC
 ↓
EVENT
 ↓
SENTIMENT / RISK
 ↓
IMPACT
 ↓
KOS / KOC / UGC
 ↓
CONTENT / PROPAGATION
 ↓
DECISION
```

## 9. Content production

```text
Data → Insight → Topic → Strategy → Title/Copy/Cover/Script
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

## 10. Report architecture

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

Families: daily, weekly, monthly, quarterly, yearly, special/event, sentiment, risk, KOS/KOC/UGC, propagation, content, Podcast.

Standard information hierarchy: Executive Summary → Key Findings → Event/Issue → Impact → Risk → Evidence → Trend → Recommendation → Appendix/Data.

## 11. Internal Coding / Multi-AI system

```text
User / System Task
        ↓
Internal Coding Workspace
        ↓
AI Orchestrator
   ┌────┼────┐
   ▼    ▼    ▼
External  External  Local
Model A   Model B   AI
   │         │        │
   └────┬────┴────────┘
        ▼
   Plan / Review
        ↓
   Local Sandbox
        ↓
 Write / Execute / Test
        ↓
 Diff + Audit
        ↓
 Human Gate
        ↓
 Git Commit
        ↓
 Learning Asset
        ↺
```

External models are collaborators/validators. Code ownership and execution workspace remain inside the system. Over time, validated local capability may replace external execution assistance. External providers can remain as optional second-opinion/benchmark services.

## 12. Visual design requirements

The final visual system must be information-first, dynamic, composable and context-preserving. It is not constrained to the legacy visual style. Visual references inform hierarchy, density, typography, motion and composition but never override functional hierarchy.

Required states: loading, empty, error, partial, stale, live/updating, selected, filtered, comparison, permission/blocked, success.

Motion is semantic: it communicates data change, navigation, expansion, processing or system state; it is not decoration.

## 13. Final drawing set

Produce, in this order:
1. System Panorama
2. Parent/Child Capability Map (ZBP/CTH/Podcast)
3. Universal Data Lineage Map
4. UI Hierarchy Map
5. Window + Route Context Map
6. Dynamic Interaction Map
7. KOS/KOC/UGC + Event Relationship Map
8. Content Production Map
9. Report/Export Map
10. Internal Coding + Multi-AI Control Map
11. Representative Page Wireframes
12. Representative Window States
13. Dynamic Table / Visualization Patterns
14. Responsive/State Variants

## 14. Visual acceptance gate
Before a visual is accepted, verify against the frozen function inventory. The drawing is an expression of the existing system, not a redesign of its business capability.

## 15. Methodology inheritance
This spec is a visual execution of the Construction Methodology. Future products/modules must reuse the method and generate their own source-backed mapping before drawing. Old rules that conflict are superseded; after dependency/reference verification they are deleted or moved to LEGACY/ARCHIVE.
