# ROUND 07 — persisted Source Brief jobs and artifact Evaluation

Base: `65329ba78c574f25e4c53c76825eeec7207f5f8c`.
Status: **bounded reporting API/runtime verified; full business Job and Round acceptance remain open**.

## Existing owner chain

The Experience API resolves the server-issued local workspace principal (or
existing account actor), validates the exact Registry scope and checks Reporting
Permission. The existing Shared Reporting projection reads signed Canonical
sources, persists a hashed artifact in `daily_reports`, reopens it, then records
artifact/source evaluations in existing `evaluation_records`. No account, job
database, Evidence store, scheduler or model provider was created.

POST `/api/experience/reports/source-brief/generate` accepts only `limit` and an
optional existing `resume_job_id`. GET
`/api/experience/reports/source-brief/jobs/<job_id>` verifies the same actor,
scope and artifact hash. Client-supplied identities/multimodal results are rejected.
Scope admission does not grant external effects. No source observations change.

## Real runtime evidence

Backup: `data/backups/pre-source-brief-jobs-20261001.db` (private).
After current-source static parsing, the verified Core child was restarted by
the existing supervisor. Core health returned healthy on loopback 8201; source
count and report contents below came from the actual product database.

| Scope | Report ID | Returned verified source count |
|---|---|---:|
| 广州太古汇 | brief-9dc970ea92d34c4d8feaecbfc54f7467 | 29 |
| 深圳罗湖万象城 | brief-06fe242896f64388a52129b1cbe08428 | 4 |
| Nike | brief-4e5c71aa504441c2b134976cb5b2ca25 | 29 |
| Le Labo | brief-db454f7a68fc403698dfc84e2a9b58e6 | 24 |
| CTH GLOBAL | brief-2f21417f428e4412905f9e3e83e3f242 | 29 |
| BMP GLOBAL | brief-35c575ddc55249bd9731d3b16f732cbe | 30 |

These are bounded query samples, not total coverage or freshness claims.
For the latter five reports, fresh HTTP reopen and same-ID retry returned the
identical result; cross-domain/scope reads returned 403. Six artifacts persisted;
`evaluation_records` advanced from 0 to 18: artifact integrity/source grounding
were assessed, while six multimodal metrics remain UNKNOWN. These are **not**
business impact, analysis accuracy, human acceptance or market proof.
Integrity check=ok; FK violations=0. Source data was not reseeded or cleared.

## Regression and recovery

113 tests passed, exit 0, errors/failures/skips=0, normal conftest and explicit
disposable v18 seed. Suites: source_brief_job_routes, source_brief_job,
local_workspace_principal, scoped_source_brief, multimodal_evaluation,
evaluation_system, content_project_listing_routes.

The first combined run failed one media-import neighbour because FFprobe was
not configured in that test process. Passing the existing FFmpeg/FFprobe paths
fixed the environment; the same assertions and entire suite then passed.
No test was removed or weakened. Constitution gate and current-source AST passed.

Tests cover actor/scope rejection, corrupt artifact hash, missing data remaining
UNKNOWN, interrupted Evaluation persistence and same-ID recovery, and distinct
same-scope/same-day reports. Stable Evaluation IDs reuse identical observations
without rewriting their time or silently replacing conflicting evidence.

## REAL DELIVERY CARD / 真实用户工作闭环验收

Job: collect a traceable scoped source brief and reopen the saved result.
Entry: the above Product Core routes; approved Flutter binding is separate work.
Input: actual signed Canonical data for the four entities and two global scopes.
Result: persisted/reopenable source brief, reference URLs and honest unknowns.
Recovery: same-ID retry; artifact tamper denial; no cross-scope reopen.
Acceptance: API/runtime verified only. Human repeated work is HUMAN_PENDING;
the Product Owner will operate it at consolidated acceptance. Multimodal analysis
is UNAVAILABLE in this batch, not completed by an assessment helper.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: Global Commercial Coverage=NO;
Global Brand Coverage=NO; Guangzhou Taikoo Hui Reference=PARTIAL.
COMMERCIAL OVERLAY IMPACT: RELEASED=NO, OPERATING=NO, COMMERCIAL_READY=NO.
CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: reused existing Reporting,
Permission and Evaluation contracts; no new external dependency was justified.
