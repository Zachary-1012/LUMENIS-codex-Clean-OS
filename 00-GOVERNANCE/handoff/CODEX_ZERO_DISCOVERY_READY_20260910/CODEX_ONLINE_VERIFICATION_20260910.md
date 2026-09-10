# CODEX ONLINE VERIFICATION PATCH — 2026-09-10

This file records facts independently re-verified against the current GitHub repository before synchronizing the handoff package. It supersedes conflicting handoff fields.

## 1. Canonical main source drift resolved
- Repo: `Zachary-1012/LUMENIS-codex-Clean-OS`
- Base used by local audit: `fc75d87938f3631bec99338c9e059eca34c6a680`
- Current online main: `ab67612367c172ced2dff62b44e98de86469d1e6`
- GitHub compare: ahead by 5 commits, behind 0.
- Final file delta contains only:
  - `00-GOVERNANCE/handoff/LUMENIS_Doubao_PreProduction_Audit_to_Codex_Handoff.md`
  - `00-GOVERNANCE/handoff/LUMENIS_P0-D_Codex_Closure_Handoff.md`
- **No product source-code file changed in this range.**
- Therefore `GIT-001` is `CLOSED_VERIFIED`; Codex must not spend quota re-running full discovery for this drift.

## 2. Canonical production runtime entry corrected
Online source at `ab67612367c172ced2dff62b44e98de86469d1e6` proves:
- `run_production.py` is explicitly marked **LEGACY** and redirects operators to `scripts/start_production.ps1`.
- `scripts/start_production.ps1` is the stated unified production launcher.
- It starts `run_supervised.py --host 0.0.0.0 --port 8201`.
- It currently hard-codes `$Root = 'D:\Taikoo-monitor-new'`.

This is a real portability/clean-clone blocker. New ticket: **RUNTIME-ENTRY-1**.

## 3. Optimized Codex start
1. `GIT-002`: protect the current local dirty/untracked P0-D work and push an integration backup branch.
2. `RUNTIME-ENTRY-1`: make the canonical production launcher repo-relative/configurable and lock the 8201 runtime contract.
3. Start the already-prepared DB/test/P0 tickets in the dependency DAG; no repository-wide rediscovery.

## 4. Remaining targeted evidence work is not “full discovery”
- `ROUTE-MAP-1` remains a narrow evidence-compilation task because the package does not contain the full local `P0D_SOURCE_CAPABILITY_EVIDENCE_20260910.json`.
- `GIT-002` should preserve/push `audit/p0d/`, `scripts/build_p0d_capability_evidence.py`, and `scripts/verify_p0d_runtime_surface.py` first, then `ROUTE-MAP-1` reuses those artifacts.
- Critical E2E remains a real implementation/verification task; it must not be faked or treated as preflight discovery.