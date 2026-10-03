# 序境 / LUMENIS

> **Production Core · Production Truth Owner**
> 当前阶段 / Current phase: **SIX-ROUND EXECUTION AUTHORIZED / PRODUCT CLOSURE IN PROGRESS**
>
> Canonical repository: Zachary-1012/LUMENIS-codex-Clean-OS (default branch: main).

序境 / LUMENIS 是面向商业运营与品牌市场的生产级产品。AI 是增强能力，不拥有 Production Truth。

本仓库承载当前生产实现、运行时、数据契约、Evidence、API、Permission、Metric、Experience、测试与发布证据。`README.md` 是人类工程入口，不是历史进度日志；文档、提交说明、CI 绿色或页面可打开，都不能单独证明功能已经 `VERIFIED / RELEASED / OPERATING`。

> Coding Agent / Codex 的当前执行入口固定为：`AGENTS.md` → `00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md` → `00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md`。当前 HEAD 必须通过 `git fetch origin` + `git rev-parse origin/main` 动态解析，不得从 README、历史 handoff、截图或粘贴 SHA 推断。
>
> 只读取 GitHub 的审查者：先看 [CURRENT 远端／本地／验收状态快照](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md#0-online-readers-current-state-snapshot)。GitHub 不包含受保护的本地未提交候选；快照有时间边界，不能代替实时源码、测试或运行验收。

Coding Agent 必须首先读取 [`AGENTS.md`](AGENTS.md)。

## 0. Current source and acceptance

At the start of every engineering task, resolve the current remote `main` HEAD. A README SHA, dated audit, handoff, or commit message is never a substitute for the current source tree.

Before changing product code, read:
```text
AGENTS.md
→ 00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md
→ 00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md
→ 00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md
→ README.md
→ 00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md
→ 00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json
→ current source, runtime, DB, API, Permission, Evidence and scoped tests
```

Describe `IMPLEMENTED`, `TESTED`, `VERIFIED`, `RELEASED` and `OPERATING` separately, with evidence tied to the current commit. A green CI result or an old audit alone does not prove live product behavior.

## Canonical product architecture

The sole product/domain architecture authority is:

`00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`

LUMENIS is **one product with four approved Experience surfaces**: Public Website, Web Workspace, Desktop App and Mobile Companion. The operational Experience uses one Flutter codebase for Web, Windows, macOS, Linux, Android and iOS over one Product Core/API; the separate SEO-capable Public Website is presentation/acquisition only. The legacy browser/Jinja/static surfaces have been removed from `main` and must not be restored. A Public Website foundation is committed, but neither it nor the local Flutter Web Workspace candidate is shipped or accepted as a complete commercial surface. See the CURRENT snapshot above and `00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md`.

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

## 2. Current implementation map

- `app.py` and the supervised runtime are the LUMENIS Product Core entry points; verify their current behavior from source and runtime evidence.
- `lumenis/` contains canonical production owners for shared capability and system services.
- `contracts/experience/` contains the retained Experience contracts.
- `app/` is the canonical Flutter user application. It now contains source-backed vertical slices for the five Golden Pages and a nested, read-only CTH-02 Subject directory. A launch surface, widget test, or registered route alone does not prove complete CTH/BMP workflows.
- CTH and BMP are distinct LUMENIS business domains. Shared services do not merge their data, metrics, actions or user tasks.
- `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md` is the fixed source classification and resume map. Normal work follows its exact owner/caller/contract/test row instead of repeating a repository-wide audit.

The Experience plan covers **44 distinct screen-specific UX blueprints** plus **54 fail-closed data/permission/Evidence binding records**. The Product Owner approved the ROUND 01 audit/missing register/multi-surface/15-round baseline on 2026-09-21, but that approval does not accept an individual screen, API, permission, workflow or implementation. Before implementing each screen, record its verified source fields, owner, route, states, separate Web/Desktop/Mobile composition, authorization/effects and executable acceptance in `contracts/experience/screen-specifications/` using `SCREEN_SPEC_TEMPLATE.md`, then obtain the screen's `DESIGN_READY` decision. The machine-readable binding registry at `contracts/experience/lumenis_app_binding_registry.json` constrains data/actor/permission/Evidence truth and is not a UI template. PDF sketches, screenshots, prototypes and Figma frames remain `DESIGN_EXPLORATION`; they may not be copied directly into code or treated as acceptance. Legacy `sectionTypes` are inventory only; one generic renderer with substituted titles is prohibited. Continue source-backed vertical slices and mark unresolved behavior as blocked or unverified until its owner and acceptance evidence exist.

Architecture documents describe intended boundaries. Production capability is established only by the current implementation and its scoped acceptance evidence.

## 3. 事实权威 / Authority order

发生冲突时：

```text
Current Production Source
> Runtime Reality
> Current DB / API / Permission / Evidence Contracts
> Tests / E2E / Production Acceptance
> Current Canonical Governance
> Canonical Experience Constitution / Current UI Capability Evidence
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

## 4. Dependencies and optional capabilities

Treat the checked-in manifests as the current dependency authority:
- `requirements.txt` for Python runtime dependencies;
- `app/pubspec.yaml` for the Flutter application;
- `package.json` for repository tooling.

Do not infer a production frontend, active provider, or capability from a dependency name or an old audit snapshot. Optional external providers must remain explicitly configured and must not silently become required for core product behavior.

The zero-auth capability acceptance criteria are maintained in [`00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md`](00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md).

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
00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md  固定源码 owner / 六轮执行与完整历史验收映射
02-ARCHITECTURE/               架构资料
app/                           唯一 Flutter 用户端
contracts/experience/          Screen / Action / State / Permission / Evidence / ViewModel 契约
lumenis/shared/                Evidence / Database / Evaluation / Learning / Reporting / Agent Skill owner
lumenis/system/                AI Gateway / Collector / Browser / Security owner
tests/ + app/test/             Python 与 Flutter 验收代码
data/ + migrations/            受保护运行数据边界与数据库迁移（不得按目录直接改写生产数据）
.opencode/                     OpenCode 研发工具配置，不是产品运行能力
scripts/audit_tools/            当前仓库结构与边界检查
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
D:\LUMENIS_REBUILD\序\序境
```

`main` 是唯一可写研发、集成和生产候选主线。

开始工作前：

```powershell
Set-Location D:\LUMENIS_REBUILD\序\序境
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

每次交付前后都要证明本地与实时远端分支清单：

```powershell
git fetch origin --prune
git branch --format="%(refname:short)"
git branch -r --format="%(refname:short)"
git ls-remote --heads origin
```

验收只接受本地 `main`、远端跟踪 `origin/main` 和实时 `refs/heads/main`。若发现其他分支，先检查独有提交和文件，保留有效能力到 `main`，再删除已确认冗余的分支并复查实时清单。不得删除未审查分支，也不得 force-push 来通过检查。

---

### 当前规则同步 / 2026-10-03

当前统一口径：完整成果 Batch、默认 GLOBAL 工作入口、序境风格的采集结果与 SH-01 Discover、由产品 Collector/Scheduler 自运行采集、可扩展案例创意与真实预算/资源约束。唯一执行路由仍为 AGENTS.md；详细体验、数据及验收分别归现有 Experience Constitution、Global contract 和 Real Delivery Overlay。规则/设计发布不代表这些产品能力已经完成；实际状态和发布证据见 CURRENT。旧暂停记录、研究包与工作回执不能成为第二套执行规则。

## 8. Codex / Coding Agent 执行标准

Coding Agent 必须首先读取 [`AGENTS.md`](AGENTS.md)，随后读取 [`00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md`](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md)。

当前唯一方案保留 **C1–C6 六个完整交付职责**：C3（CTH/BMP）与 C5（资料/共享成果）已由同一个本地「序境｜C3+C5 与未完成研究资料接续」窗口承接，并保留未完成研究；原云端 W3/W5 仅保留交接。C1、C2、C4、C6 继续本地执行，前端 F 独立，主控 M（Sol 或 Astra）把关验收，W6 集成发布。原 R01–R15、J1–J8、六项专项验收映射保留，不再分别派工。当前C1–C6已按最新明确指令恢复，前端F仍暂停；以完整用户成果组织任务，按真实依赖并行推进，遇到缺陷先定向研究再修复和必要验证。分工/云隔离见 [AGENTS.md](AGENTS.md)，完整映射见 [Source Owner Index](00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md)。旧本地模型/智谱/OpenCode 模型调用停止、接口保留；C2 完成自有权重训练运行。实时对话语音后置，音频理解/播客保留；账号密码重设计在工程闭环后，开放入口仍保留服务端 Permission/effect fence。

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

当前两类正式 Gate 是 `LUMENIS Product Gate`（唯一的跨产品契约 / Only-One / multi-surface / Python hermetic 产品 Gate）与 `LUMENIS App Gate`（Flutter analyze/test）。普通 `main` push 在本地完整 blocking Gate 通过后可发布，不自动启动这两个云端重型 Gate；必要 PR 验证和明确里程碑的 `workflow_dispatch` 保留，Release / Internal Beta / RC 验收在同一 SHA 上手动运行完整云端 Gate。重复的独立 LUMENIS-GGI workflow 已退休。Product Gate 会先执行不依赖外网的治理、多终端架构、源码编译与 test-tier manifest 检查，再进入 dependency install / hermetic pytest；App Gate 也先执行唯一 Experience authority 与 anti-template 审计，再获取 Flutter SDK/依赖。Public Website 基础已进入 `main`；其完整商业入口和专用 Gate 仍未验收，不能因基础文件存在就视为已验证。Production/Live 环境套件不会因为被 clean CI 排除而自动视为 PASS。Runner 0-step、DNS、package registry 等执行层故障必须记为 `EXECUTION-LAYER UNVERIFIED`，不得冒充产品 PASS/FAIL。

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
- [`00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)
- [`00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`](00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)
- [`00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md`](00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md)
- [`00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md`](00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md)
- [`00-GOVERNANCE/PRODUCT-POSITIONING-CURRENT.md`](00-GOVERNANCE/PRODUCT-POSITIONING-CURRENT.md)
- [`00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md`](00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md)
- [`00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md`](00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md)
- [`00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json`](00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json)

