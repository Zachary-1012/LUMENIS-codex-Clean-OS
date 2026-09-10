# LUMENIS — CODEX ZERO-DISCOVERY PREPARATION & PRODUCT CLOSURE HANDOFF

Date: 2026-09-10

## Objective

Complete every pre-Codex task that can be completed without pretending implementation is finished. Codex must not need to redo whole-repository discovery, product architecture reconstruction, DB/Route/API/Test/Runtime inventory or P0/P1/P2 classification.

Execution loop: `READ HANDOFF -> VERIFY BASELINE -> MODIFY CODE -> TEST -> RUNTIME -> E2E -> EVIDENCE -> COMMIT -> NEXT TICKET`.

## Roles

Doubao = PRE-CODEX WORK ORCHESTRATOR / SOURCE AUDITOR / ENVIRONMENT PREPARER / EVIDENCE BUILDER / TASK COMPILER / DEPENDENCY PLANNER / TEST PLANNER / RUNTIME PLANNER / GIT SAFETY CONTROLLER / CODEX HANDOFF BUILDER.

Codex = PRIMARY IMPLEMENTATION ENGINEER / SOURCE CODE MODIFIER / TEST EXECUTOR / RUNTIME DEBUGGER / E2E EXECUTOR / PRODUCT CLOSURE ENGINEER.

## Required pre-Codex outputs

