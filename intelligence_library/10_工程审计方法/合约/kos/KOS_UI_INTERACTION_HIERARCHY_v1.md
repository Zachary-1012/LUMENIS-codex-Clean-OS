# KOS UI / Interaction / Hierarchy Contract v1

## Purpose
Define the KOS reference information architecture while requiring global visual consistency and function-specific adaptive hierarchy.

## Reference hierarchy
Collection & Quality Gate -> Entity Ownership Gate -> KOS Identification & Scoring -> Account Asset -> Operations -> Growth/Paid Amplification -> Analytics/Decision -> Reporting/Dynamic Visualization.

## Core interaction
Collect -> clean/dedupe -> entity ownership -> KOS identity -> Evidence -> score/tier -> account asset -> operation -> outcome -> feedback -> report.

## Account-first model
The account is the core business object. Lists support scan/compare; detail is the 360-degree source of truth; actions are contextual to account state. Detail priority: identity, ownership evidence, tier/score, performance, content profile, comment intelligence, lifecycle/risk, lead/contact, cooperation history, opportunities, AI recommendation, Evidence.

## Adaptive hierarchy
Shared design language must remain global, but information hierarchy adapts to product function:
- Monitoring: signal -> risk -> evidence -> action.
- KOS operations: account -> relationship -> action -> outcome.
- Analytics: metric -> comparison -> drill-down -> evidence.
- Reporting: conclusion -> visualization -> evidence -> export.
- Configuration: scope -> rule -> validation -> publish/audit.

## Global visual convergence
Reuse the authoritative global Design System and components. No local competing colors, typography, spacing, radius, motion, cards, tables, forms, charts, or state patterns. High information density must remain visually legible and state visibility must be explicit.

## State-driven action contract
Actions derive from account state. Generated, queued, sent, delivered, replied, accepted, completed, and failed are distinct states. Generated content must never be represented as sent/completed.

## Ownership safety
Keep target-entity KOS, brand KOS, merchant KOS, partner KOS, independent KOL/KOC, UGC, media, official, and unknown visually and semantically distinct. Entity mention is not ownership evidence.

## Reporting
Support overview -> segment -> account -> content -> Evidence drill-down. Dynamic HTML and export outputs must use the same underlying data and Evidence. No fabricated metrics.

## Verification
Any implementation must pass hierarchy, global component reuse, responsive behavior, loading/empty/error states, ownership visibility, contextual action, accessibility, regression, runtime, and Evidence checks before release.