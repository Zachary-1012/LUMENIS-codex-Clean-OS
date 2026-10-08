> Status: **CURRENT SUBORDINATE REAL-DELIVERY OVERLAY / NOT A SECOND PRODUCT OR EXPERIENCE AUTHORITY**

> 2026-10-08 PO 正式验收策略变更：单元/集成及换名模块自动测试不再是开发、合并、验收或发布条件，Codex 不新建、不执行这些套件；保留历史测试和 FAILED 证据。当前执行真实任务→既有源码→构建运行→实际用户操作→真实结果→保存/修订/重开→恢复→验收→正式集成。适用编译、静态质量、安全/权限、数据一致性及真实产品 E2E 保留；历史材料中的测试命令不构成当前执行义务，真实缺陷仍必须修复。R01–R15/J1–J8/U01–U25 与 Owner/权益/生产数据边界不变；机器合同 v1.2.0 的 verification_policy 记录现行语义。仅 M 与 C1 本轮恢复；C1 当前指定 GPT-6 Astra / ultra，其余窗口暂停状态按最新直接指令保留。
>
> Authority boundary: this overlay adds delivery evidence and commercial-readiness gates to the six C1–C6 outcomes and retained R01–R15 acceptance coverage. The historical numbered coverage groups below preserve acceptance provenance, not an execution schedule. This overlay does not create another queue, bypass dependencies, replace Product Architecture/Experience, or erase completed source work.
>
> Canonical path: `00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md`.

序境 / LUMENIS
真实交付约束与验收覆盖补充协议
REAL DELIVERY OVERLAY FOR C1–C6 / R01–R15 ACCEPTANCE COVERAGE

REAL USER WORK E2E ACCEPTANCE remains mandatory for each complete C-window outcome and every applicable mapped requirement.

2026-10-08 最新 PO 顺序：先验收 Public Website + Web Workspace 完整适用成果，再处理 Desktop App/Mobile Companion 专项实现、打包及实机验收。使用原 REAL DELIVERY CARD 与三层 Gate，逐项注明本轮适用表面、真实输入/结果/保存修订重开恢复/Evidence/版本和未完成项。官网内容、演示真实性、可用入口，以及 Web 业务正常成功路径必须实际验证；当前 Web 所需 Core/SYSTEM 不能随原生客户端后置。后置两端保留 OPEN/DEFERRED、原 Owner 和恢复条件（官网/Web 闭环），不得以原生包/设备缺失阻塞本轮表面成果，也不得标 PASS、删除 R/J/U 或宣告四端 Goal/整产品 RELEASED。原部署、费用及外部效果授权不变。后续原生目标仅Windows/macOS桌面和iOS移动；Android/Linux原生客户端不再是待交付项，保留历史源码/回执。前端直接构建，独立设计稿/Figma/M设计审批不作为实现前置；原真实结果与质量门禁不变。

本协议约束 C1–C6。旧编号01–15的验收/依赖覆盖材料由六个C成果承接；它不是新的窗口、派工队列或十五段串行执行计划。

分配只见 AGENTS.md，完整映射只见 Source Owner Index；保留真实依赖、全部能力与现有 Product Architecture。
它的目的只有一个：

禁止把“代码完成、测试通过、页面能打开、API 200、Adapter 注册、模型安装、健康检查正常”
误判为“产品已经能交付给真实用户”。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
一、C1–C6统一真实交付验收原则
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

任何一轮的 PASS，必须同时回答下面 8 个问题：

1. REAL INPUT
   本轮处理的输入是真实生产输入、真实业务输入，还是 fixture / mock / sample？

2. REAL OWNER
   本轮结果是否来自唯一 canonical owner？

3. REAL SCOPE
   是否绑定真实 Actor / Subject / BrandFocus / Product / Domain scope？

4. REAL EVIDENCE
   用户看到的事实、数字、结论和动作能否追溯到真实 Evidence？

5. REAL STATE
   缺失、失败、未配置、无权限、无新数据、未知是否被严格区分？

6. REAL ACTION
   如果有操作，它是否真的经过 Permission / Approval / Effect Fence，并产生真实结果？

7. REAL USER RESULT
   这一轮完成后，真实用户到底多完成了哪一件工作？

8. REAL OPERATING EVIDENCE
   本轮能力只是代码存在，还是已经在真实运行环境中验证？

如果上述任意问题无法回答，不得只写 PASS。

必须使用：

PASS
PARTIAL
BLOCKED
LIVE_UNVERIFIED
NOT_CONFIGURED
DEFERRED

之一。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
二、全局禁止的“假完成”
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

以下任何情况都不得单独作为完成证据：

- HTTP 200
- bound=true
- registered=true
- adapter exists
- route exists
- model installed
- provider configured
- cookie file exists
- health_check success
- screenshot renders
- widget test passes
- fixture contains rows
- DB table exists
- API schema matches
- Flutter build succeeds
- CI green
- one manual request succeeds
- empty list returned
- zero returned
- fake demo data
- historical data snapshot
- generated report file exists
- AI produced an answer
- Agent completed a task object

这些最多只能证明 IMPLEMENTED / TESTED 的一部分。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### Current cross-capability result constraints — 2026-10-03

These are acceptance inputs to existing C/R/J/U cards, not another round or queue. Real delivery retains every existing source/permission/result/recovery gate.

- Product-owned collection: distinguish product UI/API/Scheduler execution from assisted discovery and developer harnesses. Continuous operation needs an actual unattended scheduled cycle and truthful failure/recovery evidence, not a successful manual trigger.
- Source-to-creation discovery: real collected results can enter SH-01 Discover and existing CTH/BMP/creation work; evidence-backed trend/hotspot/related-work interpretation and useful owned recommendations must reach a saved/reopened/revised result. Lack of analysis does not erase readable sources, and a model answer alone does not pass.
- Continuous research-to-production work: moving from research/decision into a pitch, video or podcast must reuse the existing task/Brief goal, relevant constraints, selected source/file references, Evidence/locators, selection rationale and exact upstream Artifact/Brief versions through canonical owners. The user must not re-enter unchanged goals, reselect the same materials or manually recheck the same unchanged sources. A common navigation shell or copied summary is not this capability. Preserve each production format's actual required inputs and distinct result acceptance.
- Inherited context does not inherit blanket authority: automatically perform current server-side scope, source-use, permission and integrity checks. Ask the user only for materially missing inputs, actual conflicts, changed scope/purpose or genuinely required approval. Pin the versions used; show meaningful upstream changes and affected outputs. Explicit adoption creates a new derivative version and preserves the prior parent/digest, decisions and content. Never silently overwrite historical work, erase original source provenance, or turn readable material into reusable/training-licensed material.
- Cross-capability acceptance must actually carry one approved real research result into production, revise a relevant upstream constraint, preserve the earlier result, explicitly adopt the change, save/reopen/export and recover from interruption. Record inherited IDs/versions and zero repeated entry of unchanged known input. Verify source withdrawal and task/client/scope changes without context leakage; Clear resets active focus without deleting artifact history or changing historical scope. A disabled AI action, route, standalone tool, fixture or navigation-only check cannot satisfy this acceptance.
- Creative research is extensible: combine cases/methods with current user Brief, new data, brand/venue context and resources. Preserve sources, versions, premises, counterexamples and outcome limits. Do not lock work to twelve mechanisms or merely swap brand names. A permitted adaptation/reuse is distinct from copying a protected work or admitting training data.
- For work involving cost/resource choices, the existing Brief/plan/domain owners retain budget/range, currency, tax basis, market/time, hard cap versus target, contingency and available resources. Unknown is not zero. Quote, estimate, confirmed commitment and actual expenditure remain distinct, with quantities/unit prices, source/date and uncertainty. Do not fabricate current prices or ROI.
- Budget/resources must change the creative and execution plan: production scope, scenes/duration, crew/location/equipment, sound/postproduction/rights, channel/media allocation, schedule and deliverables as applicable. Explain feasible alternatives and trade-offs; preserve non-negotiable safety/rights/quality constraints. Budget changes revise dependent work and saved versions, not only the total. Planning does not authorize payment, purchase or publishing.
- Verify one real Brief under two different budget/resource situations, actual meaningful plan differences and cap consistency; revise, save, reopen and export with stable figures/versions. Unknown prices, infeasible budget and excess have honest states. Actual outcomes/evaluation remain distinct from estimated performance. Pure browsing does not require an artificial budget form.

