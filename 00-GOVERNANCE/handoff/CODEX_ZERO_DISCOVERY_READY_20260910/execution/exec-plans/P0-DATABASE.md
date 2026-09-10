# ExecPlan P0-DATABASE
generated 2026-09-10 21:00:25

## Goal
收口DB路径解析与连接策略,ZBC_DB_PATH成为唯一canonical隔离契约

## Tickets(引用已有ticket,不重新设计)
- DB-001 [P0/P0-BLOCKING] 收口10个绝对硬编码 data/monitor.db 旁路到canonical resolver — deps ['GIT-001']
- DB-002 [P0/P0-BLOCKING] 修复裸相对'data/monitor.db'的cwd漂移(data_center_api/trend_api) — deps ['GIT-001']
- DB-003 [P1/P0-REQUIRED-FOR-CLOSURE] repository_registry旁路纳入ZBC_DB_PATH(brand_knowledge_base/case_deep_analysis) — deps ['DB-001']
- DB-004 [P0/P0-BLOCKING] 裁决 evidence_chain 的 ZBC_EVIDENCE_DB_PATH 别名(主库 or 独立库) — deps ['GIT-001']
- DB-005 [P1/P1-NONBLOCKING] 收口DB fallback风险(swire_group/ai_task_engine/evaluation_recorder/app_evidence在途) — deps ['DB-001']
- DB-006 [P1/P1-NONBLOCKING] 逐个审计 app.py 内21处内联sqlite3.connect并归类 — deps ['DB-001']
- DB-007 [P0/P0-REQUIRED-FOR-CLOSURE] 建立Connection Policy Matrix并分阶段开启FK enforcement — deps ['DB-001', 'P0C-CGE-1']
- TST-002 [P0/P0-BLOCKING] 8项测试自身硬连受保护库被护栏拦截→改走临时库(P0C-I) — deps []
- TST-002b [P1/P0-REQUIRED-FOR-CLOSURE] test_evidence_export 向 D:\Taikoo-monitor-new 写staging snapshot的外部写隔离 — deps []

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