其他优先级较高的长期文档：

- [`00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md`](00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md)
- [`00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md`](00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md)
- [`00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md`](00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md)
- [`00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md`](00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md)
- [`scripts/audit_tools/verify_lumenis_single_product.py`](scripts/audit_tools/verify_lumenis_single_product.py)

历史 handoff / audit / archive 只在迁移、回溯、审计需要时读取，不作为正常开发必读材料。

## 当前审核状态（2026-10-03）

最新明确授权：C1–C6目标已原地更新并恢复执行，C3+C5仍由既有本地窗口承接；独立前端F继续暂停。M已发布规则、完整成果验收与材料责任，资料研究由各Owner接续，不再把中央全量审计设为执行前置。恢复依据是用户明确指令，规则发布本身不代表能力验收。

本轮审核材料：[六轮闭环执行报告](00-GOVERNANCE/evidence/round-15/full-product-audit-20261003/SIX-ROUND-CLOSURE-REPORT.md) · [全仓能力覆盖](00-GOVERNANCE/evidence/round-15/full-product-audit-20261003/CAPABILITY-COVERAGE.md) · [官网调整提案](00-GOVERNANCE/evidence/round-15/full-product-audit-20261003/WEBSITE-ADAPTATION.md)。这些是审计和执行输入，不代表产品闭环；最新执行状态见上方及CURRENT。