- Offline audio understanding is part of existing C2/C4/C5 and video/podcast/material work. Validate Chinese, English, Korean and their requested mixtures separately. Retain original-language text, defined word/token units, anonymous within-asset speaker turns when requested, and unresolved/overlapping speech. ASR, technical DSP, speech meaning, direct-audio music/event/vocal-expression understanding and audiovisual relationships have independent coverage and quality. Text sentiment or loudness/beat/pitch alone cannot pass actual listening; untested languages/capabilities cannot disappear from the requested set. No identity, health, personality or actual-inner-state inference.
- Resolve actual authorized audio/video bytes and streams through existing owners. Preserve original channels, source hash/PTS/time base and reversible source-to-analysis-to-timeline mappings; account for downmix cancellation, edits, speed and resampling. Music/event branches retain non-speech audio. Preserve raw zero-duration/uncertain ASR units for review without deleting words or inventing timing precision; accepted aligned intervals must be valid positive ranges. Audiovisual claims require actual corresponding visual evidence. Empty output, raw language scores and small smoke samples are not semantic or whole-project acceptance.
- Persist audio analysis as a versioned derivative with actual input/model/runtime/run and locatable source-range references. Keep source Evidence, rights, current-use authorization, analysis interpretation and review distinct. Existing Evidence/Artifact/Task/Permission owners must admit and recheck the result; no fabricated refs, second store, TaskStatus rewrite or removal of an unavailable-binding guard. A changed source/transcript/channel/edit/model/visual version marks dependent analysis for review while preserving old versions and unaffected work. A subtitle correction alone does not update recorded or rendered audio.
- Prove an actual video and podcast consumption path from inherited task/material/constraints through reviewable listening-based suggestions, a chosen edit, playable export, listening review, saved project, reopen and cancellation/failure recovery. Preserve all earlier visual/storyboard and original-pitch acceptance. Tests include real per-language references, mixtures, noise/overlap, music/singing, different delivery of identical words, silence/no-track/corruption and honest missing capability. Model/software/weight rights, resource limits and network egress remain explicit; a research document's install command or historical remote run grants no new download, paid compute, audio upload or training use. Realtime/microphone work remains deferred.

The existing responsible windows are C2 owned understanding/reasoning, C3 domain decisions/campaigns, C4 original pitch/video/podcast, C5 source/research/versioned Artifact, C1 source facts, F operation/layout and C6 binding/publication. No second budget store, inference service, Evidence owner or permission plane is introduced.


### APPROVED D1–D5 convergence / OPEN ORIGINAL / SOURCE TARGET ACCEPTANCE — 2026-10-06

This approval applies to the current C1–C6/F outcomes and retained R/J/U coverage. It does not add a round, queue or parallel architecture. The subordinate machine contract is `contracts/experience/source-target-contract-v1.json`; it does not create another owner or prove implementation.

**OPEN ORIGINAL / SOURCE TARGET ACCEPTANCE** requires one real authorized platform record to complete all of the following on the same accepted version:

```text
native platform fact
→ Source → Evidence → Canonical
→ task-specific CTH/BMP LUMENIS presentation
→ verified lumenis.source-target/v1
→ explicit user Open Original
→ honest browser-handoff result
→ Return with route/scope/filter/selection/scroll restored
```

Acceptance must prove:

- internal presentation preserves native body/author/platform/time/metrics/attribution and Evidence lineage while using LUMENIS visual and interaction language, not copied source-platform Feed/chrome;
- source URL is server-projected, tied to the same row's Canonical/Evidence reference, restricted to an allowed public HTTPS target and rechecked at use time;
- `URL_MISSING`, `INVALID_URL`, `DENIED`, `UNSUPPORTED`, `LAUNCH_REJECTED`, `LAUNCH_FAILED`, `HANDOFF_ACCEPTED` and `RETURNED` remain distinct; `HANDOFF_ACCEPTED` proves only that the OS/browser accepted the request, not that the original post loaded or was readable;
- the action is a user gesture and has no implicit Cookie/session read, silent login, collection, Evidence capture, Canonical write, publish, purchase or other external effect;
- SYS-06 controlled navigation/capture remains a separate Permission/Evidence action;
- Web, Desktop and Mobile use the same SourceTarget meaning while composing their own interface; Public Website owns no protected source action;
- cancellation, unavailable source, browser failure, app background/foreground and Return preserve or honestly recover the originating task state.

The 51 historical package rows are accepted only through the eight existing-owner result packages in Source Owner Index. Historical candidate data stays quarantined with **Production admission = 0** until current rights/source/identity/scope/Permission/freshness/completeness gates pass. A parser pass, stored archive, URL string, row count or old report never grants Current view, metric, report, Learning or MODEL_TRAIN admission.

Implementation order follows actual dependencies: Truth/Safety first; then Collector/durable task; CTH/BMP business and source trace; Shared result continuity; Owned AI; same-SHA release. F continues independently alongside the one M-selected business Owner; W6 integration occupies that business slot. Dependencies determine handoff order without reducing complete outcomes. Each accepted Batch must publish its source, current contract/evidence and CURRENT status together, then prove local HEAD, `origin/main`, live GitHub main and loaded runtime identity. Documentation-only convergence is not product completion.

三、统一完成语义
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPLEMENTED
= 源码能力存在。

TESTED
= 历史隔离/自动测试证据；不再是当前强制阶段。

LIVE_VERIFIED
= 当前环境下真实输入和真实调用验证成功。

USER_VERIFIED
= 真实用户可以完成目标工作，不依赖开发者解释。

RELEASED
= 适用安全、迁移、回滚、构建、部署、当前 CI 和真实用户 E2E 满足。

OPERATING
= 能力持续运行并持续产生真实结果。

COMMERCIAL_READY
= 用户、数据、权限、运行、支持、恢复和交付全部满足商业使用要求。

任何阶段都不得升级状态词。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
四、每个C窗口都必须生成 REAL DELIVERY CARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

每个 C 窗口完整成果由 W6 汇总、M 验收，同一证据复用到 R/J 条目，不逐文件/旧编号另写报告。Product Owner 工程可操作后统一重复操作；开发期间真实 Job/恢复仍必做，不标 USER_VERIFIED。每个C成果交付：

