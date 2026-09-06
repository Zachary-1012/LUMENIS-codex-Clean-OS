# Canonical AI Execution Baseline V1 — ZBC × OSAI

Status: ACTIVE / CANONICAL
Effective: 2026-09-04
Scope: all AI-assisted research, engineering, UI/UX, Runtime, data, testing and release work coordinated with Z-Brand-Core.

## 0. Why this file exists

This file consolidates overlapping execution rules. It is the single active execution baseline. Older execution documents are historical inputs and must not be treated as parallel authorities.

The problem this solves is rule overload: multiple documents saying "highest priority", "permanent", "must never downgrade", "10x", "autonomous", or similar can create a flat and contradictory instruction space. There is only ONE top-level authority here; lower rules inherit from it.

## 1. Authority and precedence

When rules conflict, use this order:
1. Safety / security / legal / platform restrictions.
2. Product Truth, data authority and protected production rules.
3. This Canonical AI Execution Baseline.
4. Current approved Product / Architecture / Data / Runtime / UI Contracts.
5. Task-specific acceptance criteria.
6. Research recommendations and optimization ideas.
7. Historical / Legacy documents.

A lower level may refine a higher level but may not silently weaken it. If two active documents conflict, STOP, identify the conflict, trace evidence, and create one revised decision. Do not obey both simultaneously.

## 2. Priority model

Do NOT label every rule P0 or "highest priority".

Operational priority is:
P0 = safety, security, data integrity, production-blocking defects, protected truth, release blockers.
P1 = required product functionality, correctness, runtime integrity, UI/UX integrity and regression blockers.
P2 = performance, maintainability, research adoption and non-blocking optimization.
P3 = exploratory/future ideas.

"Permanent" means retained as a principle until explicitly superseded by a recorded decision; it does not mean every sentence is an immutable implementation detail.

## 3. Core operating principle

READ → AUDIT → RESEARCH/RECALL → CONTRACT → BOUNDARY → IMPLEMENT → TEST → RUN → VERIFY → REGRESSION → EVIDENCE → COMMIT → REPORT → NEXT.

Never code directly from an unstructured natural-language request when a contract or acceptance criterion is required.

## 4. No guessing / no false completion

If a requirement, dependency, data source, design rule, runtime behavior or ownership is unknown:
UNKNOWN → STOP → TRACE → RESOLVE → CONTINUE.

Do not invent requirements, suppress failures, hide warnings, create fake success, use mock data as production, or call an unverified implementation DONE.

## 5. Source-of-truth boundaries

ZBC owns Production Truth: production code, production data, business rules, runtime, collectors, reports, tests and release.
OSAI owns Research & Intelligence: research, evidence, knowledge, evaluation, architecture research, contracts and implementation specifications.

OSAI research does not directly become production truth. Promotion follows:
Research → Evidence → Contract → Implementation Specification → Production Implementation → Test → Evidence → Audit → Release.

## 6. Search/reuse before creation

Before creating or duplicating anything:
SEARCH → EXISTING IMPLEMENTATION → CONTRACT → CALLERS/DEPENDENCIES → TESTS → REUSE/ADAPT.

Create new implementation only when existing capability cannot safely satisfy the requirement. Document the reason.

## 7. UI/UX canonical shell

Default web product structure:
LEFT NAVIGATION → CENTRAL WORKSPACE.

No permanent right-side context panel by default.

The web page is an integrated fixed-viewport workspace, not an endless full-page scroll. If information does not fit, use explicit hierarchy: next-level page, focused workspace, sheet, dialog, popover or a bounded internal scroll region owned by that component.

Home is an AI workspace, not a feature warehouse. Show only high-value/core/primary information. Secondary/deep information returns to the relevant feature page. Card count is value-driven; there is no 20-card requirement.

Visual language: minimal, functional, precise, information-first. No cute oversized decoration, giant typography, decorative logo/icon dominance, excessive glass or meaningless animation.

Glass is functional for navigation/control/focus/layer/state/interaction, not a full-page skin. Motion must explain state, navigation, feedback or relationship.

## 8. UI render integrity

