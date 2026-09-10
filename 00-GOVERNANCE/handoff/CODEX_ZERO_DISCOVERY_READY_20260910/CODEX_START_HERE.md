# CODEX_START_HERE — LUMENIS / 序境 Pre-Codex 交接入口
> 2026-09-10 12:51:54。本文件是第一入口,详细证据见同目录 CODEX_*.json。原则:对照本包核对基线,匹配则**禁止重新全仓发现**,直接从 FIRST_TICKET 开工。

## WHERE WE ARE
- Canonical: **LUMENIS-codex-Clean-OS@main**, 线上 **ab67612**；本次已通过 GitHub compare 核实 fc75d87→ab67612：ahead 5，但最终文件差异仅新增 2 份 handoff Markdown，**产品源码无增量漂移**；GIT-001 已由线上核验关闭。
- 活动实现仓: D:\LUMENIS_REBUILD\Z-Brand-Core @ `2a3be0ab2e` 分支 integration/p0d-capability-recovery-v1, **1M(app_evidence.py)+3??, 0 staged**。
- 全量测试(隔离): **4133 项 / 60 failed / 0 error / 9 skipped / 381s**,受保护库 data/monitor.db 跑前后 hash 不变(隔离成立)。
- 生产状态: **NOT_READY**。

## WHAT IS ALREADY VERIFIED(可直接REUSE,勿重扫)
- 五仓角色与关系(CODEX_FIVE_REPO_RELATIONSHIP_MAP):唯一 Production Truth Owner=Clean-OS;ZBC=同源工作实现+legacy源;OSAI=智能层(契约边界);Command=研发sidecar(不入runtime);GGI=独立研究(POST_CLOSURE)。
- 根模块: ZBC 223 vs canonical fc75 221,共同221,ZBC仅多 database_isolation.py/runtime_identity.py;CAPABILITY_REGISTRY 零差异(37能力)。
- 源码事实: DB连接锚点301文件/根级70文件含sqlite3.connect(CODEX_DB_CONNECTION_MAP);路由815/蓝图47/前端引用180;隔离探测 /healthz=200、/lumenis/cth/overview=200。
- P0-D 两份证据 JSON 的 commit==当前 HEAD,直接复用。

## WHAT IS NOT VERIFIED / BROKEN
- ~~线上 fc75→ab67612 增量 UNKNOWN~~ → **RESOLVED ONLINE**：仅 handoff 文档变化，无产品源码漂移。
- /api/runtime/identity = **404**(模块在但未注册,RUNTIME-REG-1);/lumenis/bmp/overview = **404**(ROUTE-BMP-1)。
- 60 失败分类: 迁移bootstrap16 / 测试硬连真库8 / 外部cookie12 / 缺模块6 / 缺依赖5(dotenv,tenacity) / AI契约3 / 401认证3 / 在线适配2 / 真实缺陷2 / 旧契约1 / 数据fixture1 / UNKNOWN1。
- Evidence/Canonical/Metric 三处 owner=MULTIPLE(OWNER-*);CAP-REL-001 未实现。

## FIRST TICKET = GIT-002
## FIRST 10 TICKETS(严格顺序)
- **GIT-002** 保护在途成果并建立 integration/handoff 远程分支；先保存 app_evidence.py + audit/p0d + 两个 P0-D 脚本 [P0/P0-REQUIRED-FOR-CLOSURE/READY_FOR_CODEX] deps=[]
- **RUNTIME-ENTRY-1** 收口唯一生产启动入口：scripts/start_production.ps1 当前硬编码 D:\Taikoo-monitor-new，真实生产端口=8201；run_production.py 为 LEGACY，禁止再作为 canonical launcher [P0/P0-BLOCKING/READY_FOR_CODEX] deps=['GIT-002']
- **DB-002** 修复裸相对'data/monitor.db'的cwd漂移(data_center_api/trend_api) [P0/P0-BLOCKING/READY_FOR_CODEX] deps=['GIT-002']
- **DB-001** 收口10个绝对硬编码 data/monitor.db 旁路到canonical resolver [P0/P0-BLOCKING/READY_FOR_CODEX] deps=['GIT-002']
- **P0C-CGE-1** CGE根证据 parent_evidence_id 空串''改NULL(新写入根因) [P0/P0-BLOCKING/READY_FOR_CODEX] deps=['GIT-002']
- **TST-002** 8项测试自身硬连受保护库被护栏拦截→改走临时库(P0C-I) [P0/P0-BLOCKING/READY_FOR_CODEX] deps=[]
- **P0C-MIG-1** Migration原子性:故障注入回滚/源库不变/Backup WAL/版本跃迁 测试补齐 [P0/P0-REQUIRED-FOR-CLOSURE/READY_FOR_CODEX] deps=['GIT-002']
- **P0C-BOOT-1** Clean Bootstrap 三独立Gate:MigrationOnly/ApplicationReadable/RuntimeVerified [P0/P0-BLOCKING/READY_FOR_CODEX] deps=['P0C-MIG-1']
- **TST-001** 16项schema/table失败:测试临时库未bootstrap到v12(或旧平台契约) [P0/P0-BLOCKING/READY_FOR_CODEX] deps=['P0C-BOOT-1']
- **RUNTIME-REG-1** 注册 /api/runtime/identity 路由(当前404,模块已存在) [P0/P0-BLOCKING/READY_FOR_CODEX] deps=['DB-001']

