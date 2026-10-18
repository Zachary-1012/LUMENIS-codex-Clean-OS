# ROUND 05 — Core runtime and media binary recovery

Status: **ACTUAL CORE STARTUP AND ISOLATED SUPERVISOR RECOVERY VERIFIED; ROUND 05 NOT ACCEPTED**
Date: 2026-10-01 (Asia/Shanghai)
Task base observed: 1c8454ff47982d87fb4ef167db0ec5c7bcc11b69
Final shared main observed: 65329ba78c574f25e4c53c76825eeec7207f5f8c (origin/main and live refs/heads/main matched at final check)

## Scope and ownership

This bounded batch covered SYSTEM startup/runtime recovery and resolution of the existing FFmpeg/FFprobe tools. Reviewed the canonical startup script, run_supervised.py, runtime startup state, shared_artifacts.py FFmpeg resolver, the video-editing FFprobe resolver, and their targeted tests.

No product source, test, .env, user-level model/provider configuration, registry, or shared CURRENT file was edited by this batch. Existing .env already supplies LUMENIS_FFMPEG_PATH and LUMENIS_FFPROBE_PATH; normal app startup loads it. Existing resolver/configuration worked, so no source/config fix was necessary. This evidence file is the only file authored by this batch. No commit or push was made.

The shared checkout advanced to 65329ba while this task was running. The final worktree also contains unrelated shared root changes and protected work/; they were not modified or staged by this batch.

## Production Core startup

Before starting Core, used the canonical SQLite online-backup owner to create:

data/backups/r5-before-core-start-20261001-ff0a4dc2c56540eb91e8a9e4e2216e9e.db (7.80 MB)

The source DB and its existing WAL/SHM fingerprints compared equal before and after backup. Read-only checks on the backup copy reported schema version 18, current migration target 18, PRAGMA integrity_check=ok, zero foreign-key violations, and migrate(target_version=18) success with no version delta. No production migration was run.

The real product Core was started against the existing data/monitor.db and left running on loopback:

- GET http://127.0.0.1:8201/healthz: 200, ok=true, status=healthy, database dependency ok, version 5.9.9.
- Listener: 127.0.0.1:8201, PID 23504 (python.exe, HTTP-serving worker).
- App parent PID 25612; data/supervisor_state.json reports running, PID 25612, restarts=0, fast_crashes=0.
- Supervisor command observed: run_supervised.py --host 127.0.0.1 --port 8201 (supervisor process PIDs 19396 and 19440). The app/worker command line also confirms loopback host and port.
- Final check again confirmed the loopback listener and healthy endpoint. Core 8201 was not stopped or restarted during final verification.

An initial launch attempt used 0.0.0.0; that exact Core process tree was stopped and relaunched on 127.0.0.1. The final runtime is loopback-only. No DB or browser process was killed.

## FFmpeg and FFprobe

The existing local toolchain is present at:

D:\codex\downloads\lumenis-media-toolchain-20260929\verified\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe

with adjacent ffprobe.exe. Both executables reported version 9.0.2-essentials_build-www.gyan.dev. The existing .env resolver settings were used; their values were not printed into command output or changed. No duplicate installation or repository-local workstation path was added.

## Isolated controlled crash and recovery

Crash recovery was exercised separately under:

C:\Users\private-user-121dcc385158\AppData\Local\Temp\lumenis-r5-crash-proof-731e88b44d954c14b86910409759ece2

The isolated app used a fresh disposable database in that temp tree, loopback port 8202, and the current supervisor/app code. After the supervisor reached running state, only its isolated app child (PID 26216) was terminated. The supervisor relaunched the child (PID 25652); state advanced to restarts=1, and health returned with the disposable DB dependency ok. The isolated listener was 127.0.0.1:8202 (PID 5228).

After proof, the exact temp supervisor/app process tree rooted at PID 25816 was stopped successfully (taskkill exit 0). Final check found no listener on 8202. The temporary DB and diagnostic files remain in the temp directory for evidence. The production DB, 8201 Core, browser processes, and cookies/sessions were not part of the drill.

