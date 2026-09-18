# ZBC Unified UI / Interaction / Visualization System V1

Date: 2026-09-03
Status: normative design and implementation baseline
Scope: ZBC production UI, Internal Browser, future Podcast/KOS/Brand/Fashion/Luxury modules, Web/App/PWA/Mini Program surfaces.

## 0. North Star

The product must grow in capability without growing chaotic in navigation or visual language.

Principles:
- beauty serves operation; operation never serves decoration
- quiet-luxury editorial visual language, but unmistakably an intelligence/operations product
- line icons are the default semantic icon language
- static UI is restrained; motion is data-driven and purposeful
- context is preserved across navigation, investigation, evidence and action
- reuse before invention; extend before creating a new page
- one semantic truth for route, capability, state and navigation

## 1. Information Architecture

Top-level product domains:
1. 工作台 — what changed / what needs attention
2. 监测 — what is happening
3. 事件 — what happened as an event
4. 洞察 — what it means
5. 资产 — what we retain and reuse
6. 系统 — whether the system itself is healthy

Page is not the same thing as capability. A capability may appear as a module, drawer, panel, action or contextual surface without becoming a new route.

## 2. Navigation Contract

All navigations use one resolver concept:
- ZBC resource -> internal route
- monitored platform resource -> Internal Browser
- evidence resource -> Evidence Viewer
- explicitly external resource -> External Browser

No domain module may directly decide to call window.open for monitored-platform content. External opening must be an explicit user action.

## 3. Internal Browser Contract

Internal Browser is a controlled workspace, not a decorative embedded browser.

Workspace layers:
- navigation/address/search
- tabs/context
- account/session
- page state
- collector controls
- capture/evidence controls
- health/runtime state

State model:
DISCONNECTED -> CONNECTING -> CONNECTED -> AUTHENTICATED -> PAGE_READY -> COLLECTOR_READY -> CAPTURE_READY -> EVIDENCE_READY

Failure states are explicit: AUTH_FAILED, BROWSER_FAILED, COLLECTOR_FAILED, CAPTURE_FAILED.

Browser != Collector != Evidence != AI.

## 4. Capture Pipeline

Browser interaction enters Capture Orchestrator when the user or scheduled workflow requests capture:
Browser -> Platform Adapter -> Normalizer -> SUBJECT_HARD_FILTER -> subject_hit() -> Dedup -> Evidence -> DB -> AI/Event/Insight.

Existing subject rules remain authoritative and must not be changed by UI work.

## 5. Component Hierarchy

Foundation -> Tokens -> Layout -> Component -> Domain Module -> Page.

Shared component families:
- Shell / navigation
- Command/search
- Button / icon button
- Tabs / segmented controls
- Table/list
- Card / metric
- Drawer / dialog / popover
- Timeline
- Evidence viewer
- Status / badge
- Toast / notification
- Media player
- Chart / visualization
- Browser workspace
- AI contextual action

Each component owns its interaction states and accessibility semantics.

## 6. Interaction State Contract

Every interactive component must explicitly support applicable states:
Default, Hover, Focus, Active, Selected, Loading, Empty, Error, Disabled, Expanded, Success.

Transitions must preserve context. Opening a detail surface should not unexpectedly reset filters, scroll position, selected entity or investigation context.

Prefer progressive disclosure:
- list -> quick preview -> detail -> deep investigation
- summary -> evidence -> action
- trend -> event -> source

## 7. Icon System

Visual direction: precise, thin, calm line icons.

Icon architecture:
Icon source -> Z Icon Registry -> semantic alias -> component.

Do not bind business code directly to a third-party icon name. This allows future replacement while preserving semantic ownership.

Semantic groups:
- navigation: home, monitor, event, insight, asset, system
- intelligence: search, spark/AI, trend, compare, relationship
- evidence: source, capture, image, link, verify
- operation: collect, refresh, pause, play, filter, export, open
- people: brand, creator, KOS, KOL, audience
- state: success, info, attention, risk, critical, unknown

Default style: 1.5-1.75px visual weight, optically aligned, no mixed icon families inside the same control group. Icons must not be used as unexplained decoration.

## 8. Visual Language

Direction: Editorial Intelligence x Quiet Luxury x Operational UI.

Retain the existing restrained black/white/gray foundation and semantic state colors. Upgrade through:
- stronger typographic hierarchy
- larger negative space around primary decisions
- restrained borders and separators
- high-quality line iconography
- subtle depth rather than excessive shadows
- motion only when it communicates state/change

Do not imitate a luxury storefront. The interface must remain a professional intelligence workspace.

## 9. Dynamic Visualization System

Visualization is a decision interface, not decoration.