REAL DELIVERY CARD

C WINDOW / DELIVERY：
CURRENT SHA：

ONLINE DELIVERY / LOCAL-TO-MAIN CLOSURE：
- accepted Batch source paths and exact local commit/remote `origin/main` SHA
- owning C-delivery evidence and CURRENT status published with the accepted source
- fresh live remote main SHA and online file verification after push
- staged/unstaged/untracked protected work still `LOCAL_ONLY`, with owner and next gate
- CI job step count and result; a zero-step billing failure is not test evidence
- if publication fails: `LOCAL_ONLY / NOT_PUBLISHED`, not online PASS

THREE-LANGUAGE SURFACE ACCEPTANCE：
- latest native targets: Desktop Windows/macOS only; Mobile iOS only; Android/Linux native requirements superseded by direct PO, retain history without claiming PASS
- F directly constructs from current contracts; separate design drafts/Figma/M DESIGN_READY approval do not gate coding; actual operation/visual quality/accessibility/E2E and all existing security gates remain
- retain the promised four-surface matrix; current acceptance: Public Website / Web Workspace; Desktop / Mobile native-specific work follows Website/Web closure and stays OPEN/DEFERRED until verified
- `zh-CN` / `en` / `ko` user task, result, error, denied and unavailable copy
- locale switch, persistence, Trace/Return, responsive and accessibility evidence
- missing locale or key remains an explicit screen/surface acceptance gap

GLOBAL UNIVERSE / DATA MATURITY IMPACT：
- GLOBAL CTH maturity impact：本轮责任、已验证、未成熟、后续 owner/round
- GLOBAL BMP maturity impact：本轮责任、已验证、未成熟、后续 owner/round
- Guangzhou Taikoo Hui reference-loop impact：本轮责任、已验证、未成熟、后续 owner/round
- `Global Commercial Coverage = YES / NO / PARTIAL / BLOCKED / LIVE_UNVERIFIED`
- `Global Brand Coverage = YES / NO / PARTIAL / BLOCKED / LIVE_UNVERIFIED`
- `Guangzhou Taikoo Hui Reference Coverage = YES / NO / PARTIAL / BLOCKED / LIVE_UNVERIFIED`
- `LUMENIS_INTERNAL_FULL_UNIVERSE_READY = YES / NO`

RANDOM ENTITY DATA ACCEPTANCE：
- sample seed / sample count / sample IDs
- non-empty valid result rate
- stale / blocked / failed rate
- Evidence trace rate
- empty-state defects
- maturity delta since prior round

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION：
- current business / engineering / page gap
- official sources / industry cases / papers or standards / high-quality GitHub projects / applicable UI/UX flows
- source URL / accessed date / version or commit / license / maintenance / commercial and security boundary
- decision: `ADOPT / ADAPT / DEFER / REJECT`, with reason
- mapping to LUMENIS business objects / Evidence / Permission / workflow / Experience
- versioned capability / Skill / model / configuration / design improvement produced this round
- real E2E / page / effect evaluation / regression / observability / rollback evidence
- if no reasonable improvement applies: `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE`, with evidence

REAL USER：
本轮面向什么真实用户？

REAL USER JOB：
用户要完成什么实际工作？

REAL INPUT：
真实输入来自哪里？

REAL OUTPUT：
用户真正得到什么？

SOURCE：
数据/事实来源。

EVIDENCE：
如何追溯？

PERMISSION：
谁可以访问/执行？

FAILURE STATE：
失败时用户看到什么？

NOT_COLLECTED：
哪些东西当前真实没有？

LIVE TEST：
做了什么真实运行验证？

CONTINUOUS TEST：
是否证明连续运行？

USER ACCEPTANCE：
是否有人不看源码即可完成工作？

EXTERNAL DEPENDENCIES：
哪些依赖代码无法解决？

FINAL STATUS：
IMPLEMENTED / TESTED / LIVE_VERIFIED / USER_VERIFIED / OPERATING

NEXT GAP：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
五、历史覆盖组 01 — Current Truth
作为现行C成果的真实性验收，不单独派工
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

这一历史覆盖不只是“扫描仓库”；其源代码、运行和结果辨别标准适用于每个C成果。

必须最终回答：

- 当前真正存在什么能力？
- 当前真正运行什么？
- 当前哪些只是旧代码？
- 当前哪些只是 Adapter？
- 当前哪些只是 Contract？
- 当前哪些有真实数据？
- 当前哪些有真实用户入口？
- 当前哪些是假的 ready / bound？
- 当前哪些依赖外部凭证/接口？
- 当前哪些数据源完全缺失？

必须建立：

CURRENT CAPABILITY TRUTH MATRIX

每个能力至少标记：

SOURCE EXISTS
IMPLEMENTED
TESTED
LIVE VERIFIED
USER EXPOSED
OPERATING
EXTERNAL DEPENDENCY

禁止仅根据文件存在判定能力。

HISTORICAL COVERAGE 01 ACCEPTANCE：

必须能明确列出：

A. 真实存在且可运行
B. 源码存在但未运行验证
C. 只有接口/骨架
D. Historical
E. Missing
F. External blocked

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
六、历史覆盖组 02 — Authority / Only-One / Compatibility
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

不能只完成文档和命名统一。

必须证明：

- 每个重要能力只有一个 canonical owner
- 每个 compatibility caller 最终指向哪里
- 没有第二套业务真相
- 没有第二套 API owner
- 没有第二套数据 owner
- 没有第二套 Permission / Evidence
- 四 Surface 不复制业务逻辑
- 旧能力没有因为“清理”被删掉

必须生成：

OWNER → CALLER → USER CAPABILITY MATRIX

用户最终看到的每个能力必须可以回溯到一个 owner。

如果一个旧 caller 仍有唯一业务行为：
不得删除。

HISTORICAL COVERAGE 02 ACCEPTANCE：

不存在 UNKNOWN OWNER 的核心商业能力。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
七、历史覆盖组 03 — Database / Canonical Truth
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

不能只证明：

sqlite3.connect = 0
或者 tests passed。

必须证明：

真实数据：

Source
→ Write
→ Canonical DB
→ Read
→ ViewModel

没有出现：

- fixture 污染生产
- test 打开生产数据库
- silent migration
- missing → 0
- duplicated schema truth
- stale DB path
- runtime state 写源码目录
- 数据字段语义漂移

必须选择至少一条真实记录，证明：

RAW SOURCE
→ EVIDENCE ID
→ CANONICAL ROW
→ METRIC / OBJECT
→ USER READ

必须记录：

- DB path
- migration version
- row identity
- source identity
- timestamps
- rollback

HISTORICAL COVERAGE 03 ACCEPTANCE：

数据库不只是“干净”，而是能够承载真实业务事实。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
八、历史覆盖组 04 — Identity / Context / Permission / Evidence
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

必须使用真实权限场景验证：

用户 A
→ 可以访问 Subject A
→ 不可访问 Subject B

用户 B
→ 权限不同

还必须证明：

选择 Subject ≠ 获得授权

选择 BrandFocus ≠ 获得授权

Client Header ≠ 权限

Cookie Session ≠ LUMENIS Actor

每个真实业务 read：

Actor
→ Permission
→ Scope
→ Data
→ Evidence

每个真实 action：

Actor
→ Permission
→ Approval
→ Effect
→ Evidence
→ Return

