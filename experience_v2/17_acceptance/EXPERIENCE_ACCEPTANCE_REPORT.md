# Experience V2 Acceptance Report (frontend layer only)

Generated from deterministic checks, not claims. This is the Experience-layer gate; the product's six Production gates remain Codex's responsibility.

> **v2.4 (current): structural de-templating『序 · Editorial Lumen OS』** — serif editorial display (CJK Songti tier + Georgia) for mastheads/KPI over a sans body; the **Lumen Axis** (desktop margin axis + index-catalog rail with hollow/filled metal nodes + masthead rule); faint strata baseline grid; cards de-boxed into open strata over solid evidence artifacts; tightened precision radius; literary whitespace; AI language unified on the neutral orb glyph (no star). Builds on v2.3.
> v2.3: **black-silver / silver-white metal monochrome (full de-purple)** — light=black-on-silver, dark=inverse silver-on-black with readable inverse button text, Icy demoted to data-viz/status only; self-rendered canvas **chaos orb** (nebula flowing inside the sphere, state-colored, no star).
> v2.2: ownable design language baseline — fluid clamp type/spacing, name-first collapsible nav, full domain names, internal codes moved off card faces.
> All 44 screens re-captured across 8 viewports + dark + state boards, regression errors=0, validator **34/34**, demo re-recorded (~31.9s). Logo still LOGO_DEFERRED.

## Deterministic self-check — `18_validation/validate_handoff.py`
**34/34 PASS** → `validation_report.json`. Covers: every JSON parses; 44×6 per-screen packages present; runtime assets + generated data present; zh/en/ko parity 164/164; zero third-party runtime reference; zero legacy CSS/HTML class leakage; every fixture marked `prototype / DESIGN_ONLY`; M01–M15 each carry semantic_reason + reduced-motion; optical degradation chain + tiers; all 54 binding rows marked CODEX_BINDING_REQUIRED; all 66 actions carry the 9-field contract; visual regression zero errors; handoff entry present; no fake endpoint.

## Visual regression — `build/capture_all.py` → `14_visual_regression/regression_report.json`
- 44 screens × 8 viewports (1920/1440/1280/1024/768/430/390/360) + 1440 dark + per-screen 13-state board.
- **Structural errors = 0** (no unrendered ⟦key⟧, no horizontal overflow >2px, every screen reached ready).
- Critical screens at 130% zoom: AI-01 / CTH-01 / SH-01 / AI-02 / CTH-09 / BMP-01 horizontal overflow = **0px**.
- Screenshots captured under `prefers-reduced-motion` so metric count-ups rest at final values (light/dark numbers identical and deterministic).

## Smoke render — `build/smoke_render.py`
0 console/page errors; missing i18n keys = 0 in zh-CN/en/ko across AI-01, ACC-01, CTH-01, CTH-05 (calendar), SH-01, and the SH-01 state board (39 state cells).

## Interactive demo — `19_previews/experience-overview.mp4` (~31.9s, v2.4 editorial form + metal monochrome + orb)
Real interactions (motion enabled): composer input, AI-01→CTH-01→SH-01 navigation, optical HIGH→SOFT→OPAQUE degradation, SH-01 tab switching, zh→en→ko, light/dark, and a mobile 390 segment (step-chain swipe, adaptive dock) on a blurred backdrop. Plus `experience-overview.gif` (14s loop) and `experience-contact-sheet.jpg`; all-44-screen contact sheets `experience-all-screens-1..6.jpg`.

## What is intentionally NOT accepted here (honest boundaries)
- **No backend / no Runtime / no E2E**: 54 binding gaps and 66 actions (only NAVIGATION complete) are handed to Codex; nothing is marked VERIFIED from file existence.
- Dense per-screen business **fixture body** is zh-only representative DESIGN_ONLY data, replaced by the ViewModel; chrome/titles/states/actions are fully trilingual.
- Logo / launch animation = LOGO_DEFERRED.
- This report never implies Production Ready; the only token this layer emits is `DOUBAO_FRONTEND_HANDOFF=COMPLETE`.

## Reproduce
`verify_specs → generate → build_registries → smoke_render → capture_all → validate_handoff` (see `codex_handoff/MANIFEST.json` for exact commands and the real file inventory).
