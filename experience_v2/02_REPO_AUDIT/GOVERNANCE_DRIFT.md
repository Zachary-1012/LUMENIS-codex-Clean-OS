# Governance Drift (record-only, not modified)

Captured 2026-09-11. Doubao does not edit README/AGENTS/Governance; this only records drift for Codex.

## Current product truth baseline
- Product: 序境 / LUMENIS — Production Core · Production Truth Owner.
- Canonical repo: Zachary-1012/LUMENIS-codex-Clean-OS @ main `ab67612`.
- Authoritative for experience work: current README + Production Acceptance Master Checklist + current real source + the four scope documents (Master Plan docx/pdf, Frontend Addendum, Red-line xlsx) and V2.5 Design Ecosystem directive.

## Observed drift (GOVERNANCE_DRIFT)
1. **Historical product naming**: parts of AGENTS/history reference earlier CorTech / Z-Brand product definitions. These are legacy and must NOT override the current 序境/LUMENIS definition. No file was changed.
2. **Docs vs runtime**: any README/Registry claim of "complete" is not treated as runtime evidence; capability status is decided by source + runtime + tests (per user red-line). Several registries still carry MULTIPLE/PARTIAL/UNKNOWN — preserved, not auto-closed.
3. **Migration ownership (carry-over)**: manual `database_migrations.py` is the real v0→v12 chain; Alembic is stamp-only baseline; CAP-DB-002 = MULTIPLE. Left for Codex decision (P0C-H), not resolved by experience work.
4. **Old logo/visual identity**: legacy "liquid droplet sea / Opal Lilac (#B8A8FF) / Deep Indigo / Pale Gold" identity conflicts with the current black-silver/white-silver metallic language. Legacy is archived as evidence only; current = monochrome metallic + single Icy point (see LUMENIS_BRAND_COLOR_V2.5.md).
5. **Design branch**: V2.5 directive proposes `design/lumenis-design-ecosystem-v25-20260911`; it was NOT created/pushed by Doubao (user decision). Work currently lives in untracked `experience_v2/`.

## Action for Codex
Reconcile naming/ownership in governance docs after P0-C closure; do not let legacy definitions re-enter the current experience or runtime truth.
