# 序境全产品收口 - 共享进度看板

> 每10分钟由各Team更新，主Agent读取汇总。只报真实已验证事实，禁止"预计""应该"。

## 全局状态
- 分支：feat/lumenis-v2-domain-convergence
- 基线：ZBC d7236f2 / OSAI 168bcc5
- 更新时间：2026-09-06

## Team进度

| Team | 领域 | 负责人 | 修改文件数 | Commit SHA | 硬编码清除 | 测试结果 | 状态 | 阻塞 |
|------|------|--------|-----------|------------|-----------|---------|------|------|
| T1 | 产品/域/主体+Registry | ShardD | 0 | - | - | - | 运行中 | - |
| T2 | 采集+Source+Raw | Team2 | 4 | 8bba987/2885405 | 0 | 161 PASS/0 FAIL | 运行中 | - |
| T3 | Subject Filter+Dedup+Quality | Team3 | 2 | 85f7138 | 负责文件0剩余 | 主体红线24+双维度10+KOS15+质量门10+事件3=62 PASS | 运行中 | - |
| T4 | Canonical+Schema Registry | Team4 | 5 | 550d644 | 0剩余 | 21 passed | Raw→Canonical已打通,13条记录同步,时间分离0违规 | 无 |
| T5 | Event+Case+Risk+Alert | ShardA | 2 | 0c4b4f5,00bb65e | 生产0剩余 | 58 passed | 核心链路已打通 | 无verified输入致events空(非bug) |
| T6 | Metric+Dashboard+KOS/KOL/KOC+Search | Team6 | 1 | 8bba987 | 生产0剩余 | metric 6/6, KOS 47pass1skip, professional 12/12, 综合42PASS | 已完成验证+修复 | 无 |
| T7 | Report+Import/Export+Campaign | (待创建) | 0 | - | - | - | 待启动 | - |
| T8 | AI Gateway+Skill | ShardB | 7 | f228dd7(ZBC),0a6cbd1(OSAI) | 生产0剩余 | AI OFF 17/17, glm-5.3真实调用通过, Skill链SUCCESS+evidence+trace, OSAI P0 18/18 | Action Firewall接入skill_invocation, Provider Matrix完成, 无隐藏fallback | 无 |
| T9 | Agent+Orchestrator+Identity | ShardB | 7(含T8) | f228dd7(ZBC) | 生产0剩余 | Agent组合测试17/17, Identity/Delegation/OBO/JIT全通过, Agent≠User≠Task分离验证, OSAI 52模块调用图11/12 | AgentRuntimeAdapter(subprocess桥接,fail-close)已接入, 无Runtime硬耦合 | 无 |
| T10 | Evidence+Trace+Runtime+CI/CD | (待创建) | 0 | - | - | - | 待启动 | - |
| UI | 前端个性化+Security | ShardC | 10 | baa169f,557e96e | - | 20页面200OK,9项安全header验证通过,35API端点真实绑定,0UI_ONLY | 运行中 | 无 |

## 关键指标
- Feature Registry行数：0
- 硬编码路径剩余：0（生产模块）
- DB空表处置：Event/Case/Alert链路已验证
- AI OFF测试：17/17 PASSED（Team8 ShardB）
- 前端页面验收：20/20（19 LUMENIS页面 + 1 healthz，全部200 OK）
- UI_ONLY页面：0（全部已绑定真实API）
- Design Token：static/css/lumenis-tokens-v2.css（16类Language）
- 核心组件库：static/css/lumenis-core-components.css（10类可复用组件）
- API端点：35个（前端实际调用，全部200 OK）
- Security：9/9通过（CSP/X-Frame-Options/X-Content-Type-Options/Referrer-Policy/Permissions-Policy/X-XSS-Protection/COOP/CORP）

## 阻塞项汇总
（各Team遇到阻塞在此追加）

---

## 2026-09-13 Experience → Production 接线进度（追加，不改写上方历史看板）

- 分支：`codex/production-experience-wiring`；HEAD：`0efd15e`；相对 `origin/main@49c325f` 0 behind / 11 ahead（未 push，push 受当前 github.com:443 不可达阻塞，代理开启后可推）。
- 已完成：Experience V2 蓝图 → Flask 可运行接线；**38/44 屏真实只读绑定**（AI-01/CTH-01 样板 + 36 builder）；Binding 42 BOUND/3 N/A/9 blocked-rows；Action 66/66；本切片 28 测试全过；隔离真实 HTTP 集成 + 深色/浅色 1440/真 390 CDP 遍历全绿。
- 诚实缺口：4 屏 BLOCKED（BMP-05/BMP-11/SH-01/SYS-06）、2 屏 N/A（ACC-01/04）；`PRODUCTION_READY = NO`。
- 新发现工程债：DB 隔离三环境变量不统一（`ZBC_DB_PATH` / `ZBC_EVIDENCE_DB_PATH` / `ZBC_RUNTIME_GUARDIAN_DB`），列为 P0-DBISO-01。
- 剩余分类工作与 DAG：`00-GOVERNANCE/handoff/CODEX_REMAINING_WORK_20260913.md`、`CODEX_RESUME_PACK_20260913.json`；逐项 Gate 证据：`FINAL_CODEX_EXECUTION_REPORT.md`。
- 下一动作（Codex）：P0-DBISO-01 → P0-WRITEPERM-02 → P0-E2E-03 → P0-BLOCKEDSCREEN-04 → P1-LEGACYTEST-05。
