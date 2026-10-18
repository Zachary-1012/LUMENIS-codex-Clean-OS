# J8 — supervisor lifecycle and independent runtime

Status: M_ACCEPTED / BOUNDED_RUNTIME_VERIFIED / SCOPED_SECURITY_REVIEWED. The
source publication unit is the containing commit; post-push remote verification
is a separate required receipt. No Round, release, operating,
commercial or human-acceptance status is promoted. The initial J8 preparation below is historical
provenance. On 2026-10-02 the Product Owner resumed C1–C6; this existing window is
now C6/W6 and owns shared integration/publication after M final acceptance.

## Accepted lifecycle publication unit — 2026-10-02

M reviewed and accepted this bounded outcome: confirmed owned-child recovery and
operator stop, truthful terminal state, singleton failure isolation, no ordinary
startup inference heartbeat, and the approved-account CDP status mapping. Exactly
four code/test files are frozen: `run_supervised.py`, `app.py`,
`tests/test_internal_beta_startup_gate.py`, `tests/test_supervisor_lifecycle.py`.
This owning evidence and CURRENT takeover accompany them in the same commit.
Other protected local work is excluded. Source publication unit is the containing
commit; remote publication must be verified after push, never inferred here.

The 39-test stable regression and actual disposable-Core recovery/stop evidence
below remain valid at their frozen hashes. No repeat was needed after M review.
Codex Security diff scan `private-source-id-sha256-9bf4d2699c0e4418b4d8273fa9a6d3597022b9ab6f172c150c08da2c8cceb004` sealed successfully:
both changed production files and all four supporting files were reviewed; no
vulnerability candidate or confirmed finding was recorded. The frozen snapshot
digest is `codex-security-snapshot/v1:sha256:7fcb3c760d2787e1084b6fab57af6c5f695250dbee6889d57c7a85983d401eae`.
The report retains source-only coverage and actual-environment limits. The four
code/test hashes remain identical; this M-acceptance/publication status update is
documentation only. Final Constitution and exact six-path staged diff inspection
passed before publication; only this coherent outcome is included. Full C6,
business workflows, owned AI, four surfaces, release and
operation remain OPEN. The process drill covers observed child processes; detached
descendants and durable restart prevention after an unconfirmed cleanup remain
separate runtime acceptance questions.

## Current C6/W6 integration continuation — 2026-10-02

Fresh resume fetch: HEAD = origin/main =
`a85c35ee619ae75052f91b3b924e467bd8bc1622`. Full C6 Task Card is preserved at
`work/w6-integration-20261002/TASK-CARD.md`. Old J8-only no-shared-write/process/DB
restrictions below are superseded by explicit current PO/M authority; owner,
data-preservation, Permission, no stopped-provider and no personal CN XHS rules remain.

One actual current Core reproduction ran with dedicated temp DB/logs/state/lock,
non-reserved loopback port 51745 and the existing health-only effect fence. It used
an immutable supervisor source snapshot hash
`14219c284e3c238ee6c82669024e07750db7845ad3a4aaffac74034a6d682622`.
First Core became healthy in 4.612s; deliberate failure of only that owned child
recovered a distinct healthy child in 8.155s. Operator SIGINT then exited supervisor
0 in 0.656s while the second child remained alive and state stayed `starting`.
Result: FAILED — confirmed orphan/terminal-state defect, not inferred from source.
Driver final cleanup terminated only its own observed PIDs. Private OS-temp proof:
`lumenis-j8-actual-core-51c6arfz/result.json`. No formal DB or shared 8201 process was
touched. Mechanical repair remains bounded to supervisor and lifecycle tests;
root independently reviews and reruns changed-source actual process evidence.

Version-specific reference updated to Python 3.13 official subprocess/signal docs
and CPython 3.13 source (accessed 2026-10-02, PSF, maintained existing dependency):
https://docs.python.org/3.13/library/subprocess.html,
https://docs.python.org/3.13/library/signal.html,
https://github.com/python/cpython/blob/3.13/Lib/subprocess.py.
ADAPT bounded waits/cleanup and responsive cancellation within the canonical owner.
No additional runtime/dependency; no complete business or surface acceptance from
this health-only process drill. Full first CTH/BMP chain and all C6 exits remain open.