## ONLINE VERIFICATION PATCH (2026-09-10)
- GIT-001 已在 GitHub 线上核验关闭：`fc75d879..ab676123` ahead 5，最终文件差异仅 `00-GOVERNANCE/handoff/LUMENIS_Doubao_PreProduction_Audit_to_Codex_Handoff.md` 与 `LUMENIS_P0-D_Codex_Closure_Handoff.md`，无产品源码变化。
- 官方生产入口已由线上源码确认：`scripts/start_production.ps1` → `run_supervised.py --port 8201`；`run_production.py` 顶部明确标记 LEGACY，默认 8200 仅历史兼容。
- 新增 P0 `RUNTIME-ENTRY-1`：去除 launcher 对旧目录 `D:\Taikoo-monitor-new` 的硬绑定，改为仓库根/受控配置解析，并验证 clean clone 可启动。
- `ROUTE-MAP-1` 仍是**定向证据编译票**而不是重新全仓发现；GIT-002 必须先把 `audit/p0d` 与两个证据脚本安全入远程 integration 分支，避免 Codex 重建证据。

## SERIAL BLOCKERS(不可并行的硬顺序)
- DB-001/DB-002(硬编码/相对路径不收口,隔离与owner判断不可信)
- P0C-CGE-1(CGE根证据写NULL是FK与Evidence owner前提)
- P0C-MIG-1→P0C-BOOT-1→P0C-3DB-1(迁移原子性→干净boot gate→三库验证严格串行)
- P0C-BOOT-1→TST-001(无v12 bootstrap fixture,16项schema失败无法判定)
- RUNTIME-REG-1→ROUTE-BMP-1→RUNTIME-GATE-1(身份→BMP→运行时Gate)
- DB-004→OWNER-EVID-1(证据库别名裁决先于Evidence owner收口)

## SAFE PARALLEL GROUPS
- DB-resolver(after ['GIT-002']): DB-001, DB-002
- test-signal(after []): TST-002, TST-002b, TST-003
- P0C-chain(after ['GIT-002']): P0C-CGE-1, P0C-MIG-1, P0C-ALEMBIC-1
- offline-contract(after []): TST-004, TST-006, TST-007, TST-010, TST-011, TST-012
- owner(after ['DB-001', 'DB-004']): OWNER-CANON-1, OWNER-METRIC-1

## WHAT NOT TO TOUCH
- 真库 data/monitor.db 与 historical/production-candidate:只读/隔离副本;**禁止删数据降FK数**;ai_task 4孤儿 trace 前禁删。
- 失败测试只改不删;不得为绿灯删测试/改实现迎合。
- README/AGENTS/00-GOVERNANCE 本轮不改;canonical main 禁直接 push、禁 force。
- D:\Taikoo-monitor-new 跨仓:test_evidence_export 不得向其写 snapshot(TST-002b)。
- 不读取/不打印任何 API key。

## HOW TO RUN
- 测试(自动隔离): `python -m pytest tests -m "not online" -q`
- 隔离运行时: 设 `ZBC_DB_PATH` 到临时库后，使用 `.venv\Scripts\python.exe run_supervised.py --host 127.0.0.1 --port 8201`；完整生产 launcher 仅在 RUNTIME-ENTRY-1 修复旧绝对 Root 后执行 `scripts\start_production.ps1`
- 路由/探测复现: `python scripts/verify_p0d_runtime_surface.py`

## HOW TO PROVE PASS(六 Gate,PARTIAL/UNKNOWN/文档/route存在/pytest部分过 都不算过)
1. P0=0  2. Repository Integrity  3. Production Truth(唯一owner)  4. Runtime+Critical E2E  5. Security+Recovery  6. Release Lineage+Rollback

## HOW TO COMMIT
- 每个 Ticket 单 purpose、可测试、可回滚、证据关联;先在 integration 分支提交并备份远程(GIT-002),**不推 main、不 force**。

## WHEN PRODUCTION IS ALLOWED
- 六 Gate 全 PASS + Rollback 演练通过后才允许 RC;RC 后最终复审通过才允许宣布 Production。在此之前一律 NOT_READY。

## 接手协议
先 `git status` / `git branch --show-current` / `git rev-parse HEAD` 与本包 WORK_HEAD 比对:匹配→直接 FIRST_TICKET,禁止重新全仓发现;漂移→只审计漂移部分。