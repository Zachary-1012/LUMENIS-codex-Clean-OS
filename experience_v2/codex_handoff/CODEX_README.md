# LUMENIS Experience V2 — Codex Handoff (ten registries)

All machine registries are mirrored in this folder; the authoritative generated copies live in their domain folders. Start at `../19_handoff/INTEGRATION_START_HERE.md`.

| Registry | File | Purpose |
|---|---|---|
| Manifest | MANIFEST.json | full inventory, counts, freeze, build commands |
| Screen | SCREEN_REGISTRY.json | 44 screens id/domain/trilingual title/icon/dock |
| Component | COMPONENT_REGISTRY.json | foundation/data/AI components + 16 states + renderer map |
| Copy | COPY_REGISTRY.json | zh-CN/en/ko key registry with parity flags |
| Motion | MOTION_REGISTRY.json | M01–M15 canonical names, timing band, semantic reason, reduced-motion |
| Pattern | PATTERN_REGISTRY.json | PAT-* composition patterns and which screens use them |
| ViewModel | VIEWMODEL_REGISTRY.json | per-screen VM shape + current binding + unknown keys |
| Action | ACTION_REGISTRY.json | 9-field action contract, 4 action classes |
| Binding Matrix | BINDING_MATRIX.json | field-level frontend→backend binding rows |
| Unknown | UNKNOWN_LIST.json | every unresolved binding (preserved, never guessed) |

## Ownership
- Doubao = Experience Layer owner (only `experience_v2/**`). Codex = Production Code owner. Other models advisory only.
- Frontend status per capability = `PARTIAL / READY_DESIGN_ONLY`; backend column = `CODEX_BINDING_REQUIRED`.
- Completion token emitted by this layer: `DOUBAO_FRONTEND_HANDOFF=COMPLETE`. It never implies Production Ready.

## Binding order (dependency DAG, frontend slice)
Repository freeze → Design System/Component/Motion (done) → AI-01+CTH-01 calibration slice → SH-01 content production slice → remaining CTH → BMP → AI → Shared → System → Account → 13-state wiring on every bound screen → Critical E2E → six acceptance gates.
