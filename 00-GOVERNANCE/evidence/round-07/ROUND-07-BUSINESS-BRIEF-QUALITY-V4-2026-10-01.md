# ROUND 07 — business draft task relevance and prose validation

Base main `107d17cccc0eff27cf5eea10512e0a48186c8ad9`.
Existing Shared Reporting owner only; no new provider, runtime, schema or UI.
Reporting locator and current AI/Testing/DB boundaries were reused. One bounded
Luna read-only review identified the conflicting task instructions; Root made
the scoped change and performed acceptance. No external provider received data.

The previous instruction restricted unsupported inputs to fact-checking, which
could displace a requested content-research deliverable. Version 4 now permits
explicitly hypothetical research proposals and asks for a relevant direction,
source rationale and feedback method. It retains all source/citation, satire,
unknown-data, no-fabricated-outcome and human-review boundaries.

Known model-generated schema diagnostic tokens in prose are rejected through
the existing rejected-candidate Evidence path. They are not silently stripped;
source excerpts remain exact. Signed versions 1–3 remain readable, including
the failed v3 artifact and its original quality evaluation.

## Verification and runtime

- 39 normal-conftest isolated tests passed with no failures/errors/skips or
  leaked workers. JUnit: local temporary `lumenis-business-v4-tests.xml`.
  Includes malformed/generated diagnostics, immutable historical v3 reopen,
  existing grounding, permission, report and async recovery regressions.
- Python compile and AI-native Constitution passed on the source snapshot.
- Canonical WAL-consistent backup:
  `data/backups/pre-business-v4-20261001-0825.db`.
- Core was restarted under its existing supervisor to load the candidate and
  recovered `/healthz`; no system/user model configuration changed.
- The same actual Product Core async APIs produced and identically reopened:

| Domain | Job | Evidence | Execution time | Engineering quality |
| --- | --- | --- | --- | --- |
| BMP Nike | `brief-24363bbb64574425a3d5d7cfd9cdd247` | 430 | 127.39 s | FAIL |
| CTH Guangzhou | `brief-9686d79583184567b19bab70f4b941a5` | 431 | 143.48 s | UNKNOWN |

Task IDs: `rbrief_1689d53c-8f8f-4ef6-8053-fdf7c83561a0` and
`rbrief_b68747a7-225b-4bbf-b305-8d09bb808712`. Both consumed five verified
sources through the existing local Qwen3.5:4b Gateway. Admission took 0.166 and
0.088 s; this is not model-inference speed. Wrong GLOBAL context returned 403;
completed resume preserved the artifact. These jobs contain no media input.

Nike no longer emitted internal schema diagnostics but still substituted
financial-statement research for the requested content direction. Guangzhou
suggested a story-participation activity, but did not define a bounded pilot or
decision criteria; promotional language is not observed consumer demand.
Engineering reviews `business-review-<job_id>` are appended through Evaluation
and visible on scoped reopen. They are not Product Owner decisions, campaign
outcomes or market proof. No repeat prompt-only run is justified as acceptance.

Final DB: 270 Raw, 270 Canonical, 35 reports, 79 evaluations, 4 report tasks;
integrity=ok, FK violations=0. Source facts and historical drafts are unchanged.

## REAL DELIVERY CARD / 真实用户工作闭环验收

REAL USER JOB: ask a scoped operating/content research question and inspect its
evidence-backed proposal and separate quality review. ENTRY: real start/status/
reopen APIs. REAL INPUT: existing Guangzhou/Nike Canonical sources. PATH:
exact scope Permission → Source Brief → local model → signed derivative Evidence
→ immutable report → Evaluation → reopen. USER-VISIBLE RESULT: actual draft and
FAIL/UNKNOWN quality disposition. FAILURE/RECOVERY: rejected diagnostics remain
Evidence, historical report still reopens, current reports survive repeat reads
and duplicate resume; prior batch owns actual crash proof. ACCEPTANCE ASSERTION:
prose rejection/version compatibility TESTED; live scoped drafts verified;
task relevance/client usefulness REWORK, repeated human operation HUMAN_PENDING.
Frontend remains paused. No Round or Product Closure PASS.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: existing structured-output
approach checked against https://docs.ollama.com/capabilities/structured-outputs
(accessed 2026-10-01). It supports schema constraints and temperature 0; both
already exist. ADAPT validation at the current Reporting boundary; no new OSS
dependency. Structural JSON correctness is not semantic usefulness, as these
actual results demonstrate. Next work must evaluate task-relevant source
selection and model capability together, rather than accept schema-only output
or keep repeating the same prompt-only experiment.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: Global Commercial Coverage=NO;
Global Brand Coverage=NO; Guangzhou Reference=PARTIAL. COMMERCIAL OVERLAY IMPACT:
RELEASED=NO, OPERATING=NO, COMMERCIAL_READY=NO. Hosted CI still has the recorded
execution-layer blocker. Codex Cloud is a development environment and does not
prove LUMENIS hosting or independent inference.