Approved families:
- Trend: how did it change?
- Delta: how much did it change?
- Timeline: when did it happen?
- Relationship: who/what is connected?
- Heatmap: where is concentration?
- Flow: how does information/attention move?
- Risk field: where should attention go?
- Activity pulse: is the system working?
- Distribution: how is a population split?

Every visualization must state its decision question, primary measure, comparison baseline and interaction affordance.

Interaction model:
- hover/tap -> exact value + context
- select -> pin/highlight
- range select -> filter the surrounding workspace
- zoom -> never lose orientation
- drill down -> preserve parent context
- empty -> explain why data is unavailable
- stale -> expose data timestamp

Motion rules:
- animate entry only when it improves comprehension
- animate changes only when the change itself matters
- never continuously animate charts for visual effect
- respect reduced-motion preferences

## 10. Dashboard Contract

Dashboard answers only:
1. What changed?
2. What matters?
3. What requires action?

Avoid card-grid accumulation. Secondary analysis belongs in domain pages or drill-down surfaces.

## 11. Domain Interaction Blueprints

### Monitoring / Notes
List -> quick preview -> detail -> evidence -> event/subject/AI insight.
Primary actions: inspect, collect evidence, associate event.

### Events
Event list -> event workspace -> timeline -> related content/people -> evidence -> impact/risk -> action.

### Brands
Brand workspace -> overview -> content -> audience -> KOS/KOL/KOC -> events -> benchmark -> reports.

### KOS / creators
Profile -> content -> propagation/performance -> audience -> comments -> monitoring -> suggestions -> optional controlled reply workflow.

### Evidence
Evidence -> source -> captured state -> provenance -> linked entities -> linked decisions.
Evidence is immutable provenance; corrections create new interpretation records, not silent mutation of the original evidence.

### Reports
Insight -> report -> supporting evidence -> export/share. Reports are outputs of insight, not a top-level business object outside the insight domain.

### System
Runtime -> collector -> AI -> data -> auth -> permissions -> settings. Operational diagnostics stay out of the primary business dashboard except for summarized health signals.

### Internal Browser
Open from monitored resource -> navigate internally -> inspect -> capture -> evidence -> return to originating context.

## 12. Future Module Inheritance

Podcast, KOS, Fashion, Luxury, Campaign and new brands must first query the Capability Registry.

Decision:
- existing capability -> reuse
- adjacent capability -> extend
- genuinely new capability -> create and register

A new module must not automatically create a new top-level navigation item, standalone CSS stack or duplicate interaction system.

## 13. Web / App / Mini Program

Shared semantics, different density.

Web: full workspace and investigation.
App/PWA: focused monitoring, action and investigation.
Mini Program: task, alert, result and quick action; do not duplicate the full browser runtime.

The same capability ID, route/resource ID, icon semantic and state model should survive across surfaces.

## 14. Accessibility / Interaction Quality

Use semantic HTML controls where possible. Custom controls must expose correct labels, focus behavior and keyboard/touch semantics. Dialogs/drawers/popovers must manage focus and restoration. This follows the component-level principles demonstrated by Radix: accessible, functional, interoperable, composable and customizable.

## 15. Engineering Guardrails

Static/CI checks should reject:
- monitored-platform links bypassing Navigation Resolver
- direct window.open except explicit external action
- duplicated business navigation definitions
- new page-level CSS that duplicates existing component tokens
- business code directly importing third-party icon names
- visualizations without loading/empty/error/stale states
- components without defined interaction states
- new top-level navigation without IA review

## 16. Visual Regression

The UI system must include visual regression for:
- shell/navigation
- dashboard
- note list/detail
- event workspace
- brand workspace
- evidence viewer
- internal browser
- report
- mobile/responsive states
- dark/light if supported by the active product contract

Behavioral E2E must cover the navigation resolver and Internal Browser path, not only screenshots.

## 17. Reference Research Principles

External references are used as implementation patterns, not as visual copies:
- Lucide: structured, searchable icon metadata and semantic categorization support a registry approach.
- Radix: accessible, composable primitives and explicit interaction behavior are useful for the component contract.
- Luxury UX research: navigation, search, filtering, site-wide interaction and context preservation matter as much as visual polish in high-end brand experiences.

## 18. Definition of Done

The redesign is not complete when screenshots look better. It is complete when:
- every route has one owner
- every capability has one owner
- every icon has semantic ownership
- every interaction has defined states
- every visualization has a decision purpose
- monitored links stay inside Internal Browser by default
- capture returns to evidence and originating context
- new modules inherit the system without UI restructuring
- Web/App/Mini preserve the same information model
- visual and behavioral regression tests protect the contract