必须至少执行：

- authorized read
- unauthorized read
- cross-scope read
- missing actor
- missing scope
- permission backend failure
- Evidence lookup
- action denial

HISTORICAL COVERAGE 04 ACCEPTANCE：

不能跨客户、跨 Subject、跨 BrandFocus 泄露。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
九、历史覆盖组 05 — Runtime / Health / Recovery
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

不能只证明 healthz = 200。

必须做真实 failure drill：

- Product Core 崩溃
- Worker 崩溃
- Queue backlog
- DLQ
- Browser 失联
- Collector 失败
- AI provider offline
- DB temporary failure
- Session expired

必须证明：

Failure
→ Detect
→ Honest State
→ Diagnose
→ Recovery
→ Return

并且：

失败不能显示为：

0 data
ready
healthy
empty success

必须生成：

RUNTIME FAILURE MATRIX

CURRENT C6 RUNTIME INPUT / RETAINED R05 COVERAGE：
- Prove canonical Core/approved owned-runtime startup, health, interruption,
  recovery, observability and rollback; a running process is not OPERATING.
- Historical LUMENIS-Ollama-Autostart is retired; do not enable or probe it.

HISTORICAL COVERAGE 05 ACCEPTANCE：

至少一个完整失败恢复流程真实跑通。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十、历史覆盖组 06 — Collector / Browser / Acquisition
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

必须生成：

PLATFORM LIVE CAPABILITY MATRIX

逐平台覆盖：

- 小红书
- 抖音
- 微博
- B站
- 知乎
- Instagram
- Facebook
- X
- 微信公众号公开文章 / Sogou WeChat
- 快手
- TikTok
- 视频号
- RSS
- Public HTTP
- Atom
- Sitemap
- 当前 main 中其他真实 Adapter

每个平台必须记录：

Adapter
Search
Detail
Comments
Creator
Auth
Cookie
Session
Proxy
Provider
Live Connectivity
Real Result
Evidence
Canonical Persistence
Scope
Rate Limit
Risk
Recovery
Continuous Operation

分类只能是：

OPERATING
LIVE_VERIFIED
IMPLEMENTED_LIVE_UNVERIFIED
PARTIAL
NOT_CONFIGURED
PLANNED
BLOCKED
ABSENT

至少所有已有真实实现的平台必须尝试授权 live acceptance。

禁止：

Adapter exists = working
Cookie exists = valid
Health OK = collection works
one success = operating

HISTORICAL COVERAGE 06 ACCEPTANCE：

必须明确知道“哪些平台现在真的能给客户数据”。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十一、历史覆盖组 07 — AI / Agent / Skill Store / Shared Engines
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

不能只证明模型会回答。

必须选择真实业务输入：

真实 Subject / BrandFocus
+
真实 Evidence
+
真实用户任务

验证：

Intent
→ Task
→ Permission
→ Tool / Skill
→ Evidence
→ Artifact
→ Result
→ Evaluation

AI 不得：

- 编数据
- 修改 Evidence
- 修改 Canonical Truth
- 自行授权
- 自行执行高风险 effect
- 将 unknown 写成事实

Skill Store 必须真实走：

Discover
→ Inspect
→ Trust
→ Enable
→ Execute
→ Evidence
→ History
→ Update
→ Disable

至少一个 Skill 必须真实完成业务任务。

CURRENT C2 AI INPUT / RETAINED R07 COVERAGE：
- Retired local-model/Zhipu/OpenCode routes and Jev stay inactive; retain history
  and interfaces, without call/probe/auto-discovery/fallback/reactivation.
- Approved owned weights, real training, held-out useful business outputs,
  multimodal input consumption, tools and resumable tasks are required.
- Preserve model/data/license/scope/version, feedback/evaluation and controlled
  promotion/rollback. Engineering answers never own Truth or effects.
- Reading research, excerpts and unavailable providers cannot close C2.

HISTORICAL COVERAGE 07 ACCEPTANCE：

AI / Agent 是业务增强，不是 Demo Chat。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十二、历史覆盖组 08 — Cross-Surface Experience Foundation
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

不能只把四个 Surface 画出来。

必须证明：

Public Website
Web Workspace
Desktop
Mobile

共享：

- 一个 Product Core
- 一个 Permission
- 一个 Evidence
- 一个 Context
- 一个 State Meaning

同时明确：

什么能力：

WEB AVAILABLE
DESKTOP ONLY
MOBILE COMPANION
PUBLIC ONLY

例如：

Browser / CDP
Cookie / Session
Local AI
File System

不得在 Web 中伪装存在。

必须生成：

SURFACE CAPABILITY MATRIX

HISTORICAL COVERAGE 08 ACCEPTANCE：

同一业务事实跨 Surface 一致，但交互不复制。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十三、历史覆盖组 09 — Golden Pages
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AI-01
CTH-01
CTH-02
BMP-01
SH-01
SYS-01

不能以：

页面漂亮
Flutter test pass
截图正确

作为完成。

每个页面必须回答：

用户为什么打开它？
用户看到什么真实内容？
内容来源是什么？
能点击到哪条 Evidence？
能执行什么？
执行后发生什么？
失败显示什么？
下一步去哪？

至少一个真实用户必须完成：

进入
→ 找内容
→ Trace Evidence
→ 执行一个操作
→ Return

HISTORICAL COVERAGE 09 ACCEPTANCE：

Golden Pages 真正“可工作”。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十四、历史覆盖组 10 — CTH Monitoring / Analysis
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CTH-03..07 必须使用真实新数据。

必须验证：

实时流
事件关系
情绪日历
负面反馈
趋势

所有趋势必须记录：

numerator
denominator
time window
Subject
source
freshness

必须证明：

无数据
≠
采集失败
≠
未采集
≠
0

至少一次真实新事件：

Source
→ Event
→ Evidence
→ Trend / Monitoring UI

HISTORICAL COVERAGE 10 ACCEPTANCE：

用户看到的是“现在真实发生的事情”。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十五、历史覆盖组 11 — CTH Case / Risk / Decision / Report
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

必须真正闭合：

Event
→ Case
→ Insight
→ Decision
→ Action
→ Outcome
→ Evaluation
→ Report

不能只创建数据库记录。

至少选择一个真实 Case：

用户必须可以：

打开 Case
→ 看 Evidence
→ 做 Decision
→ 发起 Action
→ 等到 Outcome
→ 回来查看
→ 生成 Report

如果外部 Action 不能真实执行：
必须明确显示 approval / pending / blocked。

HISTORICAL COVERAGE 11 ACCEPTANCE：

至少一个 CTH business loop 真实闭合。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十六、历史覆盖组 12 — BMP Market / Creator
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

必须选择一个真实 BrandFocus。

从真实来源完成：

Brand
→ Market Signals
→ Competitor
→ Creator
→ Content
→ Evidence

不得：

- 使用全局 aggregate 冒充品牌数据
- 用 Subject 数据改标签当 BMP
- 用测试 creator 冒充真实 creator
- 用不一致时间窗比较品牌

必须记录：

BrandFocus
Market
Competitor Set
Source
Time Window
Metric Definition
Evidence

HISTORICAL COVERAGE 12 ACCEPTANCE：

用户可以真正理解某品牌当前市场位置。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十七、历史覆盖组 13 — BMP Content / Campaign / Podcast / Evaluation
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