Every UI region must have explicit State Owner, Data Owner, Layout Owner, DOM Owner, Renderer Owner and Event Owner.

One UI region has one authoritative renderer. Do not solve structural conflicts with arbitrary z-index, !important, absolute positioning or overflow hiding.

For clipping/overlap/disappearance, trace:
viewport → container → layout → stacking context → mount/unmount → state → async update → renderer → DOM → paint.

Root Cause → Evidence → Minimal Fix → Regression is mandatory.

## 9. Data/runtime integrity

Production data path:
External Data → Evidence → Validate → Normalize → Canonical Data → Function → Metric → Truth Surface → View Model → Visualization → UI.

UI does not independently recompute business truth.

Live capability lifecycle:
REGISTERED → SYNCED → LOADED → READY → RUNNING → UPDATED → VERIFIED.

A GitHub file existing is not evidence that runtime loaded or executed it.

## 10. Lifecycle and traceability

Every material task must be traceable:
Research-ID → Decision-ID → Requirement-ID → Task-ID → File/Function → Commit-SHA → Test-ID → Evidence → Result.

Feature lifecycle:
DISCOVERED → RESEARCHED → DECIDED → SPECIFIED → IMPLEMENTED → LOADED → RUNNING → TESTED → VERIFIED → DELIVERED → MONITORED → IMPROVED.

Never delete history to hide a revision. Supersede with evidence and a decision record.

## 11. Change boundary

Before modification declare:
Allowed Files / Components / Routes / State / Runtime / Tokens / Forbidden Areas.

Cross-boundary changes require impact analysis and an explicit decision. Never silently change Global Shell, shared contracts, canonical data or another feature.

## 12. Verification and Definition of Done

Required as applicable:
- source/static inspection;
- targeted unit/integration tests;
- E2E/UI test;
- failure-path test;
- data accuracy check;
- runtime/live-update check;
- visual verification;
- regression check;
- security/compliance check;
- evidence capture;
- scoped diff review;
- commit/push.

DONE means the affected requirement is implemented, connected, tested, verified and traceable. "Code exists" or "page opens" is not DONE.

## 13. Requirements cannot disappear into Git

Every user requirement must have a Requirement ID and status:
REGISTERED / IN_PROGRESS / IMPLEMENTED / VERIFIED / DELIVERED / BLOCKED / SUPERSEDED.

A requirement may not become invisible merely because a document was committed. Runtime adoption must be separately verified.

## 14. Research adoption

External technology, Apple ecosystem research, open-source models, UI patterns, rendering techniques and cases are inputs only. Record source, finding, relevance, license/rights boundary where applicable, decision, adaptation and verification.

Adoption states:
ADOPT / ADAPT / DEFER / REJECT.

Never copy third-party code or design assets without provenance and rights review.

## 15. Performance / 10x

10x is an efficiency objective, not a quality tier and not a permanent priority override. Optimize discovery, context, reuse, automation, verification and rework. Never reduce tests, evidence, safety, correctness or release gates for speed.

## 16. Error policy

P0: stop propagation and resolve before release.
P1: fix before affected feature delivery.
P2: schedule without blocking unrelated verified delivery.
P3: research/future.

No known defect may be disguised as success.

## 17. Legacy and document cleanup

Only one active execution baseline exists: this file.

Historical documents may remain temporarily for provenance, but must be labeled LEGACY/SUPERSEDED and must not be used as current instructions. Delete an old document only after reference/dependency/runtime/documentation checks prove it is not required. Never delete by filename alone.

## 18. Required execution report

TASK / BASELINE / RESEARCH / DECISION / REQUIREMENTS / CHANGED FILES / FUNCTIONS / RUNTIME / UI-UX / DATA / TEST / VISUAL / REGRESSION / LIFECYCLE TRACE / EVIDENCE / COMMIT / COVERAGE / REMAINING / RISKS / STATUS.

## 19. Final rule

The system is not optimized by accumulating stronger-sounding commands. It is optimized by one clear authority, explicit contracts, bounded changes, deterministic ownership, lifecycle state, automated verification and traceable evidence.

When a rule is obsolete, remove it from active authority rather than adding another exception.
