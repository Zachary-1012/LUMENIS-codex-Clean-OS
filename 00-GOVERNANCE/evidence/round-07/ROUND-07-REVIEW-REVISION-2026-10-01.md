# ROUND07 — stored report feedback into an immutable revision

- Base HEAD/origin: 274b8f4dbad5d88a5ef222c23eb1cbe02d9c1ceb; preserve work/.
- Owner: existing Shared Reporting; SYSTEM TaskEngine stores references only.
- Rules: AGENTS, Constitution, Source Owner Index, Real Delivery Overlay,
  existing Permission/Evidence and database safety; no parallel store/authority.
- Entry: existing async Source Brief start endpoint with a revision reference.
  Input is only parent job ID + signed review ID, not caller-supplied feedback.
- Resolve same actor/exact scope, immutable parent, signed request_changes review
  and recorded Evaluation. Reuse the parent's question, actual analyzed source
  IDs and media reference. Recheck at worker execution and artifact commit.
- Feed feedback and old derivative separately from source facts. Retain original
  and new artifact identity, signed revision lineage and honest quality states.
- Test: denial before model/persistence, tamper, recovery/reopen, unchanged old
  artifact, actual real Nike request_changes -> new job. User acceptance pending.
- Root: operator_review, source_brief_job/tasks, business_brief and API binding.
  Luna: only optional TaskEngine reference shape + its existing unit tests.
- Reuse recorded Strategyzer/AMEC research; no new model, cloud, dependency or UI.
- Native Goal remains active; Codex Cloud is development environment only.

## Implemented path and automated evidence

Existing `/api/experience/reports/source-brief/start` accepts only a `revision`
object containing parent_job_id and review_id. Server actor/exact scope, parent
artifact hash, signed request_changes and recorded Evaluation are resolved before
admission, worker execution, derivative Evidence and artifact persistence. Saved
references do not carry authority. Reopen verifies the direct signed feedback;
it does not recursively traverse all historical drafts. Matching review lookup
is bounded to two rows to detect duplicate/corrupt state without materializing it.
Original question, actually analyzed source IDs and media input are inherited.

Business analysis version 6 separates old derivative/review from source facts;
versions 1-5 remain readable. TaskEngine has only an optional validated reference.
No schema, source data, model routing, provider, frontend or cloud changes.

- 115 isolated affected tests: PASS, 46.89 seconds, exit 0, no thread leaks.
- After final LIMIT 2 bound: 30 review/revision/route tests PASS, 15.17 seconds,
  exit 0, no thread leaks. Syntax and blocking gates are recorded at publication.
- The real unchanged output exposed one additional acceptance-state defect.
  New generations now reject structurally unchanged analysis with
  `BUSINESS_BRIEF_REVISION_UNCHANGED`, preserve signed rejected-candidate Evidence
  and expose unavailable, without automatic regeneration. Changed drafts remain
  HUMAN_PENDING, not automatically useful. Existing Evidence439/report remain
  immutable historical output with the FAIL Evaluation. The final analyzer/
  revision group passed 38 tests (22.87s, exit0/no leaks), including unchanged
  candidate rejection, failure Evidence, reopen/resume and unchanged parent.
  This guard is TESTED, not a claim of another live model run or improved quality.
- Luna inspected only the bounded TaskEngine shape/tests, then an independent
  read-only review-reference check. Root adopted the LIMIT 2 correction. No
  worker commit/push. OpenCode/Zhipu was not retried after its earlier missing
  Authorization failure; no external-provider result is claimed for this batch.

## 真实用户工作闭环验收 — REAL DELIVERY CARD

- REAL USER JOB: revise an existing Nike content pilot after request_changes.
- ENTRY/REAL INPUT: existing async endpoint; parent
  `brief-ca26452b7adb4ffdbc9a8fcd263e81f0`, signed engineering review Evidence438
  `a52d309725907d3a8475a9296e0d38cb1423f93ee0075683373f34648c15de01`.
  Canonical source IDs `7683910956972529103` and
  `public-http:990756e975bd19f8c5c84c4c9c487a7c`; exact Nike BrandFocus retained.
- END-TO-END PATH: current permission -> stored review/parent -> managed task
  `rbrief_ed98d4bf-1d5b-4745-a286-ac8e3cf4a3ba` -> local Ollama qwen3.5:4b ->
  signed derivative Evidence439 -> new immutable report
  `brief-b8088e39a0744eba96d02dfeb536e375` -> reopen -> Evaluation.
- USER-VISIBLE RESULT: API returns source-linked revision and separate review
  history. Admission 0.227373 seconds; completion 150.51 seconds. Artifact hash
  `97044b0465850bee603344d82d5c526b09c2367d771b45ff82a1816b6a18f28d`.
  Frontend integration/user-operated review remains pending; backend entry only.
- FAILURE/RECOVERY: duplicate completed-task resume does not generate again;
  wrong GLOBAL scope 403; actual supervised Core child termination/restart
  followed by exact parent/new artifact/feedback readback and Evaluation FAIL.
  Recovery proof ran before the final read-query LIMIT 2 bound; that final bound
  has the 30-test regression above, not an additional live model invocation.
- EVIDENCE: signed inputs contain exact feedback and previous analysis. The
  generated analysis is structurally identical to the previous analysis. Its
  creator-to-consumer generalization and unsupported 20-percent baseline remain.
  Canonical engineering evaluation
  `business-review-brief-b8088e39a0744eba96d02dfeb536e375` = FAIL (0.0).
- ACCEPTANCE ASSERTION: revision transport/persistence/recovery verified;
  effective content correction NOT ACCEPTED. Model output is not business
  Outcome or Product Owner acceptance. HUMAN_PENDING remains; no action executed.

## Data protection and scope limits

Backup: `data/backups/pre-review-revision-20261001.db` (private, not committed).
Raw270/Canonical270 ordered-row hashes match backup; all prior44 report rows
match. One new report only. Reports45, evaluations114, Evidence439, tasks13;
integrity_check=ok, FK violations=0. The first engineering inspection used the
view-model scope instead of the analyzer scope and failed before any write;
using the existing `_media_scope` conversion verified the signed input correctly.

COMMERCIAL OVERLAY IMPACT: no publishing, customer, ROI, time/cost superiority,
release or operating acceptance. Final repeated real-user work belongs to PO.
GLOBAL UNIVERSE / DATA MATURITY IMPACT: unchanged coverage; no new collection or
scope rewrite. GLOBAL/FOCUS coverage remains as previously recorded, not YES.
CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: reuse already recorded
Strategyzer/AMEC pilot/evaluation rationale through existing Reporting owners;
no new research/model experiment justified by this reference-binding batch.

The quality defect is retained for the existing AI/Reporting owner; do not call
an identical draft an effective revision or spend repeated identical model calls
to manufacture progress. Hosted same-SHA, owned independent AI, frontend and
Product Owner repeated E2E remain outstanding. ROUND07/J packages remain REWORK.
