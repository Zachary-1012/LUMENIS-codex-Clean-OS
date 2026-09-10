# 序境 / LUMENIS

## P0-D → 产品闭环前 Codex 接手执行方案

版本：2026-09-10｜用途：Codex 额度恢复后直接续接执行

原则：以当前源码、API、数据库、页面、测试、Runtime 与 Evidence 为事实来源；不凭历史记忆宣布完成。

# 1. 当前结论

可以直接续接，但不能把当前状态误判为已闭环。 线上 canonical Production Core 已确认仍处于 Production Convergence；本地 Codex 已进入 P0-D 的 Runtime / 数据隔离真实性核验，并在额度中断前发现一个明确 P0：app_evidence.py 启动路径绕过 ZBC_DB_PATH，直接连接仓库数据库。

当前正确动作：先把 P0-D 一次性做成闭环，不拆成“修了一个文件但 Runtime Gate 还没过”的半成品。

OpenCode 配置保留；智谱只做一次有效性探测，失败则记录真实阻断，不循环消耗；Ollama 只在事实清单完成后用于材料精简审查。

主执行仍由 Codex 基于真实源码、数据库、API、前端消费、测试与隔离 Runtime 完成。

Subject Context、CTH/BMP 大范围功能收敛等后续任务，不应插入当前 P0-D Runtime/DB 隔离闭环。

# 2. 已确认事实：线上仓库 vs 本地 Codex 状态

| 层级 | 已确认内容 | 证据性质 |
| --- | --- | --- |
| 线上 canonical repo | Zachary-1012/LUMENIS-codex-Clean-OS；main 最新已核到 fc75d879…，提交信息为 governance: unify subject context across CTH and BMP。 | GitHub 当前线上证据 |
| 线上执行阶段 | README 明确 CURRENT PHASE: PRODUCTION CONVERGENCE；顺序为 Capability Closure → Runtime Verification → Production Acceptance → RC → Production / Operating。 | GitHub README 当前证据 |
| 线上 Gate | P0 Blocking=0；Repository Integrity；Production Truth；Runtime+Critical E2E；Security+Recovery；Release Lineage+Rollback。任一未过不得称 Production Ready。 | GitHub README/Acceptance Checklist 当前证据 |
| 线上 Capability Registry | 多个关键能力仍标记 MULTIPLE / PARTIAL / UNKNOWN / NO_RUN；CAP-DB-002 Migration 仍为 MULTIPLE/bootstrap blocked；CAP-RUN-001 Runtime Guardian 为 MULTIPLE/UNKNOWN；Release Lineage 未实现。 | GitHub Capability Registry 当前证据 |
| 本地 Codex P0-D | 用户回传：已生成源码事实索引；3800 Git files、983 Python、100 frontend files、11199 functions、1464 classes、843 backend route declarations、180 frontend API refs、456 table refs；Python parse errors=0。 | 用户提供的本地 Codex 实时回传，未由本文件独立复跑 |
| 本地 Runtime | 用户回传：8202 Runtime 当时未运行，四个探测地址拒绝连接；随后首次隔离 Runtime 被 app_evidence.py 直接连接仓库 DB 的门禁阻断。 | 用户提供的本地 Codex 实时回传，需额度恢复后复核 |

# 3. P0-D 本轮必须一次性闭环的范围

P0-D 在当前上下文中应按“真实运行时 + 数据隔离 + 入口可达性 + 页面/API真实性”收口，而不是单纯修一个连接路径。完成必须覆盖：

所有启动阶段数据库连接都服从隔离 Runtime 的数据库路径/连接策略；不得在 import/startup 时静默触碰仓库或生产候选数据库。

启动隔离 Runtime 成功，明确真实 process/host/port/DB identity，并能重复启动/停止而不污染受保护库。

真实路由注册表可导出并与源码静态索引交叉核对：已注册、未注册、重复、冲突、UNREACHED 分开处理。

关键 API 能返回真实状态；禁止 fake 200、静态假完成、UI 与 API 状态漂移。

前端实际消费的 API 与后端已注册 route 对齐；孤儿 API、孤儿 UI、旧 endpoint 只做证据分类，不凭文件名删除。

测试使用临时/隔离数据库；任何测试不得触碰生产库、仓库基线库或历史证据库。

Runtime Gate 之后再跑分层测试与 Critical E2E；失败继续定位到明确 source/symbol/route/table，而不是泛化“测试不稳定”。

所有 PASS 必须有 Evidence；不能用“代码存在”“文档说完成”“页面能打开”代替 VERIFIED。

# 4. Codex 恢复额度后的严格执行顺序

