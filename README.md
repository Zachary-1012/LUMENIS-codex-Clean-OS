# 序境 / LUMENIS

> **Production Core · Production Truth Owner**  
> 当前阶段 / Current phase: **PRODUCTION CONVERGENCE**

序境 / LUMENIS 是面向商业运营与品牌市场的生产级产品。AI 是增强能力，不拥有 Production Truth。

本仓库承载当前生产实现、运行时、数据契约、Evidence、API、Permission、Metric、Experience、测试与发布证据。`README.md` 是人类工程入口，不是历史进度日志；文档、提交说明、CI 绿色或页面可打开，都不能单独证明功能已经 `VERIFIED / RELEASED / OPERATING`。

> Coding Agent / Codex 的当前执行入口固定为：`AGENTS.md` → `00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md`。当前 HEAD 必须通过 `git fetch origin` + `git rev-parse origin/main` 动态解析，不得从 README、历史 handoff、截图或粘贴 SHA 推断。

## 0. CURRENT 接管入口与历史审计基线 / Current takeover and audit provenance

当前执行入口：

```text
AGENTS.md
→ 00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md
→ README.md
→ 00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md
→ 00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json
→ current source / runtime / DB / API / Permission / Evidence / tests for the active slice
```

2026-09-16 文档更新前的远程 `main` 审计点：

```text
repo   = Zachary-1012/LUMENIS-codex-Clean-OS
branch = main
sha    = 147e3bd331b22236930ae29112a67c613a148f67
```

**这个 SHA 只保留为 point-in-time audit provenance，不是当前 HEAD、checkout target、reset target 或 Codex 开发基线。** 当前 `origin/main` 必须在每次工程会话开始时重新读取。

该历史审计基于当时远程源码、运行入口、依赖清单、CI 分层、Evidence、Collector、Experience V2 与内容生成实现进行核对；记录见：

- [`08-AUDIT/SOURCE-LEVEL-REPOSITORY-AUDIT-20260916.md`](08-AUDIT/SOURCE-LEVEL-REPOSITORY-AUDIT-20260916.md)
- [`00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md`](00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md)

远程、当前本地 working tree、local-only commit、历史审计点、最后 runner-backed green baseline、current-head CI 与 live runtime 必须分开描述；不得互相冒充。

---

## Canonical product architecture

The sole product/domain architecture authority is:

`00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`

LUMENIS is now **App-only as the final user-facing product**. The canonical Experience is one Flutter application codebase for Windows, macOS, Linux, Android and iOS. The legacy browser/Jinja/static surfaces have been removed from `main`; retained Experience contracts live under `contracts/experience/` and bind the Flutter App to Product Core/API.

## 1. 产品定位 / Product definition

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

四域结构：

| 域 | 定位 | 主要责任 |
| --- | --- | --- |
| CTH · 商业运营 | Subject-first | 主体、场地/项目、事件、案例、风险、决策与行动 |
| BMP · 品牌市场 | Brand/Market-first | 品牌、竞品、创作者/账号、Campaign、传播表现、Benchmark、风险与评估 |
| Shared Capability | 跨域共享 | Content & Creation、Evidence、Research、Evaluation、Learning Asset、AI Enhancement |
| SYSTEM | 控制与基础设施 | Collector、Runtime、Scheduler、AI Gateway、Database、Security、Permission、Settings、Recovery、Observability |

CTH 与 BMP 可以共享 Subject Context 与基础设施，但不得静默合并领域模型、指标、关系和行动语义。

---

## 2. 2026-09-16 源码审计确认的生产事实 / Point-in-time source facts

以下内容是 `147e3bd...` 审计点确认的 source evidence，不是对未来/current HEAD 的永久声明。Codex 开始具体工作时必须以当前源码重新核验 owner、caller、contract、runtime 与 tests；若当前源码不同，以当前源码为准。

### Runtime

审计点确认的 Windows canonical launcher：

```powershell
Set-Location D:\LUMENIS_REBUILD
powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
```

审计点确认的 core health target：

```text
http://127.0.0.1:8201/healthz
```

审计点启动链使用现有 `.venv`、`run_supervised.py`、Flask/Waitress 运行时，并维护 8201 supervisor；Resident Browser 使用现有 9222/9223 双身份 CDP。工作站路径是本机入口，不应成为可移植生产代码硬依赖。

### Experience V2

审计点 `app.py` 已注册 `experience_runtime`，Experience 挂载到：

```text
/experience/
/api/experience/*
```

审计点源码明确声明真实后端绑定屏幕为 `CTH-01` 与 `AI-01`；其他屏幕不得仅因原型存在就视为生产绑定完成。当前 HEAD 是否已有变化必须重新以源码验证。

### Evidence / Canonical

