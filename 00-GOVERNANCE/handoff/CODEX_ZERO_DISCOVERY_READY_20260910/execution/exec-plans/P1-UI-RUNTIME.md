# ExecPlan P1-UI-RUNTIME
generated 2026-09-10 21:00:25

## Goal
Subject前置映射落地与UI运行时打通(不重设计)

## Tickets(引用已有ticket,不重新设计)
- SUBJ-001 [P1/POST-CLOSURE] 按Subject Context实施地图研发Selected Subject(DB/Runtime主链后) — deps ['ROUTE-BMP-1', 'OWNER-EVID-1']
- UI-001 [P2/POST-CLOSURE] 按UI实施地图补逐页responsive/state(遵循LUMENIS Design System) — deps ['RUNTIME-GATE-1']

## Execution order
按 CODEX_DEPENDENCY_DAG / CODEX_PARALLEL_EXECUTION_MAP;写同模块禁止并行。
## Parallel groups
见 PARALLEL_SAFE。
## Acceptance gates
本Plan票全CLOSED且对应GATE通过(PARTIAL/UNKNOWN不算)。
## Rollback
单purpose commit逐个revert;回滚点见RESUME_STATE。
## Stop conditions
缺源/owner不明/DB writer不明/需凭证/需外部/需生产变更/需批准→BLOCKED不补假设。
## Evidence
每票evidence_output+FAILURE_FINGERPRINT比对+受保护资产零改动。