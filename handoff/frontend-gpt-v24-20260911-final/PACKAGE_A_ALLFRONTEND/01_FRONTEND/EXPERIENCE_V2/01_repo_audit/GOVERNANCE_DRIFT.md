# Governance / Copy Drift Log (read-only evidence, no source file modified)

## DRIFT-001 Subject Context semantic drift
- Legacy baseline wording (`LUMENIS_NEW_PRODUCT_DESIGN_BASELINE_V1.md` sec2):
  CTH = Subject-first; BMP = Brand-first / Primary Focus.
- Current canonical `README.md` (sec2 统一主体上下文):
  BOTH CTH and BMP support **Selected Subject**;
  Selected Subject -> Domain Lens -> Scope/Permission -> Query/Function/Metric -> View Model -> UI.
  CTH = Selected Subject + Commerce Operations Lens;
  BMP = Selected Subject + Brand & Market Lens (brand no longer the only legal subject).
- Experience decision: use ONE **Global Subject Context** at presentation layer
  (GLOBAL SUBJECT CONTEXT -> Commerce Operations Lens=CTH UI / Brand & Market Lens=BMP UI).
- Backend modification: NONE.
- Backend contract: CODEX_REVERIFY_REQUIRED.

## DRIFT-002 Korean locale legacy confirmed_terms
- `static/locales/ko.json` -> `_meta.confirmed_terms` still lists
  "Commerce & Trading Hub / Brand Monitoring Platform" (legacy public names).
- domain.cth / domain.zbmp values are already current. Existing locale is therefore NOT a clean Copy Authority.
- Handling: build copy-registry + zh/en/ko delta; do NOT edit production locale. Owner of production merge: CODEX.

## DRIFT-003 base.html legacy UI pollution is real
- base.html loads 8 legacy design CSS (zbc-design-*, xujing-core, lumenis-global-design, adaptive-*) plus inline CSS and hard-coded legacy business names.
- Handling: new shell does not extend/import/copy base.html; isolated namespace .lum-app / lum-* / --lum-*.

## DRIFT-004 Phase wording
- README CURRENT PHASE = PRODUCTION CONVERGENCE; six production gates required before Production Ready.
- This work may only conclude DOUBAO_EXPERIENCE_HANDOFF=COMPLETE, never LUMENIS_PRODUCTION=COMPLETE.

## DRIFT-005 Mixed legacy product names across HTML/JS/locales/docs
- ZBC / Brand Intelligence / Commerce & Trading Hub / Brand Monitoring Platform coexist with new Commerce Operations / Brand & Market.
- Recorded per occurrence in 12_i18n/copy-drift.json; production cleanup owner = CODEX.
