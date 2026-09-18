# 序境 / LUMENIS

## 豆包只读审计 → Codex 直接接手闭环方案

PRE-PRODUCTION AUDIT & CODEX HANDOFF · 2026-09-10

用途：现在交给豆包执行；豆包完成后，Codex 额度恢复即可按交接包直接继续，不重新做全库发现。

# 1. 先定角色：豆包现在只做什么

豆包 = READ-ONLY Auditor + Evidence Builder + Closure Planner + Codex Handoff Builder。

本轮不写产品代码、不改数据库、不提交、不推送、不启动会写入生产数据的 Runtime；目标是把“闭环前还剩什么、先后顺序、每项如何验收”整理成 Codex 可直接执行的工单。

Codex = 后续唯一主实施者：按豆包交接工单改源码、跑测试、做 Runtime/E2E、留 Evidence、Commit/Push。

OpenCode 配置保留；智谱仅做一次有效性探测，不可用就记录真实阻断，不循环烧额度；Ollama 保持本地可调用，但只在事实清单形成后用于精简/复核材料，不替代源码事实。

# 2. 已核验的线上 Canonical 基线

| 项目 | 线上已核验事实 |
| --- | --- |
| Canonical Production Repo | Zachary-1012/LUMENIS-codex-Clean-OS |
| main 当前核验 HEAD | fc75d87938f3631bec99338c9e059eca34c6a680 |
| 最新提交 | governance: unify subject context across CTH and BMP |
| 当前阶段 | PRODUCTION CONVERGENCE |
| 收敛顺序 | Capability Closure → Runtime Verification → Production Acceptance → Release Candidate → Production / Operating |
| 最终六 Gate | P0=0；Repository Integrity；Production Truth；Runtime+Critical E2E；Security+Recovery；Release Lineage+Rollback |
| 线上治理核心 | README.md + AGENTS.md + 00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md |
| Registry 总结 | OWNERSHIP DEFINED / IMPLEMENTATION RECONCILIATION PARTIAL / PRODUCTION NO-GO |

注意：线上 README 已把 CTH/BMP 都统一为 Selected Subject 语义；Master Checklist 中仍存在较旧的 “CTH Subject-first / BMP Brand-first” 表述，豆包必须标记为 GOVERNANCE_DRIFT，不能拿旧表述覆盖线上 README 的更新定义。

# 3. 用户刚刚回传的本地 Codex 状态（必须与线上事实分开）

Codex 已建立当前源码事实索引：用户回传称覆盖约 3,800 个 Git 文件、983 Python、100 前端文件、11,199 函数、1,464 类、843 后端路由声明、180 个不同前端 API 引用、456 种数据表引用，Python 解析错误降为 0。

用户回传：8202 Runtime 当时未运行，4 个探测地址拒绝连接，因此页面不能宣称 Runtime 已验证。

用户回传：隔离 Runtime 首次启动发现 app_evidence.py 无视 ZBC_DB_PATH，直接连接仓库数据库；Codex 正在改为“调用时解析隔离路径”并准备重复 Runtime Gate 时额度耗尽。

以上属于用户提供的本地现场状态，不等于本次线上仓库已经独立验证；豆包必须在本地只读审计中重新确认现状与差异。

# 4. 豆包本轮必须完成的 8 个成果

### A. 重新锁定当前本地 repo/branch/HEAD/dirty state，并对照线上 Canonical main，记录 BRANCH_DRIFT / SOURCE_DRIFT。

### B. 复核 P0-D 当前断点：app_evidence.py 的 DB 路径行为、所有同类硬编码 DB/路径旁路、ZBC_DB_PATH/隔离 DB contract 是否一致。

### C. 生成“可重跑源码证据清单”：函数/类/Route/DB table/API consumer/Test/Runtime entry/Reachability，并把 UNKNOWN/UNREACHED 单独列出。

### D. 把线上 Capability Registry 中 MULTIPLE / P0 / NO_RUN / UNKNOWN / NOT IMPLEMENTED 项逐一映射到当前源码，不允许按文件名猜完成度。

### E. 建立从 P0-D 到 Production Acceptance 的依赖 DAG，分 P0 Blocking、P0 Required、P1 Before RC、P2 Post-launch。

### F. 把每个剩余项拆成 Codex 可直接执行 Ticket：精确文件/符号/改动范围/禁止区/测试/Runtime/Evidence/验收/回滚。

### G. 生成 Codex Resume Pack：恢复额度后从 FIRST TICKET 开始，不重新全库扫描。

### H. 给出最终 SAFE TO START=YES/NO；只有基线一致且没有工作树冲突时才能 YES。

# 5. 豆包必须重点审计的 P0-D 主线

