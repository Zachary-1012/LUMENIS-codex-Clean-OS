# Web No-Scroll Integrated UI Execution Contract v1.0

Date: 2026-09-04
Scope: ZBC production UI and shared UI/runtime implementation
Status: P0 / normative

## Core

The web application is a finite viewport workspace, not an endless document. The primary page must fit the active viewport without outer vertical page scrolling. Content that does not fit must move into explicit hierarchy: child route, focused workspace, sheet, dialog, popover, tab, or bounded internal data region.

## Information hierarchy

HOME / WORKSPACE:
- Core information: always visible
- Primary information: visible when space permits
- Secondary information: compact/expandable
- Deep information: feature page / focused state / overlay

Do not populate the home screen merely because space exists.

## Navigation

Default shell: Left Navigation -> Central Workspace.

A permanent right context column is not part of the default shell. Feature navigation must be deterministic. A large feature is decomposed by hierarchy rather than by endless page height.

## No-scroll rule

The document/root shell must remain bounded by the viewport. Local scrolling is allowed only for intrinsically long data collections such as tables or logs and must have an explicit owner and boundary. No uncontrolled nested scroll containers.

## Progressive disclosure

Level 1: summary
Level 2: focused feature
Level 3: detail/evidence/configuration
Level 4: action/deep detail

Information is not deleted; it is progressively disclosed.

## Overlay ownership

Every sheet/dialog/popover/menu has one owner, one mount authority, one z-layer contract, explicit state, focus return, close/back behavior, and viewport boundary handling. Arbitrary z-index escalation is prohibited.

## Visual system

Information first. Function second. Hierarchy third. Motion fourth. Decoration last.

Glass/material is a functional surface for navigation, controls, focus and transient states. Avoid glass-on-glass and decorative full-content glass surfaces. The interface must remain compact, calm, legible and operational.

## Motion

Motion must explain navigation, focus, continuity, state change or feedback. Each animation requires trigger, source state, target state, tokenized timing, interruption behavior and reduced-motion fallback.

## Production truth

UI displays canonical/runtime/view-model data and must not independently recompute production metrics. Data flow remains:
External Data -> Evidence -> Validate -> Normalize -> Canonical Data -> Domain Function -> Metric -> View Model -> Visualization -> UI.

## Lifecycle

DEFINED -> REGISTERED -> SYNCED -> LOADED -> READY -> RUNNING -> UPDATED -> VERIFIED.

A repository artifact is not considered live merely because it exists in Git.

## Requirement persistence

Every requirement must map to Requirement ID -> Contract -> Implementation -> Test -> Evidence -> Result. A requirement that exists only in chat or an unused document is not executed.

## AI execution

AI agents must not silently infer missing requirements. Unknown route/data/component/runtime/visual contract means UNKNOWN and blocks implementation until resolved.

Before UI changes:
READ -> LOCATE OWNER -> READ CONTRACT -> CHANGE BOUNDARY -> IMPLEMENT -> TEST -> RENDER VERIFY -> REGRESSION.

## Anti-coverage checks

Verify single render owner, state owner, layout owner and overlay owner; no duplicate mount; no competing async render; no accidental stacking context; no uncontrolled overflow; no hidden clipping.

## Acceptance

Delivery Ready requires:
- primary information visible in initial viewport
- deterministic navigation
- no endless outer scrolling
- deep information reachable through explicit hierarchy
- overlays do not obscure required controls
- visible values update from runtime
- stable hierarchy during state changes
- data accuracy verified
- regression passes
- requirement traceability complete

## Research adoption

Apple platform research is used for engineering principles rather than visual cloning. Apple guidance emphasizes hierarchy, explicit navigation structures, adaptive layouts and restrained Liquid Glass usage. MLX is relevant to Apple-silicon local ML/runtime research.

References:
- https://developer.apple.com/documentation/TechnologyOverviews/liquid-glass
- https://developer.apple.com/documentation/swiftui/navigation
- https://developer.apple.com/documentation/SwiftUI/Bringing-robust-navigation-structure-to-your-app
- https://github.com/ml-explore/mlx

## Non-negotiable outcome

Optimize for useful information per interaction, not maximum information on screen. If information cannot fit correctly, create hierarchy; never solve the problem by endless page growth, unreadable compression, or decorative clutter.
