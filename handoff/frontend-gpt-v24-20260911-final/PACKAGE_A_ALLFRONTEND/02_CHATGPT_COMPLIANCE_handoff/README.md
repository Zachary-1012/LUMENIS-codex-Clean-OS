# ChatGPT / MCP Public-Distribution Compliance — Codex Handoff

Status: **PARTIAL** (audit + proposed contracts ready; public layer not implemented).
Owner split: Doubao = audit/proposed contracts only; **Codex = Production Code Owner** for any backend/MCP/auth implementation.
Generated: 2026-09-11T15:49:51+08:00
Working repo: `Zachary-1012/LUMENIS-codex-Clean-OS` (local `D:\LUMENIS_REBUILD\LUMENIS-codex-Clean-OS`)
HEAD at audit: `ab67612367c172ced2dff62b44e98de86469d1e6` (branch `main`). Word snapshot base `31c68a942d639cd1c48fb6d37e025b9447504ef0` = explained DRIFT, not rolled back.

## Read in this order
1. `00_VERIFIED_REPO_STATE.md` — real git state, entrypoints, what exists / does not.
2. `01_COMPLIANCE_GAP_MATRIX.md` — WP0-WP9, rules A-K, gates G0-G10, each with evidence.
3. `04_OPEN_BLOCKERS.md` — what only a human / legal / Codex can close.
4. `proposed/` — editable contracts & drafts (NOT wired into production).
5. `05_NEXT_CODEX_PROMPT.md` — paste-ready first instruction for Codex.
6. `03_TEST_EVIDENCE.md` + `evidence/` — real commands / outputs.
7. `handoff_state.json` — machine-readable index (not a new source of truth).

## Hard rules carried from the plan (do not violate when implementing)
- Do NOT delete the internal Collector to satisfy ChatGPT; do NOT expose Browser/CDP/Cookie/Session/raw-DB as public tools.
- Public layer calls only **versioned internal contracts**; the model must never recompute Production Metrics.
- Every public tool gets explicit `readOnlyHint / openWorldHint / destructiveHint` traced from the real handler. MCP defaults are pessimistic (readOnly=false, destructive=true, openWorld=true), so an unannotated tool is treated as dangerous.
- Legal text is an engineering DRAFT only: every legal conclusion is `TODO(LEGAL)`.
- Output only READY_FOR_CODEX / PARTIAL / BLOCKED. Never fake READY.

## Editing convention
- `*.json` are standard JSON (JSON-Schema style, 2-space, no comments). Field-level explanations live in the adjacent `*.proposed.md`, so a human can edit the JSON safely.
- `TODO(CODEX)` = implementer action; `TODO(LEGAL)` = lawyer; `TODO(HUMAN)` = account/credential/verification.
