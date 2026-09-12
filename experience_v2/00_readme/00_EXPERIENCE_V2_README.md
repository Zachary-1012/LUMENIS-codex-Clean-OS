# LUMENIS / 序境 — Experience V2 (Production Experience Layer)

Greenfield, isolated experience layer. **Doubao owns only `experience_v2/`; Codex owns production code.** Nothing here is wired to a backend; every data surface is a `DESIGN_ONLY fixture` replaced later by a Codex ViewModel. Completion token is `DOUBAO_FRONTEND_HANDOFF=COMPLETE` — never Production Ready.

## What this layer delivers
1. A self-contained **design system** (tokens, optical materials, typography, spacing, color, elevation), **component library**, and **motion system** — all original, zero third-party UI runtime, zero copied assets.
2. **44 screens** across Account / CTH (Commerce Operations) / BMP (Brand & Market) / AI / System / Shared, each with a full per-screen contract package and 13 non-ready states.
3. A runnable **prototype SPA** (`10_prototype/index.html`) + per-screen standalone pages, trilingual chrome (zh-CN / en / ko), 8-viewport adaptive reflow, light/dark.
4. **Codex integration contracts**: ViewModel / Action / Permission / Evidence / Capability / State ports, a binding matrix with every unknown preserved, and an adapter skeleton.

## Entry points
- **Codex start here → `../19_handoff/INTEGRATION_START_HERE.md`**
- Runnable app → `../10_prototype/index.html`
- Per-screen package → `../07_screens/<ID>/` (spec / fixture / viewmodel / actions / state-board / html)
- Validation → `../18_validation/validate_handoff.py` (writes `../17_acceptance/validation_report.json`)

## Directory map
| Folder | Contents |
|---|---|
| 00_readme | this entry |
| 01_repo_audit | frozen HEAD, remote drift evidence |
| 02_authority | governance/design-authority alignment |
| 03_ia_and_flows | information architecture + user flows |
| 04_design_system | tokens + pattern registry + doc |
| 05_components | component registry + doc |
| 06_motion | M01–M15 motion registry + guidelines |
| 07_screens | 44 × per-screen contract package |
| 09_responsive | 8-viewport reflow rules |
| 10_prototype | runnable SPA + assets runtime + generated data |
| 11_integration_skeleton | binding schema + adapter stub + integration guide |
| 12_contracts | six-Port contracts, binding matrix, unknown list, backend gap |
| 12_i18n | copy registry, deltas, drift (banned legacy terms), usage map |
| 13_research | clean-room research learning assets (research-only, never shipped) |
| 14_visual_regression | 8-viewport + dark + state-board shots, regression report |
| 15_provenance_licenses | provenance manifest / sealed references |
| 16_versioning | version & change log |
| 17_acceptance | validation report / acceptance gate results |
| 18_validation | deterministic self-check script |
| 19_previews | overview images / demo media |
| 19_handoff | Codex integration start |
| build | idempotent generators + specs |
| codex_handoff | ten registries mirrored in one place |

## Build pipeline (idempotent, in order)
```
python build/verify_specs.py        # 44 specs structural check
python build/generate.py            # data/*.js + SPA + 44 screen packages
python build/build_registries.py    # design/component/motion/contract registries
python build/smoke_render.py        # headless render, 0 console error / 0 missing key
python build/capture_all.py         # 8 viewport + dark + state-board regression
python 18_validation/validate_handoff.py
```

## Hard rules honored
- HTML + CSS + Vanilla ESM only (Jinja-friendly); no React/Vue for effect; namespaced `.lum-* / --lum-*`.
- 70% information clarity / 20% spatial material / 10% motion; every motion has a semantic reason + reduced-motion fallback; optical material degrades HIGH→STANDARD→SOFT_GLASS→OPAQUE; data/evidence/report surfaces stay opaque.
- No fake 200 / silent fallback / mock-as-runtime; UNKNOWN preserved; every claim links to evidence or is marked UNKNOWN.
- Content production follows Brief→Context→Evidence→Strategy→Create→Review→Approval→Export→Evaluation→Learning; never prompt→copy.
- Logo / launch animation deferred by explicit instruction (LOGO_DEFERRED).