1. Re-lock current GitHub/local repo, branch, HEAD, dirty state, remotes, ahead/behind, local-only and unpushed work. Protect valid P0-C/P0-D work; no force push/reset-hard/clean.
2. Reuse Source Truth Index only if recorded HEAD still matches. Otherwise update drift only. Build `CODEX_SOURCE_TRUTH.json` with source, symbols, routes, runtime registration, API consumers, DB readers/writers, tables, env, migrations, background jobs, collectors, AI/Agent, Evidence/Canonical/Metric/Report/Export, auth/permission/settings/browser/subject consumers, UI pages, tests and E2E. States: VERIFIED/PARTIAL/UNREACHED/UNKNOWN/LEGACY_REFERENCE/NOT_IMPLEMENTED/BLOCKED.
3. Build `CODEX_DB_CONNECTION_MAP.json`. Re-verify all sqlite/SQLAlchemy/get_conn/path/default/import/startup/fallback paths. Treat `ZBC_DB_PATH` as current target isolation contract unless canonical source proves newer. Classify CANONICAL/SAFE_OVERRIDE/HARD_CODED_BYPASS/IMPORT_TIME_BYPASS/RELATIVE_PATH_RISK/FALLBACK_RISK/LEGACY_UNREACHED/UNKNOWN.
4. Reconcile P0-C carry-over: migration atomicity, FK policy/debt, Evidence parent NULL normalization, ai_task orphan debt, Alembic/manual ownership, backups, clean bootstrap, historical/production candidate migrations, test isolation, protected DB/WAL/SHM guards, full-suite failures. Classify CLOSED/IMPLEMENTED_BUT_UNVERIFIED/OPEN/SUPERSEDED/BLOCKED. Never delete historical data to manufacture PASS.
5. Classify every current full-suite failure/error into `CODEX_TEST_FAILURE_MATRIX.json`: test, error, root cause, source owner, capability, priority, code/env/credential/external dependency, ticket and acceptance test. Root classes include REAL_PRODUCT_DEFECT/DB_ISOLATION/MIGRATION/OLD_CONTRACT/MISSING_MODULE/AUTH/EXTERNAL_COOKIE/AI_PROVIDER/ENVIRONMENT/LEGACY_TEST/TEST_POLLUTION/DATA_FIXTURE/UNKNOWN. Never delete tests to get green.
6. Build `CODEX_RUNTIME_MANIFEST.json`: actual entrypoint/app factory/host/port/environment/DB identity/startup dependencies/blueprints/background jobs/scheduler/AI/collector dependencies, plus exact isolated start/stop, health, route dump, DB identity, protected DB, P0 test, runtime test and Critical E2E commands.
7. Build `CODEX_ROUTE_CONTRACT_MATRIX.json`: Page -> JS consumer -> API -> Blueprint -> Route -> Service -> DB/Canonical/Evidence -> Response Contract -> Test -> Runtime -> E2E. States MATCHED/BROKEN/404/FAKE_200_RISK/DEAD_CONSUMER/ORPHAN_ROUTE/DUPLICATE_ROUTE/LEGACY/UNKNOWN.
8. Convert Capability Registry into executable truth: capability ID/domain/owner/source/runtime owner/data owner/evidence owner/UI consumer/test/status/missing layer/next ticket. MULTIPLE requires evidence-grounded KEEP/MERGE/ADAPTER/DEPRECATE_LATER or CODEX_DECISION_REQUIRED.
9. Build `CODEX_PRODUCTION_TRUTH_MAP.json` for Evidence, Canonical Data, Metric, Event, Case, Risk, Report, Export, Collection, KOS/KOL/KOC/UGC, Campaign, Podcast, Research, Evaluation, Operations, AI and Agent.
10. Build `CODEX_SUBJECT_CONTEXT_IMPLEMENTATION_MAP.json`; do not insert broad Subject Context implementation ahead of DB/runtime blockers.
11. Build `CODEX_UI_IMPLEMENTATION_MAP.json` for desktop/tablet/mobile, responsive IA, drill-down, KPI/trend/table/evidence/action, modal/drawer/toast/loading/empty/error/permission/runtime states, charts/motion/navigation/settings. Legacy UI is capability evidence only.
12. Build `CODEX_SECURITY_RECOVERY_MATRIX.json` for READ/TASK/AUDIT/WRITE/DEPLOY/admin, AI/Agent/browser actions, DB writes, network, secrets, logs/minimization, backup/rollback/migration rollback/runtime-scheduler-collector failure/circuit breaker.
13. Build `CODEX_ENVIRONMENT_REPORT.md`; install/verify only compatible dependencies actually required. Do not print secrets. Do not upgrade technology merely for novelty.
14. Preserve OpenCode config. Probe Zhipu at most once when needed; record AUTH/RESOURCE/BALANCE/NETWORK/MODEL/UNKNOWN and stop retrying. Ollama may assist after factual inventory but cannot replace source/runtime/test evidence. Cloud AI must not become an accidental startup hard dependency.
15. Define CANONICAL_MAIN/CODEX_WORK_BRANCH/BACKUP_BRANCH/RC_BRANCH_POLICY/COMMIT_POLICY/ROLLBACK_POINT. Commits must be single-purpose, testable, rollback-safe and evidence-linked.
16. Derive dependency DAG from facts. Default spine to verify: Repository Integrity -> DB Isolation -> Migration/FK -> Runtime Startup -> Route Registration -> API Contract -> Frontend Consumption -> Evidence/Canonical Ownership -> Capability Closure -> Security/Permission -> Subject Context -> CTH/BMP -> Cross-domain Capabilities -> AI/Agent Boundary -> Responsive UI -> Critical E2E -> Recovery -> Production Acceptance -> Release Manifest -> Rollback Drill -> RC -> Production -> Final Re-audit. Mark safe parallel groups.
17. Compile every actionable issue into a Codex ticket containing TICKET_ID, PRIORITY, BLOCKER, STATUS, DEPENDENCIES, PARALLEL_GROUP, PRODUCT_CAPABILITY, ROOT_CAUSE, VERIFIED_EVIDENCE, EXACT_FILES, EXACT_SYMBOLS, ROUTES, TABLES, FRONTEND_CONSUMERS, CHANGE_SCOPE, DO_NOT_TOUCH, IMPLEMENTATION_INTENT, IMPLEMENTATION_STEPS, UNIT_TEST, INTEGRATION_TEST, RUNTIME_TEST, E2E, DB_GUARD, SECURITY_CHECK, EVIDENCE_REQUIRED, ACCEPTANCE_CRITERIA, ABORT_CONDITION, ROLLBACK, EXPECTED_COMMIT, MODEL, SIZE. Status only READY_FOR_CODEX/BLOCKED_EXTERNAL/NEEDS_CODEX_RUNTIME/POST_CLOSURE.
18. Fix FIRST_TICKET, FIRST_10_TICKETS, FIRST_PARALLEL_GROUP, FIRST_RUNTIME_GATE, FIRST_E2E_GATE and FIRST_COMMIT_BOUNDARY.
19. Production Acceptance requires all six gates: P0=0; Repository Integrity; Production Truth; Runtime+Critical E2E; Security+Recovery; Release Lineage+Rollback. PARTIAL/UNKNOWN/docs-only/file-exists/page-opens are not PASS.
20. Create/update `CODEX_RESUME_PACK.json` with repo/branch/head/clean state/backup/current phase/maps/DAG/tickets/P0/P1/post-launch/protected DB/do-not-touch/commands/gates/rollback/production status.
21. Keep human `CODEX_START_HERE.md` short and actionable; link to evidence rather than dumping thousands of lines.

## Codex resume protocol

First: `git status`; `git branch --show-current`; `git rev-parse HEAD`; verify canonical online HEAD. If aligned, no full rediscovery. If drifted, audit only drift. Then execute `TICKET -> IMPLEMENT -> UNIT -> INTEGRATION -> ISOLATED RUNTIME -> API CONTRACT -> FRONTEND CONSUMER -> CRITICAL E2E -> EVIDENCE -> REGRESSION -> COMMIT -> NEXT`.

## Forbidden

No fake PASS/runtime/E2E/data/200; no silent protected-DB access; no deleting real history or failing tests; no changing tests to fit wrong implementation; no deleting legacy capability by filename/import count; no Production Ready without six gates; no RC without rollback proof; no force push; no overwriting user learning/history material or valid source.

## Completion definition

Doubao is PRE_CODEX_READY only when Codex can begin the first dependency-valid ticket immediately without redoing repository discovery. Product completion still requires Codex implementation and all six Production Acceptance gates.