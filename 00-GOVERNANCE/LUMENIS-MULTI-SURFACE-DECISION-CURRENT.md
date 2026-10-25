# LUMENIS Multi-Surface Decision — CURRENT

> Status: **PRODUCT OWNER APPROVED / ARCHITECTURE DECISION**
> Approved: **2026-09-21**
> Applies from: **ROUND 02**
> Product Architecture authority: `LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`
> Experience authority: `LUMENIS-EXPERIENCE-CONSTITUTION.md`

This decision records how the approved commercial surfaces are delivered. It is not a second Product Architecture, Experience authority, data owner, runtime owner, or completion claim. Current executable source and runtime evidence remain authoritative.

The Product Owner also accepted the ROUND 01 audit and missing-capability register on 2026-09-21; its 15-round coverage is a historical audit index, not the product delivery sequence. C1–C6 retain engineering source responsibilities, and F retains frontend ownership. These roles do not establish current dispatch, a fixed local/Cloud split or a concurrency limit; actual dispatch follows the latest direct PO instruction and verified live evidence. The earlier approval is a coverage baseline, not implementation from the audit PDF or its sketches. All generated visual
artifacts remain `DESIGN_EXPLORATION` until the sole Experience authority and a
current detailed screen specification establish `DESIGN_READY`.

### 当前端范围：既定四表面，按设备条件独立验收

当前优先完成Web Workspace与Windows Desktop的真实产品工作；Public Website后置，不作为产品开发、运行或工作流闭环的前置；macOS/iOS保留完整角色和合同，待设备及后续PO指令后实施，按本端真实任务、运行、恢复与适用验收独立记录。Website使用既有`website/`；Workspace/Desktop/Mobile共用单一Flutter `app/` 和同一Product Core。直接建设任务化完整前端，不等待全部后端；已有真实API/Core立即接入，缺失行为沿现有Owner逐项连接并保持OPEN/UNBOUND，不用模拟结果。44份现有ScreenSpec是覆盖基线，不是页面或产品范围上限。保留全部R/J/U、官网内容家族、原件/源码/设计/回执；一个表面通过不代表其他表面或整产品通过。此规则不派发窗口、不更改实际调度或零新增付费边界。批准依据：`evidence/approvals/PO-20261011-WHOLE-PRODUCT-REUSE-EXPERIENCE.json`。

四个表面各自交付其既有角色适用的完整真实任务、研究/业务/创作、来源和权限、成果保存/修改/重开/恢复/评价。已存在的Core/API均直接接入；其他依赖由对应Owner继续，不因表面排期或客户端类型而遗漏。官网展示不得夸大能力，Web不使用模拟后端或桌面端跳转代替已批准能力。手机浏览器窄屏属于Web响应式验收，不等于原生Mobile Companion。

按既有Gate分别验收四个表面；每端的Goal/任务闭环只由本端真实证据支持，跨端一致性及整产品Release仍需各自适用证据，不能由单端自动宣告。部署、费用、身份和外部效果的授权边界不变。2026-10-08 Website/Web-first回执仅为历史记录，当前设备执行范围按2026-10-23直接PO修正，四表面角色批准仍见：`evidence/approvals/PO-20261011-WHOLE-PRODUCT-REUSE-EXPERIENCE.json`。

F依既有Experience/ScreenSpec/真实合同建设当前获派表面并保留其余表面的完整合同，不先做独立设计稿，不等待Figma或M的DESIGN_READY前置审批；必要设计决定随代码回写原规范。既有设计/审核状态只记录实际评审，不等同真实用户验收。原生目标为Windows/macOS与iOS；Android/Linux原生客户端已移出交付要求，原件/源码/旧构建证据保留为历史。Linux服务端/CI、各操作系统浏览器与窄屏Web不受影响。已有真实API/Core立即接入，缺失合同/行为按原Owner标OPEN/UNBOUND。批准依据：`evidence/approvals/PO-20261011-WHOLE-PRODUCT-REUSE-EXPERIENCE.json`。