### 用户七项修正：需求与研究恢复中（2026-10-03）

上一轮源文件盘点不等于所有窗口历史需求已收齐，官网栏目对照不等于逐篇研究。
全部需求/参考视频/研究材料由材料责任窗口接续逐帧、逐篇研究，M维护唯一规则。四端
UI/UX/AIGC均升级，女孩手绘水彩风格进入前端，保留丰富有用交互，非必要不
纵向滚动。最优解指实现方法的准确、有效、快速，不能缩能力换方便。具体要求
归AGENTS、Experience和Owner Index；C1–C6恢复，F暂停。C2获准按原单卡方案自行续租并训练。

### 当前收口与材料责任（2026-10-03）

M收规则和完整成果验收；视频由F/C4接续，全部资料由对应窗口负责，未读/缺件不删。
[资料责任表及逐条清单](00-GOVERNANCE/evidence/round-15/full-product-audit-20261003/MATERIAL-OWNER-CONTRACT.md)。
视频与播客都必须具备可实际滑动的时间轴；开发者模式按用户最新要求后置，保留来源/责任、不作为本次阻断项。
AI训练列P0，先补实际本地依赖再启动获准算力；不等待全量研究。按用户要求规则
同步后C1/C2/C3+C5/C4/C6用GPT-6.1 Sol/max；M按最新指令用Sol/ultra；F保留手选且暂停。
C2固定原RTX5090单卡按时方案，直接闭合权重/远端执行绑定并开始真实训练；原2026-10-03 24:00截止未达成，继续处理而不改写为完成。4090备选已撤销；失败阻断须保存并停止空转计费。
原生Goal通过官方协议原地更新并读回，预算及已用计数未重置；[目标与恢复回执](00-GOVERNANCE/evidence/round-15/full-product-audit-20261003/EXECUTION-RESUME-20261003.md)。

最新执行口径（2026-10-04）：各窗口采用**最大完整成果执行**，同一用户成果连续完成研究、实现、真实运行、保存/取回、恢复、评价与完整验收；禁止最小执行切片、逐函数交接/核对/报告及无变化的重复审计/测试。Owner/文件/授权边界仍明确，必要真实验证保留。普通依赖由责任窗口和W6直接解决，M只处理完整成果/必要裁决/风险，空闲待命。前端F仍暂停，代码、研究和测试均不恢复。[执行目标回执](00-GOVERNANCE/evidence/round-15/full-product-audit-20261003/COMPLETE-OUTCOME-EXECUTION-20261004.md)。
