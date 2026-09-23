# ROUND 02 — clean-main Windows SYS-01 acceptance

Status: **Sol PASS for the bounded ROUND 02 SYSTEM user job**. The corrected executable-source commit `7781403e2fedcfa8290922f5469dd8d6a365533b` was pushed to `origin/main` and re-resolved there. This is not a whole-product, account, collection, Web Workspace, Mobile, beta or release acceptance.

## Source and isolation

- Baseline `origin/main = HEAD = a419d4d36441274093fede0281c48c89f9ba3d2d` at export. `git archive HEAD` was expanded to an OS-temporary directory; its source ZIP SHA-256 is `2A987FA88AEDC227A2D99A19CD14912897E62487C09C00D19AB4279739C454B3`. The archive is independent of the protected dirty working tree. The Flutter lockfile and pubspec hashes match that baseline after offline dependency resolution.
- The clean baseline Windows App compiled with Flutter 3.47.5 (`flutter build windows --release --no-pub`, exit 0). Executable SHA-256: `E6B3634D462B8B9BDD445771CEF30856736AABE68E535C5C1BE1323813916388`.
- Only the staged SYS-01 `experience_screens.py` hunk and its new test were applied to the temporary clean source. The candidate `experience_screens.py` blob `86d5300586fe7a2fcedca2259e3613546b549b0a` matched the proposed index blob exactly. No interleaved CTH/SH/BMP changes were included. The unchanged clean-baseline Windows executable was used with this candidate Core.
- Core bound `127.0.0.1:8201` with `ZBC_ENV=staging`, `XHS_PRODUCTION=0`, `ZBC_TEST_OFFLINE=1`, `ZBC_GUARDIAN_ENABLED=0`, and all database/data/runtime/log/Evidence paths set to one disposable OS-temporary case. It was launched by importing the Flask app rather than executing `app.py`'s production `__main__` entry, which could start XHS/browser/scheduler paths. No browser/CDP profile, Cookie, personal Mainland XHS identity, production collector or external source was accessed.
- Protected `data/monitor.db` SHA-256 before and after: `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`; size `1,458,176` bytes; production WAL and SHM absent before and after. The controlled App and Core processes were stopped at the end. The disposable case was retained.

## Real operator journey

The operator opened the actual Windows `序境 - LUMENIS` window, selected SYSTEM / SYS-01, read the current observation, source, timestamp, trace, worker/DLQ counts and read-only boundary, stopped only the isolated Core, refreshed, saw the honest service-unavailable state and visible retry, restarted the same isolated Core, invoked retry and returned to the current result. Navigation Shared → SYSTEM also returned to a fresh observation on the baseline. HTTP `/healthz` and `/api/experience/screen/SYS-01` responses corroborated the observation but were not substituted for the page evidence.

The first clean-baseline UI disclosed `reaper=stopped` while its large overall label still said `normal`. That was a real semantic failure: RuntimeGuardian's narrower worker/circuit overall did not incorporate its reaper field. The candidate derives the SYS-01 display state solely from the same canonical RuntimeGuardian observation: stopped reaper becomes `degraded`; missing guardrail/count/breaker data becomes unavailable, never healthy; the correlation trace incorporates the guardrail state. RuntimeGuardian remains the sole runtime owner. On the candidate's real Windows page, the status is visibly `部分异常`, the service guardrail is `已停止`, and the source/time/trace remain inspectable. `runtime_observation.state=ready` means the observation was read successfully, **not** that every service is healthy.

| Phase | Target-window evidence | SHA-256 |
| --- | --- | --- |
| Clean baseline before correction | `2026-09-23-a419d4d3-sys01-ready.png` | `3ED74E6E615A590FEBE3D89D23F54E34CA3DD72B552EFE90C77A094481CAD147` |
| Clean baseline real outage | `2026-09-23-a419d4d3-sys01-unavailable.png` | `13FA9740A5B06D602915EAF2111262DCDEF53C04E85FB4498AA4C55C610CD125` |
| Clean baseline recovered | `2026-09-23-a419d4d3-sys01-recovered.png` | `08FAA41F517E01B06663FFA7F915EC14C4FDE71312AE7DF98953A4B084D922FE` |
| Baseline source, time, trace, boundary | `2026-09-23-a419d4d3-sys01-trace.png` | `D8F0FC5677391923C93302CF67E489E98391F9BEA7F62CD79292B0F8DEF93E42` |
| Baseline return from Shared | `2026-09-23-a419d4d3-sys01-return.png` | `EE3F7CAE74A5CB250A64302006DF8790499288F3E261C1A24145167EA749B84B` |
| Candidate corrected degraded state | `2026-09-23-sys01-candidate-degraded.png` | `A9825F190B88E7D763EEB441B863842F881485D48C981992D66F725D57A0724A` |
| Candidate source, time, trace, boundary | `2026-09-23-sys01-candidate-trace.png` | `4636682501B14FA1A669E2D805C37A5359C07193EC8C31D05C31058EBE8A70BF` |
| Candidate real outage | `2026-09-23-sys01-candidate-unavailable.png` | `13FA9740A5B06D602915EAF2111262DCDEF53C04E85FB4498AA4C55C610CD125` |
| Candidate recovered, still honestly degraded | `2026-09-23-sys01-candidate-recovered.png` | `2A8D8A0AFA0FD41C08D862FFE09A83FCEA6B3AA3283816B1C6AC8495E497CA19` |

## Validation and non-claims

- Clean-baseline Flutter SYS-01 and shell targeted tests: **16 passed**, exit 0. Clean-baseline Python SYS-01 tests: **6 passed**, exit 0.
- Exact clean candidate: `tests/test_sys01_runtime_health_semantics.py`, `tests/test_experience_runtime.py`, and `tests/test_runtime_guardian.py`: **120 passed**, exit 0, no background-thread leak. The four hostile SYS-01 cases cover missing reaper, worker counts, DLQ and breaker data; a stopped reaper and trace-state transition have separate assertions.
- Clean-source governance, Only-One, Experience authority, 44 Screen/54 binding blueprint, and strict static anti-template gates: exit 0. The anti-template gate is **static only**; the old CTH/Shared pages visibly remain template-like on committed main and require their owning Experience rounds. It does not certify their visual design or business readiness.
- GitHub Product/App Gates on this account have not supplied executable CI results because hosted jobs were not started by the account payment/spending-limit state. This is `NOT RUN`, not green and not a source failure.
- The staged candidate and screenshots do not prove production runtime health, global commercial/brand coverage, an approved XHS session, account lifecycle, browser workspace protected identity, live cross-surface business E2E, or commercial release. `COMMERCIAL_READY=NO`.

The only Round 02 executable correction proposed here is the SYSTEM screen's truthful aggregation of existing runtime-owner fields. The large uncommitted App/Core feature tree remains protected and unaccepted; no future-round owner was silently promoted.
