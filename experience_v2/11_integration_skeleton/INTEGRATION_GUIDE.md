# Integration Skeleton — Codex binding guide

1. The experience layer (`10_prototype`) is static HTML + CSS + Vanilla ESM, Jinja-friendly. Do NOT introduce React/Vue for effect.
2. Each screen has, in `07_screens/<id>/`:
   - `<id>.viewmodel.json` — exact shape the UI renders (`viewmodel`) and where each field comes from today (`binding`).
   - `<id>.actions.json` — the 9-field Action Contract; EFFECT/QUERY actions are CODEX_BINDING_REQUIRED.
   - `<id>.fixture.json` — DESIGN_ONLY data to replace (never ship as production data).
3. Backend returns the SAME view-model shape (see `binding_contract.schema.json`); use `server_binding_adapter.example.py`.
4. SubjectContext eight fields travel with every request; server RE-VERIFIES authorization. Switching subject changes view context only, never data ownership.
5. State: backend supplies a state per section (ready/loading/partial/stale/…). The UI already renders all 13 non-ready states — do not fake 200.
6. Evidence: every factual claim links Source->Evidence->Canonical; unresolved facts stay UNKNOWN.
7. Isolation: all experience code stays under `experience_v2/**`; backend files are read-only to this layer.
