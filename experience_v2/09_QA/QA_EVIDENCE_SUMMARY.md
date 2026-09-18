# LUMENIS Experience V2.5 — QA Evidence Summary
Generated 2026-09-11. All numbers come from real Playwright (system Chrome 152, swiftshader) probes under `09_QA/`; nothing is estimated.

## Visual baselines (04_VISUAL_BASELINES)
- 8 widths (1920/1440/1280/1024/768/430/390/360) × 2 themes (light=黑银, dark=白银) × 44 screens = **704 PNG**, all present.
- Per-group capture console/page errors: **0** for all 16 groups (see console/console-matrix-report.json).
- Note: aria-label-only a11y fixes (sections.js/i18n.js/screens.js) were applied after the matrix capture; they add no rendered pixels, so the 704 baselines remain visually exact. a11y re-probe after the fix = 0 issues (a11y/a11y-recheck.json).

## Responsive (responsive/)
- Horizontal overflow (scrollWidth > innerWidth, including nested scroll containers): **0** across all 8 widths × 44 screens × 2 themes.
- 390 mobile AI-01 verified: single-column, bottom dock, Lumen Core FAB orb visible, no purple, no clipped controls.

## Accessibility (a11y/)
- Initial probe: 11 inputs/textareas without accessible name across 10 screens → fixed by adding aria-label (form fields use their visible label; search/composer use i18n keys; ACC-01 email/password).
- Re-probe (a11y-recheck.json): **0 remaining**.
- Body text contrast light = **15.31:1** (WCAG AA needs 4.5); dark in contrast-dark.json. Primary-button contrast cell is empty only on screens with no primary button (selector absent), not a failure.

## Performance (performance/)
- External network resources per screen = **0** (fully local/vendored).
- Page load: cold ~1306ms (local fonts), warm ~403ms headless; no CDN, no blocking third party.

## Console (console/)
- total_console_errors = 0; screens_with_errors = 0; groups = 16.

## Visual regression (visual-regression/)
- Static screens SYS-01 / CTH-03 / BMP-04 captured twice after settle → SHA-256 **byte-identical** (deterministic render). Animated orb screens are intentionally frame-variable and excluded.

## Reduced motion
- All motion tokens/keyframes are gated by `@media (prefers-reduced-motion: reduce)`; launch animation ships a reduced static fallback (05_components/brand/launch/reduced-motion-static); motion demos include a reduced-motion composite (05_MOTION/reduced-motion).

## Known / UNKNOWN (not faked)
- 54 backend bindings remain UNBOUND_REQUIRES_BACKEND_CONFIRMATION (06_CONTRACTS/unknown-bindings.json) — prototype data is marked data-source=prototype and must not ship as truth.

## Addendum — Internal-flow removed from UI (per DOUBAO_FRONTEND_DELIVERY_EXECUTION_REQUIRED §5 / user red-line)
- Internal operating procedures are no longer rendered: `R.steps` skips sections flagged `internal:true` (data retained for Codex). SH-01 content 10-step and AI-02 Morph 6-step hidden; AI conversation reasoning (`R.ai` steps) intentionally kept.
- Arrow-chain subtitles/labels de-processed (CTH overview, realtime, event graph, AI-02 title, SH-01 desc, upload/podcast wording, zh/en/ko copy).
- Deterministic probe (verify_flow.mjs): SH-01/AI-02 visible generic `.lum-steps`=0, AI reasoning steps retained (5/4), body chain text=false, console errors=0.
- Full 704 baseline matrix recaptured after the change: 16 groups errScreens=0; horizontal overflow all 8 widths =0; render determinism re-verified (byte-identical); validate_handoff ok (json fail=0, missing=[]).