必须证明：

Brief
→ Evidence
→ Content
→ Review
→ Approval
→ Campaign
→ Actual Result
→ Evaluation

不能只做“内容生成”。

Campaign 必须区分：

planned
budgeted
launched
observed
measured

Podcast 必须区分：

script
source
audio
version
publish
rights

Evaluation 必须基于实际结果，不是 AI 主观评分。

HISTORICAL COVERAGE 13 ACCEPTANCE：

至少一个真实内容/活动闭环有 Actual Result。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十八、历史覆盖组 14 — Remaining ACC / AI / Shared / SYSTEM
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

80 个任务不能只批量套 UI。

每一个 Screen 都必须有：

USER JOB
REAL INPUT
OWNER
PERMISSION
EVIDENCE
ACTION
FAILURE
RETURN

如果 backend 尚不存在：

页面必须诚实显示 unavailable / blocked。

不得制作：

fake controls
fake charts
fake logs
fake AI thread
fake Evidence library
fake health

必须输出：

SCREEN DELIVERY MATRIX

44 Screens 每个分类：

USER_VERIFIED
LIVE_VERIFIED
TESTED
IMPLEMENTED
BLOCKED
DEFERRED

HISTORICAL COVERAGE 14 ACCEPTANCE：

不存在“看起来能用但其实不能用”的 Screen。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十九、历史覆盖组 15 — 完整产品闭环、发布与运行验收
并入C1–C6及最终产品决策，不单独派工
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HISTORICAL COVERAGE 15 ACCEPTANCE：

这些要求构成完整产品结果的最终“真假分界线”，不是另一个执行窗口或等待所有其他工作的独立轮次。

必须邀请真实用户或非开发参与者。

至少完成以下 Critical Journeys：

1. Public Website
→ Trial / Login
→ Web Workspace

2. Select Subject
→ Monitor
→ Evidence
→ Event
→ Case
→ Decision
→ Action
→ Outcome
→ Report

3. Select BrandFocus
→ Market
→ Creator / Content
→ Campaign
→ Result
→ Evaluation

4. AI Intent
→ Task
→ Evidence
→ Artifact
→ Action

5. Desktop
→ Local Runtime / Browser / Collector
→ Web Result

6. Mobile
→ Notification
→ Review
→ Approval
→ Return

必须使用：

REAL USER
REAL DATA
REAL CURRENT SHA
REAL PERMISSION
REAL SESSION
REAL FAILURE
REAL RECOVERY

不得使用：

demo-only fixture
manual DB injection
developer-only shortcut
pre-populated fake success

同时必须执行：

- clean clone
- install
- migration
- startup
- CI
- Tier C
- security
- backup
- rollback
- performance
- long-run
- device
- accessibility
- failure/recovery
- packaging

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
二十、最终必须输出 7 个最高状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

最后不得只写：

未附具适用状态和证据的“产品已闭环”结论

必须输出：

Global Commercial Coverage =
Global Brand Coverage =
Guangzhou Taikoo Hui Reference Coverage =
LUMENIS_INTERNAL_FULL_UNIVERSE_READY =

ENGINEERING_READY =
REAL_DATA_READY =
USER_WORKFLOW_READY =
SECURITY_READY =
RELEASE_READY =
OPERATING =
COMMERCIAL_READY =

先按 `LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md` 判断同一内部全量版的三个支撑维度。只有 `Global Commercial Coverage`、`Global Brand Coverage` 与 `Guangzhou Taikoo Hui Reference Coverage` 全部为 `YES`，唯一顶层结论 `LUMENIS_INTERNAL_FULL_UNIVERSE_READY` 才能为 `YES`。三项不得产生独立产品、版本、仓库、入口、发布轨道或 Data/Evidence/Permission/API/Context；广州太古汇单点成功、页面非空、目录存在或几个平台有数据都不能替代全球覆盖证明。

随后只有最终七状态全部 YES：

才允许写：

LUMENIS CLOSED-LOOP DELIVERY = COMPLETE

如果任意一个 NO：

必须输出具体 blocker。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
二十一、最终真实数据标准
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

至少一条真实数据必须完整证明：

External Source
→ Raw Capture
→ Evidence
→ Canonical Data
→ Subject / BrandFocus
→ Function
→ Metric / Event
→ ViewModel
→ User Surface
→ User Action
→ Outcome
→ Evaluation
→ Learning

每一步必须能定位：

owner
ID
timestamp
permission
source
state

否则不得称为 Production Truth。

本节真实数据链服从 `LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md`。每个相关C成果分别报告 `GLOBAL CTH maturity impact`、`GLOBAL BMP maturity impact` 与 `Guangzhou Taikoo Hui reference-loop impact`；完整产品发布验收只按当前SHA复核，不把未接受的历史实现堆到最终门槛。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
二十二、最终商业交付标准
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

最终商业能力清单只能包含：

OPERATING 或 LIVE_VERIFIED 且已通过 USER_VERIFIED 的能力。

不能把：

PLANNED
IMPLEMENTED_LIVE_UNVERIFIED
NOT_CONFIGURED
BLOCKED
DEFERRED

写入销售可用功能列表。

每个数据源、平台、AI Provider、Skill、Screen、Workflow 都必须有真实状态。

R01–R15 remain the complete acceptance/dependency coverage mapped into six
C1–C6 outcomes; they are not 15 separately activated dispatch rounds. Current
window activation and pause state come only from the top of `AGENTS.md`. Apply
the `REAL DELIVERY CARD` when an owner is formally activated; do not infer work
from a numbered R checkpoint or a historical charter. Preserve valid completed
source and re-use same-content evidence without treating it as user acceptance.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
二十三、全局商业交付补充红线
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Whole-product completion condition: 以唯一 Source Owner Index 和 Real Delivery Overlay 维护的全产品已确认功能清单为验收全集，覆盖 CTH、BMP、全部 Shared/SYSTEM 能力和四端；保留 R01–R15、J1–J8、原六专项的每项义务。C1–C6 是完整任务分工，不能把六专项、少量代表样本或当前已实现子集当作产品全部功能。所有本轮应交付功能必须具有实际正常路径、真实有用结果、适用的保存/重开/Evidence/Evaluation/恢复证明；任一项未完成或缺少适用证明，不得宣布产品闭环。失败/缺失状态的正确呈现是必要质量要求，本身不通过该功能的正常结果验收。仅 Product Owner 已明确后置的事项单列保留，执行者不得自行遗漏或后置。

Product Owner clarification (2026-10-02): 本轮工程/产品闭环必须完成冻结范围内真实、可用、可重复的功能与用户结果；商业授权采购、商业再分发许可和平台合作谈判后置，不得仅因这些商务事项未完成，把整项能力降为 helper、演示、禁用控件或 unavailable 并称为闭环。沿现有 owner 使用当前可用且允许的来源、自有/许可合适的素材和组件，完成真实输入→有用产物→保存/重开→Evidence→Evaluation→恢复。具体访问授权、账号边界、源用途与第三方代码/模型许可继续按实际条件执行；若某个承诺的专有字段/动作确实依赖未获授权，仅将该明确能力记录为未完成，不得伪造或用另一来源冒充。商业合作缺口单列 COMMERCIAL_READY，真实工程缺口仍须修复并如实保留。保留官方接口，未来授权后通过实际联调、范围/质量/限额及恢复验证再升级，不能预设授权自动保证能力完整。

