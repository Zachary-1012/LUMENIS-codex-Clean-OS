# Unified UI/UX Information Architecture V1

Status: CANONICAL / P0
Effective: 2026-09-04
Scope: Podcast, KOS, 舆情, Campaign, Research, AI, Evaluation, Operations

## 1. Purpose

This document is the canonical presentation and interaction baseline for the whole system. It standardizes information architecture, progressive disclosure, drill-down, tables, charts, Runtime, Evidence, Action, Evaluation and Learning without replacing business capabilities.

## 2. Non-negotiable compatibility rule

Existing stable capabilities, APIs, data, workflows and governance remain protected. UI/UX work MUST be additive or migration-safe. Before replacing an existing UI/function, map the existing capability and preserve equivalent behavior. No redesign may silently delete, rename away, orphan, or disable a previously working capability.

Replacement lifecycle:
existing asset -> audit -> map -> reuse -> adapt -> migrate -> verify -> retire only with explicit record.

## 3. Canonical hierarchy

Default: Workspace -> Module -> Object/Detail -> Deep Detail/Action.

Use 2 levels for simple tasks, 3 for standard tasks, 4 only for genuinely complex workflows. Use Drawer/Sheet/Tab/Popover/Inline Expand instead of adding navigation levels when the context can remain in place.

## 4. Canonical interaction chain

DATA -> OBJECT -> CONTEXT -> ANALYSIS -> EVIDENCE -> DECISION -> ACTION -> RESULT -> EVALUATION -> LEARNING -> KNOWLEDGE.

Every module does not need every stage visibly rendered; stages are dynamically exposed according to the task.

## 5. Canonical page skeleton

Global Shell -> Module Overview -> Core Metrics -> Trend -> Key Objects -> Key Events -> Evidence/Alerts -> Action.

Tables use Search / Filter / Sort / Group / Columns / Export where applicable. Row selection should prefer a detail Drawer before a full-page transition.

## 6. Canonical visual grammar

Line = time trend; Bar = comparison/ranking; Stacked = composition; Heatmap = concentration; Scatter/Graph = relationship; Timeline = event sequence; Runtime Timeline = execution state.

Visual priority: information hierarchy -> whitespace -> typography -> data visualization -> state -> interaction feedback -> decoration.

Decoration MUST NOT compete with information.

## 7. Runtime

Task -> Start -> Process -> Heartbeat -> Result -> Callback -> Verify -> Recovery/Complete.
Runtime must expose state, last success, elapsed time, retry/recovery state where relevant. Failures must not become silent states.

## 8. Evidence

Decision -> Source -> Time -> Original Data -> AI Analysis/Confidence where applicable -> Human Review -> Final Decision.
Claims and consequential decisions should remain traceable to evidence.

## 9. Action

Actions should be contextual and task-oriented: View, Analyze, Verify, Compare, Monitor, Create, Export, Execute, or module-specific equivalents. Action results feed back into Result/Evaluation where applicable.

## 10. Module adaptation

Podcast: Overview / Research / Episodes / Performance / Learning.
KOS: Overview / People / Content / Monitoring / Performance / Learning.
舆情: Overview / Signals / Events / Monitoring / Analysis / Reports.
Campaign: Overview / Events / Content / People / Audience / Timeline / Performance.
Research: Overview / Topics / Cases / People / Knowledge.
AI: Overview / Models / Tasks / Evaluation.
Evaluation: Task / Input / Model / Output / Score / Human Review / Final Result / Learning.
Operations: Runtime / Monitoring / Audit / Tasks / Deployment / System Health.

These are module-adapted views of the same canonical interaction model, not independent UI systems.

## 11. Progressive disclosure

Default view shows only what is necessary for the current decision. Detail, evidence, history, related objects and advanced actions appear on demand. Preserve context when drilling down and restore search/filter/sort/scroll state when returning.

## 12. Reuse-first engineering

For every new UI capability: search existing component/contract/data source first; reuse if suitable; adapt if close; build only if absent or incompatible. Do not duplicate equivalent components across modules.

## 13. Replacement gate

A legacy UI may be replaced only after:
1. capability inventory;
2. dependency/API/data mapping;
3. equivalent or improved interaction path implemented;
4. regression validation;
5. runtime verification;
6. explicit retirement record.

## 14. Twin-repository rule

Z-Brand-Core is the production-truth side. Research/design learnings may be explored on the intelligence side and promoted through the established twin-repository governance. This document governs the shared UI/UX contract; implementation remains repository-appropriate.

## 15. Definition of done

A UI change is complete only when:
- existing required capability remains available;
- navigation is within the appropriate 2-4 level depth;
- data/table/chart states are coherent;
- drill-down preserves context;
- Runtime/Evidence/Action are exposed where applicable;
- responsive and empty/error/loading states are defined;
- regression and runtime checks pass;
- twin-repository synchronization requirements are satisfied where the change crosses repository boundaries.
