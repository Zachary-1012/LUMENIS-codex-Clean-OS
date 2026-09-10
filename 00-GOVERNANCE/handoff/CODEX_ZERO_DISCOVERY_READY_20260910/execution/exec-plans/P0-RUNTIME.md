# ExecPlan P0-RUNTIME
generated 2026-09-10 21:00:25

## Goal
运行时身份注册/BMP路由/契约/运行时Gate

## Tickets(引用已有ticket,不重新设计)
- TST-005 [P1/P0-REQUIRED-FOR-CLOSURE] ic_contracts 三API 401→测试认证/鉴权契约 — deps ['TST-001']
- TST-006 [P1/P1-NONBLOCKING] AI离线默认provider契约×3(glm别名/provider chain/central gateway) — deps []
- RUNTIME-REG-1 [P0/P0-BLOCKING] 注册 /api/runtime/identity 路由(当前404,模块已存在) — deps ['DB-001']
- ROUTE-BMP-1 [P0/P0-BLOCKING] 修复 /lumenis/bmp/overview 404(对照CTH 200) — deps ['RUNTIME-REG-1', 'DB-001']
- ROUTE-MAP-1 [P1/P0-REQUIRED-FOR-CLOSURE] 叠url_prefix重算真实orphan/duplicate路由(推翻朴素277假阳性) — deps ['RUNTIME-REG-1']
- RUNTIME-GATE-1 [P0/P0-REQUIRED-FOR-CLOSURE] Runtime/E2E六Gate之Gate4:启动+核心API+Critical E2E — deps ['P0C-BOOT-1', 'RUNTIME-REG-1', 'ROUTE-BMP-1', 'TST-001']

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