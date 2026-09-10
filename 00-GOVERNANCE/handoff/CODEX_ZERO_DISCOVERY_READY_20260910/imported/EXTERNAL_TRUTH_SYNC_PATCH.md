# LUMENIS — External Truth Sync Patch

Purpose: apply only the final external-truth delta before Codex implementation. Do **not** restart repository-wide discovery.

## Verified corrections

1. `GIT-001` is already externally verified and must be treated as `CLOSED_VERIFIED`.
2. `FIRST_TICKET` must be `GIT-002`.
3. Remove `GIT-002` blocking dependency on `GIT-001`.
4. `handoff/codex-zero-discovery-ready-20260910` already exists remotely.
5. Verified handoff HEAD before this package import: `c8a57c095d2f84a02e175c826276fe7594726e35`.
6. Handoff package upload is no longer part of `GIT-002`; `GIT-002` should only protect and push the local dirty in-flight P0-D source work to an appropriate safe integration backup branch without touching `main`.
7. Canonical production runtime entry is `scripts/start_production.ps1 -> run_supervised.py --host 0.0.0.0 --port 8201`; local health probe is `http://127.0.0.1:8201/healthz`.
8. `RUNTIME-ENTRY-1` should focus on removing the stale absolute root `D:\Taikoo-monitor-new` and making the launcher repository-relative/configurable while preserving idempotency, safety guards, health checks, and resident-browser behavior.
9. Update only the affected Freeze / Resume State / DAG / One Page Start / GIT-001 / GIT-002 execution artifacts after reconciling against the current branch HEAD.
10. Re-run the handoff self-check after the patch. Preserve every existing `UNKNOWN`, `BLOCKED`, or `NOT_PASS` unless new evidence resolves it.

## Hard rules

- No product-source rewrite in this patch.
- No production DB mutation.
- No force push or direct `main` write.
- No full repository rediscovery when Freeze still matches aside from this known handoff-only drift.
- Do not declare Production Ready from document existence alone.
