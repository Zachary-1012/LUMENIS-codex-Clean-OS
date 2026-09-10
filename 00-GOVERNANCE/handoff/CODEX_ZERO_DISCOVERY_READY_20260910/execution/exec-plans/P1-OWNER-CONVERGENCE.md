# ExecPlan P1-OWNER-CONVERGENCE
generated 2026-09-10 21:00:25

## Goal
能力登记MULTIPLE裁决与剩余测试信号收敛

## Tickets(引用已有ticket,不重新设计)
- TST-002b [P1/P0-REQUIRED-FOR-CLOSURE] test_evidence_export 向 D:\Taikoo-monitor-new 写staging snapshot的外部写隔离 — deps []
- TST-003 [P1/P1-NONBLOCKING] 补齐缺失pip依赖(python-dotenv/tenacity等),不盲目升级 — deps []
- TST-004 [P1/P0-REQUIRED-FOR-CLOSURE] ad_intelligence.models 模块缺失×6 — deps []
- TST-005 [P1/P0-REQUIRED-FOR-CLOSURE] ic_contracts 三API 401→测试认证/鉴权契约 — deps ['TST-001']
- TST-006 [P1/P1-NONBLOCKING] AI离线默认provider契约×3(glm别名/provider chain/central gateway) — deps []
- TST-007 [P1/P1-NONBLOCKING] canonical_matches_live_sql 改为合成fixture(禁依赖生产数据) — deps ['TST-001']
- TST-009 [P1/P1-NONBLOCKING] 去硬编码守卫发现1处生产硬编码路径→定位并收口 — deps ['DB-006']
- TST-010 [P1/P1-NONBLOCKING] repository_registry 旧契约测试与隔离方向冲突对齐 — deps ['DB-003']
- CAP-REL-1 [P1/POST-CLOSURE] 实现Release Lineage/Rollback(CAP-REL-001当前NOT IMPLEMENTED) — deps ['P0C-MIG-1', 'GIT-002']

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