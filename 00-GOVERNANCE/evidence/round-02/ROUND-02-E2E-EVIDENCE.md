# ROUND 02 Windows Desktop E2E Evidence

> Candidate SHA: `542ee83164f3bcee1583d3ad20a64208bc066b06`
>
> Decision: **PARTIAL LIVE VERIFIED / REWORK**

## Executed real path

1. Built and launched the current Flutter Windows Desktop App through an ASCII junction because the Windows Flutter toolchain corrupted the canonical Unicode checkout path during direct packaging.
2. Launched the current Product Core on `127.0.0.1:8201` against an isolated disposable `ZBC_DB_PATH` database.
3. Entered the real workspace without a product-account wall and navigated to SYSTEM / SYS-01.
4. Verified a live RuntimeGuardian observation in the Desktop App, including source, sample time, deterministic observation ID and read-only boundary.
5. Stopped the controlled Core process and verified the live Desktop App displayed `系统服务暂不可用` with the visible `重新检查` action.
6. Restarted the same controlled Core against the same disposable database and invoked the visible retry action.
7. Verified the recovered Core/API returned a new ready observation at `2026-09-21T22:37:33+08:00`, trace `sys01rt-bf10545504bc29efe8c1d023`, boundary `read_only`.

## Target-surface artifacts

- `01-desktop-entry.png`: real Desktop workspace entry.
- `02-sys01-ready.png`: real SYS-01 ready state; observation time `2026-09-21T22:01:10`, trace `sys01rt-179292f97ba8df61ca067eb9`.
- `03-sys01-core-unavailable.png`: real Core-unavailable state and visible retry control.

An attempted recovered capture was rejected because it showed the Codex window rather than the LUMENIS target and was removed. Flutter CLI reports `Screenshot not supported for Windows`. The Windows Computer Use connector exposed browser-only methods and no native-app binding API (`getApp/listApps/listWindows` unavailable), so a trustworthy recovered target-surface capture was not obtained. The evidence set therefore does not satisfy the Charter's full recovered-UI assertion.

## Isolated runtime and protected-data proof

- Runtime identity reported `LUMENIS Experience Runtime` and isolated database `monitor-e2e.db` selected by `ZBC_DB_PATH`.
- Protected repository database metadata remained unchanged before and after:
  - `monitor.db`: 1,458,176 bytes; `2026-09-21T06:53:14.5305046Z`;
  - `monitor.db-wal`: 160,712 bytes; `2026-09-21T06:57:29.7959662Z`;
  - `monitor.db-shm`: 32,768 bytes; `2026-09-21T06:53:22.4288743Z`.
- No protected database was migrated, checkpointed, repaired or deleted.

## Current-SHA automated evidence

- Python affected suite: 75 collected and passed, exit 0.
- Flutter `analyze --no-pub`: no issues, exit 0.
- Full Flutter tests: 79 passed, exit 0.
- GGI contract, Codex takeover, Only-One, Experience authority, strict anti-template and 44-screen/54-binding validators: all exit 0.
- `git diff --check`: exit 0.
- Impeccable changed-UI detector: no flagged patterns.

GitHub `LUMENIS Product Gate` run `35613581975` and `LUMENIS App Gate` run `35613581988` both ended failure with `steps=[]`; this is execution-layer evidence only and cannot be interpreted as a product-test failure or pass.

## Random entity acceptance truth

The isolated `subject_registry.list_subjects()` returned `0` rows. No sampling seed, rate or Evidence trace was fabricated. Global entity sampling, non-reference commercial/brand Subjects and the data-maturity matrix remain `NOT YET IMPLEMENTED` under the owners scheduled from ROUND 03 onward.