| 顺序 | 检查项 | 必须得到的证据 | Codex 后续动作 |
| --- | --- | --- | --- |
| 1 | DB Path Isolation | 所有 DB writer/reader 的路径解析来源；任何绕过隔离变量的模块清单 | 逐个修复真实旁路，不大改 |
| 2 | Runtime Gate | 隔离 Runtime 是否能启动；生产/历史 DB 未触碰；health/API 实际响应 | 启动→探测→失败即根因修复→重跑 |
| 3 | Migration/FK Carry-over | P0-C 未闭环项是否仍存在；FK/migration 与 P0-D 是否冲突 | 先完成串行阻塞再继续 |
| 4 | Route Registration | 静态声明 vs 真实注册 Route 的差异 | 修 orphan/duplicate/hidden fallback |
| 5 | Frontend Consumption | 页面 API 引用是否对应真实 Route/Contract | 消除 fake 200 / dead consumer / drift |
| 6 | Runtime Readability | 核心页面/API 在隔离环境读取真实数据的能力 | 真实 Runtime + Critical E2E |
| 7 | Evidence Truth | Evidence/Canonical/Metric 的唯一 owner 与真实 writer/reader | MULTIPLE 必须 KEEP/MERGE/ADAPTER 决策 |
| 8 | Release Gate | 六大 Gate 的实际证据缺口 | 只在证据满足后升级状态 |

# 6. 豆包禁止做的事情

禁止修改源码、数据库、配置、测试、文档、Git 状态。

禁止 git pull/fetch/checkout/switch/reset/clean/stash/merge/rebase/add/commit/push。

禁止运行会写 repo、写生产/历史数据库、改变环境的测试或 Runtime。

禁止把“文件存在 / Route 声明存在 / README 写了”当成 VERIFIED。

禁止把 Legacy UI 恢复成最终 UI；Legacy 只作为能力证据源。

禁止启动 Subject Context 实施；只能规划 Ticket，必须等当前 DB/Runtime P0-D 串行阻塞关闭。

禁止把 Developer Settings 拉回当前阻塞链；它仍是 Post-Launch Upgrade。

禁止为了让报告完整而猜测 UNKNOWN。

# 7. 交给豆包的一次性执行指令

LUMENIS / 序境 — P0-D TO PRE-PRODUCTION CLOSURE READ-ONLY AUDIT

ROLE

You are READ-ONLY AUDITOR + EVIDENCE BUILDER + CODEX HANDOFF PLANNER.

Do not implement code in this round.

CANONICAL ONLINE REPO

Zachary-1012/LUMENIS-codex-Clean-OS

Verified online main baseline before this audit:

fc75d87938f3631bec99338c9e059eca34c6a680

FIRST RULE

Re-verify current local repo / branch / HEAD / dirty state and compare with current online canonical truth.

Do not trust historical chat or old reports when current source differs.

LOCAL P0-D CONTINUATION POINT REPORTED BY USER

- source fact index was generated
- runtime on 8202 was not verified
- isolated runtime exposed app_evidence.py bypassing ZBC_DB_PATH and touching repo DB
- Codex was changing that module to resolve isolated DB path at call time when quota stopped

Treat this as reported local state; verify it locally before using it as evidence.

DO NOW — READ ONLY

## 1. Audit current README.md, AGENTS.md, Production Acceptance checklist, Capability Registry and current local source.

## 2. Reconstruct current DB path contract and find every module that bypasses canonical isolation/path resolution.

## 3. Reconstruct actual runtime entrypoints, registered routes, API consumers, DB readers/writers, tests and critical pages.

## 4. Reuse the existing source index if it still matches HEAD. Do not rescan everything unless drift requires it.

## 5. Mark every item as REACHED / UNREACHED / UNKNOWN. Never infer functionality from filenames.

## 6. Map Capability Registry MULTIPLE/P0/NO_RUN/UNKNOWN/NOT_IMPLEMENTED entries to actual source evidence.

## 7. Separate governance drift from code/runtime blockers.

## 8. Build the dependency DAG from current P0-D through Production Acceptance and RC readiness.

## 9. Do not implement Subject Context now; only schedule its tickets after DB/runtime isolation blockers are closed.

## 10. Keep Developer Settings in POST_LAUNCH_UPGRADE unless current canonical governance explicitly changed.

CONNECTION POLICY

- Preserve OpenCode configuration.
- Probe Zhipu exactly once for actual availability. If unavailable/resource package blocked, record the real blocker and stop retrying.
- Keep Ollama locally callable, but use it only after the factual source inventory is built, for material review/condensation; never let it replace source/API/DB/runtime evidence.

REQUIRED OUTPUT

Create one final artifact in chat titled:

LUMENIS P0-D → PRE-PRODUCTION CODEX HANDOFF BOARD

It must contain:

### A. Current local baseline vs online canonical baseline
### B. Drift table: SOURCE / BRANCH / GOVERNANCE / RUNTIME / DATA / UNKNOWN
### C. P0-D blocker list
### D. DB path/isolation evidence map
### E. Runtime entrypoint + route + API + frontend consumer reachability map
### F. Capability gap matrix
### G. Dependency DAG
### H. Execution waves from P0-D to Production Acceptance
### I. Exact Codex tickets
### J. NO-GO list
### K. Evidence matrix
### L. Git/commit/rollback boundaries
### M. Top 10 Codex First Actions
### N. CODEX RESUME PACK