P0D-01 基线冻结：先读取当前 branch / HEAD / git status / diff；确认额度中断后的工作树是否发生变化。若变化，只重审变化范围。

P0D-02 DB 连接面全扫：以 app_evidence.py 为首个已知根因，静态+调用链枚举 startup/import/runtime 中所有 sqlite3.connect、database.get_conn、路径常量、环境变量解析。分类：SAFE / HARD-CODED / IMPORT-TIME / UNKNOWN。

P0D-03 修复连接策略：所有运行时模块统一通过当前 canonical DB resolver / isolation contract；禁止模块自行解析默认仓库数据库。修改要最小化，不顺手做架构重写。

P0D-04 Import/Startup Gate：在受保护 DB 拒绝连接的前提下 import app、注册 blueprint、构建 app。任何触碰受保护库都立即 FAIL，并定位模块。

P0D-05 隔离 Runtime 启动：临时数据库 + offline network + protected DB deny；启动 8202 或当前实际 P0-D 指定端口。记录 PID、DB path、route count、health state、startup logs。

P0D-06 Route Truth：从真实 app.url_map/等价运行时注册源导出 route registry，与静态 843 route declarations 交叉核对，区分 declaration≠registration。

P0D-07 API→DB→Consumer：从当前真实前端 API refs 出发，抽样/覆盖 P0 critical flows，建立 Frontend consumer → Route → Service → DB table → Response contract 链。

P0D-08 测试隔离：先跑 DB isolation/migration/runtime 相关测试，再跑受控回归。所有测试前后比较受保护 DB hash/mtime/foreign_key_check 或等价证据。

P0D-09 Critical E2E：只对已通过 API/DB Gate 的关键流程执行页面 E2E；PC/Tablet/Mobile 至少验证关键主链状态来自真实 API。

P0D-10 Evidence 收口：生成 P0-D evidence manifest：source diff、DB identity、runtime probe、route registry、test results、E2E、protected DB unchanged、known blocked。

P0D-11 Re-audit：重新扫描 P0-D 改动范围，确认没有新 hard-coded DB path、无跨库写入、无 orphan runtime dependency。

P0D-12 Commit/Push：只有 Gate 全过才按单一 P0-D 主题提交；不得把 Subject Context/UI 大改混入同一 commit。

# 5. P0-D 完成 Gate（全部满足才算 CLOSED）

| Gate | 必须证明 | 失败即 | 状态规则 |
| --- | --- | --- | --- |
| DB Isolation | 启动/import/test/runtime 均不触碰受保护库；DB identity 明确 | P0 BLOCKED | 无证据不得 PASS |
| Runtime Startup | 隔离 Runtime 可重复成功启动并正常关闭 | P0 BLOCKED | 连接拒绝/崩溃必须保留根因 |
| Route Registration | 关键 routes 在真实 runtime 已注册，无关键 blueprint 丢失 | P0/P1 依关键性 | 静态 declaration 不等于 runtime verified |
| API Truth | 关键 API 真实访问 service/DB，错误态真实，不 fake 200 | P0 BLOCKED | UI 不得覆盖真实失败 |
| Test Isolation | 测试只用临时/测试 DB，受保护 DB 前后不变 | P0 BLOCKED | 污染即停止全量测试 |
| Critical E2E | 关键用户链条 UI→API→DB/Evidence 可达 | P0/P1 | 页面可打开不等于 E2E PASS |
| Evidence | 每项有 source/runtime/test/DB/e2e 证据 | P0-D 不得关闭 | UNKNOWN 继续保留 |
| Git Closure | diff 单一主题、可回滚、无无关改动 | 不得合并 | 不 force push |

# 6. 当前明确禁止插入的工作

不要在 P0-D 中顺手做 Unified Subject Context 全面研发。

不要因为旧 Registry 冲突就直接删除/合并模块；先用 runtime reachability + producer/consumer + DB read/write + tests 判定。

不要恢复旧 UI；Legacy code 只能作为能力证据源，最终 UI 必须遵循当前 LUMENIS IA/Design System。

不要全量启用云 AI 反复重试。智谱只探测一次；失败记录 provider/resource/package 的真实阻断。

不要让 Ollama 在事实索引完成前参与“猜测式架构判断”；只用于后置材料精简/审查。

不要用 README/Registry 状态覆盖 Runtime 真实结果。线上文档当前本身也存在状态口径不完全一致，应以证据晋级。

# 7. P0-D 之后到产品闭环前的顺序

