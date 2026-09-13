# 序境 / LUMENIS

> **Production Core · Production Truth Owner**
>
> 当前阶段 / Current phase: **PRODUCTION CONVERGENCE**

本仓库承载序境 / LUMENIS 当前生产实现、运行时、数据契约、Evidence、API、Permission、Metric、UI binding、测试与发布证据。`README.md` 是人类工程师入口，不是历史进度日志，也不能单独证明某项功能已经完成。

This repository contains the active production implementation, runtime, data contracts, Evidence, API, Permission, Metric, UI binding, tests and release evidence for 序境 / LUMENIS. `README.md` is the human engineering entrypoint. It is not a historical progress log and does not by itself prove that a capability is complete.

---

## Current Windows takeover / 当前 Windows 接续入口

当前这台 Windows 研发机唯一有效本地工作区：

```text
D:\LUMENIS_REBUILD
```

远端唯一长期研发主线：

```text
Zachary-1012/LUMENIS-codex-Clean-OS
main
```

Codex/工程师在当前机器开始工作时必须先从 `D:\LUMENIS_REBUILD` 验证本地 HEAD、working tree、unpushed commits 与 `origin/main`，保护本地已完成修复并完成 local→main 收敛；不得用 remote tree 覆盖尚未 push 的有效本地实现。

Current takeover details: [`00-GOVERNANCE/handoff/CODEX-CURRENT-BLOCKERS-20260913.md`](00-GOVERNANCE/handoff/CODEX-CURRENT-BLOCKERS-20260913.md)

Production launcher after regression/sync gates:

```powershell
Set-Location D:\LUMENIS_REBUILD
powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
```

Expected core health endpoint:

```text
http://127.0.0.1:8201/healthz
```

This workstation path is not a portable production-code requirement; the launcher resolves the repository root from its own location.

---

## 1. 产品定位 / What LUMENIS is

序境 / LUMENIS 是面向商业运营与品牌市场的生产级产品。AI 是增强能力，不拥有 Production Truth。

LUMENIS is a production product for commerce operations and brand/market work. AI enhances the product but does not own Production Truth.

Canonical production chain / 标准生产链：

```text
External Data
→ Evidence
→ Canonical Data
→ Function
→ Metric
→ Truth Table
→ View Model
→ Visualization
→ UI / Report / Export
```

Canonical business chain / 标准业务链：

```text
Source
→ Evidence
→ Event
→ Case
→ Insight
→ Decision
→ Action
→ Outcome
→ Evaluation
→ Learning Asset
```

内部链路是生产约束，不是为了页面展示而存在的装饰流程。

These chains define production semantics; they are not decorative page flows.

---

## 2. 产品域 / Product domains

### CTH · 商业运营 / Commerce Operations

主体优先（Subject-first），负责主体、场地/项目、事件、案例、风险、决策与行动。

Subject-first domain for subjects, venues/projects, events, cases, risk, decisions and actions.

### BMP · 品牌市场 / Brand & Market

品牌/市场优先，负责品牌、竞品、创作者/账号、Campaign、传播/市场表现、Benchmark、风险与评估。

Brand/market-first domain for brands, competitors, creators/accounts, campaigns, communication/market performance, benchmarks, risk and evaluation.

### Shared Capability · 共享能力

内容与创作、Evidence、Research、Evaluation、Learning Asset、AI Enhancement 等跨域能力。

Cross-domain capabilities including Content & Creation, Evidence, Research, Evaluation, Learning Assets and AI Enhancement.

### SYSTEM · 系统

Collector、Runtime、Scheduler、AI Gateway、Database、Security、Permission、Settings、Recovery、Observability。

Infrastructure and control plane: Collector, Runtime, Scheduler, AI Gateway, Database, Security, Permission, Settings, Recovery and Observability.

CTH 与 BMP 可以共享 Subject Context 与基础设施，但不得静默合并领域模型、指标、关系和行动语义。

CTH and BMP may share Subject Context semantics and infrastructure, but their domain models, metrics, relationships and action semantics must not silently collapse into one model.

---

## 3. 事实权威 / Authority and truth

发生冲突时按以下优先级判断：

When artifacts disagree, use this precedence:

