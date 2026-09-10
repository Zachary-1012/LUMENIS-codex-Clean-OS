# ExecPlan P0-PRODUCTION-TRUTH
generated 2026-09-10 21:00:25

## Goal
Evidence/Canonical/Metric唯一owner收口,消除MULTIPLE

## Tickets(引用已有ticket,不重新设计)
- DB-004 [P0/P0-BLOCKING] 裁决 evidence_chain 的 ZBC_EVIDENCE_DB_PATH 别名(主库 or 独立库) — deps ['GIT-001']
- OWNER-EVID-1 [P0/P0-BLOCKING] 收口Evidence多写者 owner conflict(CAP-DATA-001) — deps ['DB-004', 'P0C-CGE-1']
- OWNER-CANON-1 [P0/P0-REQUIRED-FOR-CLOSURE] 收口Canonical Data owner(CAP-DATA-002) — deps ['DB-001']
- OWNER-METRIC-1 [P1/P0-REQUIRED-FOR-CLOSURE] 收口Metric owner(CAP-DATA-003) — deps ['OWNER-CANON-1']

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