最新直接PO执行调整：先完成Web Workspace与Windows Desktop的产品能力、视觉和完整工作流，再完成Public Website全部内容家族、真实演示、帮助与入口；官网未完成保持OPEN，不阻塞产品两端有界验收，也不能据此宣称完整四表面已交付；因没有设备，macOS与iOS暂不实施、不作通过声明。四表面产品范围及共享合同保留，有设备并获得后续指令后继续对应实机验收。共享源码须保持暂缓端的合同兼容，不以未执行的设备验收宣称通过。

## 1. Approved product-surface structure

```text
ONE Product
ONE Repository / main
ONE Product Core
ONE Canonical Data
ONE Evidence
ONE Permission
ONE Runtime Ownership
ONE AI Gateway / Agent Runtime
ONE API / ViewModel Contract
ONE Experience / Design Authority

MULTIPLE EXPERIENCE SURFACES
├─ Public Website
├─ Web Workspace
├─ Desktop App
└─ Mobile Companion
```

The surfaces may recompose navigation, density and interaction for their devices. They may not redefine business objects, state meanings, Permission, Evidence, workflow outcomes or Production Truth.

## 2. Product boundary by surface

Latest 2026-10-12 PO: entering an operational workspace opens the existing conversation/task home directly, with navigation to the other existing architecture capabilities. Reuse ACC-03/AI-01 and one draft/task/result contract on Web, Windows/macOS and iOS, recomposed for each approved surface role. The conversation adopts verified applicable GPT/Grok Bot operation and Intelligent UI principles in the original LUMENIS visual language. Public Website retains its own truthful introduction/help/workspace-entry role. Chat is not a model prerequisite for independent normal business, research or creation. Actual default routing, conversation operations and return/recovery require per-surface runtime acceptance.

| Surface | Product role | Permitted capability | Hard boundary |
| --- | --- | --- | --- |
| Public Website | Commercial introduction and acquisition | Product/domain explanation, industries and use cases, customer cases, truthful demo, trial request, enterprise contact, help, login/workspace entry | No Production Truth, operational workflow, privileged action, Canonical Data owner or client-side provider secret |
| Web Workspace | Primary commercial workspace | Authorized Subject/BrandFocus selection; CTH/BMP/AI/Shared/SYSTEM workflows; Evidence Trace; Case/Insight/Decision/Action; reporting/export; collaboration, approval and light configuration | Uses canonical Product Core/API/ViewModel; must not recreate local Cookie/CDP/filesystem/local-AI capability in the browser or simulate a desktop result |
| Desktop App | Power User Client | Full workspace plus local Browser/CDP, Cookie/session, Collector, long-running tasks, local files, approved owned AI capability, enterprise LAN/private deployment, recovery and advanced execution | Desktop-only capability remains behind SYSTEM Permission/effect fences and explicit capability state; it does not create separate business truth |
| Mobile Companion | Timely review and light action | Notifications, events, AI results, approvals, task state, report reading and bounded quick actions | Not the primary dense-analysis or local-execution environment; unavailable capability is shown honestly and may hand off to an authorized Web/Desktop task |

### Four-surface upgrade requirement — 2026-10-03

All four surfaces receive the approved creative UI/UX/AIGC, reference-informed
and interaction upgrades under the Experience Constitution. Painted style
applies to original icons and suitable page elements; overall visuals follow
the PO-selected pixel-cyber, botanical-ecology and retro-futurist style and existing task needs.
The roles above constrain actual execution and data ownership, not design ambition
or which surface receives improvements. Device-appropriate composition preserves
the user's capabilities and continuity; it does not justify a generic thin shell,
reduced interaction or ignoring Website/Mobile. Record each requirement's concrete
entry, behavior, state and verification on every applicable surface, including a
real handoff where the runtime capability is device-specific.

## 3. Approved technical route

