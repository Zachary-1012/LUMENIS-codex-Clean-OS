# ROUND11 — bounded real CTH Case persistence

Date: 2026-10-01. Base: `d533f9a36b51e4197b994c394a9246d3d6d4d269`.
This is a contributing implementation Batch, not acceptance of ROUND11 or J1–J8.

## Task Card / canonical owner

- CTH `cth_cases.py`: operator question and selected exact source references.
- SYSTEM Permission and Effect Fence: existing local workspace principal,
  registered CTH Subject, dedicated internal Case operation and audited admission.
- Shared Database: additive v19 `lumenis_cth_cases`, Subject/Evidence foreign keys.
- Shared Reporting: reopen and verify the existing immutable Source Brief job.
- Shared Evidence: writer-authenticated creation trace, same transaction as Case.
- No second Case library, DB, Permission, Evidence, scheduler or AI provider.
- Root inspected the bounded Luna schema slice and integrated application/API/tests.
  No Ollama, Zhipu or other retired inference route ran.

## API contract

`POST /api/experience/cth/cases` accepts only `submission_id`, `title`, `question`,
`source_job_id`, `source_ids` (1–8 distinct IDs from the verified source job).
The server resolves the principal and exact focused CTH Subject; client actor,
state and scope fields cannot grant access. Subject status follows the Registry's
configured/non-archived rule. Global and BMP Case writes are rejected.

`GET /api/experience/cth/cases/<case_id>` rechecks scope, source signatures,
creation signature and row/material binding. It never repairs or writes a Case.
IDs use `CASE-` followed by32 lowercase hex characters, not the old fixture IDs.
Result includes question, title, OPEN state, exact scope, sources, original report
hash, creation Evidence and a CASE timeline step. Analysis is NOT_REQUESTED;
business Outcome is NOT_OBSERVED. Publish status is not_performed.

Same submission and exact intent return the original Case. Conflicting intent
fails without overwrite. Permission is checked again after lock acquisition and
all report/source checks immediately before persistence. Case plus signed trace
commit atomically; failure rolls both back. This grants no general DB-write,
publisher, approval, Source Truth modification or external Action capability.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

- REAL USER JOB: register a source-backed venue investigation for later analysis.
- ENTRY: actual Core8201 APIs above; CTH-08 Case board remains unbound.
- REAL INPUT: existing Taikoo Hui source job
  `brief-350d84ee6a4b4519ab8815837a49b997`, official directory sources
  `public-http:b69b746ea9b8138823d69d03dcb529ac`/Evidence139,
  `public-http:ad654f47c6646063de7416c64ba2aa3f`/Evidence138,
  `public-http:2fb8233aa770144c5f76c574f6b51c05`/Evidence121.
- END-TO-END PATH: exact context → source job/signatures → Permission → locked
  validation → fresh authorization → atomic Case/creation Evidence → reopen.
- USER-VISIBLE RESULT: persisted API Case
  `CASE-c8f477f099e7a0d61880dce7563411cc`, creation Evidence444, question about
  venue brands/tenant categories and missing consumer/propagation support.
- FAILURE/RECOVERY: source/Case tampering rejected; denied and invalid intent
  produce no Case; isolated insert failure rolls back trace and Case then recovers;
  repeat is NOOP; conflict400; actual Luohu/GLOBAL read/write403; actual restart
  reopens the identical Case without duplicate records.
- EVIDENCE: source snapshot hashes, signed creation record, actual DB fingerprints,
  test XML and runtime proof; private DB and local proofs are not Git assets.
- ACCEPTANCE ASSERTION: automated real-data technical chain verified. No actual
  human operated this Batch, no generated Insight/Decision/Action, no observed
  business Outcome. Product Owner repeated E2E remains deferred to final review.

## Verification and protected data

Final source patch SHA256:
`ff530297a3d5aaa056472df07eb6d44b37d1c0928fea164ab8ddda87aa15bbe5`.

Nine owner/neighbor suites: Case schema/routes, migrations, local principal,
app Effect Fence, database ownership/scope registry, source job/routes.
150 tests,0 failures/errors/skips,48.200s,exit0. The regression includes revocation
after request admission and before transaction write:403,Case0,creation Evidence0.
AST10 changed Python files PASS. Constitution and database-authority checks PASS.
Existing boundary advisory:9MEDIUM/11INFO,0HIGH. No gate weakened or quarantined.
Two stale latest-version assertions now require19; explicit historical v18 tests
retain their18 target. The runtime source guard excludes installed virtualenv
dependencies, consistent with the existing canonical AST boundary policy.

Canonical backup `data/backups/pre-cth-case-real-20261001T081605Z.db` preceded
actual migration. Disposable clone18→19 + second NOOP passed; restoring the
backup into another disposable clone retained exact table fingerprints.
Actual migration changed only schema_version and added an empty Case table;
all112 pre-existing non-version tables retained exact rows. Integrityok/FK0.
The real request then added exactly one Case and one creation Evidence, preserving
notes, Canonical, Registry, reports, entity relations, evaluations and source
Evidence fingerprints. Two verified Core reloads preserved Supervisor19440;
workers8600/35596 were healthy after the final restart and the identical Case
reopened. No production data was deleted or reseeded.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

ADAPT: [SQLite transaction control](https://www.sqlite.org/lang_transaction.html),
accessed2026-10-01 (page updated2026-02-18; actual SQLite3.50.4). Use the existing
Shared Database transaction connection and BEGIN IMMEDIATE for one writer;
Evidence and Case must share the same commit/rollback. No copied dependency or
new third-party component. Existing signed operator-review write owner supplied
the fresh authorization pattern. Security review found an admission-only check
could expire while waiting for a lock; final source and revocation test correct it.
The final immutable-patch assessment returned merge / human_review_required,
validated JSON, no remaining blocking defect. Root reviewed that evidence and
accepted this bounded technical Batch under existing Product Owner authorization.
High-impact persistent/Permission changes still require coordinated rollback;
reverting code must preserve created Case and Evidence rows, not drop them.

## GLOBAL UNIVERSE / DATA MATURITY IMPACT / COMMERCIAL OVERLAY IMPACT

Global Commercial Coverage=NO; Global Brand Coverage=NO;
Guangzhou Taikoo Hui Reference Coverage=PARTIAL;
LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO. This Batch adds no collected coverage.
Case sources preserve venue tenant/brand scope, not global brand performance.
No observed campaign result, ROI, competitor benchmark, operating proof or
commercial acceptance. RELEASED=NO,OPERATING=NO,COMMERCIAL_READY=NO.

Next eligible gaps: CTH-08 real Case read/UI binding, owned useful reasoning and
the CTH Case→Insight→Decision→Action→Outcome chain. Those are existing ROUND11
obligations; no new Round/Owner is introduced. Hosted PASS remains limited to
source038fe598 until another milestone's exact Product/App source is tested.
