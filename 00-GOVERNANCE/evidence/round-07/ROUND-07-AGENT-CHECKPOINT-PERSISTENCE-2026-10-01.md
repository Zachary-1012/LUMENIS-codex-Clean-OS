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