### Current bounded verification after repair

The repaired supervisor snapshot SHA256 is
`8861f753de0d47d64534f861c5707b80afa1f039543e589bb1bfd922d7757d6d`.
Root independently reran the actual health-only Core drill with disposable DB/logs,
port64781 and owned PIDs only: child22560 became healthy in8.438s, deliberate crash
recovered healthy child37532 in9.548s, supervisor SIGINT finished in0.686s/exit0.
All observed children exited; final state stopped/cleanup confirmed; lock reacquired;
disposable DB integrity=ok/FK=0. Proof: OS-temp
`lumenis-j8-actual-core-l1tkt8gb/result.json`. This is BOUNDED_RUNTIME_VERIFIED.
One worker regression attempt observed unexplained taskkill exit255; isolated retry,
final worker10/10 and root actual drill passed. The transient is retained, not hidden.

Coherent root regression XML `work/w6-integration-20261002/runtime-regression.xml`
records39 tests,0 failures/errors/skips,31.379s across supervisor lifecycle,
internal-beta startup, runtime health and workspace context. An earlier collection
attempt overlapped the worker's unfinished edit; dependent checks were held and the
stable final candidate was rerun. Startup tests prove the retired inference heartbeat
is not called and the optional CDP check selects approved9223, using stubs only.

W1 supplied the existing WAL-consistent canonical backup
`data/backups/pre-c1-w1-refresh-20261002T074158791571.db`, SHA256
`1957d677f04dd1af9f606c8f447c10aa44cd5483222c99f238ecb7c6c6bad636`.
Root cloned it through SharedDatabaseRepository into OS-temp and ran existing
init/migrate19 twice then reopened. Counts and digests stayed identical, original
backup unchanged, integrity=ok/FK=0. No actual version migration was performed.
Proof: `lumenis-w6-db-rehearsal-4j6ctgii/result.json`.

The canonical `scripts/start_production.ps1` completed and restored actual8201 on
2026-10-02. Fresh health returned healthy/database=ok; supervisor state running,
child21764,restarts0. Only approved HK9223 and general9224 were started; no personal
CN account/profile/9222 probe was used. Post-startup read-only snapshot verified the
seven protected tables against that backup: notes276,canonical_data276,
platform_contents269,app_evidence_records447,lumenis_subject_registry179,
lumenis_cth_cases1,daily_reports50; every count/digest identical, integrity=ok/FK=0.
Proof: `lumenis-w6-startup-readback-1i6vy3mz/result.json`. This proves safe startup
of the local loaded candidate; later file edits require controlled refresh and actual
API verification. Full business, owned AI, four-surface, packaging/release exits remain
open. Historical J8-only statements below do not override this current continuation.

## Historical original J8 card — superseded restrictions and prior evidence

The following original card and checks are provenance. Its pending validation,
process/publication restrictions and old next step do not override the accepted
current C6/W6 continuation above.

### Bounded context manifest and Task Card

- Capability/query: existing SYSTEM Startup/runtime; `run_supervised.py` / shutdown.
- Freshly fetched base/local/remote: `03740bc74e645f8c4212103b8aa0f2cef02e0102`.
- Owner: Source Owner Index Startup/runtime row; existing supervisor, no new owner.
- Rules read: root AGENTS; CURRENT takeover; AI-native Constitution; Product
  Architecture; Multi-Surface Decision; Source Owner Index; Real Delivery Overlay;
  Global Universe contract; Product Positioning; README; cross-repository registry
  and JSON contract v1.1.0; Security Boundary. Runtime, testing, database safety,
  Permission/Evidence, mainline and release-completion skills apply.
- Protected paths preserved: AI Gateway/owned training, Shared Learning review and
  promotion, `business_brief.py`, training `work/`, frontend `website/` and Flutter
  pages/design, formal DBs, accounts, sessions and shared processes. Other windows'
  current edits remain protected.
- Allowed implementation: `run_supervised.py`, new
  `tests/test_supervisor_lifecycle.py`; this evidence file is J8-owned. Shared
  startup/app/workflow/governance changes require integration by 序境12.