当前 canonical owner 为 `lumenis/shared/evidence/`，提供 Evidence / Canonical lineage、存储、API 与生产契约；旧根级 `evidence_chain.py` 等 owner 已退休。Evidence 不被分析结果覆盖，provenance、rule version、AI 输出与人工修正保持分离。

XHS side-write、lineage convergence 与其他 Evidence 行为必须以当前源码和测试为准；若本地存在比远程更新的有效修复，必须先完成 local→main 收敛再把状态升级为远程已实现。

### Evaluation / Learning

当前 canonical owners 为 `lumenis/shared/evaluation/` 与 `lumenis/shared/learning/`。Evaluation 统一承载真实质量、AI、Benchmark 与 Agent trajectory 评估；Learning 统一承载反馈、修正、规则建议、学习扫描、反馈闭环与学习持久化。

Learning 输出本身不是 Production Truth。规则建议必须经过人工审核，写入规则注册表时保持非激活状态，且 AI 生成的研究内容不得绕过 Evidence 直接写成外部事件事实。

### Collector / XHS runtime

审计点 `xhs_cookie_bridge.py` 包含受控本地 Cookie/Profile 读取、双身份逻辑、9222/9223 Resident Browser、冷却/风控/次数兜底和 policy gate。Cookie/session 不得进入源码、日志、公开配置或文档。

### Content & Creation

审计点 `content_generation.py` 包含结构化内容类型、研究库检索、Evidence、Evaluation、人工反馈迭代以及 local-first AI / 显式 cloud enable 语义。AI 输出仍不是 Production Truth。

---

## 3. 事实权威 / Authority order

发生冲突时：

```text
Current Production Source
> Runtime Reality
> Current DB / API / Permission / Evidence Contracts
> Tests / E2E / Production Acceptance
> Current Canonical Governance
> Experience V2 / Current UI Capability Evidence
> README
> Historical Handoff / Legacy Evidence
> Chat History
```

状态语义必须严格区分：

```text
IMPLEMENTED = 代码存在
TESTED      = 对应 scoped automated tests 通过
VERIFIED    = Runtime / E2E 证明行为
RELEASED    = 发布、安全、恢复、回滚 Gate 通过
OPERATING   = 真实运行产生规定的线上/时间性证据
```

`CI PASS != LIVE_VERIFIED`，`RELEASED != OPERATING`。

---

## 4. 审计点依赖与零授权能力边界

2026-09-16 审计点的 `requirements.txt` 包含并可作为既有基础设施的历史核验对象：

```text
Flask / Waitress
APScheduler / schedule
requests / httpx / aiohttp
BeautifulSoup4 / lxml
Playwright
SQLite (stdlib)
tenacity
Alembic
```

审计点根 `package.json` 承担 Node tooling，并直接依赖 Playwright；它不是 Next.js/React/Vite 生产前端 manifest。当前依赖状态必须以当前 manifest 重新读取。

本轮“零授权能力”标准：免费、无需第三方 API Key/OAuth、可进入 LUMENIS 自有 Production Truth。正式验收表见：

[`00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md`](00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md)

特别说明：2026-09-16 远程审计点记录 `requirements.txt` **尚未包含 `feedparser`**，这是历史事实。当前 canonical `requirements.txt` 已包含 `feedparser>=6.0.11`；验收必须继续以当前 manifest、重启后的 runtime 和测试证据为准。

---

## 5. 标准闭环 / Canonical closed loop

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

硬约束：

- Collector 始终由 SYSTEM 单一拥有；
- Upload / Import / API / Collector 只是 acquisition adapters，必须汇聚到同一 Production Truth；
- `MetricSnapshot` append-only；
- `missing != 0`；
- AI 可提出 Pattern candidate，但不能自主执行 `Pattern → ADOPT`；
- 登录态 Collector 保持只读；未来 Publisher 必须独立经过 Permission → Approval → Effect Fence；
- 第三方组件只能位于 bounded adapter/infrastructure 边界，不能成为 DB/Evidence/Metric/Permission/Business Truth owner。

Canonical detail: [`00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md`](00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md)

---

## 6. 仓库导航 / Repository orientation

```text
README.md                       人类产品 + 工程入口
AGENTS.md                       Coding Agent 执行路由
LICENSE                         LUMENIS 源码许可边界
00-GOVERNANCE/                 权威规则、验收、handoff evidence
02-ARCHITECTURE/               架构资料
08-AUDIT/                      当前审计证据
.github/workflows/             CI
scripts/                       运维、启动、维护脚本
app.py                         当前 Flask 应用入口
run_supervised.py              当前进程监督器
requirements.txt               生产/运行 Python 依赖
requirements-dev.txt           开发/测试 Python 依赖
package.json                   Node tooling manifest
.env.example                   非敏感配置模板
```

不得按文件名批量移动/删除源码。任何重构前先完成 owner/caller/data read-write/runtime/test dependency trace。