EVERY CODEX TICKET MUST INCLUDE

Ticket ID
Priority
Status: READY_FOR_CODEX / NEEDS_MORE_EVIDENCE / BLOCKED / POST_CLOSURE
Problem
Verified Evidence
Root Cause
Exact Source Files
Exact Symbols/Routes/Tables
Affected Capability
Dependencies
Change Scope
Exact Intended Fix
Expected Files To Change
Forbidden Files/Areas
Implementation Steps
Required Tests
Runtime Verification
Evidence Required
Acceptance Criteria
Abort Condition
Rollback Condition
Risk
Parallelizable YES/NO
Size XS/S/M/L
Model: SOL / ASTRA_ONLY_IF_BLOCKED

EXECUTION ORDER

Do not invent order. Derive it from dependencies.

Default serial spine:

P0-D DB isolation
→ isolated Runtime start
→ migration/FK compatibility confirmation
→ registered route/API truth
→ frontend consumer truth
→ Evidence/Canonical/Metric ownership closure
→ Security/Permission boundary
→ Subject Context implementation tickets
→ CTH/BMP capability closure
→ Runtime + Critical E2E
→ Recovery/Security
→ Production Acceptance
→ Release Candidate/rollback
→ final re-audit

PASS RULE

Source existence != pass.
Route declaration != pass.
README statement != pass.
A capability may advance only with appropriate SOURCE + CALL GRAPH + DB/API + TEST + RUNTIME + E2E/EVIDENCE.

NO-GO EXAMPLES

- any code can silently touch production/history DB during tests/runtime isolation
- unresolved FK/migration corruption
- runtime cannot start in isolated environment
- critical API/page contract broken
- permission bypass
- cross-subject contamination
- Evidence/Canonical ownership ambiguity
- fake 200/fake data
- rollback/release lineage unknown
- critical work exists only in an unprotected dirty/local branch

FINAL CODEX RESUME PACK MUST BE SHORT

CURRENT_REPO=
CURRENT_BRANCH=
CURRENT_HEAD=
ONLINE_CANONICAL_HEAD=
DIRTY_STATE=
FIRST_TICKET=
FIRST_5_TICKETS=
P0_BLOCKERS=
NO_GO=
SAFE_TO_START=YES/NO
DO_NOT_TOUCH_FIRST=
SUBJECT_CONTEXT_MAY_START_WHEN=
PRODUCTION_ACCEPTANCE_MAY_START_WHEN=
RC_MAY_START_WHEN=

FINAL SAFETY REPORT

WORKTREE_MUTATED=NO
FILES_CREATED=0
FILES_MODIFIED=0
FILES_DELETED=0
DATABASE_MUTATED=NO
GIT_MUTATED=NO
COMMIT=NO
PUSH=NO

If any of these cannot be proven, write UNKNOWN.

CORE OBJECTIVE

When Codex quota returns, Codex must be able to start from FIRST_TICKET and execute:

Ticket → Change → Test → Runtime Verification → Evidence → Commit

without repeating full-repository discovery.

# 8. 豆包完成后，Codex 如何直接接手

第一步只核对三件事：current branch、current HEAD、git status；若与豆包交接包一致，不再重做全库审计。

从 CODEX RESUME PACK 的 FIRST_TICKET 开始，一票一闭环：Change → Test → Runtime Verification → Evidence → Commit。

如果 HEAD/dirty state 已变化，只审计变化范围并重新计算受影响工单，不推倒整个 Master Board。

P0-D 必须完整闭环后再进入 Subject Context 和后续域能力；不能把当前 Runtime/DB 隔离问题留成半成品。

# 9. Codex 接手的最低验收门槛

隔离 Runtime 可启动，且生产/历史数据库有证据证明未被测试/启动流程触碰。

DB path contract 唯一且所有关键 writer/reader 遵守；不存在 app_evidence.py 类旁路。

Migration/FK 当前状态无未处理 P0 阻断。

关键 Route 实际注册并由真实前端/API consumer 使用；无 fake 200/fake data 作为完成证据。

关键页面/接口具有 Runtime + Critical E2E 证据。

Production Truth、Evidence、Canonical、Permission、Recovery、Release Lineage 的责任与证据可追踪。

六大 Production Acceptance Gate 全部 PASS 前不得宣布 Production Ready。

# 10. 本文档依据

GitHub Canonical repo: Zachary-1012/LUMENIS-codex-Clean-OS

main HEAD checked: fc75d87938f3631bec99338c9e059eca34c6a680

README.md: current Production Convergence, canonical four-repo registry, unified Selected Subject context, six-gate rule.

00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md: mandatory audit loop, production acceptance domains/gates, legacy capability recovery rule, Developer Settings post-launch rule.

CAPABILITY_REGISTRY.md: Ownership defined, implementation reconciliation partial, Production NO-GO; multiple P0/MULTIPLE/NO_RUN/UNKNOWN capabilities still require real source/runtime reconciliation.

Local P0-D progress numbers and app_evidence.py issue are user-reported Codex runtime facts and must be locally re-verified by Doubao before promotion to verified evidence.