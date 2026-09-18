# Experience V2 — Versioning & Change Log

## v2.4.0 — 2026-09-11 (form-layer redesign『序 · Editorial Lumen OS』structural de-templating)
Response to repeated review "still the previous template, no ecosystem design language — color/text tweaks are not enough". v2.4 changes the **form/structure layer**, not the palette; it builds on v2.3 black-silver/silver-white and the orb (no rollback).

### Added
- **Editorial serif display voice** `--lum-font-display` (CJK Songti tier + Georgia/Times): page mastheads (`.lum-display/.lum-h1/.lum-h2`), editorial section heads and **KPI numerals** now serif (600, tabular lining); body/controls stay sans — a literary, ownable typographic contrast.
- **The Lumen Axis (序轴)** signature system: desktop main column gets a continuous margin axis the whole page hangs from (`.lum-page::before`, ≥1025 only); the side rail becomes an **index catalog** with a continuous axis + hollow nodes, active = filled metal node with ring; masthead closes on a hairline + 88px Lumen-line accent.
- **Strata baseline grid** behind content (320px column / 88px baseline, ultra-faint) for an ordered "ecosystem" base; `--lum-axis/--lum-strata/--lum-editorial-gap` tokens.
- `LUMENIS_DESIGN_LANGUAGE.md` rewritten to v2.4 (serif×sans, axis, strata, de-boxing, black-silver/silver-white, orb); `design-tokens.json` resynced to real v2.4 values.

### Changed (structural)
- **De-boxing**: outer `.lum-card` is now an open near-flat stratum (hairline, no shadow, hover only deepens the rule); nested `.lum-card-solid` keeps a solid "evidence artifact" surface → open-strata / solid-artifact depth instead of stacked plastic boxes.
- Geometry tightened to a precision-instrument scale (radius xs3/sm6/md10/lg14/xl18; pill unchanged); editorial section gap enlarged (`clamp(22px,2vw+14px,44px)`); eyebrow becomes a mono spaced index mark; body desc limited to 72ch / relaxed line-height for literary whitespace.
- AI markers unified on the neutral `orb` glyph (nav AI-01, AI avatar, evidence provider/insight kind, draft action) — sparkles/star removed from the AI language.

### Fixed
- Orphan margin axis on chrome-less auth screens (ACC-01/04) — axis and extra indent suppressed when `data-chrome="none"`.

## v2.3.0 — 2026-09-11 (black-silver / silver-white metal monochrome + chaos orb; full de-purple)
Response to "light = black-silver, dark = silver-white (inverse), remove the purple, the sphere must flow like chaos inside itself with no star; raise material quality".

### Added
- **Self-rendered canvas AI Orb** `assets/orb.js` (zero-dependency vanilla canvas): multiple nebula wisps orbiting **inside** a clipped metal sphere + soft core + rotating bands + specular/rim; state-colored (idle/processing/success/warning/danger), light=black pearl with silver mist, dark=silver sphere with multiply shadow; rAF pauses off-view, reduced-motion = single frame, DPR/ResizeObserver adaptive. Mobile dock FAB is the orb (replaces sparkles).
- Metal tokens: brand gradient + `--lum-metal-sheen`, `--lum-lumen-line`; true-neutral slate ramp; metal sheen on primary button/logo.

