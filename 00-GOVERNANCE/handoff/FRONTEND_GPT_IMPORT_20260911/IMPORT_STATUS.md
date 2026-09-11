# Canonical Source Import Status

Status: **CURATED / LOCALLY VALIDATED / IMPORT GATE OPEN**

Latest source package: 1331 entries, SHA-256 `c4bbb60c3e21db88d3f271ff63359dd845e052aaf69911aa554bb1a3fdcf202c`.

Legacy evidence package: 273 entries, SHA-256 `0e45ab95481de42462b291917cbbc4452e1b07f2dafb7a055776f3bf5c26d4a9`.

Curated canonical editable set: **111 files**. It contains Experience source/design/contracts/build specs/integration/validation, GPT/MCP compliance handoff and Legacy provenance/index evidence. Generated screens, large screenshots/media, duplicate production templates/static and legacy UI implementations are intentionally excluded from editable truth.

Validation before staging: 44/44 screen specs; 34/34 handoff validation; JSON parse errors 0; Python compile errors 0; JavaScript syntax checks PASS; common secret-token heuristic 0 hits.

## Fail-closed import rule

The current branch contains an unpacker/index from an earlier staging step, but the complete canonical payload transport must be present and SHA-verified before that unpacker is treated as executable delivery. **Missing/incomplete payload = STOP, not reconstruction.** Never recreate missing Experience/GPT source from memory, screenshots or Legacy evidence.

This is intentionally not called Production Ready. After verified import: reconcile current-main drift, calibrate/bind AI-01 + CTH-01, run Critical E2E, then proceed through remaining bindings and Production Acceptance.