## Tests and database evidence

Commands used the intact repository pytest configuration and explicit disposable seed; no --noconftest was used.

| Check | Result |
|---|---|
| .venv\Scripts\python.exe -X utf8 -m pytest -q tests/test_runtime_bin.py tests/test_audio_timeline_rendering.py with explicit LUMENIS_TEST_SEED_DB and existing FFmpeg/FFprobe configuration | 14 passed; exit 0 |
| powershell -NoProfile -ExecutionPolicy Bypass -File tests/test_start_production_health_gate.ps1 | PASS; exit 0 |
| python scripts/_prod_dep_check.py | OK; exit 0 |
| Disposable seed migration using canonical migrations through v18 | success; exit 0 |
| Backup-copy integrity / foreign-key / target-version checks | integrity OK; 0 FK violations; target v18 unchanged |

Reusable disposable seed for intact-conftest scoped tests:

C:\Users\private-user-121dcc385158\AppData\Local\Temp\lumenis-r5-v18-seed-741640e2ade54732a8d11da24035256d\monitor-test-seed-v18.db

It was created from an empty disposable location using the canonical migration owner. It contains no copied production data.

## REAL USER WORK E2E ACCEPTANCE / REAL DELIVERY CARD

- **REAL USER JOB:** An operator opens the internal workspace and completes a scoped business task.
- **ENTRY / REAL INPUT:** Existing local Core startup and actual product DB; no new business input was submitted.
- **END-TO-END PATH / USER-VISIBLE RESULT:** Startup → supervisor → loopback HTTP listener → /healthz → canonical DB dependency reports healthy. This proves Core availability only; no workspace business action or user-visible business result was exercised.
- **FAILURE / RECOVERY:** A controlled app-child failure in a separate disposable runtime was detected and recovered by the supervisor; the app returned healthy on port 8202. Production Core was not crash-injected.
- **EVIDENCE / ACCEPTANCE ASSERTION:** Actual product Core health and loopback bind are verified. Isolated child-process recovery is verified. **REAL USER BUSINESS WORK E2E=NO; this batch does not accept Round 05.**
- **GLOBAL UNIVERSE / DATA MATURITY IMPACT:** No coverage claim was tested. Global Commercial Coverage, Global Brand Coverage, and Guangzhou Taikoo Hui Reference Coverage remain unverified. Canonical random-entity sample count: 0; no entity-data acceptance was attempted.
- **COMMERCIAL OVERLAY IMPACT:** COMMERCIAL_READY=NO. This proves local runtime recovery, not release, business operation, or commercial readiness.

## Continuous frontier research / capability evolution

Official sources checked 2026-10-01:

- [Microsoft PowerShell Start-Process documentation](https://learn.microsoft.com/powershell/module/microsoft.powershell.management/start-process) — process startup behavior; no dependency or license change.
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html) — child-process lifecycle behavior; no dependency or license change.
- [FFprobe documentation](https://ffmpeg.org/ffprobe.html) — existing media-inspection executable behavior. The locally installed version was verified as 9.0.2; its distribution/license was not changed or re-audited in this runtime-only task.

Decision: **ADAPT / REUSE** the existing SYSTEM supervisor and media resolvers. Existing product-local configuration resolves valid FFmpeg/FFprobe binaries; no justified source upgrade, new dependency, external service, or new owner was identified. Commercial boundary: local workstation runtime only; no external media effect or paid service was invoked.

## Limitations and diagnostic note

Health establishes application boot and database connectivity, not business workflow completion, collector/source health, external login, or all required runtime initialization. A local Edge listener was observed on loopback port 9223; only executable basename msedge.exe and profile basename xhs-retinaut were checked. No cookie/session material or profile contents were read, and no browser process was stopped. External browser/login/source health remains unverified.

The current supervisor state file records running status, app PID, restart count and crash count, but not host/port after the running update. The actual command line and OS listener independently verify the final host/port. This was recorded as a diagnostic observation; no out-of-scope supervisor change was made.