### Changed
- **Global de-purple → metal monochrome**: light = black-on-silver (canvas #ECEDEF, primary near-black #1B1D23); dark = silver-on-black inverse (canvas #07080A, primary silver #E9EBEF, silver button uses inverse dark text). Primary action is always the canvas inverse; Icy Cyan demoted to data-viz/status only. Hard-coded purples (logo shadow, heatmap, optical tint/fallback, insight, steps/tabs/progress) all neutralized.

## v2.2.0 — 2026-09-11 (ownable design language『序 · Lumen Editorial OS』, de-templating)
Response to review feedback "too template-like, no design language, must not converge at the start; fluid device adaptation; internal codes off the surface; name-first nav; full domain names; collapsible groups". Second-round clean-room research: Apple HIG (Clarity/Deference/Depth, dynamic type), Tesla (radical subtraction, single accent), Linear/Vercel Geist/Stripe (type as brand anchor, near-monochrome, generous whitespace, display negative tracking, tabular numerals). No asset/visual copied.

### Added
- **`04_design_system/LUMENIS_DESIGN_LANGUAGE.md`** — the ownable language: 5 principles, the **Lumen Line** signature motif, material/type/space/nav/component/motion doctrine, per-screen anti-template checklist, non-goals.
- Fluid type & layout: every font-size token now `clamp()` (body near-constant, display scales 32→48), plus fluid page pad / section gap / rail width; display/heading negative tracking; display line-height 1.14.
- Collapsible side-nav groups (chevron + aria-expanded); name-first navigation (no glyph tiles/filled blocks; active = ink name + 2px Lumen Line).
- Second-round research appended to `13_research/RESEARCH_FINDINGS.md`; `design-tokens.json` + `DESIGN_SYSTEM.md` resynced (incl. warm palette that had drifted).

### Changed (de-templating)
- Cards de-plasticized to near-flat (`--lum-sh-flat`, hairline + whitespace carry hierarchy; glass reserved for softglass/OPT); KPI: removed radial blob & hover-lift, added 2px top Lumen Line, tertiary-grey label, hidden label glyph, big tabular value; delta pill no longer stretches.
- Internal codes moved off the surface: view-layer `human()` strips leading domain/module prefixes from eyebrows; KPI card-face `EV:` source removed → `data-provenance`/title; SubjectContext field dump removed from drawer → human sentence; AI composer `subject=…·domain=CTH` line removed; chips localized (引用证据/指定主体/时间范围).
- Domain shown by full names 商业运营/品牌市场 (topbar segmented, sign-in, filters, agent table, quick card); CTH/BMP remain internal-only in data/routes/ids.
- ≤1024 keeps a readable text rail (no empty icon-only rail); ≤560 hides the topbar domain lens (available in subject drawer) to prevent vertical wrap.

### Fixed
- Delta/segmented controls stretching or wrapping at narrow widths (align-self:flex-start; nowrap).

## v2.1.0 — 2026-09-11 (global material & human-vision refinement)
Per approved LUMENIS brand color sheet (warm paper / soft ink / Aurora Icy Cyan) and the design-research red-line; no logo built.

### Changed (material language, global)
- Light canvas cool-grey `#F5F7FB` → warm paper `#F3F1EC`; near-black text → soft ink `#2B2D36`; warm pearl surfaces `#FDFCF9`, warm hairline `#E3E0D8`; dark canvas deepened to `#0B0E15` / surface `#121722`.
- Added ultra-subtle 160px paper grain (non-interactive, .04 light / .06 dark), top catch-light on cards/controls/chrome, warm soft layered elevation.
- Aurora Icy Cyan (`#8BE7FF`/`#4FC4E8`) introduced **for fine detail only** — focus ring, eyebrow hairline tick, gradient termini (sparkline/progress/timeline/steps/tabs/nav indicator/event rail), micro-glow; Indigo stays the authoritative primary (70/20/10 unchanged).
- Literary whitespace: eyebrow letter-spacing .18em with icy tick, desktop page gap 32 / padding 32–40, gradient hairline section rules; buttons/inputs/metric/action get refined hover-lift & sheen interaction质感.
- `design-tokens.json` + `DESIGN_SYSTEM.md` synced to the refined palette/material (no doc↔CSS drift).

### Fixed
- **Mobile SPA context overlay covering content**: on ≤768 the context panel auto-opened as an 88vw overlay at startup; `mountShell` now defaults it closed on phone widths and auto-collapses when crossing into phone width (reopen on demand). Standalone per-screen captures were already correct.
- Drawer becomes a full-width sheet on ≤430.
- Demo recording: QA control bar now hidden (`lum-capture`), locale/optical switched through the runtime API (`LumI18n.setLocale` / dataset) instead of operating visible controls, mobile step-chain scrolled by real horizontal scroll (no accidental drawer); mobile segment composited with a blurred cover backdrop.
- Sparkline now uses a per-instance brand→icy SVG gradient.

## v2.0.0 — 2026-09-11 (initial production-experience handoff)
Greenfield, isolated under `experience_v2/`. No legacy UI reused (legacy used only as capability evidence).

### Added
- Self-built design system: exact V2 color tokens (light/dark), type scale, spacing, elevation, original optical-material runtime with HIGH→STANDARD→SOFT_GLASS→OPAQUE degradation.
- Self-built component library (foundation/data/AI) with 16 states; ~80 original stroke icons; self-built M01–M15 motion runtime (WAAPI), semantic-reason enforced, reduced-motion to final state.
- 44 screens (Account 4 / CTH 10 / BMP 11 / AI 5 / System 8 / Shared 6), each with spec/fixture/viewmodel/actions/state-board/standalone-html (6-file package).
- Runnable SPA prototype + per-screen standalone pages; zh-CN/en/ko chrome (164 keys, full parity); 8-viewport adaptive reflow; light/dark.
- Six-Port contracts (ViewModel/Capability/State/Action/Permission/Evidence), 54-row binding matrix, UNKNOWN list, backend gap list, binding JSON schema + Python adapter example + integration guide.
- Codex handoff: ten mirrored registries + MANIFEST (real on-disk inventory) + `19_handoff/INTEGRATION_START_HERE.md`.
- Clean-room research record (8 sources, principles only), provenance manifest.
- SH-01 Content Studio flagship implementing the Content Creation Learning Contract (10-stage chain, 6 Pattern Registries, factuality wall, scoped retrieval, cross-format artifacts, artifact-first AI marked DESIGN_ONLY).
- Deterministic validator (33 gates), visual regression (8 viewport+dark+state boards, 0 errors), smoke render, interactive demo mp4/gif/contact sheets, all-44-screen overview sheets.

### Fixed during QA
- Mobile grid blowout: `data-context="closed"` selector specificity was overriding the ≤768/≤1024 single/collapsed-column templates → moved to `minmax(0,1fr)` with matching specificity; long step-chain now horizontal-scroll on phones; long unbroken tokens wrap; subject pill ellipsizes.
- Metric count-up could be captured mid-animation → screenshots run under reduced-motion for deterministic final values (motion preserved in the demo video).
- Prototype QA control bar removed from deliverable screenshots via `html.lum-capture` (still available in live prototype).

### Deferred
- Logo / launch animation — LOGO_DEFERRED by explicit user instruction (authority spec pointer retained in `02_authority`).
- Backend wiring / Runtime / E2E — Codex (Production Code Owner); tracked as 54 binding gaps, never mocked as truth.

### Notes / honest boundaries
- Per-screen dense business fixture body is zh DESIGN_ONLY representative data; replaced by backend ViewModel. Not claimed as finished localization.
- Zero third-party UI/animation runtime; zero copied asset; research sources never shipped as product assets.
