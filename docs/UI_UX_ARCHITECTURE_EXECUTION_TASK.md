# Unified UI / UX / Information Architecture Execution Task

## Objective

Audit and optimize the existing production UI/UX, information architecture, visual hierarchy, interaction model, data visualization, Evidence presentation, Runtime presentation, and module relationships without breaking existing production functionality or architecture.

## Mandatory Rules

- Preserve all existing system rules, governance, twin-repository boundaries, Evidence, Runtime, Release Gate, permissions, security, stability, data boundaries, and deployment constraints.
- Do not rewrite stable business logic merely for visual reasons.
- Reuse existing components, tokens, APIs, data models, and patterns whenever possible.
- Modify existing implementations before creating duplicates.
- Do not introduce uncontrolled collection, tasks, data loss, silent failures, or unreported execution.
- All changes require real validation and truthful Git records.

## Target Information Architecture

```text
Xujing
├── Intelligence
│   ├── Research
│   ├── AI
│   ├── Knowledge
│   ├── Benchmark
│   └── Evaluation
├── Production
│   ├── Brand Intelligence
│   │   ├── KOS
│   │   ├── Public Opinion
│   │   └── Campaign
│   └── Content Intelligence
│       └── Podcast
└── Operations
    ├── Runtime
    ├── Monitoring
    ├── Audit
    ├── Tasks
    ├── Deployment
    └── System Health
```

Page hierarchy:

`Shell → Workspace → Domain → Module → Page → Section → Component → Detail / Action`

This is a target model, not a reason to mechanically rename or relocate working code. Map real existing functionality first.

## Unified Page Logic

Core pages should progressively reveal:

`Context → Decision → Data / Trend / Runtime → Evidence → Detail → Action`

The UI must answer: where am I, what changed, what matters, why, what is the evidence, and what can I do next?

## Visual System

Maintain the existing product visual foundation: restrained, clear, information-first, low decoration, strong hierarchy, readable typography, intentional whitespace, and meaningful emphasis.

Do not copy Xiaoyuzhou or Liangzi Interview Record visually. Their value is reference for content organization, long-form browsing, Runtime, timelines, and data storytelling only.

## Visualization System

Establish reusable patterns for:

- Table
- Chart
- Trend
- Timeline
- Runtime
- Ranking
- Distribution
- Heatmap
- Graph
- Detail

Each visualization must answer a clear question. Do not add charts only for visual effect.

## Interaction System

Reuse and standardize:

- Select
- Search
- Filter
- Sort
- Compare
- Drill-down
- Cross-highlight
- Context preservation
- Drawer / side panel
- Timeline seek
- Detail
- Action

Evidence should normally be inspectable without losing the current page context.

## Evidence Model

Important judgments should trace:

`Decision → Evidence → Source → Time → Original Data`

Clearly distinguish factual data, AI output, confidence, explanation, evidence, human decision, and final result.

## AI Presentation

Use:

`Input → AI Analysis → Confidence → Reason → Evidence → Human Decision → Final Result`

AI must not be visually presented as unquestionable system truth.

## Podcast Pattern

Podcast is the first complete reference implementation:

```text
Podcast
├── Overview
├── Intelligence
│   ├── Research
│   ├── Cases
│   ├── Topics
│   └── People
├── Production
│   ├── Episodes
│   ├── Interview
│   ├── Transcript
│   └── Assets
├── Performance
│   ├── Runtime
│   ├── Platforms
│   ├── Breakout
│   └── Audience
└── Learning
    ├── Patterns
    ├── Validation
    └── Knowledge
```

Episode experience should connect Context, Core Insight, Runtime, Story Timeline, Transcript, Story Map, Evidence, Assets, Platform Performance, and Actions.

## Cross-Module Patterns

After validating Podcast, extract reusable patterns and adapt them to KOS, Public Opinion, Campaign, Research, AI, and Evaluation. Do not copy business pages blindly.

Reusable patterns should include Overview, Decision, Evidence, Table, Timeline, Runtime, Detail, Drawer, AI Result, Performance, and Learning.

## State System

States must not depend on color alone. Use text and/or symbols as well as color where appropriate.

Suggested lifecycle:

`INPUT → DETECTED → VERIFIED → CLASSIFIED → CORRELATED → RISK → DECISION → ACTION → FEEDBACK`

## Motion

Motion is permitted only when it communicates state, cause/effect, or continuity. Avoid decorative motion and performance-heavy effects.

## Engineering Process

Execute in this order:

1. Audit real repositories and existing implementation.
2. Build existing-function → page → hierarchy → component → data → task mapping.
3. Identify keep / merge / move / restructure / reuse / modify / add / deprecate decisions.
4. Define target information architecture.
5. Implement minimum necessary changes.
6. Reuse existing design tokens and components.
7. Validate UI, UX, data, Evidence, Runtime, permissions, accessibility, performance, and regression behavior.
8. Repair failures before declaring completion.
9. Update documentation and mappings.
10. Commit with truthful messages and report exact SHAs.

## Acceptance Criteria

- No production capability is lost.
- No core data or API contract is broken.
- Navigation and hierarchy are understandable.
- Modules share a coherent interaction language.
- Data visualizations have clear semantics.
- Evidence remains traceable.
- AI output is distinguishable from facts and human decisions.
- Runtime interactions preserve context.
- Existing tests remain green and new relevant tests are added.
- Changes are auditable and reversible.