```text
Current Production Source
> Runtime Reality
> Current DB / API / Permission / Evidence Contracts
> Tests / E2E / Production Acceptance
> Current Canonical Governance
> Experience V2 / Current UI Capability Evidence
> Historical Handoff / Legacy Evidence
> Chat History
```

`IMPLEMENTED`、`TESTED`、`VERIFIED`、`RELEASED`、`OPERATING` 是不同状态。文档、提交说明或聊天记录不能自动升级运行状态。

`IMPLEMENTED`, `TESTED`, `VERIFIED`, `RELEASED` and `OPERATING` are different states. Documentation, commit messages and chat history never upgrade runtime state by themselves.

---

## 4. 标准闭环 / Canonical closed loop

Shared Capability × Collector 的正式方向：

Approved Shared Capability × Collector direction:

```text
SYSTEM Collector
→ Source / Evidence
→ Canonical Content
→ Research
→ Learning Asset
→ Content Studio
→ Application Trace
→ Collector Tracking
→ Evaluation
→ Learning Version Update
```

核心约束 / Key invariants:

- Collector 始终由 SYSTEM 唯一拥有；Collector remains a single SYSTEM-owned Runtime capability.
- Upload / Import / API / Collector 只是不同 acquisition adapter，最终进入同一 Production Truth；they converge into one Production Truth.
- `MetricSnapshot` append-only，不覆盖历史观测；historical observations are not overwritten.
- `missing != 0`，未来 T+ 表现不得伪造；future T+ performance must not be fabricated.
- AI 可提出 Pattern candidate，但不得自主执行 `Pattern → ADOPT`; AI may propose but not autonomously adopt.
- 登录态 Collector 只读；未来 Publisher 必须是独立 Permission/Effect capability; logged-in Collector remains read-only.
- `RELEASED != OPERATING`.

详细规范 / Canonical detail: [`00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md`](00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md)

---

## 5. 仓库导航 / Repository orientation

```text
README.md                       人类产品+工程入口 / human product + engineering entrypoint
AGENTS.md                       Coding Agent 路由 / coding-agent execution router
00-GOVERNANCE/                 权威规则、发布、handoff evidence / canonical governance
02-ARCHITECTURE/               架构资料 / architecture material
08-AUDIT/                       审计证据 / audit evidence
99-ARCHIVE/                     历史/归档证据 / historical evidence
.github/                        CI/workflow
scripts/                        运维、启动、维护脚本 / operations/startup/maintenance
app.py                          当前 Flask 应用入口 / current Flask application entry
run_supervised.py               当前进程监督器 / current process supervisor
requirements.txt                生产/运行 Python 依赖 / production/runtime Python dependencies
requirements-dev.txt            开发/测试 Python 依赖 / development/test dependencies
package.json                    根 Node tooling manifest
.env.example                    非敏感配置模板 / non-secret configuration template
```

以上是入口导航，不代表所有根目录文件都已经达到最终目录形态。不得只看文件名进行批量移动或重写。

This is orientation, not a claim that every root file is optimally placed. Do not mass-move or rewrite production code based on filenames alone.

工程标准 / Engineering standard: [`00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md`](00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md)

---

## 6. 唯一主线 / Single-mainline policy

**`main` 是唯一长期研发主线、唯一远端生产候选真相。**

**`main` is the only long-lived development line and the only remote production-candidate truth.**

规则 / Rules:

- 任务支线只能短期存在，用于隔离一个明确工程任务；task branches are short-lived and scoped to one coherent change.
- 有效实现、测试、规范和证据必须在完成后合入 `main`; valid implementation, tests, governance and evidence must converge back into `main`.
- 不允许长期存在第二条 production/feature/integration 真相；no parallel long-lived production/feature/integration truth.
- 分支名、旧 branch HEAD、handoff branch 不能作为当前功能完成证明；branch names and historical HEADs are not runtime proof.
- 合并前必须比较内容与依赖，不得因为“分支存在”就无脑覆盖当前主线；compare content and dependency ownership before consolidation.
- 已被 `main` 完整包含的旧分支应视为 retired；branches fully contained by `main` are retired, not development entrypoints.
- 如果旧分支存在独有实现，先把仍有效的实现/测试/证据收回 `main`，再结束该分支；if a branch has unique work, salvage valid implementation/test/evidence into `main` before retirement.

