# ROUND 07 — operator disposition of an existing report

- Base HEAD/origin `ceae183f333ef9dae9f637619b37bcab2153a0ba`; `work/` preserved.
- Owner: Shared Reporting, existing signed Evidence/Evaluation stores; server
  Permission remains SYSTEM owner. No new database or authority.
- Rules: AGENTS, Constitution, Product Architecture, Source Owner Index,
  Real Delivery Overlay, Permission/Evidence and DB-safety contracts.
- Current gap: generation/reopen and engineering feedback exist; no operator
  accept-for-next-step / request-changes / reject write, idempotency or recovery.
- Task: signed, append-only disposition of one immutable artifact with fresh
  actor/scope/write Permission and a dedicated bounded REPORT_REVIEW operation.
  Reuse the existing Evidence writer and Evaluation recorder; maintain history.
- Not authorized by this input: changing Canonical facts, editing the original
  artifact, publishing, executing a proposal, declaring observed business impact
  or upgrading product/real-user acceptance. HUMAN_PENDING remains independent.
- Worker allowed paths: Reporting operator_review.py and its isolated tests.
  Root owns route, Permission operation/resolver, response and final integration.
- Acceptance: explicit real-input engineering disposition and readback; duplicate
  replay, conflicting replay, foreign actor/scope, signature failure, revocation,
  interrupted Evaluation persistence/recovery, original artifact unchanged.
- User performs final repeated E2E; frontend remains paused. This is an existing
  J2/J3/ROUND07 integration path, not a new Round or user-acceptance claim.

Current research is reused from BUSINESS-PILOT-RESEARCH-20261001.md: feedback
must revise a proposal and must not turn output/review into business outcome.
No new dependency, model, external service or duplicated research is required.

## API integration contract (candidate; execution evidence below)

`POST /api/experience/reports/source-brief/jobs/<job_id>/reviews` uses the
existing workspace principal and exact CTH Subject/BMP BrandFocus headers.
Its JSON body has only `submission_id` (canonical UUID), `decision` and `notes`.
Allowed decisions: `use_for_next_step`, `request_changes`, `reject`.
Notes are untrusted plain text (1–2000 characters); consumers must render them
as text, never HTML or instructions. A decision is a report disposition, not
Permission to execute an action, publish, train or promote a learning asset.
The frontend should retain one submission ID across retries of unchanged input;
changing the payload with the same ID is a conflict. A new disposition appends
history and uses a new ID. Original report bytes and Evidence remain unchanged.

The existing report/task reopen response exposes `operator_review` independently
of immutable generation output, technical evaluations and `HUMAN_PENDING`.
This is an additive backend contract, not a UI implementation or real-user pass.
Codex Cloud in the user's shared chat is development infrastructure only;
it does not establish LUMENIS product hosting or owned-AI deployment.

## Actual verification and disposition

- `104 passed in 28.39s`, exit 0: operator review owner/routes, Source Brief
  job/routes/tasks, SYSTEM Security convergence and dual-domain Permission.
  Explicit isolated v18 seed; no background-thread leaks.
- Tests exercise all three decisions, foreign scope/actor/Origin/proxy headers,
  revocation before Evidence and Evaluation writes, exact route classification,
  changed replay conflict, HMAC tampering and Evidence-only failure/recovery.
  The earlier test run's pending-state naming mismatch was corrected, not waived.
- Final source compile, Constitution and `git diff --check`: exit 0.
- Root rejected the worker's initial verified/pending/rejected Evidence status
  mapping and unbounded reader. Every decision is now `derived / RECORDED`,
  business outcome stays `NOT_OBSERVED`, Evaluation value NULL/status unknown.
  Reads filter exact identity before LIMIT 51 and return at most 50, with honest
  truncation. Missing Evaluation is `pending_recovery`; same submission repairs
  it after fresh Permission. Original report and its HUMAN_PENDING stay intact.
- Codex Security bounded immutable-patch assessment SHA256
  `b3b83a0c2e9392af1cdbec344208540200d8b56e66f846388c8abbf0bcf51c08`:
  merge advisory / human_review_required; persistent-state/public-contract risk
  excludes automatic merge. Root reviewed/accepted this bounded source batch;
  this is not Product Owner or full product acceptance.

### 真实用户工作闭环验收 / REAL DELIVERY CARD

- REAL USER JOB: review a saved brand recommendation and request specific
  changes without destroying its source trail or original output.
- ENTRY: existing report/job route and new reviews endpoint; frontend unchanged.
- REAL INPUT: actual v5 Nike report `brief-ca26452b7adb4ffdbc9a8fcd263e81f0`,
  artifact `b866afff4bbe3409b1e962837715f2fec4d5710c69374e275276e99ec8c15b8b`.
  Engineering request_changes explicitly identifies unsupported consumer
  generalization and the unavailable historical comparison baseline.
- END-TO-END PATH: real open-workspace principal -> exact Nike BrandFocus ->
  REPORT_REVIEW Permission -> signed Evidence 438 -> Evaluation
  `32d907c84350bf602a96549a2881de5890c6557efc4c10fa81abe6e9e5d54437` -> report/task readback.
- USER-VISIBLE RESULT: API returns preserved report plus separate review;
  UI/real-user operation is **LIVE_NOT_VERIFIED / HUMAN_PENDING**.
- FAILURE/RECOVERY: same submission replays exactly with one Evidence/one
  Evaluation; GLOBAL scope denied 403, changed replay denied 400. Actual Core
  supervisor recovered after controlled wrapper termination; saved review and
  unchanged artifact reopened. Partial Evaluation failure tested in isolated DB.
- EVIDENCE: backup `data/backups/pre-operator-review-20261001.db`; live readback,
  stable IDs above, no duplicate review; source/daily-report ordered row digests
  identical to backup. Notes270, Canonical270, reports44, evaluations110,
  Evidence438; integrity ok, FK0. Product data/backup not committed.
- ACCEPTANCE ASSERTION: bounded backend path LIVE_VERIFIED; engineering feedback
  is not the user's acceptance, observed campaign result or business-value proof.
  User personally performs final repeated jobs. Round07 remains REWORK.

COMMERCIAL OVERLAY IMPACT: no publishing/action, no market claim, no release.
GLOBAL UNIVERSE / DATA MATURITY IMPACT: no new sources or scope rewrites;
Global Commercial/Brand Coverage remain NOT VERIFIED, Guangzhou reference
PARTIAL, FULL_UNIVERSE_READY=NO. Codex Cloud remains development-only.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: reused the existing
Strategyzer/AMEC principles with the pinned research note; feedback is derivative
and cannot convert report generation into observed outcome. No new dependency.
Next: bind approved report revision to this feedback through the existing
Reporting owner, and preserve user review/real business-outcome gaps honestly.