以下六项是C1–C6共用的横向约束，不新增执行轮次或任务队列。它们不耽误与其无冲突的产品能力交付；每个C成果在相关canonical owner范围内建设并记录差距与证据。外部账号、商业授权、合规确认或上线前运营准备尚未完成时，必须记录为 `COMMERCIAL READINESS GAP / BLOCKED FOR COMMERCIAL_READY`，不得误写成当前工程能力失败。完整产品发布决策由Product Owner依据全部适用C成果、R验收与真实用户任务统一审核。

1. DATA GOVERNANCE / COMPLIANCE

每个外部 Source 必须记录合法来源、授权方式、允许用途、数据保留期限、删除/退出路径和合规边界。“技术可采”不得自动等于“商业可用”。

2. SECRET / CREDENTIAL GOVERNANCE

不得存在生产默认密钥、固定个人凭证、真实 Cookie/Token 入库或入 Git。必须具备注入、轮换、失效、恢复和审计路径。

3. CONTRACT / VERSION COMPATIBILITY

每个 Web/Desktop/Mobile consumer-facing API/ViewModel 只能有一个 canonical owner/schema/error/state contract。升级必须验证 backward compatibility 或明确 migration。

4. DATA RETENTION / BACKUP / DISASTER RECOVERY

必须验证 retention → backup → restore → rollback → deletion，且恢复后 Evidence / Canonical lineage 不断裂。

5. TENANT / WORKSPACE LIFECYCLE

商业化前必须验证 Customer/Workspace 创建 → Subject/BrandFocus 配置 → Member 加入 → Permission → 使用 → Member 移除 → Access Revoke → Customer Exit / Data Cleanup。

6. COMMERCIAL OPERATIONS

`COMMERCIAL_READY=YES` 前必须存在并验收 onboarding、support/escalation、upgrade/migration policy、service status、usage/quota/entitlement、release communication、rollback/support path。

上述任一项为 BLOCKED，最终不得输出 `COMMERCIAL_READY=YES`。任何一项未闭合，只能令 `COMMERCIAL_READY=NO`，不能由 `ENGINEERING_READY`、`RELEASE_READY`、CI 绿色或其他状态替代。不得把真实密钥、Cookie、Token 或个人凭证复制进协议、日志、源码、测试、Evidence 或提交历史。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
二十四、持续前沿研究与能力演进门
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

每个活动 Owner Task Card 与 M Acceptance 必须包含 `CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION`。研究是本 Overlay 下的交付证据，不是第二产品、架构、设计或研究权威。每个C成果必须先记录当前业务/工程/页面差距，再核验与本轮直接相关的当前官方资料、行业案例、论文/标准、高质量 GitHub 项目及适用产品交互；保存 URL、访问日期、版本/commit、许可证、维护状态、商业可用性和安全边界，并作出 `ADOPT / ADAPT / DEFER / REJECT` 决策。

涉及页面的C成果必须主动研究当前前沿、原创、非模板化体验，且不得把 Toss Shopping、KakaoTalk Channel、Toss Design System、`motion-web` 或任何后续样本当作白名单或范围上限。外部输入只能提炼原则；禁止复制布局、视觉身份、代码、资产、参数、交互序列或受限衍生工作流。禁止 AdminLTE/Tabler 式通用后台、通用 Dashboard、Bento、Card Grid 批量套屏。只有长期 canonical 原则才可更新唯一 `LUMENIS-EXPERIENCE-CONSTITUTION.md`；研究记录、截图、Figma、模型输出和 GitHub star 都不是设计权威或 Production Truth。

Collector、Browser、AI、Content、Agent、Reporting、Evaluation、Learning 与 CTH/BMP workflow 依据真实 Evidence 持续演进。候选改进必须映射回 canonical owner、对象、Permission、Evidence、workflow 和 LUMENIS Experience，并经过版本化资产、适用构建/静态质量/安全/数据检查、真实运行/E2E、效果评估、可观测性、回滚与 M 验收后才可晋级。注册、import、模型输出、论文结论或外部项目活跃度都不能直接成为产品能力。

研究输入必须走一条双出口但不双重建库的能力进化链：`真实任务/缺口 → 定向检索 → 来源/时效/权利/可靠性核验 → 蒸馏`，随后分别进入 **PRODUCT ADOPTION** 与 **MODEL LEARNING CANDIDATE**。PRODUCT ADOPTION 只能增强当前已经批准的能力，并落实到现有 Owner/Contract/Experience，记录 `ADOPT / ADAPT / DEFER / REJECT` 及真实验证结果；MODEL LEARNING CANDIDATE 仍需经过 C2/C5 现有 rights/privacy/quality/held-out/Evaluation/Promotion 边界，不能因为同一资料已被产品采用就自动获得训练资格。真实运行后的 Outcome/Evaluation 必须反哺 Research/Learning，形成“真实世界 → 产品 → 结果 → 学习 → 下一轮产品”的闭环。

能力进化允许提高现有能力的行业理解、数据覆盖/新鲜度、判断深度、grounding、创作/多模态质量、操作效率、可靠性、恢复能力和表达质量；不得以“进化”为名新增未批准功能、第二 Owner/真相栈或外部效果。若候选改进不能对当前 Job 产生可验证的实质提升，或会在没有验收收益证据的情况下拖延闭环，则记录 `DEFER` 并继续当前闭环；持续研究不能成为永久保持 OPEN 的理由。

若本轮研究后没有适用升级，仍必须记录 `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE` 和拒绝/延后证据；不得省略研究门。外部账号、许可证或商业授权不清仅阻止对应采用，不得拖延无冲突研发。

## Product Owner full-scope correction — 2026-10-03

Acceptance remains full C1-C6/R01-R15/J1-J8/U01-U25 plus every unretracted user
requirement supplied to M, the six delivery roles and F. Optimal execution is the
best accurate, effective, feasible method for those fixed outcomes, selected from
current GitHub/official/frontier and real-product evidence before implementation;
it is not the easiest smaller capability. Reuse valid evidence, avoid unrelated
tests/candidates and retain meaningful failure/recovery verification.

Four-surface creative UI/UX/AIGC, rich useful interaction, no unnecessary vertical
scrolling and the user's watercolor/hand-drawn reference are acceptance dimensions
under the sole Experience Constitution. Every supplied reference video requires
frame-level coverage and adoption decisions;12 production exercises do not replace
the larger historical reference corpus. Research must improve applicable product
capabilities as well as approved model learning. A source file inventory, fetched
webpage, storyboard, test or example cannot prove those requirements completed.

The official-website research requirement is article-by-article, including support,
instructions, documentation and release logs, all discovered historical/language
variants and accessible relevant login pages. Maintain an explicit URL universe,
actual retrieval/read coverage and adaptation decisions. Authentication, robots,
access denial and missing pages remain real gaps, not permission to bypass or
silently sample. Index/navigation/category review alone is incomplete.

## Execution completeness and retained-material acceptance — 2026-10-03 closeout

For every unretracted user requirement and supplied material, retain its original
source, main/supporting Owner, interpretation and later corrections, C/R/J/U and
surface mapping, research/adoption state, implementation path/version, actual
normal outcome, failure/recovery and remaining blocker. Assignment or storage
does not mean read, frame-reviewed, implemented or accepted. No silent omission,
summary-based scope cut, arbitrary sample cap or unacknowledged transfer is valid.
Material corpus completeness is checked against the recovered source inventory,
including missing and second-level references, not only today's direct URLs.

