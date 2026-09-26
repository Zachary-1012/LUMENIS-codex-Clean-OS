# ROUND 05 — HealthGuard installer path correction

Sol decision: `PASS FOR BOUNDED INSTALLER SOURCE BATCH / ROUND 05 EXIT NOT ACCEPTED`, conditional on exact source/evidence/status publication. The existing Windows HealthGuard installer now derives the repository and starter script from its own script location; its scheduled action no longer points to the retired `D:\Taikoo-monitor-new` checkout. The historical task name and launcher are preserved.

## Verification and limits

- Base: fetched `main` `214adcad9c597a26976e7a3c865ff3716a7ed049`. Source scope is only `scripts/install_healthguard_task.ps1`. No user-level model route, Cookie/session, production DB, browser profile or Task Scheduler entry was changed.
- PowerShell AST parse passed. A mock execution substituted every ScheduledTasks cmdlet, captured `Register-ScheduledTask` without registering anything, and proved the task action contains the quoted current `D:\LUMENIS_REBUILD\序\序境\scripts\start_production.ps1` and retains `ZBrand-HealthGuard`. `git diff --check` passed. This is a source/action-definition test, not a real scheduled run.
- Read-only runtime check found no listener at 8201 or the prior 64252 preview and no exact `ZBrand-HealthGuard` task at observation. The current mainline launcher and App `/healthz` contract also need coherent integration: the committed launcher requires `status=healthy` and `dependencies.database=ok`, while the committed App exposes a simpler payload. Dirty local App/supervisor/launcher candidates address that contract together but remain unaccepted. Do not run the installer or claim service recovery based on this source fix alone.
- Protected `data/monitor.db` SHA-256 remained `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45` with no SQLite sidecars. No runtime or production data write was performed.

## REAL DELIVERY CARD / 真实用户工作闭环验收

`REAL USER JOB`: return to a healthy LUMENIS workspace after a service restart. `ENTRY`: existing Windows HealthGuard registration. `REAL INPUT`: the current checkout path in a mocked scheduled-task action. `END-TO-END PATH`: script location → starter path → action definition; actual registration, launch, health and user return were not exercised. `USER-VISIBLE RESULT`: none. `FAILURE/RECOVERY`: the retired path is no longer embedded, but service health remains unavailable and must fail honestly. `EVIDENCE`: mock action capture, AST parse and read-only port/task check. `ACCEPTANCE ASSERTION`: installer source correction only; ROUND 05 real user-work E2E and exit remain open.

`GLOBAL UNIVERSE / DATA MATURITY IMPACT`: no collection or entity sampling; Global Commercial Coverage=`NO`, Global Brand Coverage=`NO`, Guangzhou Taikoo Hui Reference Coverage=`PARTIAL / NOT REVERIFIED`, `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`.

`COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO`; actual startup, recovery, health, observability, rollback and release remain unverified.

`CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION`: Microsoft's maintained [PowerShell automatic-variable documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_automatic_variables?view=powershell-7.5) identifies `$PSScriptRoot` as the executing script's parent path; its [ScheduledTasks action reference](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtaskaction?view=windowsserver2025-ps) confirms `-Argument` defines the command-line action. Accessed 2026-09-26. Decision `ADAPT` the current SYSTEM Runtime installer with no new dependency or task identity. Revert the two-path source hunk if a verified deployment caller requires different quoting, then rerun the mock and actual controlled scheduling gate.
