# ROUND 07 — scoped asynchronous report execution and recovery

Base: fetched `origin/main` and local HEAD
`8c6557ff568341c5b16b43d7d9f57a83b4ab1b7e`.
Task: make the existing Source Brief job return a durable task reference before
long analysis finishes, with exact-scope status and explicit crash recovery.
Existing SYSTEM TaskEngine owns `ai_task`; Shared Reporting owns `daily_reports`;
Permission, Evidence and Evaluation retain their current owners. No new table,
database, scheduler, provider, account design or frontend implementation.

## Context and bounded implementation

Locators: `agents_skills/recovery`, `reporting/source-brief`. Pinned rules:
AGENTS, AI-native Constitution, Product Architecture, Source Owner Index and
Real Delivery Overlay. The preceding checkpoint, media and business-brief
batches remain intact. Codex Cloud is development infrastructure, not evidence
of LUMENIS production hosting or independent hosted inference.

- `POST /api/experience/reports/source-brief/start`: accepts only limit,
  optional image_source_ref and business_question; server issues task/job IDs.
- `GET .../tasks/<task_id>`: current actor and exact domain/focus required.
- `POST .../tasks/<task_id>/resume`: empty JSON body, fresh scoped authorization;
  cannot replace saved question, input, actor or scope.
- Existing synchronous generate and immutable report reopen remain compatible.
- Admission and execution use exact scope Permission and REPORT_GENERATE. The
  narrow app operation mapping does not grant general DB_WRITE. These methods
  persist operational task state and derivative reports, not Canonical facts.
- The actual start/resume request is copied in memory for its bounded worker.
  No credentials, Cookie, session, executable callback or fabricated request is
  persisted. Scope and authorization are checked again before report commit.
- TaskEngine uses conditional claims and PID/create-time identities. Dead worker
  recovery compares the exact prior identity; a stale recovery cannot interrupt
  a different worker. Generic task routes cannot read, list, run, approve or
  cancel these reserved reporting tasks.
- After process death, status honestly shows interrupted. A new authorized
  resume request is required; boot does not deserialize authority from JSON.
  Same-ID recovery reuses already persisted artifacts and evaluations.

## Verification

150 affected isolated tests passed, plus 3 TaskEngine storage/concurrency tests
passed: 153 total, no failures/errors/skips or leaked worker threads. Tests use
the explicit disposable v18 seed and per-test databases with the normal
conftest. Coverage includes real scope Permission without testing bypass,
generic-route isolation, nonblocking start, duplicate resume, artifact/Evaluation
idempotency, closed-workspace denial before report persistence, malformed stored
JSON, stale worker identity, and an actual subprocess `os._exit(23)` recovery.
Python compilation, Constitution and diff checks passed on the source snapshot.
JUnit: local temporary `lumenis-report-tasks-tests.xml` (150) and
`lumenis-managed-report-tasks-tests.xml` (3).

Before product writes, the canonical backup owner created
`data/backups/pre-report-tasks-20261001-080742.db` (8.34 MB, integrity checked).
Production Core was restarted under the existing supervisor; health recovered.

| Actual scoped job | Task | Artifact | Evidence / result |
| --- | --- | --- | --- |
| CTH Guangzhou | `rbrief_f492c0ac-666a-44b8-80b6-edf804193242` | `brief-da1a713575104f419bcd8d8f644e2602` | 5 real sources; admission 0.577 s; artifact reopen and duplicate resume agree |
| BMP Nike | `rbrief_349cf8eb-ea38-4752-a9fa-25756047b655` | `brief-2386adfb508f40f6ba8a9280330be0ab` | 5 real sources; admission 0.118 s; signed derivative Evidence 429 |

While Nike was running, exact Core wrapper PID 21100 and its owned children were
terminated; existing supervisor PID 19440 recovered Core as wrapper PID 25976.
The same task then reported interrupted. A fresh authorized request resumed the
same job, completing in 115.71 seconds and reopening with the same artifact.
Both focused tasks reject GLOBAL access with 403. The completed Guangzhou
artifact also reopened unchanged after that Core crash. This is single-host
runtime recovery, not distributed/cloud-worker or human acceptance.

Final protected data: notes=270, Canonical=270, daily_reports=33,
evaluation_records=71, ai_task=2 (both succeeded), integrity=ok, FK violations=0.
No source records, timestamps or Canonical scopes were rewritten.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

- REAL USER JOB: start a scoped evidence-backed report, continue using the
  workspace while it runs, inspect its result and recover an interrupted job.
- ENTRY: actual Product Core start/status/resume/reopen APIs; Flutter binding
  remains with the paused independent frontend and is not accepted here.
- REAL INPUT: existing writer-authenticated Guangzhou and Nike Canonical data.
- END-TO-END PATH: request Permission → durable TaskEngine intent/claim →
  scoped Source Brief → local AI when requested → signed Evidence → immutable
  Reporting artifact → Evaluation → scoped status/reopen.
- USER-VISIBLE RESULT: task/job IDs, honest state, stored report and separate
  structural/quality evaluation. Fast admission is not faster model inference.
- FAILURE/RECOVERY: actual crash, fresh authorization, same-ID resume, no duplicate
  report; isolated revocation, malformed-state and stale-claim denial.
- EVIDENCE: exact IDs, runtime facts and scoped tests above. Human repeated use
  is HUMAN_PENDING; the Product Owner will perform consolidated acceptance.
- ACCEPTANCE ASSERTION: bounded asynchronous API/runtime recovery VERIFIED.
  No Round, four-surface, business-quality or Product Closure PASS.

The Nike v3 draft fixed the tiny excerpt and recognized simulated dialogue, but
failed to deliver the requested content research direction and emitted the
internal-looking string `source_ids_all_not_used`. Engineering Evaluation
`business-review-brief-2386adfb508f40f6ba8a9280330be0ab` records usefulness=0/FAIL.
The immutable draft is retained; its quality review is returned separately.
This is engineering review, not Product Owner acceptance or observed campaign
performance. Semantic/task relevance remains REWORK. No real Action/Outcome is
invented. Recovery success does not imply client-ready output.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

ADAPT Flask 3.1.3's documented live request-context copy for in-process work;
read the body before copying, do not modify sessions or persist context, and
require fresh authorization after restart. Official reference accessed
2026-10-01: https://flask.palletsprojects.com/en/stable/api/#flask.copy_current_request_context
Installed psutil 7.2.2 supplies exact process identity. Both are existing
dependencies; no new license/component was introduced. Existing durable-session
research informs recovery semantics without installing an external Agent owner.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: Global Commercial Coverage=NO;
Global Brand Coverage=NO; Guangzhou Taikoo Hui Reference=PARTIAL.
COMMERCIAL OVERLAY IMPACT: RELEASED=NO, OPERATING=NO, COMMERCIAL_READY=NO.
Hosted execution retains its evidenced billing/spending blocker; it was not
rerun. Next: correct business task relevance/quality and expose the reviewed
workflow to the Product Owner when frontend work resumes.
