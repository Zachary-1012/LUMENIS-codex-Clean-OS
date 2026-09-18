# 02 — Change Manifest

Principle: minimal safe change. **No tracked production source / test / DB / config was modified.**

## In-repo additions (untracked, additive handoff artifacts only)
Everything under `docs/handoff/chatgpt-plugin-compliance-doubao-v1/` (this folder).
These are documents and *proposed* contracts — they are NOT imported by the application and change no runtime behavior.

## Content fix outside git (delivered package, not the repository)
| File | Change | Why | Rollback |
|---|---|---|---|
| `D:\LUMENIS_REBUILD\_handoff_build\LUMENIS_EXPERIENCE_HANDOFF_20260911_ab67612\LUMENIS_EXPERIENCE_V2.4.1_QA_CORRECTION\03_I18N\hardcoded_copy_before.json` | 18 invalid `\'` escapes corrected to `'` (legal `\"`/`\\` preserved) | File failed JSON.parse (screenshot errors at lines 85/90/100); minimal syntax-only fix, no business field removed/renamed | Re-extract the original copy from `LUMENIS_EXPERIENCE_HANDOFF_20260911_ab67612.zip` |

## Explicit non-changes
- No Collector / browser / cookie / session code touched or deleted.
- No DB opened, no migration, no write to any real database.
- No dependency install/upgrade; no README/AGENTS/Governance edit; no git add/commit/push/checkout.
- No public MCP server implemented (ownership: Codex).

## Supplement counters (syntax / JSON repair mandate)
| Metric | Value |
|---|---|
| syntax_errors_found | 0 (JS/Python/CSS/HTML/YAML all clean on first full scan) |
| syntax_errors_fixed | 0 |
| json_errors_found | 18 invalid-escape occurrences (1 file) |
| json_errors_fixed | 18 |
| schema_mismatches | 0 in owned frontend (`validate_handoff` 34/34); public contracts not yet implemented -> n/a |
| new_config_parse_failures | 0 |
| remaining_blocked | see `04_OPEN_BLOCKERS.md` |
