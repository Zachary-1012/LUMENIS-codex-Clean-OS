# ROUND 07 — Agent checkpoint persistence repair

## Bounded context and Task Card

Base local HEAD, fetched origin/main and live main:
`80014252a93c32d4256676a739532fc852c09f9f`.
Capability locator: `agents_skills`, query `durable`. Owner: existing Agent
Runtime / TaskEngine, with Shared Database and canonical Permission boundaries.
Protected untracked `work/` remains untouched.

Rules: root AGENTS, AI-native Constitution, Product Architecture, Source Owner
Index and Real Delivery Overlay. Exact source: `agent_runtime/durable_adapter.py`
and `ai_task_engine.py` create/get/step/cancel APIs. Tests:
`tests/agent_runtime/test_durable_adapter.py` and neighbouring AgentLoop tests.
Historical input: `intelligence_library/01_序境产品研究/FULL-PRODUCT-UPGRADE-CLOSURE-RESEARCH-20260929.md`,
durable/context recovery section — ADAPT the already researched requirement to
persist full checkpoints through TaskEngine; no second runtime or queue.

Observed blocker: enabled adapter calls the old `task_input` argument and treats
a returned task dictionary as its task ID. Errors silently fall back to memory.
Checkpoint plan/context is not included in the persisted step. Therefore the
existing facade cannot establish restart recovery for long-running work.

Task: correct the real TaskEngine binding, persist versioned full checkpoint
payload in the existing step field, and reopen task/plan/context with a fresh
adapter. Enabled durable failures must be explicit; disabled mode stays an
explicit memory mode. Intermediate step completion must not complete the entire
task. Keep DB-write permission denial intact.

## Verification

49 targeted adapter/persistence/AgentLoop tests passed with normal conftest,
explicit disposable v18 seed, no failures/errors/skips and no thread leaks.
The new enabled-mode tests use the real TaskEngine and its existing tables,
with an explicit test-only permission fixture. They prove stable task identity,
full checkpoint reopening, agent/context preservation, large result retention,
permission revocation, DB failure with no memory fallback, missing engine,
malformed/foreign checkpoint denial and corrupt-context detection. Completion
of one step leaves aggregate task status unchanged; cancellation is reread from
the actual task row.

A separate two-process disposable DB experiment saved a task and checkpoint,
terminated its writer with intentional exit 23 after commit, then opened a fresh
Python process. Reader exit 0 and assertions proved the same task/checkpoint ID,
plan and context survived. Its permission fixture was explicitly permissive:
this is storage/crash integration evidence, not live product permission proof.
The production DB remained at 270 Raw, 270 Canonical, 22 reports, 34 evaluations,
zero ai_task and zero ai_task_step rows, integrity=ok and FK=0.

No new report worker, automatic replay, report start/poll API or product-user
acceptance is implied. DB_WRITE remains subject to the real canonical approval
gate; default denial is now visible. Existing retry counters and automatic
AgentLoop continuation are not established by this batch. Legacy unstructured
checkpoints fail explicitly instead of fabricating recovered context. New
checkpoint writes retain a versioned envelope in the existing step detail.

Python compile and AI-native Constitution gate pass on the current source.
The bounded Luna produced the initial adapter patch; root took over, reviewed
and completed input validation and real persistence tests. No model provider
call or additional compute route was used for this batch.

## REAL DELIVERY CARD / 真实用户工作闭环验收

User job: resume a saved analysis task after interruption without losing its
plan or context. This bounded dependency repairs persistence only. The existing
Source Brief report API is still synchronous, and its full asynchronous
start/status/recovery path remains to be integrated with exact actor/scope and
effect checks. Public AI task routes are not an approved substitute for that
report boundary. No Collector queue is repurposed.

Real user acceptance remains HUMAN_PENDING for the Product Owner's final review.
GLOBAL UNIVERSE / DATA MATURITY IMPACT: Commercial Coverage=NO; Brand
Coverage=NO; Guangzhou reference=PARTIAL; no coverage expansion in this batch.
COMMERCIAL OVERLAY IMPACT: RELEASED=NO; OPERATING=NO; COMMERCIAL_READY=NO.

## 2026-10-01 — AgentLoop supplies the actual checkpoint contract

Current bounded base:980aa6c984d960ee2323d660664e4b502b848e3e, fetched
origin/main and live main verified. Existing Agent Runtime / TaskEngine / Shared
Database / SYSTEM Permission owners remain; no alternate queue or OSAI runtime.
Context uses the current locator, router, Constitution, owner index and existing
durable persistence proof. Protected work/ and other workers' learning files are
excluded from this Batch.

AgentLoop persists the current canonical Plan/PlanStep identifiers, statuses,
results and numeric token metrics through DurableExecutionAdapter. The completion
snapshot overlays the actual just-finished step before the normal loop mutates
it, and records projected cumulative cost without charging it twice. It records
elapsed execution time, started-step count, replans and limits. Replanning updates
the current checkpoint plan. Task and checkpoint contexts persist only actor_id,
domain_id and scope; the original execution context remains in RAM.

