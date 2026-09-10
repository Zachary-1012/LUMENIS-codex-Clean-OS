# ExecPlan P0-MIGRATION
generated 2026-09-10 21:00:25

## Goal
迁移原子性/干净boot三Gate/三库验证/FK数据根因

## Tickets(引用已有ticket,不重新设计)
- P0C-CGE-1 [P0/P0-BLOCKING] CGE根证据 parent_evidence_id 空串''改NULL(新写入根因) — deps ['GIT-001']
- P0C-CGE-2 [P0/P0-REQUIRED-FOR-CLOSURE] 存量 parent_evidence_id='' →NULL 修复策略(仅隔离副本先验证) — deps ['P0C-CGE-1', 'P0C-3DB-1']
- P0C-AITASK-1 [P0/P0-REQUIRED-FOR-CLOSURE] ai_task task_id='1' 四孤儿Dependency Trace(禁直接删) — deps ['P0C-3DB-1']
- P0C-MIG-1 [P0/P0-REQUIRED-FOR-CLOSURE] Migration原子性:故障注入回滚/源库不变/Backup WAL/版本跃迁 测试补齐 — deps ['GIT-001']
- P0C-BOOT-1 [P0/P0-BLOCKING] Clean Bootstrap 三独立Gate:MigrationOnly/ApplicationReadable/RuntimeVerified — deps ['P0C-MIG-1']
- P0C-3DB-1 [P0/P0-BLOCKING] 三库(clean/historical/production-candidate)各自迁移验证票 — deps ['P0C-MIG-1']
- P0C-ALEMBIC-1 [P1/P0-REQUIRED-FOR-CLOSURE] 手写migration vs Alembic stamp-only 归属裁决(CAP-DB-002 MULTIPLE) — deps ['P0C-MIG-1']
- TST-001 [P0/P0-BLOCKING] 16项schema/table失败:测试临时库未bootstrap到v12(或旧平台契约) — deps ['P0C-BOOT-1']

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