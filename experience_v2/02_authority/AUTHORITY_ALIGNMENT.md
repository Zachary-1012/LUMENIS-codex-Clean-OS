# Authority Alignment — Experience V2

> **V3 supersession notice (2026-09-18):** The canonical presentation authority is now 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION-V3-20260918.md. The DONE rows below prove compliance with the earlier V2 package only; they do not prove V3 anti-template compliance. A source audit at main@17570ae found repeated generic section signatures and a fixed-composer rule that can force unrelated workflows into the same dashboard grammar. Current status is therefore **V3 AUTHORITY ACTIVE / MIGRATION REQUIRED** until the strict anti-template gate passes. See ANTI_TEMPLATE_BASELINE_V3.json.

Maps each requirement in the four remote governance docs (main `b910117`, `00-GOVERNANCE/*20260911.md`) to the concrete implementation here. Read-only compliance trace; the governance docs themselves are not modified.

| Authority requirement | Where implemented | Status |
|---|---|---|
| Isolate to `experience_v2/**`; namespaced `.lum-app/.lum-*/--lum-*` | all assets + generated pages | DONE |
| HTML+CSS+Vanilla/ESM, Jinja-friendly; no React/Vue for effect | `10_prototype/assets/*` | DONE |
| Clean-room; no copied visual/asset; original icons | `13_research`, `15_provenance_licenses`, `assets/icons.js` (~80 original stroke icons) | DONE |
| UX chain Context→Observe→Understand→Evidence→Decision→Action→Outcome→Evaluation | screen section order + `03_ia_and_flows` | DONE |
| POINT/LINE/SURFACE/SCREEN/WORKFLOW hierarchy | `04_design_system/PATTERN_REGISTRY.json` (PAT-*) | DONE |
| Material A truth opaque / B controlled glass / C optical only AI Composer, active dock bubble, task morph, transient tool dock; degrade OPTICAL→SOFT GLASS→OPAQUE | `assets/optical.css` + `optical.js` (OPT-01..04 only) | DONE |
| M01–M15 canonical motion; timing bands; reduced-motion; semantic reason | `06_motion/MOTION_REGISTRY.json`, `assets/motion.js` | DONE |
| 8 viewports adaptive reflow (not scale) | `09_responsive`, `assets/shell.css`, `14_visual_regression` | DONE |
| 44 screens | `build/src/screens_meta.py` (assert ==44), `07_screens` | DONE |
| Dual benchmark AI-01 + CTH-01 internal calibration before continuing | both hand-tuned; regression critical set | DONE |
| Handoff entry `experience_v2/19_handoff/INTEGRATION_START_HERE.md` | file present | DONE |
| Exact design tokens V2 §9/§10 (light/dark, type scale, weights) | `assets/tokens.css`, `04_design_system/design-tokens.json` | DONE |
| 16 component states | `05_components/COMPONENT_REGISTRY.json`, `components.js STATE_ORDER` (13 non-ready + ready) | DONE |
| Icons 24×24, 1.5–2 stroke, round, currentColor | `assets/icons.js` | DONE |
| AI nine states BOOT…EVALUATION; artifact-first; no fake thinking animation | AI-01/AI-02 specs, `motion.js`, state boards | DONE |
| Capability status six enums | contracts + SH-01/AI specs | DONE |
| State source four enums (backend / frontend-derived / user-input / DESIGN_ONLY fixture) | every fixture `state_source` | DONE |
| Action 9-field contract | `12_contracts/ACTION_REGISTRY.json` | DONE |
| Six Ports (ViewModel/Capability/State/Action/Permission/Evidence) | `12_contracts/*_REGISTRY.json` | DONE |
| 14 Experience acceptance gates | `18_validation/validate_handoff.py` | DONE |
| Content creation chain + 6 Pattern Registries + factuality wall + scoped retrieval + cross-format + trilingual semantic | SH-01 flagship, `12_contracts`, SH-01 viewmodel | DONE (design/contract; backend = CODEX_BINDING_REQUIRED) |
| Research 8 sources, per-source reusable principle only; motion-scene asset shape | `13_research/experience_research_source_registry.json`, RESEARCH_FINDINGS | DONE (Uiverse source 403 recorded, not bypassed) |
| Logo / launch animation | not built | LOGO_DEFERRED (explicit user instruction) |

## Drift / honesty notes
- Frozen local checkout `ab67612` vs remote `b910117`: 5 commits, docs/governance only, zero source diff — see `01_repo_audit/canonical_head_drift_20260911.json`.
- Chrome/title/state/action copy is fully trilingual (164 keys, 0 missing). Dense per-screen business fixture **body** is zh-only representative data, intentionally replaced by the backend ViewModel; this is recorded in every fixture and the integration guide, not claimed as complete localization.
- No capability is marked VERIFIED from file existence; all data-backed surfaces are `PARTIAL` + `CODEX_BINDING_REQUIRED`.
