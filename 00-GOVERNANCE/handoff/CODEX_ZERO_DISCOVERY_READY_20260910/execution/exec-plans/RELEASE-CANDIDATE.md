# ExecPlan RELEASE-CANDIDATE
generated 2026-09-10 21:00:25

## Goal
安全恢复/Release lineage/六Gate/RC

## Tickets(引用已有ticket,不重新设计)
- GIT-001 [P0/P0-BLOCKING] 拉取并审计 canonical main fc75→ab67612 增量(本会话git对象写被禁) — deps []
- GIT-002 [P0/P0-REQUIRED-FOR-CLOSURE] 保护在途成果并建立integration/handoff远程分支(本会话push被禁) — deps ['GIT-001']
- CAP-REL-1 [P1/POST-CLOSURE] 实现Release Lineage/Rollback(CAP-REL-001当前NOT IMPLEMENTED) — deps ['P0C-MIG-1', 'GIT-002']
- SEC-001 [P1/POST-CLOSURE] 补验Browser权限/PII/日志脱敏UNKNOWN项 — deps []

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