# Web No-Scroll Integrated UI Execution Contract v1.0

Date: 2026-09-04
Scope: OSAI and compatible shared UI/runtime implementations
Status: P0 / normative

## 1. Core rule

The web application is a finite viewport workspace, not an endless document. The primary page must fit the active viewport without vertical page scrolling. Information that cannot fit must be resolved through hierarchy, internal panels, routes, sheets, dialogs, popovers, tabs, or focused detail states.

This does not mean information is deleted. It means information is progressively disclosed.

## 2. Information hierarchy

HOME / WORKSPACE
- Core: always visible
- Primary: visible when space permits
- Secondary: compact or expandable
- Deep detail: feature page / next route / focused overlay

Never fill the home screen merely to use available space.

## 3. Navigation model

Default shell:

Left Navigation -> Central Workspace

No permanent right context column by default.

Feature navigation must be explicit and deterministic. A feature that exceeds one viewport becomes a child state, route, sheet, dialog, popover, or focused workspace rather than causing endless page growth.

## 4. No-scroll web rule

The document root must not become an uncontrolled vertical scroll container.

Use a bounded layout model:
- viewport height as the shell constraint
- explicit header/navigation/workspace regions
- local scrolling only where a data collection genuinely requires it
- local scroll must have an explicit owner and boundary
- no nested uncontrolled scroll containers

A page may contain a bounded internal table/list viewport when the content itself is intrinsically long. The outer page must remain stable.

## 5. Progressive disclosure

If content exceeds the primary workspace:

Level 1: summary
Level 2: focused feature
Level 3: detail / evidence / configuration
Level 4: action / deep detail

Do not compress everything into one crowded surface.

## 6. Overlay contract

Dialogs, sheets, popovers and menus must have:
- one owner
- one mount authority
- one z-layer contract
- explicit open/close state
- focus return behavior
- escape/back behavior
- viewport boundary handling

Never solve layout conflicts by arbitrary z-index escalation.

## 7. Visual language

Use restrained visual hierarchy. Glass/material effects are functional layers, not decoration. Prefer navigation, controls, focus and transient surfaces. Avoid glass-on-glass and large decorative glass content surfaces.

The design principle is information first, function second, hierarchy third, motion fourth, decoration last.

## 8. Motion contract

Motion must communicate navigation, focus, state change, continuity or feedback. It must not obstruct interaction or hide content.

All motion must have:
- trigger
- source state
- target state
- duration/easing token
- interruption behavior
- reduced-motion fallback

## 9. Runtime truth

Every visible value must map to a runtime/view-model source. Code existing in the repository does not mean the feature is active.

Lifecycle:
DEFINED -> REGISTERED -> SYNCED -> LOADED -> READY -> RUNNING -> UPDATED -> VERIFIED

UI status must reflect the actual lifecycle state.

## 10. Requirement persistence

Every user requirement must become a traceable Requirement ID and map to:
Requirement -> Contract -> Implementation -> Test -> Evidence -> Result.

A requirement stored only in chat, README prose, or an unconsumed file is not considered executed.

The implementation registry must identify whether a requirement is:
PENDING / IMPLEMENTED / RUNNING / VERIFIED / BLOCKED.

## 11. AI execution rule

AI coding agents must not infer missing requirements silently. Missing data, component, route, runtime contract or visual specification is UNKNOWN and blocks implementation until resolved.

Before modifying UI:
READ -> LOCATE OWNER -> READ CONTRACT -> DEFINE CHANGE BOUNDARY -> IMPLEMENT -> TEST -> RENDER VERIFY -> REGRESSION.

## 12. Anti-coverage guard

For every shared UI surface verify:
- single render owner
- single state owner
- single layout owner
- single overlay owner
- no duplicate mount
- no competing async render
- no accidental stacking context
- no uncontrolled overflow
- no hidden clipping

## 13. Acceptance

A page is Delivery Ready only if:
- primary information is visible in the initial viewport
- navigation is deterministic
- no endless outer scrolling exists
- deep information is reachable through explicit hierarchy
- overlays do not obscure required controls
- live values update from runtime
- visual hierarchy remains stable during state changes
- data accuracy is verified
- existing features pass regression
- requirement traceability is complete

## 14. Research adoption principle

Apple platform research is used for engineering principles, not visual cloning. Current Apple guidance emphasizes navigation structure, hierarchy, adaptive layouts, restrained Liquid Glass usage, and avoiding stacked/nested glass surfaces. SwiftUI navigation uses explicit stacks/split navigation and supports state restoration/deep linking. MLX is relevant to local Apple-silicon ML runtime research.

Reference research:
- Apple Liquid Glass: https://developer.apple.com/documentation/TechnologyOverviews/liquid-glass
- Apple Navigation: https://developer.apple.com/documentation/swiftui/navigation
- Apple robust navigation: https://developer.apple.com/documentation/SwiftUI/Bringing-robust-navigation-structure-to-your-swiftui-app
- Apple MLX: https://github.com/ml-explore/mlx

## 15. Non-negotiable outcome

The product must feel integrated, compact, calm and operational.

Do not optimize for maximum visible content.
Optimize for maximum useful information per interaction without crowding.

If content cannot fit correctly, create hierarchy. Do not shrink it until it becomes unusable and do not extend the page indefinitely.
