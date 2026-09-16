# 序境 / LUMENIS

> **Production Core · Production Truth Owner**  
> 当前阶段 / Current phase: **PRODUCTION CONVERGENCE**

序境 / LUMENIS 是面向商业运营与品牌市场的生产级产品。AI 是增强能力，不拥有 Production Truth。

本仓库承载当前生产实现、运行时、数据契约、Evidence、API、Permission、Metric、Experience、测试与发布证据。`README.md` 是人类工程入口，不是历史进度日志；文档、提交说明、CI 绿色或页面可打开，都不能单独证明功能已经 `VERIFIED / RELEASED / OPERATING`。

## 0. 当前源码审计基线 / Current source-audit baseline

2026-09-16 文档更新前的远程 `main` 审计基线：

```text
repo   = Zachary-1012/LUMENIS-codex-Clean-OS
branch = main
sha    = 147e3bd331b22236930ae29112a67c613a148f67
```

本次更新基于远程源码、运行入口、依赖清单、CI 分层、Evidence、Collector、Experience V2 与内容生成实现进行核对；审计记录见：

- [`08-AUDIT/SOURCE-LEVEL-REPOSITORY-AUDIT-20260916.md`](08-AUDIT/SOURCE-LEVEL-REPOSITORY-AUDIT-20260916.md)
- [`00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md`](00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md)

远程基线与本地尚未 push 的有效实现必须分开描述；不得把 local-only 代码写成 GitHub 已实现。

---

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

## 2. 当前远程源码确认到的生产事实

### Runtime

当前 Windows canonical launcher：

```powershell
Set-Location D:\LUMENIS_REBUILD
powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
```

当前 core health target：

```text
http://127.0.0.1:8201/healthz
```

启动链使用现有 `.venv`、`run_supervised.py`、Flask/Waitress 运行时，并维护 8201 supervisor；Resident Browser 由现有脚本管理 9222/9223 双身份 CDP。工作站路径是本机入口，不应成为可移植生产代码硬依赖。

### Experience V2

`app.py` 已注册 `experience_runtime`；当前生产 Experience 挂载到：

```text
/experience/
/api/experience/*
```

当前源码明确声明真实后端绑定屏幕为 `CTH-01` 与 `AI-01`；其他屏幕不得仅因原型存在就视为生产绑定完成。

### Evidence / Canonical

`evidence_chain.py` 提供 `zbc_evidence`、`zbc_canonical_data` 与 lifecycle tracking 等链路，强调 Evidence 不被分析结果覆盖、provenance、rule version、AI 输出与人工修正分离。

远程 `main` 的 XHS side-write 仍应以当前源码和测试为准；若本地存在比远程更新的 lineage convergence 修复，必须先完成 local→main 收敛再把状态升级为远程已实现。

### Collector / XHS runtime

`xhs_cookie_bridge.py` 当前源码包含受控本地 Cookie/Profile 读取、双身份逻辑、9222/9223 Resident Browser、冷却/风控/次数兜底和 policy gate。Cookie/session 不得进入源码、日志、公开配置或文档。

### Content & Creation

`content_generation.py` 当前实现包含结构化内容类型、研究库检索、Evidence、Evaluation、人工反馈迭代以及 local-first AI / 显式 cloud enable 语义。AI 输出仍不是 Production Truth。

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

## 4. 当前依赖与零授权能力边界

远程 `requirements.txt` 当前包含并可作为现有基础设施核验对象：

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

根 `package.json` 当前仅承担 Node tooling，并直接依赖 Playwright；它不是 Next.js/React/Vite 生产前端 manifest。

本轮“零授权能力”标准：免费、无需第三方 API Key/OAuth、可进入 LUMENIS 自有 Production Truth。正式验收表见：

[`00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md`](00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md)

特别说明：远程审计基线 `requirements.txt` **尚未包含 `feedparser`**。本地安装/验证可以记为 local evidence，但在对应 `requirements.txt` 修改 push 到 `main` 前，不得称为 remote implemented。

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
99-ARCHIVE/                    历史/归档证据
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

Coding Agent 必须首先读取 [`AGENTS.md`](AGENTS.md)。

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

---

## 9. 测试、CI 与 Live Gate

CI 当前分层：

```text
Tier A  Repository Integrity            BLOCKING
Tier B  Hermetic Product/Contract       BLOCKING
Tier C  Production / Live / Environment required acceptance evidence
```

详见 [`tests/CI_TEST_TIERS.md`](tests/CI_TEST_TIERS.md)。

当前 GitHub workflow 会执行 dependency install、`compileall`、test-tier manifest validation 与 hermetic pytest；Production/Live 环境套件不会因为被 clean CI 排除而自动视为 PASS。

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

优先级较高的长期文档：

- [`AGENTS.md`](AGENTS.md)
- [`00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md`](00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md)
- [`00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md`](00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md)
- [`00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md`](00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md)
- [`00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md`](00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md)
- [`08-AUDIT/SOURCE-LEVEL-REPOSITORY-AUDIT-20260916.md`](08-AUDIT/SOURCE-LEVEL-REPOSITORY-AUDIT-20260916.md)

历史 handoff / audit / archive 只在迁移、回溯、审计需要时读取，不作为正常开发必读材料。