Accept a complete C outcome only when the promised normal job works with real
permitted inputs, task/material/scope/budget/versions continue across research,
decision and production, the actual effect/result is evidenced, saved artifacts
can be located/revised/exported/reopened where promised, and meaningful interruption,
revocation/denial/cancellation/restart paths pass. Every promised interface/device
is included. Honest UNAVAILABLE remains an unfinished capability, not a substitute
for the normal path. Required shared contracts and existing gates stay blocking;
reuse valid same-content evidence and do not rerun unrelated tests just to count.

Video AND podcast acceptance includes actual horizontal timeline interaction,
pan/seek separation, ruler/track synchronization and unchanged project truth under
view-only panning. Developer mode is DEFERRED_BY_USER and is not a gate for this closeout; retain
its source/Owner and revisit only when later authorized. Its deferral does not
defer timeline interaction, research ownership or the other agreed capabilities.

AI training acceptance requires the approved actual model/data/resource route,
optimizer steps/loss, durable checkpoint, reload/resume and independent held-out
results before Gateway/business quality and controlled promotion. Cached weights,
CPU simulations, tests, recipe/manifest presence and rented GPU time are not
training. Ready local prerequisites precede billing; record first-step evidence,
actual cost and failure stop/recovery. Whole corpus review is not a prerequisite
for the already approved training-pipeline inputs or unrelated business work.

At convergence verify the exact integrated source/runtime/model/build/DB identity,
required same-SHA hosted gates, four-surface continuity and recovery/rollback.
Product Owner repeat operation remains the final human gate after engineering is
ready; research, technical proof, USER_VERIFIED, RELEASED and OPERATING are separate.
M checks completeness once per full outcome, owns necessary cross-owner repairs,
and receives complete results/necessary decisions/urgent risks rather than every
function or ordinary research progress message.

The Product Owner's 2026-10-04 complete-execution correction requires each
window to continue its whole accepted delivery contract through actual results,
not serial minimum function slices. Do not insert per-function M approvals,
unchanged handoff checks or progress-only reports into that path. Existing
owners coordinate dependencies directly; preserved valid evidence and required
affected recovery/security/E2E gates still apply. F follows the newest Product Owner dispatch; M may audit its source and contracts
for the authorized convergence without resuming F's implementation. C2
prioritizes existing/free compute; no GPU SKU is preselected by this Overlay.
Paid compute requires current explicit cost authorization under AGENTS.md;
historic 4090/5090 proposals and leases are evidence only.


## Normal success and change continuity — 2026-10-04

Actual permitted material enters an actual user task and produces a useful,
editable result that can save, revise, independently reopen and recover. The
executing main/overlay/build/process/DB/model/recipe/token-budget/input/Evidence/
Artifact versions must agree. A locally accepted candidate, old evaluation path
or document/test/HTTP/manifest cannot substitute for that executing version.
Keep Source truth, analysis, human decision and production effect distinct.

Require the six combination results in the Source Owner Index: purpose-bound
collection answers a business question; Task/DOCX/SavedWork retry/cancel/parent
versions work; research Brief/source/context survive creation formats and
constraint edits; remote training/physical Artifact repeat/recover/evaluate/
promote/rollback; localized editing preserves the whole work; source corrections
locate and revise all related conclusions and works without overwriting origins.

An allowed nonempty brief_ref/evidence_refs must travel through the normal
source-use contract into useful analysis/creation. If it still produces
INTERNAL_PITCH_SOURCE_BINDING_REQUIRED, this is an unfinished binding, not
acceptance of 'research→AI pitch'. owned_model_execution=NOT_RUN cannot establish
owned analysis. Internal Word/DOCX/SavedWork composition can prove its own
bounded behavior but not that missing normal research/owned-AI path. For an
F-owned screen, the required real submission must be operable; an onPressed:null
editor/entry is not a completed action. M's bounded source audit does not prove
F's implementation or user-flow acceptance.

Domestic semantic quality must distinguish same-named commercial entities,
cross-city shops, current versus historical claims, brand self-description versus
consumer feedback, and advertisements versus organic discussion. Evaluation
checks those distinctions in the final task result, not merely Chinese labels.
Compare with peers/manual workflows on the same materials, task and budget:
record correctness, editability, human remedial effort, elapsed time and cost;
no claim of outperforming Meltwater/Brand24/YouScan follows from architecture.

The complete reusable business path is one brand/commercial job → the same
time/scope-bearing materials → budget/resource-constrained alternatives →
editable text/video/podcast outcomes → source/budget change → locate the affected
claims/sections/scenes/audio/budget decisions → explicitly adopt the new version
and revise affected parts → preserve old work, reasons and a usable rollback.
The existing Evidence/Trace/Artifact/SavedWork/Task/Evaluation owners maintain
these dependencies and version lineage; no second impact-truth store is created.
Corrections are appended/linked rather than rewriting source Evidence. Changed
constraints retain the user goal/context and unaffected valid portions; external
effects still need fresh permission/fences and do not silently replay on reopen.

Prioritize actual remote training/step/loss/checkpoint bytes/load/cancel/connection
loss; consistent training and Gateway recipes/budgets; true research→creation
source transfer; semantic queries in actual capture/refresh/recovery; same-version
integration/environment reproduction; and four-surface operation when F's
separately authorized deliverable is reviewed. These are retained product gates,
not current task activation commands.
These are complete outcome obligations, not activation commands. The Product
Owner has authorized M, independent F and one M-selected business window at a
time under AGENTS.md; other business windows preserve their full outcomes and wait.
Actual local dispatch/admission follows the live ledger and real tool receipts;
each window enters RUNNING only after fresh admission. A real dependency blocks
only its affected path. When an owner is active, it
continues the whole outcome rather than safety refusal or per-function reports.
Original six-window/R/J/U/special exits, global data construction, real
outcome/Evaluation and final human repeat gate remain without shrinking useful
normal-path standards.


### Frontend result acceptance under F's independent authorization

Consume the single consolidated mapping in Experience section 38 through F1–F5
and the existing owners. Each promised surface must prove the real task, input,
per-purpose authorization, source/version, editable saved result, return and
recovery in this Overlay's acceptance card. Distinguish frame extraction from
actual reading; F's corrected 319b evidence leaves unread intervals open until
its new receipt. Existing test/build/mount reports retain their exact versions
and cannot prove the newer four-surface implementation or user acceptance.


### Retained release and recovery obligations

The retired RELEASE_AND_AUTORUN_GATE adds no execution authority. Its still-valid
obligations remain here: trusted configuration, deployment routing and target
runtime health, explicit collection enablement, last-success evidence, bounded
recovery/cooldown, permission before external effects, and a stoppable release
with rollback that preserves Evidence. A green repository gate is necessary
but not proof of target-runtime operation. No historical fixed schedule or
external document grants collection or deployment permission.

## 2026-10-08 双层正常成果验收与成熟基础能力