分支收敛审计见 / Branch-convergence audit: `00-GOVERNANCE/SINGLE-MAINLINE-BRANCH-CONSOLIDATION-V1.md`（若存在 / when present）。

---

## 7. 工程师上手 / Engineering onboarding

### 7.1 先确认仓库身份 / Verify repository identity first

在当前 Windows 机器，先进入唯一工作区：

```powershell
Set-Location D:\LUMENIS_REBUILD
```

然后核验：

```bash
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git rev-parse HEAD
git status
git fetch origin
git rev-parse origin/main
```

正确远端 / Expected remote:

```text
Zachary-1012/LUMENIS-codex-Clean-OS
```

未知本地修改在分类前不得丢弃。

Preserve unknown local changes until classified.

### 7.2 Python 环境 / Python environment

生产/运行依赖 / Production/runtime:

```text
requirements.txt
```

开发/测试依赖 / Development/test:

```text
requirements-dev.txt
```

Windows 开发示例 / Windows development example:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

生产环境只安装运行依赖时使用 `requirements.txt`。不得提交 `.env`、凭证、Cookie、Session 或真实生产数据。

Use `requirements.txt` for a runtime-only environment. Never commit `.env`, credentials, cookies, sessions or real production data.

### 7.3 Node tooling

根 `package.json` 当前服务于 Playwright/browser/login/search 等工具。只有任务需要时才安装：

The root `package.json` supports Playwright/browser/login/search tooling. Install it only when required:

```bash
npm install
```

Node tooling 不是主应用运行时。

Node tooling is not the main application runtime.

---

## 8. 配置与数据安全 / Configuration and data safety

`.env.example` 是非敏感配置模板。历史命名或多代配置键必须通过依赖追踪逐步收口，不能凭外观直接删除。

`.env.example` is the non-secret configuration template. Historical naming and multiple configuration generations must be converged through dependency tracing, not deleted by appearance.

硬规则 / Hard rules:

- 不提交 secret/live Cookie/session；no committed secrets/live cookies/sessions.
- 生产运行不得依赖某个开发者机器绝对路径；no developer-machine absolute path as a production requirement.
- tests/staging 使用 isolated/disposable DB；tests/staging use isolated/disposable databases.
- test DB 不得静默 fallback 到受保护 production DB；no silent fallback into the protected production DB.
- DB isolation/migration 必须有运行证据；DB isolation/migration requires runtime evidence.
- missing/unknown 与数字 `0` 必须保持不同语义；missing/unknown remains distinct from numeric zero.

---

## 9. 启动与健康检查 / Start and health

当前 Windows production launcher / Current Windows production launcher:

```powershell
Set-Location D:\LUMENIS_REBUILD
powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
```

启动脚本从自身位置解析仓库根，不会把 `D:\LUMENIS_REBUILD` 硬编码进可移植生产逻辑。

The launcher resolves the repository root from its own script location; `D:\LUMENIS_REBUILD` is the current workstation entrypoint, not a portable production-code dependency.

当前 health target / Current health target:

```text
http://127.0.0.1:8201/healthz
```

启动验收 / Startup acceptance:

```text
dependencies
→ configuration
→ launcher
→ application boot
→ supervisor stability
→ port bind
→ health
→ required runtime initialization
→ critical APIs / Experience
```

外部 browser/login/source 可用性与 core application health 分开报告。

External browser/login/source availability is reported separately from core application health.

---

## 10. 开发流程 / Development workflow

```text
Current Gate / Ticket
→ Dependency Trace
→ Reuse Existing Owner
→ Implement
→ Scoped Test
→ Neighbour Regression
→ Runtime / E2E when required
→ Evidence
→ Coherent Commit
→ Merge to main
→ Next Gate
```

优先 `reuse → adapt → bind → verify`。不得为局部问题建立第二套 DB、Evidence、Metric、Permission、Runtime、Subject Context、Design System 或 API truth。

Prefer `reuse → adapt → bind → verify`. Do not create a second DB, Evidence, Metric, Permission, Runtime, Subject Context, Design System or API truth to solve a local problem.

不要每次任务都重新全仓发现，只加载当前工作需要的源码、契约与测试。

Do not rediscover the full repository for every task; load only the source, contracts and tests required by the active work.

Coding-agent rules / Agent 规则: [`AGENTS.md`](AGENTS.md)

