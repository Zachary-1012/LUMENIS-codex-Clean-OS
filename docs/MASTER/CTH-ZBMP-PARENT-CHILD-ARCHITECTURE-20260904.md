# CTH × ZBMP Parent-Child Architecture Lock

Date: 2026-09-04
Status: BUILD BASELINE

## 1. Non-negotiable relationship

CTH and ZBMP remain a parent-child system relationship. The B03 architecture reorganization MUST NOT flatten them into two unrelated products or duplicate their shared foundations.

- Parent: CTH — platform-level intelligence / operating foundation.
- Child: ZBMP — specialized brand-monitoring / brand-propagation application layer.
- ZBMP consumes governed capabilities from CTH while retaining its domain-specific rules, data views, workflows and production responsibilities.
- Shared infrastructure must be reusable; domain behavior must remain isolated.

## 2. Architecture

```text
CTH PLATFORM / PARENT
│
├── Identity / Access
├── Runtime / Health / Recovery
├── Universal Ingestion
├── Evidence / Asset Layer
├── Canonical Data Contracts
├── Metric / Formula Registry
├── Function Registry
├── Time Window Registry
├── UI Shell / Window / Route Contracts
├── Visualization Contracts
├── AI / Agent Governance
├── Knowledge / Evidence Graph
└── Cross-product orchestration
          │
          ▼
ZBMP DOMAIN CHILD
│
├── Brand Subject Rules
├── Xiaohongshu / platform collection
├── Notes / Topics / Mentions
├── Sentiment / Risk / Events
├── KOS / KOC / UGC
├── Brand propagation intelligence
├── Content production
├── Brand reports
└── Brand-specific operational workflows
```

## 3. Dependency rule

Allowed:

```text
ZBMP → CTH governed platform contracts
ZBMP → shared CTH services
ZBMP → CTH UI primitives
ZBMP → CTH ingestion / evidence / metric infrastructure
```

Not allowed:

```text
CTH → hard-coded ZBMP business rules
ZBMP → forked copies of CTH canonical services
ZBMP → direct mutation of CTH governance contracts without review
```

## 4. Data rule

External data still follows the canonical chain:

```text
External / Collector / File / Table / PPT / PDF / Image / Video / Audio / Text
        ↓
CTH Universal Ingestion
        ↓
Raw Asset / Evidence
        ↓
Parse → Validate → Normalize
        ↓
Function + Formula
        ↓
Canonical Dataset
        ↓
ZBMP Domain Dataset / View Model
        ↓
Table / Chart / UI / Report / Export
```

If a data item has no meaningful tabular representation, it remains an Asset/Evidence object and MUST NOT be converted into fabricated metrics.

## 5. UI rule

CTH owns the reusable interaction language:

```text
Shell → Workspace → Module → Page → Section → Component → Window
```

ZBMP owns domain-specific pages and workflows underneath that shell.

A ZBMP window must preserve parent context and return context. Cross-module navigation must use registered routes/actions rather than ad-hoc URL jumps.

## 6. Architecture-change gate

Architecture MAY change when research proves a measurable improvement in reliability, correctness, maintainability, performance, security or interaction quality.

Required chain:

```text
Research → Evidence → Candidate → Compatibility → Contract → Implementation → Regression → Audit → Adopt
```

No technology is adopted merely because it is fashionable or used by another project.

## 7. B03/B04 implication

B03 must first establish the parent CTH UI/interaction foundation and then bind ZBMP into it as the child domain application.

B04 visualization must consume Canonical Dataset / Metric contracts and must not create a second calculation layer inside ZBMP pages.

## 8. Migration principle

Do not rewrite stable production capabilities merely to conform visually. Reuse first, adapt second, wrap third, isolate fourth, replace only when the measured benefit justifies it.

## 9. Acceptance criteria

- CTH remains the parent platform.
- ZBMP remains a child domain system.
- No accidental flattening or duplication.
- Shared contracts have one owner.
- ZBMP-specific rules remain domain-owned.
- Data lineage remains traceable.
- UI/window/navigation hierarchy is parent-aware.
- B03 and B04 implementation references this architecture lock.
