# LUMENIS / 序境 — Codex Handoff (ALL frontend + ChatGPT compliance)

Generated 2026-09-11T16:01:15+08:00 · canonical repo HEAD `ab67612` (main) · status **PARTIAL** (ready for Codex; not public-ready).

## 01_FRONTEND  — ALL product frontend (not only this round)
- `CURRENT_PRODUCTION_UI/templates/` + `CURRENT_PRODUCTION_UI/static/` — the EXISTING production UI shipped by the Flask app (55 templates; static is byte-identical to Z-Brand-Core, so only one copy is bundled).
- `EXPERIENCE_V2/` — new Experience Layer (823 files; 44 screens, M01-M15, contracts, i18n, fixtures, validation 34/34, previews).
- `INTERNAL_BROWSER_SCRIPTS/` — four root *.js collector/browser-injection scripts. INTERNAL automation, NOT public UI and NOT for the ChatGPT layer.
- `_LEGACY_REFERENCE/ZBC_templates/` — Z-Brand-Core legacy template variants (content differs from current). CAPABILITY EVIDENCE ONLY — recover capability, do not copy obsolete UI.
- `_V2.4.1_QA_CORRECTION/` (one JSON, 18 invalid escapes fixed) and `_DELIVERY/` (11-sheet checklist).

## 02_CHATGPT_COMPLIANCE_handoff
Audit + PROPOSED contracts. Read `README.md` then `00..05`, `handoff_state.json`, `proposed/`;
Codex executes CPLG-01..07 per `05_NEXT_CODEX_PROMPT.md`.

## Hard acceptance
JSON_PARSE_ERRORS=0 · SYNTAX_ERRORS=0 · NEW_CONFIG_PARSE_FAILURES=0 · secret scan 0/367.

## Ownership
Doubao = Experience Layer + audit/proposed contracts. Codex = Production Code Owner.
Legal/demo/verification/third-party rights stay BLOCKED (see 04_OPEN_BLOCKERS.md).
Re-run git truth before editing; this bundle is an evidence index, not a new source of truth.

## 03_LEGACY_DELIVERY_EVIDENCE
Unique historical evidence from earlier packages (271 files, 42.26 MB), folded in for 100% completeness; read-only history, current source always wins.
