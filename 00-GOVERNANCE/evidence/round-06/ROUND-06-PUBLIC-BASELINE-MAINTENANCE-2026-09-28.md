# ROUND 06 — durable due-only public baseline maintenance

Base: `028ed4a821311692570129965d3c5eda84586d90`. Existing SYSTEM Collector/Scheduler/Permission, Shared
Evidence/Canonical/native-content owners; no parallel store or account system.

## Accepted source changes

- Exact versioned public HTTP/Atom plans, signed private configuration, revoked
  plans denied at collection/write boundary. End-user AUTO remains false.
- Existing schedule_decisions provides atomic claims, durable last success and
  failure/backoff, abandoned-worker recovery, due-only batching and restart.
- Existing scheduler entry and one-shot CLI share this implementation. CLI never
  starts account/browser/Flask or migrates the product database.
- Public HTTP has a native-platform mapping. Public HTTP and Atom refresh changed
  source fields in existing Canonical rows while preserving reviewed annotations,
  first scope Evidence, unknown publication dates, and signed latest observation.
  Unchanged replay reuses observation Evidence; mixed feeds also refresh old rows.

## Verification

38 focused regressions passed, exit 0, against a disposable v18 seed after the
Atom addendum. Existing scheduling module assertions executed in the same run.
No background-thread leaks. Covered tamper/revoke/wrong scope, denied-before-fetch,
1401-source inventory (no old daily quota), atomic claim, expired worker, recovery,
first/changed/unchanged/mixed refresh, annotations, unknown versus zero, and CLI.

Live isolated clone: real Guangzhou official source + Nike official company URL;
run 1 saved two signed observations/native rows, run 2 in a new process deferred
both and kept counts identical. Integrity OK and FK 0 after reopen.

Formal apply used a SQLite backup preserving the actual database and a private
project-env backup before configuration. The private signed plan contains the
190 already VERIFIED public HTTP sources, with source-specific daily/weekly/30-day
cadence. No cookie-backed platforms or user AUTO were enabled.

Actual first tick: 8 SUCCESS, 0 failure, 182 deferred (includes queued sources,
not all NOT_DUE). Raw and Canonical remain 220 each; Evidence 193 -> 201;
platform_contents 30 -> 38. All 8 new Evidence records are writer-authenticated,
with plan/authorization/source/scope versions. Integrity OK, FK violations 0.

## REAL DELIVERY CARD / 真实用户工作闭环验收

Job: keep approved public baseline current without manually reimporting it.
Entry: existing scheduler or one-shot CLI. Input: signed actual public-source plan.
Path: due policy -> exact service permission -> Collector -> Raw -> signed Evidence
-> existing Canonical/native fields -> durable success/failure record.
Result: actual persisted observations and due state survive a new process.
Recovery: revoke plan/disable it, source failure backoff, worker lease recovery;
no missing value is manufactured. Secrets/config/product DB remain ignored.

Windows scheduled activation is a separate runtime step after publication; this
evidence does not claim a future scheduled cycle already occurred. Actual user
UI E2E and complete platform/global coverage remain NOT VERIFIED. This maintains
190 known public sources; it is not a 1400-entity or social-platform completion.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: ADAPT existing stdlib/SQLite
and project scheduler contracts; no new dependency. Relevant source-policy study
is retained in intelligence_library/07_Data-Evidence-Evaluation/
COLLECTOR-CONTINUITY-RESEARCH-20260928.md. COMMERCIAL OVERLAY IMPACT: no commercial
rights or launch promotion. GLOBAL UNIVERSE / DATA MATURITY IMPACT: commercial and
brand coverage NO / NOT VERIFIED; Guangzhou PARTIAL. ROUND 06 REWORK;
Full Universe/RELEASED/OPERATING/COMMERCIAL_READY remain NO.

## Actual scheduled activation — 2026-09-28 05:31 Asia/Shanghai

Runtime is a fixed git archive of accepted `8d6e510309747607a2ce8e3253a02ce5119c05d9`
under ignored data/private/runtime. It is independent of the protected dirty app
worktree. Three conflicting older local candidates (secondary_collection,
platform_naming, Atom test) remain protected; they were not bulk-overwritten or
accepted as part of deployment. Daily data work must use accepted source until
those candidates are reconciled. The scheduled process never starts Flask or
performs schema migration.

Windows task LUMENIS-Prelaunch-Maintenance-5m was registered with least privilege,
InteractiveToken, no saved account password, hidden execution, IgnoreNew overlap,
10-minute bound, StartWhenAvailable, five-minute due evaluation and logon recovery.
It first ran from its future timer at 05:31:01 and completed at 05:31:52, exit 0:
8 succeeded, 0 failed, 182 deferred. Combined manual + scheduled attempts: 16
SUCCESS. Raw/Canonical 220/220, Evidence 209, native rows 46; integrity OK, FK 0.
This is one real scheduled cycle, not long-running operation acceptance.

The user must be logged into Windows; shutdown/logout suspends local execution.
The following login resumes evaluation. Disabled/revoked signed plans cause no
collection. Control script disables/removes only this task and preserves data.
Updating the runtime requires a newly verified accepted archive and an explicit
scheduler action update; dirty source is never automatically promoted. Private
.env, signed plan, keys, browser profiles, product DB and logs are not committed.

The register/control scripts are repeatable deployment helpers for the existing
scheduler, not a second scheduler. Installer refuses unknown existing task or
launcher overwrite. The actual source pipeline and all product release statuses
remain as stated above; global/multiplatform/user-E2E/OPERATING are not completed.
