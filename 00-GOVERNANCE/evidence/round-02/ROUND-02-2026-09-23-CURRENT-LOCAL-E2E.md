# ROUND 02 — current local Windows SYS-01 user-work E2E

Status: **LIVE VERIFIED ON THE CURRENT LOCAL CANDIDATE / NOT REMOTE SOURCE ACCEPTANCE**
Observed: 2026-09-23 11:30–11:38 Asia/Shanghai
Sol base: `dd92b9e010e528bf30426ee82dff4a71619e1d73` (`HEAD = origin/main` before this evidence file). The Flutter and adjacent Product Core working tree was dirty; this report does not imply that its executable source was committed or pushed.

## Real user job and executable boundary

An internal SYSTEM operator opened the actual Windows `序境 - LUMENIS` App, entered SYSTEM / SYS-01, read a current operational result with source/time/trace and a read-only boundary, refreshed it, observed a real Core outage, used the visible recovery action after Core restart, and returned from Shared to SYS-01 without changing business context. This is a SYSTEM read-only job, not a CTH/BMP data or commercial-release test.

The Windows release build was compiled from the current local Flutter tree using the checked `L:` `subst` alias to the canonical Unicode checkout. `flutter build windows --release --no-pub` exited `0`; the built `lumenis_app.exe` SHA-256 was `6C199877A5990BB871D86FDDCD06ABE9771A900516D9335B69BABE89AC257EA2`. `L:` is a build-path alias, not another repository or product path.

Core ran on `127.0.0.1:8201` from the current local source with `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`, `ZBC_ENV=staging`, `XHS_PRODUCTION=0`, `ZBC_GUARDIAN_ENABLED=0` and the canonical `ZBC_DB_PATH` pointing only to `C:\Users\private-user-121dcc385158\AppData\Local\Temp\lumenis-r02-9fc395cc99514d9585cea802970dfe56\data\core.sqlite3`. Data/log/runtime/temp overrides pointed under the same disposable case directory. The startup log explicitly reported `Staging/no-collect: campaign scheduler thread disabled`. No CDP URL, personal Mainland XHS profile or production collection was used. Core `/healthz` returned `ok=true,status=healthy`; `/api/experience/screen/SYS-01` returned `ok=true,bound=true,runtime_observation.state=ready` and a live `sys01rt-*` correlation ID. These HTTP facts corroborate but do not substitute for the page evidence below.

An initial isolated Core startup attempt failed because the Windows GBK console could not encode an emoji in migration logging. That attempt stopped and was not used as acceptance input. A fresh disposable case with UTF-8 process settings migrated to schema v17 and served the E2E. The encoding dependency remains a ROUND 05 startup-hardening input, not a hidden PASS.

## Target-window observations

All three PNGs were captured from the uniquely selected `序境 - LUMENIS` Windows target, not another foreground window. The accessibility tree identified the same target and user-visible state before each image was saved.

| Phase | Actual user action and result | Artifact | SHA-256 |
| --- | --- | --- | --- |
| Ready | Reconnected the workspace after Core became available, selected SYSTEM / SYS-01, read `系统整体状态：正常`, source `系统运行监测`, observation time, trace and `只读，不修改运行状态`. A normal refresh changed the trace to `sys01rt-65059c6ff7a1cbdd14e687ea`. | `2026-09-23-dd92b9e0-sys01-ready.png` | `2926826570CEF53AA4621AC8D408FFDD7DDC124661D32557EC9294321A49713F` |
| Core unavailable | Stopped only the controlled isolated Core; port 8201 ceased listening. Clicked the page refresh. The target displayed `系统服务暂不可用` and `重新检查`, not a fabricated healthy state or zero metrics. | `2026-09-23-dd92b9e0-sys01-unavailable.png` | `5A960B587EE305B9481D46DFEF03CD606DD2395258B28228DAC90B75CE259011` |
| Recovered | Restarted the same Core against the same disposable database, clicked `重新检查`, and observed the target return to `系统整体状态：正常` with a new trace `sys01rt-df240551e07911fe9921a097`. | `2026-09-23-dd92b9e0-sys01-recovered.png` | `2B826B6119DD6D6376C77E70EFB683AE75ADF1C8E634480ED680E8E723EFFEBA` |

The target also navigated SYSTEM → Shared → SYSTEM; SYS-01 returned with a fresh observation `sys01rt-b5c80b2a504538c92e92c003`. A subsequent on-page refresh produced `sys01rt-65059c6ff7a1cbdd14e687ea`. No Subject/BrandFocus was selected for this SYSTEM-only job. A protected CTH route returned 401 and showed an honest local unavailable state; it was not bypassed or used as a fabricated business result.

## Validation and protection

| Check | Current result |
| --- | --- |
| Windows release compilation | PASS, exit `0`; executable fingerprint above |
| Flutter SYS-01 plus workspace-shell tests | PASS, `23` tests, exit `0`; includes mobile 390px, tablet 1024px, desktop and Korean-copy checks. Widget tests are regression/compact evidence, not live Mobile E2E. |
| `tests/test_experience_runtime.py -k sys01` | PASS, `6` tests, exit `0`; no background-thread leak |
| `tests/test_version_api.py tests/test_experience_runtime.py` | PASS, exit `0`; affected Python regression, no background-thread leak |
| Experience anti-template strict, 44-blueprint/54-binding, Codex takeover governance, Only-One/single-product | PASS, each exit `0` |
| Production `data/monitor.db` | Before/after SHA-256 `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`, length `1,458,176`; WAL and SHM absent before/after. No production DB open, migration, deletion or checkpoint. |
| GitHub Product Gate and App Gate on `dd92b9e0` | NOT RUN: GitHub annotations state the jobs were not started because recent account payments failed or the spending limit needs increase. Neither workflow is a green test nor a code-failure diagnosis. |

The controlled Core and the owned Windows App were stopped after the test; port 8201 no longer listened. The disposable case and image evidence were retained, not deleted. `COMMERCIAL_READY=NO`, global business-data maturity unverified, Product Owner `USER_VERIFIED` unclaimed.

## Sol decision boundary

The specific ROUND 02 Windows SYS-01 real-user job is **LIVE VERIFIED LOCALLY**. Full ROUND 02 remains **REWORK** until Sol safely reconciles the heavily interleaved, uncommitted App/Core source with the single-mainline owner boundaries, reruns proportional validation on the integration candidate and records the resulting remote/CI status. The observed App code is not present in the pushed `dd92b9e0` tree merely because the governance files were pushed. This report is evidence, not a new Product/Experience/Runtime authority or a release claim.