Raw planner output and secret fields are omitted. Recognizable credential values
in persisted task goals, plans, results or step details are redacted; affected
snapshots are non-resumable. Numeric token_usage is retained. These filters are
supplemental pattern screening, not proof that arbitrary private text is safe.

Verification command:
`python -m pytest -q tests/agent_runtime/test_loop_checkpoint_contract.py tests/agent_runtime/test_loop.py tests/agent_runtime/test_durable_adapter.py tests/agent_runtime/test_durable_persistence.py`
passed52 tests, no failures/errors/skips or background-thread leaks. The three
new tests reopen actual isolated TaskEngine SQLite storage, check completed
identity/result/cumulative budget, confirm context filtering and secret omission,
and prove persisted goal redaction while the execution goal is unchanged. Security
is stubbed only for this checkpoint-storage test; it proves no production approval.
No production DB write, provider call or real product-user task was performed.

REAL DELIVERY CARD / 真实用户工作闭环验收: the job remains interrupted analysis
continuation. This Batch closes IMPLEMENTED→TESTED checkpoint serialization only;
there is still no execution resume API. The earlier oversized untested candidate
is preserved in work/osai-resume-candidate-20261001-211338 and is not accepted.
Next step is canonical fresh authorization, exact actor/domain/scope, cumulative
budgets and uncertain-effect handling in the existing loop. Real useful owned
CTH/BMP analysis and final PO repeated-job acceptance remain open.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: ADAPT OSAI's durable-task
requirement to the existing TaskEngine; REUSE this repository's checkpoint owner,
not its former independent JSON state store. OSAI live main was rechecked as
6487532205067d5d3568b75bc7ea5f842dede578. No proprietary weights or trained OSAI
reasoning are claimed. GLOBAL UNIVERSE / DATA MATURITY IMPACT: CommercialNO,
BrandNO, TaikooPARTIAL. COMMERCIAL OVERLAY IMPACT: RELEASED/OPERATING/
COMMERCIAL_READY=NO. ROUND07 remains REWORK until its real user-work gates close.

## 2026-10-01 — actual execution resume through the same driver

Base HEAD/origin/main 0c54616ea56644945619f5836b7cc4205b3c29e1. Existing
Agent Runtime / TaskEngine / Shared Database / SYSTEM Permission owners.
`AgentLoop.resume(task_id, context=...)` validates the durable task/checkpoint,
restores the exact plan and cumulative usage, and executes only remaining steps
through the existing run loop. It does not plan again or create a second task.
Completed-result reads require fresh authorization and add no checkpoints.

Fresh trusted actor, canonical domain, exact typed scope and current DB scope
grants are required. Resumed PermissionGate checks omit the previous operation
ID because its cached allow could survive revocation; stable PlanStep IDs remain
at the Effect Fence. Wrong/revoked bindings return no prior goal/plan/result.
Interrupted READ may re-execute under the current security chain; uncertain
WRITE/EXPORT/COMMIT/PUSH/DEPLOY stops for reconciliation before effect checks or
tool calls. Missing/malformed/cancelled/non-resumable/memory-only checkpoints
are refused. Missing real executor blocks instead of simulated success.

Elapsed/cost/started steps/replans do not reset. Current/saved limits take the
minimum. Enforcement checks occur between synchronous tool calls; a hard
per-step cancellation deadline is NOT_ENFORCED by the existing executor and is
reported in result metrics. This Batch does not introduce unsafe background
threads to claim cancellation. Required failed steps cannot produce completion.

Root reviewed the coherent +326/-45 core candidate and accepted its necessary
validation/security branches above the approximate 200-line target; no cosmetic
compression, alternate executor or new owner was introduced. The final guard
and documentation delta remains in the same bounded capability Batch.
Root replay uses an explicitly created empty SQLite seed in an OS-temp directory
via LUMENIS_TEST_SEED_DB; each fixture initializes its own isolated tables. The
repository P0-C guard refused an earlier attempt because protected data/monitor.db
had WAL/SHM sidecars. Those files were neither removed nor checkpointed. The
five resume/checkpoint/loop/durable suites passed69 tests (17 new plus52 prior),
with no thread leaks. Constitution/governance gates remain blocking publication.

REAL DELIVERY CARD / 真实用户工作闭环验收: ENTRY is AgentLoop.resume; REAL INPUT
is reopened isolated TaskEngine with current canonical authorization tables;
USER-VISIBLE RESULT is same-task continuation and repeat NOOP. FAILURE/RECOVERY
covers revoked cached allow, wrong scope/actor, uncertain effect, malformed
checkpoint and restored budgets. ACCEPTANCE ASSERTION is TESTED source, not an
actual Source Brief/CTH/BMP report, provider activation or ROUND07 PASS.
CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: ADAPT OSAI durable-session
semantics to this existing owner, preserving fresh permission and one executor.
GLOBAL UNIVERSE / DATA MATURITY IMPACT and COMMERCIAL OVERLAY IMPACT remain
Commercial/BrandNO, TaikooPARTIAL, RELEASED/OPERATING/COMMERCIAL_READY=NO.