The approved route is hybrid and keeps one Product Core:

```text
Public Website     SEO-capable independent presentation deployment
Web Workspace      Flutter Web target from the existing app/ codebase
Desktop App        Flutter Windows/macOS targets from app/ (current PO device scope; independent acceptance)
Mobile Companion   Flutter iOS target from app/ (current PO device scope; independent acceptance)
Product Core       existing Python/Flask canonical API and runtime owners
```

`website/` now contains a committed trilingual Public Website foundation (`77648c3b`, 2026-09-23). Its commercial destinations remain unconfigured; this is not proof of deployed acquisition or ROUND 08 acceptance. The root may contain presentation and acquisition integration only. It must not own CTH/BMP/Shared/SYSTEM workflow logic, production persistence, Permission or Evidence.

`app/` remains the single Flutter Experience implementation for Web Workspace, Desktop and Mobile. A future `app/web/` platform target is generated/configuration support, not a second Web product or design authority.

Public Website and Web Workspace are deployed separately so public SEO/content delivery and authenticated workspace runtime can evolve without mixing trust, caching, release or availability boundaries. Both remain governed by the same Product Architecture and Experience Constitution.

Historical `templates/`, `static/` and `experience_v2/` implementations remain retired. They must not be restored as a shortcut. Any unique business capability found in history must first be traced into the current Product Core/API and then exposed through an approved surface.

## 4. Shared contract and capability boundary

All operational surfaces consume the same canonical meanings:

```text
actor + tenant/scope
→ SubjectContext or BrandFocus
→ Permission / approval / effect fence
→ canonical API / typed ViewModel
→ Canonical Data + Evidence lineage
→ state/result/evaluation/return
```

Surface capability must be explicit: `AVAILABLE`, `DEGRADED`, `DESKTOP_REQUIRED`, `PERMISSION_REQUIRED`, `UNAVAILABLE` or `UNKNOWN`. A Web or Mobile request may enqueue or hand off an authorized Desktop/SYSTEM task only through a real canonical contract with status, Evidence and recovery. It may not report success from an optimistic UI, HTTP 200, registration record or fixture.

Optional product-account login, recovery and settings are part of current engineering closure; ordinary work has no global account wall. Free Google login and email codes use the existing account owner; Apple sign-in requires actual developer-account activation. Multi-surface approval does not authorize a second login database, browser-side credential store or bypass of protected server routes.

## 5. Jev product decision

Historical decision only: Jev was approved as a candidate **typed decision and evaluation provider** behind the one canonical `lumenis/system/ai_gateway/`. Jev is not a replacement for a generative language provider and is not an independent AI gateway.

Current policy keeps Jev inactive. The following design/licensing material remains research, not activation authority.

Historical candidate uses:

- routing and classification over source-backed state;
- Evidence relevance/quality scoring and uncertainty disclosure;
- risk triage and review prioritization;
- Agent route selection and output/claim verification;
- evaluation of business/model outputs against typed questions.

Forbidden ownership:

- no Canonical Data, Evidence, Permission, metric, workflow, final business-decision or effect-authorization ownership;
- no direct API key or provider call from Public Website, Web Workspace, Desktop UI or Mobile;
- no promotion of probabilities, confidence or model output to Production Truth;
- no silent fallback that changes a typed decision into unrelated free-text generation.

Historical lifecycle (inactive under current policy):

```text
OFF
→ ROUND 07 adapter/contract implementation
→ SHADOW evaluation against named datasets and human decisions
→ legal/security/privacy/cost/runtime review
→ ACTIVE only for explicitly approved typed tasks
```

Any future separately approved activation must pin an accepted model version; a moving alias is limited to development/probing. Every persisted decision record must identify provider, model/version, input/output schema, probabilities, confidence, request ID, latency, token/cost data when supplied, input/output hashes, actor/domain/object scope and Evidence references. Low confidence or schema failure remains `UNKNOWN` or requires human review.