P0-D Runtime/DB Isolation CLOSED
→ P0-C/DB-Migration-FK residual re-check
→ Production Truth / Evidence / Canonical ownership closure
→ Security / Permission / Recovery
→ Unified Subject Context
→ CTH/BMP capability closure
→ Report / Export / Event / Case / Risk / Metrics
→ AI / Agent production boundary
→ Frontend/API/ViewModel + Responsive + Critical E2E
→ Production Acceptance 6 Gates
→ Release Lineage + Rollback
→ RC
→ Production / Operating

注意：线上当前 Capability Registry 仍显示若干 MULTIPLE/PARTIAL/UNKNOWN/NO_RUN，因此 P0-D 关闭后仍不能直接宣布产品闭环；必须继续逐 Gate 晋级。

# 8. 可直接粘贴给 Codex 的续接指令

CONTINUE P0-D TO FULL CLOSURE. DO NOT LEAVE A HALF-FINISHED STATE.

FACT BASELINE:
- Re-read current local branch, HEAD, git status and diff first.
- Preserve all valid work already completed before quota interruption.
- Known current blocker from the interrupted run: app_evidence.py bypassed ZBC_DB_PATH and connected directly to the repository database during startup. Re-verify the current source before acting.
- The previous static source index is evidence, not completion: declarations must be verified against the real isolated runtime.

EXECUTION POLICY:
1. Finish P0-D as one closure unit: DB isolation -> import/startup gate -> isolated runtime -> real route registry -> API/DB/frontend reachability -> isolated tests -> critical E2E -> evidence -> re-audit -> focused commit.
2. Do not touch protected/production/reference databases. Use temporary isolated DB only. Fail closed if any module attempts a protected DB connection.
3. Enumerate all database connection paths reachable during import/startup/runtime. Fix every confirmed hard-coded or isolation-bypassing path needed for P0-D; do not perform unrelated rewrites.
4. Runtime truth overrides old Registry/docs. Static route declaration != registered route. File existence != reachable capability.
5. Classify uncertain assets UNKNOWN/UNREACHED; do not delete by filename/import count.
6. OpenCode configuration remains preserved. Probe Zhipu exactly once. If unavailable, record the real blocker and stop retrying. Do not burn quota.
7. Keep Ollama locally callable, but use it only after the factual inventory/evidence set is complete, for review/condensation; it must not replace source/runtime verification.
8. Do not start Unified Subject Context or broad UI redesign inside this P0-D closure.
9. Every PASS requires evidence: source/call graph + DB identity/check + runtime result + tests + E2E where applicable.
10. Before commit, re-audit changed scope, prove protected DB unchanged, prove runtime can start/stop repeatedly, and prove critical routes/API flows are real.

P0-D CLOSED ONLY IF:
- no protected DB access from import/startup/test/runtime;
- isolated runtime starts and stops successfully;
- critical blueprints/routes are runtime-registered;
- critical API -> service -> DB -> frontend consumer chains are verified;
- tests use isolated DB and protected DB remains unchanged;
- critical E2E passes for the selected production-critical flows;
- evidence manifest exists for all above;
- remaining UNKNOWN/BLOCKED items are explicitly listed;
- git diff is focused and rollback-safe.

If any gate fails, continue fixing within P0-D until either CLOSED or a real external blocker is proven. Do not report completion early.

# 9. Codex 最终回传格式

P0-D STATUS = CLOSED / BLOCKED
BRANCH =
HEAD =
FILES CHANGED =
ROOT CAUSES FIXED =
PROTECTED DB UNCHANGED = YES / NO / UNKNOWN
ISOLATED RUNTIME = PASS / FAIL
RUNTIME DB PATH =
REGISTERED ROUTES =
CRITICAL API CHAINS = PASS / FAIL
TEST ISOLATION = PASS / FAIL
TEST RESULTS =
CRITICAL E2E = PASS / FAIL / NOT RUN
ZHIPU PROBE = AVAILABLE / BLOCKED / NOT REQUIRED
OLLAMA = CALLABLE / BLOCKED / NOT USED
EVIDENCE MANIFEST =
REMAINING P0 =
REMAINING P1 =
COMMIT =
PUSH =
NEXT SAFE WORKSTREAM =

# 10. 证据边界说明

本文件将两类事实严格分开：
1) 线上仓库事实：来自本次对 Zachary-1012/LUMENIS-codex-Clean-OS 当前 GitHub main 的重新读取，包括 README、Production Acceptance Checklist、Capability Registry 与最新提交链。
2) 本地执行事实：来自用户粘贴的 Codex 当前实时回传。由于本助手无法直接看到用户 Windows 工作树，本地 branch/HEAD/diff/Runtime 状态必须由 Codex 恢复后重新读取确认。