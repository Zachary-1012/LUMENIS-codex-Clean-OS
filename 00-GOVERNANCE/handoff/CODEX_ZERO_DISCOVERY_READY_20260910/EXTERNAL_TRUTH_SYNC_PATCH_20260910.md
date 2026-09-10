# External Truth Sync Patch — 2026-09-10

This is a narrow current-truth override for Codex. It does **not** authorize repository-wide rediscovery.

- `GIT-001 = CLOSED_VERIFIED`; do not repeat the audited `fc75d879 → ab676123` compare unless a newer explicit main drift exists.
- `FIRST/current = GIT-002`; it has no GIT-001 dependency and only reviews/backs up the already-dirty P0-D local work to a safe integration branch. No main push/force.
- The handoff branch already exists. Its HEAD is dynamic because governance imports advance it; resolve the ref at session start instead of pinning `c8a57c0`.
- Canonical production launch: `powershell scripts/start_production.ps1` → `run_supervised.py`, default `0.0.0.0:8201`; `/healthz` probe uses `127.0.0.1:8201`. `run_production.py` is legacy, not the start command.
- `RUNTIME-ENTRY-1` owns only launcher portability (remove machine-specific absolute paths) and must close before RC; it must not broaden into business routes/Evidence/FK/database work.
- Executable ticket universe = 41: P0=20, P1=18, P2=3 in the source package; GIT-001 is closed, so P0 remaining=19. Current FIRST_TICKET=GIT-002.
- Known runtime evidence remains `/healthz=200`, `/lumenis/cth/overview=200`, `/api/runtime/identity=404`, `/lumenis/bmp/overview=404` until re-tested after fixes.
- The binary master checklist is an older 40-ticket source snapshot. Preserve it as evidence; do not use it to override normalized execution JSON/current truth.
- On session start, verify only three cheap freeze anchors: work HEAD, `git status --short`, protected DB sha256. If they match, reuse the frozen 301 DB map, 60 failure matrix, five-repo research and architecture without re-discovery.
- Handoff import changes governance/evidence only: no product source, tests, real DB, secrets or `main` mutation.

Codex read order: `execution/CODEX_ONE_PAGE_START.md` → `execution/CODEX_RESUME_STATE.json` → current ticket pack → only its scoped context. Historical snapshots lose to current runtime/test/source evidence and `execution/CURRENT_TRUTH_OVERRIDE_20260910.json`.
