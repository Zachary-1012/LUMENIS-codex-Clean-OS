# Z Brand Core UI / IA / Interaction Design Baseline

> Version: 2026-09-03 V1.0  
> Status: P0 design-system and interaction baseline  
> Scope: ZBC production UI, future ZBMP capabilities, Web / App / PWA / Mini Program surfaces

## 1. Design intent

The product must become easier to operate as capability grows. New features must inherit the existing information architecture, component system, interaction contracts and responsive rules instead of creating isolated pages.

Primary principles:

1. Operation first: the shortest safe path to the next meaningful action wins.
2. Beauty is structural: whitespace, typography, alignment, icon rhythm and motion must create calm rather than decoration.
3. Editorial luxury, not luxury-commerce imitation: restrained, tactile, precise and information-dense where useful.
4. Line icons are the primary semantic language. Icons must be consistent in stroke, optical size, corner treatment and state behavior.
5. Dynamic visualization is functional: animation explains change, hierarchy, state and causality; it must never obscure data.
6. One concept, one owner: one navigation truth, one component owner, one state model, one source of truth per capability.
7. Progressive disclosure: overview first, detail on demand, advanced controls behind contextual actions.
8. No silent context loss: opening a note, event, evidence item or monitored-platform page must preserve the user's task context and provide a clear return path.

## 2. Reference-material synthesis

The uploaded visual reference package contains 39 raster UI/reference images and 3 video recordings. The common visual language is characterized by:

- generous negative space and soft neutral surfaces;
- restrained black/white/gray foundations with occasional atmospheric accent light;
- thin outline icons and large, calm controls;
- cards used as containers rather than decoration;
- compact bottom navigation on mobile;
- progressive disclosure and contextual overlays;
- soft gradients / depth / translucent surfaces used sparingly;
- strong separation between primary content and system chrome;
- data widgets that remain visually quiet until interaction;
- motion used to reveal relationships and state transitions.

Adopt these qualities, but do not copy the reference screens literally. The ZBC expression remains a brand-intelligence operating system: editorial, analytical, precise and operational.

## 3. Proposed visual language

### Foundation

- Near-black / warm-white / neutral gray remain the primary semantic surfaces.
- Existing ZBC monochrome/wabi-sabi direction is retained as the base.
- Introduce an optional atmospheric layer for hero metrics, AI insight, system health and dynamic visualizations; never use gradients as the default surface for every card.
- Maintain semantic state colors for success, information, attention, risk, critical and unknown. State color must never be the only signal.

### Shape

- Keep the existing 10 / 14 / 20px radius family where it already works.
- Use smaller radii for dense data surfaces and larger radii for workspace containers.
- Avoid excessive pill controls. Pills are reserved for status, filters and compact selections.

### Typography

- Establish explicit display / heading / body / metadata / numeric hierarchy.
- Large numbers are treated as visual anchors.
- Long-form research and evidence text uses a calmer editorial reading width.
- Labels must describe actions or content, not implementation details.

### Iconography

Primary candidate family: Lucide or Phosphor as a controlled source, with ZBC-owned aliases and a limited custom set where necessary. Lucide emphasizes consistent open-source SVG icon data and tree-shakable delivery; Phosphor provides multiple weights and raw SVG assets suitable for a controlled icon system. See research references below.

Rules:

- default semantic icon weight: light/regular outline;
- filled icons only for selected/high-emphasis states;
- one icon family per product surface;
- no emoji as product UI icons;
- no mixed stroke widths within one control group;
- optical sizing is more important than nominal pixel size;
- icon-only actions require accessible labels and visible tooltip/help where appropriate;
- decorative icons are hidden from assistive technology; semantic icons receive accessible names.

## 4. Information architecture

Top-level product structure:

```text
Workspace
Monitoring
Events
Insights
Assets
System
```

### Workspace

Answers: what matters now and what requires action.

- Today
- Changes
- Priority risks
- Priority events
- Tasks / pending review

### Monitoring

Answers: what is happening now.

- Live stream
- Notes/content
- Topics
- Campaigns
- Monitoring configuration
- Browser Workspace

### Events

Answers: what has become an event and what is its lifecycle.

- Marketing events
- Communication events
- Public-opinion events
- Risk events
- Review queue
- Event relationships