- PO routing correction: unique Owner, unmodified, independent paths may be
  implemented and claimed asynchronously; waiting for every individual path is
  no longer required. Shared process control and Git publication remain reserved.
- Target delivery: Windows, macOS, iOS, Web Workspace, Public Website. Android
  and Linux source/history and existing gates remain; no new delivery promise.
  Shared authoritative platform matrix updates belong to 序境12.
- Model: root runtime identifies GPT-6.1 Sol; resolved effort cannot independently
  be observed here. One mechanical worker explicitly uses GPT-6 Luna. No stopped
  local/Ollama/Zhipu provider was called or probed.

## REAL DELIVERY CARD / 真实用户工作闭环验收

REAL USER JOB: an operator can stop the owned supervisor/Core tree, recover a
crashed Core, and inspect an honest terminal state without orphan processes.

ENTRY / REAL INPUT: existing canonical Windows launcher/supervisor. Fresh live
8201 probe failed to connect. Shared processes will not be started or stopped by
J8. Isolated validation uses actual current Product Core with its existing
loopback health-only safe profile and a dedicated disposable storage directory.

END-TO-END PATH: owned supervisor -> actual child -> health contract -> injected
owned-child failure -> recovery -> operator cancellation -> confirmed child exit
-> state -> lock release. A health-only drill proves bounded runtime behavior,
not the full product or cross-surface user job.

Implementation findings at base: shutdown only logs closing the child; it never
terminates/reaps it. Long crash cooldown uses non-interruptible sleep. Unexpected
lock setup errors continue without singleton ownership. The bounded correction
must preserve health thresholds, provider isolation, DB and Permission meaning.

FAILURE/RECOVERY / ACCEPTANCE ASSERTION: cancellation must interrupt cooldown,
owned-child cleanup must run after signals and loop errors, singleton setup
failure must not spawn, failed cleanup must not claim stopped, and a zombie
cleanup failure must not start a competing child. Automated fixtures count only
as regression; actual process recovery is separately recorded.

USER-VISIBLE RESULT / EVIDENCE: pending validation. Full Web -> Windows/macOS
-> iOS Task/Context/Artifact reuse, final-user operation, candidate packaging and
cross-system rollback remain open, with unavailable hosts marked UNVERIFIED.

## Reusable evidence and research

- Fresh GitHub reads confirm Product run `36876805667` and App run `36876825895`
  at the exact base SHA completed successfully. Blocking pytest and Flutter
  analyze/test steps actually ran. No hosted re-dispatch was performed. These
  gates are hermetic/source evidence, not native packaging or release.
- `ROUND-07-REAL-LOCAL-MEDIA-2026-09-30.md`: reference-only historical actual
  Product API export/reopen and process-restart evidence, including exact Artifact
  hashes and rights limits; do not repeat an already successful render merely to
  produce a new progress claim. Current binaries and candidate evidence still
  require revalidation.
- Official Python subprocess and signal documentation, accessed 2026-10-02:
  https://docs.python.org/3/library/subprocess.html and
  https://docs.python.org/3/library/signal.html. ADAPT bounded process wait/cleanup
  and responsive cancellation inside the existing supervisor; no dependency or
  new runtime. The local venv reports Python 3.13.15. Documentation is engineering
  reference only and does not establish actual process behavior.
- Locator's old local-AI continuous-runtime note: REJECT for provider activation;
  the explicit 2026-10-01 provider retirement supersedes historical routing.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: no data coverage claim or mutation. Global
Commercial Coverage, Global Brand Coverage and Guangzhou Taikoo Hui Reference
Coverage remain unadvanced; runtime fixtures cannot define an entity population.

COMMERCIAL OVERLAY IMPACT: engineering runtime repair only. USER_VERIFIED,
RELEASED, OPERATING and COMMERCIAL_READY remain unaccepted. Publication and shared
platform-rule reconciliation are pending 序境12 integration.

Next executable step: inspect the one bounded worker diff, run isolated targeted
regression and actual owned-Core recovery/cancellation, then return exact files,
hashes, evidence and remaining exit gaps to 序境12.