本节补充现有 REAL DELIVERY CARD，不新建任务编号、验收队列或机器治理状态。Product Owner 已授权 M 与独立 F，以及 M 按现有依赖选择的唯一业务窗口继续完整既有成果；其余 C 窗等待并保留源码/Goal，W6集成占用同一业务席位；实际派发/准入以本地ledger和真实工具回执为准，各窗 fresh admission 后才进入 RUNNING，再按原完整成果执行本节要求。

每个原有J1–J8/U01–U25能力行记录 `capability_observation`：`ALREADY_WORKING`（真实操作证据）、`SOURCE_ONLY`、`UI_ONLY`、`PARTIAL`、`MISSING`、`BLOCKED`（确切外部依赖）、`PO_DEFERRED`（明确PO出处）。同时记录当前源码/调用/运行差距、复用或修复对象、材料采用位置和下一动作。该字段描述能力观察，不能代替治理机器合同的 completion ladder 或 LIVE_DISPATCH。旧报告/附件计数和SHA只是其时快照，不能直接标成当前状态。

在现有卡增加两组证据及共同版本清单：

1. **基础操作层**：普通用户从真实入口，选择/导入/搜索/筛选/编辑/撤销/保存/预览/导出/重开/恢复，完成该Job承诺的常规成果。必须给真实输入、实际操作、可读取/播放的输出、持久化父版本及错误恢复，不能用源码、Widget、Demo、文件存在或测试计数取代。
2. **序境增强层**：在同一任务继续使用Scope、时间、预算、Source/Evidence/Canonical和引用；研究进入创作无需重述Brief或重选资料；分析/建议与实际执行分开；源或约束变化定位受影响范围，经明确采用形成新版，保留未变部分、原因、旧版、回滚及Evaluation。两层均有证据才关闭原Job。
3. **统一回执**：材料/授权用途、模型/配方（如实际使用）、主线SHA+受保护overlay/构建/执行进程/DB/API、Artifact/项目/Timeline版本、验证时间及局限匹配；Product/App Gate、Critical E2E、Runtime、Production DB、USER_VERIFIED各自报告。原有效证据可复用，不为统计数量重跑。

| 原成果 | 必须完成的普通操作验收 | 增强与失败恢复 |
| --- | --- | --- |
| J5 视频 | 授权真实素材→导入/缩略图→剪辑/横向时间线/播放头→字幕和多轨音频→预览→可播放导出→正式保存→关闭→重开再编辑；核对时间码/音画同步/分辨率/采样率/体积 | 编辑预览/临时导出/正式保存/重开分开；Undo/Redo后导出与可见版本一致；缺媒体/取消/失败可恢复；素材Evidence/rights不绕过；已批准分层任务如被单视频轨阻挡由现有renderer补齐 |
| J6 播客 | 导入或明确授权录音→真实声音/Seek→真实样本时间码波形→删一段/配乐/音量/混音→可听导出→保存关闭→重开局部修改再导出；录音路线另验许可拒绝/暂停/停止/实际文件/中断 | P0播放→波形→录音→编辑混音；P1降噪响度/转录→脚本声音关联。顺序是依赖，不是删减；适用OS未验证保持OPEN。人工转录可独立用；ReadAloud/静态Plan/随机波形/静音测试音频不算交付 |
| J1/J2/J3 | 真来源检索过滤排序详情分页刷新；真主体/品牌范围、可比指标/趋势、事件/Campaign、保存报告/导出/历史 | UNKNOWN非0，城市/时点/样本/广告与自然内容分清；原文和引用可回读；实际动作与Outcome证据独立 |
| J4/J7/J8 | 文稿预算编辑/审阅/版本/Word重开；材料定位引用/Skill管理/任务取消恢复；四端输入导航/设置通知/无障碍及任务恢复 | 同Brief和引用进入现有SavedWork；Agent checkpoint和效果不重复；设备/权限差异真实表达，界面不要求普通用户理解研发术语 |

对标在相同材料、任务、约束及设备条件下记录：成果正确性、误改/丢失、重复输入、人工补救、等待、步骤与恢复时间；没有实测不宣称提效百分比。GPT启发任务适配的直接交互，Apple启发可预期可撤回的控制与反馈，Tesla启发有状态的操作、偏好保存/恢复；这些是原体验的验证视角，不增加汽车能力、账号壁垒或新的批准权威。用户可选操作必须可达，减少无意义步骤不等于减少交互/功能。

### 2026-10-08 采集验收补正

采集能力完成与数据全部非空分别验收，不要求获取所有客观不可得的数据。保留准确维度，缺值显示“—”并带可查看的现有状态/原因/来源及核验时间，真实0保持0；解析缺陷/未执行/权限失效不因横杠通过。真实授权正常链、正式准入、连续刷新及恢复仍是能力门槛；业务结论必要证据不足仍不可用。取消全局固定历史起点，按话题任务采集、原始出版/事件时间组织、显式时间范围过滤；未知日期单独诚实处理。Global§10为详细合同，已定位旧日期源码待后续C1/C6实施，不把本次规则发布算新运行策略上线。

### 2026-10-08 智能UI的有用分段验收

沿已有J1–J8真实任务核对：第一个有用且有依据结果→后续新增信息→必要更正与全答一致→直接调整→明确保存→重开/断线恢复。分段不能只是状态提示或完整响应后的打字动画。检查旧run晚到、乱序/重复块、权限或输入版本改变、用户已编辑块保护和局部格式失败；不得重复效果或将部分结果升为完成。缺值维度遵守Global §10且不降低必要业务证据。

同时记录首个有用结果、首个可操作块、完整结果与保存耗时，事实/引用错误、总成本和人工补救；在同任务/资料/预算比较，不能以短等待牺牲准确性或完整成果。各Owner只运行其实际影响的检查；App/CI通过不等于真实用户任务或四端逐步交付已验收。

### 2026-10-08 产品电脑操作与浏览器真实验收

沿既有J1/J7/J8、U21、SYS-06及各Owner完整卡验证，不新增平行验收体系：

1. **产品独立运行**：从序境真实任务发起→产品自己的进程执行→观察、实际click/input/scroll或获准OS动作→核实结果→回执/Evidence→原任务消费。停止Codex开发操作后路径仍可用；录像/测试替身/操作描述/开发CUA代点不通过。
2. **三操作端实际路径**：手机任务内视口、触控键盘、当前动作、接管/停止和返回；Desktop/Web默认内置浏览；用户显式外部打开与返回单独验证。站点拒绝iframe不是弹外部即通过的理由。
3. **控制与恢复**：Agent和用户不得同时抢输入；旧frame/target/revision、旧run、撤权、断线、超时均不得向新目标送动作或重复效果；重连确认实际状态，历史事件不标Live。关闭视图不假称任务终止；实际取消需服务端回执。
4. **OS能力单验**：至少在当前承诺并具备设备的目标系统，用获准应用/文件完成完整真实任务并证明停止/恢复与边界；CDP/browser成功不能替代OS执行器。其他未验系统保持OPEN而不删承诺。
5. **安全与结果**：不得曝光/转移Cookie、秘密、个人档案、raw CDP；敏感提交及外部写入仍走现有批准。页面打开、动作已执行、Source保存、业务结果、USER_VERIFIED分开，不凭Live徽标或HTTP200判完成。

记录同Task/actor/scope、目标/控制权、源码/运行版本、动作与新画面、取消/恢复、Source/Evidence/Artifact回执及真实端环境。原有效门禁可复用，仅补受影响验证；M验收完整结果。
