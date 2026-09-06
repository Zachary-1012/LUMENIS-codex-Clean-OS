# KOS UI / Interaction / Hierarchy Contract v1

## 1. Scope
Applies to the KOS product UI and establishes the reference model for future KOS implementation. It must also conform to the global capability and style convergence gate.

## 2. Product hierarchy
KOS is organized as:
1. Collection & Quality Gate
2. Identity / Entity Ownership Gate
3. KOS Identification & Scoring
4. KOS Asset Management
5. Operations Center
6. Growth / Paid Amplification
7. Analytics & Decision
8. Reporting & Dynamic Visualization

The primary user journey is: collect -> clean/dedupe -> entity ownership -> KOS identity -> evidence -> score/tier -> account asset -> operation -> outcome -> feedback -> report.

## 3. Account-first interaction model
The KOS account is the core business object. The list view is for scanning and comparison; the detail view is the 360-degree source of truth; actions are contextual to the account state.

Account detail must surface, in priority order: identity, ownership evidence, KOS tier/score, performance, content profile, comment intelligence, lifecycle/risk, contact/lead information, cooperation history, current opportunities, AI recommendations, Evidence.

## 4. Adaptive hierarchy by product function
Do not force every module into the same page hierarchy. Shared design language is global; information hierarchy adapts to task intent:
- Monitoring: signal -> risk -> evidence -> action.
- KOS operations: account -> relationship -> action -> outcome.
- Analytics: metric -> comparison -> drill-down -> evidence.
- Reporting: conclusion -> visualization -> evidence -> export.
- Configuration: scope -> rule -> validation -> publish/audit.

## 5. Visual system
Use the global design system and tokens. No local competing visual language. Shared components should be reused for navigation, cards, tables, filters, forms, status, charts, loading, empty, error, and confirmation states.

The visual goal is high information density without clutter: clear primary/secondary hierarchy, consistent spacing, restrained decoration, predictable interactions, responsive layouts, and state visibility.

## 6. Account table reference fields
The KOS account table should support: KOS_ID, tier, account/nickname, platform, UID, profile URL, entity ownership, ownership type, KOS type, ownership confidence, followers, recent posting volume, average likes/comments/saves/shares, engagement, growth, content match, expertise, continuity, reach, comment handling, paid amplification potential, lifecycle, risk, content tags, contact fields, MCN/company, cooperation direction, budget/quote, lead completeness, verification/contact timestamps, cooperation status, next action, AI recommendation, Evidence ID, data freshness, asset health.

## 7. State-driven actions
Actions must be generated from the current account state. Examples: incomplete lead -> complete lead; qualified/uncontacted -> generate outreach; contacted/no reply -> follow-up; published -> collect performance; strong organic performance -> paid-amplification candidate; low confidence/anomaly -> quarantine/review.

Never present an action as completed merely because content was generated. Distinguish generated, queued, sent, delivered, replied, accepted, completed, and failed states.

## 8. Ownership safety
Merchant KOS, brand KOS, partner KOS, target-entity KOS, independent KOL/KOC, UGC, media, official, and unknown must remain visually and semantically distinguishable. Mentioning a target entity is not proof of KOS ownership.

## 9. Reporting interaction
Reports should support overview -> segment -> account -> content -> evidence drill-down. Dynamic HTML visualizations must derive from the same underlying data and Evidence as exports; no decorative metric may be fabricated.

## 10. Acceptance gate
A KOS UI change is not accepted until: hierarchy matches the task model; global tokens/components are reused; account states are explicit; ownership distinctions remain visible; critical actions are contextual; responsive behavior is defined; accessibility/error/empty/loading states exist; and the implementation passes regression/runtime verification.