---

## 7. 唯一本地工作区 + 唯一可写主线

当前 Windows 研发机唯一有效工作区：

```text
D:\LUMENIS_REBUILD
```

`main` 是唯一可写研发、集成和生产候选主线。

开始工作前：

```powershell
Set-Location D:\LUMENIS_REBUILD
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short --branch
git fetch origin
git rev-parse origin/main
```

硬规则：

- 保护未知/未提交/未 push 的有效本地工作；
- 不用 remote tree 覆盖本地有效修复；
- 正常研发不创建 task/feature/codex/production/integration/handoff/research 分支；
- 不 force-push `main`；
- validated change → coherent commit → push `origin/main`；
- side branch 只作历史证据，必要时一次性吸收其独有有效实现。

---

## 8. Codex / Coding Agent 执行标准

Coding Agent 必须首先读取 [`AGENTS.md`](AGENTS.md)，随后读取 [`00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md`](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md)。

默认执行方式：

```text
Active Gate / Ticket
→ Inspect exact owner / caller / contract / tests
→ Reuse before rebuild
→ Implement
→ Scoped test
→ Affected regression
→ Runtime / E2E when required
→ Evidence
→ Coherent commit
→ Sync main
```

Codex 本地开发工具（如 Playwright MCP、Filesystem MCP、Git、rg、fd、jq、sqlite3 CLI、curl）属于开发/验收工具层，不自动成为 LUMENIS 生产依赖。

不得为了“确认权限”、测试 connector、重触发 Actions 或制造活动记录而创建/删除 probe 文件、空提交、无内容变化提交或重复改写同一文件。已有证据可复用时不得重复取证；只有当前任务所需且尚未验证的事实才继续读取。

---

## 9. 测试、CI 与 Live Gate

CI 当前分层：

```text
Tier A  Repository Integrity            BLOCKING
Tier B  Hermetic Product/Contract       BLOCKING
Tier C  Production / Live / Environment required acceptance evidence
```

详见 [`tests/CI_TEST_TIERS.md`](tests/CI_TEST_TIERS.md)。

当前自动 CI 只保留两类正式 Gate：`LUMENIS Product Gate`（唯一的跨产品契约 / Only-One / App-only / Python hermetic 产品 Gate）与按 App 变更触发的 `LUMENIS App Gate`（Flutter analyze/test）。重复的独立 LUMENIS-GGI workflow 已退休。Product Gate 会先执行不依赖外网的治理、App-only 架构、源码编译与 test-tier manifest 检查，再进入 dependency install / hermetic pytest；App Gate 也先执行 App-only Experience 审计，再获取 Flutter SDK/依赖。Production/Live 环境套件不会因为被 clean CI 排除而自动视为 PASS。Runner 0-step、DNS、package registry 等执行层故障必须记为 `EXECUTION-LAYER UNVERIFIED`，不得冒充产品 PASS/FAIL。

重要用户功能应证明：

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

GitHub Actions 若出现 job 未真正开始、`steps=[]`、0-step 或无 repository-step log，只能标记为 execution-layer unverified；不得伪装成源码测试 PASS，也不得直接归因为产品回归。不要通过空提交重触发。

---

## 10. Production Convergence DAG

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

不得因为旧 handoff、旧 commit 或文档写过某 Gate 就重复做，也不得因为文档存在就跳过执行证据。

---

## 11. 第三方与 License

第三方组件登记：[`00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md`](00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md)

当前仓库源码许可边界见 [`LICENSE`](LICENSE)。第三方/开源依赖继续受各自原始许可证约束，不能被本仓库 License 覆盖或重新许可。

未知第三方许可证、未登记的 shipped third-party code、错误 attribution 均是 release blocker。

---

## 12. 安全红线

不得提交或暴露：

- `.env`、API key、credential；
- Cookie / session / browser profile secret；
- 真实生产 DB；
- system/developer prompt 或 private reasoning；
- 受保护内部工具细节；
- 未经审批的高风险外部写操作。

Tests/staging 必须显式使用 isolated/disposable DB；任何 persistence 变更都必须证明不会静默落到受保护 production DB。

---

## 13. Canonical documents

当前接管与跨产品治理优先读取：

- [`AGENTS.md`](AGENTS.md)
- [`00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md`](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md)
- [`00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md`](00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md)
- [`00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json`](00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json)

其他优先级较高的长期文档：

- [`00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md`](00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md)
- [`00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md`](00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md)
- [`00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md`](00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md)
- [`00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md`](00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md)
- [`08-AUDIT/SOURCE-LEVEL-REPOSITORY-AUDIT-20260916.md`](08-AUDIT/SOURCE-LEVEL-REPOSITORY-AUDIT-20260916.md)

历史 handoff / audit / archive 只在迁移、回溯、审计需要时读取，不作为正常开发必读材料。