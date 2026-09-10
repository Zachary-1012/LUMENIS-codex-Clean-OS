# CODEX_ONE_PAGE_START — CURRENT TRUTH OVERRIDE
generated 2026-09-10 22:55 +08:00

READ AGENTS → VERIFY WORKTREE FREEZE → READ RESUME_STATE → LOAD CURRENT TICKET PACK → IMPLEMENT → MINIMAL TEST → REQUIRED RUNTIME/E2E → EVIDENCE → COMMIT → UPDATE STATE → NEXT TICKET → CONTINUE UNTIL GATE → CONTINUE UNTIL CLOSURE

Current executable truth:
- `GIT-001 = CLOSED_VERIFIED`; never repeat `fc75d879 → ab676123` repository discovery.
- `FIRST_TICKET = GIT-002`; GIT-002 has no dependency on GIT-001 and only protects/pushes the existing local dirty P0-D work to a safe integration backup branch. It does not upload handoff artifacts.
- `handoff/codex-zero-discovery-ready-20260910` already exists remotely. Do not pin an old handoff HEAD; resolve the branch HEAD at session start because governance imports advance it.
- Canonical runtime entry is `powershell scripts/start_production.ps1` → `run_supervised.py`, default `0.0.0.0:8201`; health probe is `http://127.0.0.1:8201/healthz`.
- `run_production.py` is legacy/redirect-only context, not the production start command.
- `RUNTIME-ENTRY-1` is the scoped launcher-portability ticket; it must remove machine-specific absolute paths without changing business routes, Evidence, FK logic, or production DB.
- Ticket universe = 41 including historical closed `GIT-001` and `RUNTIME-ENTRY-1`; executable remaining counts come from `CODEX_RESUME_STATE.json`, not the stale binary workbook snapshot.

When `FREEZE_MATCH=YES`, do not rediscover the full repository, reread all 301 DB anchors, reclassify the 60 known failures, redo five-repo research, or redesign the architecture. Only verify drift relevant to the current ticket.

Historical/source snapshots may contain earlier values. For execution, this file + `CODEX_RESUME_STATE.json` + current ticket pack + `CURRENT_TRUTH_OVERRIDE_20260910.json` take precedence.
