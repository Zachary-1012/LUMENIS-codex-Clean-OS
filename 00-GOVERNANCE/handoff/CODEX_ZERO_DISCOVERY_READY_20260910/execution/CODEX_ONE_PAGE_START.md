# CODEX_ONE_PAGE_START (external-truth synchronized)

READ AGENTS → VERIFY FREEZE → READ RESUME_STATE → LOAD CURRENT TICKET PACK → IMPLEMENT → MINIMAL TEST → REQUIRED RUNTIME/E2E → EVIDENCE → COMMIT → UPDATE STATE → NEXT TICKET → CONTINUE UNTIL GATE → CONTINUE UNTIL CLOSURE

Current external truth:
- `GIT-001 = CLOSED_VERIFIED`; do not repeat `fc75d879 → ab676123` discovery.
- `FIRST_TICKET = GIT-002`.
- `handoff/codex-zero-discovery-ready-20260910` already exists remotely.
- Handoff package upload is not part of `GIT-002`; `GIT-002` only protects and pushes local dirty in-flight P0-D source work to a safe integration backup branch without touching `main`.
- Canonical runtime entry: `scripts/start_production.ps1 → run_supervised.py --host 0.0.0.0 --port 8201`; health probe `http://127.0.0.1:8201/healthz`.
- `RUNTIME-ENTRY-1` focuses on removing stale `$Root='D:\Taikoo-monitor-new'` and restoring repository-relative/configurable launch behavior without weakening existing idempotency/health/browser safeguards.

When `FREEZE_MATCH=YES`, do not rediscover the whole repository, do not reread all 301 DB rows, do not reclassify the 60 failures, do not redo five-repo research, and do not redesign the architecture.

Stop conditions are defined by `CODEX_CONTINUOUS_CLOSURE_PROTOCOL.md`; Gate transitions by `CODEX_GATE_TRANSITION_MAP.json`; Production Closure by `CODEX_FINAL_CLOSURE_CONTRACT.json`.
