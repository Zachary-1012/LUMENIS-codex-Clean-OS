# LUMENIS Component Library (self-built, Vanilla)

Machine registry: `COMPONENT_REGISTRY.json` (foundation / data / AI groups, renderer map, 16 states). Runtime: `10_prototype/assets/components.js`, `sections.js`, `icons.js`. Components are framework-free and Jinja-friendly.

## Foundation
- **AppShell** rail/topbar/context/dock grid (PAT-NAV-01/02), adaptive across 8 viewports.
- **SubjectContext pill + domain switch** — single global context; view-only switch, backend re-auth.
- **Button** variants primary/secondary/ghost/danger; sizes; high-risk never primary-blue; press micro-feedback.
- **Chip/Tag, Segmented control, Tabs, Breadcrumb, IconButton, Modal, Drawer, BottomSheet, Toast** — all with focus ring, ESC/backdrop, aria labels.

## Data / decision
- **MetricCard** KPI value (count-up, reduced-motion→final), unit, delta, sparkline, source + freshness, state slot.
- **EvidenceCard / EvidenceRail** claim → evidence id, citation chip, preview→rail (M08).
- **EventCard, RiskCard, Timeline, InsightPanel** — source-linked, decision-oriented.
- **DataTable** sticky header, horizontal scroll on mobile, empty/permission/error states, never fake rows.
- **Chart** bar/line/ring/heat (self-drawn SVG, no chart lib), legend, axis labels, empty/loading.
- **StateBlock** — one renderer for all 16 states (ready + 13 non-ready + disabled), icon+title+body+action slot.
- **Calendar cells** (deterministic demo), upload dropzone + segmented progress (M12).

## AI
- **AIComposer** (artifact-first), @Evidence/@Subject/@Time chips, nine-state machine.
- **AIThread / AIStep** real tool/status steps, citation rendering, no fake thinking loop.
- **Capability→Task morph surface (M05)**, **ArtifactCard**, **AIStatus / ProviderHealth**.

## The 16 states (mandatory for every data surface)
`ready` + `loading, updating, partial, stale, degraded, empty_true, empty_notcollected, empty_filter, empty_permission, permission_denied, blocked, offline, error` + `disabled`. Order in `components.js STATE_ORDER`; copy for all 13 non-ready states exists in zh-CN/en/ko. A block must never be silently blank.

## Icons
~80 original inline stroke icons, 24×24 viewBox, 1.5–2 stroke-width, round caps, `currentColor`, no icon font / no external icon package.

## Binding note
Components render purely from the per-screen ViewModel. They never fetch. The Codex adapter (`11_integration_skeleton/server_binding_adapter.example.py`) shapes backend data into the exact props each component reads; unknown fields stay UNKNOWN.