---

## 11. 测试与 E2E / Testing and E2E

按影响范围逐步扩大 / Widen tests proportionally:

```text
fast/static
→ targeted unit
→ affected integration
→ neighbour regression
→ representative/domain E2E
→ full regression at convergence/release gates
```

叶子修改不要反复跑完整数千测试；共享 primitive、DB、Permission、Runtime 等变化则必须扩大验证。

Do not run the entire suite after every leaf edit; widen verification when shared primitives, persistence, permission or runtime infrastructure changes.

Clean-checkout CI 与 Environment/Production-Live Acceptance 分层。详见 [`tests/CI_TEST_TIERS.md`](tests/CI_TEST_TIERS.md)。被 clean CI 排除的 live test **不等于 PASS**。

Clean-checkout CI and Environment/Production-Live Acceptance are separate tiers. See [`tests/CI_TEST_TIERS.md`](tests/CI_TEST_TIERS.md). A live test excluded from clean CI is **not** considered passed.

重要用户功能最终应证明 / Important user-operable features should prove:

```text
UI Entry
→ User Action
→ API / Service
→ Permission
→ Canonical Read/Write
→ Real Result
→ Evidence / Trace
→ Honest Error State
→ Automated Test
→ E2E
```

`UI EXISTS`、`API EXISTS`、`TEST EXISTS` 单独都不等于 `FEATURE DONE`。

`UI EXISTS`, `API EXISTS` or `TEST EXISTS` alone does not mean `FEATURE DONE`.

---

## 12. Production Convergence DAG

```text
G0  Repository Truth Convergence
→ G1  DB / Safety Foundation
→ G2  Source + Evidence Unification
→ G3  Collector Runtime
→ G4  Canonical Content Intelligence
→ G5  Research Engine
→ G6  Learning Asset Engine
→ G7  Write / Permission / Approval Closure
→ G8  Content Studio Production Binding
→ G9  Application Trace
→ G10 Performance Collector
→ G11 Evaluation → Pattern Validation
→ G12 Learning Version Update
→ G13 Shared + SYSTEM UI Binding
→ G14 凉子访谈录 60期真实 Acceptance Dataset
→ G15 Full Regression / Security / Recovery / E2E
→ G16 Release Gates
```

---

## 13. 发布语义 / Release semantics

```text
IMPLEMENTED = 代码存在 / code exists
TESTED      = 对应测试通过 / scoped tests pass
VERIFIED    = Runtime / E2E 证明行为 / runtime/E2E proves behavior
RELEASED    = 发布、安全、恢复、回滚 Gate 通过 / release/security/recovery/rollback gates pass
OPERATING   = 真实运行产生规定的线上/时间性证据 / real operation produces required live/time evidence
```

不要把 GitHub Actions 绿色、HTTP 200 或页面能打开当成 Production Ready 的替代证据。

Do not use a green workflow, HTTP 200 or a rendered page as a substitute for Production Readiness.

---

## 14. 文档索引 / Documentation index

长期规则优先阅读：

- [`AGENTS.md`](AGENTS.md)
- [`00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md`](00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md)
- [`00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md`](00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md)
- [`00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md`](00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md)
- [`00-GOVERNANCE/SINGLE-MAINLINE-BRANCH-CONSOLIDATION-V1.md`](00-GOVERNANCE/SINGLE-MAINLINE-BRANCH-CONSOLIDATION-V1.md)

当前 Windows 接续任务再读取：

- [`00-GOVERNANCE/handoff/CODEX-CURRENT-BLOCKERS-20260913.md`](00-GOVERNANCE/handoff/CODEX-CURRENT-BLOCKERS-20260913.md)

历史 handoff / audit / archive 只在迁移、回溯、审计需要时读取，不作为正常开发必读材料。

---

## 15. Third-Party / Open-Source Components

所有重要非自研组件必须登记到 [`00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md`](00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md)，并保持：purpose、usage、integration boundary、license/verification status、replaceability 与 native replacement direction。

All material non-native components must be recorded in the canonical third-party register with purpose, usage, integration boundary, license/verification status, replaceability and native-replacement direction.

Third parties may implement adapters/infrastructure but must not silently become the owner of LUMENIS DB Truth, Evidence Truth, Metric Truth, Permission Truth or Business Truth.