Vendor references used for this decision: [System One / Jev launch](https://typesafe.ai/blog/introducing-system-one-models-and-jev), [API](https://docs.typesafe.ai/api), [models](https://docs.typesafe.ai/models), [primitives](https://docs.typesafe.ai/primitives), [confidence](https://docs.typesafe.ai/confidence), and [Master Customer Agreement](https://typesafe.ai/legal/mca). These references describe a candidate external provider; current source/runtime must independently verify every production claim.

## 6. Current implementation truth

Historical approval-time baseline (not a live status table):

| Item | Approval-time observation |
| --- | --- |
| Product Core/API ownership | `IMPLEMENTED` in current Python/Flask owners; completeness varies by workflow |
| Flutter Desktop/Mobile source | `PARTIAL` |
| Flutter Web target / Web Workspace | `ABSENT` |
| Public Website | `ABSENT` |
| Multi-surface deployment | `ABSENT` |
| Jev adapter/provider configuration | `ABSENT` |
| Jev runtime/evaluation evidence | `LIVE_UNVERIFIED` |

Approval is not implementation evidence. Current source contains the trilingual Astro Website, Flutter Web target and same-origin `/workspace` host; this establishes source and route presence only. Protected CTH/BMP browser access, deployed commercial entry, and complete four-surface real-user operation remain unaccepted. Jev was retired by the Product Owner; its former provider gate is not pending product work, and no Jev activation is authorized. None of these source records establishes RELEASED or OPERATING.

## 7. Historical placement; current coverage is in the Source Owner Index

- ROUND 02: record this decision; reconcile sole authorities, naming, validators and compatibility classification. No Web/Jev implementation.
- Historical ROUND 07 planned Jev research; that implementation instruction is superseded. Jev remains inactive under current AGENTS policy.
- ROUND 08: build the Cross-Surface Experience Foundation: Public Website foundation, Flutter Web Workspace shell, Desktop shell, Mobile Companion shell, shared state/accessibility/localization and capability boundary.
- ROUND 09–14: every workflow specification records a surface matrix: Web primary/available, Desktop enhanced/exclusive, Mobile view/notify/approve/light action, Public Website explanation/demo only.
- ROUND 15: prove Public Website → trial/login entry → Web Workspace → real context/workflow/Evidence → Desktop advanced execution when applicable → Web result → Mobile notification/approval when applicable → Report/Evaluation/Learning.

Stop and return `BLOCKED` rather than creating a second truth when identity/tenant scope, Permission, Evidence, API/ViewModel, desktop handoff, provider legal terms, secret handling or runtime ownership is unresolved.

## 2026-10-08 全产品智能交互的四端落实

本节是唯一Product Architecture和Experience §38的四端路由，不新增设计权威。用户要求覆盖每个现有产品角落，44屏与官网已有内容家族均须有具体应用；页面形态按任务选择，不能强塞同一聊天/卡片模板。

| 入口 | 现有任务中的具体落实 | 同一任务与验收要求 |
|---|---|---|
| Public Website | 产品/能力说明用可操作且标注真实状态的示例、对照和步骤；帮助/说明/更新日志可查找并定位相关能力；真实入口明确。 | 演示数据和实测运行明确分开；不从示例开通业务权限，不把未来能力写成已上线。手机官网也独立排版，允许内容所需滚动。 |
| Web Workspace | 实际材料进入阅读器、对照、图表、方案表单、文稿/媒体工作台；就地筛选与修改，来源和结果联动。 | 同Task/Brief/Scope/Source/版本；键盘/屏幕阅读器完整；流式中断、断网与重开保留可确认进度。 |
| Desktop | 延续同一工作对象，适配多窗格、大文件、真实播放器、横向轨道/选区和本机系统朗读。 | 不新建本地业务真相；本机处理/服务端执行分别显示；关闭/重启恢复版本及用户选区，修改后旧播放不继续。 |
| Mobile Companion | 用触控顺序重排事实、依据、审阅、允许的轻编辑/参数调整、审批和通知返回；可把复杂工作接续到Web/Desktop。 | 不把不可运行的重计算假装在手机完成；可用动作与原权限一致，不重新解释任务或重复选择来源；焦点与回退可达。 |

四端共同要求：整体视觉采用PO确定的像素赛博＋植物生态＋复古未来主义风格，布局与操作依当前任务和屏幕合同；原创手绘彩绘用于身份/功能图标及适合的局部页面元素。功能glyph与第三方来源标识分层，颜色有节制；保留有用丰富交互、中英韩/无障碍，操作端避免不必要整页上下滑动且不截断必要长文。各端实际实现/运行证据独立记录，文档同步不提升已有状态。本轮仅更新规则和设计输入，不自动派工。


### 2026-10-08 前端审计与工具维护增补（历史授权快照）

按当时PO指令，前端直接构建真实源码，不等待独立设计稿/Figma或M逐屏DESIGN_READY审批；Figma和设计节点仅为有日期的局部证据，不作为实现前置。本段旧拓扑“独立F＋唯一业务窗口/W6占席”仅保留为2026-10-08历史授权，不再形成现行派工限制。当前并行安排由最新直接PO指令决定；本文不记录当前窗口停/开命令。实际代码、设计和验收状态仍需独立核实，本段不派发或恢复窗口。

工具维护保护现有模型/effort/tier、登录方式、权限、网络/代理及会话；只更新核实的稳定兼容版本，开发插件不变成产品依赖。需要中断桌面/会话、重启、扩大权限或新增登录/费用时等待精确批准。既有未发布源代码、私有配置及生产DB保持原边界。

### 2026-10-08 成熟操作与智能增强的四端一致性

按Product Architecture与Experience§38，四表面保留既有角色，按当前PO设备范围建设、分别验收；保留完整范围，不新增入口。Web/Desktop承载实际编辑，Mobile保持已批准触控/轻操作/恢复范围，适用的录音与音频播放逐端验证，缺设备的项目保留OPEN；官网呈现真实已验证能力和明确标记的演示，不宣传尚未实现的媒体/AI。GPT/Apple/Tesla只作为操作、反馈、撤回和状态连续性的参考。SH-01/BMP-08完整媒体操作沿原合同，必要媒体时间轴横向滚动不违反非必要上下滚动。产品范围不等于当前派工；窗口状态由最新直接指令及本地新鲜证据核实。批准依据：`evidence/approvals/PO-20261011-WHOLE-PRODUCT-REUSE-EXPERIENCE.json`。

### 2026-10-11 产品内浏览器的端能力（通用电脑控制撤回）

| 端 | 当前交付要求 | 边界 |
|---|---|---|
| Web Workspace | 在原任务中显示真实网页、完成获准操作、人工接管/停止、返回及保存恢复；按Web任务独立验收 | 由既有 SYSTEM 会话/权限服务执行，不是任意 iframe 或控制访客电脑 |
| Desktop Windows/macOS | 同一浏览器与业务合同的原生工作区承载；按当前PO设备范围实施并独立验收 | 不控制任意本机/远程应用，不读取个人浏览器档案 |
| iOS Companion | 当前任务内浏览器视口、触控/键盘、状态、接管/停止、返回；按当前PO设备范围实施并独立验收 | 不控制手机或远程电脑操作系统 |
| Public Website | 说明已验证能力、标记演示并进入 Workspace | 不以宣传视频替代运行证明 |

移除的是通用桌面/OS控制要求；原生客户端、产品内浏览、文件导入导出和媒体编辑范围保留。AI 增强跨端复用同一任务/版本，缺模型不阻断正常业务。

四端没有第二套浏览器/数据/账号体系。外部打开是用户选择，不自动替代失败的内置链；真实运行、设备权限和用户结果分别验收。细则唯一归Experience §11/§38、SYS-06及Overlay。
