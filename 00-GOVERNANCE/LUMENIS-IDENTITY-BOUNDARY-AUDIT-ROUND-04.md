# LUMENIS Identity Boundary Audit — ROUND 04

> Task: `ROUND-04-B001 / LUNA-007`
> Baseline: `07013dcd4a82e87272f4bc1aaff0525404ad5995`
> Evidence date: 2026-09-21
> Status: **PRE-BETA APP GATE REMOVED / AUTH BOUNDARIES TESTED / PACKAGED UI UNVERIFIED**

This evidence is subordinate to executable source, the Product Architecture,
the Experience Constitution, the Source Owner Index, and current runtime truth.
It does not turn a Flutter widget test into Product Core authorization proof.

## Accepted boundary

- The Flutter App opens from Product Core runtime identity without a LUMENIS
  product-account prompt. Startup does not call `/v4/auth/login`,
  `/v4/auth/logout`, or prefetch the CTH Subject Registry.
- Product Core transport authentication is not a product account. Only a
  loopback Core may supply the existing Basic header through
  `/api/auth/config`; remote HTTP and remote HTTPS skip that endpoint and never
  receive or send the reusable header.
- Media Cookie/session/browser authorization remains owned by the SYSTEM
  collector/browser chain. This Batch did not read, migrate, display, or alter
  those credentials.
- CTH-02 calls the existing protected
  `/api/settings/subjects?domain_id=CTH` route only when the user opens the
  nested directory. HTTP 401/403 stays local to CTH-02, exposes no returned
  subject data, and does not eject the user from the rest of the App.
- Core 401, Core 403, offline, invalid-response, and retry states remain
  distinct. Removing the product-account wall does not synthesize Permission
  or bypass a protected backend route.

## Source and automated evidence

The accepted slice changes the Core client, launch surface, workspace shell,
CTH-02 denial copy, their focused tests, and the App README. Generated desktop
registrants have no semantic diff and are excluded from this Batch.

- Direct Dart analysis of the complete `app/` tree: exit `0`, no issues.
- Focused Flutter suite for Core client, launch, shell, CTH-02 repository, and
  CTH-02 screen: exit `0`, `28 passed`.
- Core client subset after final copy correction: exit `0`, `6 passed`.
- Scoped whitespace validation: exit `0`.

An earlier `flutter analyze` attempt ended with an analysis-server truncated
JSON failure (exit `255`), and Sol's first `dart.bat` invocation lost the
Unicode child working directory (exit `64`). Neither is reported as a source
PASS; the final direct `dart.exe analyze` run in the explicit App directory is
the accepted static result.

## Current runtime evidence and blocker

A separately started, already-running local Product Core on port 8201 was used
only for read-only contract checks. It reported auth disabled, returned HTTP
200 for runtime identity without an Authorization header, and returned HTTP
401 for the protected CTH Subject Registry route. No credential value was
printed. This confirms the running backend did not convert Core transport
state into a product-account bypass; it is not packaged Flutter UI acceptance.

The first focused Python Auth/API Domain, Permission, request-context, and
Subject Registry regression command did not collect tests. The pytest database
gate detected the active runtime's repository `monitor.db-wal` and
`monitor.db-shm` sidecars and failed closed with exit `4`. The runtime was not
stopped, and its database or sidecars were not copied, checkpointed, removed,
or restored.

Sol then used the test harness's explicit external-seed path. The preserved
seed was verified as 53248 bytes with SHA-256
`F69208CFBA914E455B0BF34424E78E382940EE3C155F7F9C7CA4714E641E40DD`;
pytest copied it into its OS-temporary database and never opened the active
repository database. The five focused Python suites completed with exit `0`
and `75 passed`, with no background-thread leak reported. This closes the
Python regression blocker without weakening the live-database sidecar gate.

## Disposition

- Flutter source and focused automated behavior: **TESTED / PASS**.
- Live backend identity-versus-registry contract: **READ-ONLY VERIFIED** for
  the observed local runtime state.
- Server Permission implementation: **PRESERVED**, not replaced by App logic.
- Python Auth/API regression: **TESTED / PASS** (`75 passed`) through the
  verified external-seed isolation path; the active production DB sidecar gate
  remained fail closed.
- Packaged desktop/mobile launch, remote Core deployment transport, and future
  product-account identity/tenant design: **UNVERIFIED / DEFERRED**.