### Insights

Answers: why it matters.

- Trends
- Brands
- Audience
- KOS/KOL/KOC
- Benchmarking
- Reports

### Assets

Answers: what the organization has accumulated.

- Brands
- Campaigns
- Cases
- PR cases
- Communication subjects
- Knowledge
- Evidence

### System

Answers: whether the system itself is healthy and configurable.

- Runtime
- Collector
- AI
- Auth
- Data
- Permissions
- Settings

## 5. Page / module / action hierarchy

```text
Domain
  -> Page
      -> Section
          -> Module
              -> Component
                  -> Action
                      -> State
```

A feature should not become a top-level page merely because it is new. First classify its semantic owner.

## 6. Navigation contract

All navigation must go through one resolver.

```text
navigate(resource, context)
  -> internal route
  -> internal browser
  -> evidence viewer
  -> external browser
```

Monitored-platform links default to Internal Browser. External browser opening is an explicit user action only.

The resolver must preserve:

- originating page;
- active filters;
- selected entity/event;
- task context;
- return destination;
- evidence context when applicable.

## 7. Internal Browser workspace

Internal Browser is a system capability, not an isolated novelty page.

```text
Browser Workspace
  Navigation
  Tabs
  Identity
  Session
  Page state
  Collector
  Capture
  Evidence
  AI context
  Health
```

State model:

```text
DISCONNECTED
  -> CONNECTING
  -> CONNECTED
  -> AUTHENTICATED
  -> PAGE_READY
  -> COLLECTOR_READY
  -> CAPTURE_READY
  -> EVIDENCE_READY
```

Failure states must be explicit: AUTH_FAILED, BROWSER_FAILED, COLLECTOR_FAILED, CAPTURE_FAILED, COOLING_DOWN.

The browser is the interaction surface. Collector remains the data pipeline. Evidence remains the provenance layer.

## 8. Module interaction contracts

### Workspace / Dashboard

Primary action: investigate a change or risk.

Flow:

```text
Overview -> priority signal -> contextual detail -> action -> return to overview
```

No dense secondary tables by default. Detailed data opens contextually.

### Monitoring / Notes

```text
Filter -> list -> preview -> detail -> evidence / event / subject
```

Filters persist during drill-down and return.

### Monitoring / Topics

```text
Topic -> activity -> representative notes -> event / evidence
```

Topic pages emphasize change over time, not a static list.

### Events

```text
Event list -> event timeline -> evidence -> actors/content -> assessment -> lifecycle action
```

The event page is the convergence point for source evidence, interpretation and action.

### Risk / Review

```text
Queue -> reason -> supporting evidence -> approve / reject / escalate -> audit trail
```

Destructive or high-impact actions require explicit confirmation.

### Brands

```text
Brand -> profile -> monitoring -> content -> events -> audience -> benchmark -> reports
```

Do not create separate pages for every brand capability when a profile workspace can host the relationship.

### KOS / KOL / KOC

```text
Subject profile -> content -> influence signals -> audience -> comments -> monitoring -> suggested actions
```

Identity and content type remain separate concepts.

### Reports

```text
Report index -> period / subject -> executive summary -> evidence -> detail -> export
```

Report generation must preserve source period and evidence references.

### Cases / Knowledge

```text
Search -> case -> evidence -> pattern -> reusable insight
```

Knowledge is an asset; it should not compete with live monitoring navigation.

### System / Runtime

```text
Health -> component -> failure reason -> remediation -> verification
```

Never present a generic "system error" when the system knows the failing layer.

### AI Assistant

```text
Intent -> context preview -> AI result -> evidence / source -> action
```

AI output is an enhancement layer and must expose provenance where the result can affect decisions.

## 9. Dynamic visualization system

Dynamic visualization is a first-class capability.

### Principles

1. Show movement, not decoration.
2. Prefer change, delta and relationships over ornamental charts.
3. Animate entry and transition, not every element continuously.
4. Preserve stable spatial anchors so users can compare before/after.
5. Use progressive detail: overview -> hover/tap -> drill-down.
6. Motion must respect reduced-motion preferences.

### Visualization families

