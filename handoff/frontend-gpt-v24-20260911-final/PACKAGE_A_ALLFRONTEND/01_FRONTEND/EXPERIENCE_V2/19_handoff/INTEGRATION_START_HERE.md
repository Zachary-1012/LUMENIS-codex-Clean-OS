# CODEX INTEGRATION START HERE — LUMENIS Experience V2

> First screen for Codex. Read this before touching anything. Detailed evidence is linked, not inlined.
> Status token is **DOUBAO_FRONTEND_HANDOFF** — this is NOT Production Ready and NOT Runtime/E2E verified.

## WHERE WE ARE
- Experience Layer (this directory `experience_v2/`) is a **greenfield, isolated** prototype: 44 screens, self-built design system + optical/motion runtime, zero third-party UI runtime, zero copied assets.
- Built against frozen local checkout `ab67612`; latest remote `main` = `b910117` (5 commits, **docs/governance only, zero source change**). Evidence: `01_repo_audit/canonical_head_drift_20260911.json`.
- Tech: static HTML + CSS + Vanilla ESM (Jinja-friendly). Do **not** add React/Vue for effect. All selectors namespaced `.lum-app / .lum-* / --lum-*`.

## WHAT IS ALREADY VERIFIED (frontend only)
- 44/44 specs build; runtime renders with **0 console/page errors**; i18n **zh-CN/en/ko parity = 164/164 keys, 0 missing** on every screen.
- Structural regression across **8 viewports** (1920/1440/1280/1024/768/430/390/360) + dark + per-screen 13-state boards: `14_visual_regression/regression_report.json`.
- Optical material tiers + degradation HIGH→STANDARD→SOFT_GLASS→OPAQUE; `prefers-reduced-motion` fallback on every M01–M15.
- Content production flagship **SH-01** implements the Content Creation Learning Contract (10-stage chain, 6 Pattern Registries, factuality wall, scoped retrieval, cross-format reuse, artifact-first AI marked DESIGN_ONLY).

## WHAT IS NOT VERIFIED / NOT DONE
- No backend is wired. Every data section is `DESIGN_ONLY fixture`. **54 binding gaps** in `12_contracts/BACKEND_GAP.json` — each says exactly which screen/field needs a real endpoint+permission+evidence. Do not invent APIs; map to the real backend.
- Actions: 66 total; only NAVIGATION is frontend-complete. QUERY/EFFECT are `CODEX_BINDING_REQUIRED` (9-field contract in `12_contracts/ACTION_REGISTRY.json`).
- Body business fixture copy is intentionally zh-only representative data (it is replaced by the ViewModel); chrome/titles/state/actions are fully trilingual.
- Logo / launch animation **DEFERRED by explicit user instruction** (LOGO_DEFERRED); spec pointer in `02_authority`.

## FIRST TICKET (start here)
1. Open `10_prototype/index.html` (SPA) and `07_screens/SH-01/SH-01.html` (standalone) to see the target.
2. Read `12_contracts/VIEWMODEL_REGISTRY.json` + `11_integration_skeleton/INTEGRATION_GUIDE.md` + `server_binding_adapter.example.py`.
3. Bind **one** vertical slice end-to-end first: **AI-01 → CTH-01** (the two calibration benchmarks): replace fixtures with real ViewModels, wire their EFFECT/QUERY actions, keep all 13 states + evidence links.
4. Then proceed screen-by-screen following `codex_handoff/MANIFEST.json` dependency order; each screen's folder is self-contained (spec/fixture/viewmodel/actions/state-board).

## HOW TO RUN / TEST / PROVE PASS
- Run prototype: open `10_prototype/index.html` (no build step). Regenerate after editing `build/src`: `python build/generate.py` then `python build/build_registries.py`.
- Re-verify frontend: `python build/verify_specs.py`, `python build/smoke_render.py`, `python build/capture_all.py`.
- Pass for a screen = real ViewModel bound, all non-ready states reachable from real backend state, every claim linked to evidence, permission enforced server-side, no ⟦missing⟧ marker, no horizontal overflow at 8 viewports, zh/en/ko parity kept.
- Production is allowed ONLY after the six acceptance gates (`17_acceptance`): P0=0, Repository Integrity, Production Truth, Runtime+Critical E2E, Security/Recovery, Release Lineage+Rollback.

## WHAT NOT TO TOUCH
- Do not modify anything outside `experience_v2/` from the experience side. Do not delete legacy code by filename. Do not fake 200 / silent fallback / mock-as-runtime. Do not drop UNKNOWN. Do not force-push or overwrite `main`.

## DIRECTORY MAP
- `10_prototype/` runnable app (assets runtime + data generated + index) · `07_screens/<id>/` per-screen contract package
- `04_design_system` `05_components` `06_motion` registries · `12_i18n` copy registry/drift · `12_contracts` six-Port contracts
- `11_integration_skeleton` adapter stub · `codex_handoff/` ten registries (one-place) · `14_visual_regression` shots+report · `19_previews` overview media
