# Unified UI / UX / Information Architecture Execution Task

## Objective

Audit and optimize the existing intelligence-side UI/UX, information architecture, visual hierarchy, interaction model, data visualization, Evidence presentation, and module relationships while preserving research integrity and the boundary with production truth.

## Mandatory Rules

- Preserve all existing system rules, governance, Evidence, Runtime, permissions, security, stability, data boundaries, and twin-repository responsibilities.
- Research outputs must remain distinguishable from production truth.
- Reuse existing components, tokens, data models, APIs, and patterns whenever possible.
- Modify before duplicating.
- Do not introduce uncontrolled execution or unreported changes.
- All changes require real validation and truthful Git records.

## Target Intelligence IA

```text
Intelligence
├── Research
├── AI
├── Knowledge
├── Benchmark
└── Evaluation
```

Global page hierarchy:

`Shell → Workspace → Domain → Module → Page → Section → Component → Detail / Action`

Map actual functionality before applying this target model; do not mechanically reorganize stable code.

## Unified Page Logic

Use progressive disclosure:

`Context → Decision → Data / Trend / Runtime → Evidence → Detail → Action`

The interface should make it clear where the user is, what matters, why it matters, what supports it, and what can happen next.

## Visual System

Maintain a restrained, readable, information-first visual foundation with strong hierarchy, intentional whitespace, meaningful emphasis, and consistent design tokens.

Do not copy external products. External references may inform information organization and data storytelling only.

## Visualization

Standardize reusable patterns for Table, Chart, Trend, Timeline, Runtime, Ranking, Distribution, Heatmap, Graph, and Detail. Every visualization must answer a specific question.

## Interaction

Standardize Select, Search, Filter, Sort, Compare, Drill-down, Cross-highlight, Context preservation, Drawer, Timeline seek, Detail, and Action.

## Evidence and AI

Research judgments should trace:

`Decision → Evidence → Source → Time → Original Data`

AI presentation should distinguish:

`Input → AI Analysis → Confidence → Reason → Evidence → Human Decision → Final Result`

Never present AI output as unquestionable production truth.

## Cross-Repository Boundary

Zachary-OS-AI remains the research/intelligence side. Production truth belongs in Z-Brand-Core. Research findings intended for production adoption must be expressed through the established evidence/contract/specification flow rather than silently changing production behavior.

## State and Motion

State must not rely on color alone. Use text and/or symbols where appropriate.

Lifecycle:

`INPUT → DETECTED → VERIFIED → CLASSIFIED → CORRELATED → RISK → DECISION → ACTION → FEEDBACK`

Motion is permitted only for state, cause/effect, or continuity; avoid decorative motion.

## Engineering Process

1. Audit the real repository and existing implementation.
2. Map functionality → page → hierarchy → component → data → user task.
3. Decide keep / merge / move / restructure / reuse / modify / add / deprecate.
4. Define target IA.
5. Implement minimum necessary changes.
6. Reuse existing primitives.
7. Validate UI, UX, data, Evidence, permissions, accessibility, performance, and regression behavior.
8. Repair failures before completion.
9. Update documentation and mappings.
10. Commit truthfully and report exact SHA.

## Acceptance Criteria

- No research capability is lost.
- Research and production truth remain clearly separated.
- Navigation and hierarchy are understandable.
- Visualization has clear semantics.
- Evidence is traceable.
- AI output is distinguishable from facts and human decisions.
- Existing tests remain green; relevant tests are added.
- Changes are auditable and reversible.