- Trend line: time-based movement.
- Delta sparkline: compact local change.
- Event timeline: lifecycle and causal sequence.
- Relationship graph: event / subject / evidence relationships.
- Heatmap: concentration across time/category.
- Flow / Sankey-like view: only when movement between stages is the actual question.
- Risk field: severity × velocity × confidence.
- Activity pulse: live collection/runtime state.
- Map: only when geography materially changes the decision.

### Interaction model

```text
Idle -> hover/tap -> focused -> contextual detail -> drill-down
```

Charts should not navigate away merely because a point is clicked; first reveal contextual detail, then offer a clear action.

## 10. Motion system

Use restrained motion tokens rather than ad-hoc animations.

Suggested baseline:

- micro interaction: 120-160ms
- component transition: 180-240ms
- workspace transition: 280-360ms
- complex visualization transition: 360-520ms

Avoid perpetual motion except live status indicators where motion communicates activity.

## 11. Component ownership

Core component families:

```text
Navigation
Shell
PageHeader
SectionHeader
Metric
Status
FilterBar
DataList
DataTable
Card
Drawer
Dialog
Popover
Timeline
Chart
EvidenceViewer
BrowserWorkspace
EntityProfile
EventTimeline
AIInsight
Toast
CommandMenu
```

Each component must define:

- visual variants;
- interaction states;
- loading state;
- empty state;
- error state;
- disabled state;
- accessibility contract;
- responsive behavior.

## 12. Responsive strategy

Do not design separate business logic for Web/App/Mini Program.

```text
Shared capability
  -> shared semantic model
      -> platform-specific presentation
```

Desktop: multi-column workspaces and persistent contextual navigation.  
Tablet: collapse secondary columns before primary content.  
Mobile: bottom navigation / compact header, one primary task per screen, contextual sheets for secondary detail.  
Mini Program: task-oriented surfaces, notifications and result inspection; do not reproduce the complete resident browser runtime.

## 13. Regression rules

A UI change fails review if it:

- creates an unnecessary top-level navigation item;
- bypasses Navigation Resolver;
- sends monitored-platform content directly to an external browser by default;
- duplicates a component with materially identical behavior;
- adds a new global JS/CSS layer without ownership justification;
- removes subject filtering or changes production data semantics;
- loses context during drill-down;
- makes dynamic visualization decorative rather than informative;
- introduces an icon family inconsistent with the product system;
- lacks loading / empty / error / disabled states where applicable.

## 14. Research references

- Radix Primitives: accessible, functional, interoperable and composable primitives; useful as a behavioral reference for dialogs, menus, tabs, focus management and stateful components.
- Lucide: open-source SVG icon system; useful as a controlled line-icon source.
- Phosphor: flexible icon family with multiple weights and raw SVG assets; useful for evaluating icon weight systems and cross-platform asset management.
- GitHub Primer: mature design-system example emphasizing component governance and accessibility.
- Apple HIG tab views: useful reference for limiting tabs to closely related content and keeping each pane self-contained.
- Baymard luxury-goods UX research: useful benchmark for high-end fashion/luxury information hierarchy, search, filtering and site-wide interaction patterns.

## 15. Implementation order

```text
1. Freeze IA and Navigation Contract
2. Create Page Registry / Capability Registry / Interaction Registry
3. Consolidate icon source and semantic icon aliases
4. Consolidate design tokens
5. Consolidate shell + navigation + page primitives
6. Implement Navigation Resolver
7. Complete Internal Browser / Collector / Evidence integration
8. Refactor dashboard into decision-oriented workspace
9. Migrate pages module-by-module
10. Add dynamic visualization system
11. Add responsive Web/App/Mini presentation contracts
12. Add visual + interaction regression tests
```

## 16. Non-goals

- No full rewrite of the production backend merely for visual cleanup.
- No deletion of legacy assets before capability and dependency audit.
- No copying of luxury brand websites as a visual clone.
- No animation for decoration alone.
- No replacement of production rules with AI judgment.

## 17. Definition of done

The UI system is considered converged when a new module such as Podcast, KOS, Fashion, Luxury Brand or Campaign can be added by mapping capabilities into the existing IA and component system without creating a parallel navigation system or a second visual language.

The desired end state is:

> The product can grow substantially in capability without growing proportionally in UI complexity.
