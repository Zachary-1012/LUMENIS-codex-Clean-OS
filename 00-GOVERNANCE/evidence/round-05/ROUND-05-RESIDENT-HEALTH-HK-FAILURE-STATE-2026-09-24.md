# ROUND 05 — approved resident identity and CDP failure states

Sol decision: `PASS FOR BOUNDED RUNTIME HEALTH BATCH / ROUND 05 EXIT NOT ACCEPTED`. The resident health path is restricted to the approved Hong Kong/international XHS identity and distinguishes an unavailable CDP control plane from an observed logged-out session.

## Exact source and verification

- Base: fetched local and remote `main` `c1309f658365cd654b1ba56de4a74b534bc2b5d3`. Accepted source paths: `resident_health.py` and `tests/test_resident_health.py` only. Isolated worker patch SHA-256 `3E72D275175F8F0A9CF16678BFCB33244D1F6ECE608D4A2C57DC2DD10BDC9B1D`; Sol's narrow malformed-URL refinement patches SHA-256 `DCDA9ECEAC7F4BB27491277E508E55A0BFEC461F16B4F47B2BDE926FC8F0EDAC` and `1F3CC9E87E7D43E5ACBD6C974169E3E637443558E484C3BCA531D9C0636DCB31`. Broader dirty health/browser work remains unstaged.
- Active `check_all` and `recover_all` use only the approved default identity. A caller naming the blocked personal Mainland identity is rejected before port lookup, Evidence/state write or recovery. CDP disconnects, missing page targets, malformed page URLs and malformed cookie responses produce `CDP_DEGRADED` with unknown login state; a successful empty cookie list remains `NEEDS_LOGIN`.
- Sol replayed the exact staged source on a clean current-main archive and ran 22/22 fully mocked resident-health tests, exit 0, no daemon-thread leak. Git blob IDs of the tested source and test match the staged index. The old baseline test file was intentionally not executed: it probed port 9222 and invoked personal-identity health paths without mocks. No live CDP, browser, Cookie/profile, startup or recovery E2E was run.
- Protected `data/monitor.db` was file-hashed only; expected 1,458,176 bytes and SHA-256 `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`. It was not opened by SQLite. The final fingerprint and current-snapshot static/governance results are checked before publication.

## REAL DELIVERY CARD / 真实用户工作闭环验收

`REAL USER JOB`: know whether the approved collection browser is truly available so an operator can recover the correct identity. `ENTRY`: existing SYSTEM resident health owner. `REAL INPUT`: mocked HK CDP and malformed/disconnected responses; no live account state. `END-TO-END PATH`: active identity gate → port/CDP probe → distinct health result → mocked state/Evidence behavior. `USER-VISIBLE RESULT`: none live-verified. `FAILURE/RECOVERY`: unknown control-plane state is degraded, never silently logged out or healthy; blocked identity causes no probe/recovery. `EVIDENCE`: 22 isolated mocked tests and exact staged blob match. `ACCEPTANCE ASSERTION`: bounded safety/status behavior passes; real authorized operator flow and ROUND 05 exit remain open.

`GLOBAL UNIVERSE / DATA MATURITY IMPACT`: no collection or entity coverage added. Global Commercial Coverage=`NO`; Global Brand Coverage=`NO`; Guangzhou Taikoo Hui Reference Coverage=`PARTIAL / NOT REVERIFIED`; `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`. Random entity sample count is zero for this runtime-only Batch.

`COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO`. Startup safety, authorized HK live health/recovery, real Evidence, observability, and user recovery still require separate acceptance.

`CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION`: [Chrome DevTools Protocol Network domain](https://chromedevtools.github.io/devtools-protocol/tot/Network/) and [ChromeDevTools protocol source](https://github.com/ChromeDevTools/devtools-protocol), BSD-3-Clause OSS, reviewed 2026-09-24. Decision `ADAPT`: validate the existing SYSTEM browser probe's response shape and unknown state; no new dependency, profile access or runtime owner. Rollback is the source commit; no account data changed.
